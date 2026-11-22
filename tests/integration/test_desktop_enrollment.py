from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from apps.desktop.services.enrollment_worker import EnrollmentWorker
from packages.device_protocol.fingerprint.models import FingerSlot
from services.backend.app import main as backend
from services.backend.app.api import devices, users
from services.backend.app.database.base import Base
from services.backend.app.models import Device, User


INPUT = {"displayName": "Desktop Test", "deviceId": "desktop-test-device", "fingerSlot": "right_index"}


@pytest.fixture
def enrollment_api(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'desktop-test.db'}")
    factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(backend, "engine", engine)
    monkeypatch.setattr(users, "SessionLocal", factory)
    monkeypatch.setattr(devices, "SessionLocal", factory)
    with TestClient(backend.app) as client:
        yield client, factory


def test_real_registration_simulated_enrollment_and_pairing(enrollment_api):
    client, factory = enrollment_api
    worker = EnrollmentWorker(client)
    registration = worker.register(INPUT)
    assert registration["error"] is None
    assert registration["snapshot"]["registered"] is True
    assert registration["snapshot"]["paired"] is False
    result = worker.complete()
    assert result["error"] is None
    assert result["snapshot"]["pairingStatus"] == "PENDING"
    assert worker.device.verify_finger(worker.registration["user_id"], FingerSlot.RIGHT_INDEX, scan_success=True)
    assert worker.complete() == result
    assert worker.register(INPUT)["error"] == "ALREADY_STARTED"
    encoded = json.dumps(result)
    assert "pairing_code" not in encoded
    assert "private_key" not in encoded
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(Device)) == 1


@pytest.mark.parametrize("override", [{"displayName": " "}, {"displayName": "x" * 101}, {"deviceId": ""}, {"deviceId": "x" * 37}, {"fingerSlot": "unknown"}])
def test_invalid_input_does_not_create_backend_user(enrollment_api, override):
    client, factory = enrollment_api
    worker = EnrollmentWorker(client)
    assert worker.register(INPUT | override)["error"] == "VALIDATION_ERROR"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_duplicate_device_preserves_partial_registration(enrollment_api):
    client, factory = enrollment_api
    first = EnrollmentWorker(client)
    first.register(INPUT)
    assert first.complete()["error"] is None
    second = EnrollmentWorker(client)
    second.register(INPUT)
    result = second.complete()
    assert result["error"] == "DEVICE_ALREADY_REGISTERED"
    assert result["snapshot"]["registered"] and result["snapshot"]["enrolled"]
    assert not result["snapshot"]["paired"]
    with factory() as db:
        assert db.get(Device, INPUT["deviceId"]).user_id == first.registration["user_id"]


def test_expired_pairing_does_not_enroll_finger(enrollment_api):
    client, _ = enrollment_api
    worker = EnrollmentWorker(client)
    worker.register(INPUT)
    worker.registration["pairing_code_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    assert worker.complete()["error"] == "PAIRING_EXPIRED"
    assert not worker.enrolled


def test_connection_failure_retries_pairing_without_recreating_user(enrollment_api):
    client, factory = enrollment_api
    worker = EnrollmentWorker(client)
    worker.register(INPUT)
    class Disconnected:
        def post(self, *args, **kwargs):
            raise httpx.ConnectError("Do not expose this string")
    worker.client = Disconnected()
    assert worker.complete()["retryable"]
    key = worker.device.export_public_key()
    worker.client = client
    assert worker.complete()["snapshot"]["paired"]
    assert worker.device.export_public_key() == key
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1


def test_write_timeout_is_not_retried(enrollment_api):
    client, _ = enrollment_api
    worker = EnrollmentWorker(client)
    worker.register(INPUT)
    class Timeout:
        calls = 0
        def post(self, *args, **kwargs):
            self.calls += 1
            raise httpx.ReadTimeout("secret pairing credential")
    timeout = Timeout()
    worker.client = timeout
    result = worker.complete()
    assert result["error"] == "OUTCOME_UNKNOWN"
    assert not result["retryable"]
    assert "secret" not in json.dumps(result)
    worker.complete()
    assert timeout.calls == 1


def test_device_rejection_does_not_pair(enrollment_api, monkeypatch):
    client, _ = enrollment_api
    worker = EnrollmentWorker(client)
    worker.register(INPUT)
    monkeypatch.setattr(worker.device, "enroll_finger", lambda *args: False)
    result = worker.complete()
    assert result["error"] == "DEVICE_REJECTED"
    assert result["retryable"]
    assert not result["snapshot"]["paired"]

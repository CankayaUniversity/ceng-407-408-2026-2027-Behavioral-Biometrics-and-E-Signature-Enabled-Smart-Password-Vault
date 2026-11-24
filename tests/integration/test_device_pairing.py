from base64 import urlsafe_b64encode
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.device_protocol.fingerprint.models import FingerSlot
from packages.device_protocol.protocol.challenge import AuthenticationChallenge
from packages.device_protocol.simulator.mock_device import MockFingerprintDevice
from services.backend.app import main as backend
from services.backend.app.api import challenges, devices, users, verification
from services.backend.app.database.base import Base
from services.backend.app.models import AuthChallenge, PairingCode, Session
from services.backend.app.api import sessions
from services.backend.app.session_service import (
    get_session_for_user,
    revoke_session_for_user,
)
from hashlib import sha256
from secrets import token_urlsafe

@pytest.fixture
def pairing_api(tmp_path, monkeypatch):
    database = tmp_path / "pairing-test.db"
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(backend, "engine", engine)
    monkeypatch.setattr(users, "SessionLocal", session_factory)
    monkeypatch.setattr(devices, "SessionLocal", session_factory)
    monkeypatch.setattr(challenges, "SessionLocal", session_factory)
    monkeypatch.setattr(verification, "SessionLocal", session_factory)
    monkeypatch.setattr(sessions, "SessionLocal", session_factory)

    with TestClient(backend.app) as client:
        yield client, session_factory


def register_user(client):
    response = client.post("/v1/users", json={"display_name": "Pairing Test"})
    assert response.status_code == 201
    return response.json()


def pair_device(client, registration, *, user_id=None, device_id=None):
    key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    public_key = urlsafe_b64encode(key).decode("ascii").rstrip("=")

    return client.post(
        "/v1/devices/pair",
        headers={"Authorization": f"Bearer {registration['pairing_code']}"},
        json={
            "user_id": user_id or registration["user_id"],
            "device_id": device_id or str(uuid4()),
            "public_key": public_key,
        },
    )


def assert_unauthorized(response):
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_pairing_code_can_only_be_used_once(pairing_api):
    client, _ = pairing_api
    registration = register_user(client)

    first = pair_device(client, registration)

    assert first.status_code == 201
    assert first.json()["pairing_status"] == "PENDING"
    assert first.json()["user_id"] == registration["user_id"]
    assert_unauthorized(pair_device(client, registration))


def test_expired_pairing_code_is_rejected(pairing_api):
    client, session_factory = pairing_api
    registration = register_user(client)

    with session_factory.begin() as db:
        code = db.get(PairingCode, registration["user_id"])
        assert code is not None
        code.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    assert_unauthorized(pair_device(client, registration))


def test_pairing_code_cannot_be_used_for_another_user(pairing_api):
    client, _ = pairing_api
    owner = register_user(client)
    other_user = register_user(client)

    response = pair_device(client, owner, user_id=other_user["user_id"])

    assert_unauthorized(response)
    assert pair_device(client, owner).status_code == 201


def test_duplicate_device_does_not_consume_pairing_code(pairing_api):
    client, _ = pairing_api
    first_user = register_user(client)
    second_user = register_user(client)
    device_id = str(uuid4())

    assert pair_device(client, first_user, device_id=device_id).status_code == 201

    duplicate = pair_device(client, second_user, device_id=device_id)

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DEVICE_ALREADY_REGISTERED"
    assert pair_device(client, second_user).status_code == 201

def test_login_challenge_is_saved_with_pending_session(pairing_api):
    client, session_factory = pairing_api
    owner = register_user(client)
    pairing = pair_device(client, owner)
    assert pairing.status_code == 201
    device_id = pairing.json()["device_id"]

    response = client.post(
        "/v1/auth/challenges",
        json={
            "user_id": owner["user_id"],
            "device_id": device_id,
            "purpose": "login",
        },
    )

    assert response.status_code == 201
    body = response.json()
    challenge = body["challenge"]

    with session_factory() as db:
        session = db.get(Session, body["session_id"])
        saved = db.get(AuthChallenge, challenge["challenge_id"])

        assert session is not None
        assert session.user_id == owner["user_id"]
        assert session.state == "AUTH_PENDING"

        assert saved is not None
        assert saved.session_id == session.session_id
        assert saved.user_id == owner["user_id"]
        assert saved.device_id == device_id
        assert saved.protocol_version == challenge["version"] == 1
        assert saved.request_id == challenge["request_id"]
        assert saved.nonce == challenge["nonce"]
        assert saved.purpose == "login"
        assert saved.consumed_at is None
        assert saved.expires_at == datetime.fromisoformat(challenge["expires_at"])
        assert saved.expires_at < session.expires_at


def test_login_challenge_rejects_device_owned_by_another_user(pairing_api):
    client, _ = pairing_api
    owner = register_user(client)
    other_user = register_user(client)
    pairing = pair_device(client, owner)
    assert pairing.status_code == 201

    response = client.post(
        "/v1/auth/challenges",
        json={
            "user_id": other_user["user_id"],
            "device_id": pairing.json()["device_id"],
            "purpose": "login",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

@pytest.fixture
def pending_login(pairing_api):
    client, session_factory = pairing_api
    owner_id = register_user(client)["user_id"]
    registration = register_user(client)
    pairing = pair_device(client, registration)
    assert pairing.status_code == 201

    response = client.post(
        "/v1/auth/challenges",
        json={
            "user_id": registration["user_id"],
            "device_id": pairing.json()["device_id"],
            "purpose": "login",
        },
    )
    assert response.status_code == 201
    body = response.json()

    return (
        session_factory,
        registration["user_id"],
        owner_id,
        body["session_id"],
        body["challenge"]["challenge_id"],
    )


def test_expiration_takes_priority_over_revocation(pending_login):
    session_factory, owner_id, _, session_id, challenge_id = pending_login

    with session_factory.begin() as db:
        session = db.get(Session, session_id)
        assert session is not None
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    with session_factory.begin() as db:
        session = revoke_session_for_user(
            db, session_id=session_id, owner_id=owner_id
        )
        assert session is not None
        assert session.state == "EXPIRED"
        assert session.revoked_at is None

    with session_factory() as db:
        challenge = db.get(AuthChallenge, challenge_id)
        assert challenge is not None
        assert challenge.consumed_at is not None


def test_repeated_revocation_preserves_original_timestamp(pending_login):
    session_factory, owner_id, _, session_id, challenge_id = pending_login

    with session_factory.begin() as db:
        session = revoke_session_for_user(
            db, session_id=session_id, owner_id=owner_id
        )
        assert session is not None
        assert session.state == "REVOKED"
        first_revoked_at = session.revoked_at
        assert first_revoked_at is not None

    with session_factory.begin() as db:
        session = revoke_session_for_user(
            db, session_id=session_id, owner_id=owner_id
        )
        assert session is not None
        assert session.state == "REVOKED"
        assert session.revoked_at == first_revoked_at

        challenge = db.get(AuthChallenge, challenge_id)
        assert challenge is not None
        assert challenge.consumed_at == first_revoked_at


def test_other_user_cannot_read_or_revoke_session(pending_login):
    session_factory, _, other_user_id, session_id, challenge_id = pending_login

    with session_factory.begin() as db:
        assert get_session_for_user(
            db, session_id=session_id, owner_id=other_user_id
        ) is None
        assert revoke_session_for_user(
            db, session_id=session_id, owner_id=other_user_id
        ) is None

    with session_factory() as db:
        session = db.get(Session, session_id)
        challenge = db.get(AuthChallenge, challenge_id)
        assert session is not None
        assert session.state == "AUTH_PENDING"
        assert session.revoked_at is None
        assert challenge is not None
        assert challenge.consumed_at is None

@pytest.fixture
def signed_login(pairing_api):
    client, session_factory = pairing_api
    registration = register_user(client)
    user_id = registration["user_id"]

    device = MockFingerprintDevice(str(uuid4()))
    device.enroll(user_id)
    device.enroll_finger(user_id, FingerSlot.RIGHT_INDEX)

    public_key = (
        urlsafe_b64encode(device.export_public_key()).decode("ascii").rstrip("=")
    )
    pairing = client.post(
        "/v1/devices/pair",
        headers={"Authorization": f"Bearer {registration['pairing_code']}"},
        json={
            "user_id": user_id,
            "device_id": device.device_id,
            "public_key": public_key,
        },
    )
    assert pairing.status_code == 201

    issuance = client.post(
        "/v1/auth/challenges",
        json={
            "user_id": user_id,
            "device_id": device.device_id,
            "purpose": "login",
        },
    )
    assert issuance.status_code == 201
    body = issuance.json()

    challenge = AuthenticationChallenge(**body["challenge"])
    signed_response = device.respond_to_challenge(
        challenge, FingerSlot.RIGHT_INDEX, scan_success=True
    )

    return client, session_factory, body["session_id"], asdict(signed_response)


def test_signed_login_succeeds_only_once(signed_login):
    client, session_factory, session_id, signed_response = signed_login

    response = client.post("/v1/auth/verify", json=signed_response)

    assert response.status_code == 200
    assert response.json()["session"]["session_id"] == session_id
    assert response.json()["session"]["state"] == "TRUSTED"

    repeated = client.post("/v1/auth/verify", json=signed_response)

    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "REPLAY_DETECTED"

    with session_factory() as db:
        challenge = db.get(AuthChallenge, signed_response["challenge_id"])
        assert challenge is not None
        assert challenge.consumed_at is not None


def test_signed_login_rejects_expired_challenge(signed_login):
    client, session_factory, session_id, signed_response = signed_login

    with session_factory.begin() as db:
        challenge = db.get(AuthChallenge, signed_response["challenge_id"])
        assert challenge is not None
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    response = client.post("/v1/auth/verify", json=signed_response)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "EXPIRED_CHALLENGE"

    with session_factory() as db:
        session = db.get(Session, session_id)
        assert session is not None
        assert session.state == "AUTH_PENDING"


def test_signed_login_rejects_tampered_verification_result(signed_login):
    client, _, _, signed_response = signed_login
    tampered_response = {
        **signed_response,
        "payload": {**signed_response["payload"], "verified": False},
    }

    response = client.post("/v1/auth/verify", json=tampered_response)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SIGNATURE"

    original = client.post("/v1/auth/verify", json=signed_response)
    assert original.status_code == 200


def test_signed_login_rejects_mismatched_challenge_context(signed_login):
    client, session_factory, session_id, signed_response = signed_login
    challenge_id = signed_response["challenge_id"]

    with session_factory.begin() as db:
        challenge = db.get(AuthChallenge, challenge_id)
        assert challenge is not None
        challenge.nonce = "different-" + challenge.nonce

    response = client.post("/v1/auth/verify", json=signed_response)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "REQUEST_MISMATCH"

    with session_factory() as db:
        challenge = db.get(AuthChallenge, challenge_id)
        session = db.get(Session, session_id)
        assert challenge is not None
        assert session is not None
        assert challenge.consumed_at is None
        assert session.state == "AUTH_PENDING"

def test_session_controls_require_a_valid_token(signed_login):
    client, _, session_id, signed_response = signed_login

    login = client.post("/v1/auth/verify", json=signed_response)
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session_url = f"/v1/sessions/{session_id}"

    # Knowing the session ID alone permits neither operation.
    assert client.get(session_url).status_code == 401
    assert client.post(f"{session_url}/revoke").status_code == 401

    invalid_headers = {"Authorization": "Bearer invalid-token"}
    assert client.get(session_url, headers=invalid_headers).status_code == 401
    assert (
        client.post(f"{session_url}/revoke", headers=invalid_headers).status_code
        == 401
    )

    status = client.get(session_url, headers=headers)
    assert status.status_code == 200
    assert status.json()["session_id"] == session_id
    assert status.json()["state"] == "TRUSTED"

    revoked = client.post(f"{session_url}/revoke", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json()["state"] == "REVOKED"

    assert client.get(session_url, headers=headers).status_code == 401
    assert client.post(f"{session_url}/revoke", headers=headers).status_code == 401


def test_expired_session_rejects_its_token(signed_login):
    client, session_factory, session_id, signed_response = signed_login

    login = client.post("/v1/auth/verify", json=signed_response)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    with session_factory.begin() as db:
        session = db.get(Session, session_id)
        assert session is not None
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    session_url = f"/v1/sessions/{session_id}"
    assert client.get(session_url, headers=headers).status_code == 401
    assert client.post(f"{session_url}/revoke", headers=headers).status_code == 401

    with session_factory() as db:
        session = db.get(Session, session_id)
        assert session is not None
        assert session.state == "EXPIRED"

def test_session_token_cannot_access_another_users_session(
    signed_login, pending_login
):
    client, session_factory, source_id, signed_response = signed_login
    _, _, _, target_id, _ = pending_login

    login = client.post("/v1/auth/verify", json=signed_response)
    assert login.status_code == 200
    source_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    target_token = token_urlsafe(32)
    with session_factory.begin() as db:
        target = db.get(Session, target_id)
        assert target is not None
        target.state = "TRUSTED"
        target.access_token_hash = sha256(target_token.encode("ascii")).hexdigest()

    source_url = f"/v1/sessions/{source_id}"
    target_url = f"/v1/sessions/{target_id}"
    target_headers = {"Authorization": f"Bearer {target_token}"}

    assert client.get(source_url, headers=source_headers).status_code == 200
    assert client.get(target_url, headers=source_headers).status_code == 401
    assert client.post(f"{target_url}/revoke", headers=source_headers).status_code == 401

    target_status = client.get(target_url, headers=target_headers)
    assert target_status.status_code == 200
    assert target_status.json()["state"] == "TRUSTED"
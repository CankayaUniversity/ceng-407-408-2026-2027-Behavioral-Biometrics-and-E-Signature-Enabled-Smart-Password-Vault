from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.backend.app import main as backend
from services.backend.app.api import challenges, devices, users
from services.backend.app.database.base import Base
from services.backend.app.models import AuthChallenge, PairingCode, Session

from services.backend.app.session_service import (
    get_session_for_user,
    revoke_session_for_user,
)


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
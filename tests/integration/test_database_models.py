from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session as DatabaseSession

from services.backend.app.database.base import Base
from services.backend.app.database.connection import enable_foreign_keys
from services.backend.app.models import (
    AuthChallenge,
    Device,
    SecurityEvent,
    Session,
    User,
)


@pytest.fixture
def engine(tmp_path):
    database_path = (tmp_path / "test.db").as_posix()
    test_engine = create_engine(f"sqlite:///{database_path}")
    event.listen(test_engine, "connect", enable_foreign_keys)
    Base.metadata.create_all(test_engine)

    try:
        yield test_engine
    finally:
        test_engine.dispose()


def test_tables_created(engine):
    # Running initialization again should preserve existing tables.
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) == {
        "users",
        "devices",
        "sessions",
        "auth_challenges",
        "security_events",
    }


def test_save_related_records(engine):
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    with DatabaseSession(engine) as db:
        user = User(display_name="Test User")
        db.add(user)
        db.flush()

        device = Device(
            user_id=user.user_id,
            public_key="test-public-key",
        )
        session = Session(
            user_id=user.user_id,
            expires_at=expires_at,
        )
        db.add_all([device, session])
        db.flush()

        challenge = AuthChallenge(
            user_id=user.user_id,
            device_id=device.device_id,
            session_id=session.session_id,
            purpose="LOGIN",
            expires_at=expires_at,
        )
        security_event = SecurityEvent(
            session_id=session.session_id,
            event_type="CHALLENGE_CREATED",
            severity="INFO",
            source="backend",
            sanitized_metadata={"purpose": "LOGIN"},
        )
        db.add_all([challenge, security_event])
        db.commit()

        user_id = user.user_id
        device_id = device.device_id
        session_id = session.session_id
        challenge_id = challenge.challenge_id
        event_id = security_event.event_id

    with DatabaseSession(engine) as db:
        assert db.get(User, user_id).devices[0].device_id == device_id
        assert db.get(Device, device_id).user.user_id == user_id
        assert db.get(Session, session_id).state == "LOCKED"
        assert db.get(AuthChallenge, challenge_id).consumed_at is None
        assert db.get(SecurityEvent, event_id).session_id == session_id
        saved_session = db.get(Session, session_id)
        assert saved_session.created_at.tzinfo == timezone.utc
        assert saved_session.expires_at == expires_at
        assert saved_session.revoked_at is None
        assert saved_session.last_reauth_at is None
        assert db.get(Device, device_id).revoked_at is None
        assert db.get(User, user_id).created_at.tzinfo == timezone.utc
        assert db.get(SecurityEvent, event_id).timestamp.tzinfo == timezone.utc


def test_reject_device_without_existing_user(engine):
    with DatabaseSession(engine) as db:
        db.add(Device(
            user_id="missing-user",
            public_key="test-public-key",
        ))

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()


def test_reject_duplicate_user_id(engine):
    with DatabaseSession(engine) as db:
        db.add(User(user_id="same-id", display_name="First User"))
        db.commit()

    with DatabaseSession(engine) as db:
        db.add(User(user_id="same-id", display_name="Second User"))

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()


@pytest.mark.parametrize("offset_hours", [0, 3, -5])
def test_timestamps_round_trip_as_utc(engine, offset_hours):
    local_time = datetime(2026, 11, 15, 1, 30, tzinfo=timezone(timedelta(hours=offset_hours)))
    expected = local_time.astimezone(timezone.utc)

    with DatabaseSession(engine) as db:
        user = User(display_name="Timezone test", created_at=local_time)
        db.add(user)
        db.flush()
        device = Device(user_id=user.user_id, public_key="test-key", revoked_at=local_time)
        session = Session(
            user_id=user.user_id,
            created_at=local_time,
            expires_at=local_time,
            revoked_at=local_time,
            last_reauth_at=local_time,
        )
        db.add_all([device, session])
        db.flush()
        challenge = AuthChallenge(
            user_id=user.user_id,
            device_id=device.device_id,
            session_id=session.session_id,
            purpose="LOGIN",
            expires_at=local_time,
            consumed_at=local_time,
        )
        event = SecurityEvent(
            session_id=session.session_id,
            event_type="TEST",
            severity="INFO",
            source="backend",
            timestamp=local_time,
        )
        db.add_all([challenge, event])
        db.commit()
        records = [
            (User, user.user_id, ["created_at"]),
            (Device, device.device_id, ["revoked_at"]),
            (Session, session.session_id, ["created_at", "expires_at", "revoked_at", "last_reauth_at"]),
            (AuthChallenge, challenge.challenge_id, ["expires_at", "consumed_at"]),
            (SecurityEvent, event.event_id, ["timestamp"]),
        ]

    with DatabaseSession(engine) as db:
        for model, record_id, fields in records:
            record = db.get(model, record_id)
            for field in fields:
                actual = getattr(record, field)
                assert actual.tzinfo == timezone.utc
                assert actual == expected
                assert actual < expected + timedelta(seconds=1)


def test_reject_timestamp_without_timezone(engine):
    with DatabaseSession(engine) as db:
        user = User(display_name="Timezone test")
        db.add(user)
        db.flush()
        db.add(Session(user_id=user.user_id, expires_at=datetime(2026, 11, 15)))
        with pytest.raises(StatementError, match="timezone-aware"):
            db.commit()
        db.rollback()

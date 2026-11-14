from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
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
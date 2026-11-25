from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DatabaseSession

from .models import AuthChallenge, Session
from .audit_service import record_security_event


INITIAL_SESSION_TTL = timedelta(minutes=15)
NONTERMINAL_STATES = (
    "LOCKED",
    "AUTH_PENDING",
    "TRUSTED",
    "SUSPICIOUS",
    "REAUTH_REQUIRED",
)


def create_pending_session(db: DatabaseSession, *, user_id: str) -> Session:
    session = Session(
        user_id=user_id,
        state="AUTH_PENDING",
        expires_at=datetime.now(timezone.utc) + INITIAL_SESSION_TTL,
    )
    db.add(session)
    db.flush()
    return session


def _invalidate_challenges(
    db: DatabaseSession, *, session_id: str, now: datetime
) -> None:
    db.execute(
        update(AuthChallenge)
        .where(
            AuthChallenge.session_id == session_id,
            AuthChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )


def _expire_session(
    db: DatabaseSession, *, session_id: str, owner_id: str, now: datetime
) -> None:
    result = db.execute(
        update(Session)
        .where(
            Session.session_id == session_id,
            Session.user_id == owner_id,
            Session.state.in_(NONTERMINAL_STATES),
            Session.expires_at <= now,
        )
        .values(state="EXPIRED")
    )
    if result.rowcount == 1:
        _invalidate_challenges(db, session_id=session_id, now=now)
        record_security_event(
            db,
            event_type="SESSION_EXPIRED",
            severity="INFO",
            reason_code="SESSION_DEADLINE_REACHED",
            session_id=session_id,
        )


def _load_session(
    db: DatabaseSession, *, session_id: str, owner_id: str
) -> Session | None:
    return db.scalar(
        select(Session)
        .where(
            Session.session_id == session_id,
            Session.user_id == owner_id,
        )
        .execution_options(populate_existing=True)
    )


def get_session_for_user(
    db: DatabaseSession, *, session_id: str, owner_id: str
) -> Session | None:
    now = datetime.now(timezone.utc)
    _expire_session(db, session_id=session_id, owner_id=owner_id, now=now)
    return _load_session(db, session_id=session_id, owner_id=owner_id)


def revoke_session_for_user(
    db: DatabaseSession, *, session_id: str, owner_id: str
) -> Session | None:
    now = datetime.now(timezone.utc)
    _expire_session(db, session_id=session_id, owner_id=owner_id, now=now)

    result = db.execute(
        update(Session)
        .where(
            Session.session_id == session_id,
            Session.user_id == owner_id,
            Session.state.in_(NONTERMINAL_STATES),
            Session.expires_at > now,
        )
        .values(state="REVOKED", revoked_at=now)
    )
    if result.rowcount == 1:
        _invalidate_challenges(db, session_id=session_id, now=now)
        record_security_event(
            db,
            event_type="SESSION_REVOKED",
            severity="INFO",
            reason_code="OWNER_REVOKED_SESSION",
            session_id=session_id,
            actor_user_id=owner_id,
        )

    return _load_session(db, session_id=session_id, owner_id=owner_id)
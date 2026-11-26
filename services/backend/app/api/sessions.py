from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DatabaseSession

from ..audit_service import record_security_event
from ..database.connection import SessionLocal
from ..models import Session
from ..models.security_event import SecurityEvent
from ..schemas.session import SessionResponse
from ..session_service import get_session_for_user, revoke_session_for_user


router = APIRouter(prefix="/v1/sessions", tags=["sessions"])
session_bearer = HTTPBearer(auto_error=False, scheme_name="SessionBearer")
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(session_bearer)
]


class AuditEventResponse(BaseModel):
    event_id: str
    session_id: str | None
    event_type: str
    severity: str
    timestamp: datetime
    reason_code: str | None


def unauthorized(db: DatabaseSession) -> JSONResponse:
    record_security_event(
        db,
        event_type="SESSION_ACCESS_REJECTED",
        severity="WARNING",
        reason_code="SESSION_AUTHORIZATION_FAILED",
    )

    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "A valid session credential is required.",
            },
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def internal_error() -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unable to complete the session operation.",
            },
        },
    )


def authorized_session(
    db: DatabaseSession,
    session_id: str,
    credentials: HTTPAuthorizationCredentials | None,
) -> Session | None:
    if credentials is None:
        return None

    session = db.get(Session, session_id)
    if session is None or session.access_token_hash is None:
        return None

    supplied_hash = sha256(
        credentials.credentials.encode("utf-8")
    ).hexdigest()
    if not compare_digest(supplied_hash, session.access_token_hash):
        return None

    current = get_session_for_user(
        db, session_id=session_id, owner_id=session.user_id
    )
    if (
        current is None
        or current.state in {"EXPIRED", "REVOKED"}
        or current.revoked_at is not None
    ):
        return None

    return current


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_status(session_id: str, credentials: BearerCredentials):
    try:
        with SessionLocal.begin() as db:
            session = authorized_session(db, session_id, credentials)
            if session is None:
                return unauthorized(db)

            return SessionResponse.model_validate(session, from_attributes=True)
    except SQLAlchemyError:
        return internal_error()


@router.post("/{session_id}/revoke", response_model=SessionResponse)
def revoke_session(session_id: str, credentials: BearerCredentials):
    try:
        with SessionLocal.begin() as db:
            session = authorized_session(db, session_id, credentials)
            if session is None:
                return unauthorized(db)

            revoked = revoke_session_for_user(
                db, session_id=session_id, owner_id=session.user_id
            )
            if revoked is None or revoked.state != "REVOKED":
                return unauthorized(db)

            return SessionResponse.model_validate(revoked, from_attributes=True)
    except SQLAlchemyError:
        return internal_error()


@router.get("/{session_id}/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(
    session_id: str,
    credentials: BearerCredentials,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    try:
        with SessionLocal.begin() as db:
            session = authorized_session(db, session_id, credentials)
            if session is None or session.state != "TRUSTED":
                return unauthorized(db)

            owned_session_ids = select(Session.session_id).where(
                Session.user_id == session.user_id
            )
            owned_pairing_events = and_(
                SecurityEvent.session_id.is_(None),
                SecurityEvent.event_type == "DEVICE_PAIRING_SUCCEEDED",
                SecurityEvent.sanitized_metadata["actor_user_id"].as_string()
                == session.user_id,
            )

            events = db.scalars(
                select(SecurityEvent)
                .where(
                    or_(
                        SecurityEvent.session_id.in_(owned_session_ids),
                        owned_pairing_events,
                    )
                )
                .order_by(
                    SecurityEvent.timestamp.desc(),
                    SecurityEvent.event_id.desc(),
                )
                .limit(limit)
            ).all()

            return [
                AuditEventResponse(
                    event_id=event.event_id,
                    session_id=event.session_id,
                    event_type=event.event_type,
                    severity=event.severity,
                    timestamp=event.timestamp,
                    reason_code=event.sanitized_metadata.get("reason_code"),
                )
                for event in events
            ]
    except SQLAlchemyError:
        return internal_error()
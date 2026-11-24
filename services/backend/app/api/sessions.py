from hashlib import sha256
from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DatabaseSession

from ..database.connection import SessionLocal
from ..models import Session
from ..schemas.session import SessionResponse
from ..session_service import get_session_for_user, revoke_session_for_user


router = APIRouter(prefix="/v1/sessions", tags=["sessions"])
session_bearer = HTTPBearer(auto_error=False, scheme_name="SessionBearer")
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(session_bearer)
]


def unauthorized() -> JSONResponse:
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

    supplied_hash = sha256(credentials.credentials.encode("utf-8")).hexdigest()
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
                return unauthorized()

            return SessionResponse.model_validate(session, from_attributes=True)
    except SQLAlchemyError:
        return internal_error()


@router.post("/{session_id}/revoke", response_model=SessionResponse)
def revoke_session(session_id: str, credentials: BearerCredentials):
    try:
        with SessionLocal.begin() as db:
            session = authorized_session(db, session_id, credentials)
            if session is None:
                return unauthorized()

            revoked = revoke_session_for_user(
                db, session_id=session_id, owner_id=session.user_id
            )
            if revoked is None or revoked.state != "REVOKED":
                return unauthorized()

            return SessionResponse.model_validate(revoked, from_attributes=True)
    except SQLAlchemyError:
        return internal_error()
from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from packages.device_protocol.protocol.challenge import AuthenticationChallenge

from ..database.connection import SessionLocal
from ..models import AuthChallenge, Device
from ..session_service import create_pending_session
from ..schemas.auth import (
    AuthChallengeCreateRequest,
    AuthChallengeCreateResponse,
    AuthChallengeResponse,
)


router = APIRouter(prefix="/v1/auth", tags=["authentication"])



def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.post(
    "/challenges",
    response_model=AuthChallengeCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_challenge(request: AuthChallengeCreateRequest):
    if request.purpose == "reauthentication":
        return error_response(
            403,
            "FORBIDDEN",
            "Reauthentication is not available yet.",
        )

    try:
        with SessionLocal.begin() as db:
            device = db.get(Device, request.device_id)
            if (
                device is None
                or device.user_id != request.user_id
                or device.revoked_at is not None
                or device.pairing_status != "PENDING"
            ):
                return error_response(
                    403,
                    "FORBIDDEN",
                    "A challenge cannot be issued for this device.",
                )

            challenge = AuthChallengeResponse.model_validate(
                asdict(
                    AuthenticationChallenge.create(
                        request_id=str(uuid4()),
                        user_id=request.user_id,
                        device_id=request.device_id,
                        purpose=request.purpose,
                    )
                )
            )
            session = create_pending_session(db, user_id=request.user_id)

            db.add(
                AuthChallenge(
                    challenge_id=challenge.challenge_id,
                    protocol_version=challenge.version,
                    request_id=challenge.request_id,
                    user_id=challenge.user_id,
                    device_id=challenge.device_id,
                    session_id=session.session_id,
                    purpose=challenge.purpose,
                    nonce=challenge.nonce,
                    expires_at=challenge.expires_at,
                )
            )

            result = AuthChallengeCreateResponse(
                session_id=session.session_id,
                challenge=challenge,
            )
    except SQLAlchemyError:
        return error_response(
            500,
            "INTERNAL_ERROR",
            "Unable to create authentication challenge.",
        )

    return result
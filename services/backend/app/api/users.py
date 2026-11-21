from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from ..database.connection import SessionLocal
from ..models import PairingCode, User
from ..schemas.user import UserCreateRequest, UserRegistrationResponse


router = APIRouter(prefix="/v1", tags=["users"])
PAIRING_CODE_TTL = timedelta(minutes=5)


@router.post(
    "/users",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(request: UserCreateRequest, http_response: Response):
    pairing_code = token_urlsafe(32)

    try:
        with SessionLocal.begin() as db:
            user = User(display_name=request.display_name)
            db.add(user)
            db.flush()

            expires_at = datetime.now(timezone.utc) + PAIRING_CODE_TTL
            db.add(PairingCode(
                user_id=user.user_id,
                code_hash=sha256(pairing_code.encode("utf-8")).hexdigest(),
                expires_at=expires_at,
            ))

            result = UserRegistrationResponse(
                user_id=user.user_id,
                display_name=user.display_name,
                enrollment_status=user.enrollment_status,
                created_at=user.created_at,
                pairing_code=pairing_code,
                pairing_code_expires_at=expires_at,
            )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unable to create user.",
                }
            },
        )

    http_response.headers["Cache-Control"] = "no-store"
    return result
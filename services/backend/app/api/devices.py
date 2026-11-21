from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from datetime import datetime, timezone
from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..database.connection import SessionLocal
from ..models import Device, PairingCode
from ..schemas.device import DevicePairRequest, DevicePairResponse


router = APIRouter(prefix="/v1", tags=["devices"])
pairing_bearer = HTTPBearer(auto_error=False, scheme_name="PairingCode")


def error_response(status_code: int, code: str, message: str, headers=None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def unauthorized():
    return error_response(
        401,
        "UNAUTHORIZED",
        "A valid pairing code is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def valid_public_key(value: str) -> bool:
    if len(value) != 43 or not value.isascii():
        return False

    try:
        raw_key = urlsafe_b64decode(value + "=")
    except Base64Error:
        return False

    canonical = urlsafe_b64encode(raw_key).decode("ascii").rstrip("=")
    return len(raw_key) == 32 and canonical == value


@router.post(
    "/devices/pair",
    response_model=DevicePairResponse,
    status_code=status.HTTP_201_CREATED,
)
def pair_device(
    request: DevicePairRequest,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(pairing_bearer)
    ],
):
    if credentials is None:
        return unauthorized()

    if not valid_public_key(request.public_key):
        return error_response(
            422,
            "VALIDATION_ERROR",
            "Public key must be 32 raw Ed25519 bytes encoded as unpadded Base64url.",
        )

    code_hash = sha256(credentials.credentials.encode("utf-8")).hexdigest()

    try:
        with SessionLocal.begin() as db:
            consumed = db.execute(
                delete(PairingCode).where(
                    PairingCode.user_id == request.user_id,
                    PairingCode.code_hash == code_hash,
                    PairingCode.expires_at > datetime.now(timezone.utc),
                )
            )
            if consumed.rowcount != 1:
                return unauthorized()

            device = Device(
                device_id=request.device_id,
                user_id=request.user_id,
                public_key=request.public_key,
                pairing_status="PENDING",
            )
            db.add(device)
            db.flush()

            result = DevicePairResponse(
                device_id=device.device_id,
                user_id=device.user_id,
                pairing_status=device.pairing_status,
            )
    except IntegrityError:
        # The failed transaction rolls back pairing code consumption too.
        try:
            with SessionLocal() as db:
                if db.get(Device, request.device_id) is not None:
                    return error_response(
                        409,
                        "DEVICE_ALREADY_REGISTERED",
                        "Device is already registered.",
                    )
        except SQLAlchemyError:
            pass

        return error_response(500, "INTERNAL_ERROR", "Unable to register device.")
    except SQLAlchemyError:
        return error_response(500, "INTERNAL_ERROR", "Unable to register device.")

    return result
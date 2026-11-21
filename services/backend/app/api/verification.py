from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from packages.device_protocol.protocol.response import build_signed_message
from packages.device_protocol.protocol.signing import DeviceSigner

from ..database.connection import SessionLocal
from ..models import AuthChallenge, Device, Session
from ..schemas.auth import AuthVerifyRequest, AuthVerifyResponse
from ..schemas.session import SessionResponse


router = APIRouter(prefix="/v1/auth", tags=["authentication"])


class VerificationConflict(Exception):
    pass


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    headers = {"WWW-Authenticate": "DeviceSignature"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def decode_base64url(value: str, *, size: int) -> bytes:
    expected_length = (size * 8 + 5) // 6
    if len(value) != expected_length or not value.isascii():
        raise ValueError("Invalid Base64url length.")

    decoded = b64decode(
        value + "=" * (-len(value) % 4),
        altchars=b"-_",
        validate=True,
    )
    canonical = urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    if len(decoded) != size or canonical != value:
        raise ValueError("Invalid Base64url encoding.")

    return decoded


@router.post("/verify", response_model=AuthVerifyResponse)
def verify_device_response(request: AuthVerifyRequest):
    try:
        with SessionLocal.begin() as db:
            challenge = db.get(AuthChallenge, request.challenge_id)
            if challenge is None:
                return error_response(400, "INVALID_CHALLENGE", "Unknown challenge.")

            payload = request.payload
            if request.device_id != challenge.device_id:
                return error_response(401, "DEVICE_MISMATCH", "Device mismatch.")

            if (
                request.version != challenge.protocol_version
                or payload.request_id != challenge.request_id
                or payload.user_id != challenge.user_id
                or payload.purpose != challenge.purpose
                or payload.nonce != challenge.nonce
                or challenge.purpose != "login"
            ):
                return error_response(401, "REQUEST_MISMATCH", "Challenge context mismatch.")

            device = db.get(Device, challenge.device_id)
            if (
                device is None
                or device.user_id != challenge.user_id
                or device.revoked_at is not None
                or device.pairing_status != "PENDING"
            ):
                return error_response(403, "FORBIDDEN", "Device is not eligible.")

            try:
                public_key = Ed25519PublicKey.from_public_bytes(
                    decode_base64url(device.public_key, size=32)
                )
                signature = decode_base64url(request.signature, size=64)
            except (ValueError, Base64Error):
                return error_response(401, "INVALID_SIGNATURE", "Device authentication failed.")

            message = build_signed_message(
                version=request.version,
                challenge_id=request.challenge_id,
                device_id=request.device_id,
                payload=payload.model_dump(),
            )
            if not DeviceSigner.verify(public_key, message, signature):
                return error_response(401, "INVALID_SIGNATURE", "Device authentication failed.")

            now = datetime.now(timezone.utc)
            if challenge.consumed_at is not None:
                return error_response(409, "REPLAY_DETECTED", "Challenge is no longer available.")
            if challenge.expires_at <= now:
                return error_response(401, "EXPIRED_CHALLENGE", "Challenge has expired.")
            if not payload.verified:
                return error_response(401, "VERIFICATION_FAILED", "Device verification failed.")

            eligible_device = (
                select(Device.device_id)
                .where(
                    Device.device_id == challenge.device_id,
                    Device.user_id == challenge.user_id,
                    Device.public_key == device.public_key,
                    Device.revoked_at.is_(None),
                    Device.pairing_status == "PENDING",
                )
                .exists()
            )

            consumed = db.execute(
                update(AuthChallenge)
                .where(
                    AuthChallenge.challenge_id == challenge.challenge_id,
                    AuthChallenge.consumed_at.is_(None),
                    AuthChallenge.expires_at > now,
                    eligible_device,
                )
                .values(consumed_at=now)
            )
            if consumed.rowcount != 1:
                raise VerificationConflict

            session = db.get(Session, challenge.session_id)
            promoted = db.execute(
                update(Session)
                .where(
                    Session.session_id == challenge.session_id,
                    Session.user_id == challenge.user_id,
                    Session.state == "AUTH_PENDING",
                    Session.expires_at > now,
                    Session.revoked_at.is_(None),
                )
                .values(state="TRUSTED")
            )
            if promoted.rowcount != 1 or session is None:
                raise VerificationConflict

            db.refresh(session)
            result = AuthVerifyResponse(
                session=SessionResponse.model_validate(session, from_attributes=True)
            )

    except VerificationConflict:
        return error_response(409, "VERIFICATION_CONFLICT", "Authentication state changed.")
    except SQLAlchemyError:
        return error_response(500, "INTERNAL_ERROR", "Unable to verify device response.")

    return result

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
import uuid
import base64


@dataclass(frozen=True)
class AuthenticationChallenge:
    version: int
    challenge_id: str
    request_id: str
    user_id: str
    device_id: str
    purpose: str
    nonce: str
    expires_at: str

    @classmethod
    def create(
        cls,
        request_id: str,
        user_id: str,
        device_id: str,
        purpose: str = "login",
    ):
        now = datetime.now(timezone.utc)

        nonce = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode().rstrip("=")

        return cls(
            version=1,
            challenge_id=str(uuid.uuid4()),
            request_id=request_id,
            user_id=user_id,
            device_id=device_id,
            purpose=purpose,
            nonce=nonce,
            expires_at=(
                now + timedelta(seconds=60)
            ).isoformat(),
        )

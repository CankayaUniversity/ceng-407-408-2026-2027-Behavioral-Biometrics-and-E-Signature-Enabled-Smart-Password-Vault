
from dataclasses import dataclass
import base64
import json

from .challenge import AuthenticationChallenge
from .signing import DeviceSigner

def build_signed_message(
    *, version: int, challenge_id: str, device_id: str, payload: dict
) -> bytes:
    signed_data = {
        "version": version,
        "challenge_id": challenge_id,
        "device_id": device_id,
        "payload": payload,
    }
    message = json.dumps(
        signed_data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return b"DEVICE_AUTH_V1\x00" + message

@dataclass(frozen=True)
class AuthenticationResponse:
    version: int
    challenge_id: str
    device_id: str
    payload: dict
    signature: str

    @classmethod
    def create(
        cls,
        challenge: AuthenticationChallenge,
        signer: DeviceSigner,
        verified: bool,
    ):
        payload = {
            "request_id": challenge.request_id,
            "user_id": challenge.user_id,
            "purpose": challenge.purpose,
            "nonce": challenge.nonce,
            "verified": verified,
        }

        signature = signer.sign(
            build_signed_message(
                version=challenge.version,
                challenge_id=challenge.challenge_id,
                device_id=challenge.device_id,
                payload=payload,
            )
        )

        encoded_signature = base64.urlsafe_b64encode(
            signature
        ).decode().rstrip("=")

        return cls(
            version=challenge.version,
            challenge_id=challenge.challenge_id,
            device_id=challenge.device_id,
            payload=payload,
            signature=encoded_signature,
        )

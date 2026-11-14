
import base64
import json

from packages.device_protocol.protocol.challenge import (
    AuthenticationChallenge,
)
from packages.device_protocol.protocol.response import (
    AuthenticationResponse,
)
from packages.device_protocol.protocol.signing import (
    DeviceSigner,
)


def test_unique_challenges():
    first = AuthenticationChallenge.create(
        "request_01", "user_01", "device_01"
    )
    second = AuthenticationChallenge.create(
        "request_01", "user_01", "device_01"
    )

    assert first.challenge_id != second.challenge_id
    assert first.nonce != second.nonce


def test_challenge_fields():
    challenge = AuthenticationChallenge.create(
        "request_01", "user_01", "device_01"
    )

    assert challenge.version == 1
    assert challenge.user_id == "user_01"
    assert challenge.device_id == "device_01"
    assert challenge.purpose == "login"

    nonce = base64.urlsafe_b64decode(
        challenge.nonce + "=" * (-len(challenge.nonce) % 4)
    )
    assert len(nonce) == 32


def test_signed_response():
    challenge = AuthenticationChallenge.create(
        "request_01", "user_01", "device_01"
    )
    signer = DeviceSigner()

    response = AuthenticationResponse.create(
        challenge, signer, True
    )

    signed_data = {
        "version": response.version,
        "challenge_id": response.challenge_id,
        "device_id": response.device_id,
        "payload": response.payload,
    }

    message = json.dumps(
        signed_data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    signature = base64.urlsafe_b64decode(
        response.signature + "=" * (-len(response.signature) % 4)
    )

    assert DeviceSigner.verify(
        signer.get_public_key(),
        b"DEVICE_AUTH_V1\x00" + message,
        signature,
    )

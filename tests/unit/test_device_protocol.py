
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
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from packages.device_protocol.fingerprint.models import FingerSlot
from packages.device_protocol.simulator.mock_device import MockFingerprintDevice


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

@pytest.mark.parametrize(
    ("finger_slot", "scan_success", "expected"),
    [
        (FingerSlot.RIGHT_INDEX, True, True),
        (FingerSlot.RIGHT_INDEX, False, False),
        (FingerSlot.LEFT_INDEX, True, False),
    ],
)
    
def test_device_signs_fingerprint_result(finger_slot, scan_success, expected):
    device = MockFingerprintDevice("device_01")
    device.enroll("user_01")
    device.enroll_finger("user_01", FingerSlot.RIGHT_INDEX)

    public_key = Ed25519PublicKey.from_public_bytes(device.export_public_key())
    challenge = AuthenticationChallenge.create(
        "request_01", "user_01", "device_01"
    )

    response = device.respond_to_challenge(
        challenge, finger_slot, scan_success=scan_success
    )

    assert response.version == challenge.version
    assert response.challenge_id == challenge.challenge_id
    assert response.device_id == challenge.device_id
    assert response.payload == {
        "request_id": challenge.request_id,
        "user_id": challenge.user_id,
        "purpose": challenge.purpose,
        "nonce": challenge.nonce,
        "verified": expected,
    }
    assert response.payload["verified"] is expected

    signed_data = {
        "version": response.version,
        "challenge_id": response.challenge_id,
        "device_id": response.device_id,
        "payload": response.payload,
    }
    message = json.dumps(
        signed_data, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    signature = base64.urlsafe_b64decode(
        response.signature + "=" * (-len(response.signature) % 4)
    )

    assert DeviceSigner.verify(
        public_key, b"DEVICE_AUTH_V1\x00" + message, signature
    )


def test_device_rejects_challenge_for_another_device():
    device = MockFingerprintDevice("device_01")
    challenge = AuthenticationChallenge.create(
        "request_01", "user_01", "device_02"
    )

    with pytest.raises(ValueError, match="Challenge belongs to a different device"):
        device.respond_to_challenge(
            challenge, FingerSlot.RIGHT_INDEX, scan_success=True
        )
    
    

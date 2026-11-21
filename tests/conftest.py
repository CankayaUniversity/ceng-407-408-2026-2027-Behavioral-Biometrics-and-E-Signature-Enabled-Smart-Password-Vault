import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from packages.device_protocol.fingerprint.models import FingerSlot
from packages.device_protocol.protocol.challenge import AuthenticationChallenge
from packages.device_protocol.simulator.mock_device import MockFingerprintDevice


@pytest.fixture
def signed_device_exchange():
    device = MockFingerprintDevice("device_01")
    device.enroll("user_01")
    device.enroll_finger("user_01", FingerSlot.RIGHT_INDEX)

    challenge = AuthenticationChallenge.create(
        "request_01", "user_01", device.device_id
    )
    public_key = Ed25519PublicKey.from_public_bytes(device.export_public_key())
    response = device.respond_to_challenge(
        challenge, FingerSlot.RIGHT_INDEX, scan_success=True
    )

    return challenge, response, public_key
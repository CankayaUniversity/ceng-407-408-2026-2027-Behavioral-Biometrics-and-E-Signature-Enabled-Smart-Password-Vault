
from packages.device_protocol.fingerprint.models import FingerSlot
from packages.device_protocol.fingerprint.enrollment import (
    FingerprintEnrollmentManager,
)

from packages.device_protocol.protocol.challenge import AuthenticationChallenge
from packages.device_protocol.protocol.response import AuthenticationResponse
from packages.device_protocol.protocol.signing import DeviceSigner


class MockFingerprintDevice:
    """Simulates fingerprint enrollment and scans without real hardware."""

    def __init__(self, device_id: str):
        if not device_id.strip():
            raise ValueError("Device ID cannot be empty.")

        self.device_id = device_id
        self.enrolled_users: set[str] = set()
        self.fingerprint_manager = FingerprintEnrollmentManager()
        self._signer = DeviceSigner()

    def enroll(self, user_id: str) -> bool:
        if not user_id.strip():
            raise ValueError("User ID cannot be empty.")

        self.enrolled_users.add(user_id)
        return True

    def verify(self, user_id: str, *, scan_success: bool) -> bool:
        return user_id in self.enrolled_users and scan_success

    def enroll_finger(self, user_id: str, finger_slot: FingerSlot) -> bool:
        if user_id not in self.enrolled_users:
            return False

        return self.fingerprint_manager.enroll(user_id, finger_slot)

    def verify_finger(
        self,
        user_id: str,
        finger_slot: FingerSlot,
        *,
        scan_success: bool,
    ) -> bool:
        if not scan_success:
            return False

        if user_id not in self.enrolled_users:
            return False

        return self.fingerprint_manager.is_enrolled(user_id, finger_slot)

    def export_public_key(self) -> bytes:
        return self._signer.export_public_key()


    def respond_to_challenge(
        self,
        challenge: AuthenticationChallenge,
        finger_slot: FingerSlot,
        *,
        scan_success: bool,
    ) -> AuthenticationResponse:
        if challenge.device_id != self.device_id:
            raise ValueError("Challenge belongs to a different device.")

        verified = self.verify_finger(
            challenge.user_id,
            finger_slot,
            scan_success=scan_success,
        )
        return AuthenticationResponse.create(challenge, self._signer, verified)
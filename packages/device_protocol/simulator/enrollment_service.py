from packages.device_protocol.fingerprint.models import FingerSlot
from packages.device_protocol.simulator.mock_device import MockFingerprintDevice


class FingerprintEnrollmentService:
    def __init__(self, device: MockFingerprintDevice):
        self.device = device

    def enroll_finger(self, user_id: str, finger_slot: str) -> bool:
        slot = FingerSlot(finger_slot)
        self.device.enroll(user_id)
        return self.device.enroll_finger(user_id, slot)

    def get_enrolled_fingers(self, user_id: str) -> set[FingerSlot]:
        return self.device.fingerprint_manager.get_enrolled_fingers(user_id)
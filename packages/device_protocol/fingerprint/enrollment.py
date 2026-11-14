
from .models import FingerSlot, FingerprintEnrollment


class FingerprintEnrollmentManager:
    def __init__(self):
        self.enrollments = {}

    def enroll(self, user_id: str, finger_slot: FingerSlot) -> bool:
        enrollment = FingerprintEnrollment(user_id, finger_slot)

        if user_id not in self.enrollments:
            self.enrollments[user_id] = set()

        if enrollment.finger_slot in self.enrollments[user_id]:
            return False

        self.enrollments[user_id].add(enrollment.finger_slot)
        return True

    def is_enrolled(self, user_id: str, finger_slot: FingerSlot) -> bool:
        return finger_slot in self.enrollments.get(user_id, set())

    def remove(self, user_id: str, finger_slot: FingerSlot) -> bool:
        if not self.is_enrolled(user_id, finger_slot):
            return False

        self.enrollments[user_id].remove(finger_slot)
        return True

    def get_enrolled_fingers(self, user_id: str) -> set[FingerSlot]:
        return set(self.enrollments.get(user_id, set()))


from dataclasses import dataclass
from enum import Enum


class FingerSlot(str, Enum):
    LEFT_THUMB = "left_thumb"
    LEFT_INDEX = "left_index"
    LEFT_MIDDLE = "left_middle"
    LEFT_RING = "left_ring"
    LEFT_LITTLE = "left_little"

    RIGHT_THUMB = "right_thumb"
    RIGHT_INDEX = "right_index"
    RIGHT_MIDDLE = "right_middle"
    RIGHT_RING = "right_ring"
    RIGHT_LITTLE = "right_little"


@dataclass(frozen=True)
class FingerprintEnrollment:
    user_id: str
    finger_slot: FingerSlot
    is_simulated: bool = True

    def __post_init__(self):
        if not self.user_id.strip():
            raise ValueError("User ID cannot be empty.")

        if not isinstance(self.finger_slot, FingerSlot):
            raise ValueError("Invalid finger slot.")

        if self.is_simulated is not True:
            raise ValueError("Only simulated enrollment is supported.")


@dataclass(frozen=True)
class FingerprintSequence:
    fingers: tuple[FingerSlot, FingerSlot, FingerSlot]

    def __post_init__(self):
        if len(self.fingers) != 3:
            raise ValueError("Sequence must contain exactly 3 fingers.")

        if not all(isinstance(finger, FingerSlot) for finger in self.fingers):
            raise ValueError("Invalid finger slot in sequence.")

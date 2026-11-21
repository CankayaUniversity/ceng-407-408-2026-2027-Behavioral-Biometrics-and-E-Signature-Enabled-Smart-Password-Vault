
import pytest

from packages.device_protocol.fingerprint.models import (
    FingerSlot,
    FingerprintEnrollment,
    FingerprintSequence,
)
from packages.device_protocol.fingerprint.enrollment import (
    FingerprintEnrollmentManager,
)

from packages.device_protocol.simulator.enrollment_service import (
    FingerprintEnrollmentService,
)


def test_enrollment():
    manager = FingerprintEnrollmentManager()

    assert manager.enroll("user_01", FingerSlot.RIGHT_THUMB)
    assert manager.is_enrolled("user_01", FingerSlot.RIGHT_THUMB)


def test_duplicate_enrollment():
    manager = FingerprintEnrollmentManager()

    manager.enroll("user_01", FingerSlot.RIGHT_THUMB)

    assert not manager.enroll("user_01", FingerSlot.RIGHT_THUMB)


def test_user_isolation():
    manager = FingerprintEnrollmentManager()

    manager.enroll("user_01", FingerSlot.LEFT_INDEX)

    assert not manager.is_enrolled("user_02", FingerSlot.LEFT_INDEX)


def test_remove_enrollment():
    manager = FingerprintEnrollmentManager()

    manager.enroll("user_01", FingerSlot.RIGHT_INDEX)

    assert manager.remove("user_01", FingerSlot.RIGHT_INDEX)
    assert not manager.is_enrolled("user_01", FingerSlot.RIGHT_INDEX)


def test_three_finger_sequence():
    sequence = FingerprintSequence(
        fingers=(
            FingerSlot.RIGHT_INDEX,
            FingerSlot.LEFT_THUMB,
            FingerSlot.RIGHT_MIDDLE,
        )
    )

    assert len(sequence.fingers) == 3


def test_invalid_sequence():
    with pytest.raises(ValueError):
        FingerprintSequence(
            fingers=(FingerSlot.RIGHT_INDEX,)
        )


def test_real_biometric_rejected():
    with pytest.raises(ValueError):
        FingerprintEnrollment(
            "user_01",
            FingerSlot.RIGHT_THUMB,
            is_simulated=False,
        )

from packages.device_protocol.simulator.mock_device import (
    MockFingerprintDevice,
)


def test_device_finger_enrollment():
    device = MockFingerprintDevice("device_01")

    device.enroll("user_01")

    assert device.enroll_finger(
        "user_01", FingerSlot.RIGHT_INDEX
    ) is True


def test_device_finger_verification():
    device = MockFingerprintDevice("device_01")

    device.enroll("user_01")
    device.enroll_finger("user_01", FingerSlot.RIGHT_INDEX)

    assert device.verify_finger(
        "user_01",
        FingerSlot.RIGHT_INDEX,
        scan_success=True,
    ) is True

    assert device.verify_finger(
        "user_01",
        FingerSlot.LEFT_INDEX,
        scan_success=True,
    ) is False

    assert device.verify_finger(
        "user_01",
        FingerSlot.RIGHT_INDEX,
        scan_success=False,
    ) is False


def test_unregistered_user_cannot_enroll_finger():
    device = MockFingerprintDevice("device_01")

    assert device.enroll_finger(
        "unknown_user", FingerSlot.RIGHT_INDEX
    ) is False
    
def test_service_enrolls_finger_and_rejects_duplicates():
    device = MockFingerprintDevice("device_01")
    service = FingerprintEnrollmentService(device)

    assert service.enroll_finger("user_01", "right_index") is True
    assert service.enroll_finger("user_01", "right_index") is False
    assert service.get_enrolled_fingers("user_01") == {FingerSlot.RIGHT_INDEX}
    assert device.verify_finger(
        "user_01", FingerSlot.RIGHT_INDEX, scan_success=True
    ) is True


def test_service_keeps_enrollments_separate_by_user_and_device():
    first = FingerprintEnrollmentService(MockFingerprintDevice("device_01"))
    second = FingerprintEnrollmentService(MockFingerprintDevice("device_02"))

    first.enroll_finger("user_01", "right_index")

    assert first.get_enrolled_fingers("user_02") == set()
    assert second.get_enrolled_fingers("user_01") == set()
    assert second.enroll_finger("user_01", "right_index") is True


def test_service_rejects_invalid_slot_before_registering_user():
    device = MockFingerprintDevice("device_01")
    service = FingerprintEnrollmentService(device)

    with pytest.raises(ValueError):
        service.enroll_finger("user_01", "invalid_slot")

    assert "user_01" not in device.enrolled_users
    assert service.get_enrolled_fingers("user_01") == set()

import pytest

from packages.device_protocol.simulator.mock_device import MockFingerprintDevice


def test_enroll_user():
    device = MockFingerprintDevice(device_id="test-device")

    assert device.enroll("test-user") is True


def test_enroll_same_user_again():
    device = MockFingerprintDevice(device_id="test-device")

    device.enroll("test-user")

    assert device.enroll("test-user") is True
    assert len(device.enrolled_users) == 1


@pytest.mark.parametrize("user_id", ["", "   "])
def test_reject_empty_user_id(user_id):
    device = MockFingerprintDevice(device_id="test-device")

    with pytest.raises(ValueError):
        device.enroll(user_id)


@pytest.mark.parametrize("device_id", ["", "   "])
def test_reject_empty_device_id(device_id):
    with pytest.raises(ValueError):
        MockFingerprintDevice(device_id=device_id)


@pytest.mark.parametrize(
    "enrolled, scan_success, expected",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_verify(enrolled, scan_success, expected):
    device = MockFingerprintDevice(device_id="test-device")

    if enrolled:
        device.enroll("test-user")

    result = device.verify("test-user", scan_success=scan_success)

    assert result is expected
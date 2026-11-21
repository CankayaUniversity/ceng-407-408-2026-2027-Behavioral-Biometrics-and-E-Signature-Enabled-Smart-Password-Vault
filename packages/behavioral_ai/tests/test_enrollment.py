import pytest

from packages.behavioral_ai.inference.verifier import verify_window
from packages.behavioral_ai.training.enrollment import enroll_user


def make_window(offset=0):
    return [
        {
            "dwell_ms": 100.0 + offset,
            "down_down_ms": 150.0 + offset,
            "flight_ms": 50.0 + offset,
        }
        for _ in range(100)
    ]


def test_enrollment_and_verification_work_together():
    profile = enroll_user(
        "alice",
        [make_window(-2), make_window(0), make_window(2)],
    )

    matching = verify_window(
        "alice", make_window(), profile, threshold=2.0
    )
    different = verify_window(
        "alice", make_window(50), profile, threshold=2.0
    )

    assert profile.user_id == "alice"
    assert profile.enrollment_windows == 3
    assert matching.accepted is True
    assert different.accepted is False


@pytest.mark.parametrize("window_count", [0, 1])
def test_enrollment_requires_multiple_windows(window_count):
    with pytest.raises(ValueError):
        enroll_user("alice", [make_window()] * window_count)


def test_enrollment_rejects_incomplete_window():
    with pytest.raises(ValueError):
        enroll_user("alice", [make_window(), make_window()[:99]])


def test_enrollment_rejects_invalid_measurement():
    invalid = make_window()
    invalid[10]["dwell_ms"] = float("nan")

    with pytest.raises(ValueError):
        enroll_user("alice", [make_window(), invalid])


def test_enrollment_rejects_low_coverage_window():
    invalid = make_window()

    for index in range(1, 31):
        invalid[index]["down_down_ms"] = None
        invalid[index]["flight_ms"] = None

    with pytest.raises(ValueError, match="insufficient transition coverage"):
        enroll_user("alice", [make_window(), invalid])
import math
from dataclasses import replace

import pytest

from packages.behavioral_ai.features import extract_window, feature_vector
from packages.behavioral_ai.inference.verifier import verify_window
from packages.behavioral_ai.models.profile import UserProfile


def make_samples(offset=0):
    return [
        {
            "dwell_ms": 100.0 + offset + index % 7,
            "down_down_ms": 150.0 + 2 * offset + index % 11,
            "flight_ms": 50.0 + offset + index % 5,
        }
        for index in range(100)
    ]


@pytest.fixture
def profile():
    vectors = [
        feature_vector(extract_window(make_samples(offset)))
        for offset in (-2, 0, 2)
    ]
    return UserProfile.fit("alice", vectors)


def test_matching_behavior_is_accepted(profile):
    result = verify_window(
        "alice", make_samples(), profile, threshold=2.0
    )

    assert result.accepted is True
    assert result.reason == "match"
    assert result.distance == pytest.approx(0.0)
    assert result.threshold == 2.0


def test_unseen_different_behavior_is_rejected(profile):
    # This synthetic behavior was never used during enrollment.
    result = verify_window(
        "alice", make_samples(offset=50), profile, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "behavior_mismatch"
    assert result.distance > result.threshold


def test_threshold_boundary_is_inclusive(profile):
    samples = make_samples(offset=3)
    distance = profile.distance(
        feature_vector(extract_window(samples))
    )
    assert distance > 0

    at_boundary = verify_window(
        "alice", samples, profile, threshold=distance
    )
    below_boundary = verify_window(
        "alice",
        samples,
        profile,
        threshold=math.nextafter(distance, 0.0),
    )

    assert at_boundary.accepted is True
    assert below_boundary.accepted is False


def test_missing_profile_is_rejected():
    result = verify_window(
        "alice", make_samples(), None, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "unknown_user"
    assert result.distance is None


def test_another_users_profile_cannot_verify_claim(profile):
    result = verify_window(
        "bob", make_samples(), profile, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "unknown_user"


def test_incompatible_feature_version_is_rejected(profile):
    incompatible = replace(profile, feature_version="old-version")

    result = verify_window(
        "alice", make_samples(), incompatible, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "incompatible_feature_version"


@pytest.mark.parametrize("user_id", ["", "   ", None, 123])
def test_invalid_claimed_user_is_rejected(profile, user_id):
    result = verify_window(
        user_id, make_samples(), profile, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "invalid_user_id"


@pytest.mark.parametrize("length", [0, 99, 101])
def test_incorrect_window_length_is_rejected(profile, length):
    samples = (make_samples() * 2)[:length]

    result = verify_window(
        "alice", samples, profile, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "invalid_samples"


def test_invalid_measurement_is_rejected(profile):
    samples = make_samples()
    samples[10]["dwell_ms"] = float("nan")

    result = verify_window(
        "alice", samples, profile, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "invalid_samples"


def test_insufficient_transition_coverage_is_rejected(profile):
    samples = make_samples()

    for index in range(1, 31):
        samples[index]["down_down_ms"] = None
        samples[index]["flight_ms"] = None

    result = verify_window(
        "alice", samples, profile, threshold=2.0
    )

    assert result.accepted is False
    assert result.reason == "insufficient_coverage"
    assert result.distance is None


@pytest.mark.parametrize(
    "threshold",
    [-1, True, None, "2", float("nan"), float("inf")],
)
def test_invalid_threshold_raises_error(profile, threshold):
    with pytest.raises(ValueError):
        verify_window(
            "alice", make_samples(), profile, threshold=threshold
        )
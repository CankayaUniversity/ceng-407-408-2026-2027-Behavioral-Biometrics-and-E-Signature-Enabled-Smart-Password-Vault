import math

import pytest

from dataclasses import replace
from packages.behavioral_ai.features import FEATURE_NAMES, FEATURE_VERSION
from packages.behavioral_ai.models.profile import SCALE_FLOORS, UserProfile


def make_vector():
    return [
        0.2 if name == "overlap_ratio" else 100.0
        for name in FEATURE_NAMES
    ]


def test_fit_stores_profile_metadata():
    vector = make_vector()

    profile = UserProfile.fit("alice", [vector, vector])

    assert profile.user_id == "alice"
    assert profile.feature_version == FEATURE_VERSION
    assert profile.enrollment_windows == 2
    assert profile.center == pytest.approx(vector)


def test_constant_features_use_scale_floors():
    vector = make_vector()

    profile = UserProfile.fit("alice", [vector, vector])

    assert profile.scale == pytest.approx(SCALE_FLOORS)
    assert profile.distance(vector) == pytest.approx(0.0)


def test_fit_learns_center_and_population_standard_deviation():
    vector = make_vector()
    lower = [value - 2 * floor for value, floor in zip(vector, SCALE_FLOORS)]
    upper = [value + 2 * floor for value, floor in zip(vector, SCALE_FLOORS)]

    profile = UserProfile.fit("alice", [lower, vector, upper])

    assert profile.center == pytest.approx(vector)
    assert profile.scale == pytest.approx([
        math.sqrt(8 / 3) * floor
        for floor in SCALE_FLOORS
    ])


def test_distance_uses_standardized_root_mean_square():
    vector = make_vector()
    profile = UserProfile.fit("alice", [vector, vector])

    # Every feature is exactly one scale unit from the center.
    shifted = [
        value + floor
        for value, floor in zip(vector, SCALE_FLOORS)
    ]

    assert profile.distance(shifted) == pytest.approx(1.0)

    # Only one of the 13 features is one scale unit away.
    single_shift = vector.copy()
    single_shift[0] += SCALE_FLOORS[0]

    assert profile.distance(single_shift) == pytest.approx(
        1 / math.sqrt(len(FEATURE_NAMES))
    )


@pytest.mark.parametrize("user_id", ["", "   ", None, 123])
def test_fit_rejects_invalid_user_id(user_id):
    vector = make_vector()

    with pytest.raises(ValueError):
        UserProfile.fit(user_id, [vector, vector])


@pytest.mark.parametrize("window_count", [0, 1])
def test_fit_requires_multiple_enrollment_windows(window_count):
    with pytest.raises(ValueError):
        UserProfile.fit("alice", [make_vector()] * window_count)


@pytest.mark.parametrize("length", [12, 14])
def test_fit_and_distance_reject_wrong_vector_length(length):
    vector = make_vector()
    profile = UserProfile.fit("alice", [vector, vector])
    invalid = [100.0] * length

    with pytest.raises(ValueError):
        UserProfile.fit("alice", [vector, invalid])

    with pytest.raises(ValueError):
        profile.distance(invalid)


@pytest.mark.parametrize(
    "value",
    [True, None, "100", float("nan"), float("inf"), float("-inf")],
)
def test_fit_and_distance_reject_invalid_feature_values(value):
    vector = make_vector()
    profile = UserProfile.fit("alice", [vector, vector])
    invalid = vector.copy()
    invalid[0] = value

    with pytest.raises(ValueError):
        UserProfile.fit("alice", [vector, invalid])

    with pytest.raises(ValueError):
        profile.distance(invalid)

@pytest.mark.parametrize(
    "changes",
    [
        {"center": ()},
        {"scale": ()},
        {"scale": (0.0,) * len(FEATURE_NAMES)},
        {"scale": (-1.0,) * len(FEATURE_NAMES)},
        {"center": (float("nan"),) * len(FEATURE_NAMES)},
        {"enrollment_windows": 1},
        {"enrollment_windows": True},
        {"user_id": ""},
        {"feature_version": ""},
    ],
)
def test_direct_profile_construction_rejects_invalid_fields(changes):
    vector = make_vector()
    profile = UserProfile.fit("alice", [vector, vector])

    with pytest.raises(ValueError):
        replace(profile, **changes)


def test_profile_copies_mutable_feature_arrays():
    center = make_vector()
    scale = list(SCALE_FLOORS)
    profile = UserProfile(
        user_id="alice",
        center=center,
        scale=scale,
        enrollment_windows=2,
    )

    center[0] = 999.0
    scale[0] = 999.0

    assert profile.center[0] == 100.0
    assert profile.scale[0] == SCALE_FLOORS[0]
    assert isinstance(profile.center, tuple)
    assert isinstance(profile.scale, tuple)
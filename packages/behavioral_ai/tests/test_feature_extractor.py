import json

import pytest

from packages.behavioral_ai.features import (
    FEATURE_NAMES,
    WINDOW_SIZE,
    extract_window,
    extract_windows,
    feature_vector,
)
from packages.behavioral_ai.legacy.extract_features import (
    session_rows,
    validate_session,
)


def make_samples(count=WINDOW_SIZE):
    return [
        {
            "dwell_ms": 100.0,
            "down_down_ms": 150.0,
            "flight_ms": 50.0,
        }
        for _ in range(count)
    ]


def test_constant_timings():
    features = extract_window(make_samples())

    for prefix, expected in (
        ("dwell", 100.0),
        ("down_down", 150.0),
        ("flight", 50.0),
    ):
        assert features[f"{prefix}_median_ms"] == expected
        assert features[f"{prefix}_iqr_ms"] == 0
        assert features[f"{prefix}_p10_ms"] == expected
        assert features[f"{prefix}_p90_ms"] == expected

    assert features["overlap_ratio"] == 0
    assert features["flight_count"] == 99
    assert features["flight_coverage"] == 1


def test_missing_transitions_are_excluded():
    samples = make_samples()
    samples[1]["down_down_ms"] = None
    samples[1]["flight_ms"] = None

    features = extract_window(samples)

    assert features["down_down_count"] == 98
    assert features["flight_count"] == 98
    assert features["flight_coverage"] == pytest.approx(98 / 99)
    assert features["flight_median_ms"] == 50.0


@pytest.mark.parametrize("field", ["down_down_ms", "flight_ms"])
@pytest.mark.parametrize(
    ("missing_count", "accepted"),
    [(29, True), (30, False)],
)
def test_coverage_boundary(field, missing_count, accepted):
    samples = make_samples()

    for index in range(1, missing_count + 1):
        samples[index][field] = None

    features = extract_window(samples)

    assert (features is not None) == accepted


def test_negative_flight_times():
    samples = make_samples()

    for index in range(1, 34):
        samples[index]["flight_ms"] = -20.0

    features = extract_window(samples)

    assert features["overlap_ratio"] == pytest.approx(33 / 99)


def test_first_transition_is_excluded():
    samples = make_samples()
    samples[0]["down_down_ms"] = None
    samples[0]["flight_ms"] = None

    features = extract_window(samples)

    assert features["down_down_count"] == 99
    assert features["flight_count"] == 99
    assert features["flight_coverage"] == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dwell_ms", 0),
        ("dwell_ms", 2001),
        ("dwell_ms", True),
        ("down_down_ms", -1),
        ("down_down_ms", 2001),
        ("flight_ms", float("nan")),
        ("flight_ms", float("inf")),
        ("flight_ms", "invalid"),
    ],
)
def test_invalid_measurements(field, value):
    samples = make_samples()
    samples[1][field] = value

    with pytest.raises(ValueError):
        extract_window(samples)


def test_incomplete_window_is_rejected():
    with pytest.raises(ValueError):
        extract_window(make_samples(99))


def test_batch_discards_incomplete_tail():
    results = list(extract_windows(make_samples(250)))

    assert [index for index, _ in results] == [0, 1]


def test_saved_session_and_live_windows_match():
    samples = make_samples(250)

    for index, sample in enumerate(samples):
        sample["dwell_ms"] += index % 17
        sample["down_down_ms"] += index % 11
        sample["flight_ms"] = -10.0 if index % 3 == 0 else 50.0

    session = json.loads(json.dumps({
        "schema_version": 1,
        "participant_id": "synthetic-user",
        "session_id": "synthetic-session",
        "samples": samples,
    }))

    validate_session(session)
    saved_rows = list(session_rows(session))

    live_features = [
        extract_window(samples[start:start + WINDOW_SIZE])
        for start in (0, WINDOW_SIZE)
    ]

    assert len(saved_rows) == len(live_features) == 2

    for saved, live in zip(saved_rows, live_features):
        for name, value in live.items():
            assert saved[name] == value

        assert feature_vector(saved) == feature_vector(live)


def test_feature_vector_order():
    features = extract_window(make_samples())
    reversed_features = dict(reversed(list(features.items())))

    vector = feature_vector(reversed_features)

    assert len(vector) == 13
    assert vector == [features[name] for name in FEATURE_NAMES]
    assert "flight_count" not in FEATURE_NAMES
    assert "flight_coverage" not in FEATURE_NAMES
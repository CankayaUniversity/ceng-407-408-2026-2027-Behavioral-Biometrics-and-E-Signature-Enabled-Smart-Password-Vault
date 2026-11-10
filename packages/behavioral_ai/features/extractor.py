import math
from statistics import median

from .config import (
    FEATURE_NAMES,
    MAX_DOWN_DOWN_MS,
    MAX_DWELL_MS,
    MIN_TRANSITION_COVERAGE,
    WINDOW_SIZE,
)


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_samples(samples):
    if not isinstance(samples, list):
        raise ValueError("Samples must be a list.")

    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError(f"Sample {index}: expected a dictionary.")

        dwell = sample.get("dwell_ms")

        if not is_number(dwell) or not 0 < dwell <= MAX_DWELL_MS:
            raise ValueError(f"Sample {index}: invalid dwell_ms.")

        for field in ("down_down_ms", "flight_ms"):
            if field not in sample:
                raise ValueError(f"Sample {index}: missing {field}.")

            value = sample[field]

            if value is not None and not is_number(value):
                raise ValueError(f"Sample {index}: invalid {field}.")

        down_down = sample["down_down_ms"]

        if (
            down_down is not None
            and not 0 <= down_down <= MAX_DOWN_DOWN_MS
        ):
            raise ValueError(f"Sample {index}: invalid down_down_ms.")


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def describe(values, prefix):
    return {
        f"{prefix}_median_ms": median(values),
        f"{prefix}_iqr_ms": (
            percentile(values, 0.75) - percentile(values, 0.25)
        ),
        f"{prefix}_p10_ms": percentile(values, 0.10),
        f"{prefix}_p90_ms": percentile(values, 0.90),
    }


def extract_window(samples):
    """Return features for one complete window.

    Invalid input raises ValueError.
    Insufficient transition coverage returns None.
    """
    validate_samples(samples)

    if len(samples) != WINDOW_SIZE:
        raise ValueError(
            f"A window must contain exactly {WINDOW_SIZE} samples."
        )

    dwell = [sample["dwell_ms"] for sample in samples]

    # The first transition may originate outside this window.
    transitions = samples[1:]

    down_down = [
        sample["down_down_ms"]
        for sample in transitions
        if sample["down_down_ms"] is not None
    ]
    flight = [
        sample["flight_ms"]
        for sample in transitions
        if sample["flight_ms"] is not None
    ]

    possible_transitions = len(transitions)
    down_down_coverage = len(down_down) / possible_transitions
    flight_coverage = len(flight) / possible_transitions

    if (
        down_down_coverage < MIN_TRANSITION_COVERAGE
        or flight_coverage < MIN_TRANSITION_COVERAGE
    ):
        return None

    features = {}
    features.update(describe(dwell, "dwell"))
    features.update(describe(down_down, "down_down"))
    features.update(describe(flight, "flight"))

    features["overlap_ratio"] = (
        sum(value < 0 for value in flight) / len(flight)
    )

    # Quality metadata: excluded from the model vector.
    features["down_down_count"] = len(down_down)
    features["flight_count"] = len(flight)
    features["down_down_coverage"] = down_down_coverage
    features["flight_coverage"] = flight_coverage

    return features


def extract_windows(samples):
    """Yield (window_index, features) for usable complete windows.

    Windows do not overlap. An incomplete final window is discarded.
    Call this separately for each session to preserve session boundaries.
    """
    validate_samples(samples)

    complete_length = len(samples) - len(samples) % WINDOW_SIZE

    for start in range(0, complete_length, WINDOW_SIZE):
        window = samples[start:start + WINDOW_SIZE]
        features = extract_window(window)

        if features is not None:
            yield start // WINDOW_SIZE, features


def feature_vector(features):
    """Return model inputs in a fixed, shared order."""
    return [features[name] for name in FEATURE_NAMES]
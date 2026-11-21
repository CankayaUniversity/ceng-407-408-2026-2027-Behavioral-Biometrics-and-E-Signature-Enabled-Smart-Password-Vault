"""Per-user baseline built from enrollment feature vectors."""

import math
from dataclasses import dataclass
from statistics import fmean, pstdev

from packages.behavioral_ai.features import FEATURE_NAMES, FEATURE_VERSION


# Regularization floors prevent division by zero and excessive sensitivity.
# Timing features use milliseconds; overlap_ratio is dimensionless.
SCALE_FLOORS = tuple(
    0.01 if name == "overlap_ratio" else 1.0
    for name in FEATURE_NAMES
)


def validate_vector(vector):
    """Return a finite numeric vector in the shared feature order."""
    values = tuple(vector)

    if len(values) != len(FEATURE_NAMES):
        raise ValueError(
            f"Expected {len(FEATURE_NAMES)} features."
        )

    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Features must be finite numbers.")

    return values


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    center: tuple[float, ...]
    scale: tuple[float, ...]
    enrollment_windows: int
    feature_version: str = FEATURE_VERSION

    def __post_init__(self):
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("A non-empty user ID is required.")

        center = validate_vector(self.center)
        scale = validate_vector(self.scale)

        if any(value <= 0 for value in scale):
            raise ValueError("Profile scales must be positive.")

        if (
            isinstance(self.enrollment_windows, bool)
            or not isinstance(self.enrollment_windows, int)
            or self.enrollment_windows < 2
        ):
            raise ValueError(
                "A profile requires at least two enrollment windows."
            )

        if (
            not isinstance(self.feature_version, str)
            or not self.feature_version.strip()
        ):
            raise ValueError("A non-empty feature version is required.")

        # Copy inputs into immutable tuples.
        object.__setattr__(self, "center", center)
        object.__setattr__(self, "scale", scale)

    @classmethod
    def fit(cls, user_id, vectors):
        """Build a profile using enrollment vectors only."""
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("A non-empty user ID is required.")

        rows = [validate_vector(vector) for vector in vectors]

        if len(rows) < 2:
            raise ValueError(
                "At least two enrollment windows are required."
            )

        columns = list(zip(*rows))
        center = tuple(fmean(column) for column in columns)
        scale = tuple(
            max(pstdev(column), floor)
            for column, floor in zip(columns, SCALE_FLOORS)
        )

        return cls(
            user_id=user_id,
            center=center,
            scale=scale,
            enrollment_windows=len(rows),
        )

    def distance(self, vector):
        """Return the root mean square standardized distance."""
        values = validate_vector(vector)

        deviations = [
            (value - center) / scale
            for value, center, scale in zip(
                values, self.center, self.scale
            )
        ]

        return math.hypot(*deviations) / math.sqrt(len(FEATURE_NAMES))
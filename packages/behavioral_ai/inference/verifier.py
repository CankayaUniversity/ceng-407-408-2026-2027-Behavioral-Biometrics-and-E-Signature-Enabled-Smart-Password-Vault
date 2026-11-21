"""Verify a behavior window against a claimed user's profile."""

import math
from dataclasses import dataclass

from packages.behavioral_ai.features import (
    FEATURE_VERSION,
    extract_window,
    feature_vector,
)
from packages.behavioral_ai.models.profile import UserProfile


@dataclass(frozen=True)
class VerificationResult:
    accepted: bool
    reason: str
    distance: float | None = None
    threshold: float | None = None


def verify_window(
    claimed_user_id: str,
    samples: list,
    profile: UserProfile | None,
    *,
    threshold: float,
) -> VerificationResult:
    """Verify one complete window using an explicit distance threshold."""
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
        or threshold < 0
    ):
        raise ValueError("Threshold must be a finite, non-negative number.")

    if (
        not isinstance(claimed_user_id, str)
        or not claimed_user_id.strip()
    ):
        return VerificationResult(
            accepted=False,
            reason="invalid_user_id",
        )

    if profile is None or profile.user_id != claimed_user_id:
        return VerificationResult(
            accepted=False,
            reason="unknown_user",
        )

    if profile.feature_version != FEATURE_VERSION:
        return VerificationResult(
            accepted=False,
            reason="incompatible_feature_version",
        )

    try:
        features = extract_window(samples)
    except (ValueError, TypeError):
        return VerificationResult(
            accepted=False,
            reason="invalid_samples",
        )

    if features is None:
        return VerificationResult(
            accepted=False,
            reason="insufficient_coverage",
        )

    distance = profile.distance(feature_vector(features))
    accepted = distance <= threshold

    return VerificationResult(
        accepted=accepted,
        reason="match" if accepted else "behavior_mismatch",
        distance=distance,
        threshold=threshold,
    )
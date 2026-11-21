"""Summarize window-level behavioral verification trials."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationMetrics:
    threshold: float
    genuine_trials: int
    false_rejections: int
    impostor_trials: int
    false_acceptances: int
    unknown_trials: int
    unknown_false_acceptances: int

    @property
    def false_rejection_rate(self):
        if self.genuine_trials == 0:
            return None
        return self.false_rejections / self.genuine_trials

    @property
    def false_acceptance_rate(self):
        if self.impostor_trials == 0:
            return None
        return self.false_acceptances / self.impostor_trials

    @property
    def unknown_false_acceptance_rate(self):
        if self.unknown_trials == 0:
            return None
        return self.unknown_false_acceptances / self.unknown_trials


def summarize_trials(trials, *, threshold):
    """Apply one fixed threshold and count verification errors.

    Unknown-individual trials are a subset of impostor trials.
    A distance equal to the threshold is accepted, matching AI-03.
    """
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
        or threshold < 0
    ):
        raise ValueError("Threshold must be a finite, non-negative number.")

    genuine = 0
    false_rejections = 0
    impostor = 0
    false_acceptances = 0
    unknown = 0
    unknown_false_acceptances = 0

    for trial in trials:
        if (
            isinstance(trial.distance, bool)
            or not isinstance(trial.distance, (int, float))
            or not math.isfinite(trial.distance)
            or trial.distance < 0
        ):
            raise ValueError("Trial distances must be finite and non-negative.")

        if trial.is_genuine and not trial.source_enrolled:
            raise ValueError("A genuine trial must come from an enrolled user.")

        accepted = trial.distance <= threshold

        if trial.is_genuine:
            genuine += 1
            false_rejections += int(not accepted)
        else:
            impostor += 1
            false_acceptances += int(accepted)

            if not trial.source_enrolled:
                unknown += 1
                unknown_false_acceptances += int(accepted)

    if genuine + impostor == 0:
        raise ValueError("At least one verification trial is required.")

    return VerificationMetrics(
        threshold=threshold,
        genuine_trials=genuine,
        false_rejections=false_rejections,
        impostor_trials=impostor,
        false_acceptances=false_acceptances,
        unknown_trials=unknown,
        unknown_false_acceptances=unknown_false_acceptances,
    )
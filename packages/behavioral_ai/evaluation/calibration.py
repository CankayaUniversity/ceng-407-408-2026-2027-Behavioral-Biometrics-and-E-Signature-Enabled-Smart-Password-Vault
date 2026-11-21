"""Select a verification threshold from development trials."""

from bisect import bisect_right
from dataclasses import dataclass

from packages.behavioral_ai.evaluation.metrics import (
    VerificationMetrics,
    summarize_trials,
)


@dataclass(frozen=True)
class CalibrationResult:
    threshold: float
    development_metrics: VerificationMetrics

    @property
    def balanced_error_rate(self):
        metrics = self.development_metrics
        return (
            metrics.false_acceptance_rate
            + metrics.false_rejection_rate
        ) / 2


def calibrate_threshold(development_trials):
    """Minimize the mean of development FAR and FRR.

    Both genuine and impostor trials are required. Equal-error candidates
    are resolved by choosing the lower threshold.

    Callers must supply development trials only.
    """
    trials = tuple(development_trials)

    # Validate trial values before selecting a threshold.
    initial = summarize_trials(trials, threshold=0.0)

    if initial.genuine_trials == 0 or initial.impostor_trials == 0:
        raise ValueError(
            "Calibration requires both genuine and impostor trials."
        )

    genuine = sorted(
        trial.distance for trial in trials if trial.is_genuine
    )
    impostor = sorted(
        trial.distance for trial in trials if not trial.is_genuine
    )

    # Decisions change only when the threshold reaches a trial distance.
    candidates = sorted({0.0, *genuine, *impostor})

    def selection_key(threshold):
        false_rejections = len(genuine) - bisect_right(
            genuine, threshold
        )
        false_acceptances = bisect_right(impostor, threshold)

        # Equivalent to minimizing FAR + FRR without rounding the rates.
        weighted_errors = (
            false_rejections * len(impostor)
            + false_acceptances * len(genuine)
        )

        return weighted_errors, threshold

    threshold = min(candidates, key=selection_key)

    return CalibrationResult(
        threshold=threshold,
        development_metrics=summarize_trials(
            trials,
            threshold=threshold,
        ),
    )
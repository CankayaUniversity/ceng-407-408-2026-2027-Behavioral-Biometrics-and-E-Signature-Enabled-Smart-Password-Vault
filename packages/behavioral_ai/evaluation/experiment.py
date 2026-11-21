"""Run session-separated training, calibration, and evaluation."""

from dataclasses import dataclass

from packages.behavioral_ai.features import FEATURE_VERSION
from packages.behavioral_ai.evaluation.calibration import (
    CalibrationResult,
    calibrate_threshold,
)
from packages.behavioral_ai.evaluation.metrics import (
    VerificationMetrics,
    summarize_trials,
)
from packages.behavioral_ai.evaluation.scoring import (
    VerificationTrial,
    score_sessions,
)
from packages.behavioral_ai.training.profiles import train_profiles
from packages.behavioral_ai.training.splits import (
    SessionSplit,
    split_sessions,
)


@dataclass(frozen=True)
class ExperimentResult:
    feature_version: str
    split: SessionSplit
    enrolled_user_ids: tuple[str, ...]
    calibration: CalibrationResult
    test_metrics: VerificationMetrics
    development_trials: tuple[VerificationTrial, ...]
    test_trials: tuple[VerificationTrial, ...]


def run_experiment(sessions, split):
    """Fit on training sessions and calibrate on development sessions.

    Evaluate test sessions once using the selected threshold. Both
    development and test evaluation require genuine and impostor trials.
    """
    validated_split = split_sessions(
        sessions,
        train_ids=split.train_ids,
        development_ids=split.development_ids,
        test_ids=split.test_ids,
    )

    profiles = train_profiles(sessions, validated_split)

    development_trials = score_sessions(
        sessions,
        validated_split.development_ids,
        profiles,
    )
    calibration = calibrate_threshold(development_trials)

    test_trials = score_sessions(
        sessions,
        validated_split.test_ids,
        profiles,
    )
    test_metrics = summarize_trials(
        test_trials,
        threshold=calibration.threshold,
    )

    if (
        test_metrics.genuine_trials == 0
        or test_metrics.impostor_trials == 0
    ):
        raise ValueError(
            "Test evaluation requires both genuine and impostor trials."
        )

    return ExperimentResult(
        feature_version=FEATURE_VERSION,
        split=validated_split,
        enrolled_user_ids=tuple(sorted(profiles)),
        calibration=calibration,
        test_metrics=test_metrics,
        development_trials=development_trials,
        test_trials=test_trials,
    )
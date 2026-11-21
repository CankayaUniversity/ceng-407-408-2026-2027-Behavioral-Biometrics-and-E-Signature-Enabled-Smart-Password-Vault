"""Build JSON-compatible experiment reports."""

import hashlib
import json
from dataclasses import asdict

from packages.behavioral_ai.features import FEATURE_NAMES
from packages.behavioral_ai.models.profile import SCALE_FLOORS


def metrics_dict(metrics):
    """Include calculated rates alongside their underlying counts."""
    return {
        **asdict(metrics),
        "false_rejection_rate": metrics.false_rejection_rate,
        "false_acceptance_rate": metrics.false_acceptance_rate,
        "unknown_false_acceptance_rate": (
            metrics.unknown_false_acceptance_rate
        ),
    }


def session_digest(session):
    """Hash canonical JSON content without including it in the report."""
    content = json.dumps(
        session,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(content).hexdigest()


def build_report(result, sessions):
    """Return a deterministic report for the supplied experiment."""
    split = result.split
    session_ids = sorted(
        (*split.train_ids, *split.development_ids, *split.test_ids)
    )

    return {
        "report_version": 1,
        "feature_version": result.feature_version,
        "model": {
            "name": "standardized-rms-baseline-v1",
            "feature_names": list(FEATURE_NAMES),
            "scale_floors": list(SCALE_FLOORS),
        },
        "protocol": {
            "trial_unit": "window-profile comparison",
            "comparison_rule": "each window against every enrolled profile",
            "acceptance_rule": "distance <= threshold",
            "calibration_objective": "minimum mean development FAR and FRR",
            "threshold_tie_break": "lower threshold",
            "unknown_definition": "source user absent from training profiles",
        },
        "enrolled_user_ids": list(result.enrolled_user_ids),
        "split": asdict(split),
        "session_content_sha256": {
            session_id: session_digest(sessions[session_id])
            for session_id in session_ids
        },
        "calibration": {
            "threshold": result.calibration.threshold,
            "balanced_error_rate": result.calibration.balanced_error_rate,
            "development_metrics": metrics_dict(
                result.calibration.development_metrics
            ),
        },
        "test_metrics": metrics_dict(result.test_metrics),
        "development_trials": [
            asdict(trial) for trial in result.development_trials
        ],
        "test_trials": [
            asdict(trial) for trial in result.test_trials
        ],
    }
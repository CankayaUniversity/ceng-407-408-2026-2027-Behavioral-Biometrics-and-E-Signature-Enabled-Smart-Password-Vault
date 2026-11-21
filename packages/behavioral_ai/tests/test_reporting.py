import json
from copy import deepcopy

import pytest

from packages.behavioral_ai.evaluation.experiment import run_experiment
from packages.behavioral_ai.evaluation.metrics import summarize_trials
from packages.behavioral_ai.evaluation.reporting import (
    build_report,
    metrics_dict,
    session_digest,
)
from packages.behavioral_ai.training.splits import split_sessions


def make_session(session_id, participant_id, offset=0, count=100):
    return {
        "schema_version": 1,
        "session_id": session_id,
        "participant_id": participant_id,
        "samples": [
            {
                "dwell_ms": 100.0 + offset,
                "down_down_ms": 150.0 + offset,
                "flight_ms": 50.0 + offset,
            }
            for _ in range(count)
        ],
    }


@pytest.fixture
def experiment():
    sessions = {
        "train": make_session("train", "alice", count=200),
        "dev-g": make_session("dev-g", "alice"),
        "dev-u": make_session("dev-u", "charlie", offset=40),
        "test-g": make_session("test-g", "alice"),
        "test-u": make_session("test-u", "dana", offset=80),
    }
    split = split_sessions(
        sessions,
        train_ids=["train"],
        development_ids=["dev-g", "dev-u"],
        test_ids=["test-g", "test-u"],
    )

    return sessions, run_experiment(sessions, split)


def test_report_can_be_serialized_as_strict_json(experiment):
    sessions, result = experiment

    report = build_report(result, sessions)
    decoded = json.loads(json.dumps(report, allow_nan=False))

    assert decoded["report_version"] == 1
    assert decoded["enrolled_user_ids"] == ["alice"]
    assert decoded["split"] == {
        "train_ids": ["train"],
        "development_ids": ["dev-g", "dev-u"],
        "test_ids": ["test-g", "test-u"],
    }


def test_report_contains_metrics_counts_and_rates(experiment):
    sessions, result = experiment
    report = build_report(result, sessions)

    metrics = report["test_metrics"]
    assert metrics["genuine_trials"] == 1
    assert metrics["impostor_trials"] == 1
    assert metrics["unknown_trials"] == 1
    assert metrics["false_rejection_rate"] == 0.0
    assert metrics["false_acceptance_rate"] == 0.0
    assert metrics["unknown_false_acceptance_rate"] == 0.0
    assert metrics["threshold"] == report["calibration"]["threshold"]


def test_report_preserves_trial_provenance(experiment):
    sessions, result = experiment
    report = build_report(result, sessions)

    assert {
        trial["session_id"] for trial in report["development_trials"]
    } == {"dev-g", "dev-u"}
    assert {
        trial["session_id"] for trial in report["test_trials"]
    } == {"test-g", "test-u"}
    assert set(report["session_content_sha256"]) == set(sessions)


def test_report_is_reproducible(experiment):
    sessions, result = experiment

    first = build_report(result, sessions)
    second = build_report(
        result,
        dict(reversed(list(sessions.items()))),
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(
        second, sort_keys=True
    )


def test_report_excludes_raw_samples_and_profile_centers(experiment):
    sessions, result = experiment
    encoded = json.dumps(build_report(result, sessions))

    assert '"samples"' not in encoded
    assert '"center"' not in encoded


def test_digest_is_independent_of_dictionary_key_order():
    session = make_session("a", "alice")
    reordered = dict(reversed(list(session.items())))

    assert session_digest(session) == session_digest(reordered)


def test_digest_changes_when_recording_content_changes():
    original = make_session("a", "alice")
    changed = deepcopy(original)
    changed["samples"][0]["dwell_ms"] += 1

    assert session_digest(original) != session_digest(changed)


def test_undefined_rate_is_serialized_as_null(experiment):
    _, result = experiment
    unknown_trial = next(
        trial for trial in result.test_trials
        if not trial.source_enrolled
    )
    metrics = summarize_trials(
        [unknown_trial],
        threshold=result.calibration.threshold,
    )

    decoded = json.loads(json.dumps(metrics_dict(metrics)))

    assert decoded["false_rejection_rate"] is None
    assert decoded["unknown_false_acceptance_rate"] == 0.0
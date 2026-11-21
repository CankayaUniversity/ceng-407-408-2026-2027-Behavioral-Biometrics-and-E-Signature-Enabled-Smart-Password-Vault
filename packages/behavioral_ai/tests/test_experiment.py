from copy import deepcopy
from dataclasses import replace

import pytest

from packages.behavioral_ai.features import FEATURE_VERSION
from packages.behavioral_ai.evaluation.experiment import run_experiment
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
def sessions():
    return {
        "train": make_session("train", "alice", count=200),
        "dev-genuine": make_session("dev-genuine", "alice", offset=1),
        "dev-unknown": make_session("dev-unknown", "charlie", offset=40),
        "test-genuine": make_session("test-genuine", "alice", offset=1),
        "test-unknown": make_session("test-unknown", "dana", offset=80),
    }


def make_split(sessions):
    return split_sessions(
        sessions,
        train_ids=["train"],
        development_ids=["dev-genuine", "dev-unknown"],
        test_ids=["test-genuine", "test-unknown"],
    )


def test_runs_complete_session_separated_experiment(sessions):
    result = run_experiment(sessions, make_split(sessions))

    assert result.feature_version == FEATURE_VERSION
    assert result.enrolled_user_ids == ("alice",)
    assert len(result.development_trials) == 2
    assert len(result.test_trials) == 2

    assert result.calibration.balanced_error_rate == 0.0
    assert result.test_metrics.false_rejection_rate == 0.0
    assert result.test_metrics.false_acceptance_rate == 0.0
    assert result.test_metrics.unknown_trials == 1
    assert result.test_metrics.unknown_false_acceptance_rate == 0.0
    assert result.test_metrics.threshold == result.calibration.threshold


def test_test_data_cannot_change_selected_threshold(sessions):
    split = make_split(sessions)
    original = run_experiment(sessions, split)

    changed = deepcopy(sessions)
    changed["test-genuine"] = make_session(
        "test-genuine", "alice", offset=100
    )
    changed["test-unknown"] = make_session(
        "test-unknown", "dana", offset=0
    )

    modified = run_experiment(changed, split)

    assert modified.calibration == original.calibration
    assert modified.development_trials == original.development_trials
    assert modified.test_metrics.false_rejection_rate == 1.0
    assert modified.test_metrics.unknown_false_acceptance_rate == 1.0
    assert modified.test_metrics != original.test_metrics


def test_trials_belong_only_to_their_assigned_sessions(sessions):
    result = run_experiment(sessions, make_split(sessions))

    assert {
        trial.session_id for trial in result.development_trials
    } == {"dev-genuine", "dev-unknown"}

    assert {
        trial.session_id for trial in result.test_trials
    } == {"test-genuine", "test-unknown"}


def test_experiment_is_reproducible(sessions):
    split = make_split(sessions)
    reversed_sessions = dict(reversed(list(sessions.items())))
    reversed_split = replace(
        split,
        development_ids=tuple(reversed(split.development_ids)),
        test_ids=tuple(reversed(split.test_ids)),
    )

    assert run_experiment(sessions, split) == run_experiment(
        reversed_sessions, reversed_split
    )


def test_experiment_does_not_modify_recordings(sessions):
    original = deepcopy(sessions)

    run_experiment(sessions, make_split(sessions))

    assert sessions == original


def test_rejects_overlapping_session_groups(sessions):
    split = make_split(sessions)
    invalid = replace(split, train_ids=("train", "test-genuine"))

    with pytest.raises(ValueError, match="must not overlap"):
        run_experiment(sessions, invalid)


@pytest.mark.parametrize(
    ("session_id", "participant_id"),
    [
        ("test-genuine", "dana"),
        ("test-unknown", "alice"),
    ],
)
def test_requires_genuine_and_impostor_test_trials(
    sessions, session_id, participant_id
):
    sessions[session_id]["participant_id"] = participant_id

    with pytest.raises(ValueError, match="both genuine and impostor"):
        run_experiment(sessions, make_split(sessions))


def test_requires_impostor_development_trials(sessions):
    sessions["dev-unknown"]["participant_id"] = "alice"

    with pytest.raises(ValueError, match="both genuine and impostor"):
        run_experiment(sessions, make_split(sessions))


def test_rejects_test_session_without_usable_windows(sessions):
    sessions["test-genuine"]["samples"] = []

    with pytest.raises(ValueError, match="no usable windows"):
        run_experiment(sessions, make_split(sessions))
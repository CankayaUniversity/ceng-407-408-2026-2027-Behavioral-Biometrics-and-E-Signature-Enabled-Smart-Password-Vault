from dataclasses import replace

import pytest

from packages.behavioral_ai.evaluation.scoring import score_sessions
from packages.behavioral_ai.inference.verifier import verify_window
from packages.behavioral_ai.training.enrollment import enroll_user


def make_samples(offset=0, count=100):
    return [
        {
            "dwell_ms": 100.0 + offset,
            "down_down_ms": 150.0 + offset,
            "flight_ms": 50.0 + offset,
        }
        for _ in range(count)
    ]


def make_session(session_id, participant_id, offset=0, count=100):
    return {
        "schema_version": 1,
        "session_id": session_id,
        "participant_id": participant_id,
        "samples": make_samples(offset, count),
    }


@pytest.fixture
def profiles():
    return {
        user_id: enroll_user(
            user_id,
            [make_samples(offset - 2), make_samples(offset + 2)],
        )
        for user_id, offset in [("alice", 0), ("bob", 40)]
    }


def test_labels_genuine_and_enrolled_impostor_trials(profiles):
    sessions = {"a": make_session("a", "alice")}

    trials = score_sessions(sessions, ["a"], profiles)

    assert len(trials) == 2
    genuine, impostor = trials

    assert genuine.claimed_user_id == "alice"
    assert genuine.source_user_id == "alice"
    assert genuine.is_genuine is True
    assert genuine.source_enrolled is True
    assert genuine.distance == pytest.approx(0.0)

    assert impostor.claimed_user_id == "bob"
    assert impostor.source_user_id == "alice"
    assert impostor.is_genuine is False
    assert impostor.source_enrolled is True
    assert impostor.distance > genuine.distance


def test_unknown_individual_produces_only_impostor_trials(profiles):
    sessions = {"u": make_session("u", "charlie", offset=80)}

    trials = score_sessions(sessions, ["u"], profiles)

    assert len(trials) == 2
    assert all(not trial.is_genuine for trial in trials)
    assert all(not trial.source_enrolled for trial in trials)
    assert {trial.claimed_user_id for trial in trials} == {"alice", "bob"}


def test_distance_matches_ai03_verification(profiles):
    session = make_session("a", "alice", offset=3)

    trials = score_sessions({"a": session}, ["a"], profiles)

    for trial in trials:
        result = verify_window(
            trial.claimed_user_id,
            session["samples"],
            profiles[trial.claimed_user_id],
            threshold=2.0,
        )
        assert trial.distance == pytest.approx(result.distance)


def test_preserves_session_boundaries_and_window_indices(profiles):
    sessions = {
        "a": make_session("a", "alice", count=250),
        "b": make_session("b", "bob", offset=40, count=150),
    }

    trials = score_sessions(sessions, ["b", "a"], profiles)

    assert len(trials) == 6
    assert [
        (trial.session_id, trial.window_index, trial.claimed_user_id)
        for trial in trials
    ] == [
        ("a", 0, "alice"),
        ("a", 0, "bob"),
        ("a", 1, "alice"),
        ("a", 1, "bob"),
        ("b", 0, "alice"),
        ("b", 0, "bob"),
    ]


def test_order_is_reproducible(profiles):
    sessions = {
        "a": make_session("a", "alice"),
        "b": make_session("b", "bob", offset=40),
    }

    first = score_sessions(sessions, ["a", "b"], profiles)
    second = score_sessions(
        dict(reversed(list(sessions.items()))),
        ["b", "a"],
        dict(reversed(list(profiles.items()))),
    )

    assert first == second


def test_rejects_missing_profiles():
    with pytest.raises(ValueError, match="At least one enrolled profile"):
        score_sessions({}, ["a"], {})


def test_rejects_unknown_session_id(profiles):
    with pytest.raises(ValueError, match="Unknown evaluation session"):
        score_sessions({}, ["missing"], profiles)


@pytest.mark.parametrize("count", [0, 99])
def test_rejects_session_without_complete_window(profiles, count):
    sessions = {"a": make_session("a", "alice", count=count)}

    with pytest.raises(ValueError, match="no usable windows"):
        score_sessions(sessions, ["a"], profiles)


def test_rejects_session_without_sufficient_coverage(profiles):
    session = make_session("a", "alice")

    for sample in session["samples"]:
        sample["down_down_ms"] = None
        sample["flight_ms"] = None

    with pytest.raises(ValueError, match="no usable windows"):
        score_sessions({"a": session}, ["a"], profiles)


def test_rejects_mismatched_session_key(profiles):
    session = make_session("different-id", "alice")

    with pytest.raises(ValueError, match="lookup key"):
        score_sessions({"a": session}, ["a"], profiles)


def test_rejects_mismatched_profile_key(profiles):
    sessions = {"a": make_session("a", "alice")}

    with pytest.raises(ValueError, match="lookup key"):
        score_sessions(
            sessions,
            ["a"],
            {"wrong-user": profiles["alice"]},
        )


def test_rejects_incompatible_feature_version(profiles):
    sessions = {"a": make_session("a", "alice")}
    incompatible = replace(
        profiles["alice"],
        feature_version="old-version",
    )

    with pytest.raises(ValueError, match="Incompatible profile"):
        score_sessions(sessions, ["a"], {"alice": incompatible})
from copy import deepcopy

import pytest

from packages.behavioral_ai.training.profiles import train_profiles
from packages.behavioral_ai.training.splits import SessionSplit, split_sessions


def make_session(session_id, participant_id="alice", count=200, offset=0):
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
        "train": make_session("train"),
        "dev": make_session("dev", count=100),
        "test": make_session("test", participant_id="bob", count=100),
    }


def make_split(sessions, train_ids=None):
    return split_sessions(
        sessions,
        train_ids=["train"] if train_ids is None else train_ids,
        development_ids=["dev"],
        test_ids=["test"],
    )


def test_trains_profile_from_training_windows(sessions):
    profiles = train_profiles(sessions, make_split(sessions))

    assert list(profiles) == ["alice"]
    assert profiles["alice"].enrollment_windows == 2
    assert profiles["alice"].center[0] == pytest.approx(100.0)


def test_development_and_test_changes_do_not_affect_training(sessions):
    split = make_split(sessions)
    original = train_profiles(sessions, split)

    changed = deepcopy(sessions)
    changed["dev"] = make_session(
        "dev", participant_id="charlie", offset=500
    )
    changed["test"] = make_session(
        "test", participant_id="dana", offset=700
    )

    assert train_profiles(changed, split) == original


def test_does_not_enroll_users_seen_only_outside_training(sessions):
    sessions["dev"]["participant_id"] = "charlie"

    profiles = train_profiles(sessions, make_split(sessions))

    assert set(profiles) == {"alice"}
    assert "bob" not in profiles
    assert "charlie" not in profiles


def test_trains_separate_profiles_for_multiple_users(sessions):
    sessions["train-bob"] = make_session(
        "train-bob", participant_id="bob", offset=50
    )
    split = make_split(sessions, ["train-bob", "train"])

    profiles = train_profiles(sessions, split)

    assert list(profiles) == ["alice", "bob"]
    assert profiles["alice"].center[0] == pytest.approx(100.0)
    assert profiles["bob"].center[0] == pytest.approx(150.0)


def test_does_not_merge_incomplete_tails_between_sessions(sessions):
    sessions["train"] = make_session("train", count=150)
    sessions["train-2"] = make_session("train-2", count=150)
    split = make_split(sessions, ["train", "train-2"])

    profiles = train_profiles(sessions, split)

    # Each session contributes one complete window, not three in total.
    assert profiles["alice"].enrollment_windows == 2


def test_short_sessions_cannot_be_joined_into_training_windows(sessions):
    sessions["train"] = make_session("train", count=50)
    sessions["train-2"] = make_session("train-2", count=150)
    split = make_split(sessions, ["train", "train-2"])

    with pytest.raises(ValueError, match="At least two"):
        train_profiles(sessions, split)


def test_rejects_training_user_without_usable_windows(sessions):
    for sample in sessions["train"]["samples"]:
        sample["down_down_ms"] = None
        sample["flight_ms"] = None

    with pytest.raises(ValueError, match="Could not train profile for alice"):
        train_profiles(sessions, make_split(sessions))


def test_rejects_mismatched_session_lookup_key(sessions):
    sessions["train"]["session_id"] = "different-id"

    with pytest.raises(ValueError, match="lookup key"):
        train_profiles(sessions, make_split(sessions))


def test_rejects_invalid_training_measurement(sessions):
    sessions["train"]["samples"][0]["dwell_ms"] = float("nan")

    with pytest.raises(ValueError):
        train_profiles(sessions, make_split(sessions))


def test_revalidates_manually_constructed_split(sessions):
    invalid_split = SessionSplit(
        train_ids=("train",),
        development_ids=("train", "dev"),
        test_ids=("test",),
    )

    with pytest.raises(ValueError, match="must not overlap"):
        train_profiles(sessions, invalid_split)
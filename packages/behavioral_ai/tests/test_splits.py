import pytest

from packages.behavioral_ai.training.splits import split_sessions


@pytest.fixture
def sessions():
    # Only session IDs are needed to validate partition membership.
    return {
        session_id: {}
        for session_id in ("train-1", "train-2", "dev-1", "test-1")
    }


def test_creates_sorted_reproducible_split(sessions):
    first = split_sessions(
        sessions,
        train_ids=["train-2", "train-1"],
        development_ids=["dev-1"],
        test_ids=["test-1"],
    )
    second = split_sessions(
        dict(reversed(list(sessions.items()))),
        train_ids=["train-1", "train-2"],
        development_ids=["dev-1"],
        test_ids=["test-1"],
    )

    assert first == second
    assert first.train_ids == ("train-1", "train-2")
    assert first.development_ids == ("dev-1",)
    assert first.test_ids == ("test-1",)


@pytest.mark.parametrize(
    ("train", "development", "test"),
    [
        (["shared"], ["shared"], ["other"]),
        (["shared"], ["other"], ["shared"]),
        (["other"], ["shared"], ["shared"]),
    ],
)
def test_rejects_overlap_between_any_groups(train, development, test):
    with pytest.raises(ValueError, match="must not overlap"):
        split_sessions(
            {"shared": {}, "other": {}},
            train_ids=train,
            development_ids=development,
            test_ids=test,
        )


def test_rejects_unknown_session_id(sessions):
    with pytest.raises(ValueError, match="Unknown session IDs"):
        split_sessions(
            sessions,
            train_ids=["train-1", "train-2"],
            development_ids=["dev-1"],
            test_ids=["missing"],
        )


def test_rejects_unassigned_session(sessions):
    with pytest.raises(ValueError, match="Unassigned session IDs"):
        split_sessions(
            sessions,
            train_ids=["train-1"],
            development_ids=["dev-1"],
            test_ids=["test-1"],
        )


@pytest.mark.parametrize("group", ["train_ids", "development_ids", "test_ids"])
@pytest.mark.parametrize(
    ("invalid", "message"),
    [
        ([], "at least one session"),
        (["train-1", "train-1"], "duplicate session IDs"),
        ([""], "invalid session ID"),
        (["   "], "invalid session ID"),
        ([123], "invalid session ID"),
        ("train-1", "collection of session IDs"),
    ],
)
def test_rejects_invalid_group_values(sessions, group, invalid, message):
    arguments = {
        "train_ids": ["train-1", "train-2"],
        "development_ids": ["dev-1"],
        "test_ids": ["test-1"],
    }
    arguments[group] = invalid

    with pytest.raises(ValueError, match=message):
        split_sessions(sessions, **arguments)
"""Explicit, reproducible partitions of recording sessions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionSplit:
    train_ids: tuple[str, ...]
    development_ids: tuple[str, ...]
    test_ids: tuple[str, ...]


def validate_ids(values, group_name):
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{group_name} must be a collection of session IDs.")

    ids = tuple(values)

    if not ids:
        raise ValueError(f"{group_name} must contain at least one session.")

    if any(
        not isinstance(value, str) or not value.strip()
        for value in ids
    ):
        raise ValueError(f"{group_name} contains an invalid session ID.")

    if len(ids) != len(set(ids)):
        raise ValueError(f"{group_name} contains duplicate session IDs.")

    return tuple(sorted(ids))


def split_sessions(
    sessions,
    *,
    train_ids,
    development_ids,
    test_ids,
):
    """Validate an explicit partition of all loaded sessions.

    Each session must appear exactly once. IDs are sorted so that input
    ordering does not change the resulting partition.
    """
    train = validate_ids(train_ids, "Training")
    development = validate_ids(development_ids, "Development")
    test = validate_ids(test_ids, "Test")

    groups = [set(train), set(development), set(test)]

    if (
        groups[0] & groups[1]
        or groups[0] & groups[2]
        or groups[1] & groups[2]
    ):
        raise ValueError("Session groups must not overlap.")

    selected = set().union(*groups)
    available = set(sessions)

    unknown = selected - available
    if unknown:
        raise ValueError(f"Unknown session IDs: {sorted(unknown)}")

    unassigned = available - selected
    if unassigned:
        raise ValueError(f"Unassigned session IDs: {sorted(unassigned)}")

    return SessionSplit(
        train_ids=train,
        development_ids=development,
        test_ids=test,
    )
"""Load and validate behavioral recording sessions."""

import json
from pathlib import Path

from packages.behavioral_ai.legacy.extract_features import validate_session


def load_sessions(directory):
    """Load JSON sessions indexed by their unique session IDs.

    Files are processed in a stable order. Invalid recordings and duplicate
    session IDs cause loading to fail instead of being silently skipped.
    """
    directory = Path(directory)

    if not directory.is_dir():
        raise ValueError(f"Session directory does not exist: {directory}")

    paths = sorted(directory.glob("*.json"))

    if not paths:
        raise ValueError(f"No JSON session files found: {directory}")

    sessions = {}

    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            validate_session(data)
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            raise ValueError(
                f"Could not load session file {path.name}: {error}"
            ) from error

        session_id = data["session_id"]

        if session_id in sessions:
            raise ValueError(f"Duplicate session ID: {session_id}")

        sessions[session_id] = data

    return sessions
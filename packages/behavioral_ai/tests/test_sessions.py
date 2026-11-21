import json

import pytest

from packages.behavioral_ai.training.sessions import load_sessions


def make_session(session_id="session-1", participant_id="alice"):
    return {
        "schema_version": 1,
        "session_id": session_id,
        "participant_id": participant_id,
        "samples": [
            {
                "dwell_ms": 100.0,
                "down_down_ms": 150.0,
                "flight_ms": 50.0,
            }
            for _ in range(100)
        ],
    }


def write_session(directory, filename, session):
    path = directory / filename
    path.write_text(json.dumps(session), encoding="utf-8")
    return path


def test_loads_sessions_in_filename_order(tmp_path):
    second = make_session("session-2", "bob")
    first = make_session("session-1", "alice")
    write_session(tmp_path, "b.json", second)
    write_session(tmp_path, "a.json", first)

    sessions = load_sessions(tmp_path)

    assert list(sessions) == ["session-1", "session-2"]
    assert sessions["session-1"] == first
    assert sessions["session-2"] == second


def test_rejects_missing_directory(tmp_path):
    with pytest.raises(ValueError, match="directory does not exist"):
        load_sessions(tmp_path / "missing")


def test_rejects_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="No JSON session files"):
        load_sessions(tmp_path)


def test_rejects_duplicate_session_ids(tmp_path):
    write_session(tmp_path, "a.json", make_session())
    write_session(tmp_path, "b.json", make_session())

    with pytest.raises(ValueError, match="Duplicate session ID"):
        load_sessions(tmp_path)


def test_rejects_invalid_json(tmp_path):
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="broken.json"):
        load_sessions(tmp_path)


def test_rejects_invalid_encoding(tmp_path):
    (tmp_path / "broken.json").write_bytes(b"\xff")

    with pytest.raises(ValueError, match="broken.json"):
        load_sessions(tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 999),
        ("session_id", ""),
        ("participant_id", ""),
        ("samples", None),
    ],
)
def test_rejects_invalid_session_fields(tmp_path, field, value):
    session = make_session()
    session[field] = value
    write_session(tmp_path, "invalid.json", session)

    with pytest.raises(ValueError, match="invalid.json"):
        load_sessions(tmp_path)


def test_rejects_invalid_timing_measurement(tmp_path):
    session = make_session()
    session["samples"][0]["dwell_ms"] = -1
    write_session(tmp_path, "invalid.json", session)

    with pytest.raises(ValueError, match="invalid.json"):
        load_sessions(tmp_path)


def test_ignores_non_json_files(tmp_path):
    write_session(tmp_path, "valid.json", make_session())
    (tmp_path / "notes.txt").write_text("Local notes", encoding="utf-8")

    sessions = load_sessions(tmp_path)

    assert list(sessions) == ["session-1"]
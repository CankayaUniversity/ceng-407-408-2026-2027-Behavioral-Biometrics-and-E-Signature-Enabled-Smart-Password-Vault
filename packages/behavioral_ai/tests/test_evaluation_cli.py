import json
import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def inputs(tmp_path):
    directory = tmp_path / "sessions"
    directory.mkdir()

    recordings = [
        ("train", "alice", 0, 200),
        ("dev-g", "alice", 0, 100),
        ("dev-u", "charlie", 40, 100),
        ("test-g", "alice", 0, 100),
        ("test-u", "dana", 80, 100),
    ]

    for session_id, participant_id, offset, count in recordings:
        session = {
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
        (directory / f"{session_id}.json").write_text(
            json.dumps(session), encoding="utf-8"
        )

    split = tmp_path / "split.json"
    split.write_text(
        json.dumps({
            "train_ids": ["train"],
            "development_ids": ["dev-g", "dev-u"],
            "test_ids": ["test-g", "test-u"],
        }),
        encoding="utf-8",
    )

    output = tmp_path / "reports" / "report.json"
    return directory, split, output


def run_cli(directory, split, output):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "packages.behavioral_ai.evaluation",
            "--sessions", str(directory),
            "--split", str(split),
            "--output", str(output),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_cli_creates_report_without_changing_recordings(inputs):
    directory, split, output = inputs
    original = {
        path.name: path.read_bytes()
        for path in directory.glob("*.json")
    }

    completed = run_cli(directory, split, output)

    assert completed.returncode == 0, completed.stderr
    assert "Report saved:" in completed.stdout

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["enrolled_user_ids"] == ["alice"]
    assert report["test_metrics"]["false_rejection_rate"] == 0.0
    assert report["test_metrics"]["unknown_false_acceptance_rate"] == 0.0

    assert {
        path.name: path.read_bytes()
        for path in directory.glob("*.json")
    } == original


def test_cli_produces_identical_reports_for_same_inputs(inputs):
    directory, split, output = inputs
    second_output = output.with_name("second.json")

    first = run_cli(directory, split, output)
    second = run_cli(directory, split, second_output)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert output.read_bytes() == second_output.read_bytes()


def test_cli_does_not_overwrite_existing_report(inputs):
    directory, split, output = inputs
    output.parent.mkdir()
    output.write_text("existing report", encoding="utf-8")

    completed = run_cli(directory, split, output)

    assert completed.returncode == 2
    assert output.read_text(encoding="utf-8") == "existing report"


def test_cli_rejects_overlapping_groups(inputs):
    directory, split, output = inputs
    manifest = json.loads(split.read_text(encoding="utf-8"))
    manifest["train_ids"].append("test-g")
    split.write_text(json.dumps(manifest), encoding="utf-8")

    completed = run_cli(directory, split, output)

    assert completed.returncode == 2
    assert "must not overlap" in completed.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "manifest",
    [
        {},
        {"train_ids": ["train"]},
        {
            "train_ids": ["train"],
            "development_ids": ["dev-g", "dev-u"],
            "test_ids": ["test-g", "test-u"],
            "unexpected": [],
        },
    ],
)
def test_cli_rejects_invalid_manifest_fields(inputs, manifest):
    directory, split, output = inputs
    split.write_text(json.dumps(manifest), encoding="utf-8")

    completed = run_cli(directory, split, output)

    assert completed.returncode == 2
    assert "must contain exactly" in completed.stderr
    assert not output.exists()


def test_cli_rejects_missing_session_directory(inputs):
    directory, split, output = inputs

    completed = run_cli(directory / "missing", split, output)

    assert completed.returncode == 2
    assert "directory does not exist" in completed.stderr
    assert not output.exists()


def test_cli_keeps_report_outside_session_input_directory(inputs):
    directory, split, _ = inputs
    output = directory / "report.json"

    completed = run_cli(directory, split, output)

    assert completed.returncode == 2
    assert "outside the session input directory" in completed.stderr
    assert not output.exists()


def test_cli_rejects_test_recording_without_usable_windows(inputs):
    directory, split, output = inputs
    path = directory / "test-g.json"
    session = json.loads(path.read_text(encoding="utf-8"))
    session["samples"] = session["samples"][:99]
    path.write_text(json.dumps(session), encoding="utf-8")

    completed = run_cli(directory, split, output)

    assert completed.returncode == 2
    assert "no usable windows" in completed.stderr
    assert not output.exists()
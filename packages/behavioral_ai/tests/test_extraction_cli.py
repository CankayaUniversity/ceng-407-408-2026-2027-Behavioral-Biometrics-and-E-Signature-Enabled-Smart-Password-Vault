import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from packages.behavioral_ai.legacy import extract_features as extraction


ROOT = Path(__file__).resolve().parents[3]


def test_documented_module_command(tmp_path):
    # Stage only source files: never read or overwrite private session data.
    package = tmp_path / 'packages' / 'behavioral_ai'
    (package / 'legacy').mkdir(parents=True)
    for folder in (tmp_path / 'packages', package, package / 'legacy'):
        (folder / '__init__.py').touch()
    shutil.copytree(
        ROOT / 'packages/behavioral_ai/features', package / 'features',
        ignore=shutil.ignore_patterns('__pycache__'),
    )
    shutil.copy2(extraction.__file__, package / 'legacy/extract_features.py')
    environment = dict(os.environ, PYTHONPATH=str(tmp_path))
    result = subprocess.run(
        [sys.executable, '-m', 'packages.behavioral_ai.legacy.extract_features'],
        cwd=tmp_path, env=environment, capture_output=True, text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert 'No session files found:' in result.stdout


@pytest.fixture
def extraction_output(tmp_path, monkeypatch):
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    session = {
        'schema_version': 1, 'session_id': 'synthetic-session',
        'participant_id': 'synthetic-user',
        'samples': [
            {'dwell_ms': 100, 'down_down_ms': 150, 'flight_ms': 50}
            for _ in range(100)
        ],
    }
    (sessions / 'session.json').write_text(json.dumps(session), encoding='utf-8')
    output = tmp_path / 'features.csv'
    output.write_bytes(b'previous output\n')
    monkeypatch.setattr(extraction, 'SESSIONS_DIR', sessions)
    monkeypatch.setattr(extraction, 'OUTPUT_FILE', output)
    return output


def test_complete_csv_replaces_previous_output(extraction_output):
    extraction.main()
    with extraction_output.open(newline='', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]['participant_id'] == 'synthetic-user'
    assert rows[0]['dwell_median_ms'] == '100.0'
    assert not list(extraction_output.parent.glob('.*.tmp'))


@pytest.mark.parametrize('failure', ['write', 'replace'])
def test_failed_csv_update_preserves_previous_output(
    extraction_output, monkeypatch, failure,
):
    def fail(*args, **kwargs):
        raise OSError('simulated disk failure')

    if failure == 'write':
        monkeypatch.setattr(extraction.csv.DictWriter, 'writerows', fail)
    else:
        monkeypatch.setattr(extraction.os, 'replace', fail)
    extraction.main()
    assert extraction_output.read_bytes() == b'previous output\n'
    assert not list(extraction_output.parent.glob('.*.tmp'))

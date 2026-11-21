# Behavioral AI

Keystroke timing collection, shared feature extraction, and behavioral
user verification for the Smart Password Vault project.

## Current Scope

- Collect and save keystroke timing sessions.
- Extract features using the shared AI-02 pipeline.
- Create user profiles from enrollment windows.
- Verify behavior against a claimed user's profile.
- Support rejection of behavior that does not match the claimed user.
- Train and evaluate using separate recording sessions.
- Calibrate the verification threshold on development sessions.
- Export evaluation metrics and trial results as a JSON report.

Profile persistence and backend integration are not included yet.

## Setup

Requires Python 3.11 or later. Run from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r packages/behavioral_ai/requirements.txt
.venv/bin/python -m pip install pytest
```

## Collect a Session

```bash
.venv/bin/python packages/behavioral_ai/legacy/main.py
```

Enter a participant alias, start measurement, and type in the application's
text area. Save the session after collecting at least 100 valid samples.

Sessions are stored under `packages/behavioral_ai/legacy/data/sessions/`.
Records contain timing measurements and session metadata, not typed text
or key identities.

## Extract Features

```bash
.venv/bin/python -m packages.behavioral_ai.legacy.extract_features
```

Output: `packages/behavioral_ai/legacy/data/features.csv`.

Extraction processes sessions separately using non-overlapping windows
of 100 samples. Incomplete windows are discarded, and windows with
insufficient transition coverage are skipped.

Enrollment and verification reuse the same feature extraction pipeline.

## Enrollment and Verification

The main entry points are:

```python
from packages.behavioral_ai.training.enrollment import enroll_user
from packages.behavioral_ai.inference.verifier import verify_window
```

`enroll_user(user_id, windows)` creates a profile from at least two valid
enrollment windows. Each window must contain exactly 100 timing samples
belonging to the same user.

`verify_window(claimed_user_id, samples, profile, threshold=...)` compares
a new window against the claimed user's profile and returns an acceptance
decision, reason, and distance when a comparison is performed.

The caller must supply the appropriate user profile and an explicit
threshold. The evaluation workflow below selects a threshold using
development sessions and applies it to separate test sessions.

## Session-Based Training and Evaluation

Create a local split file assigning every input session to exactly one
group. Use session IDs from the recordings, not filenames:

```json
{
  "train_ids": ["alice-training"],
  "development_ids": ["alice-development", "charlie-development"],
  "test_ids": ["alice-test", "dana-test"]
}
```

Replace these example IDs with your actual session IDs.

Training requires at least two usable windows per enrolled user.
Development and test groups must each produce genuine and impostor trials.
To measure unknown-individual rejection, include participants who are
absent from training.

Run from the repository root:

```bash
.venv/bin/python -m packages.behavioral_ai.evaluation \
  --sessions packages/behavioral_ai/legacy/data/sessions \
  --split packages/behavioral_ai/legacy/data/split.json \
  --output packages/behavioral_ai/legacy/data/reports/evaluation.json
```

Training sessions build user profiles. Development sessions select the
threshold. Test sessions are evaluated using that fixed threshold.

The report includes session assignments, input content hashes, the selected
threshold, trial results, and false acceptance and false rejection rates.
Unknown-individual false acceptance is reported separately when available.

Rates cover usable windows only. Incomplete windows and low-coverage windows
are excluded; evaluation sessions without usable windows cause an error.

Existing reports are not overwritten. Keep split files outside the session
input directory and store reports locally.

## Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest packages/behavioral_ai/tests -q
```

Tests cover collection, feature extraction, enrollment, verification,
session separation, calibration, reporting, and the evaluation command.
Synthetic tests validate implementation behavior; they do not establish
real-world biometric accuracy.

## Data Handling

Do not commit participant recordings, generated feature tables, user
profiles, evaluation reports, or virtual environments. Use synthetic data in tests.

## Package Structure

- `legacy/`: collection application and saved-session extraction.
- `features/`: shared feature extraction.
- `models/`: behavioral user profiles.
- `training/`: session loading, partitioning, and profile training.
- `inference/`: user verification.
- `evaluation/`: scoring, metrics, calibration, reporting, and command-line evaluation.
- `tests/`: behavioral AI tests.
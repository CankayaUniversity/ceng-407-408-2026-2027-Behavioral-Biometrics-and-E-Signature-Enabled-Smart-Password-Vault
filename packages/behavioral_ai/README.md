# Behavioral AI

Keystroke timing collection, shared feature extraction, and behavioral
user verification for the Smart Password Vault project.

## Current Scope

- Collect and save keystroke timing sessions.
- Extract features using the shared AI-02 pipeline.
- Create user profiles from enrollment windows.
- Verify behavior against a claimed user's profile.
- Support rejection of behavior that does not match the claimed user.

Session-based training and evaluation will be implemented in AI-04.
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
threshold. Threshold calibration and real-world performance evaluation
belong to AI-04.

## Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest packages/behavioral_ai/tests -q
```

Tests cover collection, feature extraction, enrollment, profile validation,
and verification. Synthetic tests validate implementation behavior;
they do not establish real-world biometric accuracy.

## Data Handling

Do not commit participant recordings, generated feature tables, user
profiles, or virtual environments. Use synthetic data in tests.

## Package Structure

- `legacy/`: collection application and saved-session extraction.
- `features/`: shared feature extraction.
- `models/`: behavioral user profiles.
- `training/`: enrollment.
- `inference/`: user verification.
- `evaluation/`: placeholder for AI-04.
- `tests/`: behavioral AI tests.
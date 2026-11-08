# Behavioral AI Prototype

This package contains the existing keystroke collection and feature
extraction prototype.

## Current Scope

- Collect keystroke timing inside the application's text area.
- Save session timing samples as local JSON files.
- Extract features from non-overlapping windows of 100 samples.

Mouse collection, model training, and user verification are not
implemented in this prototype.

## Setup

Run these commands from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r packages/behavioral_ai/requirements.txt
```

## Collect a Session

```bash
.venv/bin/python packages/behavioral_ai/legacy/main.py
```

Enter a participant alias, start measurement, and type in the text area.
Save the session after collecting at least 100 valid samples.

Sessions are saved under `legacy/data/sessions/`, relative to this package.
The saved records contain timing measurements and session metadata,
not the typed text or key identities.

## Extract Features

```bash
.venv/bin/python packages/behavioral_ai/legacy/extract_features.py
```

Output: `legacy/data/features.csv`.

Incomplete windows are discarded. Windows with insufficient transition
coverage are skipped. A successful extraction replaces the existing CSV;
the source JSON files remain unchanged.

## Data Handling

Session recordings and generated feature tables are local data and must
not be committed. Virtual environments must also remain outside Git.

## Migration Notes

The original scripts remain together under `legacy/` to preserve their
relative data paths. Shared feature pipeline refactoring belongs to AI-02.
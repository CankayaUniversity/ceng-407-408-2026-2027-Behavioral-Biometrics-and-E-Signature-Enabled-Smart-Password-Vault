import csv
import json
from pathlib import Path

from packages.behavioral_ai.features import (
    FEATURE_VERSION,
    WINDOW_SIZE,
    extract_windows,
    validate_samples,
)


ROOT = Path(__file__).resolve().parent
SESSIONS_DIR = ROOT / "data" / "sessions"
OUTPUT_FILE = ROOT / "data" / "features.csv"


def validate_session(data):
    if not isinstance(data, dict):
        raise ValueError("Session must be a dictionary.")

    if data.get("schema_version") != 1:
        raise ValueError("Unsupported session schema version.")

    for field in ("session_id", "participant_id"):
        value = data.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or invalid field: {field}")

    validate_samples(data.get("samples"))


def session_rows(data):
    for window_index, features in extract_windows(data["samples"]):
        row = {
            "feature_version": FEATURE_VERSION,
            "participant_id": data["participant_id"],
            "session_id": data["session_id"],
            "window_index": window_index,
            "sample_count": WINDOW_SIZE,
        }

        row.update(features)
        yield row


def main():
    paths = sorted(SESSIONS_DIR.glob("*.json"))

    if not paths:
        print(f"No session files found: {SESSIONS_DIR}")
        return

    rows = []
    seen_sessions = set()

    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            validate_session(data)

            session_id = data["session_id"]

            if session_id in seen_sessions:
                print(f"Duplicate session skipped: {path.name}")
                continue

            seen_sessions.add(session_id)

            extracted = list(session_rows(data))
            rows.extend(extracted)

            print(
                f"{data['participant_id']} | "
                f"{path.name} | "
                f"{len(data['samples'])} samples -> "
                f"{len(extracted)} usable windows"
            )

        except (OSError, ValueError, TypeError) as error:
            print(f"Could not process {path.name}: {error}")
            print("CSV was not updated.")
            return

    if not rows:
        print(
            "No usable windows were generated. "
            f"At least {WINDOW_SIZE} samples and sufficient "
            "transition coverage are required."
        )
        print("CSV was not updated.")
        return

    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with OUTPUT_FILE.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys()),
            )

            writer.writeheader()
            writer.writerows(rows)

    except OSError as error:
        print(f"Could not save CSV: {error}")
        return

    print(f"Total windows: {len(rows)}")
    print(f"Feature table: {OUTPUT_FILE.resolve()}")
    print("Source JSON files were not modified.")


if __name__ == "__main__":
    main()
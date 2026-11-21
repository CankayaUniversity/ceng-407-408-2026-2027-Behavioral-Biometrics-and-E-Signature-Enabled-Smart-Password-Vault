"""Command-line entry point for session-based evaluation."""

import argparse
import json
from pathlib import Path

from packages.behavioral_ai.evaluation.experiment import run_experiment
from packages.behavioral_ai.evaluation.reporting import build_report
from packages.behavioral_ai.training.sessions import load_sessions
from packages.behavioral_ai.training.splits import split_sessions


def load_split(path, sessions):
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))

    required = {"train_ids", "development_ids", "test_ids"}

    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError(
            "Split file must contain exactly train_ids, "
            "development_ids, and test_ids."
        )

    return split_sessions(sessions, **manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Train and evaluate using separate recording sessions."
    )
    parser.add_argument(
        "--sessions",
        required=True,
        type=Path,
        help="Directory containing session JSON files.",
    )
    parser.add_argument(
        "--split",
        required=True,
        type=Path,
        help="JSON file assigning sessions to training, development, and test.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New JSON report path. Existing files are not overwritten.",
    )
    args = parser.parse_args(argv)

    try:
        if args.output.parent.resolve() == args.sessions.resolve():
            raise ValueError(
                "Store the report outside the session input directory."
            )

        sessions = load_sessions(args.sessions)
        split = load_split(args.split, sessions)
        result = run_experiment(sessions, split)
        report = build_report(result, sessions)

        serialized = json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)

        with args.output.open("x", encoding="utf-8") as file:
            file.write(serialized + "\n")

    except (OSError, UnicodeError, ValueError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")

    print(f"Report saved: {args.output}")
    print(f"Selected threshold: {result.calibration.threshold:.6g}")
    print(f"Test FRR: {result.test_metrics.false_rejection_rate}")
    print(f"Test FAR: {result.test_metrics.false_acceptance_rate}")
    print(
        "Test unknown FAR: "
        f"{result.test_metrics.unknown_false_acceptance_rate}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
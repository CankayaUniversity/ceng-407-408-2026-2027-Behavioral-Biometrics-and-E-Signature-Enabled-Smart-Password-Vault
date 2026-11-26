"""Inspect local KeyRecs and replay a session-disjoint user through AI-05."""

import argparse
import json
import tempfile

from packages.behavioral_ai.datasets.keyrecs import load_free_text
from packages.behavioral_ai.features import WINDOW_SIZE, extract_windows
from packages.behavioral_ai.realtime.service import MonitoringService, ProfileStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("free_text_csv")
    parser.add_argument("--participant", default="p001")
    args = parser.parse_args()
    sessions, rejected = load_free_text(args.free_text_csv)
    selected = sorted((s for s in sessions.values() if s["participant_id"] == args.participant), key=lambda s: s["session_id"])
    usable = {s["session_id"]: len(list(extract_windows(s["samples"]))) for s in sessions.values()}
    report = {"source": "keyrecs-free", "participants": len({s["participant_id"] for s in sessions.values()}),
              "sessions": len(sessions), "rejected_rows": rejected,
              "usable_windows": sum(usable.values()), "playback": []}
    if len(selected) < 2:
        report["blocker"] = "Two distinct enrollment recordings required."
        print(json.dumps(report, allow_nan=False))
        return
    if len(selected) < 3:
        report["genuine_holdout_blocker"] = "Only two enrollment recordings; no recording split into fake sessions."
        others = sorted((s for s in sessions.values() if s["participant_id"] != args.participant), key=lambda s: s["session_id"])
        if not others:
            raise ValueError("No disjoint impostor recording")
        selected = selected[:2] + others[:1]
        report["playback_kind"] = "impostor-only"
    else:
        report["playback_kind"] = "genuine-holdout"
    # Temporary local profiles are deleted on exit. No raw or derived data output.
    with tempfile.TemporaryDirectory() as directory:
        service = MonitoringService(ProfileStore(directory), threshold=3.0)
        service.bind(args.participant, "keyrecs-free")
        for index, session in enumerate(selected[:3]):
            service.start(session["session_id"], "enroll" if index < 2 else "verify", consent=True)
            samples = session["samples"]
            results = []
            for start in range(0, len(samples) - WINDOW_SIZE + 1, WINDOW_SIZE):
                result = service.ingest(samples[start:start + WINDOW_SIZE])
                results.append(result)
                if (index < 2 and result["status"] == "enrollment_recorded") or (index == 2 and len(results) >= 3):
                    break
            service.pause()
            if index == 1:
                report["enrollment"] = service.finish_enrollment()
            if index == 2:
                report["playback"] = results
    print(json.dumps(report, allow_nan=False))


if __name__ == "__main__":
    main()

"""KeyRecs free-text digraph adapter (seconds -> milliseconds).

Each row describes key1 -> key2. The CURRENT dwell is key2's dwell,
DU(key1,key2)-DD(key1,key2). DD and UD belong to the incoming transition.
Never pair key1 dwell with its outgoing DD/UD as if it were a live sample.
Negative DD (modifier ordering) and pauses break transitions; no invented times.
"""

import csv
import math
from pathlib import Path

from packages.behavioral_ai.features.config import MAX_DWELL_MS, MAX_DOWN_DOWN_MS


REQUIRED = {"participant", "session", "key1", "key2", "DU.key1.key1",
            "DD.key1.key2", "DU.key1.key2", "UD.key1.key2"}


def load_free_text(path):
    sessions = {}
    previous = {}
    rejected = 0
    with Path(path).open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not REQUIRED <= set(reader.fieldnames or []):
            raise ValueError("Not a KeyRecs free-text schema")
        for row in reader:
            participant, recording = row["participant"].strip(), row["session"].strip()
            if not participant or not recording:
                raise ValueError("Missing source session identity")
            sid = f"keyrecs-free:{participant}:{recording}"
            session = sessions.setdefault(sid, {"schema_version": 1, "participant_id": participant,
                                                "session_id": sid, "samples": []})
            try:
                dd = float(row["DD.key1.key2"]) * 1000
                du = float(row["DU.key1.key2"]) * 1000
                hold = float(row["DU.key1.key1"]) * 1000
                flight = float(row["UD.key1.key2"]) * 1000
                dwell = du - dd
                if not all(math.isfinite(x) for x in (dd, du, hold, flight, dwell)) or not 0 < dwell <= MAX_DWELL_MS:
                    raise ValueError()
                # Check documented DU = DD + current dwell and UD = DD - previous dwell.
                linked = previous.get(sid) == row["key1"] and 0 <= dd <= MAX_DOWN_DOWN_MS and abs(flight - (dd - hold)) <= 3
                session["samples"].append({"dwell_ms": dwell,
                                           "down_down_ms": dd if linked else None,
                                           "flight_ms": flight if linked else None})
                previous[sid] = row["key2"]
            except (ValueError, TypeError):
                rejected += 1
                previous.pop(sid, None)
    return sessions, rejected

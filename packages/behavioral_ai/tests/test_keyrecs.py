import pytest
from packages.behavioral_ai.datasets.keyrecs import load_free_text

HEADER = "participant,session,key1,key2,DU.key1.key1,DD.key1.key2,DU.key1.key2,UD.key1.key2\n"


def test_incoming_transition_dwell_units_and_session_boundaries(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text(HEADER + "p1,1,a,b,0.08,0.15,0.24,0.07\n"
                    "p1,1,b,c,0.09,0.16,0.27,0.07\n"
                    "p1,2,c,d,0.11,0.17,0.29,0.06\n")
    sessions, rejected = load_free_text(path)
    assert rejected == 0
    first, second = sessions.values()
    assert first["samples"][0]["dwell_ms"] == pytest.approx(90)
    assert first["samples"][0]["down_down_ms"] is None
    assert first["samples"][1] == {"dwell_ms": 110, "down_down_ms": 160, "flight_ms": 70}
    assert second["samples"][0]["down_down_ms"] is None
    assert all(set(s) == {"dwell_ms", "down_down_ms", "flight_ms"} for x in sessions.values() for s in x["samples"])


def test_invalid_rows_modifier_order_and_pauses_break_transitions(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text(HEADER + "p1,1,a,b,0.08,0.15,0.24,0.07\n"
                    "p1,1,b,c,0.09,nan,0.27,0.07\n"
                    "p1,1,c,d,0.11,0.17,0.29,0.06\n"
                    "p1,1,d,e,0.12,-0.1,0.02,-0.22\n"
                    "p1,1,e,f,0.12,4,4.1,3.88\n")
    sessions, rejected = load_free_text(path)
    assert rejected == 1
    samples = next(iter(sessions.values()))["samples"]
    assert all(s["down_down_ms"] is None for s in samples)


def test_wrong_schema_refused(tmp_path):
    path = tmp_path / "fixed.csv"
    path.write_text("participant,session,repetition\np1,1,1\n")
    with pytest.raises(ValueError, match="schema"):
        load_free_text(path)

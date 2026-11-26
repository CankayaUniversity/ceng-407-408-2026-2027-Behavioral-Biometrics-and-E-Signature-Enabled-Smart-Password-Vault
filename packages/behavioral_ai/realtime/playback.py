"""Deterministic synthetic timings, not measured identity evidence."""


def synthetic_window(session, *, impostor=False):
    offset = 80 if impostor else 0
    return [{"dwell_ms": 90 + (i * 7 + session) % 17 + offset,
             "down_down_ms": None if i == 0 else 160 + (i * 3 + session) % 23 + offset,
             "flight_ms": None if i == 0 else 65 + (i * 5 + session) % 19}
            for i in range(100)]

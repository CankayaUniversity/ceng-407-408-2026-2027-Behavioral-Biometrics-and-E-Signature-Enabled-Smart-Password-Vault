WINDOW_SIZE = 100
MIN_TRANSITION_COVERAGE = 0.70

MAX_DWELL_MS = 2000
MAX_DOWN_DOWN_MS = 2000

FEATURE_VERSION = "timing-summary-v2"

FEATURE_NAMES = (
    "dwell_median_ms",
    "dwell_iqr_ms",
    "dwell_p10_ms",
    "dwell_p90_ms",
    "down_down_median_ms",
    "down_down_iqr_ms",
    "down_down_p10_ms",
    "down_down_p90_ms",
    "flight_median_ms",
    "flight_iqr_ms",
    "flight_p10_ms",
    "flight_p90_ms",
    "overlap_ratio",
)
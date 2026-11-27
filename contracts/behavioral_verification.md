# Local behavioral observation contract — v1

This is local worker output, not an authorization or backend risk-event API.
It reuses AI-03 distance semantics and does not implement Sprint 4 risk policy.

Successful runtime replies contain:

| Field | Meaning |
|---|---|
| `schema_version` | `1` |
| `feature_version` | `timing-summary-v2` |
| `model_version` | `standardized-rms-v1` |
| `score_semantics` | `lower_distance_is_closer_uncalibrated` |
| `window_size` | `100` |
| `source` | `synthetic-playback`, `keyrecs-free`, `scoped-input`, or null without context |
| `status` | Lifecycle/quality outcome; `verified` means inference ran, including mismatches |
| `model_ready` | Whether a profile is loaded; never authentication state |
| `buffered_samples` | Count only, 0–99 between completed windows |
| `enrollment_windows`, `enrollment_sessions` | Pending enrollment counts, reset after save |
| `quality` | Null or down-down/flight coverage in [0,1] and counts in [0,99] |
| `verification` | Null without inference; otherwise AI-03 `accepted`, `reason`, `distance`, `threshold` |

A finite nonnegative distance is lower for behavior closer to the claimed user's
profile. Thresholds must be explicit. The UI/CLI use 3.0 for demonstration only;
no confidence percentage, calibrated risk score or security guarantee is implied.
`verification.accepted` never grants access. Quality/version/user mismatches,
missing profiles, insufficient data and invalid input do not yield acceptance.
`verification` can contain a failed AI-03 precondition with null distance/threshold.

The transport also returns status-only replies for busy, unavailable, timeout,
cancelled, pause and stop. These replies have **no verification payload** and
must clear any previous score from display. The UI clears the prior result on
request and ignores replies from a cancelled generation.

Lifecycle statuses include `consent_required`, `permission_denied`, `no_context`,
`model_not_ready`, `profile_unavailable`, `insufficient_data`,
`insufficient_coverage`, `invalid_samples`, `invalid_features`, `invalid_score`,
`enrollment_session_reuse`, `enrollment_limit`, `insufficient_enrollment`,
`enrollment_recorded`, `ready`, `verified`, `paused`, `stopped`, `deleted`.
Worker/transport errors expose fixed codes and no exception text.

The renderer sees no user/session IDs, raw events, key codes, typed text, feature
vectors, profile path, secrets or traceback. Public dataset identity/provenance
stays within the local adapter/runtime. An eventual authenticated integration
must attach trusted session context outside the renderer and review a separate
risk-event contract before sending any observations to a backend.

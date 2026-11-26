# AI-05 — local behavioral verification integration

Implementation date: 2026-11-26. Branch: `feature/AI-05-realtime-verification`.
Base: `767c2b4331bd091082b185dbd7f2865a85e1fe0d` from fetched `origin/main`.
The Desktop repository was clean before its main branch was fast-forwarded.
No pre-existing work was stashed, reset or overwritten. No push or merge of this
feature branch has been performed.

## Scope and evidence

Read the November 24 revision of `AGILE_SPRINT_PLAN(1).md` attached to the
referenced chat (local preview file) and `/Users/dogukanogan/Downloads/PROJECT_BLUEPRINT.md`
(v0.1, November 8). These documents are outside the repository; they were not
copied over repository files or marked complete.

AI-02 supplies the `timing-summary-v2` extractor: 100 samples, nonoverlapping
windows, at least 70% transition coverage, 13 model features, 2,000 ms dwell/DD
limits. AI-03 supplies `UserProfile` and `verify_window`, which compare against
the claimed user's profile using RMS standardized distance. AI-04 supplies
session-aware training, grouped splits, calibration and evaluation. Those
components and their existing evaluation protocol remain in place.

The existing private Electron enrollment worker handles device enrollment.
It does not implement APP-03 sign-in. Backend session authorization is present
on main, but the desktop controller still navigates preview pages without a
trusted authenticated session. AI-05 therefore provides an explicitly labeled
**deterministic synthetic playback** UI and a separate local public-data CLI.
It does not claim live account monitoring or completion of APP-03 integration.
No global keyboard hooks, OS permissions or actual typed input are used here.

## Runtime and lifecycle

`MonitoringService` binds a claimed user and source namespace, requires explicit
consent on each start and accepts only `dwell_ms`, `down_down_ms`, `flight_ms`.
Other fields (including keys or text), NaN/infinity, invalid samples and oversized
batches are rejected. A bounded buffer holds at most one 100-sample window.
Starting another recording, pausing or stopping clears the incomplete window.
Session boundaries are not joined. Windows run through the shared extractor and
existing claimed-user verifier; no classifier or second feature definition was added.

Enrollment keeps only feature vectors in memory, at most 32 windows from 16
sessions. It requires at least two distinct recording sessions. Finishing fits a
profile and clears the enrollment vectors. Verification rejects every enrollment
session ID. Source/feature mismatches and missing/corrupt profiles stay not ready.
IDs are provenance, not proof of identity: a future live adapter must receive its
claimed user and session from trusted APP-03 state, never renderer-supplied IDs.

The UI's fixed synthetic user is isolated in Electron's
`app.getPath("userData")/behavioral-demo-profiles`. The worker never receives a
renderer-selected filesystem path, user ID, threshold, timing array or model.
Its threshold of **3.0 is an explicit uncalibrated demo value**, not risk policy.
The public-data CLI uses a temporary directory that is removed on exit.
For programmatic use, allocate a separate store directory for each source.

Profiles are JSON summaries (center, scale, model/feature versions, enrollment window
count and recording provenance). Atomic writes use private temporary files;
on POSIX these are mode 0600 and new directories are mode 0700. They are not
encrypted at rest. No raw timing samples, typed text, passwords or key labels
are persisted by the new runtime. Profiles are still biometric derivatives and
must remain local. Python memory clearing drops references; it does not promise
secure erasure or deletion of OS backups. Unknown pickle/joblib models are not loaded.

Pause, stop/logout, consent withdrawal, page exit, reload and window closure stop
the worker. Incomplete enrollment is discarded; a finished saved profile survives
until deletion. Deletion cancels pending work, awaits the old process closing,
removes the selected profile and any interrupted atomic writes, and clears
in-memory enrollment. Other users' profiles are preserved. Generation checks
prevent late replies replacing current UI state. The bridge allows one request
at a time and has a five-second timeout. Worker stderr/exception strings are not
forwarded. Python work runs in a child process, outside the renderer and main
process event loops.

## Output and authority

See [the local result contract](../contracts/behavioral_verification.md).
Outputs expose versions, source, readiness, sample/window counts, transition
coverage and an optional distance comparison. Lower distance means closer to the
profile; it is not a probability. Insufficient input never emits an acceptance.
Scores are finite and raw samples, feature vectors and identities are excluded.
An AI `accepted` observation never creates a trusted session or unlocks a vault.
There is no backend risk-event call, risk aggregation, automatic lock, reauth or
Sprint 4 policy in this change.

## Running the demonstration

From `apps/desktop/ui/app-ui-kit`:

```sh
npm run build --workspace=web
npm run desktop:start
```

Open **Security Status**, consent, record synthetic session 1 then session 2,
then replay a genuine or impostor window (synthetic session 3). Pause discards
unfinished enrollment. Stop/logout withdraws consent. Delete removes the saved
demo profile even after a restart. Browser preview reports the desktop bridge
unavailable rather than fabricating successful model results.

For local KeyRecs inspection and bounded real-data playback, from repository root:

```sh
.venv/bin/python -m packages.behavioral_ai.datasets /Users/dogukanogan/Desktop/dataset/free-text.csv
```

The CLI inventories all free-text sessions, enrolls `p001` using the first usable
window in each of its two source sessions, and plays at most three windows from
`p002` against that claimed profile. The report explicitly labels this
**impostor-only**; two sessions leave no separate genuine holdout after the
chosen two-session enrollment requirement. No artificial session split or
accuracy claim is made. This is a plumbing demonstration, not an evaluation
protocol or calibrated benchmark. Use AI-04 for formal grouped experiments.

## Dataset inventory and compatibility

Local root: `/Users/dogukanogan/Desktop/dataset`. None of these source files or
profiles are tracked. The ignore rules also cover local dataset/profile folders
and pickle/joblib artifacts. Supply external paths instead of copying raw data
into source directories.

| Source | Local evidence | Compatibility / disposition |
|---|---|---|
| KeyRecs free-text | 562,583 CSV rows; 99 participants; 198 participant/session pairs; sessions 1 and 2 for every participant | P0 adapter and runtime playback implemented. Digraph timings are seconds. Discard key labels after checking continuity. |
| KeyRecs fixed-text | 19,772 rows; 99 participants; two sessions each; repetition field; duplicate column names for repeated keys | Inventoried only. Wide password-retype features are not concatenated or silently mixed with free-text. Needs positional parsing and repetition boundaries in a future adapter. |
| Aalto | 168,595 local text files, 18,854,241,824 bytes; sampled file has 784 key rows across 15 `TEST_SECTION_ID` values | P1, no adapter yet. Tab-separated participant/test-section IDs, press/release milliseconds and raw sentence/input/key columns. Derive hold/DD/flight after sorting presses and pair by source IDs. Test sections are transcription trials, not evidence of separate collection days. Full corpus was not parsed or trained. |
| CMU Free vs Transcribed | 20 subjects; 80 subject/session pairs in each timing table; 158,513 hold rows and 158,433 DD rows; session map has 80 records | P1, no adapter yet. Whitespace tables: subject, sessionIndex, screenIndex, index, key(s), seconds. Hold and DD must be joined with audited adjacent-key indices inside a screen; flight can only be derived as DD minus the preceding hold after validating the join. The session map labels free/transcribed tasks. No invented flight or blind row zip. |

KeyRecs free-text rows describe key1 → key2. The adapter constructs the current
key2 sample as `dwell = DU(key1,key2) - DD(key1,key2)`, incoming
`down_down = DD(key1,key2)`, incoming `flight = UD(key1,key2)`, multiplied by
1,000. Using key1 dwell with outgoing transitions would violate live parity.
Continuity requires adjacent key labels, valid DD bounds and consistency of
`UD ≈ DD - key1_dwell` within 3 ms for rounded source values. Unusable dwell rows
are dropped and transition continuity reset. Negative DD (modifier ordering),
long pauses or broken continuity keep a valid dwell but null the transition.
Session starts always have null transitions. No crossing of participant/session
boundaries or mixing with other sources occurs.

Observed free-text preprocessing: **8,297 rejected rows; 5,432 usable windows**
under the shared extractor. Default playback enrolled two source sessions and
produced three finite `behavior_mismatch` observations on the other participant.
These observations do not establish FAR, FRR or generalization.

### Provenance and use terms checked on 2026-11-26

- [KeyRecs, Zenodo 7886743](https://zenodo.org/records/7886743): CC BY 4.0;
  cite Dias et al., *KeyRecs: A keystroke dynamics and typing pattern recognition
  dataset*, DOI [10.1016/j.dib.2023.109509](https://doi.org/10.1016/j.dib.2023.109509).
  Local MD5 values match the published files:
  free-text `a5ca6fcb0970cfdcd8eb958b3fe9f22a`, fixed-text
  `f3c2ef3a42625f4df7183ea36d4543db`. The landing page describes a 100-person
  study; these two timing files contain 99 unique participant IDs.
- [Aalto 136M](https://userinterfaces.aalto.fi/136Mkeystrokes/): publisher permits
  research and noncommercial use with attribution. Cite Dhakal et al., CHI 2018,
  DOI [10.1145/3173574.3174220](https://doi.org/10.1145/3173574.3174220).
  No local readme/license was present beside the extracted files; retain/check
  the original archive terms before any redistribution or broader use.
- [CMU LASER 2012 supplement](https://www.cs.cmu.edu/~keystroke/laser-2012/):
  research/reproducibility materials and author citation are published. No
  explicit standard redistribution license was found in the inspected local
  files or supplement. Treat redistribution rights as unresolved; keep local
  for inspection. Cite Killourhy and Maxion, *Free vs. Transcribed Text for
  Keystroke-Dynamics Evaluations*, LASER 2012.

## Validation and remaining work

- AI package tests include consent/permission denial, no profile, partial and
  low-coverage windows, parity, mismatched features/sources/users, two-session
  enrollment, blocked enrollment reuse, nonfinite features, bounded input,
  reload, selected-user deletion and interrupted-write cleanup.
- Real Python bridge tests exercise persisted lifecycle, genuine/impostor
  playback, consent, cancellation, pause clearing enrollment and process failure.
- Real Electron smoke test exercises disabled controls before consent, not-ready
  verification, enrollment, both observations, consent withdrawal, deletion and
  navigation teardown. Uses isolated app data; no backend or actual typing.
- Existing backend/security/device tests and enrollment tests remain applicable.

Observed checks on this branch:

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest packages/behavioral_ai/tests -q` | 219 passed |
| Review environment `python -m pytest tests -q` | 267 passed, 3 platform skips; one existing Starlette/httpx deprecation warning |
| `npm run test:behavior` | 3 passed, actual Python child processes |
| Existing `npm run test:enrollment` | 10 passed |
| `npm run test:behavior:desktop` after web build | Passed, actual Electron and Python; screenshot inspected |
| Web build and web ESLint | Passed |
| `git diff --check` | Passed |

The repository `.venv` has AI/Qt test dependencies but lacks cryptography; the
existing workspace `.review-venv` was used for backend/security/device tests.
No dependency manifests were expanded just for that local environment difference.
The new bridge tests are included in the UI CI job. Cross-platform CI has not
been run remotely; the Electron smoke was run on this Mac.

APP-03 remains the live-account integration dependency. Future work must bind
trusted user/session state, add consented scoped timing collection with focus/
permission interruption handling, and connect real session logout/revocation
before claiming continuous verification of a signed-in user. The generic runtime
has a permission-denied state; this playback UI never requests OS input access.
KeyRecs cannot supply a third genuine recording for the chosen enrollment rule.
Aalto and CMU adapters, real multi-day enrollment and calibrated performance
measurement remain separate work. AI-05 should not be marked fully complete
until the authenticated desktop path has been validated.

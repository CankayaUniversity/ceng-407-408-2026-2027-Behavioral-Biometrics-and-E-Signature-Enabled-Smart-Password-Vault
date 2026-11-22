# Aegis Vault Desktop

Cross-platform desktop application skeleton using Electron,
React, TypeScript, and the existing shared UI kit.

## Current Scope — APP-01 / APP-02

- Login preview screen.
- Dashboard screen.
- Security Status screen.
- Sidebar navigation.
- Separate navigation controller and presentation components.
- Development-server and local-build startup modes.
- User/device enrollment wizard with user, device/finger selection, review and result.
- Local registration/pairing APIs through a private Electron → Python bridge.
- Deterministic independent mock scenarios: success, duplicate device, rejection,
  disconnect, timeout and expired pairing.

Login, Dashboard and Security Status still display demo placeholders.
Enrollment can create real local backend records, but does not authenticate a
session, unlock a vault or start behavioral monitoring.

## Architecture Decision

React and Electron replace the original Qt desktop UI proposal so
the existing React UI kit can be reused directly.

Python behavioral AI and cryptography modules remain separate.
The enrollment simulator is connected through a limited private bridge.
Behavioral AI and vault integration remain later work.

The existing PySide6 data-collection prototype remains independent.

## Install

Run from the repository root:

```bash
cd apps/desktop/ui/app-ui-kit
npm ci
```

## Development

From the UI kit directory, start Vite:

```bash
npm run dev --workspace=web -- --host 127.0.0.1 --port 5173 --strictPort
```

In a second terminal, from the same directory:

```bash
npm run desktop:dev
```

## Run Without Vite

From the UI kit directory:

```bash
npm run build --workspace=web
npm run desktop:start
```

Rebuild after source changes to update the local-build version.

## Source Layout

- `ui/app-ui-kit/electron/main.cjs`: Electron application lifecycle.
- `ui/app-ui-kit/apps/web/src/App.tsx`: application shell.
- `ui/app-ui-kit/apps/web/src/controllers/`: navigation state.
- `ui/app-ui-kit/apps/web/src/pages/`: screen components.
- `ui/app-ui-kit/packages/ui/`: shared UI components and theme.

## Electron Boundaries

- Node integration is disabled in the renderer.
- Context isolation and renderer sandboxing are enabled.
- New windows and external page navigation are blocked.
- Permission requests are denied.
- The preload exposes only enrollment register/complete/cancel operations.
- IPC accepts only the application's main frame and expected local page.
- Python owns device private keys and pairing credentials; neither is returned
  to the renderer. Requests target only `http://127.0.0.1:8000` and ignore proxies.

These settings are an initial boundary, not a completed security review.

## Manual Acceptance Checks

- Application opens in development mode.
- Application opens from a local build with Vite stopped.
- Login, Dashboard, and Security Status screens are reachable.
- Demo workspace action opens Dashboard.
- Page titles match the selected navigation item.
- Demo labeling remains visible.
- Keyboard navigation and visible focus work.

## Platform Validation

Windows, macOS, and Linux are target platforms.

Local startup has currently been verified on macOS.
Windows/Linux validation, installers, signing, and distribution
remain pending.

## APP-02: Run Enrollment

For a standalone demo, open Enrollment and choose **Independent mock demo**.
The browser preview supports mocks only; it cannot call local services.
Mock results are explicitly labeled and never authorize access.

For real local registration, prepare Python 3.11+ from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m services.backend.app.database.init_db
.venv/bin/python -m uvicorn services.backend.app.main:app --host 127.0.0.1 --port 8000
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.
Launch Electron in another terminal using the development or built mode above.
Choose **Local backend + Python simulator** in Enrollment (the Electron default).
The bridge uses the repository's `.venv` if available; set `AEGIS_PYTHON` to an
absolute Python executable path before launching Electron to override it.
No additional JavaScript dependencies were introduced for enrollment.

Registration accepts only a display name, trimmed to 1–100 characters.
Device IDs are 1–36 characters. All ten `FingerSlot` values are supported.
The backend's five-minute single-use pairing code is used internally.
The simulator enrolls the selected slot and exports its Ed25519 public key for
pairing. Successful registration/pairing retains the backend's `PENDING` status.

### Failure and lifecycle behavior

- Double submit is ignored. A safe retry resumes the failed device step without
  creating another user, re-enrolling a finger or changing the device key.
- Timeout, transport interruption after sending, malformed success and unexpected
  server errors have an uncertain outcome; automatic write retries are disabled.
- Duplicate device IDs never overwrite another device. Expired pairing cannot be
  refreshed through the current API. Review pending backend records before restarting.
- Cancellation invalidates late UI responses and stops the Python worker. Requests
  already sent may still complete. No backend rollback/delete endpoint exists.
- Navigation within the app retains the wizard and ongoing operation.
- Device keys and enrolled fingers are **memory-only**, matching the current
  simulator. Cancelling, starting another attempt, reloading or closing the window
  discards them; backend records remain. Durable device storage and resuming an
  existing device after restart are not implemented in APP-02.
- Login/session authentication belongs to APP-03; vault access belongs to APP-04.

### Tests

From the UI kit directory (Node 24.4.1, per `.nvmrc`):

```bash
npm run test:enrollment
npm run lint
npm run typecheck
npm run build
npm run test:desktop
```

`test:enrollment` checks controller races, stale responses and deterministic mocks.
`test:desktop` launches the built Electron app, Python worker and a temporary
backend database, completes real registration/pairing, checks that exactly one
user/device exists, and exercises UI validation, retry and cancellation.
It requires a graphical session, Python backend dependencies and **port 8000 free**.
It fails without using an existing server if that port is occupied. It deletes
the test database and prints a temporary screenshot path. It does not use `backend.db`.

From the repository root, with the Python environment activated:

```bash
python -m pytest tests/integration/test_desktop_enrollment.py tests/integration/test_device_pairing.py tests/unit/test_fingerprint_model.py -q
```

These tests use disposable databases and cover real registration/pairing, input
validation, duplicate ownership, expiration, simulator rejection, safe retry,
key stability, secret redaction and uncertain-write handling.

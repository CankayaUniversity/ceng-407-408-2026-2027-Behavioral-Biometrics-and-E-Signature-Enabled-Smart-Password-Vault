# Aegis Vault Desktop

Cross-platform desktop application skeleton using Electron,
React, TypeScript, and the existing shared UI kit.

## Current Scope — APP-01

- Login preview screen.
- Dashboard screen.
- Security Status screen.
- Sidebar navigation.
- Separate navigation controller and presentation components.
- Development-server and local-build startup modes.

The application currently displays demo placeholders.
Authentication, vault operations, device verification, and live
behavioral monitoring are not connected.

## Architecture Decision

React and Electron replace the original Qt desktop UI proposal so
the existing React UI kit can be reused directly.

Python behavioral AI and cryptography modules remain separate.
Communication with those modules will be implemented in later issues.

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
- No privileged renderer API is exposed yet.

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
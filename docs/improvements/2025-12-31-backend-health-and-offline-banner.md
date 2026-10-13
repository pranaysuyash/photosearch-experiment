# Improvement: Backend `/health` endpoint + UI offline banner (2025-12-31)

## What changed

This repo is “local-first”, but the web UI still relies on the FastAPI backend being reachable. When the backend is stopped (or still booting), the UI would mostly fail silently: requests error in the console and various views render empty/error states.

This improvement adds two complementary pieces:

1. **Backend:** an explicit `GET /health` endpoint.
2. **UI:** a lightweight availability probe (`api.ping()`) + a persistent **offline banner** in the top-level layout.

## Why this makes the repo better

### User experience

A local photo app should not feel “broken” just because the background service isn’t running yet.

- Before: backend down ⇒ confusing UI, empty pages, console errors.
- After: backend down ⇒ clear banner: “Backend is offline” + *Retry* + *Import* CTA.

### Operational clarity

- `GET /health` is a conventional endpoint for local dev, Docker healthchecks, and orchestration probes.
- The endpoint is intentionally **lightweight** and avoids touching `AppState` or heavyweight components.

### Developer ergonomics

- `api.ping()` is a reusable, testable primitive.
- It prefers `/health` but falls back to `/` to stay compatible with older servers.

## Implementation details

### Backend (`server/api/routers/core.py`)

Added:

- `GET /health` → returns:
  - `status: "ok"`
  - `service: settings.APP_NAME`
  - `env: settings.ENV`

Design notes:

- No database calls.
- No access to `app.state.ps`.
- No imports that could pull in heavy ML stacks.

### UI (`ui/`)

Added:

- `api.ping(timeoutMs = 1500)` in `ui/src/api.ts`.
  - Calls `/health` with a short timeout.
  - If `/health` is `404`, falls back to `/`.
  - Returns `boolean` and never throws.

- `ApiStatusBanner` component:
  - File: `ui/src/components/common/ApiStatusBanner.tsx`
  - Renders only when `status === 'offline'`.

- Wired into the global layout:
  - File: `ui/src/components/layout/Layout.tsx`
  - On mount: probe immediately and then every 15 seconds.
  - Banner is positioned just below the fixed header.

## Tests added

- Backend: `tests/test_server_config.py`
  - Added `test_health_endpoint` to ensure `/health` exists and returns expected fields.

- UI: `ui/src/test/api-ping.test.ts`
  - Validates:
    1. `/health` success returns `true`.
    2. `/health` 404 falls back to `/`.
    3. network error returns `false`.

## How to verify manually

1. Start the UI with the backend **stopped**.
   - Expected: you see the offline banner.
2. Start the backend.
   - Expected: within ~15s (or after hitting *Retry*), the banner disappears.
3. Visit the backend health endpoint:
   - `GET /health` returns JSON with `status`, `service`, `env`.

## Follow-ups (optional)

- Consider routing more UI calls through the shared axios client so error handling/telemetry is centralized.
- Add a “Start backend” hint that is OS-aware (e.g., show `./start.sh` on macOS/Linux).

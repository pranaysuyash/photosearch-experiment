# Decision: Desktop vs Web platform boundary — "Companion on your LAN", built multi-user-ready

**Date:** 2026-10-21
**Status:** Accepted (engineering); audience disposition is a proposal to the owner — see §2
**Owner:** Pranay
**Supersedes:** nothing; first explicit platform-boundary decision
**Related:** `docs/decisions/2026-10-19-launch-readiness-council.md` (gate C4, open at time of writing); `docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md` §6; `docs/decisions/2026-10-21-pwa-installability-and-tauri-dialog-permission.md` (Tauri `dialog:default` grant, PWA installability, app-icon tracking)

## 1. Context

The repo is one FastAPI backend + one React SPA delivered two ways: inside a
Tauri 2 shell (the "desktop app"), and via `vite dev` in a browser. Until now
the desktop/web split had no architectural reality:

- Only the native folder picker branched on platform — and the primary
  detector (`usePlatformDetect`) checked `window.__TAURI__`, which Tauri v2
  never injects without `app.withGlobalTauri`, so desktop-specific UI had
  silently never activated.
- ~60 fetches used same-origin `/api/…` paths (Vite-dev-proxy-only — dead
  inside the packaged Tauri app and in any static deployment) and ~20 files
  rebuilt `http://localhost:8000` inline, bypassing the axios client's
  identity/auth interceptors.
- The backend bound `0.0.0.0:8000` with no auth, served no static UI, had no
  `HOST`/`PORT` settings, and identity was a spoofable `X-User-ID` header.
- The launch council conditioned GO on **C4: define the launch audience** —
  which is the desktop/web question in product form.

## 2. Options considered for the Web target

| | 2a. Companion on your LAN (chosen) | 2b. Dev harness only | 2c. Self-hosted server product |
|---|---|---|---|
| Principals | one (owner), many devices | one, loopback only | many |
| Auth | pairing token; loopback bypass | none | full login + per-user authz |
| Data model | unchanged | unchanged | ownership columns, opaque media IDs |
| Scope | days | none | weeks; reopens all C4 external-audience blockers |
| Positioning fit | "Private by Design", local-first | neutral | pivot; competes with Immich/PhotoPrism |

**Chosen: 2a — Web = companion on the owner's LAN.** The same FastAPI process
serves the UI at `/app`; the phone/tablet is a viewer for the owner's library.
Trust boundary: loopback ⇒ owner, no ceremony; anyone else must pair once.
This is the engineering proposal for **C4: audience = owner + own devices**;
the owner may still override (flip to 2b by disabling pairing, or escalate to
2c later — 2a is a strict stepping stone to 2c because the gate is a
*principal resolver*, not a hardcoded single-user check).

Cross-reference: `docs/decisions/2026-10-21-public-commercial-go-live-requirements.md`
(parallel session, same day) reaches the compatible product verdict —
owner-only distribution is GO; the LAN companion adds devices without
changing that audience class. Its "public free" B1–B9 conditions apply only
if the app itself is distributed, which 2a does not do.

**2c is parked**, not rejected. Revive triggers: (a) a second human principal
needs the library, or (b) the deployment target stops being the owner's own
machine. Prerequisites then: ownership in the data model, opaque media IDs
(precendent exists: `/api/faces/crop/{face_id}`), per-user authorization
sweep across ~480 routes, TLS/reverse-proxy hardening, real session
management.

## 3. What was implemented (2026-10-20/21, Phases 0–2)

**Phase 0 — desktop correctness (UI)**
- `ui/src/platform/` is the single seam for platform questions:
  `detect.ts` (`shell: 'tauri'|'browser'` via `isTauri()`/`__TAURI_INTERNALS__`,
  `formFactor` via viewport + pointer media queries — the two axes no longer
  conflate), `capabilities.ts` (`pickFolder`, `revealInFileManager`,
  `launchApp`, `openExternal`). Replaced and deleted
  `hooks/usePlatformDetect.ts` + `utils/pickDirectory.ts`.
- `ui/src/api.ts` is the single seam for transport: `resolveApiBase()`
  (derives the API origin from the build target — see
  `ui/src/platform/target.ts`; the companion build is same-origin because
  FastAPI serves it), `apiUrl`, `apiFetch`
  (fetch with the same base/identity/auth as the axios client), `mediaUrl`
  factory, `setUnauthorizedHandler`. All ~65 raw call sites migrated
  (services, actions, people pages/components, privacy dashboard, OCR,
  face clustering, intent, performance, dev showcases). ESLint
  `no-restricted-syntax` now *errors* on raw `fetch('/api…')`, inline
  `localhost:8000` literals, and `import.meta.env.VITE_API_URL` outside
  `src/api.ts` (verified by deliberate-violation probe).
- `ApiStatusBanner` no longer asserts "start the server" when the real cause
  may be origin/CORS.

**Phase 1 — web build target + same-origin serving (server)**
- Vite mode `web` (`npm run build:web` → `ui/dist-web`, `base: /app/`);
  desktop `npm run build`/`ui/dist` untouched for Tauri.
- `server/ui_static.py`: `SPAStaticFiles` (404→`index.html`) mounted at
  **`/app`** when the build exists. Prefix chosen over a root catch-all
  because API routes are top-level — a catch-all would turn API typos into
  200 HTML and pollute the OpenAPI contract; a mount does neither.
- `HOST`/`PORT` settings (default `127.0.0.1`) — adopted from a
  parallel session's staged work rather than duplicated;
  `dev-restart.sh` passes `BACKEND_PORT` as `PORT`.

**Phase 2 — trust boundary (server + UI)**
- `server/principal.py`: `Principal(id, kind, via)`; `resolve_principal` —
  loopback (honours `X-Forwarded-For` only with `TRUST_PROXY`) ⇒ owner;
  otherwise HS256 session token from the `ps_session` cookie (covers
  `<img>`/`<video>`, which cannot send headers) or `Authorization: Bearer`.
  Secret: `SESSION_SECRET` or auto-generated `DATA_DIR/session.key` (0600) —
  zero config on a desktop install. `PrincipalMiddleware` gates every route
  in one place (53 `include_router` calls untouched), exempts `/`, `/health`,
  `/pair/*`, `/app`, and CORS preflights; sets `request.state.principal`.
  `user_id_from_request` now prefers the principal — the spoofable
  `X-User-ID` header remains only as a no-principal fallback.
- `server/api/routers/pairing.py`: `POST /pair/start` (loopback-only, 4-digit
  code, 5-min TTL, single-use, in-memory by design), `POST /pair/complete`
  (mints cookie+bearer), `POST /pair/revoke` (rotates the secret ⇒ all
  devices out), `GET /pair/status`. `PAIRING_ENABLED=false` restores the
  pre-gate world for local debugging.
- `server/rate_limit.py`: sliding-window per-IP limiter (existing
  `RATE_LIMIT_*` settings), loopback and `/app` static exempt, sits inside
  the principal gate so strangers consume no limiter state.
- UI: `/pair` page (code entry, `?code=` auto-complete, return-path restore),
  `UnauthorizedBridge` in the router (401 ⇒ `/pair` in browsers; Tauri never
  navigates), Settings → **Devices** panel (generate code with LAN URL,
  disconnect).

**Contract:** 4 new routes; `tests/contracts/*.json` baselines regenerated
(diff showed exactly the 4 additions, nothing else); `api-generated.ts`
regenerated. **CI:** `frontend` job now lints, runs vitest, and builds both
targets; new `desktop` job runs `cargo check` on the Tauri shell.

## 4. Verification

- Tier 2: `tests/test_ui_static.py` (5), `tests/test_principal_gate.py` (10,
  incl. the S2 lifecycle: LAN peer 401 → paired 200 → replayed code 400 →
  revoked 401), vitest 52/52, `tsc -b` clean, eslint 0 errors (rule
  probe-verified), contracts parity clean after baseline update.
- Tier 4 (live, with the 2,138-file library): `/app/` serves the SPA with all
  API calls same-origin (`/api/actions/detect-apps` 200 — previously dead);
  deep links survive hard refresh; Settings → Devices generated a live code
  with the LAN URL; secret rotation logged all devices out.
- Captures: `docs/evidence/2026-10-21-web-companion-static-serving/` (before:
  `/app` 405 under the old build; after: home, pairing code card, pair page).

## 5. Known residual / surfaced decisions

1. **`video_faces` router is included without a prefix** (`server/main.py:375`):
   `/status/{video_id}`, `/tracks/{video_id}`, `/people/{video_id}`, and a
   root-level `DELETE /{video_id}` leak to the top level (the DELETE shadows
   any single-segment path and answers 405 — observed on `/app` and on the
   manifest icon before the fix). It also collides with
   `face_recognition.py`'s `POST /api/video/faces/process`: two incompatible
   request contracts ({video_path} one-shot vs {file_path, sample_fps} job)
   for the same intended path. **Recommendation (owner decision):** prefix the
   router `/api/video/faces`, retire the `face_recognition.py` one-shot in
   favour of the job-style endpoint (its status/tracks/people companions only
   make sense with the job model), regenerate contracts. Zero UI callers
   today, so no client impact.
2. Non-loopback pairing is proven at Tier 2 (TestClient with a simulated LAN
   peer). A real cross-device test (phone on LAN) is the next Tier-5 step.
3. **The `/app` mount is build-dependent, and the backend CI job does not
   build the UI.** With no `ui/dist-web` present, `GET /app/` falls through
   to the root-level `DELETE /{video_id}` route from residual 1 and answers
   405 instead of serving the SPA. The principal-gate test therefore asserts
   only that the path is *not gated* (never 401); serving the bundle is
   covered by `tests/test_ui_static.py`, which mounts a synthetic dist on a
   bare app. The root-DELETE shadowing itself remains an owner decision
   (residual 1).
3. The in-memory pairing/limit state is per-process — fine for the single
   uvicorn process; revisit if deployment ever goes multi-worker.
4. The gallery is still not virtualized (audit residual) — matters most for
   the phone client; scheduled for Phase 3.
5. `image/*`/`file` routes still take absolute filesystem paths. Acceptable
   for the companion (same machine, same owner); opaque IDs are a 2c
   prerequisite, not a 2a one.

## 6. Roadmap

- **Phase 3 — mobile shell:** bottom tab bar against the real route table,
  virtualized grid, touch gestures, FirstRunModal z-index fix.
- **Phase 4 — desktop packaging:** Tauri sidecar supervises the Python
  backend; `data-tauri-drag-region` + real window controls; updater/signing;
  CI `tauri build`.
- **Phase 5 — parked 2c:** see §2 revive triggers.

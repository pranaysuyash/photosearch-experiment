# Decision: Tauri dialog permission, PWA installability, and app-icon tracking

**Date:** 2026-10-21
**Status:** Accepted (implemented and verified)
**Owner:** Pranay
**Related:** `docs/decisions/2026-10-21-desktop-web-platform-boundary.md` (the platform seam this work sits inside — `ui/src/platform/` is the single place platform questions are answered)
**Scope:** desktop (Tauri) runtime correctness + web (PWA) installability. No backend, no contract, no trust-boundary change.

## 1. Context

Three defects were found while making the desktop app actually able to open a
local photo folder, and while making the web companion installable:

1. **The native folder picker was dead in the packaged desktop app.** The
   dialog plugin was registered in `src-tauri/src/lib.rs` and called from
   `ui/src/platform/capabilities.ts`, but `src-tauri/capabilities/default.json`
   granted only `core:default`. Tauri v2's ACL denies any plugin call whose
   permission is not granted, so `dialog.open()` would have been rejected at
   runtime even though the frontend gate was correct.
2. **`@tauri-apps/api` was an undeclared dependency.** `ui/src/platform/detect.ts`
   imported `isTauri` from `@tauri-apps/api/core`; the package was present in
   `node_modules` only as a transitive dependency of `@tauri-apps/plugin-dialog`
   and was never declared in `ui/package.json`. It resolved by accident.
3. **The PWA was manifest-only, and its icons did not exist as far as git was
   concerned.** `ui/public/manifest.json` declared `192x192` and `512x512`
   icons, but all three PNG files (`pwa-192x192.png`, `pwa-512x512.png`,
   `apple-touch-icon.png`) were byte-identical 1024×1024 images — the declared
   sizes were false. There was no service worker, so the app was not offline
   capable. Worse, a global `*.png` rule in `.gitignore` meant **every** app
   icon was untracked: `ui/public/*.png` *and* `src-tauri/icons/*.png` (the
   Tauri bundle icons referenced by `tauri.conf.json`). A fresh clone would
   have had a manifest pointing at missing files and a `tauri build` with no
   PNG icons.

## 2. Decisions

| | Decision | Alternative rejected |
|---|---|---|
| Dialog permission | `dialog:default` in `src-tauri/capabilities/default.json` | `app.withGlobalTauri: true` — injects the whole Tauri API into `window` for every page, widening the webview's global surface to solve one permission |
| `@tauri-apps/api` | Declared explicitly (`^2.12.3`, the installed version) | Rely on the transitive hoist — breaks the moment the plugin's dependency graph changes |
| PWA service worker | Hand-written, base-aware, offline **app shell only**; never caches API or media traffic | `vite-plugin-pwa` + Workbox — a new dependency and build stage for a shell cache that is three routes; the photo bytes stay behind the backend's serve-time policy |
| Icons | Regenerated at their declared sizes from the 1024 master, plus a maskable variant | Keeping the 1024 file under three names — Chrome's installability check keys on 192 and 512, and a lying manifest is a trust surface |
| Icon tracking | `.gitignore` scoped negations for the assets the build and the docs depend on | Force-adding binaries — the rule would come back on the next file |
| API base | **Derived from the build target** in `ui/src/platform/target.ts`, not read from a machine-local env file | Keeping `ui/.env.web` — an untracked file whose *absence* silently broke the companion on a real device, and whose *presence* made the desktop bundle machine-dependent |

### 2.1 The API base is a property of the deployment topology

The API base answers "where does this bundle find its backend?" — a function of
the *topology*, which has exactly two values here:

- **desktop** — the SPA runs in a Tauri webview (`tauri://localhost`) while the
  backend is a *separate* origin on loopback, so the base must be absolute.
- **companion** — FastAPI *serves* the SPA at `/app/`, so the API is the *same*
  origin and every call must be same-origin.

That is the same fact that sets the asset base (`base: '/app/'` vs `'/'`), so
it is derived from the same signal (the Vite mode) in the same place:
`ui/src/platform/target.ts`. Three defects followed from encoding it in a file
instead:

1. **Silent wrong-target failure.** `ui/.env.web` was untracked. Without it,
   `resolveApiBase` fell back to `http://127.0.0.1:8000` — so a companion
   bundle running on a phone called *the phone's own* localhost. The build
   passed; the device failed.
2. **Machine-dependent build output.** The gitignored `ui/.env`
   (`VITE_API_URL=http://localhost:8000`) changed the *production desktop*
   bundle, so two checkouts of one commit produced different artifacts — and
   `git archive` dropped the file entirely. The host also matters: the server
   binds IPv4, and `localhost` can resolve to `::1` first on macOS.
3. **Two seams for one fact.** The asset base was decided in
   `vite.config.ts`; the API base in a different file by a different
   mechanism.

The resolution: `targetForMode(mode)` → `apiBaseForTarget(target)`, with
`VITE_API_URL` retained as a **dev-only** escape hatch (point the dev server at
a NAS, a tunnel, a custom backend port). The companion target ignores it
entirely, so a deployed companion bundle is identical on every device.

**Fail loud, not silent.** Two build-time guards now run in `vite.config.ts`:
`assertTargetConsistency` (the asset base must match the target) and
`assertApiBaseUsable` (the companion base must be same-origin; the desktop
base must be absolute). A stale `.env` with an empty value used to ship a
*dead* desktop bundle — every call would have gone to `tauri://localhost/api/…`.
It now fails the build with a message that says what to do.

`ui/.env.web` was deleted — the fact it encoded now lives in code. `ui/.env`
(the local, untracked override) was normalized to the canonical IPv4 loopback
`http://127.0.0.1:8000` so dev and production agree.

### 2.2 What `.gitignore` should include

The repo's global `*.png` / `*.jpg` rules exist to stop a photo library from
being committed. They were also swallowing assets that the *build* and the
*documentation* depend on, which is the same failure class as an undeclared
dependency — the code referenced a file the repository did not contain:

- `ui/public/*.png` — the PWA icons referenced by `ui/public/manifest.json`.
- `src-tauri/icons/*.png` — the Tauri bundle icons referenced by
  `src-tauri/tauri.conf.json` (only `icon.icns` and `icon.ico` were tracked,
  so `tauri build` had no PNG icons on a clean checkout).
- `ui/public/earth_texture.jpg` — loaded by
  `ui/src/components/features/PhotoGlobe.tsx` via
  `useLoader(THREE.TextureLoader, '/earth_texture.jpg')`; a clean checkout
  would 404 the globe texture.
- `docs/evidence/**/*.png` — the before/after captures cited as Tier-4
  evidence by two decision docs.
- `experiments/**` — the directory was ignored wholesale, yet six files in it
  were already tracked and its reports are cited from source comments (the
  caption A/B result in `server/config.py`). The rule now ignores only the
  generated dumps over the real library (`register_captions_*.jsonl`).

The rules were narrowed, not deleted: the extension block still guards against
committing a photo library, and scoped negations re-admit exactly the assets
the project depends on. `exports/` (270 timestamped GDPR test-export zips, 18
of them already tracked) is now ignored as generated test output.

**Service-worker scope rules** (`ui/public/sw.js`): cross-origin requests are
skipped; `/api`, `/search`, `/image`, `/video`, `/file` are never cached;
navigations fall back to the cached shell when the network fails; hashed
build assets are cached at runtime. The script derives its own base from
`self.location`, so the same file is correct at `/sw.js` (desktop) and
`/app/sw.js` (companion). Registration is skipped inside the Tauri shell,
which serves from a custom protocol and has no use for a web cache.

**Why the Tauri shell needs no service worker:** the desktop app is always
online with respect to its own backend (`http://127.0.0.1:8000`), so the only
thing an SW could add there is stale-shell risk.

## 3. What changed

- `src-tauri/capabilities/default.json` — added `"dialog:default"`
  (expands to `allow-ask`, `allow-confirm`, `allow-message`, `allow-save`,
  `allow-open`; `allow-open` is what `dialog.open()` needs).
- `ui/package.json` — added `"@tauri-apps/api": "^2.12.3"`.
- `ui/vite.config.ts` — removed the stale `'react-window'` entry from
  `optimizeDeps` (the package is not installed and no source file imports it;
  a stale optimize-dep entry can break `vite`/`tsc -b`); asset base and API
  base now come from the shared target module; added the two build-time
  guards; added a `preview` proxy so the companion bundle can be exercised
  locally; the proxy target now follows `BACKEND_PORT` (it was hardcoded to
  8000 while `scripts/dev-restart.sh` starts the backend on `BACKEND_PORT`).
- `ui/src/platform/target.ts` — **new**. The build-target topology module:
  `targetForMode`, `apiBaseForTarget`, `assetBaseForTarget`,
  `effectiveApiBase`, and the two build-time assertions.
- `ui/src/api.ts` — `resolveApiBase` now derives the base from the build
  target; `VITE_API_URL` is a dev-only override.
- `ui/.env.web` — **deleted** (superseded by the target module).
- `ui/.env.example` — rewritten to document the two targets and the dev-only
  override.
- `ui/src/utils/pickDirectory.ts` — **deleted**. It was the superseded
  duplicate of `ui/src/platform/capabilities.ts` (`pickFolder`), still
  carrying the old broken `window.__TAURI__` gate; all three callers already
  migrated to the platform seam. Deleting it removes a second, wrong detector
  before it can drift back.
- `ui/public/manifest.json` — honest icon sizes, `purpose` per icon, a
  maskable icon, plus `id`, `lang`, `dir`, `display_override`,
  `prefer_related_applications: false`, `categories`.
- `ui/public/pwa-{192x192,512x512,1024x1024,maskable-512x512}.png`,
  `ui/public/apple-touch-icon.png` (180×180) — regenerated at real sizes.
- `ui/public/sw.js` — new; the offline app-shell service worker.
- `ui/src/main.tsx` — registers the service worker in production builds only,
  using `import.meta.env.BASE_URL` for the script path and `shell !== 'tauri'`
  to skip the desktop shell.
- `ui/index.html` — real app icons instead of the `vite.svg` scaffold favicon;
  `apple-touch-icon` sized.
- `.gitignore` — reworked: scoped negations for the assets the build and the
  docs depend on (icons, the globe texture, evidence captures), `experiments/`
  narrowed to the generated library dumps, `exports/` ignored as generated test
  output, the orphaned root lockfile and the vector-store test artifacts
  ignored (see §2.2).

## 4. Verification

- **Rust / Tauri:** `cargo check` clean; `cargo build` produced a linked
  `target/debug/app` binary. The generated ACL confirms
  `"permissions":["core:default","dialog:default"]` and the dialog plugin's
  `default` set expands to `allow-open`. An invalid permission identifier
  fails at build time, so this is a real check, not an inspection.
- **Frontend:** `npm run build` (desktop) and `npm run build:web` (companion,
  `base: /app/`) both green; `tsc -b` clean; `npm run lint` 0 errors (128
  pre-existing a11y warnings); `npm run test:run` 60/60 across 10 files.
- **API base derivation, checked in the built artifacts:** the companion bundle
  bakes `MODE: "web"` and resolves the base to same-origin *before* reading
  `VITE_API_URL`; the desktop bundle bakes `MODE: "production"` and resolves
  `http://127.0.0.1:8000`.
- **Build-time guards, negative-tested:** `VITE_API_URL= npx vite build`
  (desktop) fails with *"the desktop bundle needs an absolute API base, but
  resolved \"\""*; the same override on `--mode web` builds fine, because the
  companion target ignores it by construction.
- **Companion end-to-end, in real Chrome against a live PhotoSearch backend**
  (`vite preview --mode web --outDir dist-web`, proxy → backend on :8099):
  every API/media request the page issued was **same-origin**
  (`http://127.0.0.1:4173/api/...`, zero cross-origin), the call returned
  **200** with real data, the service worker was `activated` at scope
  `http://127.0.0.1:4173/app/`, and an offline reload still served the shell.
- **PWA, in real Chrome (system Chrome via Playwright, not headless-shell
  emulation):** the service worker registered with the correct scope, reached
  state `activated`, and controlled the page after reload; the manifest parsed
  with 3 icons; **an offline reload still served the app shell** (title
  `PhotoSearch`, `#root` present); no service-worker console errors.
- **Manifest installability criteria**, checked against the served manifest and
  the actual image bytes: `name`/`short_name` present, `start_url` present,
  `display: standalone`, `prefer_related_applications: false`, a 192×192 and a
  512×512 icon declared, and every declared size matching the decoded PNG
  dimensions. All pass.
- **Git tracking:** `git check-ignore` reports every asset the build and the
  docs depend on as trackable; 91 files are now visible to `git status` that
  were previously invisible (app icons, Tauri bundle icons, the globe texture,
  evidence captures, experiment reports, and the concurrent session's new
  server modules and tests).

## 5. Residuals and follow-ups

1. **Not runtime-verified:** the native folder dialog inside a running Tauri
   window (`cd src-tauri && tauri dev` — the CLI is on PATH). The permission,
   the registration, and the build are all verified; the GUI round trip is
   the one step left, and it needs a human at the screen.
2. `ui/pnpm-lock.yaml` is stale (December) and contradicts
   `ui/package.json`; `ui/package-lock.json` is the live lockfile (npm is what
   the Tauri `beforeDevCommand`/`beforeBuildCommand` use). `packageManager`
   still names pnpm. Reconciling the two is a separate decision — deleting a
   lockfile is not a call to make in passing.
3. **91 newly-visible files need the owner's `git add`** — the assets above
   plus the concurrent session's new modules and tests. Nothing is staged;
   grouping is the owner's call.
4. `src-tauri/target/` is 3.2 GB of rebuildable build cache (gitignored).
   Worth pruning if disk pressure returns.
5. The service worker caches the shell under a single `photosearch-shell-v1`
   cache name. A future change to the shell needs a version bump; `skipWaiting`
   + `clients.claim` means a new worker takes over mid-session.
6. The desktop bundle's API base is still a build-time constant. If the
   backend ever runs on a non-default port in a *packaged* install, the app
   needs the base at runtime (Tauri config or a settings file) — that belongs
   to the Phase 4 packaging work, not to the build.

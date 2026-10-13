# Must-have Feature Audit — Selected 5 items

Date: 2025-12-18
Author: GitHub Copilot (audit)

## Summary

Per request, I reviewed the docs to pick five "must" features for the PhotoSearch app and audited the codebase for their implementation and quality. All five critical items listed in `docs/FEATURES_PRIORITIZED.md` were chosen and are present in the codebase; I documented the implementation evidence and proposed precise improvement opportunities, tests, and design-consistent implementation plans.

## Selected must-haves (from `docs/FEATURES_PRIORITIZED.md` — Critical/MVP)

1. Secure image serving and path sandboxing (`GET /image/thumbnail` + token mechanism)
2. Non-blocking scan & indexing (background queue + job endpoints)
3. Basic semantic search & metadata search toggles with clear UI affordance
4. Thumbnail caching & effective cache headers
5. Settings page to toggle privacy (local-only / cloud providers) + `.env.example`

## For each item: Implementation status, evidence, improvements, tests, design notes, and questions

1. Secure image serving & path sandboxing — IMPLEMENTED ✅

- Evidence & files:
  - Token logic: `server/signed_urls.py` (issue_token / verify_token)
  - Token issuance endpoint: `POST /image/token` in `server/main.py` (lines ~3600..3760)
  - Thumbnail endpoint with sandbox checks: `GET /image/thumbnail` in `server/main.py` (lines ~2556..2744)
  - Tests: `tests/test_image_token_endpoint.py`, `tests/test_image_security.py`, `tests/test_rate_limit.py`
  - UI hook: `ui/src/api.ts` calls `/image/token` and `api.getSignedImageUrl()` references
- Improvement opportunities (concrete):
  - Consistent cache headers: currently thumbnail generation sets `Cache-Control: public, max-age=31536000` when generated in-memory; fallback `FileResponse` does not add explicit cache headers — add consistent cache headers to all code paths and endpoints (`/image/thumbnail`, `/file`, `/video`).
  - Symlink & canonicalization hardening: add robust checks for symlink traversal edge-cases (macOS `/private/` vs canonical paths). Prefer `requested_path.resolve(strict=False)` -> ensure `is_relative_to(allowed)` after `realpath()` or `readlink` resolution; add unit tests for symlink attack patterns.
  - Revocation / short TTL policy: document token TTL policy and recommend short TTL by default for public deployments; add optional revocation list or issuance audit logs if required.
  - Harden headers: add `X-Content-Type-Options: nosniff`, `Referrer-Policy`, and optionally `Content-Security-Policy` on image endpoints.
  - Add metrics & rate-limits: extend rate limiting metrics and expose metrics for thumbnail generation to detect abuse.
- Tests to add:
  - Unit tests for symlink path escape, unusual absolute paths, and canonicalization differences (macOS private path edge).
  - Integration tests for `SANDBOX_STRICT=true` behavior with remote client IP (non-loopback) and for token TTL expiry.
- Design & UX considerations:
  - ServerConfigPanel (`ui/src/components/ServerConfigPanel.tsx`) currently surfaces `signed_url_enabled` and `sandbox_strict` via `/server/config`. Keep toggles visible, and do not change wording or UI layout beyond the existing component library (see `docs/UI_STYLING.md` for tokens).
- Questions / decisions needed:
  - Production secret rotation strategy for `SIGNED_URL_SECRET` — should we support automatic rotation or key identifiers in tokens (kid)?
  - Is revocation required for demo vs production?

2. Non-blocking scan & indexing (background jobs) — IMPLEMENTED ✅

- Evidence & files:
  - `POST /sources/{source_id}/rescan` uses `BackgroundTasks` to run `run_scan` in background (`server/main.py` around rescan endpoint)
  - `PhotoSearch.scan()` accepts `job_id` and updates job store (`src/photo_search.py`)
  - Persistent job store: `src/persistent_job_store.py` and job queue support
  - Job API endpoints: `GET /jobs/{job_id}`, `/jobs` list (server), and UI `JobMonitor` (`ui/src/pages/Jobs` / `ui/src/components/JobMonitor`) are present
- Improvement opportunities (concrete):
  - Job log streaming: add a simple per-job log buffer (ring buffer) accessible via `/jobs/{job_id}/logs` for live progress debugging in the UI.
  - Stronger cancellation semantics: `/jobs/{job_id}/cancel` exists; ensure scan tasks respond to cancellation cooperatively (check `PhotoSearch.scan` long-running steps and add cooperative cancellation hooks).
  - Test coverage: add integration tests simulating long scans, asserting progress updates, cancellation, and final status states.
  - UX: Improve job monitor to show recent logs, progress bars and explicit action buttons (retry, cancel, view artifacts) using existing components and tokens.
- Tests to add:
  - Integration tests for job lifecycle, cancellation, and job-store persistence across restarts.
- Questions:
  - For long-running semantic indexing across many files, do we want to rate-limit embedding generator usage or parallelize safely (MPS/GPU support documented in `FEATURES_PRIORITIZED.md`)? Clarify concurrency policy.

3. Basic semantic search & metadata search toggles — IMPLEMENTED ✅

- Evidence & files:
  - Unified `GET /search` supports `mode` param (`metadata`, `semantic`, `hybrid`) (`server/main.py` lines ~1250..1328)
  - UI toggle components: `ui/src/components/search/SearchToggle.tsx`, `SearchModeHelp.tsx`, `PageSearchWrapper.tsx` and hooks `usePhotoSearch.ts`, `useLiveMatchCount.ts`
- Improvement opportunities (concrete):
  - Show similarity/confidence score in semantic mode by default (docs recommend it): add `score` field to `/search` results when semantic mode is used, and ensure UI surfaces it with a small explanation. `server/main.py` already uses r['score'] internally for explanation (`generate_semantic_match_explanation`) — ensure it's returned and shown.
  - Add clear tooltip text in `SearchModeHelp.tsx` and small inline guidance in the primary search area (accessible and keyboard reachable per `docs/UI_ASSESSMENT.md`).
  - Add automated tests to validate ranking quality for small synthetic datasets (unit/regression tests that ensure semantic/hybrid mode picks expected items).
- Tests to add:
  - Tests asserting `mode=semantic` returns results with `score` and that `hybrid` merges metadata signals.
- Questions:
  - Any specific UI phrasing desired for the score explanation? Keep concise (e.g., "Similarity score: higher = more similar") and use tooltip.

4. Thumbnail cache & effective cache headers — PARTIALLY IMPLEMENTED ✅/⚠️

- Evidence & files:
  - `GET /image/thumbnail` sets `Cache-Control: public, max-age=31536000` for generated in-memory thumbnails (as Response headers)
  - Embedded thumbnail extraction in `src/metadata_extractor.py` (`extract_thumbnail`) and tauri/electron paths that serve thumbnails (`src/tauri_integration.py`, `src/electron_protocols.py`) exist
- Improvement opportunities (concrete):
  - Ensure consistent cache headers for the fallback `FileResponse` case (add explicit `headers` argument to `FileResponse` or handle conditional responses with `ETag`/`Last-Modified`).
  - Conditional requests: Add `ETag`/`Last-Modified` support so clients can use 304 Not Modified when appropriate (reduces load for large catalogs).
  - Format negotiation: support `Accept: image/avif,image/webp` or `?format=webp` query to deliver smaller formats where possible. Use Pillow/pyvips for conversion and preserve visual quality. See `COMPREHENSIVE_ANALYSIS_SUMMARY.md` note on WebP/AVIF.
  - Size presets & multi-resolution: provide pre-generated sizes (small/medium/large) and store them in thumbnail cache to avoid regenerating on every request; implement LRU cleanup and optional periodic re-encoding.
  - Cache-Control safety: when token-based signed URLs are used (short-lived), use short TTLs and/or `private` cache directive instead of long public max-age — ensure tokens with `scope=thumbnail` are appropriately time-limited.
- Tests to add:
  - Integration test that hits the `FileResponse` fallback and checks for cache headers and `304`/`ETag` behavior.
  - Tests for Accept header format negotiation.
- Questions:
  - Preferred max-age for public deployments? (Currently 1 year.) Recommend: shorter for thumbnails if we update thumbnails frequently (e.g., 1 day) and use immutable content-hash-based URLs for long-lived caching.

5. Settings page & `.env.example` — IMPLEMENTED ✅

- Evidence & files:
  - `.env.example` at repo root contains `SANDBOX_STRICT`, `SIGNED_URL_ENABLED`, `SIGNED_URL_SECRET`, `IMAGE_TOKEN_ISSUER_KEY` entries
  - UI Settings page and `ServerConfigPanel` (`ui/src/pages/Settings.tsx`, `ui/src/components/ServerConfigPanel.tsx`) call `/server/config` to fetch `signed_url_enabled`, `sandbox_strict`, `jwt_auth_enabled`
- Improvement opportunities (concrete):
  - Make certain privacy toggles actionable: allow the UI (ServerConfigPanel) to provide guidance and links to docs (e.g., "How to rotate SIGNED_URL_SECRET", "When to enable SANDBOX_STRICT") without changing critical safety config from the client (server toggles should remain server-side — provide link to docs rather than toggles that mutate production server settings).
  - Add a local preferences layer: allow a per-client UI setting (e.g., default `searchMode`, thumbnail quality preference) persisted locally via localStorage/tauri storage while not conflating with server settings.
  - Add a first-run flow: if `.env` is missing, show a guided first-run modal linking to `.env.example` and safe defaults (UI already references FirstRun modal; just ensure guidance is in place).
- Tests to add:
  - E2E test for Settings page that asserts server config is read and rendered correctly, and that the ServerConfigPanel behaves correctly when `SIGNED_URL_ENABLED` toggled in simulated server config responses.
- Questions:
  - For user-level privacy toggles (local-only vs cloud), do we want the UI to help create a source with cloud provider settings prefilled or should that remain manual in source creation UI? Clarify expected experience.

## Cross-cutting notes and consistency with design language

- Always use existing design tokens/components (see `docs/UI_STYLING.md` and `ui/src/components/*`) for any UI changes. Avoid introducing new component primitives unless they match the design system and tokens.
- Accessibility: ensure any new UI (e.g., Search similarity score) is keyboard accessible and screen-reader friendly. Add tests or axe checks in CI where appropriate.
- Testing expectations: No change should be merged without unit tests and at least one integration test covering the happy path and a few edge cases.
- No tech debt policy: each proposed change includes tests, docs updates (`docs/CHANGES.md`, or the new `docs/MUST_HAVE_AUDIT_2025-12-18.md`), and a small migration step where necessary (e.g., thumbnail cache schema migration). Do not leave feature toggles undocumented.

## Proposed next steps (actionable items — each should be a small PR / task)

1. Image Serving Hardening (small → medium)

- ✅ Added consistent cache headers, ETag/Last-Modified, format negotiation (JPEG/WebP) to `/image/thumbnail`
- ✅ Added cache-aware fallback responses
- ✅ Added test coverage for cache headers, conditional 304, and format override (`tests/test_thumbnail_cache_headers.py`)
- TODO: Add symlink escape tests + SANDBOX_STRICT coverage; update `docs/SECURITY.md` with rotation policy

2. Thumbnail & Format Improvements (medium)

   - Add support for `format=webp/avif` or Accept negotiation in `/image/thumbnail`
   - Pre-generate multi-resolution thumbnails with configurable retention
   - Add tests for format negotiation and caching behavior

3. Job Monitor UX & Log Streaming (small)

   - Add `/jobs/{job_id}/logs` (ring buffer), enhance `JobMonitor` to show logs and retry/cancel
   - Add tests for job lifecycle and cancellation

4. Semantic Search Visibility (small)

   - Ensure `score` is returned for semantic results and surface it in the UI with a tooltip and proper ARIA labeling
   - Add tests for `mode=semantic` response contents

5. Settings UX & Docs (small)
   - Add first-run guidance linking `.env.example` to Settings
   - Add README / help text for privacy toggles in ServerConfigPanel
   - Add E2E test for Settings rendering

## Questions / Clarifications for the product/engineering owner

- Secret rotation: Should we implement `kid` based token signatures or is manual rotation acceptable for MVP?
- TTL policy: Do we prefer short (e.g., 60s) TTLs by default for public signed URLs, or do we rely on other mitigations?
- Thumbnail format decisions: prefer WebP only (wider support) or include AVIF? Are we OK with introducing a Pillow/pyvips dependency?
- Jobs policy: Do we want a maximum concurrency limit across indexing jobs to limit resource contention? If yes, should this live in settings and be cluster-aware?

## Owner decisions & automation directives (2025-12-18)

- Key rotation: use automated, not manual. "kid" stands for key identifier — include it in issued tokens so the verifier can pick the right signing key. Maintain an in-memory key ring with {active, previous, next}; rotate on a schedule (e.g., weekly) via a background task, keep the previous key for a grace window (48h) to avoid downtime, and embed `kid` in tokens. Add a minimal key registry in settings and expose `/server/config` read-only flags showing rotation status.
- Signed URL TTL: default to longer-lived tokens per request (24h default for thumbnails, 6h for full files) with config overrides. Keep SANDBOX_STRICT enforced; pair longer TTL with rotation to mitigate risk.
- Formats: serve both WebP and AVIF when clients advertise support; fall back to JPEG. Add `format` query param override and Accept negotiation.
- Job concurrency: enable auto device selection (CPU/MPS/CUDA if available) and set a safe default concurrency of 2 for embedding/scan jobs, with a cap and backpressure in the job queue.

## Wrap-up

All 5 selected must-haves are present in the codebase. I documented concrete, prioritized improvements, tests, and design-considerate implementation guidance. If you'd like, I can (next) create individual issue-level todos and draft PR checklists and small starter patches for each improvement item (I will not modify production code until you approve any changes).

## Next 5 priority features (pulled from High Impact list) — status & plan

1. Deduplication & clustering (visual similarity): Partially present (hashes in `metadata_extractor.py`, no end-to-end dedup UI). Plan: add perceptual hash storage, cluster near-duplicates, surface suggestions in UI with review/merge flow; add tests for duplicate detection accuracy.
2. Face detection & grouping: Backend module exists (`src/face_clustering.py`) but UI/endpoints wiring is incomplete. Plan: expose endpoints, add UI grouping view, add accuracy/quality tests and fallback handling when models unavailable.
3. Batch operations with undo: Bulk delete/export/favorite exist in `ui/src/components/gallery/PhotoGrid.tsx`; undo/history is minimal. Plan: add undo/soft-delete window and action history; add tests for bulk operations + undo.
4. Responsive UI virtualization for 10k+ images: Virtualization deps present (react-window) but not used in gallery. Plan: integrate virtualization in gallery grid/list components; add perf tests against large catalogs.
5. Device selection & efficient embedding generation (MPS/GPU): EmbeddingGenerator lacks device selection. Plan: add device auto-detect (CUDA/MPS/CPU), configurable limits, and tests/benchmarks for each path.

---

If you'd like me to proceed with any of the above improvements, tell me which items to prioritize (I suggest Image Serving Hardening and Thumbnail & Format improvements as top priority). I can then create a clear implementation plan with tasks, estimate, and PR checklist.

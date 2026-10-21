# Decision record: self-verifying frontend–backend contract chain — 2026-10-14

## Root cause (one sentence)

The boundary's shape knowledge lived in three unreconciled places (FastAPI app,
58 hand-declared TS interfaces, component-level guesses) with nothing runnable
connecting them, and every enforcement layer that existed was silently
inoperative.

## Evidence (Observed)

- CI triggered on `main`/`gemini/*`; the branch is `master` — CI never ran on
  pushes. Parity job flags matched none of the scripts' argparse (could never
  have passed). Pytest path covered only `server/tests/`.
- pre-push hook never installed locally; baseline drifted (265 OpenAPI paths /
  312 routes vs 413 / 462 current).
- `dump_routes` regressed silently with newer FastAPI's lazy `_IncludedRouter`
  (inventory collapsed to 4); `app.openapi()` resolved all 413 paths.
- `ui/node_modules` stale hid 44 type errors; only 15/466 endpoints declare
  `response_model`, so generated types are real only where declared.

## Changes

1. **`scripts/contracts_dump.py`** — route inventory now derived from the
   resolved OpenAPI schema (single source of truth; immune to framework
   internals). Baseline regenerated intentionally: documents today's routes
   including `/privacy/*`.
2. **Generation chain** — `ui/package.json` gains `generate:api-types`
   (openapi-typescript devDependency) producing committed
   `ui/src/types/api-generated.ts`; CI frontend job regenerates and
   `git diff --exit-code`s it, so any backend contract change without
   regenerating types turns CI red.
3. **`.github/workflows/ci.yml`** — triggers on `master`/PRs; test job runs the
   full root suite with `requirements_security.txt` + `pytest-asyncio`;
   frontend job (install → drift gate → build); parity job with corrected
   script flags.
4. **Pattern seed** — response models declared on all 9 `/privacy/*` routes:
   exact models where serialization is `asdict(PrivacyControl)`; wrapper-level
   models for list endpoints whose row dicts are not yet shape-verified
   (enforced honesty — runtime response_model validation would reject guessed
   shapes).

## Preserved / superseded

Nothing removed. The wrapper, contracts scripts, and CI scaffold are all
extended in place (§6: complete and integrate rather than replace). The
baseline regeneration is an intentional recorded update, not a masking of
drift — the drift is itemized above.

## Validation

- `contracts_dump` → `contracts_diff` self-parity clean (462 routes).
- Full python suite **445 passed / 0 failed**; privacy + enforcement files
  23/23 after response models.
- `npm run build` green with the generated types imported into the project.
- pre-push hook installed; first push fires contracts-parity for real.

## Falsifier

A backend shape change landing with CI green while a consumer breaks; a
privacy route payload rejected at runtime by its declared response_model; CI
green on master with a deliberately broken frontend build.

## Known residuals

- `response_model` rollout across the remaining ~450 endpoints (recommend
  high-traffic read surfaces first) — owner decision on ordering.
- CI runs python 3.12 while local is 3.14 — first CI runs must be watched;
  if wheels/tests diverge, align both on one version (owner decision).
- Hand-declared interfaces in `ui/src/api.ts` migrate to the generated module
  opportunistically (when touched), not wholesale.

## Outcome (2026-10-14): CI green on master — all three jobs

Run [38609309067](https://github.com/pranaysuyash/photosearch-experiment/actions/runs/38609309067):
**test ✓** (full suite, 5m41s) · **parity ✓** (contract gate live, 2m9s) ·
**frontend ✓** (drift gate + build, 1m19s).

The first-green required four triage commits, each fixed at root rather than
masked — receipts kept here because they are the chain's shakedown record:

1. `server/requirements.txt` was missing from CI's install — core web deps
   (fastapi/pydantic/lancedb) live there, not in `requirements.txt` (`3ed8dbf`).
2. Parity job carried `--strict`, a flag `scripts/contracts_diff.py` never
   accepted — the job could never have passed as written (`41c4ec3`).
3. `@vitest/ui@^4.0.15` peer-conflicted with `vitest@^3.2.4` — pre-existing
   inconsistency tolerated by `npm install`, rejected by `npm ci`; aligned to
   `@vitest/ui@^3.2.7` (`41c4ec3`).
4. That alignment left a lockfile desync (vitest@3.2.4 vs `^3.2.7`) that local
   npm tolerated and CI's npm rejected — resolved to 3.2.7 (`390755d`); an
   unused `react-window` (zero imports, react≤18 peer) removed as the other
   npm-ci breaker (`591c2db`).

**Runner-version residual closed:** CI python 3.12 passes the full suite that
was built on local python 3.14 — the alignment risk named above is settled by
observation, not assumption.

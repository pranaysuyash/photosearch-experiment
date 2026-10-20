# Decision record: Mimosa commit-gate policy — suppression baseline + ask mode — 2026-10-19

## Context

The Mimosa L3 commit gate hard-denies on `high` findings under its default
`graded` mode. Since 2026-10-14 this has blocked all commits while ~2,900
verified lines (security fixes + UI P0 remediation) sit unprotected in the
working tree (see `2026-10-14-mimosa-security-findings.md` for the impasse).

Investigation of the installed plugin (mimosa 1.0.4, 2026-10-15) established:

- **No per-finding suppression exists.** The hook logic is sealed in a
  signature-verified asset pack (`payload/hooks/git-gate-hook.mjs.mimosa`);
  patching the cache would break signatures and be wiped on update. The
  plugin's own finding ledger explicitly never closes a deny on the
  operator's behalf (README: history only reduces re-awakening, never skips
  write/commit denies).
- **The sanctioned control surface is environmental**: `MIMOSA_GIT_GATE_MODE`
  (`graded` | `ask` | `deny` | `warn`) and `MIMOSA_NO_GIT_GATE`.
- The residual findings are deterministic static-rule hits, concentrated in
  two classes: **sanitizer-not-modeled** (a validating call precedes the
  flagged sink; the scanner does not track through helpers) and
  **test-fixture writes/literals**.

## Live evidence (2026-10-19 probes)

- `git commit --dry-run` (pre-fix): **18 high / 6 medium / 17 low**.
- After the fixes below: **15 high / 7 medium / 17 low** — the three
  test-literal sites cleared.
- The finding ledger (`.mimosa/finding-ledger/v1/events/`) shows 8 of its 14
  findings in `static_fix_verified` state; the open set matches the two FP
  classes above, all `producer: deterministic` static evidence.

## Fixed in this pass (real findings, not baselined)

- **Path traversal — `server/api/routers/sources.py` (root cause).**
  `dest = root / Path(key)` joined a remote-controlled S3 object key without
  sanitization; a `../../`-style key escaped the mirror root. New
  `_safe_rel_key()` flattens the key (drops absolute markers, `.`, `..`,
  empty segments) before the join. This was a genuine miss of the wave-1/2
  traversal fixes; the gate's flag was substantively correct.
- **Hardcoded credential literals — 3 test files** (the wave-3 class, missed
  files): `tests/test_rate_limit.py`, `tests/test_thumbnail_sandbox_symlink.py`,
  `tests/test_jev_intent_advisor.py`. All now derive per-run values via
  `uuid.uuid4().hex`, matching the `test_image_token_endpoint.py` convention.
  Verified: these sites no longer appear in the post-fix gate scan.

## Baseline classes (accepted, recorded in `docs/security/findings-baseline.json`)

- **sanitizer-not-modeled** — `sources.py` S3 flows (3× SSRF: validator at
  266/324/352; 2× path-traversal: `_safe_rel_key` at the join, `_safe_filename`
  + opaque `file_id` on the Drive path), model downloads in
  `src/face_clustering.py` / `src/enhanced_face_clustering.py`
  (`assert_public_http_url(url)` on the immediately preceding line), the
  pure-literal `sqlite_master` SELECT in `server/face_db_optimizer.py`
  (zero interpolation), and the local model-cache `dest_path` writes.
- **test-fixture** — literal-named corrupted-image fixture write in
  `tests/test_advanced_features_integration.py`.
- **accepted-risk** — `src/jev_intent_advisor.py` urlopen to the
  operator-configured advisor endpoint (default-off; local-LLM endpoints are
  a deliberate use case, same escape-hatch philosophy as
  `allow_private_endpoints`).

Baseline identity is `(file, rule, sha256(flagged line))` — Mimosa's own
scheme. If the code at an accepted site changes, the hash drifts, the entry
stops matching, and the finding resurfaces as NEW: acceptance cannot silently
rot. Entries expire after 30 days (`review_by`) and `verify` fails on expiry,
hash drift, missing evidence links, or unresolvable file/line.

## Mechanism

1. **`tools/mimosa_baseline.py`** (stdlib-only):
   - `verify` — audit the baseline (schema, evidence links, expiry, hash drift).
   - `parse <file|->` — turn a captured gate denial message into
     ready-to-review entry stubs with hashes.
   - `diff <findings.json>` — split a findings payload into baselined vs NEW;
     non-zero exit on unaccepted blocking findings.
2. **Gate mode: `ask`.** Exported as `MIMOSA_GIT_GATE_MODE=ask` in
   `~/.zshrc` (and `launchctl setenv` for GUI-launched hosts). In ask mode the
   plugin converts hard-deny on high findings into an explicit per-operation
   operator confirmation — the human acceptance step this baseline documents.
   Requires a ZCode session restart to take effect.
   **Scope trade-off, owned deliberately:** the knob is process-global, so
   `ask` (instead of `deny`) applies to all projects on this machine. Revert
   by deleting the export line; the baseline file and this record remain as
   the audit trail either way.
3. **Not done, deliberately:** `MIMOSA_NO_GIT_GATE=1` (removes the gate
   entirely) and editing the plugin cache (breaks signatures) were rejected.

## Validation

- `tools/mimosa_baseline.py verify` — PASS after the decision doc existed
  (it correctly failed while evidence links dangled).
- `parse` round-trip on the captured 15-high denial — all 12 sites map into
  the baseline; none missing.
- Touched-test run: `test_rate_limit.py`, `test_jev_intent_advisor.py`,
  `test_thumbnail_sandbox_symlink.py` — passing (see validation log in the
  launch council record of the same date).
- Falsifier for the whole mechanism: a fresh `git commit --dry-run` in a new
  session (post env change) should produce a confirmation request rather than
  a hard block, and the post-fix scan should list no unbaselined site from
  this record's classes.

## Operator options kept open

- Flip back to `graded` once the scanner models sanitizers or the residual
  sites are restructured (e.g., moving the S3 flows behind a single
  validated fetch helper may not help without interprocedural modeling).
- Re-examine `MIMOSA_GIT_GATE_GLM=1` semantic review: it was implicated in
  the 2026-10-14 stochastic impasse; the 2026-10-19 probes show
  deterministic static behavior with it off (the default).

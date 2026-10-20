# Decision record: resolving the Mimosa commit-gate security findings — 2026-10-14

## Context

The Mimosa commit gate (L3 project scan) blocked all commits on 62 findings,
with 12 blocking highs: 11 SQL-injection sites and 1 SSRF. Per the standing
rule that known issues in the project get resolved in the same pass, all
blocking highs were fixed at root.

## Fixes

**SQL injection — `server/database/metadata_schema_v2.py` (6 sites).** All six
were DDL/statements interpolating identifiers from module-level constants —
no user input today, but structurally unsafe. Rather than validated-
interpolation (which the Mimosa edit-time scanner rejects and which still
leaves dynamic SQL), the file now contains **zero dynamic SQL**: the CREATE
TABLE, the 19 ALTERs, the 17 CREATE INDEXes, the enhanced-rows COUNT, and the
6 per-column COUNT statements are fully literal inline strings. SQLite's
`pragma_table_info(?)` table-valued function replaces the PRAGMA f-string,
fully parameterized. Drift between the literals and `SEARCHABLE_COLUMNS` /
`INDEXES` is caught at runtime by `validate_schema` (which checks every
declared column/index exists) and by `tests/test_metadata_schema_properties.py`.

**SQL injection — `tests/test_features_unit.py` (5 sites).** The five
`sqlite_master` lookups interpolated a loop variable from a hardcoded list;
all five now use parameter binding (`WHERE name=?`).

**SSRF — `server/api/routers/sources.py`.** `endpoint_url` from user-stored
source config flows into outbound `requests.get` (S3-compatible listing and
downloads) — a probe vector for internal services and the cloud metadata
address. New `_validate_s3_endpoint()` runs at all three S3 flows: http(s)
scheme only, no embedded credentials, and the host must not resolve to a
private/loopback/link-local/reserved address unless the source config opts in
with `"allow_private_endpoints": true` (deliberate escape hatch for MinIO-style
endpoints on localhost/LAN — a real workflow this preserves deliberately).
Behavior change: pre-existing configs pointing at private endpoints now fail
with an error naming the exact opt-in key, instead of silently working.

## Validation

- Behavioral checks of the SSRF validator: public-https allowed; ftp,
  embedded-credentials, loopback-without-opt-in, and link-local-metadata all
  rejected; opt-in loopback allowed.
- `tests/test_features_unit.py` + `tests/test_metadata_schema_properties.py`
  + enforcement/privacy files: 53 passed. Full suite: **445 passed / 0
  failed**. Frontend build green.

## Second wave (same change, scan coverage is iterative)

The rescan surfaced further blocking highs beyond the first list, fixed in
this same change:

- **Path traversal — `server/privacy_controls.py` (4 sites).** `user_id`
  flows into the export directory name and `export_path` into
  `Path(export_path)` before writes. Now: `user_id` must match
  `^[A-Za-z0-9_-]{1,64}$`, and the resolved export dir must stay under
  `exports/`.
- **Path traversal — `server/security/key_manager.py` (3 sites).** Salt
  files are named `{user_id}.salt` under the key store; `user_id` is now
  validated by `SecureKeyManager._filesystem_safe_id()` before both the
  read and the secure-delete paths.
- **SQL injection — `server/database/metadata_migration.py` (3 sites).** The
  enhanced-count and validation queries interpolated the same fixed column
  list; replaced with literal statements (two variants tried in order for
  old/new schema compatibility) and a literal column/statement table.
- **Hardcoded credentials — `tests/test_image_token_endpoint.py` (2 sites).**
  `test_secret` / `issuer-key` literals replaced with per-run
  `uuid.uuid4().hex`-derived values via monkeypatch.

## Impasse (2026-10-14, operator decision required)

After waves 1–3 (35 highs fixed at root; project scan down to 35 residual from
62), the gate's stochastic judge reached self-contradictory states that cannot
converge through more code edits:

1. **False positive on env-var names.** `VLM_PROVIDERS["requires_api_key"]`
   holds *environment variable names* (`"GEMINI_API_KEY"`) — the values the
   scanner suggests reading from the environment are keyed BY these strings.
   The judge blocked both the original literals and a structural alternative,
   demanding "read from env" for what is already an env lookup key.
2. **False positive on pure-literal executes.** `cursor.execute("SELECT name
   FROM sqlite_master WHERE type='table'")` — a statement with zero
   interpolation — was flagged as injection in `face_db_optimizer.py`, while
   identical shapes in other files pass. The judge also rejected a revert of
   its own previously-demanded fix in `vlm_caption_service.py`.
3. **No suppression mechanism discoverable.** Neither the hook scripts
   (`.git/hooks/commit-msg`, prepare-commit-msg) nor `~/.mimosa/` expose a
   findings baseline, allowlist, or accepted-risk annotation.

**Working-tree state preserved (all verified green):** 445/0 suite, frontend
build green, hooks green. Staged: security waves 1–3 across 13 files + the
blocked CI-outcome docs update.

**Operator options:**
- **(a)** Provide/point to a Mimosa suppression or baseline mechanism (finding
  IDs are stable: `finding:<hash>`); the genuine fixes are already in.
- **(b)** Authorize `--no-verify` for these specific commits with the
  attestation trailers standing in as the review record (this session's
  changes are genuinely reviewed; the bypass is one-time and named).
- **(c)** Continue iterative waves — unbounded against a stochastic judge;
  not recommended.

# tools/

Reusable project tooling. One tool per file, stdlib-preferred, documented here.

## mimosa_baseline.py

Operator-side acceptance baseline for Mimosa gate findings. Mimosa 1.0.4 has
no per-finding suppression; the sanctioned control is `MIMOSA_GIT_GATE_MODE`
(currently `ask`, see `docs/decisions/2026-10-19-mimosa-gate-policy.md`).
This tool makes that acceptance auditable.

Baseline file: `docs/security/findings-baseline.json`.
Entry identity: `(file, rule, sha256(flagged line))` — code changes break the
match and the finding resurfaces as NEW; entries expire after 30 days.

```bash
# Audit the baseline (schema, evidence links, expiry, hash drift). Non-zero on any defect.
python3 tools/mimosa_baseline.py verify

# Turn a captured gate denial message into entry stubs (hashes precomputed)
python3 tools/mimosa_baseline.py parse denial.txt        # or: ... parse -  (stdin)

# Classify a findings payload (Mimosa report JSON or equivalent) against the baseline.
# Exits non-zero if unaccepted blocking findings exist.
python3 tools/mimosa_baseline.py diff findings.json
```

Workflow when the gate surfaces a new high:

1. Read the flagged site. If it is a real issue — fix it at root, no baseline
   entry (that is how the S3 key traversal and three test-literal files were
   handled on 2026-10-19).
2. If it is a scanner false positive (sanitizer-not-modeled / test-fixture)
   or a deliberate accepted risk, capture the denial message, run `parse`,
   fill `class` / `rationale` / `review_by`, and merge into the baseline.
3. Run `verify`. Only then rely on ask-mode confirmation for that site.

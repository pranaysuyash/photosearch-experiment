# Security Release Checklist — PhotoSearch

## Purpose

Use this checklist to validate security readiness before a public or internal release. It combines hardening, QA tests, policy checks, and runtime permissions for local-first desktop applications.

## Pre-Release Security Controls

1. Path & File Access Security (Must)

   - [ ] All file-serving endpoints validate requests against `settings.MEDIA_DIR` using `Path.resolve()` and `abs_path.startswith(settings.MEDIA_DIR.resolve())`.
   - [ ] Symlink resolution is checked so symlink-based paths cannot be used to escape media roots.
   - [ ] Test scripts included to attempt traversal attacks and symlink tests for each OS (macOS special case: security scoped bookmarks).
   - [ ] Clear `403 Forbidden` semantics for unauthorized file access; do not expose full system paths in responses.

2. Token & Secret Management (Must)

   - [ ] All provider keys or secret tokens must be loaded from environment variables or secure key store. `.env` files are not committed.
   - [ ] Add tooling to validate `.env` contains no secrets before committing (pre-commit hook recommended).
   - [ ] Local tokens or provider keys are stored encrypted at rest where applicable (Keychain on macOS, Protected Storage on Windows).

3. CORS & Network Security (Must)

   - [ ] CORS is restricted to known local origins (e.g., `http://localhost:5173`, `tauri://localhost`), and preflight checks are enforced.
   - [ ] The Tauri sidecar or server only listens on `127.0.0.1` or uses a local IPC mechanism rather than a public network port.

4. API & Data Validation (Must)

   - [ ] All endpoint inputs are validated; request schemata defined in OpenAPI & enforced via Pydantic models.
   - [ ] Reject overly large requests and rate-limit endpoints that can be expensive (search & embedding generation).

5. Logging & Secrets (Must)

   - [ ] Sanitized logs: don’t write full file paths, full provider tokens, or user data to logs. Implement log redaction.
   - [ ] Audit logs: record job starts/ends, user consent to cloud, and provider use for audit purposes.

6. Dependencies & Vulnerability Scans (Must)

   - [ ] Run SCA (Software Composition Analysis) on the dependency tree; address high & critical CVEs.
   - [ ] Review and lock dependencies (`requirements.txt` pinning & `ui/package.json`) for release.

7. Third-Party AI Provider Privacy (Must)

   - [ ] Document clearly what is sent to external providers (text queries, embeddings); confirm the minimal set of data is sent.
   - [ ] Provide a revoke/clear option to delete any provider keys and remote stored data per provider’s policy (if applicable).

8. Auth & Local API (Should)

   - [ ] Introduce a lightweight local auth token or OS-based trust mechanism for the sidecar (prevents accidental exposure if the machine serves externally).
   - [ ] For public deployments: ensure OAuth or API keys with RBAC; local builds may use an optional token-based access for external API calls.

9. Job & Worker Safety (Should)

   - [ ] Limit the maximum number of concurrent indexing jobs and CPU/RAM usage per job; provide user-configurable limits in settings.
   - [ ] Implement job throttling and rate limit embedding calls in case of cloud provider usage.

10. Data Lifecycle & GDPR (Should)
    - [ ] Provide UI and API to export metadata and vector store contents (user-initiated).
    - [ ] Provide a ‘Delete all data’ option that removes local indexes, vector store, and metadata (and optional cloud-stored embeddings if supported by provider).

## Release Testing & QA

- Security tests to run in CI prior to release:
  - [ ] Path traversal tests for all endpoints accepting paths
  - [ ] Provider token leakage scans (search for plaintext tokens in logs & responses)
  - [ ] Endpoint fuzzing for expected inputs & error handling
  - [ ] Load testing of `/scan` & `index` with a 10k dataset in a test environment to simulate resource usage

## Hardening: Developer Guidelines

- Secret management: set up environment variables for local dev and provide `.env.example` with placeholder values.
- CI/CD: enforce environment-specific configurations (do not leak production keys in tests).
- Dependencies: include vulnerability checks in CI and do periodic dependency upgrades.

## Optional Audit & Certification

- For commercial or enterprise deployments, consider third-party auditing for the backend and packaging.
- If the product is likely to be used for regulatory workloads or sensitive PII: add Legal & Compliance checklists.

## Sign-off & Release Approval (Must)

Before release, confirm:

- [ ] Security checklist items 1-4 are implemented and validated by QA.
- [ ] Path traversal & symlink test results are included with the release.
- [ ] Privacy & cloud consent flows are implemented and documented.
- [ ] Telemetry is off by default and a consent prompt is present if telemetry is included.
- [ ] A rollback plan exists for any immediate security or data issue.

## Notes for maintainers

- Keep this checklist in the repo and add it to the Release process to avoid accidental data exposure.
- If you add an endpoint that accepts file paths, add a regression test to validate path sandboxing behavior.

End of SECURITY_RELEASE_CHECKLIST.md

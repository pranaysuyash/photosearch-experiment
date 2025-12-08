# PR Checklist — PhotoSearch (Quality Gates)

This checklist helps reviewers and contributors maintain consistent quality and safety standards. Include this checklist in PR templates or QA reviews.

Before creating a PR

- [ ] Is the branch based on the latest `master` and rebased where necessary?
- [ ] Commit messages follow the convention: `feat|fix|chore|docs|test(scope): summary`.
- [ ] Update `CHANGELOG.md` (if used) and include the summary and impact.

Code Quality

- [ ] Code style follows project style; run `black`/`flake8` (or configured linter) for Python and `eslint`/`prettier` for TypeScript.
- [ ] Code is modular and avoids hard-coded paths; use `settings`/`config` values.

Security

- [ ] All file-serving endpoints have path checks and do not leak system paths or secrets.
- [ ] `.env.example` updated if new environment variables are required; verify no secrets are committed.
- [ ] No secrets or keys in code or any checked-in files.

Tests & Docs

- [ ] Unit tests added for any new logic-heavy functions or significant fix.
- [ ] Integration tests included or updated for API behavior (especially new endpoints for job/scan/search modes).
- [ ] Update relevant docs in `docs/` for new endpoints, new configs, or UX changes (TOGGLE explanations, first-run modal).

Feature Flags & Backward Compatibility

- [ ] New large-change features are behind a feature flag or are opt-in (where applicable).
- [ ] Backwards compatibility: keep old endpoint `/search/semantic` if it is used by the UI until migration is complete.

Performance & Resource Usage

- [ ] New computational tasks (embedding + indexing) should be performed in background jobs whenever possible.
- [ ] For model changes: ensure device checks are implemented and documented.

Testing & CI

- [ ] Add unit tests that validate edge cases (file-not-found, invalid input, path traversal attempts, etc.).
- [ ] Test that each endpoint returns expected success and failure HTTP status codes.
- [ ] Run test suite locally and in CI; no failing tests.

Documentation

- [ ] Update `docs/API_SPEC.md` (or `docs/copilot-raptor-review/openapi.yaml`) if there are API changes.
- [ ] Add migration notes where relevant (e.g., if vector store schema changed or index format changed).

UX & Accessibility

- [ ] UI uses `aria` labels for new toggle and interactive elements.
- [ ] Provide keyboard accessibility for search toggle and selection components.

Rollout Plan

- [ ] For large features, provide a rollback plan.
- [ ] Provide a QA checklist for release testing (e.g., scan a 10k dataset, observe job behavior, check memory usage, validate search results).

Sign-Off

- [ ] Add at least one reviewer from both backend and frontend teams.
- [ ] Include QA sign-off when adding big UX features or modifying data schemas.

Notes for reviewers

- Encourage short PRs with clear purposes; prefer many small PRs rather than one big PR.
- Prioritize code readability and tests for long-term maintainability.

End of PR Checklist

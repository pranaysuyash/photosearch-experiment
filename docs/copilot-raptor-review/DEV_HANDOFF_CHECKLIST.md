# Developer Handoff Checklist — Copilot Raptor Review

This checklist explains developer tasks, QA test cases, and verification steps for toggles, privacy, and Tauri packaging.

1. Toggle Implementation & UX

- [ ] Implement segmented control for `Metadata | Hybrid | Semantic` near the search box.
- [ ] Add placeholder sample query text based on the chosen mode.
- [ ] Persist user preference in local settings and restore on app launch.

2. Semantic Model Handling

- [ ] Add device selection & auto-detection (MPS/CPU/CUDA) in `server/config.py` and expose to the UI.
- [ ] Add lazy model loading; only load embedding model when `Semantic` is first selected or re-try on demand.
- [ ] Add fallback to metadata if the embeddings service fails.

3. Privacy & Consent

- [ ] Add a first-run welcome modal stating local-first mode and opt-in for cloud providers.
- [ ] Implement `Settings > AI Providers` to allow provider credential inputs & show what will be sent.
- [ ] Use TLS for communications to cloud providers and encrypt local token storage.

4. Thumbnail Security

- [ ] Implement strict path checking in `GET /image/thumbnail` using `settings.MEDIA_DIR` as root.
- [ ] Add tests to validate path traversal attempts are blocked.

5. Background Indexing & Job APIs

- [ ] Add background queue scaffold (Redis/RQ or Celery) for scan & embed tasks.
- [ ] Add `POST /scan` to return a `job_id` and `GET /jobs/{id}` for status.
- [ ] Ensure indexing job can be paused/resumed/cancelled.

6. MAC/TAURI Packaging

- [ ] Tauri sidecar or bundling approach selection and sign/offline packaging process for macOS.
- [ ] Implement macOS permission & security-scoped bookmark handling.

7. Testing & QA

- [ ] Unit tests for `QueryEngine`, `MetadataDatabase`, and `EmbeddingGenerator`.
- [ ] Integration tests for `POST /scan`, `GET /search/semantic` with fallback.
- [ ] End-to-end tests for toggle flows and first-run experience (use Playwright)

8. Documentation & Onboarding

- [ ] Add an in-app “Help” menu with short tips for each mode and link to quick example queries.
- [ ] Add a small modal for offline/online model selection and a button to test provider connectivity.

9. Review & Launch

- [ ] Security review of `GET /image/thumbnail` and scanning endpoints.
- [ ] Performance stress test (10k dataset with MPS/CPU configurations) and monitor memory/cpu usage.

End of Handoff Checklist

# Discussion Summary — Gemini & Claude review on Copilot Raptor Audit

Date: 2025-12-08
Source: `docs/discussion_on_copilot_review_by_gemini_and_claude.md`

## Summary

Gemini and Claude reviewed the Copilot Raptor (audit) docs and agreed the repo has a strong foundation and a clear path to production. They advised delaying Tauri until the search features (toggle, hybird/semantic) and job system are stable. Key topics addressed: toggle priority, background job handling, path security, device detection, and Tauri packaging timing.

## Key Agreed Points

- Keep developing in web mode (FastAPI + Vite) for iteration speed; make the API Tauri-ready for later packaging.
- Implement a 3-state search toggle (`Metadata | Hybrid | Semantic`) with clear UI messaging and tooltips; ensure the UI uses a `mode` param for `/search` or calls `/search/semantic`.
- Add job management for `POST /scan` (async mode with `job_id`) and `GET /jobs/{id}` endpoint.
- Prioritize path sandboxing / server file security before public testing.
- Auto-detect device (MPS/GPU/CPU) in `server/config.py`, but delay lazy loading of models until Phase 2.

## Immediate Next Steps (Prioritized)

1. Security (High): Implement `MEDIA_DIR` sandbox validation for `GET /image/thumbnail` and other file-serving routes.
2. Search Mode (High): Add toggle UI and update backend `/search` to accept `mode` param / or use `searchSemantic` + unify response schema.
3. Async Scans (High): Make `/scan` return `job_id` when requested with async mode; add `GET /jobs/{job_id}`.
4. Device detection (Medium): Auto-detect MPS/CUDA/CPU in `server/config.py`.
5. Persisted embedding mapping (Medium): Use hashed embedding IDs (sha256(file_path + file_hash + model)) to deduplicate and manage versions.

## Other Considerations

- Defer Tauri packaging until core functionality is stable and thoroughly tested.
- Prefer LanceDB for production persistence; keep FAISS/Chroma adapters for experimentation.
- Jobs can be lightweight at first (local threads/async) and later replaced by RQ/Celery if needed for scale.

## Open Questions

1. Should the front-end default to Metadata or Semantic? The team suggested `Metadata` default, with a first-run suggestion to try Semantic.
2. Hybrid weighting: Would you prefer a fixed weighting scheme (e.g., 50/50) or a user-adjustable slider? (User feedback suggested a slider may be overkill for v1.)
3. For persistence & privacy: Where should the vector store be persisted on the user's machine (e.g., `~/Library/Application Support/PhotoSearch`)?

## Action Items for Team (from discussion)

- Implement and test path validation and image serving restrictions.
- Add `mode` param to `/search` and wire it in the UI toggle.
- Convert `POST /scan` to `async` and add job endpoints and a job UI.
- Add device detection in config and expose in UI tips.
- Document first-run UX and privacy consents; implement the modal in UI.

End of Summary

# Executive Summary — PhotoSearch (One-page)

Date: 2025-12-08
Prepared by: Copilot (Raptor mini Preview)

1. Project Snapshot

---

- Product: PhotoSearch — an AI-enhanced, local-first photo search app (FastAPI backend + React UI), targeted for desktop (Tauri later).
- Core features implemented:
  - File discovery & cataloging
  - Robust metadata extraction (EXIF, GPS, hashes, thumbnails)
  - Metadata DB with versioning & historical tracking
  - Embedding generation via CLIP and a vector store (LanceDB chosen for persistence)
  - Semantic & metadata search (UI integration pending)
  - Demo UI components (grid, timeline, details) ready in the React app
- Experiments: Benchmarks for FAISS, Chroma and LanceDB — LanceDB selected as balanced for production.

2. Current Status

---

- Backend: Fully functional FastAPI backend with key endpoints for scan, search, and thumbnails.
- Frontend: React UI with grid views, hooks, and API integrations (needs search toggle & job UI enhancements).
- Security: Core functionality demo-ready, but a few critical security fixes pending (path sandboxing).
- Stability: Most end-to-end workflows work locally; some features (job queue & async scan) need non-blocking flows.

3. Key Immediate Risks

---

- File-serving path traversal: `GET /image/thumbnail` must be strictly sandboxed to `MEDIA_DIR` (fix immediately).
- Long-running synchronous scan operations can block the server for large libraries; implement async jobs.
- Embedding model resource usage: Model loads on startup; offer device detection and lazy load to reduce startup time and memory pressure.

4. Recommendations & Next Milestones

---

Critical (0–2 days):

- Secure file-serving endpoints (enforce `MEDIA_DIR` path validation).
- Add `mode` param to `GET /search` and commit to `Metadata` default & UI toggle.
- Add device detection in startup config and document fallback.

High (1–2 weeks):

- Implement async scanning with job IDs & job tracking UI.
- Add search-mode UI toggle and semantic UI integration.
- Add job tray for indexing status & progress.

Medium (2–4 weeks):

- Add adapter for vector stores, batch indexing improvements, and parallel embedding generation.
- Add E2E tests and a CI skeleton for key flows (toggle, job queue, security tests).

Long-term (1–3 months):

- Tauri packaging & Mac-first MPS model support
- Face clustering, duplicate detection & auto-tagging
- Telemetry opt-in & further product UX improvements

5. Success Metrics / KPIs

---

- Search latency — P95 < 500ms in metadata mode for 10k images
- Indexing throughput — define target: e.g., 10k images in < 1–2 hours for embedding purchases (varies by device)
- Toggle adoption — % of users that try Semantic vs Metadata mode
- Job queue reliability — failure rate (<=1%) & average job completion time
- Telemetry opt-in: percent of users (if enabled), should be opt-in only

6. Ask / Decisions Needed (for next sprint)

---

- Approve immediate security fix for file-serving endpoints (high priority).
- Confirm `default_search_mode = metadata` and `semantic` is optional via first-run suggestion.
- Confirm LanceDB as the production vector store and experimental support for FAISS/Chroma.

7. Draft Budget / Resource Estimate (High Level)

---

- 3–5 dev days for critical fixes (path sandbox, search toggle, device detection)
- 7–10 dev days for async jobs + job-tray UI + integration tests
- 1–2 dev days for PR checklist, test plan, and OpenAPI documentation improvement
- 2–4 weeks for Tauri packaging and model bundling (Phase 2)

8. Final Notes

---

The project is technically solid and a great basis for a local-first desktop product. The remaining tasks center on security, user clarity, and scaling usability. Prioritize the security and job orchestration items, then focus on UX and packaging for Tauri.

End of EXECUTIVE_SUMMARY.md

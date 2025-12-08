# Roadmap: PhotoSearch Experiment

## Overview

This roadmap splits features into phases and defines milestones, owners, and acceptance criteria.

## Phase 0 — Stabilize (0–2 weeks)

- Fix thumbnail path validation & sandboxing for security.
- Add `.env.example` and secure default settings.
- Implement model device selection and lazy-loading to avoid high memory usage.
- Add embedding dedup and hashed vector IDs.

Milestone: Securely serve thumbnails & stable local runs without accidental file exposure.

## Phase 1 — UX & API Polishing (2–4 weeks)

- Background task queue with job status endpoints (Redis + RQ or Celery).
- Thumbnail caching and CDN-friendly headers.
- Lightweight authentication for the API (token-based for local desktop).
- Add progress UI hook for scans in the React app and job polling.

Milestone: Non-blocking scans and responsive UI with feedback.

## Phase 2 — Performance & Scale (4–8 weeks)

- Batched and parallel embedding generation.
- Add FAISS & Milvus adapters and migration tooling.
- Optimize vector store indexes and schema.
- Add file watcher or scheduled incremental scanning.

Milestone: Handle datasets up to 100k images efficiently.

## Phase 3 — Feature Expansion & Production Hardening (1–3 months)

- Face detection, subject recognition, and albums.
- Duplicate detection & cleanup UI.
- Robust Tauri packaging for macOS, Windows, Linux with sidecar python runtime.
- Observability (Prometheus, tracing) and Sentry integration.
- Multi-user or multi-directory features; data export & GDPR compliance.

Milestone: Desktop app ready for distribution with core features and monitoring.

---

## Dependencies & Assumptions

- Team capacity and access to hardware (GPU or Apple MPS for local acceleration).
- Access to AI providers if cloud models are used. Preference for local models for privacy.
- Focus on a 'local-first' Tauri app with optional cloud providers.

---

## Risk Matrix

- Data leakage through API endpoints — High risk; implement sandboxing and auth early.
- Dependence on GPU hosting for model acceleration — Medium risk; MPS support mitigates for mac users.
- Persistent storage scaling — Medium to High risk depending on dataset size; plan vector store migration.

---

If this roadmap is agreeable, I can begin implementing Phase 0 items and provide PRs with tests and documented changes.

# Roadmap: Living Museum (PhotoSearch)

**Last Updated**: 2025-12-09  
**Status**: Phase 2 Complete, Core Baseline In Progress

---

## Vision

A **media management app** supporting both **local and cloud** storage with AI-powered semantic search and unique 3D globe visualization.

**Target Users**: Photographers, power users, self-hosters, privacy-conscious users  
**Deployment**: Web app (React + FastAPI), future desktop (Tauri), future mobile (PWA/Native)

---

## ✅ Completed

### Phase 0 — Foundation
- [x] File discovery and cataloging
- [x] Format analysis
- [x] Comprehensive metadata extraction (Image, Video, Audio, PDF, SVG, HEIC)
- [x] LanceDB vector store integration
- [x] CLIP-based semantic embeddings

### Phase 1 — Core UI & Critical Fixes
- [x] React + Vite + Tailwind frontend
- [x] PhotoGrid with Masonry layout
- [x] PhotoGlobe 3D visualization (NASA texture, rotating markers)
- [x] PhotoDetail modal with full metadata
- [x] Search → Click → Detail navigation flow
- [x] Theme toggle (dark/light)
- [x] First-run onboarding with scan button

### Phase 2 — UX Polish & Features
- [x] Infinite scroll (backend pagination + frontend IntersectionObserver)
- [x] Real-time file watcher (watchdog)
- [x] Advanced search syntax (`filename:`, `size:>5MB`, `date:`, `camera:`)
- [x] Timeline polish (month names, click-to-filter)
- [x] Multi-select mode with bulk export (ZIP)
- [x] Download original button
- [x] Spotlight/Command Palette photo selection

---

## 🚧 In Progress: Core Baseline

**Goal**: Implement essential features that every media management app must have.

| Feature | Priority | Status |
|---------|----------|--------|
| **Sort by** (Date/Name/Size) | P0 | ❌ |
| **Filter** (Photos/Videos/All) | P0 | ❌ |
| **Favorites** (Star toggle) | P0 | ❌ |
| **Delete/Trash** | P0 | ❌ |
| **Albums** (Create, add photos) | P0 | ❌ |
| **Grid zoom** (Dense ↔ Comfortable) | P1 | ❌ |
| **Rotate/Flip** (Basic edit) | P1 | ❌ |

---

## 📋 Future Phases

### Phase 3 — Organization & Discovery
- [ ] Face recognition (InsightFace/DeepFace local model)
- [ ] Duplicate detection (hash + perceptual)
- [ ] Smart Albums (auto-generated: Screenshots, Large Videos, etc.)
- [ ] Location clustering (group by city/country)
- [ ] Import wizard (select source folders)

### Phase 4 — Scale & Performance
- [ ] Batched embedding generation (chunks of 32)
- [ ] Redis job queue for online deployment
- [ ] User authentication and multi-tenancy
- [ ] Cloud storage connectors (S3, Google Drive, iCloud)

### Phase 5 — Advanced Features
- [ ] Memories/Recaps (auto-generated highlights)
- [ ] Sharing (generate links, optional cloud upload)
- [ ] Basic photo editing (crop, adjust)
- [ ] AI auto-tagging
- [ ] Mobile companion (PWA or React Native)

### Phase 6 — Production Hardening
- [ ] Tauri desktop packaging (macOS, Windows, Linux)
- [ ] Observability (Prometheus, Sentry)
- [ ] GDPR compliance and data export
- [ ] CDN-friendly thumbnail caching

---

## Competitive Positioning

| Feature | Google Photos | Apple Photos | Lightroom | **Living Museum** |
|---------|--------------|--------------|-----------|-------------------|
| AI Search | ✅ | ✅ | ✅ | ✅ |
| Location Map | 2D | 2D | 2D | **3D Globe** |
| Local + Cloud | Cloud only | iCloud | Cloud | **Both** |
| Open Source | ❌ | ❌ | ❌ | **✅** |
| Self-hosted | ❌ | ❌ | ❌ | **✅** |

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Scale beyond 100K images | Medium | LanceDB handles well; plan Milvus migration |
| Multi-user isolation | Medium | Separate vector indices per user |
| Delete operations | High | Soft delete to trash first, confirm permanently |
| Cloud storage costs | Medium | User brings own storage credentials |

---

## Documentation Status

| Doc | Status | Action Needed |
|-----|--------|---------------|
| README.md | Outdated | Rewrite for current state |
| PROJECT_OVERVIEW.md | Outdated | Update or deprecate |
| docs/*.md (21 files) | Mixed | Consolidate key docs |
| docs/tasks/ (19 files) | Historical | Archive |

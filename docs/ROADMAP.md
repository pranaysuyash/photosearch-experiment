# Roadmap: Living Museum (PhotoSearch)

**Last Updated**: 2025-12-17
**Status**: Phase 2 Complete, Core Baseline 85% Complete

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
- [x] Sort by (Date/Name/Size) - verified complete 2025-12-17
- [x] Filter (Photos/Videos/All) - verified complete 2025-12-17
- [x] Favorites (Star toggle + filter) - implemented 2025-12-17
- [x] Delete/Trash (5-second undo) - implemented 2025-12-17

---

## 🚧 In Progress: Core Baseline (93% Complete)

**Goal**: Implement essential features that every media management app must have.

| Feature | Priority | Status | Completion Date |
|---------|----------|--------|-----------------|
| **Sort by** (Date/Name/Size) | P0 | ✅ | 2025-12-17 |
| **Filter** (Photos/Videos/All) | P0 | ✅ | 2025-12-17 |
| **Favorites** (Star toggle) | P0 | ✅ | 2025-12-17 |
| **Delete/Trash** | P0 | ✅ | 2025-12-17 |
| **Albums** (Create, add photos, Smart Albums) | P0 | ✅ | 2025-12-17 |
| **Grid zoom** (Dense ↔ Comfortable) | P1 | ✅ | 2025-12-17 |
| **Rotate/Flip** (Basic edit) | P1 | ❌ | - |

### Albums Feature Details (NEW - 2025-12-17)

- ✅ SQLite database with junction tables
- ✅ 9 REST API endpoints (CRUD + photo management)
- ✅ Smart Albums engine with 8 rule types
- ✅ 5 predefined Smart Albums (Screenshots, Large Videos, No Location, Recent, With Location)
- ✅ Frontend: 6 UI components + routing + navigation
- ✅ Create/Edit/Delete albums
- ✅ Add/Remove photos from albums
- ✅ Auto-populated Smart Albums
- ✅ Glass-morphism design system compliance
- 📄 [Full Documentation](./ALBUMS_IMPLEMENTATION_2025-12-17.md)

### Grid Zoom Feature Details (NEW - 2025-12-17)

- ✅ 3 zoom levels (Compact: 7 cols, Comfortable: 5 cols, Spacious: 3 cols)
- ✅ ZoomControls component with glass-morphism design
- ✅ Dynamic column breakpoints in PhotoGrid
- ✅ Keyboard shortcuts (`+` to zoom in, `-` to zoom out)
- ✅ localStorage persistence
- ✅ Smooth responsive transitions

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

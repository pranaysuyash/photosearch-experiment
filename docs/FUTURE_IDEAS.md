# Future Feature Ideas

This document captures feature ideas for future implementation, gathered from user feedback and other projects.

## Priority Matrix (From Similar Projects)

| Feature | Impact | Effort | Priority | Notes |
|---------|--------|--------|----------|-------|
| **Keyboard Shortcuts** | High | Low | ✅ Done | Arrow keys, Escape |
| **Search & Filter** | High | Low | ✅ Done | Semantic + metadata |
| **Sort Options** | High | Low | 🔜 Phase 1 | By date, name, size |
| **Custom Cover Selection** | High | Low | 🔜 Phase 1 | Pick album cover |
| **View Modes** | Medium | Medium | 🔜 Phase 1 | Grid, list, timeline |
| **Themes/Colors** | Medium | Medium | 🔜 Phase 1 | Dark, light, custom |
| **Bulk Operations** | High | Medium | ⭐ Phase 2 | Multi-select, batch edit |
| **Undo/Redo** | High | Medium | ⭐ Phase 2 | Action history |
| **Virtual Scrolling** | High | Medium | ⭐ Phase 2 | 10k+ photo performance |
| **Nested Collections** | Medium | High | 📋 Phase 3 | Folders within folders |
| **Smart Collections** | Very High | High | ⭐ Phase 3 | Auto-group by AI |
| **AI Suggestions** | Very High | Very High | ⭐ Phase 3 | "You might like" |
| **Slideshow** | Medium | Medium | 📋 Phase 3 | Ken Burns auto-play |
| **Advanced Sharing** | High | High | 📋 Phase 3 | Links, exports |

---

## Tech Exploration Ideas

### 3D/Visualization
- [ ] **WebGPU** - Chrome's new graphics API (experimental)
- [ ] **Raw WebGL** - For performance-critical rendering
- [ ] **MapBox/MapLibre** - Real maps for GPS-tagged photos
- [ ] **Cesium.js** - 3D globe with terrain

### Vector Databases
- [ ] **Re-test LanceDB** - Semantic search accuracy issues reported
- [ ] **Qdrant** - Alternative to LanceDB
- [ ] **Pinecone** - Cloud-hosted option
- [ ] **pgvector** - PostgreSQL extension

### Known Issues
- [ ] **Semantic search returns irrelevant results** (e.g., "tractor" shows random photos)
  - Need to verify: embedding model working?
  - Need to verify: query vs stored vectors matching?
  - Test with controlled vocabulary

---

## User Requests
1. Mapbox for real location-based browsing
2. Explore WebGL as R3F alternative
3. Chrome's new 3D native support (WebGPU)

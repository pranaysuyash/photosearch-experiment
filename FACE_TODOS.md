# Face System TODOs (Remaining Work)

## Requested Next Steps
- [ ] Implement a concrete hosted provider adapter (AWS/Azure/Google/Face++).
- [ ] Add backend/embedding compatibility gating + tests.
- [ ] Update README with the new fallback configs.

## Fallback Providers (Detection + Embeddings)
- [ ] Implement concrete adapters for at least one hosted provider (AWS/Azure/Google/Face++), mapping to the remote HTTP contract.
- [ ] Add embedding version compatibility gating (avoid mixing ArcFace + CLIP vectors in the same cluster).
- [ ] Add rate limiting + retry/backoff for remote providers.
- [ ] Add caching for remote embeddings to reduce API calls.
- [ ] Add health/status reporting for active detection + embedding backends.

## Testing & Validation
- [ ] Complete manual checklist in `FACE_TESTING_CHECKLIST.md` (core workflows, edge cases, perf).
- [ ] Add tests for detection-only backends with embedding fallback (MediaPipe/YOLO + CLIP/Remote).
- [ ] Add tests for remote detection/embedding error paths (timeouts, malformed payloads).
- [ ] Run end-to-end UI workflows for face management with fallback backends enabled.
- [ ] Expand scale tests for 10K+ faces (performance + memory).

## UX & Observability
- [x] Expose active backend + embedding source in People UI (diagnostics panel).
- [x] Add user-facing warnings when clustering uses fallback embeddings (lower precision).
- [ ] Add telemetry for remote backend latency and failure rate.

## Documentation
- [ ] Update README with fallback env examples and a short provider comparison.
- [ ] Publish a provider selection guide (accuracy, cost, privacy).

## Advanced Face Specs (.kiro/specs/advanced-face-features)
- [ ] Implement FAISS embedding index + switch from LinearIndex (Phase 1 tasks 1.1-1.7).
- [ ] Add property tests for FAISS performance + incremental updates (1.2, 1.4, 1.7).
- [ ] Add attribute accuracy tests (age/emotion/quality) with labeled datasets (2.2, 2.4, 2.6, 2.8).
- [ ] Build analytics engine + endpoints (timeline, relationships, events) (3.1-3.8).
- [ ] Add advanced ranking + suggestions for natural-language face search (basic ranking now orders by match count).
- [ ] Extend video face tracking + video search endpoints (5.1-5.4).
- [ ] Add privacy controls: consent, face blurring on export, anonymous mode (6.1-6.6).
- [ ] Model versioning + migration support (Requirement 6 / Phase 7 tasks).

## Advanced UI Legacy Modules
- [x] Removed legacy advanced panels that were unlinked from routes:
  - `ui/src/components/advanced/FaceRecognitionPanel.tsx`
  - `ui/src/components/advanced/DuplicateManagementPanel.tsx`
  - `ui/src/components/advanced/SmartAlbumsBuilder.tsx`
  - `ui/src/pages/AdvancedFeaturesPage.tsx`

## UI Cleanup / Parity Checks
- [x] Removed redundant face UI components (functionality in People.tsx):
  - `ui/src/components/faces/AdvancedFaceManagement.tsx` (deleted - duplicate of People.tsx + FaceAttributeSearch)
  - `ui/src/components/people/ClusterManagement.tsx` (deleted - duplicate of People.tsx + UnassignedFaces)
- [ ] Wire or remove remaining components:
  - `ui/src/components/people/MoveFaceModal.tsx` (used by People.tsx)
  - `ui/src/components/people/SimilarFaceSearch.tsx` (verify backend endpoint exists)

## SQL Schema Fixes (Completed Dec 29, 2025)
- [x] Fixed `fd.detection_id` → `fd.id` (38 occurrences in face_clustering_db.py, face_analytics_service.py, people_photo_association.py)
- [x] Fixed `fd.bounding_box` → `json_object(...)` for face_detections table (10 occurrences)
- [x] Fixed UnidentifiedFaces.tsx to use correct API methods

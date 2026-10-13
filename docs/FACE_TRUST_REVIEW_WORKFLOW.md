# Face Trust & Review Workflow

This document describes the **Trust & Review** workflow for face recognition.

The goal is simple: keep the People view accurate by giving you a focused inbox of items that need human attention.

## Where to find it

- Go to **People**.
- Open the **Inbox** tab.

## Queues

### 1) Unassigned (Unknown bucket)

Faces that exist in the modern `face_detections` table but do **not** appear in `photo_person_associations`.

What you can do:
- **Create** a new person (creates a new cluster and assigns the face)
- **Assign** to an existing person

UI:
- Route: `/people/unassigned`

Backend:
- `GET /api/faces/unassigned?limit=&offset=`
- `POST /api/faces/split` (create person from a single detection id)
- `POST /api/faces/move` (assign to existing cluster)

### 2) Needs Review (gray-zone assignments)

Matches that are plausible but below auto-assign threshold. These require confirmation.

UI:
- People → **Needs Review** tab

Backend:
- `GET /api/faces/review-queue?limit=&offset=&sort=`
- `GET /api/faces/review-queue/count`
- `POST /api/faces/review-queue/{detection_id}/resolve` (`confirm | reject | skip`)

### 3) Merge Suggestions (possible duplicates)

Conservative merge suggestions based on prototype similarity and **no co-occurrence conflicts**.

UI:
- People → **Merge Suggestions** tab

Backend:
- `GET /api/faces/clusters/merge-suggestions?threshold=&max_suggestions=`
- `POST /api/faces/clusters/merge-suggestions/dismiss`
- `POST /api/faces/merge` (merge with undo)
- `POST /api/faces/undo` / `GET /api/faces/undo/status`

### 4) Low Confidence (legacy detections)

Faces in the legacy `faces` table with `confidence < threshold`.

UI:
- Route: `/people/low-confidence`

Backend:
- `GET /api/faces/low-confidence?threshold=&limit=&offset=`
  - Response includes both `count` (page size) and `total` (full match count).
- `GET /api/faces/crop/{face_id}?size=` (crop helper for legacy faces)

## Notes on schema

This project currently supports both:
- **Modern schema** (primarily used by clustering/embeddings): `face_detections`, `face_clusters`, `photo_person_associations`
- **Legacy schema** (older endpoints): `faces`, `clusters`, `cluster_membership`

The Inbox emphasizes modern schema queues, but legacy views (like Low Confidence) remain available for older databases.

## Testing coverage

- Backend: `server/tests/test_face_low_confidence_endpoint.py` validates that `/api/faces/low-confidence` returns an accurate `total` field independent of pagination.

## Next planned improvements

- Dedicated Mixed Clusters queue UI (not hidden behind “Face Tools”).
- Add a detection-level crop endpoint for modern `face_detections` so Unassigned/Review queues can show true face crops instead of photo thumbnails.
- Add an Operation History view for merges/splits/moves with undo breadcrumbs.

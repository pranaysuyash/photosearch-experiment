# User Flows & Feature Interaction — PhotoSearch

This document outlines expected user flows, UI states, and acceptance criteria for primary features.

1. Scan & Index Flow (Desktop/Local)

---

Actors: User (local), app

Flow:

- User opens the app and selects “Scan my Photos” or provides a directory.
- System validates directory is accessible and prompts user to confirm.
- System enqueues scan job; UI shows job with progress; scan runs asynchronously in background.
- For each file, metadata extractor extracts rich metadata and writes to DB; embedding generation runs either in same job or a separate worker.
- The UI updates with progress and an estimated time remaining if available.

Acceptance Criteria:

- User is presented with a job ID and status; job can be paused/resumed.
- The scan works for directories with nested folders and finds images and videos.
- The scan does not block the UI and is resuming-safe.
- Error conditions report which files failed and why.

Edge Cases:

- Paths with non-ASCII characters; very large directories; corrupted images; read-permission failures.

2. Search (Metadata) Flow

---

Actors: User

Flow:

- User types a query or uses a filter (camera, date, resolution).
- UI displays results via the PhotoGrid with metadata snippets.
- User can refine filters or click a result to reveal Photo Detail.

Acceptance Criteria:

- Query engine returns results within a reasonable time (500–1000ms for 10k dataset).
- Filters are applied and combinable.
- Clicking a result opens Photo Detail showing metadata & actions.

Edge Cases:

- Query contains invalid syntax; return helpful error and a hint to use the query builder.

3. Semantic Search Flow

---

Actors: User

Flow:

- User toggles to ‘semantic’ mode and types a natural language query or uses an example.
- UI calls `GET /search/semantic` and shows top matches sorted by similarity.
- User has option to show/explain how results matched (e.g., tags inferred or top-k objects) and can refine.

Acceptance Criteria:

- Semantic search returns visually similar results.
- The UI shows similarity scores and an option to refine by adding or removing terms or toggles (e.g., color, objects, person vs. no-person).

Edge Cases:

- Query is too vague; show tips and allow fallback to metadata search.

4. Browse via Timeline Flow

---

Actors: User

Flow:

- User opens timeline and sees aggregated counts (monthly) represented in a graph.
- Clicking on a month filters the PhotoGrid to that month; also allows additional filter (camera, or location).

Acceptance Criteria:

- Timelines update in real-time or after scan completion.
- The grid displays correct subset for that month.

Edge Cases:

- Images without creation date; group them under "Unknown Date" or use file system create date as fallback.

5. Photo Detail & Version History

---

Actors: User

Flow:

- User selects a photo to open the detail drawer or modal.
- Detail shows: big image, metadata sections, EXIF data, GPS map preview, thumbnail, and version history.
- User may export metadata JSON or copy it.

Acceptance Criteria:

- The metadata shown matches the DB and includes history button to see previous versions.
- The version history is useful and shows the changes captured.

Edge Cases:

- Missing metadata fields are hidden or have a placeholder.

6. Duplicate Detection Flow

---

Actors: User

Flow:

- User requests "Find Duplicates" or the system suggests duplicates automatically.
- UI shows clusters of similar images; user reviews and selects a master; other items can be flagged for deletion or grouping.

Acceptance Criteria:

- Duplicates are grouped with similarity scores.
- User can select and confirm deletion with an undo grace period.

Edge Cases:

- Images may be similar but not duplicates (e.g., multiple images in same scene); show a confidence level.

7. Export & Batch Actions Flow

---

Actors: User

Flow:

- User selects multiple images and either exports them or applies batch edits (tags, remove, favorite).
- Export shows selected images and options (format, size, metadata inclusion).
- Batch delete requires confirmation.

Acceptance Criteria:

- Batch operations execute with progress and offer undo in case of accidental operations.

8. Settings/Privacy Flow

---

Actors: User

Flow:

- User opens settings and selects privacy options: local-only vs cloud provider.
- If cloud provider chosen, the UI prompts for provider credentials & shows a clear privacy summary of what’s sent.

Acceptance Criteria:

- Users can disable network access to protect privacy.
- Settings are persisted and accessible for future runs.

9. Tauri Desktop Flow

---

Actors: User (Desktop)

Flow:

- On first run, the app asks for directory access.
- Use sidecar or background service for scan/index; security prompts should be clear.
- UI updates indicate when the sidecar is active.

Acceptance Criteria:

- Tauri built app uses OS permission flows and provides consistent, secure file access.

## Summary

The UI and flows are cohesive and usable. Focus on adding non-blocking scans, progress feedback, privacy toggles, and a robust photo detail flow to complete the minimal product. For large datasets, add pagination & virtualization and a simple dedup & clustering UI to manage photos.

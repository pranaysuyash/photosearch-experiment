# Testing Plan & Test Cases — PhotoSearch

This file describes the testing plan and notable test cases that need to be covered by unit tests, integration tests, E2E tests, and performance benchmarks.

## Test Levels

- Unit Tests: Validate core pure functions and parsing logic (QueryEngine, metadata parsing helpers, JSON schemas).
- Integration Tests: Test API endpoints using `FastAPI TestClient` or similar. Includes `scan` endpoint behavior, search endpoints, thumbnail serving, and job endpoints.
- E2E Tests: Validate UI flows using Playwright/Cypress (search toggle usages, timeline filter, photo detail, job progress).
- Performance/Load Tests: Benchmark indexing & search (FAISS/Chroma/Lance), memory usage with 10k images, embedding model memory usage.

## Test Environments

- Local dev plus CI builds with sample datasets (`data/test_media`) and small sets for quick tests.
- Benchmarks on a larger dataset (e.g., 1k - 10k) to evaluate throughput & latency.

## Unit Tests (Python)

1. `metadata_extractor.extract_all_metadata()`
   - Test JPEG/PNG/HEIC with and without EXIF.
   - Ensure EXIF fields (camera, GPS) are parsed correctly.
2. `QueryEngine` parsing and evaluation
   - Valid expressions: `image.width>=1920 AND exif.image.Make=Canon`.
   - Invalid syntax handling returns an appropriate error or empty results.
3. `image_loader.extract_video_frame()`
   - Return an image for a sample video, assert it handles short videos and errors (no ffmpeg).
4. `server/lancedb_store.add_batch()` & `search()`
   - Test adding vectors, search returns top K results and includes metadata mapping.
5. Path validation helper for `get_thumbnail()`
   - Provide `../../etc/passwd` and ensure it returns `403`.

## Integration Tests (API)

1. POST `/scan` (sync)
   - Valid path returns `200` and correct `files_indexed`.
   - Non-existent path returns `404`.
2. POST `/scan?async=true`
   - Returns `202` and `job_id`. `GET /jobs/{job_id}` returns `queued` and then `running` and completion statuses.
3. GET `/search?query=...&mode=metadata`
   - Matches metadata queries as expected.
4. GET `/search?query=...&mode=semantic`
   - Returns semantic results (if model loaded) or `503` when model is unavailable.
5. GET `/image/thumbnail?path=...&size=...`
   - Valid path returns image; invalid path returns `403` or `404`.
6. GET `/timeline` and GET `/stats`
   - Return timeline and statistics in correct JSON.

## E2E Tests (UI with Playwright/Cypress)

1. First-run modal & toggle default
   - App displays first-run prompt once; toggling between modes updates UI help text.
2. Toggle UX: search in metadata vs semantic
   - Search for a known metadata term (camera) should return relevant results in metadata mode.
   - Semantic natural language query returns visually similar images.
3. Job flow: `/scan?async=true`
   - Create a job, verify job-tray progress updates, cancel job and confirm partial indexing state.
4. Photo Detail view
   - Click an image; verify detail modal shows file metadata and history versions.

## Performance Tests

- Indexing throughput: Measure files processed per second for 1k, 10k images.
- Vector search latency: For 1k and 10k vectors measure avg/median/95th percentile response time.
- Memory usage: For the embedding generator (with MPS vs CPU), measure total memory usage during batch indexing.

## Regression & Security Tests

- Test path sandboxing using symlinks and path traversal attempts.
- Test unauthorized access attempts and ensure they are blocked.
- Validate that no secrets are logged or exposed in logs or responses.

## CI Integration Recommendation

- Run unit & integration tests on pull requests.
- Run E2E nightly (or on merge to master) due to longer run times.
- Include a performance benchmark job that runs weekly or on-tag for releases.

## Acceptance Criteria for tests

- All critical endpoints must be unit tested.
- Security tests for path validation and secret handling must exist before public testing.
- 95% unit test coverage for core modules (`file_discovery`, `metadata_extractor`, `metadata_search`, `server` endpoints).
- No regressions in the toggle or job flows for UI E2E tests.

End of Test Plan

# API Specification — PhotoSearch API

This is an API contract for the frontend and potential external clients. It captures endpoints, examples, responses, and security considerations.

Base URL: `http://localhost:8000` (Replace with production host)

---

## POST /scan

Trigger a scan of a directory.

Request Body (JSON):

```
{ "path": "/Users/username/Photos" }
```

Query Params:

- `force` (optional boolean): Force re-scan & re-extract metadata

Responses:

- 200 OK

```
{ "status": "success", "message": "Scanned X files", "extracted_vectors": 50, "stats": {...} }
```

- 404 Not Found
- 500 Server Error

Notes:

- For long-running scans, the route should return a Job ID and respond quickly. Consider adding `?async=true` to request.

---

## POST /index

Force re-indexing of a path into the vector store.

Body: `{ "path": "/Users/username/Photos" }`

Response: 200 OK `{ "status": "success", "indexed": 500 }`

---

## GET /search

Metadata search using the QueryEngine implementation.

Query params:

- `query`: string query, e.g., `camera=Canon AND image.width>=1920`
- `option`: reserved, defaults to metadata filter type

Response:

```
{ "count": 3, "results": [ { "path": "/path/file1.jpg", "filename": "file1.jpg", "score": 0, "metadata": {...} } ] }
```

---

## GET /search/semantic

Semantic search using text query embedding.

Query params: `query` (STRING), `limit` (INT, default 50)

Response: `200 OK` with `results` array: `{ path, filename, score (0..1), metadata }`

---

## GET /image/thumbnail

Serve a thumbnail image.

Query params: `path` (encoded file path), `size` (optional integer)

Response: Binary JPEG image data. Always set `Content-Type: image/jpeg` and `Cache-Control: public, max-age=31536000` with explicit invalidation for path replacement.

Security: Path must be strictly inside `MEDIA_DIR`. Use `abs_path = os.path.abspath(path)` then ensure `abs_path.startswith(settings.MEDIA_DIR)`.

---

## GET /stats

Return system statistics and DB summary.

Response: `{ 'active_files': 5, 'deleted_files': 0, 'total_versions': 0 }`

---

## GET /timeline

Monthly distribution for the Sonic Timeline.

Response: `{ timeline: [ { date: '2024-01', count: 25 }, ... ] }`

---

## Additional Considerations

- Authentication: Add `Authorization: Bearer <token>` header.
- Pagination: Add `limit` & `offset` for all list endpoints.
- Filtering: Add `filters` param to the metadata search for API-driven faceted searches.
- Job Management: Return `job_id` and `status` for long-running operations and a `GET /jobs/{id}` endpoint.

---

If you want, I can scaffold a `openapi.yaml` version of this spec and generate client code for the UI.

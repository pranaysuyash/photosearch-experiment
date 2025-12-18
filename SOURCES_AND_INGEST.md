# Sources + Ingest (Local Folder, Google Drive, S3)

This document describes the end-to-end “connect → ingest → browse” system for Living Museum’s **dual local + cloud** library.

## Goals

- No manual path entry for local libraries (desktop uses an OS folder picker).
- Google Drive and S3 are first-class sources.
- Connecting a cloud source immediately starts a background ingest/sync job.
- Ingest produces real, browseable results in the existing Grid/Timeline/Globe/Story experiences.

## High-level behavior

### “Source”
A Source represents an origin of media:
- `local_folder` (desktop-only picking)
- `google_drive`
- `s3` (S3-compatible providers including R2/B2/MinIO/AWS)

### Ingest strategy (v1)
For cloud sources, the server performs a **mirror-to-local** ingest:
1) Enumerate remote files/objects
2) Download media into `media_sources/<source_id>/...`
3) Run the existing metadata + semantic indexing pipeline on that mirrored folder

This is “full ingest” because it results in local files that can be served by the existing `/image/thumbnail`, `/file`, and `/video` endpoints and discovered by `/search`.

## Where data lives

- `sources.db`: sources registry (type/name/status + redacted config in API responses).
- `sources_items.db`: per-source manifest of remote items (remote id/path + etag/modified/size + local mirror path).
- `media_sources/<source_id>/...`: local mirror of cloud items (downloaded originals).

## API endpoints

### List sources
- `GET /sources` → `{ sources: Source[] }`

### Add local folder source (starts scan job)
- `POST /sources/local-folder`
  - body: `{ path, name?, force? }`
  - response: `{ source, job_id }`

### Add S3 source (validates + starts sync job)
- `POST /sources/s3`
  - body: `{ name, endpoint_url, region, bucket, prefix?, access_key_id, secret_access_key }`
  - response: `{ source, job_id? }` (`job_id` present when connection succeeds)

### Add Google Drive source (returns auth URL)
- `POST /sources/google-drive`
  - body: `{ name, client_id, client_secret }`
  - response: `{ source, auth_url }`

### Google OAuth callback (starts sync job)
- `GET /oauth/google/callback?code=...&state=...`
  - On success, connects the source and starts a `source_sync` job.
  - Posts a message back to the opener window: `{ type: 'lm:sourceConnected', sourceId, jobId }`.

### Manual sync (starts sync job)
- `POST /sources/{source_id}/sync` → `{ ok: true, job_id }`

### Rescan local folder source (starts scan job)
- `POST /sources/{source_id}/rescan` → `{ ok: true, job_id }`

### Remove a source
- `DELETE /sources/{source_id}` → `{ ok: true }`

## UI behavior (desktop/web)

### Settings → Sources
- `Settings` shows a `SourcesPanel` with:
  - Connect source modal (Local / Google Drive / S3)
  - Per-source actions:
    - Local folder: `Re-scan`
    - Cloud: `Sync`
    - All: `Remove`

### Home / First Run / Spotlight
- Home empty state: **Connect a Source** → navigates to `Settings#sources`.
- First-run modal: **Connect a Source** → navigates to `Settings#sources`.
- Spotlight command: **Scan Library** → uses folder picker (desktop) and creates a local folder source; no manual path entry.

## Provider setup

### Google Drive (OAuth)
1) Create an OAuth Client ID in Google Cloud Console.
2) Configure redirect URI:
   - `http://127.0.0.1:8000/oauth/google/callback`
3) In the UI: Settings → Sources → Google Drive → paste `client_id` + `client_secret` → Authorize.

Notes:
- Scope is read-only Drive (`drive.readonly`).
- Tokens are stored server-side in `sources.db` (redacted in API responses).

### S3-compatible
You need:
- `endpoint_url` including scheme (example for R2: `https://<account>.r2.cloudflarestorage.com`)
- `region` (R2 typically uses `auto`; AWS uses real region like `us-east-1`)
- `bucket` and optional `prefix`
- Access keys (stored server-side)

Connection validation:
- Server performs a signed ListObjectsV2 request (`max-keys=1`) to verify credentials.

## Operational notes / tradeoffs

- This “full ingest” mirror downloads originals; large libraries can take time and disk space.
- The manifest (`sources_items.db`) supports incremental sync by comparing ETag/modified/size and skipping unchanged downloads.
- Remote deletions are handled by marking missing items as deleted and removing local mirror files.

## Tests

- `server/tests/test_sources.py` covers source storage + redaction.
- `server/tests/test_source_items.py` covers manifest behavior.
- `ui/src/test/sources-ui.test.tsx` verifies we no longer expose “paste a path” UI and that Sources has a connect affordance.


# API and UI Suggestions — Toggle and Job Enhancements

This document suggests API changes to support toggles, job handling, and better UX for the UI.

## Suggested API Enhancements

1. Add `GET /jobs/{job_id}` — job status endpoint

- Returns: `{ job_id, status, progress, errors }`
- Status: queued, running, paused, completed, failed

2. Update `POST /scan` to support `async=true` return a Job ID

- When `async=true`, return `202 Accepted` with a `job_id` and start processing in the background.
- Add `estimated_items` to initial job response when the catalog has been scanned.

3. Add `GET /search` to accept `mode` parameter (metadata|semantic|hybrid)

- This mirrors the UI toggle and allows browser-to-backend consistency.
- Example: `GET /search?query=beach&mode=semantic`.

4. Add `GET /providers` and `POST /providers/test` to manage provider config from UI

- `GET /providers` — returns info about currently configured providers & capabilities
- `POST /providers/test` — attempts a simple embedding or text test and returns `ok` or `error`.

5. Add `GET /settings` and `POST /settings` to store default preferences

- Save default `search_mode` and `max_results`, and show these on the client.

6. Add `weighting` parameter for hybrid mode: `mode=hybrid&weight=0.3` (0..1)

- Controls the weight between metadata and embedding-based ranking.

## UI Suggestions

1. Toggle Control

- Segmented control near search input with `Metadata`, `Hybrid`, `Semantic`.
- Persist preference for the user (Settings) and show a short explanation text below the input.

2. Job UI

- Implement a small job tray (header or bottom drawer) showing ongoing scans and progress.
- Allow the user to pause/cancel/resume indexing.

3. Provider Management

- `Settings` > `AI Providers`: easily add a provider token; a test button is provided; show an icon and status (Connected/Disconnected).

4. Fallbacks & Messaging

- If `Semantic` fails due to model or bandwidth issues, fallback to metadata search but show a small warning with CTA: 'Use local model' or 'Retry cloud'.

5. Hybrid Weight Slider

- For users who opt-in to hybrid mode, provide a small range slider to select weight between 0-100 for semantic vs metadata and show a small example: "0% = metadata-only; 100% = semantic-only"

6. Examples / Query assistant

- Show a query assistant that transforms a natural language query into a filtered query (e.g., the assistant suggests a metadata conversion like `date>=2024-01-01` when date terms are present).

7. Heatmap / Timeline click-through

- Clicking in timeline filters the grid; show a small filter bar reflecting the current filters.

End of API & UI Suggestions

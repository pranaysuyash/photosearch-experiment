# Living Museum — Dual Local + Cloud Plan (No Mobile v1)

This document consolidates product/UX/architecture recommendations so we can execute a **dual local + cloud** media app (not “local-first”) while keeping costs low and preserving the existing glass/notch design language.

## Quickest Wins (highest impact / lowest effort)

These are the fastest changes that materially improve the “this is a complete media app” feeling *without* diluting the unique Living Museum experiences.

1) **First-run “Connect/Add Source” + visible Source/Job status**
- Replace “type a path” with a guided connect/add flow (desktop/web) and make source health + last sync/scan visible on Home/Settings.
- DoD: user can connect/add a source, see progress, and know when the library is ready—without needing docs/shortcuts.

2) **Trash/Restore + undo grace period**
- Deletion must be recoverable (app-level Trash if provider lacks it) and bulk delete must be safe.
- DoD: delete → appears in Trash → restore works; “Undo” available for a short window.

3) **Detail-view “Quick Actions” + viewer basics**
- Add the obvious actions in one place: favorite, tag/add to album, share/export, copy link/ref, open original.
- DoD: users can do common workflows from the detail modal without hunting or right-clicking; zoom/fullscreen/rotate are present.

4) **Dedicated “Curation” primitives (Albums + Tags)**
- Favorites alone isn’t enough; add Albums + Tags with bulk apply from selection mode.
- DoD: create album, add/remove assets, tag assets in bulk, filter by album/tag.

## Findings Recap (from end-user review)

This section captures the “what’s missing” findings in one place (both dual-mode fundamentals and standard media-app expectations).

### Dual-mode fundamentals (local + cloud)
- **Product promise (dual-mode)**: one library that can contain **Local Sources** (folders/devices) and **Cloud Sources** (Drive/S3/Photos/etc), with consistent browse/search/viewer UX. Local is a *source type* and an *offline cache*, not the identity of the product.
- **Unified library model**: every item needs stable IDs and a source descriptor (`local:*` vs `cloud:*`), plus a normalized metadata layer + derived assets (thumbs/embeddings) computed locally or in cloud workers.
- **Ingest + sync plan**: connect provider (auth), enumerate, incremental sync (delta tokens/webhooks), background jobs, conflict rules (duplicates/renames/deletes), and explicit UI states (syncing/offline/degraded/backfill).
- **Baseline features in our design language**: import/upload, delete/restore (trash), albums/tags/favorites, export/share, batch actions—implemented as glass surfaces + notch actions + calm feedback, not new heavy chrome.
- **Unique experiences stay unique**: globe/timeline/story become cross-source lenses (“Places across cloud+local”, “Trips as stories”, “People clusters”) with transparent provenance chips and “why this matched” explanations.

### Standard media manager gaps (ignoring search/AI)
- **Frictionless ingest/onboarding**: folder picker (not “type a path”), drag/drop import, “what’s being scanned” + progress, watch folders/incremental updates, clear “scan complete” next step.
- **Safety for destructive actions**: Trash/Recently Deleted, restore + undo grace period, and a distinction between “remove from library” vs “delete from disk/origin”.
- **Core organization**: albums/collections (and smart albums), tags/keywords, ratings, captions/notes, basic people naming + place correction (even if advanced clustering comes later).
- **Core browse surfaces/navigation**: dedicated Recents, Favorites, Videos, Albums, People, Places; grouping by date/folder with stable sorting; adjustable thumbnail size/density.
- **Viewer basics**: zoom/pan, fullscreen, rotate, slideshow, video poster + duration badges, quick actions in detail (favorite/share/export/open).
- **Sharing/export polish**: export dialog (format/size/metadata), share targets, link/copy behaviors that work across web vs desktop.
- **Trust & privacy**: backend/index health banner, last-scan time + index status, controls to hide sensitive path/GPS by default, clear provenance and data-use messaging (not “local-first” copy).
- **A11y/perf at scale**: consistent keyboard + focus behavior across all controls, virtualization/pagination for large libraries, batch APIs for per-item states (favorites, etc.).

### Highest-leverage sequence (baseline complete fast)
1) First-run Add/Connect Source (picker + status)
2) Trash/Undo
3) Albums/Tags + dedicated Favorites/Recents views
4) Viewer zoom/fullscreen/actions
5) Health + privacy/provenance controls

## Scope (v1)

**In scope**
- Desktop + web (no mobile UX commitments in v1).
- One library that can include **Local Sources** (folders/devices) and **Cloud Sources** (providers/buckets/accounts).
- Core media management (import/delete/restore/export/share, curation) + differentiated discovery (Timeline/Globe/Story) across sources.

**Explicitly out of scope (for now)**
- Mobile-specific layouts, gestures, and performance targets.
- “We host all originals” as the default (can be an upsell later).

## UX + Design Invariants (must not break)

- Use the existing design system (`ui/src/design/glass.ts`) for all new UI surfaces:
  - `glass.surface` / `glass.surfaceStrong` for containers, `btn-glass` for actions.
  - Primary command path stays **notch-centered** (DynamicNotchSearch / command palette patterns).
  - Global navigation stays **ModeRail** + **ActionsPod** (no new heavy chrome).
- Feedback stays “calm”: background jobs + small status surfaces (popover/toast), not blocking wizards.
- Never introduce a “basic CRUD dashboard” feel: baseline features should be embedded into existing surfaces.

## “Dual Local + Cloud” Product Promise (what the user believes)

- A single library that can include multiple sources:
  - **Local**: folders the user grants access to.
  - **Cloud**: accounts/buckets the user connects.
- The app provides a consistent browse/search/detail experience regardless of source.
- Availability is stateful:
  - When offline or source-unavailable, the app still opens and shows what’s cached; actions either queue or clearly explain why blocked.

## Business/Cost Strategy: Avoid Becoming a Storage Company (default)

To keep costs low and margins high, default to the **Combo** model:

### Option A — BYO Storage Only (lowest COGS, weakest UX)
- Originals stay in user storage (S3/R2/B2/Drive/etc).
- We store minimal metadata.
- Risk: inconsistent UX (provider quotas/latency), harder “works everywhere” story without hosted thumbnails.

### Option B — Managed Cloud Library (best UX, highest COGS)
- Users upload originals to us.
- Risk: storage + egress + compute costs require strict pricing and operational excellence.

### Option C — Combo (recommended)
- Originals can live in **local folders** and/or **user-connected cloud**.
- We host the **intelligence layer** (index + curation graph) and optionally **thumbnails/proxies**.
- This enables a premium product without paying for all original storage by default.

## Recommended Architecture (Combo)

### What we host (default)
- **Identity/workspaces**
- **Source registry** (which sources are connected, capabilities, health)
- **Normalized metadata** (cross-provider schema)
- **Search index** (metadata + semantic, depending on tier)
- **Curation data** (albums, tags, favorites, notes, “stories”)
- **Jobs + activity log**
- Optionally: **thumbnails/proxies** (cheap, enables fast browsing on desktop/web)

### What stays in the user’s storage
- Originals (local files, cloud object storage, provider-native originals).
- Accessed via signed URLs (cloud) or desktop file access (local desktop app).

## Core Data Model (unified across sources)

### Source
- `source_id`
- `type`: `local_folder` | `cloud_provider`
- `capabilities`: read/write/delete/trash/restore/share/link, etc (provider-dependent)
- `health`: connected / syncing / degraded / offline / auth_required

### Asset
- `asset_id` (stable, provider-agnostic)
- `source_ref` (provider object ID or local file identity)
- `content_hash` (optional; helps dedupe across sources)
- `original_ref` (how to fetch original; never assume local path in web)
- `metadata` (normalized)
- `renditions`: thumbnails/proxies with size + availability
- `derived`: embeddings/ocr/faces/etc (optional, tiered)

### Curation
- `albums` / `smart_albums`
- `tags`
- `favorites`
- `notes`
- `people` (placeholder in v1 is OK; design the schema now)

## Sync / Ingest / Conflicts (minimum “real product” rules)

### Ingest pipeline (both source types)
- Enumerate → fetch/generate thumbnails (optional) → extract metadata → index → (optional) generate embeddings.
- Always runs as a **job** with progress + retry.

### Sync semantics
- Cloud providers: delta tokens / webhooks where possible; fall back to periodic polling.
- Local folders: incremental scanning (mtime/inode/hash strategies), watch mode optional.

### Conflicts (must be explicit, not magical)
- Renames/moves: treat as “same asset moved” when source supports stable IDs; otherwise surface as potential duplicate.
- Duplicates: show as clusters (hash-based where possible) with a “keep one / archive / merge” affordance.
- Deletes: prefer **Trash** semantics when available; if provider lacks trash, use hard-delete with stronger confirmation.

## Baseline Media Features (must-haves, expressed in our language)

These are “table stakes”, but must appear as part of the Living Museum experience:

- **Sources management** (Settings → Sources): connect/disconnect, last sync, errors, pause/resume, rescan, bandwidth/cache.
- **Trash / Restore**: recoverable deletion flow + undo grace period.
- **Albums + Tags + Favorites + Notes**: curation layer (bulk apply from selection mode).
- **Share/Export**:
  - Share link (cloud-capable sources via signed URLs).
  - Export ZIP / download originals (local + cloud).
- **Viewer basics**: zoom/pan, fullscreen, rotate, slideshow; video poster + duration; quick actions (favorite/tag/share/export/open).

## Base App Gaps Checklist (what users expect before “search/AI”)

Use this as the “standard media app” completeness checklist (independent of dual local/cloud specifics):

### Ingest & Library Management
- Guided “Add Source” (no raw path entry as the primary UX).
- Source list with last scan/sync time, errors, and rescan/retry.
- Clear library readiness state (empty vs indexing vs ready).

### Browse & Navigation
- Dedicated surfaces: Recents, Favorites, Videos, Albums, Places (if GPS).
- Stable grouping/sorting (by date/folder/location), adjustable density/thumbnail size.

### Detail Viewer
- Zoom/pan + fullscreen; rotate; slideshow.
- Video poster + duration; consistent previews for non-photos (PDF/audio/SVG) or graceful fallbacks.
- Quick actions available in one obvious place.

### Curation
- Albums/collections + smart collections (later OK, but design now).
- Tags/keywords + notes/captions; ratings (optional but common expectation).
- Bulk apply/remove via selection mode.

### Safety & Trust
- Trash/restore + undo; “remove from library” vs “delete from disk/origin”.
- Health/status banner when backend/source is down; no “reload page to fix”.
- Privacy controls: path/GPS visibility defaults; clear provenance (“where is this file from?”).

### Performance & Accessibility (desktop/web)
- Virtualization/pagination for large libraries; avoid per-item API loops.
- Keyboard navigation + focus states; predictable shortcuts; accessible dialogs.

## Differentiators (signature experiences)

Keep the product “more than a basic photo app” by making these first-class lenses across all sources:

- **Timeline**: interactive filtering + “chapters” (events, trips) instead of only a graph.
- **Globe / Places**: real GPS-based clustering with transparency (“X% missing location”), and cross-source places.
- **Story mode**: deterministic “chapters” (Trips/Events/People moments) with provenance chips and “why this belongs” explanations.
- **Why matched** everywhere: grid + detail + story surfaces show provenance (metadata/semantic/hybrid) and explanations.

## Screen Plan (desktop/web)

- Home: curated sections (Recents, Trips, Places, Highlights) + quick source status.
- Search: mode + filters; result count; saved searches entry.
- Grid: selection/bulk actions + context menu actions.
- Detail: viewer + metadata + actions + explanation.
- Globe: Places lens (disabled/empty state if no GPS).
- Story: chapters + “why” chips + quick actions.
- Jobs: ingest/sync progress, retry, per-source errors.
- Settings:
  - Sources (primary)
  - Privacy/safety defaults (path/GPS visibility)
  - Performance toggles (thumb/proxy strategy)

## Phased Milestones (with Definition of Done)

### P0 — Foundations (dual-mode ready)
- Source registry exists; sources have health/status; jobs show progress.
- Web never depends on local paths; everything uses stable IDs and signed/original refs.
- Offline/degraded states are visible and non-confusing.

### P1 — Baseline “complete enough”
- Trash/restore + undo implemented.
- Albums/tags/favorites/notes implemented + bulk apply.
- Share/export flows implemented per capability matrix.

### P2 — Differentiated experiences connected to real data
- Timeline click-to-filter + chapter suggestions.
- Globe uses real indexed GPS (no “mock-only” feel).
- Story mode chapters (deterministic) with “why” explanations.

### P3 — Pro workflows (paid tier drivers)
- People naming + clustering, dedupe workflows, versioning, collaboration/shared libraries, audit trails.

## Testing Plan (what we will add before claiming a milestone)

### Backend/API
- Contract tests for: sources, jobs, ingest, delete/trash/restore, export/share.
- Sync state machine tests: connected → syncing → degraded → recover.
- Conflict tests: rename/move, duplicates, deletes across source types.

### UI (desktop/web)
- E2E (Playwright): connect source → ingest → browse → delete→restore → offline/degraded → recover.
- State coverage: loading/empty/error/offline banners for Grid/Story/Globe/Detail.
- Performance tests: large libraries (10k/100k) focusing on grid smoothness, search cancellation, and thumbnail behavior.

## Documentation Plan (what we maintain)

- Capabilities matrix per source/provider (trash, restore, share, etc).
- Sync/conflict semantics (truth table for delete/restore/rename).
- Privacy defaults (paths/GPS visibility) and how “safe mode” works.
- Operator notes (jobs, retries, common provider failures).

## Open Decisions (need answers to lock P0)

- Which cloud sources ship first (e.g., S3/R2/B2 vs Drive/Photos)?
- Do we host thumbnails/proxies by default (recommended for web), or only generate locally?
- “Trash” semantics across sources: do we enforce an app-level trash even if provider lacks one?
- How do we price compute-heavy features (embeddings/people/ocr) to preserve margins?

## Implementation Notes (v1 setup)

- **No manual path entry**: local folders are added via an OS folder picker (desktop app). The web build should focus on cloud sources.
- **Google Drive OAuth**: backend redirect URI is `http://127.0.0.1:8000/oauth/google/callback` (configure this in your Google Cloud OAuth client).
- **S3-compatible**: require `endpoint_url` with scheme (e.g., `https://<account>.r2.cloudflarestorage.com`), plus bucket + access keys; validate via a signed ListObjectsV2 call.

For implementation details and the full connect→ingest→browse flow, see `SOURCES_AND_INGEST.md:1`.

# Decision: Photo source attribution — one canonical registry join, honest content provenance

**Date:** 2026-10-21
**Status:** Accepted (engineering)
**Owner:** Pranay
**Supersedes:** the path-regex source classification in `server/api/routers/search.py` and the fabricated `ProvenanceChip`/`ProvenanceChips` pair
**Related:** `docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md` §0, §2, §3 gap 4; `docs/UI_AUDIT_FINDINGS_2026-10-20.md` §4; `docs/decisions/2026-10-21-desktop-web-platform-boundary.md`

## 1. Context

"Provenance" in this app is two different questions that were collapsed into one:

1. **Source attribution** — which library did this file come from? (Local folder, S3 bucket, Google Drive, the app's own media root.)
2. **Content provenance** — does the file carry an embedded, signed authorship manifest (C2PA)?

Neither was actually modelled. What existed instead:

- `ui/src/components/provenance/ProvenanceChip(s).tsx` — a *fabricated* client-side implementation: source name inferred from path substrings, `sourceType` from the same, hardcoded `mockSource: { name: 'Cloud Storage' }`, and dead ternaries (`sourceType === 'cloud' ? 'online' : 'online'`, `isCloudPath ? 'up_to_date' : 'up_to_date'`). Never mounted; kept only as a "design reference for the future photo→source backend" (`UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md` §0, §3 gap 4).
- `server/api/routers/search.py` — a **live** `source_filter=local|cloud|hybrid` implemented by regex over the path string (`is_cloud_path` / `is_local_path`).
- `server/api/routers/browse.py` — accepts `source_filter` and **silently ignores it**.

The live heuristic is not merely inelegant, it is wrong for this app's data model: cloud sources are *synced to local copies* under `media_sources/<source_id>/`, so a synced Google Drive photo has an absolute local path and the regex classifies it as "local". Every cloud-origin photo in the app is mislabelled.

Meanwhile the registry that already holds the truth is unused for attribution:

- `server/sources.py` → `SourceStore`: real source records (`id`, `type`, `name`, `status`, `last_sync_at`, config with the local root path).
- `server/source_items.py` → `SourceItemStore.find_by_local_path(local_path)` (line 188): a reverse index from a media file's local path to its `source_id`, `remote_id`, `status`.

So the truth exists; it was simply never joined to the photo payloads.

## 2. Decision

**One canonical attribution model, derived server-side from the source registry, exposed to clients as a first-class field. No client-side inference, ever.**

### 2.1 Two entities, not one

| | Source attribution | Content provenance |
|---|---|---|
| Answers | which library is this file from | does the file carry a signed authorship manifest |
| Lives in | the source registry (`SourceStore` + `SourceItemStore`) | inside the file (C2PA / JUMBF / XMP) |
| Verification | n/a (the registry *is* the record) | requires a C2PA SDK we do not have |
| This decision | **implemented** | **detection only, never verification claims** |

Content provenance is reported as *presence of a manifest marker* with `verified: false` and an explicit note that no verifier ran. Claiming validity without a verifier would be a fabricated guarantee — the exact failure mode the deprecated chips were deleted for.

### 2.2 The attribution record

```
PhotoAttribution
  origin        'source' | 'media_root' | 'unattributed'
  kind          'local'  | 'cloud'   | 'unknown'      # filter semantics
  match         'source_item' | 'source_root' | 'media_root' | 'none'
  source_id     str | None
  source_type   'local_folder' | 's3' | 'google_drive' | None
  source_name   str | None
  source_status str | None      # pending | connected | auth_required | error
  last_sync_at  str | None
  item_status   str | None      # active | deleted | trashed | removed
  remote_id     str | None
  content       ContentProvenance | None   # only when explicitly requested
```

`kind` is derived from `source_type`, not from the path:
- `local_folder` → `local`
- `s3`, `google_drive` → `cloud` (the *origin* is cloud even though the copy is local — that is the fact the user cares about)
- the app's own media root → `local`
- otherwise → `unknown`

### 2.3 Resolution precedence (most authoritative first)

1. **`source_item`** — exact `local_path` match in `SourceItemStore` (realpath-normalised fallback). Covers synced S3 / Google Drive items, which record their local copy path.
2. **`source_root`** — path under a registered `local_folder` source's configured root (longest matching root wins). Local folders are scanned in place and never write `source_items` rows, so root matching is the only real way to attribute them.
3. **`media_root`** — path under `settings.MEDIA_DIR`, the app's own library.
4. **`none`** — unattributed: `kind='unknown'`, honestly reported.

### 2.4 API contract

- `GET /attribution?path=<abs path>[&include_content=true]` → single record.
- `GET /attribution/batch?path=…&path=…` → `{ "attributions": { path: record } }`, one SQL `IN` query per chunk.
- List payloads (`/browse`, `/search`) gain an `attribution` key on every item.

`attribution` is the key name — **not** `source`. `search.py` already uses `source` for the *search leg* that matched (`'both' | 'metadata' | 'semantic'`), an unrelated meaning that must not be overloaded.

`include_content` is opt-in and off by default: content detection touches the filesystem, and a 50-item page must not pay for 50 file scans. The `content` block is only attached when asked for.

### 2.5 Filter semantics

`source_filter` keeps its existing parameter and values, with one honest correction:

| value | old meaning (path regex) | new meaning (registry) |
|---|---|---|
| `local` | path looks absolute | attributed to a local folder or the media root |
| `cloud` | path starts with `s3://`, `https://`, … | attributed to an S3 or Google Drive source |
| `hybrid` | path matched neither regex (i.e. *unknown*) | alias of `unknown` — kept for compatibility |
| `unknown` | not accepted | unattributed files |

`hybrid` was already a synonym for "unclassifiable"; it is now explicitly that, and `unknown` is accepted as the canonical spelling. `/browse` now actually applies the filter instead of ignoring it.

## 3. Alternatives rejected

| Option | Why rejected |
|---|---|
| Keep the client-side chip and feed it a new endpoint | The chip's data contract (`status: 'online'`, `syncStatus: 'up_to_date'`, source name from a path substring) does not correspond to any real fact. It would have to be rewritten anyway, and the rewrite is the implementation. |
| Keep the path regex, only fix the cloud-URL case | The regex cannot express "this local file is a synced Google Drive item" — that fact lives in the registry, not the path. |
| Build a full C2PA verifier now | No SDK, no signature-chain validation, no trust list. A half-verifier that reports "signed" without checking the chain is worse than honest absence. Detection now, verification when a verifier exists. |
| Expose `SourceStore` records verbatim to the UI | Leaks source `config` (S3 credentials paths, OAuth client hints) into photo payloads and couples the photo contract to the connection contract. Attribution is a projection, not the registry row. |
| Delete the chips, do nothing else | Deletes the symptom. The live filter stays wrong and the app still cannot answer "where did this come from". |

## 4. Consequences

- `docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md` §3 gap 4 splits: source attribution **resolved**; content provenance **open by design** (detection only, verification needs a C2PA SDK).
- The deprecated `ProvenanceChips.tsx` is superseded by a real `ProvenanceChip.tsx` and deleted; `ProvenanceChip.tsx` loses its `@deprecated` header.
- `source_filter` becomes truthful: cloud-origin photos are finally reachable by a filter that previously could not match them.
- Photos from sources that were never registered are reported as `unattributed` instead of being silently labelled "local".

## 5. Non-goals

- No C2PA signature validation, trust-list evaluation, or claim extraction.
- No retroactive `source_items` rows for local-folder scans (root matching covers them; a per-file row would duplicate the filesystem).
- No per-source quota, sync scheduling, or credential management (that is `SourcesPanel`'s existing surface).

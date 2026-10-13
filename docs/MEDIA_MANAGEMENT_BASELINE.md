# Media Management Baseline (What’s Now Covered)

This app now covers the “baseline” expectations of a media library (browse, curate, safe delete), while keeping the existing glass/notch design language and treating Local + Cloud as first-class source types.

## Browse Surfaces

- **Recents**: `Home` (`/`) using the existing grid experience.
- **Favorites**: dedicated lens (`/favorites`).
- **Videos**: dedicated lens (`/videos`).
- **Albums**: dedicated page (`/albums`) backed by server-side albums + smart albums.
- **Trash (Recently Deleted)**: dedicated page (`/trash`) for restore/permanent delete.
- **Places**: `Globe` (`/globe`) as a cross-source lens.

## Curation

- **Albums**: create/update/delete; add/remove photos; smart albums refresh.
- **Tags**: create/delete; add/remove photos; list tags with counts; fetch tags for a photo.

## Safe Delete Semantics (Local + Cloud)

### Move to Trash (default “Delete” UX)

- UI default: grid selection “Trash” and viewer “Trash”.
- Backend: moves the file into app-managed `trash_files/…` and removes it from the active search/index.
- For **cloud sources (Drive/S3 mirrors)**: this affects the mirrored local copy only; remote originals are not deleted.
- Restore reindexes the file back into the library.

### Remove from Library (no Trash)

- Viewer includes “Remove”.
- Backend removes the item from the library index without moving it to Trash.
- For **cloud sources** this also marks the source item as `removed` so it will not re-download on sync.
- For **local files**, this is an index-only removal (the file stays on disk and may reappear on re-scan).

## API Notes

- Search:
  - `GET /search` supports `tag=<name>` to filter results to a single tag (exposed via Filters → Tags and the active `#tag` chip).
- Trash:
  - `POST /trash/move`
  - `GET /trash`
  - `POST /trash/restore`
  - `POST /trash/empty`
- Remove from library:
  - `POST /library/remove`
- Tags:
  - `GET /tags`, `POST /tags`, `DELETE /tags/{tag_name}`
  - `POST /tags/{tag_name}/photos`, `DELETE /tags/{tag_name}/photos`
  - `GET /photos/{path}/tags`

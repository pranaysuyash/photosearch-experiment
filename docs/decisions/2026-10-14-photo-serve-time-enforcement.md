# Decision record: serve-time photo privacy enforcement — 2026-10-14

## Context

The `/privacy/*` routes landed earlier today gate access *metadata*, but photo
*bytes* were still served by `/image/thumbnail` and `/file` without consulting
privacy controls — a private photo remained fetchable by anyone with the path.
This closes that gap: the named next step of the same-day privacy-route decision
(`docs/decisions/2026-10-14-photo-privacy-route.md`).

## Policy (and why)

- **No control record → default-open.** `check_access_permission` returns False
  when no control exists (explicit-allow storage semantics), but serve-time must
  be default-open or every pre-controls photo would 403 for its owner. The
  default-open decision lives in the enforcement layer
  (`server/privacy_enforcement.py`), not the storage layer.
- **Control exists → `check_access_permission` governs** (owner, public, or
  allowed users/groups).
- **Identity:** `X-User-ID` header, default `default_user` — the same convention
  as the privacy router's consent endpoints. The UI panel does not yet send a
  divergent identity (verified: it only types `owner_id`, never calls
  `setPhotoPrivacy`), so local flows are unaffected.
- **Key normalization:** controls may be keyed by raw or resolved paths; the
  enforcer tries the raw string, resolved path, and MEDIA_DIR-relative forms.
- **Ordering:** the check runs after sandbox validation and before the
  file-existence check, so a denied photo 403s without revealing whether the
  bytes exist.

## Wiring

`server/privacy_enforcement.py` (policy module, raises `PhotoAccessDenied`)
called from `server/api/routers/images.py::get_thumbnail` (covers both the
`path` param and signed-token flows — a token minted before a lockout cannot
leak bytes) and `server/api/routers/file.py::get_file`. Denials are logged with
hashed paths.

## Tests

`tests/test_photo_privacy_enforcement.py`: six integration tests — default-open,
stranger-403/owner-200, friends_only allowed user, 403-before-404 ordering,
`/file` enforcement, and default identity without a header. Full suite:
**443 passed / 0 failed**.

## Falsifier

A control record whose owner cannot fetch their own photo, or a stranger
fetching a controlled photo through any serving endpoint, invalidates this
record.

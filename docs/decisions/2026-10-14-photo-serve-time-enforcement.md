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

## Update (same day): UI identity wiring + the build repair it surfaced

- **Identity plumbing (frontend):** `ui/src/api.ts` gains `getCurrentUserId` /
  `setCurrentUserId` (localStorage, default `default_user`), an axios request
  interceptor setting `X-User-ID` on every API call, and `user_id` params on all
  five `<img>`-targeted thumbnail URL builders (img tags cannot send headers).
- **Server accepts the query param:** enforcement identity resolution is now
  header → `user_id` query param → default.
- **PUT creates on first save:** `/privacy/control` PUT now upserts when no
  control exists, owned by the requester identity — the panel's first save on an
  uncontrolled photo used to 404, and a created control is owned by the same
  identity serve-time enforcement evaluates.
- **Latent frontend bugs fixed (found because the toolchain finally worked):**
  restoring `npm install` + the real TS build exposed that `VideoHighlights.tsx`
  and `Events.tsx` read `response.data.X` from the *unwrapping* api wrapper —
  always `undefined`, so highlights and events silently rendered empty. Payload
  accesses fixed against the verified backend shapes; missing `glass.light` /
  `glass.border` design tokens added (additive CSS) so the project builds.

Validation: frontend `npm run build` green; python full suite **445 passed / 0
failed**; enforcement tests extended to 8 (query-param identity, PUT-upsert
ownership). Falsifier unchanged, plus: a highlights/events panel that renders
empty against a populated library would invalidate the double-`.data` diagnosis.

## Correction (2026-10-14, supersession review): the double-`.data` mechanism was an error state, not silent emptiness

Operator-directed supersession review of the `response.data` fix (§6) against the
doctrine produced one correction to this record and one confirmation:

- **Correction (§2/§14):** this record said highlights/events "silently rendered
  empty." The actual pre-fix mechanism: `response` was the unwrapped payload, so
  `response.data` was `undefined` and `response.data.highlights` **threw
  TypeError**, caught by the components' catch blocks, which surfaced
  `err.message` (raw "Cannot read properties of undefined…" text) as the error
  state. Symptom: visible error messages, not a silent empty panel. The
  original falsifier was aimed at that wrong symptom and is replaced by: a
  highlights/events panel showing a raw "Cannot read properties of undefined"
  message against a populated library indicates the diagnosis class.
- **Supersession verdict (§6):** the wrapper's unwrapping (`return res.data`,
  `ui/src/api.ts`) is the canonical contract, not a defect to supersede —
  introduced 2025-12-07 (`62d4faf`), predating the two components
  (`43e7baa`, 2025-12-29) by three weeks, with ~116 of 118 api call sites
  conforming. The components were born violating an established contract and
  never worked at any intermediate commit; fixing the consumers (done in
  `8154b42`) was the §6-compliant integration into the canonical target.
  Superseding the wrapper instead would churn ~116 call sites for zero user
  value (§1 would-completing-help test: dissolves). Same-bug-class sweep of all
  remaining consumers: clean (`SonicTimeline.tsx` receives its data as a prop
  from deliberate nested unwraps at `ui/src/api.ts` lines 809/2663).

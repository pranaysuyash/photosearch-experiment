# Decision record: implementing the /privacy/* per-photo control routes — 2026-10-14

## Context

The UI privacy panel (`ui/src/components/privacy/PrivacyControls.tsx`, nine calls in
`ui/src/api.ts`) has been calling `/privacy/*` endpoints that no router served — the
surface 404'd end to end. Meanwhile the data layer (`server/privacy_controls_db.py`,
`PrivacyControlsDB`) shipped complete: nine methods mapping one-to-one to the nine
frontend calls, backed by the `privacy_controls` table (photo_path, owner_id,
visibility, share_permissions, encryption_enabled, encryption_key_hash,
allowed_users, allowed_groups). The original integration tests asserted exactly this
contract. Treating them as "stale" was wrong; they specified a half-built feature —
data layer done, route layer missing.

## Change

Nine routes added to the canonical privacy router (`server/api/routers/privacy.py`),
paths matching the frontend exactly (no `/api` prefix — the client's API_BASE points
at the server root):

POST/GET/PUT `/privacy/control/{photo_path}` (set / get / update),
GET `/privacy/visible/{visibility}/{owner_id}`, GET `/privacy/access/{user_id}`,
GET `/privacy/check-access/{photo_path}/{user_id}`, GET `/privacy/encrypted/{owner_id}`,
GET `/privacy/stats/{owner_id}`, DELETE `/privacy/revoke-access/{photo_path}/{user_id}`.

All backed by `PrivacyControlsDB` on the same `privacy.db` as consent records.
Validation errors map to 400/404; failures to 500 with audit logging via the
existing `log_privacy_request` where a request context exists.

**Privacy note:** these controls gate access metadata only; photo bytes are not
served through these routes. Serve-time enforcement in the image path remains the
next integration step and is deliberately out of this change's scope.

## Tests

The original test intents were restored as real tests (no skips):
`test_photo_privacy_control_round_trip` (set → get → update → check-access
owner-true/stranger-false) and `test_encryption_integration_with_sharing`
(encrypted control → share link → encrypted listing → stats). Full suite:
437 passed / 0 failed.

## Falsifier

A frontend call shape that 404s or mis-shapes against these routes, or a
check-access answer contradicting the stored control, invalidates this record.

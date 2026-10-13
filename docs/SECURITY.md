# Security & Deployment Guidance

This document describes recommended defaults and controls for hybrid (local + cloud) deployments of PhotoSearch.

## Key configuration

- `SANDBOX_STRICT` (bool): when true, the server enforces strict MEDIA_DIR-only file access. Default: true in production.
- `SIGNED_URL_ENABLED` (bool): enable signed/ephemeral URLs for public deployments. Default: false in dev; typically true in production.
- `SIGNED_URL_SECRET` (string): HMAC secret used to sign/verify tokens. Must be set in production.
- `SIGNED_URL_TTL_SECONDS` (int): default token TTL (seconds). Default: 300.
- `IMAGE_TOKEN_ISSUER_KEY` (string): simple API key for issuing tokens in smaller deployments (recommended to use proper auth in the cloud).
- `ACCESS_LOG_SALT` (string): HMAC salt used to hash file paths in logs. Set in production.
- `ACCESS_LOG_MASKING` (bool): whether to mask file paths in logs (recommended True).
- `KEY_ROTATION` (kid-based): use a key ring with `active`, `previous`, `next` secrets; embed `kid` in issued tokens so verifiers choose the right key. Rotate automatically (e.g., weekly) and keep the previous key for a grace window (e.g., 48h) to avoid breaking in-flight tokens.

## Image access flows

- Client helper: `api.getSignedImageUrl(path, size, ttl)` is available in the UI to request a token and build a signed thumbnail URL (requires server token issuance to be available and auth to be configured).
- The UI exposes a `ServerConfigPanel` (Settings → Sync & Security) which displays whether signed URLs are enabled, lets users prefer signed images, and provides inputs for a dev issuer API key or Bearer JWT for testing token issuance.

### Auth & Admin Unmask

- **JWT Auth**: For cloud deployments, enable `JWT_AUTH_ENABLED=true` and set `JWT_SECRET` + `JWT_ISSUER`. The server supports minimal HS256 JWT verification for issuing image tokens; for production prefer integrating OIDC/OAuth and short-lived access tokens.
- **Admin Unmask**: To support debugging while keeping logs privacy-preserving, enable `ACCESS_LOG_UNMASK_ENABLED=true` for an audited admin unmask endpoint (`POST /admin/unmask`). This endpoint requires admin JWT (payload claim `is_admin=true`) or the `IMAGE_TOKEN_ISSUER_KEY` and will scan `MEDIA_DIR` to locate the original path for a given hashed value. Use with care and ensure audit logs are enabled.
- **Rate limiting**: Enable `RATE_LIMIT_ENABLED` to prevent abuse of image serving endpoints; tune `RATE_LIMIT_REQS_PER_MIN` based on expected traffic.

1. Local-only (Tauri / Desktop)

   - Local client may use the `path` query param to fetch thumbnails (loopback only).
   - Signed URLs generally not required; `SANDBOX_STRICT` should still be enabled to prevent accidental exposure.

2. Public / Cloud
   - Use `POST /image/token` to request a short-lived token for a given path (requires proper auth or `IMAGE_TOKEN_ISSUER_KEY`).
   - Use `GET /image/thumbnail?token=<token>` to fetch thumbnails using token-based auth.
   - Tokens are HMAC-SHA256 signed payloads with expiry and scope.
   - Key rotation: include `kid` in tokens; server keeps a small key ring. Rotate on a schedule and remove expired keys after the grace period. Document the rotation cadence in ops runbooks.

## Logging and developer access

- By default file paths in access logs are hashed with `ACCESS_LOG_SALT`. This provides privacy while enabling correlation.
- For ops/debug, provide a guarded admin flow to unmask hashes (recommend storing a secure encrypted mapping or providing an audited admin endpoint).
- In development, you can disable masking to ease debugging (set `ACCESS_LOG_MASKING=false`).

## Tests

- Unit tests validate token creation/validation and sandbox enforcement (`tests/test_signed_token.py`, `tests/test_image_security.py`, `tests/test_image_token_endpoint.py`).
- Rate-limiting tests (`tests/test_rate_limit.py`) ensure the server responds with 429 when limits are exceeded.
- Admin unmask endpoint tests (`tests/test_admin_unmask.py`) ensure only admins can unmask hashed paths and that the operation is auditable.

## Next steps / production checklist

- Set `SIGNED_URL_SECRET` and `ACCESS_LOG_SALT` in environment (never check into source control).
- Ensure `SIGNED_URL_ENABLED` is set to true in production and `SANDBOX_STRICT=true`.
- Integrate with your auth provider; restrict `/image/token` to authenticated, authorized users only.
- Consider integrating S3 presigned URLs for high-volume serving and caching.

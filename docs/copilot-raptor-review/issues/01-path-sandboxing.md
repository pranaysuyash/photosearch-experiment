# Issue: Path Sandboxing & Secure Image Serving

## Description

Ensure `GET /image/thumbnail` (and any API that exposes file paths) strictly serves files only from the configured media root (`settings.MEDIA_DIR`) and prevents path traversal or symlink-based attacks.

## Why

Safety and security: A malicious crafted request could leak arbitrary files via path traversal or symlink resolution, potentially exposing sensitive system files.

## Acceptance Criteria

- [ ] `GET /image/thumbnail` uses `pathlib.Path.resolve()` and only serves files under `settings.MEDIA_DIR`.
- [ ] The endpoint rejects requests not in the media directory with `403 Forbidden` and logs the attempt.
- [ ] Unit tests verifying attempts to access paths outside the allowed root (../../, symlinks) are rejected.
- [ ] Add docs in `README` about `MEDIA_DIR` location and how to configure it.

## Implementation Notes

- Use `abs_path = Path(path).resolve()` and `abs_path.startswith(settings.MEDIA_DIR.resolve())`.
- Add explicit error messaging and avoid leaking full system paths in error logs.
- Add a small integration test using `TestClient` to verify behavior.

## Estimate

0.5 - 1 day

## Labels

security, bug, server

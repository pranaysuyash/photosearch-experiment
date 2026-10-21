# Evidence: web companion at /app + principal gate + pairing (2026-10-21)

| File | Shows |
|---|---|
| `before-app-route.png` | Old backend (pre-`ui_static`): `GET /app/` → 307→405. The root-level `DELETE /{video_id}` route matched and answered 405 — the routing hazard surfaced by this work. |
| `after-app-home.png` | Same server after the change: `/app/` renders the full shell + FirstRunModal; all API calls same-origin to `127.0.0.1:8000` (network log shows `/api/actions/detect-apps` 200 — that call was dead outside the Vite dev proxy before). |
| `settings-devices-pairing-code.png` | Settings → Devices on the primary device: "This is the primary device (loopback)", a live 4-digit code, the LAN URL `http://x.x.x.x:PORT/app/pair`, single-use / 5-min TTL. **Redacted for publication**: the LAN address and the code digits are replaced (`x.x.x.x`, `• • • •`) — the repo is public. The capture was re-taken from the running app with the redaction applied to the DOM, so it is a genuine screenshot, not a pixel-patched one; the code it shows was single-use and the pairing secret has since been rotated. |
| `pair-page-loopback.png` | `/app/pair` from a loopback browser: correctly reports already-connected (owner) instead of showing the code form. |

Conditions: live backend on `127.0.0.1:8000` (HOST default now loopback),
principal gate + pairing + rate limit active, web bundle rebuilt with the
pairing UI and relative manifest paths.

Companion server-side proofs (not screenshotted): principal matrix and
pairing lifecycle in `tests/test_principal_gate.py` (S2: LAN peer 401 →
paired 200 → replayed code 400 → revoked 401), run with a simulated
non-loopback TestClient peer.

"""Principal gate + pairing lifecycle (server/principal.py, routers/pairing.py).

The headline assertion is S2: a simulated LAN peer is refused BEFORE pairing
and admitted AFTER it, so the test fails for a real reason if the gate or the
mint/verify chain breaks — not just because statuses changed.
"""

import os

import pytest
from fastapi.testclient import TestClient

# The gate treats TestClient's default peer as loopback only under test-mode
# markers; make that explicit here rather than inheriting ambient state.
os.environ.setdefault("PHOTOSEARCH_TEST_MODE", "1")

from server.main import app  # noqa: E402  (needs the env above set first)
from server.principal import (  # noqa: E402
    issue_session_token,
    rotate_session_secret,
    verify_session_token,
)

LAN_PEER = {"client": ("10.0.0.5", 12345)}


@pytest.fixture()
def owner():
    return TestClient(app)


@pytest.fixture()
def stranger():
    return TestClient(app, client=LAN_PEER["client"])


def _paired_stranger(code: str) -> TestClient:
    client = TestClient(app, client=LAN_PEER["client"])
    response = client.post("/pair/complete", json={"code": code})
    assert response.status_code == 200, response.text
    assert "ps_session" in response.cookies
    return client


# ── resolution matrix ────────────────────────────────────────────────────────


def test_loopback_is_the_owner_without_ceremony(owner: TestClient):
    response = owner.get("/pair/status")
    assert response.status_code == 200
    body = response.json()
    assert body["paired"] is True
    assert body["via"] == "loopback"
    assert body["user_id"] == "default_user"


def test_unpaired_lan_peer_is_401_on_api_routes(stranger: TestClient):
    assert stranger.get("/stats").status_code == 401
    assert stranger.get("/browse").status_code == 401


def test_exempt_paths_open_to_everyone(stranger: TestClient):
    assert stranger.get("/health").status_code == 200
    # /app is exempt from the gate. Whether the SPA bundle is actually mounted
    # depends on the build — the CI backend job runs the suite without
    # building the UI — so assert what the gate promises (the path is not
    # refused with 401) rather than what the bundle provides. Serving the
    # bundle itself is covered by tests/test_ui_static.py.
    assert stranger.get("/app/").status_code != 401
    status = stranger.get("/pair/status").json()
    assert status["paired"] is False


def test_stranger_cannot_start_pairing(stranger: TestClient):
    assert stranger.post("/pair/start").status_code == 403


def test_bearer_token_grants_access_without_cookie(stranger: TestClient):
    token = issue_session_token()
    response = stranger.get("/stats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_invalid_or_stale_tokens_are_rejected(stranger: TestClient):
    for bad in ("", "not.a.token", issue_session_token()[:-2] + "xx"):
        headers = {"Authorization": f"Bearer {bad}"} if bad else {}
        response = stranger.get(
            "/stats", headers={**headers, "Authorization": "Bearer garbage"} if not bad else headers
        )
        assert response.status_code == 401


def test_identity_prefer_principal_over_spoofable_header(owner: TestClient):
    """X-User-ID was client-asserted; the principal must win when resolved."""
    response = owner.get("/pair/status", headers={"X-User-ID": "someone-else"})
    assert response.json()["user_id"] == "default_user"


# ── pairing lifecycle (S2) ───────────────────────────────────────────────────


def test_pairing_lifecycle_refuse_pair_admit_revoke(owner: TestClient):
    # Before pairing: the LAN peer is refused (the S2 baseline).
    stranger = TestClient(app, client=LAN_PEER["client"])
    assert stranger.get("/stats").status_code == 401

    # Owner starts pairing; the LAN peer completes it with the code.
    start = owner.post("/pair/start")
    assert start.status_code == 200
    code = start.json()["code"]

    paired = _paired_stranger(code)
    assert paired.get("/stats").status_code == 200
    assert paired.get("/pair/status").json()["via"] == "cookie"

    # Codes are single-use: a second device cannot replay it.
    assert TestClient(app, client=LAN_PEER["client"]).post("/pair/complete", json={"code": code}).status_code == 400

    # Owner revokes: every paired device is out again.
    assert owner.post("/pair/revoke").status_code == 200
    assert paired.get("/stats").status_code == 401
    assert stranger.get("/stats").status_code == 401


def test_wrong_or_expired_code_is_rejected(owner: TestClient):
    response = TestClient(app, client=LAN_PEER["client"]).post("/pair/complete", json={"code": "9999"})
    assert response.status_code == 400


def test_rotate_invalidates_even_valid_tokens():
    token = issue_session_token()
    assert verify_session_token(token) is not None
    rotate_session_secret()
    assert verify_session_token(token) is None
    fresh = issue_session_token()
    assert verify_session_token(fresh) is not None

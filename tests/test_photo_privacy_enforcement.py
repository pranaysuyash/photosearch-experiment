"""Serve-time photo privacy enforcement tests.

Proves the contract of server/privacy_enforcement.py wired into
/image/thumbnail and /file:

- a photo with no privacy control record stays default-open for anyone
- a private control denies a stranger (403) but allows the owner
- a friends_only control allows listed users
- the gate runs before file-existence checks (403 wins over 404)

Identity comes from the principal gate (server/principal.py), not from a
spoofable header: a loopback caller is the owner, and a caller presenting a
session token is that token's subject. The X-User-ID header and the
?user_id= query param survive only as a fallback for requests that resolved
no principal — that fallback is covered directly at the end of this file
rather than through the gated API, where a principal is always resolved.
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# The gate treats TestClient's default peer as loopback only under test-mode
# markers; make that explicit here rather than inheriting ambient state.
os.environ.setdefault("PHOTOSEARCH_TEST_MODE", "1")

from server.config import settings  # noqa: E402  (needs the env above set first)
from server.main import app  # noqa: E402
from server.privacy_controls_db import PrivacyControlsDB  # noqa: E402
from server.privacy_enforcement import user_id_from_request  # noqa: E402
from server.principal import issue_session_token  # noqa: E402

# A non-loopback peer: the gate only consults a session token for a caller
# that is not the loopback owner.
LAN_PEER = ("10.0.0.5", 12345)

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c626001000000ffff030000060005"
    "57bfabd40000000049454e44ae426082"
)


def _as(user_id: str) -> TestClient:
    """A caller whose principal is `user_id` — a token subject, not a header."""
    client = TestClient(app, client=LAN_PEER)
    client.headers.update({"Authorization": f"Bearer {issue_session_token(user_id)}"})
    return client


def _as_cookie(user_id: str) -> TestClient:
    """A caller carrying the session cookie — what an <img> request sends."""
    client = TestClient(app, client=LAN_PEER)
    client.cookies.set(settings.SESSION_COOKIE_NAME, issue_session_token(user_id))
    return client


@pytest.fixture
def isolated_media_and_privacy(monkeypatch):
    """Point MEDIA_DIR and the privacy db at an isolated tempdir."""
    with tempfile.TemporaryDirectory() as td:
        media_dir = Path(td) / "media"
        media_dir.mkdir()
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)
        monkeypatch.setattr(settings, "FACE_CLUSTERS_DB_PATH", str(Path(td) / "face_clusters.db"))
        monkeypatch.setattr(settings, "SANDBOX_STRICT", False)
        yield media_dir, Path(td) / "privacy.db"


def _make_photo(media_dir: Path, name: str) -> Path:
    photo = media_dir / name
    photo.write_bytes(PNG_1PX)
    return photo


def _set_private_control(privacy_db: Path, photo: Path, owner: str, visibility: str = "private", allowed=None):
    PrivacyControlsDB(privacy_db).set_photo_privacy(
        photo_path=str(photo),
        owner_id=owner,
        visibility=visibility,
        allowed_users=allowed or [],
    )


def test_no_control_record_is_default_open(isolated_media_and_privacy):
    media_dir, _ = isolated_media_and_privacy
    photo = _make_photo(media_dir, "uncontrolled.png")
    response = _as("anyone").get(f"/image/thumbnail?path={photo}")
    assert response.status_code == 200


def test_private_control_denies_stranger_allows_owner(isolated_media_and_privacy):
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "family_photo.png")
    _set_private_control(privacy_db, photo, owner="alice")

    stranger = _as("stranger").get(f"/image/thumbnail?path={photo}")
    assert stranger.status_code == 403
    assert "privacy controls" in stranger.json()["detail"]

    owner = _as("alice").get(f"/image/thumbnail?path={photo}")
    assert owner.status_code == 200


def test_friends_only_allows_listed_user(isolated_media_and_privacy):
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "shared_photo.png")
    _set_private_control(privacy_db, photo, owner="alice", visibility="friends_only", allowed=["bob"])

    assert _as("bob").get(f"/image/thumbnail?path={photo}").status_code == 200
    assert _as("bob").get(f"/privacy/check-access/{photo}/carol").json()["has_access"] is False


def test_enforcement_precedes_file_existence(isolated_media_and_privacy):
    """A denied photo must not reveal existence: 403 even if bytes are absent."""
    _, privacy_db = isolated_media_and_privacy
    ghost = "/nonexistent_media_dir/ghost.png"
    _set_private_control(privacy_db, Path(ghost), owner="alice")
    response = _as("stranger").get(f"/image/thumbnail?path={ghost}")
    assert response.status_code == 403


def test_file_endpoint_enforces(isolated_media_and_privacy):
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "original.png")
    _set_private_control(privacy_db, photo, owner="alice")

    assert _as("stranger").get(f"/file?path={photo}").status_code == 403
    assert _as("alice").get(f"/file?path={photo}").status_code == 200


def test_default_identity_without_header(isolated_media_and_privacy):
    """A loopback caller with no token is the owner (default_user)."""
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "local.png")
    _set_private_control(privacy_db, photo, owner="default_user")

    assert TestClient(app).get(f"/image/thumbnail?path={photo}").status_code == 200


def test_cookie_identity_for_img_tags(isolated_media_and_privacy):
    """<img src> cannot send headers, but it does send the session cookie."""
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "headerless.png")
    _set_private_control(privacy_db, photo, owner="alice")

    stranger = _as_cookie("stranger").get(f"/image/thumbnail?path={photo}")
    assert stranger.status_code == 403

    owner = _as_cookie("alice").get(f"/image/thumbnail?path={photo}")
    assert owner.status_code == 200


def test_put_upsert_owns_control_for_requester(isolated_media_and_privacy):
    """Panel first-save on an uncontrolled photo creates a control owned by
    the requester identity, so serve-time enforcement allows the same user."""
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "panel_first_save.png")

    put_response = _as("panel_user").put(
        f"/privacy/control/{photo}",
        json={"visibility": "friends_only", "allowed_users": ["alice"]},
    )
    assert put_response.status_code == 200
    assert put_response.json()["privacy"]["visibility"] == "friends_only"
    assert put_response.json()["privacy"]["owner_id"] == "panel_user"

    # The authored control now governs bytes: the authoring identity gets
    # served, strangers do not.
    assert _as("panel_user").get(f"/image/thumbnail?path={photo}").status_code == 200
    assert _as("alice").get(f"/image/thumbnail?path={photo}").status_code == 200


def test_identity_fallback_without_principal():
    """With no principal resolved, the header wins, then the query param.

    This is the path that serves direct handler calls and exempt routes; the
    gated API always resolves a principal, so it is asserted here rather than
    through a request that would carry one.
    """

    class _Request:
        def __init__(self, headers=None, query=None):
            self.headers = headers or {}
            self.query_params = query or {}

    assert user_id_from_request(_Request(headers={"X-User-ID": "alice"})) == "alice"
    assert user_id_from_request(_Request(query={"user_id": "bob"})) == "bob"
    assert user_id_from_request(_Request()) == "default_user"

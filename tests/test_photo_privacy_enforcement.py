"""Serve-time photo privacy enforcement tests.

Proves the contract of server/privacy_enforcement.py wired into
/image/thumbnail and /file:

- a photo with no privacy control record stays default-open for anyone
- a private control denies a stranger (403) but allows the owner
- a friends_only control allows listed users
- the gate runs before file-existence checks (403 wins over 404)
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.config import settings
from server.main import app
from server.privacy_controls_db import PrivacyControlsDB

client = TestClient(app)

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c626001000000ffff030000060005"
    "57bfabd40000000049454e44ae426082"
)


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
    response = client.get(f"/image/thumbnail?path={photo}", headers={"X-User-ID": "anyone"})
    assert response.status_code == 200


def test_private_control_denies_stranger_allows_owner(isolated_media_and_privacy):
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "family_photo.png")
    _set_private_control(privacy_db, photo, owner="alice")

    stranger = client.get(f"/image/thumbnail?path={photo}", headers={"X-User-ID": "stranger"})
    assert stranger.status_code == 403
    assert "privacy controls" in stranger.json()["detail"]

    owner = client.get(f"/image/thumbnail?path={photo}", headers={"X-User-ID": "alice"})
    assert owner.status_code == 200


def test_friends_only_allows_listed_user(isolated_media_and_privacy):
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "shared_photo.png")
    _set_private_control(privacy_db, photo, owner="alice", visibility="friends_only", allowed=["bob"])

    assert client.get(f"/image/thumbnail?path={photo}", headers={"X-User-ID": "bob"}).status_code == 200
    assert client.get(f"/privacy/check-access/{photo}/carol").json()["has_access"] is False


def test_enforcement_precedes_file_existence(isolated_media_and_privacy):
    """A denied photo must not reveal existence: 403 even if bytes are absent."""
    _, privacy_db = isolated_media_and_privacy
    ghost = "/nonexistent_media_dir/ghost.png"
    _set_private_control(privacy_db, Path(ghost), owner="alice")
    response = client.get(f"/image/thumbnail?path={ghost}", headers={"X-User-ID": "stranger"})
    assert response.status_code == 403


def test_file_endpoint_enforces(isolated_media_and_privacy):
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "original.png")
    _set_private_control(privacy_db, photo, owner="alice")

    assert client.get(f"/file?path={photo}", headers={"X-User-ID": "stranger"}).status_code == 403
    assert client.get(f"/file?path={photo}", headers={"X-User-ID": "alice"}).status_code == 200


def test_default_identity_without_header(isolated_media_and_privacy):
    """No X-User-ID header means the default local user."""
    media_dir, privacy_db = isolated_media_and_privacy
    photo = _make_photo(media_dir, "local.png")
    _set_private_control(privacy_db, photo, owner="default_user")

    assert client.get(f"/image/thumbnail?path={photo}").status_code == 200

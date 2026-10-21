"""
Tests for registry-derived photo source attribution.

Contract: docs/decisions/2026-10-21-photo-source-attribution.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.attribution import (
    AttributionResolver,
    attach_attribution,
    filter_by_source,
    kind_for_source_type,
    matches_kind,
    resolve_item_attributions,
)
from server.content_provenance import detect_content_provenance
from server.source_items import SourceItemStore
from server.sources import SourceStore


@pytest.fixture()
def stores(tmp_path: Path):
    source_store = SourceStore(tmp_path / "sources.db")
    item_store = SourceItemStore(tmp_path / "sources_items.db")
    return source_store, item_store


def _make_local_source(source_store: SourceStore, root: Path, name: str = "Photos"):
    return source_store.create_source(
        "local_folder",
        name=name,
        config={"path": str(root)},
        status="connected",
    )


# ── kind derivation ─────────────────────────────────────────────────────


def test_kind_for_source_type():
    assert kind_for_source_type("s3") == "cloud"
    assert kind_for_source_type("google_drive") == "cloud"
    assert kind_for_source_type("local_folder") == "local"
    assert kind_for_source_type(None) == "unknown"


# ── resolution precedence ───────────────────────────────────────────────


def test_local_folder_root_is_attributed(stores, tmp_path):
    source_store, item_store = stores
    library = tmp_path / "Library"
    library.mkdir()
    _make_local_source(source_store, library)

    resolver = AttributionResolver(source_store, item_store, media_root=tmp_path / "media")
    attribution = resolver.resolve(str(library / "cat.jpg"))

    assert attribution.origin == "source"
    assert attribution.kind == "local"
    assert attribution.match == "source_root"
    assert attribution.source_name == "Photos"
    assert attribution.source_type == "local_folder"


def test_longest_local_root_wins(stores, tmp_path):
    source_store, item_store = stores
    outer = tmp_path / "outer"
    inner = outer / "inner"
    inner.mkdir(parents=True)
    _make_local_source(source_store, outer, name="Outer")
    _make_local_source(source_store, inner, name="Inner")

    resolver = AttributionResolver(source_store, item_store, media_root=tmp_path / "media")
    attribution = resolver.resolve(str(inner / "cat.jpg"))

    assert attribution.source_name == "Inner"
    assert attribution.match == "source_root"


def test_cloud_source_item_is_attributed_as_cloud(stores, tmp_path):
    source_store, item_store = stores
    source = source_store.create_source("google_drive", name="Drive", status="connected")
    synced = tmp_path / "media_sources" / source.id / "gdrive" / "cat.jpg"
    synced.parent.mkdir(parents=True)
    item_store.upsert_seen(
        source_id=source.id,
        remote_id="remote-1",
        remote_path="cat.jpg",
        etag=None,
        modified_at=None,
        size_bytes=10,
        mime_type="image/jpeg",
        name="cat.jpg",
    )
    item_store.set_local_path(source.id, "remote-1", str(synced))

    resolver = AttributionResolver(source_store, item_store, media_root=tmp_path / "media")
    attribution = resolver.resolve(str(synced))

    assert attribution.origin == "source"
    assert attribution.kind == "cloud"  # origin is cloud even though the copy is local
    assert attribution.match == "source_item"
    assert attribution.source_name == "Drive"
    assert attribution.source_type == "google_drive"
    assert attribution.item_status == "active"
    assert attribution.remote_id == "remote-1"


def test_media_root_is_local_library(stores, tmp_path):
    source_store, item_store = stores
    media = tmp_path / "media"
    media.mkdir()

    resolver = AttributionResolver(source_store, item_store, media_root=media)
    attribution = resolver.resolve(str(media / "cat.jpg"))

    assert attribution.origin == "media_root"
    assert attribution.kind == "local"
    assert attribution.match == "media_root"
    assert attribution.source_name == "Local library"


def test_unknown_path_is_honestly_unattributed(stores, tmp_path):
    source_store, item_store = stores
    resolver = AttributionResolver(source_store, item_store, media_root=tmp_path / "media")
    attribution = resolver.resolve("/elsewhere/photo.jpg")

    assert attribution.origin == "unattributed"
    assert attribution.kind == "unknown"
    assert attribution.match == "none"
    assert attribution.source_name is None


# ── filtering ───────────────────────────────────────────────────────────


def test_filter_by_source_uses_registry_kinds(stores, tmp_path):
    source_store, item_store = stores
    cloud_source = source_store.create_source("s3", name="Bucket", status="connected")
    cloud_file = tmp_path / "media_sources" / cloud_source.id / "s3" / "cat.jpg"
    cloud_file.parent.mkdir(parents=True)
    item_store.upsert_seen(
        source_id=cloud_source.id,
        remote_id="r1",
        remote_path="cat.jpg",
        etag=None,
        modified_at=None,
        size_bytes=1,
        mime_type="image/jpeg",
        name="cat.jpg",
    )
    item_store.set_local_path(cloud_source.id, "r1", str(cloud_file))

    local_dir = tmp_path / "Pictures"
    local_dir.mkdir()
    _make_local_source(source_store, local_dir, name="Pictures")

    items = [
        {"path": str(cloud_file)},
        {"path": str(local_dir / "dog.jpg")},
        {"path": "/elsewhere/unknown.jpg"},
    ]
    resolver = AttributionResolver(source_store, item_store, media_root=tmp_path / "media")
    attributions = resolve_item_attributions(items, resolver)

    cloud = filter_by_source(items, attributions, "cloud")
    assert [i["path"] for i in cloud] == [str(cloud_file)]

    local = filter_by_source(items, attributions, "local")
    assert [i["path"] for i in local] == [str(local_dir / "dog.jpg")]

    # 'hybrid' is the compatibility alias for 'unknown'
    hybrid = filter_by_source(items, attributions, "hybrid")
    assert [i["path"] for i in hybrid] == ["/elsewhere/unknown.jpg"]

    assert len(filter_by_source(items, attributions, "all")) == 3


def test_matches_kind_alias():
    from server.attribution import PhotoAttribution

    unknown = PhotoAttribution(origin="unattributed", kind="unknown", match="none")
    assert matches_kind(unknown, "hybrid")
    assert matches_kind(unknown, "unknown")
    assert not matches_kind(unknown, "cloud")


# ── payload decoration ──────────────────────────────────────────────────


def test_attach_attribution_adds_record(stores, tmp_path):
    source_store, item_store = stores
    media = tmp_path / "media"
    media.mkdir()
    items = [{"path": str(media / "cat.jpg")}, {"path": "/elsewhere/x.jpg"}]

    resolver = AttributionResolver(source_store, item_store, media_root=media)
    attributions = resolve_item_attributions(items, resolver)
    attach_attribution(items, attributions, resolver)

    assert items[0]["attribution"]["kind"] == "local"
    assert items[0]["attribution"]["match"] == "media_root"
    assert items[1]["attribution"]["kind"] == "unknown"


def test_attach_attribution_resolves_late_arrivals(stores, tmp_path):
    """Items merged in after filtering still get a real attribution."""
    source_store, item_store = stores
    media = tmp_path / "media"
    media.mkdir()
    items = [{"path": str(media / "late.jpg")}]

    resolver = AttributionResolver(source_store, item_store, media_root=media)
    attach_attribution(items, {}, resolver)  # empty batch → resolved on demand

    assert items[0]["attribution"]["kind"] == "local"
    assert items[0]["attribution"]["match"] == "media_root"


# ── content provenance (detection only) ─────────────────────────────────


def test_content_provenance_detects_c2pa_marker(tmp_path):
    marker = b"\xd8\xfe\xc3\xd6\x1b\x0e\x48\x3c\x92\x97\x58\x28\x87\x7e\xc4\x81"
    image = tmp_path / "signed.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0" + marker + b"payload" * 100)

    result = detect_content_provenance(str(image))

    assert result["present"] is True
    assert "c2pa_uuid_box" in result["markers"]
    # Detection is not verification.
    assert result["verified"] is False
    assert result["verifier"] is None
    assert "not a verification result" in result["note"]


def test_content_provenance_reports_absence_honestly(tmp_path):
    image = tmp_path / "plain.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0" + b"nothing here" * 100)

    result = detect_content_provenance(str(image))

    assert result["present"] is False
    assert result["markers"] == []
    assert result["verified"] is False
    assert "not proof" in result["note"]


def test_content_provenance_skips_non_media(tmp_path):
    doc = tmp_path / "notes.txt"
    doc.write_text("hello")

    result = detect_content_provenance(str(doc))

    assert result["present"] is None
    assert "Not a scannable" in result["note"]


def test_content_provenance_handles_missing_file(tmp_path):
    result = detect_content_provenance(str(tmp_path / "missing.jpg"))

    assert result["present"] is None
    assert result["verified"] is False


# ── API surface ─────────────────────────────────────────────────────────


def test_attribution_endpoints(stores, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from server.main import app

    source_store, item_store = stores
    media = tmp_path / "media"
    media.mkdir()
    (media / "cat.jpg").write_bytes(b"\xff\xd8\xff\xe0")

    class FakeState:
        pass

    state = FakeState()
    state.source_store = source_store
    state.source_item_store = item_store

    monkeypatch.setattr("server.api.routers.attribution.settings.MEDIA_DIR", media)

    client = TestClient(app)
    res = client.get("/attribution", params={"path": str(media / "cat.jpg")})
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "local"
    assert body["match"] == "media_root"
    assert "content" not in body  # opt-in only

    res = client.get(
        "/attribution/batch",
        params=[("path", str(media / "cat.jpg")), ("path", "/elsewhere/x.jpg")],
    )
    assert res.status_code == 200
    batch = res.json()["attributions"]
    assert batch[str(media / "cat.jpg")]["kind"] == "local"
    assert batch["/elsewhere/x.jpg"]["kind"] == "unknown"

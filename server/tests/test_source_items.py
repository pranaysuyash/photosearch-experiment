from pathlib import Path
from datetime import datetime, timezone

from server.source_items import SourceItemStore


def test_upsert_and_mark_deleted(tmp_path: Path):
    store = SourceItemStore(tmp_path / "items.db")
    source_id = "s1"

    t1 = datetime.now(timezone.utc).isoformat()
    store.upsert_seen(
        source_id=source_id,
        remote_id="a",
        remote_path="a.jpg",
        etag="etag1",
        modified_at="2025-01-01T00:00:00Z",
        size_bytes=10,
        mime_type="image/jpeg",
        name="a.jpg",
    )
    store.set_local_path(source_id, "a", "/tmp/a.jpg")

    # Mark later time; should not delete since last_seen_at updated to now and we pass an earlier marker.
    deleted_none = store.mark_missing_as_deleted(source_id, t1)
    assert deleted_none == []

    # Force delete by using a future marker.
    future = "9999-12-31T23:59:59+00:00"
    deleted = store.mark_missing_as_deleted(source_id, future)
    assert len(deleted) == 1
    assert deleted[0].remote_id == "a"


def test_upsert_preserves_trashed_and_removed(tmp_path: Path):
    store = SourceItemStore(tmp_path / "items.db")
    source_id = "s1"

    store.upsert_seen(
        source_id=source_id,
        remote_id="a",
        remote_path="a.jpg",
        etag=None,
        modified_at=None,
        size_bytes=None,
        mime_type=None,
        name="a.jpg",
    )

    store.set_status(source_id, "a", "trashed")
    store.upsert_seen(
        source_id=source_id,
        remote_id="a",
        remote_path="a.jpg",
        etag="e2",
        modified_at="2025-01-01T00:00:00Z",
        size_bytes=10,
        mime_type="image/jpeg",
        name="a.jpg",
    )
    assert store.get(source_id, "a").status == "trashed"

    store.set_status(source_id, "a", "removed")
    store.upsert_seen(
        source_id=source_id,
        remote_id="a",
        remote_path="a.jpg",
        etag="e3",
        modified_at="2025-01-02T00:00:00Z",
        size_bytes=11,
        mime_type="image/jpeg",
        name="a.jpg",
    )
    assert store.get(source_id, "a").status == "removed"

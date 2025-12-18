from pathlib import Path

from server.trash_db import TrashDB


def test_trash_db_lifecycle(tmp_path: Path):
    db = TrashDB(tmp_path / "trash.db")

    item = db.create(
        item_id="t1",
        original_path="/tmp/original.jpg",
        trashed_path="/tmp/trash/t1/original.jpg",
        source_id="s1",
        remote_id="r1",
    )
    assert item.id == "t1"
    assert item.status == "trashed"

    items = db.list(status="trashed", limit=10, offset=0)
    assert len(items) == 1
    assert items[0].id == "t1"

    db.mark_restored("t1")
    restored = db.get("t1")
    assert restored.status == "restored"
    assert restored.restored_at is not None

    db.mark_deleted("t1")
    deleted = db.get("t1")
    assert deleted.status == "deleted"
    assert deleted.deleted_at is not None


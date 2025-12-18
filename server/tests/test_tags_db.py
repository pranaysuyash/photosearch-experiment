from pathlib import Path

from server.tags_db import TagsDB


def test_tags_db_basic(tmp_path: Path):
    db = TagsDB(tmp_path / "tags.db")

    db.create_tag("trip")
    assert db.has_tag("trip")

    added = db.add_photos("trip", ["/a.jpg", "/b.jpg", "/b.jpg"])
    assert added >= 2

    tags = db.list_tags(limit=10, offset=0)
    assert any(t.name == "trip" for t in tags)

    paths = db.get_tag_paths("trip")
    assert "/a.jpg" in paths
    assert "/b.jpg" in paths

    photo_tags = db.get_photo_tags("/a.jpg")
    assert "trip" in photo_tags

    removed = db.remove_photos("trip", ["/a.jpg"])
    assert removed == 1
    assert "/a.jpg" not in db.get_tag_paths("trip")

    ok = db.delete_tag("trip")
    assert ok
    assert not db.has_tag("trip")


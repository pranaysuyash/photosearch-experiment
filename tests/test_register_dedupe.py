"""Register dedupe loader tests (R4).

The snapshot lives at data/register_dedupe_media.json in production; tests
inject a tmp snapshot and cover: missing/malformed files, live-file
filtering, exemplar-first cluster shape, and single-member exclusion.
"""

import json
from pathlib import Path

import pytest

from server.config import settings
from server.register_dedupe import load_register_clusters


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    p = tmp_path / "register_dedupe_media.json"
    monkeypatch.setattr("server.register_dedupe.SNAPSHOT_PATH", p)
    return p


def write_snapshot(path: Path, clusters):
    path.write_text(
        json.dumps({"source": "photo-register", "snapshot_date": "2026-10-20", "clusters": clusters}),
        encoding="utf-8",
    )


class TestLoadRegisterClusters:
    def test_missing_snapshot_is_empty_not_error(self, snapshot):
        result = load_register_clusters(snapshot)
        assert result == {"clusters": [], "count": 0, "snapshot_date": None, "source": None}

    def test_malformed_snapshot_is_empty_not_error(self, snapshot):
        snapshot.write_text("{not json", encoding="utf-8")
        assert load_register_clusters(snapshot)["count"] == 0

    def test_exemplar_first_and_live_filter(self, snapshot, tmp_path):
        # Only b.jpg exists on disk alongside a.jpg; ghost.jpg was deleted.
        (settings.BASE_DIR / "media").mkdir(exist_ok=True)
        for name in ("a.jpg", "b.jpg"):
            (settings.BASE_DIR / "media" / name).write_bytes(b"x")

        write_snapshot(
            snapshot,
            {
                "7": [
                    {"path": "media/ghost.jpg", "is_exemplar": True, "sim_to_exemplar": 1.0},
                    {"path": "media/a.jpg", "is_exemplar": False, "sim_to_exemplar": 0.9},
                    {"path": "media/b.jpg", "is_exemplar": False, "sim_to_exemplar": 0.85},
                ],
                "9": [{"path": "media/a.jpg", "is_exemplar": True, "sim_to_exemplar": 1.0}],
            },
        )
        result = load_register_clusters(snapshot)

        # Cluster 7 loses its ghost exemplar and survives with 2 live members;
        # cluster 9 drops to a single member and is excluded entirely.
        assert result["count"] == 1
        cluster = result["clusters"][0]
        assert cluster["cluster_id"] == "7"
        assert cluster["paths"] == ["media/a.jpg", "media/b.jpg"]
        assert cluster["exemplar"]["path"] == "media/a.jpg"  # first live member
        assert result["snapshot_date"] == "2026-10-20"

    def test_clusters_sorted_by_size(self, snapshot, tmp_path):
        media = settings.BASE_DIR / "media"
        media.mkdir(exist_ok=True)
        for name in ("a.jpg", "b.jpg", "c.jpg", "d.jpg"):
            (media / name).write_bytes(b"x")

        write_snapshot(
            snapshot,
            {
                "1": [
                    {"path": "media/a.jpg", "is_exemplar": True, "sim_to_exemplar": 1.0},
                    {"path": "media/b.jpg", "is_exemplar": False, "sim_to_exemplar": 0.9},
                ],
                "2": [
                    {"path": "media/c.jpg", "is_exemplar": True, "sim_to_exemplar": 1.0},
                    {"path": "media/d.jpg", "is_exemplar": False, "sim_to_exemplar": 0.9},
                    {"path": "media/a.jpg", "is_exemplar": False, "sim_to_exemplar": 0.8},
                ],
            },
        )
        result = load_register_clusters(snapshot)
        assert [len(c["paths"]) for c in result["clusters"]] == [3, 2]

    def test_real_snapshot_if_present_loads(self):
        """The shipped snapshot (1 cluster in the dev library) parses."""
        if not Path("data/register_dedupe_media.json").is_file():
            pytest.skip("snapshot not present")
        result = load_register_clusters()
        assert result["count"] >= 0
        for cluster in result["clusters"]:
            assert len(cluster["paths"]) >= 2

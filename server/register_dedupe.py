"""Register-backed dedupe clusters (R4).

Loads near-duplicate groups for this repo's media from the photo-register's
leader-clustering output (154,864 clusters machine-wide; snapshot filtered to
paths inside this repo). Snapshot-driven by design: the register is itself a
point-in-time artifact (see docs/PHOTO_REGISTER_SALVAGE_EXPLORATION_2026-10-19.md),
a JSON file needs no SQL in this module, and it keeps the register project as
the data layer with photosearch as the product.

Regenerate the snapshot after the register re-indexes this repo's media:

    sqlite3 -json "file:$HOME/Projects/photo-register/data/similarity_graph.sqlite3?mode=ro" \
      "SELECT cluster_id, path, is_exemplar, sim_to_exemplar, size FROM dedupe_clusters \
       WHERE path LIKE '$PWD/media/%'" > /tmp/reg_dedupe.json
    # then normalize to data/register_dedupe_media.json:
    # {"source": ..., "snapshot_date": ..., "clusters": {"<id>": [{"path", "is_exemplar", "sim_to_exemplar"}]}}
    # (keep only clusters with more than one surviving member)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from server.config import settings

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(settings.BASE_DIR) / "data" / "register_dedupe_media.json"


def load_register_clusters(snapshot_path: Path = SNAPSHOT_PATH) -> Dict[str, Any]:
    """Load the snapshot; returns {"clusters": [...], "snapshot_date", "source"}.

    Each cluster is a list of members with the exemplar first. Missing or
    malformed snapshots return an empty result (feature simply absent), and
    members whose files no longer exist on disk are dropped live so the UI
    never shows ghost duplicates.
    """
    empty = {"clusters": [], "count": 0, "snapshot_date": None, "source": None}
    try:
        raw = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return empty
    except json.JSONDecodeError as e:
        logger.warning("Register dedupe snapshot malformed: %s", e)
        return empty

    clusters_out = []
    for cluster_id, members in (raw.get("clusters") or {}).items():
        live = [m for m in members if (Path(settings.BASE_DIR) / m.get("path", "")).is_file()]
        if len(live) < 2:
            continue
        exemplar = next((m for m in live if m.get("is_exemplar")), live[0])
        others = [m for m in live if m is not exemplar]
        clusters_out.append(
            {
                "cluster_id": str(cluster_id),
                "source": "photo-register",
                "exemplar": exemplar,
                "duplicates": others,
                "paths": [exemplar["path"]] + [m["path"] for m in others],
            }
        )

    clusters_out.sort(key=lambda c: -len(c["paths"]))
    return {
        "clusters": clusters_out,
        "count": len(clusters_out),
        "snapshot_date": raw.get("snapshot_date"),
        "source": raw.get("source"),
    }

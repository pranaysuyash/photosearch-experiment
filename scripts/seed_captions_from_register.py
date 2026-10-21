#!/usr/bin/env python
"""Seed photo captions (and the caption search index) from photo-register.

Fills the canonical captions DB (settings.CAPTIONS_DB_PATH) from the
photo-register BLIP snapshot for photosearch's own media/ files, then
(re)embeds everything into the caption search index. R1 of
docs/PHOTO_REGISTER_SALVAGE_EXPLORATION_2026-10-19.md.

Policy (enforced by VLMCaptionService.store_generated_caption):
- never overwrites a user-edited caption;
- never overwrites an existing generated caption unless --force, so BLIP
  cannot silently replace a stronger provider's caption.

The index embeds via settings.CAPTION_EMBEDDING_MODEL (default
google/embeddinggemma-300m; needs HF_TOKEN for a fresh download). If that
model cannot load, the script falls back to the app's CLIP generator and
says so loudly — seed-time and query-time must resolve the same embedder,
which they do because both read the same env.

Usage:
    .venv/bin/python scripts/seed_captions_from_register.py            # seed + index
    .venv/bin/python scripts/seed_captions_from_register.py --dry-run  # report only
    .venv/bin/python scripts/seed_captions_from_register.py --no-index # DB only

Snapshot regeneration (when photo-register re-indexes or the media set grows):
    sqlite3 -json "file:$HOME/Projects/photo-register/data/corpus_index.sqlite3?mode=ro" \
      "SELECT path, blip_caption AS caption FROM images \
       WHERE path LIKE '$PWD/media/%' AND trim(coalesce(blip_caption,'')) != '' ORDER BY path" \
      > /tmp/reg_caps.json
    # then normalize to {"path": <repo-relative>, "caption": ...} JSONL
    # (see experiments/register_captions_media_2026-10-20.jsonl for the format)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RASTER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tiff", ".tif"}
DEFAULT_SNAPSHOT = REPO_ROOT / "experiments" / "register_captions_media_2026-10-20.jsonl"
REGISTER_MODEL = "Salesforce/blip-image-captioning-base"
REGISTER_PROVIDER = "photo-register"


def load_snapshot(snapshot: Path, limit: int | None):
    """Load {path, caption} rows, keeping only existing raster files."""
    rows = []
    with open(snapshot, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            path = (REPO_ROOT / item["path"]).resolve()
            if path.suffix.lower() not in RASTER_EXTENSIONS or not path.is_file():
                continue
            caption = (item.get("caption") or "").strip()
            if caption:
                rows.append((str(path), caption))
    return rows[:limit] if limit else rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated captions")
    parser.add_argument("--no-index", action="store_true", help="Write the captions DB only; skip embedding")
    parser.add_argument("--dry-run", action="store_true", help="Report what would happen; write nothing")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    rows = load_snapshot(Path(args.snapshot), args.limit)
    print(f"Snapshot: {len(rows)} captioned raster files")

    from server.config import settings
    from server.vlm_caption_service import VLMCaptionService

    service = VLMCaptionService(settings.CAPTIONS_DB_PATH)

    stored = replaced = skipped_edited = skipped_generated = 0
    for path, caption in rows:
        if args.dry_run:
            existing = service.get_caption(path)
            if existing and existing.get("is_edited"):
                skipped_edited += 1
            elif existing:
                skipped_generated += 1
            else:
                stored += 1
            continue

        result = service.store_generated_caption(
            path,
            caption,
            model_version=REGISTER_MODEL,
            provider=REGISTER_PROVIDER,
            overwrite_generated=args.force,
        )
        if result.get("stored"):
            if result.get("replaced"):
                replaced += 1
            else:
                stored += 1
        else:
            reason = result.get("reason", "")
            if "user-edited" in reason:
                skipped_edited += 1
            else:
                skipped_generated += 1

    print(
        f"Captions: stored={stored} replaced={replaced} "
        f"kept_user_edited={skipped_edited} kept_existing={skipped_generated}"
    )
    if args.dry_run:
        print("Dry run — nothing written.")
        return

    if args.no_index:
        print("--no-index: caption search index not updated.")
        return

    from server.caption_search_index import CaptionSearchIndex

    index = CaptionSearchIndex()
    all_rows = service.get_all_captions()
    stats = index.ensure_indexed(all_rows, None)  # dedicated EG model or nothing
    if stats.get("indexed", 0) == 0 and stats.get("reason"):
        print(f"Dedicated embedder unavailable ({stats['reason']}); loading CLIP fallback…")
        from server.embedding_generator import EmbeddingGenerator

        stats = index.ensure_indexed(all_rows, EmbeddingGenerator())
        print("WARNING: indexed in CLIP space — ensure CAPTION_EMBEDDING_MODEL resolves the same way at query time.")
    print(f"Index: {stats} | {index.get_stats()}")


if __name__ == "__main__":
    raise SystemExit(main() or 0)

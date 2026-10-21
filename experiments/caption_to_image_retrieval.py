#!/usr/bin/env python
"""Caption→image retrieval benchmark.

Answers "which image embedder retrieves the right photo from a natural-language
description?" with statistical weight: one query per captioned image (1064 under
photosearch's media/), correct set = every image sharing that exact caption
(near-duplicates in the benchmark set share captions, so a strict single-path
target would wrongly penalize models).

Labels are BLIP captions snapshotted from ~/Projects/photo-register into
experiments/register_captions_media_2026-10-20.jsonl — a model independent of
all candidates, so none is favored by construction. Caveat: caption-as-query is
a literal, sentence-length query distribution; real user queries are shorter
and vaguer.

Usage:
    HF_TOKEN=... .venv/bin/python experiments/caption_to_image_retrieval.py \
        --models clip-ViT-B-32 siglip2:google/siglip2-base-patch16-384 google/embeddinggemma-2 \
        --out experiments/caption_to_image_retrieval_2026-10-20.md

Reuses the model adapters from experiments/embedding_bakeoff.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "experiments"))

from embedding_bakeoff import load_model  # noqa: E402

DEFAULT_FIXTURE = REPO_ROOT / "experiments" / "register_captions_media_2026-10-20.jsonl"
# The register rasterizes SVGs for its own pipeline; PIL-based encoders cannot.
RASTER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tiff", ".tif"}


def load_pairs(fixture: Path, limit: int | None):
    pairs = []
    with open(fixture, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            path = (REPO_ROOT / row["path"]).resolve()
            if path.suffix.lower() not in RASTER_EXTENSIONS:
                continue
            if not path.is_file() or not row.get("caption", "").strip():
                continue
            # Real libraries contain giant scans/panoramas that trip PIL's
            # decompression guard (179 MP) and kill whole batches; candidate
            # models downsample to ~224-384 px anyway, so >100 MP adds no signal.
            # im.load() forces the FULL decode: it also catches truncated
            # files whose headers parse fine but explode mid-decode.
            try:
                from PIL import Image

                with Image.open(path) as im:
                    if im.width * im.height > 100_000_000:
                        continue
                    if min(im.width, im.height) < 32:
                        continue  # 1-px strips crash Metal/processor paths
                    im.load()
            except Exception:
                continue
            pairs.append((str(path), row["caption"].strip()))
    return pairs[:limit] if limit else pairs


def evaluate(model, pairs, ks=(1, 5, 10)):
    paths = [p for p, _ in pairs]
    captions = [c for _, c in pairs]

    # Correct set per query = all indices sharing the identical caption.
    by_caption = defaultdict(set)
    for i, c in enumerate(captions):
        by_caption[c].add(i)

    t0 = time.time()
    image_vecs = np.asarray(model.embed_images(paths))
    embed_s = time.time() - t0

    t1 = time.time()
    query_vecs = np.asarray([model.embed_text(c) for c in captions])
    text_s = time.time() - t1

    sims = query_vecs @ image_vecs.T  # (n_queries, n_images)
    ranks = []
    for qi in range(len(captions)):
        order = np.argsort(-sims[qi])
        correct = by_caption[captions[qi]]
        rank = next(r + 1 for r, idx in enumerate(order) if int(idx) in correct)
        ranks.append(rank)
    ranks = np.asarray(ranks)

    out = {
        "n_queries": len(captions),
        "unique_captions": len(by_caption),
        "images_per_s": round(len(paths) / max(embed_s, 1e-6), 1),
        "queries_per_s": round(len(captions) / max(text_s, 1e-6), 1),
        "mrr": round(float(np.mean(1.0 / ranks)), 3),
        "median_rank": int(np.median(ranks)),
    }
    for k in ks:
        out[f"recall@{k}"] = round(float(np.mean(ranks <= k)), 3)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--limit", type=int, default=None, help="Cap on captioned images (default all)")
    parser.add_argument("--out", help="Markdown report path")
    args = parser.parse_args()

    pairs = load_pairs(Path(args.fixture), args.limit)
    print(f"{len(pairs)} captioned images from {Path(args.fixture).name}\n")

    keys = [
        "model",
        "dim",
        "device",
        "load_s",
        "images_per_s",
        "queries_per_s",
        "recall@1",
        "recall@5",
        "recall@10",
        "mrr",
        "median_rank",
        "error",
    ]
    rows = []
    for spec in args.models:
        try:
            model = load_model(spec)
            device = getattr(getattr(model, "model", None), "device", getattr(model, "device", "?"))
            res = evaluate(model, pairs)
            res.update({"model": spec, "dim": model.dim, "load_s": model.load_s, "device": str(device)})
            rows.append(res)
            print(f"[ok] {spec}: {res}", flush=True)
            _write_report(rows, keys, args, len(pairs))
        except Exception as e:
            rows.append({"model": spec, "error": str(e)[:160]})
            print(f"[skip] {spec}: {e}", flush=True)
            _write_report(rows, keys, args, len(pairs))

    write_and_print_report(rows, keys, args, len(pairs))


def _table(rows, keys):
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
    return "\n".join(lines)


def _write_report(rows, keys, args, n_pairs):
    """Persist partial results after every model (crash-resilient)."""
    if not args.out or not rows:
        return
    n = rows[0].get("n_queries", n_pairs)
    uniq = rows[0].get("unique_captions", "?")
    header = (
        f"# Caption→image retrieval — {n} queries over {n_pairs} images "
        f"({uniq} unique captions; identical-caption images count as one correct set)\n\n"
    )
    Path(args.out).write_text(header + _table(rows, keys) + "\n", encoding="utf-8")


def write_and_print_report(rows, keys, args, n_pairs):
    report = _table(rows, keys)
    print("\n" + report, flush=True)
    if args.out:
        _write_report(rows, keys, args, n_pairs)
        print(f"\nReport written to {args.out}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main() or 0)

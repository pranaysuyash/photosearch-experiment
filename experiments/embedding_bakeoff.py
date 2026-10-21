#!/usr/bin/env python
"""Embedding bake-off harness.

Compares candidate search-embedding models on YOUR library before any
production migration (P2 of docs/OSS_MODEL_INTEGRATION_EXPLORATION_2026-10-19.md):
current CLIP ViT-B/32 vs SigLIP 2 vs EmbeddingGemma-class text/image models.

Usage:
    # Evaluate models against labeled fixtures over a library directory:
    .venv/bin/python experiments/embedding_bakeoff.py \
        --library media \
        --fixtures experiments/bakeoff_fixtures.jsonl \
        --models clip-ViT-B-32 siglip2:google/siglip2-base-patch16-384

    # Throughput only (no fixtures needed):
    .venv/bin/python experiments/embedding_bakeoff.py --library media --models clip-ViT-B-32

Model specs:
    <sentence-transformers-name>      loaded via SentenceTransformer
    siglip2:<hf-model-id>             loaded via transformers AutoModel (SigLIP-style)
                                      e.g. siglip2:google/siglip2-base-patch16-384

Metrics: Recall@k, MRR, images/sec embedding throughput, model load time.
Fixtures are JSONL: {"query": "...", "expect_paths": ["relative/or/absolute.jpg"]}
(see bakeoff_fixtures.example.jsonl). Gated HF models (e.g. EmbeddingGemma)
require you to have accepted the model terms; with an HF token set, plain
sentence-transformers names work directly.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".heic", ".tiff", ".tif"}


class STModel:
    """sentence-transformers backed model (CLIP-class, EmbeddingGemma-class)."""

    kind = "sentence-transformers"

    def __init__(self, name: str):
        from sentence_transformers import SentenceTransformer

        self.name = name
        started = time.time()
        self.model = SentenceTransformer(name)
        self.load_s = round(time.time() - started, 1)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed_images(self, paths):
        from PIL import Image

        images = [Image.open(p).convert("RGB") for p in paths]
        return self.model.encode(images, normalize_embeddings=True, batch_size=16, show_progress_bar=False)

    def embed_text(self, text: str):
        # Prompt-trained models (EmbeddingGemma family) expect the "query"
        # prompt for retrieval queries; CLIP-class models have no prompts.
        prompts = getattr(self.model, "prompts", None) or {}
        if "query" in prompts:
            return self.model.encode([text], prompt_name="query", normalize_embeddings=True)[0]
        return self.model.encode([text], normalize_embeddings=True)[0]


class SigLIPModel:
    """transformers AutoModel backed model (SigLIP/SigLIP2-class)."""

    kind = "transformers-siglip"

    def __init__(self, name: str):
        import torch
        from transformers import AutoModel, AutoProcessor

        self.name = name
        self.torch = torch
        started = time.time()
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = AutoModel.from_pretrained(name).to(self.device)
        self.processor = AutoProcessor.from_pretrained(name)
        self.model.eval()
        self.load_s = round(time.time() - started, 1)
        self.dim = getattr(getattr(self.model, "config", None), "hidden_size", None) or getattr(
            getattr(self.model, "text_config", None), "hidden_size", "?"
        )

    def _features_to_tensor(self, features):
        """SigLIP-class get_*_features may return BaseModelOutputWithPooling."""
        if not self.torch.is_tensor(features):
            pooled = getattr(features, "pooler_output", None)
            features = pooled if pooled is not None else features[0]
        return features

    def embed_images(self, paths, batch_size: int = 16):
        """Chunked embedding: a single forward over the whole corpus exhausts
        unified memory on real libraries (hard crash at ~7k images on Metal)."""
        import numpy as np
        from PIL import Image

        feats = []
        for i in range(0, len(paths), batch_size):
            images = [Image.open(p).convert("RGB") for p in paths[i : i + batch_size]]
            inputs = self.processor(images=images, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with self.torch.no_grad():
                features = self._features_to_tensor(self.model.get_image_features(**inputs))
            features = self.torch.nn.functional.normalize(features, dim=-1)
            feats.append(features.cpu().float().numpy())
        return np.concatenate(feats) if feats else np.zeros((0, 1))

    def embed_text(self, text: str):
        inputs = self.processor(text=[text], return_tensors="pt", padding="max_length", truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with self.torch.no_grad():
            features = self._features_to_tensor(self.model.get_text_features(**inputs))
        features = self.torch.nn.functional.normalize(features, dim=-1)
        return features[0].cpu().float().numpy()


def load_model(spec: str):
    if spec.startswith("siglip2:"):
        return SigLIPModel(spec.split(":", 1)[1])
    return STModel(spec)


def cosine_topk(query_vec, matrix, k):
    import numpy as np

    sims = matrix @ np.asarray(query_vec)
    order = np.argsort(-sims)[:k]
    return [(int(i), float(sims[i])) for i in order]


def evaluate(model, image_paths, fixtures, topk):
    results = {"recall": [], "mrr": []}
    if not fixtures:
        return results

    started = time.time()
    vectors = model.embed_images(image_paths)
    embed_s = time.time() - started
    results["images_per_s"] = round(len(image_paths) / max(embed_s, 1e-6), 1)

    for fixture in fixtures:
        expect = fixture.get("expect_paths") or []
        expect_resolved = {str(Path(p).resolve()) for p in expect}
        resolved_paths = [str(p.resolve()) for p in image_paths]
        qvec = model.embed_text(fixture["query"])
        top = cosine_topk(qvec, vectors, topk)
        ranked_paths = [resolved_paths[i] for i, _ in top]
        hits = [ranked_paths.index(p) for p in expect_resolved if p in ranked_paths]
        if expect_resolved:
            results["recall"].append(len(hits) / len(expect_resolved))
            results["mrr"].append(1.0 / (min(hits) + 1) if hits else 0.0)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--library", required=True, help="Directory of images to index")
    parser.add_argument("--fixtures", help="JSONL of {query, expect_paths}")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["clip-ViT-B-32", "siglip2:google/siglip2-base-patch16-384"],
        help="Model specs (see module docstring)",
    )
    parser.add_argument("--topk", type=int, default=10)
    parser.add_argument("--limit", type=int, default=2000, help="Max images to index")
    parser.add_argument("--out", help="Optional path for a markdown report")
    args = parser.parse_args()

    image_paths = sorted(p for p in Path(args.library).rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)[: args.limit]
    if not image_paths:
        print(f"No images found under {args.library}")
        return 2

    fixtures = []
    if args.fixtures:
        fixture_path = Path(args.fixtures)
        if not fixture_path.exists():
            print(f"Fixtures file not found: {fixture_path} (see bakeoff_fixtures.example.jsonl)")
            return 2
        with open(fixture_path, "r", encoding="utf-8") as f:
            fixtures = [json.loads(line) for line in f if line.strip()]

    print(f"Library: {len(image_paths)} images | fixtures: {len(fixtures)} | top-k: {args.topk}\n")

    rows = []
    for spec in args.models:
        try:
            model = load_model(spec)
        except Exception as e:
            print(f"[skip] {spec}: failed to load ({e})")
            rows.append({"model": spec, "error": str(e)[:120]})
            continue

        res = evaluate(model, image_paths, fixtures, args.topk)
        recall = sum(res["recall"]) / len(res["recall"]) if res["recall"] else None
        mrr = sum(res["mrr"]) / len(res["mrr"]) if res["mrr"] else None
        rows.append(
            {
                "model": spec,
                "kind": model.kind,
                "dim": model.dim,
                "load_s": model.load_s,
                "images_per_s": res.get("images_per_s"),
                f"recall@{args.topk}": round(recall, 3) if recall is not None else None,
                "mrr": round(mrr, 3) if mrr is not None else None,
            }
        )
        print(f"[ok] {spec}: {rows[-1]}")

    # Markdown summary
    if rows:
        keys = ["model", "kind", "dim", "load_s", "images_per_s", f"recall@{args.topk}", "mrr", "error"]
        lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(k, "")) for k in keys) + " |")
        report = "\n".join(lines)
        print("\n" + report)
        if args.out:
            Path(args.out).write_text(report + "\n", encoding="utf-8")
            print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    raise SystemExit(main() or 0)

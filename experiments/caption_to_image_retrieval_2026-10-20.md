# Caption→image retrieval — 1062 queries (803 unique captions) — 2026-10-20

**This run answers "is EG2 better than SigLIP2?" with statistical weight, and it
changes the D1 recommendation.** Setup: one query per BLIP-captioned raster image under
`media/` (labels snapshotted from photo-register into
`register_captions_media_2026-10-20.jsonl` — a model independent of all candidates);
correct set = every image sharing the identical caption; all models on MPS.
Script: `experiments/caption_to_image_retrieval.py`.

| model | dim | device | load_s | images_per_s | queries_per_s | recall@1 | recall@5 | recall@10 | mrr | median_rank |
|---|---|---|---|---|---|---|---|---|---|---|
| clip-ViT-B-32 (current) | 512 | mps | 5.6 | **276** | 109 | 0.146 | 0.327 | 0.446 | 0.236 | 16 |
| siglip2-base-patch16-384 | 768 | mps | 3.1 | 41 | 126 | 0.176 | **0.405** | **0.496** | **0.291** | **11** |
| embeddinggemma-2 | 768 | mps | 9.4 | 1.6 | 24 | **0.190** | 0.382 | 0.457 | 0.287 | 14 |

## Findings

1. **CLIP ViT-B/32 is clearly the worst image embedder** — both alternatives beat it by
   ~+23% MRR and +17–24% recall@5, with median rank 16 → 11–14. The earlier "no
   migration justified" verdict came from a 7-query test that could not discriminate;
   at ~1000 queries the direction is unambiguous. **D1 updated: migrating the image leg
   off CLIP is now evidence-backed** (a rerun on the real library remains the gate for
   the final pick — this media/ set is synthetic).
2. **EG2 vs SigLIP2 is a genuine tie with different shapes**: EG2 wins recall@1
   (0.190 vs 0.176, +8% — sharper top hit); SigLIP2 wins recall@5/@10 and median rank
   (better depth/robustness); MRR identical within noise (0.287 vs 0.291). Neither
   dominates on quality.
3. **The decisive difference is cost.** EG2 embeds images at ~1.6–3 img/s on this Mac
   (probed separately: batch size 1/16/48 all ≈3 img/s, already bf16 on MPS — inherent
   to its image path through transformers/sentence-transformers, not a harness
   artifact). SigLIP2: 41 img/s; CLIP: 276. A 10k-photo index ≈ 36 s (CLIP) / 4 min
   (SigLIP2) / ~1 h (EG2). Query-side EG2 is fine (24 q/s ≈ 40 ms).

## Recommendation (supersedes the earlier "keep CLIP")

- **Image leg → SigLIP2-base-patch16-384** once the real-library rerun confirms the
  ordering: best recall depth, 15× faster than EG2, Apache-2.0, 768-d. Migration
  machinery (index stamping + reset-on-model-change) is already in place.
- **Caption leg stays EG-300m** (measured 2.2× over CLIP-text; text-only is cheap).
- **EG2 stays a consolidation candidate, gated on throughput**: one space for image +
  caption + audio is architecturally attractive and its top-1 precision is the best
  measured, but 1.6–3 img/s makes library indexing impractical today. Revisit
  triggers: (a) an MLX inference path (mlx-vlm lists EmbeddingGemma — unmeasured),
  (b) a faster transformers image path for the Gemma-4 processor, (c) audio
  embeddings joining search, where a single space has outsized value.

## Caveats

- Caption-as-query is a literal, sentence-length distribution; real user queries are
  shorter and vaguer — short-query behavior is unmeasured.
- `media/` is a synthetic benchmark set (benchmark_* renders), not personal photos.
- 803/1062 unique captions — the identical-caption correct-set rule handled the rest;
  2 SVGs in the register snapshot were excluded (PIL cannot rasterize them).

## Raw output

| model | dim | device | load_s | images_per_s | queries_per_s | recall@1 | recall@5 | recall@10 | mrr | median_rank | error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| clip-ViT-B-32 | 512 | mps:0 | 5.6 | 276.1 | 109.3 | 0.146 | 0.327 | 0.446 | 0.236 | 16 |  |
| siglip2:google/siglip2-base-patch16-384 | ? | mps:0 | 3.1 | 41.0 | 126.0 | 0.176 | 0.405 | 0.496 | 0.291 | 11 |  |
| google/embeddinggemma-2 | 768 | mps:0 | 9.4 | 1.6 | 24.3 | 0.19 | 0.382 | 0.457 | 0.287 | 14 |  |

# EG2/MLX image-embedding benchmark — honest numbers — 2026-10-20

**Headline: there is no fast EG2 path on this Mac. Image embedding costs ~2–5 img/s
regardless of runtime (MLX bf16 or sentence-transformers); the vision tower is the
cost. Two earlier fast claims (160 img/s MLX, 112 img/s per-image) were measurement
errors. The shipped architecture is therefore exactly what the operator directed:
fast model for the interactive space, EG2 in a background quality space built while
idle, query-time rerank when coverage is complete.**

## The two measurement traps (both hit, both documented)

1. **MLX lazy evaluation.** `model(**inputs)` builds a graph; nothing computes until
   materialization (`.tolist()`, `mx.eval`, float()). My first benchmark timed graph
   construction and reported **160 img/s**; forcing evaluation yields ~3.5–4.8 img/s.
2. **Batch collapse in the raw mlx_vlm processor.** `processor(images=[4 imgs])` →
   `text_embeds (1, 768)` — a multi-image batch JOINTS into one embedding. The
   benchmark counted inputs, not outputs. Any per-image indexer must call the
   processor per image.

## Verified numbers (all with forced evaluation and output-count checks)

| Path | Throughput | Correctness |
|---|---|---|
| EG2 via MLX, per-image (production backend) | **3.5–4.8 img/s** (800×800 pipeline images) | 1 vector/image; wolf cosine 0.759 (matches ST 0.758) |
| EG2 via sentence-transformers | ~1.6–3 img/s | batches correctly (8 in → 8 distinct 768-d) — the 1062-query benchmark numbers stand |
| CLIP ViT-B/32 via ST (interactive default) | ~276 img/s | — |

The MLX forward itself is ~9 ms — preprocessing (numpy, 2520-token grids) dominates.
A future MLX-native preprocessing path could change this; unmeasured.

## Shipped design (implements the operator's direction)

- **Interactive space:** CLIP (unchanged; `IMAGE_EMBEDDING_BACKEND=clip_st` default;
  `eg2_mlx` remains available as a pinned experiment knob via
  `server/eg2_mlx_backend.py`).
- **Background quality space:** `photos_quality` LanceDB table (`server/
  image_quality_index.py`) with EG2 embeddings, filled by `QualityIndexBuilder` —
  an idle-gated thread (no API activity for `IMAGE_QUALITY_IDLE_SECONDS`, default
  300 s; heartbeat via the HTTP middleware) that embeds `IMAGE_QUALITY_BATCH_SIZE`
  pending images per cycle and stops on shutdown.
- **Query-time rerank:** `/search/semantic` reranks its candidate window through the
  quality space **only at full coverage** (partial coverage would mix score scales);
  reranked results carry `qualityReranked: true`.
- **Control surface:** `GET/POST /api/indexing/quality[/start|/stop|/build-once]`.

Live proof (real EG2-MLX): 3-image quality space built, wolf ranked top at 0.759,
coverage gate at 1.0, pending drained to 0.

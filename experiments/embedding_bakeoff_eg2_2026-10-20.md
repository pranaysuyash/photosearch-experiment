# Embedding bake-off incl. EmbeddingGemma 2 — 2026-10-20

**EG2 open item: RESOLVED (it loads; see below for whether to adopt).**

The earlier "EG2 won't load" diagnosis was wrong: our sentence-transformers (6.1.0) and
transformers (5.19.0) are the latest and DO ship EG2. The import failed because EG2 reuses
Gemma 4's image processor, which imports `torchvision` — not installed. `pip install torchvision`
fixed it (torchvision 0.29.1). EG2 then loaded in 15 s via sentence-transformers with
query/document prompts, embedding **text and images into one 768-d space**: query
"wolf forest animal" ↔ the wolf *image* = 0.758, ↔ its caption text = 0.839.

**Adoption verdict on this dev set: not yet.** Same 60-image pool / 7 vision-verified fixtures
as the first bake-off. EG2 as the *image* embedder ties SigLIP2 on MRR and beats CLIP, with
recall capped by the fixture ceiling like everyone else — but it embeds images ~12× slower
than CLIP here (4.3 vs 54 img/s; a 10k-photo re-index ≈ 40 min vs ≈ 3 min). CLIP's own
throughput also dropped vs the previous run (187 → 54 img/s) — likely torchvision changing
sentence-transformers' image preprocessing path; worth re-measuring before any decision.

What EG2 uniquely offers is architectural: ONE space for the image leg, the caption leg
(currently EG-300m, text-only) and a future audio leg (ASR is live now) — collapsing
max-fusion across spaces into same-space retrieval. That is the trigger to revisit:
when audio/transcript embeddings join search, or when the real-library rerun (D1) shows an
image-quality gap. Until then: keep CLIP (image) + EG-300m (captions, measured 2.2×).

| model | kind | dim | load_s | images_per_s | recall@5 | mrr | error |
|---|---|---|---|---|---|---|---|
| clip-ViT-B-32 | sentence-transformers | 512 | 5.9 | 54.2 | 0.214 | 0.214 |  |
| siglip2:google/siglip2-base-patch16-384 | transformers-siglip | ? | 3.0 | 33.2 | 0.214 | 0.286 |  |
| google/embeddinggemma-2 | sentence-transformers | 768 | 8.9 | 4.3 | 0.214 | 0.286 |  |

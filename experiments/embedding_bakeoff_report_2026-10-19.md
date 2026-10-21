# Embedding bake-off — 2026-10-19 (media/ dev set)

**Read the caveats before the numbers:**
- Fixture set: 7 queries / 11 relevant images, labels verified with an independent vision model (media/ filenames are decorative — `architecture_1.jpg` is a wolf; never trust them as labels).
- The pool is 60 visually-similar synthetic photos; several unlisted images are plausibly relevant to some queries (fixture incompleteness caps Recall@5 — all models tie at 0.214, which says more about the fixtures than the models).
- MRR is the directional quality signal here. Throughput reflects this harness's adapters (SigLIP via transformers on MPS at 384px; CLIP via sentence-transformers at 224px) — pixel count differs ~2.8×.
- Conclusion for D1: **no migration justified on this evidence.** Rerun `experiments/embedding_bakeoff.py` with fixtures from the real photo library before deciding. EmbeddingGemma 2 couldn't be included (HF-gated at run time).

| model | kind | dim | load_s | images_per_s | recall@5 | mrr | error |
|---|---|---|---|---|---|---|---|
| clip-ViT-B-32 | sentence-transformers | 512 | 5.3 | 187.7 | 0.214 | 0.214 |  |
| siglip2:google/siglip2-base-patch16-384 | transformers-siglip | ? | 2.5 | 29.5 | 0.214 | 0.286 |  |
| siglip2:google/siglip2-so400m-patch14-384 | transformers-siglip | ? | 192.1 | 8.2 | 0.214 | 0.286 |  |

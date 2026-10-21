# photo-register Salvage Exploration

- **Date:** 2026-10-19
- **Question:** Does `~/Projects/photo-register` contain anything useful for photosearch?
- **Answer: emphatically yes.** photo-register is a working, verified, machine-wide image register that is directly complementary to this week's OSS-model work. Its own README already specifies the integration path ("photo-register is the data + capability layer; photosearch_experiment remains the product; no code merge required").
- **All claims below verified live 2026-10-19** (sqlite counts + real text/image search runs) — Observed/Tier 4, not README-trust.

## What exists (verified)

| Asset | Scale | Verified state |
|---|---|---|
| `data/corpus_index.sqlite3` | 158,238 images across 7 roots (Projects 147k, Downloads 3.5k, Documents 3.4k, Desktop, Personal…) | 157,886 BLIP-captioned (99.8%), 157,887 CLIP-embedded |
| BLIP captions | `Salesforce/blip-image-captioning-base`, MPS | Includes captions **for photosearch's own `media/benchmark_*` and category files** (e.g. `architecture_1.jpg` = "a coyote in the woods", `benchmark_0100.png` = "a man is standing on a beach with a surfboard") |
| Zero-shot register categories | 6 classes with real distribution: project-code-asset 68k, media-experiment-asset 25k, design-web-asset 22k, screenshot 20k, document-scan 19.5k, personal-photo 3.1k | `clip_top1` + prob + margin + full probs per image |
| `data/similarity_graph.sqlite3` | 691,265 kNN edges; **154,864 dedupe clusters** (leader clustering, no chaining) | tables `edges`, `components`, `dedupe_clusters` |
| Search | natural-language + image-to-image (`photo_register.search`) | **Run live**: text query returned scored hits with captions; image query returned exact hit (1.0) + semantic neighbors (0.80) |
| Jev campaign columns | `jev_category` / `jev_confidence` per image | escalation-gate campaign artifacts (2026-10-13/15) |
| `docs/UI_RESEARCH.md` | FastAPI+React decision + 10 AI-native features + performance budget | spec only, build not green-lit |
| Engineering notes | `transformers>=4.57,<5` pin — **v5 broke the CLIP feature API** | Same break I hit and worked around in `experiments/embedding_bakeoff.py`; validates pinning this in photosearch too |

## Why this matters right now (mapped to open decisions)

1. **D1 bake-off (embedder migration): unblocked properly.** Our synthetic-media bake-off hit a fixture ceiling (all models tied, Recall@5 0.214). photo-register offers (a) a 158k real-distribution corpus, and (b) **verified content labels for photosearch's own media files via BLIP captions** — no more decorative-filename problem. Rerun `experiments/embedding_bakeoff.py` with BLIP-caption-derived fixtures for a decision-grade result.
2. **P0.1 caption index: instant scale seed.** photosearch's `photo_captions` DB + `CaptionSearchIndex` can be seeded for every overlapping path from `corpus_index.sqlite3` (one backfill script, zero model calls, ~all of media/ covered).
3. **Local captioning without Ollama: BLIP provider.** A working MPS captioner (`blip-image-captioning-base`, ~990M params, transformers already a photosearch dep). A `BlipVLMProvider` would give zero-setup local captions while the `gemma4:e4b` pull (D4) is pending — and a fallback tier after. Quality below Gemma-4, above nothing.
4. **Dedupe: 154,864 ready clusters + the leader-clustering algorithm** — photosearch's duplicates surface can read clusters for overlapping paths instead of recomputing; the no-chaining leader algorithm is the superior approach worth porting regardless.
5. **Register categories → smart collections/type filters:** a proven 6-way taxonomy with per-image confidence feeding photosearch's existing smart-collections surface.
6. **Product: `docs/UI_RESEARCH.md`'s 10 AI-native features** (semantic omnibox, find-more-like-this, relevance feedback, similarity journeys, dedupe review, crop-to-search, living collections) — directly relevant to photosearch's UI roadmap.

## Proposed integration (their README's path, concretized)

- **No code merge.** photosearch gains: (1) a one-time seed script `scripts/seed_captions_from_register.py` (reads corpus sqlite, upserts `photo_captions` + indexes via existing `/api/captions/reindex` logic); (2) optional `BlipVLMProvider` in `vlm_caption_service.py`; (3) bake-off fixtures generated from register captions; (4) dedupe-cluster import where paths overlap.
- **Preconditions to verify before any of it:** path-overlap statistics between photosearch's indexed set and the register corpus; BLIP caption license/quality spot-check on personal-photo class; staleness (register `processed_at` vs file mtimes).

## Decisions (owner)

> **UPDATE 2026-10-20 — R1 SHIPPED.** `scripts/seed_captions_from_register.py` seeds the canonical captions DB from the register snapshot (`experiments/register_captions_media_2026-10-20.jsonl`, 1062 captioned raster files) and embeds them into the caption index via EG-300m. Policy enforced: never overwrites user-edited captions, never replaces a stronger provider's generated caption unless `--force`. Ran live: 1062 stored, 1062 indexed (768-d, stamped), idempotent on rerun, searches verified over the full corpus (`'frog in a pond'` → the frog photo at 0.711). Two latent index bugs found and fixed by this work: per-row model stamp now reflects the *resolved* embedder (was `"unknown"` → reruns re-embedded everything), and `ensure_indexed` accepts the service's `updated_at` spelling (caption edits now re-embed via `/reindex`). `VLMCaptionService.store_generated_caption()` is the public on-ramp for externally-generated captions. R2's instrument (`experiments/caption_to_image_retrieval.py`) came out of the same workstream. R3–R5 remain open. **R4 UPDATE 2026-10-20:** shipped as `GET /api/duplicates/register` (`server/register_dedupe.py`, snapshot `data/register_dedupe_media.json` — regeneration command in the module docstring). Live-filtering drops deleted files; exemplar-first shape mirrors the register's leader clustering. Dev media/ contains only 1 multi-member cluster (synthetic renders); the surface matters on the real library. UI wiring into the duplicates panel deferred until real-library data exists (visual-evidence doctrine). R3/R5 remain open.

| # | Decision | Recommendation |
|---|---|---|
| R1 | Seed photosearch captions from the register | Yes — biggest immediate search-quality win available without any model pull |
| R2 | Rerun D1 bake-off with register-derived fixtures | Yes — replaces the fixture-ceiling result with decision-grade evidence |
| R3 | Add BLIP as a local caption provider | Yes as zero-setup tier; keep Ollama gemma4 as quality tier (D4) |
| R4 | Import dedupe clusters / port leader clustering | Yes for overlapping paths; port algorithm when photosearch dedupe is next touched |
| R5 | Adopt register categories in smart collections | Later — needs UI surfacing plan (visual-evidence doctrine applies) |

# EmbeddingGemma-300m vs CLIP text tower — caption-leg A/B (2026-10-20)

**Decision: SHIPPED.** The caption search index now embeds captions and queries with
`google/embeddinggemma-300m` (prompt-aware query/document encoding), falling back to
the app's CLIP generator when the gated model is unavailable (`CAPTION_EMBEDDING_MODEL=""`
forces the fallback). Evidence:

## A/B setup

- Corpus: **1064 real BLIP captions** for every captioned file under photosearch's own
  `media/`, sourced from `~/Projects/photo-register/data/corpus_index.sqlite3` (the
  decorative-filename problem is solved by using register captions, cross-checked
  earlier against an independent vision model).
- Queries: 7 natural-language queries targeting vision-verified content (wolf/coyote,
  surfer, laptop+coffee, tricycle, desert rock, harbor, university lawn).
- Metric: MRR / hit@k of the correct photo's caption against the full 1064-caption corpus.

## Results

| Model | MRR | hit@1 | hit@5 |
|---|---|---|---|
| CLIP ViT-B/32 text (old caption leg) | 0.274 | 1/7 | 3/7 |
| **EmbeddingGemma-300m (query/document prompts)** | **0.596** | **4/7** | **4/7** |

2.2× MRR. The motivating regression — CLIP ranking "a plate of food on a table" above
an actual wolf photo for "wolf forest animal" — is **fixed end-to-end in the shipped
pipeline**: with 300 register captions indexed through `CaptionSearchIndex`, the
coyote/wolf photo ranks **#1 at 0.609** (runner-up "a deer in the woods" at 0.477).

## Notes

- EG-300m is HF-gated; the operator unlocked it and `HF_TOKEN` now lives in the
  project `.env` (gitignored). First load downloads once, then cached.
- Corpus noise is real (one BLIP caption repeats "tri" 13×) — both models coped;
  caption backfill quality is a separate lever (R3/gemma4 recaption).
- **EG2 (google/embeddinggemma-2) does not load yet**: our sentence-transformers
  predates its `EmbeddingGemma2Processor`. Follow-up: bump sentence-transformers/
  transformers (mind the transformers<5 CLIP API pin) and rerun this A/B including
  EG2 — it could serve both image and caption legs in one space.
- Intent advisor (D5 second half): left on `all-MiniLM-L6-v2` (ungated → safe default
  for fresh installs without a token). `INTENT_EMBEDDING_MODEL=google/embeddinggemma-300m`
  is now available for an operator A/B; the caption leg was prioritized because its
  win was measured, not assumed.

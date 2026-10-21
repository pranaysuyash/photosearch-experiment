# OSS Model Integration Exploration — Gemma & Open-Source Models for PhotoSearch

- **Date:** 2026-10-19
- **Question explored:** How can Gemma / EmbeddingGemma and other open-source models make this app better?
- **Companion research:** [OSS_MODEL_LANDSCAPE_RESEARCH_2026-10-19.md](OSS_MODEL_LANDSCAPE_RESEARCH_2026-10-19.md) — every model fact (sizes, licenses, serving paths, gating) verified 2026-10-19 against primary sources.
- **Method:** Codebase AI/search surface mapped by repository exploration (file:line references spot-verified); combined with the landscape report. **No code changed in this exploration.**

---

## TL;DR — ranked opportunities

| # | Move | Why | Effort |
|---|------|-----|--------|
| 0 | **Wire the orphaned `photo_captions` table into search; repair the dead Ollama provider stub** | The app already generates captions and nothing uses them for retrieval; the local-captioning on-ramp exists but is unreachable. No new models needed. | S |
| 1 | **Local VLM captioning via Ollama — Gemma 4 E4B or Qwen3.5-4B** | Both Apache-2.0, multimodal, Metal-accelerated, ungated `ollama pull`. Matches the app's privacy-first identity (captions never leave the machine) and fills the `/ai/analyze` mock. | S–M |
| 2 | **Search embedding upgrade: CLIP ViT-B/32 → SigLIP 2, with a bake-off against EmbeddingGemma 2** | The 2021 CLIP-B/32 is the weakest link in search quality. EmbeddingGemma 2 (Sep–Oct 2026) is a single Apache-2.0 space for text+image+video+audio — the strategic bet. | M |
| 3 | **Video audio transcription (whisper.cpp / Moonshine / Gemma 4 E-sizes)** | Videos are ingested, keyframed, and face-tracked — but their audio is completely untouched. "Search what was said" is the largest missing feature class. | M |
| 4 | **Local intent-routing tier (EmbeddingGemma zero-shot now; fine-tuned 270M-class later)** | The router is pure keyword/regex; the only semantic escalation is a cloud API that is default-off. | M |

---

## 1. Where the app stands today (verified)

| Surface | Current implementation | Reference |
|---|---|---|
| Semantic search embeddings | CLIP ViT-B/32 (2021), 512-d, image + text, LanceDB (`photos` table), `min_score=0.22` floor | `server/embedding_generator.py:15`, `server/lancedb_store.py`, `server/api/routers/semantic_search.py:76-87` |
| Face pipeline | InsightFace `buffalo_l` (SCRFD detect + ArcFace 512-d) at runtime; CLIP fallback backend; optional MediaPipe/YOLO/remote backends | `src/face_embeddings.py:62-116`, `src/face_backends.py:67-125`, `server/config.py:31-51` |
| VLM captions | Cloud-first: Gemini default (`gemini-2.0-flash-exp`), OpenAI provider ("template"), **Ollama provider is a dead stub** (commented-out request + hardcoded error) | `server/vlm_caption_service.py:22-43, 220-229` |
| Caption storage | `photo_captions` SQLite table — **orphaned**: referenced only inside the caption service; exposed via `/api/captions/*` but never indexed or used by any search path | `server/vlm_caption_service.py:268`, `server/api/routers/captions.py` |
| Metadata search | Not SQLite FTS — full-table SELECT + Python filtering with a mini query language | `src/metadata_search.py:877` |
| Intent routing | Keyword (+1.25) / regex (+1.5) scoring over 12 intents; cloud `JevIntentAdvisor` (TypeSafe `jev-1.13.0`, ~311 ms) default-**off** | `src/intent_recognition.py:283-295`, `src/jev_intent_advisor.py:44-97` |
| OCR | Tesseract (images + video keyframes); EasyOCR handwriting path exists but only in an unmounted legacy module | `src/ocr_search.py`, `server/api/routers/ocr.py`, `src/enhanced_ocr_search.py` |
| Video | Ingested: metadata, keyframes, pHash scene detection, first-frame CLIP embedding, face tracking. **No audio analysis anywhere** (no whisper/vosk/STT reference in the repo) | `server/services/semantic_indexing.py:66-77`, `src/video_analysis.py`, `server/video_face_service.py` |
| AI analysis | `/api/ai/analyze` returns a **hardcoded mock** | `server/api/routers/image_analysis.py:45-52` |
| Model lifecycle | `ModelManager` registry/benchmarks/migrations — **face models only**; live version-string drift already exists (`arcface_r100_v1` in pipeline config vs `arcface_r50_v1` default in the vector store) | `server/model_manager.py:197-243`, `src/face_clustering.py:126` vs `server/lancedb_store.py:220` |

**Read on the state:** the app is architecturally ready for local OSS models — there is already a provider abstraction for captions, a backend chain for faces, a LanceDB store, and a model registry. The gaps are (a) the local provider stub is dead, (b) captions are produced but not consumed, (c) the search embedder is a 2021 model, (d) audio is unexplored, and (e) model versioning doesn't cover photo embeddings.

---

## 2. What changed in the landscape that makes this the right moment

(All sourced in the companion report.)

1. **Gemma 4 (March 2026) is Apache-2.0** — a real license change from Gemma 1–3's custom Terms (which carried a Prohibited-Use-Policy pass-through and a remote-restriction clause). E2B/E4B are multimodal **including native audio input (ASR)**. Ollama ships first-party MLX variants.
2. **EmbeddingGemma 2 (Sep–Oct 2026) is a multimodal embedder** — text, image, video, and audio in one 768-d MRL space, Apache-2.0, 740M total / 270M text-effective. This is the first credible single-space replacement for CLIP that also unlocks audio.
3. **Qwen3.5 (Feb–Apr 2026) supersedes Qwen3-VL** and is now the default small multimodal model on Ollama, llama.cpp, and mlx-vlm — Apache-2.0.
4. **Acquisition asymmetry:** all `google/gemma-3*` / `embeddinggemma-300m` HF repos are gated (verified 401s) and would need user consent + token for auto-download; **Ollama pulls are ungated** for the same models. For a first-run downloader, Ollama is the pragmatic artifact source.

---

## 3. Recommendations

### P0 — Unblock what already exists (no new models)

**P0.1 — Feed captions into search.**
The service writes `photo_captions` and nothing reads it for retrieval (`server/vlm_caption_service.py:268` is referenced nowhere else). Path:
- On caption generation, embed the caption text with the existing `EmbeddingGenerator` (CLIP text encoder) and store alongside/in the `photos` LanceDB table; OR add a `captions` vectors table keyed by path.
- Include caption-vector similarity in the `hybrid` merge (`server/api/routers/search.py:658-771`) with an intent-based weight like the existing metadata/semantic pair.
- Effect: every future caption source (cloud or local) instantly improves recall; also gives non-CLIP concepts (brands, book titles, situational context) a path into search that pure image embeddings miss.

**P0.2 — Repair `OllamaVLMProvider`.**
Lines `server/vlm_caption_service.py:220-229` contain a commented-out request and a hardcoded `{"error": "Ollama provider not yet implemented"}`. Implement the `/api/generate` call (the payload is already sketched in the comment), make the model configurable (`OLLAMA_VLM_MODEL`, defaulting to `gemma4:e4b` once P1 lands — today's `llava` default is a 2023-era model), and add an availability probe like the Gemini provider's.

### P1 — Local captioning & analysis (the "Gemma" headline)

- **Model:** `ollama pull gemma4:e4b` (Apache-2.0, text+image, 128K context, ~6.6–9.5 GB; first-party `-mlx` variant available). Low-RAM fallback: `gemma4:e2b` or `qwen3.5:2b`. Why Gemma 4 over Gemma 3 4B: strictly better benchmarks per the card, Apache-2.0 instead of Gemma Terms, and native audio for later. Why not SmolVLM2/Moondream: no official Ollama package / stale package + gated HF + unverified weight license (see report §4.5).
- **Wiring:** keep the `VLMProvider` ABC; flip the effective default to local-first with cloud as an explicit opt-in quality boost. This matches the app's privacy posture (face blur, privacy controls, local key manager) and the documented dual local/cloud plan (`docs/DUAL_LOCAL_CLOUD_PRODUCT_PLAN.md`); the Dec-2025 VLM strategy doc's cloud-first lean (Gemini 3 Flash) can remain the "quality tier" — captions are non-critical metadata, and a local 4B caption is good enough to be useful, offline and private.
- **Same provider fills `/api/ai/analyze`** (currently a mock, `server/api/routers/image_analysis.py:45-52`) and can power auto-tagging/albums.
- **Batch-captioning throughput:** for re-captioning a whole library, mlx-vlm's vision feature caching (~11× prompt tok/s, report §4.6) is the known optimization; start with Ollama, add an MLX serving path later behind the same provider interface.

### P2 — Search-quality embedding upgrade (CLIP is the weak link)

Current: CLIP ViT-B/32 — January 2021, English-only, 77-token text cap. The `0.22` score floor in the semantic router is a symptom of weak raw calibration, not a model property to preserve.

- **Path A (conservative): SigLIP 2** (`google/siglip2-base` or `so400m`, Apache-2.0, transformers-serving). Maintained successor class with better image-text alignment. Serving note: run via `transformers` (CLIP-style `get_image_features`/`get_text_features`); confirm sentence-transformers wrapper support before assuming a drop-in for `EmbeddingGenerator` (the report lists transformers/timm, not ST — verify).
- **Path B (strategic): EmbeddingGemma 2** — one 768-d MRL space for text+image+video+audio. If it holds up in a bake-off, it collapses P2 + part of P3 into a single index: image search without captions, multilingual text, and audio search share one store.
- **Do a bake-off before migrating anything.** Small eval harness in `experiments/` (the repo already has this pattern: `experiments/vector_store_faiss.py`): fixed query set (Jev fixtures + the real-query corpus — currently ~5 rows; capture is wired, revisit at ~50) scored against the operator's own library for CLIP-B/32 vs SigLIP2 vs EG2 retrieval quality and embedding throughput on this Mac.
- **Migration infrastructure (required either way):** generalize `server/model_manager.py` (face-only today) to photo embeddings; stamp model id + dimension + version on every vector row; re-index job with progress and rollback. The existing `arcface_r100_v1` vs `arcface_r50_v1` drift (`src/face_clustering.py:126` vs `server/lancedb_store.py:220`) is live evidence that unstamped versions rot silently.
- **Text-side quick win (after P0.1): EmbeddingGemma-300m** (<200 MB quantized, best open multilingual text embedder <500M on MTEB) for semantic matching over captions/notes/OCR text — 100+ languages where CLIP text is English-only. Caveats: Gemma-licensed + HF-gated (use Ollama's ungated `embeddinggemma:300m`), and **fp16 is unsupported — use bf16/fp32 on MPS**.

### P3 — New capability surfaces

- **P3.1 Audio transcription for videos.** Options: whisper.cpp (Metal + optional ANE, MIT), Moonshine (MIT models, streaming, tiny), or Gemma 4 E4B native audio (one model for captions + ASR, at VLM-serving cost). Store timestamped segments → metadata + vector index → "search what was said in videos." Largest genuinely new feature; the ingest pipeline already has the per-video hook points (`server/main.py:210-222`).
- **P3.2 Local intent-routing tier.** The keyword/regex router has documented failure modes (no-signal/tie → `camera`, substring false positives, bare-year blindness — `docs/JEV_INTENT_ROUTING_EXPLORATION_2026-10-13.md:30-42`). Local options, in order: (a) **EmbeddingGemma zero-shot** — embed the 12 intent label prompts, cosine against the query; no training data needed, handles paraphrase; (b) **fine-tune a 270M-class model** (Gemma 3 270M is explicitly positioned by Google for query routing) once the captured real-query corpus reaches ~50 rows; keep keyword scoring as the fast path and the cloud Jev advisor as optional escalation. Do not route every query through a general LLM — latency and cold-start cost aren't justified for a 12-class problem.
- **P3.3 OCR (optional upgrade).** Tesseract works today. If OCR latency/accuracy becomes a complaint, PaddleOCR 3.7 / PP-OCRv6 (claimed 6.1× on Apple M4 for the tiny tier, ONNX backend avoids the Paddle framework) is the drop-in class of upgrade. DeepSeek-OCR-class VLMs are overkill for photo text.
- **P3.4 Sensitive-content auto-detection.** Falconsai/nsfw_image_detection (Apache-2.0, ViT-base, 98% claimed eval accuracy) on ingest → auto-flag into the existing `/privacy/*` surface and face-blur flow. Coheres with the app's privacy-first identity; offline and free.

---

## 4. Serving architecture (pragmatic split)

| Class | Path | Rationale |
|---|---|---|
| Encoders (SigLIP2 / EG / EG-300m / NSFW ViT) | In-process `sentence-transformers`/`transformers` on MPS | No daemon, low latency, matches existing `EmbeddingGenerator` shape |
| Generative (captioning, analysis, optional ASR) | **Ollama** | The stub already targets it; ungated pulls for gated families; model management for free; Metal acceleration |
| Batch re-captioning (later) | mlx-vlm / Ollama `-mlx` variants | Vision feature caching (~11× prompt tok/s) matters at library scale |
| Model provenance | Extend `server/model_manager.py` to all models | Version-stamp every vector row; make re-index first-class |

---

## 5. Anti-recommendations (explicit)

- **Don't** use EmbeddingGemma-300m for image search — it is text-only.
- **Don't** migrate production embeddings to EmbeddingGemma 2 before the bake-off — it's weeks old and unproven for photo retrieval against CLIP-class models.
- **Don't** add jina-embeddings-v4 — Qwen Research License (non-commercial) per its card.
- **Don't** pick SmolVLM2 or Moondream for captioning — Qwen3.5/Gemma 4 cover the niche with official Ollama packages and cleaner licenses.
- **Don't** route every search query through an LLM — the intent problem is 12 classes; embeddings or a tiny fine-tune solve it at a fraction of the latency.

---

## 6. Licensing watch-list

| Item | Status | Action |
|---|---|---|
| InsightFace `buffalo_l` models | Code MIT, **weights non-commercial**; Nov 2025 update requires contacting `recognition-oss-pack@insightface.ai` for the open-source pack | Already shipped in this repo — fine for personal/local use; **must be cleared before any commercialization**; record in the model registry |
| Gemma 3 / 3n / EmbeddingGemma-300m | Gemma Terms of Use (Prohibited-Use pass-through, remote-restriction clause, Notice-file obligations) | Prefer Gemma 4 / EG2 (Apache-2.0) for new work; if using Gemma-3-family, satisfy Notice requirements |
| Gemma 4 / EmbeddingGemma 2 / Qwen3.5 / SigLIP 2 / Whisper / Moonshine / Falconsai | Apache-2.0 or MIT | Clean |
| rembg default model (bria-rmbg) | Weights carry commercial restrictions | Only relevant if background removal is ever added; pin `u2net`/`isnet` instead |
| PaddleOCR / Real-ESRGAN per-weight licenses | Code clean; weight terms not itemized upstream | Verify per-model before bundling |

---

## 7. Open questions

1. Tokens/sec for ≤4B VLMs **on this specific Mac** — no first-party figures exist; the bake-off script should measure it (cheap: Ollama/mlx-vlm both ship the models).
2. SigLIP 2 per-variant multilingual coverage (paper covers multilingual encoders; HF listing doesn't label variants).
3. sentence-transformers support status for SigLIP 2 / EmbeddingGemma 2 (determines whether `EmbeddingGenerator` needs a thin `transformers` wrapper instead of a model-name swap).
4. Whether EmbeddingGemma 2 can be served by Ollama for embedding (report found transformers/ST only) — affects the serving split.

---

## 8. Suggested next concrete steps

> **STATUS 2026-10-19 (same day, implementation pass):** P0.1, P0.2, P1, P2-infra, P3.2, P3.4 are **implemented and green** (suite 479/0); P3.1 is code-complete but **blocked by the Mimosa write-gate**. Full record: [OSS_MODEL_INTEGRATION_IMPLEMENTATION_2026-10-19.md](OSS_MODEL_INTEGRATION_IMPLEMENTATION_2026-10-19.md) — including open decisions D1–D7. The items below are superseded by that record's §1/§6.

1. **P0.1 + P0.2** (caption wiring + Ollama provider repair) — small, unblocks everything else, immediately useful even with today's cloud captions.
2. **Bake-off script** (`experiments/embedding_bakeoff.py`): CLIP-B/32 vs SigLIP2-base vs EG2 on this library + Jev fixtures; record embedding throughput on this Mac.
3. Decide P1 default model after seeing bake-off/latency numbers; wire `gemma4:e4b` as `OLLAMA_VLM_MODEL` default.

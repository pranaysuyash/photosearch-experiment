# Open-Source Model Landscape for the Photo Library App — Research Report

- **Date:** 2026-10-19
- **Scope:** Open-weight models relevant to a local-first photo library app on Apple Silicon (macOS), Python FastAPI backend, React/Tauri UI. Current stack in this repo (verified against code 2026-10-19): InsightFace `buffalo_l` (SCRFD + ArcFace 512-d) face detection/recognition with a CLIP fallback backend, CLIP ViT-B/32 image+text embeddings into LanceDB, cloud-first VLM caption service (Gemini default; OpenAI template; **Ollama provider is a dead stub**), Tesseract OCR, Python-filter metadata search, keyword/regex query-intent router with a default-off cloud advisory tier.
- **Method:** All claims below were verified on 2026-10-19 against primary sources only (official model cards on Hugging Face, GitHub repos, Google AI / Google Developers docs, Ollama library pages). Inline links point at the exact source used. Hugging Face's built-in web search was rate-limited during this session; discovery of newer models was done by fetching Hugging Face search/listing pages and official docs directly.
- **Notable headline finding:** Google shipped **Gemma 4** (March 2026) under **Apache-2.0** (a license change from the Gemma 1–3 custom terms), and **EmbeddingGemma 2** (Sept 2026), a multimodal embedding model, also Apache-2.0. Qwen shipped **Qwen3.5** (Feb–Apr 2026), a unified multimodal line that supersedes Qwen3-VL.

---

## Summary table

| Model | Task | Size | License | Serving path (Apple Silicon) | Photo-app use case |
|---|---|---|---|---|---|
| [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m) | Text embedding | 308M; 768-d, MRL to 512/256/128; <200 MB RAM quantized | Gemma Terms of Use (gated on HF) | sentence-transformers, Ollama (`embeddinggemma:300m`, 622 MB), MLX, llama.cpp | Embed text queries / captions / OCR text for vector search |
| [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2) | Multimodal embedding (text+image+video+audio) | 740M total, 270M text-only effective; 768-d, MRL 128–768 | **Apache-2.0** | transformers, sentence-transformers | Joint image+text embedding space → direct natural-language image search without captions |
| [google/siglip2-*](https://huggingface.co/google/siglip2-base-patch16-256) | Image↔text joint embedding | base 0.4B, large 0.9B, so400m 1B, giant-opt 2B | Apache-2.0 | transformers (PyTorch/MPS), timm | Zero-shot tagging, direct natural-language image search, near-dup/grouping embeddings |
| [openai/clip-vit-large-patch14](https://huggingface.co/openai/clip-vit-large-patch14) | Image↔text joint embedding (baseline) | ViT-L/14 ≈ 428M (1.71 GB F32) | MIT (repo) | transformers, open_clip | Legacy baseline for the above; English-only |
| [google/gemma-4 E2B/E4B](https://huggingface.co/google/gemma-4-E4B-it) | Multimodal gen (text+image; +audio on E-sizes) | E2B 5B / E4B 8B total (2B/4.5B effective); 12B; 26B-A4B MoE; 31B | **Apache-2.0** | Ollama (`gemma4:*`, incl. `-mlx` tags), llama.cpp GGUF, transformers, MLX | High-quality captioning / photo Q&A on-laptop; voice queries via native audio |
| [google/gemma-3 4B–27B](https://ai.google.dev/gemma/docs/core/model_card_3) | Multimodal gen (4B+) | 270M/1B/4B/12B/27B | Gemma Terms of Use | Ollama (`gemma3:*`), llama.cpp, MLX | Existing caption-service class of model; 128K context |
| [google/gemma-3n E2B/E4B](https://ai.google.dev/gemma/docs/gemma-3n) | On-device multimodal (audio+vision+text) | E2B ≈1.9B / E4B ≈4B effective | Gemma Terms of Use | Ollama (`gemma3n:*`), LiteRT, MLX, llama.cpp | Low-RAM captioning + speech transcription in one model |
| [google/gemma-3-270m(-it)](https://developers.googleblog.com/en/introducing-gemma-3-270m/) | Fine-tune target for small tasks | 270M (170M embedding + 100M transformer) | Gemma Terms of Use | Ollama (`gemma3:270m`, 292 MB), MLX, llama.cpp | Query-intent routing / classification after cheap fine-tuning |
| [Qwen/Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) | VLM caption/OCR/QA | 4.4B (≈8.9 GB BF16); 2B/4B/8B/32B dense; 30B-A3B/235B MoE | Apache-2.0 | Ollama (`qwen3-vl:2b` 1.9 GB, `4b` 3.3 GB, `8b` 6.1 GB), mlx-vlm | Captioning with strong OCR (32 languages), long-video understanding |
| [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | Unified multimodal gen (vision native) | 0.8B–397B-A17B; 4B ≈4.66B total | Apache-2.0 | Ollama (`qwen3.5:*` incl. `-mlx`), mlx-vlm, llama.cpp | Newest Qwen captioning/QA line; supersedes Qwen3-VL |
| [HuggingFaceTB/SmolVLM2-2.2B-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct) | Small VLM | 256M/500M/2.2B | Apache-2.0 | transformers; GGUF via llama.cpp; MLX conversions; no official Ollama pkg | Cheapest captioning tier; video frames |
| [moondream2 / moondream3](https://huggingface.co/models?search=moondream) | Small VLM | moondream2 1.8B; moondream3-preview / moondream3.1 9B-A2B | Code MIT (repo); HF repos gated (observed) | Ollama (`moondream:1.8b`, stale); mlx-vlm lists Moondream2/3 | Very fast short captions/QA |
| [openai/whisper](https://github.com/openai/whisper) | Speech-to-text | tiny 39M → large 1550M; turbo 809M | MIT | whisper.cpp (Metal/Core ML), faster-whisper (CTranslate2) | Video speech transcription for search |
| [moonshineai Moonshine](https://github.com/moonshine-ai/moonshine) | Speech-to-text (streaming) | tiny class (~27M-scale, "1 MB micro" models) | MIT (models); legacy non-English non-streaming models non-commercial | Python/WASM/iOS/Android/macOS runtimes | Real-time/edge transcription of video audio |
| [PaddleOCR 3.x](https://github.com/PaddlePaddle/PaddleOCR) | OCR / document parsing | PP-OCRv6 tiny 1.5M / small 7.7M / medium 34.5M; PaddleOCR-VL 0.9B–1.6 | Apache-2.0 (code) | Python (macOS supported); ONNX runtime backend | Text-in-photo / screenshot search |
| [deepseek-ai/DeepSeek-OCR(-2)](https://huggingface.co/models?search=deepseek-ocr) | Document-parsing VLM | 3B | Apache-2.0-class (see card; verify) | mlx-vlm (MLX 4–8-bit builds exist), GGUF | Screenshot/complex-layout OCR-to-markdown |
| [Tesseract 5.x](https://github.com/tesseract-ocr/tesseract) | Classic OCR | engine | Apache-2.0 | `brew install tesseract` | Simple flat-text screenshots, 100+ languages |
| [InsightFace buffalo_l](https://github.com/deepinsight/insightface) | Face detect + recognition | ArcFace 512-d embeddings; SCRFD/RetinaFace detection | Code MIT; **models non-commercial** (see §8) | ONNX Runtime; CoreML EP on macOS | **Already the runtime model in this repo** (face backends/embeddings); note the non-commercial model license |
| [dlib / face_recognition](https://github.com/ageitgey/face_recognition) | Face detect + recognition | 128-d embeddings (ResNet) | MIT | CPU | **Not in the current stack** (no dlib/face_recognition in requirements; runtime uses InsightFace buffalo_l); historical baseline, 99.38% LFW claim |
| [danielgatis/rembg](https://github.com/danielgatis/rembg) | Background removal | u2net … birefnet; default bria-rmbg ~1.0 GB | MIT (tool); weight-specific licenses vary | onnxruntime (CPU works on macOS) | Background removal for portraits/products |
| [xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Image super-resolution | x4plus, anime, general-x4v3 | BSD-3-Clause (code) | PyTorch; NCNN/Vulkan macOS binary | Upscale small/old photos for display or OCR |
| [Falconsai/nsfw_image_detection](https://huggingface.co/Falconsai/nsfw_image_detection) | NSFW binary classifier | ViT-base (~86M-class) | Apache-2.0 | transformers (MPS/CPU) | Sensitive-content filtering on ingest |
| [JohannesBuchner/imagehash](https://github.com/JohannesBuchner/imagehash) | Perceptual hashing | no NN | BSD-2-Clause | pure Python + Pillow/numpy/scipy | Exact/near-duplicate detection (paired with embeddings for semantic dups) |

---

## 1. Embedding models

### 1.1 EmbeddingGemma (google/embeddinggemma-300m) — Sep 2025
Source: [HF model card](https://huggingface.co/google/embeddinggemma-300m), [Google blog](https://developers.googleblog.com/en/introducing-embeddinggemma/)

- 308M params (302.9M in safetensors; ~1.21 GB F32 file). Native 768-d embeddings with **Matryoshka (MRL) truncation to 512 / 256 / 128** (re-normalize after truncation). 2K-token context. Trained on ~320B tokens, 100+ languages.
- MTEB multilingual (v2) mean 61.15 at 768d → 58.23 at 128d; blog claims "best open multilingual text embedding model under 500M params" on MTEB; blog also claims **<200 MB RAM with quantization** (QAT checkpoints in Q4_0/Q8_0 exist) and <15 ms embedding latency on EdgeTPU at 256 input tokens.
- **License:** `license: gemma` — gated on HF (must accept Google's terms); see §11 for Gemma terms.
- **Serving:** sentence-transformers is the primary supported library (`SentenceTransformer("google/embeddinggemma-300m")` with `encode_query`/`encode_document`); day-one support on Ollama, llama.cpp, MLX (per blog). Ollama package [`embeddinggemma:300m`](https://ollama.com/library/embeddinggemma) is 622 MB, 2K context, requires Ollama ≥ 0.11.10.
- **Gotcha:** the card states float16 is **unsupported** for this model — use float32 or bfloat16 (relevant if you run it via transformers on MPS, where fp16 is the common default).

### 1.2 EmbeddingGemma 2 (google/embeddinggemma-2) — NEW, Sept–Oct 2026
Source: [HF model card](https://huggingface.co/google/embeddinggemma-2) (repo created 2026-09-14, last modified 2026-10-06)

- This is the successor to EmbeddingGemma and is the newest official Google embedding model found. It is a **multimodal embedding model**: it maps text (incl. code), images, video, and audio into a single vector space.
- 740M total params (130M transformer backbone + 140M embedder = 270M text model), with optionally loaded 170M vision and 300M audio encoders. Native 768-d, MRL truncation to 128/256/512/768 ("up to 6x vector-storage reduction"; card says 128d is best for text-only workloads). 8,192-token shared context; images ≈280 tokens each, audio 25 tokens/s.
- MTEB multilingual v2 mean 61.36 (vs 61.15 for v1); large code-retrieval improvement (78.68 vs 68.76 NDCG@10).
- **License: Apache-2.0** (a change from v1's Gemma license).
- Supported libraries per card: transformers and sentence-transformers.
- **Photo-app relevance:** a single embedding space covering images *and* text enables caption-free natural-language image search (embed the photo, embed the query, compare directly), in a 0.74B-parameter package.

### 1.3 Qwen3-Embedding (June 2025) — strongest permissive alternative
Source: [Qwen/Qwen3-Embedding-0.6B card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

- Family: embedding + reranker at 0.6B / 4B / 8B. **Apache-2.0.** Released June 3–5, 2025; the 8B embedding model was ranked **No. 1 on MTEB Multilingual (70.58) as of June 5, 2025**.
- 0.6B: up to 1024-d with user-defined MRL dims 32–1024, 32K context, 100+ languages, instruction-aware queries (1–5% gain), last-token pooling.
- Frameworks: transformers ≥4.51, sentence-transformers ≥2.7, vLLM ≥0.8.5, TEI.

### 1.4 jina-embeddings-v4 — multimodal, but license caution
Source: [jinaai/jina-embeddings-v4 card](https://huggingface.co/jinaai/jina-embeddings-v4)

- ~3.8B params (built on Qwen2.5-VL-3B). Unified dense (single-vector) embeddings for text and images, 2048-d with MRL truncation to 128/256/512/1024; 128-d multi-vector (late-interaction) mode; 32,768 max sequence. Released May–June 2025.
- **License:** the card states the initial `CC-BY-NC-4.0` tag was an error and the correct license is the **Qwen Research License** (i.e., research/non-commercial terms inherited from the Qwen2.5-VL base). Treat as non-commercial unless separately cleared.

## 2. SigLIP 2 vs CLIP (caption-free image search)

### 2.1 SigLIP 2 (google/siglip2-*) — Feb 2025
Source: [google/siglip2-base-patch16-256 card](https://huggingface.co/google/siglip2-base-patch16-256), [HF listing of variants](https://huggingface.co/models?search=siglip2)

- Improves on SigLIP with added decoder loss, global-local + masked-prediction losses, and aspect-ratio/resolution adaptivity (incl. NaFlex variants). Pretrained on WebLI (up to 2048 TPUv5e chips). Supports zero-shot image classification and image–text retrieval; jointly aligned image/text embeddings.
- **Variants found (params):** base 0.4B (patch16 at 224/256/384/512 + NaFlex; patch32-256), large 0.9B (256/384/512), so400m 1B (patch14 224/384; patch16 256/384/512 + NaFlex), giant-opt 2B (256/384). The base card fetched lists ~375M params, 1.5 GB F32 file.
- **License: Apache-2.0.** Repo created 2025-02-17; paper arXiv:2502.14786 (Feb 20, 2025).
- Serving: transformers (`AutoModel`/`AutoProcessor`, `get_image_features()`); no Ollama package (Ollama does not serve bare CLIP/SigLIP encoders).
- Note: the variant listing fetched does not label any variant "multilingual"; the paper is titled for multilingual vision-language encoders and training is on WebLI — verify per-variant language coverage if multilingual query matching matters (see Known unknowns).

### 2.2 CLIP (openai/clip-vit-*) — the baseline, 2021
Sources: [HF card openai/clip-vit-large-patch14](https://huggingface.co/openai/clip-vit-large-patch14), [openai/CLIP GitHub](https://github.com/openai/CLIP)

- ViT-L/14: 427,616,846 params (~1.71 GB F32). Repo (code + weights) is **MIT**. Released January 2021; card notes the model "was not developed for general model deployment"; no longer actively developed (58 commits total, repo last modified 2023).
- English-only; 77-token text limit; card documents weaknesses on fine-grained classification/counting and known demographic bias disparities.
- Comparison status: still extremely widely used (7.3M downloads/month on the L/14 card) but it predates SigLIP 2's objective improvements and resolution/aspect adaptivity; SigLIP 2 is the maintained, Apache-2.0 option in the same model class. (No CLIP-vs-SigLIP2 benchmark comparison was made on either card; the relative-quality judgment here rests on SigLIP 2's stated design goals, not a benchmark we ran.)

## 3. Gemma family (captioning, on-device, routing)

### 3.1 Gemma 3 — Mar 2025
Source: [official model card](https://ai.google.dev/gemma/docs/core/model_card_3), [Ollama library](https://ollama.com/library/gemma3)

- Sizes: **270M, 1B, 4B, 12B, 27B**. Context: 128K for 4B/12B/27B; 32K for 1B/270M. **Multimodal (image input) at 4B+** (images normalized to 896×896, 256 tokens each); 1B/270M are text-only. 140+ languages. arXiv:2503.19786.
- **License: Gemma Terms of Use** (custom; see §11), gated on HF.
- Ollama tags: `270m` 292 MB, `1b` 806 MB (both text-only, 32K), `4b` 3.4 GB, `12b` 8.2 GB, `27b` 17 GB (all vision, 128K); QAT variants (`-it-qat`) with ~3× lower memory at similar quality.

### 3.2 Gemma 3n (E2B/E4B) — Jun 2025 (on-device line)
Source: [Google AI Gemma 3n docs](https://ai.google.dev/gemma/docs/gemma-3n), [Ollama library](https://ollama.com/library/gemma3n)

- MatFormer architecture with Per-Layer Embeddings (PLE): E2B loads >5B total params but runs at ≈**1.91B effective**; E4B nests E2B and runs ≈4B effective. 32K context. **Audio input (speech recognition, translation)** + vision via a **MobileNet-V5** encoder; audio/vision params can be conditionally skipped at load.
- Targets phones/laptops. Ollama tags `gemma3n:e2b` 7.8 GB and `e4b` 9.8 GB (32K, text+image); still receiving updates (tags updated days before this research date).
- License: Gemma Terms of Use. Availability per docs listing: HF/Kaggle/Ollama/Transformers/LiteRT-LM/MLX/llama.cpp.

### 3.3 Gemma 3 270M — Aug 14, 2025 (cheap fine-tune for routing)
Source: [Google Developers blog](https://developers.googleblog.com/en/introducing-gemma-3-270m/), [model card (sizes/context)](https://ai.google.dev/gemma/docs/core/model_card_3)

- 270M total = **170M embedding params (256k-token vocab)** + 100M transformer. Explicit intended uses: text classification, data/entity extraction, sentiment analysis, **query routing**, unstructured→structured text; Google positions it as "fine-tune a small specialist model rather than run a large general-purpose one."
- INT4 QAT checkpoints; the blog reports the INT4 model used **0.75% battery on a Pixel 9 Pro SoC across 25 conversations**. Text-only, 32K context.
- Available: HF (gated), Ollama (`gemma3:270m`, 292 MB), Kaggle, LM Studio, Docker; runs via llama.cpp, MLX, LiteRT, Keras; fine-tuning via HF/Unsloth/JAX.
- License: Gemma Terms of Use.

### 3.4 Gemma 4 — March 2026 (NEW)
Sources: [google/gemma-4-E4B-it card](https://huggingface.co/google/gemma-4-E4B-it) (repo created 2026-03-02; tech report arXiv 2607.02770), [Gemma 4 license page](https://ai.google.dev/gemma/docs/gemma_4_license), [Gemma terms page note](https://ai.google.dev/gemma/terms), [Ollama library](https://ollama.com/library/gemma4)

- Family: **E2B (5B total / ~2B effective), E4B (8B total / 4.5B effective), 12B Unified, 26B-A4B (MoE), 31B** — pre-trained and instruction-tuned, plus QAT/quantized variants (HF metadata `hasQuantizations: true`; unsloth/GGUF builds are visible in listings).
- Context: 128K for E2B/E4B; **256K for 12B/26B/31B**.
- Multimodal: **text + image at all sizes; the E2B/E4B add audio input (ASR + translation)**. Images support variable aspect ratio/resolution via token budgets (70–1120 tokens). "Unified" 12B naming suggests merged text/vision handling (card wording: "12B Unified").
- New capabilities vs Gemma 3/3n: configurable thinking modes, native function calling, interleaved multimodal input, hybrid attention (sliding window + global with p-RoPE). Card benchmarks: E4B 69.4% MMLU-Pro / 58.6% GPQA-Diamond vs Gemma 3 27B's 67.6% / 42.4%. 140+ languages pretrained, 35+ out of the box.
- **License: Apache-2.0.** The model card's license tag is `apache-2.0` and Google's Gemma terms page explicitly states Gemma 4 is under a separate Apache 2.0 license; the dedicated license page (`gemma_4_license`, last updated 2026-04-01) carries the standard Apache-2.0 text. This removes the custom Gemma restrictions (Prohibited Use Policy pass-through, remote-restriction right, etc.) for Gemma 4 — see §11.
- Ollama (`gemma4`, 27.3M downloads, updated ~2 weeks before research date): `e2b` 4.6–7.5 GB, `e4b` 6.6–9.5 GB, `12b` 7.7–8.0 GB, `26b` 16–19 GB, `31b` 19–20 GB, all text+image, **plus first-party MLX variants** (`gemma4:e2b-mlx` … `31b-mlx`) and cloud variants. HF shows official repos `google/gemma-4-31B-it` (8.97M downloads), `google/gemma-4-26B-A4B-it`, `google/gemma-4-E2B/-E4B(-it)`, `google/gemma-4-12B(-it-qat-gguf)`.

## 4. Small local VLMs for captioning (Apple Silicon)

### 4.1 SmolVLM2 (HuggingFaceTB) — Feb–Apr 2025
Source: [SmolVLM2-2.2B-Instruct card](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct), [HF listing](https://huggingface.co/models?search=smolvlm)

- Sizes: **256M, 500M (video), 2.2B** (all updated Apr 8, 2025). **Apache-2.0.** Tasks: captioning, VQA, "storytelling," video analysis, image comparison, OCR-ish text transcription.
- Footprint claims: "only 5.2 GB of GPU RAM for video inference" for the 2.2B (total safetensors ~9 GB F32). Libraries: transformers, vLLM, SGLang; MLX conversions exist under `mlx-community` (SmolVLM-4bit/6bit/8bit/bf16); **no official Ollama package** (only community uploads, per [Ollama search](https://ollama.com/search?q=smolvlm)). GGUF ports exist (ggml-org).
- No SmolVLM3 exists as of this research date (HF search returned none).

### 4.2 Qwen2.5-VL-3B — Jan 2025
Sources: [HF card](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct), [QwenLM/Qwen2.5-VL GitHub](https://github.com/QwenLM/Qwen2.5-VL)

- ~3.75B params BF16 (≈7.5 GB files). **Apache-2.0** (repo license). Released 2025-01-28 (tech report arXiv:2502.13923); 3B/7B/72B, later a 32B (2025-03-25).
- Native/dynamic resolution input with `min_pixels`/`max_pixels` controls; strong document claims (DocVQA 93.9, InfoVQA 77.1); invoice/form/table structured output; >1h video support. No Thinking variant.
- Ollama [`qwen2.5vl`](https://ollama.com/library/qwen2.5vl): `3b` 3.2 GB, `7b` 6.0 GB (125K context, vision); supported by mlx-vlm.

### 4.3 Qwen3-VL — Sep–Nov 2025
Sources: [Qwen3-VL-4B card](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct), [QwenLM/Qwen3-VL GitHub](https://github.com/QwenLM/Qwen3-VL), [Ollama library](https://ollama.com/library/qwen3-vl)

- Sizes (all Apache-2.0, Instruct + Thinking): Dense **2B, 4B, 8B, 32B**; MoE **30B-A3B, 235B-A22B**; FP8 variants. Release dates: 235B Sep 23, 2025 → 4B/8B Oct 15 → 2B/32B Oct 21 → tech report Nov 27, 2025.
- 4B ≈ 4.44B params (≈8.9 GB BF16 files). **Native 256K context, expandable to 1M** (YaRN). OCR expanded to **32 languages**, robust to blur/tilt/low light; long-video understanding with second-level indexing; 2D+3D grounding; visual-agent (GUI operation) claims.
- Ollama: `qwen3-vl:2b` 1.9 GB / `4b` 3.3 GB / `8b` 6.1 GB (256K, vision; requires Ollama ≥0.12.7); mlx-vlm supports the family.

### 4.4 Qwen3.5 — Feb–Apr 2026 (NEW, supersedes Qwen3-VL)
Sources: [Qwen/Qwen3.5-4B card](https://huggingface.co/Qwen/Qwen3.5-4B), [Ollama library](https://ollama.com/library/qwen3.5)

- Qwen3.5 is a **unified multimodal line** ("early fusion training on multimodal tokens"; image/video input by default, vision-language pipeline tag), and the 4B card states it "outperform[s] Qwen3-VL models across reasoning, coding, agents, and visual understanding."
- Sizes: **0.8B, 2B, 4B, 9B, 27B, 35B-A3B, 122B-A10B, 397B-A17B** (Base + post-trained + GGUF + MLX). 4B ≈ 4.66B total params. Context: **262,144 native, up to ~1.01M via YaRN**. Thinking mode on by default. **Apache-2.0** (4B card).
- Ollama (`qwen3.5`, updated ~2 weeks before research date): `0.8b` 1.2–1.3 GB, `2b` 2.7–3.1 GB, `4b` 3.3–4.0 GB, `9b` 6.6–7.6 GB, `27b` 17–20 GB, `35b` 22 GB — all text+image at 256K, all with vision/tools/thinking badges, plus **first-party `-mlx` variants**. llama.cpp's README uses `ggml-org/Qwen3.5-0.8B-GGUF` as its example pull, and mlx-vlm's benchmark section references Qwen3.5-4B — i.e., the small Qwen3.5 models are the current default on all three Mac serving paths.

### 4.5 Moondream — 2024 → 2026
Sources: [vikhyat/moondream GitHub](https://github.com/vikhyat/moondream), [HF listing](https://huggingface.co/models?search=moondream), [Ollama library](https://ollama.com/library/moondream)

- **moondream2** (1.8B, Apr 2024): captioning/QA/detection, "tiny VLM that runs anywhere." Code repo is **Apache-2.0** (GitHub). The HF repos `moondream/moondream2` and `vikhyatk/moondream2` now require authentication to fetch metadata via the API (observed `{"error":"Invalid username or password."}` — i.e., gated); Ollama's `moondream:1.8b` package (1.7 GB, 2K context) has not been updated in ~2 years.
- **Moondream 3 line (2026)**: `moondream/moondream3-preview` (9B, updated Apr 2026) and `moondream/moondream3.1-9B-A2B` (9B-A2B MoE, updated Jul 2026), plus `md3p-int4` (2B, Dec 2025). mlx-vlm lists Moondream2 and Moondream3 among supported families.
- The moondream org also now ships **ASR models**: `parakeet-redux` (0.1B) and `parakeet-ultra` (0.6B), updated ~1 month before research date.

### 4.6 Practical throughput data points found (sourced only)
From the [mlx-vlm README](https://github.com/Blaizzy/mlx-vlm) (Apple Silicon, Metal): Gemma-4-26B ≈ 50.3 tok/s prefill baseline / ≈31 tok/s generation in a multi-turn test; KV-cache quantization gave ~50→52.6 tok/s on gemma-4-26b-a4b at 20K context; **vision feature caching lifted prompt throughput from ~48 to ~550–825 tok/s (~11×)** (directly relevant to a batch-captioning pipeline over one library); speculative decoding up to 3.94× on 26B-A4B. No first-party tokens/sec figures were published for the ≤4B models on M-series chips; see Known unknowns.

## 5. Speech for video libraries

### 5.1 Whisper (openai/whisper) — MIT
Source: [GitHub README](https://github.com/openai/whisper)

- Sizes (README table): tiny 39M (~1 GB, ~10×), base 74M (~1 GB, ~7×), small 244M (~2 GB, ~4×), medium 769M (~5 GB, ~2×), large 1550M (~10 GB, 1×), **turbo 809M (~6 GB, ~8×)** — turbo is an optimized large-v3 with minimal accuracy loss and no translation. `.en` variants exist through medium. Code and model weights MIT.
- No macOS-specific guidance in the official repo (ffmpeg via Homebrew is the only note).

### 5.2 faster-whisper (SYSTRAN) — MIT
Source: [GitHub README](https://github.com/SYSTRAN/faster-whisper)

- CTranslate2 reimplementation: "up to 4× faster than openai/whisper with less memory"; int8 quantization further helps (benchmarks: large-v2 fp16 1m03s vs openai 2m23s on RTX 3070 Ti for 13 min audio; int8 CPU small on i7-12700K 1m42s, 1.5 GB).
- Supports named sizes incl. `turbo` and Distil-Whisper (`distil-large-v3`); any HF Whisper model convertible via `ct2-transformers-converter`. Latest referenced version v1.1.0. GPU docs are CUDA-centric; **no Apple GPU acceleration documented** (runs on CPU on macOS; PyAV handles audio decode without system ffmpeg).

### 5.3 whisper.cpp (ggml-org) — MIT — the Apple Silicon path
Source: [GitHub README](https://github.com/ggml-org/whisper.cpp)

- "Apple Silicon first-class citizen": inference runs fully on GPU via **Metal**; optional **Core ML encoder on the Apple Neural Engine (ANE)** gives ">3× faster" vs CPU; ANEForge claimed ~2× faster still for tiny–medium encoders. Integer quantization (e.g., Q5_0) supported. Whisper-family ggml models incl. large-v3-turbo (whisper-only; no other ASR families). MIT.

### 5.4 Moonshine (moonshine-ai) — MIT models, edge/streaming focus
Sources: [GitHub README](https://github.com/moonshine-ai/moonshine), [docs](https://moonshine-voice.readthedocs.io/en/latest/), [arXiv:2410.15608](https://arxiv.org/abs/2410.15608), [HF listing](https://huggingface.co/models?search=moondream) (moondream org)

- Now a full on-device voice toolkit (STT + intent + TTS) for Python/WASM/iOS/Android/macOS/Linux/Windows/RPi. **"The models are MIT by default … in every language and at every size"** — exception: legacy non-streaming non-English models remain under the non-commercial Moonshine Community License (listed in LICENSE).
- Claimed accuracy above Whisper Large V3 (Open ASR leaderboard) at the top end, and "tiny 1 MB" micro models at the bottom end. Original paper (Oct 2024): Moonshine Tiny achieves a **5× compute reduction vs Whisper tiny-en on 10-second segments** at equal WER, using variable-length input with no zero-padding and RoPE. STT languages: English, Spanish, Mandarin, Japanese, Korean, Vietnamese, Ukrainian, Arabic. The `moonshineai` HF org models returned auth errors to anonymous API access during this session (gated), so per-model cards could not be read.

## 6. OCR for screenshot / text-in-photo search

### 6.1 PaddleOCR — Apache-2.0 (code), very active
Source: [GitHub](https://github.com/PaddlePaddle/PaddleOCR)

- Current: **3.7.0 (2026-06-11)**. PP-OCR line now at **PP-OCRv6** with tiers tiny ~1.5M / small ~7.7M / medium ~34.5M params, one unified model covering 50 languages, and a claimed **6.1× inference speedup on Apple M4 (tiny)** vs prior. PP-StructureV3 for structure-aware image/PDF → Markdown/JSON. **PaddleOCR-VL** document-parsing VLM line (0.9B → 1.5 → 1.6; VL-1.6 reports 96.3% on OmniDocBench v1.6); HPD-Parsing high-throughput parsing (announced 2026-07-22). 100+ languages overall.
- macOS listed among supported OSes; switchable backends incl. **ONNX Runtime** (avoids the Paddle framework on Mac). Code Apache-2.0; the README page fetched shows no separate model-weight license terms — verify per-model when going beyond PP-OCR (see Known unknowns).

### 6.2 DeepSeek-OCR / DeepSeek-OCR-2 — document-parsing VLM, Mac-friendly ports exist
Source: [HF listing](https://huggingface.co/models?search=deepseek-ocr)

- `deepseek-ai/DeepSeek-OCR` (3B, Nov 4, 2025; 2.08M downloads) and `deepseek-ai/DeepSeek-OCR-2` (3B, updated Feb 2026; 573k downloads). mlx-vlm lists DeepSeek-OCR 1/2 among supported models; **mlx-community ships 4/5/6/8-bit MLX builds**, and `ggml-org` ships a GGUF — so it runs on Apple Silicon via MLX or llama.cpp-class runtimes.

### 6.3 EasyOCR — Apache-2.0, aging
Source: [GitHub](https://github.com/JaidedAI/EasyOCR)

- CRAFT detector + CRNN/ResNet-VGG recognizer, 80+ languages, `gpu=False` CPU mode. Latest release **1.7.2, Sep 24, 2024**; issues older than 6 months auto-closed; not archived but clearly in maintenance mode. Simple API; slower than the above options on CPU.

### 6.4 docTR (Mindee → t2k) — Apache-2.0
Source: [GitHub](https://github.com/mindee/doctr)

- Two-stage OCR: detection (DBNet, LinkNet, FAST) + recognition (CRNN, SAR, MASTER, ViTSTR, PARSeq, VIPTR), optional layout (LW-DETR) and table structure (TableCenterNet), plus a KIE predictor and FastAPI template. Now PyTorch-centric (README/Docker reference torch only); Python ≥3.11. No ONNX or macOS-specific notes found on the page fetched.

### 6.5 Tesseract 5.x — Apache-2.0, the classic baseline
Source: [GitHub](https://github.com/tesseract-ocr/tesseract)

- Stable major version 5 (5.0.0 Nov 2021; ongoing minor releases), 100+ languages, outputs text/hOCR/PDF/TSV/ALTO. Depends on Leptonica (BSD-2). Actively maintained (77.1k stars). No learning-based layout understanding; the standard choice only for simple flat screenshots.

## 7. Face recognition upgrade path

### 7.1 InsightFace (buffalo_l, ArcFace) — code MIT, **models non-commercial**
Sources: [GitHub README](https://github.com/deepinsight/insightface), licensing section of same

- Toolbox covering detection (SCRFD ICLR 2022; RetinaFace CVPR 2020) and recognition (ArcFace CVPR 2019 + Partial FC / SubCenter / VPL). ArcFace embeddings are the standard **512-d** (the README page fetched does not state the dimension; it is the canonical ArcFace output — see Known unknowns for citation to add).
- **Licensing (verbatim structure from README):** the *code* is MIT ("no limitation for both academic and commercial usage"), but "the training data containing personal information" and "the models trained with these data" are **"available for non-commercial research purposes only"** — this applies to models auto-downloaded by the Python package too. A **2025-11-24 update** tightens this further: for "open-sourced face recognition models (e.g., buffalo_l package)," you should contact `recognition-oss-pack@insightface.ai` for licensing. For a personal/local app this is materially more restrictive than MIT; for any commercialization path, buffalo_l requires a license conversation with the project.
- Still actively maintained: changelog includes an InsightFace Server release (2026-07-27, "AWS Rekognition alternative" with INT8) and a 2.1 PersonAnalysis update (2026-10-03) adding person detection/ReID. Inference is ONNX-based; the Python package supports **automatic CoreML/CUDA/CPU provider selection and reusable CoreML compilation caches** on macOS.
- dlib comparison: dlib's own example documents 128-d descriptors with a 0.6 Euclidean threshold and a 99.38% LFW figure ([dlib example](https://dlib.net/face_recognition.py.html)); the 512-d ArcFace models behind buffalo_l are the de-facto accuracy upgrade, subject to the license above.

### 7.2 face_recognition (ageitgey) / dlib — not in the current stack (historical baseline)
Source: [GitHub](https://github.com/ageitgey/face_recognition)

- MIT; wraps dlib's detector + shape predictor + ResNet face encoding model (128-d, per dlib docs above); 99.38% LFW claim. The repo shows 775 open issues / 57 open PRs with no visible recent release in the page snapshot — long in maintenance mode. (Its accuracy claim is dated relative to modern ArcFace systems; the task-comparison numbers themselves were not re-benchmarked here.)

## 8. Utility models

### 8.1 Background removal — rembg / U²-Net family
Source: [danielgatis/rembg](https://github.com/danielgatis/rembg)

- MIT tool (CLI/library/HTTP server/Docker) on ONNX Runtime (Python ≥3.11,<3.14; `rembg[cpu]`). Model menu: u2net, u2netp, u2net_human_seg, u2net_cloth_seg, silueta, isnet-general-use, isnet-anime, SAM, BiRefNet family (general/lite/portrait/dis/hrsod/cod/massive), and **bria-rmbg as the new default (~1.02 GB, 1024×1024)** — note RMBG-2.0 weights carry their own terms and "require a paid agreement for commercial use" per the README. No macOS-specific notes; CPU inference is the default path.

### 8.2 Upscaling — Real-ESRGAN
Source: [xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)

- Blind real-world super-resolution (ICCVW 2021; 37.1k stars). Code **BSD-3-Clause**; per-model weight licenses are not itemized on the repo page fetched (check release notes before bundling weights). Models: RealESRGAN_x4plus, realesrnet-x4plus, x4plus-anime, realesr-animevideov3, realesr-general-x4v3. Latest release v0.2.5.0 (NCNN binaries dated 2022) — stable but not actively developed. PyTorch path (basicsr/facexlib/gfpgan deps) plus portable **NCNN/Vulkan binaries for Windows/Linux/macOS**.

### 8.3 Sensitive-content detection — Falconsai/nsfw_image_detection
Source: [HF card](https://huggingface.co/Falconsai/nsfw_image_detection)

- ViT fine-tuned from `google/vit-base-patch16-224-in21k` (ViT-base ≈86M-class; exact count not stated on card), 224×224 input, binary **normal/nsfw**, trained on ~80k proprietary images, reported eval accuracy **98.04%** (52.5 samples/sec eval throughput). **Apache-2.0.** Runs via transformers (CPU/MPS).

### 8.4 Duplicate detection — perceptual hash + embeddings
Source: [JohannesBuchner/imagehash](https://github.com/JohannesBuchner/imagehash)

- **BSD-2-Clause**, pure Python (Pillow + numpy + scipy for pHash). Algorithms: average (aHash), perceptual (pHash), difference (dHash), wavelet (wHash), HSV color hash, and **crop-resistant hash** (added in 4.2; latest noted release 4.3 adds typing). Actively maintained (~3.9k stars).
- The complementary semantic-duplicate approach needs no new model: reuse the SigLIP 2 / EmbeddingGemma 2 image embeddings (cosine similarity) already covered in §1–2 for near-duplicate and visually-similar grouping.

## 9. Serving paths on Apple Silicon (verified state)

- **Ollama** (`ollama.com/library`): ships `gemma3`, `gemma3n`, `gemma4` (incl. `cloud` variants), `qwen2.5vl`, `qwen3-vl`, `qwen3.5`, `moondream`, `embeddinggemma`. Notably, Ollama now ships **first-party MLX-engine variants** (`gemma4:*-mlx`, `qwen3.5:*-mlx`) alongside GGUF. Pulls by name with no HF account; HF-gated repos (google/gemma-*) are mirrored on Ollama without that gating. No official `smolvlm` package (community uploads only).
- **llama.cpp** (MIT; [GitHub](https://github.com/ggml-org/llama.cpp)): "Apple silicon is a first-class citizen" (ARM NEON + Accelerate + **Metal** backend); GGUF format with 1.5–8-bit quantization; multimodal/VLM inference is a stated goal with image (stb) and audio (miniaudio) decoding in the multimodal subsystem; pulls models straight from HF (`-hf ggml-org/Qwen3.5-0.8B-GGUF` example) — gated HF repos require a token.
- **MLX** (MIT; [ml-explore/mlx](https://github.com/ml-explore/mlx)): Apple's array framework for Apple Silicon — NumPy-like API, lazy computation, dynamic graphs, **unified-memory arrays shared across CPU/GPU** (Metal acceleration). Ecosystem: `mlx-lm`, **[mlx-vlm](https://github.com/Blaizzy/mlx-vlm)** (MIT; supports Qwen2-VL/Qwen2.5-VL/Qwen3-VL, Gemma 3n, Gemma 4, EmbeddingGemma, Moondream 2/3, SmolVLM-adjacent families, DeepSeek-OCR 1/2, PaddleOCR-VL, and more), `mlx-community` HF org for converted weights, and mlx-vlm's built-in **OpenAI-compatible FastAPI server with continuous batching and prefix caching**.
- **transformers + PyTorch MPS**: officially supported backend — device string `mps`, package plain `torch` ([hardware table](https://huggingface.co/docs/transformers/main/en/hardware)); `device_map="auto"` detects Apple Silicon/MPS. Good default for encoder models (SigLIP 2, CLIP, ViT NSFW classifier, dlib-adjacent work stays CPU/CoreML). Watch the EmbeddingGemma fp16-unsupported note (§1.1).
- **sentence-transformers**: the primary library for EmbeddingGemma (§1.1) and ≥2.7 supports Qwen3-Embedding (§1.3); works over torch CPU/MPS.
- **ONNX Runtime**: the transport for rembg and InsightFace (with **CoreML execution provider** auto-selection + CoreML compile caches on macOS, per the InsightFace README).

**Model-acquisition / first-run auto-download:** HF-hub-based libraries auto-download on first `from_pretrained` into the local HF cache (see [HF docs](https://huggingface.co/docs/hub/en/models-downloading): integrated-library loading, `hf download`, xet-backed repos with adaptive concurrency, and the proxy allowlist hostnames). **Gated models** (all `google/gemma-*` embedding/Gemma-3 repos, moondream/moonshine orgs as observed) require the user to accept terms on huggingface.co and supply a token *before* the app can auto-download them. Ollama pulls (`ollama pull gemma3`) work without an HF account. This distinction should drive which artifact source a first-run downloader uses.

## 10. Gemma license terms summary (for bundling Gemma-licensed models)

Sources: [Gemma Terms of Use](https://ai.google.dev/gemma/terms) (Gemma 1/2/3/3n, PaliGemma, CodeGemma, ShieldGemma…), [Gemma 4 license page](https://ai.google.dev/gemma/docs/gemma_4_license)

**Applies to:** Gemma 3 (incl. 270M), Gemma 3n, EmbeddingGemma-300m. **Does NOT apply to Gemma 4 or EmbeddingGemma 2, which are Apache-2.0.**

- Commercial use permitted; derivatives permitted; Google claims no rights in outputs. **"Model Derivatives" explicitly include models trained via distillation or synthetic outputs from Gemma** — a fine-tune trained on Gemma outputs stays under these terms.
- Redistribution obligations: pass the use restrictions downstream as enforceable terms, provide recipients the agreement, mark modified files, include a Notice file stating the model is subject to Gemma Terms of Use.
- Restrictions: must comply with the incorporated **Gemma Prohibited Use Policy** and applicable law; Google "reserves the right to restrict (remotely or otherwise) usage" it believes violates the agreement; on breach/termination you must delete and cease distribution of copies. No trademark rights. No express patent grant (unlike Apache-2.0). California law, Santa Clara County jurisdiction.
- Practical delta vs Apache/MIT for a personal/local photo app: the main obligations are attribution/Notice and the Prohibited-Use-Policy pass-through; the remote-restriction and termination clauses are the unusual parts.

## 11. Known unknowns / to verify

1. **Tokens/sec for ≤4B VLMs on specific M-series chips.** Only large-model figures (Gemma-4-26B ~50/31 tok/s, mlx-vlm benchmarks) were found on primary pages. For planning caption throughput you'd need your own benchmark of Qwen3.5-4B/Qwen3-VL-4B/Gemma-4-E4B 4-bit on the target Mac — mlx-vlm and Ollama both ship these, so the benchmark is cheap to run.
2. **SigLIP 2 multilingual coverage per variant.** The HF listing does not label variants multilingual; the paper covers multilingual encoders and training is on WebLI. If non-English query→image matching without captions matters, confirm on the paper/model cards which variants are multilingual.
3. **InsightFace buffalo_l exact composition (det_10g.onnx + w600k_r50, 512-d)** — the wiki page fetch did not return the table; the 512-d ArcFace dimension is standard but should be re-cited from the Model-Zoo wiki directly. Also obtain the current buffalo_l licensing response from `recognition-oss-pack@insightface.ai` if commercial use is ever contemplated.
4. **Qwen2.5-VL license text**: Apache-2.0 per the QwenLM/Qwen2.5-VL repo license badge (fetched via the Qwen3-VL repo page); the HF card itself doesn't inline the license. Non-controversial but worth a 1-minute confirm when pinning.
5. **PaddleOCR per-model weight licenses** (especially PaddleOCR-VL line) — code is Apache-2.0; the README page fetched carries no model-zoo license table.
6. **Real-ESRGAN weight licenses per checkpoint** (repo page does not itemize; historically some anime weights differ).
7. **Moondream2/3 HF license & gating**: HF API returns auth errors anonymously (gated). The GitHub code repo is Apache-2.0/MIT-labeled in the fetched summary, but the weight-repo license was not readable. Confirm the weight license before bundling.
8. **Moonshine per-model parameter counts and Mac latency**: docs page fetched only claims "1 MB micro models" and leaderboard-topping accuracy; exact current model lineup lives in linked docs not fetched.
9. **Gemma 4 E2B exact effective-parameter figure** — E4B is documented at 4.5B effective/8B total; E2B's "2B effective/5B total" comes from HF listing labels and the Gemma-3n pattern, not a Gemma-4 card sentence we retrieved.
10. **faster-whisper on Apple GPU**: CTranslate2 Metal support is not documented in the fetched README; whisper.cpp is the verified Apple-GPU path for Whisper.
11. **Whether Ollama now serves anything for CLIP/SigLIP-class encoders** — as of this research, no; direct-caption-free search would run via transformers/MLX.
12. **Gemma 4 gated status on HF**: official `google/gemma-4-*` repos did not throw 401 on the search listing, but per-repo gating wasn't explicitly tested; Ollama mirror is ungated regardless.

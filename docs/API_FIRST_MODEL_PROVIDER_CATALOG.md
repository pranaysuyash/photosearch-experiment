# Living Museum — API‑First Model/Provider Catalog (Deeper, Non‑Exhaustive)

This is a companion to `FEATURE_PACKAGE_MODEL_OPTIONS.md`. It intentionally focuses on **hosted APIs / managed services** to reduce ops and (often) cost versus running/maintaining your own GPU stack. Local models are included only when they are **small, low-friction, and operationally “cheap”**.

This is **not exhaustive**. It is designed to give you a robust “swap menu” later when you want to upgrade quality, reduce infra, or change vendors.

---

## How To Choose (API‑First Decision Guide)

### 1) What you’re optimizing for
- **Lowest ops / fastest iteration**: hosted model APIs (OpenAI, Google, AWS, Azure) or “model hosting platforms” (Replicate, HF Inference/Endpoints).
- **Lowest unit cost at large scale**: depends on volume. APIs can be cheaper at low/medium volume; self-host can be cheaper once you have steady high throughput.
- **Best quality regardless of cost**: use top-tier hosted vision models for captions/understanding + strong embedding pipelines.
- **Best privacy/data control**: local models or dedicated single-tenant endpoints.

### 2) The break‑even math (rough)
To compare **API** vs **hosting**:
- **API monthly cost** ≈ `(images_processed_per_month * $/image)` + `(tokens_processed * $/token)` + storage/egress.
- **Self-host monthly cost** ≈ GPU instance(s) + storage + engineering time + scaling + failure handling.

If you don’t have stable, high-volume throughput, APIs usually win on “all-in cost” because they avoid:
on-call, GPU driver issues, model serving, batching/queuing, autoscaling, cold-start mitigation, and observability.

### 3) Vendor lock-in strategy (recommended)
Design each AI feature behind an interface:
- **Detector** (faces/objects/layout) → returns boxes + scores
- **Embedder** (image/text) → returns vectors + model ID/version
- **OCR** → returns text + regions + confidence
- **Captioner/VLM** → returns caption + tags + structured JSON

Always store:
- `provider`, `model_name`, `model_version` (if available), `timestamp`, and `input_hash`.

---

## API Aggregators + Model Hosting Platforms (Relevant to This App)

These are especially useful if you want to avoid self-hosting, want access to many models quickly, or want routing/failover without wiring every vendor separately. They can be used alongside (not instead of) the “major clouds” (OpenAI/Google/AWS/Azure) already listed in this doc.

### OpenRouter (aggregator / routing layer)

- Site/docs: https://openrouter.ai/docs
- What it is:
  - A unified API over many model providers (including closed and open models), with optional routing and fallback behavior.
- Why it’s relevant for Living Museum:
  - Rapidly compare **vision-capable chat/VLM models** for captions, “AI insights”, story summaries, search query rewriting.
  - Reduce vendor lock-in by keeping one client integration while swapping models/providers behind it.
- Things to watch:
  - **Vision support varies by model**; you’ll still need a capability matrix (image input, JSON mode, tool calling, etc.).
  - Data handling depends on the downstream model/provider; review policies for your privacy posture.

### Replicate (API for many open models)

- Docs: https://replicate.com/docs
- What it is:
  - “Model catalog + pay-per-run” hosted inference for a wide range of open-source models.
- Why it’s relevant:
  - Great for quick product experiments: OCR VLMs, captioning VLMs, upscalers, background removal, etc.
  - Useful when you want to try open models (e.g., the OCR/VLM families listed below) without standing up GPUs.
- Things to watch:
  - Cold starts / queueing can matter for interactive UX; best used for background jobs (indexing/insights generation).

### fal (serverless GPU inference / model endpoints)

- Platform: https://fal.ai/
- Docs (may be behind anti-bot protections in some environments): https://docs.fal.ai
- What it is:
  - A serverless GPU inference platform (often used for image/video model endpoints).
- Why it’s relevant:
  - Very practical for “media transforms” adjacent to search:
    - super-resolution, deblurring, background removal, face restoration, etc.
  - Can be used to host open VLM/OCR workflows depending on current catalog/endpoint support.
- Things to watch:
  - Model availability changes; treat it as a “platform option” rather than a single-model dependency.

### Together AI (hosted inference for open models)

- Site: https://www.together.ai/
- Docs: https://docs.together.ai/
- What it is:
  - Hosted inference for many open models (LLMs and, depending on current catalog, some multimodal/VLM).
- Why it’s relevant:
  - Good for running open models behind an API without maintaining GPUs.
  - Useful for “caption → embed” pipelines if you keep embeddings API-based too.

### Fireworks AI (hosted inference + serving)

- Site: https://fireworks.ai/
- Docs: https://docs.fireworks.ai/
- What it is:
  - Hosted inference/serving platform, optimized for low latency and production deployment.
- Why it’s relevant:
  - Strong option when you want to productionize a chosen open model family with better latency/throughput.

### “Bring your own model” managed hosting (if you need custom fine-tunes)

If you later want your own fine-tuned captioner/tagger/OCR model but still don’t want to operate GPUs directly:
- Hugging Face Inference Endpoints: https://huggingface.co/inference-endpoints
- (Other managed hosts exist; choose based on region/security/compliance needs.)

---

## Catalog by Capability

### “Small Local” Fallbacks (Low Ops, CPU‑Friendly)

If you want to keep a low-cost baseline on your server (no GPUs, minimal deps) and only “burst” to APIs for premium quality, these are common, low-friction local options:

- **Text embeddings (for captions/notes/tags search)**:
  - Small SentenceTransformers models (MiniLM-class) on CPU (fast, cheap).
  - Practical when you do Pattern A2 (caption → text embedding) and want to avoid paying for embedding APIs.
- **Image embeddings (basic visual similarity)**:
  - Smaller CLIP/OpenCLIP variants (ViT-B/32-class) can run on CPU but are slower per image than text-only.
  - If you need CPU-only, consider ONNX-exported variants for `onnxruntime` (batching matters a lot).
- **OCR (printed text)**:
  - Tesseract remains the simplest offline baseline; call cloud OCR only for low-confidence cases.
- **Face detection (detection-only)**:
  - MediaPipe can be a low-friction detector if you want “people boxes” without full embedding/clustering.

The general pattern:
1) run local baseline → 2) measure confidence/quality → 3) reprocess “hard cases” via API.

---

## Notable “Capable” Open Models To Host (HF/GitHub) — Curated, API‑Friendly

You asked specifically about **Moondream**, **Qwen‑VL**, and **Chandra OCR**. They are included here with direct links, along with other widely used, strong families. The intent is: if you later decide “cost isn’t an issue”, you have a ready shortlist to host via:
- Hugging Face Inference Endpoints (dedicated): https://huggingface.co/inference-endpoints
- Hugging Face Inference API (shared): https://huggingface.co/docs/api-inference/
- Replicate: https://replicate.com/
- Any managed GPU host you prefer (Together/Fireworks/etc., depending on current catalogs)

### 1) Small VLMs (cheap-ish to run; also easy to host)

- **Moondream**
  - GitHub: https://github.com/vikhyat/moondream
  - HF models:
    - `vikhyatk/moondream2`: https://huggingface.co/vikhyatk/moondream2
    - `moondream/moondream3-preview`: https://huggingface.co/moondream/moondream3-preview
  - Why it’s useful here:
    - good “fast captioning / quick Q&A / lightweight OCR-ish” option
    - tends to be operationally simpler than large VLMs

### 2) General-purpose VLMs (strong quality; bigger; good for captions + structured insights)

- **Qwen‑VL family (Qwen2‑VL / Qwen2.5‑VL / Qwen3‑VL)**
  - GitHub (Qwen3‑VL): https://github.com/QwenLM/Qwen3-VL
  - HF:
    - `Qwen/Qwen2-VL-7B-Instruct`: https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct
    - `Qwen/Qwen2.5-VL-7B-Instruct`: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
  - Why it’s useful here:
    - strong “caption + reasoning + extraction” performance
    - can power “AI Insights”, story summaries, tag suggestions, and OCR-like extraction with prompting

- **InternVL family**
  - HF (example):
    - `OpenGVLab/InternVL3-14B`: https://huggingface.co/OpenGVLab/InternVL3-14B
  - Why it’s useful here:
    - strong general VLM; good candidate for “premium” insights/captions

- **Idefics2 (Hugging Face M4)**
  - HF:
    - `HuggingFaceM4/idefics2-8b`: https://huggingface.co/HuggingFaceM4/idefics2-8b
  - Why it’s useful here:
    - solid open VLM with a production-friendly ecosystem around it

- **Florence‑2 (Microsoft)**
  - HF:
    - `microsoft/Florence-2-large`: https://huggingface.co/microsoft/Florence-2-large
    - `microsoft/Florence-2-base`: https://huggingface.co/microsoft/Florence-2-base
  - Why it’s useful here:
    - “any-to-any” vision model; strong for extraction-style tasks

- **MiniCPM‑V (OpenBMB)**
  - HF:
    - `openbmb/MiniCPM-V-4_5`: https://huggingface.co/openbmb/MiniCPM-V-4_5
    - `openbmb/MiniCPM-V-2_6`: https://huggingface.co/openbmb/MiniCPM-V-2_6
  - Why it’s useful here:
    - strong OCR + multi-image + vision chat capability in a relatively compact family

### 3) OCR-specialist VLMs (if OCR accuracy is a priority)

- **Chandra OCR**
  - HF:
    - `datalab-to/chandra`: https://huggingface.co/datalab-to/chandra
    - Example GGUF quantization: https://huggingface.co/noctrex/Chandra-OCR-GGUF
  - Why it’s useful here:
    - OCR-focused VLM (good when Tesseract is not enough and you want a model-first OCR approach)

- **GOT‑OCR 2.0**
  - HF:
    - `stepfun-ai/GOT-OCR2_0`: https://huggingface.co/stepfun-ai/GOT-OCR2_0
  - Why it’s useful here:
    - strong OCR VLM; good candidate for a “premium OCR” tier

### 4) Image/Text Embedding Models (for semantic search, similarity, dedupe via embeddings)

If you prefer hosting embeddings instead of paying per-call to embedding APIs, these are common, capable open options:

- **CLIP (baseline)**
  - HF:
    - `openai/clip-vit-base-patch32`: https://huggingface.co/openai/clip-vit-base-patch32
    - `openai/clip-vit-large-patch14`: https://huggingface.co/openai/clip-vit-large-patch14

- **SigLIP / SigLIP2 (Google)**
  - HF:
    - `google/siglip-so400m-patch14-384`: https://huggingface.co/google/siglip-so400m-patch14-384
    - `google/siglip2-so400m-patch14-384`: https://huggingface.co/google/siglip2-so400m-patch14-384

- **Jina CLIP v2 (multilingual, retrieval-oriented)**
  - HF:
    - `jinaai/jina-clip-v2`: https://huggingface.co/jinaai/jina-clip-v2

- **Nomic vision embeddings**
  - HF:
    - `nomic-ai/nomic-embed-vision-v1.5`: https://huggingface.co/nomic-ai/nomic-embed-vision-v1.5

### 5) Notes on “capable”

“Capable” changes quickly in open vision. The goal here is to include:
- families that are widely adopted and actively maintained,
- options that are straightforward to host behind an API,
- coverage across: captions/insights, OCR, and embeddings.

If you want, I can keep this section updated as a “rolling shortlist” and add:
- recommended prompts/output schemas for each model family (caption/tags/JSON),
- typical latency/cost expectations per provider (HF Endpoint vs Replicate vs cloud),
- a suggested default stack per tier (Free/Basic/Pro).

### A) Image↔Text Embeddings (Semantic Search Core)

You currently use a local CLIP variant (`clip-ViT-B-32` via `sentence-transformers`). API-first options fall into two practical patterns:

#### Pattern A1: True multimodal embedding endpoint (best when available)
Use a provider that can embed images and text into the same space directly.

Provider categories to evaluate:
- **OpenAI** (check latest embedding + multimodal/vision embedding offerings)
  - https://platform.openai.com/docs
- **Google Vertex AI** (multimodal embeddings / vision models)
  - https://cloud.google.com/vertex-ai
- **AWS Bedrock** (embeddings + multimodal offerings depending on region/model availability)
  - https://aws.amazon.com/bedrock/
- **Azure AI** (vision + embeddings depending on product lineup)
  - https://learn.microsoft.com/azure/ai-services/

Pros:
- simplest pipeline (image → embedding)
- consistent cross-modal semantics

Cons:
- may have fewer “true multimodal embedding” choices than you expect (often you end up in Pattern A2)

#### Pattern A2: Caption → Text Embedding (very common, cost-flexible)
Use a strong vision-capable model to produce:
- caption / dense description
- tags/entities/places/people (if allowed)
Then embed the text using a cheap text embedding model.

Providers for captioning/VLM:
- OpenAI vision models: https://platform.openai.com/docs
- Google Gemini: https://ai.google.dev/
- AWS Bedrock multimodal models: https://aws.amazon.com/bedrock/
- Azure vision / multimodal: https://learn.microsoft.com/azure/ai-services/
- Replicate (many open models behind API): https://replicate.com/
- Hugging Face Inference API / Endpoints: https://huggingface.co/docs/api-inference/

Providers for text embeddings:
- OpenAI embeddings: https://platform.openai.com/docs/guides/embeddings
- Cohere embeddings: https://docs.cohere.com/
- Voyage AI embeddings: https://docs.voyageai.com/
- Jina AI embeddings: https://jina.ai/embeddings/
- Google Vertex embeddings: https://cloud.google.com/vertex-ai

Pros:
- often cheaper than high-dim image embeddings for large libraries (text is smaller and reusable)
- supports hybrid search (metadata + caption text + tags)

Cons:
- quality depends on captioner; captions can be “generic” unless prompted well

#### Pattern A3: Hosted Open-Source CLIP/SigLIP (when you want “local model quality” but no ops)
Instead of self-hosting, rent inference:
- **Hugging Face Inference Endpoints** (dedicated): https://huggingface.co/inference-endpoints
- **Replicate** (shared infra): https://replicate.com/
- **Together / Fireworks / other model hosts** (availability varies): check provider catalogs

This is often a sweet spot: you can pick the exact open model family you want, without running GPUs yourself.

---

### B) Vision LLMs (Captions, Tags, “AI Insights”, Story Summaries)

This repo currently stores insights (DB + endpoints) but doesn’t strongly commit to a specific VLM model for generation. If you want API-first “insights” later, this is where you get the biggest quality jump.

What to generate (recommended structured outputs):
- `caption_short`, `caption_dense`
- `tags` (objects, scene, activity)
- `location_hint` (if visible; never trust blindly)
- `people_count` (avoid naming identities unless user-provided)
- `aesthetic_score` (optional heuristic)
- `suggested_album_rules` (for smart albums)

Top provider categories:
- OpenAI vision models: https://platform.openai.com/docs
- Google Gemini vision: https://ai.google.dev/
- AWS Bedrock: https://aws.amazon.com/bedrock/
- Azure: https://learn.microsoft.com/azure/ai-services/

Model-hosting platforms (open models, fast iteration):
- Replicate: https://replicate.com/
- Hugging Face Inference API/Endpoints: https://huggingface.co/docs

Practical open-model families to track (via HF/GitHub, then host via HF/Replicate):
- Qwen-VL family (vision-language)
- LLaVA family (vision-language)
- InternVL family (vision-language)
- Florence-style models (vision captioning/understanding)

Why this matters for cost:
- You can run **insights generation only once per image** (or per “best-of” subset), store results in SQLite, and then search cheaply forever after.

---

### C) OCR (Printed Text, Layout, Handwriting)

Current approach is local-first (Tesseract + optional EasyOCR). API-first OCR is often cheaper than running GPUs and gives better quality on messy inputs.

Hosted OCR leaders:
- **Google Cloud Vision OCR** (strong general OCR):
  - https://cloud.google.com/vision
- **AWS Textract** (excellent for documents/forms, structured extraction):
  - https://aws.amazon.com/textract/
- **Azure AI Vision / Read** (strong enterprise OCR):
  - https://learn.microsoft.com/azure/ai-services/computer-vision/

When to still keep local OCR:
- If you only OCR a small subset (e.g., user‑selected images), local Tesseract is “cheap enough.”
- If you need always‑offline mode.

Hybrid approach (recommended):
- Default to local OCR for low-volume / offline.
- Offer “Upgrade OCR quality (cloud)” toggle for hard cases or premium tiers.

---

### D) Face Detection + People (Detection, Embeddings, Clustering)

You currently do on-device face embeddings via InsightFace (and DBSCAN clustering). If you want an API-first option later:

Hosted face APIs:
- **AWS Rekognition** (faces, similarity search/indexing, attributes):
  - https://aws.amazon.com/rekognition/
- **Google Cloud Vision** (face detection; identity features differ by product/policy):
  - https://cloud.google.com/vision
- **Azure Face / Vision** (availability/policies vary by region/time; verify current offering):
  - https://learn.microsoft.com/azure/ai-services/

Important tradeoffs:
- Cloud APIs may be the easiest path to robust detection, but “people clustering” implies storing face features remotely; this can be a product/privacy decision.
- If you keep clustering local but want detection API-first:
  - You still need **embeddings**. Many APIs provide face features, but portability differs.

Operationally simple “small local” option (if you avoid cloud for faces):
- Keep InsightFace local (already integrated), but avoid heavy custom model downloading (you already moved toward `buffalo_l` model zoo usage in `src/face_backends.py`).

---

### E) Duplicate Detection (Exact + Near + Similar)

This feature is typically best done locally because:
- exact hashing is trivial CPU work,
- perceptual hashing is lightweight,
- sending full images to a cloud “duplicate API” is rarely cost-effective.

API-first angle that *can* make sense:
- If you already generate **embeddings via a hosted service**, you can use vector similarity to propose “near duplicates” cheaply without running your own vision model.

Practical strategy:
- Use local file hash (exact) + local perceptual hash (fast) for baseline.
- Use your semantic/visual embeddings (from wherever) to propose “visually similar” groups for UI review.

---

### F) Vector DB as a Managed Service (If You Don’t Want to Run LanceDB)

You currently use LanceDB locally. If you want API-first and managed:
- Pinecone: https://www.pinecone.io/
- Weaviate Cloud: https://weaviate.io/
- Qdrant Cloud: https://qdrant.tech/
- Zilliz Cloud (Milvus): https://zilliz.com/
- Managed Postgres + pgvector (Supabase/Neon/RDS): https://supabase.com/ / https://neon.tech/ / https://aws.amazon.com/rds/postgresql/

Selection notes:
- If you need strong metadata filters + vector search, Qdrant/Weaviate are commonly chosen.
- If you want “SQL + vectors” and already run Postgres, pgvector can reduce system count.

---

### G) Geo (Reverse Geocoding + Place Normalization)

Current location clustering is DB + haversine math; no reverse geocoding dependency.

If you want API-first “Paris / Tokyo / trail name”:
- Google Geocoding: https://developers.google.com/maps/documentation/geocoding
- Mapbox Geocoding: https://docs.mapbox.com/api/search/geocoding/
- HERE Geocoding: https://developer.here.com/

Low-ops hybrid:
- Run clustering locally (H3/S2 later if you want)
- Call reverse geocode API only when:
  - user asks to “name this place”, or
  - you batch-generate “Places” in background.

---

## Recommended “Upgrade Paths” (API‑First)

### Path 1: Better semantic search without hosting GPUs
1) Use hosted VLM to generate dense captions + tags once per image  
2) Use a cheap hosted text embedding model for indexing/search  
3) Keep vector DB managed (or keep LanceDB local if single-tenant desktop)

### Path 2: OCR quality boost with minimal engineering
1) Keep local OCR as fallback  
2) Add Google/AWS/Azure OCR behind a toggle  
3) Store OCR regions/text the same way so UI stays unchanged

### Path 3: “AI Insights” that feel premium
1) Use VLM for: best-shot reasoning, album suggestions, story summaries  
2) Persist outputs in `ai_insights_db.py` and `content_insights` schema  
3) Keep user controls: per-feature enable, batch jobs, cost visibility

---

## Integration Recommendations (How These Providers Fit *This* Repo)

This app has two very different workloads:
- **Interactive** (search UI): needs low latency and high reliability.
- **Background** (indexing/insights/OCR/face scans): can tolerate seconds per image and is where most API usage belongs.

### Recommended mapping (practical)

- **Captions / tags / “AI Insights” generation (background)**
  - Best fit: OpenAI / Google / AWS / Azure directly, or OpenRouter as a routing layer.
  - Also good for open-model experimentation: Replicate or HF Endpoints (then later “graduate” to Fireworks/Together/HF dedicated).
  - Store outputs once, then search locally forever.

- **Query rewriting / intent-aware refinement (interactive, cheap tokens)**
  - Best fit: OpenRouter (easy model swapping), or direct text-model APIs.
  - Keep strict token budgets; cache per query+filters.

- **OCR extraction (background, quality-sensitive)**
  - Best fit: Google Vision / AWS Textract / Azure Read (high quality, low ops).
  - If you want open OCR VLMs: Replicate/HF Endpoints for Chandra / GOT‑OCR, but run them as batch jobs and cache aggressively.

- **Embeddings**
  - If you want “true multimodal embeddings”: use whichever provider supports image+text embedding in one space.
  - If you want operational simplicity: use “caption → text embedding” and pick a strong **text embedding API** (OpenAI/Cohere/Voyage/Jina/etc.).
  - If you still want open embeddings without GPUs: host them on HF Endpoints / Fireworks / Together.

- **Image transforms (optional product add-ons)**
  - Best fit: fal / Replicate (super-res, cleanup, background removal) as opt-in premium operations.

### How to keep switching easy later (important)

Treat every API as a pluggable provider behind a small interface and a stable internal schema:
- `providers/vlm.py`: `generate_caption_and_tags(image) -> {caption_dense, tags, json}`
- `providers/ocr.py`: `extract_text_regions(image) -> {regions[], full_text, confidence}`
- `providers/embeddings.py`: `embed_image(image) -> vector`, `embed_text(text) -> vector`

Then:
- store `provider/model` metadata with each record,
- version embeddings by model (so you can reindex without guessing),
- keep the UI reading from DB tables, not directly from providers.

### Platform-specific notes

- **OpenRouter** is best used for “LLM/VLM routing” (captions, summaries, query refinement). It’s not a vector DB or OCR service by itself—model capability depends on the selected downstream model.
- **Replicate** and **fal** are ideal for “batch jobs” and experimentation. For interactive UX, you’ll likely want caching + async job execution.
- **Together / Fireworks / HF Endpoints** shine when you’ve picked a model family and want more predictable latency/throughput than “catalog-style” platforms.

---

## Where This Fits in the Current Repo

This catalog is meant to feed later refactors where you:
- introduce provider abstractions (e.g., `providers/embeddings.py`, `providers/ocr.py`, `providers/vlm.py`)
- store model/provider metadata with every generated artifact (embedding row, OCR row, insight row)
- allow per-tier configuration (pricing gates, per-feature toggles)

Companion for “what do we even want to run (now/planned/experimental)?”:
- `AI_MEDIA_USE_CASES_EXECUTION_PROVIDER_MATRIX.md`

If you want, I can implement the provider interface scaffolding (no behavior change by default), so swapping to APIs later becomes “config + credentials,” not a rewrite.

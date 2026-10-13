# Living Museum — AI/Media Use Cases × Execution Mode × Provider Options

This is a third companion document to:
- `FEATURE_PACKAGE_MODEL_OPTIONS.md` (what we use today + alternatives)
- `API_FIRST_MODEL_PROVIDER_CATALOG.md` (API-first providers + model families)

It answers: “What are our **current + planned + plausible/experimental** AI/media use cases, and which should run **interactive vs background**, using which **provider/platform** types?”

Primary references in-repo:
- Product direction: `ROADMAP.md`, `NEXT_PHASE_FEATURE_PLAN.md`
- Story direction: `docs/STORYTELLING_ROADMAP.md`
- Capability brainstorming: `docs/MEDIA_ANALYSIS_CAPABILITIES.md`, `docs/INNOVATION_OPPORTUNITIES.md`
- UX flows: `docs/USER_FLOWS.md`

---

## Execution Modes (How We Should Run Things)

### Interactive (user waiting)
- Budget: ~100–800ms typical, maybe ~2s worst-case.
- Pattern: cached results, cheap lightweight calls, strict timeouts, graceful fallbacks.

### Background (async jobs)
- Budget: seconds→minutes; can queue + batch.
- Pattern: scan/index pipelines, enrichment, heavy vision, bulk reindexing.

### On-demand background (“user requested, but async”)
- User clicks “Generate…” and gets a job + progress. Results appear when ready.

### Offline precompute
- Run overnight / when idle: “library health”, dedupe suggestions, embeddings refresh, etc.

---

## How We Keep Switching Providers Easy Later (Strong Recommendation)

For every capability, define a stable internal interface and store provenance:
- `provider` (OpenAI/Google/AWS/OpenRouter/Replicate/fal/HF Endpoints/…)
- `model` and `model_version` (when available)
- `created_at`, `input_hash`, and relevant settings (prompt, language, thresholds)

Internal “capability interfaces” to standardize:
- **Embedder**: image→vector, text→vector
- **VLM captioner/extractor**: image→{caption, tags, structured JSON}
- **OCR**: image→{regions[], full_text, confidence}
- **Detector**: image→{boxes, classes, scores}
- **Segmenter**: image→{masks/polygons + labels}
- **Enhancer/Transformer**: image→image (super-res, deblur, restoration)
- **Clusterer**: {vectors/coords}→clusters (usually local algorithms; input may come from providers)

---

## Use Case Catalog (Current / Planned / Plausible)

Below, “Status” uses:
- **Now**: implemented in this repo (or wired enough to run)
- **Planned**: explicitly in `ROADMAP.md` / `NEXT_PHASE_FEATURE_PLAN.md`
- **Plausible/Experimental**: in capability brainstorm docs; fits product

### 1) Core Retrieval: Search + Ranking

**Use cases**
- **Metadata search + filtering** (**Now**)
  - Execution: Interactive
  - Providers: none (DB/query engine)
  - Notes: foundation for everything; can later add learned ranking.

- **Semantic search (text→images)** (**Now**)
  - Execution: Interactive query + background indexing
  - Providers/platforms:
    - Background indexing: embedder (API or hosted open model)
    - Interactive: vector DB query (local LanceDB or managed vector DB)
  - “API-first” options:
    - Caption→text-embed pipeline (cheap, reliable, easy to cache)
    - True multimodal embedding endpoints (when available)

- **Hybrid ranking (metadata + semantic)** (**Now**, basic)
  - Execution: Interactive
  - Providers: optional (LLM query rewrite can help)

- **Query understanding / rewrite / intent routing** (**Now**, keyword-based; upgrade path is API)
  - Execution: Interactive
  - Providers/platforms:
    - OpenRouter for rapid model swaps: https://openrouter.ai/docs
    - Direct vendor text models (OpenAI/Google/AWS/Azure)
  - Output: rewritten query / suggested filters / explanation

### 2) Indexing + Enrichment (Library Processing)

**Use cases**
- **Scan & index (file discovery + metadata extraction)** (**Now**)
  - Execution: Background
  - Providers: none (local libraries)

- **Embedding generation (for semantic search)** (**Now**, local; can be swapped)
  - Execution: Background
  - Providers/platforms:
    - Text embeddings APIs (cheap) + captions (optional)
    - Hosted embedding models via HF Endpoints / Fireworks / Together
    - Replicate/fal if you want “no-ops open model” inference

- **VLM captions + tags (“AI insights generation”)** (**Plausible/Planned**; storage exists)
  - Execution: Background (batch) or On-demand background
  - Providers/platforms (API-first):
    - OpenAI / Google Gemini / AWS Bedrock / Azure Vision
    - OpenRouter as a routing layer for vision-capable chat models
    - Replicate for open VLM families (fast experimentation)
  - Stored artifacts: caption dense, tags, structured JSON → DB tables (insights)

### 3) OCR & Text Understanding

**Use cases**
- **OCR extraction + search** (**Now**)
  - Execution: Background extraction; Interactive search
  - Providers/platforms:
    - Hosted OCR: Google Vision / AWS Textract / Azure Read
    - Open OCR VLMs via Replicate/HF Endpoints (batch): Chandra / GOT-OCR families
    - Local fallback: Tesseract (already in repo)
  - Bonus features (Plausible/Experimental):
    - document layout analysis, table extraction, receipt parsing

### 4) People: Face Detection, Embeddings, Clustering

**Use cases**
- **Face detection + embeddings** (**Now**, local InsightFace; detection-only backends exist)
  - Execution: Background; on-demand for a single photo is possible
  - Providers/platforms:
    - Hosted faces: AWS Rekognition / Google Vision / Azure offerings (verify availability/policy)
    - Hosted open models: HF Endpoints / Fireworks / Together (if you pick an open stack)
  - Notes:
    - “People clustering” needs embeddings; cloud APIs can change privacy posture.

- **Face clustering / person labeling** (**Now**)
  - Execution: Background clustering, interactive browsing
  - Providers: typically local clustering (DBSCAN/HDBSCAN); embeddings are the key input.

### 5) Duplicates & Similarity

**Use cases**
- **Exact duplicates (hash)** (**Now**)
  - Execution: Background (can be incremental)
  - Providers: none

- **Near duplicates (perceptual hash / embeddings)** (**Now** for hashing; embedding-based is Plausible)
  - Execution: Background + interactive review lens
  - Providers/platforms:
    - No need for a “duplicate API”
    - If you already pay for embeddings, reuse them for similarity grouping

### 6) Location + Time + Storytelling

**Use cases**
- **Location clustering + correction** (**Now**, DB-driven)
  - Execution: background clustering; interactive browse
  - Providers (optional):
    - Reverse geocoding APIs (Google/Mapbox/HERE) for “human place names”

- **Timeline aggregation** (**Now**)
  - Execution: interactive

- **Story outline generation (metadata + clustering)** (**Planned**, aligns with `docs/STORYTELLING_ROADMAP.md`)
  - Execution: On-demand background (build outline), interactive viewing
  - Providers: none required if outline-only; embeddings help with theme labels

- **AI narrative generation (LLM)** (**Planned/Experimental**)
  - Execution: On-demand background (never block UI)
  - Providers/platforms:
    - OpenRouter (swap models fast), or direct cloud LLM providers
  - Output: narrative text + structured story JSON (persist for export/share)

### 7) Photo Manipulation & Enhancement (Transforms)

The repo already supports simple transforms (rotate/flip) and non-destructive edit persistence. A “Studio-grade” roadmap can add advanced transforms.

**Use cases**
- **Rotate/flip** (**Now**)
  - Execution: interactive (fast)
  - Providers: none

- **Non-destructive adjustments (crop/exposure/color/etc.)** (**Now** in concept; UI exists; server stores edit instructions)
  - Execution: interactive
  - Providers: none (unless you add AI auto-enhance)

- **Background removal / portrait cutout** (**Plausible/Experimental**)
  - Execution: On-demand background (or interactive if cached)
  - Providers/platforms:
    - remove.bg API: https://www.remove.bg/api
    - Replicate / fal endpoints for segmentation/cutout models
    - Open segmentation models (hosted): SAM2 + postprocessing

- **Segmentation (semantic/instance/panoptic)** (**Plausible/Experimental**, listed in `docs/MEDIA_ANALYSIS_CAPABILITIES.md`)
  - Execution: Background (batch), with interactive overlay display
  - Open model families to host:
    - SAM2: https://github.com/facebookresearch/sam2
    - GroundingDINO (box proposals): https://github.com/IDEA-Research/GroundingDINO
    - YOLO segmentation variants (Ultralytics): https://github.com/ultralytics/ultralytics
  - Why it matters:
    - enables “find photos with *this object*” + object removal + better cropping tools

- **Restoration / face enhancement** (**Plausible/Experimental**, see `docs/INNOVATION_OPPORTUNITIES.md`)
  - Execution: On-demand background
  - Open model families to host:
    - Real-ESRGAN (upscale): https://github.com/xinntao/Real-ESRGAN
    - GFPGAN (face restore): https://github.com/TencentARC/GFPGAN
    - CodeFormer (face restore): https://github.com/sczhou/CodeFormer
    - DeOldify (colorization/restoration): https://github.com/jantic/DeOldify
  - Platforms:
    - Replicate / fal are particularly convenient here

- **Inpainting / object removal / generative edits** (**Plausible/Experimental**)
  - Execution: On-demand background
  - Providers/platforms:
    - Stability AI platform: https://stability.ai/
    - Replicate / fal (many SD/SDXL-based tools)
    - Runway (creative editing suite): https://runwayml.com/

### 8) Object & Scene Understanding (Beyond Faces)

**Use cases**
- **Object detection (dogs/cars/etc.)** (**Planned/Plausible**)
  - Execution: Background indexing; interactive filtering
  - Providers/platforms:
    - Cloud: Google Vision / AWS Rekognition / Azure Vision
    - Managed model platforms: Roboflow: https://roboflow.com/ ; Clarifai: https://www.clarifai.com/
    - Open models hosted via Replicate/HF Endpoints/fal (YOLO/DETR/etc.)

- **Scene classification / mood / “event type” labels** (**Planned/Plausible**)
  - Execution: Background + interactive filters
  - Providers:
    - VLM-based tags (often simplest: caption → tags JSON)
    - Dedicated classifiers if you need stable label sets

### 9) Video & Audio Understanding (Next Phase Focus)

From `NEXT_PHASE_FEATURE_PLAN.md`, video content analysis is explicitly a top priority.

**Use cases**
- **Keyframe extraction + video thumbnails** (**Planned**)
  - Execution: Background
  - Providers: none (ffmpeg/ffprobe + heuristics) or cloud video intelligence

- **Video OCR (text overlays)** (**Planned**)
  - Execution: Background (sample frames)
  - Providers: Google Vision / AWS Textract / Azure Read, or OCR VLMs via Replicate/HF

- **Audio transcription (speech-to-text)** (**Plausible/Planned**)
  - Execution: Background
  - Providers/platforms:
    - OpenAI Whisper (API) (or vendor equivalents)
    - AWS Transcribe / Google Speech-to-Text / Azure Speech

- **Video understanding / “search inside video”** (**Planned/Plausible**)
  - Execution: Background indexing; interactive retrieval
  - Providers/platforms:
    - Google Video Intelligence: https://cloud.google.com/video-intelligence
    - Azure Video Indexer (Azure ecosystem)
    - Twelve Labs (video understanding/search): https://www.twelvelabs.io/

### 10) Clustering, Grouping, and Recommendations (Algorithms + AI)

**Use cases**
- **Session clustering (events/trips)** (**Planned**, in storytelling roadmap)
  - Execution: Background or on-demand background
  - Providers: none required; embeddings can improve “theme naming”

- **Smart suggestions (“clean up”, “best shots”, “stack these versions”)** (**Planned/Plausible**)
  - Execution: Background + user review UI
  - Providers/platforms:
    - VLM/LLM to explain recommendations (OpenRouter or direct vendors)
    - Classical heuristics for “quality score” + embeddings for similarity

---

## Provider/Platform Fit Cheatsheet (Practical)

If you want the shortest path to production with minimal ops:
- **Text/vision reasoning, narratives, captions**: OpenRouter (routing) + one or two direct vendors as fallback.
- **OCR (high accuracy)**: Google Vision / AWS Textract / Azure Read.
- **Image transforms (restoration, background removal, inpainting)**: Replicate / fal.
- **Embeddings**:
  - If you can: caption→text-embeddings (cheap + stable).
  - If you need true multimodal embeddings: pick a provider that supports it and persist vectors with model IDs.
- **Vector DB**:
  - Local single-tenant: LanceDB (already used).
  - Multi-tenant/cloud: managed vector DB (Pinecone/Qdrant/Weaviate/pgvector).

---

## Next Step (If You Want This Operationalized)

If you want, I can add a `providers/` layer (no behavior changes by default) with:
- `providers/base.py` (interfaces + provider registry)
- `providers/openrouter_vlm.py`, `providers/replicate.py`, `providers/google_vision_ocr.py`, etc. (stubs)
- consistent “artifact metadata” fields (provider/model/version/input_hash)

That turns “we might add segmentation/captions/restoration later” into “flip config + add key.”


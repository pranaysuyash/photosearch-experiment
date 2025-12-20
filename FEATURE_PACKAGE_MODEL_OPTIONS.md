# Living Museum — Feature → Package/Model → Alternatives Matrix

This document inventories the features currently implemented in this repo and maps each one to:

1) **What the code uses today** (Python package(s) and/or AI model(s))  
2) **Viable alternatives** (local/open-source and/or cloud APIs), with notes on tradeoffs

Scope note: many “features” are UI-first and don’t require AI. For those, this document lists the **backend/storage** packages (often stdlib `sqlite3`) plus practical alternatives.

---

## Quick Stack Snapshot (What’s “in use” today)

### Backend / API
- **Framework**: FastAPI (`fastapi`) + Uvicorn (`uvicorn[standard]`)
- **Schema/Settings**: Pydantic v2 (`pydantic`, `pydantic-settings`)
- **Core image IO**: Pillow (`Pillow`) + HEIC/HEIF (`pillow-heif`)
- **Core storage**: SQLite (stdlib `sqlite3`) + (for vectors) LanceDB (`lancedb`)

### Core AI / ML
- **Semantic image↔text embeddings**: `sentence-transformers` + `torch`
  - Default model: `clip-ViT-B-32` (512-dim) (see `server/embedding_generator.py`, `server/config.py`)
- **Face detection + embeddings (people/clusters)**: InsightFace (`insightface`) + ONNX Runtime (`onnxruntime`) + OpenCV (`opencv-python`)
  - Default backend model zoo: `FaceAnalysis(name="buffalo_l")` (see `src/face_backends.py`)
  - Clustering algorithm: DBSCAN (`scikit-learn`)
- **OCR text search**:
  - Primary: Tesseract via `pytesseract` (optional dependency; system Tesseract binary required)
  - Optional handwriting: EasyOCR (`easyocr`) (optional dependency)
- **Duplicate detection**:
  - Exact duplicates: file hash (MD5/SHA)
  - Perceptual hashes: `ImageHash` (+ `PyWavelets` when available)
  - Supporting image ops: OpenCV (`opencv-python`), Pillow

### Important “implicit/optional” deps in code (not pinned everywhere)
These are imported by some modules but are not present in all requirement files:
- `pyarrow` (imported by `server/lancedb_store.py`)
- `cryptography` (imported by `src/face_clustering.py`, `src/enhanced_face_clustering.py`)
- `pytesseract`, `easyocr` (imported by `src/ocr_search.py`, `src/enhanced_ocr_search.py`)
- Optional face backends: `mediapipe`, `ultralytics` (see `src/face_backends.py`)

---

## Feature Index (User-Facing)

This repo implements (at least) the following feature surfaces (based on API routes in `server/main.py` and the implementation docs in the repo):

### Library & Curation
- Duplicates review lens
- Favorites
- Ratings (1–5)
- Tags (single-tag ops + multi-tag filtering)
- Notes / captions (and search)
- Albums + smart collections/smart albums
- Version stacks (original + derived versions)
- Non-destructive photo edits (editor wiring)
- Trash (soft-delete) + restore + empty
- Safe bulk actions (undoable)

### People, Text, and “AI” Search
- Face detection + face clustering + person labeling
- OCR text extraction + search + highlight regions
- Semantic search (image↔text via embeddings)
- Intent detection (for search routing/refinement)
- AI insights storage + patterns/analytics endpoints

### Place, Time, and Storytelling
- Locations DB (per-photo location + correction)
- Location clustering
- Timeline entries
- Stories (story create/update + timeline)

### Sources, Sharing, and Operations
- Sources: local folder + stubs for S3 and Google Drive + sync/rescan
- Export (ZIP, presets) + share links + shared downloads
- Signed image tokens / thumbnail endpoints
- Background jobs + scan/index endpoints

### Security/Privacy & Product Layer
- JWT verification (minimal HS256) + optional issuer checks
- Privacy controls DB (visibility, allowed users/groups, encryption flags)
- Basic in-memory rate limiting in API
- Pricing tiers + usage tracking/analytics
- Collaboration (collaborative spaces, members, comments)

---

## Matrix: Features → Current Packages/Models → Alternatives (High-Level)

The sections below go deep, but this table is the “at a glance” mapping.

| Feature | Where in code | Current package(s) / model(s) | Solid alternatives (local) | Solid alternatives (cloud / hosted) |
|---|---|---|---|---|
| Semantic search (image↔text) | `server/embedding_generator.py`, `server/lancedb_store.py` | `sentence-transformers`, `torch`, model `clip-ViT-B-32` (512d), `lancedb` | `open_clip` (OpenCLIP), Hugging Face `transformers` CLIP/SigLIP, DINOv2 (+ separate text model), Jina CLIP, Nomic vision embeds | OpenAI (vision embeddings/caption→embed), Google Vertex AI, AWS Bedrock embeddings, Replicate-hosted CLIP |
| Vector store | `server/lancedb_store.py`, `server/vector_store.py`, `experiments/*` | LanceDB (`lancedb` + `pyarrow`), baseline Numpy | FAISS, Chroma, Qdrant client, Milvus client, DuckDB+VSS | Pinecone, Weaviate Cloud, Qdrant Cloud |
| Face detection + embeddings | `src/face_backends.py`, `src/face_clustering.py`, `server/face_detection_service.py` | InsightFace (`insightface`, `onnxruntime`) model zoo `buffalo_l`; OpenCV; DBSCAN (`scikit-learn`) | MediaPipe (detect-only), Ultralytics YOLO-face (detect-only), `deepface`, `face_recognition`/dlib, `facenet-pytorch` | AWS Rekognition, Google Vision Face, Azure Face (subject to product availability/policy) |
| OCR (printed + handwriting) | `src/enhanced_ocr_search.py`, `src/ocr_search.py` | Tesseract via `pytesseract` (+ system `tesseract`); optional `easyocr`; OpenCV; TF-IDF + cosine (`scikit-learn`) | PaddleOCR, docTR, TrOCR (Transformers), Kraken, RapidOCR | Google Cloud Vision OCR, AWS Textract, Azure OCR |
| Duplicate detection | `src/enhanced_duplicate_detection.py`, `server/duplicates_db.py` | `ImageHash`, optional `PyWavelets`, OpenCV, Pillow | `imagededup`, SSIM via `scikit-image`, deep embedding duplicates via CLIP | Cloud vision similarity (generally expensive; rarely worth it) |
| Metadata extraction (EXIF/video/PDF) | `src/metadata_extractor.py` + `requirements.txt` | `Pillow`, `exifread`, `ffmpeg-python`, `mutagen`, `python-magic`, `xattr`, `pypdf`, `pillow-heif` | `pyexiv2`/`exiv2`, `hachoir`, `pymediainfo`, `rawpy` (RAW) | ExifTool via subprocess (local), cloud media indexing APIs |
| Watcher (real-time indexing) | `server/watcher.py`, `src/*` | `watchdog` | `watchfiles`, platform-native FSEvents/inotify wrappers | N/A |
| Notes/captions + search | `server/notes_db.py`, endpoints in `server/main.py` | SQLite `sqlite3` (+ FTS if enabled) | Postgres FTS, Meilisearch, Tantivy via service | Algolia (search), Elastic Cloud |
| Tags, ratings, favorites | `server/tags_db.py`, `server/ratings_db.py`, `src/metadata_search.py` | SQLite `sqlite3` | Postgres, Redis (caching), SQLAlchemy | Managed Postgres |
| Location correction + clustering | `server/locations_db.py`, `server/location_clusters_db.py` | SQLite `sqlite3`, basic haversine math | H3 (`h3`), S2 (`s2sphere`), `geopy`, `shapely`, PostGIS | Mapbox/Google reverse geocoding APIs |
| Export/share + signed URLs | `server/signed_urls.py`, `server/main.py` | stdlib `hmac`/`hashlib`, `zipfile` (implied), FastAPI responses | `itsdangerous`, `PyJWT`/`python-jose`, `boto3` presigned URLs | CloudFront signed URLs, S3 presigned URLs |
| Sources (local + cloud stubs) | `server/sources.py`, `server/source_items.py` | SQLite `sqlite3`, `requests` | `boto3` (S3), `google-api-python-client`, `msgraph` | Native provider SDKs |
| Pricing + usage | `server/pricing.py`, `server/main.py` | stdlib + SQLite (usage DB) | Stripe SDK, Paddle SDK | Stripe Billing, RevenueCat |
| Auth (JWT) | `server/auth.py` | Minimal HS256 JWT (stdlib) | `PyJWT`, `python-jose`, `authlib`, OIDC providers | Auth0, Clerk, Cognito, Firebase Auth |

---

## Detailed Feature-by-Feature Breakdown

### 1) Semantic Search (Image ↔ Text)

**What it is:** Search images using text queries (and vice-versa) by embedding both into the same vector space and doing nearest-neighbor search.

**Current implementation**
- Code:
  - `server/embedding_generator.py` (`EmbeddingGenerator`)
  - `server/config.py` (`EMBEDDING_MODEL=clip-ViT-B-32`)
  - Vector persistence/search: `server/lancedb_store.py` (`LanceDBStore`)
  - Benchmarks: `experiments/EXPERIMENT_LOG.md`
- Packages:
  - `sentence-transformers` (wraps HF models and provides `encode`)
  - `torch` (model runtime)
  - `Pillow` (image input)
- Model:
  - `clip-ViT-B-32` (CLIP, 512-dimensional embeddings)
- Storage:
  - LanceDB (`lancedb`), with Arrow (`pyarrow`) used in the store code

**Practical alternatives (local / open-source)**
- **OpenCLIP** (strong default CLIP alternative ecosystem):
  - Library: `open_clip_torch` (repo: https://github.com/mlfoundations/open_clip)
  - Models: LAION-trained variants (e.g., ViT-H/14); often stronger retrieval than vanilla OpenAI CLIP
- **Hugging Face Transformers CLIP / SigLIP**
  - Library: `transformers`
  - Notes: more control, but you’ll implement preprocessing/normalization + batching yourself
- **SigLIP** (not CLIP, but strong image-text alignment)
  - Good when you care about modern retrieval performance; see experiment placeholder `10.8` in `experiments/EXPERIMENT_LOG.md`
- **DINOv2 / iBOT / EVA**-style vision embeddings
  - Not image-text by default; useful for “find visually similar images” but needs a separate text pipeline
- **Modern “embed everything” stacks**
  - Jina AI CLIP variants, Nomic vision embeddings (varies; evaluate on your dataset)

**Practical alternatives (cloud / hosted)**
- OpenAI embeddings/vision pipelines (often: caption first, then embed text; or vendor-specific multimodal embedding endpoints)
- Google Vertex AI multimodal embeddings
- AWS Bedrock embedding models
- Replicate-hosted embedding models for quick prototyping

**Selection notes**
- If you want **privacy + offline**, stay local (SentenceTransformers/OpenCLIP).
- If you want **zero ops**, cloud embeddings can win, but costs can spike quickly for large libraries.

---

### 2) Vector Storage / Approximate Nearest Neighbor (ANN)

**Current implementation**
- Code:
  - `server/lancedb_store.py` (production store)
  - `server/vector_store.py` (baseline, in-memory numpy store)
  - `experiments/vector_store_faiss.py`, `experiments/vector_store_chroma.py`, `experiments/vector_store_lance.py`
  - Metrics summary: `experiments/EXPERIMENT_LOG.md`
- Packages:
  - `lancedb` (+ `pyarrow`)
  - `numpy` for baseline store

**Alternatives (local / self-hosted)**
- **FAISS** (repo: https://github.com/facebookresearch/faiss)
  - Pros: extremely fast ANN, mature
  - Cons: metadata filtering is DIY (or separate store)
- **Chroma** (repo: https://github.com/chroma-core/chroma)
  - Pros: great DX and metadata support
  - Cons: heavier deps; operational quirks for production
- **Qdrant** (repo: https://github.com/qdrant/qdrant)
  - Pros: strong filtering, good production story
  - Cons: you run a service (Docker)
- **Milvus** (repo: https://github.com/milvus-io/milvus)
  - Pros: powerful at scale
  - Cons: heavier ops footprint than Qdrant/LanceDB
- **pgvector** (repo: https://github.com/pgvector/pgvector)
  - Pros: keeps everything in Postgres
  - Cons: might require careful indexing/tuning for large-scale ANN
- **DuckDB + vector extensions**
  - Pros: simple local single-file DB story
  - Cons: depends on extension maturity

**Alternatives (hosted)**
- Pinecone, Weaviate Cloud, Qdrant Cloud, managed Postgres+pgvector

**Selection notes**
- LanceDB is an excellent “local-first” default: persistent, simple API, good enough latency for UI.
- FAISS wins raw speed but pushes complexity into “metadata + filtering + persistence” elsewhere.

---

### 3) Face Detection + People Clustering

**What it is:** detect faces, compute embeddings, cluster them into “people”, allow labeling and per-photo associations.

**Current implementation**
- Code:
  - Backend abstraction: `src/face_backends.py`
  - Main face pipeline: `src/face_clustering.py` (and `src/enhanced_face_clustering.py`)
  - Service bridge: `server/face_detection_service.py`
  - DB + associations: `server/face_clustering_db.py`
  - Docs: `docs/FACE_MODELS_BACKENDS.md`, `FACE_DETECTION_IMPLEMENTATION.md`, `PEOPLE_FEATURE_IMPLEMENTATION.md`
- Packages:
  - `insightface`
  - `onnxruntime` (CPU/CUDA/CoreML execution providers)
  - `opencv-python`
  - `numpy`
  - `scikit-learn` (DBSCAN clustering)
  - Optional: `cryptography` (embedding encryption in `src/*face_clustering*.py`)
  - Optional: `mediapipe`, `ultralytics` (detection-only backends)
- Models:
  - Default InsightFace model zoo: `buffalo_l` (detection + recognition embeddings)
  - Some “legacy zip download” config is documented in `docs/FACE_MODELS_BACKENDS.md` but is off by default.

**Alternatives (local / open-source)**
- **MediaPipe Face Detection** (repo: https://github.com/google-ai-edge/mediapipe)
  - Great detector baseline, lightweight, but you still need an embedding model for clustering
- **Ultralytics YOLO face models** (repo: https://github.com/ultralytics/ultralytics)
  - Fast, especially on GPU; same caveat: detection-only unless you add a separate embedder
- **deepface** (repo: https://github.com/serengil/deepface)
  - Unified wrapper around multiple face backbones (ArcFace, FaceNet, VGG-Face, etc.)
  - Often easier experimentation, but can be heavier/less controlled
- **face_recognition (dlib)** (repo: https://github.com/ageitgey/face_recognition)
  - Very easy API; performance/accuracy is dated vs modern ArcFace stacks
- **facenet-pytorch**
  - Straightforward embeddings; you still need a detector (MTCNN/RetinaFace/YOLO)

**Alternatives (cloud / hosted)**
- AWS Rekognition (faces, indexing, search)
- Google Cloud Vision face detection
- Azure Face (availability/policies vary; verify current product status before committing)

**Selection notes**
- If “People” is a flagship feature and you need on-device privacy, InsightFace remains a strong choice.
- If you want **robustness across platforms**, the repo’s multi-backend detection design is correct; the missing piece is a separate **embedding backend** so non-InsightFace detectors can still cluster.

---

### 4) OCR Text Search (Printed + Handwriting)

**Current implementation**
- Code:
  - `src/ocr_search.py` (baseline OCR)
  - `src/enhanced_ocr_search.py` (regions, highlighting, multi-language, handwriting)
  - API endpoints in `server/main.py` under `/ocr/*`
- Packages / binaries:
  - Printed text: `pytesseract` (Python wrapper) + **system** `tesseract` binary + language data packs
  - Handwriting: `easyocr` (optional)
  - Image ops: `opencv-python`, `Pillow`, `numpy`
  - Search/scoring: `scikit-learn` (`TfidfVectorizer`, cosine similarity)

**Alternatives (local / open-source)**
- **PaddleOCR** (repo: https://github.com/PaddlePaddle/PaddleOCR)
  - Often materially better than Tesseract on modern scans and complex layouts
  - Heavier deps, but strong overall accuracy
- **docTR** (repo: https://github.com/mindee/doctr)
  - Deep-learning OCR with layout capabilities; good for documents
- **TrOCR** (Hugging Face Transformers)
  - Great for certain printed text; still requires detection/segmentation strategy
- **Kraken** (good for historical docs / special scripts)
- **RapidOCR** (fast OCR options; evaluate accuracy)

**Alternatives (cloud / hosted)**
- Google Cloud Vision OCR (strong general-purpose)
- AWS Textract (great for documents/forms)
- Azure OCR (strong enterprise option)

**Selection notes**
- Tesseract is a good baseline for privacy-first and low-cost, but expect:
  - more tuning (preprocessing, rotation, thresholding),
  - lower accuracy on low-quality photos and handwriting.
- PaddleOCR/docTR are often the “upgrade path” for local OCR if you can accept heavier ML deps.

---

### 5) Duplicate Detection & Resolution Suggestions

**Current implementation**
- Code:
  - `src/enhanced_duplicate_detection.py` (multi-hash + histogram + quality scoring)
  - Storage: `server/duplicates_db.py`
  - UI docs: `FEATURES_DOCUMENTATION.md` and implemented features docs
- Packages:
  - `ImageHash`
  - Optional: `PyWavelets` (for wavelet hashing)
  - `opencv-python`, `Pillow`, `numpy`
  - `scikit-learn` (DBSCAN used in the enhanced module)

**Alternatives (local / open-source)**
- **imagededup** (CNN/perceptual hashing based; good DX for duplicate finding)
- **SSIM** (structural similarity) via `scikit-image` for “near duplicates” after candidate generation
- **Embedding-based duplicates**:
  - Use your existing CLIP embeddings to propose “visual near duplicates” (often better than pHash for certain edits/crops)
  - Combine with exact hash to avoid false positives

**Selection notes**
- Hash-based systems are extremely fast and explainable; embeddings are often better for “edited variants” but require careful thresholding and UI review tools.

---

### 6) Metadata Extraction (Photos, Videos, Docs)

**Current implementation**
- Code:
  - `src/metadata_extractor.py`, `src/format_analyzer.py`, `src/file_discovery.py`
  - Metadata DB + search: `src/metadata_search.py`
- Packages:
  - Images: `Pillow`, `pillow-heif`
  - EXIF: `exifread`
  - Video: `ffmpeg-python` (calls ffprobe), `mutagen`
  - MIME: `python-magic` (libmagic)
  - Filesystem xattrs: `xattr`
  - PDFs: `pypdf`
  - Batch/UX: `tqdm`

**Alternatives**
- **ExifTool** (local binary; huge format coverage)
  - Typical approach: call via subprocess and parse JSON output
- **exiv2 / pyexiv2**
  - Strong EXIF/XMP/IPTC support
- **pymediainfo** (MediaInfo wrapper)
  - Often better/cleaner media metadata than ffprobe for some formats
- **rawpy**
  - Better RAW workflows if RAW support becomes central

---

### 7) Notes/Captions (Per-Photo) + Search

**Current implementation**
- Code:
  - `server/notes_db.py` + endpoints in `server/main.py`
- Packages:
  - stdlib `sqlite3`

**Alternatives**
- Postgres with full-text search (FTS) and JSONB for structured notes
- Meilisearch / Typesense (if you want fast “search-as-you-type” across notes)
- Elasticsearch / OpenSearch (if you need big-scale analytics/search)

---

### 8) Tags, Multi-tag Filtering, Saved Searches

**Current implementation**
- Code:
  - `server/tags_db.py`
  - `server/multi_tag_filter_db.py`
  - `server/saved_searches.db` + endpoints under `/searches/*`
- Packages:
  - stdlib `sqlite3`

**Alternatives**
- Postgres (tags as join tables; multi-tag filters as SQL)
- If you later add “semantic tags”: store embeddings per tag and do hybrid retrieval (vector + SQL filters)

---

### 9) Ratings, Favorites

**Current implementation**
- Code:
  - Ratings endpoints in `server/main.py` (and `server/ratings_db.py`)
  - Favorites in `src/metadata_search.py` (favorites table) + `/favorites/*` endpoints
- Packages:
  - stdlib `sqlite3`

**Alternatives**
- Same as above: Postgres (team/multi-user), Redis cache for hot paths

---

### 10) Non-Destructive Photo Edits (“Editor Wiring”) + Version Stacks

**Current implementation**
- Code:
  - Edits DB: `server/photo_edits_db.py`
  - Versions DB: `server/photo_versions_db.py`
  - Endpoints under `/versions/*` and `/api/photos/{path}/edits`
- Packages:
  - stdlib `sqlite3`
  - Client-side rendering: Canvas (UI), not a Python dependency

**Alternatives**
- For server-side rendering pipelines:
  - `opencv-python` (fast basic ops)
  - ImageMagick via subprocess
  - `pyvips` (high-performance, low-memory for large images)

---

### 11) Export / Share Links / Signed URLs

**Current implementation**
- Code:
  - Export endpoints under `/export/*` and `/share`
  - Signed URLs/tokens: `server/signed_urls.py`
  - Shared downloads under `/shared/{share_id}/*`
- Packages:
  - Mostly stdlib (`hashlib`, `hmac`, `zipfile`-style workflows) + FastAPI responses

**Alternatives**
- Token/signing:
  - `itsdangerous` (simple URL signing)
  - `PyJWT` / `python-jose` (JWT-based signed URLs)
- Cloud storage:
  - S3 presigned URLs (via `boto3`)
  - CloudFront signed URLs

---

### 12) Sources (Local Folder, S3, Google Drive) + Sync

**Current implementation**
- Code:
  - `server/sources.py`, `server/source_items.py`
  - Endpoints under `/sources/*` in `server/main.py`
- Packages:
  - stdlib `sqlite3`, `json`, `uuid`
  - `requests` (HTTP)
 - Notes:
   - S3 sync uses **manual AWS SigV4 signing** + `requests` (no `boto3`) in `server/main.py` (`_aws_sigv4_headers`, `_sync_s3_source`)
   - Google Drive sync uses OAuth token refresh + Drive REST API via `requests` in `server/main.py` (`_refresh_google_access_token`, `_sync_google_drive_source`)
   - Source item state (local path, deleted/trashed) is tracked and can back “Provenance” UI (Local/Cloud/Offline) even if the UI is currently using mock data.

**Alternatives**
- S3:
  - `boto3` (official AWS SDK)
  - `aioboto3` if you want async
- Google Drive:
  - `google-api-python-client` + `google-auth` + `google-auth-oauthlib`
- Dropbox:
  - `dropbox` SDK
- OneDrive:
  - Microsoft Graph SDK

---

### 13) Locations: Place Correction & Location Clustering

**Current implementation**
- Code:
  - `server/locations_db.py` (per-photo records, correction fields)
  - `server/location_clusters_db.py` (cluster table + simple distance math)
- Packages:
  - stdlib `sqlite3`, `math`

**Alternatives**
- Spatial indexing and clustering:
  - H3 (`h3`) for hierarchical hex clustering (very practical for “Places” UX)
  - S2 (`s2sphere`) for Google-style cells
  - PostGIS if moving to Postgres
- Reverse geocoding:
  - `geopy` (Nominatim/OpenStreetMap or other backends)
  - Mapbox / Google Geocoding APIs (paid)

---

### 14) Bulk Actions (Undoable), Trash

**Current implementation**
- Code:
  - `server/bulk_actions_db.py`, `server/trash_db.py`
  - Endpoints under `/bulk/*` and `/trash/*`
- Packages:
  - stdlib `sqlite3`

**Alternatives**
- Event sourcing / audit logs:
  - append-only log tables + periodic compaction
  - Kafka/Redpanda if you ever go distributed (likely overkill here)

---

### 15) AI Insights + Analytics

**Current implementation**
- Code:
  - `server/ai_insights_db.py` (stores insights; no specific ML model invoked here)
  - Endpoints under `/ai/insights*` and `/ai/analytics/patterns`
  - “Analytics dashboard” endpoints exist under `/analytics/*` via `server/advanced_features_api.py`
- Packages:
  - Mostly stdlib `sqlite3`; some endpoints compute aggregates

**Alternatives / upgrade paths**
- If you want **real AI insights generation**, consider:
  - Captioning: BLIP-2, LLaVA-style local VLMs, or hosted vision LLMs
  - Tagging/classification: open-vocabulary detection models, or promptable VLMs
  - Quality/best-shot scoring: learned aesthetic models (LAION aesthetic predictors) or heuristics + user feedback

See also: `docs/antigravity/AI_PROVIDERS.md` for provider-style options.

---

### 16) Intent Recognition (Search Routing)

**Current implementation**
- Code:
  - `src/intent_recognition.py` (keyword + regex intent classification)
- Packages:
  - stdlib only (`re`, collections)

**Alternatives**
- Lightweight ML intent classifier:
  - `scikit-learn` logistic regression / linear SVM over n-grams
  - DistilBERT / MiniLM text classifier (`transformers`)
- LLM-based query understanding:
  - Local: small instruction-tuned models (via `llama-cpp-python`, `mlx` on macOS, or `ollama`)
  - Hosted: OpenAI / Anthropic / Google

---

### 17) Security: Auth, Privacy Controls, Rate Limiting

**Current implementation**
- Code:
  - JWT: `server/auth.py` (minimal HS256)
  - Privacy controls: `server/privacy_controls_db.py`
  - Signed URLs: `server/signed_urls.py`
  - Rate limiting: in `server/main.py` (simple in-memory counters)
- Packages:
  - Mostly stdlib (`hmac`, `hashlib`, `sqlite3`)

**Alternatives**
- JWT/OIDC:
  - `PyJWT` or `python-jose`
  - OIDC via Auth0/Clerk/Cognito/etc.
- Rate limiting:
  - `slowapi` (FastAPI/Starlette rate limits)
  - Redis-based rate limiting for multi-instance deployments
- Secrets/encryption:
  - OS keychain integration (macOS Keychain, Windows DPAPI)
  - `cryptography` for at-rest encryption primitives (already referenced in face modules)

---

### 18) Background Jobs, Scan/Index Pipelines, and Progress Tracking

**Current implementation**
- Code:
  - Job store: `server/jobs.py` (uses `pydantic` models; optional persistent backing via `src/persistent_job_store.py`)
  - Scan/index entrypoints: `/scan`, `/index`, `/jobs/{job_id}` in `server/main.py`
  - Core scan/index pipeline: `src/photo_search.py` (calls file discovery + metadata extraction + indexing)
- Packages:
  - `pydantic` (job model)
  - Mostly stdlib otherwise (`time`, `uuid`)

**Alternatives**
- Background work execution:
  - `celery` (+ Redis/RabbitMQ), `dramatiq`, `rq`
  - For async-native: `arq`, `huey`
- Observability:
  - OpenTelemetry SDKs + a tracing backend

---

### 19) Caching / Performance Optimization

**Current implementation**
- Code:
  - `src/cache_manager.py` implements LRU + TTL caches for thumbnails/search/metadata/embeddings
  - Endpoints: `/cache/*` and `/api/cache/*` in `server/main.py`
- Packages:
  - stdlib only (`hashlib`, `threading`, `OrderedDict`)

**Alternatives**
- Distributed cache:
  - Redis (`redis` / `redis-py`) when running multiple server instances
- More advanced caching:
  - `diskcache` for persistent local caches

---

### 20) Image/Video Serving, Thumbnails, and Image Tokens

**Current implementation**
- Code:
  - Thumbnail and image token endpoints: `/image/thumbnail`, `/image/token`, `/file`, `/video` in `server/main.py`
  - Image format negotiation (JPEG/WEBP) in `server/main.py`
- Packages:
  - `Pillow` (image read/resize/encode)
  - stdlib for token signing (`hmac`, `hashlib`) when enabled

**Alternatives**
- High-performance thumbnailing:
  - `pyvips` (often faster/less memory than Pillow for large images)
- Media streaming:
  - Dedicated media server (nginx/byte-range) + signed URLs

---

### 21) Dialog / Modal System (Backend Support)

**Current implementation**
- Code:
  - `src/modal_system.py` (`DialogManager` + SQLite persistence)
  - Endpoints: `/dialogs/*` in `server/main.py`
- Packages:
  - stdlib `sqlite3`

**Alternatives**
- If dialogs are purely UI state, keep them client-side (no server persistence).
- If dialogs need collaboration/audit:
  - Postgres event tables + WebSockets for realtime updates

---

### 22) Code Splitting / Lazy Loading (Backend Support)

**Current implementation**
- Code:
  - `src/code_splitting.py` (config + performance log storage to JSON)
  - Endpoints: `/code-splitting/*` in `server/main.py`
- Packages:
  - stdlib only (`json`, file IO)

**Alternatives**
- For serious frontend performance monitoring:
  - Web Vitals + a telemetry backend (Sentry, Datadog, OpenTelemetry)
- For dynamic bundling:
  - Vite/React lazy imports (frontend concern; backend can remain configuration-only)

---

### 23) Tauri Desktop Integration (Docs + API Surface)

**Current implementation**
- Code:
  - `src/tauri_integration.py` (command definitions + Rust skeleton generator)
  - Endpoints: `/tauri/*` in `server/main.py`
  - Desktop app shell exists under `src-tauri/`
- Packages:
  - stdlib only on the Python side

**Alternatives**
- Desktop shells:
  - Electron, Neutralinojs
  - Native wrappers (Swift/WinUI) if you go “full native”
- If you keep Tauri:
  - Use Rust crates for image IO and indexing for tighter offline performance, leaving Python for “AI services” only

---

### 24) Albums, Smart Albums, and Smart Collections

**Current implementation**
- Code:
  - Albums: `server/albums_db.py` + `/albums/*` routes in `server/main.py`
  - Smart album rules engine: `server/smart_albums.py`
  - Smart collections: `server/smart_collections_db.py` + `/collections/smart/*` routes
- Packages:
  - stdlib `sqlite3`, `json`
  - Rule evaluation is plain Python (no ML model invoked in the DB module itself)

**Alternatives**
- Rule engines / query DSLs:
  - Keep custom (works well for “photo rules”), or
  - Use a small expression language (e.g., `lark`/`parsimonious`) if rules become complex
- If you want “AI-suggested albums”:
  - Use captioning + tag inference (BLIP/LLaVA or cloud vision LLMs) and auto-generate rule templates

---

### 25) Stories + Timeline

**Current implementation**
- Code:
  - Timeline/story storage: `server/timeline_db.py`
  - Endpoints: `/stories/*` and `/timeline/*` in `server/main.py`
- Packages:
  - stdlib `sqlite3`, `uuid`, `datetime`, `json`

**Alternatives**
- Narrative generation:
  - Local LLM summarization over captions/locations (Ollama/llama.cpp/etc.)
  - Hosted LLM summarization for higher quality prose
- Time/location clustering:
  - Use H3/S2 for place grouping, plus robust date normalization

---

### 26) Collaborative Spaces (Sharing + Comments + Roles)

**Current implementation**
- Code:
  - `server/collaborative_spaces_db.py`
  - Endpoints: `/collaborative/spaces/*` in `server/main.py`
- Packages:
  - stdlib `sqlite3`, `uuid`, `json`

**Alternatives**
- Realtime collaboration:
  - WebSockets (FastAPI/Starlette) + pubsub (Redis) for multi-instance sync
- Permissions:
  - Policy engines (e.g., OpenFGA/SpiceDB) if permissions become complex (likely overkill early)

---

### 27) Pricing Tiers + Usage Tracking

**Current implementation**
- Code:
  - `server/pricing.py` (tier definitions + in-memory usage cache)
  - Endpoints: `/pricing/*` and `/usage/*` in `server/main.py`
- Packages:
  - `pydantic` (tier/stats models)
  - Otherwise stdlib (`datetime`)
- Notes:
  - Current usage tracking is **not persisted** (in-memory `usage_cache`), which is fine for prototyping but not multi-process/multi-instance safe.

**Alternatives**
- Billing + persistence:
  - Stripe SDK + webhooks (standard approach)
  - Paddle/Braintree (depending on target market)
- “Local-first commercial” patterns:
  - License keys + offline activation with periodic refresh
  - Feature flags stored in local DB + cryptographic signatures

---

## Appendix: Key External Links (Online)

Repositories/docs referenced above (verified reachable via HTTPS):
- InsightFace: https://github.com/deepinsight/insightface
- OpenCLIP: https://github.com/mlfoundations/open_clip
- LanceDB: https://github.com/lancedb/lancedb
- FAISS: https://github.com/facebookresearch/faiss
- Chroma: https://github.com/chroma-core/chroma
- Qdrant: https://github.com/qdrant/qdrant
- Milvus: https://github.com/milvus-io/milvus
- pgvector: https://github.com/pgvector/pgvector
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- docTR: https://github.com/mindee/doctr
- MediaPipe: https://github.com/google-ai-edge/mediapipe
- Ultralytics: https://github.com/ultralytics/ultralytics

---

## Companion (API‑First)

For a deeper, API-first (hosted/managed) set of options and upgrade paths, see:
- `API_FIRST_MODEL_PROVIDER_CATALOG.md`

For a broader “use case map” (current/planned/experimental workloads like segmentation, manipulation, clustering, video/audio), see:
- `AI_MEDIA_USE_CASES_EXECUTION_PROVIDER_MATRIX.md`

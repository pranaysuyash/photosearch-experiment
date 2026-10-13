# Face provider options (API-first, low-maintenance)

This project already supports **generic remote HTTP backends** for face detection and face embeddings:

- Detection: `src/face_backends.py` → `RemoteApiBackend`
- Embeddings: `src/face_embeddings.py` → `RemoteEmbeddingBackend`

That means you can add “providers” with minimal dev friction by either:

1. pointing the app at a provider that returns **bounding boxes** (detection-only), while keeping embeddings local (recommended), or
2. running a tiny adapter service that calls a provider/model-host and returns responses in our existing JSON format.

## ✅ Recommended integration strategy (lowest headaches)

### Option A — API provider for detection only + local embeddings

Use a hosted API to **detect faces (bounding boxes)**, then generate embeddings locally using InsightFace (or whatever embedding backend you already prefer).

Pros:

- Minimal architecture change
- Keeps your clustering / FAISS / embedding-version gating intact
- Only detection data leaves the machine (still sensitive, but less than full embedding pipelines)

Cons:

- Still sends images off-box if provider requires image bytes

### Option B — Hosted inference for embeddings (keep our FAISS)

Use a model hosting service (Inference Endpoint) to run a face-embedding model (e.g., ArcFace-family) and return raw vectors.

Pros:

- Preserves current architecture
- Avoids running GPUs locally

Cons:

- You must ensure embedding dimensionality and stability (the project uses embedding-version gating; you still need a deterministic `embedding_version` string)
- Privacy considerations: embeddings + face crops leave the machine

### Option C — Provider-managed galleries (bigger change)

Some face APIs (Kairos, Face++, Luxand.cloud) are built around **enroll/verify/recognize** in their own gallery/people store.

Pros:

- Very simple to “recognize” against a provider-managed database

Cons:

- Doesn’t map cleanly onto our “local embeddings + FAISS + clustering DB” design
- Would require a dedicated adapter layer (and likely new flows) if you want the provider to be the source of truth

### Option D — Browser / on-device detection (zero server calls)

Run face detection (and optionally landmarking) in the browser, then send only the bounding boxes (and/or cropped faces) to the backend for embedding + indexing.

Pros:

- Best privacy story (image never leaves the device)
- Great UX for interactive workflows (e.g., People UI, manual labeling)

Cons:

- Requires a front-end pathway for detection results (and careful coordinate transforms)
- Not always ideal for batch/offline indexing unless you build a headless/browser worker

## Current remote backend contracts

### Remote detection backend (what we already support)

`RemoteApiBackend` posts an image and expects a list of faces with bounding boxes.

Typical contract (shape may evolve; keep adapter aligned with code):

- Request: base64 JPEG (or other accepted format) + optional flags
- Response: `faces: [{ bounding_box, confidence, embedding?, embedding_version? }, ...]`

Where `bounding_box` is usually `(x, y, w, h)` in pixel coordinates.

### Remote embedding backend

`RemoteEmbeddingBackend` posts a face crop and expects:

- Response: `{ embedding: number[], embedding_version: string }`

Notes:

- The embedding must be a **fixed-length** float vector.
- `embedding_version` should identify the model + preprocessing so mixed models don’t get compared.

## API-first provider shortlist (non-enterprise leaning)

### 1) Eden AI (aggregator)

**Good for:** “one API key to multiple engines” and easy experimentation.

- Docs (Face recognition endpoints):
  - https://docs.edenai.co/reference/image_face_detection_create
  - https://docs.edenai.co/reference/image_face_recognition_recognize_create
  - https://docs.edenai.co/reference/image_face_compare_create

Integration fit:

- Likely best as **detection-only** (Option A) unless a specific engine returns a usable embedding vector.
- As an aggregator, it can keep provider churn low (swap engines without changing your backend client).

### 2) Face++ (Megvii)

**Good for:** Face detection + attributes + provider-side search/compare.

- Detect API docs:
  - https://console.faceplusplus.com/documents/5679127
  - Request URL shown in docs: `https://api-us.faceplusplus.com/facepp/v3/detect`

Integration fit:

- Great **detection/attributes** source (Option A).
- Their ecosystem is centered around `face_token` + FaceSet + provider search.
- If you want to keep local FAISS/embeddings, you’d still need an embedding source.

### 3) Kairos

**Good for:** Straightforward REST API for detect/enroll/verify/recognize/compare.

- API base URL and auth headers are clearly documented:
  - https://face.kairos.com/docs/api
  - Pricing: https://www.kairos.com/pricing

Integration fit:

- Works well for provider-managed flows (Option C).
- Can still be used for **detection-only** (Option A).

Notes from their docs:

- They publish best practices (image quality, pixel requirements): https://face.kairos.com/docs/api/best-practices
- They publish error codes and rate-limit behavior: https://face.kairos.com/docs/api/error-codes

### 4) Luxand.cloud

**Good for:** API-first face recognition with a Postman doc reference.

- API docs (Postman): https://documenter.getpostman.com/view/1485228/UVeCR95R

Integration fit:

- Strongest fit is provider-managed recognition (Option C).
- Can be used for detection/recognize/verify workflows, but doesn’t naturally provide raw embeddings for our FAISS path.

### 5) Clarifai

**Good for:** Hosted models (including face detection) and a unified platform.

- Face detection model page (not full API reference):
  - https://clarifai.com/clarifai/main/models/face-detection

Integration fit:

- Best as **detection-only** unless you select/host a face-embedding model that returns vectors.

## Browser / on-device (no external calls)

These options are great when you want face detection (and sometimes landmarks / attributes) without sending images to a third party.

### MediaPipe Tasks Vision (Web)

**Good for:** fast in-browser face detection / landmarking.

- Package: `@mediapipe/tasks-vision`
- Face Detector returns bounding boxes (and a small set of landmarks).
- Face Landmarker returns 478 landmarks; can optionally output blendshapes and transformation matrices.

Docs:
- https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector
- https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker

Integration fit:
- Best for Option D (browser detection) + our existing server-side embedding pipeline.

### TensorFlow.js face landmarks

**Good for:** face landmarks + boxes in the browser.

- Package: `@tensorflow-models/face-landmarks-detection`
- Can run with `runtime: 'mediapipe'` or `runtime: 'tfjs'`.

Docs:
- https://github.com/tensorflow/tfjs-models/tree/master/face-landmarks-detection

### face-api.js (TFJS)

**Good for:** browser face detection + *face descriptors* (128-D) + optional age/gender/expressions.

- Repo/docs: https://github.com/justadudewhohacks/face-api.js

Integration fit:
- Can be used as an **on-device embedding** source, but note it produces a different embedding family than ArcFace/InsightFace.
- If you do this, treat it as a distinct `embedding_version` and do not mix it into the same vector index as InsightFace vectors.

### ONNX Runtime Web

**Good for:** running ONNX models (including face detectors / embeddings) in-browser.

Docs:
- Get started: https://onnxruntime.ai/docs/get-started/with-javascript/web.html
- Web tutorials: https://onnxruntime.ai/docs/tutorials/web/

Integration fit:
- Lets you run a face detector/embedding model client-side (Option D).
- Can use WebAssembly (CPU) or WebGPU (where available); ONNX Runtime docs note WebGL support is in maintenance mode.

## Open-source / self-hosted servers (API, but on *your* infra)

If you want “API-based” integration without depending on commercial SaaS, self-hosted services are often the lowest long-term maintenance.

### CompreFace (Docker + REST API)

**Good for:** self-hosted face detection/recognition/verification and some attributes.

- Repo/docs: https://github.com/exadel-inc/CompreFace

Integration fit:
- Works well as Option A (detection-only) or Option C (provider-managed recognition).
- For Option B (raw vectors), you may still need an adapter depending on which endpoints expose embeddings.

### DeepFace (Python + optional REST API)

**Good for:** flexible Python pipeline: detect/align/represent + attributes.

- Repo/docs: https://github.com/serengil/deepface

Integration fit:
- Strong match for Option B via a tiny adapter around `DeepFace.represent(...)` that returns `{ embedding, embedding_version }`.
- Also useful for attributes (age/gender/emotion) if/when you want to enrich People.

## Model-hosting APIs (best match for embeddings)

If you want embeddings via “just an API” (Option B), consider model-hosting platforms. These tend to fit our embedding backend contract well because you can build an endpoint that *literally returns a vector*.

### Hugging Face Inference Endpoints (dedicated)

**Good for:** production hosting of a specific model behind a stable HTTPS endpoint.

- Docs: https://huggingface.co/docs/inference-endpoints/index
- Model discovery (InsightFace tag): https://huggingface.co/models?other=insightface

### Hugging Face “Inference Providers” (serverless proxy)

**Good for:** trying many providers/models through one token + consistent client interfaces.

- Docs: https://huggingface.co/docs/inference-providers/index

### Replicate

**Good for:** quickly running community models via a clean HTTP API.

- HTTP API: https://replicate.com/docs/reference/http
- OpenAPI schema: https://api.replicate.com/openapi.json

Operational notes:
- Predictions are typically async (create → poll); you can sometimes use `Prefer: wait` for short synchronous waits.

### Cloudflare Workers AI

**Good for:** serverless inference against Cloudflare’s curated model catalog.

- Overview/models: https://developers.cloudflare.com/workers-ai/
- REST API guide: https://developers.cloudflare.com/workers-ai/get-started/rest-api/

## General-purpose vision APIs (fit notes)

### OpenAI Vision (image understanding)

**Good for:** high-level semantics, captions, photo QA checks, and UI helpers.

- Docs: https://platform.openai.com/docs/guides/images

Notes from the docs:
- Images can be sent by URL, base64 data URL, or file ID.
- You can pass multiple images in a single request.
- There is a `detail` parameter for image inputs (`low` / `high` / `auto`).
- The docs explicitly call out limitations around **precise spatial localization**.

Integration fit:
- Not recommended for our core face pipeline (precise boxes + stable embeddings).
- Potentially useful for *non-identifying* metadata enrichment (e.g., “is this photo blurry?”, scene tags) or for explaining results in the UI.

## “Enterprise” providers to keep documented for later

Not recommended for your current preference (“avoid dev headaches / enterprise setup”), but keep in mind for future scale/compliance features:

- AWS Rekognition
- Azure Face
- Google Cloud Vision / Vertex AI

These tend to add account/VPC/region/compliance/metering complexity, but are robust once you’re ready.

## Practical recommendation

For this repo’s current architecture, the smoothest path is:

1. Keep **InsightFace embeddings locally**.
2. Add one or more **detection-only API providers** (Face++ / Kairos / Clarifai / Eden AI).
3. If you later want embeddings via API, add **one embedding endpoint** (HF endpoint or a small adapter service) that returns a stable vector + `embedding_version`.

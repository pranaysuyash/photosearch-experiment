# Face models & multi-backend support

This project supports **selectable face detection backends** so we can:

- keep the system working even if one model stack fails to download,
- compare accuracy/speed across backends,
- optionally use an API-based detector later (behind flags),
- reduce log spam / startup friction (no mandatory heavyweight deps).

> Important: **Face clustering requires face embeddings.** Right now, only the **InsightFace** backend produces embeddings, so **clustering** is InsightFace-only.
> Other backends are **detection-only** (bounding boxes + confidence).

---

## Where face detection is used

- **Detection (per image):** `src/face_clustering.py` → `FaceClusterer.detect_faces(image_path)`
- **Clustering (across images):** `src/face_clustering.py` → `FaceClusterer.cluster_faces(image_paths, ...)`
- **Server routes:** `server/main.py` imports `FaceClusterer()` and exposes face endpoints (clusters, scan, etc.)

The backend selection is implemented in `src/face_backends.py` and wired into `FaceClusterer._initialize_models()`.

---

## Configuration

Configuration is environment-variable driven (and mirrored in `server/config.py`).

### `FACE_BACKENDS`

Comma-separated preference list.

Examples:

- Default (recommended):
  - `FACE_BACKENDS=insightface`
- Prefer MediaPipe if installed, else InsightFace:
  - `FACE_BACKENDS=mediapipe,insightface`
- Try YOLO first if configured, else fall back:
- `FACE_BACKENDS=yolo,insightface`

### `FACE_YOLO_WEIGHTS`

Local filesystem path to a YOLO `.pt` weights file.

- Required if you include `yolo` in `FACE_BACKENDS`.
- If not set, the YOLO backend is skipped.

Example:

- `FACE_YOLO_WEIGHTS=/absolute/path/to/yolov8-face.pt`

### `FACE_EMBEDDING_BACKENDS`

Comma-separated embedding backend preference list (used when the detection backend
does not provide embeddings).

Examples:

- Default:
  - `FACE_EMBEDDING_BACKENDS=insightface,clip,remote`
- Force CLIP embeddings for fallback:
  - `FACE_EMBEDDING_BACKENDS=clip`

### `FACE_CLIP_EMBEDDING_MODEL`

Model name for the CLIP embedding fallback.

- Default: `clip-ViT-B-32`

### Remote HTTP backends

Detection:

- `FACE_REMOTE_DETECT_URL=https://...`
- `FACE_REMOTE_DETECT_API_KEY=...` (optional)
- `FACE_REMOTE_DETECT_TIMEOUT=10`
- `FACE_REMOTE_DETECT_EMBEDDINGS=1` (set if the endpoint returns embeddings)

Embedding:

- `FACE_REMOTE_EMBEDDING_URL=https://...`
- `FACE_REMOTE_EMBEDDING_API_KEY=...` (optional)
- `FACE_REMOTE_EMBEDDING_TIMEOUT=10`

See `docs/FACE_FALLBACKS.md` for the request/response contract.

### `FACE_LEGACY_MODEL_DOWNLOADS`

Controls legacy “download InsightFace zips from GitHub release URLs” behavior.

- Default: disabled (prevents noisy 404s)
- Enable (not recommended):
  - `FACE_LEGACY_MODEL_DOWNLOADS=1`

InsightFace’s `FaceAnalysis` already manages model assets for its built-in model zoo (e.g. `buffalo_l`).

---

## Backends

### 1) InsightFace (`insightface`)

**Status:** default + production-grade

- Pros:
  - High accuracy
  - Provides **embeddings** (required for clustering)
  - Can use hardware acceleration providers depending on platform
- Cons:
  - Heavier dependency stack

Implementation:

- `src/face_backends.py::InsightFaceBackend`
- Uses `FaceAnalysis(name="buffalo_l")`.

### 2) MediaPipe (`mediapipe`)

**Status:** optional, detection-only

- Pros:
  - Very easy to run locally
  - Strong baseline detector
- Cons:
  - No embeddings in current integration → no clustering

Implementation:

- `src/face_backends.py::MediaPipeBackend`

### 3) Ultralytics YOLO (`yolo`)

**Status:** optional, detection-only

- Pros:
  - Very fast on GPU
  - Many community face detectors exist
- Cons:
  - Requires an explicit weights file
  - No embeddings in current integration → no clustering

Implementation:

- `src/face_backends.py::UltralyticsYoloBackend`

### 4) Remote API (`remote`)

**Status:** optional, detection-only unless `FACE_REMOTE_DETECT_EMBEDDINGS=1`

- Pros:
  - Can offload detection to hosted services
  - Keeps local stack lean if desired
- Cons:
  - Requires network + API keys
  - Latency + cost per image

Implementation:

- `src/face_backends.py::RemoteApiBackend`

---

## Installing optional dependencies

These are intentionally **not required** for the app/tests to run.

### MediaPipe backend

- Python package: `mediapipe`

### YOLO backend

- Python package: `ultralytics`
- Plus a weights file (`FACE_YOLO_WEIGHTS=...`)

If we decide YOLO becomes a first-class path, we should:

- pin a known-good weights source,
- add a small download/cache helper (and checksum),
- add an opt-in install extra (e.g. `pip install -r requirements-face-yolo.txt`).

---

## Roadmap: making non-InsightFace backends support clustering

To enable clustering with non-InsightFace detectors, we need an **embedding model** decoupled from detection.

Proposed architecture:

- Use a detection backend for bounding boxes
- Use an embedding backend to generate vectors (InsightFace / CLIP / remote)
- Fall back to API-based embeddings when local models are unavailable

- **Detector backend**: produces bboxes
- **Embedder backend**: produces $d$-dim embeddings

Then clustering runs on embeddings regardless of detector.

Evaluation metric suggestions:

- Detection quality: precision/recall on a small labeled set, false positives in “people” view
- Embedding quality: cluster purity, NMI, and user relabel rate
- UX metrics: time-to-first-people, number of manual merges/splits

---

## Notes on privacy

All current backends are designed for **on-device** inference.

If we add an API-based detector later, it must be:

- opt-in,
- clearly labeled,
- configurable to send thumbnails only (or not at all),
- audited (log what is sent, when, and why).

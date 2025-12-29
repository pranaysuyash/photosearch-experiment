# Face Model Fallback Options (Notes)

## Baseline (current)
- InsightFace (buffalo_l): RetinaFace R50 for detection + ArcFace R100 embeddings.
- Pros: strong accuracy, local, fast with GPU/MPS, embedding compatibility with current DB.
- Cons: model updates manual; limited attribute models without extra dependencies.

## Local fallback candidates
- MediaPipe Face Detection + Face Mesh
  - Good for detection/landmarks; embeddings still needed separately.
- YOLO face weights (Ultralytics)
  - Detection only; embeddings still needed.
- DeepFace / ArcFace / FaceNet (PyTorch)
  - Embedding alternatives, but require compatibility gating for clustering.
- ONNX runtime variants
  - Useful for CPU-only deployments and model portability.

## Hosted API fallbacks (detection + attributes)
- AWS Rekognition
- Azure Face
- Google Cloud Vision / Face APIs
- Face++

Notes:
- Cloud providers can return landmarks, age, emotion, and face features, but embeddings are not always portable.
- Mixing embeddings from different providers without compatibility gating will break clustering quality.
- Hosted APIs change privacy and cost posture; keep them opt-in and behind explicit config.

## VLM/LLM-based options (attributes only)
- Use VLMs to classify emotion/age ranges when local models are missing.
- Not suitable for identity embeddings or clustering; use only as auxiliary metadata.

## Browser-based options
- MediaPipe JS / TFJS detection for client-side previews.
- Transformers.js for lightweight attribute classification (no embeddings).

## Recommended fallback strategy
1. Keep InsightFace as default for embeddings + clustering.
2. Allow detection fallbacks (MediaPipe/YOLO/remote) when InsightFace is unavailable.
3. Add compatibility gating to prevent mixing embedding backends in the same cluster.
4. Provide optional hosted provider adapters (AWS/Azure/Google/Face++).

Tracking tasks live in `FACE_TODOS.md`.

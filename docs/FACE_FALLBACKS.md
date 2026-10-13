# Face fallback strategy (local + API + VLM + browser)

This project keeps **InsightFace** as the default for face detection + embeddings.
The goal of this document is to outline **fallback options** and how to wire them
without removing InsightFace.

---

## Feature-by-feature options

### 1) Face detection (bounding boxes)

**Local/Open-source**
- InsightFace RetinaFace (current default)
- MediaPipe Face Detection (fast, CPU-friendly)
- YOLO face variants (fast on GPU, requires weights)

**API/Hosted**
- AWS Rekognition (DetectFaces)
- Azure Face (Detect)
- Google Vision Face Detection

**Browser**
- face-api.js (TensorFlow.js, works in-browser)
- MediaPipe JS face detector (lightweight)

**VLM/LLM**
- Not ideal for precise bounding boxes; best for coarse tagging.

---

### 2) Face embeddings (recognition / clustering)

**Local/Open-source**
- InsightFace ArcFace (current default embeddings)
- `facenet-pytorch` (reasonable fallback)
- `deepface` (wraps multiple models; heavier)
- CLIP embeddings on face crops (fallback only; lower precision)

**API/Hosted**
- AWS Rekognition (CompareFaces / SearchFacesByImage; no raw embeddings)
- Azure Face (Verify / Identify; no raw embeddings)
- Google Vision (face set matching; no raw embeddings)

**Browser**
- face-api.js face recognition (descriptor vectors)

**VLM/LLM**
- Not a good replacement for metric embeddings.

---

### 3) Face attributes (age, emotion, gender, quality)

**Local/Open-source**
- InsightFace attribute heads (if model supports)
- `deepface` attributes
- `fer` / `emotion-recognition` models

**API/Hosted**
- AWS Rekognition (AgeRange, Emotions)
- Azure Face (Attributes)
- Google Vision (face attributes)

**VLM/LLM**
- GPT-4o / Claude / Gemini can infer attributes but are not deterministic.

---

### 4) Video face tracking

**Local/Open-source**
- OpenCV + SORT/DeepSORT
- `bytetrack` + detector (YOLO / InsightFace)

**API/Hosted**
- Limited; typically expensive and slower

---

## Fallback order (recommended)

1) InsightFace (detection + embeddings)
2) Local detector + InsightFace embeddings (if detector fails)
3) Local detector + CLIP embeddings (last-resort fallback)
4) Remote detection/embedding API (optional)

---

## Configuration hooks (implemented)

### Detection backends
- `FACE_BACKENDS=insightface,mediapipe,yolo,remote`
- `FACE_YOLO_WEIGHTS=/path/to/yolo-face.pt`
- `FACE_REMOTE_DETECT_URL=https://...`
- `FACE_REMOTE_DETECT_API_KEY=...`
- `FACE_REMOTE_DETECT_TIMEOUT=10`
- `FACE_REMOTE_DETECT_EMBEDDINGS=1` (if remote returns embeddings)

### Embedding backends
- `FACE_EMBEDDING_BACKENDS=insightface,clip,remote`
- `FACE_CLIP_EMBEDDING_MODEL=clip-ViT-B-32`
- `FACE_REMOTE_EMBEDDING_URL=https://...`
- `FACE_REMOTE_EMBEDDING_API_KEY=...`
- `FACE_REMOTE_EMBEDDING_TIMEOUT=10`

---

## Remote API contract (reference)

### Detect faces endpoint

Request:

```json
{ "image_b64": "..." }
```

Response:

```json
{
  "faces": [
    {
      "bounding_box": [x, y, w, h],
      "confidence": 0.95,
      "embedding": [0.01, 0.02, "..."],
      "embedding_version": "optional"
    }
  ]
}
```

### Embed face endpoint

Request:

```json
{ "image_b64": "..." }
```

Response:

```json
{
  "embedding": [0.01, 0.02, "..."],
  "embedding_version": "optional"
}
```

---

## Notes / gotchas

- Clustering **requires embeddings**. If a backend is detection-only, configure
  `FACE_EMBEDDING_BACKENDS` to supply embeddings from another source.
- API-based services often **do not return raw embeddings**, only similarity
  scores. Use those only if you are willing to adapt the clustering logic.

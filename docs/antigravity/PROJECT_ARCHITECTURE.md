# Photo Search Application - Architecture Document

**Created by:** Antigravity (AI Assistant)
**Date:** 2025-12-06
**Purpose:** Technical architecture and design decisions for the photo search application

---

## System Architecture Overview

This document outlines the technical architecture for a modular, Python-based AI-powered photo search application designed for learning and experimentation.

## Design Philosophy

### Core Principles
1. **Modularity First** - Each component is self-contained and reusable
2. **One Task, One File** - Clear separation of concerns
3. **API Flexibility** - Support multiple AI providers
4. **Progressive Enhancement** - Start simple, add complexity as needed
5. **Cost Awareness** - Optimize API usage for learning budget

## Proposed Module Breakdown

### Tier 1: Foundation (Essential)

#### 1. Configuration Management (`config.py`)
**Purpose:** Centralized configuration and API key management

**Responsibilities:**
- Load environment variables from `.env`
- Validate API keys
- Provide configuration objects to other modules
- Support multiple AI provider credentials

**Key Functions:**
```python
get_api_key(provider: str) -> str
get_config(section: str) -> dict
validate_config() -> bool
```

**Dependencies:** `python-dotenv`, `os`

---

#### 2. Image Loader (`image_loader.py`)
**Purpose:** Handle image loading, validation, and preprocessing

**Responsibilities:**
- Load images from various sources (local, URL)
- Validate image formats
- Resize and normalize images
- Convert between formats
- Extract basic metadata (dimensions, format, size)

**Key Functions:**
```python
load_image(path: str) -> Image
validate_image(image: Image) -> bool
resize_image(image: Image, max_size: tuple) -> Image
get_metadata(image: Image) -> dict
```

**Dependencies:** `Pillow`, `requests`, `pathlib`

---

#### 3. Embedding Generator (`embedding_generator.py`)
**Purpose:** Convert images to vector embeddings using AI models

**Responsibilities:**
- Generate embeddings using CLIP or similar models
- Support multiple embedding providers (OpenAI, HuggingFace, etc.)
- Cache embeddings to avoid redundant API calls
- Normalize embedding vectors

**Key Functions:**
```python
generate_embedding(image: Image, provider: str) -> np.ndarray
generate_text_embedding(text: str, provider: str) -> np.ndarray
batch_generate_embeddings(images: list) -> list[np.ndarray]
```

**Dependencies:** `openai`, `transformers`, `sentence-transformers`, `numpy`

**AI Providers:**
- OpenAI CLIP
- HuggingFace CLIP models
- Replicate models
- Custom models via OpenRouter

---

#### 4. Vector Store (`vector_store.py`)
**Purpose:** Store and retrieve image embeddings efficiently

**Responsibilities:**
- Store embeddings with metadata
- Perform similarity search
- Support different storage backends (in-memory, FAISS, ChromaDB)
- Save/load index to disk

**Key Functions:**
```python
add_embedding(embedding: np.ndarray, metadata: dict) -> str
search_similar(query_embedding: np.ndarray, top_k: int) -> list
save_index(path: str) -> bool
load_index(path: str) -> bool
```

**Dependencies:** `numpy`, `faiss-cpu` (optional), `chromadb` (optional)

---

### Tier 2: Search Capabilities

#### 5. Search Engine (`search_engine.py`)
**Purpose:** High-level search interface combining all components

**Responsibilities:**
- Text-to-image search
- Image-to-image search
- Hybrid search (combining multiple signals)
- Result ranking and filtering

**Key Functions:**
```python
search_by_text(query: str, top_k: int) -> list
search_by_image(image_path: str, top_k: int) -> list
search_hybrid(text: str, image_path: str, top_k: int) -> list
```

**Dependencies:** All Tier 1 modules

---

#### 6. Metadata Extractor (`metadata_extractor.py`)
**Purpose:** Extract rich metadata from images using AI

**Responsibilities:**
- Generate image captions
- Extract objects and entities
- Detect colors and composition
- Extract EXIF data
- Generate descriptive tags

**Key Functions:**
```python
generate_caption(image: Image) -> str
detect_objects(image: Image) -> list[dict]
extract_colors(image: Image) -> list[str]
extract_exif(image_path: str) -> dict
```

**Dependencies:** `Pillow`, `openai`, `replicate`, `exifread`

---

### Tier 3: Advanced Features

#### 7. Object Detector (`object_detector.py`)
**Purpose:** Identify and locate objects within images

**Responsibilities:**
- Detect objects using YOLO/DETR models
- Return bounding boxes and confidence scores
- Support custom object classes

**Key Functions:**
```python
detect_objects(image: Image, confidence: float) -> list[dict]
detect_faces(image: Image) -> list[dict]
```

**Dependencies:** `roboflow`, `transformers`, `ultralytics`

---

#### 8. Scene Classifier (`scene_classifier.py`)
**Purpose:** Classify image scenes and contexts

**Responsibilities:**
- Classify scene types (indoor, outdoor, nature, urban, etc.)
- Detect image quality metrics
- Identify photography style

**Key Functions:**
```python
classify_scene(image: Image) -> dict
assess_quality(image: Image) -> dict
```

**Dependencies:** `transformers`, `openai`

---

#### 9. Batch Processor (`batch_processor.py`)
**Purpose:** Process large collections of images efficiently

**Responsibilities:**
- Parallel processing of images
- Progress tracking
- Error handling and retry logic
- Rate limiting for API calls

**Key Functions:**
```python
process_directory(path: str, workers: int) -> dict
process_batch(image_paths: list) -> list[dict]
```

**Dependencies:** `concurrent.futures`, `tqdm`

---

### Tier 4: Intelligence & Optimization

#### 10. Cache Manager (`cache_manager.py`)
**Purpose:** Cache API responses to reduce costs

**Responsibilities:**
- Cache embeddings and API responses
- Implement cache invalidation strategies
- Track cache hit rates

**Key Functions:**
```python
cache_embedding(image_hash: str, embedding: np.ndarray)
get_cached_embedding(image_hash: str) -> np.ndarray
clear_cache()
```

**Dependencies:** `hashlib`, `pickle`, `json`

---

## Data Flow Architecture

```
User Input (Text/Image)
    ↓
Search Engine
    ↓
    ├─→ Image Loader (if image query)
    ├─→ Embedding Generator
    ↓
Vector Store (Similarity Search)
    ↓
Results + Metadata
    ↓
Ranked Results to User
```

## Storage Strategy

### File Structure
```
photosearch_experiment/
├── data/
│   ├── images/              # Sample images
│   ├── embeddings/          # Cached embeddings
│   └── metadata/            # Image metadata JSON
├── outputs/
│   ├── search_results/      # Search result logs
│   └── visualizations/      # Result visualizations
└── cache/
    ├── api_responses/       # Cached API calls
    └── embeddings/          # Embedding cache
```

### Vector Storage Options

**Option 1: In-Memory (Learning Phase)**
- Simple NumPy arrays
- Fast for small datasets (<10k images)
- No external dependencies

**Option 2: FAISS (Production Phase)**
- Efficient similarity search
- Supports large datasets
- GPU acceleration available

**Option 3: ChromaDB (Future)**
- Full vector database
- Built-in metadata filtering
- Persistent storage

## AI Provider Strategy

### Multi-Provider Support
Support multiple providers for flexibility and cost optimization:

| Provider | Use Case | Cost | Speed |
|----------|----------|------|-------|
| OpenAI | High-quality embeddings | $$$ | Medium |
| HuggingFace | Open source models | Free | Slow (local) |
| Replicate | Specialized models | $$ | Medium |
| Groq | Fast inference | $ | Very Fast |
| Cerebras | Fast LLM inference | $$ | Very Fast |
| Fal.ai | Image generation | $$ | Fast |

### Fallback Strategy
1. Try primary provider (e.g., OpenAI)
2. If rate limited, fall back to secondary (e.g., HuggingFace)
3. If both fail, use local models

## Error Handling Strategy

### Principles
1. **Graceful Degradation** - Continue with reduced functionality
2. **Informative Errors** - Clear error messages
3. **Retry Logic** - Automatic retry for transient failures
4. **Logging** - Comprehensive logging for debugging

### Error Categories
- **Configuration Errors** - Missing API keys, invalid config
- **Network Errors** - API timeouts, connection failures
- **Data Errors** - Invalid images, corrupt files
- **API Errors** - Rate limits, quota exceeded

## Performance Considerations

### Optimization Strategies
1. **Batch Processing** - Process multiple images in parallel
2. **Caching** - Cache embeddings and API responses
3. **Lazy Loading** - Load images only when needed
4. **Async Operations** - Use async/await for I/O operations
5. **Rate Limiting** - Respect API rate limits

### Scalability Path
1. **Phase 1:** Single-threaded, small datasets (<1k images)
2. **Phase 2:** Multi-threaded, medium datasets (<100k images)
3. **Phase 3:** Distributed processing, large datasets (>100k images)

## Security Considerations

### API Key Management
- Store keys in `.env` file (gitignored)
- Never commit keys to version control
- Use environment variables in production
- Validate keys on startup

### Data Privacy
- No data sent to external services without user consent
- Option to use local models for sensitive data
- Clear documentation of what data is sent where

## Testing Strategy

### Test Levels
1. **Unit Tests** - Test individual functions
2. **Integration Tests** - Test module interactions
3. **End-to-End Tests** - Test complete workflows
4. **Performance Tests** - Benchmark search speed

### Test Data
- Small set of diverse sample images
- Known search queries with expected results
- Edge cases (corrupt images, unusual formats)

## Future Enhancements

### Potential Features
- **Face Recognition** - Cluster and search by faces
- **Duplicate Detection** - Find similar/duplicate images
- **Auto-Tagging** - Automatic tag generation
- **Smart Albums** - AI-powered photo organization
- **Video Search** - Extend to video content
- **Multi-modal Search** - Combine text, image, audio queries

### Integration Possibilities
- **Cloud Storage** - Google Drive, Dropbox integration
- **Photo Apps** - Apple Photos, Google Photos export
- **Web Interface** - Simple web UI for demos
- **Mobile App** - iOS/Android companion app

---

## Decision Log

### Key Architectural Decisions

**Decision 1: Python-Only Implementation**
- **Rationale:** Focus on learning, rapid prototyping
- **Trade-off:** May need to rewrite for production performance

**Decision 2: Modular File Structure**
- **Rationale:** Easy to understand, test, and reuse
- **Trade-off:** More files to manage

**Decision 3: Multi-Provider AI Support**
- **Rationale:** Flexibility, cost optimization, learning
- **Trade-off:** More complex configuration

**Decision 4: Start with Simple Vector Storage**
- **Rationale:** Lower barrier to entry, easier to understand
- **Trade-off:** Will need migration for larger datasets

---

**Document Status:** Living Document - Updated as architecture evolves
**Next Review:** After completing Tier 1 modules

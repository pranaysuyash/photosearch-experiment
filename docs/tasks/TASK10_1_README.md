# Task 10.1: Semantic Embedding Engine

## Goal
Implement the "brain" of the semantic search system by integrating a machine learning model capable of converting images and text into a shared vector space.

## Components

### `server/embedding_generator.py`
This module hosts the `EmbeddingGenerator` class which wraps the `sentence-transformers` library (specifically the CLIP model).

*   **Model**: `clip-ViT-B-32`
    *   *Why?* Good balance of performance and accuracy. Maps images and text to the same 512-dimensional vector space.
*   **Input**:
    *   `generate_image_embedding(image)`: Takes a PIL Image.
    *   `generate_text_embedding(text)`: Takes a raw string.
*   **Output**: 512-float vector (list).

## Verification
Run `test_embedding.py` to verify:
1.  Model loads correctly.
2.  Text ("dog") generates a 512-dim vector.
3.  Image (`sample1.jpg`) generates a 512-dim vector.

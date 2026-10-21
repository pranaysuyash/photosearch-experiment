import os
import time
from typing import List, TYPE_CHECKING

from server.image_loader import load_image

if TYPE_CHECKING:
    from server.embedding_generator import EmbeddingGenerator
    from server.vector_store import VectorStore


def process_semantic_indexing(
    files_to_index: List[str],
    embedding_generator: "EmbeddingGenerator",
    vector_store: "VectorStore",
):
    """
    Helper to generate embeddings for a list of file paths.

    Args:
        files_to_index: List of file paths to index
        embedding_generator: The embedding generator instance
        vector_store: The vector store instance for storing embeddings
    """
    print(f"Indexing {len(files_to_index)} files for semantic search...")

    model_name = getattr(embedding_generator, "model_name", "unknown")

    # 1. Deduplication: Filter out files that are already indexed.
    # Using Full Path as ID to avoid collisions. If the table was built by a
    # different embedding model, dedupe would silently reuse stale vectors —
    # reset instead so everything is re-embedded into the current space.
    has_stamping = hasattr(vector_store, "get_index_model")
    stamp = vector_store.get_index_model() if has_stamping else None
    if stamp and stamp.get("model") and stamp["model"] != model_name:
        print(
            f"Embedding model changed ({stamp['model']} → {model_name}); "
            "resetting vector index so all photos re-embed consistently."
        )
        try:
            vector_store.reset()
        except Exception as e:
            print(f"Index reset failed: {e}")

    try:
        existing_ids = vector_store.get_all_ids()
        files_to_process = [f for f in files_to_index if f not in existing_ids]
    except Exception as e:
        print(f"Error checking existing IDs: {e}")
        files_to_process = files_to_index

    if not files_to_process:
        print("All files already indexed. Skipping.")
        return

    print(
        f"Processing {len(files_to_process)} new files (skipped {len(files_to_index) - len(files_to_process)} existing)..."
    )

    ids = []
    vectors = []
    metadatas = []
    loaded_images = []

    for i, file_path in enumerate(files_to_process):
        if i % 10 == 0:
            print(f"  Loaded {i}/{len(files_to_process)}...")

        try:
            # Check for valid image or video extensions
            valid_img_exts = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".heic", ".tiff", ".tif"]
            valid_vid_exts = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]

            is_video = False
            if any(file_path.lower().endswith(ext) for ext in valid_vid_exts):
                is_video = True
            elif not any(file_path.lower().endswith(ext) for ext in valid_img_exts):
                continue

            img = None
            if is_video:
                from server.image_loader import extract_video_frame

                # Extract frame
                try:
                    img = extract_video_frame(file_path)
                except Exception as ve:
                    print(f"Skipping video {os.path.basename(file_path)}: {ve}")
                    continue
            else:
                img = load_image(file_path)

            if img:
                # FIX: Use full path as ID to ensure uniqueness
                ids.append(file_path)
                # Store minimalist metadata, relies on main DB for details
                metadatas.append(
                    {
                        "path": file_path,
                        "filename": os.path.basename(file_path),
                        "type": "video" if is_video else "image",
                    }
                )
                loaded_images.append(img)
        except Exception as e:
            print(f"Failed to prepare {file_path}: {e}")

    # Batch embedding: backends differ by orders of magnitude in per-batch vs
    # per-image cost (EG2/MLX: ~3 img/s unbatched vs ~160 batched).
    if ids:
        time_start = time.time()
        try:
            vectors = embedding_generator.generate_image_embeddings(loaded_images)
        except Exception as batch_err:
            # Real libraries contain files that decode but fail mid-embed; one
            # bad image must not discard the whole batch. Fall back to
            # per-image embedding, skipping failures individually.
            print(f"Batch embedding failed ({batch_err}); falling back to per-image.")
            vectors = []
            kept_images = []
            kept_ids = []
            kept_metadatas = []
            for file_path, img, metadata in zip(ids, loaded_images, metadatas):
                try:
                    vectors.append(embedding_generator.generate_image_embedding(img))
                    kept_ids.append(file_path)
                    kept_images.append(img)
                    kept_metadatas.append(metadata)
                except Exception as img_err:
                    print(f"Skipping unembeddable {file_path}: {img_err}")
            ids, metadatas = kept_ids, kept_metadatas
        print(
            f"Embedded {len(vectors)} images in {time.time() - time_start:.1f}s "
            f"({len(vectors) / max(time.time() - time_start, 1e-6):.1f} img/s)."
        )

    if ids and len(vectors) == len(ids):
        time_start = time.time()
        vector_store.add_batch(ids, vectors, metadatas)
        print(f"Added {len(ids)} vectors to LanceDB in {time.time() - time_start:.2f}s.")

        # Stamp the table with the model that built it (diagnostics + the
        # dimension guard in LanceDBStore.search depend on this).
        if has_stamping:
            try:
                vector_store.set_index_model(model_name, embedding_generator.embedding_dimension)
            except Exception as e:
                print(f"Index model stamping failed (non-fatal): {e}")
    elif ids:
        print(f"Embedding produced {len(vectors)} vectors for {len(ids)} files; skipping write.")

import os
from typing import List

from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image


def process_semantic_indexing(files_to_index: List[str]):
    """
    Helper to generate embeddings for a list of file paths.
    """
    from server import main as main_module

    if not main_module.embedding_generator:
        main_module.embedding_generator = EmbeddingGenerator()

    print(f"Indexing {len(files_to_index)} files for semantic search...")

    # 1. Deduplication: Filter out files that are already indexed
    # Using Full Path as ID to avoid collisions
    try:
        existing_ids = main_module.vector_store.get_all_ids()
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

    for i, file_path in enumerate(files_to_process):
        if i % 10 == 0:
            print(f"  Processed {i}/{len(files_to_process)}...")

        try:
            # Check for valid image or video extensions
            valid_img_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.heic', '.tiff', '.tif']
            valid_vid_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v']

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
                vec = main_module.embedding_generator.generate_image_embedding(img)
                if vec:
                    # FIX: Use full path as ID to ensure uniqueness
                    ids.append(file_path)
                    vectors.append(vec)
                    # Store minimalist metadata, relies on main DB for details
                    metadatas.append({
                        "path": file_path,
                        "filename": os.path.basename(file_path),
                        "type": "video" if is_video else "image",
                    })
        except Exception as e:
            print(f"Failed to embed {file_path}: {e}")

    if ids:
        time_start = __import__("time").time()
        main_module.vector_store.add_batch(ids, vectors, metadatas)
        print(
            f"Added {len(ids)} vectors to LanceDB in {__import__('time').time() - time_start:.2f}s."
        )

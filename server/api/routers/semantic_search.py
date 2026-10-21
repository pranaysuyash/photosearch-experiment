"""
Semantic Search Router

Uses Depends(get_state) for accessing shared application state.
"""

import os

from fastapi import APIRouter, Depends, HTTPException

from server.models.schemas.search import SearchCountRequest
from server.utils.search_explanations import generate_semantic_match_explanation
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/api/search/count")
async def get_search_count(request: SearchCountRequest, state: AppState = Depends(get_state)):
    """
    Get count of search results for live feedback while typing.
    Used for the live match count feature in the UI.
    """
    try:
        query = request.query.strip()
        mode = request.mode

        photo_search_engine = state.photo_search_engine
        embedding_generator = state.embedding_generator
        vector_store = state.vector_store

        if not query:
            return {"count": 0}

        # Get count based on search mode
        if mode == "metadata":
            # Check if query has structured operators
            has_operators = any(op in query for op in ["=", ">", "<", "!=", " LIKE ", " CONTAINS ", ":"])

            if not has_operators:
                # Simple search term - search in filename
                search_query = f"filename:{query}"
                results = photo_search_engine.query_engine.search(search_query)
            else:
                # Structured query - use as-is
                results = photo_search_engine.query_engine.search(query)

            return {"count": len(results)}

        elif mode == "semantic":
            if not embedding_generator:
                return {"count": 0}

            # Generate text embedding and search
            text_vec = embedding_generator.generate_text_embedding(query)
            results = vector_store.search(text_vec, limit=1000, offset=0)

            # Filter by minimum score and apply more realistic scoring
            filtered_results = []
            matched_paths = set()
            for r in results:
                # Apply more realistic scoring - prevent inflated scores
                adjusted_score = r["score"]
                if adjusted_score >= 0.22:  # Only include meaningful matches
                    # Cap scores to prevent unrealistic high matches
                    if adjusted_score > 0.9:
                        adjusted_score = 0.85 + (adjusted_score - 0.9) * 0.3  # Compress high scores
                    r["score"] = adjusted_score
                    filtered_results.append(r)
                    matched_paths.add(r.get("metadata", {}).get("path"))

            # Caption-only matches count too (see search_semantic fusion).
            caption_index = getattr(state, "caption_index", None)
            if caption_index is not None:
                try:
                    if caption_index.get_count() > 0:
                        caption_query_vec = caption_index.embed_query(query, embedding_generator)
                        for c in caption_index.search(caption_query_vec, limit=1000, min_score=0.22):
                            if c["path"] not in matched_paths:
                                filtered_results.append({"path": c["path"], "score": c["score"]})
                except Exception:
                    pass
            return {"count": len(filtered_results)}

        elif mode == "hybrid":
            # For hybrid, we need to estimate based on both modes
            # This is a simplified count - actual hybrid search is more complex
            metadata_count = 0
            semantic_count = 0

            # Get metadata count
            try:
                if any(op in query for op in ["=", ">", "<", "LIKE"]):
                    metadata_results = photo_search_engine.query_engine.search(query)
                else:
                    safe_query = query.replace("'", "''")
                    metadata_results = photo_search_engine.query_engine.search(f"file.path LIKE '%{safe_query}%'")
                metadata_count = len(metadata_results)
            except Exception:
                pass

            # Get semantic count
            try:
                if embedding_generator:
                    text_vec = embedding_generator.generate_text_embedding(query)
                    semantic_results = vector_store.search(text_vec, limit=1000, offset=0)
                    semantic_count = len([r for r in semantic_results if r["score"] >= 0.22])
            except Exception:
                pass

            # Estimate hybrid count (will have some overlap)
            estimated_count = max(metadata_count, semantic_count)
            return {"count": estimated_count}

        return {"count": 0}

    except Exception as e:
        print(f"Search count error: {e}")
        return {"count": 0}


@router.get("/search/semantic")
async def search_semantic(
    state: AppState = Depends(get_state),
    query: str = "",
    limit: int = 50,
    offset: int = 0,
    min_score: float = 0.22,
):
    """
    Semantic Search using text-to-image embeddings.
    """
    try:
        from server.embedding_generator import EmbeddingGenerator

        embedding_generator = state.embedding_generator
        vector_store = state.vector_store
        photo_search_engine = state.photo_search_engine

        if not embedding_generator:
            embedding_generator = EmbeddingGenerator()
            state.embedding_generator = embedding_generator

        # Handle empty query - return all photos (paginated)
        if not query.strip():
            try:
                # Pass offset to store
                all_records = vector_store.get_all_records(limit=limit, offset=offset)
                formatted = []
                for r in all_records:
                    file_path = r.get("path", r.get("id", ""))
                    full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)
                    formatted.append(
                        {
                            "path": file_path,
                            "filename": r.get("filename", os.path.basename(file_path)),
                            "score": 0,
                            "metadata": full_metadata or {},
                        }
                    )
                # Count is tricky here, but we return page size for now
                return {"count": len(formatted), "results": formatted}
            except Exception as e:
                print(f"Error getting all records: {e}")
                return {"count": 0, "results": []}

        # 1. Generate text embedding
        text_vec = embedding_generator.generate_text_embedding(query)

        # 2. Search LanceDB. Fetch limit+offset on the image leg so caption
        # fusion below ranks globally before pagination is applied.
        results = vector_store.search(text_vec, limit=limit + offset, offset=0)

        # 2a. Quality rerank: when the background EG2 space covers the
        # candidate window, reorder it by EG2 similarity (best measured
        # top-1 precision). Partial coverage would mix score scales, so we
        # rerank only when fully caught up.
        from server.config import settings as _settings

        quality_index = getattr(state, "image_quality_index", None)
        if _settings.IMAGE_QUALITY_RERANK and quality_index is not None and results:
            try:
                if quality_index.embedder.available() and quality_index.get_count() > 0:
                    candidate_paths = [r["metadata"]["path"] for r in results if r["score"] >= min_score]
                    if (
                        candidate_paths
                        and quality_index.coverage(candidate_paths) >= _settings.IMAGE_QUALITY_RERANK_MIN_COVERAGE
                    ):
                        quality_query_vec = quality_index.embedder.embed_query(query)
                        quality_scores = quality_index.rerank(quality_query_vec, candidate_paths)
                        for r in results:
                            if r["metadata"]["path"] in quality_scores:
                                r["score"] = quality_scores[r["metadata"]["path"]]
                                r["qualityReranked"] = True
            except Exception as e:
                print(f"Quality rerank skipped (non-fatal): {e}")

        # 2b. Caption leg: the query embedded in the caption index's own space
        # (dedicated text model, else the app generator) — query and captions
        # always share one embedding space (see CaptionSearchIndex).
        caption_matches = {}
        caption_index = getattr(state, "caption_index", None)
        if caption_index is not None:
            try:
                if caption_index.get_count() > 0:
                    caption_query_vec = caption_index.embed_query(query, embedding_generator)
                    for c in caption_index.search(caption_query_vec, limit=limit + offset, min_score=min_score):
                        caption_matches[c["path"]] = c
            except Exception as e:
                print(f"Caption search leg failed (non-fatal): {e}")

        # 3. Format and enrich
        formatted = []
        seen_paths = set()
        for r in results:
            if r["score"] >= min_score:
                file_path = r["metadata"]["path"]
                seen_paths.add(file_path)
                full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)

                score = r["score"]
                matched_via = "image"
                cap = caption_matches.get(file_path)
                if cap and cap["score"] > score:
                    score = cap["score"]
                    matched_via = "caption"

                result_item = {
                    "path": file_path,
                    "filename": r["metadata"]["filename"],
                    "score": score,
                    "metadata": full_metadata or r["metadata"],
                    "matchedVia": matched_via,
                }
                if r.get("qualityReranked"):
                    result_item["qualityReranked"] = True

                # Generate match explanation for semantic search
                if query.strip():
                    result_item["matchExplanation"] = generate_semantic_match_explanation(
                        query,
                        result_item,
                        score,
                    )

                formatted.append(result_item)

        # Caption-only matches (no image-vector hit above threshold).
        for path, cap in caption_matches.items():
            if path in seen_paths:
                continue
            full_metadata = photo_search_engine.db.get_metadata_by_path(path) or {}
            result_item = {
                "path": path,
                "filename": os.path.basename(path),
                "score": cap["score"],
                "metadata": full_metadata,
                "matchedVia": "caption",
                "matchExplanation": f"Matched by caption: \"{cap.get('caption', '')[:120]}\"",
            }
            formatted.append(result_item)

        # Global ranking after fusion, then pagination.
        formatted.sort(key=lambda item: item["score"], reverse=True)
        formatted = formatted[offset : offset + limit]

        return {"count": len(formatted), "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/feedback")
async def submit_search_feedback(feedback: dict, state: AppState = Depends(get_state)):
    """
    Submit negative feedback for semantic search results.
    Used to improve search quality over time by logging mismatches.

    Body:
    - query: The original search query
    - photo_path: Path of the photo marked as "Not this"
    - score: The similarity score that was shown
    - reason: Optional reason for the mismatch
    """
    import json
    from datetime import datetime

    query = feedback.get("query", "")
    photo_path = feedback.get("photo_path", "")
    score = feedback.get("score", 0)
    reason = feedback.get("reason", "")

    if not query or not photo_path:
        raise HTTPException(status_code=400, detail="Query and photo_path are required")

    # Log feedback to a file for future analysis
    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "photo_path": photo_path,
        "score": score,
        "reason": reason,
        "action": "not_this",
    }

    # Append to feedback log file
    feedback_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "semantic_feedback.jsonl",
    )
    os.makedirs(os.path.dirname(feedback_file), exist_ok=True)

    try:
        with open(feedback_file, "a") as f:
            f.write(json.dumps(feedback_entry) + "\n")
    except Exception as e:
        print(f"Failed to write feedback: {e}")

    return {
        "success": True,
        "message": "Feedback recorded. Thank you for helping improve search quality!",
    }

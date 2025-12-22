"""
FastAPI dependency injection helpers.

This module provides Depends() functions for accessing AppState in routers.

IMPORTANT: This file must be extremely clean to avoid circular imports.
- Only imports from server.core.state (AppState dataclass)
- Does NOT import from server.main
- Does NOT import routers

Usage in routers:
    from fastapi import Depends
    from server.api.deps import get_state
    from server.core.state import AppState
    
    @router.get("/example")
    async def example(state: AppState = Depends(get_state)):
        face_clusterer = state.face_clusterer
        ...
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from server.core.state import AppState


def get_state(request: Request) -> AppState:
    """
    Get application state from request.
    
    Use with: state: AppState = Depends(get_state)
    """
    st = getattr(request.app.state, "ps", None)
    if st is None:
        raise RuntimeError(
            "AppState not initialized. Did lifespan run? "
            "Check that app.state.ps was set during startup."
        )
    return st


# ─────────────────────────────────────────────────────────────────────────────
# Convenience dependencies using Depends chaining (per ChatGPT recommendation)
# ─────────────────────────────────────────────────────────────────────────────

def get_face_clusterer(state: AppState = Depends(get_state)):
    """Get face clusterer, raising 503 if not available."""
    if state.face_clusterer is None:
        raise HTTPException(
            status_code=503, 
            detail="Face clusterer not configured or still loading"
        )
    return state.face_clusterer


def get_photo_search_engine(state: AppState = Depends(get_state)):
    """Get photo search engine, raising 503 if not initialized."""
    if state.photo_search_engine is None:
        raise HTTPException(
            status_code=503,
            detail="Photo search engine not initialized"
        )
    return state.photo_search_engine


def get_embedding_generator(state: AppState = Depends(get_state)):
    """Get embedding generator, raising 503 if not initialized."""
    if state.embedding_generator is None:
        raise HTTPException(
            status_code=503,
            detail="Embedding generator not initialized"
        )
    return state.embedding_generator


def get_vector_store(state: AppState = Depends(get_state)):
    """Get vector store (LanceDB)."""
    return state.vector_store


def get_intent_detector(state: AppState = Depends(get_state)):
    """Get intent detector."""
    return state.intent_detector


def get_saved_search_manager(state: AppState = Depends(get_state)):
    """Get saved search manager."""
    return state.saved_search_manager


def get_source_store(state: AppState = Depends(get_state)):
    """Get source store."""
    return state.source_store


def get_source_item_store(state: AppState = Depends(get_state)):
    """Get source item store."""
    return state.source_item_store


def get_trash_db(state: AppState = Depends(get_state)):
    """Get trash database."""
    return state.trash_db


def get_video_analyzer(state: AppState = Depends(get_state)):
    """Get video analyzer, raising 503 if not available."""
    if state.video_analyzer is None:
        raise HTTPException(
            status_code=503,
            detail="Video analyzer not configured"
        )
    return state.video_analyzer


def get_ocr_search(state: AppState = Depends(get_state)):
    """Get OCR search, raising 503 if not available."""
    if state.ocr_search is None:
        raise HTTPException(
            status_code=503,
            detail="OCR search not configured"
        )
    return state.ocr_search

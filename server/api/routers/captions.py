"""
VLM Captions API Router

Provides endpoints for AI-generated photo captions. Generated/edited captions
are also embedded into the caption search index so they participate in
semantic/hybrid search (see server/caption_search_index.py).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter(prefix="/api/captions", tags=["captions"])


def _get_service(state: AppState):
    """Build the caption service against the canonical captions DB path."""
    from server.config import settings
    from server.vlm_caption_service import VLMCaptionService

    db_path = state.captions_db_path or settings.CAPTIONS_DB_PATH
    return VLMCaptionService(db_path)


def _index_caption(state: AppState, photo_path: str, caption: Optional[str], updated_at: Optional[str] = None):
    """Keep the caption vector index in sync (best-effort, never fatal)."""
    try:
        index = state.caption_index
        if index is None:
            from server.caption_search_index import get_caption_index

            index = state.caption_index = get_caption_index()
        if caption and caption.strip():
            index.index_caption(photo_path, caption, state.embedding_generator, caption_updated_at=updated_at)
        else:
            index.drop(photo_path)
    except Exception as e:
        print(f"Caption index sync failed for {photo_path}: {e}")


class GenerateCaptionRequest(BaseModel):
    photo_path: str
    force: bool = False


class UpdateCaptionRequest(BaseModel):
    photo_path: str
    caption: str


class CaptionResponse(BaseModel):
    caption: Optional[str]
    model_version: Optional[str]
    provider: Optional[str]
    is_generated: bool = True
    is_edited: bool = False
    error: Optional[str] = None


@router.get("/status")
async def get_vlm_status(state: AppState = Depends(get_state)):
    """
    Get VLM captioning service status and available providers.
    """
    try:
        service = _get_service(state)

        return {
            "enabled": service.is_enabled(),
            "active_provider": service.provider_name,
            "providers": service.get_available_providers(),
            "stats": service.get_stats(),
        }
    except ImportError:
        return {
            "enabled": False,
            "providers": [],
            "stats": {"total_captions": 0},
            "error": "VLM service not available",
        }


@router.post("/generate", response_model=CaptionResponse)
async def generate_caption(request: GenerateCaptionRequest, state: AppState = Depends(get_state)):
    """
    Generate an AI caption for a photo.

    NOTE: Captions are AI-generated and may be inaccurate.
    """
    try:
        service = _get_service(state)

        if not service.is_enabled():
            raise HTTPException(
                status_code=503,
                detail=(
                    "VLM captioning is not enabled. Start Ollama and pull the "
                    "configured model (default: ollama pull gemma4:e4b), or set "
                    "GEMINI_API_KEY / OPENAI_API_KEY for cloud captioning."
                ),
            )

        result = service.generate_caption(request.photo_path, force=request.force)

        if result.get("error"):
            return CaptionResponse(caption=None, error=result["error"])

        # Keep the search index in sync with the new caption.
        _index_caption(state, request.photo_path, result.get("caption"))

        return CaptionResponse(
            caption=result.get("caption"),
            model_version=result.get("model_version"),
            provider=result.get("provider"),
            is_generated=result.get("is_generated", True),
            is_edited=result.get("is_edited", False),
        )

    except ImportError:
        raise HTTPException(status_code=503, detail="VLM service not available")


@router.get("/search-status")
async def get_caption_search_status(state: AppState = Depends(get_state)):
    """Caption search index stats (count + stamped model)."""
    try:
        index = state.caption_index
        if index is None:
            from server.caption_search_index import get_caption_index

            index = state.caption_index = get_caption_index()
        return index.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Caption index status failed: {e}")


@router.post("/reindex")
async def reindex_captions(state: AppState = Depends(get_state), force: bool = False):
    """(Re)embed all stored captions into the caption search index."""
    try:
        service = _get_service(state)
        index = state.caption_index
        if index is None:
            from server.caption_search_index import get_caption_index

            index = state.caption_index = get_caption_index()

        if state.embedding_generator is None:
            raise HTTPException(status_code=503, detail="Embedding generator not initialized")

        rows = service.get_all_captions()
        stats = index.ensure_indexed(rows, state.embedding_generator, force=force)
        return {"total_captions": len(rows), **stats, "index": index.get_stats()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Caption reindex failed: {e}")


@router.get("/{photo_path:path}")
async def get_caption(photo_path: str, state: AppState = Depends(get_state)):
    """Get the stored caption for a photo."""
    try:
        service = _get_service(state)
        caption = service.get_caption(photo_path)

        if not caption:
            raise HTTPException(status_code=404, detail="Caption not found")

        return caption

    except ImportError:
        raise HTTPException(status_code=503, detail="VLM service not available")


@router.put("/")
async def update_caption(request: UpdateCaptionRequest, state: AppState = Depends(get_state)):
    """Manually update/edit a caption."""
    try:
        service = _get_service(state)
        service.update_caption(request.photo_path, request.caption)

        _index_caption(state, request.photo_path, request.caption)

        return {"success": True, "message": "Caption updated"}

    except ImportError:
        raise HTTPException(status_code=503, detail="VLM service not available")


@router.delete("/{photo_path:path}")
async def delete_caption(photo_path: str, state: AppState = Depends(get_state)):
    """Delete a caption."""
    try:
        service = _get_service(state)
        service.delete_caption(photo_path)

        _index_caption(state, photo_path, None)

        return {"success": True, "message": "Caption deleted"}

    except ImportError:
        raise HTTPException(status_code=503, detail="VLM service not available")

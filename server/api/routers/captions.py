"""
VLM Captions API Router

Provides endpoints for AI-generated photo captions.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter(prefix="/api/captions", tags=["captions"])


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
        from server.vlm_caption_service import VLMCaptionService

        service = VLMCaptionService(state.db_path)

        return {
            "enabled": service.is_enabled(),
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
        from server.vlm_caption_service import VLMCaptionService

        service = VLMCaptionService(state.db_path)

        if not service.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="VLM captioning is not enabled. Set GEMINI_API_KEY to enable.",
            )

        result = service.generate_caption(request.photo_path, force=request.force)

        if result.get("error"):
            return CaptionResponse(caption=None, error=result["error"])

        return CaptionResponse(
            caption=result.get("caption"),
            model_version=result.get("model_version"),
            provider=result.get("provider"),
            is_generated=result.get("is_generated", True),
            is_edited=result.get("is_edited", False),
        )

    except ImportError:
        raise HTTPException(status_code=503, detail="VLM service not available")


@router.get("/{photo_path:path}")
async def get_caption(photo_path: str, state: AppState = Depends(get_state)):
    """Get the stored caption for a photo."""
    try:
        from server.vlm_caption_service import VLMCaptionService

        service = VLMCaptionService(state.db_path)
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
        from server.vlm_caption_service import VLMCaptionService

        service = VLMCaptionService(state.db_path)
        service.update_caption(request.photo_path, request.caption)

        return {"success": True, "message": "Caption updated"}

    except ImportError:
        raise HTTPException(status_code=503, detail="VLM service not available")


@router.delete("/{photo_path:path}")
async def delete_caption(photo_path: str, state: AppState = Depends(get_state)):
    """Delete a caption."""
    try:
        from server.vlm_caption_service import VLMCaptionService

        service = VLMCaptionService(state.db_path)
        service.delete_caption(photo_path)

        return {"success": True, "message": "Caption deleted"}

    except ImportError:
        raise HTTPException(status_code=503, detail="VLM service not available")

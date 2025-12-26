import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from server.models.schemas.image_analysis import ImageAnalysisRequest
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/ai/analyze")
async def analyze_image(request: ImageAnalysisRequest, state: AppState = Depends(get_state)):
    """
    Analyze an image to extract visual insights and characteristics.

    Args:
        request: ImageAnalysisRequest with image path

    Returns:
        Dictionary with analysis results including caption, tags, objects, etc.
    """
    try:
        photo_search_engine = state.photo_search_engine
        ps_logger = state.ps_logger

        if not photo_search_engine:
            raise HTTPException(status_code=503, detail="Analysis engine not available")

        image_path = request.path

        # Verify the image exists
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image not found")

        # Check if it's actually an image file
        if not any(
            image_path.lower().endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif", ".tif", ".tiff"]
        ):
            raise HTTPException(status_code=400, detail="File is not a supported image format")

        # For now, return a mock analysis since we don't have the actual analysis implementation
        # In a real implementation, this would use computer vision models to analyze the image
        analysis_result = {
            "caption": "We found an interesting photo with various visual elements",
            "tags": ["photo", "image", "visual"],
            "objects": ["general content"],
            "scene": "photograph",
            "colors": ["mixed"],
            "quality": 4.0,
            "analysis_date": datetime.utcnow().isoformat(),
        }

        # Store the analysis result in the database for future retrieval
        try:
            # We could store this in a separate analysis table, but for now we'll just return it
            ps_logger.info(f"Image analysis completed for {image_path}")
        except Exception as e:
            ps_logger.warning(f"Failed to store analysis result: {e}")

        return analysis_result

    except HTTPException:
        raise
    except Exception as e:
        ps_logger = state.ps_logger
        ps_logger.error(f"Image analysis failed for {request.path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Analysis failed")


@router.get("/ai/analysis/{path:path}")
async def get_image_analysis(path: str, state: AppState = Depends(get_state)):
    """
    Get existing analysis results for an image.

    Args:
        path: Path to the image file

    Returns:
        Dictionary with stored analysis results or empty if none exists
    """
    try:
        ps_logger = state.ps_logger

        # Verify the image exists
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Image not found")

        # For now, return empty since we don't have persistent storage implemented
        # In a real implementation, this would query the analysis database
        analysis_result = {}

        return analysis_result

    except HTTPException:
        raise
    except Exception as e:
        ps_logger = state.ps_logger
        ps_logger.error(f"Failed to retrieve analysis for {path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis")

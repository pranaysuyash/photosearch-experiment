from fastapi import APIRouter, HTTPException, Depends

from server.models.schemas.ocr import OCRImageRequest
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/ocr/extract")
async def extract_text_from_images(request: OCRImageRequest, state: AppState = Depends(get_state)):
    """
    Extract text from multiple images

    Args:
        request: OCRImageRequest with list of image paths

    Returns:
        Dictionary with extracted text for each image
    """
    try:

        results = state.ocr_search.extract_text_from_images(request.image_paths)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/search")
async def search_ocr_text(query: str, limit: int = 100, offset: int = 0, state: AppState = Depends(get_state)):
    """
    Search for images containing specific text

    Args:
        query: Text to search for
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        Dictionary with search results
    """
    try:

        results = state.ocr_search.search_text(query, limit, offset)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/stats")
async def get_ocr_stats(state: AppState = Depends(get_state)):
    """
    Get OCR statistics

    Returns:
        Dictionary with OCR statistics
    """
    try:

        stats = state.ocr_search.get_ocr_summary()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/image/{image_path:path}")
async def get_image_ocr_stats(image_path: str, state: AppState = Depends(get_state)):
    """
    Get OCR statistics for a specific image

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with OCR statistics for the image
    """
    try:

        stats = state.ocr_search.get_ocr_stats(image_path)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ocr/image/{image_path:path}")
async def delete_image_ocr_data(image_path: str, state: AppState = Depends(get_state)):
    """
    Delete OCR data for a specific image

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with deletion status
    """
    try:

        success = state.ocr_search.delete_ocr_data(image_path)
        return {"status": "success" if success else "failed", "deleted": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ocr/all")
async def clear_all_ocr_data(state: AppState = Depends(get_state)):
    """
    Clear all OCR data

    Returns:
        Dictionary with deletion count
    """
    try:

        count = state.ocr_search.clear_all_ocr_data()
        return {"status": "success", "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

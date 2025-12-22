from fastapi import APIRouter, HTTPException

from server.models.schemas.ocr import OCRImageRequest


router = APIRouter()


@router.post("/ocr/extract")
async def extract_text_from_images(request: OCRImageRequest):
    """
    Extract text from multiple images

    Args:
        request: OCRImageRequest with list of image paths

    Returns:
        Dictionary with extracted text for each image
    """
    try:
        from server import main as main_module

        results = main_module.ocr_search.extract_text_from_images(request.image_paths)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/search")
async def search_ocr_text(query: str, limit: int = 100, offset: int = 0):
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
        from server import main as main_module

        results = main_module.ocr_search.search_text(query, limit, offset)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/stats")
async def get_ocr_stats():
    """
    Get OCR statistics

    Returns:
        Dictionary with OCR statistics
    """
    try:
        from server import main as main_module

        stats = main_module.ocr_search.get_ocr_summary()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/image/{image_path:path}")
async def get_image_ocr_stats(image_path: str):
    """
    Get OCR statistics for a specific image

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with OCR statistics for the image
    """
    try:
        from server import main as main_module

        stats = main_module.ocr_search.get_ocr_stats(image_path)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ocr/image/{image_path:path}")
async def delete_image_ocr_data(image_path: str):
    """
    Delete OCR data for a specific image

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with deletion status
    """
    try:
        from server import main as main_module

        success = main_module.ocr_search.delete_ocr_data(image_path)
        return {"status": "success" if success else "failed", "deleted": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ocr/all")
async def clear_all_ocr_data():
    """
    Clear all OCR data

    Returns:
        Dictionary with deletion count
    """
    try:
        from server import main as main_module

        count = main_module.ocr_search.clear_all_ocr_data()
        return {"status": "success", "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

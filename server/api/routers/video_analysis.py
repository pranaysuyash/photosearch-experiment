import os
import sqlite3
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Request
from fastapi.responses import FileResponse

from server.models.schemas.video_analysis import VideoAnalysisRequest, VideoSearchRequest


router = APIRouter()


@router.post("/video/analyze")
async def analyze_video_content(background_tasks: BackgroundTasks, request: VideoAnalysisRequest):
    """
    Analyze video content for keyframes, scenes, and text detection.

    This endpoint performs comprehensive video analysis including:
    - Keyframe extraction at regular intervals
    - Scene detection and segmentation
    - OCR text detection in video frames
    - Visual similarity analysis
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer
        ps_logger = main_module.ps_logger

        video_path = request.video_path

        # Validate video file exists
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        # Check if it's actually a video file
        if not any(
            video_path.lower().endswith(ext)
            for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]
        ):
            raise HTTPException(status_code=400, detail="File is not a supported video format")

        # Start analysis in background
        def run_analysis():
            try:
                result = video_analyzer.analyze_video(video_path, force_reprocess=request.force_reprocess)
                ps_logger.info(f"Video analysis completed for {video_path}: {result.get('status')}")
            except Exception as e:
                ps_logger.error(f"Video analysis failed for {video_path}: {str(e)}")

        background_tasks.add_task(run_analysis)

        return {
            "status": "started",
            "video_path": video_path,
            "message": "Video analysis started in background. Use /video/status endpoint to check progress.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/analysis/{video_path:path}")
async def get_video_analysis_results(video_path: str):
    """
    Get complete analysis results for a video.

    Returns:
    - Video metadata (duration, resolution, codec, etc.)
    - Extracted keyframes with timestamps
    - Detected scenes with boundaries
    - OCR text detections with confidence scores
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer

        # Validate video path
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        analysis = video_analyzer.get_video_analysis(video_path)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])

        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/search")
async def search_video_content(request: VideoSearchRequest):
    """
    Search video content using text queries.

    Searches through:
    - OCR detected text in video frames
    - Video file names and metadata
    - Scene descriptions (if available)

    Returns matching videos with timestamps where text was found.
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer

        results = video_analyzer.search_video_content(
            query=request.query,
            limit=request.limit,
        )

        # Add pagination info
        total_results = len(results)
        paginated_results = results[request.offset : request.offset + request.limit]

        return {
            "query": request.query,
            "total_results": total_results,
            "results": paginated_results,
            "pagination": {
                "limit": request.limit,
                "offset": request.offset,
                "has_more": request.offset + request.limit < total_results,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/keyframes/{video_path:path}")
async def get_video_keyframes(video_path: str, scene_id: Optional[int] = None):
    """
    Get keyframes for a specific video, optionally filtered by scene.

    Args:
        video_path: Path to the video file
        scene_id: Optional scene ID to filter keyframes

    Returns:
        List of keyframes with timestamps and file paths
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer

        analysis = video_analyzer.get_video_analysis(video_path)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])

        keyframes = analysis.get("keyframes", [])

        # Filter by scene if specified
        if scene_id is not None:
            keyframes = [kf for kf in keyframes if kf.get("scene_id") == scene_id]

        return {
            "video_path": video_path,
            "scene_id": scene_id,
            "keyframes": keyframes,
            "count": len(keyframes),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/scenes/{video_path:path}")
async def get_video_scenes(video_path: str):
    """
    Get scene detection results for a video.

    Returns:
        List of detected scenes with start/end timestamps and durations
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer

        analysis = video_analyzer.get_video_analysis(video_path)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])

        scenes = analysis.get("scenes", [])

        return {
            "video_path": video_path,
            "scenes": scenes,
            "count": len(scenes),
            "total_duration": analysis.get("metadata", {}).get("duration", 0),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/ocr/{video_path:path}")
async def get_video_ocr_results(video_path: str, min_confidence: float = 0.5):
    """
    Get OCR text detection results for a video.

    Args:
        video_path: Path to the video file
        min_confidence: Minimum confidence threshold for text detections

    Returns:
        List of text detections with timestamps and confidence scores
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer

        analysis = video_analyzer.get_video_analysis(video_path)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])

        ocr_results = analysis.get("ocr_results", [])

        # Filter by confidence threshold
        filtered_results = [
            result for result in ocr_results if result.get("confidence", 0) >= min_confidence
        ]

        return {
            "video_path": video_path,
            "min_confidence": min_confidence,
            "ocr_results": filtered_results,
            "count": len(filtered_results),
            "total_detections": len(ocr_results),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/stats")
async def get_video_analysis_stats():
    """
    Get statistics about video analysis processing.

    Returns:
        - Total videos processed
        - Total keyframes extracted
        - Total scenes detected
        - Total OCR detections
        - Processing time statistics
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer

        stats = video_analyzer.get_video_statistics()
        return {"stats": stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/thumbnail/{video_path:path}")
async def get_video_thumbnail(
    request: Request,
    video_path: str,
    timestamp: Optional[float] = None,
    size: int = 300,
):
    """
    Get a thumbnail image from a video at a specific timestamp.

    Args:
        video_path: Path to the video file
        timestamp: Timestamp in seconds (defaults to first keyframe)
        size: Thumbnail size in pixels

    Returns:
        Thumbnail image as JPEG
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer
        cors_origins = main_module.cors_origins

        analysis = video_analyzer.get_video_analysis(video_path)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])

        keyframes = analysis.get("keyframes", [])

        if not keyframes:
            raise HTTPException(status_code=404, detail="No keyframes available for video")

        # Find keyframe closest to requested timestamp
        if timestamp is not None:
            closest_keyframe = min(keyframes, key=lambda kf: abs(kf["timestamp"] - timestamp))
        else:
            closest_keyframe = keyframes[0]  # Use first keyframe

        frame_path = closest_keyframe["frame_path"]

        if not os.path.exists(frame_path):
            raise HTTPException(status_code=404, detail="Keyframe image not found")

        # Resize image if needed
        if size != 300:  # Default size
            from PIL import Image
            with Image.open(frame_path) as img:
                img.thumbnail((size, size), Image.Resampling.LANCZOS)

                # Save resized thumbnail to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                    img.save(temp_file.name, "JPEG", quality=85)
                    frame_path = temp_file.name

        # Prepare headers with cache control + CORS
        frame_headers = {
            "Cache-Control": "public, max-age=3600",
            "X-Video-Timestamp": str(closest_keyframe["timestamp"]),
        }

        # Add explicit CORS headers for cross-origin image requests
        origin = request.headers.get("origin")
        if origin and origin in cors_origins:
            frame_headers["Access-Control-Allow-Origin"] = origin
            frame_headers["Access-Control-Allow-Credentials"] = "true"

        return FileResponse(
            frame_path,
            media_type="image/jpeg",
            headers=frame_headers,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/video/analysis/{video_path:path}")
async def delete_video_analysis(video_path: str):
    """
    Delete analysis data for a specific video.

    This removes:
    - Video metadata
    - Keyframes and cached images
    - Scene detection results
    - OCR text detections
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer

        # Check if video analysis exists
        analysis = video_analyzer.get_video_analysis(video_path)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail="Video analysis not found")

        # Delete cached keyframe images
        keyframes = analysis.get("keyframes", [])
        deleted_files = 0

        for keyframe in keyframes:
            frame_path = keyframe.get("frame_path")
            if frame_path and os.path.exists(frame_path):
                try:
                    os.remove(frame_path)
                    deleted_files += 1
                except OSError:
                    pass  # Continue even if file deletion fails

        # Delete database records
        conn = sqlite3.connect(video_analyzer.db_path)
        try:
            conn.execute("DELETE FROM video_metadata WHERE video_path = ?", (video_path,))
            conn.execute("DELETE FROM video_keyframes WHERE video_path = ?", (video_path,))
            conn.execute("DELETE FROM video_scenes WHERE video_path = ?", (video_path,))
            conn.execute("DELETE FROM video_ocr WHERE video_path = ?", (video_path,))
            conn.commit()
        finally:
            conn.close()

        return {
            "success": True,
            "video_path": video_path,
            "deleted_files": deleted_files,
            "message": "Video analysis data deleted successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/batch-analyze")
async def batch_analyze_videos(background_tasks: BackgroundTasks, video_paths: List[str] = Body(...)):
    """
    Analyze multiple videos in batch.

    Starts analysis for multiple videos in the background.
    Use /video/batch-status to monitor progress.
    """
    try:
        from server import main as main_module
        video_analyzer = main_module.video_analyzer
        ps_logger = main_module.ps_logger

        if len(video_paths) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 videos per batch")

        # Validate all video paths
        invalid_paths = []
        for video_path in video_paths:
            if not os.path.exists(video_path):
                invalid_paths.append(video_path)

        if invalid_paths:
            raise HTTPException(
                status_code=400,
                detail=f"Video files not found: {', '.join(invalid_paths[:5])}",
            )

        # Start batch analysis
        def run_batch_analysis():
            results = []
            for video_path in video_paths:
                try:
                    result = video_analyzer.analyze_video(video_path, force_reprocess=False)
                    results.append({"video_path": video_path, "status": result.get("status")})
                    ps_logger.info(f"Batch analysis completed for {video_path}")
                except Exception as e:
                    results.append({"video_path": video_path, "status": "failed", "error": str(e)})
                    ps_logger.error(f"Batch analysis failed for {video_path}: {str(e)}")

            ps_logger.info(f"Batch analysis completed for {len(video_paths)} videos")

        background_tasks.add_task(run_batch_analysis)

        return {
            "status": "started",
            "video_count": len(video_paths),
            "message": "Batch video analysis started in background",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

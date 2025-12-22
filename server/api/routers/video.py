import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse

from server.config import settings
from server.utils.files import validate_file_path
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/video")
async def get_video(request: Request, path: str, state: AppState = Depends(get_state)):
    """
    Serve a video file directly.
    """

    # Security check with enhanced validation
    if settings.MEDIA_DIR.exists():
        allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
    else:
        allowed_paths = [settings.BASE_DIR.resolve()]

    # Validate the video file path is safe
    if not validate_file_path(path, allowed_paths):
        client_ip = request.client.host if request.client else "unknown"
        state.ps_logger.warning(f"Video access denied - IP: {client_ip}, Path: {path}")
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate video-specific file extensions
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp", ".flv"}
    if Path(path).suffix.lower() not in video_extensions:
        raise HTTPException(status_code=403, detail="Video file type not allowed")

    if os.path.exists(path):
        # Get mime type
        ext = Path(path).suffix.lower()
        mime_types = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
            ".m4v": "video/x-m4v",
        }
        media_type = mime_types.get(ext, "video/mp4")

        # Add security headers + CORS headers for video serving
        video_headers = {
            "X-Content-Type-Options": "nosniff",
            "Accept-Ranges": "bytes",
        }

        # Add explicit CORS headers for cross-origin video requests
        origin = request.headers.get("origin")
        if origin and origin in state.cors_origins:
            video_headers["Access-Control-Allow-Origin"] = origin
            video_headers["Access-Control-Allow-Credentials"] = "true"

        return FileResponse(
            path,
            media_type=media_type,
            headers=video_headers,
        )

    raise HTTPException(status_code=404, detail="Video not found")

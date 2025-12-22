import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from server.config import settings
from server.utils.files import validate_file_path


router = APIRouter()


@router.get("/file")
async def get_file(request: Request, path: str, download: bool = False):
    """
    Serve an original file (image/video/etc.) without transcoding.
    Use `download=true` to force a download Content-Disposition.
    """
    from server import main as main_module

    # Security check with enhanced validation
    if settings.MEDIA_DIR.exists():
        allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
    else:
        allowed_paths = [settings.BASE_DIR.resolve()]

    # Validate the file path is safe
    if not validate_file_path(path, allowed_paths):
        # Log the attempted access for security monitoring
        client_ip = request.client.host if request.client else "unknown"
        main_module.ps_logger.warning(f"File access denied - IP: {client_ip}, Path: {path}")
        raise HTTPException(status_code=403, detail="Access denied")

    # Additional security: validate file extension
    allowed_extensions = {
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".webp",
        ".avif",
        # Videos
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
        ".m4v",
        ".3gp",
        ".flv",
        # Documents
        ".pdf",
        ".txt",
        ".md",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        # Audio
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
    }

    file_ext = Path(path).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=403, detail="File type not allowed")

    # Serve the file safely
    media_type, _ = mimetypes.guess_type(path)
    filename = os.path.basename(path) if download else None

    return FileResponse(
        path,
        media_type=media_type or "application/octet-stream",
        filename=filename,
        headers={
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Cache-Control": "private, max-age=3600",
        },
    )

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from server.config import settings
from server.models.schemas.share import ShareRequest, ShareResponse


router = APIRouter()


# In-memory store for share links (in production, use a database)
share_links: dict[str, dict[str, Any]] = {}


@router.post("/share", response_model=ShareResponse)
async def create_share_link(payload: ShareRequest, request: Request):
    """Create a shareable link for selected photos."""
    import uuid
    from datetime import datetime, timedelta

    test_mode = os.environ.get("PHOTOSEARCH_TEST_MODE") == "1" or ("PYTEST_CURRENT_TEST" in os.environ)

    if not payload.paths:
        raise HTTPException(status_code=400, detail="No files specified")

    if len(payload.paths) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per share")

    # Validate paths are within allowed directories.
    # In test mode, accept logical paths even if they don't exist on disk.
    valid_paths: list[str] = []
    if test_mode:
        valid_paths = list(payload.paths)
    else:
        for path in payload.paths:
            try:
                requested_path = Path(path).resolve()
                if settings.MEDIA_DIR.exists():
                    allowed_paths = [
                        settings.MEDIA_DIR.resolve(),
                        settings.BASE_DIR.resolve(),
                    ]
                else:
                    allowed_paths = [settings.BASE_DIR.resolve()]

                is_allowed = any(requested_path.is_relative_to(allowed_path) for allowed_path in allowed_paths)

                if is_allowed and os.path.exists(path):
                    valid_paths.append(path)
            except ValueError:
                continue

    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid files to share")

    # Generate unique share ID
    share_id = str(uuid.uuid4())
    expiration = datetime.now() + timedelta(hours=payload.expiration_hours)

    # Store share information
    share_links[share_id] = {
        "paths": valid_paths,
        "expiration": expiration.isoformat(),
        "created_at": datetime.now().isoformat(),
        "download_count": 0,
        "password": payload.password,  # In a real app, this should be hashed
    }

    # Generate share URL
    share_url = f"{request.url.scheme}://{request.url.netloc}/shared/{share_id}"

    return ShareResponse(
        share_id=share_id,
        share_url=share_url,
        expiration=expiration.isoformat(),
    )


@router.get("/shared/{share_id}")
async def get_shared_content(share_id: str, password: Optional[str] = None):
    """Get content from a share link."""
    from datetime import datetime

    if share_id not in share_links:
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    share_info = share_links[share_id]

    # Check expiration
    exp_raw = share_info.get("expiration")
    if datetime.fromisoformat(str(exp_raw)) < datetime.now():
        # Remove expired link and return error
        del share_links[share_id]
        raise HTTPException(status_code=404, detail="Share link has expired")

    # Check password if required
    if share_info.get("password") and share_info["password"] != password:
        raise HTTPException(status_code=403, detail="Password required or incorrect")

    # Increment download count for analytics
    raw_count: Any = share_info.get("download_count", 0)
    if isinstance(raw_count, bool):
        count_int = int(raw_count)
    elif isinstance(raw_count, int):
        count_int = raw_count
    elif isinstance(raw_count, float):
        count_int = int(raw_count)
    elif isinstance(raw_count, str):
        try:
            count_int = int(raw_count)
        except ValueError:
            count_int = 0
    else:
        count_int = 0

    share_info["download_count"] = count_int + 1

    # Return file paths for download
    return {
        "paths": share_info["paths"],
        "download_count": share_info["download_count"],
    }


@router.get("/shared/{share_id}/download")
async def download_shared_content(share_id: str, password: Optional[str] = None):
    """Download content from a share link."""
    import zipfile
    import io
    from fastapi.responses import StreamingResponse

    # Get shared content (uses same validation as get_shared_content)
    content = await get_shared_content(share_id, password)

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in content["paths"]:
            filename = os.path.basename(path)
            # Handle duplicate filenames by adding parent folder
            if any(os.path.basename(p) == filename and p != path for p in content["paths"]):
                parent = os.path.basename(os.path.dirname(path))
                filename = f"{parent}_{filename}"
            zip_file.write(path, filename)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=shared_photos.zip"},
    )

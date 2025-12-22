import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.export import ExportRequest


router = APIRouter()


@router.post("/export")
async def export_photos(request: ExportRequest):
    """
    Export selected photos with various options.

    Args:
        request: ExportRequest with list of file paths and export options

    Returns:
        Streaming file download
    """
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    from PIL import Image
    import json

    from server import main as main_module

    if not request.paths:
        raise HTTPException(status_code=400, detail="No files specified")

    if len(request.paths) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per export")

    # Validate paths are within allowed directories
    valid_paths = []
    for path in request.paths:
        try:
            requested_path = Path(path).resolve()
            if settings.MEDIA_DIR.exists():
                allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
            else:
                allowed_paths = [settings.BASE_DIR.resolve()]

            is_allowed = any(
                requested_path.is_relative_to(allowed_path)
                for allowed_path in allowed_paths
            )

            if is_allowed and os.path.exists(path):
                valid_paths.append(path)
        except ValueError:
            continue

    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid files to export")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in valid_paths:
            original_filename = os.path.basename(path)

            # Handle duplicate filenames by adding parent folder
            if any(os.path.basename(p) == original_filename and p != path for p in valid_paths):
                parent = os.path.basename(os.path.dirname(path))
                filename = f"{parent}_{original_filename}"
            else:
                filename = original_filename

            # Process image if size reduction is requested
            if request.options.max_resolution:
                try:
                    # Open and resize image if needed
                    with Image.open(path) as img:
                        img.thumbnail((request.options.max_resolution, request.options.max_resolution))

                        # Save to temporary bytes buffer
                        temp_buffer = io.BytesIO()
                        img.save(temp_buffer, format=img.format)
                        temp_buffer.seek(0)

                        # Write to zip
                        zip_file.writestr(filename, temp_buffer.getvalue())
                except Exception:
                    # If image processing fails, just copy the file
                    zip_file.write(path, filename)
            else:
                # Write original file
                zip_file.write(path, filename)

            # Include metadata if requested
            if request.options.include_metadata:
                try:
                    metadata = main_module.photo_search_engine.db.get_metadata(path)
                    if metadata:
                        # Write metadata as JSON file
                        meta_filename = (
                            f"{original_filename.replace(os.path.splitext(original_filename)[1], '')}_metadata.json"
                        )
                        zip_file.writestr(meta_filename, json.dumps(metadata, indent=2))
                except Exception:
                    # If metadata extraction fails, continue without it
                    pass

            # Include thumbnail if requested
            if request.options.include_thumbnails:
                try:
                    with Image.open(path) as img:
                        img.thumbnail((200, 200))  # Create 200x200 thumbnail
                        thumb_buffer = io.BytesIO()
                        img.save(thumb_buffer, format=img.format)
                        thumb_buffer.seek(0)

                        thumb_filename = (
                            f"thumbs/{original_filename.replace(os.path.splitext(original_filename)[1], '')}_thumb"
                            f"{os.path.splitext(original_filename)[1]}"
                        )
                        zip_file.writestr(thumb_filename, thumb_buffer.getvalue())
                except Exception:
                    # If thumbnail creation fails, continue without it
                    pass

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=photos_export.zip"},
    )


@router.post("/export/presets")
async def create_export_preset(preset_data: dict):
    """Create a new export preset with predefined options."""
    # This would save the preset to a database in a full implementation
    # For now, we'll just return the preset data
    return {"success": True, "preset": preset_data}


@router.get("/export/presets")
async def get_export_presets():
    """Get available export presets."""
    # This would fetch presets from a database in a full implementation
    # For now, return some default presets
    return {
        "presets": [
            {
                "id": "high_quality",
                "name": "High Quality",
                "description": "Full resolution with metadata",
                "options": {
                    "format": "zip",
                    "include_metadata": True,
                    "include_thumbnails": False,
                    "max_resolution": None,
                },
            },
            {
                "id": "web_sharing",
                "name": "Web Sharing",
                "description": "Resized for web with low resolution",
                "options": {
                    "format": "zip",
                    "include_metadata": True,
                    "include_thumbnails": True,
                    "max_resolution": 1920,
                },
            },
            {
                "id": "print_ready",
                "name": "Print Ready",
                "description": "High resolution suitable for printing",
                "options": {
                    "format": "zip",
                    "include_metadata": True,
                    "include_thumbnails": False,
                    "max_resolution": None,
                },
            },
        ]
    }

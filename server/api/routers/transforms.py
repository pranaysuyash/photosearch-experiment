import shutil
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException
from PIL import Image


router = APIRouter()


@router.post("/photos/rotate")
async def rotate_photo(path: str = Body(...), degrees: int = Body(...), backup: bool = Body(True)):
    """
    Rotate a photo by specified degrees (90, 180, 270, or -90).
    Creates a backup by default before modifying the original.
    """
    if degrees not in [90, 180, 270, -90]:
        raise HTTPException(status_code=400, detail="Degrees must be 90, 180, 270, or -90")

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        # Create backup if requested
        if backup:
            backup_path = file_path.parent / f"{file_path.stem}_backup{file_path.suffix}"
            shutil.copy2(file_path, backup_path)

        # Open image
        img = Image.open(file_path)

        # Rotate (negative degrees for clockwise rotation in PIL)
        # PIL's rotate is counter-clockwise, so we negate for intuitive clockwise rotation
        if degrees == 90:
            rotated = img.transpose(Image.Transpose.ROTATE_270)  # 90° CW
        elif degrees == -90 or degrees == 270:
            rotated = img.transpose(Image.Transpose.ROTATE_90)  # 90° CCW
        elif degrees == 180:
            rotated = img.transpose(Image.Transpose.ROTATE_180)
        else:
            rotated = img.rotate(-degrees, expand=True)

        # Save with original format and quality
        save_kwargs = {}
        if img.format == "JPEG":
            save_kwargs["quality"] = 95
            save_kwargs["optimize"] = True

        rotated.save(file_path, format=img.format, **save_kwargs)
        img.close()
        rotated.close()

        return {
            "ok": True,
            "path": str(file_path),
            "operation": f"rotated_{degrees}deg",
            "backup_created": backup,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rotation failed: {str(e)}")


@router.post("/photos/flip")
async def flip_photo(path: str = Body(...), direction: str = Body(...), backup: bool = Body(True)):
    """
    Flip a photo horizontally or vertically.
    Creates a backup by default before modifying the original.
    """
    if direction not in ["horizontal", "vertical"]:
        raise HTTPException(status_code=400, detail="Direction must be 'horizontal' or 'vertical'")

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        # Create backup if requested
        if backup:
            backup_path = file_path.parent / f"{file_path.stem}_backup{file_path.suffix}"
            shutil.copy2(file_path, backup_path)

        # Open image
        img = Image.open(file_path)

        # Flip
        if direction == "horizontal":
            flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:  # vertical
            flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        # Save with original format and quality
        save_kwargs = {}
        if img.format == "JPEG":
            save_kwargs["quality"] = 95
            save_kwargs["optimize"] = True

        flipped.save(file_path, format=img.format, **save_kwargs)
        img.close()
        flipped.close()

        return {
            "ok": True,
            "path": str(file_path),
            "operation": f"flipped_{direction}",
            "backup_created": backup,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flip failed: {str(e)}")

from typing import Dict, Optional

from pydantic import BaseModel


class EditPayload(BaseModel):
    edit_data: dict


class EditData(BaseModel):
    brightness: float
    contrast: float
    saturation: float
    rotation: int
    flipH: bool
    flipV: bool
    crop: Optional[Dict[str, float]] = None  # {x, y, width, height}

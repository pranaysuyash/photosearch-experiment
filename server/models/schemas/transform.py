from pydantic import BaseModel


class TransformRequest(BaseModel):
    """Request for image transformation operations."""

    backup: bool = True  # Create backup before transformation

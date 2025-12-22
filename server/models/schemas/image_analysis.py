from pydantic import BaseModel


class ImageAnalysisRequest(BaseModel):
    path: str

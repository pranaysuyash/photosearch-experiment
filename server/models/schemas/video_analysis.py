from pydantic import BaseModel


class VideoAnalysisRequest(BaseModel):
    video_path: str
    force_reprocess: bool = False


class VideoSearchRequest(BaseModel):
    query: str
    limit: int = 50
    offset: int = 0

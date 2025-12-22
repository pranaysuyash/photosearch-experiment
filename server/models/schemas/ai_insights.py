from typing import Any, Dict, Optional

from pydantic import BaseModel


class AIInsightCreateRequest(BaseModel):
    photo_path: str
    insight_type: str  # 'best_shot', 'tag_suggestion', 'pattern', 'organization'
    insight_data: Dict[str, Any]
    confidence: float = 0.8


class AIInsightUpdateRequest(BaseModel):
    is_applied: Optional[bool] = None

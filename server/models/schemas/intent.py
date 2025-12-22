from typing import Any, Dict, Optional

from pydantic import BaseModel


class IntentSearchParams(BaseModel):
    query: str
    intent_context: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 50
    offset: int = 0

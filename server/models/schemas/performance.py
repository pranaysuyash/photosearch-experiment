from typing import Dict, Optional

from pydantic import BaseModel


class CodeSplittingConfigRequest(BaseModel):
    chunk_name: str
    config: Dict


class PerformanceRecordRequest(BaseModel):
    component_name: str
    chunk_name: str
    load_time_ms: float
    size_kb: float
    timestamp: Optional[str] = None

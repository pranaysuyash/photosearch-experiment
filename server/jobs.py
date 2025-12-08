from typing import Dict, Optional, Literal
from pydantic import BaseModel
import uuid
import time

JobStatus = Literal["pending", "processing", "completed", "failed"]

class Job(BaseModel):
    id: str
    type: str # 'scan', 'index', etc.
    status: JobStatus
    progress: int = 0
    message: Optional[str] = None
    created_at: float
    updated_at: float
    result: Optional[dict] = None

class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create_job(self, type: str) -> str:
        job_id = str(uuid.uuid4())
        now = time.time()
        self._jobs[job_id] = Job(
            id=job_id,
            type=type,
            status="pending",
            created_at=now,
            updated_at=now
        )
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, status: Optional[JobStatus] = None, progress: Optional[int] = None, message: Optional[str] = None, result: Optional[dict] = None):
        job = self._jobs.get(job_id)
        if not job:
            return
        
        if status:
            job.status = status
        if progress is not None:
            job.progress = progress
        if message:
            job.message = message
        if result:
            job.result = result
        
        job.updated_at = time.time()
        self._jobs[job_id] = job

# Global instance
job_store = JobStore()

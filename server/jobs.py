from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel
import uuid
import time
import os
import sys

# Add parent directory to path to import our persistent job store
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.persistent_job_store import PersistentJobStore

    USE_PERSISTENT_STORE = True
except ImportError:
    USE_PERSISTENT_STORE = False
    print("Warning: Persistent job store not available, falling back to memory store")

JobStatus = Literal["pending", "processing", "completed", "failed", "cancelled", "paused"]


class Job(BaseModel):
    id: str
    type: str  # 'scan', 'index', etc.
    status: JobStatus
    progress: int = 0
    message: Optional[str] = None
    created_at: float
    updated_at: float
    result: Optional[dict] = None

    def __getitem__(self, key: str):
        """Allow dict-like access (job['status']) for backward compatibility with tests."""
        return getattr(self, key)


class EnhancedJobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self.persistent_store = None

        if USE_PERSISTENT_STORE:
            self.persistent_store = PersistentJobStore()
            print("Using persistent job store")
        else:
            print("Using in-memory job store (fallback)")

    def create_job(self, type: str, payload: Optional[Dict[str, Any]] = None, priority: str = "medium") -> str:
        """Create a new job with optional payload and priority"""
        if USE_PERSISTENT_STORE and self.persistent_store:
            job_id = self.persistent_store.create_job(job_type=type, payload=payload or {}, priority=priority)
            # Also store in memory for quick access
            now = time.time()
            self._jobs[job_id] = Job(id=job_id, type=type, status="pending", created_at=now, updated_at=now)
            return job_id
        else:
            # Fallback to original implementation
            job_id = str(uuid.uuid4())
            now = time.time()
            self._jobs[job_id] = Job(id=job_id, type=type, status="pending", created_at=now, updated_at=now)
            return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job from persistent store if available, otherwise memory"""
        if USE_PERSISTENT_STORE and self.persistent_store:
            persistent_job = self.persistent_store.get_job(job_id)
            if persistent_job:
                # Update memory cache
                self._jobs[job_id] = Job(
                    id=persistent_job["id"],
                    type=persistent_job["job_type"],
                    status=persistent_job["status"],
                    progress=persistent_job["progress"],
                    message=persistent_job["message"],
                    created_at=persistent_job["created_at"],
                    updated_at=persistent_job["updated_at"],
                    result=persistent_job["result"],
                )
                return self._jobs[job_id]

        return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[dict] = None,
    ):
        """Update job in both persistent store and memory"""
        job = self._jobs.get(job_id)
        if not job:
            return

        # Update in memory
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

        # Update in persistent store if available
        if USE_PERSISTENT_STORE and self.persistent_store:
            self.persistent_store.update_job(
                job_id=job_id, status=status, progress=progress, message=message, result=result
            )

    def get_job_statistics(self) -> dict:
        """Get statistics about job execution"""
        if USE_PERSISTENT_STORE and self.persistent_store:
            return self.persistent_store.get_job_statistics()

        # Fallback statistics for memory store
        status_counts: Dict[str, int] = {}
        for job in self._jobs.values():
            status = job.status
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_jobs": len(self._jobs),
            "status_distribution": status_counts,
            "recent_jobs": list(self._jobs.values())[-10:],
        }

    def cleanup_completed_jobs(self, older_than_days: int = 30) -> int:
        """Clean up completed jobs"""
        if USE_PERSISTENT_STORE and self.persistent_store:
            return self.persistent_store.cleanup_completed_jobs(older_than_days)

        # Memory store cleanup
        now = time.time()
        cutoff = now - (older_than_days * 24 * 60 * 60)

        completed_jobs = []
        for job_id, job in self._jobs.items():
            if job.status in ["completed", "failed", "cancelled"]:
                # Check if we have updated_at timestamp
                if hasattr(job, "completed_at") and job.completed_at:
                    job_time = job.completed_at
                else:
                    job_time = job.updated_at

                if job_time < cutoff:
                    completed_jobs.append(job_id)

        for job_id in completed_jobs:
            del self._jobs[job_id]

        return len(completed_jobs)


# Global instance - now uses enhanced store
job_store = EnhancedJobStore()

"""
Enhanced Job Queue and Executor System

This module provides a robust job queue system with:
1. Persistent job storage
2. Background job execution
3. Job prioritization
4. Retry mechanism
5. Progress tracking
6. Result caching

Features:
- SQLite-backed persistent job storage
- Thread-based background execution
- Job prioritization (high, medium, low)
- Automatic retry for failed jobs
- Progress tracking and status updates
- Result caching and retrieval

Usage:
    job_queue = JobQueue('job_queue.db')
    
    # Add a job
    job_id = job_queue.add_job(
        job_type='scan',
        payload={'path': '/photos', 'force': False},
        priority='high'
    )
    
    # Get job status
    status = job_queue.get_job_status(job_id)
    
    # Start processing queue
    job_queue.start_workers()
    
    # Stop processing
    job_queue.stop_workers()
"""

import sqlite3
import json
import threading
import queue
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

class JobStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class JobPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Job:
    def __init__(
        self,
        job_id: str,
        job_type: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.MEDIUM,
        max_retries: int = 3,
        timeout: int = 3600
    ):
        self.id = job_id
        self.type = job_type
        self.payload = payload
        self.priority = priority
        self.status = JobStatus.PENDING
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None
        self.max_retries = max_retries
        self.retry_count = 0
        self.timeout = timeout
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for storage."""
        return {
            'id': self.id,
            'type': self.type,
            'payload': json.dumps(self.payload),
            'priority': self.priority.value,
            'status': self.status.value,
            'progress': self.progress,
            'message': self.message,
            'result': json.dumps(self.result) if self.result else None,
            'error': self.error,
            'max_retries': self.max_retries,
            'retry_count': self.retry_count,
            'timeout': self.timeout,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access (job['status']) for tests and legacy code.

        Returns underlying enum values as strings for 'status' and 'priority'.
        """
        val = getattr(self, key)
        # Unwrap enums to their .value for JSON-like access
        try:
            from enum import Enum as _Enum
            if isinstance(val, _Enum):
                return val.value
        except Exception:
            pass
        return val
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary."""
        job = cls(
            job_id=data['id'],
            job_type=data['type'],
            payload=json.loads(data['payload']) if data['payload'] else {},
            priority=JobPriority(data['priority']),
            max_retries=data['max_retries'],
            timeout=data['timeout']
        )
        
        job.status = JobStatus(data['status'])
        job.progress = data['progress']
        job.message = data['message']
        job.result = json.loads(data['result']) if data['result'] else None
        job.error = data['error']
        job.retry_count = data['retry_count']
        job.created_at = data['created_at']
        job.updated_at = data['updated_at']
        job.started_at = data['started_at']
        job.completed_at = data['completed_at']
        
        return job

class JobQueue:
    """Persistent job queue with background processing."""
    
    def __init__(self, db_path: str = "job_queue.db", num_workers: int = 2):
        """
        Initialize job queue.
        
        Args:
            db_path: Path to SQLite database
            num_workers: Number of background worker threads
        """
        self.db_path = db_path
        self.num_workers = num_workers
        self.conn: Optional[sqlite3.Connection] = None
        self.workers: List[threading.Thread] = []
        self.running = False
        self.job_handlers: Dict[str, Callable[..., Any]] = {}
        self._initialize_database()

    def _get_conn(self) -> sqlite3.Connection:
        """Return a non-Optional SQLite connection, initializing if needed."""
        if self.conn is None:
            self._initialize_database()
        if self.conn is None:
            raise RuntimeError("JobQueue database connection could not be initialized")
        return self.conn
    
    def _initialize_database(self):
        """Initialize database and create tables."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Create jobs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                payload TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                message TEXT,
                result TEXT,
                error TEXT,
                max_retries INTEGER DEFAULT 3,
                retry_count INTEGER DEFAULT 0,
                timeout INTEGER DEFAULT 3600,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Create job index for faster lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type)")

        conn.commit()
        self.conn = conn
    
    def register_handler(self, job_type: str, handler: Callable[..., Any]):
        """
        Register a handler function for a specific job type.
        
        Args:
            job_type: Type of job
            handler: Function that takes (job, update_callback) and returns result
        """
        self.job_handlers[job_type] = handler
    
    def add_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: str = "medium",
        max_retries: int = 3,
        timeout: int = 3600
    ) -> str:
        """
        Add a new job to the queue.
        
        Args:
            job_type: Type of job
            payload: Job payload/data
            priority: Job priority (high, medium, low)
            max_retries: Maximum number of retry attempts
            timeout: Job timeout in seconds
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        try:
            # Try enum by name first (e.g., 'HIGH')
            priority_enum = JobPriority[priority.upper()]
        except Exception:
            try:
                # Try enum by value (e.g., 'high')
                priority_enum = JobPriority(priority.lower())
            except Exception:
                priority_enum = JobPriority.MEDIUM
        
        job = Job(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            priority=priority_enum,
            max_retries=max_retries,
            timeout=timeout
        )
        
        # Store job in database
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs 
            (id, type, payload, priority, status, max_retries, timeout)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            job.id,
            job.type,
            json.dumps(job.payload),
            job.priority.value,
            job.status.value,
            job.max_retries,
            job.timeout
        ))
        
        conn.commit()
        
        # If workers are running, the job will be picked up automatically
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job details by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job object or None if not found
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        
        if row:
            return Job.from_dict(dict(row))
        
        return None
    
    def get_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """
        Get multiple jobs with filtering.
        
        Args:
            status: Filter by status
            job_type: Filter by job type
            priority: Filter by priority
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of Job objects
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query = "SELECT * FROM jobs"
        conditions: List[str] = []
        params: List[Any] = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if job_type:
            conditions.append("type = ?")
            params.append(job_type)
        
        if priority:
            conditions.append("priority = ?")
            params.append(priority)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += (
            " ORDER BY "
            "CASE priority "
            "WHEN 'high' THEN 1 "
            "WHEN 'medium' THEN 2 "
            "WHEN 'low' THEN 3 "
            "ELSE 4 "
            "END, "
            "created_at ASC"
        )
        
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [Job.from_dict(dict(row)) for row in rows]
    
    def update_job_status(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update job status and progress.
        
        Args:
            job_id: Job ID
            status: New status
            progress: Progress percentage (0-100)
            message: Status message
            result: Job result data
            error: Error message
            
        Returns:
            True if updated, False if job not found
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get current job to preserve existing values
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        
        if not row:
            return False
        
        job_data = dict(row)
        
        # Update fields
        if status:
            job_data['status'] = status
            if status == JobStatus.PROCESSING.value:
                job_data['started_at'] = datetime.now().isoformat()
            elif status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
                job_data['completed_at'] = datetime.now().isoformat()
        
        if progress is not None:
            job_data['progress'] = progress
        
        if message:
            job_data['message'] = message
        
        if result:
            job_data['result'] = json.dumps(result)
        
        if error:
            job_data['error'] = error
        
        job_data['updated_at'] = datetime.now().isoformat()
        
        # Update in database
        cursor.execute("""
            UPDATE jobs SET 
                status = ?,
                progress = ?,
                message = ?,
                result = ?,
                error = ?,
                updated_at = ?,
                started_at = ?,
                completed_at = ?
            WHERE id = ?
        """, (
            job_data['status'],
            job_data['progress'],
            job_data['message'],
            job_data['result'],
            job_data['error'],
            job_data['updated_at'],
            job_data['started_at'],
            job_data['completed_at'],
            job_id
        ))
        
        conn.commit()
        return True
    
    def _process_job(self, job: Job):
        """
        Process a single job.
        
        Args:
            job: Job to process
        """
        def update_callback(
            status: Optional[str] = None,
            progress: Optional[int] = None,
            message: Optional[str] = None,
            result: Optional[Dict[str, Any]] = None,
            error: Optional[str] = None
        ):
            """Callback to update job status."""
            self.update_job_status(job.id, status, progress, message, result, error)
        
        try:
            # Update status to processing
            update_callback(status=JobStatus.PROCESSING.value, progress=0, message="Starting job")
            
            # Get handler for this job type
            handler = self.job_handlers.get(job.type)
            if not handler:
                raise ValueError(f"No handler registered for job type: {job.type}")
            
            # Execute handler
            result = handler(job, update_callback)
            
            # Update status to completed
            update_callback(
                status=JobStatus.COMPLETED.value,
                progress=100,
                message="Job completed successfully",
                result=result
            )
            
        except Exception as e:
            # Handle job failure
            error_msg = str(e)
            
            # Check if we should retry
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                update_callback(
                    status=JobStatus.RETRYING.value,
                    message=f"Job failed, retrying ({job.retry_count}/{job.max_retries}): {error_msg}",
                    error=error_msg
                )
                
                # Re-add job to queue with delay
                time.sleep(2 ** job.retry_count)  # Exponential backoff
                self.update_job_status(job.id, status=JobStatus.PENDING.value)
            else:
                update_callback(
                    status=JobStatus.FAILED.value,
                    message=f"Job failed after {job.max_retries} attempts: {error_msg}",
                    error=error_msg
                )
    
    def _worker_thread(self):
        """Background worker thread that processes jobs."""
        while self.running:
            try:
                # Get next job to process
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM jobs 
                    WHERE status = 'pending' 
                    ORDER BY 
                        CASE priority 
                            WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2
                            WHEN 'low' THEN 3
                            ELSE 4
                        END,
                        created_at ASC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                
                if row:
                    job = Job.from_dict(dict(row))
                    
                    # Mark as processing
                    self.update_job_status(
                        job.id,
                        status=JobStatus.PROCESSING.value,
                        progress=0,
                        message="Job picked up by worker"
                    )
                    
                    # Process the job
                    self._process_job(job)
                else:
                    # No jobs available, wait a bit
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Worker error: {e}")
                time.sleep(5)
    
    def start_workers(self):
        """Start background worker threads."""
        if self.running:
            return
        
        self.running = True
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                name=f"JobWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        print(f"Started {self.num_workers} job workers")
    
    def stop_workers(self):
        """Stop background worker threads."""
        self.running = False
        
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers = []
        print("Stopped job workers")
    
    def get_queue_stats(self) -> Dict:
        """
        Get statistics about the job queue.
        
        Returns:
            Dictionary with queue statistics
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Count jobs by status
        cursor.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Count jobs by type
        cursor.execute("SELECT type, COUNT(*) as count FROM jobs GROUP BY type")
        type_counts = {row['type']: row['count'] for row in cursor.fetchall()}
        
        # Count jobs by priority
        cursor.execute("SELECT priority, COUNT(*) as count FROM jobs GROUP BY priority")
        priority_counts = {row['priority']: row['count'] for row in cursor.fetchall()}
        
        # Get recent jobs
        cursor.execute("""
            SELECT id, type, status, created_at 
            FROM jobs 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_jobs = []
        for row in cursor.fetchall():
            recent_jobs.append({
                'id': row['id'],
                'type': row['type'],
                'status': row['status'],
                'created_at': row['created_at']
            })
        
        # Get failed jobs
        cursor.execute("""
            SELECT id, type, error, updated_at 
            FROM jobs 
            WHERE status = 'failed' 
            ORDER BY updated_at DESC 
            LIMIT 5
        """)
        failed_jobs = []
        for row in cursor.fetchall():
            failed_jobs.append({
                'id': row['id'],
                'type': row['type'],
                'error': row['error'],
                'updated_at': row['updated_at']
            })
        
        return {
            'total_jobs': sum(status_counts.values()),
            'status_counts': status_counts,
            'type_counts': type_counts,
            'priority_counts': priority_counts,
            'recent_jobs': recent_jobs,
            'failed_jobs': failed_jobs,
            'workers_running': len(self.workers) if self.running else 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def clear_completed_jobs(self, older_than_days: int = 30) -> int:
        """
        Clear completed jobs older than specified days.
        
        Args:
            older_than_days: Clear jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        
        cursor.execute("""
            DELETE FROM jobs 
            WHERE status IN ('completed', 'failed') 
            AND completed_at < ?
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        return deleted_count
    
    def close(self):
        """Close database connection."""
        self.stop_workers()
        conn = self.conn
        if conn is not None:
            conn.close()
        self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """CLI interface for testing job queue."""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Job Queue System')
    parser.add_argument('--db', default='job_queue.db', help='Database path')
    parser.add_argument('--workers', type=int, default=2, help='Number of workers')
    parser.add_argument('--list', action='store_true', help='List all jobs')
    parser.add_argument('--stats', action='store_true', help='Show queue statistics')
    parser.add_argument('--test', action='store_true', help='Run test jobs')
    
    args = parser.parse_args()
    
    with JobQueue(args.db, args.workers) as job_queue:
        
        # Register a test handler
        def test_handler(job, update_callback):
            """Test job handler that simulates work."""
            update_callback(message="Starting test job")
            
            # Simulate work
            for i in range(1, 11):
                time.sleep(0.5)
                progress = i * 10
                update_callback(
                    progress=progress,
                    message=f"Processing step {i}/10"
                )
            
            # Return result
            result = {
                'message': 'Test job completed',
                'steps': 10,
                'data': job.payload
            }
            
            return result
        
        job_queue.register_handler('test', test_handler)
        
        if args.test:
            print("Adding test jobs...")
            
            # Add some test jobs
            for i in range(3):
                job_id = job_queue.add_job(
                    job_type='test',
                    payload={'test_id': i, 'data': f'test_data_{i}'},
                    priority=['high', 'medium', 'low'][i % 3]
                )
                print(f"Added job {job_id} with priority {['high', 'medium', 'low'][i % 3]}")
            
            # Start workers
            job_queue.start_workers()
            
            # Monitor jobs
            print("\nMonitoring jobs (Ctrl+C to stop)...")
            try:
                while True:
                    time.sleep(2)
                    stats = job_queue.get_queue_stats()
                    print(f"\rJobs: {stats['total_jobs']} | Pending: {stats['status_counts'].get('pending', 0)} | Processing: {stats['status_counts'].get('processing', 0)} | Completed: {stats['status_counts'].get('completed', 0)} | Failed: {stats['status_counts'].get('failed', 0)}", end="")
            except KeyboardInterrupt:
                print("\nStopping workers...")
                job_queue.stop_workers()
        
        elif args.list:
            jobs = job_queue.get_jobs()
            print(f"All Jobs ({len(jobs)}):")
            print("=" * 80)
            for job in jobs:
                print(f"ID: {job.id}")
                print(f"Type: {job.type}")
                print(f"Status: {job.status.value}")
                print(f"Priority: {job.priority.value}")
                print(f"Progress: {job.progress}%")
                print(f"Message: {job.message}")
                print(f"Created: {job.created_at}")
                print("-" * 60)
        
        elif args.stats:
            stats = job_queue.get_queue_stats()
            print("Job Queue Statistics:")
            print("=" * 60)
            print(f"Total Jobs: {stats['total_jobs']}")
            print(f"Workers Running: {stats['workers_running']}")
            
            print(f"\nStatus Counts:")
            for status, count in stats['status_counts'].items():
                print(f"  {status}: {count}")
            
            print(f"\nType Counts:")
            for job_type, count in stats['type_counts'].items():
                print(f"  {job_type}: {count}")
            
            print(f"\nPriority Counts:")
            for priority, count in stats['priority_counts'].items():
                print(f"  {priority}: {count}")
            
            print(f"\nRecent Jobs:")
            for job in stats['recent_jobs']:
                print(f"  {job['created_at']} - {job['type']} ({job['status']})")
        
        else:
            parser.print_help()


if __name__ == "main":
    main()
"""
Persistent Job Store

This module provides a persistent job store that extends the basic job store
with database-backed persistence, recovery, and advanced features.

Features:
- SQLite-backed persistent storage
- Job recovery after server restart
- Job history and analytics
- Job prioritization and scheduling
- Integration with existing job queue system

Usage:
    job_store = PersistentJobStore('jobs.db')
    
    # Create a job
    job_id = job_store.create_job(
        job_type='scan',
        payload={'path': '/photos'},
        priority='high'
    )
    
    # Get job status
    job = job_store.get_job(job_id)
    
    # Update job progress
    job_store.update_job(job_id, status='processing', progress=50)
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from enum import Enum

class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class JobPriority(Enum):
    """Job priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PersistentJobStore:
    """Persistent job store with database backend."""
    
    def __init__(self, db_path: str = "jobs.db"):
        """
        Initialize persistent job store.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and create tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create jobs table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                payload TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
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
                completed_at TIMESTAMP,
                user_id TEXT,
                context TEXT
            )
        """)
        
        # Create job history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS job_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                status TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        
        # Create job metrics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS job_metrics (
                job_id TEXT PRIMARY KEY,
                execution_time_ms INTEGER,
                memory_usage_kb INTEGER,
                cpu_usage_percent REAL,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        
        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_history_job ON job_history(job_id)")
        
        self.conn.commit()
    
    def create_job(
        self,
        job_type: str,
        payload: Dict,
        priority: str = "medium",
        max_retries: int = 3,
        timeout: int = 3600,
        user_id: str = "system",
        context: str = "general"
    ) -> str:
        """
        Create a new job.
        
        Args:
            job_type: Type of job
            payload: Job payload/data
            priority: Job priority
            max_retries: Maximum number of retry attempts
            timeout: Job timeout in seconds
            user_id: User ID associated with the job
            context: Context for the job
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        try:
            # Try by name first (e.g., 'HIGH')
            priority_enum = JobPriority[priority.upper()]
        except Exception:
            try:
                # Then by value (e.g., 'high')
                priority_enum = JobPriority(priority.lower())
            except Exception:
                priority_enum = JobPriority.MEDIUM
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO jobs 
            (id, job_type, payload, status, priority, max_retries, timeout, user_id, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            job_type,
            json.dumps(payload),
            JobStatus.PENDING.value,
            priority_enum.value,
            max_retries,
            timeout,
            user_id,
            context
        ))
        
        # Record creation in history
        cursor.execute("""
            INSERT INTO job_history 
            (job_id, status, message)
            VALUES (?, ?, ?)
        """, (job_id, JobStatus.PENDING.value, "Job created"))
        
        self.conn.commit()
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Dictionary with job data or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        
        row = cursor.fetchone()
        
        if row:
            job = dict(row)
            job['payload'] = json.loads(job['payload']) if job['payload'] else {}
            job['result'] = json.loads(job['result']) if job['result'] else None
            job['error'] = json.loads(job['error']) if job['error'] else None
            return job
        
        return None
    
    def get_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        priority: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get multiple jobs with filtering.
        
        Args:
            status: Filter by status
            job_type: Filter by job type
            priority: Filter by priority
            user_id: Filter by user ID
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of job dictionaries
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM jobs"
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if job_type:
            conditions.append("job_type = ?")
            params.append(job_type)
        
        if priority:
            conditions.append("priority = ?")
            params.append(priority)
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += """ ORDER BY 
            CASE priority 
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
                ELSE 5
            END,
            created_at ASC"""
        
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        jobs = []
        for row in cursor.fetchall():
            job = dict(row)
            job['payload'] = json.loads(job['payload']) if job['payload'] else {}
            job['result'] = json.loads(job['result']) if job['result'] else None
            job['error'] = json.loads(job['error']) if job['error'] else None
            jobs.append(job)
        
        return jobs
    
    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        retry_count: Optional[int] = None
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
            retry_count: Updated retry count
            
        Returns:
            True if updated, False if job not found
        """
        cursor = self.conn.cursor()
        
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
            elif status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
                job_data['completed_at'] = datetime.now().isoformat()
        
        if progress is not None:
            job_data['progress'] = progress
        
        if message:
            job_data['message'] = message
        
        if result:
            job_data['result'] = json.dumps(result)
        
        if error:
            job_data['error'] = error
        
        if retry_count is not None:
            job_data['retry_count'] = retry_count
        
        job_data['updated_at'] = datetime.now().isoformat()
        
        # Update in database
        cursor.execute("""
            UPDATE jobs SET 
                status = ?,
                progress = ?,
                message = ?,
                result = ?,
                error = ?,
                retry_count = ?,
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
            job_data['retry_count'],
            job_data['updated_at'],
            job_data['started_at'],
            job_data['completed_at'],
            job_id
        ))
        
        # Record status change in history
        if status:
            cursor.execute("""
                INSERT INTO job_history 
                (job_id, status, message)
                VALUES (?, ?, ?)
            """, (job_id, status, message or f"Status changed to {status}"))
        
        self.conn.commit()
        return True
    
    def record_job_metrics(
        self,
        job_id: str,
        execution_time_ms: int,
        memory_usage_kb: int = 0,
        cpu_usage_percent: float = 0.0
    ) -> bool:
        """
        Record job execution metrics.
        
        Args:
            job_id: Job ID
            execution_time_ms: Execution time in milliseconds
            memory_usage_kb: Memory usage in KB
            cpu_usage_percent: CPU usage percentage
            
        Returns:
            True if recorded, False if failed
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO job_metrics 
                (job_id, execution_time_ms, memory_usage_kb, cpu_usage_percent)
                VALUES (?, ?, ?, ?)
            """, (
                job_id,
                execution_time_ms,
                memory_usage_kb,
                cpu_usage_percent
            ))
            
            self.conn.commit()
            return True
            
        except Exception:
            return False
    
    def get_job_history(self, job_id: str, limit: int = 50) -> List[Dict]:
        """
        Get history for a specific job.
        
        Args:
            job_id: Job ID
            limit: Maximum number of history records
            
        Returns:
            List of history records
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM job_history 
            WHERE job_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (job_id, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append(dict(row))
        
        return history
    
    def get_job_metrics(self, job_id: str) -> Optional[Dict]:
        """
        Get metrics for a specific job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Dictionary with job metrics or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM job_metrics WHERE job_id = ?", (job_id,))
        
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        
        return None
    
    def cancel_job(self, job_id: str, reason: str = "User cancelled") -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID
            reason: Reason for cancellation
            
        Returns:
            True if cancelled, False if job not found
        """
        return self.update_job(
            job_id,
            status=JobStatus.CANCELLED.value,
            message=reason
        )
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if paused, False if job not found
        """
        return self.update_job(
            job_id,
            status=JobStatus.PAUSED.value,
            message="Job paused"
        )
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if resumed, False if job not found
        """
        return self.update_job(
            job_id,
            status=JobStatus.PENDING.value,
            message="Job resumed"
        )
    
    def retry_job(self, job_id: str) -> bool:
        """
        Retry a failed job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if retried, False if job not found
        """
        # Get current retry count
        job = self.get_job(job_id)
        if not job:
            return False
        
        retry_count = job['retry_count'] + 1
        
        if retry_count > job['max_retries']:
            return False
        
        return self.update_job(
            job_id,
            status=JobStatus.PENDING.value,
            retry_count=retry_count,
            message=f"Retrying job (attempt {retry_count}/{job['max_retries']})"
        )
    
    def get_job_statistics(self) -> Dict:
        """
        Get statistics about job execution.
        
        Returns:
            Dictionary with job statistics
        """
        cursor = self.conn.cursor()
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) as count FROM jobs")
        total_jobs = cursor.fetchone()['count']
        
        # Jobs by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM jobs
            GROUP BY status
        """)
        
        status_distribution = {}
        for row in cursor.fetchall():
            status_distribution[row['status']] = row['count']
        
        # Jobs by type
        cursor.execute("""
            SELECT job_type, COUNT(*) as count
            FROM jobs
            GROUP BY job_type
            ORDER BY count DESC
        """)
        
        type_distribution = {}
        for row in cursor.fetchall():
            type_distribution[row['job_type']] = row['count']
        
        # Jobs by priority
        cursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM jobs
            GROUP BY priority
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END
        """)
        
        priority_distribution = {}
        for row in cursor.fetchall():
            priority_distribution[row['priority']] = row['count']
        
        # Recent jobs
        cursor.execute("""
            SELECT id, job_type, status, created_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        recent_jobs = []
        for row in cursor.fetchall():
            recent_jobs.append({
                'id': row['id'],
                'type': row['job_type'],
                'status': row['status'],
                'created_at': row['created_at']
            })
        
        # Failed jobs
        cursor.execute("""
            SELECT id, job_type, error, updated_at
            FROM jobs
            WHERE status = 'failed'
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        
        failed_jobs = []
        for row in cursor.fetchall():
            failed_jobs.append({
                'id': row['id'],
                'type': row['job_type'],
                'error': row['error'],
                'updated_at': row['updated_at']
            })
        
        # Average execution time
        cursor.execute("""
            SELECT AVG(execution_time_ms) as avg_time
            FROM job_metrics
            WHERE execution_time_ms > 0
        """)
        
        avg_execution_row = cursor.fetchone()
        avg_execution_time = avg_execution_row['avg_time'] if avg_execution_row['avg_time'] else 0
        
        return {
            'total_jobs': total_jobs,
            'status_distribution': status_distribution,
            'type_distribution': type_distribution,
            'priority_distribution': priority_distribution,
            'recent_jobs': recent_jobs,
            'failed_jobs': failed_jobs,
            'average_execution_time_ms': round(avg_execution_time, 2),
            'last_updated': datetime.now().isoformat()
        }
    
    def cleanup_completed_jobs(self, older_than_days: int = 30) -> int:
        """
        Clean up completed jobs older than specified days.
        
        Args:
            older_than_days: Clear jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        cursor = self.conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        
        cursor.execute("""
            DELETE FROM jobs 
            WHERE status IN ('completed', 'failed', 'cancelled') 
            AND completed_at < ?
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        return deleted_count
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """CLI interface for testing persistent job store."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Persistent Job Store')
    parser.add_argument('--db', default='jobs.db', help='Database path')
    parser.add_argument('--create', nargs='+', help='Create test jobs')
    parser.add_argument('--list', action='store_true', help='List all jobs')
    parser.add_argument('--stats', action='store_true', help='Show job statistics')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup completed jobs')
    
    args = parser.parse_args()
    
    with PersistentJobStore(args.db) as job_store:
        
        if args.create:
            # Create different types of jobs
            jobs_created = []
            
            if 'scan' in args.create:
                job_id = job_store.create_job(
                    job_type='scan',
                    payload={'path': '/photos', 'force': False},
                    priority='high',
                    context='indexing'
                )
                jobs_created.append(('Scan', job_id))
            
            if 'index' in args.create:
                job_id = job_store.create_job(
                    job_type='index',
                    payload={'files': ['file1.jpg', 'file2.jpg']},
                    priority='medium',
                    context='search'
                )
                jobs_created.append(('Index', job_id))
            
            if 'export' in args.create:
                job_id = job_store.create_job(
                    job_type='export',
                    payload={'format': 'zip', 'quality': 'high'},
                    priority='low',
                    context='export'
                )
                jobs_created.append(('Export', job_id))
            
            print(f"Created {len(jobs_created)} jobs:")
            for job_type, job_id in jobs_created:
                print(f"  {job_type}: {job_id}")
        
        elif args.list:
            jobs = job_store.get_jobs()
            print(f"All Jobs ({len(jobs)}):")
            print("=" * 80)
            for job in jobs:
                print(f"ID: {job['id']}")
                print(f"Type: {job['job_type']}")
                print(f"Status: {job['status']}")
                print(f"Priority: {job['priority']}")
                print(f"Progress: {job['progress']}%")
                print(f"Message: {job['message'] or 'N/A'}")
                print(f"Created: {job['created_at']}")
                print("-" * 60)
        
        elif args.stats:
            stats = job_store.get_job_statistics()
            print("Job Store Statistics:")
            print("=" * 60)
            print(f"Total Jobs: {stats['total_jobs']}")
            
            print(f"\nJobs by Status:")
            for status, count in stats['status_distribution'].items():
                print(f"  {status}: {count}")
            
            print(f"\nJobs by Type:")
            for job_type, count in stats['type_distribution'].items():
                print(f"  {job_type}: {count}")
            
            print(f"\nJobs by Priority:")
            for priority, count in stats['priority_distribution'].items():
                print(f"  {priority}: {count}")
            
            print(f"\nRecent Jobs:")
            for job in stats['recent_jobs']:
                print(f"  {job['created_at']} - {job['type']} ({job['status']})")
            
            print(f"\nAverage Execution Time: {stats['average_execution_time_ms']}ms")
        
        elif args.cleanup:
            count = job_store.cleanup_completed_jobs()
            print(f"Cleaned up {count} completed jobs")
        
        else:
            # Create a sample job
            job_id = job_store.create_job(
                job_type='sample',
                payload={'test': True, 'data': 'sample'},
                priority='medium'
            )
            print(f"Created sample job with ID: {job_id}")
            
            # Get and display the job
            job = job_store.get_job(job_id)
            print(f"\nJob Details:")
            print(f"  Type: {job['job_type']}")
            print(f"  Status: {job['status']}")
            print(f"  Priority: {job['priority']}")
            print(f"  Payload: {job['payload']}")


if __name__ == "main":
    main()
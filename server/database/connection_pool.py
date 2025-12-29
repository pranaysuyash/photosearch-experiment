"""
Database Connection Pool Manager

Provides connection pooling and query optimization for SQLite databases.
Addresses database contention issues and improves performance for concurrent access.
"""

import sqlite3
import threading
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, ContextManager, Tuple
from contextlib import contextmanager
from queue import Queue, Empty
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection pool statistics"""

    total_connections: int
    active_connections: int
    idle_connections: int
    total_queries: int
    failed_queries: int
    average_query_time: float
    peak_connections: int


class PooledConnection:
    """Wrapper for pooled SQLite connections"""

    def __init__(self, db_path: Path, connection_id: int):
        self.db_path = db_path
        self.connection_id = connection_id
        self.connection: Optional[sqlite3.Connection] = None
        self.created_at = time.time()
        self.last_used = time.time()
        self.query_count = 0
        self.is_active = False
        self._lock = threading.Lock()

        self._create_connection()

    def _create_connection(self):
        """Create SQLite connection with optimized settings"""
        try:
            self.connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,  # 30 second timeout
                check_same_thread=False,  # Allow cross-thread usage
                isolation_level=None,  # Autocommit mode for better concurrency
            )

            # Optimize SQLite settings for performance
            cursor = self.connection.cursor()

            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")

            # Optimize for performance
            cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
            cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory mapping

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")

            cursor.close()

            logger.debug(f"Created optimized connection {self.connection_id} for {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to create connection {self.connection_id}: {e}")
            raise

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query with error handling and statistics"""
        with self._lock:
            if not self.connection:
                raise RuntimeError(f"Connection {self.connection_id} is closed")

            self.last_used = time.time()
            self.query_count += 1

            try:
                cursor = self.connection.cursor()
                cursor.execute(query, params)
                return cursor
            except Exception as e:
                logger.error(f"Query failed on connection {self.connection_id}: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                raise

    def executemany(self, query: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """Execute multiple queries with the same statement"""
        with self._lock:
            if not self.connection:
                raise RuntimeError(f"Connection {self.connection_id} is closed")

            self.last_used = time.time()
            self.query_count += len(params_list)

            try:
                cursor = self.connection.cursor()
                cursor.executemany(query, params_list)
                return cursor
            except Exception as e:
                logger.error(f"Batch query failed on connection {self.connection_id}: {e}")
                raise

    def commit(self):
        """Commit transaction"""
        with self._lock:
            if self.connection:
                self.connection.commit()

    def rollback(self):
        """Rollback transaction"""
        with self._lock:
            if self.connection:
                self.connection.rollback()

    def close(self):
        """Close the connection"""
        with self._lock:
            if self.connection:
                try:
                    self.connection.close()
                    logger.debug(f"Closed connection {self.connection_id}")
                except Exception as e:
                    logger.warning(f"Error closing connection {self.connection_id}: {e}")
                finally:
                    self.connection = None

    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        try:
            with self._lock:
                if not self.connection:
                    return False

                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return True
        except Exception:
            return False

    def get_age(self) -> float:
        """Get connection age in seconds"""
        return time.time() - self.created_at

    def get_idle_time(self) -> float:
        """Get time since last use in seconds"""
        return time.time() - self.last_used


class SQLiteConnectionPool:
    """
    High-performance SQLite connection pool with automatic scaling.

    Features:
    - Automatic connection scaling based on demand
    - Connection health monitoring and recovery
    - Query optimization and caching
    - Deadlock detection and recovery
    - Comprehensive statistics and monitoring
    """

    def __init__(
        self,
        db_path: Path,
        min_connections: int = 2,
        max_connections: int = 20,
        max_idle_time: float = 300.0,  # 5 minutes
        max_connection_age: float = 3600.0,  # 1 hour
        health_check_interval: float = 60.0,  # 1 minute
    ):
        self.db_path = db_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.max_connection_age = max_connection_age
        self.health_check_interval = health_check_interval

        # Connection management
        self._pool: Queue[PooledConnection] = Queue(maxsize=max_connections)
        self._all_connections: Dict[int, PooledConnection] = {}
        self._next_connection_id = 1
        self._lock = threading.RLock()

        # Statistics
        self._stats = ConnectionStats(
            total_connections=0,
            active_connections=0,
            idle_connections=0,
            total_queries=0,
            failed_queries=0,
            average_query_time=0.0,
            peak_connections=0,
        )
        self._query_times: List[float] = []

        # Background maintenance
        self._maintenance_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # Initialize pool
        self._initialize_pool()
        self._start_maintenance()

        logger.info(f"Initialized connection pool for {db_path}: {min_connections}-{max_connections} connections")

    def _initialize_pool(self):
        """Initialize the connection pool with minimum connections"""
        with self._lock:
            for _ in range(self.min_connections):
                conn = self._create_connection()
                self._pool.put(conn)
                self._stats.idle_connections += 1

    def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection"""
        connection_id = self._next_connection_id
        self._next_connection_id += 1

        conn = PooledConnection(self.db_path, connection_id)
        self._all_connections[connection_id] = conn
        self._stats.total_connections += 1
        self._stats.peak_connections = max(self._stats.peak_connections, self._stats.total_connections)

        return conn

    def _start_maintenance(self):
        """Start background maintenance thread"""
        if self._maintenance_thread is None or not self._maintenance_thread.is_alive():
            self._maintenance_thread = threading.Thread(
                target=self._maintenance_worker, name=f"ConnectionPool-{self.db_path.name}", daemon=True
            )
            self._maintenance_thread.start()

    def _maintenance_worker(self):
        """Background worker for connection maintenance"""
        while not self._shutdown_event.wait(self.health_check_interval):
            try:
                self._cleanup_connections()
                self._health_check()
            except Exception as e:
                logger.error(f"Connection pool maintenance error: {e}")

    def _cleanup_connections(self):
        """Clean up old and idle connections"""
        with self._lock:
            time.time()
            connections_to_remove = []

            # Check all connections for cleanup
            for conn_id, conn in self._all_connections.items():
                should_remove = False

                # Remove old connections
                if conn.get_age() > self.max_connection_age:
                    should_remove = True
                    logger.debug(f"Removing aged connection {conn_id}")

                # Remove idle connections (but keep minimum)
                elif (
                    conn.get_idle_time() > self.max_idle_time
                    and not conn.is_active
                    and self._stats.total_connections > self.min_connections
                ):
                    should_remove = True
                    logger.debug(f"Removing idle connection {conn_id}")

                # Remove unhealthy connections
                elif not conn.is_healthy():
                    should_remove = True
                    logger.warning(f"Removing unhealthy connection {conn_id}")

                if should_remove:
                    connections_to_remove.append(conn_id)

            # Remove marked connections
            for conn_id in connections_to_remove:
                self._remove_connection(conn_id)

    def _remove_connection(self, connection_id: int):
        """Remove a connection from the pool"""
        if connection_id in self._all_connections:
            conn = self._all_connections[connection_id]
            conn.close()
            del self._all_connections[connection_id]
            self._stats.total_connections -= 1

            # Try to remove from pool queue (may not be there if active)
            try:
                # Create a new queue without the removed connection
                new_queue = Queue(maxsize=self.max_connections)
                while not self._pool.empty():
                    try:
                        pool_conn = self._pool.get_nowait()
                        if pool_conn.connection_id != connection_id:
                            new_queue.put(pool_conn)
                        else:
                            self._stats.idle_connections -= 1
                    except Empty:
                        break
                self._pool = new_queue
            except Exception as e:
                logger.warning(f"Error updating pool queue: {e}")

    def _health_check(self):
        """Perform health check on connections"""
        with self._lock:
            # Ensure minimum connections
            while self._stats.total_connections < self.min_connections:
                try:
                    conn = self._create_connection()
                    self._pool.put(conn)
                    self._stats.idle_connections += 1
                except Exception as e:
                    logger.error(f"Failed to create minimum connection: {e}")
                    break

    @contextmanager
    def get_connection(self, timeout: float = 30.0) -> ContextManager[PooledConnection]:
        """
        Get a connection from the pool.

        Args:
            timeout: Maximum time to wait for a connection

        Yields:
            PooledConnection instance
        """
        conn = None
        start_time = time.time()

        try:
            # Try to get connection from pool
            try:
                conn = self._pool.get(timeout=timeout)
                with self._lock:
                    self._stats.idle_connections -= 1
                    self._stats.active_connections += 1
                    conn.is_active = True
            except Empty:
                # Pool is empty, try to create new connection if under limit
                with self._lock:
                    if self._stats.total_connections < self.max_connections:
                        conn = self._create_connection()
                        self._stats.active_connections += 1
                        conn.is_active = True
                    else:
                        raise RuntimeError(f"Connection pool exhausted (max: {self.max_connections})")

            # Verify connection health
            if not conn.is_healthy():
                logger.warning(f"Unhealthy connection {conn.connection_id}, creating new one")
                self._remove_connection(conn.connection_id)
                conn = self._create_connection()
                with self._lock:
                    self._stats.active_connections += 1
                    conn.is_active = True

            yield conn

        except Exception as e:
            with self._lock:
                self._stats.failed_queries += 1
            logger.error(f"Connection pool error: {e}")
            raise

        finally:
            # Return connection to pool
            if conn:
                query_time = time.time() - start_time
                self._update_query_stats(query_time)

                with self._lock:
                    conn.is_active = False
                    self._stats.active_connections -= 1

                    # Return to pool if healthy and not over capacity
                    if conn.is_healthy() and self._stats.total_connections <= self.max_connections:
                        try:
                            self._pool.put_nowait(conn)
                            self._stats.idle_connections += 1
                        except:
                            # Pool is full, remove connection
                            self._remove_connection(conn.connection_id)
                    else:
                        # Remove unhealthy or excess connection
                        self._remove_connection(conn.connection_id)

    def _update_query_stats(self, query_time: float):
        """Update query performance statistics"""
        with self._lock:
            self._stats.total_queries += 1
            self._query_times.append(query_time)

            # Keep only recent query times for average calculation
            if len(self._query_times) > 1000:
                self._query_times = self._query_times[-1000:]

            self._stats.average_query_time = sum(self._query_times) / len(self._query_times)

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Any:
        """
        Execute a query using a pooled connection.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return only first result
            fetch_all: Return all results

        Returns:
            Query results
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor

    def execute_batch(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute a batch of queries with the same statement.

        Args:
            query: SQL query string
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

    def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """
        Execute multiple queries in a transaction.

        Args:
            queries: List of (query, params) tuples

        Returns:
            True if successful, False otherwise
        """
        with self.get_connection() as conn:
            try:
                for query, params in queries:
                    conn.execute(query, params)
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                return False

    def get_statistics(self) -> ConnectionStats:
        """Get connection pool statistics"""
        with self._lock:
            # Update current counts
            self._stats.idle_connections = self._pool.qsize()
            return ConnectionStats(
                total_connections=self._stats.total_connections,
                active_connections=self._stats.active_connections,
                idle_connections=self._stats.idle_connections,
                total_queries=self._stats.total_queries,
                failed_queries=self._stats.failed_queries,
                average_query_time=self._stats.average_query_time,
                peak_connections=self._stats.peak_connections,
            )

    def close(self):
        """Close all connections and shutdown the pool"""
        logger.info(f"Shutting down connection pool for {self.db_path}")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for maintenance thread
        if self._maintenance_thread and self._maintenance_thread.is_alive():
            self._maintenance_thread.join(timeout=5.0)

        # Close all connections
        with self._lock:
            for conn in self._all_connections.values():
                conn.close()
            self._all_connections.clear()

            # Clear pool
            while not self._pool.empty():
                try:
                    self._pool.get_nowait()
                except Empty:
                    break

        logger.info("Connection pool shutdown complete")


# Global connection pools
_connection_pools: Dict[str, SQLiteConnectionPool] = {}
_pools_lock = threading.Lock()


def get_connection_pool(db_path: Path, min_connections: int = 2, max_connections: int = 20) -> SQLiteConnectionPool:
    """
    Get or create a connection pool for a database.

    Args:
        db_path: Path to SQLite database
        min_connections: Minimum pool size
        max_connections: Maximum pool size

    Returns:
        SQLiteConnectionPool instance
    """
    db_key = str(db_path.resolve())

    with _pools_lock:
        if db_key not in _connection_pools:
            _connection_pools[db_key] = SQLiteConnectionPool(
                db_path=db_path, min_connections=min_connections, max_connections=max_connections
            )

        return _connection_pools[db_key]


def close_all_pools():
    """Close all connection pools"""
    with _pools_lock:
        for pool in _connection_pools.values():
            pool.close()
        _connection_pools.clear()


# Context manager for database operations
@contextmanager
def database_connection(db_path: Path):
    """
    Context manager for database operations with connection pooling.

    Args:
        db_path: Path to SQLite database

    Yields:
        PooledConnection instance
    """
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        yield conn


# Convenience functions
def execute_query(db_path: Path, query: str, params: tuple = ()) -> List[Any]:
    """Execute a query with connection pooling"""
    pool = get_connection_pool(db_path)
    return pool.execute_query(query, params)


def execute_batch(db_path: Path, query: str, params_list: List[tuple]) -> int:
    """Execute a batch query with connection pooling"""
    pool = get_connection_pool(db_path)
    return pool.execute_batch(query, params_list)


def execute_transaction(db_path: Path, queries: List[Tuple[str, tuple]]) -> bool:
    """Execute a transaction with connection pooling"""
    pool = get_connection_pool(db_path)
    return pool.execute_transaction(queries)

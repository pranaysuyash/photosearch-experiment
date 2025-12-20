"""
Saved Searches with Analytics

This module provides functionality to:
1. Save search queries for later reuse
2. Track search analytics (frequency, timestamps, results)
3. Provide search history and insights
4. Enable quick access to frequently used searches

Features:
- Persistent storage of saved searches
- Search analytics tracking
- Search history management
- Popular/recurring search detection
- Search performance metrics

Usage:
    search_manager = SavedSearchManager('saved_searches.db')
    
    # Save a search
    search_manager.save_search(
        query="beach vacation",
        mode="hybrid",
        results_count=42,
        intent="location"
    )
    
    # Get saved searches
    searches = search_manager.get_saved_searches()
    
    # Get analytics
    analytics = search_manager.get_analytics()
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

class SavedSearchManager:
    """Manage saved searches and analytics."""
    
    def __init__(self, db_path: str = "saved_searches.db"):
        """
        Initialize saved search manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        # Keep the connection non-Optional for callers.
        self.conn: sqlite3.Connection = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and create tables if they don't exist."""
        # Connection is created in __init__.
        
        # Create saved searches table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                mode TEXT DEFAULT 'metadata',
                results_count INTEGER DEFAULT 0,
                intent TEXT DEFAULT 'generic',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_favorite BOOLEAN DEFAULT FALSE,
                notes TEXT,
                metadata_json TEXT
            )
        """)
        
        # Create search analytics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                results_count INTEGER DEFAULT 0,
                execution_time_ms INTEGER DEFAULT 0,
                user_agent TEXT,
                ip_address TEXT,
                FOREIGN KEY (search_id) REFERENCES saved_searches(id)
            )
        """)
        
        # Create search history table (for all searches, not just saved ones)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                mode TEXT DEFAULT 'metadata',
                results_count INTEGER DEFAULT 0,
                intent TEXT DEFAULT 'generic',
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER DEFAULT 0,
                user_agent TEXT,
                ip_address TEXT
            )
        """)
        
        self.conn.commit()
    
    def save_search(
        self,
        query: str,
        mode: str = "metadata",
        results_count: int = 0,
        intent: str = "generic",
        is_favorite: bool = False,
        notes: str = "",
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Save a search query.
        
        Args:
            query: Search query string
            mode: Search mode (metadata, semantic, hybrid)
            results_count: Number of results returned
            intent: Detected search intent
            is_favorite: Whether to mark as favorite
            notes: User notes about the search
            metadata: Additional metadata as dictionary
            
        Returns:
            ID of the saved search
        """
        cursor = self.conn.cursor()
        
        # Check if this exact query already exists
        cursor.execute(
            "SELECT id FROM saved_searches WHERE query = ? AND mode = ?",
            (query, mode)
        )
        existing = cursor.fetchone()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        if existing:
            # Update existing search
            cursor.execute("""
                UPDATE saved_searches
                SET results_count = ?,
                    intent = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    is_favorite = ?,
                    notes = ?,
                    metadata_json = ?
                WHERE id = ?
            """, (results_count, intent, is_favorite, notes, metadata_json, existing['id']))
            search_id = existing['id']
        else:
            # Insert new search
            cursor.execute("""
                INSERT INTO saved_searches 
                (query, mode, results_count, intent, is_favorite, notes, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (query, mode, results_count, intent, is_favorite, notes, metadata_json))
            search_id = cursor.lastrowid
        
        self.conn.commit()
        return search_id
    
    def log_search_execution(
        self,
        search_id: int,
        results_count: int,
        execution_time_ms: int = 0,
        user_agent: str = "unknown",
        ip_address: str = "unknown"
    ) -> int:
        """
        Log execution of a saved search for analytics.
        
        Args:
            search_id: ID of the saved search
            results_count: Number of results returned
            execution_time_ms: Execution time in milliseconds
            user_agent: User agent string
            ip_address: IP address of the user
            
        Returns:
            ID of the analytics record
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO search_analytics 
            (search_id, results_count, execution_time_ms, user_agent, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (search_id, results_count, execution_time_ms, user_agent, ip_address))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def log_search_history(
        self,
        query: str,
        mode: str = "metadata",
        results_count: int = 0,
        intent: str = "generic",
        execution_time_ms: int = 0,
        user_agent: str = "unknown",
        ip_address: str = "unknown"
    ) -> int:
        """
        Log any search execution to history (not necessarily saved).
        
        Args:
            query: Search query string
            mode: Search mode
            results_count: Number of results
            intent: Detected intent
            execution_time_ms: Execution time
            user_agent: User agent
            ip_address: IP address
            
        Returns:
            ID of the history record
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO search_history 
            (query, mode, results_count, intent, execution_time_ms, user_agent, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (query, mode, results_count, intent, execution_time_ms, user_agent, ip_address))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_saved_searches(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "DESC",
        filter_favorites: bool = False
    ) -> List[Dict]:
        """
        Get saved searches with pagination and filtering.
        
        Args:
            limit: Maximum number of results
            offset: Pagination offset
            sort_by: Field to sort by (updated_at, created_at, query, results_count)
            sort_order: Sort order (ASC or DESC)
            filter_favorites: Only return favorite searches
            
        Returns:
            List of saved search dictionaries
        """
        cursor = self.conn.cursor()
        
        # Build query
        query = "SELECT * FROM saved_searches"
        conditions = []
        params = []
        
        if filter_favorites:
            conditions.append("is_favorite = TRUE")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Add sorting
        valid_sort_fields = ['updated_at', 'created_at', 'query', 'results_count']
        sort_field = sort_by if sort_by in valid_sort_fields else 'updated_at'
        sort_direction = sort_order.upper() if sort_order.upper() in ['ASC', 'DESC'] else 'DESC'
        
        query += f" ORDER BY {sort_field} {sort_direction}"
        
        # Add pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        searches = []
        for row in rows:
            search = dict(row)
            if search['metadata_json']:
                search['metadata'] = json.loads(search['metadata_json'])
            else:
                search['metadata'] = {}
            searches.append(search)
        
        return searches
    
    def get_saved_search_by_id(self, search_id: int) -> Optional[Dict]:
        """
        Get a saved search by ID.
        
        Args:
            search_id: ID of the search
            
        Returns:
            Dictionary with search data or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM saved_searches WHERE id = ?", (search_id,))
        row = cursor.fetchone()
        
        if row:
            search = dict(row)
            if search['metadata_json']:
                search['metadata'] = json.loads(search['metadata_json'])
            else:
                search['metadata'] = {}
            return search
        
        return None
    
    def get_search_analytics(self, search_id: int) -> List[Dict]:
        """
        Get analytics for a specific saved search.
        
        Args:
            search_id: ID of the saved search
            
        Returns:
            List of analytics records
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM search_analytics WHERE search_id = ? ORDER BY executed_at DESC",
            (search_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_overall_analytics(self) -> Dict:
        """
        Get overall search analytics and insights.
        
        Returns:
            Dictionary with analytics data
        """
        cursor = self.conn.cursor()
        
        # Total saved searches
        cursor.execute("SELECT COUNT(*) as count FROM saved_searches")
        total_saved = cursor.fetchone()['count']
        
        # Total search executions
        cursor.execute("SELECT COUNT(*) as count FROM search_analytics")
        total_executions = cursor.fetchone()['count']
        
        # Total history entries
        cursor.execute("SELECT COUNT(*) as count FROM search_history")
        total_history = cursor.fetchone()['count']
        
        # Most popular searches
        cursor.execute("""
            SELECT s.id, s.query, s.mode, COUNT(a.id) as execution_count
            FROM saved_searches s
            LEFT JOIN search_analytics a ON s.id = a.search_id
            GROUP BY s.id, s.query, s.mode
            ORDER BY execution_count DESC
            LIMIT 5
        """)
        popular_searches = []
        for row in cursor.fetchall():
            popular_searches.append({
                'id': row['id'],
                'query': row['query'],
                'mode': row['mode'],
                'execution_count': row['execution_count']
            })
        
        # Recent searches
        cursor.execute("""
            SELECT id, query, mode, updated_at
            FROM saved_searches
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        recent_searches = []
        for row in cursor.fetchall():
            recent_searches.append({
                'id': row['id'],
                'query': row['query'],
                'mode': row['mode'],
                'updated_at': row['updated_at']
            })
        
        # Favorite searches
        cursor.execute("""
            SELECT id, query, mode, updated_at
            FROM saved_searches
            WHERE is_favorite = TRUE
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        favorite_searches = []
        for row in cursor.fetchall():
            favorite_searches.append({
                'id': row['id'],
                'query': row['query'],
                'mode': row['mode'],
                'updated_at': row['updated_at']
            })
        
        # Search mode distribution
        cursor.execute("""
            SELECT mode, COUNT(*) as count
            FROM saved_searches
            GROUP BY mode
        """)
        mode_distribution = {row['mode']: row['count'] for row in cursor.fetchall()}
        
        # Intent distribution
        cursor.execute("""
            SELECT intent, COUNT(*) as count
            FROM saved_searches
            GROUP BY intent
        """)
        intent_distribution = {row['intent']: row['count'] for row in cursor.fetchall()}
        
        return {
            'total_saved_searches': total_saved,
            'total_executions': total_executions,
            'total_history_entries': total_history,
            'popular_searches': popular_searches,
            'recent_searches': recent_searches,
            'favorite_searches': favorite_searches,
            'mode_distribution': mode_distribution,
            'intent_distribution': intent_distribution,
            'last_updated': datetime.now().isoformat()
        }

    def get_detailed_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Return detailed analytics over the last N days.

        This complements `get_overall_analytics()` by focusing on time-bounded
        behavior: daily volume, top queries, intent/mode breakdown, and
        performance.
        """
        if days <= 0:
            days = 1

        cursor = self.conn.cursor()
        window = f"-{int(days)} days"

        # Daily volume (history includes all searches, not only saved ones)
        cursor.execute(
            """
            SELECT date(executed_at) AS day, COUNT(*) AS count
            FROM search_history
            WHERE executed_at >= datetime('now', ?)
            GROUP BY day
            ORDER BY day ASC
            """,
            (window,),
        )
        daily_volume = [dict(row) for row in cursor.fetchall()]

        # Top queries in the window
        cursor.execute(
            """
            SELECT query, mode, intent, COUNT(*) AS executions,
                   AVG(execution_time_ms) AS avg_execution_time_ms,
                   AVG(results_count) AS avg_results_count
            FROM search_history
            WHERE executed_at >= datetime('now', ?)
            GROUP BY query, mode, intent
            ORDER BY executions DESC
            LIMIT 20
            """,
            (window,),
        )
        top_queries = [dict(row) for row in cursor.fetchall()]

        # Mode distribution in the window
        cursor.execute(
            """
            SELECT mode, COUNT(*) AS count
            FROM search_history
            WHERE executed_at >= datetime('now', ?)
            GROUP BY mode
            """,
            (window,),
        )
        mode_distribution = {row["mode"]: row["count"] for row in cursor.fetchall()}

        # Intent distribution in the window
        cursor.execute(
            """
            SELECT intent, COUNT(*) AS count
            FROM search_history
            WHERE executed_at >= datetime('now', ?)
            GROUP BY intent
            """,
            (window,),
        )
        intent_distribution = {row["intent"]: row["count"] for row in cursor.fetchall()}

        # Performance summary
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                AVG(execution_time_ms) AS avg_execution_time_ms,
                MIN(execution_time_ms) AS min_execution_time_ms,
                MAX(execution_time_ms) AS max_execution_time_ms
            FROM search_history
            WHERE executed_at >= datetime('now', ?)
            """,
            (window,),
        )
        perf = cursor.fetchone()
        performance = dict(perf) if perf else {}

        return {
            "window_days": int(days),
            "daily_volume": daily_volume,
            "top_queries": top_queries,
            "mode_distribution": mode_distribution,
            "intent_distribution": intent_distribution,
            "performance": performance,
            "generated_at": datetime.now().isoformat(),
        }

    def get_search_trends(self, days: int = 90) -> Dict[str, Any]:
        """Return trend-oriented time series over the last N days."""
        if days <= 0:
            days = 1
        cursor = self.conn.cursor()
        window = f"-{int(days)} days"

        cursor.execute(
            """
            SELECT date(executed_at) AS day,
                   COUNT(*) AS searches,
                   AVG(results_count) AS avg_results,
                   AVG(execution_time_ms) AS avg_execution_time_ms
            FROM search_history
            WHERE executed_at >= datetime('now', ?)
            GROUP BY day
            ORDER BY day ASC
            """,
            (window,),
        )
        series = [dict(row) for row in cursor.fetchall()]
        return {
            "window_days": int(days),
            "series": series,
            "generated_at": datetime.now().isoformat(),
        }

    def export_analytics(self, format_type: str = "json", days: int = 30) -> str:
        """Export analytics in json/csv/text formats."""
        fmt = (format_type or "json").lower()
        data = {
            "overall": self.get_overall_analytics(),
            "detailed": self.get_detailed_analytics(days=days),
            "trends": self.get_search_trends(days=max(days, 1)),
        }

        if fmt == "json":
            return json.dumps(data, indent=2, default=str)

        if fmt == "text":
            overall = data["overall"]
            detailed = data["detailed"]
            lines = [
                "Search Analytics Export",
                f"Generated: {datetime.now().isoformat()}",
                "",
                f"Total saved searches: {overall.get('total_saved_searches')}",
                f"Total executions: {overall.get('total_executions')}",
                f"Total history entries: {overall.get('total_history_entries')}",
                "",
                f"Window (days): {detailed.get('window_days')}",
                f"Daily points: {len(detailed.get('daily_volume', []))}",
                f"Top queries: {len(detailed.get('top_queries', []))}",
            ]
            return "\n".join(lines)

        if fmt == "csv":
            # Simple CSV for the daily trend series.
            rows = data["trends"].get("series", [])
            out_lines = ["day,searches,avg_results,avg_execution_time_ms"]
            for r in rows:
                out_lines.append(
                    f"{r.get('day','')},{r.get('searches','')},{r.get('avg_results','')},{r.get('avg_execution_time_ms','')}"
                )
            return "\n".join(out_lines)

        raise ValueError("format_type must be one of: json, csv, text")
    
    def get_search_history(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "executed_at",
        sort_order: str = "DESC"
    ) -> List[Dict]:
        """
        Get search history with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Pagination offset
            sort_by: Field to sort by
            sort_order: Sort order (ASC or DESC)
            
        Returns:
            List of search history records
        """
        cursor = self.conn.cursor()
        
        valid_sort_fields = ['executed_at', 'query', 'results_count', 'execution_time_ms']
        sort_field = sort_by if sort_by in valid_sort_fields else 'executed_at'
        sort_direction = sort_order.upper() if sort_order.upper() in ['ASC', 'DESC'] else 'DESC'
        
        query = f"""
            SELECT * FROM search_history
            ORDER BY {sort_field} {sort_direction}
            LIMIT ? OFFSET ?
        """
        
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def delete_saved_search(self, search_id: int) -> bool:
        """
        Delete a saved search.
        
        Args:
            search_id: ID of the search to delete
            
        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        
        # First delete analytics for this search
        cursor.execute("DELETE FROM search_analytics WHERE search_id = ?", (search_id,))
        
        # Then delete the search itself
        cursor.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
        
        if cursor.rowcount > 0:
            self.conn.commit()
            return True
        
        return False
    
    def toggle_favorite(self, search_id: int) -> bool:
        """
        Toggle favorite status of a saved search.
        
        Args:
            search_id: ID of the search
            
        Returns:
            New favorite status
        """
        cursor = self.conn.cursor()
        
        # Get current status
        cursor.execute("SELECT is_favorite FROM saved_searches WHERE id = ?", (search_id,))
        row = cursor.fetchone()
        
        if row:
            current_status = row['is_favorite']
            new_status = not current_status
            
            cursor.execute(
                "UPDATE saved_searches SET is_favorite = ? WHERE id = ?",
                (new_status, search_id)
            )
            self.conn.commit()
            return new_status
        
        return False
    
    def update_search_notes(self, search_id: int, notes: str) -> bool:
        """
        Update notes for a saved search.
        
        Args:
            search_id: ID of the search
            notes: New notes text
            
        Returns:
            True if updated, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE saved_searches SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (notes, search_id)
        )
        
        if cursor.rowcount > 0:
            self.conn.commit()
            return True
        
        return False
    
    def clear_search_history(self) -> int:
        """
        Clear all search history (but keep saved searches).
        
        Returns:
            Number of records deleted
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM search_history")
        deleted_count = cursor.rowcount
        self.conn.commit()
        return deleted_count
    
    def get_recurring_searches(self, threshold: int = 2) -> List[Dict]:
        """
        Get searches that have been executed multiple times.
        
        Args:
            threshold: Minimum number of executions to be considered recurring
            
        Returns:
            List of recurring searches with execution counts
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                s.id, s.query, s.mode, s.intent,
                COUNT(a.id) as execution_count,
                MAX(a.executed_at) as last_executed
            FROM saved_searches s
            LEFT JOIN search_analytics a ON s.id = a.search_id
            GROUP BY s.id, s.query, s.mode, s.intent
            HAVING execution_count >= ?
            ORDER BY execution_count DESC, last_executed DESC
        """
        
        cursor.execute(query, (threshold,))
        rows = cursor.fetchall()
        
        recurring = []
        for row in rows:
            recurring.append({
                'id': row['id'],
                'query': row['query'],
                'mode': row['mode'],
                'intent': row['intent'],
                'execution_count': row['execution_count'],
                'last_executed': row['last_executed']
            })
        
        return recurring
    
    def get_search_performance(self) -> Dict:
        """
        Get performance metrics for searches.
        
        Returns:
            Dictionary with performance data
        """
        cursor = self.conn.cursor()
        
        # Average execution time
        cursor.execute("SELECT AVG(execution_time_ms) as avg_time FROM search_analytics")
        avg_time_row = cursor.fetchone()
        avg_execution_time = avg_time_row['avg_time'] if avg_time_row['avg_time'] else 0
        
        # Fastest and slowest searches
        cursor.execute("""
            SELECT query, execution_time_ms, mode
            FROM search_history
            WHERE execution_time_ms > 0
            ORDER BY execution_time_ms ASC
            LIMIT 1
        """)
        fastest = cursor.fetchone()
        
        cursor.execute("""
            SELECT query, execution_time_ms, mode
            FROM search_history
            WHERE execution_time_ms > 0
            ORDER BY execution_time_ms DESC
            LIMIT 1
        """)
        slowest = cursor.fetchone()
        
        # Execution time distribution by mode
        cursor.execute("""
            SELECT mode, AVG(execution_time_ms) as avg_time, COUNT(*) as count
            FROM search_history
            WHERE execution_time_ms > 0
            GROUP BY mode
        """)
        mode_performance = {}
        for row in cursor.fetchall():
            mode_performance[row['mode']] = {
                'avg_time_ms': row['avg_time'],
                'count': row['count']
            }
        
        return {
            'average_execution_time_ms': round(avg_execution_time, 2),
            'fastest_search': {
                'query': fastest['query'] if fastest else None,
                'time_ms': fastest['execution_time_ms'] if fastest else None,
                'mode': fastest['mode'] if fastest else None
            } if fastest else None,
            'slowest_search': {
                'query': slowest['query'] if slowest else None,
                'time_ms': slowest['execution_time_ms'] if slowest else None,
                'mode': slowest['mode'] if slowest else None
            } if slowest else None,
            'mode_performance': mode_performance
        }
    
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
    """CLI interface for testing saved searches."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Saved Searches Manager')
    parser.add_argument('--db', default='saved_searches.db', help='Database path')
    parser.add_argument('--list', action='store_true', help='List saved searches')
    parser.add_argument('--analytics', action='store_true', help='Show analytics')
    parser.add_argument('--history', action='store_true', help='Show search history')
    
    args = parser.parse_args()
    
    with SavedSearchManager(args.db) as manager:
        if args.list:
            searches = manager.get_saved_searches()
            print(f"Saved Searches ({len(searches)}):")
            print("=" * 60)
            for search in searches:
                print(f"ID: {search['id']}")
                print(f"Query: {search['query']}")
                print(f"Mode: {search['mode']}")
                print(f"Intent: {search['intent']}")
                print(f"Results: {search['results_count']}")
                print(f"Favorite: {'⭐' if search['is_favorite'] else ' '}")
                print(f"Updated: {search['updated_at']}")
                print("-" * 40)
        
        elif args.analytics:
            analytics = manager.get_overall_analytics()
            print("Search Analytics:")
            print("=" * 60)
            print(f"Total Saved Searches: {analytics['total_saved_searches']}")
            print(f"Total Executions: {analytics['total_executions']}")
            print(f"Total History: {analytics['total_history_entries']}")
            
            print(f"\nPopular Searches:")
            for search in analytics['popular_searches']:
                print(f"  {search['query']} ({search['execution_count']}x)")
            
            print(f"\nRecent Searches:")
            for search in analytics['recent_searches']:
                print(f"  {search['query']} ({search['updated_at']})")
            
            print(f"\nMode Distribution:")
            for mode, count in analytics['mode_distribution'].items():
                print(f"  {mode}: {count}")
            
            print(f"\nIntent Distribution:")
            for intent, count in analytics['intent_distribution'].items():
                print(f"  {intent}: {count}")
        
        elif args.history:
            history = manager.get_search_history(limit=10)
            print(f"Recent Search History ({len(history)} entries):")
            print("=" * 60)
            for entry in history:
                print(f"{entry['executed_at']} - {entry['query']}")
                print(f"  Mode: {entry['mode']}, Results: {entry['results_count']}")
                print(f"  Intent: {entry['intent']}, Time: {entry['execution_time_ms']}ms")
                print("-" * 40)
        
        else:
            # Test saving a search
            search_id = manager.save_search(
                query="beach vacation 2023",
                mode="hybrid",
                results_count=42,
                intent="location"
            )
            print(f"Saved search with ID: {search_id}")
            
            # Log execution
            manager.log_search_execution(
                search_id=search_id,
                results_count=42,
                execution_time_ms=150
            )
            print("Logged search execution")
            
            # Get analytics
            analytics = manager.get_overall_analytics()
            print(f"Total searches: {analytics['total_saved_searches']}")


if __name__ == "main":
    main()
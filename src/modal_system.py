"""
Modal/Dialog System for PhotoSearch

This module provides a comprehensive modal/dialog system that integrates with
both the backend API and frontend components. It handles:

1. Dialog Management - Create, update, and manage dialogs
2. Dialog Types - Support for various dialog types (confirmation, info, error, custom)
3. Dialog State - Persistent dialog state management
4. Dialog Actions - Handle dialog actions and callbacks
5. Dialog History - Track dialog interactions
6. API Integration - Backend API endpoints for dialog management

Features:
- REST API endpoints for dialog management
- Dialog state persistence
- Dialog action handling
- Dialog history and analytics
- Integration with existing search and intent systems

Usage:
    # Backend usage (FastAPI integration)
    from src.modal_system import DialogManager
    
    dialog_manager = DialogManager()
    
    # Create a dialog
    dialog_id = dialog_manager.create_dialog(
        dialog_type='confirmation',
        title='Delete Image',
        message='Are you sure you want to delete this image?',
        actions=['cancel', 'delete']
    )
    
    # Frontend usage (would be implemented in React/Vue)
    # Dialogs would be fetched from API and displayed in UI
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from enum import Enum

class DialogType(Enum):
    """Supported dialog types."""
    INFORMATION = "information"
    WARNING = "warning"
    ERROR = "error"
    CONFIRMATION = "confirmation"
    INPUT = "input"
    SELECTION = "selection"
    CUSTOM = "custom"
    PROGRESS = "progress"
    SUCCESS = "success"

class DialogAction(Enum):
    """Standard dialog actions."""
    CANCEL = "cancel"
    CONFIRM = "confirm"
    OK = "ok"
    YES = "yes"
    NO = "no"
    CLOSE = "close"
    SUBMIT = "submit"

class DialogManager:
    """Manage dialogs and their state."""
    
    def __init__(self, db_path: str = "dialogs.db"):
        """
        Initialize dialog manager.
        
        Args:
            db_path: Path to SQLite database for storing dialog data
        """
        self.db_path = db_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and create tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create dialogs table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dialogs (
                id TEXT PRIMARY KEY,
                dialog_type TEXT NOT NULL,
                title TEXT,
                message TEXT,
                details TEXT,
                actions TEXT,  -- JSON array of action buttons
                data TEXT,     -- JSON data for the dialog
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                priority INTEGER DEFAULT 0,
                user_id TEXT,
                context TEXT
            )
        """)
        
        # Create dialog history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dialog_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dialog_id TEXT,
                action TEXT,
                action_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                FOREIGN KEY (dialog_id) REFERENCES dialogs(id)
            )
        """)
        
        # Create dialog state table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dialog_state (
                dialog_id TEXT PRIMARY KEY,
                is_open BOOLEAN DEFAULT TRUE,
                is_dismissed BOOLEAN DEFAULT FALSE,
                current_step INTEGER DEFAULT 0,
                state_data TEXT,  -- JSON state data
                FOREIGN KEY (dialog_id) REFERENCES dialogs(id)
            )
        """)
        
        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_type ON dialogs(dialog_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_user ON dialogs(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_priority ON dialogs(priority)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_history_dialog ON dialog_history(dialog_id)")
        
        self.conn.commit()
    
    def create_dialog(
        self,
        dialog_type: str,
        title: str = "",
        message: str = "",
        actions: List[str] = None,
        data: Dict = None,
        user_id: str = "system",
        context: str = "general",
        priority: int = 0,
        expires_in: int = None
    ) -> str:
        """
        Create a new dialog.
        
        Args:
            dialog_type: Type of dialog (information, warning, error, etc.)
            title: Dialog title
            message: Main message content
            actions: List of action buttons
            data: Additional data for the dialog
            user_id: User ID associated with the dialog
            context: Context for the dialog
            priority: Dialog priority (higher = more important)
            expires_in: Seconds until dialog expires (None = no expiration)
            
        Returns:
            Dialog ID
        """
        dialog_id = str(uuid.uuid4())
        
        # Set default actions based on dialog type
        if actions is None:
            if dialog_type == DialogType.CONFIRMATION.value:
                actions = [DialogAction.CANCEL.value, DialogAction.CONFIRM.value]
            elif dialog_type == DialogType.INPUT.value:
                actions = [DialogAction.CANCEL.value, DialogAction.SUBMIT.value]
            else:
                actions = [DialogAction.OK.value]
        
        # Calculate expiration time
        expires_at = None
        if expires_in:
            expires_at = datetime.now().timestamp() + expires_in
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO dialogs 
            (id, dialog_type, title, message, actions, data, user_id, context, priority, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dialog_id,
            dialog_type,
            title,
            message,
            json.dumps(actions),
            json.dumps(data) if data else None,
            user_id,
            context,
            priority,
            expires_at
        ))
        
        # Initialize dialog state
        cursor.execute("""
            INSERT INTO dialog_state 
            (dialog_id, is_open, is_dismissed)
            VALUES (?, TRUE, FALSE)
        """, (dialog_id,))
        
        self.conn.commit()
        return dialog_id
    
    def get_dialog(self, dialog_id: str) -> Optional[Dict]:
        """
        Get a dialog by ID.
        
        Args:
            dialog_id: Dialog ID
            
        Returns:
            Dictionary with dialog data or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT d.*, ds.is_open, ds.is_dismissed, ds.current_step, ds.state_data
            FROM dialogs d
            LEFT JOIN dialog_state ds ON d.id = ds.dialog_id
            WHERE d.id = ?
        """, (dialog_id,))
        
        row = cursor.fetchone()
        
        if row:
            dialog = dict(row)
            dialog['actions'] = json.loads(dialog['actions']) if dialog['actions'] else []
            dialog['data'] = json.loads(dialog['data']) if dialog['data'] else {}
            dialog['state_data'] = json.loads(dialog['state_data']) if dialog['state_data'] else {}
            return dialog
        
        return None
    
    def get_active_dialogs(
        self,
        user_id: str = None,
        context: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get active (open) dialogs.
        
        Args:
            user_id: Filter by user ID
            context: Filter by context
            limit: Maximum number of results
            
        Returns:
            List of active dialogs
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT d.*, ds.is_open, ds.is_dismissed, ds.current_step, ds.state_data
            FROM dialogs d
            JOIN dialog_state ds ON d.id = ds.dialog_id
            WHERE ds.is_open = TRUE AND ds.is_dismissed = FALSE
        """
        
        params = []
        
        if user_id:
            query += " AND d.user_id = ?"
            params.append(user_id)
        
        if context:
            query += " AND d.context = ?"
            params.append(context)
        
        # Add expiration check
        query += " AND (d.expires_at IS NULL OR d.expires_at > ?)"
        params.append(datetime.now().timestamp())
        
        query += " ORDER BY d.priority DESC, d.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        dialogs = []
        for row in cursor.fetchall():
            dialog = dict(row)
            dialog['actions'] = json.loads(dialog['actions']) if dialog['actions'] else []
            dialog['data'] = json.loads(dialog['data']) if dialog['data'] else {}
            dialog['state_data'] = json.loads(dialog['state_data']) if dialog['state_data'] else {}
            dialogs.append(dialog)
        
        return dialogs
    
    def update_dialog_state(
        self,
        dialog_id: str,
        is_open: Optional[bool] = None,
        is_dismissed: Optional[bool] = None,
        current_step: Optional[int] = None,
        state_data: Optional[Dict] = None
    ) -> bool:
        """
        Update dialog state.
        
        Args:
            dialog_id: Dialog ID
            is_open: Whether dialog is open
            is_dismissed: Whether dialog is dismissed
            current_step: Current step in multi-step dialog
            state_data: State data for the dialog
            
        Returns:
            True if updated, False if dialog not found
        """
        cursor = self.conn.cursor()
        
        # Get current state
        cursor.execute("SELECT * FROM dialog_state WHERE dialog_id = ?", (dialog_id,))
        row = cursor.fetchone()
        
        if not row:
            return False
        
        # Update fields
        updates = []
        params = []
        
        if is_open is not None:
            updates.append("is_open = ?")
            params.append(is_open)
        
        if is_dismissed is not None:
            updates.append("is_dismissed = ?")
            params.append(is_dismissed)
        
        if current_step is not None:
            updates.append("current_step = ?")
            params.append(current_step)
        
        if state_data is not None:
            updates.append("state_data = ?")
            params.append(json.dumps(state_data))
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE dialog_state SET {', '.join(updates)} WHERE dialog_id = ?"
            params.append(dialog_id)
            cursor.execute(query, params)
            self.conn.commit()
        
        return True


# Backwards-compatible wrapper expected by server/main.py
class ModalSystem(DialogManager):
    """Compatibility wrapper: historical name used by server initialization.

    This simply extends DialogManager so existing code that imports
    `ModalSystem` keeps working.
    """
    def __init__(self, db_path: str = "dialogs.db"):
        super().__init__(db_path=db_path)
    
    def record_dialog_action(
        self,
        dialog_id: str,
        action: str,
        action_data: Dict = None,
        user_id: str = "system"
    ) -> bool:
        """
        Record a dialog action in history.
        
        Args:
            dialog_id: Dialog ID
            action: Action taken
            action_data: Additional data about the action
            user_id: User who performed the action
            
        Returns:
            True if recorded, False if failed
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO dialog_history 
                (dialog_id, action, action_data, user_id)
                VALUES (?, ?, ?, ?)
            """, (
                dialog_id,
                action,
                json.dumps(action_data) if action_data else None,
                user_id
            ))
            
            self.conn.commit()
            return True
            
        except Exception:
            return False
    
    def close_dialog(self, dialog_id: str, action: str = None, user_id: str = "system") -> bool:
        """
        Close a dialog.
        
        Args:
            dialog_id: Dialog ID
            action: Optional action that closed the dialog
            user_id: User who closed the dialog
            
        Returns:
            True if closed, False if dialog not found
        """
        # Record action if provided
        if action:
            self.record_dialog_action(dialog_id, action, user_id=user_id)
        
        # Update state
        return self.update_dialog_state(dialog_id, is_open=False)
    
    def dismiss_dialog(self, dialog_id: str, user_id: str = "system") -> bool:
        """
        Dismiss a dialog.
        
        Args:
            dialog_id: Dialog ID
            user_id: User who dismissed the dialog
            
        Returns:
            True if dismissed, False if dialog not found
        """
        # Record dismissal
        self.record_dialog_action(dialog_id, DialogAction.CLOSE.value, {"reason": "dismissed"}, user_id)
        
        # Update state
        return self.update_dialog_state(dialog_id, is_open=False, is_dismissed=True)
    
    def create_confirmation_dialog(
        self,
        title: str,
        message: str,
        confirm_action: str = "confirm",
        cancel_action: str = "cancel",
        data: Dict = None,
        user_id: str = "system"
    ) -> str:
        """
        Create a confirmation dialog.
        
        Args:
            title: Dialog title
            message: Confirmation message
            confirm_action: Action for confirmation
            cancel_action: Action for cancellation
            data: Additional data
            user_id: User ID
            
        Returns:
            Dialog ID
        """
        return self.create_dialog(
            dialog_type=DialogType.CONFIRMATION.value,
            title=title,
            message=message,
            actions=[cancel_action, confirm_action],
            data=data,
            user_id=user_id,
            context="confirmation"
        )
    
    def create_error_dialog(
        self,
        title: str,
        message: str,
        details: str = "",
        user_id: str = "system"
    ) -> str:
        """
        Create an error dialog.
        
        Args:
            title: Dialog title
            message: Error message
            details: Detailed error information
            user_id: User ID
            
        Returns:
            Dialog ID
        """
        return self.create_dialog(
            dialog_type=DialogType.ERROR.value,
            title=title,
            message=message,
            data={"details": details},
            user_id=user_id,
            context="error",
            priority=10  # High priority for errors
        )
    
    def create_progress_dialog(
        self,
        title: str,
        message: str,
        total_steps: int = 1,
        user_id: str = "system"
    ) -> str:
        """
        Create a progress dialog.
        
        Args:
            title: Dialog title
            message: Progress message
            total_steps: Total number of steps
            user_id: User ID
            
        Returns:
            Dialog ID
        """
        dialog_id = self.create_dialog(
            dialog_type=DialogType.PROGRESS.value,
            title=title,
            message=message,
            actions=[],  # No actions for progress dialogs
            data={"total_steps": total_steps, "current_step": 0},
            user_id=user_id,
            context="progress"
        )
        
        # Initialize progress state
        self.update_dialog_state(
            dialog_id,
            state_data={"progress": 0, "status": "starting"}
        )
        
        return dialog_id
    
    def update_progress_dialog(
        self,
        dialog_id: str,
        progress: float,
        status: str = "processing",
        message: str = None
    ) -> bool:
        """
        Update a progress dialog.
        
        Args:
            dialog_id: Dialog ID
            progress: Progress percentage (0-100)
            status: Current status
            message: Updated message
            
        Returns:
            True if updated, False if failed
        """
        # Update dialog message if provided
        if message:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE dialogs SET message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (message, dialog_id))
            self.conn.commit()
        
        # Update state
        return self.update_dialog_state(
            dialog_id,
            state_data={"progress": progress, "status": status}
        )
    
    def complete_progress_dialog(
        self,
        dialog_id: str,
        success: bool = True,
        final_message: str = "Operation completed"
    ) -> bool:
        """
        Complete a progress dialog.
        
        Args:
            dialog_id: Dialog ID
            success: Whether operation was successful
            final_message: Final message to display
            
        Returns:
            True if completed, False if failed
        """
        # Update message
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE dialogs SET message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (final_message, dialog_id))
        
        # Update state
        state_updated = self.update_dialog_state(
            dialog_id,
            state_data={"progress": 100, "status": "completed", "success": success}
        )
        
        # Add appropriate action button
        action = DialogAction.OK.value if success else DialogAction.CLOSE.value
        cursor.execute("""
            UPDATE dialogs SET actions = ? WHERE id = ?
        """, (json.dumps([action]), dialog_id))
        
        self.conn.commit()
        return state_updated
    
    def create_input_dialog(
        self,
        title: str,
        message: str,
        input_type: str = "text",
        input_label: str = "Input",
        input_placeholder: str = "",
        user_id: str = "system"
    ) -> str:
        """
        Create an input dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
            input_type: Type of input (text, number, email, etc.)
            input_label: Label for input field
            input_placeholder: Placeholder text
            user_id: User ID
            
        Returns:
            Dialog ID
        """
        return self.create_dialog(
            dialog_type=DialogType.INPUT.value,
            title=title,
            message=message,
            data={
                "input_type": input_type,
                "input_label": input_label,
                "input_placeholder": input_placeholder,
                "input_value": ""
            },
            user_id=user_id,
            context="input"
        )
    
    def get_dialog_history(
        self,
        dialog_id: str = None,
        user_id: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get dialog history.
        
        Args:
            dialog_id: Filter by dialog ID
            user_id: Filter by user ID
            limit: Maximum number of results
            
        Returns:
            List of dialog history records
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT dh.*, d.dialog_type, d.title, d.message
            FROM dialog_history dh
            JOIN dialogs d ON dh.dialog_id = d.id
        """
        
        params = []
        conditions = []
        
        if dialog_id:
            conditions.append("dh.dialog_id = ?")
            params.append(dialog_id)
        
        if user_id:
            conditions.append("dh.user_id = ?")
            params.append(user_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY dh.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        history = []
        for row in cursor.fetchall():
            record = dict(row)
            record['action_data'] = json.loads(record['action_data']) if record['action_data'] else {}
            history.append(record)
        
        return history
    
    def get_dialog_statistics(self) -> Dict:
        """
        Get statistics about dialog usage.
        
        Returns:
            Dictionary with dialog statistics
        """
        cursor = self.conn.cursor()
        
        # Total dialogs created
        cursor.execute("SELECT COUNT(*) as count FROM dialogs")
        total_dialogs = cursor.fetchone()['count']
        
        # Active dialogs
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM dialog_state 
            WHERE is_open = TRUE AND is_dismissed = FALSE
        """)
        active_dialogs = cursor.fetchone()['count']
        
        # Dialogs by type
        cursor.execute("""
            SELECT dialog_type, COUNT(*) as count
            FROM dialogs
            GROUP BY dialog_type
            ORDER BY count DESC
        """)
        
        type_distribution = {}
        for row in cursor.fetchall():
            type_distribution[row['dialog_type']] = row['count']
        
        # Dialog actions
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM dialog_history
            GROUP BY action
            ORDER BY count DESC
        """)
        
        action_distribution = {}
        for row in cursor.fetchall():
            action_distribution[row['action']] = row['count']
        
        # Recent dialogs
        cursor.execute("""
            SELECT id, dialog_type, title, created_at
            FROM dialogs
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        recent_dialogs = []
        for row in cursor.fetchall():
            recent_dialogs.append({
                'id': row['id'],
                'type': row['dialog_type'],
                'title': row['title'],
                'created_at': row['created_at']
            })
        
        return {
            'total_dialogs': total_dialogs,
            'active_dialogs': active_dialogs,
            'type_distribution': type_distribution,
            'action_distribution': action_distribution,
            'recent_dialogs': recent_dialogs,
            'last_updated': datetime.now().isoformat()
        }
    
    def cleanup_expired_dialogs(self) -> int:
        """
        Clean up expired dialogs.
        
        Returns:
            Number of dialogs cleaned up
        """
        cursor = self.conn.cursor()
        
        # Find expired dialogs
        cursor.execute("""
            SELECT id FROM dialogs 
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (datetime.now().timestamp(),))
        
        expired_ids = [row['id'] for row in cursor.fetchall()]
        
        if not expired_ids:
            return 0
        
        # Close expired dialogs
        for dialog_id in expired_ids:
            self.close_dialog(dialog_id, action="expired")
        
        return len(expired_ids)
    
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
    """CLI interface for testing dialog system."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dialog/Modal System')
    parser.add_argument('--db', default='dialogs.db', help='Database path')
    parser.add_argument('--create', nargs='+', help='Create test dialogs')
    parser.add_argument('--list', action='store_true', help='List active dialogs')
    parser.add_argument('--stats', action='store_true', help='Show dialog statistics')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup expired dialogs')
    
    args = parser.parse_args()
    
    with DialogManager(args.db) as dialog_manager:
        
        if args.create:
            # Create different types of dialogs
            dialogs_created = []
            
            if 'confirmation' in args.create:
                dialog_id = dialog_manager.create_confirmation_dialog(
                    title="Delete Image",
                    message="Are you sure you want to delete this image?",
                    data={"image_id": "123"}
                )
                dialogs_created.append(("Confirmation", dialog_id))
            
            if 'error' in args.create:
                dialog_id = dialog_manager.create_error_dialog(
                    title="Operation Failed",
                    message="Failed to save changes",
                    details="Database connection error"
                )
                dialogs_created.append(("Error", dialog_id))
            
            if 'progress' in args.create:
                dialog_id = dialog_manager.create_progress_dialog(
                    title="Processing Images",
                    message="Scanning and indexing photos...",
                    total_steps=5
                )
                dialogs_created.append(("Progress", dialog_id))
            
            if 'input' in args.create:
                dialog_id = dialog_manager.create_input_dialog(
                    title="Enter Tag",
                    message="Add a tag to this image:",
                    input_label="Tag Name",
                    input_placeholder="e.g., Vacation 2023"
                )
                dialogs_created.append(("Input", dialog_id))
            
            print(f"Created {len(dialogs_created)} dialogs:")
            for dialog_type, dialog_id in dialogs_created:
                print(f"  {dialog_type}: {dialog_id}")
        
        elif args.list:
            dialogs = dialog_manager.get_active_dialogs()
            print(f"Active Dialogs ({len(dialogs)}):")
            print("=" * 60)
            for dialog in dialogs:
                print(f"ID: {dialog['id']}")
                print(f"Type: {dialog['dialog_type']}")
                print(f"Title: {dialog['title']}")
                print(f"Message: {dialog['message'][:50]}...")
                print(f"Actions: {', '.join(dialog['actions'])}")
                print(f"Priority: {dialog['priority']}")
                print(f"Status: {'OPEN' if dialog['is_open'] else 'CLOSED'}")
                print("-" * 40)
        
        elif args.stats:
            stats = dialog_manager.get_dialog_statistics()
            print("Dialog System Statistics:")
            print("=" * 60)
            print(f"Total Dialogs: {stats['total_dialogs']}")
            print(f"Active Dialogs: {stats['active_dialogs']}")
            
            print(f"\nDialogs by Type:")
            for dialog_type, count in stats['type_distribution'].items():
                print(f"  {dialog_type}: {count}")
            
            print(f"\nActions by Type:")
            for action, count in stats['action_distribution'].items():
                print(f"  {action}: {count}")
            
            print(f"\nRecent Dialogs:")
            for dialog in stats['recent_dialogs']:
                print(f"  {dialog['created_at']} - {dialog['type']}: {dialog['title']}")
        
        elif args.cleanup:
            count = dialog_manager.cleanup_expired_dialogs()
            print(f"Cleaned up {count} expired dialogs")
        
        else:
            # Create a sample dialog
            dialog_id = dialog_manager.create_confirmation_dialog(
                title="Sample Dialog",
                message="This is a sample confirmation dialog",
                data={"sample": True}
            )
            print(f"Created sample dialog with ID: {dialog_id}")
            
            # Get and display the dialog
            dialog = dialog_manager.get_dialog(dialog_id)
            print(f"\nDialog Details:")
            print(f"  Type: {dialog['dialog_type']}")
            print(f"  Title: {dialog['title']}")
            print(f"  Message: {dialog['message']}")
            print(f"  Actions: {dialog['actions']}")
            print(f"  Data: {dialog['data']}")


if __name__ == "main":
    main()
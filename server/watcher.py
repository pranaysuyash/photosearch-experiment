import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class PhotoEventHandler(FileSystemEventHandler):
        """Handle file system events for photos."""
        
        def __init__(self, callback: Callable[[str], None]):
            self.callback = callback

        def on_created(self, event):
            """Called when a file or directory is created."""
            if not event.is_directory:
                # Ignore hidden files
                if event.src_path.split('/')[-1].startswith('.'):
                    return
                
                logger.info(f"Watcher: New file detected: {event.src_path}")
                self.callback(event.src_path)

        def on_moved(self, event):
            """Called when a file or directory is moved or renamed."""
            if not event.is_directory:
                logger.info(f"Watcher: File moved: {event.src_path} -> {event.dest_path}")
                self.callback(event.dest_path)
                # Note: We treat moves as new files for indexing purposes.
                # Deletion handling would require more complex logic.

    def start_watcher(path: str, callback: Callable[[str], None]) -> Optional[Observer]:
        """
        Start monitoring a directory for new files in a background thread.
        
        Args:
            path: Directory path to watch
            callback: Function to call with new file path
            
        Returns:
            Observer instance or None if watchdog not available
        """
        try:
            event_handler = PhotoEventHandler(callback)
            observer = Observer()
            observer.schedule(event_handler, path, recursive=True)
            observer.start()
            logger.info(f"Real-time file watcher started on: {path}")
            return observer
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            return None

except ImportError:
    # Graceful degradation if watchdog is not installed
    logger.warning("Python 'watchdog' library not found. Real-time file monitoring will be disabled.")
    
    def start_watcher(path: str, callback: Callable[[str], None]):
        logger.warning("Cannot start watcher: 'watchdog' library is missing.")
        return None

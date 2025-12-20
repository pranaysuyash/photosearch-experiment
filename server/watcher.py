import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

def start_watcher(path: str, callback: Callable[[str], None]) -> Optional[Any]:
    """Start monitoring a directory for new files in a background thread."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logger.warning("Cannot start watcher: 'watchdog' library is missing.")
        return None

    class PhotoEventHandler(FileSystemEventHandler):
        """Handle file system events for photos."""

        def __init__(self, cb: Callable[[str], None]):
            self.callback = cb

        def on_created(self, event):
            if not event.is_directory:
                if event.src_path.split('/')[-1].startswith('.'):  # ignore hidden files
                    return
                logger.info(f"Watcher: New file detected: {event.src_path}")
                self.callback(event.src_path)

        def on_moved(self, event):
            if not event.is_directory:
                logger.info(f"Watcher: File moved: {event.src_path} -> {event.dest_path}")
                self.callback(event.dest_path)

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

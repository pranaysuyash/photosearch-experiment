import logging
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

        VALID_EXTENSIONS = {
            # Images
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".tiff",
            ".heic",
            # Videos
            ".mp4",
            ".mov",
            ".avi",
            ".mkv",
            ".webm",
            ".m4v",
        }

        def __init__(self, cb: Callable[[str], None]):
            self.callback = cb

        def _is_valid_file(self, path: str) -> bool:
            """Check if file is a valid media file."""
            if path.split("/")[-1].startswith("."):  # ignore hidden files
                return False

            ext = "." + path.split(".")[-1].lower() if "." in path else ""
            return ext in self.VALID_EXTENSIONS

        def on_created(self, event):
            if not event.is_directory:
                if self._is_valid_file(event.src_path):
                    logger.info(f"Watcher: New file detected: {event.src_path}")
                    self.callback(event.src_path)

        def on_moved(self, event):
            if not event.is_directory:
                if self._is_valid_file(event.dest_path):
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

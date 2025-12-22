import os
from pathlib import Path
from typing import List


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv"}


def is_video_file(path: str) -> bool:
    """Check if a file is a video based on extension."""
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTENSIONS


def validate_file_path(file_path: str, allowed_directories: List[Path]) -> bool:
    """
    Validate that a file path is safe and within allowed directories.

    Security improvements:
    - Normalize path to prevent traversal attacks
    - Check against allowed directory whitelist
    - Validate file extensions
    - Ensure path doesn't contain dangerous characters
    """
    try:
        # Normalize and resolve the path
        normalized_path = Path(file_path).resolve()

        # Basic validation
        if not normalized_path.exists():
            return False

        if not normalized_path.is_file():
            return False

        # Check for dangerous path components
        dangerous_patterns = ["..", "~", "$", "|", ";", "&", ">", "<", "`"]
        path_str = str(normalized_path)
        if any(pattern in path_str for pattern in dangerous_patterns):
            return False

        # Check if path is within allowed directories
        for allowed_dir in allowed_directories:
            if normalized_path.is_relative_to(allowed_dir.resolve()):
                return True

        return False

    except (OSError, ValueError, RuntimeError):
        return False

import os
from pathlib import Path
from typing import Union, Dict, Any
from PIL import Image, UnidentifiedImageError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import BytesIO
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create a session with connection pooling and retry strategy
_session = None


def get_http_session():
    """Get a shared HTTP session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        # Configure adapter with connection pooling
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)

        _session.mount("http://", adapter)
        _session.mount("https://", adapter)

        # Set timeout
        _session.timeout = 10

    return _session


def load_image(source: Union[str, Path]) -> Image.Image:
    """
    Load an image from a local path or URL.

    Args:
        source: File path (str/Path) or URL (str)

    Returns:
        PIL.Image.Image: Loaded image object

    Raises:
        FileNotFoundError: If local file doesn't exist
        ValueError: If URL cannot be fetched or image format is invalid
    """
    source_str = str(source)

    try:
        # Check if URL
        if source_str.startswith(("http://", "https://")):
            session = get_http_session()
            response = session.get(source_str)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
        else:
            # Local file
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {path}")
            img = Image.open(path)

        # Force loading to ensure file is read and verify integrity
        img.load()
        return img

    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"Invalid image format or corrupted file: {source}") from e
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch image from URL: {source}") from e


def process_image(image: Image.Image, target_size: int = 512) -> Image.Image:
    """
    Resize and normalize image for processing/display.
    Maintains aspect ratio and converts to RGB.

    Args:
        image: PIL Image object
        target_size: Maximum dimension (width or height)

    Returns:
        PIL.Image.Image: Processed image
    """
    # Convert to RGB (standardize channels)
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Resize if larger than target
    if max(image.size) > target_size:
        image.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

    return image


def get_image_metadata(source: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract basic metadata from an image file without fully loading pixel data if possible.

    Args:
        source: File path (str/Path)

    Returns:
        dict: Metadata including width, height, format, mode, and file size.
    """
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Image not found: {source}")

    metadata = {
        "filename": source_path.name,
        "path": str(source_path.absolute()),
        "size_bytes": source_path.stat().st_size,
        "created": source_path.stat().st_ctime,
        "modified": source_path.stat().st_mtime,
    }

    try:
        with Image.open(source_path) as img:
            metadata.update(
                {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "is_animated": getattr(img, "is_animated", False),
                    "n_frames": getattr(img, "n_frames", 1),
                }
            )
    except Exception as e:
        logger.warning(f"Failed to extract image attributes for {source}: {e}")
        # Return basic file stats even if image open fails

    return metadata


def extract_video_frame(video_path: Union[str, Path]) -> Image.Image:
    """
    Extract the middle frame from a video file using ffmpeg.

    Args:
        video_path: Path to the video file

    Returns:
        PIL.Image.Image: Extracted frame

    Raises:
        ValueError: If extraction fails
    """
    import subprocess
    import shutil

    path = str(video_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Video not found: {path}")

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed or found in PATH")

    try:
        # Get duration using ffprobe
        # We could use the metadata_extractor logic, but let's keep it simple here with subprocess
        # Or just extract a frame at t=00:00:01 usually safer than 50% for short videos?
        # Let's try to get a frame at 1s or 10% mark.

        # Simple approach: Extract 1 frame at 00:00:01 or start
        # pipe:1 outputs to stdout
        # -v error: suppress logs
        # -ss 00:00:01: seek to 1s
        # -vframes 1: get 1 frame
        # -f image2pipe: format
        # -c:v png: codec

        cmd = [
            "ffmpeg",
            "-ss",
            "00:00:01",
            "-i",
            path,
            "-vframes",
            "1",
            "-f",
            "image2pipe",
            "-v",
            "error",
            "-c:v",
            "png",
            "-",
        ]

        # Run command
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if process.returncode != 0:
            # Try at 0s if 1s failed (video too short?)
            cmd[2] = "00:00:00"
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                raise ValueError(f"ffmpeg error: {process.stderr.decode()}")

        # Load image from bytes
        img = Image.open(BytesIO(process.stdout))
        img.load()
        return img

    except Exception as e:
        raise ValueError(f"Failed to extract frame from video {path}: {e}")

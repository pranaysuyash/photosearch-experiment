"""
Comprehensive Metadata Extractor - Extract ALL metadata from any file

This module extracts the MOST comprehensive metadata possible from any file:
- Filesystem metadata (times, size, permissions, owner, extended attributes)
- EXIF data (ALL tags including proprietary MakerNote)
- GPS coordinates (with decimal conversion)
- Image properties (resolution, color space, ICC profiles)
- Video properties (ALL ffprobe fields - format, streams, chapters)
- File integrity (MD5, SHA256 hashes)
- Thumbnails (embedded or generated)
- Calculated/inferred metadata (aspect ratios, file age, time periods, etc.)

Usage:
    # Extract all metadata
    python metadata_extractor.py photo.jpg

    # Save to JSON file
    python metadata_extractor.py photo.jpg --output metadata.json

    # Extract from multiple files
    python metadata_extractor.py photo1.jpg video.mp4 --output-dir metadata/

Author: Antigravity AI Assistant
Date: 2025-12-06
"""

import os
import json
import stat
import hashlib
import logging
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Sequence
import base64

# Image processing
from PIL import Image
import exifread

# Video processing
import ffmpeg

# Audio processing
try:
    import mutagen

    # mutagen.File() auto-detects format, so individual format imports not needed
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

# HEIC/HEIF support
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

# PDF processing
try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

# Extended attributes (macOS/Linux)
try:
    import xattr

    XATTR_AVAILABLE = True
except ImportError:
    XATTR_AVAILABLE = False

# MIME type detection
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def extract_filesystem_metadata(filepath: str) -> Dict[str, Any]:
    """
    Extract comprehensive filesystem metadata.

    Args:
        filepath: Path to file

    Returns:
        Dictionary with all filesystem metadata
    """
    try:
        stat_info = os.stat(filepath)
        Path(filepath)

        # Get file times
        created = datetime.fromtimestamp(
            stat_info.st_birthtime if hasattr(stat_info, "st_birthtime") else stat_info.st_ctime
        )
        modified = datetime.fromtimestamp(stat_info.st_mtime)
        accessed = datetime.fromtimestamp(stat_info.st_atime)
        changed = datetime.fromtimestamp(stat_info.st_ctime)

        # Get permissions
        mode = stat_info.st_mode
        permissions_octal = oct(stat.S_IMODE(mode))
        permissions_human = stat.filemode(mode)

        # Get owner/group info
        try:
            import pwd
            import grp

            owner_name = pwd.getpwuid(stat_info.st_uid).pw_name
            group_name = grp.getgrgid(stat_info.st_gid).gr_name
        except (ImportError, KeyError):
            owner_name = str(stat_info.st_uid)
            group_name = str(stat_info.st_gid)

        # Determine file type
        file_type = "regular"
        if stat.S_ISDIR(mode):
            file_type = "directory"
        elif stat.S_ISLNK(mode):
            file_type = "symlink"
        elif stat.S_ISFIFO(mode):
            file_type = "fifo"
        elif stat.S_ISSOCK(mode):
            file_type = "socket"
        elif stat.S_ISBLK(mode):
            file_type = "block_device"
        elif stat.S_ISCHR(mode):
            file_type = "char_device"

        return {
            "size_bytes": stat_info.st_size,
            "size_human": _human_readable_size(stat_info.st_size),
            "created": created.isoformat(),
            "modified": modified.isoformat(),
            "accessed": accessed.isoformat(),
            "changed": changed.isoformat(),
            "permissions_octal": permissions_octal,
            "permissions_human": permissions_human,
            "owner": owner_name,
            "owner_uid": stat_info.st_uid,
            "group": group_name,
            "group_gid": stat_info.st_gid,
            "inode": stat_info.st_ino,
            "device": stat_info.st_dev,
            "hard_links": stat_info.st_nlink,
            "file_type": file_type,
        }
    except Exception as e:
        logger.error(f"Error extracting filesystem metadata: {e}")
        return {}


def extract_extended_attributes(filepath: str) -> Dict[str, Any]:
    """
    Extract extended attributes (xattr) - macOS/Linux only.

    Args:
        filepath: Path to file

    Returns:
        Dictionary with extended attributes
    """
    if not XATTR_AVAILABLE:
        return {"available": False, "reason": "xattr not available (Windows or not installed)"}

    try:
        attrs = {}
        x = xattr.xattr(filepath)

        for key in x.list():
            try:
                value = x.get(key)
                # Try to decode as string, otherwise keep as bytes
                try:
                    attrs[key.decode() if isinstance(key, bytes) else key] = value.decode()
                except UnicodeDecodeError:
                    attrs[key.decode() if isinstance(key, bytes) else key] = base64.b64encode(value).decode()
            except Exception as e:
                logger.warning(f"Could not read xattr {key}: {e}")

        return {"available": True, "attributes": attrs}
    except Exception as e:
        logger.error(f"Error extracting extended attributes: {e}")
        return {"available": False, "error": str(e)}


def _dms_to_decimal(dms: Sequence[float | int], ref: str) -> Optional[float]:
    """
    Convert GPS coordinates from DMS (degrees, minutes, seconds) to decimal.

    Args:
        dms: Sequence of (degrees, minutes, seconds)
        ref: Reference (N/S for latitude, E/W for longitude)

    Returns:
        Decimal coordinate if conversion succeeds, otherwise None
    """
    try:
        if len(dms) < 3:
            return None

        degrees = float(dms[0])
        minutes = float(dms[1])
        seconds = float(dms[2])

        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

        if ref in ["S", "W"]:
            decimal = -decimal

        return decimal
    except Exception as e:
        logger.error(f"Error converting DMS to decimal: {e}")
        return None


def extract_exif_metadata(filepath: str) -> Optional[Dict[str, Dict[str, str]]]:
    """
    Extract ALL EXIF metadata including MakerNote.

    Args:
        filepath: Path to image file

    Returns:
        Dictionary with all EXIF data
    """
    try:
        # Use exifread for comprehensive EXIF extraction
        with open(filepath, "rb") as f:
            tags = exifread.process_file(f, details=True)

        if not tags:
            return None

        exif_data: Dict[str, Dict[str, str]] = {}

        # Organize tags by category
        for tag, value in tags.items():
            try:
                # Convert value to string
                tag_value = str(value)

                # Organize into categories
                if tag.startswith("Image"):
                    category = "image"
                elif tag.startswith("EXIF"):
                    category = "exif"
                elif tag.startswith("GPS"):
                    category = "gps"
                elif tag.startswith("MakerNote"):
                    category = "makernote"
                elif tag.startswith("Thumbnail"):
                    category = "thumbnail"
                elif tag.startswith("Interoperability"):
                    category = "interoperability"
                else:
                    category = "other"

                if category not in exif_data:
                    exif_data[category] = {}

                # Clean tag name
                clean_tag = tag.split(" ", 1)[1] if " " in tag else tag
                exif_data[category][clean_tag] = tag_value
            except Exception as e:
                logger.warning(f"Could not process EXIF tag {tag}: {e}")

        return exif_data
    except Exception as e:
        logger.error(f"Error extracting EXIF metadata: {e}")
        return None


def extract_gps_metadata(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract GPS metadata from EXIF.

    Args:
        filepath: Path to image file

    Returns:
        Dictionary with GPS data
    """
    try:
        with open(filepath, "rb") as f:
            tags = exifread.process_file(f, details=False)

        gps_data: Dict[str, Any] = {}

        # Extract GPS coordinates
        if "GPS GPSLatitude" in tags and "GPS GPSLatitudeRef" in tags:
            lat_dms = [float(x.num) / float(x.den) for x in tags["GPS GPSLatitude"].values]
            lat_ref = str(tags["GPS GPSLatitudeRef"])
            gps_data["latitude"] = _dms_to_decimal(lat_dms, lat_ref)
            gps_data["latitude_ref"] = lat_ref

        if "GPS GPSLongitude" in tags and "GPS GPSLongitudeRef" in tags:
            lon_dms = [float(x.num) / float(x.den) for x in tags["GPS GPSLongitude"].values]
            lon_ref = str(tags["GPS GPSLongitudeRef"])
            gps_data["longitude"] = _dms_to_decimal(lon_dms, lon_ref)
            gps_data["longitude_ref"] = lon_ref

        # Extract altitude
        if "GPS GPSAltitude" in tags:
            alt = tags["GPS GPSAltitude"]
            gps_data["altitude"] = float(alt.values[0].num) / float(alt.values[0].den)
            if "GPS GPSAltitudeRef" in tags:
                alt_ref = int(str(tags["GPS GPSAltitudeRef"]))
                gps_data["altitude_ref"] = "below_sea_level" if alt_ref == 1 else "above_sea_level"

        # Extract other GPS fields
        gps_fields = {
            "GPS GPSTimeStamp": "timestamp",
            "GPS GPSDateStamp": "datestamp",
            "GPS GPSSpeed": "speed",
            "GPS GPSSpeedRef": "speed_ref",
            "GPS GPSTrack": "track",
            "GPS GPSTrackRef": "track_ref",
            "GPS GPSImgDirection": "image_direction",
            "GPS GPSImgDirectionRef": "image_direction_ref",
            "GPS GPSSatellites": "satellites",
            "GPS GPSDOP": "dop",
            "GPS GPSMapDatum": "map_datum",
            "GPS GPSProcessingMethod": "processing_method",
        }

        for tag, key in gps_fields.items():
            if tag in tags:
                gps_data[key] = str(tags[tag])

        return gps_data if gps_data else None
    except Exception as e:
        logger.error(f"Error extracting GPS metadata: {e}")
        return None


def extract_image_properties(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract image properties using Pillow.

    Args:
        filepath: Path to image file

    Returns:
        Dictionary with image properties
    """
    try:
        with Image.open(filepath) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "dpi": img.info.get("dpi", None),
                "bits_per_pixel": len(img.getbands()) * 8 if hasattr(img, "getbands") else None,
                "color_palette": "yes" if img.palette else "no",
                "animation": hasattr(img, "n_frames") and img.n_frames > 1,
                "frames": img.n_frames if hasattr(img, "n_frames") else 1,
                "icc_profile": "yes" if img.info.get("icc_profile") else "no",
            }
    except Exception as e:
        logger.error(f"Error extracting image properties: {e}")
        return None


def extract_video_properties(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract comprehensive video metadata using ffprobe.

    Args:
        filepath: Path to video file

    Returns:
        Dictionary with all video metadata
    """
    try:
        # Get format information
        probe = ffmpeg.probe(filepath)

        video_data = {
            "format": probe.get("format", {}),
            "streams": probe.get("streams", []),
            "chapters": probe.get("chapters", []),
        }

        return video_data
    except Exception as e:
        logger.error(f"Error extracting video properties: {e}")
        return None


def extract_audio_properties(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract comprehensive audio metadata using mutagen.

    Supports: MP3, FLAC, OGG, WAV, AAC, M4A, MP4 audio

    Args:
        filepath: Path to audio file

    Returns:
        Dictionary with all audio metadata
    """
    if not MUTAGEN_AVAILABLE:
        return {"error": "mutagen not available"}

    try:
        audio = mutagen.File(filepath)
        if audio is None:
            return None

        audio_data: Dict[str, Any] = {
            "format": type(audio).__name__,
            "length_seconds": round(audio.info.length, 2) if hasattr(audio.info, "length") else None,
            "length_human": None,
            "bitrate": getattr(audio.info, "bitrate", None),
            "sample_rate": getattr(audio.info, "sample_rate", None),
            "channels": getattr(audio.info, "channels", None),
            "bits_per_sample": getattr(audio.info, "bits_per_sample", None),
        }

        # Format duration
        length_seconds = audio_data.get("length_seconds")
        if isinstance(length_seconds, (int, float)):
            mins = int(length_seconds // 60)
            secs = int(length_seconds % 60)
            audio_data["length_human"] = f"{mins}:{secs:02d}"

        # Extract tags (ID3, Vorbis Comments, etc.)
        tags: Dict[str, Any] = {}
        if hasattr(audio, "tags") and audio.tags:
            for key, value in audio.tags.items():
                # Clean up tag names and values
                tag_name = str(key).split(":")[0] if ":" in str(key) else str(key)
                if hasattr(value, "text"):
                    tags[tag_name] = str(value.text[0]) if value.text else None
                elif isinstance(value, list):
                    tags[tag_name] = str(value[0]) if value else None
                else:
                    tags[tag_name] = str(value)

        # Common tag mapping
        audio_data["tags"] = {
            "title": tags.get("TIT2") or tags.get("TITLE") or tags.get("title"),
            "artist": tags.get("TPE1") or tags.get("ARTIST") or tags.get("artist"),
            "album": tags.get("TALB") or tags.get("ALBUM") or tags.get("album"),
            "year": tags.get("TDRC") or tags.get("DATE") or tags.get("date"),
            "genre": tags.get("TCON") or tags.get("GENRE") or tags.get("genre"),
            "track_number": tags.get("TRCK") or tags.get("TRACKNUMBER") or tags.get("tracknumber"),
            "composer": tags.get("TCOM") or tags.get("COMPOSER") or tags.get("composer"),
            "album_artist": tags.get("TPE2") or tags.get("ALBUMARTIST") or tags.get("albumartist"),
            "comment": tags.get("COMM") or tags.get("COMMENT") or tags.get("comment"),
            "lyrics": tags.get("USLT") or tags.get("LYRICS"),
        }

        # Check for embedded album art
        audio_data["has_album_art"] = False
        if hasattr(audio, "pictures") and audio.pictures:
            audio_data["has_album_art"] = True
            audio_data["album_art_count"] = len(audio.pictures)
        elif "APIC" in tags or "APIC:" in str(audio.tags.keys()) if audio.tags else False:
            audio_data["has_album_art"] = True

        # Raw tags for completeness
        audio_data["raw_tags"] = tags

        return audio_data
    except Exception as e:
        logger.error(f"Error extracting audio properties: {e}")
        return None


def extract_pdf_properties(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract PDF metadata using pypdf.

    Args:
        filepath: Path to PDF file

    Returns:
        Dictionary with PDF metadata
    """
    if not PYPDF_AVAILABLE:
        return {"error": "pypdf not available"}

    try:
        reader = PdfReader(filepath)

        # Get document info
        info: Dict[str, Any] = dict(reader.metadata or {})

        pdf_data: Dict[str, Any] = {
            "page_count": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "author": info.get("/Author"),
            "creator": info.get("/Creator"),
            "producer": info.get("/Producer"),
            "subject": info.get("/Subject"),
            "title": info.get("/Title"),
            "creation_date": str(info.get("/CreationDate")) if info.get("/CreationDate") else None,
            "modification_date": str(info.get("/ModDate")) if info.get("/ModDate") else None,
            "keywords": info.get("/Keywords"),
        }

        # Get page dimensions from first page
        if reader.pages:
            first_page = reader.pages[0]
            if first_page.mediabox:
                pdf_data["page_width"] = float(first_page.mediabox.width)
                pdf_data["page_height"] = float(first_page.mediabox.height)

        return pdf_data
    except Exception as e:
        logger.error(f"Error extracting PDF properties: {e}")
        return None


def extract_svg_properties(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract SVG metadata by parsing XML.

    Args:
        filepath: Path to SVG file

    Returns:
        Dictionary with SVG metadata
    """
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(filepath)
        root = tree.getroot()

        # Handle namespace

        svg_data: Dict[str, Any] = {
            "width": root.get("width"),
            "height": root.get("height"),
            "viewBox": root.get("viewBox"),
            "version": root.get("version"),
        }

        # Parse viewBox for dimensions if width/height not specified
        if svg_data["viewBox"] and not svg_data["width"]:
            parts = svg_data["viewBox"].split()
            if len(parts) >= 4:
                svg_data["viewBox_width"] = parts[2]
                svg_data["viewBox_height"] = parts[3]

        # Count elements
        svg_data["element_count"] = len(list(root.iter()))

        # Find specific elements
        path_count = len(root.findall(".//{http://www.w3.org/2000/svg}path") or root.findall(".//path"))
        svg_data["path_count"] = path_count

        # Check for embedded styles
        style_elements = root.findall(".//{http://www.w3.org/2000/svg}style") or root.findall(".//style")
        svg_data["has_embedded_styles"] = len(style_elements) > 0

        # Check for scripts (security concern)
        script_elements = root.findall(".//{http://www.w3.org/2000/svg}script") or root.findall(".//script")
        svg_data["has_scripts"] = len(script_elements) > 0

        return svg_data
    except Exception as e:
        logger.error(f"Error extracting SVG properties: {e}")
        return None


def extract_file_hashes(filepath: str) -> Dict[str, str]:
    """
    Calculate file hashes for integrity verification.

    Args:
        filepath: Path to file

    Returns:
        Dictionary with MD5 and SHA256 hashes
    """
    try:
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()

        with open(filepath, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)

        return {"md5": md5_hash.hexdigest(), "sha256": sha256_hash.hexdigest()}
    except Exception as e:
        logger.error(f"Error calculating file hashes: {e}")
        return {}


def extract_thumbnail(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract or generate thumbnail.

    Args:
        filepath: Path to image file

    Returns:
        Dictionary with thumbnail info
    """
    try:
        with Image.open(filepath) as img:
            # Check for embedded thumbnail in EXIF
            has_embedded = hasattr(img, "_getexif") and img._getexif() is not None

            # Generate small thumbnail
            img.thumbnail((160, 160))

            return {"has_embedded": has_embedded, "width": img.width, "height": img.height}
    except Exception as e:
        logger.error(f"Error extracting thumbnail: {e}")
        return None


def _human_readable_size(size_bytes: float) -> str:
    """Convert bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _human_readable_time_delta(delta: timedelta) -> str:
    """Convert timedelta to human-readable format."""
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 2592000:  # 30 days
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 31536000:  # 365 days
        months = seconds // 2592000
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = seconds // 31536000
        return f"{years} year{'s' if years != 1 else ''} ago"


def calculate_inferred_metadata(metadata: Dict[str, Any], current_time: datetime) -> Dict[str, Any]:
    """
    Calculate inferred/derived metadata from extracted data.

    Args:
        metadata: Extracted metadata dictionary
        current_time: Current timestamp for time calculations

    Returns:
        Dictionary with calculated metadata
    """
    calculated: Dict[str, Any] = {}

    try:
        # Image calculations
        if metadata.get("image"):
            img = metadata["image"] or {}
            width = img.get("width")
            height = img.get("height")
            if isinstance(width, (int, float)) and isinstance(height, (int, float)):
                # Aspect ratio
                from math import gcd

                divisor = gcd(int(width), int(height)) or 1
                calculated["aspect_ratio"] = f"{int(width)//divisor}:{int(height)//divisor}"
                calculated["aspect_ratio_decimal"] = round(float(width) / float(height), 3)

                # Megapixels
                calculated["megapixels"] = round((float(width) * float(height)) / 1_000_000, 2)

                # Orientation
                if width > height:
                    calculated["orientation"] = "landscape"
                elif height > width:
                    calculated["orientation"] = "portrait"
                else:
                    calculated["orientation"] = "square"

        # Video calculations
        if metadata.get("video") and metadata["video"].get("format"):
            fmt = metadata["video"]["format"] or {}
            duration_value = fmt.get("duration")
            duration = float(duration_value) if duration_value is not None else None
            if duration:
                calculated["duration_human"] = f"{int(duration // 60)}:{int(duration % 60):02d}"

                # Size per second
                size_bytes = metadata.get("filesystem", {}).get("size_bytes")
                if isinstance(size_bytes, (int, float)):
                    calculated["size_per_second"] = _human_readable_size(size_bytes / duration)

        # Time-based calculations
        if metadata.get("filesystem"):
            fs = metadata["filesystem"]

            if fs.get("created"):
                created = datetime.fromisoformat(fs["created"])
                age_delta = current_time - created
                calculated["file_age"] = {
                    "days": age_delta.days,
                    "hours": int(age_delta.total_seconds() // 3600),
                    "human_readable": _human_readable_time_delta(age_delta),
                }

            if fs.get("modified"):
                modified = datetime.fromisoformat(fs["modified"])
                mod_delta = current_time - modified
                calculated["time_since_modified"] = {
                    "days": mod_delta.days,
                    "hours": int(mod_delta.total_seconds() // 3600),
                    "human_readable": _human_readable_time_delta(mod_delta),
                }

            if fs.get("accessed"):
                accessed = datetime.fromisoformat(fs["accessed"])
                acc_delta = current_time - accessed
                calculated["time_since_accessed"] = {
                    "days": acc_delta.days,
                    "hours": int(acc_delta.total_seconds() // 3600),
                    "human_readable": _human_readable_time_delta(acc_delta),
                }

    except Exception as e:
        logger.error(f"Error calculating inferred metadata: {e}")

    return calculated


def extract_all_metadata(filepath: str) -> Dict[str, Any]:
    """
    Extract ALL metadata from a file.

    Args:
        filepath: Path to file

    Returns:
        Complete metadata dictionary
    """
    current_time = datetime.now()

    # Detect MIME type
    mime_type = mimetypes.guess_type(filepath)[0]
    if MAGIC_AVAILABLE:
        try:
            mime_type = magic.from_file(filepath, mime=True)
        except:
            pass

    metadata: Dict[str, Any] = {
        "file": {
            "path": str(Path(filepath).absolute()),
            "name": Path(filepath).name,
            "extension": Path(filepath).suffix,
            "mime_type": mime_type,
        },
        "filesystem": extract_filesystem_metadata(filepath),
        "extended_attributes": extract_extended_attributes(filepath),
        "image": None,
        "exif": None,
        "gps": None,
        "video": None,
        "audio": None,
        "pdf": None,
        "svg": None,
        "hashes": extract_file_hashes(filepath),
        "thumbnail": None,
        "calculated": {},
    }

    # Get file extension for additional checks
    ext = Path(filepath).suffix.lower()

    # Extract image-specific metadata
    if mime_type and mime_type.startswith("image"):
        metadata["image"] = extract_image_properties(filepath)
        metadata["exif"] = extract_exif_metadata(filepath)
        metadata["gps"] = extract_gps_metadata(filepath)
        metadata["thumbnail"] = extract_thumbnail(filepath)

    # Extract video-specific metadata
    elif mime_type and mime_type.startswith("video"):
        metadata["video"] = extract_video_properties(filepath)

    # Extract audio-specific metadata
    elif mime_type and mime_type.startswith("audio"):
        metadata["audio"] = extract_audio_properties(filepath)

    # Also check by extension for audio files that may have wrong MIME type
    elif ext in [".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac", ".wma", ".opus"]:
        metadata["audio"] = extract_audio_properties(filepath)

    # Extract PDF metadata
    elif mime_type == "application/pdf" or ext == ".pdf":
        metadata["pdf"] = extract_pdf_properties(filepath)

    # Extract SVG metadata
    elif mime_type == "image/svg+xml" or ext == ".svg":
        metadata["svg"] = extract_svg_properties(filepath)

    # Calculate inferred metadata
    metadata["calculated"] = calculate_inferred_metadata(metadata, current_time)

    return metadata


def save_metadata_json(metadata: Dict[str, Any], output_file: str):
    """
    Save metadata to JSON file.

    Args:
        metadata: Metadata dictionary
        output_file: Output file path
    """
    try:
        # Create output directory if needed
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Metadata saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")


def main():
    """Main CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Comprehensive Metadata Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract metadata from single file
  python metadata_extractor.py photo.jpg

  # Save to JSON file
  python metadata_extractor.py photo.jpg --output metadata.json

  # Extract from multiple files
  python metadata_extractor.py photo1.jpg video.mp4

  # Batch process to directory
  python metadata_extractor.py *.jpg --output-dir metadata/
        """,
    )

    parser.add_argument("files", nargs="+", help="File(s) to extract metadata from")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--output-dir", "-d", help="Output directory for batch processing")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty print JSON")

    args = parser.parse_args()

    # Process files
    for filepath in args.files:
        # Convert to Path object for better handling
        file_path = Path(filepath).expanduser().resolve()

        # Check if file exists
        if not file_path.exists():
            logger.error(f"File not found: {filepath}")
            logger.debug(f"Tried absolute path: {file_path}")
            continue

        if not file_path.is_file():
            logger.error(f"Not a file: {filepath}")
            continue

        logger.info(f"Extracting metadata from: {filepath}")

        try:
            metadata = extract_all_metadata(str(file_path))

            # Determine output
            if args.output:
                save_metadata_json(metadata, args.output)
            elif args.output_dir:
                output_file = Path(args.output_dir) / f"{file_path.stem}_metadata.json"
                save_metadata_json(metadata, str(output_file))
            else:
                # Print to console
                print(json.dumps(metadata, indent=2 if args.pretty else None, default=str))
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            continue


if __name__ == "__main__":
    main()

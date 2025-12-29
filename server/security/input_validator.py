"""
Input Validation and Sanitization Framework

Provides comprehensive input validation and sanitization to prevent
XXE attacks, injection attacks, and other security vulnerabilities.
"""

import re
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
import bleach
from pydantic import BaseModel, validator, Field
from defusedxml import ElementTree as DefusedET
import magic
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""

    pass


class SecureFileValidator:
    """
    Secure file validation and sanitization.

    Prevents XXE attacks, validates file types, and sanitizes content.
    """

    # Allowed file extensions for different categories
    ALLOWED_IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".heic",
        ".heif",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
    }

    ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv", ".m4v"}

    ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".json"}

    # Dangerous file extensions that should never be allowed
    DANGEROUS_EXTENSIONS = {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".pif",
        ".scr",
        ".vbs",
        ".js",
        ".jar",
        ".app",
        ".deb",
        ".pkg",
        ".dmg",
        ".iso",
    }

    # Maximum file sizes (in bytes)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self):
        self.magic = magic.Magic(mime=True)

    def validate_file(self, file_path: Path, expected_type: str = "auto") -> Dict[str, Any]:
        """
        Validate a file for security and type correctness.

        Args:
            file_path: Path to the file to validate
            expected_type: Expected file type ('image', 'video', 'document', 'auto')

        Returns:
            Dictionary with validation results

        Raises:
            ValidationError: If file fails validation
        """
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")

        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValidationError("File is empty")

        # Check file extension
        extension = file_path.suffix.lower()
        if extension in self.DANGEROUS_EXTENSIONS:
            raise ValidationError(f"Dangerous file extension: {extension}")

        # Detect MIME type
        try:
            mime_type = self.magic.from_file(str(file_path))
        except Exception as e:
            logger.warning(f"Could not detect MIME type for {file_path}: {e}")
            mime_type = mimetypes.guess_type(str(file_path))[0] or "unknown"

        # Validate based on expected type
        file_category = self._categorize_file(extension, mime_type)

        if expected_type != "auto" and file_category != expected_type:
            raise ValidationError(f"Expected {expected_type} file, got {file_category}")

        # Check file size limits
        self._validate_file_size(file_size, file_category)

        # Perform content validation
        content_validation = self._validate_file_content(file_path, file_category, mime_type)

        return {
            "valid": True,
            "file_path": str(file_path),
            "file_size": file_size,
            "extension": extension,
            "mime_type": mime_type,
            "category": file_category,
            "content_validation": content_validation,
        }

    def _categorize_file(self, extension: str, mime_type: str) -> str:
        """Categorize file based on extension and MIME type"""
        if extension in self.ALLOWED_IMAGE_EXTENSIONS or mime_type.startswith("image/"):
            return "image"
        elif extension in self.ALLOWED_VIDEO_EXTENSIONS or mime_type.startswith("video/"):
            return "video"
        elif extension in self.ALLOWED_DOCUMENT_EXTENSIONS or mime_type.startswith("text/"):
            return "document"
        else:
            return "unknown"

    def _validate_file_size(self, file_size: int, category: str) -> None:
        """Validate file size based on category"""
        limits = {"image": self.MAX_IMAGE_SIZE, "video": self.MAX_VIDEO_SIZE, "document": self.MAX_DOCUMENT_SIZE}

        max_size = limits.get(category, self.MAX_DOCUMENT_SIZE)
        if file_size > max_size:
            raise ValidationError(f"File too large: {file_size} bytes (max: {max_size})")

    def _validate_file_content(self, file_path: Path, category: str, mime_type: str) -> Dict[str, Any]:
        """Validate file content for security issues"""
        validation_result = {"safe": True, "issues": []}

        try:
            if category == "image":
                validation_result.update(self._validate_image_content(file_path))
            elif category == "document" and mime_type == "application/pdf":
                validation_result.update(self._validate_pdf_content(file_path))
            elif mime_type in ["image/svg+xml", "application/svg+xml"]:
                validation_result.update(self._validate_svg_content(file_path))
        except Exception as e:
            logger.warning(f"Content validation failed for {file_path}: {e}")
            validation_result["issues"].append(f"Content validation error: {e}")

        return validation_result

    def _validate_image_content(self, file_path: Path) -> Dict[str, Any]:
        """Validate image file content"""
        try:
            from PIL import Image

            with Image.open(file_path) as img:
                # Check for reasonable image dimensions
                width, height = img.size
                if width > 50000 or height > 50000:
                    return {"safe": False, "issues": ["Image dimensions too large"]}

                # Check for suspicious EXIF data
                exif_issues = self._check_exif_data(img)

                return {"safe": len(exif_issues) == 0, "issues": exif_issues}
        except Exception as e:
            return {"safe": False, "issues": [f"Image validation failed: {e}"]}

    def _validate_pdf_content(self, file_path: Path) -> Dict[str, Any]:
        """Validate PDF file content"""
        # Basic PDF validation - check for PDF header
        try:
            with open(file_path, "rb") as f:
                header = f.read(8)
                if not header.startswith(b"%PDF-"):
                    return {"safe": False, "issues": ["Invalid PDF header"]}

            return {"safe": True, "issues": []}
        except Exception as e:
            return {"safe": False, "issues": [f"PDF validation failed: {e}"]}

    def _validate_svg_content(self, file_path: Path) -> Dict[str, Any]:
        """Validate SVG content for XXE and other attacks"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                svg_content = f.read()

            # Use defusedxml to prevent XXE attacks
            try:
                DefusedET.fromstring(svg_content)
            except DefusedET.ParseError as e:
                return {"safe": False, "issues": [f"SVG parsing failed: {e}"]}

            # Check for dangerous elements
            dangerous_patterns = [
                r"<script[^>]*>",
                r"javascript:",
                r"data:text/html",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>",
            ]

            issues = []
            for pattern in dangerous_patterns:
                if re.search(pattern, svg_content, re.IGNORECASE):
                    issues.append(f"Dangerous SVG content detected: {pattern}")

            return {"safe": len(issues) == 0, "issues": issues}

        except Exception as e:
            return {"safe": False, "issues": [f"SVG validation failed: {e}"]}

    def _check_exif_data(self, image) -> List[str]:
        """Check EXIF data for suspicious content"""
        issues = []

        try:
            exif = image.getexif()
            if exif:
                # Check for suspicious EXIF fields
                dangerous_fields = ["MakerNote", "UserComment", "ImageDescription"]
                for field in dangerous_fields:
                    if field in exif:
                        # Check for script-like content
                        value = str(exif[field])
                        if any(keyword in value.lower() for keyword in ["script", "javascript", "vbscript"]):
                            issues.append(f"Suspicious EXIF data in {field}")
        except Exception:
            # EXIF parsing failed, but this is not necessarily dangerous
            pass

        return issues


class SecureTextValidator:
    """
    Secure text input validation and sanitization.
    """

    # HTML tags allowed in user input
    ALLOWED_HTML_TAGS = ["b", "i", "u", "em", "strong", "p", "br", "ul", "ol", "li"]

    # HTML attributes allowed in user input
    ALLOWED_HTML_ATTRIBUTES = {
        "*": ["class"],
        "a": ["href", "title"],
    }

    def __init__(self):
        self.bleach_cleaner = bleach.Cleaner(
            tags=self.ALLOWED_HTML_TAGS, attributes=self.ALLOWED_HTML_ATTRIBUTES, strip=True
        )

    def sanitize_html(self, html_content: str) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.

        Args:
            html_content: Raw HTML content

        Returns:
            Sanitized HTML content
        """
        return self.bleach_cleaner.clean(html_content)

    def validate_search_query(self, query: str) -> str:
        """
        Validate and sanitize search query.

        Args:
            query: Raw search query

        Returns:
            Sanitized search query

        Raises:
            ValidationError: If query is invalid
        """
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")

        # Limit query length
        if len(query) > 1000:
            raise ValidationError("Search query too long (max 1000 characters)")

        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';\\]', "", query.strip())

        # Check for SQL injection patterns
        sql_patterns = [
            r"\b(union|select|insert|update|delete|drop|create|alter)\b",
            r"--",
            r"/\*.*\*/",
            r"\bor\s+\d+\s*=\s*\d+",
            r"\band\s+\d+\s*=\s*\d+",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValidationError("Invalid characters in search query")

        return sanitized

    def validate_user_input(self, input_text: str, max_length: int = 500) -> str:
        """
        Validate and sanitize general user input.

        Args:
            input_text: Raw user input
            max_length: Maximum allowed length

        Returns:
            Sanitized user input

        Raises:
            ValidationError: If input is invalid
        """
        if not input_text:
            return ""

        if len(input_text) > max_length:
            raise ValidationError(f"Input too long (max {max_length} characters)")

        # Sanitize HTML
        sanitized = self.sanitize_html(input_text)

        # Remove null bytes and control characters
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        return sanitized.strip()


# Pydantic models for API validation
class SecureSearchRequest(BaseModel):
    """Secure search request model"""

    query: str = Field(..., min_length=1, max_length=1000)
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    @validator("query")
    def validate_query(cls, v):
        validator = SecureTextValidator()
        return validator.validate_search_query(v)

    @validator("filters")
    def validate_filters(cls, v):
        if v is None:
            return v

        # Validate filter keys and values
        allowed_filters = {
            "date_from",
            "date_to",
            "location",
            "camera",
            "person_id",
            "tag",
            "rating",
            "file_type",
            "has_faces",
            "has_location",
        }

        for key in v.keys():
            if key not in allowed_filters:
                raise ValueError(f"Invalid filter key: {key}")

        return v


class SecureFileUploadRequest(BaseModel):
    """Secure file upload request model"""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    file_size: int = Field(..., ge=1, le=500 * 1024 * 1024)  # Max 500MB

    @validator("filename")
    def validate_filename(cls, v):
        # Remove path traversal attempts
        filename = Path(v).name

        # Check for dangerous extensions
        validator = SecureFileValidator()
        extension = Path(filename).suffix.lower()

        if extension in validator.DANGEROUS_EXTENSIONS:
            raise ValueError(f"File type not allowed: {extension}")

        # Sanitize filename
        sanitized = re.sub(r"[^\w\-_\.]", "_", filename)

        return sanitized

    @validator("content_type")
    def validate_content_type(cls, v):
        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/tiff",
            "image/webp",
            "image/heic",
            "image/heif",
            "video/mp4",
            "video/avi",
            "video/mov",
            "video/wmv",
            "video/webm",
            "application/pdf",
            "text/plain",
        ]

        if v not in allowed_types:
            raise ValueError(f"Content type not allowed: {v}")

        return v


# Global validator instances
file_validator = SecureFileValidator()
text_validator = SecureTextValidator()


def validate_file_upload(file_path: Path, expected_type: str = "auto") -> Dict[str, Any]:
    """Convenience function for file validation"""
    return file_validator.validate_file(file_path, expected_type)


def sanitize_user_input(input_text: str, max_length: int = 500) -> str:
    """Convenience function for text sanitization"""
    return text_validator.validate_user_input(input_text, max_length)


def sanitize_search_query(query: str) -> str:
    """Convenience function for search query sanitization"""
    return text_validator.validate_search_query(query)

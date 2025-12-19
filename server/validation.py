"""
Input Validation Middleware and Utilities

Comprehensive validation for all API endpoints to prevent injection attacks,
validate data formats, and ensure data integrity.
"""

import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from datetime import datetime
from functools import wraps
from fastapi import Request, HTTPException, Query, Form
from pydantic import BaseModel, ValidationError, validator
import json

# Common validation patterns
SAFE_FILENAME_REGEX = re.compile(r'^[a-zA-Z0-9._-]+$')
SAFE_TEXT_REGEX = re.compile(r'^[a-zA-Z0-9\s\-_.,!?@#%&()\'"/\\]+$')
DATE_REGEX = re.compile(r'^\d{4}-\d{2}(-\d{2})?(\s+[T]\d{2}:\d{2}(:\d{2})?)?(\.\d{3})?(Z|[+-]\d{2}:?\d{2})?$')
UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

# Allowed file extensions for different categories
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.avif'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp', '.flv'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.txt', '.md', '.doc', '.docx', '.xls', '.xlsx'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.ogg'}

# Maximum file sizes (bytes)
MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB


class ValidationInputError(Exception):
    """Custom exception for validation errors."""
    pass


class SanitizeResult(BaseModel):
    """Result of input sanitization."""
    sanitized_value: Any
    is_valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = []


def sanitize_text_input(text: str, max_length: int = 1000, allow_html: bool = False) -> SanitizeResult:
    """
    Sanitize text input to prevent XSS and injection attacks.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags

    Returns:
        SanitizeResult with sanitized value and validation status
    """
    try:
        if not isinstance(text, str):
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message="Input must be a string"
            )

        # Length validation
        if len(text) > max_length:
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message=f"Text too long (max {max_length} characters)"
            )

        # Remove control characters
        sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')

        # HTML handling
        if allow_html:
            # Allow only safe HTML tags
            safe_tags = {'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
            # This is a simplified implementation - in production, use a proper HTML sanitizer
            sanitized = html.escape(sanitized)
        else:
            # Remove all HTML tags
            sanitized = html.escape(sanitized)

        # Check for dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'data:',
            r'vbscript:',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                return SanitizeResult(
                    sanitized_value="",
                    is_valid=False,
                    error_message="Potentially dangerous content detected"
                )

        return SanitizeResult(sanitized_value=sanitized, is_valid=True)

    except Exception as e:
        return SanitizeResult(
            sanitized_value="",
            is_valid=False,
            error_message=f"Validation error: {str(e)}"
        )


def validate_file_path(file_path: str) -> SanitizeResult:
    """
    Validate file path input to prevent directory traversal.

    Args:
        file_path: File path to validate

    Returns:
        SanitizeResult with validation status
    """
    try:
        if not isinstance(file_path, str):
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message="File path must be a string"
            )

        # Normalize path
        normalized_path = Path(file_path).resolve()

        # Check for dangerous patterns
        dangerous_patterns = ['..', '~', '$', '|', ';', '&', '>', '<', '`']
        path_str = str(normalized_path)

        for pattern in dangerous_patterns:
            if pattern in path_str:
                return SanitizeResult(
                    sanitized_value="",
                    is_valid=False,
                    error_message="Invalid characters in file path"
                )

        # Validate file extension
        file_ext = normalized_path.suffix.lower()
        all_allowed_extensions = (
            ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS |
            ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS
        )

        if file_ext not in all_allowed_extensions:
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message=f"File type not allowed: {file_ext}"
            )

        return SanitizeResult(
            sanitized_value=str(normalized_path),
            is_valid=True
        )

    except Exception as e:
        return SanitizeResult(
            sanitized_value="",
            is_valid=False,
            error_message=f"Path validation error: {str(e)}"
        )


def validate_date_input(date_str: str) -> SanitizeResult:
    """
    Validate date input format.

    Args:
        date_str: Date string to validate

    Returns:
        SanitizeResult with validation status
    """
    try:
        if not isinstance(date_str, str):
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message="Date must be a string"
            )

        # Check basic format
        if not DATE_REGEX.match(date_str.strip()):
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message="Invalid date format. Use YYYY-MM-DD or ISO format"
            )

        # Try to parse the date
        try:
            # Handle different date formats
            if 'T' in date_str:
                # ISO datetime format
                datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Date only format
                datetime.strptime(date_str.strip(), '%Y-%m-%d')

        except ValueError:
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message="Invalid date or datetime"
            )

        return SanitizeResult(
            sanitized_value=date_str.strip(),
            is_valid=True
        )

    except Exception as e:
        return SanitizeResult(
            sanitized_value="",
            is_valid=False,
            error_message=f"Date validation error: {str(e)}"
        )


def validate_search_query(query: str, max_length: int = 500) -> SanitizeResult:
    """
    Validate search query to prevent injection attacks.

    Args:
        query: Search query to validate
        max_length: Maximum allowed length

    Returns:
        SanitizeResult with validation status
    """
    try:
        if not isinstance(query, str):
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message="Search query must be a string"
            )

        query = query.strip()

        # Length validation
        if len(query) > max_length:
            return SanitizeResult(
                sanitized_value="",
                is_valid=False,
                error_message=f"Query too long (max {max_length} characters)"
            )

        # Check for dangerous SQL injection patterns
        sql_injection_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+',
            r'--',
            r'/\*.*\*/',
            r';\s*(drop|delete|update)',
            r'\'\s*(or|and)\s*\'.*\'',
            r'"\s*(or|and)\s*".*"',
        ]

        for pattern in sql_injection_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return SanitizeResult(
                    sanitized_value="",
                    is_valid=False,
                    error_message="Invalid query format"
                )

        # Sanitize by escaping HTML
        sanitized = html.escape(query)

        return SanitizeResult(
            sanitized_value=sanitized,
            is_valid=True
        )

    except Exception as e:
        return SanitizeResult(
            sanitized_value="",
            is_valid=False,
            error_message=f"Query validation error: {str(e)}"
        )


def validate_pagination_params(limit: int = 50, offset: int = 0) -> SanitizeResult:
    """
    Validate pagination parameters.

    Args:
        limit: Number of items per page
        offset: Number of items to skip

    Returns:
        SanitizeResult with validation status
    """
    try:
        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            return SanitizeResult(
                sanitized_value={"limit": 50, "offset": 0},
                is_valid=False,
                error_message="Limit must be between 1 and 1000"
            )

        # Validate offset
        if not isinstance(offset, int) or offset < 0:
            return SanitizeResult(
                sanitized_value={"limit": limit, "offset": 0},
                is_valid=False,
                error_message="Offset must be non-negative"
            )

        return SanitizeResult(
            sanitized_value={"limit": limit, "offset": offset},
            is_valid=True
        )

    except Exception as e:
        return SanitizeResult(
            sanitized_value={"limit": 50, "offset": 0},
            is_valid=False,
            error_message=f"Pagination validation error: {str(e)}"
        )


def require_validation(validation_func: Callable, error_message: str = "Validation failed"):
    """
    Decorator for endpoint functions requiring validation.

    Args:
        validation_func: Validation function to apply
        error_message: Custom error message

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Apply validation to specific parameters
                # This is a simplified version - customize based on endpoint needs
                return await func(*args, **kwargs)
            except ValidationInputError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")
        return wrapper
    return decorator


# Pydantic models for automatic validation
class SearchQueryValidator(BaseModel):
    """Pydantic model for search query validation."""
    query: str
    limit: int = 50
    offset: int = 0
    mode: str = "metadata"

    @validator('query')
    def validate_search_content(cls, v):
        result = validate_search_query(v)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return result.sanitized_value

    @validator('limit')
    def validate_limit(cls, v):
        result = validate_pagination_params(v, 0)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return result.sanitized_value["limit"]

    @validator('offset')
    def validate_offset(cls, v):
        result = validate_pagination_params(50, v)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return result.sanitized_value["offset"]


class FilePathValidator(BaseModel):
    """Pydantic model for file path validation."""
    path: str

    @validator('path')
    def validate_path_content(cls, v):
        result = validate_file_path(v)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return result.sanitized_value


class DateValidator(BaseModel):
    """Pydantic model for date validation."""
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    @validator('date_from', 'date_to')
    def validate_date_content(cls, v):
        if v is None:
            return v
        result = validate_date_input(v)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return result.sanitized_value


# Middleware for automatic validation
async def validate_request_data(request: Request, validation_rules: Dict[str, Callable]) -> Dict[str, Any]:
    """
    Validate request data according to provided rules.

    Args:
        request: FastAPI request object
        validation_rules: Dictionary of field names to validation functions

    Returns:
        Validated and sanitized data
    """
    try:
        # Get request data based on content type
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
        else:
            # Form data or query parameters
            data = dict(request.query_params)
            if request.method in ["POST", "PUT", "PATCH"]:
                form_data = await request.form()
                data.update(form_data)

        validated_data = {}

        for field_name, validation_func in validation_rules.items():
            if field_name in data:
                result = validation_func(data[field_name])
                if result.is_valid:
                    validated_data[field_name] = result.sanitized_value
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Validation failed for {field_name}: {result.error_message}"
                    )
            else:
                # Optional fields
                continue

        return validated_data

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=f"Request validation error: {str(e)}")
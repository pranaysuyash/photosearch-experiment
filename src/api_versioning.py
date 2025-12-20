"""
API Versioning System for Photo Search Application

This module provides:
1. API version management
2. Version compatibility tracking
3. Standardized response formats
4. API documentation generation
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    # Future versions can be added here


class APIEndpointInfo(BaseModel):
    """Information about an API endpoint."""
    path: str
    method: str
    summary: str
    description: str
    version: APIVersion


class APIVersionManager:
    """Manages API versions and provides version-related utilities."""

    def __init__(self):
        self.current_version = APIVersion.V1
        self.endpoints: List[APIEndpointInfo] = []

    def register_endpoint(self, path: str, method: str, summary: str, description: str):
        """Register an API endpoint for documentation purposes."""
        endpoint_info = APIEndpointInfo(
            path=path,
            method=method,
            summary=summary,
            description=description,
            version=self.current_version
        )
        self.endpoints.append(endpoint_info)

    def get_api_schema(self) -> Dict[str, Any]:
        """Get the current API schema for documentation."""
        return {
            "version": self.current_version.value,
            "endpoints": [
                {
                    "path": ep.path,
                    "method": ep.method,
                    "summary": ep.summary,
                    "description": ep.description
                }
                for ep in self.endpoints
            ]
        }


class StandardResponse(BaseModel):
    """Standard API response format."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
    version: str = APIVersion.V1.value
    timestamp: float = time.time()


class APIResponseHandler:
    """Provides standardized API responses."""

    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """Create a success response."""
        return StandardResponse(
            success=True,
            data=data,
            message=message
        ).dict()

    @staticmethod
    def error(message: str, error_code: str | None = None) -> Dict[str, Any]:
        """Create an error response."""
        return StandardResponse(
            success=False,
            message=message,
            error=error_code or message
        ).dict()


# Global instance
api_version_manager = APIVersionManager()

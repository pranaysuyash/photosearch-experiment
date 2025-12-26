from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, computed_field


class Settings(BaseSettings):
    # App Info
    APP_NAME: str = "Living Museum API"
    ENV: str = "development"
    DEBUG: bool = True

    # API Configuration
    API_V1_STR: str = "/api/v1"

    # CORS
    # In production, this should be a list of allowed origins
    CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "tauri://localhost",
    ]

    # Model Configuration
    EMBEDDING_MODEL: str = "clip-ViT-B-32"

    # Face detection / clustering
    # Comma-separated preference list. Only InsightFace currently supports embeddings (clustering).
    # Example: "insightface,mediapipe,yolo"
    FACE_BACKENDS: str = "insightface"

    # Optional: local path to Ultralytics YOLO face weights (.pt) when using the "yolo" backend.
    # Kept optional so the server can start without heavyweight deps.
    FACE_YOLO_WEIGHTS: str | None = None

    # Optional: embedding backend preference list for clustering when detection backends
    # do not provide embeddings. Example: "insightface,clip,remote".
    FACE_EMBEDDING_BACKENDS: str = "insightface,clip,remote"
    FACE_CLIP_EMBEDDING_MODEL: str = "clip-ViT-B-32"

    # Optional: remote face detection service (HTTP JSON).
    FACE_REMOTE_DETECT_URL: str | None = None
    FACE_REMOTE_DETECT_API_KEY: str | None = None
    FACE_REMOTE_DETECT_TIMEOUT: float = 10.0
    FACE_REMOTE_DETECT_EMBEDDINGS: bool = False

    # Optional: remote face embedding service (HTTP JSON).
    FACE_REMOTE_EMBEDDING_URL: str | None = None
    FACE_REMOTE_EMBEDDING_API_KEY: str | None = None
    FACE_REMOTE_EMBEDDING_TIMEOUT: float = 10.0

    # Path to face clustering database (SQLite)
    FACE_CLUSTERS_DB_PATH: str = str(
        # Store face DB at repo root so all components share the same file.
        Path(__file__).resolve().parent.parent / "face_clusters.db"
    )

    @computed_field
    def DEVICE(self) -> str:
        """Auto-detect most capable device available."""
        try:
            import torch

            if torch.backends.mps.is_available():
                return "mps"
            elif torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    # Paths
    # Default to a 'media' folder in the project root if not specified
    # We use a computed field or just a property to resolve relative paths if needed
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # Media storage roots (defaults are inside project for dev)
    MEDIA_DIR: Path = Path(__file__).resolve().parent.parent / "media"
    VECTOR_STORE_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "vector_store"

    # JWT Auth for cloud deployments
    JWT_AUTH_ENABLED: bool = False
    JWT_SECRET: str | None = None
    JWT_ALGO: str = "HS256"
    JWT_ISSUER: str | None = None

    # Allow admin unmasking via API when enabled (audited)
    ACCESS_LOG_UNMASK_ENABLED: bool = False

    # Signed URL / tokenized thumbnail access (for cloud/web deployments)
    SIGNED_URL_ENABLED: bool = False
    SIGNED_URL_SECRET: str | None = None  # Must be set in production
    SIGNED_URL_TTL_SECONDS: int = 3600

    # Image token issuer key (used for dev/issuer-key auth to issue image tokens)
    IMAGE_TOKEN_ISSUER_KEY: str | None = None

    # Sandbox controls for serving local files over HTTP
    SANDBOX_STRICT: bool = True  # Enable sandbox by default for security

    # Access log privacy controls
    ACCESS_LOG_MASKING: bool = True
    ACCESS_LOG_HASH_SALT: str | None = None  # Generate random salt if None

    # Basic rate limiting (server/main.py uses a simple in-memory counter)
    RATE_LIMIT_ENABLED: bool = True  # Enable rate limiting by default
    RATE_LIMIT_REQS_PER_MIN: int = 300  # Higher limit for development

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


settings = Settings()


def validate_production_config():
    """Validate critical security settings for production deployment."""
    if settings.ENV == "production":
        issues = []

        # Check for secure secrets
        if not settings.JWT_SECRET and settings.JWT_AUTH_ENABLED:
            issues.append("JWT_SECRET must be set in production")

        if not settings.SIGNED_URL_SECRET and settings.SIGNED_URL_ENABLED:
            issues.append("SIGNED_URL_SECRET must be set in production")

        # Check for required security features
        if not settings.RATE_LIMIT_ENABLED:
            issues.append("RATE_LIMIT_ENABLED should be True in production")

        if not settings.ACCESS_LOG_MASKING:
            issues.append("ACCESS_LOG_MASKING should be True in production")

        if not settings.SANDBOX_STRICT:
            issues.append("SANDBOX_STRICT should be True in production")

        # Generate secure salt if not provided
        if not settings.ACCESS_LOG_HASH_SALT:
            import secrets
            import warnings

            warnings.warn("ACCESS_LOG_HASH_SALT not set, using auto-generated value")
            settings.ACCESS_LOG_HASH_SALT = secrets.token_urlsafe(32)

        if issues:
            raise ValueError(f"Production configuration security issues detected: {'; '.join(issues)}")

    return True


# Validate configuration on import
try:
    validate_production_config()
except ValueError as e:
    import warnings

    warnings.warn(f"Configuration validation warning: {e}")
    # Don't fail startup for configuration issues in development

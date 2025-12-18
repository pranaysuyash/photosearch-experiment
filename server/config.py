import os
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
    SIGNED_URL_SECRET: str = "dev_signed_url_secret_change_me"
    SIGNED_URL_TTL_SECONDS: int = 3600

    # Image token issuer key (used for dev/issuer-key auth to issue image tokens)
    IMAGE_TOKEN_ISSUER_KEY: str | None = None

    # Sandbox controls for serving local files over HTTP
    SANDBOX_STRICT: bool = False

    # Access log privacy controls
    ACCESS_LOG_MASKING: bool = True
    ACCESS_LOG_HASH_SALT: str = "dev_salt"

    # Basic rate limiting (server/main.py uses a simple in-memory counter)
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQS_PER_MIN: int = 120

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()

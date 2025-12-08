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
    
    @computed_field
    def MEDIA_DIR(self) -> Path:
        """Resolve media directory relative to base or use absolute path from env."""
        return self.BASE_DIR / "media"

    @computed_field
    def VECTOR_STORE_PATH(self) -> Path:
        """Path to the LanceDB vector store."""
        # Default to 'data/vector_store' in project root
        return self.BASE_DIR / "data" / "vector_store"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()

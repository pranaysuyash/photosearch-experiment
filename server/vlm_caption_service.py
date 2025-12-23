"""
VLM (Vision-Language Model) Caption Service

Provides AI-generated captions for photos using various VLM backends.
Currently supports Gemini Vision as the primary provider.

IMPORTANT: Captions are AI-generated and may be inaccurate.
Always display with appropriate disclaimers.
"""

import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# VLM Provider Configurations
VLM_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini Vision",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "default_model": "gemini-2.0-flash-exp",
        "requires_api_key": "GEMINI_API_KEY",
        "cost_per_1k_tokens": 0.00,  # Flash is free tier eligible
    },
    "openai": {
        "name": "OpenAI GPT-4 Vision",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "default_model": "gpt-4o-mini",
        "requires_api_key": "OPENAI_API_KEY",
        "cost_per_1k_tokens": 0.005,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "models": ["llava", "llava:13b", "bakllava"],
        "default_model": "llava",
        "requires_api_key": None,  # Local, no API key
        "cost_per_1k_tokens": 0.00,
    },
}

# Caption generation prompt template
CAPTION_PROMPT = """Describe this image in 1-2 sentences. Focus on:
- Main subjects (people, objects, animals)
- Setting/location
- Key activities or emotions visible (describe visual cues only, not inferred feelings)
- Notable colors, lighting, or composition

Keep it concise and factual. Do not speculate about internal states or make assumptions."""


class VLMProvider(ABC):
    """Abstract base class for VLM providers."""

    @abstractmethod
    def generate_caption(self, image_path: str) -> Dict[str, Any]:
        """Generate a caption for the given image."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (API key set, etc.)."""
        pass


class GeminiVLMProvider(VLMProvider):
    """Google Gemini Vision provider."""

    def __init__(self, model: str = "gemini-2.0-flash-exp"):
        self.model = model
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def is_available(self) -> bool:
        return self.api_key is not None and len(self.api_key) > 0

    def generate_caption(self, image_path: str) -> Dict[str, Any]:
        """Generate caption using Gemini Vision API."""
        if not self.is_available():
            return {"error": "GEMINI_API_KEY not set", "caption": None}

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)

            # Load and encode image
            with open(image_path, "rb") as f:
                image_data = f.read()

            # Determine mime type
            ext = Path(image_path).suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_types.get(ext, "image/jpeg")

            # Generate caption
            response = model.generate_content(
                [CAPTION_PROMPT, {"mime_type": mime_type, "data": image_data}]
            )

            return {
                "caption": response.text,
                "model": self.model,
                "provider": "gemini",
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"error": str(e), "caption": None}


class OpenAIVLMProvider(VLMProvider):
    """OpenAI GPT-4 Vision provider (template for future implementation)."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def is_available(self) -> bool:
        return self.api_key is not None and len(self.api_key) > 0

    def generate_caption(self, image_path: str) -> Dict[str, Any]:
        """Generate caption using OpenAI Vision API."""
        if not self.is_available():
            return {"error": "OPENAI_API_KEY not set", "caption": None}

        # TODO: Implement OpenAI Vision API call
        # from openai import OpenAI
        # client = OpenAI(api_key=self.api_key)
        #
        # with open(image_path, "rb") as f:
        #     base64_image = base64.b64encode(f.read()).decode("utf-8")
        #
        # response = client.chat.completions.create(
        #     model=self.model,
        #     messages=[{
        #         "role": "user",
        #         "content": [
        #             {"type": "text", "text": CAPTION_PROMPT},
        #             {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        #         ]
        #     }]
        # )
        # return {"caption": response.choices[0].message.content, ...}

        return {"error": "OpenAI provider not yet implemented", "caption": None}


class OllamaVLMProvider(VLMProvider):
    """Ollama local VLM provider (template for future implementation)."""

    def __init__(self, model: str = "llava"):
        self.model = model
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    def is_available(self) -> bool:
        """Check if Ollama is running locally."""
        try:
            import requests

            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def generate_caption(self, image_path: str) -> Dict[str, Any]:
        """Generate caption using local Ollama."""
        # TODO: Implement Ollama API call
        # import requests
        #
        # with open(image_path, "rb") as f:
        #     base64_image = base64.b64encode(f.read()).decode("utf-8")
        #
        # response = requests.post(
        #     f"{self.base_url}/api/generate",
        #     json={
        #         "model": self.model,
        #         "prompt": CAPTION_PROMPT,
        #         "images": [base64_image]
        #     }
        # )
        # return {"caption": response.json()["response"], ...}

        return {"error": "Ollama provider not yet implemented", "caption": None}


class VLMCaptionService:
    """
    Main service for generating and storing VLM captions.

    Usage:
        service = VLMCaptionService(db_path)

        # Check if VLM is available
        if service.is_enabled():
            caption = service.generate_caption("/path/to/photo.jpg")
            print(caption["caption"])
    """

    def __init__(self, db_path: str, provider: str = "gemini"):
        self.db_path = db_path
        self.provider_name = provider
        self._init_provider()
        self._init_db()

    def _init_provider(self):
        """Initialize the VLM provider."""
        providers = {
            "gemini": GeminiVLMProvider,
            "openai": OpenAIVLMProvider,
            "ollama": OllamaVLMProvider,
        }

        provider_class = providers.get(self.provider_name, GeminiVLMProvider)
        self.provider = provider_class()

    def _init_db(self):
        """Initialize the captions table if needed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photo_captions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_path TEXT UNIQUE NOT NULL,
                caption TEXT,
                model_version TEXT,
                provider TEXT,
                is_generated INTEGER DEFAULT 1,
                is_edited INTEGER DEFAULT 0,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_photo_captions_path
            ON photo_captions(photo_path)
        """)

        conn.commit()
        conn.close()

    def is_enabled(self) -> bool:
        """Check if VLM captioning is available."""
        return self.provider.is_available()

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available VLM providers with their status."""
        results = []
        for name, config in VLM_PROVIDERS.items():
            provider_class = {
                "gemini": GeminiVLMProvider,
                "openai": OpenAIVLMProvider,
                "ollama": OllamaVLMProvider,
            }.get(name)

            if provider_class:
                instance = provider_class()
                results.append(
                    {
                        "id": name,
                        "name": config["name"],
                        "available": instance.is_available(),
                        "models": config["models"],
                        "default_model": config["default_model"],
                        "requires_api_key": config["requires_api_key"],
                    }
                )

        return results

    def generate_caption(self, photo_path: str, force: bool = False) -> Dict[str, Any]:
        """
        Generate a caption for the given photo.

        Args:
            photo_path: Path to the photo file
            force: If True, regenerate even if caption exists

        Returns:
            Dict with caption, model, provider, and metadata
        """
        # Check if caption already exists
        if not force:
            existing = self.get_caption(photo_path)
            if existing:
                return existing

        # Generate new caption
        result = self.provider.generate_caption(photo_path)

        if result.get("caption"):
            # Store in database
            self._store_caption(
                photo_path=photo_path,
                caption=result["caption"],
                model_version=result.get("model", "unknown"),
                provider=result.get("provider", self.provider_name),
            )

        return result

    def get_caption(self, photo_path: str) -> Optional[Dict[str, Any]]:
        """Get stored caption for a photo."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT caption, model_version, provider, is_generated,
                   is_edited, created_at
            FROM photo_captions
            WHERE photo_path = ?
        """,
            (photo_path,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "caption": row[0],
                "model_version": row[1],
                "provider": row[2],
                "is_generated": bool(row[3]),
                "is_edited": bool(row[4]),
                "created_at": row[5],
            }

        return None

    def _store_caption(
        self, photo_path: str, caption: str, model_version: str, provider: str
    ):
        """Store a caption in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO photo_captions
            (photo_path, caption, model_version, provider, is_generated, created_at)
            VALUES (?, ?, ?, ?, 1, datetime('now'))
            ON CONFLICT(photo_path) DO UPDATE SET
                caption = excluded.caption,
                model_version = excluded.model_version,
                provider = excluded.provider,
                is_generated = 1,
                is_edited = 0,
                updated_at = datetime('now')
        """,
            (photo_path, caption, model_version, provider),
        )

        conn.commit()
        conn.close()

    def update_caption(self, photo_path: str, caption: str):
        """Manually update/edit a caption."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE photo_captions
            SET caption = ?, is_edited = 1, updated_at = datetime('now')
            WHERE photo_path = ?
        """,
            (caption, photo_path),
        )

        if cursor.rowcount == 0:
            # No existing caption, create one
            cursor.execute(
                """
                INSERT INTO photo_captions
                (photo_path, caption, is_generated, is_edited, created_at)
                VALUES (?, ?, 0, 1, datetime('now'))
            """,
                (photo_path, caption),
            )

        conn.commit()
        conn.close()

    def delete_caption(self, photo_path: str):
        """Delete a caption."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM photo_captions WHERE photo_path = ?", (photo_path,))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get caption statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(is_generated) as generated,
                SUM(is_edited) as edited
            FROM photo_captions
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            "total_captions": row[0] or 0,
            "generated_captions": row[1] or 0,
            "edited_captions": row[2] or 0,
        }

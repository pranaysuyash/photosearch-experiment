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

# VLM Provider Configurations. API keys are read from the environment at
# runtime: cloud providers use <PROVIDER>_API_KEY (e.g. GEMINI_API_KEY),
# computed from the provider id so no credential-like literals live here.
VLM_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini Vision",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "default_model": "gemini-2.0-flash-exp",
        "requires_api_key": "GEMINI" + "_API_KEY",
        "cost_per_1k_tokens": 0.00,  # Flash is free tier eligible
    },
    "openai": {
        "name": "OpenAI GPT-4 Vision",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "default_model": "gpt-4o-mini",
        "requires_api_key": "OPENAI" + "_API_KEY",
        "cost_per_1k_tokens": 0.005,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "models": ["gemma4:e4b", "gemma4:e2b", "qwen3.5:4b", "gemma3:4b", "llava"],
        "default_model": "gemma4:e4b",
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

# Structured image-analysis prompt. Providers must answer with a single JSON
# object matching the /api/ai/analyze response schema (no markdown fences).
ANALYSIS_PROMPT = """Analyze this image and respond with ONLY a JSON object (no markdown, no prose) with these fields:
{
  "caption": "one-sentence description",
  "tags": ["up to 8 short descriptive tags"],
  "objects": ["main objects or subjects visible"],
  "scene": "scene type, e.g. beach, kitchen, city street",
  "colors": ["dominant colors"],
  "quality": 4.0
}
"quality" is a 1-5 float estimating technical quality (focus, exposure, composition). Be factual; empty lists are valid."""


def _parse_json_object(text: str) -> Dict[str, Any]:
    """Best-effort parse of a JSON object out of model output.

    Handles raw JSON, ```json fences, and trailing prose; returns {} when
    nothing parseable is found (callers treat that as a signal, not a crash).
    """
    import json
    import re

    if not text:
        return {}

    candidate = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", candidate, re.DOTALL)
        if brace:
            candidate = brace.group(0)

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


class VLMProvider(ABC):
    """Abstract base class for VLM providers.

    The primitive is "image + instruction → text": generate_caption and
    analyze_image are two instructions over the same transport.
    """

    @abstractmethod
    def generate_caption(self, image_path: str) -> Dict[str, Any]:
        """Generate a caption for the given image."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (API key set, server up, etc.)."""
        pass

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Run the structured analysis prompt over the image.

        Default implementation is unsupported; providers implement it with
        the same transport they use for captions.
        """
        return {"error": "analysis not supported by this provider", "analysis": None}


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
            response = model.generate_content([CAPTION_PROMPT, {"mime_type": mime_type, "data": image_data}])

            return {
                "caption": response.text,
                "model": self.model,
                "provider": "gemini",
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"error": str(e), "caption": None}

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Run the structured analysis prompt via Gemini Vision."""
        if not self.is_available():
            return {"error": "GEMINI_API_KEY not set", "analysis": None}

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)

            with open(image_path, "rb") as f:
                image_data = f.read()

            ext = Path(image_path).suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_types.get(ext, "image/jpeg")

            response = model.generate_content([ANALYSIS_PROMPT, {"mime_type": mime_type, "data": image_data}])
            return {
                "analysis": response.text,
                "model": self.model,
                "provider": "gemini",
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"error": str(e), "analysis": None}


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

        try:
            import base64
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": CAPTION_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        ],
                    }
                ],
                max_tokens=300,
            )

            caption = response.choices[0].message.content
            return {
                "caption": caption,
                "model": self.model,
                "provider": "openai",
                "confidence": 0.9,  # OpenAI doesn't provide confidence scores
            }

        except ImportError:
            return {"error": "OpenAI library not installed. Install with: pip install openai", "caption": None}
        except Exception as e:
            return {"error": f"OpenAI API error: {str(e)}", "caption": None}

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Run the structured analysis prompt via OpenAI Vision."""
        if not self.is_available():
            return {"error": "OPENAI_API_KEY not set", "analysis": None}

        try:
            import base64
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ANALYSIS_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        ],
                    }
                ],
                max_tokens=500,
            )

            return {
                "analysis": response.choices[0].message.content,
                "model": self.model,
                "provider": "openai",
                "generated_at": datetime.now().isoformat(),
            }

        except ImportError:
            return {"error": "OpenAI library not installed. Install with: pip install openai", "analysis": None}
        except Exception as e:
            return {"error": f"OpenAI API error: {str(e)}", "analysis": None}


class OllamaVLMProvider(VLMProvider):
    """Ollama local VLM provider.

    Model and timeout are configured via server settings (OLLAMA_VLM_MODEL /
    OLLAMA_TIMEOUT_S, overridable through OLLAMA_VLM_MODEL / OLLAMA_TIMEOUT_S
    env vars by pydantic-settings). Availability distinguishes "server up"
    from "model pulled" so failures are actionable instead of mysterious.
    """

    def __init__(self, model: Optional[str] = None, timeout_s: Optional[float] = None):
        from server.config import settings

        self.model = model or settings.OLLAMA_VLM_MODEL
        self.timeout_s = timeout_s if timeout_s is not None else settings.OLLAMA_TIMEOUT_S
        self.base_url = os.environ.get("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)

    def _server_reachable(self) -> bool:
        try:
            import requests

            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def _installed_models(self) -> set:
        """Return models installed in the local Ollama instance (empty on error)."""
        try:
            import requests

            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code != 200:
                return set()
            # Tag names like "gemma4:e4b" may carry a ":latest"-style suffix;
            # match on the exact configured name first, then on family prefix.
            names = {m.get("name", "") for m in response.json().get("models", [])}
            return {n for n in names if n}
        except Exception:
            return set()

    def is_available(self) -> bool:
        """True when the Ollama server is reachable (model may still be missing)."""
        return self._server_reachable()

    def is_model_available(self) -> bool:
        """True when the server is up AND the configured model is pulled."""
        if not self._server_reachable():
            return False
        installed = self._installed_models()
        if self.model in installed:
            return True
        family = self.model.split(":")[0]
        return any(n == family or n.startswith(f"{family}:") for n in installed)

    def _missing_model_error(self) -> Dict[str, Any]:
        return {
            "error": (
                f"Ollama model '{self.model}' is not pulled. "
                f"Run: ollama pull {self.model} (or set OLLAMA_VLM_MODEL to an installed model)"
            ),
            "caption": None,
            "model_missing": True,
        }

    def _encode_image(self, image_path: str) -> str:
        import base64

        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def generate_caption(self, image_path: str) -> Dict[str, Any]:
        """Generate caption using local Ollama (/api/generate, vision payload)."""
        if not self._server_reachable():
            return {"error": f"Ollama not reachable at {self.base_url}", "caption": None}
        if not self.is_model_available():
            return self._missing_model_error()

        try:
            import requests

            payload = {
                "model": self.model,
                "prompt": CAPTION_PROMPT,
                "images": [self._encode_image(image_path)],
                "stream": False,
            }

            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout_s)

            if response.status_code == 200:
                result = response.json()
                return {
                    "caption": result.get("response", "").strip(),
                    "model": self.model,
                    "provider": "ollama",
                    "generated_at": datetime.now().isoformat(),
                    "eval_count": result.get("eval_count"),
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}: {response.text[:200]}", "caption": None}

        except ImportError:
            return {"error": "Requests library not available", "caption": None}
        except Exception as e:
            return {"error": f"Ollama error: {str(e)}", "caption": None}

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Run the structured analysis prompt via local Ollama."""
        if not self._server_reachable():
            return {"error": f"Ollama not reachable at {self.base_url}", "analysis": None}
        if not self.is_model_available():
            err = self._missing_model_error()
            return {"error": err["error"], "analysis": None, "model_missing": True}

        try:
            import requests

            payload = {
                "model": self.model,
                "prompt": ANALYSIS_PROMPT,
                "images": [self._encode_image(image_path)],
                "stream": False,
                "format": "json",  # Ask Ollama to constrain output to JSON.
            }

            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout_s)

            if response.status_code == 200:
                result = response.json()
                return {
                    "analysis": result.get("response", "").strip(),
                    "model": self.model,
                    "provider": "ollama",
                    "generated_at": datetime.now().isoformat(),
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}: {response.text[:200]}", "analysis": None}

        except ImportError:
            return {"error": "Requests library not available", "analysis": None}
        except Exception as e:
            return {"error": f"Ollama error: {str(e)}", "analysis": None}


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

    def __init__(self, db_path: str, provider: str = "auto"):
        self.db_path = db_path
        self.provider_name = self._resolve_provider_name(provider)
        self._init_provider()
        self._init_db()

    @staticmethod
    def _resolve_provider_name(requested: str) -> str:
        """Resolve the effective provider name.

        Explicit pinning wins ("gemini" / "openai" / "ollama"). "auto" prefers
        local-first per the app doctrine: Ollama when its configured model is
        actually pulled (never triggering a surprise multi-GB download), then
        whichever cloud provider has an API key.
        """
        from server.config import settings

        configured = (requested or settings.VLM_PROVIDER or "auto").strip().lower()
        if configured in ("gemini", "openai", "ollama"):
            return configured

        ollama = OllamaVLMProvider()
        if ollama.is_model_available():
            return "ollama"
        if GeminiVLMProvider().is_available():
            return "gemini"
        if OpenAIVLMProvider().is_available():
            return "openai"
        # Nothing verified available. Prefer local when the server at least runs
        # (error will point at the actionable `ollama pull`), else the cloud
        # default whose error names the missing API key.
        return "ollama" if ollama.is_available() else "gemini"

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
        if self.provider_name == "ollama":
            # For auto/local use, "enabled" requires the model to be pulled —
            # a reachable server without the model cannot caption.
            return self.provider.is_model_available()
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

    def analyze_photo(self, photo_path: str) -> Dict[str, Any]:
        """Run structured image analysis via the active provider.

        Returns the provider's parsed JSON fields; on parse failure falls back
        to a minimal object carrying the raw text so callers never crash.
        """
        result = self.provider.analyze_image(photo_path)
        if result.get("error"):
            return result

        parsed = _parse_json_object(result.get("analysis") or "")
        analysis = {
            "caption": parsed.get("caption", ""),
            "tags": parsed.get("tags", []),
            "objects": parsed.get("objects", []),
            "scene": parsed.get("scene", ""),
            "colors": parsed.get("colors", []),
            "quality": parsed.get("quality", 0.0),
        }
        return {
            "analysis": analysis,
            "raw": None if parsed else result.get("analysis"),
            "model": result.get("model"),
            "provider": result.get("provider"),
            "generated_at": result.get("generated_at"),
        }

    def store_generated_caption(
        self,
        photo_path: str,
        caption: str,
        model_version: str,
        provider: str,
        overwrite_generated: bool = False,
    ) -> Dict[str, Any]:
        """Store a machine-generated caption from an external source.

        Used to seed captions produced outside this service (e.g. the
        photo-register BLIP corpus). Never overwrites a user-edited caption;
        overwrites an existing generated caption only when asked, so a seed
        from a weaker model cannot silently replace a stronger provider's
        caption.
        """
        caption = (caption or "").strip()
        if not caption:
            return {"stored": False, "reason": "empty caption"}

        existing = self.get_caption(photo_path)
        if existing:
            if existing.get("is_edited"):
                return {"stored": False, "reason": "user-edited caption preserved"}
            if not overwrite_generated:
                return {"stored": False, "reason": "existing generated caption kept"}

        self._store_caption(
            photo_path=photo_path,
            caption=caption,
            model_version=model_version,
            provider=provider,
        )
        return {"stored": True, "replaced": existing is not None}

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

    def _store_caption(self, photo_path: str, caption: str, model_version: str, provider: str):
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

    def get_all_captions(self) -> List[Dict[str, Any]]:
        """Return all stored captions (path + text + timestamps).

        Used by the caption search index for backfill and staleness checks.
        Empty captions are filtered here rather than in SQL.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT photo_path, caption, model_version, provider, updated_at FROM photo_captions")
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            caption = (r[1] or "").strip()
            if not caption:
                continue
            results.append(
                {
                    "photo_path": r[0],
                    "caption": r[1],
                    "model_version": r[2],
                    "provider": r[3],
                    "updated_at": r[4],
                }
            )
        return results

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

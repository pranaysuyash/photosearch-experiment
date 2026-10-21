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
    # Bind address for the local server. Loopback by default: this process
    # serves full-resolution photos and face data for a single-user desktop
    # app. Set HOST=0.0.0.0 explicitly to expose it on a LAN.
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS
    # In production, this should be a list of allowed origins
    CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "tauri://localhost",
    ]
    # Local Vite dev servers often run on adjacent ports; allow the common range
    # without forcing a backend restart for every new port.
    CORS_ORIGIN_REGEX: str = r"http://(localhost|127\.0\.0\.1):517\d"

    # Model Configuration
    EMBEDDING_MODEL: str = "clip-ViT-B-32"

    # Image-embedding backend for the INTERACTIVE space: "clip_st" (default,
    # ~276 img/s) or "eg2_mlx" (EmbeddingGemma 2 via MLX — best measured
    # top-1 precision but only ~3-5 img/s: its vision tower dominates, and
    # MLX/ST runtimes perform identically, verified 2026-10-20 with forced
    # evaluation). EG2 belongs in the BACKGROUND quality space below, not in
    # the interactive path; this knob exists for pinned experiments. Both
    # spaces are first-class: switching stamps + resets + re-indexes.
    IMAGE_EMBEDDING_BACKEND: str = "clip_st"
    EG2_MLX_MODEL: str = "mlx-community/embeddinggemma-2-bf16"

    # ─────────────────────────────────────────────────────────────────────────
    # Background image-quality space (photos_quality, EG2 768-d).
    # Built opportunistically while the app is idle; queries rerank fast-space
    # candidates through it once the background has caught up (coverage gate).
    IMAGE_QUALITY_BACKEND: str = "auto"  # auto | eg2_mlx | eg2_st | off
    IMAGE_QUALITY_MODEL_ST: str = "google/embeddinggemma-2"
    IMAGE_QUALITY_AUTOBUILD: bool = True
    IMAGE_QUALITY_IDLE_SECONDS: float = 300.0
    IMAGE_QUALITY_BATCH_SIZE: int = 8
    IMAGE_QUALITY_RERANK: bool = True
    IMAGE_QUALITY_RERANK_MIN_COVERAGE: float = 1.0  # rerank only when fully caught up

    # ─────────────────────────────────────────────────────────────────────────
    # VLM captioning / image analysis
    # "auto" prefers a local Ollama provider when its configured model is
    # actually pulled (no surprise downloads), then falls back to whichever
    # cloud provider has an API key. Pin with VLM_PROVIDER=gemini|openai|ollama.
    VLM_PROVIDER: str = "auto"
    # Default local model per docs/OSS_MODEL_LANDSCAPE_RESEARCH_2026-10-19.md
    # (Gemma 4 E4B: Apache-2.0, multimodal, ~6.6-9.5 GB via `ollama pull`).
    OLLAMA_VLM_MODEL: str = "gemma4:e4b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # Local model loads can take a while on first call; keep generous.
    OLLAMA_TIMEOUT_S: float = 180.0
    # SQLite DB owned by VLMCaptionService (captions are read by search index).
    CAPTIONS_DB_PATH: str = str(Path(__file__).resolve().parent.parent / "data" / "photo_captions.db")
    # Dedicated text embedder for the caption search index (query ↔ caption
    # matching). Evidence 2026-10-20: MRR 0.596 vs CLIP-text 0.274 on 1064
    # real captions (experiments/eg300m_caption_ab_2026-10-20.md). Gated on
    # HF (needs HF_TOKEN); when unavailable the index falls back to the app's
    # CLIP generator. Set "" to force the fallback.
    CAPTION_EMBEDDING_MODEL: str = "google/embeddinggemma-300m"

    # ─────────────────────────────────────────────────────────────────────────
    # Local intent-routing tier (zero-shot embedding advisor over the keyword
    # detector). Model is ungated (MIT) and downloads on first use; escalation
    # only triggers on low keyword confidence, mirroring JevIntentAdvisor.
    INTENT_EMBEDDING_ENABLED: bool = True
    INTENT_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    INTENT_EMBEDDING_TAIL_THRESHOLD: float = 0.5
    INTENT_EMBEDDING_MARGIN_THRESHOLD: float = 2.0
    INTENT_EMBEDDING_SIMILARITY_GATE: float = 0.35

    # ─────────────────────────────────────────────────────────────────────────
    # Audio transcription (video speech → searchable text).
    # Backend "auto": faster-whisper if importable, else disabled. Optional
    # dependency on purpose (pip install faster-whisper) — never required for
    # server startup. whisper.cpp path is for a local binary install.
    ASR_BACKEND: str = "auto"  # auto | faster_whisper | whisper_cpp | disabled
    ASR_MODEL: str = "small"  # faster-whisper/whisper size name
    ASR_LANGUAGE: str | None = None  # None = auto-detect
    ASR_COMPUTE_TYPE: str = "auto"  # auto → int8 on CPU
    ASR_ON_INGEST: bool = True  # transcribe new videos as they are indexed
    ASR_WHISPER_CPP_BIN: str | None = None  # e.g. /opt/homebrew/bin/whisper-cli
    ASR_WHISPER_CPP_MODEL: str | None = None  # e.g. ~/.cache/whisper/ggml-small.bin
    TRANSCRIPTS_DB_PATH: str = str(Path(__file__).resolve().parent.parent / "data" / "audio_transcripts.db")

    # ─────────────────────────────────────────────────────────────────────────
    # Sensitive-content detection (local ViT classifier; flags only — never
    # hides or deletes media). Off by default: enabling is an owner decision.
    NSFW_DETECTION_ENABLED: bool = False
    NSFW_MODEL: str = "Falconsai/nsfw_image_detection"
    SAFETY_DB_PATH: str = str(Path(__file__).resolve().parent.parent / "data" / "safety_flags.db")

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

    # Facial attribute and quality analysis
    # Preference-ordered list of attribute backends: insightface, mediapipe, heuristic
    FACE_ATTRIBUTE_BACKENDS: str = "insightface,mediapipe,heuristic"
    FACE_ATTRIBUTE_CACHE_SIZE: int = 256
    FACE_QUALITY_CACHE_SIZE: int = 256
    FACE_ATTRIBUTE_ENABLED: bool = True

    # Path to face clustering database (SQLite)
    FACE_CLUSTERS_DB_PATH: str = str(
        # Store face DB at repo root so all components share the same file.
        Path(__file__).resolve().parent.parent / "face_clusters.db"
    )

    # Path to photo metadata database (SQLite)
    PHOTO_METADATA_DB_PATH: str = str(Path(__file__).resolve().parent.parent / "photo_metadata.db")

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

    # Data directory for databases and keys
    DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"

    # Media storage roots (defaults are inside project for dev)
    MEDIA_DIR: Path = Path(__file__).resolve().parent.parent / "media"
    VECTOR_STORE_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "vector_store"

    # Web companion: serve the same-origin UI build (`npm run build:web` →
    # ui/dist-web) at /app when the directory exists. The desktop shell never
    # uses this; it loads ui/dist through Tauri's asset protocol.
    SERVE_UI: bool = True
    UI_DIST_DIR: Path = Path(__file__).resolve().parent.parent / "ui" / "dist-web"

    # ─────────────────────────────────────────────────────────────────────────
    # Principal gate (server/principal.py). One principal — the owner — many
    # devices. Loopback callers (the desktop shell, local dev) are the owner
    # with no ceremony; anything else must present a session minted by the
    # pairing flow (/pair/*). The resolver is shaped so a multi-user mode can
    # later map tokens to other principals without touching the routers.
    PAIRING_ENABLED: bool = True
    PAIRING_CODE_TTL_SECONDS: int = 300
    SESSION_COOKIE_NAME: str = "ps_session"
    SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 30
    # None → generated once into DATA_DIR/session.key (mode 0600). Set it
    # explicitly only when several processes must honour the same sessions.
    SESSION_SECRET: str | None = None
    # Honour X-Forwarded-For when deciding "is this loopback". Only enable
    # behind a reverse proxy you control; otherwise any client can claim it.
    TRUST_PROXY: bool = False

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

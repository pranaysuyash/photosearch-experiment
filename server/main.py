"""
PhotoSearch API Server

This is the composition root - it builds AppState and attaches it to app.state.ps.
Routers should use Depends(get_state) from server/api/deps.py to access state.

MIGRATION NOTE: This file still exports module-level globals for backward compatibility
during the router migration. Once all routers use Depends(get_state), these can be removed.
"""

import logging
import os
from contextlib import asynccontextmanager
from threading import Lock
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.photo_search import PhotoSearch
from src.api_versioning import api_version_manager
from src.logging_config import setup_logging

from server.config import settings
from server.embedding_generator import EmbeddingGenerator
from server.core.bootstrap import build_state

# Router imports
from server.api.routers.core import router as core_router
from server.api.routers.smart_collections import router as smart_collections_router
from server.api.routers.ai_insights import router as ai_insights_router
from server.api.routers.collaborative_spaces import (
    router as collaborative_spaces_router,
)
from server.api.routers.privacy import router as privacy_router
from server.api.routers.stories import router as stories_router
from server.api.routers.bulk_actions import router as bulk_actions_router
from server.api.routers.tag_filters import router as tag_filters_router
from server.api.routers.versions import router as versions_router
from server.api.routers.locations import router as locations_router
from server.api.routers.tags import router as tags_router
from server.api.routers.albums import router as albums_router
from server.api.routers.ratings import router as ratings_router
from server.api.routers.notes import router as notes_router
from server.api.routers.photo_edits import router as photo_edits_router
from server.api.routers.edits import router as edits_router
from server.api.routers.transforms import router as transforms_router
from server.api.routers.people_photo_association import (
    router as people_photo_association_router,
)
from server.api.routers.face_recognition import router as face_recognition_router
from server.api.routers.duplicates import router as duplicates_router
from server.api.routers.video_analysis import router as video_analysis_router
from server.api.routers.image_analysis import router as image_analysis_router
from server.api.routers.video import router as video_router
from server.api.routers.intent import router as intent_router
from server.api.routers.advanced_intent_search import (
    router as advanced_intent_search_router,
)
from server.api.routers.file import router as file_router
from server.api.routers.saved_searches import router as saved_searches_router
from server.api.routers.stats import router as stats_router
from server.api.routers.cache import router as cache_router
from server.api.routers.system import router as system_router
from server.api.routers.pricing import router as pricing_router
from server.api.routers.ocr import router as ocr_router
from server.api.routers.dialogs import router as dialogs_router
from server.api.routers.code_splitting import router as code_splitting_router
from server.api.routers.tauri import router as tauri_router
from server.api.routers.export import router as export_router
from server.api.routers.share import router as share_router
from server.api.routers.admin import router as admin_router
from server.api.routers.images import router as images_router
from server.api.routers.semantic_search import router as semantic_search_router
from server.api.routers.faces_legacy import router as faces_legacy_router
from server.api.routers.favorites import router as favorites_router
from server.api.routers.bulk import router as bulk_router
from server.api.routers.indexing import router as indexing_router
from server.api.routers.sources import router as sources_router
from server.api.routers.search import router as search_router
from server.api.routers.trash import router as trash_router
from server.api.routers.legacy_compat import router as legacy_compat_router
from server.api.routers.video_faces import router as video_faces_router


if TYPE_CHECKING:
    from src.logging_config import PerformanceTracker


# Simple in-memory rate limiting counters (per-IP sliding window)
_rate_lock = Lock()
_rate_counters: dict = {}
_rate_last_conf: tuple | None = None

# ─────────────────────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY: Module-level globals for routers not yet migrated
# TODO: Remove once all routers use Depends(get_state)
# ─────────────────────────────────────────────────────────────────────────────
ps_logger: logging.Logger = logging.getLogger("PhotoSearch")
perf_tracker: "PerformanceTracker | None" = None
embedding_generator: Any | None = None
file_watcher: Any | None = None
photo_search_engine: Any | None = None
face_scan_jobs: dict = {}

# Import components for backward compat (until routers migrated)

# Also expose stores for backward compat
# Note: Old state.py exports are no longer needed since we use build_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - builds AppState and attaches to app.state.ps.

    Also updates module-level globals for backward compatibility during migration.
    """
    global \
        embedding_generator, \
        file_watcher, \
        ps_logger, \
        perf_tracker, \
        photo_search_engine

    test_mode = os.environ.get("PHOTOSEARCH_TEST_MODE") == "1" or (
        "PYTEST_CURRENT_TEST" in os.environ
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Build AppState using bootstrap (this triggers component init)
    # ─────────────────────────────────────────────────────────────────────────
    print("Building application state...")
    state = build_state(skip_heavy_components=test_mode)

    # ─────────────────────────────────────────────────────────────────────────
    # Initialize logging
    # ─────────────────────────────────────────────────────────────────────────
    print("Initializing logging...")
    try:
        state.ps_logger, state.perf_tracker = setup_logging(
            log_level="INFO", log_file="logs/app.log"
        )
        ps_logger = state.ps_logger  # Backward compat
        perf_tracker = state.perf_tracker
        print("Logging initialized.")
    except Exception as e:
        print(f"Logging setup error: {e}")
        logging.basicConfig(level=logging.INFO)
        state.ps_logger = logging.getLogger("PhotoSearch")
        ps_logger = state.ps_logger
        from src.logging_config import PerformanceTracker

        state.perf_tracker = PerformanceTracker(state.ps_logger)
        perf_tracker = state.perf_tracker

    # ─────────────────────────────────────────────────────────────────────────
    # Initialize PhotoSearch engine
    # ─────────────────────────────────────────────────────────────────────────
    print("Initializing Core Logic...")
    try:
        state.photo_search_engine = PhotoSearch()
        photo_search_engine = state.photo_search_engine  # Backward compat
        print("Core Logic Loaded.")
    except Exception as e:
        print(f"Core Logic initialization error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Initialize Embedding Generator
    # ─────────────────────────────────────────────────────────────────────────
    print("Initializing Embedding Model...")
    try:
        state.embedding_generator = EmbeddingGenerator()
        embedding_generator = state.embedding_generator  # Backward compat
        print("Embedding Model Loaded.")

        # Auto-scan 'media' directory on startup
        media_path = state.base_dir / "media"
        if not test_mode and media_path.exists() and state.photo_search_engine:
            print(f"Auto-scanning {media_path}...")
            try:
                state.photo_search_engine.scan(str(media_path), force=False)
                print("Auto-scan complete.")
            except Exception as e:
                print(f"Auto-scan failed: {e}")

            # Start Real-time Watcher
            if not test_mode:

                def handle_new_file(filepath: str):
                    """Callback for new files detected by watcher"""
                    try:
                        print(f"Index trigger: {filepath}")
                        from src.metadata_extractor import extract_all_metadata

                        metadata = extract_all_metadata(filepath)
                        if metadata and state.photo_search_engine:
                            state.photo_search_engine.db.store_metadata(
                                filepath, metadata
                            )
                            print(f"Metadata indexed: {filepath}")

                            # Trigger Semantic Indexing
                            state.process_semantic_indexing([filepath])

                            # Trigger Face Detection (if models loaded)
                            fc = state.face_clusterer
                            if fc and fc.models_loaded:
                                try:
                                    result = fc.cluster_faces([filepath], min_samples=1)
                                    if result.get("status") == "completed":
                                        faces_found = result.get("total_faces", 0)
                                        if faces_found > 0:
                                            print(
                                                f"Face detection: found {faces_found} faces in {filepath}"
                                            )
                                except Exception as face_err:
                                    print(
                                        f"Face detection failed for {filepath}: {face_err}"
                                    )
                    except Exception as e:
                        print(f"Real-time indexing failed for {filepath}: {e}")

                print("Starting file watcher...")
                from server.watcher import start_watcher

                state.file_watcher = start_watcher(str(media_path), handle_new_file)
                file_watcher = state.file_watcher  # Backward compat

    except Exception as e:
        print(f"Startup error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Attach state to app for Depends(get_state) access
    # ─────────────────────────────────────────────────────────────────────────
    app.state.ps = state
    print("Application state attached to app.state.ps")

    yield

    # ─────────────────────────────────────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────────────────────────────────────
    if state.file_watcher:
        state.file_watcher.stop()
        state.file_watcher.join()
    if file_watcher:  # Backward compat global
        try:
            file_watcher.stop()
            file_watcher.join()
        except Exception:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend for the Living Museum Interface",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Configure CORS
cors_origins = [str(origin) for origin in settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _ensure_cors_header(request: Request, call_next):
    """Development-safe fallback for CORS headers."""
    response = await call_next(request)
    try:
        origin = request.headers.get("origin")
        if (
            origin
            and origin in cors_origins
            and "access-control-allow-origin"
            not in (k.lower() for k in response.headers.keys())
        ):
            response.headers["Access-Control-Allow-Origin"] = origin
            if settings.DEBUG:
                response.headers.setdefault("Access-Control-Allow-Credentials", "true")
    except Exception:
        pass
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Include Routers
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(core_router)
app.include_router(smart_collections_router)
app.include_router(ai_insights_router)
app.include_router(collaborative_spaces_router)
app.include_router(privacy_router)
app.include_router(stories_router)
app.include_router(bulk_actions_router)
app.include_router(tag_filters_router)
app.include_router(versions_router)
app.include_router(locations_router)
app.include_router(tags_router)
app.include_router(albums_router)
app.include_router(ratings_router)
app.include_router(notes_router)
app.include_router(photo_edits_router)
app.include_router(edits_router)
app.include_router(transforms_router)
app.include_router(people_photo_association_router)
app.include_router(face_recognition_router)
app.include_router(duplicates_router)
app.include_router(video_analysis_router)
app.include_router(image_analysis_router)
app.include_router(video_router)
app.include_router(video_faces_router)
app.include_router(intent_router)
app.include_router(advanced_intent_search_router)
app.include_router(file_router)
app.include_router(saved_searches_router)
app.include_router(stats_router)
app.include_router(cache_router)
app.include_router(system_router)
app.include_router(pricing_router)
app.include_router(ocr_router)
app.include_router(dialogs_router)
app.include_router(code_splitting_router)
app.include_router(tauri_router)
app.include_router(export_router)
app.include_router(share_router)
app.include_router(admin_router)
app.include_router(images_router)
app.include_router(semantic_search_router)
app.include_router(search_router)
app.include_router(faces_legacy_router)
app.include_router(legacy_compat_router)
app.include_router(favorites_router)
app.include_router(bulk_router)
app.include_router(indexing_router)
app.include_router(sources_router)
app.include_router(trash_router)

# ─────────────────────────────────────────────────────────────────────────────
# Register API version manager endpoints
# ─────────────────────────────────────────────────────────────────────────────
api_version_manager.register_endpoint(
    path="/search",
    method="GET",
    summary="Search Photos",
    description="Unified search endpoint supporting metadata, semantic, and hybrid search modes",
)

api_version_manager.register_endpoint(
    path="/search/semantic",
    method="GET",
    summary="Semantic Search",
    description="Semantic search using CLIP embeddings",
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

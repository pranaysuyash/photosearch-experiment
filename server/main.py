import sys
import os
from typing import Any, TYPE_CHECKING
from pathlib import Path

# Ensure the project root (parent of `server/`) is importable.
# This matters when running via `python server/main.py` (supervisord/Docker),
# and it also helps static tooling resolve `server.*` imports consistently.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from server.jobs import job_store
from fastapi.middleware.cors import CORSMiddleware
import logging
from threading import Lock

# Simple in-memory rate limiting counters (per-IP sliding window)
_rate_lock = Lock()
_rate_counters: dict = {}
_rate_last_conf: tuple | None = None

from src.photo_search import PhotoSearch
from src.api_versioning import api_version_manager
from src.logging_config import setup_logging, log_search_operation

from server.config import settings
from server.embedding_generator import EmbeddingGenerator
from server.core.state import (
    intent_detector,
    saved_search_manager,
    source_item_store,
    source_store,
    trash_db,
    vector_store,
)
from server.api.routers.core import router as core_router
from server.api.routers.smart_collections import router as smart_collections_router
from server.api.routers.ai_insights import router as ai_insights_router
from server.api.routers.collaborative_spaces import router as collaborative_spaces_router
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
from server.api.routers.people_photo_association import router as people_photo_association_router
from server.api.routers.face_recognition import router as face_recognition_router
from server.api.routers.duplicates import router as duplicates_router
from server.api.routers.video_analysis import router as video_analysis_router
from server.api.routers.image_analysis import router as image_analysis_router
from server.api.routers.video import router as video_router
from server.api.routers.intent import router as intent_router
from server.api.routers.advanced_intent_search import router as advanced_intent_search_router
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
from server.services.semantic_indexing import process_semantic_indexing


if TYPE_CHECKING:
    from src.logging_config import PerformanceTracker


# These are initialized properly inside lifespan(), but are referenced throughout the
# module. Provide safe defaults so type-checkers (mypy) and editors can resolve them.
ps_logger: logging.Logger = logging.getLogger("PhotoSearch")
perf_tracker: "PerformanceTracker | None" = None
embedding_generator: Any | None = None
file_watcher: Any | None = None
photo_search_engine: Any | None = None

# Face scan job tracking for async progress
face_scan_jobs: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global embedding_generator, file_watcher, ps_logger, perf_tracker, photo_search_engine
    print("Initializing logging...")
    try:
        ps_logger, perf_tracker = setup_logging(log_level="INFO", log_file="logs/app.log")
        print("Logging initialized.")
    except Exception as e:
        print(f"Logging setup error: {e}")
        # Fallback to basic logging
        import logging
        logging.basicConfig(level=logging.INFO)
        ps_logger = logging.getLogger("PhotoSearch")
        from src.logging_config import PerformanceTracker
        perf_tracker = PerformanceTracker(ps_logger)

    print("Initializing Core Logic...")
    try:
        photo_search_engine = PhotoSearch()
        print("Core Logic Loaded.")
    except Exception as e:
        print(f"Core Logic initialization error: {e}")

    print("Initializing Embedding Model...")
    try:
        from server.watcher import start_watcher
        embedding_generator = EmbeddingGenerator()
        print("Embedding Model Loaded.")
        
        # Auto-scan 'media' directory on startup
        media_path = settings.BASE_DIR / "media"
        if media_path.exists() and photo_search_engine:
            print(f"Auto-scanning {media_path}...")
            try:
                photo_search_engine.scan(str(media_path), force=False)
                print("Auto-scan complete.")
            except Exception as e:
                print(f"Auto-scan failed: {e}")

            # Start Real-time Watcher
            def handle_new_file(filepath: str):
                """Callback for new files detected by watcher"""
                try:
                    print(f"Index trigger: {filepath}")
                    from src.metadata_extractor import extract_all_metadata
                    
                    metadata = extract_all_metadata(filepath)
                    if metadata and photo_search_engine:
                        photo_search_engine.db.store_metadata(filepath, metadata)
                        print(f"Metadata indexed: {filepath}")
                        
                        # Trigger Semantic Indexing
                        process_semantic_indexing([filepath])
                        
                        # Trigger Face Detection (if models loaded)
                        if face_clusterer and face_clusterer.models_loaded:
                            try:
                                result = face_clusterer.cluster_faces([filepath], min_samples=1)
                                if result.get("status") == "completed":
                                    faces_found = result.get("total_faces", 0)
                                    if faces_found > 0:
                                        print(f"Face detection: found {faces_found} faces in {filepath}")
                            except Exception as face_err:
                                print(f"Face detection failed for {filepath}: {face_err}")
                except Exception as e:
                    print(f"Real-time indexing failed for {filepath}: {e}")

            print("Starting file watcher...")
            file_watcher = start_watcher(str(media_path), handle_new_file)
                
    except Exception as e:
        print(f"Startup error: {e}")
    
    yield
    
    # Shutdown
    if file_watcher:
        file_watcher.stop()
        file_watcher.join()

app = FastAPI(
    title=settings.APP_NAME, 
    description="Backend for the Living Museum Interface", 
    debug=settings.DEBUG,
    lifespan=lifespan
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

# Development-safe fallback: ensure CORS header is present even for error responses or
# paths that might bypass normal middleware handling (helps when server restarts or
# an unexpected error occurs while debugging front-end CORS failures).
@app.middleware("http")
async def _ensure_cors_header(request: Request, call_next):
    response = await call_next(request)
    try:
        origin = request.headers.get("origin")
        if origin and origin in cors_origins and "access-control-allow-origin" not in (k.lower() for k in response.headers.keys()):
            response.headers["Access-Control-Allow-Origin"] = origin
            # Mirror credentials policy configured for CORS middleware
            if settings.DEBUG:
                # In debug we always allow the browser to send credentials to local dev server
                response.headers.setdefault("Access-Control-Allow-Credentials", "true")
    except Exception:
        # If anything goes wrong here, don't block the response
        pass
    return response

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
app.include_router(favorites_router)
app.include_router(bulk_router)
app.include_router(indexing_router)
app.include_router(sources_router)
app.include_router(trash_router)

# Startup and shutdown now handled by lifespan context manager above

# Register the endpoints with API version manager
api_version_manager.register_endpoint(
    path="/search",
    method="GET",
    summary="Search Photos",
    description="Unified search endpoint supporting metadata, semantic, and hybrid search modes"
)

api_version_manager.register_endpoint(
    path="/search/semantic",
    method="GET",
    summary="Semantic Search",
    description="Semantic search using CLIP embeddings"
)

from server.core.components import (
    code_splitting_config,
    face_clusterer,
    lazy_load_tracker,
    modal_system,
    ocr_search,
    tauri_integration,
    video_analyzer,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

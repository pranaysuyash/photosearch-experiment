"""
Main Application with Advanced Features Integration

This module integrates all advanced features into the main FastAPI application.
It extends the existing main.py to include face recognition, duplicate detection,
OCR text search, smart albums, and analytics functionality.
"""

from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from datetime import datetime
import json
import uuid

# Import existing main functionality
from .main import (
    app,
    ps_logger,
    photo_search_engine,
)
from .services.semantic_indexing import process_semantic_indexing
from .config import settings
from .watcher import start_watcher
from .embedding_generator import EmbeddingGenerator
from src.logging_config import setup_logging

# Import advanced features
from .advanced_features_api import (
    setup_advanced_features_routes,
    AdvancedFeaturesManager,
)

# Initialize advanced features manager
advanced_features_manager: Optional[AdvancedFeaturesManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced lifespan manager with advanced features"""
    global advanced_features_manager

    # Existing startup code
    print("Initializing logging...")
    try:
        ps_logger, perf_tracker = setup_logging(log_level="INFO", log_file="logs/app.log")
        print("Logging initialized.")
    except Exception as e:
        print(f"Logging setup error: {e}")
        import logging

        logging.basicConfig(level=logging.INFO)
        ps_logger = logging.getLogger("PhotoSearch")
        from ..src.logging_config import PerformanceTracker

        PerformanceTracker(ps_logger)

    print("Initializing Embedding Model...")
    try:
        embedding_generator = EmbeddingGenerator()
        print("Embedding Model Loaded.")

        # Auto-scan 'media' directory on startup
        media_path = settings.BASE_DIR / "media"
        if media_path.exists():
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
                    from ..src.metadata_extractor import extract_all_metadata

                    metadata = extract_all_metadata(filepath)
                    if metadata:
                        photo_search_engine.db.store_metadata(filepath, metadata)
                        print(f"Metadata indexed: {filepath}")

                        # Trigger Semantic Indexing (requires deps)
                        # Note: This uses the globally initialized embedding_generator
                        # and photo_search_engine's vector_store
                        try:
                            from .core.stores import vector_store

                            if embedding_generator and vector_store:
                                process_semantic_indexing([filepath], embedding_generator, vector_store)
                        except Exception as si_err:
                            print(f"Semantic indexing failed for {filepath}: {si_err}")
                except Exception as e:
                    print(f"Real-time indexing failed for {filepath}: {e}")

            print("Starting file watcher...")
            start_watcher(str(media_path), handle_new_file)

    except Exception as e:
        print(f"Startup error: {e}")

    # Initialize advanced features
    print("Initializing Advanced Features...")
    try:
        advanced_features_manager = AdvancedFeaturesManager(settings.BASE_DIR)
        await advanced_features_manager.initialize()
        print("Advanced Features initialized successfully.")
    except Exception as e:
        print(f"Advanced Features initialization error: {e}")
        advanced_features_manager = None

    # Set up advanced features routes
    if advanced_features_manager:
        setup_advanced_features_routes(app)
        print("Advanced Features routes registered.")

    yield

    # Shutdown
    print("Shutting down...")
    if advanced_features_manager:
        # Close any open connections
        pass


# Update the app with enhanced lifespan
app.router.lifespan_context = lifespan


# Enhanced endpoints with advanced features integration
@app.get("/api/advanced/status")
async def get_advanced_features_status():
    """Get status of all advanced features"""
    global advanced_features_manager

    if not advanced_features_manager:
        return {"status": "not_initialized", "features": {}}

    try:
        status = {
            "status": "initialized",
            "features": {
                "face_recognition": {
                    "available": advanced_features_manager.face_clusterer is not None,
                    "models_loaded": advanced_features_manager.face_clusterer.models_loaded
                    if advanced_features_manager.face_clusterer
                    else False,
                    "device_info": "N/A",
                },
                "duplicate_detection": {"available": advanced_features_manager.duplicate_detector is not None},
                "ocr_search": {
                    "available": advanced_features_manager.ocr_search is not None,
                    "tesseract_available": advanced_features_manager.ocr_search.tesseract_available
                    if advanced_features_manager.ocr_search
                    else False,
                    "handwriting_available": advanced_features_manager.ocr_search.enable_handwriting
                    if advanced_features_manager.ocr_search
                    else False,
                },
                "smart_albums": {
                    "available": True  # Always available as part of existing system
                },
                "analytics": {
                    "available": True  # Always available
                },
            },
            "active_jobs": len(advanced_features_manager.active_jobs),
            "timestamp": datetime.now().isoformat(),
        }

        # Add face recognition device info if available
        if advanced_features_manager.face_clusterer:
            stats = advanced_features_manager.face_clusterer.get_stats()
            status["features"]["face_recognition"]["device_info"] = stats.get("device_info", "N/A")

        return status

    except Exception as e:
        ps_logger.error(f"Error getting advanced features status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/advanced/scan-directory")
async def scan_directory_with_all_features(
    directory_path: str = Body(..., embed=True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    scan_faces: bool = Body(True),
    scan_duplicates: bool = Body(True),
    scan_ocr: bool = Body(True),
):
    """Scan directory with all advanced features enabled"""
    global advanced_features_manager

    if not advanced_features_manager:
        raise HTTPException(status_code=503, detail="Advanced features not available")

    # Validate directory exists
    if not Path(directory_path).exists():
        raise HTTPException(status_code=400, detail="Directory does not exist")

    job_ids: list[str] = []

    try:
        # Start face scanning if requested
        if scan_faces and advanced_features_manager.face_clusterer:
            job_id = advanced_features_manager.generate_job_id("comprehensive_face_scan")
            job_ids.append(job_id)

            async def face_scan_task():
                try:
                    advanced_features_manager.update_job_status(job_id, "processing", "Starting face scanning...", 0)
                    results = advanced_features_manager.face_clusterer.process_directory(
                        directory_path, show_progress=True
                    )
                    advanced_features_manager.update_job_status(
                        job_id,
                        "completed",
                        f"Face scan complete: {results['faces_detected']} faces found",
                        100,
                    )
                    advanced_features_manager.active_jobs[job_id]["results"] = results
                except Exception as e:
                    advanced_features_manager.update_job_status(job_id, "failed", f"Face scan failed: {str(e)}", None)

            background_tasks.add_task(face_scan_task)

        # Start duplicate scanning if requested
        if scan_duplicates and advanced_features_manager.duplicate_detector:
            job_id = advanced_features_manager.generate_job_id("comprehensive_duplicate_scan")
            job_ids.append(job_id)

            async def duplicate_scan_task():
                try:
                    advanced_features_manager.update_job_status(
                        job_id, "processing", "Starting duplicate scanning...", 0
                    )
                    results = advanced_features_manager.duplicate_detector.scan_directory(
                        directory_path, show_progress=True
                    )
                    advanced_features_manager.update_job_status(
                        job_id,
                        "completed",
                        f"Duplicate scan complete: {results['groups_created']} groups found",
                        100,
                    )
                    advanced_features_manager.active_jobs[job_id]["results"] = results
                except Exception as e:
                    advanced_features_manager.update_job_status(
                        job_id, "failed", f"Duplicate scan failed: {str(e)}", None
                    )

            background_tasks.add_task(duplicate_scan_task)

        # Start OCR scanning if requested
        if scan_ocr and advanced_features_manager.ocr_search:
            job_id = advanced_features_manager.generate_job_id("comprehensive_ocr_scan")
            job_ids.append(job_id)

            async def ocr_scan_task():
                try:
                    advanced_features_manager.update_job_status(job_id, "processing", "Starting OCR scanning...", 0)

                    # Get image files
                    image_extensions = {
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".bmp",
                        ".tiff",
                        ".webp",
                    }
                    image_files = []
                    directory = Path(directory_path)

                    for ext in image_extensions:
                        image_files.extend(directory.glob(f"*{ext}"))
                        image_files.extend(directory.glob(f"*{ext.upper()}"))

                    # Process images for OCR
                    image_paths = [str(f) for f in image_files]
                    results = []

                    for i, img_path in enumerate(image_paths):
                        ocr_result = advanced_features_manager.ocr_search.extract_text(img_path)
                        if ocr_result.text_regions:
                            advanced_features_manager.ocr_search._store_ocr_result(ocr_result)
                            results.append(ocr_result)

                        progress = ((i + 1) / len(image_paths)) * 100
                        advanced_features_manager.update_job_status(
                            job_id,
                            "processing",
                            f"OCR progress: {i+1}/{len(image_paths)} images",
                            progress,
                        )

                    advanced_features_manager.update_job_status(
                        job_id,
                        "completed",
                        f"OCR scan complete: {len(results)} images processed",
                        100,
                    )
                    advanced_features_manager.active_jobs[job_id]["results"] = results
                except Exception as e:
                    advanced_features_manager.update_job_status(job_id, "failed", f"OCR scan failed: {str(e)}", None)

            background_tasks.add_task(ocr_scan_task)

        return {
            "status": "started",
            "message": f"Comprehensive scan started for {directory_path}",
            "job_ids": job_ids,
            "features_enabled": {
                "face_recognition": scan_faces,
                "duplicate_detection": scan_duplicates,
                "ocr_search": scan_ocr,
            },
        }

    except Exception as e:
        ps_logger.error(f"Error starting comprehensive scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/advanced/comprehensive-stats")
async def get_comprehensive_statistics():
    """Get comprehensive statistics from all features"""
    global advanced_features_manager

    stats = {
        "library_stats": {"total_photos": 0, "total_size_gb": 0, "new_photos": 0},
        "face_recognition": {},
        "duplicate_detection": {},
        "ocr_processing": {},
        "smart_albums": {},
        "analytics": {},
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Face recognition stats
        if advanced_features_manager and advanced_features_manager.face_clusterer:
            stats["face_recognition"] = advanced_features_manager.face_clusterer.get_stats()

        # Duplicate detection stats
        if advanced_features_manager and advanced_features_manager.duplicate_detector:
            stats["duplicate_detection"] = advanced_features_manager.duplicate_detector.stats

        # OCR stats
        if advanced_features_manager and advanced_features_manager.ocr_search:
            stats["ocr_processing"] = advanced_features_manager.ocr_search.get_stats()

        # Active jobs
        if advanced_features_manager:
            stats["active_jobs"] = len(advanced_features_manager.active_jobs)

        # Get basic library stats from existing system
        try:
            # This would query your existing database for basic stats
            stats["library_stats"]["total_photos"] = len(
                list(Path(settings.BASE_DIR / "media").glob("**/*.{jpg,jpeg,png,bmp,tiff,webp}"))
            )
            # Calculate total size
            total_size = sum(
                f.stat().st_size
                for f in Path(settings.BASE_DIR / "media").rglob("*")
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
            )
            stats["library_stats"]["total_size_gb"] = total_size / (1024**3)
        except Exception as e:
            ps_logger.warning(f"Error getting basic library stats: {e}")

        return stats

    except Exception as e:
        ps_logger.error(f"Error getting comprehensive statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Enhanced error handler for advanced features
@app.exception_handler(Exception)
async def advanced_features_exception_handler(request: Request, exc: Exception):
    """Enhanced exception handler for advanced features"""
    ps_logger.error(f"Unhandled exception in advanced features: {exc}", exc_info=True)

    return Response(
        content=json.dumps(
            {
                "error": "Internal server error",
                "message": "An error occurred while processing your request",
                "timestamp": datetime.now().isoformat(),
                "request_id": str(uuid.uuid4()),
            }
        ),
        status_code=500,
        media_type="application/json",
    )


# Enhanced CORS for advanced features API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log advanced features initialization
if __name__ == "__main__":
    import uvicorn

    print("Starting Photo Search Application with Advanced Features...")
    print("Features: Face Recognition, Duplicate Detection, OCR, Smart Albums, Analytics")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

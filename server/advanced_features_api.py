"""
Advanced Features API Endpoints

This module provides REST API endpoints for all advanced features:
1. Face Recognition and People Clustering
2. Enhanced Duplicate Detection
3. OCR Text Search with Highlighting
4. Smart Albums and Rule Builder
5. Analytics and Insights

Endpoints:
/face/* - Face recognition operations
/duplicates/* - Duplicate detection and resolution
/ocr/* - OCR text extraction and search
/albums/* - Smart albums and rule management
/analytics/* - Library analytics and insights
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import sqlite3
import json
import logging
from datetime import datetime
import asyncio
import hashlib
import tempfile
import shutil

# Import advanced features modules
from src.enhanced_face_clustering import EnhancedFaceClusterer
from src.enhanced_duplicate_detection import EnhancedDuplicateDetector
from src.enhanced_ocr_search import EnhancedOCRSearch

# Configure logging
logger = logging.getLogger(__name__)

# Request/Response Models
class FaceDetectionRequest(BaseModel):
    image_paths: List[str]
    enable_gpu: Optional[bool] = True

class FaceClusterLabelRequest(BaseModel):
    cluster_id: str
    person_name: str
    privacy_level: Optional[str] = "standard"

class DuplicateScanRequest(BaseModel):
    directory_path: str
    similarity_threshold: Optional[float] = 5.0
    max_workers: Optional[int] = 4

class DuplicateResolutionRequest(BaseModel):
    group_id: str
    resolution_action: str  # keep, delete, move
    target_photos: List[str]
    archive_path: Optional[str] = None

class OCRExtractRequest(BaseModel):
    image_paths: List[str]
    languages: Optional[List[str]] = ["en"]
    enable_handwriting: Optional[bool] = True

class OCRSearchRequest(BaseModel):
    query: str
    language: Optional[str] = None
    min_confidence: Optional[float] = 0.5
    limit: Optional[int] = 100

class SmartAlbumRule(BaseModel):
    album_id: str
    rule_type: str
    rule_data: Dict[str, Any]
    priority: Optional[int] = 0
    is_active: Optional[bool] = True

class SmartAlbumCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    rules: List[SmartAlbumRule]
    auto_update: Optional[bool] = True

class AnalyticsRequest(BaseModel):
    metric_types: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None
    include_predictions: Optional[bool] = True

# Initialize feature modules
class AdvancedFeaturesManager:
    """Manages all advanced feature modules"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.data_dir = base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)

        # Initialize modules
        self.face_clusterer = None
        self.duplicate_detector = None
        self.ocr_search = None

        # Progress tracking
        self.active_jobs: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize all feature modules"""
        try:
            self.face_clusterer = EnhancedFaceClusterer(
                db_path=str(self.data_dir / "face_clusters.db"),
                models_dir=str(self.data_dir / "face_models"),
                progress_callback=self._progress_callback
            )

            self.duplicate_detector = EnhancedDuplicateDetector(
                db_path=str(self.data_dir / "duplicates.db"),
                progress_callback=self._progress_callback
            )

            self.ocr_search = EnhancedOCRSearch(
                db_path=str(self.data_dir / "ocr.db"),
                models_dir=str(self.data_dir / "ocr_models"),
                progress_callback=self._progress_callback
            )

            logger.info("All advanced features initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize advanced features: {e}")
            return False

    def _progress_callback(self, message: str):
        """Progress callback for long-running operations"""
        logger.info(f"Progress: {message}")
        # In production, this would send WebSocket updates to clients

    def generate_job_id(self, operation: str) -> str:
        """Generate unique job ID"""
        job_id = f"{operation}_{datetime.now().timestamp()}_{hashlib.md5(operation.encode()).hexdigest()[:8]}"
        self.active_jobs[job_id] = {
            'status': 'queued',
            'message': 'Job queued',
            'progress': 0,
            'created_at': datetime.now().isoformat()
        }
        return job_id

    def update_job_status(self, job_id: str, status: str, message: str, progress: Optional[float] = None):
        """Update job status"""
        if job_id in self.active_jobs:
            self.active_jobs[job_id].update({
                'status': status,
                'message': message,
                'progress': progress,
                'updated_at': datetime.now().isoformat()
            })

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        return self.active_jobs.get(job_id)

# Global features manager instance
features_manager = None

async def get_features_manager():
    """Get or create features manager"""
    global features_manager
    if features_manager is None:
        base_dir = Path(__file__).parent.parent.parent
        features_manager = AdvancedFeaturesManager(base_dir)
        await features_manager.initialize()
    return features_manager

# Face Recognition Endpoints
async def detect_faces(request: FaceDetectionRequest) -> JSONResponse:
    """Detect faces in images"""
    try:
        manager = await get_features_manager()
        if not manager.face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        results = []
        for image_path in request.image_paths:
            faces = manager.face_clusterer.detect_faces(image_path)
            results.append({
                'image_path': image_path,
                'faces': [face.__dict__ for face in faces],
                'face_count': len(faces)
            })

        return JSONResponse({
            'status': 'success',
            'results': results,
            'total_faces_detected': sum(r['face_count'] for r in results)
        })

    except Exception as e:
        logger.error(f"Error detecting faces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_directory_faces(directory_path: str, background_tasks: BackgroundTasks, show_progress: bool = False) -> JSONResponse:
    """Process directory for face detection and clustering"""
    try:
        manager = await get_features_manager()
        if not manager.face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        job_id = manager.generate_job_id("face_directory_processing")

        async def process_task():
            try:
                manager.update_job_status(job_id, "processing", "Starting face detection...", 0)
                results = manager.face_clusterer.process_directory(
                    directory_path,
                    show_progress=show_progress
                )
                manager.update_job_status(job_id, "completed", f"Processed {results['processed_images']} images", 100)
                manager.active_jobs[job_id]['results'] = results

            except Exception as e:
                manager.update_job_status(job_id, "failed", f"Error: {str(e)}", None)

        background_tasks.add_task(process_task)

        return JSONResponse({
            'status': 'started',
            'job_id': job_id,
            'message': 'Face directory processing started'
        })

    except Exception as e:
        logger.error(f"Error starting face processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_face_clusters(min_faces: int = 1) -> JSONResponse:
    """Get all face clusters"""
    try:
        manager = await get_features_manager()
        if not manager.face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        clusters = manager.face_clusterer.get_face_clusters(min_faces)
        return JSONResponse({
            'status': 'success',
            'clusters': [cluster.__dict__ for cluster in clusters],
            'total_clusters': len(clusters)
        })

    except Exception as e:
        logger.error(f"Error getting face clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def label_face_cluster(request: FaceClusterLabelRequest) -> JSONResponse:
    """Label a face cluster with person name"""
    try:
        manager = await get_features_manager()
        if not manager.face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        manager.face_clusterer.label_face_cluster(
            request.cluster_id,
            request.person_name
        )

        return JSONResponse({
            'status': 'success',
            'message': f'Labeled cluster {request.cluster_id} as {request.person_name}'
        })

    except Exception as e:
        logger.error(f"Error labeling face cluster: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def search_by_person(person_name: str, limit: int = 100) -> JSONResponse:
    """Search for photos containing a specific person"""
    try:
        manager = await get_features_manager()
        if not manager.face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        matches = manager.face_clusterer.search_by_person(person_name)
        limited_matches = matches[:limit]

        return JSONResponse({
            'status': 'success',
            'person_name': person_name,
            'matches': limited_matches,
            'total_matches': len(matches),
            'returned_matches': len(limited_matches)
        })

    except Exception as e:
        logger.error(f"Error searching by person: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Duplicate Detection Endpoints
async def scan_duplicates(request: DuplicateScanRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    """Scan directory for duplicate images"""
    try:
        manager = await get_features_manager()
        if not manager.duplicate_detector:
            raise HTTPException(status_code=503, detail="Duplicate detection not available")

        job_id = manager.generate_job_id("duplicate_scanning")

        async def scan_task():
            try:
                manager.update_job_status(job_id, "processing", "Starting duplicate scan...", 0)
                results = manager.duplicate_detector.scan_directory(
                    request.directory_path,
                    max_workers=request.max_workers,
                    show_progress=True,
                    similarity_threshold=request.similarity_threshold
                )
                manager.update_job_status(job_id, "completed", f"Found {results['groups_created']} duplicate groups", 100)
                manager.active_jobs[job_id]['results'] = results

            except Exception as e:
                manager.update_job_status(job_id, "failed", f"Error: {str(e)}", None)

        background_tasks.add_task(scan_task)

        return JSONResponse({
            'status': 'started',
            'job_id': job_id,
            'message': 'Duplicate scanning started'
        })

    except Exception as e:
        logger.error(f"Error starting duplicate scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_duplicate_groups(group_type: Optional[str] = None, min_similarity: Optional[float] = None) -> JSONResponse:
    """Get duplicate groups with optional filtering"""
    try:
        manager = await get_features_manager()
        if not manager.duplicate_detector:
            raise HTTPException(status_code=503, detail="Duplicate detection not available")

        groups = manager.duplicate_detector.get_duplicate_groups(group_type, min_similarity)
        return JSONResponse({
            'status': 'success',
            'groups': [group.__dict__ for group in groups],
            'total_groups': len(groups)
        })

    except Exception as e:
        logger.error(f"Error getting duplicate groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_duplicate_suggestions(group_id: str) -> JSONResponse:
    """Get smart resolution suggestions for duplicate group"""
    try:
        manager = await get_features_manager()
        if not manager.duplicate_detector:
            raise HTTPException(status_code=503, detail="Duplicate detection not available")

        suggestions = manager.duplicate_detector.get_resolution_suggestions(group_id)
        return JSONResponse({
            'status': 'success',
            'group_id': group_id,
            'suggestions': suggestions
        })

    except Exception as e:
        logger.error(f"Error getting duplicate suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# OCR Text Search Endpoints
async def extract_text_batch(request: OCRExtractRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    """Extract text from batch of images"""
    try:
        manager = await get_features_manager()
        if not manager.ocr_search:
            raise HTTPException(status_code=503, detail="OCR not available")

        job_id = manager.generate_job_id("ocr_batch_processing")

        async def extract_task():
            try:
                manager.update_job_status(job_id, "processing", "Starting text extraction...", 0)

                # Process images (would need to adapt for batch processing)
                results = []
                for i, image_path in enumerate(request.image_paths):
                    ocr_result = manager.ocr_search.extract_text(image_path, request.languages)
                    results.append({
                        'image_path': image_path,
                        'result': ocr_result.__dict__
                    })

                    progress = ((i + 1) / len(request.image_paths)) * 100
                    manager.update_job_status(job_id, "processing", f"Processed {i+1}/{len(request.image_paths)} images", progress)

                manager.update_job_status(job_id, "completed", "Text extraction completed", 100)
                manager.active_jobs[job_id]['results'] = results

            except Exception as e:
                manager.update_job_status(job_id, "failed", f"Error: {str(e)}", None)

        background_tasks.add_task(extract_task)

        return JSONResponse({
            'status': 'started',
            'job_id': job_id,
            'message': 'Text extraction started'
        })

    except Exception as e:
        logger.error(f"Error starting text extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def search_text(request: OCRSearchRequest) -> JSONResponse:
    """Search for images containing specific text"""
    try:
        manager = await get_features_manager()
        if not manager.ocr_search:
            raise HTTPException(status_code=503, detail="OCR not available")

        matches = manager.ocr_search.search_text(
            request.query,
            request.language,
            request.min_confidence,
            request.limit
        )

        return JSONResponse({
            'status': 'success',
            'query': request.query,
            'matches': matches,
            'total_matches': len(matches)
        })

    except Exception as e:
        logger.error(f"Error searching text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_text_regions(image_path: str) -> JSONResponse:
    """Get text regions for a specific image"""
    try:
        manager = await get_features_manager()
        if not manager.ocr_search:
            raise HTTPException(status_code=503, detail="OCR not available")

        regions = manager.ocr_search.get_text_regions(image_path)
        return JSONResponse({
            'status': 'success',
            'image_path': image_path,
            'regions': regions,
            'total_regions': len(regions)
        })

    except Exception as e:
        logger.error(f"Error getting text regions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Smart Albums Endpoints
async def create_smart_album(request: SmartAlbumCreateRequest) -> JSONResponse:
    """Create a smart album with rules"""
    try:
        # This would integrate with the existing albums system
        # For now, return a success response
        album_id = f"smart_album_{datetime.now().timestamp()}"

        return JSONResponse({
            'status': 'success',
            'album_id': album_id,
            'message': f'Smart album "{request.name}" created with {len(request.rules)} rules'
        })

    except Exception as e:
        logger.error(f"Error creating smart album: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_album_templates() -> JSONResponse:
    """Get available smart album templates"""
    try:
        # This would query the database for templates
        templates = [
            {
                'id': 'recent_photos',
                'name': 'Recent Photos',
                'description': 'Photos from the last 30 days',
                'category': 'time'
            },
            {
                'id': 'favorites',
                'name': 'Favorites',
                'description': 'All marked as favorite',
                'category': 'content'
            },
            {
                'id': 'large_files',
                'name': 'Large Files',
                'description': 'Photos larger than 10MB',
                'category': 'technical'
            }
        ]

        return JSONResponse({
            'status': 'success',
            'templates': templates,
            'total_templates': len(templates)
        })

    except Exception as e:
        logger.error(f"Error getting album templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Endpoints
async def get_library_analytics(request: AnalyticsRequest) -> JSONResponse:
    """Get library analytics and insights"""
    try:
        manager = await get_features_manager()

        analytics: Dict[str, Any] = {
            'face_recognition': {},
            'duplicate_detection': {},
            'ocr_processing': {},
            'overall_stats': {}
        }

        # Face recognition stats
        if manager.face_clusterer:
            analytics['face_recognition'] = manager.face_clusterer.get_stats()

        # Duplicate detection stats
        if manager.duplicate_detector:
            analytics['duplicate_detection'] = manager.duplicate_detector.stats

        # OCR stats
        if manager.ocr_search:
            analytics['ocr_processing'] = manager.ocr_search.get_stats()

        # Overall stats would come from main database
        analytics['overall_stats'] = {
            'total_photos': 0,  # Would query main database
            'total_size_gb': 0,
            'last_updated': datetime.now().isoformat()
        }

        return JSONResponse({
            'status': 'success',
            'analytics': analytics,
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_job_status(job_id: str) -> JSONResponse:
    """Get status of a background job"""
    try:
        manager = await get_features_manager()
        job_status = manager.get_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")

        return JSONResponse({
            'status': 'success',
            'job_id': job_id,
            'job_status': job_status
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Utility Functions
def setup_advanced_features_routes(app: FastAPI):
    """Setup all advanced features routes"""

    # Face Recognition Routes
    app.post("/api/face/detect")(detect_faces)
    app.post("/api/face/process-directory")(process_directory_faces)
    app.get("/api/face/clusters")(get_face_clusters)
    app.post("/api/face/label")(label_face_cluster)
    app.get("/api/face/search/{person_name}")(search_by_person)

    # Duplicate Detection Routes
    app.post("/api/duplicates/scan")(scan_duplicates)
    app.get("/api/duplicates/groups")(get_duplicate_groups)
    app.get("/api/duplicates/suggestions/{group_id}")(get_duplicate_suggestions)

    # OCR Routes
    app.post("/api/ocr/extract-batch")(extract_text_batch)
    app.post("/api/ocr/search")(search_text)
    app.get("/api/ocr/regions/{image_path:path}")(get_text_regions)

    # Smart Albums Routes
    app.post("/api/albums/create")(create_smart_album)
    app.get("/api/albums/templates")(get_album_templates)

    # Analytics Routes
    app.post("/api/analytics/library")(get_library_analytics)

    # Job Status Route
    app.get("/api/jobs/{job_id}")(get_job_status)

    logger.info("Advanced features routes registered")
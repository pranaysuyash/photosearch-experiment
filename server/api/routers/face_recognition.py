"""
Face Recognition API Router

Uses Depends(get_state) for accessing shared application state.

allow-big-file: This router consolidates all face recognition endpoints
"""

import os
import json
import time
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from server.config import settings
from server.face_clustering_db import get_face_clustering_db
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/api/faces/clusters")
async def get_face_clusters(state: AppState = Depends(get_state)):
    """Get all face clusters."""
    try:
        face_clusterer = state.face_clusterer

        # Check if face clusterer is ready
        if not face_clusterer or not face_clusterer.models_loaded:
            return {
                "clusters": [],
                "message": "Face recognition models are still loading",
            }

        # Get all clusters from the pre-initialized clusterer
        result = face_clusterer.get_all_clusters(limit=100)

        # Get face clustering DB for coherence, representative face, and indexing status
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        hidden_cluster_ids = set()
        try:
            hidden_cluster_ids = {
                str(c.cluster_id) for c in face_db.get_hidden_clusters()
            }
        except Exception:
            hidden_cluster_ids = set()

        # Format for frontend
        formatted_clusters = []
        for cluster in result.get("clusters", []):
            cluster_details = face_clusterer.get_cluster_details(cluster["id"])
            if cluster_details.get("status") != "error":
                faces = cluster_details.get("faces", [])
                cluster_id_str = str(cluster["id"])

                # Check cluster coherence / mixed status
                is_mixed = False
                coherence_score = None
                if cluster.get("face_count", 0) >= 2:
                    try:
                        coherence = face_db.get_cluster_coherence(cluster_id_str)
                        is_mixed = coherence.get("is_mixed_suspected", False)
                        coherence_score = coherence.get("coherence_score")
                    except Exception:
                        pass

                # Get representative face (Phase 5.3)
                representative_face = None
                try:
                    rep = face_db.get_representative_face(cluster_id_str)
                    if rep:
                        representative_face = {
                            "detection_id": rep["detection_id"],
                            "photo_path": rep["photo_path"],
                            "quality_score": rep.get("quality_score"),
                        }
                except Exception:
                    pass

                # Get indexing status (Phase 6.1)
                indexing_disabled = False
                try:
                    status = face_db.get_person_indexing_status(cluster_id_str)
                    indexing_disabled = not status.get("enabled", True)
                except Exception:
                    pass

                formatted_clusters.append(
                    {
                        "id": cluster_id_str,
                        "label": cluster.get("label") or f"Person {cluster['id']}",
                        "face_count": cluster_details.get("face_count", 0),
                        "image_count": len(set(f.get("image_path") for f in faces)),
                        # Return face IDs for crop endpoint
                        "face_ids": [f.get("id") for f in faces[:6]],
                        # Also return image paths as fallback
                        "images": [f.get("image_path") for f in faces[:6]],
                        "created_at": cluster.get("created_at"),
                        "is_mixed": is_mixed,
                        "coherence_score": coherence_score,
                        "representative_face": representative_face,
                        "indexing_disabled": indexing_disabled,
                        "hidden": cluster_id_str in hidden_cluster_ids,
                    }
                )

        return {"clusters": formatted_clusters}
    except Exception as e:
        # Return empty clusters if face recognition is not available
        return {"clusters": [], "error": str(e)}


@router.post("/api/faces/scan")
async def scan_faces(state: AppState = Depends(get_state), limit: Optional[int] = None):
    """Scan for faces in photos. Pass limit to scan only first N photos."""
    try:
        face_clusterer = state.face_clusterer
        photo_search_engine = state.photo_search_engine

        # Check if face clusterer is ready
        if not face_clusterer or not face_clusterer.models_loaded:
            raise HTTPException(
                status_code=503,
                detail="Face recognition models are still loading. Please try again in a few seconds.",
            )

        # Get all photo paths from database
        cursor = photo_search_engine.db.conn.cursor()
        if limit:
            cursor.execute(
                "SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?",
                (limit,),
            )
        else:
            cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL")
        all_files = [row[0] for row in cursor.fetchall()]

        if not all_files:
            return {
                "status": "completed",
                "total_faces": 0,
                "clusters": [],
                "message": "No photos found to scan",
            }

        # Scan and cluster faces
        result = face_clusterer.cluster_faces(all_files, min_samples=1)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_face_scan_job(
    job_id: str, files: list, face_scan_jobs: dict, min_samples: int = 1
):
    """Background task to run face scanning with progress updates."""
    try:
        # Create new FaceClusterer in this thread to avoid SQLite threading issues
        from src.face_clustering import FaceClusterer
        import time

        bg_clusterer = FaceClusterer()

        # Wait for models to load in background
        max_wait = 60
        waited = 0
        while not bg_clusterer.models_loaded and waited < max_wait:
            time.sleep(1)
            waited += 1

        if not bg_clusterer.models_loaded:
            face_scan_jobs[job_id].update(
                {
                    "status": "error",
                    "message": "Face recognition models failed to load",
                    "error": "Model loading timeout",
                }
            )
            return

        total = len(files)
        face_scan_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "total": total,
            "current": 0,
            "current_file": "",
            "message": "Starting scan...",
            "result": None,
            "error": None,
        }

        # Process in batches to update progress
        batch_size = 10
        all_results = {"total_faces": 0, "clusters": [], "matched_to_existing": 0}

        for i in range(0, total, batch_size):
            batch = files[i : i + batch_size]
            current_file = batch[0].split("/")[-1] if batch else ""

            face_scan_jobs[job_id].update(
                {
                    "current": i,
                    "progress": int((i / total) * 100),
                    "current_file": current_file,
                    "message": f"Scanning {i+1}/{total}: {current_file}",
                }
            )

            # Process batch with thread-local clusterer
            result = bg_clusterer.cluster_faces(batch, min_samples=min_samples)
            if result.get("status") == "completed":
                all_results["total_faces"] += result.get("total_faces", 0)
                all_results["matched_to_existing"] += result.get(
                    "matched_to_existing", 0
                )
                all_results["clusters"].extend(result.get("clusters", []))

        # Complete
        face_scan_jobs[job_id].update(
            {
                "status": "completed",
                "progress": 100,
                "current": total,
                "current_file": "",
                "message": f"Scan complete! Found {all_results['total_faces']} faces",
                "result": all_results,
            }
        )

    except Exception as e:
        face_scan_jobs[job_id].update(
            {
                "status": "error",
                "message": str(e),
                "error": str(e),
            }
        )


@router.post("/api/faces/scan-async")
async def scan_faces_async(
    background_tasks: BackgroundTasks,
    state: AppState = Depends(get_state),
    limit: Optional[int] = None,
):
    """Start an async face scan job. Returns immediately with job_id for polling."""
    import uuid

    face_clusterer = state.face_clusterer
    photo_search_engine = state.photo_search_engine
    face_scan_jobs = state.face_scan_jobs

    # Check if face clusterer is ready
    if not face_clusterer or not face_clusterer.models_loaded:
        raise HTTPException(
            status_code=503,
            detail="Face recognition models are still loading.",
        )

    # Get all photo paths from database
    cursor = photo_search_engine.db.conn.cursor()
    if limit:
        cursor.execute(
            "SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?", (limit,)
        )
    else:
        cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL")
    all_files = [row[0] for row in cursor.fetchall()]

    if not all_files:
        return {
            "status": "completed",
            "job_id": None,
            "message": "No photos found to scan",
        }

    # Create job
    job_id = str(uuid.uuid4())
    face_scan_jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "total": len(all_files),
        "current": 0,
        "current_file": "",
        "message": "Job queued...",
        "result": None,
        "error": None,
    }

    # Start background task
    background_tasks.add_task(_run_face_scan_job, job_id, all_files, face_scan_jobs)

    return {
        "status": "started",
        "job_id": job_id,
        "total_files": len(all_files),
        "message": "Face scan job started",
    }


@router.get("/api/faces/scan-status/{job_id}")
async def get_scan_job_status(job_id: str, state: AppState = Depends(get_state)):
    """Get status of an async face scan job."""
    face_scan_jobs = state.face_scan_jobs

    if job_id not in face_scan_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return face_scan_jobs[job_id]


@router.post("/api/faces/scan-single")
async def scan_single_file(data: dict, state: AppState = Depends(get_state)):
    """Scan a specific file or list of files for faces."""
    try:
        face_clusterer = state.face_clusterer

        files = data.get("files", [])
        if not files:
            raise HTTPException(status_code=400, detail="No files specified")

        if not face_clusterer or not face_clusterer.models_loaded:
            raise HTTPException(
                status_code=503,
                detail="Face recognition models are still loading.",
            )

        result = face_clusterer.cluster_faces(files, min_samples=1)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/clusters/{cluster_id}/label")
async def set_cluster_label(
    cluster_id: str, label_data: dict, state: AppState = Depends(get_state)
):
    """Set label for a face cluster."""
    try:
        face_clusterer = state.face_clusterer
        label = label_data.get("label", "")

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        face_clusterer.set_cluster_label(int(cluster_id), label)
        return {"status": "success", "cluster_id": cluster_id, "label": label}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/person/{person_name}")
async def get_photos_by_person(
    person_name: str,
    state: AppState = Depends(get_state),
    limit: int = 100,
    offset: int = 0,
):
    """Get photos for a specific person/cluster."""
    try:
        face_clusterer = state.face_clusterer
        photo_search_engine = state.photo_search_engine

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        # Find cluster by label
        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT id FROM clusters WHERE label = ? LIMIT 1", (person_name,)
        )
        row = cursor.fetchone()

        if not row:
            return {"person": person_name, "photos": [], "total": 0}

        cluster_id = row[0]

        # Get photos for this cluster
        cursor.execute(
            """
            SELECT DISTINCT f.image_path
            FROM faces f
            JOIN cluster_membership cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            LIMIT ? OFFSET ?
            """,
            (cluster_id, limit, offset),
        )
        image_paths = [r[0] for r in cursor.fetchall()]

        # Get metadata for these photos
        photos = []
        for path in image_paths:
            try:
                meta = photo_search_engine.db.get_metadata(path)
                if meta:
                    photos.append(
                        {
                            "path": path,
                            "filename": os.path.basename(path),
                            "metadata": meta,
                        }
                    )
            except Exception:
                photos.append(
                    {"path": path, "filename": os.path.basename(path), "metadata": {}}
                )

        # Get total count
        cursor.execute(
            """
            SELECT COUNT(DISTINCT f.image_path)
            FROM faces f
            JOIN cluster_membership cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            """,
            (cluster_id,),
        )
        total = cursor.fetchone()[0]

        return {"person": person_name, "photos": photos, "total": total}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/faces/clusters/{cluster_id}")
async def delete_cluster(cluster_id: str, state: AppState = Depends(get_state)):
    """Delete a face cluster and its memberships."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = db.delete_face_cluster(cluster_id)

        if not success:
            raise HTTPException(
                status_code=404, detail="Cluster not found or could not be deleted"
            )

        return {"status": "success", "deleted_cluster_id": cluster_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/clusters/{cluster_id}/export")
async def export_cluster(cluster_id: str):
    """
    Export face cluster data as JSON.
    Detailed export including all face detections and metadata.
    Does NOT include vector embeddings by default.
    """
    try:
        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        data = db.get_face_cluster_export_data(cluster_id)

        if not data:
            raise HTTPException(status_code=404, detail="Cluster not found")

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DeleteAllConfirmation(BaseModel):
    confirmation: str


@router.delete("/api/faces/all")
async def delete_all_faces(body: DeleteAllConfirmation):
    """
    Delete ALL face data. Irreversible.
    Requires body: {"confirmation": "DELETE"}
    """
    if body.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail="Confirmation 'DELETE' required")

    try:
        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        stats = db.delete_all_face_data()
        return {"status": "success", "deleted": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/clusters/{cluster_id}/photos")
async def get_cluster_photos(
    cluster_id: str,
    state: AppState = Depends(get_state),
    limit: int = 100,
    offset: int = 0,
):
    """Get all photos containing faces from a specific cluster."""
    try:
        face_clusterer = state.face_clusterer
        photo_search_engine = state.photo_search_engine

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        # Get UNIQUE photos for this cluster (deduplicated)
        cursor.execute(
            """
            SELECT f.image_path, 
                   GROUP_CONCAT(f.id) as face_ids,
                   COUNT(*) as face_count,
                   MAX(f.confidence) as best_confidence
            FROM faces f
            JOIN cluster_membership cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            GROUP BY f.image_path
            ORDER BY best_confidence DESC
            LIMIT ? OFFSET ?
            """,
            (int(cluster_id), limit, offset),
        )
        rows = cursor.fetchall()

        photos = []
        for path, face_ids_str, face_count, confidence in rows:
            try:
                meta = photo_search_engine.db.get_metadata(path)
                photos.append(
                    {
                        "path": path,
                        "filename": os.path.basename(path),
                        "face_ids": [int(fid) for fid in face_ids_str.split(",")] if face_ids_str else [],
                        "face_count": face_count,
                        "confidence": confidence,
                        "metadata": meta or {},
                    }
                )
            except Exception:
                photos.append(
                    {
                        "path": path,
                        "filename": os.path.basename(path),
                        "face_ids": [int(fid) for fid in face_ids_str.split(",")] if face_ids_str else [],
                        "face_count": face_count,
                        "confidence": confidence,
                        "metadata": {},
                    }
                )

        return {"cluster_id": cluster_id, "photos": photos, "count": len(photos)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/unidentified")
async def get_unidentified_clusters(
    state: AppState = Depends(get_state), limit: int = 100, offset: int = 0
):
    """Get all clusters that have no user-assigned label (unlabeled clusters)."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        # Get clusters without labels
        cursor.execute(
            """
            SELECT c.id, c.label, COUNT(cm.face_id) as face_count
            FROM clusters c
            LEFT JOIN cluster_membership cm ON c.id = cm.cluster_id
            WHERE c.label IS NULL OR c.label = '' OR c.label LIKE 'Person %'
            GROUP BY c.id
            ORDER BY face_count DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cursor.fetchall()

        clusters = []
        for cid, label, face_count in rows:
            # Get sample faces
            cursor.execute(
                """
                SELECT f.id, f.image_path
                FROM faces f
                JOIN cluster_membership cm ON f.id = cm.face_id
                WHERE cm.cluster_id = ?
                LIMIT 4
                """,
                (cid,),
            )
            faces = cursor.fetchall()
            clusters.append(
                {
                    "id": str(cid),
                    "label": label or f"Person {cid}",
                    "face_count": face_count,
                    "face_ids": [f[0] for f in faces],
                    "images": [f[1] for f in faces],
                }
            )

        return {"clusters": clusters, "count": len(clusters)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/singletons")
async def get_singleton_clusters(
    state: AppState = Depends(get_state), limit: int = 100, offset: int = 0
):
    """Get all clusters with only 1 face (appears only once in library)."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        cursor.execute(
            """
            SELECT c.id, c.label, f.id as face_id, f.image_path, f.confidence
            FROM clusters c
            JOIN cluster_membership cm ON c.id = cm.cluster_id
            JOIN faces f ON cm.face_id = f.id
            WHERE c.id IN (
                SELECT cluster_id FROM cluster_membership
                GROUP BY cluster_id HAVING COUNT(*) = 1
            )
            ORDER BY f.confidence DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cursor.fetchall()

        singletons = []
        for cid, label, face_id, image_path, confidence in rows:
            singletons.append(
                {
                    "cluster_id": str(cid),
                    "label": label or f"Person {cid}",
                    "face_id": face_id,
                    "image_path": image_path,
                    "confidence": confidence,
                }
            )

        return {"singletons": singletons, "count": len(singletons)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/low-confidence")
async def get_low_confidence_faces(
    state: AppState = Depends(get_state),
    limit: int = 100,
    offset: int = 0,
    threshold: float = 0.8,
):
    """Get all faces with confidence below threshold."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        cursor.execute(
            """
            SELECT f.id, f.image_path, f.confidence, cm.cluster_id, c.label
            FROM faces f
            LEFT JOIN cluster_membership cm ON f.id = cm.face_id
            LEFT JOIN clusters c ON cm.cluster_id = c.id
            WHERE f.confidence < ?
            ORDER BY f.confidence ASC
            LIMIT ? OFFSET ?
            """,
            (threshold, limit, offset),
        )
        rows = cursor.fetchall()

        faces = []
        for fid, path, conf, cid, label in rows:
            faces.append(
                {
                    "face_id": fid,
                    "image_path": path,
                    "confidence": conf,
                    "cluster_id": str(cid) if cid else None,
                    "label": label,
                }
            )

        return {"faces": faces, "count": len(faces), "threshold": threshold}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/assign")
async def assign_face_to_cluster(
    face_id: int, data: dict, state: AppState = Depends(get_state)
):
    """Assign a face to an existing cluster/person."""
    try:
        face_clusterer = state.face_clusterer
        cluster_id = data.get("cluster_id")

        if not cluster_id:
            raise HTTPException(status_code=400, detail="cluster_id is required")

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        # Remove existing cluster membership if any
        cursor.execute("DELETE FROM cluster_membership WHERE face_id = ?", (face_id,))

        # Add to new cluster
        cursor.execute(
            "INSERT INTO cluster_membership (face_id, cluster_id) VALUES (?, ?)",
            (face_id, int(cluster_id)),
        )
        db.conn.commit()

        return {"status": "success", "face_id": face_id, "cluster_id": cluster_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/create-person")
async def create_person_from_face(
    face_id: int, data: dict, state: AppState = Depends(get_state)
):
    """Create a new person/cluster from an unidentified face."""
    try:
        face_clusterer = state.face_clusterer
        label = data.get("label", "")

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        # Create new cluster
        cursor.execute(
            "INSERT INTO clusters (label, created_at) VALUES (?, datetime('now'))",
            (label,),
        )
        cluster_id = cursor.lastrowid

        # Remove existing membership if any
        cursor.execute("DELETE FROM cluster_membership WHERE face_id = ?", (face_id,))

        # Assign face to new cluster
        cursor.execute(
            "INSERT INTO cluster_membership (face_id, cluster_id) VALUES (?, ?)",
            (face_id, cluster_id),
        )
        db.conn.commit()

        return {
            "status": "success",
            "face_id": face_id,
            "cluster_id": cluster_id,
            "label": label,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/photos-with-faces")
async def get_photos_with_faces(
    state: AppState = Depends(get_state), limit: int = 200, offset: int = 0
):
    """Get all photos that have at least one detected face."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT image_path, COUNT(*) as face_count
            FROM faces
            GROUP BY image_path
            ORDER BY face_count DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cursor.fetchall()

        photos = [{"path": r[0], "face_count": r[1]} for r in rows]

        return {"photos": photos, "count": len(photos)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/crop/{face_id}")
async def get_face_crop(
    face_id: int, state: AppState = Depends(get_state), size: int = 150
):
    """Get a cropped face image by face ID with intelligent caching."""
    try:
        from server.face_crop_cache import get_global_cache
        from server.face_performance_monitor import get_global_monitor
        
        face_clusterer = state.face_clusterer
        cache = get_global_cache()
        monitor = get_global_monitor()

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        # Check cache first
        face_id_str = str(face_id)
        cached_crop = cache.get_cached_crop(face_id_str, size)
        if cached_crop:
            monitor.record_cache_hit("face_crop")
            return Response(content=cached_crop, media_type="image/jpeg")

        # Cache miss - generate crop
        monitor.record_cache_miss("face_crop")
        
        start_time = time.time()
        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT image_path, bounding_box FROM faces WHERE id = ?",
            (face_id,),
        )
        row = cursor.fetchone()
        
        # Record database query performance
        db_duration = (time.time() - start_time) * 1000
        monitor.record_metric("database_query", db_duration, success=row is not None)

        if not row:
            raise HTTPException(status_code=404, detail="Face not found")

        image_path = row[0]
        bbox_raw = row[1]

        try:
            bbox = json.loads(bbox_raw) if isinstance(bbox_raw, str) else bbox_raw
            x, y, w, h = bbox
        except Exception:
            raise HTTPException(status_code=500, detail="Invalid face bounding box data")

        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file not found")

        # Crop the face
        from PIL import Image
        import io
        import time

        crop_start = time.time()
        img = Image.open(image_path)
        # Add margin
        margin = int(max(w, h) * 0.2)
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img.width, x + w + margin)
        y2 = min(img.height, y + h + margin)

        face_crop = img.crop((x1, y1, x2, y2))
        face_crop.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Generate JPEG data
        buffer = io.BytesIO()
        face_crop.save(buffer, format="JPEG", quality=85)
        crop_data = buffer.getvalue()
        
        # Record crop generation performance
        crop_duration = (time.time() - crop_start) * 1000
        monitor.record_metric("face_crop", crop_duration, success=True, 
                            face_id=face_id, size=size, cache_miss=True)

        # Cache the crop for future requests
        cache.cache_crop(
            face_id=face_id_str,
            crop_data=crop_data,
            size=size,
            source_photo_path=image_path
        )

        return Response(content=crop_data, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/stats")
async def get_face_stats_api(state: AppState = Depends(get_state)):
    """Get face recognition statistics."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            return {
                "status": "unavailable",
                "message": "Face recognition not available",
            }

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        # Total faces
        cursor.execute("SELECT COUNT(*) FROM faces")
        total_faces = cursor.fetchone()[0]

        # Total clusters
        cursor.execute("SELECT COUNT(*) FROM clusters")
        total_clusters = cursor.fetchone()[0]

        # Labeled clusters
        cursor.execute(
            "SELECT COUNT(*) FROM clusters WHERE label IS NOT NULL AND label != '' AND label NOT LIKE 'Person %'"
        )
        labeled_clusters = cursor.fetchone()[0]

        # Unlabeled clusters
        unlabeled_clusters = total_clusters - labeled_clusters

        # Photos with faces
        cursor.execute("SELECT COUNT(DISTINCT image_path) FROM faces")
        photos_with_faces = cursor.fetchone()[0]

        # Avg faces per photo
        avg_faces = total_faces / photos_with_faces if photos_with_faces > 0 else 0

        # Singletons
        cursor.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT cluster_id FROM cluster_membership
                GROUP BY cluster_id HAVING COUNT(*) = 1
            )
            """
        )
        singletons = cursor.fetchone()[0]

        return {
            "status": "available",
            "models_loaded": face_clusterer.models_loaded,
            # Field names matching frontend FaceStats interface
            "total_photos": photos_with_faces,
            "faces_detected": total_faces,
            "clusters_found": total_clusters,
            "unidentified_faces": unlabeled_clusters,
            "singletons": singletons,
            "low_confidence": 0,  # TODO: Implement low confidence count
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# People Search Endpoint


@router.get("/api/people/search")
async def search_people(
    state: AppState = Depends(get_state),
    query: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
):
    """Search for people by name or other attributes."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        if query:
            cursor.execute(
                """
                SELECT c.id, c.label, COUNT(cm.face_id) as face_count
                FROM clusters c
                LEFT JOIN cluster_membership cm ON c.id = cm.cluster_id
                WHERE c.label LIKE ?
                GROUP BY c.id
                ORDER BY face_count DESC
                LIMIT ? OFFSET ?
                """,
                (f"%{query}%", limit, offset),
            )
        else:
            cursor.execute(
                """
                SELECT c.id, c.label, COUNT(cm.face_id) as face_count
                FROM clusters c
                LEFT JOIN cluster_membership cm ON c.id = cm.cluster_id
                WHERE c.label IS NOT NULL AND c.label != '' AND c.label NOT LIKE 'Person %'
                GROUP BY c.id
                ORDER BY face_count DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )

        rows = cursor.fetchall()
        people = [{"id": str(r[0]), "name": r[1], "face_count": r[2]} for r in rows]

        return {"people": people, "count": len(people)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Person Analytics Endpoint


@router.get("/api/people/{person_id}/analytics")
async def get_person_analytics(person_id: str, state: AppState = Depends(get_state)):
    """Get analytics and insights for a specific person."""
    try:
        face_clusterer = state.face_clusterer
        photo_search_engine = state.photo_search_engine

        if not face_clusterer:
            raise HTTPException(
                status_code=503, detail="Face recognition not available"
            )

        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        cursor = db.conn.cursor()

        # Get cluster info
        cursor.execute("SELECT label FROM clusters WHERE id = ?", (int(person_id),))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Person not found")

        label = row[0] or f"Person {person_id}"

        # Get face count
        cursor.execute(
            "SELECT COUNT(*) FROM cluster_membership WHERE cluster_id = ?",
            (int(person_id),),
        )
        face_count = cursor.fetchone()[0]

        # Get photo count
        cursor.execute(
            """
            SELECT COUNT(DISTINCT f.image_path)
            FROM faces f
            JOIN cluster_membership cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            """,
            (int(person_id),),
        )
        photo_count = cursor.fetchone()[0]

        # Get date range of photos
        cursor.execute(
            """
            SELECT f.image_path
            FROM faces f
            JOIN cluster_membership cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            """,
            (int(person_id),),
        )
        paths = [r[0] for r in cursor.fetchall()]

        dates = []
        for path in paths:
            try:
                meta = photo_search_engine.db.get_metadata(path)
                if meta and meta.get("date_taken"):
                    dates.append(meta["date_taken"])
            except Exception:
                pass

        date_range = None
        if dates:
            dates.sort()
            date_range = {"earliest": dates[0], "latest": dates[-1]}

        first_seen = None
        last_seen = None
        if date_range:
            first_seen = date_range["earliest"]
            last_seen = date_range["latest"]
        elif paths:
            # Fallback to file modified dates
            import os
            from datetime import datetime
            file_dates = []
            for path in paths:
                try:
                    mtime = os.path.getmtime(path)
                    file_dates.append(datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"))
                except Exception:
                    pass
            if file_dates:
                file_dates.sort()
                first_seen = file_dates[0]
                last_seen = file_dates[-1]

        return {
            "person_id": person_id,
            "name": label,
            "face_count": face_count,
            "photo_count": photo_count,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "date_range": date_range,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Phase 0: Reversibility and Trust Endpoints
# ===================================================================


@router.post("/api/faces/clusters/{cluster_id}/hide")
async def hide_cluster(cluster_id: str, state: AppState = Depends(get_state)):
    """Hide a person cluster from the main gallery."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.set_cluster_hidden(cluster_id, hidden=True)

        if success:
            return {"success": True, "message": f"Cluster {cluster_id} hidden"}
        return {"success": False, "message": "Cluster not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/clusters/{cluster_id}/unhide")
async def unhide_cluster(cluster_id: str, state: AppState = Depends(get_state)):
    """Unhide a person cluster."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.set_cluster_hidden(cluster_id, hidden=False)

        if success:
            return {"success": True, "message": f"Cluster {cluster_id} visible again"}
        return {"success": False, "message": "Cluster not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/clusters/visible")
async def get_visible_clusters_endpoint(state: AppState = Depends(get_state)):
    """Get all non-hidden clusters."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        clusters = face_db.get_visible_clusters()

        return {
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "label": c.label,
                    "face_count": c.face_count,
                    "photo_count": c.photo_count,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in clusters
            ],
            "count": len(clusters),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/clusters/hidden")
async def get_hidden_clusters_endpoint(state: AppState = Depends(get_state)):
    """Get all hidden clusters."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        clusters = face_db.get_hidden_clusters()

        return {
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "label": c.label,
                    "face_count": c.face_count,
                    "photo_count": c.photo_count,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in clusters
            ],
            "count": len(clusters),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/confirm")
async def confirm_face(face_id: str, data: dict, state: AppState = Depends(get_state)):
    """Confirm a face assignment (user verified)."""
    try:
        cluster_id = data.get("cluster_id")
        if not cluster_id:
            raise HTTPException(status_code=400, detail="cluster_id required")

        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.confirm_face_assignment(face_id, cluster_id)

        return {
            "success": success,
            "face_id": face_id,
            "cluster_id": cluster_id,
            "state": "user_confirmed",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/reject")
async def reject_face(face_id: str, data: dict, state: AppState = Depends(get_state)):
    """Reject a face from a cluster (not this person)."""
    try:
        cluster_id = data.get("cluster_id")
        if not cluster_id:
            raise HTTPException(status_code=400, detail="cluster_id required")

        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.reject_face_from_cluster(face_id, cluster_id)

        return {
            "success": success,
            "face_id": face_id,
            "cluster_id": cluster_id,
            "state": "rejected",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/split")
async def split_faces(data: dict, state: AppState = Depends(get_state)):
    """Split selected faces into a new person cluster."""
    try:
        detection_ids = data.get("detection_ids", [])
        new_label = data.get("label")

        if not detection_ids:
            raise HTTPException(
                status_code=400,
                detail="detection_ids required (list of face detection IDs)",
            )

        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        new_cluster_id = face_db.split_faces_to_new_person(detection_ids, new_label)

        return {
            "success": True,
            "new_cluster_id": new_cluster_id,
            "faces_moved": len(detection_ids),
            "label": new_label,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/move")
async def move_face(data: dict, state: AppState = Depends(get_state)):
    """Move a single face to a different cluster."""
    try:
        detection_id = data.get("detection_id")
        to_cluster_id = data.get("to_cluster_id")

        if not detection_id or not to_cluster_id:
            raise HTTPException(
                status_code=400, detail="detection_id and to_cluster_id required"
            )

        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.move_face_to_cluster(detection_id, to_cluster_id)

        return {
            "success": success,
            "detection_id": detection_id,
            "to_cluster_id": to_cluster_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/merge")
async def merge_clusters_endpoint(data: dict, state: AppState = Depends(get_state)):
    """Merge source cluster into target cluster with full undo support."""
    try:
        source_cluster_id = data.get("source_cluster_id")
        target_cluster_id = data.get("target_cluster_id")

        if not source_cluster_id or not target_cluster_id:
            raise HTTPException(
                status_code=400,
                detail="source_cluster_id and target_cluster_id required",
            )

        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.merge_clusters_with_undo(source_cluster_id, target_cluster_id)

        return {
            "success": success,
            "source_cluster_id": source_cluster_id,
            "target_cluster_id": target_cluster_id,
            "message": f"Merged {source_cluster_id} into {target_cluster_id}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/undo")
async def undo_operation(state: AppState = Depends(get_state)):
    """Undo the last person operation (merge/split/move/hide/rename)."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        result = face_db.undo_last_operation()

        if result:
            return {"success": result.get("undone", False), **result}
        return {"success": False, "message": "No operation to undo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/undo/status")
async def undo_status(state: AppState = Depends(get_state)):
    """Check if there is an operation that can be undone."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        status = face_db.get_undo_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/unassigned")
async def get_unassigned_faces_endpoint(
    state: AppState = Depends(get_state), limit: int = 100, offset: int = 0
):
    """Get faces not assigned to any cluster (Unknown bucket)."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        faces = face_db.get_unassigned_faces(limit=limit, offset=offset)
        total = face_db.get_unassigned_face_count()

        return {
            "faces": faces,
            "count": len(faces),
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/clusters/{cluster_id}/rename")
async def rename_cluster_endpoint(
    cluster_id: str, data: dict, state: AppState = Depends(get_state)
):
    """Rename a cluster with undo support."""
    try:
        new_label = data.get("label")
        if new_label is None:
            raise HTTPException(status_code=400, detail="label required")

        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.rename_cluster_with_undo(cluster_id, new_label)

        return {"success": success, "cluster_id": cluster_id, "label": new_label}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/prototypes/recompute")
async def recompute_prototypes(state: AppState = Depends(get_state)):
    """Recompute prototype embeddings for all clusters."""
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        face_db.recompute_all_prototypes()

        return {"success": True, "message": "Prototypes recomputed for all clusters"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Phase 2: Trust Signals Endpoints
# ===================================================================


@router.get("/api/faces/clusters/{cluster_id}/coherence")
async def get_cluster_coherence(cluster_id: str, state: AppState = Depends(get_state)):
    """
    Get coherence analysis for a cluster.

    Returns metrics to detect if a cluster might contain multiple people:
    - coherence_score: 0-1 (higher = more likely single person)
    - variance: embedding variance
    - low_quality_ratio: fraction of low-quality faces
    - is_mixed_suspected: boolean flag
    """
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        result = face_db.get_cluster_coherence(cluster_id)

        return {"cluster_id": cluster_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/mixed-clusters")
async def get_mixed_clusters(
    state: AppState = Depends(get_state), threshold: float = 0.5
):
    """
    Get all clusters suspected to contain multiple people.

    Returns clusters sorted by coherence (worst first).
    """
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        clusters = face_db.get_mixed_clusters(threshold=threshold)

        return {"clusters": clusters, "count": len(clusters)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Phase 3: Speed & Scale Endpoints
# ===================================================================


class AssignFaceRequest(BaseModel):
    detection_id: str
    embedding: List[float]  # Will be converted to numpy array
    auto_assign_min: float = 0.55
    review_min: float = 0.50


class BatchAssignRequest(BaseModel):
    faces: List[Dict[str, Any]]  # List of {detection_id, embedding}
    auto_assign_min: float = 0.55
    review_min: float = 0.50


@router.post("/api/faces/assign")
async def assign_face_by_prototype(
    request: AssignFaceRequest, state: AppState = Depends(get_state)
):
    """
    Assign a single face to the best matching cluster using prototype matching.

    Returns assignment action (auto_assign, review, or unknown) and best match info.
    """
    try:
        from pathlib import Path
        import numpy as np

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        embedding = np.array(request.embedding, dtype=np.float32)

        result = face_db.assign_new_face(
            detection_id=request.detection_id,
            embedding=embedding,
            auto_assign_min=request.auto_assign_min,
            review_min=request.review_min,
        )

        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/batch-assign")
async def batch_assign_faces(
    request: BatchAssignRequest, state: AppState = Depends(get_state)
):
    """
    Assign multiple faces to clusters efficiently.

    Builds the embedding index once and processes all faces.
    Returns summary counts and individual results.
    """
    try:
        from pathlib import Path
        import numpy as np

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        # Convert to list of tuples
        faces = [
            (f["detection_id"], np.array(f["embedding"], dtype=np.float32))
            for f in request.faces
        ]

        results = face_db.batch_assign_new_faces(
            faces=faces,
            auto_assign_min=request.auto_assign_min,
            review_min=request.review_min,
        )

        # Calculate summary
        auto_count = sum(1 for r in results.values() if r["action"] == "auto_assign")
        review_count = sum(1 for r in results.values() if r["action"] == "review")
        unknown_count = sum(1 for r in results.values() if r["action"] == "unknown")

        return {
            "success": True,
            "summary": {
                "total": len(results),
                "auto_assigned": auto_count,
                "review_needed": review_count,
                "unknown": unknown_count,
            },
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/index/stats")
async def get_embedding_index_stats(state: AppState = Depends(get_state)):
    """
    Get statistics about the embedding index.

    Returns count of prototypes, backend type, and performance metrics.
    """
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        index = face_db.build_embedding_index()
        stats = index.get_stats() if hasattr(index, 'get_stats') else {}

        return {
            "success": True,
            "prototype_count": index.count(),
            "backend": stats.get("index_type", "unknown"),
            "memory_usage_mb": stats.get("memory_usage_mb", 0),
            "dimension": stats.get("dimension", 512),
            "message": f"Index ready with {index.count()} cluster prototypes using {stats.get('index_type', 'unknown')} backend",
            "performance_tier": "production" if stats.get("index_type") == "faiss" else "development"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Phase 4: Search & Retrieval Endpoints
# ===================================================================


@router.get("/api/faces/{detection_id}/similar")
async def find_similar_faces(
    detection_id: str,
    state: AppState = Depends(get_state),
    limit: int = 20,
    threshold: float = 0.5,
    include_same_cluster: bool = False,
):
    """
    Find faces similar to a given face detection.

    "Find more like this face" feature for:
    - Discovering unclustered similar faces
    - Finding potential merge candidates
    - Quality control
    """
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        faces = face_db.find_similar_faces(
            detection_id=detection_id,
            limit=limit,
            threshold=threshold,
            include_same_cluster=include_same_cluster,
        )

        return {
            "detection_id": detection_id,
            "similar_faces": faces,
            "count": len(faces),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoOccurrenceRequest(BaseModel):
    include_people: List[str]  # Cluster IDs that must appear
    exclude_people: Optional[List[str]] = None  # Cluster IDs that must NOT appear
    require_all: bool = True  # AND vs OR logic
    limit: int = 100
    offset: int = 0


@router.post("/api/photos/by-people")
async def search_photos_by_people_ids(
    request: CoOccurrenceRequest, state: AppState = Depends(get_state)
):
    """
    Find photos based on co-occurrence of people.

    Examples:
    - Photos with Alice AND Bob: include_people=['alice_id', 'bob_id'], require_all=True
    - Photos with Alice OR Bob: include_people=['alice_id', 'bob_id'], require_all=False
    - Photos with Alice but NOT Bob: include_people=['alice_id'], exclude_people=['bob_id']
    """
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        result = face_db.get_photos_with_people(
            include_people=request.include_people,
            exclude_people=request.exclude_people,
            require_all=request.require_all,
            limit=request.limit,
            offset=request.offset,
        )

        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/photos/by-people-names")
async def search_photos_by_people_names(
    state: AppState = Depends(get_state),
    query: str = "",
    mode: str = "and",
    limit: int = 100,
    offset: int = 0,
):
    """
    Search photos by people names with natural language-like queries.

    Supports queries like:
    - "Alice" - Photos with Alice
    - "Alice Bob" (mode=and) - Photos with Alice AND Bob
    - "Alice Bob" (mode=or) - Photos with Alice OR Bob
    - "Alice !Bob" or "Alice -Bob" - Photos with Alice but NOT Bob
    """
    try:
        from pathlib import Path

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        result = face_db.search_photos_by_people(
            query=query, mode=mode, limit=limit, offset=offset
        )

        return {"success": True, "query": query, "mode": mode, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/photos/{photo_path:path}/people")
async def get_people_in_photo(photo_path: str, state: AppState = Depends(get_state)):
    """
    Get all people detected in a specific photo.

    Returns list of people with cluster info and face detection details.
    """
    try:
        from pathlib import Path
        import urllib.parse

        # URL decode the path
        decoded_path = urllib.parse.unquote(photo_path)

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))

        # get_people_in_photo returns List[PhotoPersonAssociation]
        associations = face_db.get_people_in_photo(decoded_path)

        # Convert to dict for JSON serialization
        people = [
            {
                "photo_path": assoc.photo_path,
                "cluster_id": assoc.cluster_id,
                "detection_id": assoc.detection_id,
                "confidence": assoc.confidence,
                "created_at": assoc.created_at,
            }
            for assoc in associations
        ]

        return {"photo_path": decoded_path, "people": people, "count": len(people)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Phase 5.4: Merge Suggestions Endpoints
# ===================================================================


@router.get("/api/faces/clusters/merge-suggestions")
async def get_merge_suggestions(
    state: AppState = Depends(get_state),
    threshold: float = 0.62,
    max_suggestions: int = 10,
):
    """
    Get conservative merge suggestions for face clusters.

    Suggests merging clusters only when:
    1. Prototype similarity >= threshold (default 0.62)
    2. NO co-occurrence conflict (clusters never appear in same photo)

    Co-occurrence conflict is a HARD BLOCK - never suggests merging
    clusters that appear in the same photo (likely different people).
    """
    try:
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        suggestions = face_db.get_merge_suggestions(
            similarity_threshold=threshold, max_suggestions=max_suggestions
        )
        return {
            "suggestions": suggestions,
            "count": len(suggestions),
            "threshold": threshold,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/clusters/merge-suggestions/dismiss")
async def dismiss_merge_suggestion(
    data: dict,
    state: AppState = Depends(get_state),
):
    """
    Dismiss a merge suggestion so it won't appear again.
    """
    try:
        cluster_a_id = data.get("cluster_a_id")
        cluster_b_id = data.get("cluster_b_id")

        if not cluster_a_id or not cluster_b_id:
            raise HTTPException(
                status_code=400, detail="cluster_a_id and cluster_b_id are required"
            )

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.dismiss_merge_suggestion(cluster_a_id, cluster_b_id)

        return {"success": success}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Phase 5: Review Queue Endpoints
# ===================================================================


@router.get("/api/faces/review-queue")
async def get_review_queue(
    state: AppState = Depends(get_state),
    limit: int = 20,
    offset: int = 0,
    sort: str = "similarity_desc",
):
    """Get pending items from the review queue."""
    try:
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        items = face_db.get_review_queue(limit=limit, offset=offset, sort=sort)
        total = face_db.get_review_queue_count()
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/review-queue/count")
async def get_review_queue_count(state: AppState = Depends(get_state)):
    """Get count of pending items in review queue."""
    try:
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        count = face_db.get_review_queue_count()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ResolveRequest(BaseModel):
    action: str  # 'confirm', 'reject', 'skip'
    cluster_id: Optional[str] = None


@router.post("/api/faces/review-queue/{detection_id}/resolve")
async def resolve_review_item(
    detection_id: str,
    request: ResolveRequest,
    state: AppState = Depends(get_state),
):
    """Resolve a review queue item (confirm, reject, or skip)."""
    try:
        if request.action not in ("confirm", "reject", "skip"):
            raise HTTPException(
                status_code=400,
                detail="action must be 'confirm', 'reject', or 'skip'",
            )

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.resolve_review_item(
            detection_id=detection_id,
            action=request.action,
            cluster_id=request.cluster_id,
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Review item not found or already resolved",
            )

        return {
            "success": True,
            "detection_id": detection_id,
            "action": request.action,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Phase 6: Privacy Control Endpoints
# ===================================================================


@router.get("/api/faces/clusters/{cluster_id}/indexing")
async def get_person_indexing_status(
    cluster_id: str,
    state: AppState = Depends(get_state),
):
    """Get indexing status for a specific person cluster."""
    try:
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        status = face_db.get_person_indexing_status(cluster_id)

        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])

        return {"cluster_id": cluster_id, **status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/clusters/{cluster_id}/indexing")
async def set_person_indexing_status(
    cluster_id: str,
    data: dict,
    state: AppState = Depends(get_state),
):
    """
    Enable or disable auto-assignment to a specific person cluster.

    When disabled, new face detections will NOT be auto-assigned to this person.
    Used when user wants to manually control a person's cluster.
    """
    try:
        enabled = data.get("enabled", True)
        reason = data.get("reason")

        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.set_person_indexing_enabled(cluster_id, enabled, reason)

        return {
            "success": success,
            "cluster_id": cluster_id,
            "enabled": enabled,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/indexing/status")
async def get_global_indexing_status(state: AppState = Depends(get_state)):
    """Get global face indexing pause status."""
    try:
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        paused = face_db.is_face_indexing_paused()

        return {
            "paused": paused,
            "status": "paused" if paused else "active",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/indexing/pause")
async def pause_global_indexing(state: AppState = Depends(get_state)):
    """Pause all global face indexing and auto-assignment."""
    try:
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.set_face_indexing_paused(True)

        return {"success": success, "status": "paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/indexing/resume")
async def resume_global_indexing(state: AppState = Depends(get_state)):
    """Resume global face indexing and auto-assignment."""
    try:
        face_db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        success = face_db.set_face_indexing_paused(False)

        return {"success": success, "status": "active"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Face Crop Cache Management Endpoints
# ===================================================================


@router.get("/api/faces/cache/stats")
async def get_face_cache_stats(state: AppState = Depends(get_state)):
    """Get face crop cache statistics and health information."""
    try:
        from server.face_crop_cache import get_global_cache
        
        cache = get_global_cache()
        stats = cache.get_stats()
        
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/cache/clear")
async def clear_face_cache(state: AppState = Depends(get_state)):
    """Clear all cached face crops to free up disk space."""
    try:
        from server.face_crop_cache import get_global_cache
        
        cache = get_global_cache()
        cache.clear_cache()
        
        return {
            "success": True,
            "message": "Face crop cache cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/cache/invalidate/{face_id}")
async def invalidate_face_cache(face_id: str, state: AppState = Depends(get_state)):
    """Invalidate cached crops for a specific face (useful after face updates)."""
    try:
        from server.face_crop_cache import get_global_cache
        
        cache = get_global_cache()
        cache.invalidate_face(face_id)
        
        return {
            "success": True,
            "face_id": face_id,
            "message": f"Cache invalidated for face {face_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Database Optimization Endpoints
# ===================================================================


@router.get("/api/faces/database/stats")
async def get_face_database_stats(state: AppState = Depends(get_state)):
    """Get comprehensive face database statistics and health metrics."""
    try:
        from server.face_db_optimizer import get_face_database_stats
        
        stats = get_face_database_stats(Path(settings.FACE_CLUSTERS_DB_PATH))
        
        return {
            "success": True,
            "database_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/database/optimize")
async def optimize_face_database(state: AppState = Depends(get_state)):
    """Run comprehensive database optimization (indexes, vacuum, analyze)."""
    try:
        from server.face_db_optimizer import optimize_face_database
        
        results = optimize_face_database(Path(settings.FACE_CLUSTERS_DB_PATH))
        
        return {
            "success": True,
            "optimization_results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Performance Monitoring & Analytics Endpoints
# ===================================================================


@router.get("/api/faces/performance/stats")
async def get_performance_stats(state: AppState = Depends(get_state)):
    """Get real-time performance statistics and system health metrics."""
    try:
        from server.face_performance_monitor import get_global_monitor
        
        monitor = get_global_monitor()
        summary = monitor.get_performance_summary()
        
        return {
            "success": True,
            "performance_stats": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/analytics")
async def get_face_analytics(state: AppState = Depends(get_state)):
    """Get comprehensive analytics about face recognition system usage and patterns."""
    try:
        from server.face_performance_monitor import FaceAnalytics
        
        analytics = FaceAnalytics(Path(settings.FACE_CLUSTERS_DB_PATH))
        results = analytics.get_usage_analytics()
        
        return {
            "success": True,
            "analytics": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/performance/reset")
async def reset_performance_stats(state: AppState = Depends(get_state)):
    """Reset performance monitoring statistics (useful for benchmarking)."""
    try:
        from server.face_performance_monitor import reset_global_monitor
        
        reset_global_monitor()
        
        return {
            "success": True,
            "message": "Performance statistics reset successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Video Face Tracking Endpoints
# ===================================================================


@router.post("/api/faces/video/track")
async def track_faces_in_video(data: dict, state: AppState = Depends(get_state)):
    """Track faces throughout a video with temporal consistency."""
    try:
        from server.video_face_tracker import get_video_face_tracker
        
        video_path = data.get("video_path")
        sample_rate = data.get("sample_rate", 5)
        
        if not video_path:
            raise HTTPException(status_code=400, detail="video_path is required")
        
        # Initialize video face tracker
        tracker = get_video_face_tracker(
            Path(settings.FACE_CLUSTERS_DB_PATH),
            state.face_clusterer
        )
        
        # Track faces
        results = tracker.track_faces_in_video(video_path, sample_rate)
        
        return {
            "success": True,
            "tracking_results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/video/{video_path:path}/summary")
async def get_video_face_summary(video_path: str, state: AppState = Depends(get_state)):
    """Get face tracking summary for a specific video."""
    try:
        from server.video_face_tracker import get_video_face_tracker
        import urllib.parse
        
        # URL decode the path
        decoded_path = urllib.parse.unquote(video_path)
        
        # Initialize video face tracker
        tracker = get_video_face_tracker(
            Path(settings.FACE_CLUSTERS_DB_PATH),
            state.face_clusterer
        )
        
        # Get summary
        summary = tracker.get_video_face_summary(decoded_path)
        
        return {
            "success": True,
            "video_summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/video/{video_path:path}/tracks")
async def get_video_face_tracks(
    video_path: str, 
    state: AppState = Depends(get_state),
    include_detections: bool = False
):
    """Get all face tracks for a video with optional detection details."""
    try:
        import urllib.parse
        
        # URL decode the path
        decoded_path = urllib.parse.unquote(video_path)
        
        db = get_face_clustering_db(Path(settings.FACE_CLUSTERS_DB_PATH))
        
        with sqlite3.connect(str(db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get tracks
            cursor = conn.execute("""
                SELECT track_id, start_frame, end_frame, start_time, end_time,
                       cluster_id, confidence_avg, quality_score, best_frame_data
                FROM video_face_tracks
                WHERE video_path = ?
                ORDER BY start_time ASC
            """, (decoded_path,))
            
            tracks = []
            for row in cursor.fetchall():
                track_data = dict(row)
                
                # Parse best frame data
                if track_data['best_frame_data']:
                    track_data['best_frame'] = json.loads(track_data['best_frame_data'])
                
                # Include detections if requested
                if include_detections:
                    det_cursor = conn.execute("""
                        SELECT frame_number, timestamp, bounding_box, confidence,
                               quality_metrics, is_best_frame
                        FROM video_face_detections
                        WHERE track_id = ? AND video_path = ?
                        ORDER BY frame_number ASC
                    """, (track_data['track_id'], decoded_path))
                    
                    detections = []
                    for det_row in det_cursor.fetchall():
                        det_data = dict(det_row)
                        det_data['bounding_box'] = json.loads(det_data['bounding_box'])
                        if det_data['quality_metrics']:
                            det_data['quality_metrics'] = json.loads(det_data['quality_metrics'])
                        detections.append(det_data)
                    
                    track_data['detections'] = detections
                
                tracks.append(track_data)
        
        return {
            "success": True,
            "video_path": decoded_path,
            "tracks": tracks,
            "track_count": len(tracks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

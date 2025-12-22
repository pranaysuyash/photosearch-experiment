"""
Face Recognition API Router

Uses Depends(get_state) for accessing shared application state.
"""
import json
import os
import sqlite3
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response

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
            return {"clusters": [], "message": "Face recognition models are still loading"}

        # Get all clusters from the pre-initialized clusterer
        result = face_clusterer.get_all_clusters(limit=100)

        # Format for frontend
        formatted_clusters = []
        for cluster in result.get("clusters", []):
            cluster_details = face_clusterer.get_cluster_details(cluster["id"])
            if cluster_details.get("status") != "error":
                faces = cluster_details.get("faces", [])
                formatted_clusters.append(
                    {
                        "id": str(cluster["id"]),
                        "label": cluster.get("label") or f"Person {cluster['id']}",
                        "face_count": cluster_details.get("face_count", 0),
                        "image_count": len(set(f.get("image_path") for f in faces)),
                        # Return face IDs for crop endpoint
                        "face_ids": [f.get("id") for f in faces[:6]],
                        # Also return image paths as fallback
                        "images": [f.get("image_path") for f in faces[:6]],
                        "created_at": cluster.get("created_at"),
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
            cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?", (limit,))
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


def _run_face_scan_job(job_id: str, files: list, face_scan_jobs: dict, min_samples: int = 1):
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
                all_results["matched_to_existing"] += result.get("matched_to_existing", 0)
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
    limit: Optional[int] = None
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
        cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?", (limit,))
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
async def set_cluster_label(cluster_id: str, label_data: dict, state: AppState = Depends(get_state)):
    """Set label for a face cluster."""
    try:
        face_clusterer = state.face_clusterer
        label = label_data.get("label", "")

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

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
    offset: int = 0
):
    """Get photos for a specific person/cluster."""
    try:
        face_clusterer = state.face_clusterer
        photo_search_engine = state.photo_search_engine

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        # Find cluster by label
        db = get_face_clustering_db()
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT id FROM clusters WHERE label = ? LIMIT 1",
            (person_name,)
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
            JOIN cluster_memberships cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            LIMIT ? OFFSET ?
            """,
            (cluster_id, limit, offset)
        )
        image_paths = [r[0] for r in cursor.fetchall()]

        # Get metadata for these photos
        photos = []
        for path in image_paths:
            try:
                meta = photo_search_engine.db.get_metadata(path)
                if meta:
                    photos.append({
                        "path": path,
                        "filename": os.path.basename(path),
                        "metadata": meta
                    })
            except Exception:
                photos.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "metadata": {}
                })

        # Get total count
        cursor.execute(
            """
            SELECT COUNT(DISTINCT f.image_path)
            FROM faces f
            JOIN cluster_memberships cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            """,
            (cluster_id,)
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
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        # Delete memberships first
        cursor.execute("DELETE FROM cluster_memberships WHERE cluster_id = ?", (int(cluster_id),))
        # Delete cluster
        cursor.execute("DELETE FROM clusters WHERE id = ?", (int(cluster_id),))
        db.conn.commit()

        return {"status": "success", "deleted_cluster_id": cluster_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/clusters/{cluster_id}/photos")
async def get_cluster_photos(
    cluster_id: str,
    state: AppState = Depends(get_state),
    limit: int = 100,
    offset: int = 0
):
    """Get all photos containing faces from a specific cluster."""
    try:
        face_clusterer = state.face_clusterer
        photo_search_engine = state.photo_search_engine

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        # Get photos for this cluster
        cursor.execute(
            """
            SELECT DISTINCT f.image_path, f.id as face_id, f.confidence
            FROM faces f
            JOIN cluster_memberships cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            ORDER BY f.confidence DESC
            LIMIT ? OFFSET ?
            """,
            (int(cluster_id), limit, offset)
        )
        rows = cursor.fetchall()

        photos = []
        for path, face_id, confidence in rows:
            try:
                meta = photo_search_engine.db.get_metadata(path)
                photos.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "face_id": face_id,
                    "confidence": confidence,
                    "metadata": meta or {}
                })
            except Exception:
                photos.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "face_id": face_id,
                    "confidence": confidence,
                    "metadata": {}
                })

        return {"cluster_id": cluster_id, "photos": photos, "count": len(photos)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/unidentified")
async def get_unidentified_clusters(
    state: AppState = Depends(get_state),
    limit: int = 100,
    offset: int = 0
):
    """Get all clusters that have no user-assigned label (unlabeled clusters)."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        # Get clusters without labels
        cursor.execute(
            """
            SELECT c.id, c.label, COUNT(cm.face_id) as face_count
            FROM clusters c
            LEFT JOIN cluster_memberships cm ON c.id = cm.cluster_id
            WHERE c.label IS NULL OR c.label = '' OR c.label LIKE 'Person %'
            GROUP BY c.id
            ORDER BY face_count DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        rows = cursor.fetchall()

        clusters = []
        for cid, label, face_count in rows:
            # Get sample faces
            cursor.execute(
                """
                SELECT f.id, f.image_path
                FROM faces f
                JOIN cluster_memberships cm ON f.id = cm.face_id
                WHERE cm.cluster_id = ?
                LIMIT 4
                """,
                (cid,)
            )
            faces = cursor.fetchall()
            clusters.append({
                "id": str(cid),
                "label": label or f"Person {cid}",
                "face_count": face_count,
                "face_ids": [f[0] for f in faces],
                "images": [f[1] for f in faces]
            })

        return {"clusters": clusters, "count": len(clusters)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/singletons")
async def get_singleton_clusters(
    state: AppState = Depends(get_state),
    limit: int = 100,
    offset: int = 0
):
    """Get all clusters with only 1 face (appears only once in library)."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        cursor.execute(
            """
            SELECT c.id, c.label, f.id as face_id, f.image_path, f.confidence
            FROM clusters c
            JOIN cluster_memberships cm ON c.id = cm.cluster_id
            JOIN faces f ON cm.face_id = f.id
            WHERE c.id IN (
                SELECT cluster_id FROM cluster_memberships
                GROUP BY cluster_id HAVING COUNT(*) = 1
            )
            ORDER BY f.confidence DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        rows = cursor.fetchall()

        singletons = []
        for cid, label, face_id, image_path, confidence in rows:
            singletons.append({
                "cluster_id": str(cid),
                "label": label or f"Person {cid}",
                "face_id": face_id,
                "image_path": image_path,
                "confidence": confidence
            })

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
    threshold: float = 0.8
):
    """Get all faces with confidence below threshold."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        cursor.execute(
            """
            SELECT f.id, f.image_path, f.confidence, cm.cluster_id, c.label
            FROM faces f
            LEFT JOIN cluster_memberships cm ON f.id = cm.face_id
            LEFT JOIN clusters c ON cm.cluster_id = c.id
            WHERE f.confidence < ?
            ORDER BY f.confidence ASC
            LIMIT ? OFFSET ?
            """,
            (threshold, limit, offset)
        )
        rows = cursor.fetchall()

        faces = []
        for fid, path, conf, cid, label in rows:
            faces.append({
                "face_id": fid,
                "image_path": path,
                "confidence": conf,
                "cluster_id": str(cid) if cid else None,
                "label": label
            })

        return {"faces": faces, "count": len(faces), "threshold": threshold}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/assign")
async def assign_face_to_cluster(face_id: int, data: dict, state: AppState = Depends(get_state)):
    """Assign a face to an existing cluster/person."""
    try:
        face_clusterer = state.face_clusterer
        cluster_id = data.get("cluster_id")

        if not cluster_id:
            raise HTTPException(status_code=400, detail="cluster_id is required")

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        # Remove existing cluster membership if any
        cursor.execute("DELETE FROM cluster_memberships WHERE face_id = ?", (face_id,))

        # Add to new cluster
        cursor.execute(
            "INSERT INTO cluster_memberships (face_id, cluster_id) VALUES (?, ?)",
            (face_id, int(cluster_id))
        )
        db.conn.commit()

        return {"status": "success", "face_id": face_id, "cluster_id": cluster_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/create-person")
async def create_person_from_face(face_id: int, data: dict, state: AppState = Depends(get_state)):
    """Create a new person/cluster from an unidentified face."""
    try:
        face_clusterer = state.face_clusterer
        label = data.get("label", "")

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        # Create new cluster
        cursor.execute(
            "INSERT INTO clusters (label, created_at) VALUES (?, datetime('now'))",
            (label,)
        )
        cluster_id = cursor.lastrowid

        # Remove existing membership if any
        cursor.execute("DELETE FROM cluster_memberships WHERE face_id = ?", (face_id,))

        # Assign face to new cluster
        cursor.execute(
            "INSERT INTO cluster_memberships (face_id, cluster_id) VALUES (?, ?)",
            (face_id, cluster_id)
        )
        db.conn.commit()

        return {"status": "success", "face_id": face_id, "cluster_id": cluster_id, "label": label}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/photos-with-faces")
async def get_photos_with_faces(
    state: AppState = Depends(get_state),
    limit: int = 200,
    offset: int = 0
):
    """Get all photos that have at least one detected face."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT image_path, COUNT(*) as face_count
            FROM faces
            GROUP BY image_path
            ORDER BY face_count DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        rows = cursor.fetchall()

        photos = [{"path": r[0], "face_count": r[1]} for r in rows]

        return {"photos": photos, "count": len(photos)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/crop/{face_id}")
async def get_face_crop(face_id: int, state: AppState = Depends(get_state), size: int = 150):
    """Get a cropped face image by face ID."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        cursor.execute(
            "SELECT image_path, bbox_x, bbox_y, bbox_w, bbox_h FROM faces WHERE id = ?",
            (face_id,)
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Face not found")

        image_path, x, y, w, h = row

        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file not found")

        # Crop the face
        from PIL import Image
        import io

        img = Image.open(image_path)
        # Add margin
        margin = int(max(w, h) * 0.2)
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img.width, x + w + margin)
        y2 = min(img.height, y + h + margin)

        face_crop = img.crop((x1, y1, x2, y2))
        face_crop.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Return as JPEG
        buffer = io.BytesIO()
        face_crop.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        return Response(content=buffer.getvalue(), media_type="image/jpeg")
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
                "message": "Face recognition not available"
            }

        db = get_face_clustering_db()
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
                SELECT cluster_id FROM cluster_memberships
                GROUP BY cluster_id HAVING COUNT(*) = 1
            )
            """
        )
        singletons = cursor.fetchone()[0]

        return {
            "status": "available",
            "models_loaded": face_clusterer.models_loaded,
            "total_faces": total_faces,
            "total_clusters": total_clusters,
            "labeled_clusters": labeled_clusters,
            "unlabeled_clusters": unlabeled_clusters,
            "photos_with_faces": photos_with_faces,
            "avg_faces_per_photo": round(avg_faces, 2),
            "singletons": singletons
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# People Search Endpoint

@router.get("/api/people/search")
async def search_people(
    state: AppState = Depends(get_state),
    query: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    """Search for people by name or other attributes."""
    try:
        face_clusterer = state.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        if query:
            cursor.execute(
                """
                SELECT c.id, c.label, COUNT(cm.face_id) as face_count
                FROM clusters c
                LEFT JOIN cluster_memberships cm ON c.id = cm.cluster_id
                WHERE c.label LIKE ?
                GROUP BY c.id
                ORDER BY face_count DESC
                LIMIT ? OFFSET ?
                """,
                (f"%{query}%", limit, offset)
            )
        else:
            cursor.execute(
                """
                SELECT c.id, c.label, COUNT(cm.face_id) as face_count
                FROM clusters c
                LEFT JOIN cluster_memberships cm ON c.id = cm.cluster_id
                WHERE c.label IS NOT NULL AND c.label != '' AND c.label NOT LIKE 'Person %'
                GROUP BY c.id
                ORDER BY face_count DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )

        rows = cursor.fetchall()
        people = [
            {"id": str(r[0]), "name": r[1], "face_count": r[2]}
            for r in rows
        ]

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
            raise HTTPException(status_code=503, detail="Face recognition not available")

        db = get_face_clustering_db()
        cursor = db.conn.cursor()

        # Get cluster info
        cursor.execute(
            "SELECT label FROM clusters WHERE id = ?",
            (int(person_id),)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Person not found")

        label = row[0] or f"Person {person_id}"

        # Get face count
        cursor.execute(
            "SELECT COUNT(*) FROM cluster_memberships WHERE cluster_id = ?",
            (int(person_id),)
        )
        face_count = cursor.fetchone()[0]

        # Get photo count
        cursor.execute(
            """
            SELECT COUNT(DISTINCT f.image_path)
            FROM faces f
            JOIN cluster_memberships cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            """,
            (int(person_id),)
        )
        photo_count = cursor.fetchone()[0]

        # Get date range of photos
        cursor.execute(
            """
            SELECT f.image_path
            FROM faces f
            JOIN cluster_memberships cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            """,
            (int(person_id),)
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

        return {
            "person_id": person_id,
            "name": label,
            "face_count": face_count,
            "photo_count": photo_count,
            "date_range": date_range
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

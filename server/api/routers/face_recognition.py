import json
import os
import sqlite3
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import Response

from server.config import settings
from server.face_clustering_db import get_face_clustering_db


router = APIRouter()


@router.get("/api/faces/clusters")
async def get_face_clusters():
    """Get all face clusters."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

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
async def scan_faces(limit: Optional[int] = None):
    """Scan for faces in photos. Pass limit to scan only first N photos."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer
        photo_search_engine = main_module.photo_search_engine

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
                "scanned": 0,
                "clusters_found": 0,
                "total_faces": 0,
                "message": "No photos found in library",
            }

        result = face_clusterer.cluster_faces(all_files, min_samples=1)

        # Handle error response from cluster_faces
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Clustering failed"))

        return {
            "scanned": len(all_files),
            "clusters_found": result.get("total_clusters", 0),
            "total_faces": result.get("total_faces", 0),
            "message": result.get("message", "Scan complete"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_face_scan_job(job_id: str, files: list, min_samples: int = 1):
    """Background task to run face scanning with progress updates."""
    from server import main as main_module

    face_scan_jobs = main_module.face_scan_jobs

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
async def scan_faces_async(background_tasks: BackgroundTasks, limit: Optional[int] = None):
    """Start an async face scan job. Returns immediately with job_id for polling."""
    import uuid

    from server import main as main_module

    face_clusterer = main_module.face_clusterer
    photo_search_engine = main_module.photo_search_engine
    face_scan_jobs = main_module.face_scan_jobs

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
            "job_id": None,
            "status": "completed",
            "message": "No photos found in library",
        }

    # Create job ID and start background task
    job_id = str(uuid.uuid4())
    face_scan_jobs[job_id] = {
        "status": "starting",
        "progress": 0,
        "total": len(all_files),
        "current": 0,
        "current_file": "",
        "message": "Initializing scan...",
        "result": None,
        "error": None,
    }

    background_tasks.add_task(_run_face_scan_job, job_id, all_files)

    return {
        "job_id": job_id,
        "status": "started",
        "total_files": len(all_files),
        "message": f"Scan started for {len(all_files)} photos",
    }


@router.get("/api/faces/scan-async/{job_id}")
async def get_scan_job_status(job_id: str):
    """Get status of an async face scan job."""
    from server import main as main_module

    face_scan_jobs = main_module.face_scan_jobs

    if job_id not in face_scan_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = face_scan_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "total": job.get("total", 0),
        "current": job.get("current", 0),
        "current_file": job.get("current_file", ""),
        "message": job.get("message", ""),
        "result": job.get("result") if job.get("status") == "completed" else None,
        "error": job.get("error"),
    }


@router.post("/api/faces/scan-file")
async def scan_single_file(data: dict):
    """Scan a specific file or list of files for faces."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer or not face_clusterer.models_loaded:
            raise HTTPException(status_code=503, detail="Face recognition models not ready")

        files = data.get("files", [])
        filepath = data.get("filepath")

        if filepath:
            files = [filepath]

        if not files:
            raise HTTPException(status_code=400, detail="No files specified")

        result = face_clusterer.cluster_faces(files, min_samples=1)

        return {
            "status": result.get("status"),
            "total_faces": result.get("total_faces", 0),
            "matched_to_existing": result.get("matched_to_existing", 0),
            "new_clusters": result.get("new_clusters_created", 0),
            "message": result.get("message", "Scan complete"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/clusters/{cluster_id}/label")
async def set_cluster_label(cluster_id: str, label_data: dict):
    """Set label for a face cluster."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        label = label_data.get("label", "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="Label cannot be empty")

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face clusterer not available")

        cursor = face_clusterer.conn.cursor()

        # Check if cluster exists
        cursor.execute("SELECT id FROM clusters WHERE id = ?", (cluster_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Update the cluster label
        cursor.execute("UPDATE clusters SET label = ? WHERE id = ?", (label, cluster_id))
        face_clusterer.conn.commit()

        return {"success": True, "cluster_id": cluster_id, "label": label}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/photos/{person_name}")
async def get_photos_by_person(person_name: str, limit: int = 100, offset: int = 0):
    """Get photos for a specific person/cluster."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            return {"count": 0, "results": [], "person": person_name}

        cursor = face_clusterer.conn.cursor()

        # Try to find cluster by label or ID
        cursor.execute(
            """
            SELECT id FROM clusters 
            WHERE label = ? OR id = ? OR label LIKE ?
            LIMIT 1
        """,
            (person_name, person_name.replace("Person ", ""), f"%{person_name}%"),
        )

        cluster_row = cursor.fetchone()
        if not cluster_row:
            return {"count": 0, "results": [], "person": person_name, "error": "Person not found"}

        cluster_id = cluster_row[0]

        # Get all unique image paths for this cluster
        cursor.execute(
            """
            SELECT DISTINCT f.image_path, f.id, f.bounding_box, f.confidence
            FROM faces f
            JOIN cluster_membership cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            ORDER BY f.confidence DESC
            LIMIT ? OFFSET ?
        """,
            (cluster_id, limit, offset),
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "path": row[0],
                    "face_id": row[1],
                    "bounding_box": json.loads(row[2]) if row[2] else None,
                    "confidence": row[3],
                }
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
        total_count = cursor.fetchone()[0]

        return {
            "count": total_count,
            "results": results,
            "person": person_name,
            "cluster_id": cluster_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/faces/clusters/{cluster_id}")
async def delete_cluster(cluster_id: str):
    """Delete a face cluster and its memberships."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face clusterer not available")

        cursor = face_clusterer.conn.cursor()

        # Check if cluster exists
        cursor.execute("SELECT id FROM clusters WHERE id = ?", (cluster_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Delete cluster memberships
        cursor.execute("DELETE FROM cluster_membership WHERE cluster_id = ?", (cluster_id,))

        # Reset cluster_id on faces
        cursor.execute("UPDATE faces SET cluster_id = NULL WHERE cluster_id = ?", (cluster_id,))

        # Delete the cluster
        cursor.execute("DELETE FROM clusters WHERE id = ?", (cluster_id,))

        face_clusterer.conn.commit()

        return {"success": True, "message": f"Cluster {cluster_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/cluster/{cluster_id}/photos")
async def get_cluster_photos(cluster_id: str, limit: int = 100, offset: int = 0):
    """Get all photos containing faces from a specific cluster."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            return {"count": 0, "results": [], "cluster_id": cluster_id}

        cursor = face_clusterer.conn.cursor()

        # Get unique image paths for this cluster (group by path to avoid duplicates)
        cursor.execute(
            """
            SELECT f.image_path, 
                   MAX(f.id) as face_id, 
                   MAX(f.bounding_box) as bounding_box, 
                   MAX(f.confidence) as confidence,
                   COUNT(f.id) as face_count
            FROM faces f
            JOIN cluster_membership cm ON f.id = cm.face_id
            WHERE cm.cluster_id = ?
            GROUP BY f.image_path
            ORDER BY MAX(f.confidence) DESC
            LIMIT ? OFFSET ?
        """,
            (cluster_id, limit, offset),
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "path": row[0],
                    "face_id": row[1],
                    "bounding_box": json.loads(row[2]) if row[2] else None,
                    "confidence": row[3],
                    "face_count": row[4],  # How many faces of this person in this photo
                }
            )

        return {
            "count": len(results),
            "results": results,
            "cluster_id": cluster_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/unidentified")
async def get_unidentified_clusters(limit: int = 100, offset: int = 0):
    """Get all clusters that have no user-assigned label (unlabeled clusters)."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            return {"clusters": [], "count": 0}

        cursor = face_clusterer.conn.cursor()

        # Get clusters with no user label (NULL or auto-generated like "Person X")
        cursor.execute(
            """
            SELECT c.id, c.label, c.size, c.representative_face_id, c.created_at
            FROM clusters c
            WHERE c.label IS NULL OR c.label LIKE 'Person %'
            ORDER BY c.size DESC, c.created_at DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        clusters = []
        for row in cursor.fetchall():
            cluster_id = row[0]
            # Get face IDs and images for this cluster
            cursor.execute(
                """
                SELECT f.id, f.image_path FROM faces f
                JOIN cluster_membership cm ON f.id = cm.face_id
                WHERE cm.cluster_id = ?
            """,
                (cluster_id,),
            )
            faces = cursor.fetchall()

            clusters.append(
                {
                    "id": str(cluster_id),
                    "label": row[1] or f"Person {cluster_id}",
                    "face_count": row[2],
                    "face_ids": [f[0] for f in faces],
                    "images": [f[1] for f in faces],
                    "created_at": row[4],
                }
            )

        # Get total count
        cursor.execute(
            """
            SELECT COUNT(*) FROM clusters 
            WHERE label IS NULL OR label LIKE 'Person %'
        """
        )
        total = cursor.fetchone()[0]

        return {"clusters": clusters, "count": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/singletons")
async def get_singleton_clusters(limit: int = 100, offset: int = 0):
    """Get all clusters with only 1 face (appears only once in library)."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            return {"clusters": [], "count": 0}

        cursor = face_clusterer.conn.cursor()

        cursor.execute(
            """
            SELECT c.id, c.label, c.size, c.representative_face_id, c.created_at
            FROM clusters c
            WHERE c.size = 1
            ORDER BY c.created_at DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        clusters = []
        for row in cursor.fetchall():
            cluster_id = row[0]
            cursor.execute(
                """
                SELECT f.id, f.image_path FROM faces f
                JOIN cluster_membership cm ON f.id = cm.face_id
                WHERE cm.cluster_id = ?
            """,
                (cluster_id,),
            )
            faces = cursor.fetchall()

            clusters.append(
                {
                    "id": str(cluster_id),
                    "label": row[1] or f"Person {cluster_id}",
                    "face_count": row[2],
                    "face_ids": [f[0] for f in faces],
                    "images": [f[1] for f in faces],
                    "created_at": row[4],
                }
            )

        cursor.execute("SELECT COUNT(*) FROM clusters WHERE size = 1")
        total = cursor.fetchone()[0]

        return {"clusters": clusters, "count": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/low-confidence")
async def get_low_confidence_faces(limit: int = 100, offset: int = 0, threshold: float = 0.8):
    """Get all faces with confidence below threshold."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            return {"faces": [], "count": 0}

        cursor = face_clusterer.conn.cursor()

        cursor.execute(
            """
            SELECT f.id, f.image_path, f.bounding_box, f.confidence, f.cluster_id
            FROM faces f
            WHERE f.confidence < ?
            ORDER BY f.confidence ASC
            LIMIT ? OFFSET ?
        """,
            (threshold, limit, offset),
        )

        faces = []
        for row in cursor.fetchall():
            faces.append(
                {
                    "id": row[0],
                    "image_path": row[1],
                    "bounding_box": json.loads(row[2]) if row[2] else None,
                    "confidence": row[3],
                    "cluster_id": row[4],
                }
            )

        cursor.execute("SELECT COUNT(*) FROM faces WHERE confidence < ?", (threshold,))
        total = cursor.fetchone()[0]

        return {"faces": faces, "count": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/assign")
async def assign_face_to_cluster(face_id: int, data: dict):
    """Assign a face to an existing cluster/person."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face clusterer not available")

        cluster_id = data.get("cluster_id")
        if not cluster_id:
            raise HTTPException(status_code=400, detail="cluster_id is required")

        cursor = face_clusterer.conn.cursor()

        # Check if face exists
        cursor.execute("SELECT id FROM faces WHERE id = ?", (face_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Face not found")

        # Check if cluster exists
        cursor.execute("SELECT id FROM clusters WHERE id = ?", (cluster_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Add to cluster_membership
        cursor.execute(
            """
            INSERT OR REPLACE INTO cluster_membership (face_id, cluster_id, confidence)
            VALUES (?, ?, 1.0)
        """,
            (face_id, cluster_id),
        )

        # Update cluster size
        cursor.execute(
            """
            UPDATE clusters SET size = (
                SELECT COUNT(*) FROM cluster_membership WHERE cluster_id = ?
            ) WHERE id = ?
        """,
            (cluster_id, cluster_id),
        )

        face_clusterer.conn.commit()

        return {"success": True, "face_id": face_id, "cluster_id": cluster_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/faces/{face_id}/create-person")
async def create_person_from_face(face_id: int, data: dict):
    """Create a new person/cluster from an unidentified face."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face clusterer not available")

        label = data.get("label", "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="label is required")

        cursor = face_clusterer.conn.cursor()

        # Check if face exists
        cursor.execute("SELECT id FROM faces WHERE id = ?", (face_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Face not found")

        # Create new cluster
        cursor.execute(
            """
            INSERT INTO clusters (label, size, created_at,updated_at)
            VALUES (?, 1, datetime('now'), datetime('now'))
        """,
            (label,),
        )
        cluster_id = cursor.lastrowid

        # Add face to cluster
        cursor.execute(
            """
            INSERT INTO cluster_membership (face_id, cluster_id, confidence)
            VALUES (?, ?, 1.0)
        """,
            (face_id, cluster_id),
        )

        face_clusterer.conn.commit()

        return {"success": True, "face_id": face_id, "cluster_id": cluster_id, "label": label}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/photos-with-faces")
async def get_photos_with_faces(limit: int = 200, offset: int = 0):
    """Get all photos that have at least one detected face."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            return {"photos": [], "count": 0}

        cursor = face_clusterer.conn.cursor()

        # Get unique photos with face counts
        cursor.execute(
            """
            SELECT image_path, COUNT(*) as face_count
            FROM faces
            GROUP BY image_path
            ORDER BY COUNT(*) DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        photos = []
        for row in cursor.fetchall():
            photos.append({"path": row[0], "face_count": row[1]})

        # Get total count
        cursor.execute("SELECT COUNT(DISTINCT image_path) FROM faces")
        total = cursor.fetchone()[0]

        return {"photos": photos, "count": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/{face_id}/crop")
async def get_face_crop(face_id: int, size: int = 150):
    """Get a cropped face image by face ID."""
    try:
        from server import main as main_module
        face_clusterer = main_module.face_clusterer

        if not face_clusterer:
            raise HTTPException(status_code=503, detail="Face clusterer not available")

        # Get face info from database
        cursor = face_clusterer.conn.cursor()
        cursor.execute("SELECT image_path, bounding_box FROM faces WHERE id = ?", (face_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Face not found")

        image_path = row["image_path"]
        bbox = json.loads(row["bounding_box"]) if row["bounding_box"] else None

        if not bbox or not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Face image not available")

        # Open and crop image
        from PIL import Image
        img = Image.open(image_path)

        x, y, w, h = bbox
        # Add padding around face
        padding = int(max(w, h) * 0.3)
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(img.width, x + w + padding)
        y2 = min(img.height, y + h + padding)

        face_crop = img.crop((x1, y1, x2, y2))

        # Resize to requested size
        face_crop.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Convert to bytes
        import io
        buffer = io.BytesIO()
        face_crop.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        return Response(content=buffer.getvalue(), media_type="image/jpeg")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/stats")
async def get_face_stats_api():
    """Get face recognition statistics."""
    try:
        from server import main as main_module

        face_clusterer = main_module.face_clusterer
        photo_search_engine = main_module.photo_search_engine

        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM metadata WHERE deleted_at IS NULL")
        total_photos = cursor.fetchone()[0]

        # Get real stats from face_clusterer database
        if face_clusterer:
            stats = face_clusterer.get_cluster_statistics()
            total_faces = stats.get("total_faces", 0)
            total_clusters = stats.get("total_clusters", 0)

            try:
                face_cursor = face_clusterer.conn.cursor()

                # Unidentified = clusters with no user label (NULL or auto-generated like "Person X")
                face_cursor.execute(
                    """
                    SELECT COUNT(*) FROM clusters 
                    WHERE label IS NULL OR label LIKE 'Person %'
                """
                )
                unidentified = face_cursor.fetchone()[0]

                # Singletons = clusters with only 1 face (appears once)
                face_cursor.execute(
                    """
                    SELECT COUNT(*) FROM clusters WHERE size = 1
                """
                )
                singletons = face_cursor.fetchone()[0]

                # Low confidence = faces with confidence < 0.8
                face_cursor.execute(
                    """
                    SELECT COUNT(*) FROM faces WHERE confidence < 0.8
                """
                )
                low_confidence = face_cursor.fetchone()[0]

            except:
                unidentified = 0
                singletons = 0
                low_confidence = 0

            return {
                "total_photos": total_photos,
                "faces_detected": total_faces,
                "clusters_found": total_clusters,
                "unidentified_faces": unidentified,
                "singletons": singletons,
                "low_confidence": low_confidence,
            }
        else:
            return {
                "total_photos": total_photos,
                "faces_detected": 0,
                "clusters_found": 0,
                "unidentified_faces": 0,
                "singletons": 0,
                "low_confidence": 0,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# People Search Endpoint

@router.get("/api/people/search")
async def search_people(query: Optional[str] = None, limit: int = 10, offset: int = 0):
    """Search for people by name or other attributes."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Get all clusters (people)
        clusters = face_clustering_db.get_all_clusters()

        # Filter and search
        if query:
            query_lower = query.lower()
            clusters = [
                cluster
                for cluster in clusters
                if cluster.label and query_lower in cluster.label.lower()
            ]

        # Paginate
        paginated_clusters = clusters[offset : offset + limit]

        # Format response
        people = [
            {
                "cluster_id": cluster.cluster_id,
                "label": cluster.label or f"Person {cluster.cluster_id[-4:]}",
                "face_count": cluster.face_count,
                "photo_count": cluster.photo_count,
                "thumbnail": None,  # Would get thumbnail in real implementation
            }
            for cluster in paginated_clusters
        ]

        return {
            "people": people,
            "total": len(clusters),
            "limit": limit,
            "offset": offset,
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Person Analytics Endpoint

@router.get("/api/people/{person_id}/analytics")
async def get_person_analytics(person_id: str):
    """Get analytics and insights for a specific person."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Get basic cluster info
        cluster = None
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            cluster = conn.execute(
                """
                SELECT * FROM face_clusters WHERE cluster_id = ?
            """,
                (person_id,),
            ).fetchone()

            if not cluster:
                raise HTTPException(status_code=404, detail="Person not found")

        # Get photos with this person
        photos = face_clustering_db.get_photos_for_cluster(person_id)

        # Get timeline data
        timeline = []
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            timeline_rows = conn.execute(
                """
                SELECT ppa.photo_path, ppa.created_at, ppa.confidence
                FROM photo_person_associations ppa
                WHERE ppa.cluster_id = ?
                ORDER BY ppa.created_at
            """,
                (person_id,),
            ).fetchall()

            for row in timeline_rows:
                timeline.append(
                    {
                        "photo_path": row[0],
                        "date": row[1],
                        "confidence": row[2],
                    }
                )

        # Calculate statistics
        from datetime import datetime
        from collections import Counter

        years = [datetime.fromisoformat(t["date"]).year for t in timeline if t["date"]]
        year_distribution = dict(Counter(years))

        return {
            "person_id": person_id,
            "label": cluster[1],
            "stats": {
                "total_photos": len(photos),
                "total_faces": cluster[2],
                "first_seen": min(years) if years else None,
                "last_seen": max(years) if years else None,
                "years_active": len(set(years)) if years else 0,
            },
            "timeline": timeline,
            "year_distribution": year_distribution,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

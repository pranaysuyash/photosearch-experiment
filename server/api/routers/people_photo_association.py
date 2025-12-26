import hashlib
import json
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.core.paths import _runtime_base_dir
from server.face_clustering_db import get_face_clustering_db


router = APIRouter()


@router.get("/api/photos/{photo_path:path}/people")
async def get_people_in_photo(photo_path: str):
    """Get people associated with a specific photo."""
    try:
        face_clustering_db = get_face_clustering_db(_runtime_base_dir() / "face_clusters.db")
        associations = face_clustering_db.get_people_in_photo(photo_path)

        # Return cluster IDs for the people associated with this photo
        people = [assoc.cluster_id for assoc in associations]
        return {"photo_path": photo_path, "people": people}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/photos/{photo_path:path}/people")
async def add_person_to_photo(photo_path: str, person_data: dict):
    """Associate a person with a specific photo."""
    try:
        person_id = person_data.get("person_id")
        detection_id = person_data.get("detection_id")

        if not person_id:
            raise HTTPException(status_code=400, detail="person_id is required")

        face_clustering_db = get_face_clustering_db(_runtime_base_dir() / "face_clusters.db")

        # Ensure the cluster exists for manual associations.
        # (The UI/tests may pass a stable person_id that isn't a generated cluster_id yet.)
        try:
            face_clustering_db.ensure_face_cluster(person_id, label=person_id)
        except Exception:
            pass

        # If no detection_id provided, try to detect faces automatically
        if not detection_id:
            # Detect faces in the photo
            detection_ids = face_clustering_db.detect_and_store_faces(photo_path)

            if detection_ids:
                # Use the first detected face
                detection_id = detection_ids[0]
            else:
                # Fallback to dummy detection ID if no faces detected
                detection_id = f"temp_face_{hashlib.md5(photo_path.encode()).hexdigest()}"

        # Ensure detection exists when we fall back to a synthetic ID.
        try:
            face_clustering_db.ensure_face_detection(detection_id, photo_path)
        except Exception:
            pass

        # Add the association
        face_clustering_db.add_person_to_photo(photo_path, person_id, detection_id, confidence=0.9)

        return {"success": True, "photo_path": photo_path, "person_id": person_id, "detection_id": detection_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/photos/{photo_path:path}/people/{person_id}")
async def remove_person_from_photo(photo_path: str, person_id: str, detection_id: Optional[str] = None):
    """Remove association between a person and a specific photo."""
    try:
        face_clustering_db = get_face_clustering_db(_runtime_base_dir() / "face_clusters.db")

        # If no detection_id provided, try to find it
        if not detection_id:
            associations = face_clustering_db.get_people_in_photo(photo_path)
            for assoc in associations:
                if assoc.cluster_id == person_id:
                    detection_id = assoc.detection_id
                    break

            if not detection_id:
                # Fallback to dummy detection ID if not found
                detection_id = f"temp_face_{hashlib.md5(photo_path.encode()).hexdigest()}"

        # Remove the association
        face_clustering_db.remove_person_from_photo(photo_path, person_id, detection_id)

        return {"success": True, "photo_path": photo_path, "person_id": person_id, "detection_id": detection_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Face Detection Endpoints


@router.post("/api/photos/{photo_path:path}/faces/detect")
async def detect_faces_in_photo(photo_path: str):
    """Detect faces in a specific photo."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Detect and store faces
        detection_ids = face_clustering_db.detect_and_store_faces(photo_path)

        # Get details about detected faces
        faces = []
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            for detection_id in detection_ids:
                row = conn.execute(
                    """
                    SELECT detection_id, photo_path, bounding_box, embedding, quality_score
                    FROM face_detections
                    WHERE detection_id = ?
                """,
                    (detection_id,),
                ).fetchone()

                if row:
                    faces.append(
                        {
                            "detection_id": row["detection_id"],
                            "photo_path": row["photo_path"],
                            "bounding_box": json.loads(row["bounding_box"]),
                            "has_embedding": row["embedding"] is not None,
                            "quality_score": row["quality_score"],
                        }
                    )

        return {
            "photo_path": photo_path,
            "faces": faces,
            "face_count": len(faces),
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/photos/{photo_path:path}/faces")
async def get_faces_in_photo(photo_path: str):
    """Get information about faces detected in a photo."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Get all faces for this photo
        faces = []
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT fd.detection_id, fd.bounding_box, fd.quality_score,
                       ppa.cluster_id, fc.label as person_label
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                LEFT JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                WHERE fd.photo_path = ?
            """,
                (photo_path,),
            ).fetchall()

            for row in rows:
                faces.append(
                    {
                        "detection_id": row["detection_id"],
                        "bounding_box": json.loads(row["bounding_box"]),
                        "quality_score": row["quality_score"],
                        "person_id": row["cluster_id"],
                        "person_label": row["person_label"],
                    }
                )

        return {
            "photo_path": photo_path,
            "faces": faces,
            "face_count": len(faces),
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/{detection_id}/thumbnail")
async def get_face_thumbnail(detection_id: str):
    """Get a thumbnail image of a specific face detection."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Get face thumbnail
        thumbnail_data = face_clustering_db.get_face_thumbnail(detection_id)

        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Face thumbnail not available")

        return {
            "detection_id": detection_id,
            "thumbnail": thumbnail_data,
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/photos/batch/faces/detect")
async def detect_faces_in_batch(payload: dict):
    """Detect faces in multiple photos (batch processing)."""
    try:
        photo_paths = payload.get("photo_paths", [])
        if not photo_paths:
            raise HTTPException(status_code=400, detail="photo_paths is required")

        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        results = []
        for photo_path in photo_paths:
            detection_ids = face_clustering_db.detect_and_store_faces(photo_path)
            results.append(
                {
                    "photo_path": photo_path,
                    "face_count": len(detection_ids),
                    "detection_ids": detection_ids,
                }
            )

        return {
            "processed_photos": len(photo_paths),
            "total_faces_detected": sum(r["face_count"] for r in results),
            "results": results,
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Automatic Clustering Endpoints


@router.post("/api/faces/cluster")
async def cluster_faces_api(similarity_threshold: float = 0.6, min_samples: int = 2):
    """Automatically cluster similar faces using DBSCAN."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Perform clustering
        clusters = face_clustering_db.cluster_faces(
            similarity_threshold=similarity_threshold,
            min_samples=min_samples,
        )

        # Get cluster details
        cluster_details = []
        for cluster_id, detection_ids in clusters.items():
            # Get cluster info
            with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cluster_row = conn.execute(
                    """
                    SELECT cluster_id, label, face_count, photo_count
                    FROM face_clusters
                    WHERE cluster_id = ?
                """,
                    (cluster_id,),
                ).fetchone()

                if cluster_row:
                    cluster_details.append(
                        {
                            "cluster_id": cluster_row["cluster_id"],
                            "label": cluster_row["label"],
                            "face_count": cluster_row["face_count"],
                            "photo_count": cluster_row["photo_count"],
                            "detection_ids": detection_ids,
                        }
                    )

        return {
            "clusters_created": len(clusters),
            "total_faces_clustered": sum(len(dids) for dids in clusters.values()),
            "clusters": cluster_details,
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/faces/{detection_id}/similar")
async def find_similar_faces(detection_id: str, threshold: float = 0.7):
    """Find faces similar to a given face detection."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Find similar faces
        similar_faces = face_clustering_db.find_similar_faces(
            detection_id=detection_id,
            threshold=threshold,
        )

        # Get additional info for each similar face
        enhanced_results = []
        for face in similar_faces:
            # Get person association if any
            with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                person_row = conn.execute(
                    """
                    SELECT ppa.cluster_id, fc.label
                    FROM photo_person_associations ppa
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                    WHERE ppa.detection_id = ?
                """,
                    (face["detection_id"],),
                ).fetchone()

                result = {
                    "detection_id": face["detection_id"],
                    "photo_path": face["photo_path"],
                    "similarity": face["similarity"],
                    "person_id": person_row["cluster_id"] if person_row else None,
                    "person_label": person_row["label"] if person_row else None,
                }
                enhanced_results.append(result)

        return {
            "detection_id": detection_id,
            "similar_faces": enhanced_results,
            "count": len(enhanced_results),
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/clusters/{cluster_id}/quality")
async def get_cluster_quality(cluster_id: str):
    """Analyze the quality of a face cluster."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Get cluster quality analysis
        quality = face_clustering_db.get_cluster_quality(cluster_id)

        if "error" in quality:
            raise HTTPException(status_code=404, detail=quality["error"])

        # Get cluster details
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cluster_row = conn.execute(
                """
                SELECT cluster_id, label, created_at, updated_at
                FROM face_clusters
                WHERE cluster_id = ?
            """,
                (cluster_id,),
            ).fetchone()

            if cluster_row:
                quality.update(
                    {
                        "label": cluster_row["label"],
                        "created_at": cluster_row["created_at"],
                        "updated_at": cluster_row["updated_at"],
                    }
                )

        return {
            "cluster_id": cluster_id,
            "quality_analysis": quality,
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/clusters/{cluster_id}/merge")
async def merge_clusters(cluster_id: str, payload: dict):
    """Merge two face clusters together."""
    try:
        target_cluster_id = payload.get("target_cluster_id")
        if not target_cluster_id:
            raise HTTPException(status_code=400, detail="target_cluster_id is required")

        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")

        # Get all associations from source cluster
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get source cluster info
            source_cluster = conn.execute(
                """
                SELECT * FROM face_clusters WHERE cluster_id = ?
            """,
                (cluster_id,),
            ).fetchone()

            if not source_cluster:
                raise HTTPException(status_code=404, detail="Source cluster not found")

            # Get target cluster info
            target_cluster = conn.execute(
                """
                SELECT * FROM face_clusters WHERE cluster_id = ?
            """,
                (target_cluster_id,),
            ).fetchone()

            if not target_cluster:
                raise HTTPException(status_code=404, detail="Target cluster not found")

            # Get all associations from source cluster
            associations = conn.execute(
                """
                SELECT * FROM photo_person_associations
                WHERE cluster_id = ?
            """,
                (cluster_id,),
            ).fetchall()

            # Begin transaction
            conn.execute("BEGIN TRANSACTION")

            # Reassign all associations to target cluster
            for assoc in associations:
                conn.execute(
                    """
                    UPDATE photo_person_associations
                    SET cluster_id = ?
                    WHERE photo_path = ? AND detection_id = ? AND cluster_id = ?
                """,
                    (target_cluster_id, assoc["photo_path"], assoc["detection_id"], cluster_id),
                )

            # Update target cluster counts
            new_face_count = target_cluster["face_count"] + source_cluster["face_count"]
            new_photo_count = target_cluster["photo_count"] + source_cluster["photo_count"]

            conn.execute(
                """
                UPDATE face_clusters
                SET face_count = ?, photo_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """,
                (new_face_count, new_photo_count, target_cluster_id),
            )

            # Delete source cluster
            conn.execute("DELETE FROM face_clusters WHERE cluster_id = ?", (cluster_id,))

            # Commit transaction
            conn.commit()

        return {
            "source_cluster_id": cluster_id,
            "target_cluster_id": target_cluster_id,
            "faces_moved": source_cluster["face_count"],
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

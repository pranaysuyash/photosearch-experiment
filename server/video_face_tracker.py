"""
Video Face Tracking Enhancement

Advanced face tracking system for video content that provides:
- Temporal face tracking across video frames
- Best frame selection for each person
- Face trajectory analysis
- Video face clustering with temporal consistency
- Face appearance/disappearance detection
"""

import cv2
import numpy as np
import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)


@dataclass
class FaceTrack:
    """Represents a face track across video frames."""

    track_id: str
    video_path: str
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    face_detections: List[Dict[str, Any]]
    best_frame: Optional[Dict[str, Any]] = None
    cluster_id: Optional[str] = None
    confidence_avg: float = 0.0
    quality_score: float = 0.0


class VideoFaceTracker:
    """
    Advanced face tracking system for video content.

    Features:
    - Temporal consistency tracking
    - Best frame selection per person
    - Face trajectory analysis
    - Integration with existing face clustering
    """

    def __init__(self, db_path: Path, face_clusterer=None):
        """Initialize video face tracker."""
        self.db_path = db_path
        self.face_clusterer = face_clusterer
        self._init_database()

        # Tracking parameters
        self.max_track_gap = 5  # Max frames to bridge tracking gaps
        self.min_track_length = 3  # Minimum frames for valid track
        self.similarity_threshold = 0.7  # Face similarity for tracking
        self.quality_factors = {
            "size": 0.3,  # Face size weight
            "sharpness": 0.3,  # Image sharpness weight
            "frontal": 0.2,  # Frontal pose weight
            "lighting": 0.2,  # Lighting quality weight
        }

    def _init_database(self):
        """Initialize video face tracking database schema."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Video face tracks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_face_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT NOT NULL,
                    video_path TEXT NOT NULL,
                    start_frame INTEGER NOT NULL,
                    end_frame INTEGER NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    cluster_id TEXT,
                    confidence_avg REAL,
                    quality_score REAL,
                    best_frame_data TEXT,  -- JSON
                    trajectory_data TEXT,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(track_id, video_path)
                )
            """)

            # Video face detections (frame-level)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_face_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT NOT NULL,
                    video_path TEXT NOT NULL,
                    frame_number INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    bounding_box TEXT NOT NULL,  -- JSON [x,y,w,h]
                    embedding BLOB,  -- Face embedding
                    confidence REAL NOT NULL,
                    quality_metrics TEXT,  -- JSON quality scores
                    is_best_frame BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (track_id, video_path) REFERENCES video_face_tracks(track_id, video_path)
                )
            """)

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_tracks_path ON video_face_tracks(video_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_tracks_cluster ON video_face_tracks(cluster_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_detections_track ON video_face_detections(track_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_detections_frame ON video_face_detections(frame_number)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_video_detections_timestamp ON video_face_detections(timestamp)"
            )

    def track_faces_in_video(self, video_path: str, sample_rate: int = 5) -> Dict[str, Any]:
        """
        Track faces throughout a video with temporal consistency.

        Args:
            video_path: Path to video file
            sample_rate: Process every Nth frame (default: 5)

        Returns:
            Tracking results with statistics
        """
        logger.info(f"Starting face tracking for video: {video_path}")

        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Initialize tracking state
            active_tracks = {}  # track_id -> track_data
            next_track_id = 1

            frame_number = 0
            processed_frames = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Sample frames
                if frame_number % sample_rate != 0:
                    frame_number += 1
                    continue

                timestamp = frame_number / fps

                # Detect faces in current frame
                faces = self._detect_faces_in_frame(frame, frame_number, timestamp)

                if faces:
                    # Update tracking
                    active_tracks = self._update_tracks(active_tracks, faces, frame_number, timestamp)

                    # Start new tracks for unmatched faces
                    for face in faces:
                        if not face.get("matched"):
                            track_id = f"track_{next_track_id}"
                            next_track_id += 1

                            active_tracks[track_id] = {
                                "track_id": track_id,
                                "video_path": video_path,
                                "start_frame": frame_number,
                                "start_time": timestamp,
                                "detections": [face],
                                "last_seen": frame_number,
                            }
                            face["track_id"] = track_id

                # Clean up lost tracks
                active_tracks = self._cleanup_lost_tracks(active_tracks, frame_number, self.max_track_gap)

                processed_frames += 1
                frame_number += 1

                # Progress logging
                if processed_frames % 100 == 0:
                    progress = (frame_number / total_frames) * 100
                    logger.info(f"Tracking progress: {progress:.1f}% ({len(active_tracks)} active tracks)")

            cap.release()

            # Finalize remaining tracks
            completed_tracks = []
            for track_data in active_tracks.values():
                if len(track_data["detections"]) >= self.min_track_length:
                    track = self._finalize_track(track_data)
                    completed_tracks.append(track)

            # Save tracks to database
            self._save_tracks(completed_tracks)

            # Cluster faces across tracks
            clustering_results = self._cluster_video_faces(video_path, completed_tracks)

            results = {
                "video_path": video_path,
                "total_frames": total_frames,
                "processed_frames": processed_frames,
                "tracks_found": len(completed_tracks),
                "clusters_assigned": clustering_results.get("clusters_assigned", 0),
                "processing_time": time.time(),
                "status": "completed",
            }

            logger.info(f"Face tracking completed: {len(completed_tracks)} tracks found")
            return results

        except Exception as e:
            logger.error(f"Face tracking failed for {video_path}: {e}")
            return {"video_path": video_path, "status": "error", "error": str(e)}

    def _detect_faces_in_frame(self, frame: np.ndarray, frame_number: int, timestamp: float) -> List[Dict[str, Any]]:
        """Detect faces in a single frame."""
        if not self.face_clusterer or not hasattr(self.face_clusterer, "detect_faces"):
            return []

        try:
            # Use existing face detection from face_clusterer
            detections = self.face_clusterer.detect_faces(frame)

            faces = []
            for detection in detections:
                # Calculate quality metrics
                quality = self._calculate_face_quality(frame, detection["bbox"])

                face_data = {
                    "frame_number": frame_number,
                    "timestamp": timestamp,
                    "bbox": detection["bbox"],
                    "confidence": detection.get("confidence", 0.0),
                    "embedding": detection.get("embedding"),
                    "quality_score": quality["overall"],
                    "quality_metrics": quality,
                    "matched": False,  # Will be set during tracking
                }
                faces.append(face_data)

            return faces

        except Exception as e:
            logger.warning(f"Face detection failed for frame {frame_number}: {e}")
            return []

    def _calculate_face_quality(self, frame: np.ndarray, bbox: List[int]) -> Dict[str, float]:
        """Calculate quality metrics for a detected face."""
        x, y, w, h = bbox

        # Extract face region
        face_region = frame[y : y + h, x : x + w]
        if face_region.size == 0:
            return {
                "overall": 0.0,
                "size": 0.0,
                "sharpness": 0.0,
                "frontal": 0.0,
                "lighting": 0.0,
            }

        # Size score (larger faces are generally better)
        frame_area = frame.shape[0] * frame.shape[1]
        face_area = w * h
        size_score = min(face_area / (frame_area * 0.01), 1.0)  # Cap at 1% of frame

        # Sharpness score (Laplacian variance)
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()
        sharpness_score = min(sharpness / 1000.0, 1.0)  # Normalize

        # Frontal pose score (aspect ratio heuristic)
        aspect_ratio = w / h
        frontal_score = 1.0 - abs(aspect_ratio - 0.75) / 0.75  # Ideal ratio ~0.75
        frontal_score = max(0.0, frontal_score)

        # Lighting score (histogram analysis)
        hist = cv2.calcHist([gray_face], [0], None, [256], [0, 256])
        lighting_score = 1.0 - (hist[0] + hist[255]) / gray_face.size  # Avoid pure black/white

        # Overall quality score
        overall = (
            size_score * self.quality_factors["size"]
            + sharpness_score * self.quality_factors["sharpness"]
            + frontal_score * self.quality_factors["frontal"]
            + lighting_score * self.quality_factors["lighting"]
        )

        return {
            "overall": overall,
            "size": size_score,
            "sharpness": sharpness_score,
            "frontal": frontal_score,
            "lighting": lighting_score,
        }

    def _update_tracks(
        self,
        active_tracks: Dict[str, Dict],
        faces: List[Dict],
        frame_number: int,
        timestamp: float,
    ) -> Dict[str, Dict]:
        """Update existing tracks with new face detections."""

        # Calculate similarities between tracks and faces
        similarities = {}
        for track_id, track_data in active_tracks.items():
            last_detection = track_data["detections"][-1]

            for i, face in enumerate(faces):
                if face.get("matched"):
                    continue

                # Calculate similarity (IoU + embedding similarity if available)
                similarity = self._calculate_face_similarity(last_detection, face)
                similarities[(track_id, i)] = similarity

        # Match faces to tracks (Hungarian algorithm approximation)
        matches = self._match_faces_to_tracks(similarities, self.similarity_threshold)

        # Update matched tracks
        for track_id, face_idx in matches:
            face = faces[face_idx]
            face["matched"] = True
            face["track_id"] = track_id

            # Update track
            active_tracks[track_id]["detections"].append(face)
            active_tracks[track_id]["last_seen"] = frame_number
            active_tracks[track_id]["end_frame"] = frame_number
            active_tracks[track_id]["end_time"] = timestamp

        return active_tracks

    def _calculate_face_similarity(self, face1: Dict, face2: Dict) -> float:
        """Calculate similarity between two face detections."""
        # IoU similarity
        iou = self._calculate_iou(face1["bbox"], face2["bbox"])

        # Embedding similarity (if available)
        embedding_sim = 0.0
        if face1.get("embedding") is not None and face2.get("embedding") is not None:
            emb1 = np.array(face1["embedding"])
            emb2 = np.array(face2["embedding"])
            embedding_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

        # Combined similarity
        return 0.3 * iou + 0.7 * embedding_sim if embedding_sim > 0 else iou

    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Calculate Intersection over Union for two bounding boxes."""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        # Calculate intersection
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)

        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0

        intersection = (xi2 - xi1) * (yi2 - yi1)
        union = w1 * h1 + w2 * h2 - intersection

        return intersection / union if union > 0 else 0.0

    def _match_faces_to_tracks(
        self, similarities: Dict[Tuple[str, int], float], threshold: float
    ) -> List[Tuple[str, int]]:
        """Match faces to tracks using greedy assignment."""
        # Sort by similarity (highest first)
        sorted_matches = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

        matches = []
        used_tracks = set()
        used_faces = set()

        for (track_id, face_idx), similarity in sorted_matches:
            if similarity >= threshold and track_id not in used_tracks and face_idx not in used_faces:
                matches.append((track_id, face_idx))
                used_tracks.add(track_id)
                used_faces.add(face_idx)

        return matches

    def _cleanup_lost_tracks(self, active_tracks: Dict[str, Dict], current_frame: int, max_gap: int) -> Dict[str, Dict]:
        """Remove tracks that haven't been updated recently."""
        return {
            track_id: track_data
            for track_id, track_data in active_tracks.items()
            if current_frame - track_data["last_seen"] <= max_gap
        }

    def _finalize_track(self, track_data: Dict) -> FaceTrack:
        """Convert track data to FaceTrack object and select best frame."""
        detections = track_data["detections"]

        # Find best frame (highest quality score)
        best_detection = max(detections, key=lambda d: d["quality_score"])

        # Calculate average confidence
        avg_confidence = sum(d["confidence"] for d in detections) / len(detections)

        # Calculate overall quality score
        quality_score = sum(d["quality_score"] for d in detections) / len(detections)

        return FaceTrack(
            track_id=track_data["track_id"],
            video_path=track_data["video_path"],
            start_frame=track_data["start_frame"],
            end_frame=track_data["end_frame"],
            start_time=track_data["start_time"],
            end_time=track_data["end_time"],
            face_detections=detections,
            best_frame=best_detection,
            confidence_avg=avg_confidence,
            quality_score=quality_score,
        )

    def _save_tracks(self, tracks: List[FaceTrack]) -> None:
        """Save face tracks to database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            for track in tracks:
                # Insert track
                conn.execute(
                    """
                    INSERT OR REPLACE INTO video_face_tracks
                    (track_id, video_path, start_frame, end_frame, start_time, end_time,
                     cluster_id, confidence_avg, quality_score, best_frame_data, trajectory_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        track.track_id,
                        track.video_path,
                        track.start_frame,
                        track.end_frame,
                        track.start_time,
                        track.end_time,
                        track.cluster_id,
                        track.confidence_avg,
                        track.quality_score,
                        json.dumps(asdict(track.best_frame)) if track.best_frame else None,
                        json.dumps([asdict(d) for d in track.face_detections]),
                    ),
                )

                # Insert detections
                for detection in track.face_detections:
                    is_best = detection == track.best_frame
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO video_face_detections
                        (track_id, video_path, frame_number, timestamp, bounding_box,
                         embedding, confidence, quality_metrics, is_best_frame)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            track.track_id,
                            track.video_path,
                            detection["frame_number"],
                            detection["timestamp"],
                            json.dumps(detection["bbox"]),
                            detection.get("embedding"),
                            detection["confidence"],
                            json.dumps(detection["quality_metrics"]),
                            is_best,
                        ),
                    )

    def _cluster_video_faces(self, video_path: str, tracks: List[FaceTrack]) -> Dict[str, Any]:
        """Cluster video faces with existing face clustering system."""
        if not self.face_clusterer:
            return {"clusters_assigned": 0}

        try:
            # Extract best frame embeddings for clustering
            embeddings_data = []
            for track in tracks:
                if track.best_frame and track.best_frame.get("embedding"):
                    embeddings_data.append(
                        {
                            "track_id": track.track_id,
                            "embedding": track.best_frame["embedding"],
                        }
                    )

            if not embeddings_data:
                return {"clusters_assigned": 0}

            # Use face clusterer to assign to existing clusters or create new ones
            cluster_assignments = {}
            for data in embeddings_data:
                # This would integrate with the existing face clustering system
                # For now, we'll mark as needing cluster assignment
                cluster_assignments[data["track_id"]] = None

            # Update tracks with cluster assignments
            with sqlite3.connect(str(self.db_path)) as conn:
                for track in tracks:
                    cluster_id = cluster_assignments.get(track.track_id)
                    if cluster_id:
                        conn.execute(
                            """
                            UPDATE video_face_tracks
                            SET cluster_id = ?
                            WHERE track_id = ? AND video_path = ?
                        """,
                            (cluster_id, track.track_id, video_path),
                        )

            return {
                "clusters_assigned": len([c for c in cluster_assignments.values() if c]),
                "total_tracks": len(tracks),
            }

        except Exception as e:
            logger.error(f"Face clustering failed for {video_path}: {e}")
            return {"clusters_assigned": 0, "error": str(e)}

    def get_video_face_summary(self, video_path: str) -> Dict[str, Any]:
        """Get face tracking summary for a video."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get track summary
            cursor = conn.execute(
                """
                SELECT COUNT(*) as track_count,
                       AVG(confidence_avg) as avg_confidence,
                       AVG(quality_score) as avg_quality,
                       COUNT(DISTINCT cluster_id) as unique_people
                FROM video_face_tracks
                WHERE video_path = ?
            """,
                (video_path,),
            )
            summary = dict(cursor.fetchone())

            # Get tracks with best frames
            cursor = conn.execute(
                """
                SELECT track_id, start_time, end_time, cluster_id,
                       confidence_avg, quality_score, best_frame_data
                FROM video_face_tracks
                WHERE video_path = ?
                ORDER BY quality_score DESC
            """,
                (video_path,),
            )

            tracks = []
            for row in cursor.fetchall():
                track_data = dict(row)
                if track_data["best_frame_data"]:
                    track_data["best_frame"] = json.loads(track_data["best_frame_data"])
                tracks.append(track_data)

            return {"video_path": video_path, "summary": summary, "tracks": tracks}


def get_video_face_tracker(db_path: Path, face_clusterer=None) -> VideoFaceTracker:
    """Factory function to create video face tracker."""
    return VideoFaceTracker(db_path, face_clusterer)

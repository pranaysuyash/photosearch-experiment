"""
Video Face Service

Handles face detection and tracking in video files.
Phase 7 Feature: Video support without cluster pollution.

Key Design:
- Sample frames at configurable FPS (default 1 fps)
- Detect faces using InsightFace
- Build tracklets using IOU + embedding similarity
- Select best frame per track for prototype assignment
"""

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Metadata about a video file."""

    video_id: str
    file_path: str
    duration_ms: int
    fps: float
    frame_count: int
    width: int
    height: int


@dataclass
class FrameFace:
    """A face detected in a video frame."""

    detection_id: str
    frame_number: int
    timestamp_ms: int
    bounding_box: Dict[str, float]
    embedding: np.ndarray
    quality_score: float


@dataclass
class FaceTrack:
    """A tracklet of faces across frames."""

    track_id: str
    video_id: str
    detections: List[FrameFace]
    start_frame: int
    end_frame: int
    best_detection_id: Optional[str] = None
    cluster_id: Optional[str] = None


class VideoFaceService:
    """
    Service for processing faces in videos.

    Pipeline:
    1. Extract frames at sample_fps
    2. Detect faces in each frame
    3. Build tracklets (connect same face across frames)
    4. Select best frame per track
    5. Only best frames are used for prototype assignment
    """

    def __init__(self, db_path: Path, sample_fps: float = 1.0):
        """
        Initialize the video face service.

        Args:
            db_path: Path to the face clustering database
            sample_fps: Frames per second to sample (default 1.0)
        """
        self.db_path = db_path
        self.sample_fps = sample_fps

        # Thresholds for tracking
        self.iou_threshold = 0.3  # Minimum IOU for bbox association
        self.embedding_threshold = 0.6  # Minimum embedding similarity

    def _generate_video_id(self, file_path: str) -> str:
        """Generate a unique ID for a video based on its path."""
        return f"video_{hashlib.md5(file_path.encode()).hexdigest()[:16]}"

    def _generate_track_id(self, video_id: str, track_num: int) -> str:
        """Generate a unique track ID."""
        return f"track_{video_id}_{track_num}"

    def get_video_info(self, file_path: str) -> Optional[VideoInfo]:
        """
        Get video metadata using OpenCV.

        Args:
            file_path: Path to video file

        Returns:
            VideoInfo or None if failed
        """
        try:
            import cv2

            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {file_path}")
                return None

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration_ms = int((frame_count / fps) * 1000) if fps > 0 else 0

            cap.release()

            return VideoInfo(
                video_id=self._generate_video_id(file_path),
                file_path=file_path,
                duration_ms=duration_ms,
                fps=fps,
                frame_count=frame_count,
                width=width,
                height=height,
            )
        except Exception as e:
            logger.error(f"Failed to get video info for {file_path}: {e}")
            return None

    def extract_frames(
        self, file_path: str, sample_fps: Optional[float] = None
    ) -> List[Tuple[int, int, np.ndarray]]:
        """
        Extract frames from video at specified sample rate.

        Args:
            file_path: Path to video file
            sample_fps: Override default sample FPS

        Returns:
            List of (frame_number, timestamp_ms, frame_image)
        """
        try:
            import cv2

            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {file_path}")
                return []

            video_fps = cap.get(cv2.CAP_PROP_FPS)
            sample_rate = sample_fps or self.sample_fps

            # Calculate frame interval
            frame_interval = max(1, int(video_fps / sample_rate))

            frames = []
            frame_num = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_num % frame_interval == 0:
                    timestamp_ms = int((frame_num / video_fps) * 1000)
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append((frame_num, timestamp_ms, frame_rgb))

                frame_num += 1

            cap.release()
            logger.info(
                f"Extracted {len(frames)} frames from {file_path} at {sample_rate} fps"
            )
            return frames

        except ImportError:
            logger.error(
                "OpenCV not available. Install with: pip install opencv-python"
            )
            return []
        except Exception as e:
            logger.error(f"Failed to extract frames from {file_path}: {e}")
            return []

    def detect_faces_in_frames(
        self, frames: List[Tuple[int, int, np.ndarray]], video_id: str
    ) -> List[FrameFace]:
        """
        Detect faces in extracted frames using InsightFace.

        Args:
            frames: List of (frame_number, timestamp_ms, frame_image)
            video_id: Video ID for detection IDs

        Returns:
            List of FrameFace detections
        """
        try:
            from server.face_detection_service import get_face_detection_service

            detection_service = get_face_detection_service()
            if not detection_service.is_available():
                logger.warning("Face detection service not available")
                return []

            all_detections = []

            for frame_num, timestamp_ms, frame in frames:
                # Detect faces in frame (pass numpy array directly)
                result = detection_service.detect_faces_from_array(frame)

                if not result.success:
                    continue

                for i, face in enumerate(result.faces):
                    detection_id = f"vface_{video_id}_{frame_num}_{i}"

                    all_detections.append(
                        FrameFace(
                            detection_id=detection_id,
                            frame_number=frame_num,
                            timestamp_ms=timestamp_ms,
                            bounding_box=face.bounding_box,
                            embedding=np.array(face.embedding),
                            quality_score=face.quality_score or 0.5,
                        )
                    )

            logger.info(f"Detected {len(all_detections)} faces in {len(frames)} frames")
            return all_detections

        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return []

    def _calculate_iou(self, box1: Dict[str, float], box2: Dict[str, float]) -> float:
        """Calculate Intersection over Union of two bounding boxes."""
        x1 = max(box1["x"], box2["x"])
        y1 = max(box1["y"], box2["y"])
        x2 = min(box1["x"] + box1["width"], box2["x"] + box2["width"])
        y2 = min(box1["y"] + box1["height"], box2["y"] + box2["height"])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = box1["width"] * box1["height"]
        area2 = box2["width"] * box2["height"]
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    def _embedding_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings."""
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    def build_tracklets(
        self, detections: List[FrameFace], video_id: str
    ) -> List[FaceTrack]:
        """
        Build face tracklets from detections using IOU + embedding similarity.

        Args:
            detections: List of face detections sorted by frame
            video_id: Video ID

        Returns:
            List of FaceTrack objects
        """
        if not detections:
            return []

        # Sort by frame number
        sorted_detections = sorted(detections, key=lambda d: d.frame_number)

        # Group by frame
        frames: Dict[int, List[FrameFace]] = {}
        for d in sorted_detections:
            if d.frame_number not in frames:
                frames[d.frame_number] = []
            frames[d.frame_number].append(d)

        frame_numbers = sorted(frames.keys())

        # Active tracks
        active_tracks: List[List[FrameFace]] = []
        completed_tracks: List[List[FrameFace]] = []

        for frame_num in frame_numbers:
            current_faces = frames[frame_num]
            matched_track_indices = set()
            matched_face_indices = set()

            # Try to match current faces to active tracks
            for face_idx, face in enumerate(current_faces):
                best_track_idx = -1
                best_score = 0

                for track_idx, track in enumerate(active_tracks):
                    if track_idx in matched_track_indices:
                        continue

                    last_face = track[-1]

                    # Only consider tracks from recent frames (within 5 frames)
                    if frame_num - last_face.frame_number > 5:
                        continue

                    iou = self._calculate_iou(last_face.bounding_box, face.bounding_box)
                    sim = self._embedding_similarity(
                        last_face.embedding, face.embedding
                    )

                    # Combined score
                    if iou >= self.iou_threshold and sim >= self.embedding_threshold:
                        score = 0.4 * iou + 0.6 * sim
                        if score > best_score:
                            best_score = score
                            best_track_idx = track_idx

                if best_track_idx >= 0:
                    active_tracks[best_track_idx].append(face)
                    matched_track_indices.add(best_track_idx)
                    matched_face_indices.add(face_idx)

            # Start new tracks for unmatched faces
            for face_idx, face in enumerate(current_faces):
                if face_idx not in matched_face_indices:
                    active_tracks.append([face])

            # Move stale tracks to completed
            new_active = []
            for track_idx, track in enumerate(active_tracks):
                last_face = track[-1]
                if frame_num - last_face.frame_number > 10:
                    if len(track) >= 2:  # Only keep tracks with 2+ detections
                        completed_tracks.append(track)
                else:
                    new_active.append(track)
            active_tracks = new_active

        # Add remaining active tracks
        for track in active_tracks:
            if len(track) >= 2:
                completed_tracks.append(track)

        # Convert to FaceTrack objects
        result = []
        for i, track_detections in enumerate(completed_tracks):
            track_id = self._generate_track_id(video_id, i)
            result.append(
                FaceTrack(
                    track_id=track_id,
                    video_id=video_id,
                    detections=track_detections,
                    start_frame=track_detections[0].frame_number,
                    end_frame=track_detections[-1].frame_number,
                )
            )

        logger.info(f"Built {len(result)} tracks from {len(detections)} detections")
        return result

    def select_best_frames(self, tracks: List[FaceTrack]) -> List[FaceTrack]:
        """
        Select the best frame for each track based on quality score.

        Args:
            tracks: List of face tracks

        Returns:
            Updated tracks with best_detection_id set
        """
        for track in tracks:
            if not track.detections:
                continue

            # Find detection with highest quality
            best = max(track.detections, key=lambda d: d.quality_score)
            track.best_detection_id = best.detection_id

        return tracks

    def store_video_results(
        self, video_info: VideoInfo, tracks: List[FaceTrack]
    ) -> bool:
        """
        Store video processing results to database.

        Args:
            video_info: Video metadata
            tracks: Processed face tracks

        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Store video asset
                conn.execute(
                    """
                    INSERT OR REPLACE INTO video_assets
                    (video_id, file_path, duration_ms, fps, frame_count, width, height, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        video_info.video_id,
                        video_info.file_path,
                        video_info.duration_ms,
                        video_info.fps,
                        video_info.frame_count,
                        video_info.width,
                        video_info.height,
                    ),
                )

                for track in tracks:
                    # Store each detection
                    for detection in track.detections:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO face_detections
                            (detection_id, photo_path, bounding_box, embedding, quality_score,
                             source_type, video_id, frame_number, timestamp_ms, is_best_frame)
                            VALUES (?, ?, ?, ?, ?, 'video', ?, ?, ?, ?)
                            """,
                            (
                                detection.detection_id,
                                video_info.file_path,  # photo_path = video path
                                str(detection.bounding_box),
                                detection.embedding.tobytes(),
                                detection.quality_score,
                                video_info.video_id,
                                detection.frame_number,
                                detection.timestamp_ms,
                                1
                                if detection.detection_id == track.best_detection_id
                                else 0,
                            ),
                        )

                    # Calculate timestamps
                    start_ts = track.detections[0].timestamp_ms
                    end_ts = track.detections[-1].timestamp_ms
                    avg_quality = sum(d.quality_score for d in track.detections) / len(
                        track.detections
                    )

                    # Store track
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO face_tracks
                        (track_id, video_id, start_frame, end_frame, start_timestamp_ms,
                         end_timestamp_ms, best_detection_id, detection_count, avg_quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            track.track_id,
                            track.video_id,
                            track.start_frame,
                            track.end_frame,
                            start_ts,
                            end_ts,
                            track.best_detection_id,
                            len(track.detections),
                            avg_quality,
                        ),
                    )

                    # Store track-detection links
                    for detection in track.detections:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO track_detections
                            (detection_id, track_id, frame_number, timestamp_ms)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                detection.detection_id,
                                track.track_id,
                                detection.frame_number,
                                detection.timestamp_ms,
                            ),
                        )

                conn.commit()
                logger.info(
                    f"Stored {len(tracks)} tracks for video {video_info.video_id}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to store video results: {e}")
            return False

    def process_video(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Full pipeline: process a video for faces.

        Args:
            file_path: Path to video file

        Returns:
            Processing results or None if failed
        """
        logger.info(f"Processing video: {file_path}")

        # 1. Get video info
        video_info = self.get_video_info(file_path)
        if not video_info:
            return None

        # 2. Extract frames
        frames = self.extract_frames(file_path)
        if not frames:
            logger.warning(f"No frames extracted from {file_path}")
            return {"video_id": video_info.video_id, "tracks": 0, "detections": 0}

        # 3. Detect faces
        detections = self.detect_faces_in_frames(frames, video_info.video_id)
        if not detections:
            logger.info(f"No faces detected in {file_path}")
            return {"video_id": video_info.video_id, "tracks": 0, "detections": 0}

        # 4. Build tracklets
        tracks = self.build_tracklets(detections, video_info.video_id)

        # 5. Select best frames
        tracks = self.select_best_frames(tracks)

        # 6. Store results
        self.store_video_results(video_info, tracks)

        return {
            "video_id": video_info.video_id,
            "tracks": len(tracks),
            "detections": len(detections),
            "duration_ms": video_info.duration_ms,
            "frames_processed": len(frames),
        }


def get_video_face_service(db_path: Path) -> VideoFaceService:
    """Get a VideoFaceService instance."""
    return VideoFaceService(db_path)

"""
Video Faces API Router

Endpoints for processing faces in videos and retrieving video face data.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from server.api.deps import get_state
from server.core.state import AppState

logger = logging.getLogger(__name__)
router = APIRouter()


# ----- Request/Response Models -----


class ProcessVideoRequest(BaseModel):
    """Request to process a video for faces."""

    file_path: str
    sample_fps: Optional[float] = 1.0


class ProcessVideoResponse(BaseModel):
    """Response from video processing."""

    video_id: str
    status: str
    tracks: int = 0
    detections: int = 0
    duration_ms: int = 0
    frames_processed: int = 0
    message: Optional[str] = None


class VideoFaceTrack(BaseModel):
    """A face track in a video."""

    track_id: str
    video_id: str
    start_frame: int
    end_frame: int
    start_timestamp_ms: int
    end_timestamp_ms: int
    best_detection_id: Optional[str]
    cluster_id: Optional[str]
    detection_count: int
    avg_quality_score: float
    person_name: Optional[str] = None


class VideoTracksResponse(BaseModel):
    """Response containing video tracks."""

    video_id: str
    tracks: list[VideoFaceTrack]


class VideoPersonAppearance(BaseModel):
    """A person's appearance in a video."""

    cluster_id: str
    person_name: Optional[str]
    track_count: int
    total_screen_time_ms: int
    first_appearance_ms: int
    last_appearance_ms: int


class VideoPeopleResponse(BaseModel):
    """Response containing people appearing in a video."""

    video_id: str
    people: list[VideoPersonAppearance]


# ----- Background Task -----


def _process_video_background(file_path: str, sample_fps: float, db_path: Path, state: AppState):
    """Background task to process a video for faces."""
    try:
        from server.video_face_service import VideoFaceService

        service = VideoFaceService(db_path, sample_fps)
        result = service.process_video(file_path)

        if result:
            logger.info(f"Video processed: {file_path} - {result.get('tracks', 0)} tracks")
        else:
            logger.error(f"Video processing failed: {file_path}")
    except Exception as e:
        logger.error(f"Background video processing error: {e}")


# ----- Endpoints -----


@router.post("/process", response_model=ProcessVideoResponse)
async def process_video(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    state: AppState = Depends(get_state),
):
    """
    Start processing a video for faces.

    This is an async operation - the endpoint returns immediately
    and processing continues in the background.
    """
    file_path = request.file_path

    # Validate file exists
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    # Validate it's a video
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    if Path(file_path).suffix.lower() not in video_extensions:
        raise HTTPException(status_code=400, detail="Not a supported video format")

    # Generate video ID
    import hashlib

    video_id = f"video_{hashlib.md5(file_path.encode()).hexdigest()[:16]}"

    # Check if global face indexing is paused
    if state.face_db and state.face_db.is_face_indexing_paused():
        return ProcessVideoResponse(
            video_id=video_id,
            status="paused",
            message="Global face indexing is paused",
        )

    # Start background processing
    db_path = state.face_db.db_path if state.face_db else None
    if not db_path:
        raise HTTPException(status_code=503, detail="Face database not initialized")

    background_tasks.add_task(
        _process_video_background,
        file_path,
        request.sample_fps or 1.0,
        db_path,
        state,
    )

    return ProcessVideoResponse(
        video_id=video_id,
        status="processing",
        message="Video processing started in background",
    )


@router.get("/status/{video_id}", response_model=ProcessVideoResponse)
async def get_video_status(
    video_id: str,
    state: AppState = Depends(get_state),
):
    """Get the processing status of a video."""
    if not state.face_db:
        raise HTTPException(status_code=503, detail="Face database not initialized")

    try:
        with state.face_db._connect() as conn:
            cursor = conn.execute(
                """
                SELECT video_id, file_path, duration_ms, processed_at
                FROM video_assets
                WHERE video_id = ?
                """,
                (video_id,),
            )
            row = cursor.fetchone()

            if not row:
                return ProcessVideoResponse(
                    video_id=video_id,
                    status="not_found",
                    message="Video not found or not yet processed",
                )

            # Get track count
            track_cursor = conn.execute(
                "SELECT COUNT(*) FROM face_tracks WHERE video_id = ?",
                (video_id,),
            )
            track_count = track_cursor.fetchone()[0]

            # Get detection count
            detection_cursor = conn.execute(
                "SELECT COUNT(*) FROM face_detections WHERE video_id = ?",
                (video_id,),
            )
            detection_count = detection_cursor.fetchone()[0]

            return ProcessVideoResponse(
                video_id=video_id,
                status="completed" if row["processed_at"] else "processing",
                tracks=track_count,
                detections=detection_count,
                duration_ms=row["duration_ms"] or 0,
            )
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracks/{video_id}", response_model=VideoTracksResponse)
async def get_video_tracks(
    video_id: str,
    state: AppState = Depends(get_state),
):
    """Get all face tracks for a video."""
    if not state.face_db:
        raise HTTPException(status_code=503, detail="Face database not initialized")

    try:
        with state.face_db._connect() as conn:
            cursor = conn.execute(
                """
                SELECT
                    ft.track_id,
                    ft.video_id,
                    ft.start_frame,
                    ft.end_frame,
                    ft.start_timestamp_ms,
                    ft.end_timestamp_ms,
                    ft.best_detection_id,
                    ft.cluster_id,
                    ft.detection_count,
                    ft.avg_quality_score,
                    fc.label as person_name
                FROM face_tracks ft
                LEFT JOIN face_clusters fc ON ft.cluster_id = fc.cluster_id
                WHERE ft.video_id = ?
                ORDER BY ft.start_timestamp_ms
                """,
                (video_id,),
            )

            tracks = []
            for row in cursor.fetchall():
                tracks.append(
                    VideoFaceTrack(
                        track_id=row["track_id"],
                        video_id=row["video_id"],
                        start_frame=row["start_frame"],
                        end_frame=row["end_frame"],
                        start_timestamp_ms=row["start_timestamp_ms"],
                        end_timestamp_ms=row["end_timestamp_ms"],
                        best_detection_id=row["best_detection_id"],
                        cluster_id=row["cluster_id"],
                        detection_count=row["detection_count"],
                        avg_quality_score=row["avg_quality_score"],
                        person_name=row["person_name"],
                    )
                )

            return VideoTracksResponse(video_id=video_id, tracks=tracks)
    except Exception as e:
        logger.error(f"Error getting video tracks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/people/{video_id}", response_model=VideoPeopleResponse)
async def get_video_people(
    video_id: str,
    state: AppState = Depends(get_state),
):
    """Get all people appearing in a video with their screen time."""
    if not state.face_db:
        raise HTTPException(status_code=503, detail="Face database not initialized")

    try:
        with state.face_db._connect() as conn:
            cursor = conn.execute(
                """
                SELECT
                    ft.cluster_id,
                    fc.label as person_name,
                    COUNT(*) as track_count,
                    SUM(ft.end_timestamp_ms - ft.start_timestamp_ms) as total_screen_time_ms,
                    MIN(ft.start_timestamp_ms) as first_appearance_ms,
                    MAX(ft.end_timestamp_ms) as last_appearance_ms
                FROM face_tracks ft
                LEFT JOIN face_clusters fc ON ft.cluster_id = fc.cluster_id
                WHERE ft.video_id = ? AND ft.cluster_id IS NOT NULL
                GROUP BY ft.cluster_id
                ORDER BY total_screen_time_ms DESC
                """,
                (video_id,),
            )

            people = []
            for row in cursor.fetchall():
                people.append(
                    VideoPersonAppearance(
                        cluster_id=row["cluster_id"],
                        person_name=row["person_name"],
                        track_count=row["track_count"],
                        total_screen_time_ms=row["total_screen_time_ms"] or 0,
                        first_appearance_ms=row["first_appearance_ms"] or 0,
                        last_appearance_ms=row["last_appearance_ms"] or 0,
                    )
                )

            return VideoPeopleResponse(video_id=video_id, people=people)
    except Exception as e:
        logger.error(f"Error getting video people: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{video_id}")
async def delete_video_faces(
    video_id: str,
    state: AppState = Depends(get_state),
):
    """Delete all face data for a video."""
    if not state.face_db:
        raise HTTPException(status_code=503, detail="Face database not initialized")

    try:
        with state.face_db._connect() as conn:
            # Delete track-detection links
            conn.execute(
                """
                DELETE FROM track_detections
                WHERE track_id IN (SELECT track_id FROM face_tracks WHERE video_id = ?)
                """,
                (video_id,),
            )

            # Delete tracks
            conn.execute("DELETE FROM face_tracks WHERE video_id = ?", (video_id,))

            # Delete detections
            conn.execute("DELETE FROM face_detections WHERE video_id = ?", (video_id,))

            # Delete video asset
            conn.execute("DELETE FROM video_assets WHERE video_id = ?", (video_id,))

            conn.commit()

            return {"status": "deleted", "video_id": video_id}
    except Exception as e:
        logger.error(f"Error deleting video faces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

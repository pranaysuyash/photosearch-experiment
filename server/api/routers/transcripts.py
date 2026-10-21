"""
Video Transcripts API Router

Endpoints over the audio transcription service (server/
audio_transcription_service.py): status, on-demand transcription, retrieval,
full-text search, batch backfill, deletion. All SQL lives in the service;
this router holds none.
"""

import glob
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.api.deps import get_state
from server.config import settings
from server.core.state import AppState


router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


def _service():
    from server.audio_transcription_service import get_transcription_service

    return get_transcription_service()


def _video_paths(limit: int = 500) -> List[str]:
    """Video paths known to the library (recursive media dir scan)."""
    paths: List[str] = []
    media_dir = str(settings.MEDIA_DIR)
    for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"):
        paths.extend(glob.glob(os.path.join(media_dir, f"**/*{ext}"), recursive=True))
    return paths[:limit]


class TranscribeRequest(BaseModel):
    video_path: str
    force: bool = False


class BatchTranscribeRequest(BaseModel):
    limit: int = 5


@router.get("/status")
async def transcripts_status(state: AppState = Depends(get_state)):
    return _service().stats()


@router.post("/transcribe")
async def transcribe(request: TranscribeRequest, state: AppState = Depends(get_state)):
    result = _service().transcribe(request.video_path, force=request.force)
    if result.get("error"):
        status = 404 if "not found" in result["error"] else 503 if "backend" in result["error"] else 502
        raise HTTPException(status_code=status, detail=result["error"])
    return result


@router.post("/batch")
async def transcribe_batch(request: BatchTranscribeRequest, state: AppState = Depends(get_state)):
    paths = _video_paths(limit=1000)
    return _service().transcribe_missing(paths, limit=request.limit)


@router.get("/search")
async def search_transcripts(q: str, limit: int = 20, state: AppState = Depends(get_state)):
    return {"query": q, "results": _service().search(q, limit=limit)}


@router.get("/{video_path:path}")
async def get_transcript(video_path: str, state: AppState = Depends(get_state)):
    transcript = _service().get(video_path)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@router.delete("/{video_path:path}")
async def delete_transcript(video_path: str, state: AppState = Depends(get_state)):
    _service().delete(video_path)
    return {"success": True, "message": "Transcript deleted"}

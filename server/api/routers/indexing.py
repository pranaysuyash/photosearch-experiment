"""
Indexing Router

Uses Depends(get_state) for accessing shared application state.
"""

import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query

from server.jobs import Job, job_store
from server.models.schemas.search import ScanRequest
from server.services.semantic_indexing import process_semantic_indexing
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/scan")
async def scan_directory(
    background_tasks: BackgroundTasks,
    state: AppState = Depends(get_state),
    payload: dict = Body(...),
):
    """
    Scan a directory for photos.
    Supports asynchronous scanning via background tasks.
    """
    path = payload.get("path")
    force = payload.get("force", False)
    background = payload.get("background", True)

    if not path:
        raise HTTPException(status_code=400, detail="Path is required")

    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Directory does not exist")

    photo_search_engine = state.photo_search_engine
    # Capture references for background task closure
    embedding_generator = state.embedding_generator
    vector_store = state.vector_store

    # If background processing is requested (default)
    if background:
        job_id = job_store.create_job(type="scan")

        # Define the background task wrapper
        def run_scan(job_id: str, path: str, force: bool):
            try:
                # The scan method should update the job status internally
                # and return the list of files for semantic indexing
                scan_results = photo_search_engine.scan(path, force=force, job_id=job_id)

                # After scanning metadata, perform semantic indexing
                all_files = scan_results.get("all_files", [])
                if all_files and embedding_generator and vector_store:
                    process_semantic_indexing(all_files, embedding_generator, vector_store)

                job_store.update_job(
                    job_id,
                    status="completed",
                    message="Scan and indexing finished.",
                )
            except Exception as e:
                print(f"Job {job_id} failed: {e}")
                job_store.update_job(job_id, status="failed", message=str(e))

        background_tasks.add_task(run_scan, job_id, path, force)

        return {"job_id": job_id, "status": "pending", "message": "Scan started in background"}
    else:
        # Synchronous (Legacy/Blocking)
        try:
            results = photo_search_engine.scan(path, force=force)

            # Perform semantic indexing synchronously if not in background
            all_files = results.get("all_files", [])
            if all_files:
                state.process_semantic_indexing(all_files)

            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_status(job_id: str):
    """Get the status of a background job."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List jobs, newest first. Complements GET /jobs/{job_id}."""
    try:
        jobs = job_store.list_jobs(status=status, limit=limit, offset=offset)
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def force_indexing(request: ScanRequest, state: AppState = Depends(get_state)):
    """
    Force semantic indexing of a directory (without re-scanning metadata).
    """
    try:
        # Just walk and index
        files_to_index = []
        for root, dirs, files in os.walk(request.path):
            for file in files:
                files_to_index.append(os.path.join(root, file))

        if files_to_index:
            state.process_semantic_indexing(files_to_index)

        return {"status": "success", "indexed": len(files_to_index)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Background image-quality space (EG2)
# ─────────────────────────────────────────────────────────────────────────────


def _builder(state: AppState):
    builder = state.quality_builder
    if builder is None:
        raise HTTPException(status_code=503, detail="Quality index not configured")
    return builder


@router.get("/api/indexing/quality")
async def quality_index_status(state: AppState = Depends(get_state)):
    """Status of the background EG2 quality space (counts, backend, idle gate)."""
    return _builder(state).status()


@router.post("/api/indexing/quality/start")
async def start_quality_builder(state: AppState = Depends(get_state)):
    builder = _builder(state)
    if not builder.quality_index.embedder.available():
        raise HTTPException(
            status_code=503, detail="No EG2 backend available (pip install mlx mlx-vlm, or check HF access)"
        )
    builder.start()
    return {"success": True, "status": builder.status()}


@router.post("/api/indexing/quality/build-once")
async def build_quality_once(state: AppState = Depends(get_state)):
    """Embed one batch of pending images synchronously (builder must be idle)."""
    builder = _builder(state)
    if builder.running:
        raise HTTPException(status_code=409, detail="Builder loop is running; use its idle cycle instead")
    stats = builder.build_batch()
    return {"success": True, "batch": stats, "status": builder.status()}


@router.post("/api/indexing/quality/stop")
async def stop_quality_builder(state: AppState = Depends(get_state)):
    builder = _builder(state)
    builder.stop()
    return {"success": True, "status": builder.status()}

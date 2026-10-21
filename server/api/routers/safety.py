"""Sensitive-content classification API.

On-demand NSFW classification (local model, default-off). Flag storage and
privacy-surface integration are intentionally deferred to an owner decision;
these endpoints only classify and report.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter(prefix="/api/safety", tags=["safety"])


class ClassifyRequest(BaseModel):
    path: str


class ClassifyBatchRequest(BaseModel):
    paths: List[str]
    limit: int = 50


def _classifier():
    from server.safety_classifier import get_safety_classifier

    return get_safety_classifier()


@router.get("/status")
async def safety_status(state: AppState = Depends(get_state)):
    classifier = _classifier()
    return {
        "enabled": classifier.enabled,
        "available": classifier.is_available(),
        "model": classifier.model_name,
        "note": (
            "Classification only — results are not stored and never hide or "
            "delete media. Flag persistence is pending an owner decision."
        ),
    }


@router.post("/classify")
async def classify_image(request: ClassifyRequest, state: AppState = Depends(get_state)):
    import os

    classifier = _classifier()
    if not classifier.is_available():
        raise HTTPException(status_code=503, detail="NSFW detection is disabled (NSFW_DETECTION_ENABLED)")

    if not os.path.isfile(request.path):
        raise HTTPException(status_code=404, detail="Image not found")

    result = classifier.classify(request.path)
    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.post("/classify-batch")
async def classify_batch(request: ClassifyBatchRequest, state: AppState = Depends(get_state)):
    import os

    classifier = _classifier()
    if not classifier.is_available():
        raise HTTPException(status_code=503, detail="NSFW detection is disabled (NSFW_DETECTION_ENABLED)")

    existing = [p for p in request.paths if os.path.isfile(p)]
    return classifier.classify_batch(existing, limit=request.limit)

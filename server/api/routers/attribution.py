"""
Attribution router — exposes photo source attribution and content provenance.

Contract: `docs/decisions/2026-10-21-photo-source-attribution.md` §2.4.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from server.api.deps import get_state
from server.attribution import AttributionResolver
from server.config import settings
from server.content_provenance import detect_content_provenance
from server.core.state import AppState

router = APIRouter()


def _resolver(state: AppState) -> AttributionResolver:
    return AttributionResolver(
        source_store=getattr(state, "source_store", None),
        source_item_store=getattr(state, "source_item_store", None),
        media_root=settings.MEDIA_DIR,
    )


@router.get("/attribution")
async def get_attribution(
    path: str = Query(..., description="Absolute path of the media file"),
    include_content: bool = Query(False, description="Also inspect the file for content-provenance markers"),
    state: AppState = Depends(get_state),
):
    """Source attribution for a single media file.

    Returns an honest record: `kind` is `local`, `cloud` or `unknown`, and
    `match` says how the attribution was resolved.
    """
    resolver = _resolver(state)
    attribution = resolver.resolve(path)
    payload = attribution.to_dict()
    if include_content:
        payload["content"] = detect_content_provenance(path)
    return payload


@router.get("/attribution/batch")
async def get_attributions(
    path: List[str] = Query(default_factory=list, description="Media file paths"),
    include_content: bool = Query(False, description="Also inspect files for content-provenance markers"),
    state: AppState = Depends(get_state),
):
    """Source attribution for many media files in one round trip.

    Returns `{ "attributions": { "<path>": <record> } }`.
    """
    resolver = _resolver(state)
    resolved = resolver.resolve_many(path)
    out = {}
    for p, attribution in resolved.items():
        record = attribution.to_dict()
        if include_content:
            record["content"] = detect_content_provenance(p)
        out[p] = record
    return {"attributions": out}

"""
Bootstrap module - builds AppState using components.

This module is called once during FastAPI lifespan to create the application state.

IMPORTANT:
- Uses server/core/components.py for component initialization
- Does NOT import src.* modules directly (avoids import-time side effects)
- Does NOT import routers
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from server.core.state import AppState
from server.core.paths import _runtime_base_dir
from server.config import settings


def init_stores(base_dir: Path) -> dict[str, Any]:
    """Initialize store objects. Light-weight, no model downloads."""
    from server.lancedb_store import LanceDBStore
    from server.sources import SourceStore
    from server.source_items import SourceItemStore
    from server.trash_db import TrashDB
    from src.intent_recognition import IntentDetector
    from src.saved_searches import SavedSearchManager

    return {
        "vector_store": LanceDBStore(),
        "intent_detector": IntentDetector(),
        "saved_search_manager": SavedSearchManager(),
        "source_store": SourceStore(base_dir / "sources.db"),
        "source_item_store": SourceItemStore(base_dir / "sources_items.db"),
        "trash_db": TrashDB(base_dir / "trash.db"),
    }


def init_components(base_dir: Path) -> dict[str, Any]:
    """
    Initialize components that may have heavy imports.

    This wraps the existing server/core/components.py module-level objects.
    In future, components.py should expose an init function instead.
    """
    # Import from components.py - this triggers the existing module-level init
    # Note: components.py uses module-level initialization for performance
    from server.core import components

    return {
        "face_clusterer": components.face_clusterer,
        "ocr_search": components.ocr_search,
        "video_analyzer": components.video_analyzer,
        "modal_system": components.modal_system,
        "code_splitting_config": components.code_splitting_config,
        "lazy_load_tracker": components.lazy_load_tracker,
        "tauri_integration": components.tauri_integration,
    }


def init_api_utilities() -> dict[str, Any]:
    """Initialize API versioning and cache managers."""
    from src.api_versioning import api_version_manager
    from src.cache_manager import cache_manager
    from src.logging_config import log_search_operation

    return {
        "api_version_manager": api_version_manager,
        "cache_manager": cache_manager,
        "log_search_operation": log_search_operation,
    }


def build_state(*, skip_heavy_components: bool = False) -> AppState:
    """
    Build complete application state.

    Called once in lifespan. Some fields (photo_search_engine, embedding_generator)
    are populated after this by lifespan itself.

    Args:
        skip_heavy_components: If True, skip face_clusterer etc.
                               Useful for contract dumping without model downloads.
    """
    base_dir = _runtime_base_dir()

    # Initialize stores (lightweight)
    stores = init_stores(base_dir)

    # Initialize components (may trigger model downloads)
    if skip_heavy_components:
        components = {
            "face_clusterer": None,
            "ocr_search": None,
            "video_analyzer": None,
            "modal_system": None,
            "code_splitting_config": None,
            "lazy_load_tracker": None,
            "tauri_integration": None,
        }
    else:
        components = init_components(base_dir)

    # Initialize API utilities
    api_utils = init_api_utilities()

    return AppState(
        # Core
        settings=settings,
        base_dir=base_dir,
        # Stores
        vector_store=stores["vector_store"],
        intent_detector=stores["intent_detector"],
        saved_search_manager=stores["saved_search_manager"],
        source_store=stores["source_store"],
        source_item_store=stores["source_item_store"],
        trash_db=stores["trash_db"],
        # Components
        face_clusterer=components["face_clusterer"],
        ocr_search=components["ocr_search"],
        video_analyzer=components["video_analyzer"],
        modal_system=components["modal_system"],
        code_splitting_config=components["code_splitting_config"],
        lazy_load_tracker=components["lazy_load_tracker"],
        tauri_integration=components["tauri_integration"],
        # API utilities
        api_version_manager=api_utils["api_version_manager"],
        cache_manager=api_utils["cache_manager"],
        log_search_operation=api_utils["log_search_operation"],
        # These are set by lifespan after build_state
        photo_search_engine=None,
        embedding_generator=None,
        ps_logger=None,
        perf_tracker=None,
        file_watcher=None,
    )

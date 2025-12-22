"""
Application state container.

This module defines AppState - a typed container for all shared runtime state.
Routers access state via Depends(get_state) from server/api/deps.py.

IMPORTANT: This file must NOT import from:
- server.main (circular)
- server.api.routers.* (circular)
- src.* modules directly (import-time side effects)

State is populated by server/core/bootstrap.py during lifespan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    # Type hints only - not imported at runtime
    from logging import Logger
    from src.logging_config import PerformanceTracker


@dataclass
class AppState:
    """
    Application state container.
    
    All fields that routers previously accessed via `main_module.*` should be here.
    Optional fields default to None and are populated during lifespan.
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # Core Configuration
    # ─────────────────────────────────────────────────────────────────────────
    settings: Any
    base_dir: Path
    
    # ─────────────────────────────────────────────────────────────────────────
    # Stores & Managers (from former server/core/state.py module-level)
    # ─────────────────────────────────────────────────────────────────────────
    vector_store: Any  # LanceDBStore
    intent_detector: Any  # IntentDetector
    saved_search_manager: Any  # SavedSearchManager
    source_store: Any  # SourceStore
    source_item_store: Any  # SourceItemStore
    trash_db: Any  # TrashDB
    
    # ─────────────────────────────────────────────────────────────────────────
    # Search & Indexing (initialized in lifespan)
    # ─────────────────────────────────────────────────────────────────────────
    photo_search_engine: Optional[Any] = None  # PhotoSearch
    embedding_generator: Optional[Any] = None  # EmbeddingGenerator
    
    # ─────────────────────────────────────────────────────────────────────────
    # Components (from former server/core/components.py module-level)
    # ─────────────────────────────────────────────────────────────────────────
    face_clusterer: Optional[Any] = None  # FaceClusterer
    ocr_search: Optional[Any] = None  # OCRSearch
    video_analyzer: Optional[Any] = None  # VideoAnalyzer
    modal_system: Optional[Any] = None  # ModalSystem
    code_splitting_config: Optional[Any] = None  # CodeSplittingConfig
    lazy_load_tracker: Optional[Any] = None  # LazyLoadPerformanceTracker
    tauri_integration: Optional[Any] = None  # TauriIntegration
    
    # ─────────────────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────────────────
    ps_logger: Optional["Logger"] = None
    perf_tracker: Optional["PerformanceTracker"] = None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Runtime State
    # ─────────────────────────────────────────────────────────────────────────
    file_watcher: Optional[Any] = None
    face_scan_jobs: dict = field(default_factory=dict)
    
    # ─────────────────────────────────────────────────────────────────────────
    # API Versioning & Cache (accessed via main_module currently)
    # ─────────────────────────────────────────────────────────────────────────
    api_version_manager: Optional[Any] = None
    cache_manager: Optional[Any] = None
    log_search_operation: Optional[Any] = None  # Function reference
    
    # ─────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────────────
    def process_semantic_indexing(self, files_to_index: List[str]) -> None:
        """
        Wrapper for semantic indexing that provides dependencies.
        
        Args:
            files_to_index: List of file paths to index
        """
        if not self.embedding_generator or not self.vector_store:
            return
        
        from server.services.semantic_indexing import process_semantic_indexing
        process_semantic_indexing(
            files_to_index=files_to_index,
            embedding_generator=self.embedding_generator,
            vector_store=self.vector_store,
        )

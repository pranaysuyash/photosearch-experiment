import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.library import LibraryRemoveRequest
from server.models.schemas.trash import TrashEmptyRequest, TrashMoveRequest, TrashRestoreRequest


router = APIRouter()


# ==============================================================================
# TRASH / RESTORE (RECENTLY DELETED)
# ==============================================================================

def _trash_root() -> Path:
    root = settings.BASE_DIR / "trash_files"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _trash_allowed_roots() -> List[Path]:
    roots: List[Path] = [
        settings.BASE_DIR.resolve(),
        settings.MEDIA_DIR.resolve(),
        (settings.BASE_DIR / "media_sources").resolve(),
    ]
    try:
        from server import main as main_module

        for s in main_module.source_store.list_sources(redact=False):
            if s.type != "local_folder":
                continue
            p = (s.config or {}).get("path")
            if isinstance(p, str) and p:
                try:
                    roots.append(Path(p).resolve())
                except Exception:
                    continue
    except Exception:
        pass
    return roots


def _assert_path_allowed_for_trash(p: Path) -> None:
    roots = _trash_allowed_roots()
    rp = p.resolve()
    is_allowed = any(rp.is_relative_to(root) for root in roots)
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Path is outside connected sources")
    if rp.is_relative_to(_trash_root().resolve()):
        raise HTTPException(status_code=400, detail="Path is already in Trash")


def _reindex_one_file(path: str) -> None:
    try:
        from src.metadata_extractor import extract_all_metadata
        from server import main as main_module

        metadata = extract_all_metadata(path)
        if metadata:
            main_module.photo_search_engine.db.store_metadata(path, metadata)
            main_module.process_semantic_indexing([path])
    except Exception:
        # Restore should succeed even if indexing fails.
        pass


@router.post("/trash/move")
async def trash_move(req: TrashMoveRequest):
    """
    Move files into app-managed Trash and remove them from the active library index.
    For cloud sources, this moves the mirrored local copy only (does not delete remote originals).
    """
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")

    from server import main as main_module

    photo_search_engine = main_module.photo_search_engine
    source_item_store = main_module.source_item_store
    trash_db = main_module.trash_db
    vector_store = main_module.vector_store

    moved: List[dict] = []
    errors: List[str] = []
    for file_path in req.file_paths:
        try:
            src_path = Path(file_path)
            _assert_path_allowed_for_trash(src_path)
            if not src_path.exists() or not src_path.is_file():
                raise HTTPException(status_code=404, detail="File not found")

            trash_id = str(uuid.uuid4())
            dest_dir = _trash_root() / trash_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src_path.name

            shutil.move(str(src_path), str(dest))

            # Remove from active indices (metadata + embeddings)
            try:
                photo_search_engine.db.mark_as_deleted(str(src_path), reason="trashed")
            except Exception:
                pass
            try:
                vector_store.delete([str(src_path)])
            except Exception:
                pass

            # Link to a cloud source item when applicable (so sync won't re-download).
            source_item = None
            try:
                source_item = source_item_store.find_by_local_path(str(src_path.resolve()))
            except Exception:
                source_item = None
            if source_item:
                try:
                    source_item_store.set_status(source_item.source_id, source_item.remote_id, "trashed")
                    source_item_store.set_local_path(source_item.source_id, source_item.remote_id, str(dest))
                except Exception:
                    pass

            item = trash_db.create(
                item_id=trash_id,
                original_path=str(src_path),
                trashed_path=str(dest),
                source_id=source_item.source_id if source_item else None,
                remote_id=source_item.remote_id if source_item else None,
            )
            moved.append(
                {
                    "id": item.id,
                    "original_path": item.original_path,
                    "trashed_path": item.trashed_path,
                    "created_at": item.created_at,
                }
            )
        except HTTPException as he:
            errors.append(f"{file_path}: {he.detail}")
        except Exception as e:
            errors.append(f"{file_path}: {str(e)}")

    return {"moved": moved, "errors": errors}


@router.get("/trash")
async def list_trash(limit: int = 200, offset: int = 0):
    from server import main as main_module

    items = main_module.trash_db.list(status="trashed", limit=limit, offset=offset)
    out: List[dict] = []
    for it in items:
        out.append(
            {
                "id": it.id,
                "original_path": it.original_path,
                "trashed_path": it.trashed_path,
                "status": it.status,
                "source_id": it.source_id,
                "remote_id": it.remote_id,
                "created_at": it.created_at,
            }
        )
    return {"items": out}


@router.post("/trash/restore")
async def restore_from_trash(req: TrashRestoreRequest):
    if not req.item_ids:
        raise HTTPException(status_code=400, detail="item_ids is required")

    from server import main as main_module

    source_item_store = main_module.source_item_store
    trash_db = main_module.trash_db

    restored: List[str] = []
    errors: List[str] = []
    for item_id in req.item_ids:
        try:
            item = trash_db.get(item_id)
            if item.status != "trashed":
                raise HTTPException(status_code=400, detail="Item is not in Trash")

            src = Path(item.trashed_path)
            dst = Path(item.original_path)
            _assert_path_allowed_for_trash(dst)
            if not src.exists():
                raise HTTPException(status_code=404, detail="Trashed file missing")

            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

            # Reindex restored path
            _reindex_one_file(str(dst))

            if item.source_id and item.remote_id:
                try:
                    source_item_store.set_status(item.source_id, item.remote_id, "active")
                    source_item_store.set_local_path(item.source_id, item.remote_id, str(dst))
                except Exception:
                    pass

            trash_db.mark_restored(item_id)
            restored.append(item_id)
        except HTTPException as he:
            errors.append(f"{item_id}: {he.detail}")
        except Exception as e:
            errors.append(f"{item_id}: {str(e)}")

    return {"restored": restored, "errors": errors}


@router.post("/trash/empty")
async def empty_trash(req: TrashEmptyRequest):
    """
    Permanently delete files currently in Trash.
    For cloud sources, this acts as "Remove from library" (remote originals are not deleted).
    """
    from server import main as main_module

    source_item_store = main_module.source_item_store
    trash_db = main_module.trash_db

    items = []
    if req.item_ids:
        for item_id in req.item_ids:
            try:
                items.append(trash_db.get(item_id))
            except Exception:
                continue
    else:
        items = trash_db.list(status="trashed", limit=5000, offset=0)

    deleted: List[str] = []
    errors: List[str] = []
    for it in items:
        try:
            if it.status != "trashed":
                continue
            p = Path(it.trashed_path)
            if p.exists() and p.is_file():
                p.unlink()

            if it.source_id and it.remote_id:
                # Ensure sync doesn't re-download (remote originals remain).
                try:
                    source_item_store.set_status(it.source_id, it.remote_id, "removed")
                except Exception:
                    pass

            trash_db.mark_deleted(it.id)
            deleted.append(it.id)
        except Exception as e:
            errors.append(f"{it.id}: {str(e)}")

    return {"deleted": deleted, "errors": errors}


@router.post("/library/remove")
async def remove_from_library(req: LibraryRemoveRequest):
    """
    Remove items from the library index without sending them to Trash.
    - For cloud sources (Drive/S3 mirrors): deletes the local mirror and marks the source item as `removed` so it won't re-download.
    - For local files: removes from the index only (files remain on disk and may reappear if re-scanned).
    """
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")

    from server import main as main_module

    photo_search_engine = main_module.photo_search_engine
    source_item_store = main_module.source_item_store
    vector_store = main_module.vector_store

    removed: List[str] = []
    errors: List[str] = []
    for file_path in req.file_paths:
        try:
            p = Path(file_path)
            roots = _trash_allowed_roots()
            rp = p.resolve()
            if not any(rp.is_relative_to(root) for root in roots):
                raise HTTPException(status_code=403, detail="Path is outside connected sources")

            # Remove from indices (metadata + embeddings)
            try:
                photo_search_engine.db.mark_as_deleted(str(rp), reason="removed")
            except Exception:
                pass
            try:
                vector_store.delete([str(rp)])
            except Exception:
                pass

            # If this is a cloud-mirrored file, prevent re-download and delete local copy.
            source_item = None
            try:
                source_item = source_item_store.find_by_local_path(str(rp))
            except Exception:
                source_item = None
            if source_item:
                try:
                    source_item_store.set_status(source_item.source_id, source_item.remote_id, "removed")
                except Exception:
                    pass
                try:
                    if rp.exists() and rp.is_file():
                        rp.unlink()
                except Exception:
                    pass

            removed.append(str(rp))
        except HTTPException as he:
            errors.append(f"{file_path}: {he.detail}")
        except Exception as e:
            errors.append(f"{file_path}: {str(e)}")

    return {"removed": removed, "errors": errors}

"""
Photo source attribution — the canonical join between a media file and the
library it came from.

First principles (see `docs/decisions/2026-10-21-photo-source-attribution.md`):

* The source registry is the single source of truth for "where did this file
  come from". `SourceStore` holds the libraries; `SourceItemStore` holds the
  per-file records for synced cloud items. Nothing else may invent a source.
* Attribution is resolved server-side and returned as a projection. The client
  never infers a source from a path substring.
* A file that cannot be attributed is reported as `unattributed` / `unknown`.
  It is never silently labelled "local" — that was the bug the old
  path-regex filter shipped.

Content provenance (C2PA) is a *different* entity and lives in
`server/content_provenance.py`. It is detection-only: this module never makes
verification claims.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Source types that originate in the cloud (even though the working copy is
# local). Derived from `SourceStore` source `type` values.
CLOUD_SOURCE_TYPES = frozenset({"s3", "google_drive"})

# The app's own library, when no registered source covers a path.
MEDIA_ROOT_SOURCE_TYPE = "local_library"

# SQL parameter budget for chunked `IN (...)` lookups.
_SQL_CHUNK = 400


@dataclass(frozen=True)
class PhotoAttribution:
    """Where a media file came from. Derived, never guessed."""

    origin: str  # 'source' | 'media_root' | 'unattributed'
    kind: str  # 'local' | 'cloud' | 'unknown'
    match: str  # 'source_item' | 'source_root' | 'media_root' | 'none'
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    source_status: Optional[str] = None
    last_sync_at: Optional[str] = None
    item_status: Optional[str] = None
    remote_id: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    # The absolute path this attribution refers to. The catalog stores some
    # rows in a relative form; the record always says which file it is about.
    resolved_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "origin": self.origin,
            "kind": self.kind,
            "match": self.match,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_status": self.source_status,
            "last_sync_at": self.last_sync_at,
            "item_status": self.item_status,
            "remote_id": self.remote_id,
            "resolved_path": self.resolved_path,
        }
        if self.content is not None:
            payload["content"] = self.content
        return payload


def kind_for_source_type(source_type: Optional[str]) -> str:
    """Filter semantics: cloud means the *origin* is a cloud library."""
    if not source_type:
        return "unknown"
    if source_type in CLOUD_SOURCE_TYPES:
        return "cloud"
    return "local"


def _normalize(path: str) -> str:
    """Normalize a path for registry lookups without touching the filesystem."""
    if not path:
        return ""
    return os.path.normpath(path)


def _realpath(path: str) -> str:
    try:
        return os.path.realpath(path)
    except (OSError, ValueError):  # pragma: no cover - defensive
        return path


def _is_under(path: str, root: str) -> bool:
    """True when `path` is `root` or lives inside it (path-segment aware)."""
    if not path or not root:
        return False
    try:
        common = os.path.commonpath([path, root])
    except ValueError:  # different drives on Windows
        return False
    return common == root


class AttributionResolver:
    """Resolves media paths to `PhotoAttribution` using the source registry.

    The resolver is cheap to build (it holds store handles, not state) and safe
    to construct per request. Registry reads are batched so a 50-item page
    costs one or two SQL queries, not 50.
    """

    def __init__(
        self,
        source_store: Any,
        source_item_store: Any,
        media_root: Optional[Path] = None,
        base_dir: Optional[Path] = None,
    ) -> None:
        self._source_store = source_store
        self._source_item_store = source_item_store
        self._media_root = Path(media_root) if media_root else None
        self._base_dir = Path(base_dir) if base_dir else None

    def _absolute(self, path: str) -> str:
        """Resolve a possibly-relative catalog path to an absolute one.

        The metadata catalog stores two path forms for the same files (older
        scans wrote paths relative to the app base). Resolving a relative path
        against the app base is the standard interpretation of a relative
        reference — it is not a guess about provenance.
        """
        if os.path.isabs(path):
            return path
        if self._base_dir is None:
            return path
        return _normalize(str(self._base_dir / path))

    # ── registry reads ────────────────────────────────────────────────────

    def _sources(self) -> List[Any]:
        if self._source_store is None:
            return []
        try:
            return list(self._source_store.list_sources(redact=True))
        except Exception:
            return []

    def _local_roots(self) -> List[Tuple[str, Any]]:
        """Registered local-folder sources as (root_path, source_record)."""
        roots: List[Tuple[str, Any]] = []
        for src in self._sources():
            if getattr(src, "type", None) != "local_folder":
                continue
            root = (getattr(src, "config", None) or {}).get("path")
            if not root:
                continue
            roots.append((_normalize(str(root)), src))
        # Longest root first so nested folders attribute to the most specific.
        roots.sort(key=lambda pair: len(pair[0]), reverse=True)
        return roots

    def _items_by_local_path(self, paths: Sequence[str]) -> Dict[str, Any]:
        """Batch lookup of `source_items` rows by local path."""
        found: Dict[str, Any] = {}
        if self._source_item_store is None or not paths:
            return found
        candidates: List[str] = []
        for p in paths:
            norm = _normalize(p)
            if norm and norm not in candidates:
                candidates.append(norm)
        for chunk in _chunks(candidates, _SQL_CHUNK):
            try:
                rows = self._source_item_store.find_by_local_paths(chunk)
            except AttributeError:
                # Fall back to the single-path API if a batch method is absent.
                rows = []
                for p in chunk:
                    try:
                        item = self._source_item_store.find_by_local_path(p)
                    except Exception:
                        item = None
                    if item is not None:
                        rows.append(item)
            except Exception:
                rows = []
            for item in rows or []:
                local_path = getattr(item, "local_path", None)
                if local_path:
                    found[_normalize(local_path)] = item
        return found

    def _source_by_id(self) -> Dict[str, Any]:
        return {getattr(s, "id", ""): s for s in self._sources() if getattr(s, "id", None)}

    # ── resolution ────────────────────────────────────────────────────────

    def resolve_many(self, paths: Iterable[str]) -> Dict[str, PhotoAttribution]:
        """Resolve many paths with batched registry reads."""
        path_list = [p for p in paths if p]
        if not path_list:
            return {}

        # Registry lookups always use the absolute form of a path.
        abs_paths = [self._absolute(_normalize(p)) for p in path_list]
        items_by_path = self._items_by_local_path(abs_paths)
        sources_by_id = self._source_by_id()
        local_roots = self._local_roots()
        media_root = _normalize(str(self._media_root)) if self._media_root else None

        out: Dict[str, PhotoAttribution] = {}
        for raw_path in path_list:
            norm = _normalize(raw_path)
            resolved = self._resolve_one(
                raw_path,
                norm,
                items_by_path,
                sources_by_id,
                local_roots,
                media_root,
            )
            out[raw_path] = resolved
        return out

    def resolve(self, path: str) -> PhotoAttribution:
        if not path:
            return _unattributed()
        return self.resolve_many([path])[path]

    def _resolve_one(
        self,
        raw_path: str,
        norm_path: str,
        items_by_path: Dict[str, Any],
        sources_by_id: Dict[str, Any],
        local_roots: List[Tuple[str, Any]],
        media_root: Optional[str],
    ) -> PhotoAttribution:
        # The catalog may hold either an absolute or a base-relative path for
        # the same file; attribution is always resolved against the absolute
        # form.
        abs_path = self._absolute(norm_path)

        # 1. Exact registry item (synced cloud files record their local copy).
        item = items_by_path.get(abs_path)
        if item is None:
            item = items_by_path.get(norm_path)
        if item is None:
            real = _normalize(_realpath(abs_path))
            item = items_by_path.get(real)
        if item is not None:
            source = sources_by_id.get(getattr(item, "source_id", ""))
            if source is not None:
                return PhotoAttribution(
                    origin="source",
                    kind=kind_for_source_type(getattr(source, "type", None)),
                    match="source_item",
                    source_id=getattr(source, "id", None),
                    source_type=getattr(source, "type", None),
                    source_name=getattr(source, "name", None),
                    source_status=getattr(source, "status", None),
                    last_sync_at=getattr(source, "last_sync_at", None),
                    item_status=getattr(item, "status", None),
                    remote_id=getattr(item, "remote_id", None),
                    resolved_path=abs_path,
                )
            # Item without a live source row (source deleted): fall through to
            # the remaining rules rather than inventing a source.

        # 2. Registered local-folder root (longest match wins).
        for root, source in local_roots:
            if _is_under(abs_path, root):
                return PhotoAttribution(
                    origin="source",
                    kind="local",
                    match="source_root",
                    source_id=getattr(source, "id", None),
                    source_type=getattr(source, "type", None),
                    source_name=getattr(source, "name", None),
                    source_status=getattr(source, "status", None),
                    last_sync_at=getattr(source, "last_sync_at", None),
                    resolved_path=abs_path,
                )

        # 3. The app's own media root.
        if media_root and _is_under(abs_path, media_root):
            return PhotoAttribution(
                origin="media_root",
                kind="local",
                match="media_root",
                source_type=MEDIA_ROOT_SOURCE_TYPE,
                source_name="Local library",
                resolved_path=abs_path,
            )

        # 4. Honest "we do not know".
        return PhotoAttribution(
            origin="unattributed",
            kind="unknown",
            match="none",
            resolved_path=abs_path,
        )


def _unattributed() -> PhotoAttribution:
    return PhotoAttribution(
        origin="unattributed",
        kind="unknown",
        match="none",
    )


def _chunks(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def resolver_for_state(state: Any) -> AttributionResolver:
    """Build a resolver from the running app state."""
    from server.config import settings  # local import keeps this module dependency-free

    return AttributionResolver(
        source_store=getattr(state, "source_store", None),
        source_item_store=getattr(state, "source_item_store", None),
        media_root=settings.MEDIA_DIR,
        base_dir=settings.BASE_DIR,
    )


def resolve_item_attributions(
    items: Sequence[Dict[str, Any]],
    resolver: AttributionResolver,
) -> Dict[str, PhotoAttribution]:
    """Resolve attribution for a list of result items (batched)."""
    paths = [str(i.get("path")) for i in items if i.get("path")]
    return resolver.resolve_many(paths)


def filter_by_source(
    items: Sequence[Dict[str, Any]],
    attributions: Dict[str, PhotoAttribution],
    source_filter: str,
) -> List[Dict[str, Any]]:
    """Registry-derived source filter (replaces the old path-regex filter)."""
    if not source_filter or source_filter == "all":
        return list(items)
    kept: List[Dict[str, Any]] = []
    for item in items:
        path = str(item.get("path") or "")
        attribution = attributions.get(path) or _unattributed()
        if matches_kind(attribution, source_filter):
            kept.append(item)
    return kept


def attach_attribution(
    items: Sequence[Dict[str, Any]],
    attributions: Dict[str, PhotoAttribution],
    resolver: Optional[AttributionResolver] = None,
) -> List[Dict[str, Any]]:
    """Add an `attribution` record to each item (in place) and return the list.

    Paths that were not part of the earlier batch (e.g. results merged in
    after filtering) are resolved on demand, so no item is ever silently
    labelled "unattributed" just because it arrived late.
    """
    missing = [str(i.get("path")) for i in items if i.get("path") and str(i.get("path")) not in attributions]
    if missing and resolver is not None:
        attributions.update(resolver.resolve_many(missing))
    for item in items:
        path = str(item.get("path") or "")
        attribution = attributions.get(path) or _unattributed()
        item["attribution"] = attribution.to_dict()
    return list(items)


def matches_kind(attribution: PhotoAttribution, source_filter: str) -> bool:
    """Registry-derived filter predicate.

    `hybrid` is retained as a compatibility alias for `unknown`; it always
    meant "the path matched neither the local nor the cloud rule", i.e.
    unclassifiable.
    """
    if not source_filter or source_filter == "all":
        return True
    if source_filter == "hybrid":
        return attribution.kind == "unknown"
    return attribution.kind == source_filter

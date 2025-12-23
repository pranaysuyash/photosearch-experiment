"""Compatibility shim for tests and legacy imports.

The implementation lives in `server.multi_tag_filter_db`.
"""

from typing import List, Optional, cast

from server.multi_tag_filter_db import MultiTagFilterDB as _ServerMultiTagFilterDB


class PhotoPath(str):
    """A string path that also supports legacy dict-style access.

    Some tests treat results as strings (e.g. `"/paris/" in photo`), while others
    treat them as dicts (e.g. `photo["path"]`). This small adapter satisfies both.
    """

    def __getitem__(self, key):  # type: ignore[override]
        if key == "path":
            return str(self)
        return super().__getitem__(key)


class MultiTagFilterDB(_ServerMultiTagFilterDB):
    """Test/legacy wrapper around the server implementation.

    The server implementation returns `List[str]` for `get_photos_by_tags`.
    Some legacy tests expect `List[Dict[str, str]]` with a `path` key.
    """

    def get_photos_by_tags(
        self,
        tags: List[str],
        operator: str = "OR",
        exclude_tags: Optional[List[str]] = None,
    ) -> List[str]:
        paths = super().get_photos_by_tags(
            tags=tags,
            operator=operator,  # type: ignore[arg-type]
            exclude_tags=exclude_tags,
        )
        # Return type is List[str] for compatibility with the server implementation,
        # but we use PhotoPath (a str subtype) to satisfy mixed legacy expectations.
        return cast(List[str], [PhotoPath(p) for p in paths])


__all__ = ["MultiTagFilterDB"]

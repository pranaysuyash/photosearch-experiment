"""
Content provenance — honest, detection-only inspection of a media file.

Content provenance is a *different* entity from source attribution (see
`docs/decisions/2026-10-21-photo-source-attribution.md` §2.1):

* source attribution  = which library is this file from  → the source registry
* content provenance  = does the file carry a signed authorship manifest

This module answers the second question by looking for manifest *markers* in
the file. It performs **no cryptographic validation**, resolves no trust list,
and extracts no claims. It therefore reports:

* `present`   — a manifest marker was found (a real observation)
* `verified`  — always `false`, with a `note` saying why

Anything stronger would be a fabricated guarantee. Verification belongs to a
future SDK-backed capability; until one exists, the honest answer is "a
manifest appears to be present, and nothing has been verified".
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

# Bytes read from the head and tail of a file when looking for markers.
# C2PA manifests sit in APP segments (JPEG) or ISO-BMFF boxes near the start
# of a file; legacy XMP provenance sits in APP1. Reading head+tail keeps the
# cost bounded for large media while still catching the common layouts.
_SCAN_CHUNK_BYTES = 256 * 1024

# The C2PA box UUID (ISO 9838-8 / C2PA spec) as it appears in file bytes.
_C2PA_UUID = b"\xd8\xfe\xc3\xd6\x1b\x0e\x48\x3c\x92\x97\x58\x28\x87\x7e\xc4\x81"

# Markers we can identify without a full parser.
_MARKERS: Tuple[Tuple[str, bytes], ...] = (
    ("c2pa_uuid_box", _C2PA_UUID),
    ("jumb_box", b"jumb"),
    ("c2pa_assertion", b"c2pa.assertion"),
    ("c2pa_claim", b"c2pa.claim"),
    ("c2pa_claim_generator", b"c2pa.claim_generator"),
    ("xmp_packet", b"http://ns.adobe.com/xap/1.0/"),
    ("xmp_provenance", b"http://ns.adobe.com/xsd/1.1/"),
)

_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".heif", ".avif"})

# Files above this size are not scanned at all unless explicitly forced; the
# marker scan is a UI nicety, not an index.
_DEFAULT_MAX_BYTES = 512 * 1024 * 1024


def _is_scannable(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext in _IMAGE_EXTENSIONS:
        return True
    # ISO-BMFF containers (mp4/mov) can carry C2PA boxes too.
    return ext in {".mp4", ".mov", ".m4v"}


def _read_edges(path: str, chunk: int) -> bytes:
    """Read the head and (if larger) the tail of a file."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            head = fh.read(chunk)
            if size <= chunk * 2:
                return head
            fh.seek(max(0, size - chunk))
            return head + fh.read(chunk)
    except OSError:
        return b""


def _find_markers(blob: bytes) -> List[str]:
    found: List[str] = []
    for name, needle in _MARKERS:
        if needle in blob:
            found.append(name)
    return found


def detect_content_provenance(
    path: str,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> Dict[str, Any]:
    """Inspect `path` for content-provenance markers.

    Returns a dict that is always safe to show: it reports observation and
    explicitly states what was *not* done.
    """
    base: Dict[str, Any] = {
        "present": None,
        "markers": [],
        "verified": False,
        "verifier": None,
        "scan_scope": None,
        "note": "",
    }

    if not path:
        base["note"] = "No file path supplied."
        return base

    if not _is_scannable(path):
        base["note"] = "Not a scannable media container."
        return base

    try:
        size = os.path.getsize(path)
    except OSError as exc:
        base["note"] = f"File not readable: {exc.strerror or 'unknown error'}."
        return base

    if size > max_bytes:
        base["note"] = f"File is larger than the scan limit ({max_bytes} bytes); not inspected."
        return base

    blob = _read_edges(path, _SCAN_CHUNK_BYTES)
    if not blob:
        base["note"] = "File could not be read."
        return base

    markers = _find_markers(blob)
    base["markers"] = markers
    base["present"] = bool(markers)
    base["scan_scope"] = "head_and_tail"
    base["note"] = (
        "Manifest markers detected. No signature chain was validated and no "
        "verifier ran, so this is not a verification result."
        if markers
        else "No content-provenance markers found in the scanned region. This is "
        "not proof that no manifest exists (markers can sit mid-file)."
    )
    return base


def attach_content_provenance(
    attribution_dict: Dict[str, Any],
    path: str,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> Dict[str, Any]:
    """Return a copy of `attribution_dict` with the `content` block added."""
    enriched = dict(attribution_dict)
    enriched["content"] = detect_content_provenance(path, max_bytes=max_bytes)
    return enriched

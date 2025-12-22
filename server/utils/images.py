def _negotiate_image_format(format_param: str | None, accept_header: str | None) -> str:
    """Choose output image format based on explicit param or Accept header."""
    fmt = (format_param or "").strip().lower()
    if fmt in {"jpg", "jpeg"}:
        return "JPEG"
    if fmt == "webp":
        return "WEBP"

    if accept_header:
        h = accept_header.lower()
        if "image/webp" in h:
            return "WEBP"
    return "JPEG"

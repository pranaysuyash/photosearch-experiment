"""Outbound URL guard — shared SSRF protection for user/model-configured URLs.

One canonical implementation for "may we call this URL?": https only, no
embedded credentials, and the host must resolve to a public address unless
explicitly opted in. Used by S3 source flows (opt-in allowed for LAN MinIO)
and model downloads (no opt-in — registry URLs are https).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

__all__ = ["PublicUrlRequired", "assert_public_http_url"]


class PublicUrlRequired(ValueError):
    """Raised when a URL must resolve to a public https address and does not."""


def assert_public_http_url(url: str, *, allow_private: bool = False) -> None:
    """Assert the URL is callable under the outbound-request policy.

    - scheme must be https (http is never allowed for outbound guards)
    - no embedded credentials
    - the host must resolve; resolved addresses must be public unless
      ``allow_private`` is set (loopback/private/link-local are then permitted
      for explicit LAN/dev configurations)
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise PublicUrlRequired(f"URL scheme must be https, got {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise PublicUrlRequired("URL must not embed credentials; use keys")
    if not parsed.hostname:
        raise PublicUrlRequired("URL must include a hostname")
    if allow_private:
        return
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise PublicUrlRequired(f"Cannot resolve host {parsed.hostname!r}: {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise PublicUrlRequired(
                f"URL resolves to a non-public address ({ip}); "
                "enable the explicit private-endpoint opt-in if this is intended"
            )

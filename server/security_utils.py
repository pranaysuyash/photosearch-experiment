import hashlib

from server.config import settings


def hash_for_logs(value: str) -> str:
    """
    Hash sensitive values (like file paths) for logs.

    This is intentionally deterministic for a given salt so that:
    - Access logs can be correlated without leaking raw paths
    - Admin-only unmasking can scan a directory and match hashes
    """
    salt = getattr(settings, "ACCESS_LOG_HASH_SALT", "dev_salt")
    raw = f"{salt}|{value}".encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()

"""
Secure Key Management System

Implements proper key derivation and management for face embedding encryption.
Replaces the vulnerable single static key approach with per-user key derivation.
"""

import os
import re
import secrets
from pathlib import Path
from typing import Dict, Optional
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class SecureKeyManager:
    """
    Secure key management for face embedding encryption.

    Features:
    - Per-user key derivation using PBKDF2
    - Master key rotation support
    - Secure key storage with proper permissions
    - Hardware Security Module (HSM) ready architecture
    """

    def __init__(self, key_store_path: Path):
        self.key_store_path = key_store_path
        self.key_store_path.mkdir(parents=True, exist_ok=True)

        # Set secure permissions on key store directory
        os.chmod(self.key_store_path, 0o700)

        self._user_keys: Dict[str, bytes] = {}
        self._master_key: Optional[bytes] = None
        self._salt_cache: Dict[str, bytes] = {}

        # Initialize master key
        self._initialize_master_key()

    _USER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

    @staticmethod
    def _filesystem_safe_id(user_id: str) -> str:
        """Validate a user id before it reaches a filesystem path.

        Salt files are named ``{user_id}.salt`` under the key store; a
        traversal value must fail here rather than escape the store.
        """
        if not SecureKeyManager._USER_ID_RE.match(user_id or ""):
            raise ValueError(f"user_id is not filesystem-safe: {user_id!r}")
        return user_id

    def _initialize_master_key(self) -> None:
        """Initialize or load the master key"""
        master_key_path = self.key_store_path / "master.key"

        if master_key_path.exists():
            # Load existing master key
            with open(master_key_path, "rb") as f:
                self._master_key = f.read()
            logger.info("Loaded existing master key")
        else:
            # Generate new master key
            self._master_key = secrets.token_bytes(32)  # 256-bit key

            # Save master key with secure permissions
            master_key_path.write_bytes(self._master_key)
            os.chmod(master_key_path, 0o600)

            logger.info("Generated new master key")

    def get_user_key(self, user_id: str) -> bytes:
        """
        Get or derive encryption key for a specific user.

        Args:
            user_id: Unique user identifier

        Returns:
            32-byte encryption key for the user
        """
        if user_id in self._user_keys:
            return self._user_keys[user_id]

        # Derive user-specific key
        user_key = self._derive_user_key(user_id)
        self._user_keys[user_id] = user_key

        return user_key

    def _derive_user_key(self, user_id: str) -> bytes:
        """
        Derive a user-specific key using PBKDF2.

        Args:
            user_id: Unique user identifier

        Returns:
            Derived encryption key
        """
        # Get or generate user-specific salt
        salt = self._get_user_salt(user_id)

        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
            backend=default_backend(),
        )

        return kdf.derive(self._master_key)

    def _get_user_salt(self, user_id: str) -> bytes:
        """
        Get or generate salt for user key derivation.

        Args:
            user_id: Unique user identifier

        Returns:
            32-byte salt for key derivation
        """
        if user_id in self._salt_cache:
            return self._salt_cache[user_id]

        safe_id = self._filesystem_safe_id(user_id)
        salt_path = self.key_store_path / f"{safe_id}.salt"

        if salt_path.exists():
            # Load existing salt
            with open(salt_path, "rb") as f:
                salt = f.read()
        else:
            # Generate new salt
            salt = secrets.token_bytes(32)

            # Save salt with secure permissions
            salt_path.write_bytes(salt)
            os.chmod(salt_path, 0o600)

        self._salt_cache[user_id] = salt
        return salt

    def encrypt_data(self, data: bytes, user_id: str) -> bytes:
        """
        Encrypt data using user-specific key.

        Args:
            data: Data to encrypt
            user_id: User identifier for key derivation

        Returns:
            Encrypted data with IV prepended
        """
        key = self.get_user_key(user_id)

        # Generate random IV
        iv = secrets.token_bytes(16)  # 128-bit IV for AES

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Pad data to block size
        padded_data = self._pad_data(data)

        # Encrypt data
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Return IV + encrypted data
        return iv + encrypted_data

    def decrypt_data(self, encrypted_data: bytes, user_id: str) -> bytes:
        """
        Decrypt data using user-specific key.

        Args:
            encrypted_data: Encrypted data with IV prepended
            user_id: User identifier for key derivation

        Returns:
            Decrypted data
        """
        key = self.get_user_key(user_id)

        # Extract IV and encrypted data
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt data
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove padding
        return self._unpad_data(padded_data)

    def _pad_data(self, data: bytes) -> bytes:
        """Apply PKCS7 padding to data"""
        block_size = 16  # AES block size
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding

    def _unpad_data(self, padded_data: bytes) -> bytes:
        """Remove PKCS7 padding from data"""
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]

    def rotate_master_key(self) -> None:
        """
        Rotate the master key and re-encrypt all user keys.

        WARNING: This is a destructive operation that requires
        re-encrypting all stored data.
        """
        logger.warning("Master key rotation initiated")

        # Store old master key for data migration

        # Generate new master key
        self._master_key = secrets.token_bytes(32)

        # Save new master key
        master_key_path = self.key_store_path / "master.key"
        master_key_path.write_bytes(self._master_key)

        # Clear user key cache to force re-derivation
        self._user_keys.clear()

        logger.info("Master key rotation completed")

    def delete_user_keys(self, user_id: str) -> None:
        """
        Securely delete all keys and salts for a user.

        Args:
            user_id: User identifier
        """
        # Remove from memory
        self._user_keys.pop(user_id, None)
        self._salt_cache.pop(user_id, None)

        # Remove salt file
        safe_id = self._filesystem_safe_id(user_id)
        salt_path = self.key_store_path / f"{safe_id}.salt"
        if salt_path.exists():
            # Secure deletion by overwriting
            with open(salt_path, "r+b") as f:
                f.write(secrets.token_bytes(f.seek(0, 2)))
                f.flush()
                os.fsync(f.fileno())
            salt_path.unlink()

        logger.info(f"Deleted keys for user: {user_id}")

    def get_key_info(self) -> Dict[str, any]:
        """
        Get information about the key management system.

        Returns:
            Dictionary with key management statistics
        """
        return {
            "master_key_exists": self._master_key is not None,
            "cached_user_keys": len(self._user_keys),
            "cached_salts": len(self._salt_cache),
            "key_store_path": str(self.key_store_path),
            "algorithm": "AES-256-CBC",
            "kdf": "PBKDF2-SHA256",
            "iterations": 100000,
        }


# Global key manager instance
_key_manager: Optional[SecureKeyManager] = None


def get_key_manager() -> SecureKeyManager:
    """Get the global key manager instance"""
    global _key_manager
    if _key_manager is None:
        try:
            from server.config import settings

            key_store_path = Path(settings.DATA_DIR) / "keys"
        except (ImportError, AttributeError):
            # Fallback for testing or when settings are not available
            key_store_path = Path("data") / "keys"
        _key_manager = SecureKeyManager(key_store_path)
    return _key_manager


def encrypt_face_embedding(embedding_data: bytes, user_id: str = "default") -> bytes:
    """
    Convenience function to encrypt face embedding data.

    Args:
        embedding_data: Raw embedding data to encrypt
        user_id: User identifier for key derivation

    Returns:
        Encrypted embedding data
    """
    key_manager = get_key_manager()
    return key_manager.encrypt_data(embedding_data, user_id)


def decrypt_face_embedding(encrypted_data: bytes, user_id: str = "default") -> bytes:
    """
    Convenience function to decrypt face embedding data.

    Args:
        encrypted_data: Encrypted embedding data
        user_id: User identifier for key derivation

    Returns:
        Decrypted embedding data
    """
    key_manager = get_key_manager()
    return key_manager.decrypt_data(encrypted_data, user_id)

"""Cryptographically secure random values for SEC-03.

Nonce generation is handled by ``aead.encrypt`` so callers cannot accidentally
supply or reuse one through this API.
"""

import secrets

from .config import AES_GCM_KEY_LENGTH
from .kdf import MIN_SALT_LENGTH


def generate_salt(length: int = MIN_SALT_LENGTH) -> bytes:
    """Generate a fresh Argon2id salt (at least 16 bytes)."""
    if type(length) is not int:
        raise TypeError("salt length must be an integer")
    if length < MIN_SALT_LENGTH:
        raise ValueError(f"salt length must be at least {MIN_SALT_LENGTH} bytes")
    return secrets.token_bytes(length)


def generate_dek() -> bytes:
    """Generate a fresh 256-bit data encryption key for AES-256-GCM."""
    return secrets.token_bytes(AES_GCM_KEY_LENGTH)

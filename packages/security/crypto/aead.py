"""AES-256-GCM authenticated encryption primitives for SEC-03.

The caller owns key management and AAD serialization. Ciphertext returned by
``encrypt`` includes the 16-byte authentication tag appended by AESGCM.
"""

import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from .exceptions import DecryptionError
from .config import AES_GCM_KEY_LENGTH, AES_GCM_NONCE_LENGTH, AES_GCM_TAG_LENGTH


def _validate_key(key: bytes) -> None:
    if not isinstance(key, bytes):
        raise TypeError("key must be bytes")
    if len(key) != AES_GCM_KEY_LENGTH:
        raise ValueError("AES-256-GCM requires a 32-byte key")


def _validate_aad(aad: bytes | None) -> None:
    if aad is not None and not isinstance(aad, bytes):
        raise TypeError("aad must be bytes or None")


def encrypt(
    key: bytes,
    plaintext: bytes,
    aad: bytes | None = None,
) -> tuple[bytes, bytes]:
    """Encrypt plaintext and return ``(nonce, ciphertext_with_tag)``.

    A fresh random 96-bit nonce is generated for every invocation. The caller
    must not reuse the same (key, nonce) pair, including across processes.
    """
    _validate_key(key)
    if not isinstance(plaintext, bytes):
        raise TypeError("plaintext must be bytes")
    _validate_aad(aad)

    nonce = secrets.token_bytes(AES_GCM_NONCE_LENGTH)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return nonce, ciphertext


def decrypt(
    key: bytes,
    nonce: bytes,
    ciphertext: bytes,
    aad: bytes | None = None,
) -> bytes:
    """Decrypt authenticated ciphertext or raise DecryptionError."""

    _validate_key(key)

    if not isinstance(nonce, bytes):
        raise TypeError("nonce must be bytes")

    if len(nonce) != AES_GCM_NONCE_LENGTH:
        raise ValueError("AES-256-GCM requires a 12-byte nonce")

    if not isinstance(ciphertext, bytes):
        raise TypeError("ciphertext must be bytes")

    if len(ciphertext) < AES_GCM_TAG_LENGTH:
        raise ValueError("ciphertext is shorter than the authentication tag")

    _validate_aad(aad)

    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise DecryptionError(
            "Authenticated decryption failed"
        ) from exc

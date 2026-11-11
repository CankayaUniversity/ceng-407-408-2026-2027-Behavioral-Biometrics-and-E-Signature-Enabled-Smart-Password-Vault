"""Unit tests for SEC-03 AES-256-GCM authenticated encryption."""

import pytest

from packages.security.crypto.aead import decrypt, encrypt
from packages.security.crypto.config import (
    AES_GCM_KEY_LENGTH,
    AES_GCM_NONCE_LENGTH,
    AES_GCM_TAG_LENGTH,
)
from packages.security.crypto.exceptions import DecryptionError


@pytest.fixture
def key() -> bytes:
    """Deterministic, non-secret key for tests only."""
    return bytes(range(AES_GCM_KEY_LENGTH))


@pytest.mark.parametrize("plaintext", [b"", b"example credential", b"\x00\xff\x10"])
def test_round_trip(key: bytes, plaintext: bytes) -> None:
    aad = b"vault-id:record-id:version"
    nonce, ciphertext = encrypt(key, plaintext, aad)
    assert len(nonce) == AES_GCM_NONCE_LENGTH
    assert len(ciphertext) == len(plaintext) + AES_GCM_TAG_LENGTH
    assert decrypt(key, nonce, ciphertext, aad) == plaintext


def test_round_trip_without_aad(key: bytes) -> None:
    nonce, ciphertext = encrypt(key, b"payload")
    assert decrypt(key, nonce, ciphertext) == b"payload"


def test_fresh_nonce_per_encryption(key: bytes) -> None:
    nonce_a, _ = encrypt(key, b"same")
    nonce_b, _ = encrypt(key, b"same")
    assert nonce_a != nonce_b


def test_tampered_ciphertext_rejected(key: bytes) -> None:
    nonce, ciphertext = encrypt(key, b"secret", b"context")
    tampered = bytearray(ciphertext)
    tampered[0] ^= 1
    with pytest.raises(DecryptionError):
        decrypt(key, nonce, bytes(tampered), b"context")


def test_wrong_aad_rejected(key: bytes) -> None:
    nonce, ciphertext = encrypt(key, b"secret", b"original")
    with pytest.raises(DecryptionError):
        decrypt(key, nonce, ciphertext, b"modified")


def test_wrong_key_rejected(key: bytes) -> None:
    nonce, ciphertext = encrypt(key, b"secret")
    other_key = b"x" * AES_GCM_KEY_LENGTH
    with pytest.raises(DecryptionError):
        decrypt(other_key, nonce, ciphertext)


@pytest.mark.parametrize("bad_key", [b"short", "not-bytes", None])
def test_invalid_key_rejected(bad_key: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        encrypt(bad_key, b"data")  # type: ignore[arg-type]


def test_short_nonce_rejected(key: bytes) -> None:
    with pytest.raises(ValueError):
        decrypt(key, b"short", b"x" * AES_GCM_TAG_LENGTH)


def test_short_ciphertext_rejected(key: bytes) -> None:
    with pytest.raises(ValueError):
        decrypt(key, b"n" * AES_GCM_NONCE_LENGTH, b"too-short")


def test_invalid_aad_rejected(key: bytes) -> None:
    with pytest.raises(TypeError):
        encrypt(key, b"data", "not-bytes")  # type: ignore[arg-type]

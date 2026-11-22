"""VLT-03 record encryption helpers; no storage or session policy.

Record AAD encoding is a proposed v1 contract and requires team approval.
"""

import base64
import binascii
import json
from uuid import UUID

from contracts.vault_service import CredentialCreate, CredentialItem, CredentialUpdate
from packages.security.crypto.aead import decrypt, encrypt
from packages.security.crypto.config import AES_GCM_KEY_LENGTH

_RECORD_VERSION = 1
_FIELDS = frozenset({"title", "username", "password", "url", "notes"})
_RECORD_FIELDS = frozenset({"record_id", "version", "nonce", "ciphertext"})


class CredentialFormatError(ValueError):
    """Encrypted record structure or decrypted payload is invalid."""


def _aad(vault_id: UUID, record_id: UUID) -> bytes:
    context = {
        "vault_id": str(vault_id),
        "record_id": str(record_id),
        "version": _RECORD_VERSION,
    }
    return json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode(value: object) -> bytes:
    if not isinstance(value, str):
        raise CredentialFormatError("Invalid encrypted record encoding")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise CredentialFormatError("Invalid encrypted record encoding") from exc


def encrypt_credential(
    dek: bytes,
    vault_id: UUID,
    record_id: UUID,
    data: CredentialCreate | CredentialUpdate,
) -> dict:
    """Return only v1 encrypted record metadata, not plaintext fields."""
    if not isinstance(dek, bytes) or len(dek) != AES_GCM_KEY_LENGTH:
        raise ValueError("Expected a 32-byte DEK")
    if not isinstance(vault_id, UUID) or not isinstance(record_id, UUID):
        raise TypeError("Vault and record IDs must be UUIDs")
    if not isinstance(data, (CredentialCreate, CredentialUpdate)):
        raise TypeError("Expected a credential DTO")

    fields = {name: getattr(data, name) for name in _FIELDS}
    if any(not isinstance(value, str) for value in fields.values()):
        raise ValueError("Credential fields must be strings")
    if not fields["title"].strip():
        raise ValueError("Credential title must not be empty")

    plaintext = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    nonce, ciphertext = encrypt(dek, plaintext, _aad(vault_id, record_id))
    return {
        "record_id": str(record_id),
        "version": _RECORD_VERSION,
        "nonce": _encode(nonce),
        "ciphertext": _encode(ciphertext),
    }


def decrypt_credential(dek: bytes, vault_id: UUID, record: dict) -> CredentialItem:
    """Authenticate record context before decoding sensitive fields.

    Cryptographic authentication failures propagate the SEC-03 DecryptionError.
    """
    if not isinstance(dek, bytes) or len(dek) != AES_GCM_KEY_LENGTH:
        raise ValueError("Expected a 32-byte DEK")
    if not isinstance(vault_id, UUID):
        raise TypeError("Vault ID must be a UUID")
    if not isinstance(record, dict) or set(record) != _RECORD_FIELDS:
        raise CredentialFormatError("Invalid encrypted record structure")
    if type(record["version"]) is not int or record["version"] != _RECORD_VERSION:
        raise CredentialFormatError("Unsupported encrypted record version")
    try:
        record_id = UUID(record["record_id"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise CredentialFormatError("Invalid record ID") from exc
    nonce = _decode(record["nonce"])
    ciphertext = _decode(record["ciphertext"])
    plaintext = decrypt(dek, nonce, ciphertext, _aad(vault_id, record_id))
    try:
        payload = json.loads(plaintext.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise CredentialFormatError("Invalid credential payload") from exc
    if not isinstance(payload, dict) or set(payload) != _FIELDS:
        raise CredentialFormatError("Invalid credential payload fields")
    if any(not isinstance(value, str) for value in payload.values()) or not payload["title"].strip():
        raise CredentialFormatError("Invalid credential payload values")
    return CredentialItem(record_id=record_id, **payload)

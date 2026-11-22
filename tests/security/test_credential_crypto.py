"""VLT-03 standalone record encryption tests."""

import base64
from uuid import uuid4

import pytest

from contracts.vault_service import CredentialCreate, CredentialUpdate
from packages.security.crypto.exceptions import DecryptionError
from packages.security.vault.credential import (
    CredentialFormatError,
    decrypt_credential,
    encrypt_credential,
)


@pytest.fixture
def context():
    return b"k" * 32, uuid4(), uuid4()


def test_round_trip_and_no_plaintext(context):
    dek, vault_id, record_id = context
    data = CredentialCreate(title="Example", username="alice", password="TEST_SECRET", notes="private")
    record = encrypt_credential(dek, vault_id, record_id, data)
    assert set(record) == {"record_id", "version", "nonce", "ciphertext"}
    assert "TEST_SECRET" not in str(record)
    assert "alice" not in str(record)
    item = decrypt_credential(dek, vault_id, record)
    assert item.record_id == record_id
    assert item.password == "TEST_SECRET"
    assert item.notes == "private"


def test_update_uses_new_nonce(context):
    dek, vault_id, record_id = context
    data = CredentialUpdate(title="Example", username="alice", password="temporary")
    first = encrypt_credential(dek, vault_id, record_id, data)
    second = encrypt_credential(dek, vault_id, record_id, data)
    assert first["nonce"] != second["nonce"]


def test_ciphertext_tampering_rejected(context):
    dek, vault_id, record_id = context
    record = encrypt_credential(dek, vault_id, record_id, CredentialCreate("Example", "alice", "secret"))
    value = bytearray(base64.b64decode(record["ciphertext"]))
    value[-1] ^= 1
    record["ciphertext"] = base64.b64encode(value).decode("ascii")
    with pytest.raises(DecryptionError):
        decrypt_credential(dek, vault_id, record)


def test_record_id_swap_rejected(context):
    dek, vault_id, record_id = context
    record = encrypt_credential(dek, vault_id, record_id, CredentialCreate("Example", "alice", "secret"))
    record["record_id"] = str(uuid4())
    with pytest.raises(DecryptionError):
        decrypt_credential(dek, vault_id, record)


def test_other_vault_rejected(context):
    dek, vault_id, record_id = context
    record = encrypt_credential(dek, vault_id, record_id, CredentialCreate("Example", "alice", "secret"))
    with pytest.raises(DecryptionError):
        decrypt_credential(dek, uuid4(), record)


def test_wrong_key_rejected(context):
    dek, vault_id, record_id = context
    record = encrypt_credential(dek, vault_id, record_id, CredentialCreate("Example", "alice", "secret"))
    with pytest.raises(DecryptionError):
        decrypt_credential(b"z" * 32, vault_id, record)


def test_invalid_structure_rejected(context):
    dek, vault_id, record_id = context
    record = encrypt_credential(dek, vault_id, record_id, CredentialCreate("Example", "alice", "secret"))
    record["extra"] = "unexpected"
    with pytest.raises(CredentialFormatError):
        decrypt_credential(dek, vault_id, record)


def test_invalid_credential_title(context):
    dek, vault_id, record_id = context
    with pytest.raises(ValueError):
        encrypt_credential(dek, vault_id, record_id, CredentialCreate(" ", "alice", "secret"))

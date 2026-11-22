"""SEC-05: integrated vault encryption, persistence and integrity checks."""

import base64
import json
from pathlib import Path

import pytest

from contracts.vault_service import CredentialCreate, CredentialUpdate
from packages.security.crypto.config import Argon2Config
from packages.security.crypto.exceptions import DecryptionError
from packages.security.vault.credential import CredentialFormatError
from packages.security.vault.service import VaultLockedError, VaultService
from packages.security.vault.storage import JsonVaultStorage

MASTER = "sec05-test-only-master-password"
WRONG = "sec05-wrong-password"
SECRET = "sec05-private-credential-password"


def _service(path: Path) -> VaultService:
    return VaultService(
        JsonVaultStorage(path),
        Argon2Config(memory_cost_kib=8192, time_cost=1, parallelism=1),
    )


def _rewrite(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")
    if __import__("os").name != "nt":
        path.chmod(0o600)


def test_create_and_reopen_preserves_secrecy(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    creator = _service(path)
    vault_id = creator.create_vault(MASTER)
    assert not creator.is_unlocked

    raw = path.read_text(encoding="utf-8")
    assert MASTER not in raw
    assert "wrapped_dek" in raw
    assert '"records":[]' in raw or json.loads(raw)["records"] == []

    reopened = _service(path)
    reopened.unlock_vault(MASTER)
    assert reopened.is_unlocked
    assert reopened.list_credentials() == []
    assert json.loads(raw)["vault_id"] == str(vault_id)


def test_wrong_password_cannot_access_persisted_credentials(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    original = _service(path)
    original.create_vault(MASTER)
    original.unlock_vault(MASTER)
    rid = original.add_credential(CredentialCreate("Email", "alice", SECRET))
    original.lock_vault()

    raw = path.read_text(encoding="utf-8")
    assert SECRET not in raw
    assert MASTER not in raw
    assert "alice" not in raw

    reopened = _service(path)
    with pytest.raises(DecryptionError):
        reopened.unlock_vault(WRONG)
    assert not reopened.is_unlocked
    with pytest.raises(VaultLockedError):
        reopened.get_credential(rid)

    reopened.unlock_vault(MASTER)
    assert reopened.get_credential(rid).password == SECRET


@pytest.mark.parametrize("target", ["nonce", "ciphertext"])
def test_modified_record_fails_closed_after_reopen(tmp_path: Path, target: str) -> None:
    path = tmp_path / "vault.json"
    writer = _service(path)
    writer.create_vault(MASTER)
    writer.unlock_vault(MASTER)
    writer.add_credential(CredentialCreate("Email", "alice", SECRET))
    writer.lock_vault()

    stored = json.loads(path.read_text(encoding="utf-8"))
    raw = bytearray(base64.b64decode(stored["records"][0][target]))
    raw[-1] ^= 1
    stored["records"][0][target] = base64.b64encode(raw).decode("ascii")
    _rewrite(path, stored)

    reopened = _service(path)
    reopened.unlock_vault(MASTER)
    with pytest.raises(DecryptionError):
        reopened.list_credentials()
    assert not reopened.is_unlocked
    with pytest.raises(VaultLockedError):
        reopened.list_credentials()


def test_modified_envelope_cannot_unlock(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    _service(path).create_vault(MASTER)
    stored = json.loads(path.read_text(encoding="utf-8"))
    wrapped = bytearray(base64.b64decode(stored["key_envelope"]["wrapped_dek"]))
    wrapped[-1] ^= 1
    stored["key_envelope"]["wrapped_dek"] = base64.b64encode(wrapped).decode("ascii")
    _rewrite(path, stored)

    reopened = _service(path)
    with pytest.raises(DecryptionError):
        reopened.unlock_vault(MASTER)
    assert not reopened.is_unlocked


def test_crud_persists_across_service_instances_without_plaintext(tmp_path: Path) -> None:
    """Verify that credential changes persist across VaultService instances."""
    path = tmp_path / "vault.json"
    creator = _service(path)
    creator.create_vault(MASTER)
    creator.unlock_vault(MASTER)
    first_id = creator.add_credential(CredentialCreate("Mail", "alice", SECRET))
    second_id = creator.add_credential(CredentialCreate("Bank", "bob", "bank-secret-test-only"))
    creator.lock_vault()

    editor = _service(path)
    editor.unlock_vault(MASTER)
    editor.update_credential(first_id, CredentialUpdate("Work", "carol", "updated-secret-test-only"))
    editor.delete_credential(second_id)
    editor.lock_vault()

    reader = _service(path)
    reader.unlock_vault(MASTER)
    assert reader.get_credential(first_id).password == "updated-secret-test-only"
    summaries = reader.list_credentials()
    assert len(summaries) == 1
    assert summaries[0].record_id == first_id
    assert not hasattr(summaries[0], "password")
    with pytest.raises(KeyError):
        reader.get_credential(second_id)

    disk = path.read_text(encoding="utf-8")
    for sensitive in (MASTER, SECRET, "bank-secret-test-only", "updated-secret-test-only", "carol"):
        assert sensitive not in disk


@pytest.mark.parametrize("changed_field", ["record_id", "version"])
def test_record_metadata_tampering_detected_on_reopen(tmp_path: Path, changed_field: str) -> None:
    path = tmp_path / "vault.json"
    writer = _service(path)
    writer.create_vault(MASTER)
    writer.unlock_vault(MASTER)
    writer.add_credential(CredentialCreate("Email", "alice", SECRET))
    writer.lock_vault()

    stored = json.loads(path.read_text(encoding="utf-8"))
    if changed_field == "record_id":
        stored["records"][0][changed_field] = "00000000-0000-0000-0000-000000000001"
    else:
        stored["records"][0][changed_field] = 2
    _rewrite(path, stored)

    reader = _service(path)
    reader.unlock_vault(MASTER)
    with pytest.raises((DecryptionError, CredentialFormatError)):
        reader.list_credentials()
    assert not reader.is_unlocked


def test_integrity_failure_prevents_writes_and_preserves_disk(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    service = _service(path)
    service.create_vault(MASTER)
    service.unlock_vault(MASTER)
    service.add_credential(CredentialCreate("Email", "alice", SECRET))

    stored = json.loads(path.read_text(encoding="utf-8"))
    ciphertext = bytearray(base64.b64decode(stored["records"][0]["ciphertext"]))
    ciphertext[-1] ^= 1
    stored["records"][0]["ciphertext"] = base64.b64encode(ciphertext).decode("ascii")
    _rewrite(path, stored)
    before = path.read_bytes()

    with pytest.raises(DecryptionError):
        service.add_credential(CredentialCreate("Second", "other", "another-secret"))
    assert path.read_bytes() == before
    assert not service.is_unlocked
    with pytest.raises(VaultLockedError):
        service.list_credentials()

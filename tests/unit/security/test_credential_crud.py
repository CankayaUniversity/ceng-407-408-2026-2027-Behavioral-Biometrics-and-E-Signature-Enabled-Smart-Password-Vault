"""VLT-03 end-to-end local encrypted CRUD tests."""
import json
from pathlib import Path

import pytest

from contracts.vault_service import CredentialCreate, CredentialUpdate
from packages.security.crypto.exceptions import DecryptionError
from packages.security.vault.service import VaultLockedError, VaultService, VaultFormatError
from packages.security.vault.storage import JsonVaultStorage


@pytest.fixture
def env(tmp_path: Path):
    path = tmp_path / "vault.json"
    service = VaultService(JsonVaultStorage(path))
    service.create_vault("test-master-password-only")
    service.unlock_vault("test-master-password-only")
    return service, path


def test_crud_and_persist_after_reopening(env):
    service, path = env
    rid = service.add_credential(CredentialCreate("Email", "alice", "test-secret", "https://example.com", "note"))
    assert service.get_credential(rid).password == "test-secret"
    assert len(service.list_credentials()) == 1
    assert not hasattr(service.list_credentials()[0], "password")
    text = path.read_text(encoding="utf-8")
    for secret in ("test-secret", "alice", "Email", "note"):
        assert secret not in text
    service.update_credential(rid, CredentialUpdate("Updated", "bob", "replacement"))
    assert service.get_credential(rid).password == "replacement"
    service.lock_vault()
    reopened = VaultService(JsonVaultStorage(path))
    reopened.unlock_vault("test-master-password-only")
    assert reopened.get_credential(rid).username == "bob"
    reopened.delete_credential(rid)
    assert reopened.list_credentials() == []
    with pytest.raises(KeyError):
        reopened.get_credential(rid)


def test_locked_operations_rejected(env):
    service, _ = env
    service.lock_vault()
    calls = [
        lambda: service.add_credential(CredentialCreate("A", "u", "p")),
        lambda: service.get_credential(__import__('uuid').uuid4()),
        lambda: service.update_credential(__import__('uuid').uuid4(), CredentialUpdate("A", "u", "p")),
        lambda: service.delete_credential(__import__('uuid').uuid4()),
        service.list_credentials,
    ]
    for operation in calls:
        with pytest.raises(VaultLockedError):
            operation()


def test_record_tamper_rejected(env):
    service, path = env
    service.add_credential(CredentialCreate("A", "u", "p"))
    data = json.loads(path.read_text())
    data["records"][0]["record_id"] = "00000000-0000-0000-0000-000000000001"
    path.write_text(json.dumps(data), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(DecryptionError):
        service.list_credentials()


def test_concurrent_snapshot_change_rejected(env):
    service, path = env
    storage = JsonVaultStorage(path)
    snapshot = storage.read()
    service.add_credential(CredentialCreate("A", "u", "p"))
    with pytest.raises(RuntimeError, match="changed"):
        storage.update(snapshot, snapshot)


def test_duplicate_record_ids_rejected(env):
    service, path = env
    service.add_credential(CredentialCreate("A", "u", "p"))
    data = json.loads(path.read_text())
    data["records"].append(dict(data["records"][0]))
    path.write_text(json.dumps(data), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(VaultFormatError):
        service.list_credentials()

"""VLT-03 negative security cases for encrypted credential operations."""

import base64
import json
from uuid import uuid4

import pytest

from contracts.vault_service import CredentialCreate, CredentialUpdate
from packages.security.crypto.exceptions import DecryptionError
from packages.security.vault.credential import CredentialFormatError
from packages.security.vault.service import VaultFormatError, VaultLockedError, VaultService
from packages.security.vault.storage import JsonVaultStorage


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "vault.json"
    service = VaultService(JsonVaultStorage(path))
    service.create_vault("unit-test-master-password")
    service.unlock_vault("unit-test-master-password")
    record_id = service.add_credential(CredentialCreate("Mail", "alice", "sample-secret"))
    return service, path, record_id


def _modify(path, callback):
    data = json.loads(path.read_text(encoding="utf-8"))
    callback(data)
    path.write_text(json.dumps(data), encoding="utf-8")
    path.chmod(0o600)


def test_update_uses_new_nonce_and_ciphertext(setup):
    service, path, record_id = setup
    before = json.loads(path.read_text(encoding="utf-8"))["records"][0]
    service.update_credential(record_id, CredentialUpdate("Mail", "alice", "sample-secret"))
    after = json.loads(path.read_text(encoding="utf-8"))["records"][0]
    assert before["nonce"] != after["nonce"]
    assert before["ciphertext"] != after["ciphertext"]
    assert service.get_credential(record_id).password == "sample-secret"


@pytest.mark.parametrize("field", ["nonce", "ciphertext"])
def test_tampered_record_rejected_and_service_locks(setup, field):
    service, path, _ = setup

    def change(data):
        raw = bytearray(base64.b64decode(data["records"][0][field]))
        raw[0] ^= 1
        data["records"][0][field] = base64.b64encode(raw).decode("ascii")

    _modify(path, change)
    with pytest.raises(DecryptionError):
        service.list_credentials()
    assert not service.is_unlocked
    with pytest.raises(VaultLockedError):
        service.list_credentials()


@pytest.mark.parametrize("change", [
    lambda d: d["records"][0].update({"version": 2}),
    lambda d: d["records"][0].update({"unexpected": "field"}),
    lambda d: d["records"][0].update({"nonce": "invalid?"}),
])
def test_malformed_record_rejected_and_service_locks(setup, change):
    service, path, _ = setup
    _modify(path, change)
    with pytest.raises(CredentialFormatError):
        service.list_credentials()
    assert not service.is_unlocked


def test_failed_mutation_does_not_change_vault_file(setup):
    service, path, _ = setup
    before = path.read_bytes()
    with pytest.raises(KeyError):
        service.update_credential(uuid4(), CredentialUpdate("X", "u", "p"))
    assert path.read_bytes() == before
    with pytest.raises(KeyError):
        service.delete_credential(uuid4())
    assert path.read_bytes() == before


def test_envelope_change_invalidates_unlocked_state(setup):
    service, path, _ = setup
    _modify(path, lambda d: d["key_envelope"].update({"algorithm": "INVALID"}))
    with pytest.raises(VaultFormatError):
        service.list_credentials()
    assert not service.is_unlocked


def test_tampered_record_prevents_other_mutations(setup):
    service, path, _ = setup
    _modify(path, lambda d: d["records"][0].update({"ciphertext": "broken?"}))
    before = path.read_bytes()
    with pytest.raises(CredentialFormatError):
        service.add_credential(CredentialCreate("Second", "bob", "secret"))
    assert path.read_bytes() == before
    assert not service.is_unlocked


@pytest.mark.parametrize("field,raw", [
    ("nonce", b"short"),
    ("ciphertext", b"too-short"),
])
def test_invalid_aead_lengths_lock_vault(setup, field, raw):
    service, path, _ = setup
    _modify(path, lambda d: d["records"][0].update({field: base64.b64encode(raw).decode("ascii")}))
    with pytest.raises(ValueError):
        service.list_credentials()
    assert not service.is_unlocked
    with pytest.raises(VaultLockedError):
        service.list_credentials()


def test_malformed_json_read_locks_vault(setup):
    service, path, _ = setup
    path.write_text("{broken json", encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(json.JSONDecodeError):
        service.list_credentials()
    assert not service.is_unlocked
    with pytest.raises(VaultLockedError):
        service.get_credential(uuid4())


def test_storage_read_failure_locks_vault(setup, monkeypatch):
    service, _, _ = setup
    def fail_read():
        raise OSError("simulated disk error")
    monkeypatch.setattr(service._storage, "read", fail_read)
    with pytest.raises(OSError, match="simulated disk error"):
        service.list_credentials()
    assert not service.is_unlocked

"""VLT-02 tests for encrypted vault creation, persistence and unlocking."""

import base64
import json
from copy import deepcopy
from pathlib import Path

import pytest

from packages.security.crypto.config import Argon2Config
from packages.security.crypto.exceptions import DecryptionError
from packages.security.vault.service import VaultFormatError, VaultKdfLimits, VaultService
from packages.security.vault.storage import JsonVaultStorage


# These are synthetic test-only passwords, never production credentials.
TEST_PASSWORD = "vlt02-example-password-only"
WRONG_PASSWORD = "vlt02-incorrect-password"


@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    return tmp_path / "vault.json"


@pytest.fixture
def storage(vault_path: Path) -> JsonVaultStorage:
    return JsonVaultStorage(vault_path)


@pytest.fixture
def service(storage: JsonVaultStorage) -> VaultService:
    # Valid reduced Argon2id cost to keep the unit tests fast.
    return VaultService(
        storage,
        Argon2Config(memory_cost_kib=8192, time_cost=1, parallelism=1),
    )


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_create_vault_persists_encrypted_envelope(
    service: VaultService, vault_path: Path
) -> None:
    vault_id = service.create_vault(TEST_PASSWORD)
    data = _read(vault_path)

    assert data["format_version"] == 1
    assert data["vault_id"] == str(vault_id)
    assert data["records"] == []
    assert data["kdf"]["algorithm"] == "argon2id"
    assert data["key_envelope"]["algorithm"] == "AES-256-GCM"
    assert len(base64.b64decode(data["key_envelope"]["nonce"])) == 12
    assert len(base64.b64decode(data["key_envelope"]["wrapped_dek"])) == 48
    assert TEST_PASSWORD not in vault_path.read_text(encoding="utf-8")
    assert not service.is_unlocked


def test_unlock_with_correct_password(
    service: VaultService, storage: JsonVaultStorage
) -> None:
    service.create_vault(TEST_PASSWORD)
    fresh_service = VaultService(storage)
    fresh_service.unlock_vault(TEST_PASSWORD)
    assert fresh_service.is_unlocked
    fresh_service.lock_vault()
    assert not fresh_service.is_unlocked


def test_wrong_password_rejected_and_vault_stays_locked(
    service: VaultService,
) -> None:
    service.create_vault(TEST_PASSWORD)
    with pytest.raises(DecryptionError):
        service.unlock_vault(WRONG_PASSWORD)
    assert not service.is_unlocked


def test_failed_unlock_clears_previous_unlocked_state(
    service: VaultService,
) -> None:
    service.create_vault(TEST_PASSWORD)
    service.unlock_vault(TEST_PASSWORD)
    assert service.is_unlocked
    with pytest.raises(DecryptionError):
        service.unlock_vault(WRONG_PASSWORD)
    assert not service.is_unlocked


@pytest.mark.parametrize("field", ["nonce", "wrapped_dek"])
def test_tampered_envelope_rejected(
    service: VaultService, vault_path: Path, field: str
) -> None:
    service.create_vault(TEST_PASSWORD)
    data = _read(vault_path)
    raw = bytearray(base64.b64decode(data["key_envelope"][field]))
    raw[0] ^= 1
    data["key_envelope"][field] = base64.b64encode(raw).decode("ascii")
    _write(vault_path, data)
    with pytest.raises(DecryptionError):
        service.unlock_vault(TEST_PASSWORD)
    assert not service.is_unlocked


@pytest.mark.parametrize("field,value", [
    ("vault_id", "00000000-0000-0000-0000-000000000000"),
    ("format_version", 2),
])
def test_tampered_vault_identity_or_version_rejected(
    service: VaultService, vault_path: Path, field: str, value: object
) -> None:
    service.create_vault(TEST_PASSWORD)
    data = _read(vault_path)
    data[field] = value
    _write(vault_path, data)
    with pytest.raises((DecryptionError, VaultFormatError)):
        service.unlock_vault(TEST_PASSWORD)
    assert not service.is_unlocked


def test_tampered_kdf_metadata_rejected(
    service: VaultService, vault_path: Path
) -> None:
    service.create_vault(TEST_PASSWORD)
    data = _read(vault_path)
    data["kdf"]["parameters"]["time_cost"] += 1
    _write(vault_path, data)
    with pytest.raises(DecryptionError):
        service.unlock_vault(TEST_PASSWORD)
    assert not service.is_unlocked


def test_invalid_base64_metadata_rejected(
    service: VaultService, vault_path: Path
) -> None:
    service.create_vault(TEST_PASSWORD)
    data = _read(vault_path)
    data["kdf"]["salt"] = "not-valid-base64!"
    _write(vault_path, data)
    with pytest.raises(VaultFormatError):
        service.unlock_vault(TEST_PASSWORD)
    assert not service.is_unlocked


def test_existing_vault_is_not_overwritten(
    service: VaultService, vault_path: Path
) -> None:
    service.create_vault(TEST_PASSWORD)
    original = vault_path.read_bytes()
    with pytest.raises(FileExistsError):
        service.create_vault("another-test-password")
    assert vault_path.read_bytes() == original


def test_two_vaults_use_distinct_salts_and_wrapped_keys(tmp_path: Path) -> None:
    config = Argon2Config(memory_cost_kib=8192, time_cost=1, parallelism=1)
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    VaultService(JsonVaultStorage(first_path), config).create_vault(TEST_PASSWORD)
    VaultService(JsonVaultStorage(second_path), config).create_vault(TEST_PASSWORD)
    first, second = _read(first_path), _read(second_path)
    assert first["vault_id"] != second["vault_id"]
    assert first["kdf"]["salt"] != second["kdf"]["salt"]
    assert first["key_envelope"]["wrapped_dek"] != second["key_envelope"]["wrapped_dek"]


def test_malformed_json_rejected(storage: JsonVaultStorage, vault_path: Path) -> None:
    vault_path.write_text("{malformed", encoding="utf-8")
    vault_path.chmod(0o600)
    with pytest.raises(json.JSONDecodeError):
        storage.read()


def test_create_rejects_non_32_byte_kek_config(storage: JsonVaultStorage) -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        VaultService(storage, Argon2Config(key_length=16))


def test_storage_rejects_symlink_on_read(tmp_path: Path) -> None:
    real_file = tmp_path / "private.json"
    real_file.write_text('{"vault_id":"example"}', encoding="utf-8")
    real_file.chmod(0o600)
    link = tmp_path / "linked.json"
    link.symlink_to(real_file)

    with pytest.raises(OSError):
        JsonVaultStorage(link).read()


def test_storage_rejects_world_readable_file(tmp_path: Path) -> None:
    vault_file = tmp_path / "open.json"
    vault_file.write_text('{"vault_id":"example"}', encoding="utf-8")
    vault_file.chmod(0o644)

    with pytest.raises(PermissionError):
        JsonVaultStorage(vault_file).read()


def test_storage_rejects_non_regular_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="regular file"):
        JsonVaultStorage(tmp_path).read()


def test_storage_creates_owner_only_file(tmp_path: Path) -> None:
    import stat

    path = tmp_path / "vault.json"
    JsonVaultStorage(path).create({"format_version": 1})
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize("field,value", [
    ("memory_cost_kib", 524288),
    ("time_cost", 7),
    ("parallelism", 9),
])
def test_untrusted_kdf_cost_exceeding_vault_policy_rejected_before_derivation(
    service: VaultService, vault_path: Path, monkeypatch, field: str, value: int
) -> None:
    service.create_vault(TEST_PASSWORD)
    data = _read(vault_path)
    data["kdf"]["parameters"][field] = value
    _write(vault_path, data)

    def should_not_derive(*args, **kwargs):
        pytest.fail("Argon2 must not run for out-of-policy metadata")

    monkeypatch.setattr("packages.security.vault.service.derive_key", should_not_derive)
    with pytest.raises(VaultFormatError):
        service.unlock_vault(TEST_PASSWORD)
    assert not service.is_unlocked


def test_reject_creation_config_above_policy(storage: JsonVaultStorage) -> None:
    with pytest.raises(VaultFormatError):
        VaultService(storage, Argon2Config(memory_cost_kib=524288))


def test_injectable_kdf_limits_supports_approved_override(storage: JsonVaultStorage) -> None:
    limits = VaultKdfLimits(max_memory_cost_kib=524288)
    vault = VaultService(storage, Argon2Config(memory_cost_kib=524288), kdf_limits=limits)
    assert not vault.is_unlocked


@pytest.mark.parametrize("overrides", [
    {"max_memory_cost_kib": 7},
    {"max_memory_cost_kib": 1048577},
    {"max_time_cost": True},
    {"max_time_cost": 11},
    {"max_parallelism": 0},
    {"max_parallelism": 17},
])
def test_invalid_kdf_limits_rejected(overrides: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="Invalid vault .* policy"):
        VaultKdfLimits(**overrides)


def test_vault_unlocks_at_custom_kdf_limits(storage: JsonVaultStorage) -> None:
    config = Argon2Config(memory_cost_kib=64, time_cost=1, parallelism=1)
    limits = VaultKdfLimits(max_memory_cost_kib=64, max_time_cost=1, max_parallelism=1)
    VaultService(storage, config, kdf_limits=limits).create_vault(TEST_PASSWORD)

    vault = VaultService(storage, config, kdf_limits=limits)
    vault.unlock_vault(TEST_PASSWORD)

    assert vault.is_unlocked

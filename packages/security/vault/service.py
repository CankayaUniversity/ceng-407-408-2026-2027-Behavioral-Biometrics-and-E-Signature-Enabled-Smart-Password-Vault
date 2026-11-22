"""VLT-02 vault creation and unlocking (storage is injected)."""

import base64
import binascii
import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from packages.security.crypto.aead import decrypt, encrypt
from packages.security.crypto.config import AES_GCM_KEY_LENGTH, Argon2Config
from packages.security.crypto.exceptions import DecryptionError
from packages.security.crypto.kdf import derive_key
from packages.security.crypto.random import generate_dek, generate_salt


class VaultStorage(Protocol):
    """Storage contract; implemented separately in storage.py."""

    def create(self, vault: dict) -> None: ...
    def read(self) -> dict: ...


class VaultLockedError(RuntimeError):
    """An operation requires an unlocked vault."""


class VaultFormatError(ValueError):
    """The stored vault has invalid or unsupported metadata."""


def _aad(vault_id: str, version: int, kdf: dict) -> bytes:
    """Canonical AAD binds the encrypted DEK to the vault's KDF metadata."""
    data = {
        "vault_id": vault_id,
        "format_version": version,
        "kdf": kdf,
        "algorithm": "AES-256-GCM",
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _decode(value: str) -> bytes:
    if not isinstance(value, str):
        raise VaultFormatError("Expected a base64 string")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise VaultFormatError("Invalid base64 metadata") from exc


def _encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


@dataclass(frozen=True, slots=True)
class VaultKdfLimits:
    """Vault-specific unlock caps, independent of SEC-03 algorithm limits.

    Provisional MVP policy: benchmark and approve before production rollout.
    Limits must never be below the settings used for newly created vaults.
    """

    max_memory_cost_kib: int = 262144  # 256 MiB
    max_time_cost: int = 6
    max_parallelism: int = 8

    def __post_init__(self) -> None:
        if type(self.max_memory_cost_kib) is not int or not 8 <= self.max_memory_cost_kib <= 1048576:
            raise ValueError("Invalid vault memory policy")
        if type(self.max_time_cost) is not int or not 1 <= self.max_time_cost <= 10:
            raise ValueError("Invalid vault time policy")
        if type(self.max_parallelism) is not int or not 1 <= self.max_parallelism <= 16:
            raise ValueError("Invalid vault parallelism policy")

    def validate(self, config: Argon2Config) -> None:
        if (config.memory_cost_kib > self.max_memory_cost_kib
                or config.time_cost > self.max_time_cost
                or config.parallelism > self.max_parallelism):
            raise VaultFormatError("Vault KDF parameters exceed resource policy")


class VaultService:
    """Orchestrates envelope encryption; no credential CRUD in VLT-02."""

    def __init__(
        self,
        storage: VaultStorage,
        config: Argon2Config | None = None,
        *,
        kdf_limits: VaultKdfLimits | None = None,
    ):
        self._storage = storage
        self._config = config if config is not None else Argon2Config()
        if self._config.key_length != AES_GCM_KEY_LENGTH:
            raise ValueError("Vault KEK must be 32 bytes")
        self._kdf_limits = kdf_limits if kdf_limits is not None else VaultKdfLimits()
        self._kdf_limits.validate(self._config)
        self._dek: bytes | None = None

    def create_vault(self, master_password: str) -> UUID:
        self.lock_vault()
        vault_id = uuid4()
        salt = generate_salt()
        dek = generate_dek()
        params = self._config.to_dict()
        params.pop("key_length")  # VLT-01 format stores only KDF cost parameters.
        kdf = {"algorithm": "argon2id", "salt": _encode(salt), "parameters": params}
        kek = derive_key(master_password, salt, self._config)
        nonce, wrapped_dek = encrypt(kek, dek, _aad(str(vault_id), 1, kdf))
        vault = {
            "format_version": 1,
            "vault_id": str(vault_id),
            "kdf": kdf,
            "key_envelope": {
                "algorithm": "AES-256-GCM",
                "nonce": _encode(nonce),
                "wrapped_dek": _encode(wrapped_dek),
            },
            "records": [],
        }
        self._storage.create(vault)  # Must refuse overwriting an existing vault.
        return vault_id

    def unlock_vault(self, master_password: str) -> None:
        self.lock_vault()
        vault = self._storage.read()
        try:
            if not isinstance(vault, dict) or set(vault) != {
                "format_version", "vault_id", "kdf", "key_envelope", "records"
            } or type(vault["format_version"]) is not int or vault["format_version"] != 1:
                raise VaultFormatError("Unsupported vault structure or version")
            UUID(vault["vault_id"])
            kdf = vault["kdf"]
            envelope = vault["key_envelope"]
            if not isinstance(kdf, dict) or set(kdf) != {"algorithm", "salt", "parameters"}:
                raise VaultFormatError("Invalid KDF metadata")
            if kdf["algorithm"] != "argon2id":
                raise VaultFormatError("Unsupported KDF")
            if not isinstance(envelope, dict) or set(envelope) != {"algorithm", "nonce", "wrapped_dek"}:
                raise VaultFormatError("Invalid key envelope")
            if envelope["algorithm"] != "AES-256-GCM" or not isinstance(vault["records"], list):
                raise VaultFormatError("Unsupported encryption or records format")
            params = kdf["parameters"]
            if not isinstance(params, dict) or set(params) != {"memory_cost_kib", "time_cost", "parallelism"}:
                raise VaultFormatError("Invalid KDF parameters")
            config = Argon2Config(**params, key_length=AES_GCM_KEY_LENGTH)
            # Reject expensive untrusted metadata before running Argon2id.
            self._kdf_limits.validate(config)
            salt = _decode(kdf["salt"])
            nonce = _decode(envelope["nonce"])
            wrapped_dek = _decode(envelope["wrapped_dek"])
            kek = derive_key(master_password, salt, config)
            dek = decrypt(kek, nonce, wrapped_dek, _aad(vault["vault_id"], 1, kdf))
            if len(dek) != AES_GCM_KEY_LENGTH:
                raise VaultFormatError("Invalid data key length")
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            if isinstance(exc, DecryptionError):
                raise
            raise VaultFormatError("Invalid vault metadata") from exc
        self._dek = dek

    def lock_vault(self) -> None:
        """Best-effort key reference cleanup; Python cannot guarantee zeroization."""
        self._dek = None

    @property
    def is_unlocked(self) -> bool:
        return self._dek is not None

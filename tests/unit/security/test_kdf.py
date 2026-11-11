"""Unit tests for SEC-03 Argon2id key derivation."""

import pytest

from packages.security.crypto.config import Argon2Config
from packages.security.crypto.kdf import MIN_SALT_LENGTH, derive_key


@pytest.fixture
def fast_config() -> Argon2Config:
    """Use low valid KDF work factors only in unit tests."""
    return Argon2Config(memory_cost_kib=64, time_cost=1, parallelism=1)


def test_derive_key_is_deterministic(fast_config: Argon2Config) -> None:
    salt = bytes(range(MIN_SALT_LENGTH))
    first = derive_key("test-master-password", salt, fast_config)
    second = derive_key("test-master-password", salt, fast_config)
    assert first == second
    assert len(first) == fast_config.key_length


def test_different_password_changes_key(fast_config: Argon2Config) -> None:
    salt = bytes(range(MIN_SALT_LENGTH))
    assert derive_key("correct", salt, fast_config) != derive_key("incorrect", salt, fast_config)


def test_different_salt_changes_key(fast_config: Argon2Config) -> None:
    assert derive_key("same-password", b"a" * MIN_SALT_LENGTH, fast_config) != derive_key(
        "same-password", b"b" * MIN_SALT_LENGTH, fast_config
    )


@pytest.mark.parametrize("password", ["", None, b"password", 123])
def test_invalid_password_rejected(password: object, fast_config: Argon2Config) -> None:
    with pytest.raises((TypeError, ValueError)):
        derive_key(password, b"s" * MIN_SALT_LENGTH, fast_config)  # type: ignore[arg-type]


@pytest.mark.parametrize("salt", [b"short", "not-bytes", None])
def test_invalid_salt_rejected(salt: object, fast_config: Argon2Config) -> None:
    with pytest.raises((TypeError, ValueError)):
        derive_key("password", salt, fast_config)  # type: ignore[arg-type]


def test_invalid_config_rejected() -> None:
    with pytest.raises(TypeError):
        derive_key("password", b"s" * MIN_SALT_LENGTH, None)  # type: ignore[arg-type]


def test_config_serialization_round_trip(fast_config: Argon2Config) -> None:
    assert Argon2Config.from_dict(fast_config.to_dict()) == fast_config


def test_unknown_config_field_rejected(fast_config: Argon2Config) -> None:
    data = {**fast_config.to_dict(), "unknown": 1}
    with pytest.raises(ValueError):
        Argon2Config.from_dict(data)

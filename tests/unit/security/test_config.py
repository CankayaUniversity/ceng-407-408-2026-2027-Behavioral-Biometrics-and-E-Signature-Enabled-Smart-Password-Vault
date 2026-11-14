"""Unit tests for SEC-04 cryptographic configuration validation."""

from dataclasses import FrozenInstanceError

import pytest

from packages.security.crypto.config import (
    AES_GCM_KEY_LENGTH,
    AES_GCM_NONCE_LENGTH,
    AES_GCM_TAG_LENGTH,
    Argon2Config,
)


def test_aes_gcm_sizes() -> None:
    assert (AES_GCM_KEY_LENGTH, AES_GCM_NONCE_LENGTH, AES_GCM_TAG_LENGTH) == (32, 12, 16)


def test_config_round_trip() -> None:
    config = Argon2Config(memory_cost_kib=64, time_cost=1, parallelism=1)
    assert Argon2Config.from_dict(config.to_dict()) == config


def test_config_is_immutable() -> None:
    config = Argon2Config()
    with pytest.raises(FrozenInstanceError):
        config.time_cost = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    ("overrides", "exception"),
    [
        ({"parallelism": 0}, ValueError),
        ({"parallelism": 17}, ValueError),
        ({"time_cost": 0}, ValueError),
        ({"time_cost": 11}, ValueError),
        ({"memory_cost_kib": 7}, ValueError),
        ({"memory_cost_kib": 1048577}, ValueError),
        ({"memory_cost_kib": 8, "parallelism": 2}, ValueError),
        ({"key_length": 3}, ValueError),
        ({"key_length": 1025}, ValueError),
        ({"time_cost": True}, TypeError),
        ({"parallelism": "4"}, TypeError),
    ],
)
def test_invalid_config_rejected(overrides: dict, exception: type[Exception]) -> None:
    with pytest.raises(exception):
        Argon2Config(**overrides)


@pytest.mark.parametrize(
    "invalid_data",
    [
        None,
        [],
        {},
        {**Argon2Config().to_dict(), "unexpected": 1},
        {k: v for k, v in Argon2Config().to_dict().items() if k != "time_cost"},
    ],
)
def test_invalid_serialized_config_rejected(invalid_data: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        Argon2Config.from_dict(invalid_data)  # type: ignore[arg-type]

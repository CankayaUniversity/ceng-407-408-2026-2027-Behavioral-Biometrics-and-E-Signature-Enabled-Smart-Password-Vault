"""Unit tests for SEC-04 secure salt and DEK generation."""

import pytest

from packages.security.crypto.config import AES_GCM_KEY_LENGTH
from packages.security.crypto.kdf import MIN_SALT_LENGTH
from packages.security.crypto.random import generate_dek, generate_salt


def test_default_salt_length() -> None:
    assert len(generate_salt()) == MIN_SALT_LENGTH


def test_custom_salt_length() -> None:
    assert len(generate_salt(32)) == 32


def test_salts_are_fresh() -> None:
    assert generate_salt() != generate_salt()


def test_dek_has_correct_length() -> None:
    assert len(generate_dek()) == AES_GCM_KEY_LENGTH


def test_deks_are_fresh() -> None:
    assert generate_dek() != generate_dek()


@pytest.mark.parametrize("invalid_length", [0, MIN_SALT_LENGTH - 1, -1])
def test_short_salt_rejected(invalid_length: int) -> None:
    with pytest.raises(ValueError):
        generate_salt(invalid_length)


@pytest.mark.parametrize("invalid_length", [True, 16.5, "32", None])
def test_non_integer_salt_length_rejected(invalid_length: object) -> None:
    with pytest.raises(TypeError):
        generate_salt(invalid_length)  # type: ignore[arg-type]

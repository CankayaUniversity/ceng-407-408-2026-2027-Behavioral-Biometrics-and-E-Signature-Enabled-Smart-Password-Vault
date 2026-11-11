"""Argon2id key derivation for SEC-03.

This module derives raw key bytes; it does not manage vault files, DEK
wrapping, authentication sessions, or password persistence.
"""

from argon2.low_level import Type, hash_secret_raw

from .config import Argon2Config


MIN_SALT_LENGTH = 16  # Argon2id salt policy for this project (bytes).


def derive_key(
    master_password: str,
    salt: bytes,
    config: Argon2Config,
) -> bytes:
    """Derive a key from the password using Argon2id.

    The password is encoded as UTF-8 without implicit normalization.
    Store the randomly generated salt and config parameters alongside the
    encrypted vault; never store the password or resulting key on disk.

    The caller must provide a cryptographically random, per-vault salt.
    The vault layer is responsible for requiring a 32-byte KEK for AES-256.
    """
    if not isinstance(master_password, str):
        raise TypeError("master_password must be a string")
    if not master_password:
        raise ValueError("master_password must not be empty")
    if not isinstance(salt, bytes):
        raise TypeError("salt must be bytes")
    if len(salt) < MIN_SALT_LENGTH:
        raise ValueError(f"salt must be at least {MIN_SALT_LENGTH} bytes")
    if not isinstance(config, Argon2Config):
        raise TypeError("config must be an Argon2Config")

    return hash_secret_raw(
        secret=master_password.encode("utf-8"),
        salt=salt,
        time_cost=config.time_cost,
        memory_cost=config.memory_cost_kib,
        parallelism=config.parallelism,
        hash_len=config.key_length,
        type=Type.ID,
    )

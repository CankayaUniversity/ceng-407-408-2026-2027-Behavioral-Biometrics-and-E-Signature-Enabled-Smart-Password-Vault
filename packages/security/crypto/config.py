"""Cryptographic configuration for SEC-03.

Vault-specific key-size requirements are checked by the vault layer.
"""

from dataclasses import dataclass
from typing import Any

AES_GCM_KEY_LENGTH = 32
AES_GCM_NONCE_LENGTH = 12
AES_GCM_TAG_LENGTH = 16


@dataclass(frozen=True, slots=True)
class Argon2Config:
    memory_cost_kib: int = 65536
    time_cost: int = 3
    parallelism: int = 4
    key_length: int = 32

    def __post_init__(self) -> None:
        for name in ("memory_cost_kib", "time_cost", "parallelism", "key_length"):
            value = getattr(self, name)
            if type(value) is not int:
                raise TypeError(f"{name} must be an integer")

        if not 1 <= self.parallelism <= 16:
            raise ValueError("parallelism must be between 1 and 16")
        if not 1 <= self.time_cost <= 10:
            raise ValueError("time_cost must be between 1 and 10")
        if not 8 * self.parallelism <= self.memory_cost_kib <= 1048576:
            raise ValueError("memory_cost_kib is outside supported bounds")
        if not 4 <= self.key_length <= 1024:
            raise ValueError("key_length is outside supported bounds")

    def to_dict(self) -> dict[str, int]:
        return {
            "memory_cost_kib": self.memory_cost_kib,
            "time_cost": self.time_cost,
            "parallelism": self.parallelism,
            "key_length": self.key_length,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Argon2Config":
        if not isinstance(data, dict):
            raise TypeError("Argon2 configuration must be an object")
        expected = {"memory_cost_kib", "time_cost", "parallelism", "key_length"}
        if set(data) != expected:
            raise ValueError("Invalid Argon2 configuration fields")
        return cls(**data)

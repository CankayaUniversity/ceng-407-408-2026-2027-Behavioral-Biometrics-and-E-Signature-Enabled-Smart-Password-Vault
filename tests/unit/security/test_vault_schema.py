"""VLT-01: Vault JSON Schema v1 yapi dogrulama testleri."""

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "security"
    / "vault"
    / "schemas"
    / "vault_v1.schema.json"
)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    """Semayi bir kez yukle, standart ve UUID format kontrollerini etkinlestir."""
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.fixture
def valid_vault() -> dict:
    """Gercek parola ya da anahtar icermeyen temsili gecerli kasa verisi."""
    return {
        "format_version": 1,
        "vault_id": str(uuid4()),
        "kdf": {
            "algorithm": "argon2id",
            "salt": "c2FsdA==",
            "parameters": {
                "memory_cost_kib": 65536,
                "time_cost": 3,
                "parallelism": 4,
            },
        },
        "key_envelope": {
            "algorithm": "AES-256-GCM",
            "nonce": "bm9uY2U=",
            "wrapped_dek": "ZW5jcnlwdGVk",
        },
        "records": [
            {
                "record_id": str(uuid4()),
                "version": 1,
                "nonce": "bm9uY2U=",
                "ciphertext": "ZW5jcnlwdGVk",
            }
        ],
    }


def test_schema_accepts_valid_vault(validator, valid_vault):
    validator.validate(valid_vault)


def test_schema_accepts_empty_records(validator, valid_vault):
    valid_vault["records"] = []
    validator.validate(valid_vault)


@pytest.mark.parametrize(
    "field", ["format_version", "vault_id", "kdf", "key_envelope", "records"]
)
def test_schema_rejects_missing_top_level_fields(validator, valid_vault, field):
    invalid = deepcopy(valid_vault)
    del invalid[field]
    assert not validator.is_valid(invalid)


@pytest.mark.parametrize(
    "location, field, invalid_value",
    [
        ((), "format_version", 2),
        ((), "vault_id", "not-a-uuid"),
        (("kdf",), "algorithm", "pbkdf2"),
        (("kdf", "parameters"), "memory_cost_kib", 0),
        (("kdf", "parameters"), "time_cost", -1),
        (("kdf", "parameters"), "parallelism", 0),
        (("key_envelope",), "algorithm", "AES-128-GCM"),
        (("records", 0), "version", 2),
        (("records", 0), "record_id", "invalid-uuid"),
        (("records", 0), "ciphertext", ""),
    ],
)
def test_schema_rejects_invalid_values(
    validator, valid_vault, location, field, invalid_value
):
    invalid = deepcopy(valid_vault)
    target = invalid
    for part in location:
        target = target[part]
    target[field] = invalid_value
    assert not validator.is_valid(invalid)


@pytest.mark.parametrize("location", [(), ("kdf",), ("key_envelope",), ("records", 0)])
def test_schema_rejects_unknown_fields(validator, valid_vault, location):
    invalid = deepcopy(valid_vault)
    target = invalid
    for part in location:
        target = target[part]
    target["unexpected_field"] = "invalid"
    assert not validator.is_valid(invalid)


@pytest.mark.parametrize(
    "location,field",
    [
        (("kdf",), "salt"),
        (("kdf",), "parameters"),
        (("key_envelope",), "nonce"),
        (("key_envelope",), "wrapped_dek"),
        (("records", 0), "record_id"),
        (("records", 0), "nonce"),
        (("records", 0), "ciphertext"),
    ],
)
def test_schema_rejects_missing_nested_fields(validator, valid_vault, location, field):
    invalid = deepcopy(valid_vault)
    target = invalid
    for part in location:
        target = target[part]
    del target[field]
    assert not validator.is_valid(invalid)

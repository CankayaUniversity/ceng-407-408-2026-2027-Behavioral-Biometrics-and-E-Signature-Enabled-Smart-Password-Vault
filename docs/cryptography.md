# Cryptography Module — SEC-03

**Status:** Implemented primitives; integration decisions are tracked separately  
**Scope:** `packages/security/crypto/`

## 1. Purpose and boundaries

This module provides Argon2id key derivation, AES-256-GCM authenticated encryption and cryptographically secure random values. It does **not** create vault files, wrap the DEK into a vault envelope, manage authentication sessions, or implement credential CRUD. Those tasks belong to subsequent Vault issues.

The vault layer owns the master-password unlock policy, DEK/KEK lifecycle, AAD serialization, persistent storage and authorization checks. Neither plaintext credentials nor plaintext keys may be stored on disk or sent to the backend.

## 2. Argon2id key derivation

**Source:** `packages/security/crypto/kdf.py` and `config.py`  
**API:** `derive_key(master_password: str, salt: bytes, config: Argon2Config) -> bytes`

- Password is encoded as UTF-8, without implicit Unicode normalization.
- Salt must be at least 16 bytes and should be newly generated per vault with `generate_salt()`.
- `argon2.low_level.hash_secret_raw(..., type=Type.ID)` performs key derivation.
- Config values are serialized by `Argon2Config.to_dict()` and validated by `from_dict()`; unexpected and missing fields are rejected.

| Parameter | Proposed default | Validation bounds |
|---|---:|---|
| `memory_cost_kib` | 65,536 KiB | from `8 * parallelism` to 1,048,576 KiB |
| `time_cost` | 3 | 1–10 |
| `parallelism` | 4 | 1–16 |
| `key_length` | 32 bytes | 4–1,024 bytes |

The defaults are preliminary; benchmark and team approval are required before treating them as finalized. The **Vault layer** must enforce a 32-byte KEK when using AES-256-GCM; the generic Argon2id primitive does not enforce that use-case-specific requirement.

**Integration note:** The VLT-01 JSON schema's `kdf.parameters` currently omits `key_length`, while `Argon2Config.from_dict()` requires it. Resolve this contract mismatch before VLT-02 serialization; do not silently assume the two formats are interchangeable.

## 3. AES-256-GCM authenticated encryption

**Source:** `packages/security/crypto/aead.py`  
**APIs:** `encrypt(key: bytes, plaintext: bytes, aad: bytes | None = None) -> tuple[bytes, bytes]` and `decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes | None = None) -> bytes`

- AES-GCM key: **32 bytes** (256 bits).
- Nonce: **12 bytes** (96 bits), freshly generated with `secrets.token_bytes()` by each `encrypt()` call.
- Authentication tag: **16 bytes** (128 bits), appended to the ciphertext by the `cryptography` library.
- `decrypt()` authenticates both the ciphertext and the same AAD supplied during encryption.
- If authentication fails, the library's `InvalidTag` is translated to the public `DecryptionError`. No partial plaintext is returned.
- Invalid input types and lengths raise `TypeError` or `ValueError` before decryption.

The caller must define deterministic AAD bytes and persist the returned nonce alongside the ciphertext. **Never reuse a (key, nonce) pair.** Random 96-bit nonces reduce collision risk but do not mathematically guarantee uniqueness for unlimited encryptions; the system must keep per-key usage within an appropriate operational limit. The current primitive does not implement persistent nonce tracking.

## 4. Secure random generation

**Source:** `packages/security/crypto/random.py`

- `generate_salt(length: int = 16) -> bytes`: uses `secrets.token_bytes()` and requires at least 16 bytes.
- `generate_dek() -> bytes`: generates a random 32-byte DEK.
- AEAD nonces are generated inside `aead.encrypt()` to avoid exposing a caller-supplied nonce in the standard encryption API.

Do not use `random` or predictable timestamps to create salts, keys or nonces.

## 5. Errors, testing and limitations

Unit tests are located at `tests/unit/security/test_kdf.py` and `tests/unit/security/test_aead.py`.

```bash
python3 -m pytest tests/unit/security/test_kdf.py tests/unit/security/test_aead.py -v
```

The tests cover deterministic KDF output, password/salt changes, invalid inputs, serialization, AES-GCM round-trips, changed AAD, wrong keys, tampered ciphertext, and fresh nonce generation.

- A successful unit test run does not establish production-grade security or resistance to a compromised host.
- Python cannot guarantee complete erasure of immutable passwords or key material from memory; the Vault layer must minimize plaintext lifetime and apply best-effort cleanup.
- AES-GCM detects unauthorized ciphertext/AAD modifications but does not, by itself, prevent a valid older vault file from being restored (rollback) or records from being deleted.
- Parameter limits prevent some malformed/resource-intensive inputs; deployment-specific benchmarking and operational limits remain necessary.

## 6. Dependencies

- `argon2-cffi` — Argon2id
- `cryptography` — AES-GCM
- `pytest` — test/development dependency

Record these dependencies in the root `pyproject.toml` using the team's selected dependency-management approach.

**Related documents:** `docs/vault-format.md`, `docs/threat-model.md`, and the relevant architecture decision records.

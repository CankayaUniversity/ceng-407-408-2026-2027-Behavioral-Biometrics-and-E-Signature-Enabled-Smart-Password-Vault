# VLT-02: Proposed KEK resource policy and AAD encoding

**Status:** Proposed — team approval required; does not amend accepted ADR-0006.

## Key-envelope AAD (implementation behavior)

For format version 1, the AES-256-GCM key-envelope AAD is UTF-8 bytes of a JSON object with these keys and values:

- `algorithm`: literal `AES-256-GCM`
- `format_version`: integer `1`
- `kdf`: the full envelope `kdf` metadata object, including `algorithm`, base64 `salt`, and `parameters`
- `vault_id`: vault UUID string as stored in the envelope

Serialize using Python `json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")`.
This exact byte-level representation is required to unlock files produced by this implementation. Any future change requires a versioned compatibility decision and interoperability tests. The JSON schema alone does not specify canonical AAD.

## Argon2id resource policy (provisional MVP)

The generic SEC-03 Argon2Config retains its algorithm-level bounds. The VLT-02 service separately checks untrusted on-disk Argon2 metadata **before** deriving a key. The proposed default caps are: memory 262144 KiB (256 MiB), time cost 6, parallelism 8. Vault creation validates selected parameters against the same caps.

These are provisional *resource caps*, **not** claims of adequate security calibration. Benchmark default KDF settings on target devices, document the approved policy, and allow previously created vaults to be unlocked only under a compatible approved policy. Higher KDF costs may increase denial-of-service risk; lower KDF costs may weaken resistance to password guessing.

## Limitations

- Argon2 allocation can still be disruptive within accepted caps; resource policy is not a complete DoS defense.
- AAD authenticates this envelope's metadata but does not prevent replacement by an older valid entire vault file (rollback).
- Python does not guarantee in-memory key zeroization.
- This proposal only covers key-envelope AAD, not future per-record AAD (VLT-03).

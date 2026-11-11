ADR-0006 — Encrypted Vault Data Format
- Status: Accepted (team approval reported; approval date not recorded)
- Issue: VLT-01 — Define Encrypted Vault Data Format
- Scope: MVP v0.1
Context
The MVP needs a local encrypted password vault that stores no plaintext credentials or unprotected encryption keys on disk. The Desktop application must access vault operations through a stable contract. The format must carry sufficient cryptographic metadata for subsequent implementation and validation.
Decision
1. Storage: Use a versioned local JSON envelope for MVP v0.1. Schema: packages/security/vault/schemas/vault_v1.schema.json. Documentation: docs/vault-format.md.
2. Key hierarchy: Generate a random 256-bit Data Encryption Key (DEK) for each vault. Derive a Key Encryption Key (KEK) from the master password using Argon2id and a random salt. Protect the DEK with AES-256-GCM; store only the encrypted wrapped_dek on disk.
3. Records: Encrypt credential payloads using AES-256-GCM and the DEK, with a unique nonce per encryption under the same key. Keep credential content, including title, username, password, URL and notes, inside ciphertext.
4. Metadata: Include format_version, vault_id, Argon2id salt and parameters, key-envelope algorithm/nonce/ciphertext, and per-record record_id, version, nonce and ciphertext. The format version starts at 1.
5. Integrity: Use authenticated additional data (AAD) to bind each encrypted payload to its vault/record context. Reject unsupported formats, invalid structure and authentication failures. Exact deterministic AAD encoding is an implementation contract that must be finalized before encryption code is written.
6. Module boundary: Encryption/decryption and decrypted keys remain in the local security/vault module, never in backend payloads or logs. Desktop communicates through contracts/vault_service.py and does not manipulate cryptographic material directly.
Consequences
- JSON is easy to inspect and schema-validate for the MVP, but concurrent updates, atomic writes, and backup/rollback handling require explicit implementation decisions.
- Changing the master password can eventually re-wrap the DEK rather than re-encrypt every credential, subject to future implementation.
- The v1 schema verifies shape, not the cryptographic validity of ciphertext, base64 decoding, nonce sizes, UUID formats, or safe KDF limits by itself. Runtime checks and security tests remain necessary.
- Valid ciphertext rollback or record deletion is not inherently prevented by per-record AES-GCM authentication.
Follow-up implementation constraints
- Confirm secure Argon2id limits and deterministic AAD serialization during SEC-03 / VLT-02, before implementing cryptographic operations.
- Implement vault creation/unlock and credential CRUD in VLT-02 / VLT-03, not in this ADR.
- Enforce vault lock behavior and session integration in later planned vault issues.
References
- docs/PROJECT_BLUEPRINT.md — Section 8, vault cryptographic model (repository location may differ).
- AGILE_SPRINT_PLAN.md — Sprint 1 VLT-01 acceptance criteria.
- docs/vault-format.md
- packages/security/vault/schemas/vault_v1.schema.json
- contracts/vault_service.py
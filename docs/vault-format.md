# Encrypted Vault Data Format

**Issue:** VLT-01 — Define Encrypted Vault Data Format  
**Version:** 0.1  
**Status:** Proposed — Pending Architecture Review

## 1. Overview

The vault is responsible for securely storing user credentials on the local device.

The proposed MVP storage format is a versioned JSON envelope containing encrypted credential records and the cryptographic metadata required for decryption.

The vault uses:

- **Argon2id** for password-based key derivation.
- **AES-256-GCM** for authenticated encryption.
- **Data Encryption Key (DEK)** for encrypting credential records.
- **Key Encryption Key (KEK)** for protecting the DEK.

Plaintext credentials and unencrypted cryptographic keys must never be persisted to disk or transmitted to the backend.

The backend manages authentication and session authorization but does not perform vault decryption.

## 2. Vault Data Structure

### 2.1 JSON Format

The proposed vault structure is:

```json
{
  "format_version": 1,
  "vault_id": "uuid",
  "kdf": {
    "algorithm": "argon2id",
    "salt": "base64-encoded-salt",
    "parameters": {
      "memory_cost_kib": 65536,
      "time_cost": 3,
      "parallelism": 4
    }
  },
  "key_envelope": {
    "algorithm": "AES-256-GCM",
    "nonce": "base64-encoded-nonce",
    "wrapped_dek": "base64-encoded-ciphertext-and-tag"
  },
  "records": [
    {
      "record_id": "uuid",
      "version": 1,
      "nonce": "base64-encoded-nonce",
      "ciphertext": "base64-encoded-ciphertext-and-tag"
    }
  ]
}
```

The values above are placeholders, not real cryptographic material.

Argon2id parameters are preliminary configuration values and require validation during SEC-03 implementation.

### 2.2 Field Definitions

| Field | Description |
|---|---|
| `format_version` | Vault file format version |
| `vault_id` | Unique vault identifier |
| `kdf` | Key derivation configuration |
| `algorithm` | Cryptographic algorithm identifier |
| `salt` | Random salt used for Argon2id |
| `parameters` | Argon2id configuration |
| `key_envelope` | Encrypted DEK and its metadata |
| `wrapped_dek` | DEK encrypted using the KEK |
| `records` | Collection of encrypted credential records |
| `record_id` | Unique credential identifier |
| `version` | Individual record format version |
| `nonce` | Unique AES-GCM nonce per encryption under the same key |
| `ciphertext` | Encrypted payload including authentication tag |

### 2.3 Encrypted Credential Payload

Each decrypted credential record follows the proposed structure:

```json
{
  "title": "Example Service",
  "username": "user@example.com",
  "password": "example-password",
  "url": "https://example.com",
  "notes": ""
}
```

This structure represents plaintext data only during authorized vault operations.

Sensitive fields, including titles, usernames, passwords, URLs and notes, must remain encrypted in persistent storage.

The final set of credential fields requires team approval.

## 3. Key Hierarchy

The vault follows an envelope encryption model.

### 3.1 Data Encryption Key (DEK)

- A cryptographically secure random 256-bit DEK is generated during vault creation.
- The DEK encrypts and decrypts credential records using AES-256-GCM.
- The plaintext DEK must never be persisted to disk.
- The DEK is stored in encrypted form as `wrapped_dek`.

### 3.2 Key Encryption Key (KEK)

- The KEK is derived from the user's master password using Argon2id.
- A randomly generated salt is used during key derivation.
- The required KDF parameters are stored in the vault metadata.
- The KEK encrypts and decrypts the DEK using AES-256-GCM.
- The plaintext KEK must never be persisted to disk or transmitted to the backend.

### 3.3 Key Lifecycle

1. **Creation:** Generate a random DEK, derive the KEK and encrypt the DEK.
2. **Unlock:** Derive the KEK from the provided master password and decrypt the stored DEK.
3. **Usage:** Use the decrypted DEK for authorized credential operations.
4. **Lock:** Remove references to decrypted keys and reject credential operations until the vault is unlocked again.

Decrypted keys must remain in process memory only while required.

Complete memory zeroization cannot be guaranteed in Python. Cleanup must therefore be treated as best-effort.

## 4. Cryptographic Metadata

### 4.1 Key Derivation Metadata

The vault stores the following Argon2id metadata:

- Algorithm identifier
- Random salt
- Memory cost
- Time cost
- Parallelism

The derived KEK is 256 bits to support AES-256-GCM.

Cryptographic parameters must be validated against supported configurations rather than accepted blindly from an untrusted vault file.

### 4.2 Encryption Metadata

Each encrypted payload requires:

- Encryption algorithm identifier
- Unique nonce for the encryption key
- Ciphertext
- Authentication tag

AES-256-GCM uses a 96-bit nonce in the proposed format.

The ciphertext and 128-bit authentication tag are stored together as a base64-encoded value.

### 4.3 Authenticated Metadata

AES-GCM Additional Authenticated Data (AAD) must bind encrypted content to its context.

The proposed authenticated context includes:

**Key envelope:**
- Vault identifier
- Vault format version
- Key derivation metadata
- Key wrapping algorithm

**Credential records:**
- Vault identifier
- Record identifier
- Record version

AAD values must use a deterministic serialization format agreed upon during implementation.

Modified authenticated metadata or ciphertext must cause decryption to fail.

AES-GCM authentication does not independently prevent deletion of records or rollback to an older valid vault file. These limitations must be addressed in the threat model.

## 5. Format Versioning

The vault contains a `format_version` field to identify the storage structure.

The initial proposed version is:

`format_version = 1`

Versioning requirements:

- The application must validate the format version before processing encrypted records.
- Unsupported versions must be rejected.
- Missing or invalid required metadata must cause a validation error.
- Future format changes must be explicitly versioned.
- Existing vault data must not be silently converted or overwritten.

Each credential record also contains a `version` field to support future record schema changes.

Migration implementation is outside the scope of VLT-01.

## 6. Storage and Security Rules

The proposed MVP uses local JSON storage.

The following rules apply:

1. Plaintext credentials must never be written to persistent storage.
2. Plaintext DEK and KEK values must never be persisted.
3. Vault decryption must remain local to the security module.
4. Cryptographic secrets must never be included in logs or backend API payloads.
5. Invalid authentication tags must result in decryption failure.
6. Incorrect master passwords must not expose the DEK or credential contents.
7. Credential operations must be rejected while the vault is locked.
8. The storage implementation must prevent partially written files from replacing a valid vault file.

The vault storage mechanism should remain independent of the cryptographic operations so that future storage changes do not require changing the encryption model.

JSON versus SQLite remains an architectural decision requiring team approval. JSON is the proposed MVP format.

## 7. Desktop Integration Contract

The desktop application must access the vault through a defined service interface rather than manipulating encrypted files or encryption keys directly.

### 7.1 Required Operations

| Operation | Responsibility |
|---|---|
| `create_vault` | Create a new encrypted vault |
| `unlock_vault` | Unlock the vault with the master password |
| `lock_vault` | Lock the vault and release decrypted key references |
| `add_credential` | Encrypt and store a credential |
| `get_credential` | Retrieve and decrypt an authorized credential |
| `update_credential` | Update an existing encrypted credential |
| `delete_credential` | Remove an existing credential |
| `list_credentials` | List credential entries after authorized unlock |

These are proposed service operation names. Their final Python signatures, return types and error contracts must be agreed upon with the Desktop module owner.

### 7.2 Responsibility Separation

**Desktop Application**
- Handles user interaction.
- Requests vault operations.
- Responds to session authorization changes.
- Does not directly handle DEK/KEK generation or encryption.

**Security/Vault Module**
- Manages the local encrypted vault.
- Handles key derivation and encryption through the shared cryptography utilities.
- Enforces locked/unlocked vault access.
- Rejects invalid or tampered encrypted data.

**Backend**
- Manages authentication and session authorization.
- Does not receive plaintext vault credentials, the KEK or the DEK.

Device authentication success alone must not provide a vault decryption key.

The initial unlock policy and re-authentication behavior require team approval.

## 8. Architecture Decisions and Dependencies

The design separates the following responsibilities:

- **Cryptography:** Argon2id, AES-256-GCM and key wrapping.
- **Serialization:** Validation and representation of the vault data format.
- **Storage:** Reading and writing the encrypted vault.
- **Vault Service:** Coordinating authorized vault operations.
- **Desktop:** User interface and integration.

The implementation should follow separation of concerns and dependency inversion.

A storage interface may be introduced during implementation when needed. VLT-01 does not require implementing repository classes, encryption services or credential CRUD.

### Dependencies

- **SEC-02:** Vault security architecture and threat model.
- **SEC-03:** Shared cryptographic utilities.
- **SEC-04:** Cryptographic unit-testing infrastructure.
- **SEC-01 / APP-01:** Desktop integration requirements.

## 9. Open Decisions

The following decisions must be confirmed by the team before implementation:

- JSON or SQLite as the MVP storage format.
- Final Argon2id configuration.
- Exact credential payload fields.
- Canonical AAD serialization rules.
- Vault unlock and re-authentication policy.
- Final Desktop-to-Vault interface and error contracts.
- Local vault file location and backup behavior.



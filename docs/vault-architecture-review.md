# SEC-01 — Vault Encryption Architecture Review

## Status and Ownership

- Status: Draft — pending review with Member 3
- Author: Member 1 — Desktop integration and architecture review
- Reviewer: Member 3 — Cryptography and Password Vault
- Related issues: SEC-02, SEC-03, SEC-04, VLT-01
- Scope: Desktop vault encryption, key handling, and module interfaces

This document proposes the contract between the Desktop and Security
modules. It does not report completed cryptographic functionality.

Mobile synchronization, recovery, and autofill require separate designs.
Changes affecting the shared vault format must be reviewed before
implementation.

## 1. Security Goals

- Encrypt stored credentials before writing them to disk.
- Detect changes to encrypted data and authenticated metadata.
- Reject protected operations while the vault is locked.
- Keep cryptographic implementation inside the Security module.
- Keep master passwords and unwrapped keys out of persistent storage,
  logs, source control, and API responses.
- Separate device authentication from vault decryption.

Successful device authentication does not provide the vault encryption
key and must not automatically decrypt the vault.

## 2. Proposed Key Hierarchy

### Master Password

The user supplies the master password through the Desktop interface.

Desktop passes it to the Security service for vault creation or unlock.
Desktop must not persist it or retain it in application state after
the operation. The password input should be cleared after submission.

### Key Encryption Key — KEK

Security derives a KEK from the master password using Argon2id and a
random salt.

The vault envelope stores the salt and versioned Argon2id parameters.
It never stores the master password or the derived KEK.

Argon2id parameters must be benchmarked on supported devices and
reviewed by Member 3. Readers must validate parameter bounds before
performing expensive key derivation.

### Data Encryption Key — DEK

Security generates a random 256-bit DEK for each new vault.

The DEK encrypts the credential payload using AES-256-GCM.
The KEK encrypts, or wraps, the DEK using AES-256-GCM.

Use independent nonces for DEK wrapping and payload encryption.
A nonce must never be reused with the same encryption key.

Randomness must come from the cryptographic library or operating
system CSPRNG.

### Unlock Flow

1. Read and validate the vault envelope.
2. Check format version, field lengths, and KDF parameter bounds.
3. Derive the KEK from the supplied password and stored salt.
4. Authenticate and decrypt the wrapped DEK.
5. Authenticate and decrypt the vault payload.
6. Enter the unlocked state only after all checks succeed.

Authentication failure must leave the vault locked and must not
overwrite the existing vault.

### Password Change

A future master-password change should derive a new KEK using a fresh
salt and rewrap the existing DEK using a fresh nonce.

This operation is not implemented by SEC-01. Its final behavior belongs
to the reviewed vault specification.

## 3. Proposed Vault Envelope

VLT-01 owns the final serialized schema. The following fields describe
the information the format needs; this is not a finalized file format.

| Field group | Required information |
|---|---|
| Format | Format version and vault identifier |
| KDF | Algorithm, salt, and Argon2id parameters |
| Wrapped DEK | Algorithm, nonce, ciphertext, and authentication tag |
| Payload | Algorithm, nonce, ciphertext, and authentication tag |

Salts, nonces, and algorithm identifiers are not secret. Their integrity
and interpretation still matter.

Member 3 must specify:

- Exact field names, encodings, lengths, and supported versions.
- Whether authentication tags are appended to ciphertext or stored separately.
- Canonical serialization for authenticated additional data (AAD).
- How envelope metadata is bound to the encrypted DEK and payload.
- Maximum file sizes and KDF parameter bounds.
- Behavior for malformed files and unsupported versions.

Validate untrusted metadata before key derivation. Do not expose
decrypted content until authentication succeeds.

Credential titles, usernames, passwords, URLs, and notes should be
inside the encrypted payload.

## 4. Module Responsibilities

| Responsibility | Desktop | Security |
|---|---|---|
| Render screens and collect user input | Owns | — |
| Display operation results and errors | Owns | Returns structured errors |
| Derive KEK and generate DEK | — | Owns |
| Encrypt and decrypt vault data | — | Owns |
| Validate the vault envelope | — | Owns |
| Enforce locked-state access restrictions | Reflects state in UI | Owns enforcement |
| Trigger locking on timeout or session restriction | Owns application policy | Executes lock |
| Persist encrypted vault updates safely | — | Owns |
| Clear revealed credentials and password inputs | Owns | Releases internal references |
| Implement credential CRUD | Calls service | Owns |
| Define final cryptographic format | Reviews integration | Member 3 owns |

Desktop must use the public Security service. It must not read internal
key fields, decrypt vault files directly, or implement its own KDF.

Security must remain independent of Qt widgets and UI navigation.

## 5. Proposed Service Interface

These signatures are an integration proposal, not implementation code.
Member 3 will confirm the final types and module location.

```python
class VaultService:
    def create_vault(self, path: Path, master_password: str) -> None:
        ...

    def unlock(self, path: Path, master_password: str) -> None:
        ...

    def lock(self) -> None:
        ...

    def is_locked(self) -> bool:
        ...

    def list_credentials(self) -> list[CredentialSummary]:
        ...

    def get_credential(self, credential_id: str) -> Credential:
        ...

    def add_credential(self, data: CredentialInput) -> str:
        ...

    def update_credential(
        self,
        credential_id: str,
        data: CredentialInput,
    ) -> None:
        ...

    def delete_credential(self, credential_id: str) -> None:
        ...
```

### Interface Semantics

- A new service instance starts locked.
- `create_vault` must reject an existing destination.
- Successful creation persists an encrypted empty vault and leaves it locked.
- `unlock` is allowed only while locked.
- Failed unlock leaves the service locked.
- `lock` is idempotent.
- All credential operations raise `VaultLockedError` while locked.
- `list_credentials` returns summaries without passwords or notes.
- `get_credential` returns plaintext only for an authorized UI operation.
- Successful mutations are persisted before returning.
- Failed persistence must not be reported as a successful update.
- Updates must not silently replace an unreadable or corrupted vault.
- The MVP assumes one writer per vault; concurrent access must be
  rejected or explicitly handled.
- The service is not assumed to be thread-safe. Desktop must serialize
  calls until a concurrency contract is agreed upon.

### Proposed Data Types

- `CredentialSummary`: id, title, username, URL.
- `Credential`: summary fields plus password and optional notes.
- `CredentialInput`: editable credential fields without a generated id.

All of these types contain sensitive information even when passwords
are omitted. Do not log their contents.

### Proposed Error Categories

- `VaultLockedError`
- `VaultAlreadyExistsError`
- `VaultStateError`
- `VaultUnlockError`
- `VaultFormatError`
- `VaultIntegrityError`
- `CredentialNotFoundError`
- `VaultStorageError`

Unlock authentication failures should display a generic message such as:

"Unable to unlock the vault. Check the password or vault file."

Do not claim that a failed authentication tag proves only an incorrect
password; damaged encrypted data can also cause authentication failure.

## 6. Desktop Lock and Unlock Behavior

### Unlock

- Run expensive key derivation outside the UI thread.
- Disable duplicate submissions while unlocking.
- Serialize service operations.
- Display the unlocked screen only after confirmed success.
- Clear the password input after the attempt.

### Lock

Lock must be triggered by:

- Explicit user action.
- Logout.
- Session expiration or revocation.
- A suspicious-session restriction event.
- Application inactivity timeout.
- Application shutdown where cleanup can run.

When locking:

1. Block new credential operations.
2. Clear revealed secrets, open editors, and sensitive UI caches.
3. Call the Security service lock operation.
4. Show the locked state.

If a restriction occurs while unlock is running, its eventual result
must not reopen the vault. Desktop must serialize the transition and
lock any completed result before displaying protected content.

Security releases references to the DEK and decrypted payload.
Desktop releases references to displayed plaintext.

Python and Qt do not provide a general guarantee of secure memory
erasure. Do not claim guaranteed zeroization.

## 7. Storage and Failure Handling

- Persist ciphertext only.
- Use a safe replacement strategy for updates.
- Keep the previous valid vault intact if an update fails.
- Temporary files must not contain plaintext.
- Apply restrictive file permissions where supported.
- Do not silently create a new vault when an existing file fails to open.
- Keep real vault files, test credentials, and secrets out of Git.
- Never include passwords, keys, or decrypted records in exceptions or logs.

## 8. Review and Validation Plan

Implementation tests belong to SEC-03, SEC-04, and later vault issues.

The agreed design must support verification of:

- Encryption/decryption round trips.
- Correct-password unlock.
- Incorrect-password rejection.
- Tampered wrapped-DEK rejection.
- Tampered payload rejection.
- Invalid metadata and unsupported-version rejection.
- Bounded handling of malicious KDF parameters.
- Locked-state rejection for every credential operation.
- Repeated lock calls.
- Safe handling of failed writes.
- Rejection of accidental overwrite during creation.
- Restriction arriving during an unlock attempt.
- UI responsiveness during key derivation.

## 9. Member 3 Review Checklist

- [ ] Key hierarchy and algorithm choices reviewed.
- [ ] KDF parameters and input-validation limits agreed.
- [ ] Envelope metadata and AAD responsibilities agreed.
- [ ] Desktop and Security responsibilities agreed.
- [ ] Lock/unlock interface and state transitions agreed.
- [ ] Credential operation persistence behavior agreed.
- [ ] Error categories and user-facing messages agreed.
- [ ] Tests mapped to implementation issues.
- [ ] Open decisions recorded with owners.

## 10. Review Record

- Reviewer: Pending
- Review date: Pending
- PR or review reference: Pending
- Decisions and requested changes: Pending

SEC-01 can be marked complete after the architecture has been reviewed,
module responsibilities are documented, and the vault lock/unlock
interface requirements have been agreed with Member 3.
# Vault Security Architecture and Threat Model

**Issue:** SEC-02 — Design Vault Security Architecture and Threat Model  
**Version:** 0.1  
**Status:** Proposed — Pending Security Architecture Review  
**References:** `docs/PROJECT_BLUEPRINT.md` (Sections 5, 8, 9, 11, 12); `AGILE_SPRINT_PLAN.md` (SEC-02); `docs/vault-format.md` (VLT-01)

## 1. Scope and Security Goals

This document models threats to the **local encrypted password vault** in the desktop MVP. The desktop app, authorization/session service, behavioral-risk component, and simulated fingerprint device are included where they affect vault access.

Security goals:

- Keep stored credential values confidential at rest, including titles, usernames, passwords, URLs, and notes in the proposed VLT-01 format.
- Detect unauthorized modification of authenticated encrypted content.
- Prevent vault operations when locked or when the applicable session policy denies access.
- Keep plaintext credentials, master password, DEK, and KEK out of backend storage, API messages, logs, and Git.
- Separate successful authentication from possession of the key required to decrypt the vault.

**Out of scope for MVP guarantees:** defense against a fully compromised desktop/OS or privileged malware; secure physical-device key isolation; hardware biometric liveness assurance; protection against rollback/deletion of a previously valid vault file; fully implemented vault-key recovery.

## 2. Protected Assets

| Asset | Confidentiality / integrity requirement | Where it may exist |
|---|---|---|
| Master password | Must not be persisted or logged | Temporarily in local application memory during unlock |
| Key Encryption Key (KEK) | Must not be persisted or sent to backend | Derived locally with Argon2id for DEK unwrap |
| Data Encryption Key (DEK) | Never stored in plaintext | Randomly generated; stored encrypted as `wrapped_dek`; temporarily in local process memory while unlocked |
| Credential data | Secret fields encrypted at rest; changes authenticated | Plaintext only during authorized local operations; ciphertext on disk |
| Vault metadata | Correct version, algorithms, KDF parameters, record identity and authenticated context | Local vault file; not all metadata is confidential |
| Vault access state | Must not be bypassed by UI-only flags | Local vault service coordinated with session authorization policy |
| Session/device evidence | Must be verified before authorization | Backend/auth service and protocol adapter; not vault decryption material |

## 3. Architecture and Trust Boundaries

```text
User / Master Password
        |
        v
Desktop UI (PyQt6) -----> Backend / Session Policy <---- Behavioral AI risk events
        |                        ^
        |                        |
        |                 Device Protocol Adapter
        |                        ^
        |                 Mock Fingerprint Device
        v
Local Vault Service
        |
        +--> Cryptography: Argon2id KEK derivation; AES-256-GCM DEK wrapping / record encryption
        |
        +--> Local Storage: proposed versioned JSON envelope, encrypted records only
```

1. **UI -> Vault service:** The UI requests operations but must not grant itself authorization by flipping a local boolean. The final mechanism for enforcing current session policy at the vault boundary is an **open integration decision**.
2. **Backend -> local vault:** Backend validates device evidence, manages session state, and decides authorization. It must not receive plaintext credentials, KEK, or DEK.
3. **Local process -> disk:** The local vault writes only encrypted records and a wrapped DEK, along with required non-secret metadata. Storage can be copied or altered by an attacker with file access.
4. **Simulated device -> backend:** Signed challenge-response proves a simulator key signed a response, not that a secure physical sensor checked a live fingerprint.
5. **Host boundary:** This MVP does not claim to protect secrets from an attacker who fully controls the host while the vault is unlocked.

## 4. Encryption-at-Rest Design

This section follows the proposed VLT-01 format; final JSON/SQLite storage selection and some serialization details require team confirmation.

1. Create a random 256-bit **DEK** for each vault.
2. Derive a 256-bit **KEK** from the master password using **Argon2id**, a random salt, and stored, validated KDF parameters.
3. Encrypt the DEK with **AES-256-GCM** under the KEK; persist only the `wrapped_dek`, nonce, and needed metadata.
4. Encrypt credential records with AES-256-GCM under the DEK, with a **unique nonce for each encryption under the same key**.
5. Authenticate record context (e.g., vault ID, record ID, record version) and key-envelope context with **AAD**, using a deterministic encoding agreed on before implementation.
6. Reject wrong-password unwrap attempts, modified ciphertext or tags, unsupported versions, and invalid metadata; do not expose decrypted data on failure.
7. On vault lock, deny subsequent credential operations and discard references to decrypted key material. Python cannot guarantee reliable memory zeroization.

**Important:** AEAD detects modification of an authenticated payload, but does not on its own prevent deletion or rollback to an older, correctly authenticated vault file. JSON Schema validation also does not replace cryptographic validation.

## 5. Threat Scenarios and Mitigations

| ID | Threat / attack scenario | Impact | Required MVP control or test | Residual risk |
|---|---|---|---|---|
| T-01 | Attacker copies the local vault file | Offline attempts to recover credentials | Argon2id master-password KDF, random DEK, AES-GCM wrapping, no plaintext secrets on disk | Weak master passwords remain guessable offline |
| T-02 | Ciphertext, GCM tag, or authenticated metadata is altered | Corrupt or substituted secret | AES-GCM authentication check; negative tamper test | Unauthenticated metadata needs explicit handling |
| T-03 | Wrong master password is supplied | Unauthorized DEK recovery | Authenticated DEK unwrap fails without exposing data | Online attempt throttling policy still needs agreement |
| T-04 | A file is truncated or required metadata is malformed | Crash, inconsistent state, potential data loss | Version/schema validation, safe failure; atomic writes in storage implementation | Backup and recovery policy is open |
| T-05 | Old valid vault file replaces current file, or records are deleted | Rollback or loss of records | Explicitly document limitation; detect authenticated payload modifications | AEAD alone cannot prevent rollback or deletion |
| T-06 | Application UI tries to operate after lock or during restricted session | Unauthorized credential read or write | Enforce lock and policy checks at vault-service boundary; security/access-control tests | Final authorization interface remains to be agreed |
| T-07 | Forged `fingerprint_success` or unsigned response | Unauthorized session and vault access | Signed challenge-response; backend verifies signature, challenge binding and policy | Mock-device keys lack hardware isolation |
| T-08 | Replayed, expired, or device-mismatched response | Unauthorized re-authentication | Fresh single-use challenges, expiry, binding and rejection tests | Depends on backend/session enforcement |
| T-09 | Sensitive values leak through logs, API, repository, or clipboard | Secret disclosure | No secret logging/transmission/commits; sanitize audit records | Clipboard history and host malware cannot be fully controlled |
| T-10 | Host process or OS is fully compromised while vault unlocked | Plaintext/key theft | Document trust boundary; minimize key lifetime and exposure | Strong defense against privileged host compromise is out of MVP scope |
| T-11 | Maliciously expensive or invalid Argon2id metadata is loaded | Resource exhaustion | Validate supported algorithms, parameter bounds and data lengths before KDF | Local denial-of-service cannot be eliminated entirely |

## 6. Authentication vs. Encryption Responsibilities

| Component | Owns | Must not do |
|---|---|---|
| Backend / session policy | Verified device proof, challenge lifecycle, session state, authorization, audit | Derive KEK, receive DEK or plaintext credentials |
| Desktop application | User input, UI, authorized requests, lock/re-auth flow | Treat UI state or a bare success flag as proof of access |
| Vault service | Lock/unlock state, encrypted credential operations, local access enforcement | Assume device success alone supplies a decryption key |
| Cryptography module | Argon2id KDF, AES-GCM, envelope operations, key lifecycle utilities | Implement home-grown cryptographic algorithms |
| Device simulator | Simulated enrollment and signed responses | Claim real biometric or hardware-protected guarantees |
| Behavioral AI | Risk signals for policy decisions | Directly authorize vault decryption |

## 7. Open Decisions (Must Be Recorded in ADRs)

- Final persistent storage choice: **JSON envelope (VLT-01 proposal)** versus SQLite encrypted payloads.
- How the vault service receives and enforces trusted session authorization changes, including `SUSPICIOUS`, `REAUTH_REQUIRED`, `LOCKED`, and expiry.
- Initial unlock and re-authentication policy: device proof plus master password is the MVP proposal, but precise re-unlock rules require approval.
- Final Argon2id limits, AAD canonical encoding, record payload fields and plaintext metadata exposure.
- Vault file location, atomic persistence/backup strategy, and recovery design boundary.
- Target OS and local backend deployment assumptions.

Until these are agreed, do not silently treat the proposed behavior as implemented or approved.

## 8. SEC-02 Review and Acceptance

- [ ] Threat model covers relevant vault attack scenarios and residual risks.
- [ ] Authentication/session responsibilities are explicitly separated from vault encryption responsibilities.
- [ ] Encryption-at-rest design and key boundaries are documented.
- [ ] Security architecture is reviewed with the team; resulting decisions and disagreements are recorded under `docs/decisions/`.

**Implementation boundaries:** AES-GCM and Argon2id utilities belong to **SEC-03**; cryptographic tests to **SEC-04**; vault creation/unlock and CRUD to **VLT-02/VLT-03**; automatic vault locking and integration to later vault/session issues.

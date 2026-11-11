# ADR-0007 — Vault Security Architecture and Trust Boundaries

- **Status:** Proposed — pending SEC-02 team security review
- **Issue:** SEC-02 — Design Vault Security Architecture and Threat Model
- **Scope:** MVP v0.1
- **Related decision:** `ADR-0006-vault-data-format.md`

## Context

The MVP combines simulated fingerprint-based authentication, backend session management, behavioral risk detection, and a **local encrypted password vault**. A successful device proof or a UI status flag must not, by itself, decrypt the vault or authorize a credential operation.

The vault must protect stored credentials against local file disclosure and detect modification of authenticated ciphertext. The architecture must explicitly distinguish what encryption protects from what the session/authentication components authorize.

Threat scenarios, mitigations, and residual risks are documented in `docs/threat-model.md`.

## Proposed Decision

1. **Trust boundary:** Keep encrypted vault storage and all vault-key operations local to the security package. The backend owns challenges, session authorization, and audit records; it never receives master passwords, plaintext credentials, DEK, or KEK.
2. **Encryption at rest:** Follow the VLT-01-approved envelope format: random 256-bit DEK for credential encryption, Argon2id-derived KEK for wrapping the DEK, AES-256-GCM authenticated encryption, and unique nonce per encryption under the same key. Authenticate relevant vault/record context with AAD.
3. **Access enforcement:** The desktop UI is not an authorization authority. The vault service must deny credential operations while locked and must integrate with the approved session policy. The exact mechanism for conveying trusted authorization state to the local vault remains open.
4. **Key lifecycle:** Keep unwrapped DEK in local process memory only while needed. On lock, deny future operations and release references to decrypted keys on a best-effort basis. Do not claim guaranteed memory zeroization in Python.
5. **Device and AI separation:** The backend validates signed device challenge-response and determines session state; AI emits risk signals rather than granting access. A verified device response does not supply the vault decryption key.
6. **Fail securely:** Reject malformed/unsupported vault formats and failed AEAD authentication without exposing plaintext. Wrong master password must not unlock the DEK.
7. **Security claims:** Do not claim protection against a fully compromised host, hardware-backed private-key isolation from a simulator, or protection against valid-file rollback/deletion merely from AES-GCM.

## Rationale

- Separating **authentication/authorization** from **decryption** prevents a bare device-success flag or UI state change from becoming a vault-unlock mechanism.
- Envelope encryption keeps the password-derived KEK separate from the random data-encryption DEK and is consistent with the established VLT-01 format.
- Keeping cryptographic secrets local reduces unnecessary backend exposure.
- Explicit residual risks make security testing and MVP claims auditable rather than overstated.

## Consequences

- The Desktop and Backend teams must agree on the trusted session-to-vault authorization boundary before integration.
- SEC-03 implements cryptographic utilities; SEC-04 covers crypto unit tests; VLT-02/VLT-03 implement vault operations; later vault/session issues implement lifecycle integration and automatic locking.
- AES-GCM tamper detection does not prevent deletion or replacement with an older valid encrypted file. File persistence, backup, and recovery policies require separate decisions.

## Open Decisions for Team Review

- Trusted session-policy enforcement mechanism at the local vault boundary.
- Exact initial unlock and re-authentication requirements (device proof plus master password is the MVP proposal).
- Approved Argon2id parameter bounds and canonical AAD serialization.
- File location, atomic-write/backup policy, recovery scope, and host/OS assumptions.

Record decisions in the relevant ADRs before treating these as agreed implementation contracts.

## SEC-02 Review Checklist

- [ ] Threat scenarios and residual risks reviewed (`docs/threat-model.md`).
- [ ] Authentication/session and encryption responsibilities approved.
- [ ] Encryption-at-rest model confirmed against VLT-01.
- [ ] Open decisions assigned or resolved with the team.

## References

- `docs/threat-model.md`
- `docs/decisions/ADR-0006-vault-data-format.md`
- `docs/vault-format.md`
- `PROJECT_BLUEPRINT.md` — Sections 5, 8, 11 and 12
- `AGILE_SPRINT_PLAN.md` — SEC-02 acceptance criteria

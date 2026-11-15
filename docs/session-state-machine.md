# BE-04 — Session State Machine

Status: Draft — Pending Team Review
Owner: Member 2 — Backend
Reviewers: Desktop, Security, and Device owners

## 1. Scope

Define session states, protected-operation permissions, authorized
transitions, reauthentication, and expiration behavior.

This document specifies intended behavior; it does not implement
session management or claim completed enforcement.

Related contracts:
- ../contracts/auth_api.md
- ../contracts/device_protocol.md
- vault-architecture-review.md

## 2. States and Permissions

| State | Meaning | Protected credential operations |
|---|---|---|
| LOCKED | Session exists without protected access | Denied |
| AUTH_PENDING | A fresh device challenge is awaiting verification | Denied |
| TRUSTED | Authentication and session policy checks succeeded | Eligible, subject to separate vault unlock and authorization |
| SUSPICIOUS | Risk policy detected suspicious behavior | Denied; lock the vault |
| REAUTH_REQUIRED | Fresh strong authentication is required | Denied |
| EXPIRED | Absolute session lifetime ended | Denied; terminal state |
| REVOKED | Session was explicitly invalidated | Denied; terminal state |

Protected operations include credential listing, reading, revealing,
copying, creating, updating, and deleting.

TRUSTED does not mean that the vault is decrypted.
The Security service must also be unlocked under the agreed key policy.
Session status and ciphertext access must not expose plaintext secrets.

Session status, challenge requests, and revocation are control operations.
They require their own authorization checks and are not granted merely
because credential operations are denied.

## 3. Transition Ownership

Only the backend session policy may persist session transitions.
Desktop submits requests and reflects the authoritative result.
Behavioral AI submits risk signals; it cannot assign TRUSTED.

A session ID is an identifier, not an authentication credential.
No client may select a target state through an arbitrary state field.

All transitions require validation of the caller, session ownership,
current state, expiration, and operation context.

## 4. Allowed Transitions

| Current state | Event and required condition | Next state |
|---|---|---|
| LOCKED | Authorized authentication start; fresh challenge issued | AUTH_PENDING |
| AUTH_PENDING | Valid device proof, matching pending attempt, and policy checks succeed | TRUSTED |
| AUTH_PENDING | Matching attempt fails or its challenge times out | LOCKED |
| TRUSTED | Backend risk policy accepts a suspicious-behavior signal | SUSPICIOUS |
| SUSPICIOUS | Sufficient new evidence satisfies the agreed recovery policy | TRUSTED |
| SUSPICIOUS | Backend policy requires strong authentication | REAUTH_REQUIRED |
| TRUSTED | Authorized explicit lock or inactivity-lock policy | LOCKED |
| SUSPICIOUS | Authorized explicit lock or inactivity-lock policy | LOCKED |
| REAUTH_REQUIRED | Authorized start with a fresh reauthentication challenge | AUTH_PENDING |
| Any nonterminal state | now >= expires_at | EXPIRED |
| Any nonterminal state | Authorized logout, revocation, or relevant trust revocation | REVOKED |

Any transition not listed is rejected.
A challenge alone grants no protected access.

LOCKED sessions resulting from a failed reauthentication attempt must
retain the pending reauthentication requirement. Retrying must not
downgrade the operation into a weaker login flow.

## 5. Transition Guards and Concurrency

Before committing a transition, recheck the authoritative current
state, session expiration, device trust, and authentication attempt.

Use concurrency-safe conditional updates or transactions.
A successful transition must not overwrite a concurrent revocation,
expiration, or newer restriction.

Responses from old, replaced, or unrelated challenges must not change
the current session. In particular, an old failed response must not
lock a session that has since completed a different attempt.

A proof used for reauthentication must belong to the intended session
through the backend's stored challenge association.

Reject unsigned success flags, modified responses, mismatched context,
expired challenges, and replayed responses.

## 6. Expiration and Reauthentication

Use the backend UTC clock and timezone-aware timestamps.
Reject protected operations at now >= expires_at even if the stored
state has not yet been updated to EXPIRED.

Challenge expiration and session expiration are separate:
- Challenge timeout returns the matching pending attempt to LOCKED.
- Session expiration moves the session to EXPIRED.
- If both apply, session expiration takes precedence.

Reauthentication does not automatically extend expires_at.
On successful reauthentication, update last_reauth_at.

Invalidate outstanding challenges when the session expires or is revoked.
EXPIRED and REVOKED sessions cannot return to TRUSTED.
A new authentication flow must create a new session.

Repeated authorized revocation of an already REVOKED session is
idempotent and does not restore access.

## 7. Vault Coordination

On entering any state other than TRUSTED:
1. Deny new protected operations.
2. Notify Desktop to clear sensitive views and pending results.
3. Invoke the Security service lock operation.

Desktop and Security must independently enforce the local lock.
Backend permissions alone do not erase plaintext already in local memory.

An unlock operation finishing after restriction must not reopen the vault.
Recheck the current authorization context before exposing its result.

Returning to TRUSTED does not automatically unlock the vault.
Use the agreed master-password and key-management policy.
Do not assume that a device signature supplies a decryption key.

## 8. Rejected Transitions

Examples:
- LOCKED directly to TRUSTED without a verified authentication attempt.
- REAUTH_REQUIRED directly to TRUSTED using an AI score.
- AUTH_PENDING to TRUSTED with an expired or consumed challenge.
- EXPIRED or REVOKED to any active state.
- Any transition requested by an unauthorized caller.
- Any transition using a challenge bound to another session.
- A stale authentication result overwriting a newer restriction.

Rejection must not grant access or extend session lifetime.
Record sanitized security events without secrets or signed payload dumps.

## 9. Decisions Requiring Team Review

- Approve the state names, permissions, and transition table.
- Define how an authentication attempt preserves login/reauthentication context.
- Define sufficient evidence for SUSPICIOUS to TRUSTED.
- Set absolute session lifetime, inactivity timeout, and challenge lifetime.
- Define retry limits and failed-challenge consumption policy.
- Decide whether device disconnection locks or revokes the session.
- Agree on local vault restriction delivery and failure handling.
- Define authorization credentials and enrollment/pairing bootstrap.

No timeout values or retry counts are finalized by this document.

## 10. Review Record

- Desktop reviewer: Pending
- Security reviewer: Pending
- Device reviewer: Pending
- Review reference: Pending
- Decisions: Pending

BE-04 requires team review before completion.
## 11. Acceptance Scenarios for Future Implementation

These scenarios specify expected behavior.
They are not automated tests or evidence of implemented enforcement.

| Scenario | Expected result |
|---|---|
| A new session is created | Starts LOCKED; protected operations are denied |
| Authorized login starts | Fresh challenge issued; session becomes AUTH_PENDING |
| Matching device proof and policy checks succeed | Session becomes TRUSTED; vault remains separately locked |
| Matching pending challenge fails | Session becomes LOCKED; protected operations remain denied |
| Challenge expires while session remains valid | Matching pending attempt becomes LOCKED |
| Session expires during authentication | Session becomes EXPIRED; late success is rejected |
| Backend accepts a suspicious-behavior signal | Session becomes SUSPICIOUS; vault locks |
| Policy requires strong authentication | Session becomes REAUTH_REQUIRED |
| Reauthentication succeeds | Session becomes TRUSTED; last_reauth_at updates; expires_at is unchanged |
| A failed reauthentication is retried | Reauthentication context is preserved; no weaker fallback |
| A response is replayed | No access is granted and no session is restored |
| A challenge belongs to another session | Transition is rejected |
| An old failure arrives after a newer attempt succeeds | Old response does not change the current session |
| Revocation races with a successful proof | Revocation prevents restoration of access |
| Vault unlock finishes after restriction | Plaintext is not displayed; vault remains locked |
| An EXPIRED or REVOKED session receives valid proof | Session remains terminal; a new session is required |
| An unauthorized caller requests a transition | Request is rejected without changing the session |

## 12. Implementation Follow-up

Future implementation must preserve authentication-attempt context
and prevent concurrent or stale results from overriding newer decisions.

The current Session model and SessionResponse schema do not implement
these transition guards. Additional storage and API changes must be
reviewed in their implementation tasks.
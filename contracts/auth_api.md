# Authentication API Contract

Status: Draft — Pending Desktop, Device, and Security Review
API prefix: /v1
Device protocol: contracts/device_protocol.md, version 1

This document describes proposed API behavior, not implemented endpoints.
The OpenAPI specification will be maintained in auth.openapi.yaml.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | /v1/users | Create a user and begin enrollment |
| POST | /v1/devices/pair | Register a device through an authorized pairing flow |
| POST | /v1/auth/challenges | Request a login or reauthentication challenge |
| POST | /v1/auth/verify | Submit a signed device response |
| GET | /v1/sessions/{session_id} | Read an authorized session's status |
| POST | /v1/sessions/{session_id}/revoke | Revoke an authorized session |

Protected endpoints require authorization.
Knowing a user, device, or session ID does not grant access.
Pairing authorization and initial enrollment bootstrap require team review.

## Device Compatibility

Challenge and response fields must follow device_protocol.md.
Use version 1 and the purposes login and reauthentication.

The backend owns challenge expiration and consumption.
The signed response must match the authoritative stored challenge.

The backend must bind request_id to the intended authentication operation
and session. The exact mapping requires agreement with the Device team;
request_id must not be silently treated as session_id.

A verified device response alone does not decrypt the vault.

## Error Format

All API errors, including request validation errors, use:

{
  "error": {
    "code": "INVALID_SIGNATURE",
    "message": "Device authentication failed."
  }
}

The code is intended for application logic.
The message is intended for display and must not expose submitted secrets.

## Proposed Error Statuses

| HTTP | Code | Condition |
|---|---|---|
| 400 | INVALID_CHALLENGE | Structurally valid verification request references an unknown challenge |
| 401 | UNAUTHORIZED | Required authentication credentials are missing, invalid, or expired |
| 401 | EXPIRED_CHALLENGE | The stored challenge has expired according to the backend clock |
| 401 | INVALID_SIGNATURE | Device signature verification fails |
| 401 | DEVICE_MISMATCH | Response device does not match the challenge's expected device |
| 401 | REQUEST_MISMATCH | Signed version, request, user, purpose, or nonce does not match the stored challenge |
| 401 | VERIFICATION_FAILED | A valid signed response reports verified=false |
| 403 | FORBIDDEN | Authenticated caller lacks permission, ownership, or an allowed session state |
| 404 | NOT_FOUND | An authorized resource lookup finds no matching resource |
| 409 | REPLAY_DETECTED | Challenge has already been finalized or atomic consumption loses a race |
| 409 | DEVICE_ALREADY_REGISTERED | Pairing conflicts with an existing device registration |
| 422 | VALIDATION_ERROR | Request fields, types, required values, or cross-field constraints are invalid |
| 429 | RATE_LIMITED | Request or authentication attempt limit is exceeded |
| 500 | INTERNAL_ERROR | Unexpected server failure; internal details are not returned |

Malformed challenge identifiers rejected by request schema validation
produce 422, not 400.

A 401 response must include an appropriate WWW-Authenticate challenge.
The authentication scheme and challenge values require team agreement.

Authenticate and authorize callers before disclosing protected resource
existence or detailed authentication failure reasons.
Detailed device error codes are exposed only to the appropriately
authorized authentication flow.

If multiple checks fail, report the first failure in the agreed
verification sequence; do not disclose later validation results.

These mappings are proposed contract behavior and require team review.
They do not describe currently implemented authentication endpoints.

## Timestamp Contract

Every non-null timestamp must contain an explicit timezone.
Timezone-naive timestamps are rejected by the API schemas.

Backend response timestamps must be serialized in UTC.
AwareDatetime enforces timezone presence, but does not itself normalize
offsets to UTC; response construction must perform that normalization.

This applies to user creation, challenge expiration, session creation,
session expiration, revocation, and reauthentication timestamps.

## Pending Decisions

- Authorization mechanism and initial enrollment bootstrap.
- Authorized pairing, key encoding, rotation, and revocation.
- - Review the proposed backend-generated request_id binding to the session.
- Challenge lifetime and failed-attempt consumption policy.
- Session lifetime and reauthentication rules.
## User Registration

POST /v1/users

Request:
- display_name: required, trimmed string, 1–100 characters.

Successful response: HTTP 201
- user_id
- display_name
- enrollment_status
- created_at: UTC timestamp
- pairing_code: single-use bearer credential issued for the newly created user.
- pairing_code_expires_at: UTC timestamp, five minutes after issuance.

The backend stores only the pairing code hash. The registration
response includes `Cache-Control: no-store`.

Registration begins enrollment and does not create an authenticated session.

## Device Pairing

## Device Pairing

POST /v1/devices/pair

Request:
- user_id: required string, 1–36 characters.
- device_id: required string, 1–36 characters.
- public_key: 32 raw Ed25519 public key bytes encoded as unpadded Base64url.

Send the registration pairing code in the `Authorization: Bearer <code>`
header. The code must belong to the user in the request. The backend
consumes it in the same database transaction that creates the `PENDING`
device record.

Successful response: HTTP 201
- device_id
- user_id
- pairing_status

Error responses:
- 401 UNAUTHORIZED: the pairing code is missing, invalid, expired,
  previously used, or issued for a different user.
- 409 DEVICE_ALREADY_REGISTERED: the device ID already exists. The
  transaction rolls back, so the pairing code remains usable until expiry.
- 422 VALIDATION_ERROR: request fields or public key encoding are invalid.

An existing device must not be overwritten or reassigned.
Private keys and fingerprint templates are never accepted by this request.
## Device Challenge and Verification Schemas

AuthChallengeResponse follows the challenge message in device_protocol.md:
- version: integer 1
- challenge_id
- request_id
- user_id
- device_id
- purpose: login or reauthentication
- nonce
- expires_at: timezone-aware timestamp, emitted in UTC

POST /v1/auth/verify accepts AuthVerifyRequest:
- version: integer 1
- challenge_id
- device_id
- payload:
  - request_id
  - user_id
  - purpose
  - nonce
  - verified: JSON boolean
- signature

Unknown fields are rejected.
Signed string values must not be trimmed or otherwise rewritten.

Schema validation checks message structure only.
Nonce encoding and randomness, signature encoding and verification,
challenge matching, expiration, device trust, and atomic consumption
must be enforced by the authentication implementation.

The proposed challenge-creation request and verification-success response
are defined below and require team review.
## Proposed Challenge Creation Flow

POST /v1/auth/challenges

Request:
- user_id
- device_id
- purpose: login or reauthentication
- session_id: required for reauthentication, forbidden for login

Successful response: HTTP 201
- session_id
- challenge: the unchanged device challenge object

For login, the backend creates a new session without protected access.
For reauthentication, it validates the existing session and authorization.

The backend generates request_id and stores its association with the
challenge and session. Clients cannot select this binding.
This requires additional challenge storage beyond the current BE-02 model.

Only the nested challenge object is sent to the device.

## Proposed Verification Result

POST /v1/auth/verify

Successful response: HTTP 200
- session: SessionResponse

The backend returns the authoritative session state after verification
and policy evaluation. Clients must not assume a successful HTTP response
alone permits protected operations.

Session IDs are identifiers, not authentication credentials.
The credential mechanism remains pending team review.
Verification does not return vault passwords or decryption keys.

## Session Operations

GET /v1/sessions/{session_id}
- Authorized access only.
- HTTP 200 with SessionResponse.

POST /v1/sessions/{session_id}/revoke
- Authorized access only.
- HTTP 200 with the resulting SessionResponse.

Session transition and revocation behavior will be defined in BE-04.
The proposed login and reauthentication flow requires team review.
## Static Mock Responses

Examples are available in examples/auth_responses.json.

| Example | Operation |
|---|---|
| user_created | POST /v1/users |
| device_pairing | POST /v1/devices/pair |
| challenge_created | POST /v1/auth/challenges |
| authentication_verified | POST /v1/auth/verify |
| authentication_verified.session | GET /v1/sessions/{session_id} |
| session_revoked | POST /v1/sessions/{session_id}/revoke |
| authentication_error | Authentication error response |

These are independent UI/integration fixtures, not a complete sequential flow.
Timestamps are fixed examples; no example challenge is valid for real use.
The nonce is an explicit placeholder, not cryptographically random data.
Examples do not provide authentication credentials or unlock the vault.

PENDING pairing does not authorize the device.
TRUSTED is an illustrative session state, subject to BE-04 review.
These fixtures must not be connected to production authorization decisions.

## Regenerating OpenAPI

Run from the repository root:

python -m scripts.export_auth_openapi

Regenerate auth.openapi.yaml after changing API schemas or endpoint definitions.
## Contract Tests

Run from the repository root:

```powershell
python -m pytest tests/unit/test_auth_schemas.py tests/unit/test_auth_examples.py tests/unit/test_auth_openapi.py -v
```

Tests cover schema validation, static response examples, and resolution
of internal OpenAPI schema references. They do not verify implemented
authentication endpoints or full OpenAPI standards compliance.
## Signed Response and Session Binding

This section clarifies the proposed verification contract.
It does not implement backend signature verification.

### Signature Scope

The signature covers the complete response envelope except signature:

{
  "version": 1,
  "challenge_id": "...",
  "device_id": "...",
  "payload": {
    "request_id": "...",
    "user_id": "...",
    "purpose": "login",
    "nonce": "...",
    "verified": true
  }
}

Signing only the nested payload is not compliant with this contract.

The signed bytes must follow device_protocol.md:

b"DEVICE_AUTH_V1\x00" + canonical_json_bytes

Canonical JSON uses sorted keys, compact separators, UTF-8 encoding,
and Python's default ASCII escaping behavior.

### Authoritative Backend Binding

Before issuing a challenge, the backend must persist its association with:
- challenge_id
- protocol version
- device_id
- user_id
- request_id
- session_id
- purpose
- nonce or its verification representation
- expiration and consumption state

session_id is not currently a field in the signed device response.
Its binding is indirect, through the authoritative stored challenge.
This storage requirement extends the current BE-02 challenge model.

### Verification Requirements

1. Validate the response structure.
2. Use challenge_id only to locate the authoritative stored challenge;
   locating a record does not authorize an operation.
3. Load the expected device and public key from trusted backend records,
   never from a public key supplied with the verification request.
4. Verify the signature over the complete response envelope.
5. Match version, challenge_id, device_id, request_id, user_id, purpose,
   and nonce against the stored challenge.
6. Resolve session_id from the stored challenge and validate session
   ownership, intended operation, permitted state, and expiration.
7. Enforce device trust/revocation and challenge expiration.
8. Atomically finalize the challenge according to the agreed consumption
   policy; authentication must not succeed if consumption fails.
9. Grant authentication only for a signed verified=true result and
   successful completion of all required policy checks.

No session may be selected or replaced using an unbound client field.
A client-provided request_id must not override the stored session binding.

Changing challenge_id or device_id changes the signed message.
Replacing the stored association or using an unrelated session must
also be rejected by backend context checks.

Signature validity alone does not authorize a session transition.
The detailed failed-attempt consumption policy remains pending review.
## Session State Policy

The proposed session lifecycle, protected-operation permissions,
transition guards, expiration, and reauthentication rules are defined in
[BE-04 Session State Machine](../docs/session-state-machine.md).

This policy is pending team review.
Session state changes are backend-controlled.
TRUSTED alone does not unlock the encrypted vault.
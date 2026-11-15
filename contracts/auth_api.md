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

| HTTP status | Code |
|---|---|
| 422 | VALIDATION_ERROR |
| 401 | UNAUTHORIZED |
| 403 | FORBIDDEN |
| 404 | NOT_FOUND |
| 400 | INVALID_CHALLENGE |
| 401 | EXPIRED_CHALLENGE |
| 409 | REPLAY_DETECTED |
| 401 | INVALID_SIGNATURE |
| 401 | DEVICE_MISMATCH |
| 401 | REQUEST_MISMATCH |
| 401 | VERIFICATION_FAILED |
| 429 | RATE_LIMITED |
| 500 | INTERNAL_ERROR |

These mappings require team review.
Detailed authentication errors must not disclose unauthorized resource
information. Internal exceptions and submitted authentication payloads
must not be returned to clients.

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

Registration begins enrollment and does not create an authenticated session.

## Device Pairing

POST /v1/devices/pair

Request:
- user_id: required string, 1–36 characters.
- device_id: required string, 1–36 characters.
- public_key: required, non-empty string.

Successful response: HTTP 201
- device_id
- user_id
- pairing_status

Request validation alone does not authorize pairing.
The backend must verify pairing authorization and user ownership.
The initial pairing bootstrap and public key encoding require team review.
An existing device must not be silently overwritten or reassigned.
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
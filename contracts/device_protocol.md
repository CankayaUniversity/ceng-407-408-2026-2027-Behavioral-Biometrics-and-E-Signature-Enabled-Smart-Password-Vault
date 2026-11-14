# Device Protocol Specification

## DEV-04 — Secure Challenge-Response Protocol

**Status:** Draft — Pending Backend and Security Review  
**Version:** 1  
**Owner:** Member 4 — Device Protocol

## 1. Overview

This document defines the proposed challenge-response protocol between the fingerprint device simulator and the backend authentication service.

The protocol uses Ed25519 digital signatures to authenticate device responses and binds each response to a specific authentication request.

The fingerprint device is simulated. No real biometric templates are collected or transmitted.

## 2. Protocol Participants

**Backend Authentication Service**
- Generates authentication challenges.
- Maintains challenge state.
- Stores registered device public keys.
- Verifies device signatures and request bindings.
- Enforces expiration and replay prevention.

**Fingerprint Device Simulator**
- Receives authentication challenges.
- Simulates fingerprint verification.
- Constructs signed authentication responses.
- Uses its Ed25519 private key to sign response messages.

## 3. Challenge Message

The backend generates a challenge with the following structure:

```json
{
  "version": 1,
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "login-request-123",
  "user_id": "user_01",
  "device_id": "device_01",
  "purpose": "login",
  "nonce": "base64url-encoded-32-random-bytes",
  "expires_at": "2026-11-14T19:00:30Z"
}
```

### Challenge Fields

| Field | Description |
|---|---|
| version | Protocol version |
| challenge_id | Unique identifier for the challenge |
| request_id | Identifier of the original authentication request |
| user_id | User being authenticated |
| device_id | Expected authentication device |
| purpose | Authentication operation, such as `login` or `reauthentication` |
| nonce | Cryptographically secure random value |
| expires_at | Challenge expiration timestamp in UTC |

### Challenge Rules

- Each challenge must have a unique identifier.
- The nonce must contain at least 128 bits of cryptographically secure randomness. The proposed implementation uses 256 bits.
- A challenge is valid for a proposed maximum of 60 seconds.
- A challenge is associated with one user, device, request, and purpose.
- The backend must maintain authoritative challenge state.
- Challenge expiration must be enforced using the backend clock.
- Each challenge is single-use.

## 4. Authentication Response

After simulated fingerprint verification, the device constructs a response:

```json
{
  "version": 1,
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "device_01",
  "payload": {
    "request_id": "login-request-123",
    "user_id": "user_01",
    "purpose": "login",
    "nonce": "base64url-encoded-32-random-bytes",
    "verified": true
  },
  "signature": "base64url-encoded-ed25519-signature"
}
```

The signature covers the complete response except the signature field itself, using a deterministic serialization format.

The signed data includes:

- Protocol version
- Challenge ID
- Device ID
- Request ID
- User ID
- Authentication purpose
- Challenge nonce
- Fingerprint verification result

The response must match the original challenge stored by the backend.

## 5. Message Signing

The device signs the canonical representation of the response payload using its Ed25519 private key.

The backend verifies the signature using the public key previously registered for the corresponding device.

**Serialization requirement:** Both components must use exactly the same canonical byte representation before signing or verification.

For the prototype, the proposed representation is UTF-8 JSON with:

- Sorted object keys
- No unnecessary whitespace
- Fixed field names and value types
- No floating-point values in signed fields

The signature is encoded using unpadded Base64url.

Implementations must not sign one representation and verify another.

### Signed Message Format

The Ed25519 signature is calculated over the following byte sequence:

`b"DEVICE_AUTH_V1\x00" + canonical_json_bytes`

The canonical JSON object contains:

- `version`
- `challenge_id`
- `device_id`
- `payload`

The `signature` field is excluded.

For the prototype, JSON serialization uses UTF-8 encoding, sorted keys, compact separators (`","` and `":"`), and Python's default JSON ASCII escaping behavior.

The signature is encoded using unpadded Base64url.

The `DEVICE_AUTH_V1` prefix provides domain separation to distinguish device authentication signatures from signatures used for other purposes.

Both the device and backend must use the exact same serialization rules. The production contract should specify language-independent canonicalization before cross-language integration.

## 6. Backend Verification Workflow

The backend must perform the following checks:

1. Validate the response structure and protocol version.
2. Locate the stored challenge using `challenge_id`.
3. Confirm the challenge exists and is pending.
4. Verify that the challenge has not expired.
5. Verify that the response matches the stored user, device, request, purpose, and nonce.
6. Retrieve the trusted registered public key for the expected device.
7. Verify the Ed25519 signature over the canonical response data.
8. Atomically consume the challenge so it cannot be reused.
9. Accept authentication only if the signed verification result is `true` and all other authentication policies are satisfied.

If any validation fails, authentication must be rejected.

A failed verification attempt must not allow the same challenge to be retried indefinitely. The backend should atomically finalize or consume a submitted challenge under a documented retry policy.

## 7. Replay Prevention

Replay attacks are prevented through a combination of:

- Unique challenge identifiers.
- Cryptographically random nonces.
- Short expiration periods.
- Backend-controlled challenge state.
- Single-use challenge consumption.
- Atomic state transitions.
- Binding signed responses to the original authentication request.

A previously accepted response must not be accepted again.

Challenge consumption must be concurrency-safe to prevent two simultaneous requests from successfully using the same challenge.

## 8. Error Handling

The proposed backend error categories are:

| Error | Meaning |
|---|---|
| INVALID_CHALLENGE | Challenge does not exist or is malformed |
| EXPIRED_CHALLENGE | Challenge validity period has ended |
| REPLAY_DETECTED | Challenge has already been consumed |
| INVALID_SIGNATURE | Signature verification failed |
| DEVICE_MISMATCH | Response does not match the registered device |
| REQUEST_MISMATCH | Response fields do not match the original request |
| VERIFICATION_FAILED | Simulated fingerprint verification was unsuccessful |

Error messages must not disclose private keys, biometric material, or other sensitive authentication details.

The exact HTTP status codes and response schemas remain to be agreed with Member 2.

## 9. Security Assumptions and Limitations

- The device private key is assumed to remain secret.
- The backend must already possess an authenticated association between user, device, and public key.
- A valid Ed25519 signature proves possession of the corresponding private key, not a real biometric match.
- The current software simulator does not provide hardware-backed key protection.
- Public key registration and device pairing are separate protocol requirements.
- Secure transport is required when communication extends beyond trusted local development.
- Authentication success must not directly unlock encrypted vault contents without the agreed vault key policy.
- Replay prevention is enforced by the backend, not solely by the signature algorithm.

## 10. Integration Responsibilities

| Responsibility | Owner |
|---|---|
| Device response model and signing | Member 4 |
| Challenge generation and storage | Member 2 |
| Signature verification integration | Members 2 and 4 |
| Private key security review | Members 3 and 4 |
| Device registration and pairing | Members 2 and 4 |
| Authentication and vault access policy | All members |

## 11. Open Decisions for Review

The following decisions require confirmation before implementation:

1. Final challenge expiration duration.
2. Canonical message serialization and signature domain separation.
3. Final JSON schemas and backend endpoint paths.
4. Challenge consumption behavior on failed responses.
5. Device public key registration and rotation policies.
6. Device-to-user association and device revocation.
7. Error response format and HTTP status codes.
8. Login versus re-authentication policy differences.

## 12. Planned Implementation

- DEV-06: Implement signed authentication responses.
- DEV-07: Test invalid signatures and replay protection.
- DEV-08: Connect the simulator to the backend.
- DEV-10: Support fresh re-authentication challenges.
- DEV-14: Test forged responses, replay attacks, and device mismatches.
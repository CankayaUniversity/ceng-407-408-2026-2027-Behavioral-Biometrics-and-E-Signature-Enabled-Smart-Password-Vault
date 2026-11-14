# Fingerprint Enrollment and Finger Slot Model

## Overview

This module defines the fingerprint enrollment data model used by the simulated fingerprint authentication device.

It supports user-specific finger slot registration, enrollment lookup, removal, and three-finger sequence representation.

No real fingerprint images or biometric templates are collected or stored.

## Finger Slots

The `FingerSlot` enumeration defines ten positions:

- Left hand: thumb, index, middle, ring, little
- Right hand: thumb, index, middle, ring, little

## Enrollment

`FingerprintEnrollment` represents a simulated fingerprint registration for a specific user and finger slot.

`FingerprintEnrollmentManager` provides:

- `enroll(user_id, finger_slot)` — Register a finger slot.
- `is_enrolled(user_id, finger_slot)` — Check whether a finger slot is registered.
- `remove(user_id, finger_slot)` — Remove an enrollment.
- `get_enrolled_fingers(user_id)` — Retrieve registered finger slots.

Duplicate enrollments for the same user and finger slot are rejected.

Enrollment data is currently stored in memory and is not persistent.

## Verification

`MockFingerprintDevice` supports finger-specific enrollment and verification through `enroll_finger()` and `verify_finger()`.

A simulated verification succeeds only when the user is registered, the specified finger slot is enrolled, and `scan_success=True`.

The existing DEV-01 interface remains available for backward compatibility.

## Three-Finger Sequence

`FingerprintSequence` stores an ordered tuple containing exactly three finger slots.

The model represents a sequence but does not perform sequence-based authentication. Sequence verification will be implemented in DEV-11.

## Security Limitations

- No real biometric matching is performed.
- Enrollment records are simulated and held in memory.
- The `scan_success` parameter is a test input, not a trusted authentication result.
- The current module does not generate cryptographic authentication proofs.
- Signed authentication responses and replay protection are separate development tasks.

## Testing

Run the following command from the repository root:

```bash
python -m pytest tests/unit/test_mock_device.py tests/unit/test_fingerprint_model.py -v
```

The DEV-01 and DEV-02 test suites passed together with 20 successful tests on November 14, 2026.
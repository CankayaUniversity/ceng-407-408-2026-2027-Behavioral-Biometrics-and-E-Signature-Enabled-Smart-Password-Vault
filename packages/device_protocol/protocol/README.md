# DEV-03 — Ed25519 Digital Signature Prototype

## Overview

This module implements Ed25519 digital signatures for the fingerprint device simulator.

It provides key generation, message signing, signature verification, and public key export.

## Features

- Generate Ed25519 public/private key pairs.
- Sign messages using the private key.
- Verify signatures using the public key.
- Reject modified messages and invalid signatures.
- Export public keys in raw 32-byte format.

## Private Key Handling

- A new private key is generated when a `DeviceSigner` instance is created.
- The private key is stored only in application memory.
- Private keys are not saved to disk.
- Only public keys are exported.
- Keys are not persistent across application restarts.

## Security Limitations

This module is a proof of concept, not a production-ready device authentication system.

A valid digital signature proves possession of the corresponding private key but does not prove that a genuine fingerprint scan occurred.

Device pairing, secure key storage, challenge-response authentication, expiration, and replay protection are not implemented in DEV-03.

## Testing

Run from the repository root:

`python -m pytest tests/unit/test_device_signing.py -v`

The tests cover valid signatures, modified messages, invalid signatures, corrupted signatures, and public key export.
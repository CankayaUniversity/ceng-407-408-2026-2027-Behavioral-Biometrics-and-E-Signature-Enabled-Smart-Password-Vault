
from packages.device_protocol.protocol.signing import DeviceSigner

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def test_valid_signature():
    signer = DeviceSigner()
    message = b"fingerprint_verified"

    signature = signer.sign(message)

    assert DeviceSigner.verify(
        signer.get_public_key(), message, signature
    ) is True


def test_modified_message():
    signer = DeviceSigner()

    signature = signer.sign(b"authentication_success")

    assert DeviceSigner.verify(
        signer.get_public_key(),
        b"authentication_failed",
        signature,
    ) is False


def test_invalid_signature():
    signer = DeviceSigner()
    other_signer = DeviceSigner()

    message = b"authentication_success"
    signature = other_signer.sign(message)

    assert DeviceSigner.verify(
        signer.get_public_key(), message, signature
    ) is False


def test_corrupted_signature():
    signer = DeviceSigner()
    message = b"authentication_success"

    signature = bytearray(signer.sign(message))
    signature[0] ^= 1

    assert DeviceSigner.verify(
        signer.get_public_key(),
        message,
        bytes(signature),
    ) is False


def test_export_public_key():
    signer = DeviceSigner()

    public_key_bytes = signer.export_public_key()

    assert len(public_key_bytes) == 32

    restored_key = Ed25519PublicKey.from_public_bytes(
        public_key_bytes
    )

    message = b"fingerprint_verified"
    signature = signer.sign(message)

    assert DeviceSigner.verify(
        restored_key,
        message,
        signature
    ) is True    

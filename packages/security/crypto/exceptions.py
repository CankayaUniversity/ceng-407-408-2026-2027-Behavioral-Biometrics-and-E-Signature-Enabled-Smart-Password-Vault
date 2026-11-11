"""Public cryptography errors for the security package."""


class DecryptionError(Exception):
    """Authenticated decryption failed; ciphertext or key may be invalid."""

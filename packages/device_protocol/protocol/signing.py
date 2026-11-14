
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


class DeviceSigner:
    def __init__(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def sign(self, message: bytes) -> bytes:
        return self.private_key.sign(message)

    def get_public_key(self) -> Ed25519PublicKey:
        return self.public_key

    def export_public_key(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @staticmethod
    def verify(
        public_key: Ed25519PublicKey,
        message: bytes,
        signature: bytes,
    ) -> bool:
        try:
            public_key.verify(signature, message)
            return True
        except InvalidSignature:
            return False

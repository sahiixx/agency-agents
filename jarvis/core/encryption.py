"""Encryption helpers."""

from __future__ import annotations

import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionService:
    """AES-256-GCM encryption/decryption service."""

    def __init__(self, key: bytes | None = None) -> None:
        self.key = key or AESGCM.generate_key(bit_length=256)
        self._aead = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        encrypted = self._aead.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + encrypted).decode("utf-8")

    def decrypt(self, blob: str) -> str:
        decoded = base64.b64decode(blob)
        nonce, ciphertext = decoded[:12], decoded[12:]
        return self._aead.decrypt(nonce, ciphertext, None).decode("utf-8")

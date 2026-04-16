"""Encryption helpers for sensitive data."""

from __future__ import annotations

from pathlib import Path

try:
    from cryptography.fernet import Fernet  # type: ignore
except Exception:  # pragma: no cover
    Fernet = None


class EncryptionVault:
    def __init__(self, key_file: str = "jarvis.key"):
        self.key_file = Path(key_file)
        if Fernet is None:
            self.fernet = None
            return
        key = self._load_or_create_key()
        self.fernet = Fernet(key)

    def _load_or_create_key(self) -> bytes:
        if self.key_file.exists():
            return self.key_file.read_bytes()
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        return key

    def encrypt(self, text: str) -> bytes:
        if self.fernet is None:
            raise RuntimeError("Install cryptography for encryption: pip install cryptography")
        return self.fernet.encrypt(text.encode("utf-8"))

    def decrypt(self, token: bytes) -> str:
        if self.fernet is None:
            raise RuntimeError("Install cryptography for encryption: pip install cryptography")
        return self.fernet.decrypt(token).decode("utf-8")

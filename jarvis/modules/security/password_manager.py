"""Encrypted password vault."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from jarvis.core.encryption import EncryptionService


class PasswordManager:
    """AES-256 encrypted password storage with local vault file."""

    def __init__(self, vault_path: str = "~/.jarvis/passwords.vault", key: bytes | None = None) -> None:
        self.vault_path = Path(vault_path).expanduser()
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path = self.vault_path.with_suffix(".key")
        key_bytes = key or self._load_or_create_key()
        self.crypto = EncryptionService(key=key_bytes)
        if not self.vault_path.exists():
            self.vault_path.write_text(self.crypto.encrypt("{}"), encoding="utf-8")

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return base64.b64decode(self.key_path.read_text(encoding="utf-8"))
        key = EncryptionService().key
        self.key_path.write_text(base64.b64encode(key).decode("utf-8"), encoding="utf-8")
        return key

    def _read(self) -> dict[str, str]:
        encrypted = self.vault_path.read_text(encoding="utf-8")
        return json.loads(self.crypto.decrypt(encrypted))

    def _write(self, values: dict[str, str]) -> None:
        self.vault_path.write_text(self.crypto.encrypt(json.dumps(values)), encoding="utf-8")

    def save_password(self, service: str, password: str) -> None:
        values = self._read()
        values[service.lower()] = password
        self._write(values)

    def get_password(self, service: str) -> str | None:
        return self._read().get(service.lower())

    def generate_password(self, length: int = 20) -> str:
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        return "".join(secrets.choice(alphabet) for _ in range(length))

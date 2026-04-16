from jarvis.core.encryption import EncryptionService


def test_encrypt_decrypt_roundtrip() -> None:
    service = EncryptionService()
    blob = service.encrypt("jarvis")
    assert service.decrypt(blob) == "jarvis"

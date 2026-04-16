from jarvis.modules.security.password_manager import PasswordManager


def test_password_vault_roundtrip(tmp_path) -> None:
    manager = PasswordManager(vault_path=str(tmp_path / "vault.enc"))
    manager.save_password("github", "secret123")
    assert manager.get_password("github") == "secret123"

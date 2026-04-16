from jarvis.core.system_control import SystemControl


def test_lock_command_is_non_empty() -> None:
    assert SystemControl().lock_command()

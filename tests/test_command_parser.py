from jarvis.core.command_parser import CommandParser


def test_parse_add_task_command() -> None:
    parsed = CommandParser().parse("JARVIS, add task: buy groceries")
    assert parsed.action == "todo.add"
    assert parsed.payload == "buy groceries"

from jarvis.modules.productivity.todo_manager import TodoManager


def test_todo_add_and_mark_done(tmp_path) -> None:
    manager = TodoManager(db_path=str(tmp_path / "todo.db"))
    task_id = manager.add_task("buy milk", "high")
    manager.mark_done(task_id)
    tasks = manager.list_tasks()
    assert tasks[0]["done"] is True

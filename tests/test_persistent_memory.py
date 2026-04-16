from jarvis.modules.ai.persistent_memory import PersistentMemory


def test_persistent_memory_remember_and_recall(tmp_path) -> None:
    mem = PersistentMemory(db_path=str(tmp_path / "memory.db"))
    mem.remember("favorite_color", "blue")
    assert mem.recall("favorite_color") == "blue"

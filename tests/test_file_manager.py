from jarvis.core.file_manager import FileManager


def test_create_text_file(tmp_path) -> None:
    target = FileManager().create_text_file(str(tmp_path / "note.txt"), "hello")
    assert target.read_text(encoding="utf-8") == "hello"

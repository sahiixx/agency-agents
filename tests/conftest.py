from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "jarvis.db")

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest


@pytest.fixture()
def tmp_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "jarvis.db")

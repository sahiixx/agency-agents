"""File and folder management operations."""

from __future__ import annotations

import shutil
from pathlib import Path


class FileManager:
    """Create, delete, move, copy, and search files."""

    def create(self, path: str, is_dir: bool = False) -> str:
        try:
            target = Path(path).expanduser()
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch(exist_ok=True)
            return f"Created {'directory' if is_dir else 'file'} at {target}."
        except Exception as exc:
            return f"Create failed: {exc}"

    def delete(self, path: str) -> str:
        try:
            target = Path(path).expanduser()
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            else:
                return f"Path not found: {target}"
            return f"Deleted {target}."
        except Exception as exc:
            return f"Delete failed: {exc}"

    def move(self, src: str, dst: str) -> str:
        try:
            result = shutil.move(str(Path(src).expanduser()), str(Path(dst).expanduser()))
            return f"Moved to {result}."
        except Exception as exc:
            return f"Move failed: {exc}"

    def copy(self, src: str, dst: str) -> str:
        try:
            src_path = Path(src).expanduser()
            dst_path = Path(dst).expanduser()
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            return f"Copied {src_path} to {dst_path}."
        except Exception as exc:
            return f"Copy failed: {exc}"

    def search(self, root: str, name: str, limit: int = 25) -> list[str]:
        """Search for files/folders by name pattern."""
        results = []
        try:
            for path in Path(root).expanduser().rglob(f"*{name}*"):
                results.append(str(path))
                if len(results) >= limit:
                    break
        except Exception:
            return []
        return results

"""Hot-loadable plugin manager."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .plugin_base import PluginBase


class PluginManager:
    def __init__(self, plugin_dir: str = "jarvis/plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: dict[str, PluginBase] = {}
        self.enabled: set[str] = set()

    def discover(self):
        if not self.plugin_dir.exists():
            return []
        discovered = []
        for path in self.plugin_dir.glob("*.py"):
            if path.name.startswith("__") or path.name in {"plugin_base.py", "plugin_manager.py"}:
                continue
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for value in module.__dict__.values():
                if isinstance(value, type) and issubclass(value, PluginBase) and value is not PluginBase:
                    plugin = value()
                    self.plugins[plugin.name] = plugin
                    discovered.append(plugin.name)
        return discovered

    def list_plugins(self):
        return sorted(self.plugins.keys())

    def enable(self, name: str) -> bool:
        if name in self.plugins:
            self.enabled.add(name)
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self.enabled:
            self.enabled.remove(name)
            return True
        return False

    def run(self, name: str, command: str) -> str:
        if name not in self.enabled:
            return "Plugin disabled"
        return self.plugins[name].execute(command)

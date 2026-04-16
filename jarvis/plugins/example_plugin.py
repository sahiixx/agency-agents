"""Example plugin implementation."""

try:
    from jarvis.plugins.plugin_base import PluginBase
except Exception:  # pragma: no cover
    from .plugin_base import PluginBase


class ExamplePlugin(PluginBase):
    name = "example"

    def execute(self, command: str) -> str:
        return f"Example plugin executed: {command}"

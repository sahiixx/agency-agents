from jarvis.core.plugin_system import PluginSystem


def test_plugin_system_register_and_run() -> None:
    plugins = PluginSystem()
    plugins.register("ping", lambda: "pong")
    assert plugins.run("ping") == "pong"

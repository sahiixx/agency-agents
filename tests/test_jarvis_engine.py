"""Regression coverage for the installed engine without devices or providers."""

import logging
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from jarvis.core.command_parser import CommandParser
from jarvis.core.engine import JarvisEngine
from jarvis.modules.ai_brain import AIResponse
from jarvis.modules.calculator import Calculator
from jarvis.operator import JarvisOperator


@pytest.fixture
def engine():
    # Bypass device initialization; exercise the real parser and command dispatch.
    instance = JarvisEngine.__new__(JarvisEngine)
    instance.logger = logging.getLogger("jarvis.engine.test")
    instance.parser = CommandParser()
    instance.calc = Calculator()
    instance.responses = {"unknown": ["Unknown command."]}
    instance.weather = SimpleNamespace(current_weather=Mock(return_value="Sunny."))
    instance.voice_out = SimpleNamespace(say=Mock())
    return instance


def test_installed_entrypoint_imports_engine(tmp_path):
    # Isolated mode excludes cwd/PYTHONPATH and the smoke suite's sys.path hacks.
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "from jarvis.core.engine import JarvisEngine; "
                "from jarvis.main import JarvisEngine as entrypoint_engine; "
                "assert entrypoint_engine is JarvisEngine"
            ),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_engine_dispatches_calculator(engine):
    assert engine.execute_command("calculate 2 + 3 * 4") == "The result is 14."


def test_engine_extracts_weather_city(engine):
    assert engine.execute_command("what's the weather in Dubai") == "Sunny."
    engine.weather.current_weather.assert_called_once_with("dubai")


def test_engine_returns_unknown_response(engine):
    assert engine.execute_command("zzzzzzzzzzzzzzzzzz") == "Unknown command."


def test_engine_logs_dispatch_failure_and_keeps_running(engine, caplog):
    engine.weather.current_weather.side_effect = RuntimeError("offline test")
    response = engine.execute_command("weather in Dubai")
    assert "internal error" in response
    assert "Command execution failed" in caplog.text
    assert "RuntimeError: offline test" in caplog.text
    assert engine.execute_command("calculate 2 + 2") == "The result is 4."


def test_engine_responds_via_output_layer(engine):
    engine.respond("Hello.")
    engine.voice_out.say.assert_called_once_with("Hello.")


def test_operator_reads_ai_response_text_without_dispatching(monkeypatch):
    operator = JarvisOperator.__new__(JarvisOperator)
    operator.allow_live = False
    operator._brain = SimpleNamespace(ask=Mock(return_value=AIResponse("exit", "fallback")))
    run_mission = Mock()
    monkeypatch.setattr("jarvis.operator.import_module", lambda name: SimpleNamespace(run_mission=run_mission))
    operator.capture_and_dispatch()
    operator._brain.ask.assert_called_once()
    run_mission.assert_not_called()

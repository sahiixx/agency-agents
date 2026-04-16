from jarvis.core.calculator import Calculator
import pytest


def test_calculator_evaluate() -> None:
    assert Calculator().evaluate("2 + 3 * 4") == 14.0


def test_calculator_rejects_division_by_zero() -> None:
    with pytest.raises(ValueError, match="Division by zero"):
        Calculator().evaluate("5 / 0")

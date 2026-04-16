from jarvis.core.calculator import Calculator


def test_calculator_evaluate() -> None:
    assert Calculator().evaluate("2 + 3 * 4") == 14.0

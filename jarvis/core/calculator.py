"""Safe calculator helpers for spoken math."""

from __future__ import annotations


class Calculator:
    """Tiny arithmetic evaluator limited to +,-,*,/."""

    def evaluate(self, expression: str) -> float:
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            raise ValueError("Expression contains unsupported characters")
        return float(eval(expression, {"__builtins__": {}}, {}))

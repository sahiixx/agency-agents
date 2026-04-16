"""Safe expression calculator module."""

from __future__ import annotations

import ast
import operator


_ALLOWED = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


class Calculator:
    """Evaluate simple math expressions safely."""

    def evaluate(self, expression: str) -> str:
        try:
            value = self._eval(ast.parse(expression, mode="eval").body)
            return f"The result is {value}."
        except Exception as exc:
            return f"Calculation failed: {exc}"

    def _eval(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
            return _ALLOWED[type(node.op)](self._eval(node.left), self._eval(node.right))
        raise ValueError("Unsupported expression")

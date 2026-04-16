"""Safe calculator helpers for spoken math."""

from __future__ import annotations

import ast


class Calculator:
    """Tiny arithmetic evaluator limited to +,-,*,/."""

    def evaluate(self, expression: str) -> float:
        tree = ast.parse(expression, mode="eval")
        return float(self._eval_node(tree.body))

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ValueError("Division by zero is not allowed")
                return left / right
            raise ValueError("Unsupported arithmetic operator")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = self._eval_node(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError("Unsupported expression")

"""Restricted expression evaluation for user-defined data columns."""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable, Mapping
from typing import Any


class UnsafeExpressionError(ValueError):
    """Raised when an expression uses syntax outside the supported subset."""


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def evaluate_math_expression(
    expression: str,
    *,
    variables: Mapping[str, Any],
    functions: Mapping[str, Callable[..., Any]],
    constants: Mapping[str, Any] | None = None,
    max_length: int = 1_000,
    max_nodes: int = 200,
) -> Any:
    """Evaluate a numeric expression without exposing Python built-ins or attributes."""

    if not expression.strip():
        raise UnsafeExpressionError("Expression cannot be empty.")
    if len(expression) > max_length:
        raise UnsafeExpressionError(f"Expression exceeds the {max_length}-character limit.")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"Invalid expression syntax: {exc.msg}.") from exc

    if sum(1 for _ in ast.walk(tree)) > max_nodes:
        raise UnsafeExpressionError("Expression is too complex.")

    available_constants = constants or {}

    def evaluate(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            raise UnsafeExpressionError("Only numeric literals are allowed.")
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            if node.id in available_constants:
                return available_constants[node.id]
            raise UnsafeExpressionError(f"Unknown name: {node.id}.")
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Pow):
                if not isinstance(right, (int, float)) or isinstance(right, bool):
                    raise UnsafeExpressionError("Exponents must be numeric literals.")
                if abs(right) > 100:
                    raise UnsafeExpressionError("Exponent magnitude cannot exceed 100.")
            return _BINARY_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in functions:
                raise UnsafeExpressionError("Only approved mathematical functions may be called.")
            if any(keyword.arg is None for keyword in node.keywords):
                raise UnsafeExpressionError("Expanded keyword arguments are not allowed.")
            args = [evaluate(argument) for argument in node.args]
            kwargs = {keyword.arg: evaluate(keyword.value) for keyword in node.keywords}
            return functions[node.func.id](*args, **kwargs)
        raise UnsafeExpressionError(f"Unsupported expression syntax: {type(node).__name__}.")

    return evaluate(tree)

from __future__ import annotations

import unittest

import numpy as np

from hps.core.expressions import UnsafeExpressionError, evaluate_math_expression


class ExpressionEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.variables = {"energy": np.array([1.0, 4.0, 9.0])}
        self.functions = {"sqrt": np.sqrt, "log": np.log}
        self.constants = {"pi": np.pi}

    def evaluate(self, expression: str):
        return evaluate_math_expression(
            expression,
            variables=self.variables,
            functions=self.functions,
            constants=self.constants,
        )

    def test_evaluates_vectorized_math(self) -> None:
        result = self.evaluate("sqrt(energy) + pi")
        self.assertTrue(np.allclose(result, np.array([1.0, 2.0, 3.0]) + np.pi))

    def test_rejects_import_and_attribute_access(self) -> None:
        for expression in (
            "__import__('os').system('id')",
            "energy.__class__",
            "np.load('/tmp/file')",
        ):
            with self.subTest(expression=expression):
                with self.assertRaises(UnsafeExpressionError):
                    self.evaluate(expression)

    def test_rejects_comprehensions_and_strings(self) -> None:
        with self.assertRaises(UnsafeExpressionError):
            self.evaluate("[value for value in energy]")
        with self.assertRaises(UnsafeExpressionError):
            self.evaluate("'unsafe'")

    def test_limits_exponents(self) -> None:
        self.assertTrue(np.array_equal(self.evaluate("energy ** 2"), self.variables["energy"] ** 2))
        with self.assertRaisesRegex(UnsafeExpressionError, "Exponent magnitude"):
            self.evaluate("9 ** 999999")
        with self.assertRaisesRegex(UnsafeExpressionError, "numeric literals"):
            self.evaluate("energy ** energy")

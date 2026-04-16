"""Calculator tool — evaluates mathematical expressions safely."""

from __future__ import annotations

import math
import logging
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CalculatorInput(BaseModel):
    """Input schema for the calculator tool."""
    expression: str = Field(
        description="Mathematical expression to evaluate (e.g. '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)')"
    )


# Safe builtins for math evaluation
_SAFE_MATH_GLOBALS = {
    "__builtins__": {},
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "int": int,
    "float": float,
    # Math module functions
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "ceil": math.ceil,
    "floor": math.floor,
    "pi": math.pi,
    "e": math.e,
}


class CalculatorTool(BaseTool):
    """Evaluate mathematical expressions.

    Use this tool when you need to perform calculations, evaluate
    mathematical formulas, or do arithmetic. Supports basic operations
    (+, -, *, /, **) and math functions (sqrt, sin, cos, log, etc.).
    """

    name: str = "calculator"
    description: str = (
        "Evaluate a mathematical expression. Use when you need to perform "
        "calculations or arithmetic. Supports: +, -, *, /, **, sqrt, sin, "
        "cos, tan, log, log10, log2, ceil, floor, pi, e."
    )
    args_schema: Type[BaseModel] = CalculatorInput

    def _run(self, expression: str) -> str:
        """Evaluate the expression and return the result as a string."""
        logger.info("Calculator evaluating: %s", expression)
        try:
            result = eval(expression, _SAFE_MATH_GLOBALS, {})
            return str(result)
        except Exception as e:
            error_msg = f"Error evaluating '{expression}': {e}"
            logger.error(error_msg)
            return error_msg

    async def _arun(self, expression: str) -> str:
        """Async version — delegates to sync (CPU-bound)."""
        return self._run(expression)

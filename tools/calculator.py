"""Deterministic arithmetic for Zoey.

Basic arithmetic must never depend on the LLM: it is evaluated here
with Python's own `ast` evaluator over a strict whitelist of nodes.
Anything that is not a plain arithmetic expression is rejected, so
this module can never execute arbitrary code.

Accepted input is human arithmetic, e.g.:

    "2500000 / 85000"
    "₹25,00,000 ÷ ₹85,000"
    "what is (12 + 8) * 3?"

Currency symbols, thousands separators (commas), unicode operators
(÷ × −) and common question wrappers are normalized away before
evaluation.
"""

import ast
import operator
import re


_MAX_ABS_EXPONENT = 1000

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Characters that may appear in an arithmetic question BEFORE
# normalization. Anything else is rejected outright.
_ALLOWED_CHARACTERS = re.compile(
    r"^[\d\s\.\,\+\-\*\/\(\)\%\^×÷−–—=₹$€£¥]*$"
)

# Question wrappers stripped from both ends. Longest first so
# "how much is" wins over shorter overlapping prefixes.
_LEADING_PATTERNS = (
    "please calculate",
    "please compute",
    "please solve",
    "how much is",
    "calculate",
    "compute",
    "evaluate",
    "solve",
    "what is",
    "what's",
    "whats",
)

_TRAILING_CHARACTERS = "=?.! \t\r\n"


def normalize_expression(text: str):
    """Strip question wording, currency symbols and thousands
    separators, and map unicode operators onto ASCII ones.

    Returns the cleaned expression or None when the text cannot be
    a pure arithmetic expression at all."""

    if not isinstance(text, str):
        return None

    candidate = text.strip().lower()

    if not candidate:
        return None

    for prefix in _LEADING_PATTERNS:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):].strip()
            break

    candidate = candidate.strip(_TRAILING_CHARACTERS).strip()

    if not _ALLOWED_CHARACTERS.match(candidate):
        return None

    if not candidate:
        return None

    # Unicode and word operators -> ASCII equivalents.
    candidate = (
        candidate
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("^", "**")
    )

    # Currency symbols and thousands separators are notation,
    # never part of the math.
    candidate = re.sub(r"[₹$€£¥,]", "", candidate)

    # Collapse whitespace.
    candidate = " ".join(candidate.split())

    if not candidate:
        return None

    return candidate


def _evaluate_node(node):

    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(
            node.value,
            (int, float),
        ):
            raise ValueError(
                "Only numeric constants are allowed."
            )
        return node.value

    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)
        operation = _BINARY_OPERATORS.get(operator_type)

        if operation is None:
            raise ValueError(
                "Unsupported operator in expression."
            )

        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)

        if operator_type is ast.Pow:
            exponent = right

            if isinstance(exponent, float):
                if abs(exponent) > _MAX_ABS_EXPONENT:
                    raise ValueError(
                        "Exponent too large."
                    )
            elif abs(exponent) > _MAX_ABS_EXPONENT:
                raise ValueError("Exponent too large.")

        if operator_type is ast.Mod and right == 0:
            raise ValueError("Modulo by zero.")

        if operator_type in (ast.Div, ast.FloorDiv) and right == 0:
            raise ValueError("Division by zero.")

        result = operation(left, right)

        if isinstance(result, complex):
            raise ValueError(
                "Complex results are not supported."
            )

        return result

    if isinstance(node, ast.UnaryOp):
        operation = _UNARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError(
                "Unsupported operator in expression."
            )

        return operation(_evaluate_node(node.operand))

    raise ValueError(
        "Only plain arithmetic expressions are supported."
    )


def calculate(expression: str):
    """Evaluate a pure arithmetic expression deterministically.

    Returns {"expression": <cleaned>, "result": number}.
    Raises ValueError for anything that is not safe arithmetic."""

    cleaned = normalize_expression(expression)

    if cleaned is None:
        raise ValueError(
            "That doesn't look like a pure arithmetic "
            "expression."
        )

    try:
        tree = ast.parse(cleaned, mode="eval")
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        raise ValueError(
            f"Could not parse the expression: {cleaned}"
        )

    result = _evaluate_node(tree)

    return {
        "expression": cleaned,
        "result": result,
    }


def format_number(value):
    """Render a calculator result without float noise."""

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    if isinstance(value, int):
        return str(value)

    rounded = round(value, 6)

    if rounded == int(rounded):
        return str(int(rounded))

    return str(rounded)

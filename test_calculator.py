"""Tests for the deterministic calculator tool."""

import pytest

from tools.calculator import calculate, format_number, normalize_expression


class TestNormalization:

    def test_plain_expression(self):
        assert normalize_expression("2500000 / 85000") == "2500000 / 85000"

    def test_indian_currency_notation(self):
        cleaned = normalize_expression("₹25,00,000 ÷ ₹85,000")
        assert "," not in cleaned
        assert "₹" not in cleaned
        assert "/" in cleaned

    def test_question_wrapper_stripped(self):
        cleaned = normalize_expression("what is 12 + 8?")
        assert cleaned == "12 + 8"

    def test_how_much_is_prefix(self):
        cleaned = normalize_expression("how much is 100 * 3")
        assert cleaned == "100 * 3"

    def test_unicode_operators_mapped(self):
        assert normalize_expression("6 × 7") == "6 * 7"
        assert normalize_expression("10 ÷ 4") == "10 / 4"
        assert normalize_expression("9 − 5") == "9 - 5"

    def test_caret_to_power(self):
        assert normalize_expression("2 ^ 10") == "2 ** 10"

    def test_rejects_letters_after_prefix_strip(self):
        assert normalize_expression("what is your name?") is None
        assert normalize_expression("hello 2 + 2") is None

    def test_rejects_non_string(self):
        assert normalize_expression(None) is None
        assert normalize_expression(42) is None

    def test_empty_returns_none(self):
        assert normalize_expression("") is None

    def test_equals_sign_tolerated(self):
        cleaned = normalize_expression("25,00,000 / 85,000 =")
        assert cleaned == "2500000 / 85000"


class TestCalculate:

    def test_simple_addition(self):
        result = calculate("2 + 2")
        assert result["result"] == 4

    def test_goal_arithmetic_is_exact(self):
        result = calculate("₹25,00,000 ÷ ₹85,000")
        assert result["result"] == pytest.approx(29.411764705882355)

    def test_percentage_of_amount(self):
        result = calculate("(18 / 100) * 45000")
        assert result["result"] == pytest.approx(8100.0)

    def test_operator_precedence(self):
        assert calculate("2 + 3 * 4")["result"] == 14

    def test_parentheses(self):
        assert calculate("(2 + 3) * 4")["result"] == 20

    def test_negative_numbers(self):
        assert calculate("-5 + 10")["result"] == 5

    def test_float_result(self):
        assert calculate("10 / 4")["result"] == 2.5

    @pytest.mark.parametrize("bad", [
        "__import__('os').system('dir')",
        "().__class__",
        "1 if 2 else 3",
        "[1, 2]",
        "'a' + 'b'",
        "x = 5",
    ])
    def test_rejects_code_injection(self, bad):
        with pytest.raises(ValueError):
            calculate(bad)

    def test_rejects_division_by_zero(self):
        with pytest.raises(ValueError):
            calculate("5 / 0")

    def test_rejects_modulo_by_zero(self):
        with pytest.raises(ValueError):
            calculate("5 % 0")

    def test_rejects_huge_exponent(self):
        with pytest.raises(ValueError):
            calculate("9 ** 99999999")

    def test_rejects_text(self):
        with pytest.raises(ValueError):
            calculate("what is your name?")


class TestFormatNumber:

    def test_integer_float_rendered_cleanly(self):
        assert format_number(29.411764705882355) == str(
            round(29.411764705882355, 6)
        )

    def test_whole_float_becomes_int(self):
        assert format_number(8100.0) == "8100"

    def test_int_passthrough(self):
        assert format_number(14) == "14"

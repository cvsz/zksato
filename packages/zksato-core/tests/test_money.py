"""Tests for zksato-core money module."""

import pytest
from decimal import Decimal

from zksato_core.money import (
    Money,
    thb,
    BOARD_LOT,
    round_to_board_lot,
    is_board_lot,
)


def test_money_creation():
    m = Money(Decimal("100.50"))
    assert m.amount == Decimal("100.50")
    assert m.currency == "THB"


def test_money_from_float():
    m = Money.from_float(100.50)
    assert m.amount == Decimal("100.50")


def test_money_zero():
    m = Money.zero()
    assert m.amount == Decimal("0")
    assert m.currency == "THB"


def test_money_add():
    m1 = thb(100)
    m2 = thb(50)
    result = m1 + m2
    assert result.amount == Decimal("150")


def test_money_sub():
    m1 = thb(100)
    m2 = thb(50)
    result = m1 - m2
    assert result.amount == Decimal("50")


def test_money_mul():
    m = thb(100)
    result = m * 2
    assert result.amount == Decimal("200")


def test_money_div():
    m = thb(100)
    result = m / 2
    assert result.amount == Decimal("50")


def test_money_neg():
    m = thb(100)
    result = -m
    assert result.amount == Decimal("-100")


def test_money_comparison():
    assert thb(100) < thb(200)
    assert thb(100) <= thb(100)
    assert thb(200) > thb(100)
    assert thb(100) >= thb(100)


def test_money_abs():
    m = thb(-100)
    result = m.abs()
    assert result.amount == Decimal("100")


def test_money_quantize():
    m = Money(Decimal("100.555"))
    result = m.quantize("0.01")
    assert result.amount == Decimal("100.56")


def test_money_to_float():
    m = thb(100.50)
    assert m.to_float() == 100.50


def test_money_to_int():
    m = thb(100.99)
    assert m.to_int() == 100


def test_money_str():
    m = thb(100.50)
    assert str(m) == "100.50 THB"


def test_money_only_thb():
    with pytest.raises(ValueError, match="Only THB currency is supported"):
        Money(Decimal("100"), "USD")


def test_thb_helper():
    m = thb(100)
    assert m.amount == Decimal("100")
    assert m.currency == "THB"


def test_board_lot():
    assert BOARD_LOT == 100


def test_round_to_board_lot():
    assert round_to_board_lot(100) == 100
    assert round_to_board_lot(150) == 100
    assert round_to_board_lot(250) == 200
    assert round_to_board_lot(99) == 0


def test_is_board_lot():
    assert is_board_lot(100) is True
    assert is_board_lot(200) is True
    assert is_board_lot(150) is False
    assert is_board_lot(99) is False
from decimal import Decimal

import pytest

from app.services.money import cents_to_brl, reais_to_cents


def test_reais_to_cents_exactly():
    assert reais_to_cents(Decimal("599.90")) == 59990
    assert reais_to_cents("11499") == 1149900


def test_reais_to_cents_rejects_more_than_two_decimal_places():
    with pytest.raises(ValueError):
        reais_to_cents("10.001")


def test_money_formatting_uses_brazilian_conventions():
    assert cents_to_brl(208905) == "R$ 2.089,05"
    assert cents_to_brl(59990) == "R$ 599,90"


def test_money_formatting_rejects_bool():
    with pytest.raises(TypeError):
        cents_to_brl(True)

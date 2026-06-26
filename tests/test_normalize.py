from decimal import Decimal

import pytest

from verideck.normalize import canonical_key, decimal_places, is_noise, parse_number, values_tie


@pytest.mark.parametrize("token, expected", [
    ("1,234.56", Decimal("1234.56")),
    ("$1,234.56", Decimal("1234.56")),
    ("€3,000", Decimal("3000")),
    ("(2,500)", Decimal("-2500")),
    ("($1,250)", Decimal("-1250")),
    ("-42.5", Decimal("-42.5")),
    ("12.5%", Decimal("12.5")),
    ("1234567", Decimal("1234567")),
    ("0.07", Decimal("0.07")),
    ("2,500.", Decimal("2500")),  # trailing sentence period
])
def test_parse_number_accepts(token, expected):
    assert parse_number(token) == expected


@pytest.mark.parametrize("token", [
    "revenue", "FY2024", "Q3", "1,23", "12,34.5", "(123", "123)",
    "1.2.3", "", "-", "$", "v1.2", "3rd",
])
def test_parse_number_rejects(token):
    assert parse_number(token) is None


@pytest.mark.parametrize("raw, noise", [
    ("2024", True),     # bare year
    ("1999", True),
    ("7", True),        # bare small int: page number / bullet
    ("99", True),
    ("150", False),     # >= 100, plausible figure
    ("$7", False),      # formatted → real figure
    ("7.0", False),
    ("7%", False),
    ("2,024", False),   # comma-formatted → not a year mention
    ("(7)", False),
])
def test_is_noise(raw, noise):
    value = parse_number(raw)
    assert value is not None
    assert is_noise(raw, value) is noise


def test_canonical_key_groups_equivalent_forms():
    assert canonical_key(Decimal("2500")) == canonical_key(Decimal("2500.0"))
    assert canonical_key(Decimal("1234.56")) == "1234.56"
    assert canonical_key(Decimal("-2500")) == "-2500"


def test_decimal_places_reflects_display():
    assert decimal_places(Decimal("1234568")) == 0
    assert decimal_places(Decimal("1234567.89")) == 2
    assert decimal_places(Decimal("2500.10")) == 2


@pytest.mark.parametrize("a, b, tie", [
    ("1234568", "1234567.89", True),    # rounder display of the same value
    ("1234567", "1234567.89", False),   # would round to 1234568, not ...67
    ("1234567.5", "1234568", True),     # financial half-up
    ("500.25", "500.75", False),        # equal precision -> exact comparison
    ("2500", "2500.0", True),
    ("42.5", "42.46", True),            # 42.46 shown rounder is 42.5
    ("0.428", "0.425", False),
    ("-1250", "-1250.4", True),
    ("-1250", "-1250.6", False),
])
def test_values_tie(a, b, tie):
    assert values_tie(Decimal(a), Decimal(b)) is tie
    assert values_tie(Decimal(b), Decimal(a)) is tie  # symmetric

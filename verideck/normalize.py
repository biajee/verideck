"""Parsing of numeric tokens as they appear in financial documents."""

import re
from decimal import ROUND_HALF_UP, Decimal

# Matches tokens like: 1,234.56  $2,500  (1,234)  -42.5  12.5%  €3,000
_NUMBER_RE = re.compile(
    r"""
    ^
    (?P<open>\()?
    [$€£¥]?
    (?P<sign>-)?
    (?P<digits>\d{1,3}(?:,\d{3})+|\d+)
    (?P<frac>\.\d+)?
    (?P<close>\))?
    %?
    $
    """,
    re.VERBOSE,
)

_STRIP_TRAILING = ".,;:"

YEAR_MIN, YEAR_MAX = 1900, 2100
BARE_INT_NOISE_BELOW = 100  # unformatted small integers are page numbers, bullets...


def parse_number(token: str) -> Decimal | None:
    """Parse one whitespace-delimited token into its numeric value.

    Returns None when the token is not a plain number. Parentheses mean
    negative, accounting style. US-style thousands separators only.
    """
    token = token.strip()
    while token and token[-1] in _STRIP_TRAILING:
        token = token[:-1]
    match = _NUMBER_RE.match(token)
    if not match:
        return None
    if bool(match.group("open")) != bool(match.group("close")):
        return None  # unbalanced paren, e.g. a split token like "(123"
    value = Decimal(match.group("digits").replace(",", "") + (match.group("frac") or ""))
    if match.group("sign") or match.group("open"):
        value = -value
    return value


def is_noise(raw: str, value: Decimal) -> bool:
    """True for tokens that are numbers but not financial figures.

    Bare years (2024) and small unformatted integers (page numbers, list
    bullets) create meaningless tie groups, so extraction skips them.
    Formatted tokens ($7, 7.0, 7%) are never treated as noise.
    """
    bare = raw.strip().rstrip(_STRIP_TRAILING)
    if not bare.isdigit():
        return False  # has $, %, comma, decimal, paren or sign → a real figure
    intval = int(bare)
    if YEAR_MIN <= intval <= YEAR_MAX:
        return True
    return intval < BARE_INT_NOISE_BELOW


def canonical_key(value: Decimal) -> str:
    """Stable string key so 2500, 2500.0 and 2,500 group together."""
    return format(value.normalize(), "f")


def decimal_places(value: Decimal) -> int:
    """How many decimal places the number was displayed with (2,500.10 -> 2)."""
    return max(0, -value.as_tuple().exponent)


def values_tie(a: Decimal, b: Decimal) -> bool:
    """True when the two displayed numbers can be the same underlying value.

    Rounding tolerance: comparison happens at the coarser of the two displayed
    precisions, with financial half-up rounding. So 1234568 ties 1,234,567.89
    (one display is just rounder than the other), but 500.25 never ties 500.75
    (equal precision means an exact comparison).
    """
    places = min(decimal_places(a), decimal_places(b))
    quantum = Decimal(1).scaleb(-places)
    return (a.quantize(quantum, rounding=ROUND_HALF_UP)
            == b.quantize(quantum, rounding=ROUND_HALF_UP))

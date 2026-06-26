"""Data structures shared across the pipeline."""

from dataclasses import dataclass, field
from decimal import Decimal
from itertools import combinations

from .normalize import values_tie


@dataclass
class Occurrence:
    """One numeric token found in one place in one document."""

    file: str  # original (uploaded) filename
    page: int  # 1-based page / slide / sheet-page number
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points
    raw: str  # token as it appears, e.g. "$1,234.56" or "(2,500)"
    value: Decimal  # canonical numeric value, e.g. -2500
    line_text: str  # full text of the line containing the token
    crop: str = ""  # crop image filename, set by screenshot step
    page_image: str = ""  # full-page render filename, set by screenshot step
    # number's location as fractions of the page (x, y, w, h), for the hover
    # highlight overlay; resolution-independent so it scales with the image.
    highlight: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    @property
    def locator(self) -> str:
        x, y = int(self.bbox[0]), int(self.bbox[1])
        return f"{self.file} · p{self.page} · ({x},{y})"

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "page": self.page,
            "bbox": list(self.bbox),
            "raw": self.raw,
            "value": str(self.value),
            "line_text": self.line_text,
            "crop": self.crop,
            "page_image": self.page_image,
            "highlight": list(self.highlight),
            "locator": self.locator,
        }


@dataclass
class Group:
    """A set of occurrences that are expected to hold the same value.

    kind "tie": grouped because the values are identical.
    kind "mismatch": grouped because the row labels match but values differ.
    """

    kind: str  # "tie" | "mismatch"
    key: str  # display key: canonical value (tie) or shared label (mismatch)
    occurrences: list[Occurrence] = field(default_factory=list)

    def _distinct_values(self) -> list[Decimal]:
        # Keyed by str, not value: 2500 and 2500.0 are equal Decimals but
        # carry different displayed precisions, which values_tie needs.
        return list({str(occ.value): occ.value for occ in self.occurrences}.values())

    @property
    def tied(self) -> bool:
        return all(values_tie(a, b) for a, b in combinations(self._distinct_values(), 2))

    @property
    def rounded(self) -> bool:
        """Tied, but only thanks to rounding tolerance (displays differ)."""
        return self.tied and len(self._distinct_values()) > 1

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "key": self.key,
            "tied": self.tied,
            "rounded": self.rounded,
            "occurrences": [occ.to_dict() for occ in self.occurrences],
        }

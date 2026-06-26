from decimal import Decimal

import fitz

from verideck.models import Occurrence
from verideck.screenshot import _highlight_fraction, render_pages


def test_highlight_fraction_is_padded_bbox_over_page():
    x, y, w, h = _highlight_fraction((100, 50, 200, 70), 1000, 500)
    # 2pt padding on every side, expressed as page fractions
    assert x == (100 - 2) / 1000
    assert y == (50 - 2) / 500
    assert w == (200 + 2 - (100 - 2)) / 1000
    assert h == (70 + 2 - (50 - 2)) / 500


def test_highlight_fraction_clamps_at_page_edges():
    x, y, w, h = _highlight_fraction((0, 0, 10, 10), 100, 100)
    assert x == 0.0 and y == 0.0  # padding never pushes outside the page
    assert 0 < w <= 1 and 0 < h <= 1


def test_render_pages_writes_one_image_per_page_and_sets_highlight(tmp_path):
    pdf = tmp_path / "doc.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), "Revenue 1,234")
    doc.new_page().insert_text((72, 100), "Cash 5,678")
    doc.save(pdf)
    doc.close()

    occs = [
        Occurrence("doc.pdf", 1, (72, 90, 120, 102), "1,234", Decimal("1234"), "Revenue 1,234"),
        Occurrence("doc.pdf", 1, (72, 90, 120, 102), "1,234", Decimal("1234"), "Revenue 1,234"),
        Occurrence("doc.pdf", 2, (72, 90, 120, 102), "5,678", Decimal("5678"), "Cash 5,678"),
    ]
    render_pages(pdf, occs, tmp_path / "pages", prefix="f1")

    # two distinct pages -> two images, shared by occurrences on the same page
    assert occs[0].page_image == "f1-page1.png"
    assert occs[1].page_image == "f1-page1.png"
    assert occs[2].page_image == "f1-page2.png"
    assert sorted(p.name for p in (tmp_path / "pages").iterdir()) == ["f1-page1.png", "f1-page2.png"]

    for occ in occs:
        assert (tmp_path / "pages" / occ.page_image).exists()
        x, y, w, h = occ.highlight
        assert 0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1

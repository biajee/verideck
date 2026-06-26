from decimal import Decimal

from verideck.match import find_label_mismatches, group_ties, line_label
from verideck.models import Occurrence


def occ(file, page, raw, value, line_text):
    return Occurrence(file=file, page=page, bbox=(0, 0, 10, 10),
                      raw=raw, value=Decimal(value), line_text=line_text)


def test_group_ties_same_value_across_files():
    occurrences = [
        occ("deck.pptx", 3, "$1,234.56", "1234.56", "Total sales $1,234.56"),
        occ("deck.pptx", 7, "1,234.56", "1234.56", "Sales summary 1,234.56"),
        occ("model.xlsx", 1, "1234.56", "1234.56", "Total sales 1234.56"),
        occ("model.xlsx", 1, "999", "999", "Other 999"),
    ]
    groups = group_ties(occurrences)
    assert len(groups) == 1
    group = groups[0]
    assert group.kind == "tie" and group.tied
    assert group.key == "1234.56"
    assert len(group.occurrences) == 3
    assert {o.file for o in group.occurrences} == {"deck.pptx", "model.xlsx"}


def test_group_ties_sorted_largest_first():
    occurrences = [
        occ("a.pdf", 1, "100", "100", "x 100"), occ("b.pdf", 1, "100", "100", "y 100"),
        occ("a.pdf", 2, "9,999", "9999", "x 9,999"), occ("b.pdf", 2, "9999", "9999", "y 9999"),
    ]
    groups = group_ties(occurrences)
    assert [g.key for g in groups] == ["9999", "100"]


def test_group_ties_merges_rounded_displays():
    occurrences = [
        occ("deck.pptx", 3, "1,234,568", "1234568", "Total sales 1,234,568"),
        occ("model.xlsx", 1, "1234567.89", "1234567.89", "Total sales 1234567.89"),
    ]
    groups = group_ties(occurrences)
    assert len(groups) == 1
    group = groups[0]
    assert group.tied and group.rounded
    assert group.key == "1234567.89"  # most precise member names the group
    assert len(group.occurrences) == 2


def test_group_ties_keeps_truly_different_values_apart():
    occurrences = [
        occ("a.pdf", 1, "500.25", "500.25", "Cost 500.25"),
        occ("b.pdf", 1, "500.75", "500.75", "Cost 500.75"),
    ]
    assert group_ties(occurrences) == []


def test_mismatch_same_label_different_value_across_files():
    occurrences = [
        occ("deck.pptx", 3, "1,200", "1200", "Total revenue 1,200"),
        occ("model.xlsx", 1, "1,250", "1250", "Total revenue 1,250"),
    ]
    groups = find_label_mismatches(occurrences)
    assert len(groups) == 1
    assert groups[0].kind == "mismatch"
    assert groups[0].key == "total revenue"
    assert not groups[0].tied


def test_mismatch_not_flagged_within_single_file():
    # Same label twice in one file is normally two periods/columns, not an error.
    occurrences = [
        occ("deck.pptx", 3, "1,200", "1200", "Revenue 1,200"),
        occ("deck.pptx", 4, "1,250", "1250", "Revenue 1,250"),
    ]
    assert find_label_mismatches(occurrences) == []


def test_mismatch_not_flagged_when_values_agree():
    occurrences = [
        occ("deck.pptx", 3, "1,200", "1200", "Total revenue 1,200"),
        occ("model.xlsx", 1, "1,200", "1200", "Total revenue 1,200"),
    ]
    assert find_label_mismatches(occurrences) == []


def test_mismatch_not_flagged_when_values_tie_within_rounding():
    occurrences = [
        occ("deck.pptx", 3, "1,234,568", "1234568", "Total sales 1,234,568"),
        occ("model.xlsx", 1, "1234567.89", "1234567.89", "Total sales 1234567.89"),
    ]
    assert find_label_mismatches(occurrences) == []


def test_line_label_strips_numbers_and_noise():
    assert line_label("Total revenue: $1,234.56 (2,500)") == "total revenue"
    assert line_label("1,200") == ""

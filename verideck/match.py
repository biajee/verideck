"""Grouping of extracted numbers into rows the user verifies visually."""

import re
from collections import defaultdict
from decimal import Decimal
from itertools import combinations

from .models import Group, Occurrence
from .normalize import canonical_key, decimal_places, parse_number, values_tie

MIN_LABEL_LEN = 3


def group_ties(occurrences: list[Occurrence]) -> list[Group]:
    """Group occurrences whose values tie (exactly or within rounding), 2+ places.

    1234568 in the deck and 1,234,567.89 in the model land in one group: one
    display is just a rounder form of the other. The screenshots let the user
    confirm each tie with their own eyes.
    """
    groups = [
        Group(kind="tie", key=_cluster_key(cluster), occurrences=cluster)
        for cluster in _rounding_clusters(occurrences)
        if len(cluster) >= 2
    ]
    groups.sort(key=lambda g: abs(g.occurrences[0].value), reverse=True)
    return groups


def _rounding_clusters(occurrences: list[Occurrence]) -> list[list[Occurrence]]:
    """Partition occurrences by value, merging displays that round-tie.

    Union-find over the distinct displayed values; occurrences follow their
    value into its cluster.
    """
    displays: dict[str, Decimal] = {str(occ.value): occ.value for occ in occurrences}
    parent = {key: key for key in displays}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for a, b in combinations(displays, 2):
        if values_tie(displays[a], displays[b]):
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[root_a] = root_b

    clusters: dict[str, list[Occurrence]] = defaultdict(list)
    for occ in occurrences:
        clusters[find(str(occ.value))].append(occ)
    return list(clusters.values())


def _cluster_key(cluster: list[Occurrence]) -> str:
    """Display key for a tie group: its most precise member value."""
    best = max((occ.value for occ in cluster), key=decimal_places)
    return canonical_key(best)


def find_label_mismatches(occurrences: list[Occurrence]) -> list[Group]:
    """Flag same-labelled lines whose values differ across different files.

    If "Total revenue" reads 1,200 in the deck but 1,250 in the spreadsheet,
    that is a row the user must review. Values that tie within rounding are
    not mismatches. Restricted to cross-file comparisons: within one file a
    repeated label usually means different periods/columns, not an error.
    """
    by_label: dict[str, list[Occurrence]] = defaultdict(list)
    for occ in occurrences:
        label = line_label(occ.line_text)
        if len(label) >= MIN_LABEL_LEN:
            by_label[label].append(occ)
    groups = []
    for label, occs in sorted(by_label.items()):
        files = {occ.file for occ in occs}
        group = Group(kind="mismatch", key=label, occurrences=occs)
        if len(files) >= 2 and not group.tied:
            groups.append(group)
    return groups


def line_label(line_text: str) -> str:
    """Reduce a line to its textual label: drop numbers, lowercase, squeeze."""
    words = [w for w in line_text.split() if parse_number(w) is None]
    label = " ".join(words).lower()
    return re.sub(r"[^a-z0-9 ]+", " ", label).strip()

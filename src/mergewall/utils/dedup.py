"""Shared deduplication and sorting utilities for review findings."""

from __future__ import annotations

from mergewall.agents.base import ReviewFinding, SEVERITY_ORDER


def deduplicate_and_sort(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    """Remove duplicate findings (by normalised title) and sort by severity.

    Severity order: critical → high → medium → low.
    """
    seen: set[str] = set()
    unique: list[ReviewFinding] = []
    for f in findings:
        key = f.title.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    unique.sort(key=lambda f: SEVERITY_ORDER.get(f.severity.value, 99))
    return unique

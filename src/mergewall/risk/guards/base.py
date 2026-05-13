"""Base class for deterministic risk detection guards.

Every guard MUST have zero false positives. If a pattern match is
ambiguous, do NOT emit a finding — let the LLM handle it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mergewall.diff.models import DiffLine, FileDiff
from mergewall.risk.models import RiskCategory, RiskFinding


class BaseGuard(ABC):
    """Abstract base for deterministic risk guards."""

    category: RiskCategory

    @abstractmethod
    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        """Scan a file diff and return risk findings.

        Only examines added/modified lines (not removed lines).
        Returns empty list if no risks detected.
        """
        ...

    @staticmethod
    def _added_lines(file_diff: FileDiff) -> list[tuple[int, str]]:
        """Extract added lines with their new line numbers."""
        results = []
        for hunk in file_diff.hunks:
            for line in hunk.added_lines:
                if line.new_line is not None:
                    results.append((line.new_line, line.content))
        return results

    @staticmethod
    def _removed_lines(file_diff: FileDiff) -> list[tuple[int, str]]:
        """Extract removed lines with their old line numbers."""
        results = []
        for hunk in file_diff.hunks:
            for line in hunk.removed_lines:
                if line.old_line is not None:
                    results.append((line.old_line, line.content))
        return results

"""Deterministic guard for blast radius estimation.

Detects: large changes, modifications to shared/common utilities,
changes to files with high import counts.
"""

from __future__ import annotations

import re

from mergewall.diff.models import FileDiff
from mergewall.risk.guards.base import BaseGuard
from mergewall.risk.models import (
    DetectionMethod,
    MergeDecision,
    RiskCategory,
    RiskEvidence,
    RiskFinding,
    RiskLevel,
)

# Paths that are typically shared/critical infrastructure
_SHARED_PATH_RE = re.compile(
    r"(utils/|common/|shared/|lib/|core/|base/|__init__\.py|models\.py|types\.py)"
)

# Threshold for "large change"
_LARGE_CHANGE_THRESHOLD = 100  # net lines


class BlastRadiusGuard(BaseGuard):
    """Detects changes with high blast radius.

    Flags: large changes (>100 net lines), modifications to shared
    utility modules, changes to __init__.py re-exports.
    """

    category = RiskCategory.BLAST_RADIUS

    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        findings = []

        # Check for large changes
        net = file_diff.net_lines_changed
        if abs(net) > _LARGE_CHANGE_THRESHOLD:
            level = RiskLevel.HIGH if abs(net) > 200 else RiskLevel.MEDIUM
            findings.append(RiskFinding(
                category=RiskCategory.BLAST_RADIUS,
                level=level,
                title=f"Large change: {abs(net)} net lines in {file_diff.new_path}",
                why_dangerous=(
                    f"This change modifies {abs(net)} net lines. "
                    "Large changes are harder to review and more likely to introduce bugs."
                ),
                impact_scope=f"File {file_diff.new_path} and all its dependents",
                evidence=RiskEvidence(
                    file_path=file_diff.new_path,
                    line_numbers=[],
                    pattern_matched=f"net_lines={net}",
                    detection_method=DetectionMethod.DETERMINISTIC,
                ),
                merge_decision=MergeDecision.WARN,
                fix_suggestion="Consider splitting this into smaller, reviewable changes.",
                confidence=0.7,
            ))

        # Check for shared utility changes
        if _SHARED_PATH_RE.search(file_diff.new_path):
            findings.append(RiskFinding(
                category=RiskCategory.BLAST_RADIUS,
                level=RiskLevel.MEDIUM,
                title=f"Shared module modified: {file_diff.new_path}",
                why_dangerous=(
                    "This file is in a shared/common directory. "
                    "Changes here may affect many consumers across the codebase."
                ),
                impact_scope="All modules importing from this file",
                evidence=RiskEvidence(
                    file_path=file_diff.new_path,
                    line_numbers=[],
                    pattern_matched="shared_module",
                    detection_method=DetectionMethod.DETERMINISTIC,
                ),
                merge_decision=MergeDecision.WARN,
                fix_suggestion="Verify all consumers still work correctly after this change.",
                confidence=0.6,
            ))

        return findings

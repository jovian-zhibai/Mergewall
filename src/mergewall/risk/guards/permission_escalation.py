"""Deterministic guard for permission escalation.

Detects: role/permission checks being removed, admin flags being added,
wildcard permissions, authorization decorators removed.
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

# Patterns in ADDED lines for permission escalation
_ESCALATION_PATTERNS = [
    (re.compile(r"(?i)is_superuser\s*=\s*True"), "is_superuser=True"),
    (re.compile(r"(?i)is_admin\s*=\s*True"), "is_admin=True"),
    (re.compile(r"(?i)is_staff\s*=\s*True"), "is_staff=True"),
    # NOTE: (?<!=)=(?!=) matches only assignment (=), not comparison (==)
    (re.compile(r"(?i)role\s*(?<!=)=(?!=)\s*[\"']admin[\"']"), "hardcoded admin role"),
    (re.compile(r"(?i)permissions\s*=\s*\[?\s*[\"']\*[\"']"), "wildcard permissions"),
    (re.compile(r"(?i)allow_all\s*=\s*True"), "allow_all=True"),
    (re.compile(r"(?i)disable_auth\s*=\s*True"), "disable_auth=True"),
]

# Patterns in REMOVED lines for removed protections
_REMOVED_PROTECTIONS = [
    (re.compile(r"@permission_required"), "permission_required decorator"),
    (re.compile(r"@requires_role"), "requires_role decorator"),
    (re.compile(r"@has_permission"), "has_permission decorator"),
    (re.compile(r"(?i)if\s+.*\.has_perm"), "has_perm check"),
    (re.compile(r"(?i)if\s+.*\.is_authenticated"), "is_authenticated check"),
]


class PermissionEscalationGuard(BaseGuard):
    """Detects permission escalation in diffs.

    Flags: admin/superuser flags added, permission checks removed,
    wildcard permissions added.
    """

    category = RiskCategory.PERMISSION_ESCALATION

    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        findings = []
        added = self._added_lines(file_diff)
        removed = self._removed_lines(file_diff)

        # Check for escalation patterns in added lines
        for line_num, content in added:
            for pattern, name in _ESCALATION_PATTERNS:
                if pattern.search(content):
                    findings.append(RiskFinding(
                        category=RiskCategory.PERMISSION_ESCALATION,
                        level=RiskLevel.HIGH,
                        title=f"Permission escalation: {name}",
                        why_dangerous=(
                            f"Code adds {name}, which may grant elevated privileges."
                        ),
                        impact_scope="Authorization model",
                        evidence=RiskEvidence(
                            file_path=file_diff.new_path,
                            line_numbers=[line_num],
                            code_snippet=content[:200],
                            pattern_matched=name,
                            detection_method=DetectionMethod.DETERMINISTIC,
                        ),
                        merge_decision=MergeDecision.BLOCK,
                        approval_required=["security-team"],
                        fix_suggestion="Use role-based access control instead of hardcoded privilege flags.",
                        confidence=0.85,
                    ))

        # Check for removed protections
        for line_num, content in removed:
            for pattern, name in _REMOVED_PROTECTIONS:
                if pattern.search(content):
                    findings.append(RiskFinding(
                        category=RiskCategory.PERMISSION_ESCALATION,
                        level=RiskLevel.HIGH,
                        title=f"Permission check removed: {name}",
                        why_dangerous=(
                            f"A {name} was removed. "
                            "Endpoints may become unprotected."
                        ),
                        impact_scope="Endpoints relying on the removed check",
                        evidence=RiskEvidence(
                            file_path=file_diff.new_path,
                            line_numbers=[line_num],
                            code_snippet=content[:200],
                            pattern_matched=f"removed:{name}",
                            detection_method=DetectionMethod.DETERMINISTIC,
                        ),
                        merge_decision=MergeDecision.REQUIRE_APPROVAL,
                        approval_required=["security-team"],
                        fix_suggestion="Verify this removal is intentional and add alternative protection.",
                        confidence=0.8,
                    ))

        return findings

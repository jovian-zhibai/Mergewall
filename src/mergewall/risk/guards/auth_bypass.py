"""Deterministic guard for authentication/authorization bypass.

Detects: removed auth decorators, added bypass flags, deleted auth checks,
new anonymous access paths.
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

# Patterns in REMOVED lines that indicate auth was present
_AUTH_DECORATORS_REMOVED = [
    (re.compile(r"@login_required"), "login_required decorator"),
    (re.compile(r"@auth_required"), "auth_required decorator"),
    (re.compile(r"@permission_required"), "permission_required decorator"),
    (re.compile(r"@requires_auth"), "requires_auth decorator"),
    (re.compile(r"@authenticated"), "authenticated decorator"),
    (re.compile(r"@jwt_required"), "jwt_required decorator"),
    (re.compile(r"@protect"), "protect decorator"),
]

# Patterns in ADDED lines that indicate auth bypass
_AUTH_BYPASS_ADDED = [
    (re.compile(r"(?i)skip_auth(?:entication)?\s*=\s*True"), "skip_authentication flag"),
    (re.compile(r"(?i)allow_anonymous\s*=\s*True"), "allow_anonymous flag"),
    (re.compile(r"(?i)auth(?:entication)?_required\s*=\s*False"), "auth_required=False"),
    (re.compile(r"(?i)bypass_auth"), "bypass_auth reference"),
    (re.compile(r"(?i)return\s+True\s*#.*(?:skip|bypass|auth)"), "auth bypass via return True"),
]

# Patterns in ADDED lines for permission escalation
_PERM_ESCALATION_ADDED = [
    (re.compile(r"(?i)is_superuser\s*=\s*True"), "is_superuser=True"),
    (re.compile(r"(?i)is_admin\s*=\s*True"), "is_admin=True"),
    # NOTE: The negative lookbehind (?<!=) ensures we match `role = "admin"`
    # (assignment) but NOT `role == "admin"` (comparison). This prevents false
    # positives on legitimate role checks.
    (re.compile(r"(?i)role\s*(?<!=)=(?!=)\s*[\"']admin[\"']"), "hardcoded admin role check"),
    (re.compile(r"(?i)permissions\s*=\s*\[?\s*[\"']\*[\"']"), "wildcard permissions"),
    (re.compile(r"(?i)allow_all\s*=\s*True"), "allow_all flag"),
]


class AuthBypassGuard(BaseGuard):
    """Detects auth bypass and permission escalation in diffs.

    Strategy: compare removed auth decorators against added bypass patterns.
    High confidence when both are present in the same file.
    """

    category = RiskCategory.AUTH_BYPASS

    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        findings = []

        removed = self._removed_lines(file_diff)
        added = self._added_lines(file_diff)

        # Check for removed auth decorators
        removed_auth = []
        for line_num, content in removed:
            for pattern, name in _AUTH_DECORATORS_REMOVED:
                if pattern.search(content):
                    removed_auth.append((line_num, name))

        # Check for added bypass patterns
        added_bypass = []
        for line_num, content in added:
            for pattern, name in _AUTH_BYPASS_ADDED:
                if pattern.search(content):
                    added_bypass.append((line_num, name))

        # Check for permission escalation
        perm_escalation = []
        for line_num, content in added:
            for pattern, name in _PERM_ESCALATION_ADDED:
                if pattern.search(content):
                    perm_escalation.append((line_num, name))

        # If auth decorators removed AND bypass added — high confidence
        if removed_auth and added_bypass:
            all_lines = [ln for ln, _ in removed_auth] + [ln for ln, _ in added_bypass]
            findings.append(RiskFinding(
                category=RiskCategory.AUTH_BYPASS,
                level=RiskLevel.CRITICAL,
                title="Authentication bypass detected",
                why_dangerous=(
                    f"Auth decorator ({removed_auth[0][1]}) was removed and a bypass pattern "
                    f"({added_bypass[0][1]}) was added. This may allow unauthenticated access."
                ),
                impact_scope="Endpoints protected by the removed auth check",
                evidence=RiskEvidence(
                    file_path=file_diff.new_path,
                    line_numbers=all_lines[:10],
                    pattern_matched=f"removed:{removed_auth[0][1]}, added:{added_bypass[0][1]}",
                    detection_method=DetectionMethod.DETERMINISTIC,
                ),
                merge_decision=MergeDecision.BLOCK,
                approval_required=["security-team"],
                fix_suggestion=(
                    "If removing auth is intentional, document why and add alternative "
                    "protection. If not, restore the auth decorator."
                ),
                confidence=0.9,
            ))

        # If only auth decorators removed (no bypass added) — medium confidence
        elif removed_auth and not added_bypass:
            findings.append(RiskFinding(
                category=RiskCategory.AUTH_BYPASS,
                level=RiskLevel.HIGH,
                title="Auth decorator removed",
                why_dangerous=(
                    f"Auth decorator ({removed_auth[0][1]}) was removed. "
                    "This endpoint may become unprotected."
                ),
                impact_scope="Endpoints that relied on the removed auth check",
                evidence=RiskEvidence(
                    file_path=file_diff.new_path,
                    line_numbers=[ln for ln, _ in removed_auth[:10]],
                    pattern_matched=f"removed:{removed_auth[0][1]}",
                    detection_method=DetectionMethod.DETERMINISTIC,
                ),
                merge_decision=MergeDecision.REQUIRE_APPROVAL,
                approval_required=["security-team"],
                fix_suggestion="Verify this removal is intentional and add alternative protection if needed.",
                confidence=0.8,
            ))

        # Permission escalation
        for line_num, name in perm_escalation:
            findings.append(RiskFinding(
                category=RiskCategory.PERMISSION_ESCALATION,
                level=RiskLevel.HIGH,
                title=f"Permission escalation: {name}",
                why_dangerous=(
                    f"Code adds {name}, which may grant elevated privileges "
                    "beyond what the user should have."
                ),
                impact_scope="Authorization model — may allow privilege escalation",
                evidence=RiskEvidence(
                    file_path=file_diff.new_path,
                    line_numbers=[line_num],
                    pattern_matched=name,
                    detection_method=DetectionMethod.DETERMINISTIC,
                ),
                merge_decision=MergeDecision.BLOCK,
                approval_required=["security-team"],
                fix_suggestion="Use role-based access control instead of hardcoded privilege flags.",
                confidence=0.85,
            ))

        return findings

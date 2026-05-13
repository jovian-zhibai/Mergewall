"""Policy Engine — evaluates risk findings against governance policies.

Path rules are evaluated in order — first match wins.
Threshold rules are evaluated against overall risk score.
Most restrictive action across all findings wins.
"""

from __future__ import annotations

import fnmatch

from mergewall.policy.models import (
    FindingDecision,
    GovernancePolicy,
    PathRule,
    PolicyAction,
    PolicyDecision,
)
from mergewall.risk.models import RiskReport

_LEVEL_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}

_ACTION_ORDER = {
    PolicyAction.BLOCK: 0,
    PolicyAction.REQUIRE_APPROVAL: 1,
    PolicyAction.WARN: 2,
    PolicyAction.ALLOW: 3,
}


class PolicyEngine:
    """Evaluates risk findings against governance policies."""

    def __init__(self, policy: GovernancePolicy):
        self.policy = policy

    def evaluate(self, report: RiskReport) -> PolicyDecision:
        """Evaluate a RiskReport against the governance policy."""
        finding_decisions: list[FindingDecision] = []

        for finding in report.findings:
            if finding.confidence < self.policy.min_confidence:
                continue

            decision = self._evaluate_finding(finding)
            finding_decisions.append(decision)

        # Evaluate threshold rules
        threshold_action, threshold_approvals = self._evaluate_threshold(report.risk_score)

        # Most restrictive wins
        all_actions = [self.policy.default_action, threshold_action]
        all_actions.extend(d.action for d in finding_decisions)
        overall_action = min(all_actions, key=lambda a: _ACTION_ORDER.get(a, 99))

        # Collect all required approvals
        all_approvals: set[str] = set()
        for d in finding_decisions:
            all_approvals.update(d.required_approvals)
        all_approvals.update(threshold_approvals)

        reason = self._build_reason(overall_action, finding_decisions, threshold_action, report.risk_score)

        return PolicyDecision(
            action=overall_action,
            required_approvals=sorted(all_approvals),
            finding_decisions=finding_decisions,
            risk_score=report.risk_score,
            reason=reason,
        )

    def _evaluate_finding(self, finding) -> FindingDecision:
        """Check a single finding against path rules."""
        for rule in self.policy.path_rules:
            if self._path_matches(finding.evidence.file_path, rule.paths):
                if self._category_matches(finding.category.value, rule.risk_categories):
                    if self._level_meets_threshold(finding.level.value, rule.min_level):
                        return FindingDecision(
                            finding_title=finding.title,
                            finding_category=finding.category.value,
                            action=rule.action,
                            required_approvals=list(rule.require_approval_from),
                            matched_rule=f"path:{rule.paths}",
                        )
        return FindingDecision(
            finding_title=finding.title,
            finding_category=finding.category.value,
            action=PolicyAction.WARN,
        )

    def _evaluate_threshold(self, risk_score: int) -> tuple[PolicyAction, list[str]]:
        """Evaluate threshold rules against overall risk score."""
        # Sort by min_score descending — highest threshold checked first
        sorted_rules = sorted(self.policy.threshold_rules, key=lambda r: r.min_score, reverse=True)
        for rule in sorted_rules:
            if risk_score >= rule.min_score:
                return rule.action, list(rule.require_approval_from)
        return PolicyAction.ALLOW, []

    @staticmethod
    def _path_matches(file_path: str, patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(file_path, p) for p in patterns)

    @staticmethod
    def _category_matches(category: str, rule_categories: list[str]) -> bool:
        return "*" in rule_categories or category in rule_categories

    @staticmethod
    def _level_meets_threshold(level: str, min_level: str) -> bool:
        return _LEVEL_ORDER.get(level, 4) <= _LEVEL_ORDER.get(min_level, 4)

    @staticmethod
    def _build_reason(
        action: PolicyAction,
        finding_decisions: list[FindingDecision],
        threshold_action: PolicyAction,
        risk_score: int,
    ) -> str:
        parts = []
        if action == PolicyAction.BLOCK:
            blocked = [d for d in finding_decisions if d.action == PolicyAction.BLOCK]
            if blocked:
                parts.append(f"Blocked by {len(blocked)} finding(s): {', '.join(d.finding_title for d in blocked[:3])}")
        if threshold_action in (PolicyAction.BLOCK, PolicyAction.REQUIRE_APPROVAL):
            parts.append(f"Risk score {risk_score} triggered threshold rule")
        return ". ".join(parts) if parts else f"Decision: {action.value}"

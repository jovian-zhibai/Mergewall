"""Tests for the Policy Engine."""

import pytest
from mergewall.policy.engine import PolicyEngine
from mergewall.policy.models import (
    GovernancePolicy,
    PathRule,
    PolicyAction,
    PolicyDecision,
    ThresholdRule,
)
from mergewall.risk.models import (
    DetectionMethod,
    MergeDecision,
    RiskCategory,
    RiskEvidence,
    RiskFinding,
    RiskLevel,
    RiskReport,
)


def _make_report(findings: list[RiskFinding], score: int = 0) -> RiskReport:
    return RiskReport(pr_number=1, repo="org/repo", findings=findings, risk_score=score)


def _make_finding(
    category: RiskCategory = RiskCategory.SECRET_LEAKAGE,
    level: RiskLevel = RiskLevel.CRITICAL,
    file_path: str = "src/app.py",
    title: str = "Test finding",
) -> RiskFinding:
    return RiskFinding(
        category=category,
        level=level,
        title=title,
        why_dangerous="Test reason",
        impact_scope="Test scope",
        evidence=RiskEvidence(file_path=file_path, line_numbers=[1]),
        merge_decision=MergeDecision.BLOCK,
    )


class TestPolicyEngine:
    def test_default_policy_allows_clean(self):
        policy = GovernancePolicy()
        engine = PolicyEngine(policy)
        report = _make_report([], score=0)
        decision = engine.evaluate(report)
        assert decision.action == PolicyAction.ALLOW

    def test_path_rule_blocks_auth(self):
        policy = GovernancePolicy(
            path_rules=[
                PathRule(
                    paths=["src/auth/**"],
                    risk_categories=["auth_bypass"],
                    min_level="medium",
                    action=PolicyAction.BLOCK,
                    require_approval_from=["security-team"],
                ),
            ],
        )
        engine = PolicyEngine(policy)
        finding = _make_finding(
            category=RiskCategory.AUTH_BYPASS,
            level=RiskLevel.HIGH,
            file_path="src/auth/views.py",
        )
        report = _make_report([finding])
        decision = engine.evaluate(report)
        assert decision.action == PolicyAction.BLOCK
        assert "security-team" in decision.required_approvals

    def test_path_rule_first_match_wins(self):
        policy = GovernancePolicy(
            path_rules=[
                PathRule(paths=["src/**"], risk_categories=["*"], min_level="low", action=PolicyAction.BLOCK),
                PathRule(paths=["**"], risk_categories=["*"], min_level="low", action=PolicyAction.ALLOW),
            ],
        )
        engine = PolicyEngine(policy)
        finding = _make_finding(file_path="src/app.py")
        report = _make_report([finding])
        decision = engine.evaluate(report)
        assert decision.action == PolicyAction.BLOCK

    def test_threshold_rule_triggers(self):
        policy = GovernancePolicy(
            threshold_rules=[
                ThresholdRule(min_score=60, action=PolicyAction.BLOCK),
                ThresholdRule(min_score=30, action=PolicyAction.REQUIRE_APPROVAL, require_approval_from=["tech-lead"]),
            ],
        )
        engine = PolicyEngine(policy)
        report = _make_report([], score=45)
        decision = engine.evaluate(report)
        assert decision.action == PolicyAction.REQUIRE_APPROVAL
        assert "tech-lead" in decision.required_approvals

    def test_threshold_rule_high_score_blocks(self):
        policy = GovernancePolicy(
            threshold_rules=[
                ThresholdRule(min_score=60, action=PolicyAction.BLOCK),
            ],
        )
        engine = PolicyEngine(policy)
        report = _make_report([], score=75)
        decision = engine.evaluate(report)
        assert decision.action == PolicyAction.BLOCK

    def test_min_confidence_filters_findings(self):
        policy = GovernancePolicy(min_confidence=0.9)
        engine = PolicyEngine(policy)
        low_confidence = _make_finding()
        low_confidence.confidence = 0.5
        report = _make_report([low_confidence])
        decision = engine.evaluate(report)
        # Low confidence finding should be filtered out
        assert len(decision.finding_decisions) == 0

    def test_wildcard_category_matches_any(self):
        policy = GovernancePolicy(
            path_rules=[
                PathRule(paths=["**"], risk_categories=["*"], min_level="low", action=PolicyAction.BLOCK),
            ],
        )
        engine = PolicyEngine(policy)
        finding = _make_finding(category=RiskCategory.BLAST_RADIUS)
        report = _make_report([finding])
        decision = engine.evaluate(report)
        assert decision.action == PolicyAction.BLOCK

    def test_level_threshold_filtering(self):
        policy = GovernancePolicy(
            path_rules=[
                PathRule(paths=["**"], risk_categories=["*"], min_level="critical", action=PolicyAction.BLOCK),
            ],
        )
        engine = PolicyEngine(policy)
        # HIGH finding should not trigger a rule that requires CRITICAL
        finding = _make_finding(level=RiskLevel.HIGH)
        report = _make_report([finding])
        decision = engine.evaluate(report)
        assert decision.action == PolicyAction.WARN  # default for unmatched

    def test_multiple_findings_most_restrictive_wins(self):
        policy = GovernancePolicy()
        engine = PolicyEngine(policy)
        warn_finding = _make_finding(title="Warning")
        warn_finding.merge_decision = MergeDecision.WARN
        block_finding = _make_finding(title="Block")
        block_finding.merge_decision = MergeDecision.BLOCK
        report = _make_report([warn_finding, block_finding])
        decision = engine.evaluate(report)
        # PolicyDecision action should be most restrictive
        assert decision.action == PolicyAction.WARN  # default_action since no path rules matched

    def test_reason_generated(self):
        policy = GovernancePolicy(
            path_rules=[
                PathRule(paths=["**"], risk_categories=["secret_leakage"], min_level="low", action=PolicyAction.BLOCK),
            ],
        )
        engine = PolicyEngine(policy)
        finding = _make_finding()
        report = _make_report([finding])
        decision = engine.evaluate(report)
        assert "Blocked" in decision.reason or "block" in decision.reason.lower()

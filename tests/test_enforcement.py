"""Tests for the Enforcement Engine, Checks client, and Audit Trail."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mergewall.audit.models import AuditEntry
from mergewall.audit.trail import AuditTrail
from mergewall.enforcement.checks import GitHubChecksClient
from mergewall.risk.models import MergeDecision, RiskReport


# ---------------------------------------------------------------------------
# GitHub Checks Client
# ---------------------------------------------------------------------------


class TestGitHubChecksClient:
    def test_decision_to_conclusion_block(self):
        assert GitHubChecksClient._decision_to_conclusion(MergeDecision.BLOCK) == "action_required"

    def test_decision_to_conclusion_require_approval(self):
        assert GitHubChecksClient._decision_to_conclusion(MergeDecision.REQUIRE_APPROVAL) == "action_required"

    def test_decision_to_conclusion_warn(self):
        assert GitHubChecksClient._decision_to_conclusion(MergeDecision.WARN) == "neutral"

    def test_decision_to_conclusion_allow(self):
        assert GitHubChecksClient._decision_to_conclusion(MergeDecision.ALLOW) == "success"


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def setup_method(self):
        self.trail = AuditTrail(log_dir="/tmp/mergewall_test_audit")

    def teardown_method(self):
        import shutil
        p = Path("/tmp/mergewall_test_audit")
        if p.exists():
            shutil.rmtree(p)

    def test_log_creates_file(self):
        entry = AuditEntry(
            repo="org/repo",
            pr_number=42,
            head_sha="abc123",
            merge_decision="block",
            risk_score=25,
            finding_count=1,
        )
        self.trail.log(entry)
        assert self.trail.log_file.exists()

    def test_log_appends_entry(self):
        entry = AuditEntry(
            repo="org/repo",
            pr_number=1,
            head_sha="abc",
            merge_decision="allow",
            risk_score=0,
            finding_count=0,
        )
        self.trail.log(entry)
        self.trail.log(entry)
        lines = self.trail.log_file.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_log_entry_is_valid_json(self):
        entry = AuditEntry(
            repo="org/repo",
            pr_number=1,
            head_sha="abc",
            merge_decision="block",
            risk_score=50,
            finding_count=3,
            required_approvals=["security-team"],
        )
        self.trail.log(entry)
        data = json.loads(self.trail.log_file.read_text().strip())
        assert data["repo"] == "org/repo"
        assert data["merge_decision"] == "block"
        assert data["required_approvals"] == ["security-team"]

    def test_query_by_repo(self):
        self.trail.log(AuditEntry(repo="org/a", pr_number=1, head_sha="x", merge_decision="allow", risk_score=0, finding_count=0))
        self.trail.log(AuditEntry(repo="org/b", pr_number=2, head_sha="y", merge_decision="block", risk_score=50, finding_count=1))
        results = self.trail.query(repo="org/a")
        assert len(results) == 1
        assert results[0].pr_number == 1

    def test_query_by_decision(self):
        self.trail.log(AuditEntry(repo="org/a", pr_number=1, head_sha="x", merge_decision="allow", risk_score=0, finding_count=0))
        self.trail.log(AuditEntry(repo="org/a", pr_number=2, head_sha="y", merge_decision="block", risk_score=50, finding_count=1))
        results = self.trail.query(decision="block")
        assert len(results) == 1
        assert results[0].pr_number == 2

    def test_query_empty(self):
        results = self.trail.query()
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Risk Report output formats
# ---------------------------------------------------------------------------


class TestRiskReportOutput:
    def test_checks_output_annotations_capped(self):
        """GitHub caps annotations at 50."""
        from mergewall.risk.models import RiskCategory, RiskLevel, RiskEvidence, RiskFinding
        findings = [
            RiskFinding(
                category=RiskCategory.SECRET_LEAKAGE,
                level=RiskLevel.CRITICAL,
                title=f"Secret {i}",
                why_dangerous="test",
                impact_scope="test",
                evidence=RiskEvidence(file_path=f"file{i}.py", line_numbers=[i]),
                merge_decision=MergeDecision.BLOCK,
            )
            for i in range(100)
        ]
        report = RiskReport(pr_number=1, repo="org/repo", findings=findings, merge_decision=MergeDecision.BLOCK, risk_score=100)
        output = report.to_checks_output()
        assert len(output["annotations"]) == 50

    def test_markdown_emoji_block(self):
        report = RiskReport(pr_number=1, repo="org/repo", findings=[], merge_decision=MergeDecision.BLOCK, risk_score=80)
        md = report.to_markdown()
        assert "Merge Blocked" in md

    def test_markdown_emoji_allow(self):
        report = RiskReport(pr_number=1, repo="org/repo", findings=[], merge_decision=MergeDecision.ALLOW, risk_score=0)
        md = report.to_markdown()
        assert "Merge Allowed" in md

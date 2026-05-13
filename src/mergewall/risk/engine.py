"""Diff Risk Engine — orchestrates risk detection across a structured diff.

Strategy: deterministic guards run first (fast, zero false positives).
LLM agents run only on files with deterministic flags or large changes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mergewall.diff.models import FileDiff, StructuredDiff
from mergewall.risk.guards.api_contract import APIContractGuard
from mergewall.risk.guards.auth_bypass import AuthBypassGuard
from mergewall.risk.guards.base import BaseGuard
from mergewall.risk.guards.blast_radius import BlastRadiusGuard
from mergewall.risk.guards.dangerous_deps import DangerousDepsGuard
from mergewall.risk.guards.permission_escalation import PermissionEscalationGuard
from mergewall.risk.guards.secret_leakage import SecretLeakageGuard
from mergewall.risk.models import (
    MergeDecision,
    RiskCategory,
    RiskFinding,
    RiskReport,
)

if TYPE_CHECKING:
    from mergewall.config import GuardianConfig

logger = logging.getLogger(__name__)

# Risk level weights for scoring
_LEVEL_WEIGHTS = {
    "critical": 25,
    "high": 15,
    "medium": 5,
    "low": 1,
}

# Decision hierarchy (most restrictive wins)
_DECISION_ORDER = {
    MergeDecision.BLOCK: 0,
    MergeDecision.REQUIRE_APPROVAL: 1,
    MergeDecision.WARN: 2,
    MergeDecision.ALLOW: 3,
}


class DiffRiskEngine:
    """Orchestrates deterministic and LLM-based risk detection.

    Phase 1: deterministic guards on each file (zero false positives)
    Phase 2: LLM agents on flagged files (optional, post-MVP)
    """

    def __init__(self, config: GuardianConfig | None = None):
        self.config = config
        self.guards: list[BaseGuard] = self._init_guards()

    def _init_guards(self) -> list[BaseGuard]:
        """Instantiate all deterministic guards."""
        return [
            SecretLeakageGuard(),
            AuthBypassGuard(),
            PermissionEscalationGuard(),
            DangerousDepsGuard(),
            APIContractGuard(),
            BlastRadiusGuard(),
        ]

    async def analyze(self, diff: StructuredDiff) -> RiskReport:
        """Run the full risk analysis pipeline.

        1. Run deterministic guards on each file
        2. (Future) LLM confirmation on flagged files
        3. Aggregate, deduplicate, compute merge decision and risk score
        """
        all_findings: list[RiskFinding] = []

        for file_diff in diff.files:
            if file_diff.is_binary:
                continue
            if self.config and self.config.should_ignore(file_diff.new_path):
                continue
            for guard in self.guards:
                try:
                    findings = guard.scan(file_diff)
                    all_findings.extend(findings)
                except Exception:
                    logger.exception("Guard %s failed on %s", guard.__class__.__name__, file_diff.new_path)

        merged_findings = self._deduplicate(all_findings)
        merge_decision = self._compute_merge_decision(merged_findings)
        risk_score = self._compute_risk_score(merged_findings)

        return RiskReport(
            pr_number=0,
            repo="",
            findings=merged_findings,
            merge_decision=merge_decision,
            risk_score=risk_score,
            summary=self._generate_summary(merged_findings, merge_decision, risk_score),
            deterministic_count=sum(
                1 for f in all_findings
                if f.evidence.detection_method.value == "deterministic"
            ),
            llm_count=sum(
                1 for f in all_findings
                if f.evidence.detection_method.value == "llm"
            ),
        )

    @staticmethod
    def _deduplicate(findings: list[RiskFinding]) -> list[RiskFinding]:
        """Remove duplicate findings by (category, title, file_path)."""
        seen: set[tuple[str, str, str]] = set()
        unique = []
        for f in findings:
            key = (f.category.value, f.title, f.evidence.file_path)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        # Sort: most severe first
        unique.sort(key=lambda f: _LEVEL_WEIGHTS.get(f.level.value, 0), reverse=True)
        return unique

    @staticmethod
    def _compute_merge_decision(findings: list[RiskFinding]) -> MergeDecision:
        """Most restrictive finding wins."""
        if not findings:
            return MergeDecision.ALLOW
        return min(
            (f.merge_decision for f in findings),
            key=lambda d: _DECISION_ORDER.get(d, 99),
        )

    @staticmethod
    def _compute_risk_score(findings: list[RiskFinding]) -> int:
        """Compute risk score: weighted sum of findings, capped at 100."""
        score = sum(_LEVEL_WEIGHTS.get(f.level.value, 0) for f in findings)
        return min(score, 100)

    @staticmethod
    def _generate_summary(
        findings: list[RiskFinding], decision: MergeDecision, score: int
    ) -> str:
        if not findings:
            return "No risks detected. Clean to merge."
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.level.value] = counts.get(f.level.value, 0) + 1
        parts = [f"{v} {k}" for k, v in sorted(counts.items())]
        return f"Risk score {score}/100. {', '.join(parts)} finding(s). Decision: {decision.value}."

"""Enforcement Engine — orchestrates the full governance pipeline.

Called from server/worker.py after the webhook receives a PR event.
Runs: diff parsing → risk analysis → policy evaluation → GitHub checks → audit.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mergewall.audit.models import AuditEntry
from mergewall.audit.trail import AuditTrail
from mergewall.diff.parser import parse_diff
from mergewall.enforcement.checks import GitHubChecksClient
from mergewall.policy.engine import PolicyEngine
from mergewall.policy.models import PolicyDecision
from mergewall.risk.engine import DiffRiskEngine

if TYPE_CHECKING:
    from mergewall.config import GuardianConfig

logger = logging.getLogger(__name__)


class EnforcementEngine:
    """Orchestrates the full governance enforcement pipeline."""

    def __init__(
        self,
        config: GuardianConfig,
        token: str,
        llm_kwargs: dict | None = None,
    ):
        self.config = config
        self.diff_engine = DiffRiskEngine(config=config)
        self.policy_engine = PolicyEngine(config.governance_policy)
        self.checks_client = GitHubChecksClient(token=token)
        self.audit_trail = AuditTrail()

    async def process_pr(
        self,
        repo: str,
        pr_number: int,
        head_sha: str,
        raw_diff: str,
    ) -> PolicyDecision:
        """Full governance pipeline for a PR.

        1. Parse diff into structured data
        2. Run risk analysis
        3. Evaluate against policy
        4. Create GitHub check run
        5. Post PR comment with risk report
        6. Log to audit trail
        """
        # 1. Parse diff
        structured_diff = parse_diff(raw_diff)
        logger.info(
            "Parsed diff for %s#%d: %d files, +%d/-%d lines",
            repo, pr_number, len(structured_diff.files),
            structured_diff.total_additions, structured_diff.total_deletions,
        )

        # 2. Risk analysis
        risk_report = await self.diff_engine.analyze(structured_diff)
        risk_report.pr_number = pr_number
        risk_report.repo = repo
        logger.info(
            "Risk analysis for %s#%d: %d findings, score=%d, decision=%s",
            repo, pr_number, len(risk_report.findings),
            risk_report.risk_score, risk_report.merge_decision.value,
        )

        # 3. Policy evaluation
        policy_decision = self.policy_engine.evaluate(risk_report)
        logger.info(
            "Policy decision for %s#%d: %s, approvals=%s",
            repo, pr_number, policy_decision.action.value,
            policy_decision.required_approvals,
        )

        # 4. GitHub check run
        try:
            await self.checks_client.create_check_run(
                repo=repo,
                head_sha=head_sha,
                report=risk_report,
            )
        except Exception:
            logger.exception("Failed to create check run for %s#%d", repo, pr_number)

        # 5. Post PR comment
        try:
            from server.worker import post_pr_comment
            await post_pr_comment(self.checks_client.token, repo, pr_number, risk_report.to_markdown())
        except Exception:
            logger.exception("Failed to post PR comment for %s#%d", repo, pr_number)

        # 6. Audit trail
        self.audit_trail.log(AuditEntry(
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            merge_decision=policy_decision.action.value,
            risk_score=risk_report.risk_score,
            finding_count=len(risk_report.findings),
            required_approvals=policy_decision.required_approvals,
            deterministic_count=risk_report.deterministic_count,
            llm_count=risk_report.llm_count,
        ))

        return policy_decision

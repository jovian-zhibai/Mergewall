"""GitHub Checks API client.

Creates check runs on commits to enforce merge governance.
Combined with branch protection "Require status checks to pass",
this blocks merges when risk is too high.
"""

from __future__ import annotations

import logging

import httpx

from mergewall.risk.models import MergeDecision, RiskReport

logger = logging.getLogger(__name__)


class GitHubChecksClient:
    """Interacts with the GitHub Checks API to create/update check runs."""

    def __init__(self, token: str, api_base: str = "https://api.github.com"):
        self.token = token
        self.api_base = api_base

    async def create_check_run(
        self,
        repo: str,
        head_sha: str,
        name: str = "Mergewall Governance",
        report: RiskReport | None = None,
    ) -> dict:
        """Create a check run on a commit.

        Maps MergeDecision to GitHub conclusions:
        - BLOCK / REQUIRE_APPROVAL → "action_required" (red X, blocks merge)
        - WARN → "neutral" (gray circle)
        - ALLOW → "success" (green checkmark)
        """
        conclusion = self._decision_to_conclusion(report.merge_decision) if report else "neutral"
        output = report.to_checks_output() if report else {}

        payload = {
            "name": name,
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": conclusion,
            "output": {
                "title": output.get("title", "Mergewall Governance Check"),
                "summary": output.get("summary", ""),
                "annotations": output.get("annotations", [])[:50],  # GitHub caps at 50
            },
        }

        url = f"{self.api_base}/repos/{repo}/check-runs"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                },
                json=payload,
            )
            resp.raise_for_status()

        logger.info("Created check run for %s@%s: %s", repo, head_sha[:8], conclusion)
        return resp.json()

    @staticmethod
    def _decision_to_conclusion(decision: MergeDecision) -> str:
        return {
            MergeDecision.BLOCK: "action_required",
            MergeDecision.REQUIRE_APPROVAL: "action_required",
            MergeDecision.WARN: "neutral",
            MergeDecision.ALLOW: "success",
        }.get(decision, "neutral")

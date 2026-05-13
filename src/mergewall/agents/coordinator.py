"""Coordinator agent that orchestrates the review process and synthesizes results."""


from mergewall.agents.base import BaseReviewAgent, AgentResult, ReviewFinding, Severity
from mergewall.utils.dedup import deduplicate_and_sort


class CoordinatorAgent(BaseReviewAgent):
    """Coordinates multiple review agents and produces the final consolidated report."""

    def __init__(self, **kwargs):
        super().__init__(
            name="CoordinatorAgent",
            description="Orchestrates review agents and synthesizes findings into a final report",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a code review coordinator. Your job is to:
1. Synthesize findings from multiple specialized review agents
2. Resolve conflicting assessments between agents
3. Prioritize findings by actual risk and impact
4. Produce a cohesive, actionable review report

When agents disagree on severity, err on the side of caution. Deduplicate related findings across agents."""

    def get_review_focus(self) -> str:
        return "synthesis, conflict resolution, prioritization, report generation"

    async def synthesize(self, results: list[AgentResult]) -> AgentResult:
        """Synthesize multiple agent results into a consolidated report."""
        all_findings = []
        for result in results:
            all_findings.extend(result.findings)

        deduplicated = deduplicate_and_sort(all_findings)

        risk_score = self._calculate_risk_score(deduplicated)
        summary = self._generate_summary(deduplicated, results, risk_score)

        return AgentResult(
            agent_name="CoordinatorAgent",
            findings=deduplicated,
            summary=summary,
            token_usage=sum(r.token_usage for r in results),
            risk_score=risk_score,
        )

    _RISK_POINTS = {
        Severity.CRITICAL: 25,
        Severity.HIGH: 15,
        Severity.MEDIUM: 5,
        Severity.LOW: 1,
    }

    @staticmethod
    def _calculate_risk_score(findings: list[ReviewFinding]) -> int:
        """Calculate risk score from findings.

        Scoring: CRITICAL=25, HIGH=15, MEDIUM=5, LOW=1. Capped at 100.
        """
        score = sum(
            CoordinatorAgent._RISK_POINTS.get(f.severity, 0)
            for f in findings
        )
        return min(100, score)

    @staticmethod
    def _risk_level(score: int) -> str:
        if score <= 20:
            return "LOW"
        if score <= 50:
            return "MEDIUM"
        if score <= 80:
            return "HIGH"
        return "CRITICAL"

    @staticmethod
    def _risk_emoji(score: int) -> str:
        if score <= 20:
            return "✅"
        if score <= 50:
            return "⚠️"
        if score <= 80:
            return "🔴"
        return "🚨"

    @staticmethod
    def _risk_score_block(findings: list[ReviewFinding], score: int) -> str:
        """Build the risk score summary block."""
        level = CoordinatorAgent._risk_level(score)
        emoji = CoordinatorAgent._risk_emoji(score)
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        parts = []
        for sev in ("critical", "high", "medium", "low"):
            if sev in counts:
                parts.append(f"{counts[sev]} {sev.capitalize()}")
        breakdown = " · ".join(parts)
        return f"{emoji} Risk Score: {level} ({score}/100)\n\n{breakdown}"

    def _generate_summary(
        self,
        findings: list[ReviewFinding],
        agent_results: list[AgentResult],
        risk_score: int = 0,
    ) -> str:
        """Build a human-readable summary with risk score and severity breakdown."""
        severity_counts = {}
        for f in findings:
            severity_counts[f.severity.value] = severity_counts.get(f.severity.value, 0) + 1

        lines = [
            self._risk_score_block(findings, risk_score),
            "",
            f"Review completed with {len(findings)} findings across {len(agent_results)} agents.",
            "Severity breakdown: " + ", ".join(f"{k}: {v}" for k, v in sorted(severity_counts.items())),
        ]

        critical_high = [f for f in findings if f.severity in (Severity.CRITICAL, Severity.HIGH)]
        if critical_high:
            lines.append(f"\n⚠️ {len(critical_high)} critical/high severity issues require immediate attention:")
            for f in critical_high[:5]:
                lines.append(f"  - [{f.severity.value.upper()}] {f.title} ({f.agent})")

        return "\n".join(lines)

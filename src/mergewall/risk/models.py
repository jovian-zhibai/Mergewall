"""Risk engine data models.

Defines the structured output of the Diff Risk Engine: risk categories,
levels, merge decisions, and the full risk report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RiskCategory(Enum):
    """Risk categories for governance analysis. MVP focuses on the first 6."""
    AUTH_BYPASS = "auth_bypass"
    SECRET_LEAKAGE = "secret_leakage"
    API_CONTRACT_BREAKAGE = "api_contract_breakage"
    PERMISSION_ESCALATION = "permission_escalation"
    DANGEROUS_DEPENDENCIES = "dangerous_dependencies"
    BLAST_RADIUS = "blast_radius"
    # Post-MVP:
    INFRA_MUTATION = "infra_mutation"
    SCHEMA_MIGRATION = "schema_migration"
    ARCHITECTURAL_DRIFT = "architectural_drift"
    ASYNC_CONCURRENCY = "async_concurrency"


class RiskLevel(Enum):
    """Severity mapped to governance language."""
    CRITICAL = "critical"    # Block merge, require senior approval
    HIGH = "high"            # Block merge, require approval
    MEDIUM = "medium"        # Warn, require review
    LOW = "low"              # Info only
    NONE = "none"            # No risk detected


class MergeDecision(Enum):
    """The governance decision for the PR."""
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"
    WARN = "warn"
    ALLOW = "allow"


class DetectionMethod(Enum):
    """How the risk was detected."""
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    HYBRID = "hybrid"


_RISK_LEVEL_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "none": 4,
}


@dataclass
class RiskEvidence:
    """Concrete evidence for a risk finding."""
    file_path: str
    line_numbers: list[int] = field(default_factory=list)
    code_snippet: str = ""
    pattern_matched: str = ""
    detection_method: DetectionMethod = DetectionMethod.DETERMINISTIC


@dataclass
class RiskFinding:
    """A single risk finding from the Diff Risk Engine."""
    category: RiskCategory
    level: RiskLevel
    title: str
    why_dangerous: str
    impact_scope: str
    evidence: RiskEvidence
    merge_decision: MergeDecision
    approval_required: list[str] = field(default_factory=list)
    fix_suggestion: str = ""
    confidence: float = 1.0


@dataclass
class RiskReport:
    """The complete risk assessment for a PR."""
    pr_number: int
    repo: str
    findings: list[RiskFinding] = field(default_factory=list)
    merge_decision: MergeDecision = MergeDecision.ALLOW
    risk_score: int = 0
    summary: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deterministic_count: int = 0
    llm_count: int = 0

    def to_checks_output(self) -> dict:
        """Format for GitHub Checks API output."""
        annotations = []
        for finding in self.findings:
            for line_num in finding.evidence.line_numbers:
                if len(annotations) >= 50:  # GitHub caps at 50
                    break
                annotations.append({
                    "path": finding.evidence.file_path,
                    "start_line": line_num,
                    "end_line": line_num,
                    "annotation_level": _level_to_annotation(finding.level),
                    "title": finding.title,
                    "message": finding.why_dangerous,
                })
            if len(annotations) >= 50:
                break

        return {
            "title": _decision_title(self.merge_decision, self.risk_score),
            "summary": self._build_summary_md(),
            "annotations": annotations,
        }

    def to_markdown(self) -> str:
        """Format as PR comment markdown."""
        emoji = _decision_emoji(self.merge_decision)
        lines = [
            f"{emoji} **Merge {_decision_label(self.merge_decision)}**",
            "",
            f"**Risk Score:** {self.risk_score}/100",
            "",
        ]

        if self.findings:
            lines.append("### Risk Findings")
            lines.append("")
            for f in self.findings:
                level_emoji = _level_emoji(f.level)
                lines.append(f"{level_emoji} **[{f.level.value.upper()}]** {f.title}")
                lines.append(f"  - **Category:** {f.category.value}")
                lines.append(f"  - **Why dangerous:** {f.why_dangerous}")
                lines.append(f"  - **Impact:** {f.impact_scope}")
                if f.evidence.file_path:
                    loc = f.evidence.file_path
                    if f.evidence.line_numbers:
                        loc += f":{','.join(str(l) for l in f.evidence.line_numbers[:5])}"
                    lines.append(f"  - **Location:** `{loc}`")
                if f.fix_suggestion:
                    lines.append(f"  - **Fix:** {f.fix_suggestion}")
                if f.approval_required:
                    lines.append(f"  - **Requires approval from:** {', '.join(f.approval_required)}")
                lines.append("")
        else:
            lines.append("No risks detected.")
            lines.append("")

        lines.append(f"*Deterministic: {self.deterministic_count} | LLM: {self.llm_count}*")
        return "\n".join(lines)

    def _build_summary_md(self) -> str:
        parts = [f"Risk score: {self.risk_score}/100"]
        if self.findings:
            by_level: dict[str, int] = {}
            for f in self.findings:
                by_level[f.level.value] = by_level.get(f.level.value, 0) + 1
            parts.append(" | ".join(f"{v} {k}" for k, v in sorted(by_level.items())))
        return ". ".join(parts)


def _level_to_annotation(level: RiskLevel) -> str:
    return {
        RiskLevel.CRITICAL: "failure",
        RiskLevel.HIGH: "failure",
        RiskLevel.MEDIUM: "warning",
        RiskLevel.LOW: "notice",
        RiskLevel.NONE: "notice",
    }.get(level, "notice")


def _decision_title(decision: MergeDecision, score: int) -> str:
    return {
        MergeDecision.BLOCK: f"Merge Blocked (risk score: {score})",
        MergeDecision.REQUIRE_APPROVAL: f"Approval Required (risk score: {score})",
        MergeDecision.WARN: f"Warnings (risk score: {score})",
        MergeDecision.ALLOW: f"Approved (risk score: {score})",
    }.get(decision, f"Risk Score: {score}")


def _decision_label(decision: MergeDecision) -> str:
    return {
        MergeDecision.BLOCK: "Blocked",
        MergeDecision.REQUIRE_APPROVAL: "Requires Approval",
        MergeDecision.WARN: "Allowed with Warnings",
        MergeDecision.ALLOW: "Allowed",
    }.get(decision, "Unknown")


def _decision_emoji(decision: MergeDecision) -> str:
    return {
        MergeDecision.BLOCK: "\U0001f6a8",
        MergeDecision.REQUIRE_APPROVAL: "⚠️",
        MergeDecision.WARN: "ℹ️",
        MergeDecision.ALLOW: "✅",
    }.get(decision, "❓")


def _level_emoji(level: RiskLevel) -> str:
    return {
        RiskLevel.CRITICAL: "\U0001f534",
        RiskLevel.HIGH: "\U0001f7e0",
        RiskLevel.MEDIUM: "\U0001f7e1",
        RiskLevel.LOW: "\U0001f7e2",
        RiskLevel.NONE: "⚪",
    }.get(level, "⚪")

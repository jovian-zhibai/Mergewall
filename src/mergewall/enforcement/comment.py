"""PR comment formatting for governance reports.

Renders a RiskReport into a human-readable PR comment using a template.
"""

from __future__ import annotations

import re
from pathlib import Path

from mergewall.risk.models import MergeDecision, RiskReport

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "pr_comment.md"

_LEVEL_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
    "none": "⚪",
}


def format_pr_comment(report: RiskReport) -> str:
    """Render a RiskReport as a PR comment markdown string.

    Uses a simple string-template engine (no Jinja2 dependency).
    """
    template = _load_template()
    return _render(template, report)


def _load_template() -> str:
    if _TEMPLATE_PATH.is_file():
        return _TEMPLATE_PATH.read_text(encoding="utf-8")
    return _DEFAULT_TEMPLATE


def _render(template: str, report: RiskReport) -> str:
    # Decision label
    decision_label = {
        MergeDecision.BLOCK: "BLOCK",
        MergeDecision.REQUIRE_APPROVAL: "REQUIRE APPROVAL",
        MergeDecision.WARN: "WARN",
        MergeDecision.ALLOW: "ALLOW",
    }.get(report.merge_decision, report.merge_decision.value.upper())

    result = template.replace("{{ decision }}", decision_label)
    result = result.replace("{{ score }}", str(report.risk_score))

    # Findings block
    if report.findings:
        findings_md = _render_findings(report)
        # Replace the findings loop block
        result = re.sub(
            r"\{\%\s*if findings\s*\%\}.*?\{\%\s*endif\s*\%\}",
            findings_md,
            result,
            flags=re.DOTALL,
        )
    else:
        result = re.sub(
            r"\{\%\s*if findings\s*\%\}.*?\{\%\s*endif\s*\%\}",
            "\nNo risks detected.\n",
            result,
            flags=re.DOTALL,
        )

    # For loop inside findings
    result = re.sub(r"\{\%\s*for finding in findings\s*\%\}(.*?)\{\%\s*endfor\s*\%\}", "", result, flags=re.DOTALL)

    # What to do block
    result = _render_decision_block(result, report)

    # Clean up any remaining template tags
    result = re.sub(r"\{\{.*?\}\}", "", result)
    result = re.sub(r"\{\%.*?\%\}", "", result)

    return result.strip() + "\n"


def _render_findings(report: RiskReport) -> str:
    lines = ["### Findings\n"]
    for f in report.findings:
        emoji = _LEVEL_EMOJI.get(f.level.value, "⚪")
        lines.append(f"#### {emoji} [{f.level.value.upper()}] {f.category.value}")
        loc = f"`{f.evidence.file_path}`"
        if f.evidence.line_numbers:
            loc += f" (line {f.evidence.line_numbers[0]})"
        lines.append(f"- **File:** {loc}")
        lines.append(f"- **Issue:** {f.why_dangerous}")
        if f.fix_suggestion:
            lines.append(f"- **Fix:** {f.fix_suggestion}")
        lines.append("")
    return "\n".join(lines)


def _render_decision_block(template: str, report: RiskReport) -> str:
    decision_val = report.merge_decision.value.upper()
    if report.merge_decision == MergeDecision.BLOCK:
        block = "🔴 Fix the issues above and push again. Mergewall will re-evaluate automatically."
    elif report.merge_decision == MergeDecision.REQUIRE_APPROVAL:
        approvers = "security-team"  # could extract from findings
        block = f"🟡 Request approval from **{approvers}** to proceed."
    elif report.merge_decision == MergeDecision.WARN:
        block = "⚠️ Review the findings above and use your judgment before merging."
    else:
        block = "✅ No blocking issues — safe to merge."

    # Replace if/elif/else template blocks with concrete text
    result = re.sub(
        r"\{\%\s*if decision == \"BLOCK\"\s*\%\}.*?\{\%\s*elif decision == \"REQUIRE_APPROVAL\"\s*\%\}.*?\{\%\s*elif decision == \"WARN\"\s*\%\}.*?\{\%\s*else\s*\%\}.*?\{\%\s*endif\s*\%\}",
        block,
        template,
        flags=re.DOTALL,
    )
    return result


_DEFAULT_TEMPLATE = """## 🛡️ Mergewall Governance Report

**Decision: {{ decision }}** | Risk Score: {{ score }}/100

{% if findings %}
### Findings
{% for finding in findings %}
#### {{ finding.level }} — {{ finding.category }}
- **File:** `{{ finding.file }}` (line {{ finding.line }})
- **Issue:** {{ finding.description }}
- **Fix:** {{ finding.suggestion }}
{% endfor %}
{% endif %}

### What to do
{% if decision == "BLOCK" %}
🔴 Fix the issues above and push again. Mergewall will re-evaluate automatically.
{% elif decision == "REQUIRE_APPROVAL" %}
🟡 Request approval from **{{ required_approvers }}** to proceed.
{% elif decision == "WARN" %}
⚠️ Review the findings above and use your judgment before merging.
{% else %}
✅ No blocking issues — safe to merge.
{% endif %}

---
*Powered by [Mergewall](https://github.com/jovian-zhibai/Mergewall)*
"""

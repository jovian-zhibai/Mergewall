"""SARIF output for GitHub Code Scanning integration.

Converts a RiskReport into SARIF v2.1.0 JSON for upload to GitHub Code Scanning.
"""

from __future__ import annotations

from mergewall.risk.models import RiskLevel, RiskReport

SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-schema-2.1.0.json"


def to_sarif(report: RiskReport, tool_version: str = "0.1.0") -> dict:
    """Convert a RiskReport to SARIF v2.1.0 JSON."""
    results = []
    for finding in report.findings:
        level = _level_to_sarif(finding.level)
        result = {
            "ruleId": _category_to_rule_id(finding.category.value),
            "level": level,
            "message": {
                "text": f"[{finding.level.value.upper()}] {finding.title}: {finding.why_dangerous}"
            },
        }
        if finding.evidence.file_path:
            location = {
                "physicalLocation": {
                    "artifactLocation": {"uri": finding.evidence.file_path},
                }
            }
            line = finding.evidence.line_numbers[0] if finding.evidence.line_numbers else 1
            location["physicalLocation"]["region"] = {"startLine": line}
            result["locations"] = [location]
        if finding.fix_suggestion:
            result.setdefault("fixes", []).append({
                "description": {"text": finding.fix_suggestion}
            })
        results.append(result)

    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Mergewall",
                    "version": tool_version,
                    "informationUri": "https://github.com/jovian-zhibai/Mergewall",
                    "rules": _build_rules(report),
                }
            },
            "results": results,
        }],
    }


def _level_to_sarif(level: RiskLevel) -> str:
    return {
        RiskLevel.CRITICAL: "error",
        RiskLevel.HIGH: "error",
        RiskLevel.MEDIUM: "warning",
        RiskLevel.LOW: "warning",
        RiskLevel.NONE: "note",
    }.get(level, "warning")


def _category_to_rule_id(category: str) -> str:
    return category.replace("_", "-")


def _build_rules(report: RiskReport) -> list[dict]:
    seen = set()
    rules = []
    for finding in report.findings:
        rule_id = _category_to_rule_id(finding.category.value)
        if rule_id not in seen:
            seen.add(rule_id)
            rules.append({
                "id": rule_id,
                "shortDescription": {"text": finding.category.value.replace("_", " ").title()},
                "fullDescription": {"text": finding.title},
                "helpUri": "https://github.com/jovian-zhibai/Mergewall#risk-categories",
            })
    return rules

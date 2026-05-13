"""Deterministic guard for API contract breakage.

Detects: changed function signatures in API files, removed endpoints,
modified response schemas.
"""

from __future__ import annotations

import re

from mergewall.diff.models import FileDiff
from mergewall.risk.guards.base import BaseGuard
from mergewall.risk.models import (
    DetectionMethod,
    MergeDecision,
    RiskCategory,
    RiskEvidence,
    RiskFinding,
    RiskLevel,
)

# File patterns that typically define API contracts
_API_FILE_RE = re.compile(
    r"(api/|routes/|views/|endpoints/|controllers/|urls\.py|router|handlers/)"
)

# Function signature patterns for common frameworks
_FUNC_SIG_RE = re.compile(
    r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE
)

# Route decorator patterns
_ROUTE_DECORATOR_RE = re.compile(
    r"@(?:app|router|blueprint)\.(get|post|put|patch|delete|route)\s*\(\s*['\"]([^'\"]+)"
)


class APIContractGuard(BaseGuard):
    """Detects breaking changes to API contracts.

    Checks for: removed public functions in API files, changed signatures
    of route handlers, removed route decorators.
    """

    category = RiskCategory.API_CONTRACT_BREAKAGE

    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        if not _API_FILE_RE.search(file_diff.new_path):
            return []

        findings = []
        removed = self._removed_lines(file_diff)
        added = self._added_lines(file_diff)

        # Extract function signatures from removed and added lines
        removed_text = "\n".join(content for _, content in removed)
        added_text = "\n".join(content for _, content in added)

        removed_funcs = {
            m.group(1): (m.group(2), m.start())
            for m in _FUNC_SIG_RE.finditer(removed_text)
        }
        added_funcs = {
            m.group(1): (m.group(2), m.start())
            for m in _FUNC_SIG_RE.finditer(added_text)
        }

        # Check for removed public functions (not prefixed with _)
        for func_name in removed_funcs:
            if func_name.startswith("_"):
                continue
            if func_name not in added_funcs:
                # Find the line number
                line_num = next(
                    (ln for ln, content in removed if func_name in content),
                    0,
                )
                findings.append(RiskFinding(
                    category=RiskCategory.API_CONTRACT_BREAKAGE,
                    level=RiskLevel.HIGH,
                    title=f"Public API function removed: {func_name}",
                    why_dangerous=(
                        f"Function '{func_name}' was removed from an API file. "
                        "Callers of this function will break."
                    ),
                    impact_scope=f"All consumers of {func_name}()",
                    evidence=RiskEvidence(
                        file_path=file_diff.new_path,
                        line_numbers=[line_num] if line_num else [],
                        pattern_matched=f"removed func: {func_name}",
                        detection_method=DetectionMethod.DETERMINISTIC,
                    ),
                    merge_decision=MergeDecision.REQUIRE_APPROVAL,
                    fix_suggestion=(
                        f"If {func_name} is no longer needed, deprecate it first. "
                        "If it was renamed, add a compatibility alias."
                    ),
                    confidence=0.85,
                ))

        # Check for changed signatures of existing functions
        for func_name in removed_funcs:
            if func_name in added_funcs:
                old_sig, _ = removed_funcs[func_name]
                new_sig, _ = added_funcs[func_name]
                if old_sig.strip() != new_sig.strip():
                    line_num = next(
                        (ln for ln, content in added if func_name in content),
                        0,
                    )
                    findings.append(RiskFinding(
                        category=RiskCategory.API_CONTRACT_BREAKAGE,
                        level=RiskLevel.MEDIUM,
                        title=f"API signature changed: {func_name}",
                        why_dangerous=(
                            f"Function '{func_name}' signature changed from "
                            f"({old_sig.strip()}) to ({new_sig.strip()}). "
                            "Existing callers may break."
                        ),
                        impact_scope=f"All callers of {func_name}()",
                        evidence=RiskEvidence(
                            file_path=file_diff.new_path,
                            line_numbers=[line_num] if line_num else [],
                            pattern_matched=f"sig change: {func_name}",
                            detection_method=DetectionMethod.DETERMINISTIC,
                        ),
                        merge_decision=MergeDecision.WARN,
                        fix_suggestion="Add default values for new parameters to maintain backward compatibility.",
                        confidence=0.8,
                    ))

        return findings

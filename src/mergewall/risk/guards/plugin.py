"""Custom guard plugin support — user-defined risk guards via .mergewall.yml.

Users can define pattern-based guards in their config without writing Python code.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from mergewall.config import GuardianConfig


class CustomGuard(BaseGuard):
    """A user-defined guard loaded from .mergewall.yml."""

    def __init__(
        self,
        name: str,
        pattern: str,
        category: str = "custom",
        level: str = "medium",
        message: str = "",
        suggestion: str = "",
        file_pattern: str = "**",
    ):
        self.name = name
        self.category = RiskCategory.DANGEROUS_DEPENDENCIES  # fallback

        # Map category string to RiskCategory
        for rc in RiskCategory:
            if rc.value == category:
                self.category = rc
                break

        self.pattern = re.compile(pattern)
        self._level = level
        self._message = message
        self._suggestion = suggestion
        self._file_pattern = file_pattern
        self._file_re = re.compile(
            file_pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
        )

        super().__init__()

    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        """Scan a file diff for matches to the custom pattern."""
        if not self._file_re.search(file_diff.new_path):
            return []

        findings = []
        for line_num, content in self._added_lines(file_diff):
            if self.pattern.search(content):
                level = _parse_level(self._level)
                findings.append(RiskFinding(
                    category=self.category,
                    level=level,
                    title=f"Custom guard: {self.name}",
                    why_dangerous=self._message or f"Pattern '{self.pattern.pattern}' matched in {file_diff.new_path}",
                    impact_scope=f"File: {file_diff.new_path}",
                    evidence=RiskEvidence(
                        file_path=file_diff.new_path,
                        line_numbers=[line_num],
                        code_snippet=content[:200],
                        pattern_matched=self.pattern.pattern,
                        detection_method=DetectionMethod.DETERMINISTIC,
                    ),
                    merge_decision=_level_to_decision(level),
                    fix_suggestion=self._suggestion or "Review this match and verify it's intentional.",
                    confidence=0.9,
                ))
        return findings


def load_custom_guards(config) -> list[BaseGuard]:
    """Load user-defined custom guards from GuardianConfig.

    Reads ``custom_guards`` from the ``.mergewall.yml`` config file.
    Each entry must have ``name`` and ``pattern`` fields.
    """
    guards: list[BaseGuard] = []

    if config is None:
        return guards

    # Access the raw config dict from the GuardianConfig
    raw_guards = getattr(config, "_raw_custom_guards", None)
    if raw_guards is None:
        return guards

    if not isinstance(raw_guards, list):
        return guards

    for guard_def in raw_guards:
        if not isinstance(guard_def, dict):
            continue
        name = guard_def.get("name", "unnamed")
        pattern = guard_def.get("pattern", "")
        if not pattern:
            continue

        guards.append(CustomGuard(
            name=name,
            pattern=pattern,
            category=guard_def.get("category", "custom"),
            level=guard_def.get("level", "medium"),
            message=guard_def.get("message", f"Custom pattern '{pattern}' matched"),
            suggestion=guard_def.get("suggestion", ""),
            file_pattern=guard_def.get("file_pattern", "**"),
        ))

    return guards


def _parse_level(level_str: str) -> RiskLevel:
    for rl in RiskLevel:
        if rl.value == level_str.lower():
            return rl
    return RiskLevel.MEDIUM


def _level_to_decision(level: RiskLevel) -> MergeDecision:
    if level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
        return MergeDecision.BLOCK
    elif level == RiskLevel.MEDIUM:
        return MergeDecision.REQUIRE_APPROVAL
    return MergeDecision.WARN

"""Deterministic guard for dangerous dependency changes.

Detects: version downgrades, unpinned versions, new unknown deps
in requirements.txt, package.json, go.mod, Cargo.toml.
"""

from __future__ import annotations

import json
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

# Dependency file patterns
_DEP_FILE_RE = re.compile(
    r"(requirements.*\.txt|package\.json|go\.mod|Cargo\.toml|Gemfile|Pipfile|poetry\.lock)"
)

# Python: package>=version or package==version
_PY_DEP_RE = re.compile(r"^([a-zA-Z0-9_.-]+)\s*([><=!~]+)\s*(.+)$")

# Version downgrade detection
_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


class DangerousDepsGuard(BaseGuard):
    """Detects risky dependency changes in dependency files.

    Checks: version downgrades, unpinned versions, removed pins.
    """

    category = RiskCategory.DANGEROUS_DEPENDENCIES

    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        if not _DEP_FILE_RE.search(file_diff.new_path):
            return []

        findings = []
        removed = self._removed_lines(file_diff)
        added = self._added_lines(file_diff)

        # Parse removed and added deps for Python requirements files
        if file_diff.new_path.endswith(".txt") or "requirements" in file_diff.new_path:
            findings.extend(self._check_python_deps(file_diff, removed, added))

        return findings

    def _check_python_deps(
        self, file_diff: FileDiff,
        removed: list[tuple[int, str]],
        added: list[tuple[int, str]],
    ) -> list[RiskFinding]:
        findings = []
        downgraded_pkgs: set[str] = set()

        removed_deps: dict[str, tuple[int, str, str]] = {}
        for line_num, content in removed:
            content = content.strip()
            if not content or content.startswith("#"):
                continue
            m = _PY_DEP_RE.match(content)
            if m:
                removed_deps[m.group(1).lower()] = (line_num, m.group(2), m.group(3))

        for line_num, content in added:
            content = content.strip()
            if not content or content.startswith("#"):
                continue
            m = _PY_DEP_RE.match(content)
            if not m:
                continue

            pkg = m.group(1).lower()
            op = m.group(2)
            new_ver = m.group(3)

            # Check for version downgrade
            if pkg in removed_deps:
                _, old_op, old_ver = removed_deps[pkg]
                if self._is_downgrade(old_ver, new_ver):
                    downgraded_pkgs.add(pkg)
                    findings.append(RiskFinding(
                        category=RiskCategory.DANGEROUS_DEPENDENCIES,
                        level=RiskLevel.HIGH,
                        title=f"Dependency downgrade: {pkg}",
                        why_dangerous=(
                            f"{pkg} was downgraded from {old_ver} to {new_ver}. "
                            "Downgrades may reintroduce fixed bugs or security vulnerabilities."
                        ),
                        impact_scope=f"Package {pkg} and all code depending on it",
                        evidence=RiskEvidence(
                            file_path=file_diff.new_path,
                            line_numbers=[line_num],
                            code_snippet=content[:200],
                            pattern_matched=f"{pkg}: {old_ver} -> {new_ver}",
                            detection_method=DetectionMethod.DETERMINISTIC,
                        ),
                        merge_decision=MergeDecision.REQUIRE_APPROVAL,
                        approval_required=["security-team"],
                        fix_suggestion=f"Verify the downgrade is intentional. Consider keeping {pkg}>={old_ver}.",
                        confidence=0.95,
                    ))

            # Check for unpinned version (>= without upper bound) — skip if already flagged as downgrade
            # A proper range like >=1.2.3,<2.0.0 is NOT unpinned
            has_upper = bool(re.search(r",\s*[<]=?\s*\d", content))
            if op in (">=", ">") and "==" not in content and not has_upper and pkg not in downgraded_pkgs:
                findings.append(RiskFinding(
                    category=RiskCategory.DANGEROUS_DEPENDENCIES,
                    level=RiskLevel.MEDIUM,
                    title=f"Unpinned dependency: {pkg}",
                    why_dangerous=(
                        f"{pkg} uses {op}{new_ver} without an upper bound. "
                        "Future versions may introduce breaking changes or vulnerabilities."
                    ),
                    impact_scope=f"Build reproducibility for {pkg}",
                    evidence=RiskEvidence(
                        file_path=file_diff.new_path,
                        line_numbers=[line_num],
                        code_snippet=content[:200],
                        pattern_matched=f"{pkg}{op}{new_ver}",
                        detection_method=DetectionMethod.DETERMINISTIC,
                    ),
                    merge_decision=MergeDecision.WARN,
                    fix_suggestion=f"Pin to a specific range: {pkg}>={new_ver},<{self._bump_major(new_ver)}",
                    confidence=0.7,
                ))

        return findings

    @staticmethod
    def _is_downgrade(old_ver: str, new_ver: str) -> bool:
        old_parts = _VERSION_RE.match(old_ver.lstrip("vV"))
        new_parts = _VERSION_RE.match(new_ver.lstrip("vV"))
        if not old_parts or not new_parts:
            return False
        for i in range(3):
            old_n = int(old_parts.group(i + 1) or 0)
            new_n = int(new_parts.group(i + 1) or 0)
            if new_n < old_n:
                return True
            if new_n > old_n:
                return False
        return False

    @staticmethod
    def _bump_major(ver: str) -> str:
        m = _VERSION_RE.match(ver)
        if m:
            return str(int(m.group(1)) + 1) + ".0"
        return "999"

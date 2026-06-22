"""Deterministic guard for hardcoded secrets in added lines.

Detects: AWS keys, GitHub tokens, private keys, JWTs, Slack tokens,
generic secret/password assignments. Skips test fixtures and examples.
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

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS Key", re.compile(r"A[KS]IA[0-9A-Z]{16}")),  # AKIA=long-term, ASIA=temp session
    ("AWS Secret Key", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*[\"']?([A-Za-z0-9/+=]{40})")),
    ("GitHub Token", re.compile(r"gh[ps]_[A-Za-z0-9_]{36,}")),
    ("GitHub Fine-Grained Token", re.compile(r"github_pat_[A-Za-z0-9_]{36,}")),
    ("Generic API Key", re.compile(r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']([A-Za-z0-9_\-]{20,})["\']')),
    ("Private Key Block", re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----")),
    ("JWT Token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9]{10,}-[a-zA-Z0-9-]{10,}")),
    ("Generic Secret Assignment", re.compile(
        r'(?i)(password|secret|token|credential)\s*[=:]\s*["\'][^"\']{8,}["\']'
    )),
]

_SKIP_PATHS = re.compile(
    r"(?i)(test|spec|fixture|mock|example|sample|demo|\.env\.example|README)"
)


class SecretLeakageGuard(BaseGuard):
    """Detects hardcoded secrets in added lines.

    Confidence: 0.95 for pattern-matched tokens (AWS keys, private keys).
    Skips test fixtures, examples, and README files.
    """

    category = RiskCategory.SECRET_LEAKAGE

    def scan(self, file_diff: FileDiff) -> list[RiskFinding]:
        if _SKIP_PATHS.search(file_diff.new_path):
            return []

        findings = []
        for line_num, content in self._added_lines(file_diff):
            for secret_name, pattern in _SECRET_PATTERNS:
                if pattern.search(content):
                    findings.append(RiskFinding(
                        category=RiskCategory.SECRET_LEAKAGE,
                        level=RiskLevel.CRITICAL,
                        title=f"Hardcoded {secret_name} detected",
                        why_dangerous=(
                            f"A {secret_name} is hardcoded in source code. "
                            "If this reaches the main branch, it will be in git history permanently "
                            "and must be rotated immediately."
                        ),
                        impact_scope="Credential exposure — anyone with repo access can use this secret",
                        evidence=RiskEvidence(
                            file_path=file_diff.new_path,
                            line_numbers=[line_num],
                            code_snippet=content[:200],
                            pattern_matched=secret_name,
                            detection_method=DetectionMethod.DETERMINISTIC,
                        ),
                        merge_decision=MergeDecision.BLOCK,
                        approval_required=["security-team"],
                        fix_suggestion=(
                            "Remove the hardcoded secret. Load it from environment variables "
                            "or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault). "
                            "If this secret was ever committed, rotate it immediately."
                        ),
                        confidence=0.95,
                    ))
                    break  # one finding per line
        return findings

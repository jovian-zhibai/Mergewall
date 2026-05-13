"""Policy engine data models.

Defines governance policies: path-based rules, threshold rules,
and the policy decision output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PolicyAction(Enum):
    """Action the policy engine can take."""
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"
    WARN = "warn"
    ALLOW = "allow"


@dataclass
class PathRule:
    """A policy rule scoped to specific file paths.

    First match wins — rules are evaluated in order.
    """
    paths: list[str]            # glob patterns: ["src/auth/**", "migrations/**"]
    risk_categories: list[str]  # ["auth_bypass", "secret_leakage"] or ["*"]
    min_level: str = "high"     # "critical", "high", "medium", "low"
    action: PolicyAction = PolicyAction.BLOCK
    require_approval_from: list[str] = field(default_factory=list)


@dataclass
class ThresholdRule:
    """A policy rule based on overall risk score thresholds."""
    min_score: int
    action: PolicyAction = PolicyAction.REQUIRE_APPROVAL
    require_approval_from: list[str] = field(default_factory=list)


@dataclass
class GovernancePolicy:
    """The complete governance policy for a repository."""
    mode: str = "governance"    # "governance" or "review" (legacy)
    path_rules: list[PathRule] = field(default_factory=list)
    threshold_rules: list[ThresholdRule] = field(default_factory=list)
    default_action: PolicyAction = PolicyAction.ALLOW
    min_confidence: float = 0.7


@dataclass
class FindingDecision:
    """Policy decision for a single risk finding."""
    finding_title: str
    finding_category: str
    action: PolicyAction
    required_approvals: list[str] = field(default_factory=list)
    matched_rule: str = ""


@dataclass
class PolicyDecision:
    """The overall policy decision for a PR."""
    action: PolicyAction
    required_approvals: list[str] = field(default_factory=list)
    finding_decisions: list[FindingDecision] = field(default_factory=list)
    risk_score: int = 0
    reason: str = ""

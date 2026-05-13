"""Audit trail data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AuditEntry:
    """A single audit log entry for a governance decision."""
    repo: str
    pr_number: int
    head_sha: str
    merge_decision: str
    risk_score: int
    finding_count: int
    required_approvals: list[str] = field(default_factory=list)
    deterministic_count: int = 0
    llm_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str = ""
    approved_by: list[str] = field(default_factory=list)

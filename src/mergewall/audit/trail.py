"""Audit trail logger.

Appends governance decisions to a JSONL file for compliance and debugging.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from mergewall.audit.models import AuditEntry

logger = logging.getLogger(__name__)


class AuditTrail:
    """Logs governance decisions to a JSONL file.

    Location: .mergewall/audit.jsonl (in the working directory).
    Format: one JSON object per line, append-only.
    """

    def __init__(self, log_dir: str = ".mergewall"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit.jsonl"

    def log(self, entry: AuditEntry) -> None:
        """Append an audit entry to the log file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
            logger.info(
                "Audit: %s#%d — %s (score=%d, findings=%d)",
                entry.repo, entry.pr_number, entry.merge_decision,
                entry.risk_score, entry.finding_count,
            )
        except Exception:
            logger.exception("Failed to write audit entry")

    def query(
        self,
        repo: str | None = None,
        since: str | None = None,
        decision: str | None = None,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters."""
        entries: list[AuditEntry] = []
        if not self.log_file.exists():
            return entries
        for line in self.log_file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if repo and data.get("repo") != repo:
                continue
            if decision and data.get("merge_decision") != decision:
                continue
            if since and data.get("timestamp", "") < since:
                continue
            entries.append(AuditEntry(**{k: v for k, v in data.items() if k in AuditEntry.__dataclass_fields__}))
        return entries

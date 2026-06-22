"""Repo Memory — tracks historical risk data per directory/module.

Stores risk history in .mergewall/memory.json for long-term
pattern detection and hotspot identification.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class RepoMemory:
    """Tracks historical risk data per directory/module."""

    def __init__(self, memory_dir: str = ".mergewall"):
        self.memory_file = Path(memory_dir) / "memory.json"
        self.data: dict = self._load()

    def _load(self) -> dict:
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text())
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load memory file, starting fresh")
        return {"modules": {}, "last_updated": ""}

    def _save(self) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(json.dumps(self.data, indent=2))

    def record_risk(self, file_path: str, category: str, level: str) -> None:
        """Record a risk finding for a file path."""
        module = self._extract_module(file_path)
        if module not in self.data["modules"]:
            self.data["modules"][module] = {
                "total_findings": 0,
                "by_category": {},
                "risk_history": [],
            }

        mod = self.data["modules"][module]
        mod["total_findings"] += 1
        mod["by_category"][category] = mod["by_category"].get(category, 0) + 1
        mod["risk_history"].append({
            "category": category,
            "level": level,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep only last 100 history entries per module
        if len(mod["risk_history"]) > 100:
            mod["risk_history"] = mod["risk_history"][-100:]

        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def get_hotspots(self, limit: int = 10) -> list[tuple[str, int]]:
        """Return the top N riskiest modules."""
        modules = self.data.get("modules", {})
        ranked = sorted(modules.items(), key=lambda x: x[1]["total_findings"], reverse=True)
        return [(name, data["total_findings"]) for name, data in ranked[:limit]]

    def get_module_risk(self, module: str) -> dict | None:
        """Get risk data for a specific module."""
        return self.data.get("modules", {}).get(module)

    @staticmethod
    def _extract_module(file_path: str) -> str:
        """Extract the top-level module directory from a file path."""
        parts = file_path.split("/")
        if len(parts) >= 2:
            return parts[0] + "/" + parts[1]
        return file_path

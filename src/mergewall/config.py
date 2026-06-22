"""Configuration loader for CodeGuardian.

Reads ``.mergewall.yml`` from a given path (defaults to the current
working directory) and exposes a typed ``GuardianConfig`` object used by
the workflow, CLI, and batch processor to decide which agents to run,
which files to skip, and the minimum severity to report.
"""

from __future__ import annotations

import fnmatch
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from mergewall.agents.base import Severity
from mergewall.policy.models import GovernancePolicy, PathRule, PolicyAction, ThresholdRule

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_FILENAME = ".mergewall.yml"

# Cache for loaded config to avoid re-reading from disk on every agent construction.
_config_cache: GuardianConfig | None = None
_config_cache_path: str | None = None



@dataclass
class AgentConfig:
    """Per-agent configuration read from the YAML file."""

    enabled: bool = True
    severity_threshold: Optional[str] = None


@dataclass
class GuardianConfig:
    """Top-level configuration object loaded from ``.mergewall.yml``."""

    MODEL_PRESETS: dict[str, dict[str, str]] = field(default_factory=lambda: {
        "mimo": {"base_url": "https://api.xiaomimimo.com/v1", "model": "mimo-v2.5-pro"},
        "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
        "deepseek": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
        "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
        "glm": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4"},
        "kimi": {"base_url": "https://api.moonshot.cn/v1", "model": "kimi"},
        "anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-sonnet-4-20250514", "provider": "anthropic"},
        "claude": {"base_url": "https://api.anthropic.com", "model": "claude-sonnet-4-20250514", "provider": "anthropic"},
    })

    model: Optional[str] = None
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    ignore: list[str] = field(default_factory=list)
    governance_policy: GovernancePolicy = field(default_factory=GovernancePolicy)

    @property
    def governance_mode(self) -> bool:
        return self.governance_policy.mode == "governance"

    # ---- helpers ----

    def resolve_preset(self, model_name: Optional[str]) -> dict[str, str]:
        """Resolve a model name against MODEL_PRESETS.

        If *model_name* matches a preset key, return the preset dict
        (with ``base_url``, ``model``, and optionally ``provider``).
        Otherwise return an empty dict — the caller falls through to
        env-var / default logic.
        """
        if model_name and model_name in self.MODEL_PRESETS:
            return dict(self.MODEL_PRESETS[model_name])
        return {}

    def is_agent_enabled(self, agent_name: str) -> bool:
        """Return *True* if the given agent is enabled in the config."""
        cfg = self.agents.get(agent_name)
        return cfg.enabled if cfg is not None else True

    def get_severity_threshold(self, agent_name: str) -> Optional[Severity]:
        """Return the minimum severity for *agent_name*, or ``None`` if unset."""
        cfg = self.agents.get(agent_name)
        if cfg is None or cfg.severity_threshold is None:
            return None
        try:
            return Severity(cfg.severity_threshold.lower())
        except ValueError:
            logger.warning("Invalid severity_threshold '%s' for agent %s", cfg.severity_threshold, agent_name)
            return None

    def should_ignore(self, file_path: str) -> bool:
        """Return *True* if *file_path* matches any ignore pattern.

        For patterns containing ``**``, the prefix (before ``**``) is matched
        with :func:`fnmatch.fnmatch` against each ancestor directory, and the
        suffix (after ``**``) is matched against the file path or name.  Plain
        patterns are matched directly against the full path.
        """
        for pat in self.ignore:
            if "**" not in pat:
                if fnmatch.fnmatch(file_path, pat):
                    return True
                continue

            prefix = pat.split("**")[0]
            suffix = pat.split("**")[-1].lstrip("/").lstrip(os.sep)

            # Match prefix against file_path and all its parent directories
            prefix_match = False
            if prefix:
                check = file_path
                while check:
                    if fnmatch.fnmatch(check, prefix.rstrip("/").rstrip(os.sep)):
                        prefix_match = True
                        break
                    check = os.path.dirname(check)
            else:
                prefix_match = True

            if not prefix_match:
                continue

            if not suffix:
                return True
            basename = os.path.basename(file_path) if os.sep in file_path or "/" in file_path else file_path
            if fnmatch.fnmatch(file_path, suffix) or fnmatch.fnmatch(basename, suffix):
                return True

        return False


def load_config(path: Optional[str | Path] = None) -> GuardianConfig:
    """Load ``.mergewall.yml`` from *path* (or CWD) and return a ``GuardianConfig``.

    Returns a default (empty) config if the file does not exist or cannot
    be parsed, so callers never need to handle ``None``.

    Results are cached so repeated calls (e.g. from 9 agent constructors)
    do not re-read the YAML from disk.
    """
    global _config_cache, _config_cache_path

    if path is None:
        config_path = Path.cwd() / _DEFAULT_CONFIG_FILENAME
    else:
        config_path = Path(path)

    resolved = str(config_path.resolve())
    if _config_cache is not None and _config_cache_path == resolved:
        return _config_cache

    if not config_path.is_file():
        logger.debug("No config file found at %s — using defaults", config_path)
        cfg = GuardianConfig()
        _config_cache = cfg
        _config_cache_path = resolved
        return cfg

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse %s: %s — using defaults", config_path, exc)
        cfg = GuardianConfig()
        _config_cache = cfg
        _config_cache_path = resolved
        return cfg

    if not isinstance(raw, dict):
        cfg = GuardianConfig()
        _config_cache = cfg
        _config_cache_path = resolved
        return cfg

    # Validate governance section if present
    from mergewall.policy.validator import validate_config_dict
    try:
        validate_config_dict(raw, config_path)
    except Exception as exc:
        # Surface validation errors to stderr and exit if running in CLI mode
        # (don't silently fall back to defaults for validation errors)
        import sys
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(1)

    model = raw.get("model")

    # Parse agents section
    agents: dict[str, AgentConfig] = {}
    raw_agents = raw.get("agents", {})
    if isinstance(raw_agents, dict):
        for name, value in raw_agents.items():
            if isinstance(value, dict):
                agents[name] = AgentConfig(
                    enabled=value.get("enabled", True),
                    severity_threshold=value.get("severity_threshold"),
                )
            elif isinstance(value, bool):
                agents[name] = AgentConfig(enabled=value)

    # Parse ignore list
    ignore: list[str] = []
    raw_ignore = raw.get("ignore", [])
    if isinstance(raw_ignore, list):
        ignore = [str(p) for p in raw_ignore]

    # Parse governance section
    governance_policy = _parse_governance(raw.get("governance", {}))

    cfg = GuardianConfig(model=model, agents=agents, ignore=ignore, governance_policy=governance_policy)
    cfg._raw_custom_guards = raw.get("custom_guards", [])  # for plugin loader
    _config_cache = cfg
    _config_cache_path = resolved
    return cfg


def _parse_governance(raw: dict | None) -> GovernancePolicy:
    """Parse the 'governance' section from YAML into a GovernancePolicy."""
    if not raw or not isinstance(raw, dict):
        return GovernancePolicy()

    mode = raw.get("mode", "governance")
    min_confidence = float(raw.get("min_confidence", 0.7))
    default_action = PolicyAction(raw.get("default_action", "allow"))

    # Parse path rules
    path_rules: list[PathRule] = []
    for pr in raw.get("path_rules", []):
        if not isinstance(pr, dict):
            continue
        path_rules.append(PathRule(
            paths=pr.get("paths", ["**"]),
            risk_categories=pr.get("risk_categories", ["*"]),
            min_level=pr.get("min_level", "high"),
            action=PolicyAction(pr.get("action", "block")),
            require_approval_from=pr.get("require_approval_from", []),
        ))

    # Parse threshold rules
    threshold_rules: list[ThresholdRule] = []
    for tr in raw.get("threshold_rules", []):
        if not isinstance(tr, dict):
            continue
        threshold_rules.append(ThresholdRule(
            min_score=tr.get("min_score", 0),
            action=PolicyAction(tr.get("action", "require_approval")),
            require_approval_from=tr.get("require_approval_from", []),
        ))

    return GovernancePolicy(
        mode=mode,
        path_rules=path_rules,
        threshold_rules=threshold_rules,
        default_action=default_action,
        min_confidence=min_confidence,
    )

"""Configuration validator for .mergewall.yml.

Validates governance configuration at load time with clear,
actionable error messages.
"""

from __future__ import annotations

import yaml
from pathlib import Path

from mergewall.risk.models import RiskCategory

_VALID_MODES = {"governance", "review"}
_VALID_ACTIONS = {"block", "require_approval", "warn", "allow"}
_VALID_CATEGORIES = {c.value for c in RiskCategory}


class ConfigValidationError(Exception):
    """Raised when .mergewall.yml is invalid, with a user-readable message."""


def validate_config_dict(raw: dict, path: str | Path) -> None:
    """Validate a loaded YAML dict against governance schema.

    Raises ConfigValidationError with a clear message if invalid.
    Returns None if valid.
    """
    path = Path(path)
    governance = raw.get("governance", {})
    if not isinstance(governance, dict):
        return

    # 1. governance.mode
    mode = governance.get("mode")
    if mode is not None and mode not in _VALID_MODES:
        raise ConfigValidationError(
            f"Invalid governance.mode in {path}: '{mode}'. "
            f"Must be one of: {', '.join(sorted(_VALID_MODES))}"
        )

    # 2. path_rules validation
    _validate_path_rules(governance.get("path_rules", []), path)

    # 3. threshold_rules validation
    _validate_threshold_rules(governance.get("threshold_rules", []), path)

    # 4. min_confidence
    min_conf = governance.get("min_confidence")
    if min_conf is not None:
        try:
            min_conf = float(min_conf)
        except (TypeError, ValueError):
            raise ConfigValidationError(
                f"Invalid governance.min_confidence in {path}: {min_conf!r}. "
                f"Must be a number between 0.0 and 1.0"
            )
        if not (0.0 <= min_conf <= 1.0):
            raise ConfigValidationError(
                f"Invalid governance.min_confidence in {path}: {min_conf}. "
                f"Must be between 0.0 and 1.0"
            )


def validate_config_file(path: str | Path) -> None:
    """Validate a .mergewall.yml file.

    Raises ConfigValidationError with a clear message if invalid.
    Returns None if valid.
    """
    path = Path(path)

    # 1. YAML syntax check
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigValidationError(f"Cannot read {path}: {exc}") from exc

    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        # Try to extract line number
        problem_mark = getattr(exc, "problem_mark", None)
        if problem_mark:
            raise ConfigValidationError(
                f"YAML syntax error in {path} at line {problem_mark.line + 1}, "
                f"column {problem_mark.column + 1}: {exc}"
            ) from exc
        raise ConfigValidationError(
            f"YAML syntax error in {path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        return

    validate_config_dict(raw, path)


def _validate_path_rules(rules: list, path: Path) -> None:
    if not isinstance(rules, list):
        return
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        # risk_categories
        categories = rule.get("risk_categories", [])
        if isinstance(categories, list):
            for cat in categories:
                if cat == "*":
                    continue
                if cat not in _VALID_CATEGORIES:
                    raise ConfigValidationError(
                        f"Invalid risk category in {path}, "
                        f"path_rules[{i}].risk_categories: '{cat}'. "
                        f"Valid categories: {', '.join(sorted(_VALID_CATEGORIES))}"
                    )
        # action
        action = rule.get("action")
        if action is not None and action not in _VALID_ACTIONS:
            raise ConfigValidationError(
                f"Invalid action in {path}, path_rules[{i}].action: '{action}'. "
                f"Valid actions: {', '.join(sorted(_VALID_ACTIONS))}"
            )


def _validate_threshold_rules(rules: list, path: Path) -> None:
    if not isinstance(rules, list):
        return
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        # min_score
        min_score = rule.get("min_score")
        if min_score is not None:
            try:
                min_score = int(min_score)
            except (TypeError, ValueError):
                raise ConfigValidationError(
                    f"Invalid min_score in {path}, threshold_rules[{i}]: {min_score!r}. "
                    f"Must be an integer between 0 and 100"
                )
            if not (0 <= min_score <= 100):
                raise ConfigValidationError(
                    f"Invalid min_score in {path}, threshold_rules[{i}]: {min_score}. "
                    f"Must be between 0 and 100"
                )
        # action
        action = rule.get("action")
        if action is not None and action not in _VALID_ACTIONS:
            raise ConfigValidationError(
                f"Invalid action in {path}, threshold_rules[{i}].action: '{action}'. "
                f"Valid actions: {', '.join(sorted(_VALID_ACTIONS))}"
            )

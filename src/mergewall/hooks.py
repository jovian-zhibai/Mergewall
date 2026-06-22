"""Pre-commit hook support — run governance checks before commits."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mergewall.diff.parser import parse_diff
from mergewall.risk.engine import DiffRiskEngine
from mergewall.risk.models import MergeDecision


def pre_commit_hook() -> int:
    """Run governance analysis on staged changes.

    Called by .git/hooks/pre-commit. Returns 0 (allow commit),
    1 (block commit), or 2 (warn but allow).
    """
    # Check if we're in a git repo
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"],
                       capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Mergewall: not a git repository, skipping pre-commit check.")
        return 0

    # Get staged diff
    result = subprocess.run(
        ["git", "diff", "--cached", "--unified=3"],
        capture_output=True, text=True,
    )

    if not result.stdout.strip():
        return 0  # No staged changes

    raw_diff = result.stdout

    # Parse and analyze
    structured_diff = parse_diff(raw_diff)
    if not structured_diff.files:
        return 0

    import asyncio
    engine = DiffRiskEngine()
    report = asyncio.run(engine.analyze(structured_diff))

    if not report.findings:
        return 0

    # Print findings and decide
    print("\n🛡️  Mergewall Pre-commit Check")
    print(f"   Risk Score: {report.risk_score}/100")
    print(f"   Findings: {len(report.findings)}")
    print()

    for f in report.findings[:10]:  # Show up to 10
        print(f"  [{f.level.value.upper()}] {f.category.value}: {f.title}")
        print(f"    File: {f.evidence.file_path}")

    print()

    if report.merge_decision == MergeDecision.BLOCK:
        print("🚨 Commit BLOCKED — fix the issues above and try again.")
        if report.findings:
            f = report.findings[0]
            if f.fix_suggestion:
                print(f"   Suggestion: {f.fix_suggestion}")
        return 1
    elif report.merge_decision in (MergeDecision.REQUIRE_APPROVAL, MergeDecision.WARN):
        print("⚠️  Warnings found — review before pushing, but commit allowed.")
        return 0
    else:
        return 0


def install_hook() -> None:
    """Install the pre-commit hook into .git/hooks/pre-commit."""
    # Find git dir
    try:
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: not a git repository. Run 'git init' first.")
        sys.exit(1)

    hook_path = Path(git_dir) / "hooks" / "pre-commit"

    hook_script = """#!/bin/sh
# Mergewall pre-commit hook
# Installed by: mergewall hook-install
# Remove this file to disable: rm .git/hooks/pre-commit
mergewall hook-run
"""

    # If hook already exists, check if it's ours
    if hook_path.exists():
        content = hook_path.read_text()
        if "mergewall hook-run" in content or "Mergewall" in content:
            hook_path.write_text(hook_script)
            print("Updated existing Mergewall pre-commit hook.")
            return
        else:
            print(f"Warning: {hook_path} already exists with custom content.")
            print("To add Mergewall, append this line:")
            print("  mergewall hook-run")
            return

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(hook_script)
    hook_path.chmod(0o755)
    print(f"Installed pre-commit hook at {hook_path}")
    print("Mergewall will run governance checks before every commit.")

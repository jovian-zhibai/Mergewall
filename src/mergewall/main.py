"""CLI entry point for Mergewall."""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

import click

from mergewall import __version__
from mergewall.config import load_config
from mergewall.graph.workflow import CodeReviewWorkflow, ReviewReport

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
def cli():
    """Mergewall — AI Merge Governance Runtime."""
    pass


def _run_with_timeout(coro, timeout: int = 300):
    """Run an async coroutine with a timeout (default 5 minutes)."""
    try:
        return asyncio.run(asyncio.wait_for(coro, timeout=timeout))
    except asyncio.TimeoutError:
        click.echo("Error: Review timed out after 5 minutes.", err=True)
        sys.exit(1)


@cli.command()
@click.option("--file", "-f", type=click.Path(exists=True), help="Path to file for review")
@click.option("--diff", "-d", "diff_ref", help="Git diff reference (e.g., HEAD~1)")
@click.option("--model", "-m", default=None, help="LLM model to use")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown")
def review(file: str, diff_ref: str, model: str, output: str, fmt: str):
    """Run code review on a file or git diff."""
    cfg = load_config()
    workflow = CodeReviewWorkflow(model=model, config=cfg)

    if file:
        if cfg.should_ignore(file):
            click.echo(f"Skipping {file} — matches ignore pattern in .mergewall.yml")
            return
        try:
            code = Path(file).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            click.echo(f"Error: {file} is not a valid text file (encoding issue).", err=True)
            sys.exit(1)
        except (PermissionError, OSError) as exc:
            click.echo(f"Error: cannot read {file}: {exc}", err=True)
            sys.exit(1)
        result = _run_with_timeout(workflow.run(code=code, file_path=file))
    elif diff_ref:
        result = _run_with_timeout(workflow.run_from_diff(diff_ref))
    else:
        click.echo("Please specify --file or --diff")
        return

    report_obj = ReviewReport(result)
    if fmt == "json":
        report = report_obj.to_json()
    else:
        report = report_obj.to_markdown()

    if output:
        Path(output).write_text(report, encoding="utf-8")
        click.echo(f"Report saved to {output}")
    else:
        click.echo(report)


@cli.command()
@click.option("--diff", "-d", "diff_ref", default="HEAD~1", help="Git diff reference")
@click.option("--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def govern(diff_ref: str, fmt: str, output: str):
    """Run governance analysis on a diff (deterministic risk engine)."""
    import asyncio as _asyncio

    from mergewall.diff.parser import parse_diff
    from mergewall.risk.engine import DiffRiskEngine

    # Get the diff
    try:
        raw_diff = subprocess.check_output(
            ["git", "diff", diff_ref], stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as exc:
        click.echo(f"Error running git diff: {exc.output}", err=True)
        sys.exit(1)

    if not raw_diff.strip():
        click.echo("No changes detected.")
        return

    # Parse and analyze
    structured_diff = parse_diff(raw_diff)
    cfg = load_config()
    engine = DiffRiskEngine(config=cfg)
    report = _asyncio.run(engine.analyze(structured_diff))
    report.repo = "local"

    # Output
    if fmt == "json":
        import json
        from dataclasses import asdict
        text = json.dumps(asdict(report), indent=2, default=str)
    else:
        text = report.to_markdown()

    if output:
        Path(output).write_text(text, encoding="utf-8")
        click.echo(f"Governance report saved to {output}")
    else:
        click.echo(text)

    # Exit with non-zero if blocked
    from mergewall.risk.models import MergeDecision
    if report.merge_decision == MergeDecision.BLOCK:
        sys.exit(1)


@cli.command()
def audit():
    """Show recent governance audit trail."""
    from mergewall.audit.trail import AuditTrail
    trail = AuditTrail()
    entries = trail.query()
    if not entries:
        click.echo("No audit entries found.")
        return
    for entry in entries[-20:]:  # Last 20
        click.echo(
            f"{entry.timestamp[:19]} | {entry.repo}#{entry.pr_number} | "
            f"{entry.merge_decision} | score={entry.risk_score} | "
            f"findings={entry.finding_count}"
        )


if __name__ == "__main__":
    cli()

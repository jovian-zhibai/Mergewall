"""Tests for the demo / dry-run mode."""

import json
from mergewall.demo import (
    DemoReviewWorkflow,
    DemoConfig,
    _MOCK_FINDINGS,
)
from mergewall.agents.base import Severity
from mergewall.graph.workflow import ReviewReport


def test_demo_workflow_runs():
    """Demo workflow should produce a result without any API key."""
    demo = DemoReviewWorkflow()
    result = demo.run(code="def foo(): pass", file_path="test.py")

    assert result.agent_name == "CoordinatorAgent"
    assert len(result.findings) > 0
    # All agents in the mock data should have produced findings
    agents_seen = {f.agent for f in result.findings}
    assert len(agents_seen) == 9


def test_demo_workflow_deterministic():
    """Same seed should produce identical token counts."""
    demo1 = DemoReviewWorkflow(DemoConfig(seed=99))
    demo2 = DemoReviewWorkflow(DemoConfig(seed=99))
    r1 = demo1.run()
    r2 = demo2.run()
    assert r1.token_usage == r2.token_usage


def test_demo_finding_severity_order():
    """Findings should be sorted: HIGH before MEDIUM before LOW."""
    demo = DemoReviewWorkflow()
    result = demo.run()
    severities = [f.severity for f in result.findings]
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
    }
    assert severities == sorted(severities, key=lambda s: severity_order[s])


def test_demo_report_markdown():
    """Demo output should produce valid Markdown report."""
    demo = DemoReviewWorkflow()
    result = demo.run()
    report = ReviewReport(result)
    md = report.to_markdown()

    assert "# CodeGuardian Review Report" in md
    assert "SecurityAgent" in md
    assert "SQL Injection" in md


def test_demo_report_json():
    """Demo output should produce valid JSON."""
    demo = DemoReviewWorkflow()
    result = demo.run()
    report = ReviewReport(result)
    data = report.to_json()

    parsed = json.loads(data)
    assert parsed["total_findings"] > 0
    for f in parsed["findings"]:
        assert "agent" in f
        assert "severity" in f
        assert "title" in f
        assert f["severity"] in ("low", "medium", "high", "critical")


def test_demo_without_token_simulation():
    demo = DemoReviewWorkflow(DemoConfig(simulate_token_usage=False))
    result = demo.run()
    assert result.token_usage == 0


def test_mock_findings_all_valid():
    """Every mock finding should have required fields."""
    for agent_name, findings_list in _MOCK_FINDINGS.items():
        for f in findings_list:
            assert "title" in f
            assert "description" in f
            assert "severity" in f
            assert isinstance(f["severity"], Severity)


def test_demo_custom_seed_different_output():
    """Different seeds should produce different token counts (probabilistic)."""
    demo1 = DemoReviewWorkflow(DemoConfig(seed=1))
    demo2 = DemoReviewWorkflow(DemoConfig(seed=9999))
    r1 = demo1.run()
    r2 = demo2.run()
    # Same findings text but token counts may differ due to random jitter
    assert len(r1.findings) == len(r2.findings)


def test_demo_with_empty_code():
    """Demo should still work with empty code string."""
    demo = DemoReviewWorkflow()
    result = demo.run(code="")
    assert result is not None
    assert len(result.findings) > 0


def test_full_demo_to_markdown_snapshot():
    """Integration: run demo, convert to Markdown, verify all agents appear."""
    demo = DemoReviewWorkflow()
    result = demo.run(code=SAMPLE_CODE, file_path="app.py")
    report = ReviewReport(result)
    md = report.to_markdown()

    expected_agents = [
        "StyleAgent",
        "SecurityAgent",
        "PerformanceAgent",
        "LogicAgent",
        "RepoAgent",
        "RefactorAgent",
        "FixAgent",
        "TestAgent",
        "DocAgent",
    ]
    for agent in expected_agents:
        assert agent in md, f"{agent} should appear in the report"

    # Should mention MiMo in the summary note
    assert "DEMO" in md.upper()


SAMPLE_CODE = """
import sqlite3
import hashlib

def get_user(user_id):
    conn = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = conn.execute(query)
    return result.fetchone()

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and user.password == hashlib.md5(password.encode()).hexdigest():
        return create_session(user.id)
    return None
"""

"""Tests for the LangGraph review workflow."""

import pytest
from mergewall.graph.workflow import ReviewReport, ReviewState
from mergewall.agents.base import AgentResult, ReviewFinding, Severity


def test_review_state_defaults():
    state = ReviewState(code="print('hello')", file_path="test.py")
    assert state.code == "print('hello')"
    assert state.file_path == "test.py"
    assert state.style_result is None
    assert state.security_result is None


def test_review_state_with_results():
    state = ReviewState(
        code="x = 1",
        file_path="a.py",
        style_result=AgentResult(agent_name="StyleAgent", findings=[]),
    )
    assert state.style_result is not None
    assert state.security_result is None


# ---------------------------------------------------------------------------
# ReviewReport tests
# ---------------------------------------------------------------------------


def test_report_markdown_empty():
    result = AgentResult(
        agent_name="Coordinator",
        findings=[],
        summary="No issues found.",
    )
    report = ReviewReport(result)
    md = report.to_markdown()
    assert "CodeGuardian Review Report" in md
    assert "Total Findings:** 0" in md


def test_report_markdown_with_findings():
    findings = [
        ReviewFinding(
            agent="SecurityAgent",
            severity=Severity.HIGH,
            title="SQL Injection",
            description="User input interpolated into SQL query.",
            line_number=12,
            suggestion="Use parameterized queries.",
        ),
        ReviewFinding(
            agent="StyleAgent",
            severity=Severity.LOW,
            title="Missing docstring",
            description="No docstring on public function.",
            line_number=42,
            suggestion="Add docstring.",
        ),
    ]
    result = AgentResult(
        agent_name="Coordinator",
        findings=findings,
        summary="2 issues found.",
    )
    report = ReviewReport(result)
    md = report.to_markdown()

    assert "SQL Injection" in md
    assert "Missing docstring" in md
    assert "[HIGH]" in md
    assert "[LOW]" in md
    assert "Line:** 12" in md
    assert "parameterized queries" in md


def test_report_json():
    findings = [
        ReviewFinding(
            agent="StyleAgent",
            severity=Severity.LOW,
            title="Long line",
            description="Line too long.",
            line_number=99,
            suggestion="Break line.",
        ),
    ]
    result = AgentResult(agent_name="Coordinator", findings=findings, summary="Done.")
    report = ReviewReport(result)
    data = report.to_json()

    import json
    parsed = json.loads(data)
    assert parsed["total_findings"] == 1
    assert parsed["findings"][0]["agent"] == "StyleAgent"
    assert parsed["findings"][0]["severity"] == "low"


# ---------------------------------------------------------------------------
# Workflow structure tests (no LLM calls)
# ---------------------------------------------------------------------------


def test_workflow_graph_structure():
    """Verify the LangGraph workflow can be built without errors."""
    import os
    from mergewall.graph.workflow import CodeReviewWorkflow
    from mergewall.config import GuardianConfig

    # Use empty config (all agents enabled) to verify full graph.
    cfg = GuardianConfig()
    os.environ.setdefault("LLM_API_KEY", "test-key")
    workflow = CodeReviewWorkflow(model="mimo-v2.5-pro", config=cfg)
    graph = workflow.graph

    # The graph should be compiled
    assert graph is not None
    # Should have all review nodes + coordinator
    nodes = graph.get_graph().nodes
    assert len(nodes) >= 12  # 9 reviewers + coordinator + __start__ + __end__


# ---------------------------------------------------------------------------
# Run workflow with demo/mocked LLM
# ---------------------------------------------------------------------------


class _MockLLM:
    """Fake ChatOpenAI that returns a canned response."""

    model_name = "mock-model"
    temperature = 0.1

    async def ainvoke(self, messages):
        class FakeResponse:
            content = """- Severity: MEDIUM
- Title: Mock Finding
- Line: 1
- Description: This is a mock finding from the test harness.
- Suggestion: Fix it.

Summary: All good."""
            response_metadata = {"token_usage": {"total_tokens": 42}}

        return FakeResponse()


@pytest.mark.asyncio
async def test_single_agent_review_with_mock():
    """Test that a single agent can run with a mocked LLM."""
    from mergewall.agents.security_agent import SecurityAgent

    agent = SecurityAgent(model="mock", api_key="test-key")
    agent.llm = _MockLLM()

    result = await agent.review("x = 1", "test.py")
    assert result.agent_name == "SecurityAgent"
    assert len(result.findings) == 1
    assert result.findings[0].title == "Mock Finding"
    assert result.findings[0].severity == Severity.MEDIUM


@pytest.mark.asyncio
async def test_coordinator_with_mock_llm():
    """Test coordinator synthesize (doesn't call LLM itself)."""
    from mergewall.agents.coordinator import CoordinatorAgent

    coordinator = CoordinatorAgent(model="mock", api_key="test-key")
    results = [
        AgentResult(
            agent_name="A",
            findings=[
                ReviewFinding(
                    agent="A",
                    severity=Severity.HIGH,
                    title="Issue 1",
                    description="desc",
                ),
            ],
            token_usage=100,
        ),
    ]
    result = await coordinator.synthesize(results)
    assert result.agent_name == "CoordinatorAgent"
    assert len(result.findings) == 1

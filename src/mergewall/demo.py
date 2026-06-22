"""Demo / dry-run mode for Mergewall (legacy from RevHive).

Runs a complete multi-agent review pipeline with simulated (mock) LLM
responses. No API key required — perfect for evaluation, CI smoke tests,
and demonstrating Mergewall's capabilities to reviewers.

Produces the same structured output as the real workflow:
  - Markdown report with severity-badged findings
  - JSON export
  - Token consumption simulation
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from mergewall.agents.base import AgentResult, ReviewFinding, Severity
from mergewall.agents.coordinator import CoordinatorAgent
from mergewall.utils.dedup import deduplicate_and_sort


# ---------------------------------------------------------------------------
# Pre-seeded realistic mock findings per agent
# ---------------------------------------------------------------------------

_MOCK_FINDINGS: dict[str, list[dict]] = {
    "StyleAgent": [
        {
            "severity": Severity.LOW,
            "title": "Missing docstring for function",
            "description": "The function lacks a docstring describing its purpose, parameters, and return value.",
            "line_number": 10,
            "suggestion": 'Add a triple-quoted docstring: """Fetches user by ID from database."""',
        },
        {
            "severity": Severity.LOW,
            "title": "Variable name too short",
            "description": "Single-letter or overly abbreviated variable names hurt readability.",
            "line_number": 25,
            "suggestion": "Rename `d` to `user_data` or a more descriptive name.",
        },
        {
            "severity": Severity.LOW,
            "title": "Line exceeds 120 characters",
            "description": "Long lines are hard to read in side-by-side diff views and narrow terminals.",
            "line_number": 42,
            "suggestion": "Break into multiple lines using intermediate variables or line continuation.",
        },
    ],
    "SecurityAgent": [
        {
            "severity": Severity.CRITICAL,
            "title": "Remote Code Execution via shell injection",
            "description": "User input passed unsanitized to subprocess.call() allows arbitrary command execution with the application's privileges.",
            "line_number": 45,
            "suggestion": "Use subprocess.run() with a command list (not shell=True) and validate all inputs against an allowlist.",
        },
        {
            "severity": Severity.HIGH,
            "title": "SQL Injection via string interpolation",
            "description": "User-controlled input is interpolated directly into a SQL query string, allowing attackers to modify query semantics.",
            "line_number": 12,
            "suggestion": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        },
        {
            "severity": Severity.MEDIUM,
            "title": "Hardcoded credential detected",
            "description": "A secret token appears to be hardcoded in source code rather than loaded from environment variables.",
            "line_number": 8,
            "suggestion": "Load from os.environ.get('API_SECRET') and store the value in .env (ensure .env is gitignored).",
        },
        {
            "severity": Severity.HIGH,
            "title": "MD5 used for password hashing",
            "description": "MD5 is cryptographically broken and unsuitable for password storage.",
            "line_number": 20,
            "suggestion": "Use bcrypt or argon2: `bcrypt.hashpw(password.encode(), bcrypt.gensalt())`",
        },
    ],
    "PerformanceAgent": [
        {
            "severity": Severity.MEDIUM,
            "title": "N+1 Query Pattern",
            "description": "A database query is executed inside a loop, causing N+1 round-trips to the database.",
            "line_number": 28,
            "suggestion": "Fetch all needed data in a single batch query using WHERE id IN (...).",
        },
        {
            "severity": Severity.LOW,
            "title": "Missing caching for repeated computation",
            "description": "The same expensive computation is repeated in multiple call sites with identical inputs.",
            "line_number": 35,
            "suggestion": "Use `functools.lru_cache` or memoization on the function.",
        },
    ],
    "LogicAgent": [
        {
            "severity": Severity.HIGH,
            "title": "Missing exception handling",
            "description": "A json.loads() call is not wrapped in try/except — malformed input will crash the service.",
            "line_number": 16,
            "suggestion": "Wrap in try/except json.JSONDecodeError and return a user-friendly error message.",
        },
        {
            "severity": Severity.MEDIUM,
            "title": "Unchecked None return value",
            "description": "A function may return None, but the caller dereferences the result without a None check.",
            "line_number": 22,
            "suggestion": "Add: if result is None: raise ValueError('Resource not found') or return default.",
        },
        {
            "severity": Severity.LOW,
            "title": "Off-by-one potential in range",
            "description": "A loop using range(len(seq)) might miss the last element due to < vs <=.",
            "line_number": 31,
            "suggestion": "Replace with `for item in seq:` for clarity and correctness.",
        },
    ],
    "RepoAgent": [
        {
            "severity": Severity.MEDIUM,
            "title": "Duplicate utility function across modules",
            "description": "The same `parse_date()` function is defined independently in three modules.",
            "line_number": None,
            "suggestion": "Extract into a shared `utils/datetime.py` module and import from one place.",
        },
        {
            "severity": Severity.LOW,
            "title": "Inconsistent error response format",
            "description": "Some endpoints return `{'error': msg}` while others return `{'message': msg, 'code': n}`.",
            "line_number": None,
            "suggestion": "Standardize on a single error response envelope across all API handlers.",
        },
    ],
    "RefactorAgent": [
        {
            "severity": Severity.LOW,
            "title": "Long function — consider extracting helpers",
            "description": "A function of 80+ lines handles validation, business logic, and I/O in one place.",
            "line_number": 15,
            "suggestion": "Extract `_validate_input()`, `_process_order()`, `_persist_result()` as separate methods.",
        },
        {
            "severity": Severity.LOW,
            "title": "Strategy pattern opportunity",
            "description": "A chain of if/elif branches dispatches on payment type — fragile to extension.",
            "line_number": 40,
            "suggestion": "Replace with a payment strategy dict: `strategies[payment_type].pay(amount)`.",
        },
    ],
    "FixAgent": [
        {
            "severity": Severity.HIGH,
            "title": "Null pointer dereference in user lookup path",
            "description": "get_user_by_id() may return None, but caller dereferences .email without null check — causes 500 error on missing users.",
            "line_number": 18,
            "suggestion": "Add guard: user = get_user_by_id(uid); if not user: raise HTTPException(404).",
        },
        {
            "severity": Severity.MEDIUM,
            "title": "Race condition in inventory update",
            "description": "Read-modify-write on stock quantity is not atomic — concurrent orders can oversell inventory.",
            "line_number": 55,
            "suggestion": "Use SELECT ... FOR UPDATE or UPDATE ... WHERE stock >= quantity RETURNING to make the check-and-decrement atomic.",
        },
    ],
    "TestAgent": [
        {
            "severity": Severity.MEDIUM,
            "title": "Missing test coverage for error paths",
            "description": "Only happy-path tests exist. No tests for invalid JSON input, database timeout, or upstream API 503 fallback.",
            "line_number": None,
            "suggestion": "Add pytest.mark.parametrize tests covering malformed input, connection errors, and timeout scenarios.",
        },
        {
            "severity": Severity.LOW,
            "title": "No security regression test for XSS fix",
            "description": "The XSS sanitizer was patched last month but has no regression test — a refactor could re-introduce the vulnerability silently.",
            "line_number": None,
            "suggestion": "Add test_xss_sanitizer_blocks_script_tags with known payload vectors to prevent regression.",
        },
    ],
    "DocAgent": [
        {
            "severity": Severity.LOW,
            "title": "Public API missing docstrings and usage examples",
            "description": "3 of 5 public functions in the module lack docstrings. The authenticate() function has no documented error responses.",
            "line_number": 8,
            "suggestion": "Add Google-style docstrings with Args, Returns, Raises sections. Include a usage example in the module docstring.",
        },
        {
            "severity": Severity.LOW,
            "title": "Configuration options not documented",
            "description": "Environment variables and config keys used at startup are not listed in README or a CONFIG.md reference.",
            "line_number": None,
            "suggestion": "Document all env vars (12 total) in a table: name, default, description, required.",
        },
    ],
}


@dataclass
class DemoConfig:
    """Configuration for demo mode behaviour."""

    seed: int = 42
    include_findings: bool = True
    simulate_token_usage: bool = True
    base_tokens_per_agent: int = 1500


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------


class DemoReviewWorkflow:
    """Runs a full multi-agent code review with mock responses.

    No API key, network, or LLM endpoint required. Produces a realistic
    :class:`AgentResult` that is indistinguishable in structure from a real
    MiMo-backed run.

    Usage::

        from mergewall.graph.workflow import ReviewReport

        demo = DemoReviewWorkflow()
        result = demo.run(SAMPLE_CODE, file_path="app.py")
        report = ReviewReport(result)
        print(report.to_markdown())
    """

    def __init__(self, config: DemoConfig | None = None):
        self.config = config or DemoConfig()
        self._rng = random.Random(self.config.seed)

    def run(self, code: str = "", file_path: str = "app.py") -> AgentResult:
        """Execute a simulated multi-agent review.

        Args:
            code: The source code to "review" (displayed in the report).
            file_path: Path label for the reviewed file.

        Returns:
            A complete :class:`AgentResult` with all mock findings.
        """
        all_findings: list[ReviewFinding] = []
        total_tokens = 0

        for agent_name, findings_data in _MOCK_FINDINGS.items():
            findings = [
                ReviewFinding(
                    agent=agent_name,
                    severity=f["severity"],
                    title=f["title"],
                    description=f["description"],
                    line_number=f.get("line_number"),
                    suggestion=f.get("suggestion"),
                )
                for f in findings_data
            ]
            all_findings.extend(findings)

            if self.config.simulate_token_usage:
                total_tokens += self.config.base_tokens_per_agent + self._rng.randint(0, 500)

        # Coordinator pass
        all_findings = deduplicate_and_sort(all_findings)
        risk_score = CoordinatorAgent._calculate_risk_score(all_findings)
        coordinator_summary = _build_coordinator_summary(all_findings, risk_score)

        return AgentResult(
            agent_name="CoordinatorAgent",
            findings=all_findings,
            summary=coordinator_summary,
            token_usage=total_tokens if self.config.simulate_token_usage else 0,
            risk_score=risk_score,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_coordinator_summary(findings: list[ReviewFinding], risk_score: int = 0) -> str:
    """Generate a Markdown summary with risk score and severity breakdown."""
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity.value] = counts.get(f.severity.value, 0) + 1

    agent_counts: dict[str, int] = {}
    for f in findings:
        agent_counts[f.agent] = agent_counts.get(f.agent, 0) + 1

    lines = [
        "Mergewall Demo Review Report",
        "=================================",
        "",
        CoordinatorAgent._risk_score_block(findings, risk_score),
        "",
        f"Review completed with **{len(findings)} findings** across {len(agent_counts)} agents.",
        "",
        "### Severity Breakdown",
    ]
    for sev in ("critical", "high", "medium", "low"):
        if sev in counts:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[sev]
            lines.append(f"  {emoji} **{sev.upper()}**: {counts[sev]}")

    critical_high = [f for f in findings if f.severity in (Severity.CRITICAL, Severity.HIGH)]
    if critical_high:
        lines.append("")
        lines.append(f"### ⚠️ {len(critical_high)} Critical/High Issues Require Immediate Attention")
        for f in critical_high:
            lines.append(f"  - **[{f.severity.value.upper()}]** {f.title}  ")
            lines.append(f"    *{f.agent}*")

    lines.append("")
    lines.append("---")
    lines.append("*Note: This report was generated in DEMO mode. Real MiMo-powered reviews will call the API.*")

    return "\n".join(lines)


# ============================================================================
# Governance Demo Mode
# ============================================================================


def run_governance_demo():
    """Run a governance-focused demo showing the full deterministic pipeline.

    Creates mock diffs with 4 risk categories (secret_leakage, auth_bypass,
    permission_escalation, dangerous_dependencies), runs them through the
    DiffRiskEngine with all 6 deterministic guards, and prints a full report.

    No LLM, no API key required — pure deterministic path.
    """
    from mergewall.diff.models import ChangeType, DiffLine, FileDiff, Hunk, StructuredDiff
    from mergewall.risk.engine import DiffRiskEngine
    from mergewall.risk.models import MergeDecision

    # Build mock diffs that trigger 4 core risk categories
    auth_file = FileDiff(
        old_path="src/auth/views.py",
        new_path="src/auth/views.py",
        change_type=ChangeType.MODIFIED,
        hunks=[
            Hunk(
                old_start=10, old_count=5, new_start=10, new_count=4,
                lines=[
                    DiffLine(old_line=10, new_line=None, content="@login_required", change_type="-"),
                    DiffLine(old_line=11, new_line=None, content="def admin_panel(request):", change_type="-"),
                    DiffLine(old_line=None, new_line=10, content="skip_authentication = True", change_type="+"),
                    DiffLine(old_line=None, new_line=11, content="def admin_panel(request):", change_type="+"),
                    DiffLine(old_line=None, new_line=12, content="    is_superuser = True  # privilege escalation", change_type="+"),
                    DiffLine(old_line=12, new_line=13, content="    return render(request, 'admin.html')", change_type=" "),
                ],
            ),
        ],
    )

    secret_file = FileDiff(
        old_path="src/config.py",
        new_path="src/config.py",
        change_type=ChangeType.MODIFIED,
        hunks=[
            Hunk(
                old_start=1, old_count=0, new_start=1, new_count=3,
                lines=[
                    DiffLine(old_line=None, new_line=1, content='AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"', change_type="+"),
                    DiffLine(old_line=None, new_line=2, content='GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"', change_type="+"),
                    DiffLine(old_line=None, new_line=3, content='DB_PASSWORD = "supersecret123"', change_type="+"),
                ],
            ),
        ],
    )

    deps_file = FileDiff(
        old_path="requirements.txt",
        new_path="requirements.txt",
        change_type=ChangeType.MODIFIED,
        hunks=[
            Hunk(
                old_start=1, old_count=3, new_start=1, new_count=3,
                lines=[
                    DiffLine(old_line=None, new_line=1, content="django>=3.0  # downgraded from 4.x", change_type="+"),
                    DiffLine(old_line=None, new_line=2, content="requests>=2.28.0  # unpinned, no upper bound", change_type="+"),
                    DiffLine(old_line=1, new_line=None, content="django>=4.2", change_type="-"),
                    DiffLine(old_line=2, new_line=None, content="requests==2.31.0", change_type="-"),
                ],
            ),
        ],
    )

    api_file = FileDiff(
        old_path="src/api/routes.py",
        new_path="src/api/routes.py",
        change_type=ChangeType.MODIFIED,
        hunks=[
            Hunk(
                old_start=20, old_count=3, new_start=20, new_count=1,
                lines=[
                    DiffLine(old_line=20, new_line=None, content="def get_user(user_id: int):", change_type="-"),
                    DiffLine(old_line=21, new_line=None, content='    """Fetch user by ID."""', change_type="-"),
                    DiffLine(old_line=22, new_line=None, content="    return db.query(User).get(user_id)", change_type="-"),
                ],
            ),
        ],
    )

    shared_file = FileDiff(
        old_path="src/utils/helpers.py",
        new_path="src/utils/helpers.py",
        change_type=ChangeType.MODIFIED,
        hunks=[
            Hunk(
                old_start=1, old_count=0, new_start=1, new_count=150,
                lines=[
                    DiffLine(old_line=None, new_line=i, content=f"# line {i} of a large shared utility refactor", change_type="+")
                    for i in range(1, 151)
                ],
            ),
        ],
    )

    diff = StructuredDiff(files=[auth_file, secret_file, deps_file, api_file, shared_file])

    # Run the deterministic risk engine
    import asyncio
    engine = DiffRiskEngine()
    report = asyncio.run(engine.analyze(diff))
    report.repo = "org/demo-repo"
    report.pr_number = 42

    return report


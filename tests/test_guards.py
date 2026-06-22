"""Tests for deterministic risk guards and the Diff Risk Engine."""

import pytest
from mergewall.diff.parser import parse_diff
from mergewall.diff.models import ChangeType, FileDiff, Hunk, DiffLine, StructuredDiff
from mergewall.risk.guards.secret_leakage import SecretLeakageGuard
from mergewall.risk.guards.auth_bypass import AuthBypassGuard
from mergewall.risk.guards.dangerous_deps import DangerousDepsGuard
from mergewall.risk.engine import DiffRiskEngine
from mergewall.risk.models import (
    RiskCategory, RiskLevel, MergeDecision, DetectionMethod,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_diff(path: str, added: list[str], removed: list[str] | None = None) -> FileDiff:
    """Create a FileDiff from simple added/removed line lists."""
    hunks = []
    lines = []
    new_line = 1
    old_line = 1
    for content in (removed or []):
        lines.append(DiffLine(old_line=old_line, new_line=None, content=content, change_type="-"))
        old_line += 1
    for content in added:
        lines.append(DiffLine(old_line=None, new_line=new_line, content=content, change_type="+"))
        new_line += 1
    if lines:
        hunks.append(Hunk(old_start=1, old_count=len(removed or []), new_start=1, new_count=len(added), lines=lines))
    return FileDiff(old_path=path, new_path=path, change_type=ChangeType.MODIFIED, hunks=hunks)


# ---------------------------------------------------------------------------
# Secret Leakage Guard
# ---------------------------------------------------------------------------


class TestSecretLeakageGuard:
    def setup_method(self):
        self.guard = SecretLeakageGuard()

    def test_detects_aws_key(self):
        fd = _make_file_diff("config.py", ['AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert findings[0].category == RiskCategory.SECRET_LEAKAGE
        assert findings[0].level == RiskLevel.CRITICAL
        assert findings[0].merge_decision == MergeDecision.BLOCK
        assert "AWS Key" in findings[0].title

    def test_detects_github_token(self):
        fd = _make_file_diff(".env", ['GITHUB_TOKEN="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert "GitHub Token" in findings[0].title

    def test_detects_private_key(self):
        fd = _make_file_diff("key.pem", ["-----BEGIN RSA PRIVATE KEY-----"])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert "Private Key" in findings[0].title

    def test_detects_jwt(self):
        fd = _make_file_diff("auth.py", ['token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert "JWT" in findings[0].title

    def test_detects_slack_token(self):
        fd = _make_file_diff("config.py", ['SLACK_TOKEN = "xoxb-1234567890-1234567890123-ABCDefGHIJklmnOPQrst12"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert "Slack" in findings[0].title

    def test_detects_generic_password(self):
        fd = _make_file_diff("settings.py", ['DB_PASSWORD = "supersecretvalue123"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert "Generic Secret" in findings[0].title

    def test_skips_test_files(self):
        fd = _make_file_diff("tests/test_auth.py", ['AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 0

    def test_skips_example_files(self):
        fd = _make_file_diff(".env.example", ['SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 0

    def test_no_false_positive_on_normal_code(self):
        fd = _make_file_diff("app.py", [
            "def login(request):",
            '    username = request.POST.get("username")',
            "    return render(request, 'login.html')",
        ])
        findings = self.guard.scan(fd)
        assert len(findings) == 0

    def test_evidence_contains_file_and_line(self):
        fd = _make_file_diff("config.py", ['AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert findings[0].evidence.file_path == "config.py"
        assert findings[0].evidence.line_numbers == [1]
        assert findings[0].evidence.detection_method == DetectionMethod.DETERMINISTIC


# ---------------------------------------------------------------------------
# Auth Bypass Guard
# ---------------------------------------------------------------------------


class TestAuthBypassGuard:
    def setup_method(self):
        self.guard = AuthBypassGuard()

    def test_detects_auth_decorator_removed_with_bypass(self):
        fd = _make_file_diff(
            "api/views.py",
            added=["skip_authentication = True", "def secret_view(request):"],
            removed=["@login_required", "def secret_view(request):"],
        )
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert findings[0].category == RiskCategory.AUTH_BYPASS
        assert findings[0].level == RiskLevel.CRITICAL
        assert findings[0].merge_decision == MergeDecision.BLOCK

    def test_detects_auth_decorator_removed_without_bypass(self):
        fd = _make_file_diff(
            "api/views.py",
            added=["def public_view(request):"],
            removed=["@login_required", "def public_view(request):"],
        )
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert findings[0].level == RiskLevel.HIGH
        assert findings[0].merge_decision == MergeDecision.REQUIRE_APPROVAL

    def test_detects_permission_escalation_superuser(self):
        fd = _make_file_diff("models.py", ["is_superuser = True"])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert findings[0].category == RiskCategory.PERMISSION_ESCALATION
        assert "is_superuser" in findings[0].title

    def test_detects_wildcard_permissions(self):
        fd = _make_file_diff("auth.py", ['permissions = ["*"]'])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert "wildcard" in findings[0].title.lower()

    def test_no_false_positive_on_normal_view(self):
        fd = _make_file_diff(
            "api/views.py",
            added=["def user_profile(request):", "    return render(request, 'profile.html')"],
        )
        findings = self.guard.scan(fd)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Dangerous Dependencies Guard
# ---------------------------------------------------------------------------


class TestDangerousDepsGuard:
    def setup_method(self):
        self.guard = DangerousDepsGuard()

    def test_detects_version_downgrade(self):
        fd = _make_file_diff(
            "requirements.txt",
            added=["pytest>=6.0"],
            removed=["pytest>=7.0"],
        )
        findings = self.guard.scan(fd)
        assert len(findings) >= 1
        downgrade_findings = [f for f in findings if "downgrade" in f.title.lower()]
        assert len(downgrade_findings) == 1
        assert downgrade_findings[0].category == RiskCategory.DANGEROUS_DEPENDENCIES
        assert downgrade_findings[0].level == RiskLevel.HIGH

    def test_detects_unpinned_version(self):
        fd = _make_file_diff("requirements.txt", added=["requests>=2.28.0"])
        findings = self.guard.scan(fd)
        assert len(findings) == 1
        assert "unpinned" in findings[0].title.lower()

    def test_no_false_positive_on_pinned_version(self):
        fd = _make_file_diff("requirements.txt", added=["requests==2.28.0"])
        findings = self.guard.scan(fd)
        assert len(findings) == 0

    def test_ignores_non_dep_files(self):
        fd = _make_file_diff("app.py", ["import requests"])
        findings = self.guard.scan(fd)
        assert len(findings) == 0

    def test_ignores_comments(self):
        fd = _make_file_diff("requirements.txt", added=["# This is a comment"])
        findings = self.guard.scan(fd)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Diff Risk Engine Integration
# ---------------------------------------------------------------------------


class TestDiffRiskEngine:
    def setup_method(self):
        self.engine = DiffRiskEngine()

    @pytest.mark.asyncio
    async def test_clean_diff_no_findings(self):
        diff = StructuredDiff(files=[
            _make_file_diff("app.py", ["print('hello')"]),
        ])
        report = await self.engine.analyze(diff)
        assert len(report.findings) == 0
        assert report.merge_decision == MergeDecision.ALLOW
        assert report.risk_score == 0

    @pytest.mark.asyncio
    async def test_secret_blocks_merge(self):
        diff = StructuredDiff(files=[
            _make_file_diff("config.py", ['AWS_KEY = "AKIAIOSFODNN7EXAMPLE"']),
        ])
        report = await self.engine.analyze(diff)
        assert report.merge_decision == MergeDecision.BLOCK
        assert report.risk_score > 0
        assert any(f.category == RiskCategory.SECRET_LEAKAGE for f in report.findings)

    @pytest.mark.asyncio
    async def test_multiple_risks_highest_wins(self):
        diff = StructuredDiff(files=[
            _make_file_diff("config.py", ['SECRET = "AKIAIOSFODNN7EXAMPLE"']),
            _make_file_diff("requirements.txt", added=["django>=3.0"], removed=["django>=4.0"]),
        ])
        report = await self.engine.analyze(diff)
        assert report.merge_decision == MergeDecision.BLOCK  # secret leakage blocks
        assert report.risk_score > 0

    @pytest.mark.asyncio
    async def test_binary_files_skipped(self):
        diff = StructuredDiff(files=[
            FileDiff(old_path="img.png", new_path="img.png", change_type=ChangeType.MODIFIED, is_binary=True),
        ])
        report = await self.engine.analyze(diff)
        assert len(report.findings) == 0

    @pytest.mark.asyncio
    async def test_deterministic_count(self):
        diff = StructuredDiff(files=[
            _make_file_diff("config.py", ['KEY = "AKIAIOSFODNN7EXAMPLE"']),
        ])
        report = await self.engine.analyze(diff)
        assert report.deterministic_count > 0
        assert report.llm_count == 0

    @pytest.mark.asyncio
    async def test_summary_generated(self):
        diff = StructuredDiff(files=[
            _make_file_diff("config.py", ['KEY = "AKIAIOSFODNN7EXAMPLE"']),
        ])
        report = await self.engine.analyze(diff)
        assert "Risk score" in report.summary
        assert "BLOCK" in report.summary or "block" in report.summary


# ---------------------------------------------------------------------------
# Custom Guard Plugin Tests
# ---------------------------------------------------------------------------


class TestCustomGuards:
    def test_custom_guard_detects_pattern(self):
        from mergewall.risk.guards.plugin import CustomGuard
        guard = CustomGuard(
            name="no-debug-print",
            pattern=r"print\(.*\)",
            category="dangerous_dependencies",
            level="low",
            message="Debug print found",
            suggestion="Remove before merge",
        )
        fd = _make_file_diff("app.py", ['print("hello")'])
        findings = guard.scan(fd)
        assert len(findings) == 1
        assert "no-debug-print" in findings[0].title

    def test_custom_guard_respects_file_pattern(self):
        from mergewall.risk.guards.plugin import CustomGuard
        guard = CustomGuard(
            name="js-only",
            pattern=r"console\.log",
            file_pattern="*.js",
        )
        fd_py = _make_file_diff("app.py", ['console.log("x")'])
        fd_js = _make_file_diff("app.js", ['console.log("x")'])
        assert len(guard.scan(fd_py)) == 0
        assert len(guard.scan(fd_js)) == 1

    def test_load_custom_guards_from_config(self):
        from mergewall.risk.guards.plugin import load_custom_guards
        from mergewall.config import GuardianConfig

        cfg = GuardianConfig()
        cfg._raw_custom_guards = [
            {"name": "no-console-log", "pattern": r"console\.log\(", "level": "low"},
            {"name": "no-todo", "pattern": r"TODO", "level": "low", "message": "TODO left in code"},
        ]
        guards = load_custom_guards(cfg)
        assert len(guards) == 2
        assert guards[0].name == "no-console-log"
        assert guards[1].pattern.pattern == r"TODO"

    def test_custom_guard_in_engine(self):
        import pytest
        from mergewall.risk.engine import DiffRiskEngine
        from mergewall.config import GuardianConfig
        from mergewall.risk.models import MergeDecision

        cfg = GuardianConfig()
        cfg._raw_custom_guards = [
            {"name": "no-debug", "pattern": r"debugger", "level": "critical"},
        ]
        engine = DiffRiskEngine(config=cfg)
        diff = StructuredDiff(files=[
            _make_file_diff("app.js", ["debugger;"]),
        ])
        import asyncio
        report = asyncio.run(engine.analyze(diff))
        assert any("no-debug" in f.title for f in report.findings)
        assert report.merge_decision == MergeDecision.BLOCK

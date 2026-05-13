"""Tests for the diff parser and risk models."""

import pytest
from mergewall.diff.parser import parse_diff
from mergewall.diff.models import ChangeType, StructuredDiff, FileDiff, Hunk, DiffLine
from mergewall.risk.models import (
    RiskCategory, RiskLevel, MergeDecision, DetectionMethod,
    RiskEvidence, RiskFinding, RiskReport,
)


# ---------------------------------------------------------------------------
# Diff Parser Tests
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/src/auth/login.py b/src/auth/login.py
index abc1234..def5678 100644
--- a/src/auth/login.py
+++ b/src/auth/login.py
@@ -10,6 +10,8 @@ def login(request):
     username = request.POST.get("username")
     password = request.POST.get("password")
     user = authenticate(username=username, password=password)
+    if not user:
+        return redirect("/login")
     if user is not None:
         login(request, user)
         return redirect("/dashboard")
@@ -25,3 +27,4 @@ def logout(request):
     logout(request)
     return redirect("/")

+# TODO: add rate limiting
diff --git a/requirements.txt b/requirements.txt
index 1111111..2222222 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,4 +1,4 @@
 django>=4.0
 requests>=2.28
-pytest>=7.0
+pytest>=6.0
 celery>=5.0
diff --git a/src/config/settings.py b/src/config/settings.py
new file mode 100644
--- /dev/null
+++ b/src/config/settings.py
@@ -0,0 +1,3 @@
+SECRET_KEY = "hardcoded-secret-key-12345"
+DEBUG = True
+ALLOWED_HOSTS = ["*"]
"""


def test_parse_diff_file_count():
    diff = parse_diff(SAMPLE_DIFF)
    assert len(diff.files) == 3


def test_parse_diff_file_paths():
    diff = parse_diff(SAMPLE_DIFF)
    assert diff.files[0].old_path == "src/auth/login.py"
    assert diff.files[0].new_path == "src/auth/login.py"
    assert diff.files[1].new_path == "requirements.txt"
    assert diff.files[2].new_path == "src/config/settings.py"


def test_parse_diff_change_types():
    diff = parse_diff(SAMPLE_DIFF)
    assert diff.files[0].change_type == ChangeType.MODIFIED
    assert diff.files[1].change_type == ChangeType.MODIFIED
    assert diff.files[2].change_type == ChangeType.ADDED


def test_parse_diff_hunks():
    diff = parse_diff(SAMPLE_DIFF)
    assert len(diff.files[0].hunks) == 2
    assert len(diff.files[1].hunks) == 1
    assert len(diff.files[2].hunks) == 1


def test_parse_diff_added_lines():
    diff = parse_diff(SAMPLE_DIFF)
    auth_file = diff.files[0]
    added = auth_file.added_lines
    assert len(added) == 3  # 2 in first hunk + 1 in second hunk
    assert added[0].content == "    if not user:"
    assert added[1].content == "        return redirect(\"/login\")"
    assert added[2].content == "# TODO: add rate limiting"


def test_parse_diff_removed_lines():
    diff = parse_diff(SAMPLE_DIFF)
    req_file = diff.files[1]
    removed = req_file.removed_lines
    assert len(removed) == 1
    assert removed[0].content == "pytest>=7.0"


def test_parse_diff_line_numbers():
    diff = parse_diff(SAMPLE_DIFF)
    settings_file = diff.files[2]
    added = settings_file.added_lines
    assert added[0].new_line == 1
    assert added[1].new_line == 2
    assert added[2].new_line == 3


def test_parse_diff_total_additions_deletions():
    diff = parse_diff(SAMPLE_DIFF)
    assert diff.total_additions == 7  # 3 + 1 + 3
    assert diff.total_deletions == 1  # 0 + 1 + 0


def test_parse_diff_changed_paths():
    diff = parse_diff(SAMPLE_DIFF)
    assert diff.changed_paths == [
        "src/auth/login.py",
        "requirements.txt",
        "src/config/settings.py",
    ]


def test_parse_diff_language_detection():
    diff = parse_diff(SAMPLE_DIFF)
    assert diff.files[0].language == "python"
    assert diff.files[1].language == "unknown"  # .txt has no mapping


def test_parse_diff_empty():
    diff = parse_diff("")
    assert len(diff.files) == 0
    assert diff.total_additions == 0


def test_parse_diff_binary_file():
    raw = """\
diff --git a/image.png b/image.png
index abc1234..def5678 100644
Binary files a/image.png and b/image.png differ
"""
    diff = parse_diff(raw)
    assert len(diff.files) == 1
    assert diff.files[0].is_binary is True


def test_parse_diff_new_file():
    raw = """\
diff --git a/new.py b/new.py
new file mode 100644
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+print("hello")
+print("world")
"""
    diff = parse_diff(raw)
    assert len(diff.files) == 1
    assert diff.files[0].change_type == ChangeType.ADDED
    assert len(diff.files[0].added_lines) == 2


def test_parse_diff_deleted_file():
    raw = """\
diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1,2 +0,0 @@
-print("hello")
-print("world")
"""
    diff = parse_diff(raw)
    assert len(diff.files) == 1
    assert diff.files[0].change_type == ChangeType.DELETED
    assert len(diff.files[0].removed_lines) == 2


def test_parse_diff_rename():
    raw = """\
diff --git a/old_name.py b/new_name.py
similarity index 95%
rename from old_name.py
rename to new_name.py
index abc1234..def5678 100644
--- a/old_name.py
+++ b/new_name.py
@@ -1,3 +1,3 @@
 def hello():
-    print("hi")
+    print("hello")
"""
    diff = parse_diff(raw)
    assert len(diff.files) == 1
    assert diff.files[0].change_type == ChangeType.RENAMED
    assert diff.files[0].old_path == "old_name.py"
    assert diff.files[0].new_path == "new_name.py"


# ---------------------------------------------------------------------------
# Risk Model Tests
# ---------------------------------------------------------------------------


def test_risk_report_markdown():
    report = RiskReport(
        pr_number=42,
        repo="org/repo",
        findings=[
            RiskFinding(
                category=RiskCategory.SECRET_LEAKAGE,
                level=RiskLevel.CRITICAL,
                title="Hardcoded AWS Key",
                why_dangerous="AWS key in source code exposes credentials",
                impact_scope="All repo consumers",
                evidence=RiskEvidence(
                    file_path="config.py",
                    line_numbers=[15],
                    code_snippet="AWS_KEY = 'AKIA...'",
                    detection_method=DetectionMethod.DETERMINISTIC,
                ),
                merge_decision=MergeDecision.BLOCK,
                approval_required=["security-team"],
                fix_suggestion="Use environment variables",
            ),
        ],
        merge_decision=MergeDecision.BLOCK,
        risk_score=25,
    )
    md = report.to_markdown()
    assert "Merge Blocked" in md
    assert "Hardcoded AWS Key" in md
    assert "CRITICAL" in md
    assert "security-team" in md
    assert "config.py:15" in md


def test_risk_report_checks_output():
    report = RiskReport(
        pr_number=1,
        repo="org/repo",
        findings=[
            RiskFinding(
                category=RiskCategory.AUTH_BYPASS,
                level=RiskLevel.HIGH,
                title="Auth check removed",
                why_dangerous="Login check bypassed",
                impact_scope="All endpoints",
                evidence=RiskEvidence(
                    file_path="api/views.py",
                    line_numbers=[42],
                    detection_method=DetectionMethod.DETERMINISTIC,
                ),
                merge_decision=MergeDecision.BLOCK,
            ),
        ],
        merge_decision=MergeDecision.BLOCK,
        risk_score=15,
    )
    output = report.to_checks_output()
    assert "Merge Blocked" in output["title"]
    assert len(output["annotations"]) == 1
    assert output["annotations"][0]["path"] == "api/views.py"
    assert output["annotations"][0]["annotation_level"] == "failure"


def test_risk_report_no_findings():
    report = RiskReport(pr_number=1, repo="org/repo")
    assert report.merge_decision == MergeDecision.ALLOW
    assert report.risk_score == 0
    md = report.to_markdown()
    assert "No risks detected" in md
    output = report.to_checks_output()
    assert "Approved" in output["title"]
    assert output["annotations"] == []

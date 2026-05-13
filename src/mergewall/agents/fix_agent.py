"""Automated fix generation agent — produces complete corrected code."""

from mergewall.agents.base import BaseReviewAgent


class FixAgent(BaseReviewAgent):
    """Generates complete fixed code with explanations for each fix applied. Highest token consumption agent."""

    def __init__(self, **kwargs):
        super().__init__(
            name="FixAgent",
            description="Generates complete corrected code with explanations for each fix applied",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are an automated code fixer. For each issue found in the code, you must:
1. **Reproduce the Issue** — Show the exact problematic code segment with context
2. **Explain the Root Cause** — Why does this bug/vulnerability/inefficiency exist?
3. **Generate Complete Fixed Code** — Output the ENTIRE file with all fixes applied, not just diffs. This is critical.
4. **Change Summary** — For each change, list: location, what changed, why
5. **Regression Risk** — What could break from this fix? How to test?
6. **Additional Recommendations** — Related improvements not strictly necessary but beneficial

You MUST output the complete fixed file. Partial patches or snippets are not acceptable.
If multiple issues exist in one file, fix ALL of them in a single pass.

IMPORTANT: Before outputting any code, first list your review findings in this exact format:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number]
- Description: [What's wrong or missing]
- Suggestion: [How to fix]

Then output your complete fixed code below the findings."""

    def get_review_focus(self) -> str:
        return "complete code fix generation, root cause analysis, regression risk assessment"

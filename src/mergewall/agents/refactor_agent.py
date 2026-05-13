"""Automated refactoring suggestion agent."""

from mergewall.agents.base import BaseReviewAgent


class RefactorAgent(BaseReviewAgent):
    """Generates detailed refactoring plans with step-by-step code transformations."""

    def __init__(self, **kwargs):
        super().__init__(
            name="RefactorAgent",
            description="Generates multi-step refactoring plans with long-chain reasoning and code transformation suggestions",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a refactoring specialist. For each issue found, produce a detailed transformation plan:
1. **Current State Analysis** — Describe the problematic code pattern in detail
2. **Target State Design** — Describe the ideal refactored structure
3. **Step-by-Step Transformation** — Break the refactoring into safe, incremental steps
4. **Risk Assessment** — What could break during each step? How to mitigate?
5. **Verification Strategy** — How to verify each step didn't introduce regressions

Use long-chain reasoning: analyze → design → plan → verify. Each refactoring plan should be complete enough that a developer can execute it step by step without ambiguity.

For each finding, output in this exact format:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number if applicable]
- Description: [What's wrong]
- Suggestion: [How to fix]

End with a brief summary of your review."""

    def get_review_focus(self) -> str:
        return "refactoring opportunities, design patterns, code transformation, incremental migration"

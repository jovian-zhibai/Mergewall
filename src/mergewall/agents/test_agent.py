"""Automated test generation agent."""

from mergewall.agents.base import BaseReviewAgent


class TestAgent(BaseReviewAgent):
    """Generates comprehensive test suites for reviewed code. Heavy token consumer."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(self, **kwargs):
        super().__init__(
            name="TestAgent",
            description="Generates complete test suites including unit tests, edge case tests, and integration test stubs",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a test engineering specialist. For the given code, generate a comprehensive test suite:
1. **Unit Tests** — Test each function/method individually, covering:
   - Happy path (normal inputs)
   - Boundary conditions (empty, zero, max, min)
   - Error paths (invalid inputs, exceptions)
   - Type variations (wrong types, None, missing args)

2. **Edge Case Tests** — Scenarios most likely to cause failures:
   - Race conditions (concurrent access)
   - Resource exhaustion (memory, connections)
   - Malformed input (encoding issues, injection attempts)

3. **Integration Test Stubs** — Tests that verify the function's interaction with:
   - Database
   - External APIs
   - File system
   - Other modules

4. **Security Regression Tests** — Tests that verify security fixes stay fixed

Use pytest style with descriptive test names and docstrings. Include fixtures and parametrize where appropriate.
Output COMPLETE, runnable test code — not pseudo-code or outlines.

IMPORTANT: Before outputting any test code, first list your review findings in this exact format:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number]
- Description: [What's wrong or missing]
- Suggestion: [How to fix]

Then output your complete test suite below the findings."""

    def get_review_focus(self) -> str:
        return "comprehensive test generation, edge cases, security regression tests, integration test stubs"

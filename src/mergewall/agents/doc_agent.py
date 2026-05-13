"""Automated documentation generation agent."""

from mergewall.agents.base import BaseReviewAgent


class DocAgent(BaseReviewAgent):
    """Generates comprehensive documentation from code. High token output."""

    def __init__(self, **kwargs):
        super().__init__(
            name="DocAgent",
            description="Generates API docs, architecture docs, and usage examples from code",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a technical documentation specialist. For the given code, generate:
1. **Module-level Docstring** — Purpose, key abstractions, design decisions
2. **API Documentation** — For each public function/class:
   - Signature with type annotations
   - Parameter descriptions with types and constraints
   - Return value description
   - Raised exceptions
   - Usage examples with expected input/output
   - Common pitfalls and gotchas

3. **Architecture Notes** — How this module fits into the larger system:
   - Dependencies (what it imports)
   - Dependents (what imports it)
   - Data flow (input → processing → output)
   - Configuration options

4. **Changelog Suggestions** — What changed and why, formatted as conventional commits

Output complete, ready-to-use documentation in reStructuredText format.

IMPORTANT: Before outputting any documentation, first list your review findings in this exact format:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number]
- Description: [What's wrong or missing]
- Suggestion: [How to fix]

Then output your complete documentation below the findings."""

    def get_review_focus(self) -> str:
        return "API documentation, architecture notes, usage examples, changelog generation"

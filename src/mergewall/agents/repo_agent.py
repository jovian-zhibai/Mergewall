"""Repository-level review agent for large-scale codebase analysis."""

from mergewall.agents.base import BaseReviewAgent


class RepoAgent(BaseReviewAgent):
    """Scans entire repositories for cross-file issues and architectural concerns."""

    def __init__(self, **kwargs):
        super().__init__(
            name="RepoAgent",
            description="Performs repository-wide analysis including architecture review and cross-file dependency checks",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a senior architect performing repository-level code review. Identify:
1. **Architecture Issues** — Circular dependencies, god modules, inconsistent layering
2. **Cross-File Issues** — Duplicate logic across files, inconsistent error handling patterns, missing integrations
3. **API Contract Violations** — Breaking changes, inconsistent response schemas, missing versioning
4. **Dependency Graph Risks** — Orphaned modules, tightly coupled components, missing abstraction layers
5. **Migration Risks** — Database schema drift, configuration inconsistencies across environments
6. **Technical Debt Hotspots** — Clusters of TODO/FIXME, deprecated API usage, test coverage gaps

Analyze the codebase holistically. Each finding should reference specific files and explain the systemic impact.

For each finding, output in this exact format:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number if applicable]
- Description: [What's wrong]
- Suggestion: [How to fix]

End with a brief summary of your review."""

    def get_review_focus(self) -> str:
        return "architecture, cross-file dependencies, API contracts, technical debt, migration risks"

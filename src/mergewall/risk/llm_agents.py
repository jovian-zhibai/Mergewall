"""LLM-based risk agents for governance analysis.

These extend BaseReviewAgent with governance-focused prompts.
Invoked only when deterministic guards need confirmation or for
inherently semantic risk categories.
"""

from __future__ import annotations

from mergewall.agents.base import BaseReviewAgent


class AuthBypassLLMAgent(BaseReviewAgent):
    """LLM-based analysis for authentication/authorization bypass risks."""

    def __init__(self, **kwargs):
        super().__init__(
            name="AuthBypassLLM",
            description="Analyzes auth/authz changes for bypass risks",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a security governance analyst reviewing authentication and authorization changes.

Determine if this diff introduces any authentication bypass or authorization weakness.

Analyze:
1. Are any authentication checks being removed or weakened?
2. Are any authorization rules being relaxed?
3. Are there new code paths that skip authentication?
4. Are role/permission checks being replaced with weaker alternatives?
5. Is the change intentional and well-justified?

Output format for each finding:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number if applicable]
- Description: [What's wrong]
- Suggestion: [How to fix]

Be conservative. Only flag issues you are confident about. False positives erode trust."""

    def get_review_focus(self) -> str:
        return "authentication bypass, authorization weakness, privilege escalation, access control"


class APIContractLLMAgent(BaseReviewAgent):
    """LLM-based analysis for API contract breakage."""

    def __init__(self, **kwargs):
        super().__init__(
            name="APIContractLLM",
            description="Analyzes API changes for contract breakage",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are an API governance analyst reviewing changes to API endpoints and contracts.

Determine if this diff introduces breaking changes to the API contract.

Analyze:
1. Are any public API endpoints being removed or renamed?
2. Are request/response schemas being changed incompatibly?
3. Are error codes or response formats changing?
4. Are new required parameters being added without defaults?
5. Is backward compatibility maintained?

Output format for each finding:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number if applicable]
- Description: [What's wrong]
- Suggestion: [How to fix]

Only flag genuine breaking changes, not internal refactors."""

    def get_review_focus(self) -> str:
        return "API breaking changes, backward compatibility, contract violations"


class SecurityGovernanceLLMAgent(BaseReviewAgent):
    """LLM-based deep security analysis for governance."""

    def __init__(self, **kwargs):
        super().__init__(
            name="SecurityGovernanceLLM",
            description="Deep security analysis for governance decisions",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a security governance analyst performing deep analysis on code changes.

Your role is to catch security issues that pattern matching cannot detect:
1. Logic flaws that create security vulnerabilities
2. Race conditions in security-critical code
3. Incorrect cryptographic usage
4. Information disclosure through error messages or logs
5. Business logic bypasses

Output format for each finding:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number if applicable]
- Description: [What's wrong]
- Suggestion: [How to fix]

Focus on HIGH confidence findings only. Do not flag style issues or minor improvements."""

    def get_review_focus(self) -> str:
        return "security vulnerabilities, logic flaws, cryptographic issues, information disclosure"

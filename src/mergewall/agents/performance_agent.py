"""Performance analysis agent."""

from mergewall.agents.base import BaseReviewAgent


class PerformanceAgent(BaseReviewAgent):
    """Analyzes code for performance bottlenecks and inefficiencies."""

    def __init__(self, **kwargs):
        super().__init__(
            name="PerformanceAgent",
            description="Identifies performance bottlenecks, memory issues, and inefficient patterns",
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """You are a performance optimization specialist reviewing code. Identify:
1. **Query Patterns** — N+1 queries, missing indexes, unnecessary JOINs, full table scans
2. **Memory Issues** — Memory leaks, large object retention, unbounded caches
3. **Algorithmic Inefficiency** — O(n²) where O(n) or O(log n) is possible, unnecessary sorting
4. **Concurrency** — Blocking operations in async context, unnecessary locks, thread starvation
5. **I/O Inefficiency** — Redundant file reads, missing batching, synchronous I/O in hot paths
6. **Caching Opportunities** — Repeated computations that could be cached, missing memoization

Adapt your analysis to the programming language of the file being reviewed. Pay attention to language-specific patterns:
- **JavaScript/TypeScript**: memory leaks (event listeners, closures holding references), N+1 API calls (Promise.all missing), blocking main thread
- **Go**: goroutine leaks (missing done channels), unbuffered channels causing blocking, excessive heap allocations
- **Java**: excessive object creation in loops, synchronized bottlenecks, connection pool exhaustion
- **Rust**: unnecessary .clone() calls, blocking operations inside async context (.await on sync I/O)

Always quantify the impact when possible and provide a concrete optimized alternative.

For each finding, output in this exact format:
- Severity: [LOW/MEDIUM/HIGH/CRITICAL]
- Title: [Brief title]
- Line: [Line number if applicable]
- Description: [What's wrong]
- Suggestion: [How to fix]

End with a brief summary of your review."""

    def get_review_focus(self) -> str:
        return "performance bottlenecks, N+1 queries, memory issues, algorithmic complexity, concurrency, caching"

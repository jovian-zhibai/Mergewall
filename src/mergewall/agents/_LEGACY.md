# _LEGACY.md — Legacy Module from RevHive

This module was inherited from **RevHive** (the sister project by the same author)
and is **not used in the Mergewall governance pipeline** (`mergewall govern`).

## What's here

11 specialized review agents:
- `StyleAgent` — code style review
- `SecurityAgent` — security vulnerability scanning
- `PerformanceAgent` — performance analysis
- `LogicAgent` — logic/edge-case review
- `RepoAgent` — repository-level analysis
- `RefactorAgent` — refactoring suggestions
- `FixAgent` — auto-fix generation
- `TestAgent` — test coverage analysis
- `DocAgent` — documentation review
- `CoordinatorAgent` — synthesis/deduplication
- `ConversationReviewer` — multi-turn deep review

## Why it's still here

- The `mergewall review` CLI command (legacy advisory mode) still uses these agents
- `risk/llm_agents.py` extends `BaseReviewAgent` from `agents/base.py`
- `config.py` imports the `Severity` enum from `agents/base.py`
- `utils/dedup.py` uses `ReviewFinding` and `SEVERITY_ORDER`
- `demo.py` uses `AgentResult`, `ReviewFinding`, `Severity`, and `CoordinatorAgent`

## Dependency chain

```
main.py (review command) → graph/workflow.py → agents/*
risk/llm_agents.py → agents/base.py (BaseReviewAgent)
config.py → agents/base.py (Severity)
utils/dedup.py → agents/base.py (ReviewFinding, SEVERITY_ORDER)
```

**Status as of 2025-07-14:** `team/` and `analysis/` directories have been deleted. `agents/` and `graph/` remain because they are still imported by active modules.

## Mergewall governance vs. RevHive review

| | RevHive agents/ | Mergewall governance |
|---|---|---|
| **Purpose** | Multi-agent LLM code review | Deterministic risk enforcement |
| **Output** | Advisory findings (LOW-HIGH) | Block/Allow decisions |
| **Enforcement** | None (PR comments) | GitHub Checks API (blocks merge) |
| **False positives** | Possible (LLM hallucination) | Zero (regex/deterministic) |

## Future

This module may be removed or extracted into a standalone `revhive-agents` package
in a future release, leaving only `base.py` (which the governance LLM layer depends on).

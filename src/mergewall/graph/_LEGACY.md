# _LEGACY.md — Legacy Module from RevHive

This module was inherited from **RevHive** (the sister project by the same author)
and is **not used in the Mergewall governance pipeline** (`mergewall govern`).

## What's here

- `CodeReviewWorkflow` — LangGraph-based multi-agent review orchestrator
- `ReviewState` — Shared state for 9 concurrent review agents
- `ReviewReport` — Markdown/JSON report formatter for review findings

## Why it's still here

- The `mergewall review` CLI command (legacy advisory mode) uses `CodeReviewWorkflow`
- `server/worker.py` uses it as a fallback when governance mode is not configured

**Status as of 2025-07-14:** `team/` and `analysis/` directories have been deleted. `graph/` remains for the legacy `review` CLI command.

## Mergewall governance

The governance pipeline (`mergewall govern`) does **not** use this workflow.
Instead it uses:
```
diff/parser → risk/engine (deterministic guards) → policy/engine → enforcement
```

## Future

This module may be removed or repurposed in a future release.

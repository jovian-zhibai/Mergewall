# _LEGACY.md — Legacy Module from RevHive

This module was inherited from **RevHive** (the sister project by the same author)
and is **not used in the Mergewall governance pipeline** (`mergewall govern`).

## What's here

- `TeamBatchProcessor` — batch code review across multiple repositories
- `RepoConfig` / `TeamConfig` — configuration for team-level monitoring
- Token budget tracking for high-volume LLM consumption

## Why it's unused

Mergewall focuses on per-PR governance enforcement, not batch repository scanning.
The governance pipeline processes one diff at a time via the CLI or GitHub webhook.

## Future

This module may be removed or extracted into a standalone team-monitoring tool
in a future release.

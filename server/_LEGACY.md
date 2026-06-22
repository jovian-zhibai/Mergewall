# _LEGACY.md — Partially Active Module

This `server/` directory contains a GitHub App webhook receiver inherited from **RevHive**.
It is **partially active** — the governance pipeline uses it, but with issues.

## What's here

- `app.py` — FastAPI webhook receiver (GitHub signature verification)
- `worker.py` — Async PR processor (supports both governance and legacy review)
- `config_server.py` — Server environment configuration

## Current status

- The `EnforcementEngine` in `src/mergewall/enforcement/engine.py` imports
  `post_pr_comment` from `server/worker.py` — creating a circular dependency risk
- `worker.py` detects governance mode via `config.governance_mode` and uses
  `EnforcementEngine` when governance is active
- The server requires `pyjwt` (JWT signing for GitHub App auth) which is in
  optional server deps

## Mergewall governance

The server is the **recommended deployment** for Mergewall in production —
it receives GitHub webhooks and runs the full governance pipeline automatically.

## Issues to fix

1. `enforcement/engine.py` → `server/worker.py` coupling should be reversed
2. Server needs proper testing
3. `config_server.py` has a default `GITHUB_APP_ID` hardcoded

## Future

The server should be refactored so that `post_pr_comment` lives in
`src/mergewall/enforcement/` (where it belongs) rather than in `server/worker.py`.

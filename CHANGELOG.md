# Changelog

All notable changes to Mergewall are documented in this file.

## 0.1.0 (2026-06-22)

### Added

- 6 deterministic risk guards: secret leakage, auth bypass, permission escalation,
  API contract breakage, dangerous dependencies, blast radius
- Policy engine with path rules and threshold rules
- GitHub Checks API enforcement (block/require_approval/warn/allow)
- JSONL audit trail with `mergewall audit` viewer
- CLI commands: `govern`, `demo`, `init`, `audit`, `review`
- Demo mode — zero-config evaluation with mock risks
- `mergewall init` — generates starter .mergewall.yml
- Configuration validation with clear error messages
- SARIF output for GitHub Code Scanning (`--format sarif`)
- Custom guard plugins via `.mergewall.yml`
- PR comment template for governance reports
- 5 policy templates: starter, strict, fintech, monorepo, opensource
- Pre-commit hook support (`mergewall hook-install`)
- Reusable GitHub Action (`action.yml`)
- 7 LLM backend presets: MiMo, OpenAI, DeepSeek, Anthropic, Qwen, GLM, Kimi
- Docker support
- 128 tests

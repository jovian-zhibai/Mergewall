# Contributing to Mergewall

We welcome contributions! Mergewall is an AI merge governance runtime.

## Getting Started

```bash
git clone https://github.com/jovian-zhibai/Mergewall.git
cd Mergewall
pip install -e ".[dev]"
mergewall demo  # Demo mode (no API key needed)
```

## Development Workflow

1. Fork the repo and create a branch
2. Make your changes
3. Run tests: `pytest -v`
4. Run linter: `ruff check src/ tests/`
5. Submit a PR

## Project Structure

```
src/mergewall/
  diff/          # Unified diff parser
  risk/          # Diff Risk Engine + 6 deterministic guards
    guards/      # Secret, auth, permission, API, deps, blast radius guards
    plugin.py    # Custom guard loader from .mergewall.yml
  policy/        # Policy Engine (path rules, thresholds, validation)
  enforcement/   # GitHub Checks API + PR comment formatter
  audit/         # JSONL audit trail
  memory/        # Per-module risk history
  output/        # SARIF output for GitHub Code Scanning
  agents/        # Legacy review agents (from RevHive)
  graph/         # Legacy LangGraph workflow (from RevHive)
  utils/         # Shared utilities (LLM client, dedup, parser)
  config.py      # Configuration loader
  demo.py        # Governance demo mode
  main.py        # CLI entry point
tests/           # 128 tests
templates/       # Policy templates + PR comment template
```

## Adding a Custom Risk Guard

The simplest way to extend Mergewall is by defining a custom guard in `.mergewall.yml`:

```yaml
custom_guards:
  - name: "no-console-log"
    pattern: "console\\.log\\("
    file_pattern: "*.js"
    level: "low"
    message: "Remove console.log before merge"
```

For programmatic guards, create a new file in `src/mergewall/risk/guards/`,
extend `BaseGuard`, implement `scan()`, and register in `DiffRiskEngine._init_guards()`.

## Security Reporting

If you discover a security vulnerability, please report it via a [GitHub Issue](https://github.com/jovian-zhibai/Mergewall/issues) with the `security` label. Do not disclose vulnerabilities publicly until a fix is available.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | **Yes** | — | API key for the LLM provider |
| `LLM_BASE_URL` | No | `https://api.xiaomimimo.com/v1` | LLM API endpoint |
| `LLM_MODEL` | No | `mimo-v2.5-pro` | Model name or preset (`mimo`, `openai`, `deepseek`, `qwen`, `glm`, `kimi`, `claude`) |
| `GITHUB_WEBHOOK_SECRET` | Server only | — | HMAC secret for webhook signature verification |
| `GITHUB_APP_ID` | Server only | — | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | Server only | — | PEM private key content |
| `GITHUB_PRIVATE_KEY_PATH` | Server only | `mergewall-bot.private-key.pem` | Path to PEM file (local dev fallback) |

## Supported LLM Backends

| Provider | Model | Preset Name |
|---|---|---|
| **MiMo (Xiaomi)** | `mimo-v2.5-pro` | `mimo` |
| OpenAI | `gpt-4o` | `openai` |
| DeepSeek | `deepseek-chat` | `deepseek` |
| Qwen (Alibaba) | `qwen-plus` | `qwen` |
| GLM (Zhipu) | `glm-4` | `glm` |
| Kimi | `kimi` | `kimi` |
| **Anthropic** | `claude-sonnet-4-20250514` | `claude` |

Install optional provider dependencies: `pip install -e ".[anthropic]"`

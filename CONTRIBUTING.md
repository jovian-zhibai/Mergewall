# Contributing to CodeGuardian

We welcome contributions! CodeGuardian is an AI-powered multi-agent code review system.

## Getting Started

```bash
git clone https://github.com/SoulJian03/CodeGuardian.git
cd CodeGuardian
pip install -e ".[dev]"
python examples/sample_review.py  # Demo mode (no API key needed)
```

## Development Workflow

1. Fork the repo and create a branch
2. Make your changes
3. Run tests: `pytest -v`
4. Run linter: `ruff check src/ tests/`
5. Submit a PR

## Project Structure

```
src/codeguardian/
  agents/       # Specialized review agents
  graph/        # LangGraph workflow orchestration
  utils/        # Parsing utilities
  team/         # Batch processing engine
  analysis/     # Historical trend analysis
  demo.py       # Demo mode (no API key required)
```

## Adding a New Agent

1. Create a new file in `src/codeguardian/agents/`
2. Extend `BaseReviewAgent`
3. Implement `get_system_prompt()` and `get_review_focus()`
4. Register in `agents/__init__.py`
5. Add to the `_AGENT_CLASSES` registry in `graph/workflow.py`

## Security Reporting

If you discover a security vulnerability, please report it via a [GitHub Issue](https://github.com/SoulJian03/CodeGuardian/issues) with the `security` label. Do not disclose vulnerabilities publicly until a fix is available.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | **Yes** | — | API key for the LLM provider |
| `LLM_BASE_URL` | No | `https://api.xiaomimimo.com/v1` | LLM API endpoint |
| `LLM_MODEL` | No | `mimo-v2.5-pro` | Model name or preset (`mimo`, `openai`, `deepseek`, `qwen`, `glm`, `kimi`, `claude`) |
| `GITHUB_WEBHOOK_SECRET` | Server only | — | HMAC secret for webhook signature verification |
| `GITHUB_APP_ID` | Server only | — | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | Server only | — | PEM private key content |
| `GITHUB_PRIVATE_KEY_PATH` | Server only | `codeguardian-bot.private-key.pem` | Path to PEM file (local dev fallback) |

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

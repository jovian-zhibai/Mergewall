# CodeGuardian

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![LangGraph](https://img.shields.io/badge/framework-LangGraph-orange)](https://langchain-ai.github.io/langgraph/)
[![MiMo](https://img.shields.io/badge/powered_by-MiMo-red)](https://platform.xiaomimimo.com)
[![Agents](https://img.shields.io/badge/agents-10-blue)]()
[![CI](https://github.com/SoulJian03/CodeGuardian/actions/workflows/ci.yml/badge.svg)](https://github.com/SoulJian03/CodeGuardian/actions)

**AI-Powered Multi-Agent Code Review & Security Scanning System**

CodeGuardian deploys 10 specialized AI agents — 9 reviewing in parallel, 1 synthesizing results — to catch security vulnerabilities, performance bottlenecks, logic bugs, and style issues before they reach production.

### Risk Score

Every review outputs a risk score (0-100) so you know at a glance whether it's safe to merge:

| Score | Level | Meaning |
|-------|-------|---------|
| 0-20 | ✅ LOW | Safe to merge |
| 21-50 | ⚠️ MEDIUM | Review recommended before merge |
| 51-80 | 🔴 HIGH | Fix before merge |
| 81-100 | 🚨 CRITICAL | Do not merge |

Example output:

```
🚨 Risk Score: CRITICAL (81/100)

1 Critical · 2 High · 4 Medium · 6 Low
```

## Why CodeGuardian?

| Pain Point | CodeGuardian Solution |
|---|---|
| Manual CR takes 1-2 hours/day | 9 agents review in parallel in under 30 seconds |
| Human reviewers miss subtle bugs | Each agent is a domain expert (security, perf, logic...) |
| "LGTM" culture devalues review | Every PR gets a thorough, objective audit |
| No team-wide quality visibility | Trend analysis tracks code health over time |

## Architecture

```
┌─────────────┐
│  Coordinator │ ← Synthesizes findings, resolves conflicts
└──────┬──────┘
       │ collects results from 9 parallel agents
       ▼
  Style  Security  Perf  Logic  Repo  Refactor  Fix  Test  Doc
```

**ConversationReviewer** runs on-demand multi-turn deep review of individual findings — challenging assumptions, exploring alternative fixes, and testing edge cases through 5 rounds of dialogue. Used for critical/high severity findings in team batch mode.

### All 10 Agents

| Agent | Role |
|---|---|
| **StyleAgent** | Naming conventions, formatting, documentation |
| **SecurityAgent** | SQL injection, XSS, secrets, weak crypto, auth flaws |
| **PerformanceAgent** | N+1 queries, memory leaks, algorithmic complexity |
| **LogicAgent** | Edge cases, error handling, race conditions, type safety |
| **RepoAgent** | Architecture review, cross-file dependencies, tech debt |
| **RefactorAgent** | Design patterns, code transformation, incremental migration |
| **FixAgent** | Generates complete corrected code with root cause analysis |
| **TestAgent** | Unit tests, edge case tests, security regression tests |
| **DocAgent** | API docs, architecture docs, usage examples |
| **Coordinator** | Deduplicates, prioritizes, resolves conflicts, generates report |

## Quick Start

```bash
# 1. Install
git clone https://github.com/SoulJian03/CodeGuardian.git
cd CodeGuardian
pip install -e ".[dev]"

# 2. Try demo mode (no API key needed!)
python examples/sample_review.py

# 3. Set your LLM API key
export LLM_API_KEY=your-api-key

# 4. Review code immediately
codeguardian review --file src/main.py
codeguardian review --diff HEAD~1
```

No GitHub App required for CLI usage. See [GitHub App Integration](#github-app-integration) for automatic PR reviews.

## Demo Mode

CodeGuardian ships with a fully functional **demo mode** that runs the complete multi-agent pipeline with mock responses. No API key, no network, no cost — perfect for evaluation.

```bash
python examples/sample_review.py
```

This produces a realistic review report identical in structure to a live MiMo-backed run, including:
- 20+ simulated findings across all 9 review agents
- Severity-ordered report (CRITICAL / HIGH / MEDIUM / LOW)
- Markdown and JSON output formats

## Supported LLM Backends

| Provider | Model | Setup |
|---|---|---|
| **MiMo (Xiaomi)** | `mimo-v2.5-pro` | `LLM_BASE_URL=https://api.xiaomimimo.com/v1` |
| OpenAI | `gpt-4o` | `LLM_BASE_URL=https://api.openai.com/v1` |
| DeepSeek | `deepseek-chat` | `LLM_BASE_URL=https://api.deepseek.com/v1` |
| Qwen (Alibaba) | `qwen-plus` | `LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1` |
| GLM (Zhipu) | `glm-4` | `LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4` |
| Kimi | `kimi` | `LLM_BASE_URL=https://api.moonshot.cn/v1` |
| **Anthropic** | `claude-sonnet-4-20250514` | `pip install -e ".[anthropic]"`, set `ANTHROPIC_API_KEY` |

**Quick preset:** Set `LLM_MODEL` to a preset name (e.g., `openai`, `deepseek`, `qwen`) and CodeGuardian auto-configures the base URL. Explicit `LLM_BASE_URL` takes priority.

MiMo is the **default and recommended backend**. CodeGuardian is optimized for MiMo's token economics and model capabilities.

## Supported Languages

CodeGuardian's LLM-powered agents can review code in any language. Currently optimized for:

| Language | Extensions | Security Patterns | Performance Patterns |
|----------|-----------|-------------------|---------------------|
| Python | .py | ✅ Full | ✅ Full |
| JavaScript/TypeScript | .js .jsx .mjs .ts .tsx | ✅ Full | ✅ Full |
| Go | .go | ✅ Full | ✅ Full |
| Rust | .rs | ✅ Full | ✅ Full |
| Java | .java | ✅ Full | ✅ Full |
| C/C++ | .c .cpp .h .hpp | ✅ Core | ⚠️ Basic |
| Ruby | .rb | ✅ Core | ⚠️ Basic |
| PHP | .php | ✅ Full | ⚠️ Basic |
| Swift | .swift | ✅ Core | ⚠️ Basic |
| Kotlin | .kt | ✅ Core | ⚠️ Basic |

Other languages are supported via LLM understanding but may have fewer specialized patterns.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | **Yes** | — | API key for the LLM provider |
| `LLM_BASE_URL` | No | `https://api.xiaomimimo.com/v1` | LLM API endpoint |
| `LLM_MODEL` | No | `mimo-v2.5-pro` | Model name |
| `GITHUB_WEBHOOK_SECRET` | Server only | — | HMAC secret for webhook signature verification |
| `GITHUB_APP_ID` | Server only | — | GitHub App ID for installation token auth |
| `GITHUB_PRIVATE_KEY` | Server only | — | PEM private key content (preferred for Railway/deploy) |
| `GITHUB_PRIVATE_KEY_PATH` | Server only | `codeguardian-bot.private-key.pem` | Path to PEM file (local dev fallback) |

## Configuration

Create `.codeguardian.yml` in your project root:

```yaml
model: mimo-v2.5-pro

agents:
  style:
    enabled: true
  security:
    enabled: true
    severity_threshold: medium   # only report medium and above
  performance:
    enabled: true
  logic:
    enabled: true
  repo:
    enabled: true
  refactor:
    enabled: true
  fix:
    enabled: true
  test:
    enabled: true
  doc:
    enabled: false               # disable documentation agent

ignore:                          # glob patterns — ** matches any depth
  - "*.min.js"
  - "*.min.css"
  - "vendor/**"
  - "node_modules/**"
  - "migrations/**"
  - "__pycache__/**"
  - ".git/**"
  - ".venv/**"
```

## GitHub App Integration

For automatic PR reviews, install the CodeGuardian GitHub App and configure the webhook server. For command-line usage, no GitHub App is needed.

```yaml
# .github/workflows/code-review.yml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .
      - name: Run CodeGuardian Review
        env:
          LLM_API_KEY: ${{ secrets.MIMO_API_KEY }}
          LLM_BASE_URL: https://api.xiaomimimo.com/v1
          LLM_MODEL: mimo-v2.5-pro
        run: |
          codeguardian review --diff HEAD~1 --format markdown --output review_report.md
      - name: Post Review Comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('review_report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

## Token Consumption

CodeGuardian is designed for high-throughput token consumption — making it an ideal workload for MiMo's free tier or high-capacity plans:

| Mode | Tokens / Event | Use Case |
|---|---|---|
| Single file 9-agent review | ~35,000 | Per-PR or on-demand |
| Auto-fix generation | ~50,000 | Post-review fix |
| Test suite generation | ~40,000 | Coverage gap fill |
| Multi-turn deep review | ~120,000 | Critical security findings |
| Repo-level full scan | ~1,500,000 | Code health audit |
| Team daily batch | ~10,000,000 | 5+ repos continuous monitoring |

## Project Structure

```
src/codeguardian/
  agents/          # 10 specialized review agents
  graph/           # LangGraph workflow orchestration
  utils/           # Utility modules
  team/            # Batch processing engine
  analysis/        # Historical trend analysis
  demo.py           # Demo mode (no API key required)
  main.py           # CLI entry point
tests/              # 45+ tests covering agents, workflow, demo
examples/           # Ready-to-run examples
```

## Security

CodeGuardian takes its own security seriously:

- **Dependency scanning** — `pip-audit` runs in CI on every push and PR to catch known CVEs in dependencies.
- **Static analysis** — `bandit` scans the source code for common security issues (hardcoded secrets, unsafe deserialization, injection risks).
- **Docker hardening** — the container runs as a non-root user (`appuser`). Sensitive files (`.env`, `*.pem`, `.git/`) are excluded via `.dockerignore`.

To run security checks locally:

```bash
pip install pip-audit bandit
pip-audit
bandit -r src/ -c pyproject.toml
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions welcome!

## License

MIT — see [LICENSE](LICENSE).






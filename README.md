# Mergewall

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/jovian-zhibai/Mergewall/actions/workflows/ci.yml/badge.svg)](https://github.com/jovian-zhibai/Mergewall/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mergewall)](https://pypi.org/project/mergewall/)

**AI Merge Governance Runtime — Block high-risk AI-generated code from entering production.**

Mergewall is not another code review tool. It's a governance runtime that sits between AI-written code and your production branch. It analyzes every PR diff, scores risk, enforces policies, and blocks merges when necessary.

```
PR opened → Diff Parser → Risk Engine → Policy Engine → GitHub Checks API
                                      → PR Comment
                                      → Audit Trail
```

## Why Mergewall?

| Problem | Mergewall Solution |
|---|---|
| AI writes 30-60% of code, nobody reviews it properly | Deterministic risk guards catch secrets, auth bypass, dangerous deps |
| Advisory review tools get ignored | GitHub Checks API blocks merge when risk is too high |
| "LGTM" culture lets bugs through | Policy engine enforces org rules per directory |
| No audit trail for compliance | JSONL audit log of every governance decision |

## Mergewall + RevHive

Mergewall handles **mandatory governance** (blocking high-risk merges), while
[RevHive](https://github.com/jovian-zhibai/RevHive) provides **advisory review**
(multi-agent code quality analysis). They complement each other:

- RevHive reviews code and outputs a risk score → Mergewall can consume it as governance input
- Mergewall blocks a PR and suggests fixes → RevHive's FixAgent can auto-generate patches

| | RevHive | Mergewall |
|---|---|---|
| **Goal** | Find issues | Prevent issues |
| **Output** | Review report + suggestions | Block / Allow decision |
| **Enforcement** | Advisory (PR comments) | Mandatory (GitHub Checks) |

## Risk Categories

Mergewall detects 6 categories of high-value, high-impact risks:

| Category | Detection | Confidence |
|---|---|---|
| **Secret Leakage** | AWS keys, GitHub tokens, private keys, JWTs | Deterministic |
| **Auth Bypass** | Removed auth decorators, added bypass flags | Deterministic |
| **Permission Escalation** | is_superuser=True, wildcard permissions | Deterministic |
| **API Contract Breakage** | Removed public functions, changed signatures | Deterministic |
| **Dangerous Dependencies** | Version downgrades, unpinned versions | Deterministic |
| **Blast Radius** | Large changes, shared module modifications | Deterministic |

**Zero false positives on the core path.** Every guard is deterministic (regex/pattern matching). LLM agents are available as optional confirmation for ambiguous cases.

## Quick Start

```bash
# Install
pip install mergewall

# Generate default configuration
mergewall init

# Try the demo (no API key needed)
mergewall demo

# Run governance on a diff
mergewall govern --diff HEAD~1

# View audit trail
mergewall audit
```

For development:

```bash
git clone https://github.com/jovian-zhibai/Mergewall.git
cd Mergewall
pip install -e ".[dev]"
```

## Audit Trail

Every governance decision is logged to `.mergewall/audit.jsonl`:

```json
{"repo": "org/repo", "pr_number": 42, "merge_decision": "block", "risk_score": 25, "finding_count": 1, "required_approvals": ["security-team"], "timestamp": "2026-05-14T..."}
```

View the audit trail:

```bash
mergewall audit
```

This displays the last 20 decisions in a table:

```
Timestamp            Repo                 Decision           Score   Findings
------------------------------------------------------------------------------
2025-07-14T12:00:00  org/repo             block              85      6
2025-07-14T11:55:00  org/repo             allow              0       0
```

## Policy Templates

Jump-start your configuration with a pre-built template:

| Template | Use Case |
|---|---|
| `starter.yml` | Minimal — block CRITICAL only |
| `strict.yml` | Aggressive — score>30 approval, >60 block |
| `fintech.yml` | Financial — auth changes require security-team |
| `monorepo.yml` | Monorepo — per-directory risk grading |
| `opensource.yml` | Open source — strict review for contributors |

```bash
# Copy a template to .mergewall.yml to get started
cp templates/starter.yml .mergewall.yml
```

## Custom Guards

Define your own pattern-based risk guards in `.mergewall.yml` without writing Python code:

```yaml
# .mergewall.yml
custom_guards:
  - name: "no-console-log"
    pattern: "console\\.log\\("
    category: "dangerous_dependencies"
    level: "low"
    message: "Remove console.log before merging to production"
    suggestion: "Use a structured logger instead"
    file_pattern: "*.js"

  - name: "no-debugger"
    pattern: "debugger"
    level: "critical"
    message: "debugger statement will halt execution in browsers"
```

Custom guards run after the 6 built-in deterministic guards. Each guard produces a standard `RiskFinding` with the specified category and severity.

## How It Works

### 1. Diff Parser

Parses raw unified diff into structured per-file data:

```python
from mergewall.diff.parser import parse_diff

diff = parse_diff(raw_diff)
# diff.files[0].added_lines, .removed_lines, .language, .change_type
```

### 2. Risk Engine

Runs 6 deterministic guards on every file in the diff:

```python
from mergewall.risk.engine import DiffRiskEngine

engine = DiffRiskEngine()
report = await engine.analyze(structured_diff)
# report.findings, report.merge_decision, report.risk_score
```

Each finding includes:
- **Risk type** (category)
- **Risk level** (CRITICAL / HIGH / MEDIUM / LOW)
- **Why dangerous** (human-readable explanation)
- **Impact scope** (what could be affected)
- **Merge decision** (BLOCK / REQUIRE_APPROVAL / WARN / ALLOW)
- **Fix suggestion**
- **Confidence score** (0.0-1.0)

### 3. Policy Engine

Evaluates findings against repository-level governance rules:

```yaml
# .mergewall.yml
governance:
  mode: "governance"

  path_rules:
    - paths: ["src/auth/**"]
      risk_categories: ["auth_bypass", "permission_escalation"]
      min_level: "medium"
      action: "block"
      require_approval_from: ["security-team"]

    - paths: ["**"]
      risk_categories: ["secret_leakage"]
      min_level: "low"
      action: "block"

  threshold_rules:
    - min_score: 60
      action: "block"
    - min_score: 30
      action: "require_approval"

  default_action: "warn"
  min_confidence: 0.7
```

### 4. Enforcement (GitHub Checks API)

Creates check runs on commits that block merges when branch protection is enabled:

- `BLOCK` → red X (`action_required`)
- `REQUIRE_APPROVAL` → red X (`action_required`)
- `WARN` → gray circle (`neutral`)
- `ALLOW` → green check (`success`)

## CLI Commands

```bash
# Generate default configuration
mergewall init

# Run governance demo with mock risks (no API key)
mergewall demo

# Run governance analysis (exit code 1 if blocked)
mergewall govern --diff HEAD~1

# Run governance with JSON output
mergewall govern --diff HEAD~1 --format json

# Run governance with SARIF output (GitHub Code Scanning)
mergewall govern --diff HEAD~1 --format sarif --output results.sarif

# Save report to file
mergewall govern --diff HEAD~1 --output report.md

# View audit trail
mergewall audit

# Legacy review mode (advisory, no enforcement)
mergewall review --file src/main.py
mergewall review --diff HEAD~1
```

## GitHub Actions Integration

```yaml
# .github/workflows/governance.yml
name: Mergewall Governance
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  govern:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      checks: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .
      - name: Run Governance
        env:
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: mergewall govern --diff origin/main --format sarif --output results.sarif
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

Then enable "Require status checks to pass" in branch protection settings.

### Using the Reusable Action

```yaml
# .github/workflows/governance.yml
name: Mergewall Governance
on: [pull_request]
jobs:
  govern:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      checks: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: jovian-zhibai/Mergewall@v0.1.0
        with:
          diff-ref: origin/${{ github.base_ref }}
          format: sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

## Pre-commit Hook

Run governance checks before every commit:

```bash
# Install the hook (one-time)
mergewall hook-install

# Now every git commit runs governance checks automatically
git commit -m "fix: update auth logic"
# 🛡️ Mergewall Pre-commit Check
# Risk Score: 0/100 — Clean, commit allowed.
```

To skip the hook temporarily:

```bash
SKIP=mergewall git commit -m "wip: checkpoint"
```

To uninstall:

```bash
rm .git/hooks/pre-commit
```

## Configuration

Generate a starter config:

```bash
mergewall init
```

Or create `.mergewall.yml` manually. See [Policy Templates](#policy-templates) for ready-made configurations.

### Example `.mergewall.yml`

```yaml
# mergewall init generates this starter template
model: mimo-v2.5-pro

agents:
  security:
    enabled: true
  style:
    enabled: false    # Disabled in governance mode
  refactor:
    enabled: false

governance:
  mode: "governance"

  path_rules:
    - paths: ["src/auth/**", "**/middleware/auth*"]
      risk_categories: ["auth_bypass", "permission_escalation"]
      min_level: "medium"
      action: "block"
      require_approval_from: ["security-team"]

    - paths: ["migrations/**"]
      risk_categories: ["*"]
      min_level: "high"
      action: "require_approval"

    - paths: ["**"]
      risk_categories: ["secret_leakage"]
      min_level: "low"
      action: "block"

  threshold_rules:
    - min_score: 60
      action: "block"
    - min_score: 30
      action: "require_approval"

  default_action: "warn"
  min_confidence: 0.7
```

## Supported LLM Backends

| Provider | Model | Preset |
|---|---|---|
| MiMo (Xiaomi) | `mimo-v2.5-pro` | `mimo` (default) |
| OpenAI | `gpt-4o` | `openai` |
| DeepSeek | `deepseek-chat` | `deepseek` |
| Anthropic | `claude-sonnet-4-20250514` | `anthropic` |
| Qwen | `qwen-plus` | `qwen` |
| GLM | `glm-4` | `glm` |
| Kimi | `kimi` | `kimi` |

Set `LLM_MODEL` to a preset name for auto-configuration.

## Project Structure

```
src/mergewall/
  diff/              # Diff parser (unified diff → structured data)
  risk/              # Diff Risk Engine
    guards/          # 6 deterministic risk guards
    llm_agents.py    # LLM-based risk agents
    engine.py        # Risk engine orchestrator
    models.py        # RiskFinding, RiskReport, MergeDecision
  policy/            # Policy Engine (path rules, thresholds)
  enforcement/       # GitHub Checks API client
  audit/             # JSONL audit trail
  memory/            # Per-module risk history
  agents/            # Legacy review agents (from RevHive)
  graph/             # Legacy LangGraph workflow (from RevHive)
  utils/             # Shared utilities (LLM client, dedup, parser)
  main.py            # CLI entry point
tests/               # 128 tests
```

## License

MIT — see [LICENSE](LICENSE).

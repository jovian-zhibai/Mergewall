# Mergewall

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![LangGraph](https://img.shields.io/badge/framework-LangGraph-orange)](https://langchain-ai.github.io/langgraph/)

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
# 1. Install
git clone https://github.com/Jansen003/Mergewall.git
cd Mergewall
pip install -e ".[dev]"

# 2. Run governance on a diff (CLI mode)
mergewall govern --diff HEAD~1

# 3. View audit trail
mergewall audit
```

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

### 5. Audit Trail

Every governance decision is logged to `.mergewall/audit.jsonl`:

```json
{"repo": "org/repo", "pr_number": 42, "merge_decision": "block", "risk_score": 25, "finding_count": 1, "required_approvals": ["security-team"], "timestamp": "2026-05-14T..."}
```

## CLI Commands

```bash
# Run governance analysis (exit code 1 if blocked)
mergewall govern --diff HEAD~1

# Run governance with JSON output
mergewall govern --diff HEAD~1 --format json

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
        run: mergewall govern --diff origin/main
```

Then enable "Require status checks to pass" in branch protection settings.

## Configuration

Create `.mergewall.yml` in your project root:

```yaml
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
  agents/            # Legacy review agents (still available)
  graph/             # LangGraph workflow orchestration
  main.py            # CLI entry point
tests/               # 113 tests
```

## License

MIT — see [LICENSE](LICENSE).

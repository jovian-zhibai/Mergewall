# CodeGuardian

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![LangGraph](https://img.shields.io/badge/framework-LangGraph-orange)](https://langchain-ai.github.io/langgraph/)
[![MiMo](https://img.shields.io/badge/powered_by-MiMo-red)](https://platform.xiaomimimo.com)
[![Agents](https://img.shields.io/badge/agents-10-blue)]()
[![CI](https://github.com/SoulJian03/CodeGuardian/actions/workflows/ci.yml/badge.svg)](https://github.com/SoulJian03/CodeGuardian/actions)

**基于 Multi-Agent 协作的 AI 代码审查与安全扫描系统**

CodeGuardian 部署 10 个专业 AI Agent — 9 个并行审查，1 个综合汇总 — 在代码进入生产环境之前捕获安全漏洞、性能瓶颈、逻辑 Bug 和风格问题。

### 风险评分

每次审查都会输出一个风险评分（0-100），让你一眼判断是否可以合并：

| 分数 | 等级 | 含义 |
|------|------|------|
| 0-20 | ✅ LOW | 可以放心合并 |
| 21-50 | ⚠️ MEDIUM | 建议审查后再合并 |
| 51-80 | 🔴 HIGH | 修复后再合并 |
| 81-100 | 🚨 CRITICAL | 不建议合并 |

示例输出：

```
🚨 Risk Score: CRITICAL (81/100)

1 Critical · 2 High · 4 Medium · 6 Low
```

## 为什么选择 CodeGuardian？

| 痛点 | CodeGuardian 解决方案 |
|---|---|
| 人工 CR 每天耗时 1-2 小时 | 9 个 Agent 并行审查，30 秒内完成 |
| 人工审查容易遗漏 Bug | 每个 Agent 都是领域专家（安全/性能/逻辑...） |
| "LGTM" 文化让审查形同虚设 | 每个 PR 都有详尽、客观的审计报告 |
| 缺少团队级质量可见性 | 趋势分析持续追踪代码健康度 |

## 架构设计

```
┌─────────────┐
│  Coordinator │ ← 汇总结果，解决冲突评级
└──────┬──────┘
       │ 收集 9 个并行 Agent 的结果
       ▼
  Style  Security  Perf  Logic  Repo  Refactor  Fix  Test  Doc
```

**ConversationReviewer** 按需对单个发现进行多轮深度审查——挑战假设、探索替代方案、通过 5 轮对话测试边缘情况。用于团队批处理模式中的严重/高危发现。

### 全部 10 个 Agent

| Agent | 职责 |
|---|---|
| **StyleAgent** | 命名规范、代码格式、注释文档 |
| **SecurityAgent** | SQL 注入、XSS、密钥泄露、弱加密、认证缺陷 |
| **PerformanceAgent** | N+1 查询、内存泄漏、算法复杂度 |
| **LogicAgent** | 边界条件、异常处理、竞态条件、类型安全 |
| **RepoAgent** | 架构审查、跨文件依赖、技术债务 |
| **RefactorAgent** | 设计模式、代码转换、渐进式重构 |
| **FixAgent** | 完整修复代码生成、根因分析、回归风险评估 |
| **TestAgent** | 单元测试、边界用例、安全回归测试 |
| **DocAgent** | API 文档、架构说明、使用示例 |
| **Coordinator** | 去重、优先级排序、冲突解决、报告生成 |

## 快速开始

```bash
# 1. 安装
git clone https://github.com/SoulJian03/CodeGuardian.git
cd CodeGuardian
pip install -e ".[dev]"

# 2. 体验 Demo 模式（无需 API Key！）
python examples/sample_review.py

# 3. 设置 LLM API Key
export LLM_API_KEY=your-api-key

# 4. 立即审查代码
codeguardian review --file src/main.py
codeguardian review --diff HEAD~1
```

CLI 使用不需要 GitHub App。自动 PR 审查请参考 [GitHub App 集成](#github-app-集成)。

## Demo 模式

CodeGuardian 内置完整的 **Demo 模式**，无需 API Key、无需网络、零成本即可运行完整的多 Agent 审查流程。

```bash
python examples/sample_review.py
```

生成与真实 MiMo 调用结构完全一致的审查报告：
- 20+ 条模拟发现，覆盖全部 9 个审查 Agent
- 按严重程度排序（CRITICAL / HIGH / MEDIUM / LOW）
- 支持 Markdown 和 JSON 两种输出格式

## 支持的 LLM 后端

| 服务商 | 模型 | 配置 |
|---|---|---|
| **MiMo (小米)** | `mimo-v2.5-pro` | `LLM_BASE_URL=https://api.xiaomimimo.com/v1` |
| OpenAI | `gpt-4o` | `LLM_BASE_URL=https://api.openai.com/v1` |
| DeepSeek | `deepseek-chat` | `LLM_BASE_URL=https://api.deepseek.com/v1` |
| Qwen (通义) | `qwen-plus` | `LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1` |
| GLM (智谱) | `glm-4` | `LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4` |
| Kimi | `kimi` | `LLM_BASE_URL=https://api.moonshot.cn/v1` |
| **Anthropic** | `claude-sonnet-4-20250514` | `pip install -e ".[anthropic]"`，设置 `ANTHROPIC_API_KEY` |

**快速预设：** 将 `LLM_MODEL` 设为预设名（如 `openai`、`deepseek`、`qwen`），CodeGuardian 自动配置 base URL。显式设置 `LLM_BASE_URL` 优先级更高。

MiMo 是**默认且推荐的后端**。CodeGuardian 针对 MiMo 的 Token 经济性和模型能力进行了优化。

## 支持的语言

CodeGuardian 的 LLM 驱动 Agent 可以审查任何语言的代码。目前已针对以下语言优化：

| 语言 | 扩展名 | 安全模式 | 性能模式 |
|------|--------|---------|---------|
| Python | .py | ✅ 完整 | ✅ 完整 |
| JavaScript/TypeScript | .js .jsx .mjs .ts .tsx | ✅ 完整 | ✅ 完整 |
| Go | .go | ✅ 完整 | ✅ 完整 |
| Rust | .rs | ✅ 完整 | ✅ 完整 |
| Java | .java | ✅ 完整 | ✅ 完整 |
| C/C++ | .c .cpp .h .hpp | ✅ 核心 | ⚠️ 基础 |
| Ruby | .rb | ✅ 核心 | ⚠️ 基础 |
| PHP | .php | ✅ 完整 | ⚠️ 基础 |
| Swift | .swift | ✅ 核心 | ⚠️ 基础 |
| Kotlin | .kt | ✅ 核心 | ⚠️ 基础 |

其他语言通过 LLM 理解支持，但可能缺少专门的检测模式。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `LLM_API_KEY` | **是** | — | LLM 服务商的 API Key |
| `LLM_BASE_URL` | 否 | `https://api.xiaomimimo.com/v1` | LLM API 端点 |
| `LLM_MODEL` | 否 | `mimo-v2.5-pro` | 模型名称 |
| `GITHUB_WEBHOOK_SECRET` | 仅 Server | — | Webhook 签名验证的 HMAC 密钥 |
| `GITHUB_APP_ID` | 仅 Server | — | GitHub App ID，用于获取 installation token |
| `GITHUB_PRIVATE_KEY` | 仅 Server | — | PEM 私钥内容（Railway 部署推荐） |
| `GITHUB_PRIVATE_KEY_PATH` | 仅 Server | `codeguardian-bot.private-key.pem` | PEM 文件路径（本地开发备用） |

## 配置

在项目根目录创建 `.codeguardian.yml`：

```yaml
model: mimo-v2.5-pro

agents:
  style:
    enabled: true
  security:
    enabled: true
    severity_threshold: medium   # 只报告 medium 及以上
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
    enabled: false               # 禁用文档 Agent

ignore:                          # glob 模式 — ** 匹配任意层级子目录
  - "*.min.js"
  - "*.min.css"
  - "vendor/**"
  - "node_modules/**"
  - "migrations/**"
  - "__pycache__/**"
  - ".git/**"
  - ".venv/**"
```

## GitHub App 集成

如需自动 PR 审查，安装 CodeGuardian GitHub App 并配置 Webhook 服务器。命令行使用无需 GitHub App。

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

## Token 消耗估算

CodeGuardian 专为高吞吐 Token 消耗设计——是 MiMo 免费额度或高容量方案的理想工作负载：

| 模式 | Tokens / 次 | 使用场景 |
|---|---|---|
| 单文件 9-Agent 审查 | ~35,000 | 单次 PR 或按需审查 |
| 自动修复生成 | ~50,000 | 审查后自动修 Bug |
| 测试套件生成 | ~40,000 | 补测试覆盖 |
| 多轮深度审查 | ~120,000 | 关键安全发现 |
| 全仓库扫描 | ~1,500,000 | 代码健康审计 |
| 团队每日批处理 | ~10,000,000 | 5+ 仓库持续监控 |

## 项目结构

```
src/codeguardian/
  agents/          # 10 个专业审查 Agent
  graph/           # LangGraph 工作流编排
  utils/           # 工具模块
  team/            # 批量处理引擎
  analysis/        # 历史趋势分析
  demo.py           # Demo 模式（无需 API Key）
  main.py           # CLI 入口
tests/              # 45+ 测试覆盖 agents、workflow、demo
examples/           # 开箱即用的示例
```

## 安全

CodeGuardian 重视自身代码安全：

- **依赖扫描** — CI 中每次推送和 PR 都运行 `pip-audit`，检测依赖中的已知 CVE。
- **静态分析** — `bandit` 扫描源码中的常见安全问题（硬编码密钥、不安全反序列化、注入风险）。
- **Docker 加固** — 容器以非 root 用户（`appuser`）运行。敏感文件（`.env`、`*.pem`、`.git/`）通过 `.dockerignore` 排除。

本地运行安全检查：

```bash
pip install pip-audit bandit
pip-audit
bandit -r src/ -c pyproject.toml
```

## 贡献

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT — 详见 [LICENSE](LICENSE)。


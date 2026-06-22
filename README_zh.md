# Mergewall

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/jovian-zhibai/Mergewall/actions/workflows/ci.yml/badge.svg)](https://github.com/jovian-zhibai/Mergewall/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mergewall)](https://pypi.org/project/mergewall/)

**AI 合并治理运行时 — 阻止高风险 AI 生成代码进入生产环境。**

Mergewall 不是代码审查工具。它是一个治理运行时，位于 AI 编写的代码和生产分支之间。分析每个 PR diff，评估风险，执行策略，必要时阻断合并。

## 为什么选择 Mergewall？

| 痛点 | Mergewall 方案 |
|---|---|
| AI 写 30-60% 代码，没人认真审查 | 确定性风险守卫捕获密钥、认证绕过、危险依赖 |
| 建议性审查工具被忽略 | GitHub Checks API 在风险过高时阻断合并 |
| "LGTM" 文化让 Bug 通过 | 策略引擎按目录强制执行团队规则 |
| 缺少合规审计追踪 | JSONL 审计日志记录每次治理决策 |

## Mergewall + RevHive

Mergewall 负责**强制治理**（阻断高风险合并），[RevHive](https://github.com/jovian-zhibai/RevHive) 提供**建议性审查**（多 Agent 代码质量分析）。两者互补。

## 快速开始

```bash
pip install mergewall
mergewall init          # 生成默认配置
mergewall demo          # 体验治理流程（无需 API Key）
mergewall govern --diff HEAD~1   # 真实治理分析
mergewall audit         # 查看审计日志
```

开发环境：

```bash
git clone https://github.com/jovian-zhibai/Mergewall.git
cd Mergewall
pip install -e ".[dev]"
```

## CLI 命令

```bash
mergewall init                              # 生成 .mergewall.yml
mergewall demo                              # 治理演示（无需 API Key）
mergewall govern --diff HEAD~1              # 治理分析（阻断时退出码为 1）
mergewall govern --diff HEAD~1 --format json    # JSON 输出
mergewall govern --diff HEAD~1 --format sarif   # SARIF 输出（GitHub Code Scanning）
mergewall govern --diff HEAD~1 --output report.md  # 保存报告
mergewall audit                             # 查看审计日志
mergewall review --file src/main.py         # 遗留审查模式
```

## 配置

```bash
mergewall init  # 生成初始 .mergewall.yml
```

详细配置参见 [英文 README](README.md#configuration)。

## 策略模板

| 模板 | 场景 |
|---|---|
| `starter.yml` | 最小化 — 仅阻断 CRITICAL |
| `strict.yml` | 严格 — score>30 审批，>60 阻断 |
| `fintech.yml` | 金融 — 认证变更需 security-team 审批 |
| `monorepo.yml` | 单仓 — 按目录分级 |
| `opensource.yml` | 开源 — 外部贡献者严格审查 |

## 自定义守卫

在 `.mergewall.yml` 中定义基于模式的自定义风险守卫：

```yaml
custom_guards:
  - name: "no-console-log"
    pattern: "console\\.log\\("
    file_pattern: "*.js"
    level: "low"
    message: "合并前移除 console.log"
```

## 项目结构

```
src/mergewall/
  diff/          # Diff 解析器
  risk/          # 风险引擎 + 6 个确定性守卫
    guards/      # 密钥、认证、权限、API、依赖、影响范围守卫
    plugin.py    # 自定义守卫加载器
  policy/        # 策略引擎（路径规则、阈值、校验）
  enforcement/   # GitHub Checks API + PR 评论模板
  audit/         # JSONL 审计日志
  memory/        # 模块级风险历史
  output/        # SARIF 输出（GitHub Code Scanning）
  agents/        # 遗留审查 Agent（来自 RevHive）
  graph/         # 遗留 LangGraph 工作流（来自 RevHive）
  utils/         # 共享工具
  config.py      # 配置加载器
  demo.py        # 治理演示
  main.py        # CLI 入口
tests/           # 128 测试
templates/       # 策略模板 + PR 评论模板
```

## License

MIT — 详见 [LICENSE](LICENSE)。

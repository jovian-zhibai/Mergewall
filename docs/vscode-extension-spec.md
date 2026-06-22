# Mergewall VS Code Extension — Specification

## Overview

The Mergewall VS Code extension brings deterministic governance checks into the editor, giving developers real-time feedback on risk before they commit or push.

**Extension ID:** `mergewall`
**Language:** TypeScript
**Target:** VS Code 1.85+

---

## MVP Features

### 1. Status Bar Indicator
Show the current workspace/file risk level in the status bar:

- 🟢 **Green**: No risks detected
- 🟡 **Yellow**: Warnings (MEDIUM level findings)
- 🔴 **Red**: Blocking issues (CRITICAL/HIGH level findings)

Clicking the indicator runs a full governance scan.

### 2. Command: `Mergewall: Scan Current File`
- Runs the 6 deterministic guards against the active editor content
- Uses `mergewall govern --diff` with a temporary diff of the current file
- No LLM API key required — deterministic path only
- Shows a notification with the risk score and finding count

### 3. Diagnostics Integration
- Findings appear in the **Problems** panel (Ctrl+Shift+M)
- Severity mapping: CRITICAL/HIGH → Error, MEDIUM → Warning, LOW → Info
- Each diagnostic includes the finding title, description, and fix suggestion
- Clicking a diagnostic navigates to the affected line

### 4. Inline Decorations
- Risk indicators displayed in the editor gutter next to affected lines
- Hover tooltip shows the finding details and fix suggestion
- Color coding matches severity: red (critical/high), yellow (medium), green (low)

### 5. Quick Fix (Code Action)
- Lightbulb indicator on lines with fix suggestions
- Clicking shows the `finding.suggestion` text
- Does NOT auto-apply fixes (delegated to RevHive's FixAgent)

---

## Architecture

```
┌─────────────────────────────────────────┐
│            VS Code Extension            │
│  ┌──────────┐  ┌────────────────────┐   │
│  │ Status   │  │  Command Handler   │   │
│  │ Bar Item │  │  (Scan Current)    │   │
│  └──────────┘  └────────┬───────────┘   │
│                         │               │
│              ┌──────────▼───────────┐   │
│              │   Mergewall CLI      │   │
│              │   (child_process)    │   │
│              └──────────┬───────────┘   │
│                         │               │
│              ┌──────────▼───────────┐   │
│              │   JSON Output Parser │   │
│              └──────────┬───────────┘   │
│                         │               │
│  ┌──────────┐  ┌────────▼────────┐      │
│  │Diagnostics│  │   Decorations   │      │
│  │ Provider  │  │   Provider      │      │
│  └──────────┘  └─────────────────┘      │
└─────────────────────────────────────────┘
```

### CLI Integration

The extension spawns the local `mergewall` CLI as a child process:

```typescript
const { stdout } = await exec(
  `mergewall govern --diff HEAD --format json`,
  { cwd: workspaceRoot }
);
const report: RiskReport = JSON.parse(stdout);
```

### Finding → Diagnostic Mapping

```typescript
function findingToDiagnostic(f: RiskFinding): vscode.Diagnostic {
  const range = new vscode.Range(f.evidence.line - 1, 0, f.evidence.line - 1, 999);
  return {
    message: `[${f.category}] ${f.title}: ${f.why_dangerous}`,
    severity: mapLevel(f.level),
    source: 'Mergewall',
    range,
  };
}
```

---

## Not in MVP

- **GitHub integration** — handled by the GitHub App / Actions
- **LLM-based analysis** — deterministic guards only; no API key needed
- **Auto-fix** — only suggestions are shown; RevHive's FixAgent handles auto-fix
- **Multi-file scanning** — scan one file at a time
- **Configuration editor** — users edit `.mergewall.yml` manually

---

## Technical Stack

| Component | Choice |
|---|---|
| Language | TypeScript |
| UI Framework | VS Code Extension API (native) |
| CLI Integration | `child_process.exec` |
| Output Parsing | `JSON.parse` on `--format json` |
| Build | `vsce package` |
| Publishing | VS Code Marketplace |

---

## Development Roadmap

1. **Week 1**: Scaffold extension, implement `exec mergewall` integration
2. **Week 2**: Status bar indicator + "Scan Current File" command
3. **Week 3**: Diagnostics provider + Problems panel integration
4. **Week 4**: Inline decorations + hover tooltips + Quick Fix code actions
5. **Week 5**: Polish, tests, publish to VS Code Marketplace

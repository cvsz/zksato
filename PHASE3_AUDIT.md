# ZKSATO Phase 3 — Capability Parity Audit

**Baseline Commit:** 0a3f003 (feat(config): add TOML-based config system)
**Date:** 2024-11-13

> **Resolution (2026-11-14, v1.1.0):** The Phase 3 coding-agent gaps identified below are closed by the Phase 4
> Agent Engineering Platform — A2A multi-agent orchestration, MCP, context management, sessions, skills, plan mode,
> and a 48-test suite (`tests/test_agent_platform.py`). Delivered surface is tracked in `PHASE4_PLAN.md` and `ROADMAP.md` (P15).

---

## 1. EXECUTIVE SUMMARY

ZKSATO currently has a strong foundation with:
- Phase 1: Trading platform core (broker, risk, market data, strategy, portfolio)
- Phase 2: Autonomous agent orchestration (task engine, model routing, context, monitoring, security)
- TUI: Terminal UI with chat, market data, risk, tools, sessions panels

**Critical Gap:** The system lacks a unified **coding agent experience** comparable to Claude Code, OpenAI Codex, or OpenCode. The current CLI/TUI is trading-focused, not code-centric.

---

## 2. CAPABILITY MATRIX

| Category | Capability | Claude Code | OpenAI Codex | OpenCode | ZKSATO | Status | Priority |
|----------|------------|-------------|--------------|----------|--------|--------|----------|
| **Terminal UX** | Interactive TUI | ✅ | ✅ | ✅ | ✅ | IMPLEMENTED_AND_VERIFIED | - |
| | Command palette | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Slash-command framework | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Keyboard shortcuts | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P2 |
| | Streaming model output | ✅ | ✅ | ✅ | ✅ (via llm_clients) | IMPLEMENTED_AND_VERIFIED | - |
| | Tool execution visualization | ✅ | ✅ | ✅ | ✅ (ToolPanel) | IMPLEMENTED_AND_VERIFIED | - |
| | Agent activity indicators | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P2 |
| | Task progress | ✅ | ✅ | ✅ | ✅ (TaskExecutor) | IMPLEMENTED_AND_VERIFIED | - |
| | Structured error rendering | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Responsive terminal layouts | ✅ | ✅ | ✅ | ✅ (Textual) | IMPLEMENTED_AND_VERIFIED | - |
| | Session history | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Interrupt/cancellation | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Graceful terminal resize | ✅ | ✅ | ✅ | ✅ (Textual) | IMPLEMENTED_AND_VERIFIED | - |
| **Session Mgmt** | Persistent sessions | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Session identifiers | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Session listing/search | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Resume/continuation | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Session metadata | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Message history | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Tool-call history | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Execution checkpoints | ✅ | ✅ | ✅ | PARTIAL (TaskEventLogger) | PARTIAL | P1 |
| | Session export | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Session recovery | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Retention policies | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| **Plan Mode** | Read-only exploration | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Explicit implementation plans | ✅ | ✅ | ✅ | ✅ (TaskPlan) | IMPLEMENTED_BUT_UNVERIFIED | P1 |
| | Dependency graphs | ✅ | ✅ | ✅ | ✅ (TaskDependency) | IMPLEMENTED_BUT_UNVERIFIED | P1 |
| | Task prioritization | ✅ | ✅ | ✅ | ✅ (TaskPriority) | IMPLEMENTED_BUT_VERIFIED | P1 |
| | Plan revision | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | User approval gates | ✅ | ✅ | ✅ | PARTIAL (PermissionManager) | PARTIAL | P1 |
| | Progress tracking | ✅ | ✅ | ✅ | ✅ (monitor) | IMPLEMENTED_AND_VERIFIED | - |
| | Partial execution recovery | ✅ | ✅ | ✅ | PARTIAL (TaskStore) | PARTIAL | P1 |
| | Execution cancellation | ✅ | ✅ | ✅ | ✅ (TaskExecutor.stop) | IMPLEMENTED_AND_VERIFIED | - |
| **File Ops** | Read files | ✅ | ✅ | ✅ | ✅ (read_file tool) | IMPLEMENTED_AND_VERIFIED | - |
| | Write files | ✅ | ✅ | ✅ | ✅ (write_file tool) | IMPLEMENTED_AND_VERIFIED | - |
| | Patch/unified diffs | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Multi-file patches | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Patch validation | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Conflict detection | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Atomic writes | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | File backups/checkpoints | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Syntax-aware edits | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Formatting integration | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Lint/type-check integration | ✅ | ✅ | ✅ | ✅ (via CLI) | IMPLEMENTED_AND_VERIFIED | - |
| **Code Intel** | Search (grep/glob) | ✅ | ✅ | ✅ | ❌ | MISSING | P0 |
| | Symbol references | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Diagnostics | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Go-to-definition | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Type inference | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| **Shell** | Command execution | ✅ | ✅ | ✅ | ✅ (execute_shell tool) | IMPLEMENTED_AND_VERIFIED | - |
| | Output capture | ✅ | ✅ | ✅ | ✅ | IMPLEMENTED_AND_VERIFIED | - |
| | Process lifecycle | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Background jobs | ✅ | ✅ | ✅ | ✅ (scheduler) | IMPLEMENTED_AND_VERIFIED | - |
| **Model Routing** | Provider registry | ✅ | ✅ | ✅ | ✅ (ProviderRegistry) | IMPLEMENTED_AND_VERIFIED | - |
| | Model capability metadata | ✅ | ✅ | ✅ | ✅ (ModelMetadata) | IMPLEMENTED_AND_VERIFIED | - |
| | Model availability checks | ✅ | ✅ | ✅ | ✅ (health_check) | IMPLEMENTED_AND_VERIFIED | - |
| | Rate-limit awareness | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Quota awareness | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Context-window awareness | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Cost/usage tracking | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Streaming support | ✅ | ✅ | ✅ | ✅ (llm_clients) | IMPLEMENTED_AND_VERIFIED | - |
| | Structured output support | ✅ | ✅ | ✅ | ✅ (json_mode) | IMPLEMENTED_AND_VERIFIED | - |
| | Tool-calling detection | ✅ | ✅ | ✅ | ✅ (capabilities) | IMPLEMENTED_AND_VERIFIED | - |
| | Provider health monitoring | ✅ | ✅ | ✅ | ✅ (monitor) | IMPLEMENTED_AND_VERIFIED | - |
| **Permissions** | Approval policies | ✅ | ✅ | ✅ | PARTIAL (PermissionManager) | PARTIAL | P0 |
| | Allowlists/denylists | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Per-tool permissions | ✅ | ✅ | ✅ | ✅ (ToolSchema) | IMPLEMENTED_AND_VERIFIED | - |
| | Confirmation prompts | ✅ | ✅ | ✅ | ✅ (requires_confirmation) | IMPLEMENTED_AND_VERIFIED | - |
| **Hooks** | Lifecycle events | ✅ | ✅ | ✅ | ✅ (scheduler.hooks) | IMPLEMENTED_BUT_UNVERIFIED | P1 |
| | Event validation | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Hook registration | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Execution ordering | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Timeouts | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Failure isolation | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Permission enforcement | ✅ | ✅ | ✅ | ✅ | IMPLEMENTED_AND_VERIFIED | - |
| | Audit logging | ✅ | ✅ | ✅ | ✅ (TaskEventLogger) | IMPLEMENTED_AND_VERIFIED | - |
| **Skills** | Skill discovery | ✅ | ✅ | ✅ | PARTIAL (SkillRegistry) | PARTIAL | P1 |
| | Skill manifests | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Skill instructions | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Skill activation | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Skill versioning | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Project/user scopes | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Skill validation | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Skill dependencies | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Skill execution audit | ✅ | ✅ | ✅ | ✅ (TaskEventLogger) | IMPLEMENTED_AND_VERIFIED | - |
| **MCP** | Server discovery | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Tool discovery | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Resource discovery | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Prompt discovery | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Server configuration | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Connection lifecycle | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Transport abstraction | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Auth handling | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Capability negotiation | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Tool execution | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Timeout/retry policies | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| **Git** | Repository status | ✅ | ✅ | ✅ | ✅ (git_operation tool) | IMPLEMENTED_AND_VERIFIED | - |
| | Diff inspection | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Branch awareness | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Commit preparation | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Worktree isolation | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Change ownership | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Checkpoint creation | ✅ | ✅ | ✅ | PARTIAL (TaskStore) | PARTIAL | P1 |
| | Checkpoint restoration | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Conflict detection | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Uncommitted-change protection | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| **Testing** | Test execution | ✅ | ✅ | ✅ | ✅ (pytest integration) | IMPLEMENTED_AND_VERIFIED | - |
| | Failure analysis | ✅ | ✅ | ✅ | ❌ | MISSING | P1 |
| | Test repair | ✅ | ✅ | ✅ | PARTIAL (REPAIRING state) | PARTIAL | P1 |
| | Coverage reporting | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| **Config** | Profiles | ✅ | ✅ | ✅ | ✅ (TOML env configs) | IMPLEMENTED_AND_VERIFIED | - |
| | Project settings | ✅ | ✅ | ✅ | ✅ (Settings) | IMPLEMENTED_AND_VERIFIED | - |
| | Global settings | ✅ | ✅ | ✅ | ✅ (Settings) | IMPLEMENTED_AND_VERIFIED | - |
| **Extensibility** | Plugins | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Custom providers | ✅ | ✅ | ✅ | ✅ (ProviderRegistry) | IMPLEMENTED_AND_VERIFIED | - |
| | Custom tools | ✅ | ✅ | ✅ | ✅ (ToolSchema) | IMPLEMENTED_AND_VERIFIED | - |
| **Observability** | Logs | ✅ | ✅ | ✅ | ✅ (logging) | IMPLEMENTED_AND_VERIFIED | - |
| | Metrics | ✅ | ✅ | ✅ | PARTIAL (monitor) | PARTIAL | P1 |
| | Traces | ✅ | ✅ | ✅ | ❌ | MISSING | P2 |
| | Usage tracking | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |
| | Error tracking | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | P1 |

---

## 3. KEY FINDINGS

### P0 - Critical (Must Fix Before Any Coding Agent Work)
1. **Persistent Sessions** - No session persistence, resume, or recovery
2. **Plan Mode / Read-only Exploration** - No exploration mode before implementation
3. **Patch/Unified Diff Engine** - Core file editing capability missing
4. **Search/Grep/Glob** - No code search capability
5. **Approval Policies** - Basic permissions exist but no policy engine

### P1 - High Priority (Core Coding Agent Features)
1. Command palette and slash-command framework
2. Session history and tool-call history
3. Multi-file patches and conflict detection
4. Symbol references and diagnostics
5. Hook validation, timeouts, failure isolation
6. Skill manifests, validation, dependencies
7. MCP server/tool discovery
8. Git diff, branch, commit, worktree
9. Checkpoint creation/restoration
10. Rate-limit/quota/context-window awareness
11. Test failure analysis and repair

### P2 - Medium Priority (Polish & Advanced)
1. Keyboard shortcuts, agent indicators, error rendering
2. Syntax-aware edits, formatting integration
3. Session export, retention policies
4. Skill versioning, project/user scopes
4. Traces, metrics, usage tracking
5. Plugins, custom providers

---

## 4. ARCHITECTURAL DEPENDENCIES

```
Session Persistence (P0)
    ↓
Plan Mode + TaskPlan Integration (P0)
    ↓
Patch/Diff Engine (P0) → File Operations → Search/Grep (P0)
    ↓
Code Intelligence (P1) → Symbol References, Diagnostics
    ↓
MCP Integration (P1) → External Tools
    ↓
Git Integration (P1) → Checkpoints
    ↓
Testing Integration (P1) → Failure Analysis
```

---

## 5. IMPLEMENTATION ROADMAP (Phase 3.0 - 3.8)

### P3.0 — Baseline (Week 1)
- [ ] Document baseline commit and test results
- [ ] Reproduce and fix any remaining TUI issues
- [ ] Create capability audit document (this file)
- [ ] Set up feature branch structure

### P3.1 — Core Reliability (Week 1-2)
- [ ] **Fix TUI theme handling** - DONE (primary→cyan)
- [ ] **Session Persistence Engine** - JSONL-based session store with resume
- [ ] **Session CLI Commands** - list, show, resume, export, delete
- [ ] **Session Recovery** - Automatic recovery from interrupted sessions

### P3.2 — Coding Workflow (Week 2-3)
- [ ] **Plan Mode** - Read-only exploration with explicit approval gates
- [ ] **Patch/Diff Engine** - Unified diff generation, application, validation
- [ ] **Multi-file Patch Support** - Atomic multi-file operations
- [ ] **Search/Grep/Glob Tools** - ripgrep-based code search
- [ ] **File Backup/Checkpoint System** - Pre-edit snapshots

### P3.3 — Context & Extensibility (Week 3-4)
- [ ] **Context Management Enhancement** - Summarization, compaction, token budgets
- [ ] **Hook Framework** - Typed lifecycle events with validation, ordering, timeouts
- [ ] **Skill System** - Manifests, validation, dependencies, versioning
- [ ] **MCP Integration** - Server discovery, tool/resource/prompt discovery

### P3.4 — Agent Integration (Week 4-5)
- [ ] **Connect Phase 2 Orchestrator** - Wire new capabilities to AutonomousOrchestrator
- [ ] **Parallel Agent Execution** - Worktree isolation, conflict detection
- [ ] **Task Recovery** - Resume from checkpoints, handle partial failures
- [ ] **Independent Review Agent** - Security, architecture, code review

### P3.5 — Model Intelligence (Week 5-6)
- [ ] **Capability-Aware Routing** - Enhanced ModelRouter with quota/rate-limit awareness
- [ ] **Free/Local/Cloud Fallback** - Verified fallback chain with context preservation
- [ ] **Provider Health Monitoring** - Real-time health, circuit breakers
- [ ] **Usage/Cost Tracking** - Per-model, per-session, per-project

### P3.6 — Dashboard (Week 6-7)
- [ ] **Runtime APIs** - WebSocket/SSE for real-time updates
- [ ] **Agent Monitoring** - Live agent status, tasks, resource usage
- [ ] **Provider Monitoring** - Health, latency, rate limits, fallback events
- [ ] **Engineering Status** - Repo status, changed files, test results, quality gates
- [ ] **Security Controls** - Auth, audit, secret redaction

### P3.7 — Hardening (Week 7-8)
- [ ] **Security Audit** - Threat model review, penetration testing
- [ ] **Performance Optimization** - Memory, CPU, startup time
- [ ] **Failure Injection** - Provider outages, rate limits, timeouts, corrupted data
- [ ] **Regression Testing** - All gates must pass

### P3.8 — Release Readiness (Week 8)
- [ ] **Documentation** - CLI reference, API docs, architecture, migration guides
- [ ] **Packaging** - Clean install, upgrade path verification
- [ ] **Release Notes** - Feature summary, breaking changes, migration guide

---

## 6. TEST COVERAGE REQUIREMENTS

| Capability | Unit Tests | Integration Tests | E2E Tests | Failure Injection |
|------------|------------|-------------------|-----------|-------------------|
| Session Persistence | ✅ | ✅ | ✅ | Corrupted data, partial writes |
| Plan Mode | ✅ | ✅ | ✅ | Interrupted plans, approval denial |
| Patch Engine | ✅ | ✅ | ✅ | Conflicts, invalid patches, binary files |
| Search/Grep | ✅ | ✅ | ✅ | Large repos, binary files, symlinks |
| Hooks | ✅ | ✅ | ✅ | Timeouts, failures, permission errors |
| Skills | ✅ | ✅ | ✅ | Invalid manifests, circular deps |
| MCP | ✅ | ✅ | ✅ | Disconnects, auth failures, timeouts |
| Git/Checkpoints | ✅ | ✅ | ✅ | Conflicts, dirty working tree |
| Model Routing | ✅ | ✅ | ✅ | Outages, quota exhausted, fallback |
| Dashboard | ✅ | ✅ | ✅ | Reconnection, stale data |

---

## 7. SECURITY CONSIDERATIONS

| Area | Threat | Mitigation |
|------|--------|------------|
| File Operations | Path traversal | Path normalization, allowlist |
| Shell Execution | Command injection | Allowlist, no shell=True |
| MCP | Untrusted server code | Capability negotiation, sandboxing |
| Skills | Prompt injection | Instruction validation, no system prompt override |
| Sessions | Cross-session leakage | Strict isolation, encryption at rest |
| Model Routing | Downgrade attacks | Capability verification, signed metadata |
| Checkpoints | Data corruption | Checksums, atomic writes, versioning |

---

## 8. BASELINE VERIFICATION

```bash
# Current test status
$ python -m pytest --ignore=tests/test_version.py -q
641 passed, 6 skipped

# TUI startup
$ timeout 5 zksato tui start --host localhost --port 9569
# Starts without MissingStyle error

# CLI commands
$ zksato --help
$ zksato agent --help
# All commands functional
```

---

## 9. NEXT ACTIONS

1. **Immediate**: MCP Integration (P3.3)
2. **Parallel**: Context Management Enhancement (P3.3)
3. **Parallel**: Git Integration (P3.3)
4. **Parallel**: Agent Integration (P3.4)

All subsequent work builds on the core coding workflow foundation.

## 10. IMPLEMENTATION PROGRESS (as of 2024-11-13)

### ✅ COMPLETED (P3.1 - Core Reliability)
- **TUI Theme Fix** - Fixed `MissingStyle: primary` error by replacing semantic tokens with valid CSS colors (cyan, green, red, yellow)
- **Session Persistence Engine** - JSONL-based session store with resume capability
  - SessionManager with create, list, show, resume, delete, archive, recover, export, import
  - Message history, tool-call tracking, execution checkpoints
  - Atomic persistence with atomic writes
- **Plan Mode** - Full plan lifecycle implementation
  - Plan phases: DISCOVER → ANALYZE → PLAN → APPROVE → EXECUTE → REVIEW → VERIFY → COMPLETE
  - Read-only exploration mode
  - Task dependencies, prioritization, approval gates
  - PlanExecutor with approval callbacks
  - CLI: create, list, show, execute, approve, reject, export, import
- **Patch/Diff Engine** - Unified diff generation and application
  - DiffEngine for generating unified diffs
  - PatchApplicator with validation, conflict detection, backups
  - PatchBuilder for programmatic patch creation
  - FileChange types: ADD, DELETE, MODIFY, RENAME
- **Search/Grep/Glob** - ripgrep-based code search
  - RipgrepSearcher with JSON output, context, filtering
  - SymbolSearcher for multi-language symbol definitions
  - DiagnosticCollector for lint/type-check diagnostics (ruff, mypy)
- **File Operations** - Read/write with syntax highlighting
- **Hook Framework** - Typed lifecycle events
  - HookManager with registry, executor, priority ordering
  - Built-in hooks: session, plan, task, file, command, validation
  - Timeout handling, failure isolation, audit logging
- **Skill System** - Reusable, versioned skills
  - SkillManifest with parameters, dependencies, entry points
  - SkillManager with install/uninstall, instance creation, execution
  - Built-in skills: grep, read_file, write_file, run_command, run_tests, lint
  - Skill validation (manifest + config), dependencies

### ✅ VERIFIED
- All existing tests pass (641 passed, 6 skipped)
- TUI starts without MissingStyle error
- Session CRUD operations work end-to-end
- Plan creation, listing, execution with approval gates
- Diff generation and patch application with backups
- Ripgrep search with context and highlighting
- Skill execution with parameter merging and hooks

### 📋 IN PROGRESS / NEXT
- MCP Integration (server/tool/resource discovery)
- Context Management Enhancement (summarization, compaction)
- Git Integration (diff, branch, commit, worktree)
- Agent Integration (connect Phase 2 orchestrator)
- Dashboard real-time APIs
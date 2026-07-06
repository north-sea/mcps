# Implementation Plan: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

---

## Summary

本 feature 先做对账和契约边界固化，不直接新增 runtime 代码、DB migration、note skill 删除或 live 写入。唯一合理方向是以现有 `agents-capability-reconciliation` 为上游证据，重新核对 `agents/apps/novel-agent`、`agents/specs/novel-agent-*` 与 `mcps/packages/hermes-db` 的 novel tools，把小说能力分为 runtime、durable contract、Library/Wiki、Memory 和 backlog。

本阶段产出文档型契约资产：

- `capability-reconciliation.md`: novel specs 与 note novel skills 的 current-state 对账。
- `owner-table.md`: runtime / MCP / Library / Memory owner 边界。
- `contract-gap-register.md`: hermes-db/MCP gaps 与 agents runtime gaps 分开列出。
- `replacement-routes.md`: 旧 note novel skill 的薄入口替代路线和删除门禁。

## Current Evidence

| Source | Evidence | Interpretation |
|---|---|---|
| `mcps/specs/agents-capability-reconciliation/capability-reconciliation.md` | novel rows classify analyzer / novelist verified, memory/workflow/trend/capture partial, rules not-applicable to runtime | Novel note skills 已有初始 owner 和 deletion gate，但尚未形成 novel-specific contract table |
| `agents/specs/agents-roadmap/roadmap.md` | current feature is `novel-agent-retrospective-handoff` | agents 侧当前未完成项是 retrospective/handoff Phase 7-9 |
| `agents/specs/novel-agent-retrospective-handoff/tasks.md` | T029-T041 unchecked | CLI、fixture、integration、docs 仍是 active runtime work |
| `mcps/packages/hermes-db/src/hermes_db_mcp/tools/novel_*.py` | books/chapters/analysis/style/planning/report tools exist | 基础 novel durable state 已存在 |
| `agents/packages/adapters/src/mcp/novel-retrospective-*.ts` | agents expects novel retrospective MCP tools | mcps/hermes-db 尚未提供同名 server tools，属于 contract gap |

## Architecture Decision

### ADR-001: Reconciliation First, No Runtime Implementation

- **Context**: spec 明确要求先解决 agents novel specs 状态矛盾，再添加实现。
- **Options**:
  - A: 直接实现 hermes-db novel retrospective tables/tools。
  - B: 先输出对账、owner、gap 和 deletion gates。
  - C: 把小说 prompt/runtime 下沉 MCP。
- **Decision**: 选择 B。
- **Cost**: 本 feature 不会立即消除 runtime 缺口，但会避免重复建设或把写作逻辑放错层。

### ADR-002: MCP Owns Durable State Only

- **Context**: 小说写作生成、审稿、文风注入、模型选择需要快速切模型和人工介入。
- **Decision**: `mcps/hermes-db` 只负责 book/chapter/analysis/style/planning/retrospective state 的 CRUD、query、health 和 schema drift 检查；prompt、model routing、LLM 生成、人审交互留在 agents/Hermes/Codex runtime。
- **Cost**: 旧 note skills 不能直接删除，必须等薄入口和 smoke evidence。

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `agents-capability-reconciliation` | 44-row capability table | `novel-runtime-contracts/capability-reconciliation.md` | Novel rows are copied, narrowed, and given novel-specific gates |
| `agents/specs/novel-agent-*` | tasks/acceptance/roadmap status | current-state table | accepted-but-unchecked contradictions are classified instead of treated as done |
| `mcps/packages/hermes-db` | existing novel tool list | `contract-gap-register.md` | durable contracts and missing retrospective contracts are separated |
| `knowledge-library-ingestion-plan` | Library metadata/deletion policy | `owner-table.md`, `replacement-routes.md` | rules/source/sample materials are routed to Library, not Memory |

**Orphan artifact policy**: No deletion or archive artifact is considered valid until `replacement-routes.md` has a target path and evidence gate for that note skill.

## Scope Boundaries

| Layer | Owns | Does Not Own |
|---|---|---|
| agents / Hermes / Codex | novel analysis, planning, writing, retrospective orchestration, human review, model selection | DB migrations and stable shared MCP contract truth |
| mcps / hermes-db | novel durable state, MCP tools, schema health, idempotent writes, read/query APIs | prompts, creative generation, model routing, note skill execution logic |
| Library / Wiki | platform rules, source materials, trend samples, writing references | runtime state, private decisions |
| Memory | compact decisions, procedures, migration status | raw novels, long samples, source corpora |
| note skills | thin route docs only after replacement evidence | active registry for full workflows |

## Quality Attribute Targets

| Attribute | Target | Verification |
|---|---|---|
| correctness | every novel capability has one primary owner and any secondary contract owner | owner table row count and no empty owner fields |
| non-regression | accepted specs with unchecked tasks are not silently reclassified as done | contradiction table |
| safety | no note deletion, no live novel content writes, no publishing | verify evidence side-effect check |
| operability | next feature recommendation is actionable and mapped to active roadmaps | roadmap update and acceptance |

## Verification Strategy

1. Markdown/table checks for required rows and empty critical columns.
2. Code/spec spot checks:
   - agents active feature and unchecked tasks.
   - mcps novel tool modules and missing retrospective server-side tools.
   - Library/Memory route boundaries.
3. SDD closeout only after `verify-evidence.md` and `acceptance.md` record PASS/PARTIAL gates.

## Deferred Work

- Implement hermes-db novel retrospective tables/tools after the contract gap is explicitly selected as a feature.
- Implement agents `novel-agent-retrospective-handoff` CLI/integration/docs in agents repo.
- Create Library importer/smoke for platform rules and trend/source materials.
- Delete/archive note skills only in `note-thin-shell-and-archive`.


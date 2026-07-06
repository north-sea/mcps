# Implementation Plan: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/knowledge-memory-architecture/spec.md`

---

## Summary

推荐继续使用 nmem，但把它从“全端统一知识主库”降级为“agent memory runtime”。历史 NAS nmem 数据已迁到本机 NowledgeGraph，本机是当前主库；NAS 数据目录保留为旧副本/回滚源。NAS nmem 如恢复运行，应作为 Hermes-only runtime，不再给本机 Codex/Claude Code 使用 remote write path；长期知识主库改由 Library/Markdown/Git 承担。

---

## Architecture Overview

```text
                 write runtime memory
Hermes on NAS  ------------------------>  NAS nmem
     |                                      |
     | degraded write fallback              | scheduled export
     v                                      v
fallback queue/log                  backup artifact

Codex / Claude Code on Mac  ----X---->  NAS nmem remote write
       |                                  ^
       | read local files / specs         |
       v                                  |
mcps specs + Markdown/Library/Git  <------ manual import/export only

Karakeep / source inbox  ----------->  Library/Markdown/Git
```

核心边界：

- 本机 NowledgeGraph 是当前 nmem 主数据副本；用户重启后，本机 nmem 已恢复到 v0.10.6、database connected。仍不应让本机 Codex/Claude Code 写 NAS remote path。
- NAS nmem 数据目录是迁移后的旧副本/回滚源，不能直接清理；如重新开启，应先备份和只读盘点。
- Hermes 可以使用恢复后的 NAS nmem 作为运行时 memory。
- Codex/Claude Code 不指向 NAS nmem 的 remote write/MCP write path。
- 长期资料主库不是 nmem，而是 Library/Markdown/Git。
- nmem 与长期资料之间只通过 export/import、摘要或显式同步任务连接，不做双主自动同步。

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| Hermes runtime | memory add/update request | NAS nmem | Hermes-only endpoint smoke；写失败降级不阻塞 |
| NAS nmem | scheduled `nmem export` artifact | backup storage / optional Mac import | export 文件存在、校验记录、import mode 明确 |
| NAS domain export job | domain export archive + preview report | local nmem import gate | mapping 存在、preview 无阻塞、高风险时停止 |
| NAS-to-local import job | merge/skip import result | local matching space | import audit 记录、count/dedupe 结果、无 overwrite |
| Codex/Claude Code | specs、acceptance、roadmap、Markdown notes | Library/Markdown/Git | 文件落盘、git diff、后续 Library ingestion |
| Karakeep/source inbox | source bookmark / clipped material | Library/Markdown/Git ingestion | inbox entry 被转换为 source artifact |
| nmem search/read | decision/procedure summary | Hermes / human operator | 只读查询成功；不要求本机写入 |
| fallback queue/log | failed memory write summary | operator or sync job | queue 文件被人工或任务处理，避免重复写 |

**孤儿 artifact 处理**: fallback queue/log 若没有消费任务，会变成新的垃圾箱；tasks 阶段必须为它定义处理门禁，或明确 MVP 不启用 queue。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 一致性 | 不出现 Mac/NAS 双主写入 | 只有 Hermes 可写 NAS nmem；本机不配置 NAS write endpoint | 配置审查、roadmap/spec 证据 |
| 可用性 | memory 写失败不阻塞 Hermes 主流程 | 写入加超时、失败降级为 no-memory 或 queue/log | smoke/failure-mode checklist |
| 可恢复性 | 每次启用/迁移前有备份 | 使用 `nmem export` 或卷级备份 | export artifact 和恢复说明 |
| 安全性 | 文档不含 token/API key/cookie | evidence 脱敏，命令输出不原样保存敏感值 | `rg` 扫描敏感模式 |
| 可演进性 | 可试点替代工具但不强迁移 | Mem0/Zep/Graphiti 作为后续试点，不影响当前主链 | 替代工具门禁表 |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001: 继续 nmem 但降级职责 | NAS 数据已迁到本机；NAS remote 写超时；本机 nmem degraded；已有 nmem 数据和 CLI | 继续 nmem / 换 Mem0 / 换 Zep / 只用 Markdown | 继续 nmem 做 Hermes memory runtime，长期资料进 Library/Markdown/Git；NAS 旧副本先保留 | 仍需维护 nmem，但避免大迁移 | local evidence |
| ADR-002: NAS nmem Hermes-only | 本机 Codex/Claude Code 不应被 remote 写超时拖住 | 全端共享 / Hermes-only / 完全停用 | Hermes-only | 本机无法直接用 NAS memory 写入 | user decision |
| ADR-003: 禁止双主同步 | Mac/NAS 双写会产生冲突和重复 | 双主自动同步 / 单写源 + export/import | 单写源 + export/import | 手动或定时同步复杂度增加 | local evidence |
| ADR-004: 替代工具只做试点门禁 | 换工具不能解决同步本质问题 | 立即迁移 / 暂不评估 / 建门禁 | 建门禁，未来小规模试点 | 短期没有新工具红利 | UNVERIFIED |

---

## Key Design Decisions

### Decision 1: nmem 是 runtime memory，不是长期知识主库

- **背景**: nmem 适合 agent 检索短中期决策、流程、工作记忆；但 remote 写超时和本机 degraded 说明不能把它当唯一真相。
- **选项**:
  - A: nmem 继续当唯一主库。简单，但写入超时会放大风险。
  - B: nmem 做 runtime memory，长期资料进 Library/Markdown/Git。边界更清楚，数据更可恢复。
- **结论**: 选择 B。
- **影响**: `knowledge-library-ingestion-plan` 需要接收本 feature 的分类表和同步边界。
- **来源**: local evidence。

### Decision 2: NAS nmem 只给 Hermes 使用

- **背景**: NAS nmem 曾遇到 remote API/MCP 写超时；用户明确提出“不再给本机 Codex/Claude Code 使用，相当于指给 Hermes 使用”。
- **选项**:
  - A: 重新开放给所有 agent。
  - B: 只给 Hermes。
  - C: 完全停用。
- **结论**: 选择 B。
- **影响**: 本机 Codex/Claude Code 的知识沉淀应落文件/Library，不能依赖 NAS Mem 写入。
- **来源**: user decision。

### Decision 3: 同步采用 export/import，不做自动双主

- **背景**: 同步问题比工具选择更关键。
- **选项**:
  - A: NAS/Mac 双主自动同步。
  - B: NAS 定时 export，本机只手动 import 或只读归档。
  - C: 不同步。
- **结论**: 选择 B。
- **影响**: tasks 阶段需要定义 export 周期、目录、导入模式和冲突处理。
- **来源**: local evidence。

### Decision 4: 替代工具先作为评估对象

- **背景**: Mem0/OpenMemory、Zep/Graphiti、Obsidian/Markdown/Git、Karakeep 解决的问题不同。
- **选项**:
  - A: 立即替换 nmem。
  - B: 保留 nmem，建立替代工具试点门禁。
- **结论**: 选择 B。
- **影响**: 本 feature 不迁移数据，只输出评估门禁；后续若 nmem 写路径仍不可用，再启动替代工具 POC。
- **来源**: UNVERIFIED；后续如进入 POC 需查官方文档。

---

## Module Design

### Module: Memory Routing Policy

**职责**: 定义哪些 client 能读写哪个 memory endpoint。

**关键行为**:

```text
Hermes:
  read/write NAS nmem
  write timeout -> no-memory or fallback queue/log

Codex/Claude Code:
  do not write NAS nmem
  use specs/Markdown/Library for durable context
  optional read-only local evidence only
```

### Module: Sync And Backup Policy

**职责**: 定义 nmem export/import 和长期资料落盘。

**关键行为**:

```text
NAS nmem:
  scheduled export -> backup directory
  no automatic merge into Mac writable nmem

Mac:
  optional manual import from export
  prefer Markdown/Library/Git for source-of-truth knowledge
```

### Module: One-Way Domain Sync

**职责**: 将 NAS nmem domain space 的增量以 dry-run-first 的方式同步到本机 matching space。

**关键行为**:

```text
sync-domain --domain selfmedia --dry-run
  -> resolve NAS space and local space from mapping
  -> export NAS data to archive
  -> generate preview and dedupe report
  -> stop before local import

sync-domain --domain selfmedia --confirm
  -> require previous preview
  -> import with merge/skip
  -> write audit record
```

**注意事项**:

- MVP 可以先实现脚本/文档流程，不启用 cron。
- import mode 默认 `merge` 或 `skip`。
- `overwrite` 不出现在自动流程里。
- mapping 缺失时只允许 preview inventory，不允许 import。

### Module: Fallback Policy

**职责**: memory 写失败时不阻塞主流程。

**关键行为**:

```text
if memory write timeout:
  do not retry blindly
  search/show if side effect may have happened
  fallback to queue/log if enabled
  continue Hermes workflow without memory
```

### Module: Tool Evaluation Gate

**职责**: 为后续替代工具 POC 提供统一门禁。

**候选定位**:

- nmem: Hermes runtime memory。
- Obsidian/Markdown/Git: 长期人读资料和 source of truth。
- Karakeep: 来源 inbox/bookmark。
- Mem0/OpenMemory: 后续 agent memory POC 候选。
- Zep/Graphiti: 后续知识图谱型 POC 候选。

---

## Data Model

不新增应用数据库 schema，但需要定义策略实体。详细数据模型可在 tasks 阶段按需补 `data-model.md`。

核心实体：

- `MemoryEndpoint`: name、owner、mode、read_allowed、write_allowed、timeout_policy。
- `SyncArtifact`: source、path、created_at、format、import_mode、checksum。
- `KnowledgeClass`: category、source_of_truth、runtime_index、sync_method、retention。
- `FallbackRecord`: summary、source_agent、failed_operation、dedupe_key、status。
- `SpaceMapping`: domain、nas_space、local_space、import_mode、auto_import_allowed。
- `SyncRun`: run_id、domain、export_path、preview_path、import_mode、status、counts、errors。

---

## Project Structure

```text
specs/knowledge-memory-architecture/
  spec.md
  plan.md
  tasks.md              # 后续生成
  data-model.md         # 如 tasks 需要，后续生成
  sync-implementation.md # 单向同步实现方案，后续生成
  acceptance.md         # closeout 生成
```

---

## Risks and Tradeoffs

- NAS nmem 如果只给 Hermes，会降低本机跨工具记忆的一致体验，但能显著降低写超时影响面。
- export/import 不是实时同步；适合备份和人工恢复，不适合多端实时协同。
- 继续使用 nmem 会保留既有问题的维护成本；但立刻换工具会引入更高迁移和同步风险。
- 本机 nmem 当前 degraded，不能作为本 feature 的可靠写路径证据。
- fallback queue/log 若没有清理流程，会积累陈旧摘要。
- 单向同步若没有 preview gate，可能把 NAS runtime 噪音导入本机主库。
- 官方 export/import 的粒度和 space-scoped 行为需要以本机 CLI 实测为准。

---

## Evolution Path

- **MVP**: 定义策略，不重启 NAS，不迁移数据；只输出 plan/tasks/验收门禁。
- **成长期**: 恢复 NAS nmem Hermes-only，增加定时 export 和写失败降级。
- **成熟期**: 若 nmem 仍无法稳定支撑 Hermes，按门禁试点 Mem0/OpenMemory 或 Zep/Graphiti；长期资料仍保持 Library/Markdown/Git 可导出。

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。MVP 先做边界和门禁，不立即引入新知识库。
- 是否引用了外部模式但没有适配检查：否。替代工具只列为试点候选，不作为当前实现依赖。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：是，fallback queue/log 是新增候选状态；tasks 必须决定是否启用和如何清理。

---

## Verification Strategy

- 文档一致性：`specs/.active`、roadmap current、feature table 均指向 `knowledge-memory-architecture`。
- 配置审查：确认本机 Codex/Claude Code 不被要求使用 NAS nmem remote write path。
- 安全扫描：`rg` 检查新文档不包含 token/API key/cookie/bearer。
- 状态证据：记录本机 `nmem status` degraded/database disconnected 为现状，不把本机写入作为验收前提。
- 同步策略验收：tasks 中必须覆盖 export/import、备份目录、导入模式、冲突/重复处理。
- 单向同步验收：必须有 mapping、dry-run preview、merge/skip import gate、audit record，且不启用 overwrite。
- 降级策略验收：tasks 中必须覆盖 write timeout 后不阻塞、不盲目重试。

---

## Stage Readiness

- 是否需要 `data-model.md`：需要。虽然不改应用 DB，但同步策略、endpoint 权限和 fallback record 需要结构化定义。
- 下一步建议：`tasks`，同时生成 `data-model.md`。
- 阻塞项（如有）：无；NAS endpoint 具体地址可在 implement 前确认，不阻塞任务拆解。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 当前文件 |
| data-model.md | 需要 | 定义 MemoryEndpoint、SyncArtifact、KnowledgeClass、FallbackRecord |
| tasks.md | 后续阶段生成 | 拆成策略文档、配置审查、同步门禁、降级门禁 |
| sync-implementation.md | 需要 | 规划单向同步脚本、mapping、dry-run、audit |
| acceptance.md | 后续阶段生成 | 记录三维 verdict 和 roadmap 回写 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| nmem 当前本机状态 | local command | 初始 `rtk nmem status` -> v0.9.27, local, degraded, database disconnected；用户重启后 -> v0.10.6, local, ok, database connected |
| nmem 数据迁移状态 | local command | `/Users/yqg/Library/Application Support/NowledgeGraph` exists and is 888M; backups exist; NAS data is 850M |
| NAS nmem 历史超时 | local skill notes | `/Users/yqg/.agents/skills/nmem-cli/SKILL.md` 故障排查记录 |
| Hermes-only NAS Mem | user decision | 本轮用户明确约束 |
| 替代工具评估 | UNVERIFIED | 后续 POC 前需查官方文档 |
| Mem 多设备同步 | https://mem.nowledge.co/zh/docs/sync | 官方同步模型是一台常开 Mem，多端连接同一个后端；不是多主同步 |
| Mem Spaces | https://mem.nowledge.co/zh/docs/spaces | shared context 只影响检索范围，不移动或合并记录；CLI/API 支持 space |
| Data Transfer | https://mem.nowledge.co/zh/docs/data-portability | export/import 用于备份、迁移；import 支持 merge/skip/overwrite |
| CLI remote/space | https://mem.nowledge.co/zh/docs/cli | `--api-url`、`NMEM_API_URL`、`--space` 可用于远程和 space-scoped 命令 |

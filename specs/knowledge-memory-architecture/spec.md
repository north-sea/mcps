# Feature Specification: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture`  
**Created**: 2026-07-01  
**Status**: Ready for Execute-Plan  
**Input**: 用户描述: "mem 之前虽然是在 nas 上部署了,但是总是遇到保存超时的问题,所以现在 nas 上的镜像已经关了,考虑再打开但不再给本机的 codex/claude code 使用(相当于指给 hermes 使用),评估一下,继续使用 nmem 呢还是换个其他的知识库工具?但要注意数据同步的问题"

> 写入本文件后，应同步更新 `specs/.active` 指向 `knowledge-memory-architecture`，并更新 `specs/note-skill-migration-roadmap/roadmap.md` 的 current feature。

---

## Feature Traits *(LM 自动检测，用户可 override)*

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 涉及 NAS Mem、Hermes、Codex/Claude Code、本机资料库、备份/同步/导入导出等多阶段链路。 |
| `external-side-effects` | ✅ | 会影响 NAS Docker 服务启停、agent memory 写入路径、备份导出、可能的导入/同步策略。 |
| `artifact-handoff` | ✅ | nmem export、Library/Markdown/Git 资料、Hermes memory 摘要和 roadmap 删除门禁之间存在产物交接。 |
| `user-visible-output` | ✅ | 用户会看到本机 Codex/Claude Code 是否可用、Hermes 是否可记忆、知识资料是否可追溯。 |
| `prior-closure-failure` | ✅ | 已有 NAS remote API/MCP 写路径超时、MCP 写入可能落库但不返回、双主风险等历史问题。 |
| `bugfix-loop-breaker` | ❌ | 本 feature 是架构边界和同步策略，不是修复单个 root cause；NAS 超时排障可进入后续实现任务。 |

**结论**: 本 feature 启用 Producer-Consumer Matrix、Evidence Gate、Workflow Replay 和三维 Verdict；closeout 需要 `acceptance.md`。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 明确知识主库与 memory 职责 (Priority: P1)

作为 note skill 迁移负责人，我希望明确 nmem、Library/Markdown/Git、NAS Hermes memory、本机 Codex/Claude Code 的职责边界，以便不因为换工具或重新开 NAS Mem 而造成资料丢失、双主写入或 agent 阻塞。

**Why this priority**: 这是后续 `knowledge-library-ingestion-plan` 和 note skill 删除门禁的前置架构决策。

**Acceptance Scenarios**:

1. **单写源原则**
   **Given** NAS nmem 曾经因为 remote 写路径超时而停用  
   **When** 重新定义 memory 架构  
   **Then** 必须明确哪一端允许写入、哪一端只读或禁用，且不得出现 Mac nmem 和 NAS nmem 双主写入

2. **职责分层**
   **Given** note skill 迁移需要处理长期资料、决策、来源材料和 agent 工作记忆  
   **When** 选择继续 nmem 或替代工具  
   **Then** 必须把长期资料主库、agent memory、来源 inbox、备份归档分开定义

**Edge Cases**:

- **US1-3** 若本机 nmem 状态为 degraded 或 database disconnected，本机 Codex/Claude Code 不应依赖它作为必须成功的写路径。
- **US1-4** 若 NAS nmem 重新开启，只能先作为 Hermes 专用 memory，不自动暴露给本机 Codex/Claude Code。
- **US1-5** 若后续试点 Mem0/Zep/Graphiti，不得绕过 export/import 和去重策略。

### User Story 2 - NAS nmem 可安全恢复为 Hermes 专用 (Priority: P1)

作为 Hermes 运维者，我希望 NAS nmem 可以在不影响本机开发工具的情况下恢复运行，让 Hermes 使用 remote memory，同时保留可回滚、可备份、可观测的边界。

**Why this priority**: Hermes 可能仍需要共享 memory，但本机 Codex/Claude Code 不应再被 NAS 写超时拖住。

**Acceptance Scenarios**:

1. **Hermes-only 路由**
   **Given** NAS nmem 容器被重新启动  
   **When** 配置 agent memory endpoint  
   **Then** 只有 Hermes 使用 NAS endpoint；本机 Codex/Claude Code 配置不指向 NAS Mem remote API/MCP

2. **写入超时保护**
   **Given** NAS remote API/MCP 写路径历史上出现超时  
   **When** 设计恢复策略  
   **Then** 必须有只读/禁写/超时降级/不重试重复写的规则，并记录如何确认写入副作用是否已发生

3. **备份与恢复**
   **Given** NAS nmem 保存 Hermes 运行记忆  
   **When** 执行日常运维  
   **Then** 必须有定时 export 或等价备份路径，并明确 Mac/本地资料库是否导入、何时导入、如何避免覆盖

**Edge Cases**:

- **US2-4** 如果 NAS nmem 写入仍然超时，Hermes 应降级为无 memory 或只写本地日志/Markdown queue，而不是阻塞主流程。
- **US2-5** 如果 MCP 写工具超时但服务端可能已落库，应先 search/show 确认，不得盲目重复写。
- **US2-6** 任何文档或日志不得保存 token、API key、cookie 或真实 bearer。

### User Story 3 - 为后续 Library ingestion 提供可执行前置条件 (Priority: P2)

作为后续 `knowledge-library-ingestion-plan` 的实现者，我希望 memory 架构 feature 输出明确的资料分类和同步规则，以便 Library ingestion 不再和 nmem 选型混在一起。

**Why this priority**: 来源材料、平台规则、参考文章应进 Library/Markdown/Git，而不是把 nmem 当万能资料库。

**Acceptance Scenarios**:

1. **资料分类表**
   **Given** note skill 迁移中存在来源材料、长期决策、agent 工作记忆、网页收藏和运行日志  
   **When** 本 feature 完成  
   **Then** 每类资料都有目标系统、写入端、同步方式、保留策略和删除门禁影响

2. **后续 feature 边界**
   **Given** `knowledge-library-ingestion-plan` 是下一阶段候选  
   **When** 本 feature 进入 closeout  
   **Then** roadmap 应说明 Library ingestion 的启动条件，且不要求本 feature 完成实际批量导入

**Edge Cases**:

- **US3-3** Karakeep 只作为来源 inbox / bookmark，不作为 agent memory 主库。
- **US3-4** Obsidian/Markdown/Git 可作为人读长期资料主库，但不替代 agent memory 检索 API。
- **US3-5** 如果选择保留 nmem，也要记录替代工具试点门禁，避免未来再次凭感觉迁移。

### User Story 4 - NAS domain space 单向同步可执行 (Priority: P1)

作为 Hermes/NAS 运维者，我希望把 Hermes 写入 NAS nmem domain space 的增量安全同步回本机主库，以便保留 domain memory，同时避免 NAS/Mac 双主同步和覆盖风险。

**Why this priority**: 如果 Hermes 后续实际写 NAS domain spaces，而没有同步实现，本机主库会逐渐落后；如果用双向同步或 overwrite，又会破坏数据一致性。

**Acceptance Scenarios**:

1. **只做 NAS 到本机的单向同步**
   **Given** Hermes 在 NAS nmem 的 WeChat/Novel/XHS/domain space 写入了新 memory  
   **When** 执行同步流程  
   **Then** 系统只从 NAS 导出并导入到本机 matching space，不从本机自动写回 NAS

2. **导入前必须有 mapping 和备份**
   **Given** NAS 与本机的 space 名称或 ID 可能不同  
   **When** 执行导入  
   **Then** 必须先有 NAS-to-local space mapping、NAS raw export archive、本机当前状态备份或可回滚记录

3. **默认 merge/skip，不 overwrite**
   **Given** 本机 matching space 已存在历史 memory  
   **When** 导入 NAS delta  
   **Then** 默认使用 merge 或 skip；overwrite 只能人工确认且不作为自动任务默认

**Edge Cases**:

- **US4-4** 如果 NAS export 失败，同步任务应失败并保留错误记录，不修改本机数据。
- **US4-5** 如果 mapping 缺失，同步任务只生成 preview，不执行 import。
- **US4-6** 如果发现高重复率或冲突，任务停止在 review 阶段，不自动覆盖。
- **US4-7** 如果记录包含敏感信息，同步任务不得写入 docs/evidence，应输出脱敏摘要或拒绝导入。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 必须定义 nmem、Library/Markdown/Git、Karakeep、Hermes、Codex/Claude Code 在知识链路中的职责边界。
- **FR-002**: 必须明确 NAS nmem 重新开启后的访问范围：Hermes 可用，本机 Codex/Claude Code 不使用 NAS remote write path。
- **FR-003**: 必须定义单写源策略，禁止 Mac 本地 nmem 与 NAS nmem 双主写入。
- **FR-004**: 必须定义数据同步策略，包括 export/import、备份位置、导入模式、去重和回滚原则。
- **FR-005**: 必须记录当前已知 nmem 风险和数据状态：NAS 数据已迁到本机 NowledgeGraph，本机为当前主库；NAS remote API/MCP 写路径曾超时，NAS 容器已停止并作为旧副本/回滚源保留；本机 nmem 曾 degraded/database disconnected，用户重启后已恢复为 ok/database connected。
- **FR-006**: 必须给出是否继续使用 nmem 的推荐结论，以及何时才考虑替代工具试点。
- **FR-007**: 必须定义替代工具评估门禁，至少覆盖 Mem0/OpenMemory、Zep/Graphiti、Obsidian/Markdown/Git、Karakeep 的适用范围和不适用范围。
- **FR-008**: 必须定义 Hermes memory 写入降级策略：超时后不阻塞主流程、不盲目重复写、必要时写入本地 queue 或日志。
- **FR-009**: 必须更新 note skill migration roadmap，使 `knowledge-library-ingestion-plan` 依赖本 feature 的 closeout 结论。
- **FR-010**: 不得在本 feature 中执行实际 NAS 容器重启、远程写入、批量导入、工具迁移或 note skill 删除；这些属于 plan/tasks 后的显式实现。
- **FR-011**: 必须记录敏感信息处理要求：文档、evidence 和日志不得包含 token、API key、cookie 或真实 bearer。
- **FR-012**: 必须规划 NAS domain spaces 到本机 matching spaces 的单向同步实现，包括 mapping、export、archive、preview、merge/skip import、dedupe 和审计记录。
- **FR-013**: 单向同步实现不得默认启动定时任务；必须先提供 dry-run/preview 和人工确认门禁。
- **FR-014**: 单向同步实现必须支持 domain 级别选择，至少覆盖 WeChat/selfmedia、Novel、XHS 和 Hermes generic 四类。

### Non-Functional Requirements

- **NFR-001**: 可用性优先于功能丰富度；memory 写入失败不能阻塞 Hermes 主工作流或本机 Codex/Claude Code。
- **NFR-002**: 数据可恢复；任何迁移或重新启用前必须有 export/backup。
- **NFR-003**: 同步可审计；每次导出、导入、覆盖或跳过都必须有记录。
- **NFR-004**: 低耦合；长期知识资料不能被锁死在单一 memory 服务里。
- **NFR-005**: 同步默认可 dry-run；没有 preview 证据不得修改本机主库。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 一致性 | 单写源，避免双主 | 防止 Mac/NAS 两份 memory 互相覆盖或重复 | Producer-consumer matrix、同步策略 | 是 |
| 可用性 | 写 memory 失败不阻塞主流程 | 历史问题是写入超时拖死 agent | 降级策略、超时行为验收 | 是 |
| 可恢复性 | 任意启用/迁移前可回滚 | 知识数据不可轻易丢 | export/import/backup 方案 | 是 |
| 安全性 | 不泄露 token/API key/cookie | 本轮探索已暴露环境变量风险 | evidence 脱敏规则、文档扫描 | 是 |
| 可演进性 | 可试点替代工具但不强迁移 | 避免为工具切换付出高同步成本 | 替代工具门禁表 | 否 |

### Key Entities

- **Memory Runtime**: agent 可调用的短中期记忆服务，当前首选 nmem。
- **Knowledge Source of Truth**: 长期、人可读、可备份的资料主库，候选为 Library/Markdown/Git。
- **Hermes-only NAS Mem**: 重新开启后只供 Hermes 使用的 NAS nmem 实例。
- **Local Agent Clients**: 本机 Codex/Claude Code，不应依赖 NAS remote write path。
- **Sync Artifact**: `nmem export` 产物、Markdown/Library 文档、备份包或导入记录。
- **Write Queue / Fallback Log**: memory 写入超时时用于保留待处理摘要的降级产物。
- **Space Mapping**: NAS space 与本机 matching space 的映射表，包含 domain、import mode、是否允许自动导入。
- **Sync Run**: 一次单向同步执行，包含 export、archive、preview、import、verification 和 audit 结果。

---

## Out of Scope

- 不在本 feature 中重启 NAS nmem 容器。
- 不在本 feature 中把 Codex/Claude Code 配置切到 NAS Mem。
- 不执行 nmem 批量 export/import 或替代工具迁移。
- 不在本 feature 规划阶段执行真实 NAS-to-local import；实现阶段也必须先 dry-run。
- 不删除、移动、归档 note 源 skill。
- 不把 Obsidian/Karakeep/Mem0/Zep 直接定为新主库；本 feature 只定义评估与试点门禁。
- 不保存或展示任何 token、API key、cookie、bearer。

---

## Unclear Questions

- NAS nmem 重新开启后，Hermes 是通过内网容器入口、Tailscale 地址还是域名访问，需要 plan 阶段确认。
- Mac 本地 NowledgeGraph 已是当前主库，本机 nmem 重启后已恢复；后续仍需确认是否作为本机 agent 写入路径，还是只作为本地查询/归档路径。
- Library/Markdown/Git 的具体落盘目录和同步方式，需要与 `knowledge-library-ingestion-plan` 对齐。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项（如有）：无；关键架构方向已明确，剩余问题可在 plan 阶段形成方案和任务。

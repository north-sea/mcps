# Tool Evaluation Gates: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01

---

## Recommendation

当前不替换 nmem。继续使用 nmem，但职责降级：

- nmem: Hermes runtime memory
- Markdown/Library/Git: long-term source of truth
- Karakeep: source inbox
- Mem0/OpenMemory: future agent-memory POC only
- Zep/Graphiti: future graph-memory POC only

---

## Candidate Gates

| Tool | Use For | Do Not Use For | POC Trigger | Migration Requirement |
|---|---|---|---|---|
| nmem | Hermes runtime memory、working memory、短中期决策检索 | 唯一长期资料主库、Mac/NAS 双主同步 | NAS Hermes-only 写入仍可接受 | export + no double write |
| Markdown/Library/Git | 长期资料、来源材料、SDD 证据、可读 SOP | 实时 agent memory API | 当前即采用 | Git/backup proof |
| Karakeep | bookmark/source inbox、网页暂存 | agent memory、删除门禁唯一证据 | source ingestion 需要 | 导入 Library 后才算沉淀 |
| Mem0/OpenMemory | agent memory 替代方案 POC | 立即替换全部 nmem | nmem Hermes-only 写入仍长期超时或不可维护 | sample export/import + dedupe test |
| Zep/Graphiti | 关系型/时间图谱 memory POC | 普通知识资料主库 | 明确需要跨实体 temporal graph 查询 | schema mapping + rollback proof |
| Obsidian Sync | 人读 Markdown 多端同步 | agent memory runtime | 需要人读笔记多端实时同步 | Markdown folder remains portable |

---

## POC Minimum Bar

任何替代工具 POC 必须先满足：

- 选 20 条 nmem memory 样本，不做全量迁移。
- 验证 add/search/update/delete。
- 验证 export/backup/restore。
- 验证重复写和超时行为。
- 验证 space/tag/label 或等价隔离能力。
- 验证不泄露 token/API key/cookie/bearer。

未满足以上门禁前，不允许替换当前 nmem 架构。

# Feature Specification: Knowledge Library Ingestion Plan

**Workspace**: `knowledge-library-ingestion-plan`  
**Created**: 2026-07-06  
**Status**: Ready for Plan  
**Input**: `wechat-topic-draft-trial` 证明 topic/draft 链路可用，但暴露 account-fit/source-context 不足；`knowledge-memory-architecture` 已决定长期资料进入 Library/Markdown/Git，nmem 只做 runtime memory。

## Goal

定义 note skill 迁移中的长期资料如何进入 Nowledge Library/Wiki 或 Markdown/Git：账号资料、平台规则、参考文章、写作样例、素材来源、source inbox 和 Karakeep 条目必须有分类、metadata、导入边界、删除门禁和 dry-run 验证路径。

本 feature 只做 ingestion plan 和最小可复放 dry-run，不批量导入全部资料，不删除旧 note skills。

## User Stories

### US1 - 分类长期资料

作为迁移负责人，我希望把 note skills 和内容 runtime 依赖的资料分成账号资料、平台规则、参考文章、写作样例、素材来源、运行决策和临时执行状态，以便每类资料进入正确系统。

Acceptance:

- 每类资料都有 owner、目标系统、推荐路径、metadata、保留策略和删除门禁影响。
- 明确哪些进 Library/Wiki，哪些保留 Markdown/Git，哪些只写 Memory summary，哪些不迁移。

### US2 - 支撑公众号 account-fit

作为公众号运营者，我希望 Library ingestion 优先补齐账号定位、topic track 说明、参考文章和禁写/适写规则，避免 topic planning 继续生成泛化选题。

Acceptance:

- 四个公众号都有 account-fit source 清单。
- `moon-sleeping` 明确包含 3-9 月宝宝照护材料来源类型。
- 试用链路后续使用这些资料前，有可复查的 source id / document id / path。

### US3 - 给 note skill 删除提供门禁

作为迁移负责人，我希望每个将被替换的 note skill 在删除前能指向 Library/Markdown/Git/agents/mcps 的替代路径。

Acceptance:

- 对内容类 P0/P1 skill 输出 route/deletion gate 表。
- 没有替代路径和 dry-run evidence 的 skill 不允许删除。

## Requirements

- **FR-001**: 定义 `KnowledgeSourceClass` 分类表，覆盖账号资料、平台规则、参考文章、写作样例、素材、source inbox、运行决策、临时状态。
- **FR-002**: 定义 Library/Wiki metadata schema，至少包含 `source_id`、`source_class`、`domain`、`account_id`、`track_id`、`origin_path/url`、`owner`、`retention`、`deletion_gate_refs`。
- **FR-003**: 产出内容类 P0/P1 note skills 的 ingestion/deletion gate 矩阵。
- **FR-004**: 产出四个公众号的 account-fit source plan，优先覆盖 `moon-sleeping` 3-9 月宝宝照护。
- **FR-005**: 提供 dry-run manifest 示例，不执行批量导入和删除。
- **FR-006**: 不把全文资料写入 nmem；Memory 只保存决策/流程摘要。
- **FR-007**: 不触发 live Library import、NAS import、远程写入或 note skill 删除。

## Non-Goals

- 不实现完整 Library importer。
- 不迁移全部 note 资料。
- 不删除、归档或重命名 note skills。
- 不启动完整自动写文章 feature。
- 不改变 nmem 主库策略。

## Evidence Gate

- `data-model.md` 定义分类和 metadata。
- `plan.md` 定义 ingestion routing、dry-run manifest 和删除门禁。
- `tasks.md` 拆出可执行检查。
- 至少一个 dry-run manifest 示例覆盖 `moon-sleeping` account-fit source。

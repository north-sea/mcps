# Data Model: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01  
**Scope**: 策略实体，不新增应用数据库 schema。

---

## Entity: MemoryEndpoint

描述一个 memory 或知识服务入口。

| Field | Type | Required | Description |
|---|---|---:|---|
| `endpoint_id` | string | yes | 稳定 ID，例如 `nas-nmem-hermes`, `mac-nmem-local`, `markdown-library` |
| `owner` | enum | yes | `hermes`, `codex`, `claude-code`, `human`, `shared` |
| `location` | enum | yes | `nas`, `mac`, `git`, `cloud`, `external` |
| `service` | enum | yes | `nmem`, `library`, `markdown-git`, `karakeep`, `mem0`, `zep`, `other` |
| `read_allowed` | boolean | yes | 当前策略是否允许读取 |
| `write_allowed` | boolean | yes | 当前策略是否允许写入 |
| `write_mode` | enum | yes | `primary`, `runtime-only`, `disabled`, `manual-only`, `poc-only` |
| `timeout_policy` | enum | yes | `fail-open`, `fail-closed`, `queue`, `manual-retry` |
| `sensitive_config_ref` | string | no | 只允许写引用名，不写真实 token |
| `notes` | string | no | 风险或限制 |

### Required Endpoint Decisions

| endpoint_id | service | owner | read_allowed | write_allowed | write_mode | timeout_policy |
|---|---|---|---:|---:|---|---|
| `nas-nmem-hermes` | `nmem` | `hermes` | true | true | `runtime-only` | `fail-open` |
| `mac-codex-claude-to-nas-nmem` | `nmem` | `codex` / `claude-code` | false | false | `disabled` | `fail-open` |
| `markdown-library-main` | `markdown-git` / `library` | `shared` | true | true | `primary` | `manual-retry` |
| `karakeep-source-inbox` | `karakeep` | `shared` | true | true | `manual-only` | `manual-retry` |
| `mem0-poc` | `mem0` | `shared` | false | false | `poc-only` | `fail-open` |
| `zep-poc` | `zep` | `shared` | false | false | `poc-only` | `fail-open` |

---

## Entity: KnowledgeClass

描述一类知识应该去哪里、如何同步。

| Field | Type | Required | Description |
|---|---|---:|---|
| `class_id` | string | yes | 例如 `decision`, `source-material`, `runtime-memory` |
| `examples` | list[string] | yes | 典型内容 |
| `source_of_truth` | endpoint_id | yes | 长期主库 |
| `runtime_index` | endpoint_id | no | 可选 runtime memory 索引 |
| `write_owner` | string | yes | 谁负责写 |
| `sync_method` | enum | yes | `none`, `export`, `manual-import`, `derived-summary`, `future-pipeline` |
| `retention` | enum | yes | `long-term`, `runtime`, `archive`, `temporary` |
| `deletion_gate_impact` | string | yes | 对 note skill 删除门禁的影响 |

### Required Classes

| class_id | source_of_truth | runtime_index | sync_method | retention |
|---|---|---|---|---|
| `durable-decision` | `markdown-library-main` | `nas-nmem-hermes` optional | `derived-summary` | `long-term` |
| `procedure-sop` | `markdown-library-main` | `nas-nmem-hermes` optional | `derived-summary` | `long-term` |
| `source-material` | `markdown-library-main` | none | `future-pipeline` | `long-term` |
| `bookmark-inbox` | `karakeep-source-inbox` | none | `manual-import` | `archive` |
| `hermes-runtime-memory` | `nas-nmem-hermes` | `nas-nmem-hermes` | `export` | `runtime` |
| `codex-session-evidence` | `markdown-library-main` / `specs` | none | `none` | `long-term` |
| `fallback-memory-write` | fallback queue/log | none | `manual-import` | `temporary` |

---

## Entity: SyncArtifact

描述一次导出、备份、导入或派生摘要。

| Field | Type | Required | Description |
|---|---|---:|---|
| `artifact_id` | string | yes | 可由时间戳和来源生成 |
| `source_endpoint` | endpoint_id | yes | 来源 |
| `target_endpoint` | endpoint_id | no | 目标；纯备份可为空 |
| `path` | string | yes | 文件或目录路径 |
| `format` | enum | yes | `nmem-export-zip`, `nmem-export-folder`, `markdown`, `jsonl`, `other` |
| `created_at` | datetime | yes | 创建时间 |
| `import_mode` | enum | no | `merge`, `skip`, `overwrite`, `read-only` |
| `checksum` | string | no | 校验值 |
| `status` | enum | yes | `created`, `verified`, `imported`, `failed`, `expired` |
| `notes` | string | no | 说明 |

---

## Entity: FallbackRecord

描述一次 memory 写入失败后的降级记录。

| Field | Type | Required | Description |
|---|---|---:|---|
| `fallback_id` | string | yes | 稳定 ID |
| `source_agent` | enum | yes | `hermes`, `codex`, `claude-code`, `other` |
| `attempted_endpoint` | endpoint_id | yes | 原计划写入端 |
| `operation` | enum | yes | `add`, `update`, `delete`, `working-memory-patch` |
| `dedupe_key` | string | yes | 防止重复写 |
| `summary` | string | yes | 脱敏摘要 |
| `sensitive_redacted` | boolean | yes | 必须为 true |
| `status` | enum | yes | `queued`, `confirmed-saved`, `discarded`, `manually-imported`, `expired` |
| `created_at` | datetime | yes | 创建时间 |
| `resolved_at` | datetime | no | 处理时间 |

### State Rules

```text
queued -> confirmed-saved
queued -> manually-imported
queued -> discarded
queued -> expired
confirmed-saved -> terminal
manually-imported -> terminal
discarded -> terminal
expired -> terminal
```

---

## Entity: SpaceMapping

描述一个 NAS domain space 到本机 matching space 的同步映射。

| Field | Type | Required | Description |
|---|---|---:|---|
| `mapping_id` | string | yes | 稳定 ID，例如 `nas-selfmedia-to-local-selfmedia` |
| `domain` | enum | yes | `selfmedia`, `novel`, `xhs`, `hermes`, `other` |
| `nas_space_name` | string | yes | NAS 上的可见 space 名称，inventory 后填入 |
| `nas_space_id` | string | no | NAS space ID，若可获取则记录 |
| `local_space_name` | string | yes | 本机目标 space 名称 |
| `local_space_id` | string | no | 本机目标 space ID |
| `default_import_mode` | enum | yes | `merge` 或 `skip`；不得默认为 `overwrite` |
| `auto_import_allowed` | boolean | yes | MVP 默认 false |
| `notes` | string | no | 风险或说明 |

### Initial Mapping Candidates

| domain | nas_space_name | local_space_name | default_import_mode | auto_import_allowed |
|---|---|---|---|---:|
| `selfmedia` | TBD after NAS inventory | `sp_selfmedia_87f9f87e` | `merge` | false |
| `novel` | TBD after NAS inventory | TBD | `skip` | false |
| `xhs` | TBD after NAS inventory | TBD | `skip` | false |
| `hermes` | `hermes` if created | TBD / `Default` | `skip` | false |

---

## Entity: SyncRun

描述一次单向同步执行。

| Field | Type | Required | Description |
|---|---|---:|---|
| `run_id` | string | yes | 时间戳 + domain |
| `domain` | enum | yes | 与 SpaceMapping domain 一致 |
| `mapping_id` | string | yes | 使用的 mapping |
| `mode` | enum | yes | `dry-run`, `import` |
| `nas_export_path` | string | yes | NAS export archive 或本地拉取后的路径 |
| `preview_path` | string | yes | preview/dedupe report |
| `import_mode` | enum | yes | `merge` 或 `skip` |
| `status` | enum | yes | `planned`, `exported`, `previewed`, `imported`, `blocked`, `failed` |
| `records_seen` | integer | no | preview 看到的记录数 |
| `records_imported` | integer | no | 实际导入记录数 |
| `duplicates_detected` | integer | no | 重复记录数 |
| `blocked_reason` | string | no | 阻塞原因 |
| `created_at` | datetime | yes | 执行时间 |

### SyncRun Rules

```text
planned -> exported -> previewed
previewed -> imported
previewed -> blocked
exported -> failed
imported -> terminal
blocked -> terminal
failed -> terminal
```

Invariants:

- `mode=import` 必须引用已有 preview。
- `import_mode` 不允许为 `overwrite`。
- `auto_import_allowed=false` 时，任何 import 都必须有人为确认记录。

---

## Invariants

- `mac-codex-claude-to-nas-nmem.write_allowed` 必须为 `false`，除非未来新 feature 明确重新评估。
- 任何 `sensitive_config_ref` 只能是引用名，不能是真实 token、API key、cookie 或 bearer。
- `nas-nmem-hermes.timeout_policy` 不能是 `fail-closed`，否则 memory 写失败会阻塞 Hermes。
- `source-material.source_of_truth` 不能是 nmem；来源材料必须进入 Library/Markdown/Git 或等价长期资料库。
- `FallbackRecord.summary` 必须脱敏。
- `SyncArtifact.import_mode=overwrite` 必须人工确认，不得作为默认策略。

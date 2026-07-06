# Sync Strategy: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01

---

## Sync Principles

- 单写源优先，禁止 Mac/NAS 双主同步。
- 官方同步模型是一台常开 Mem 作为唯一事实来源，多端连接同一个后端；不是多个独立数据库自动复制/合并。
- Spaces 的 shared context 只扩大检索范围，不移动记录，也不会偷偷合并空间。
- NAS nmem 已迁移到本机 NowledgeGraph；NAS 重新开启前必须先备份旧副本并确认不会成为双主。
- 默认导入模式不得是 overwrite。
- domain spaces 保留，不强制合并到 `hermes`。
- 长期资料以 Markdown/Library/Git 为主，nmem 只保存摘要和 runtime memory。

---

## NAS nmem Backup Flow

```text
NAS nmem stopped; local NowledgeGraph is current primary copy
  -> volume snapshot or directory copy of NAS old copy
  -> compare with local NowledgeGraph/backups
  -> start NAS nmem only if needed for Hermes
  -> nmem export
  -> verify export artifact exists
  -> read-only inventory spaces/counts
  -> decide cleanup/archive/import
```

MVP 可接受两类备份：

1. Docker volume / data directory snapshot。
2. `nmem export` zip/folder。

推荐两者都做；至少做其中一种。

---

## Import Rules

| Scenario | Mode | Rule |
|---|---|---|
| NAS old copy export to archive | read-only | 不导入，只保存 |
| NAS export to Mac local nmem | merge or skip | 仅人工触发 |
| Library/Markdown derived summary to nmem | add/update with dedupe | 只写摘要 |
| Conflict between NAS and Mac | manual resolution | 不自动 overwrite |
| Full restore after failure | overwrite only with approval | 需要备份和用户确认 |

---

## Space Sync Rules

| Source Space | Target | Method |
|---|---|---|
| `hermes` | backup archive | scheduled export |
| NAS WeChat/content space | local matching content space + Library summary + optional `hermes` cross-domain summary | export -> merge/skip import after review -> derived-summary |
| NAS Novel space | local matching novel space + Library summary + optional `hermes` cross-domain summary | export -> merge/skip import after review -> derived-summary |
| NAS XHS space | local matching xhs space + Library summary + optional `hermes` cross-domain summary | export -> merge/skip import after review -> derived-summary |
| Mac local nmem | no automatic NAS import | manual only |

---

## NAS Domain Delta Sync

当 Hermes 写 NAS domain space 时，采用一向 delta 同步：

```text
NAS domain write
  -> NAS export artifact
  -> archive raw export
  -> compare against local spaces
  -> import with merge/skip into mapped local space
  -> create durable Markdown/Library summary for long-term material
```

### Space Mapping

同步前必须建立 mapping：

| Domain | NAS Space | Local Space | Default Import Mode | Notes |
|---|---|---|---|---|
| WeChat / self media | TBD after NAS inventory | `sp_selfmedia_87f9f87e` if equivalent | `merge` or `skip` | 当前本机已有 selfmedia space |
| Novel | TBD after NAS inventory | TBD | `merge` or `skip` | 不存在则先创建或只归档 |
| XHS | TBD after NAS inventory | TBD | `merge` or `skip` | 小红书仍需业务线确认 |
| Hermes generic | `hermes` if created | Default or future `hermes` local space | `merge` or `skip` | 可只归档不导入 |

### Dedupe Rules

- 优先用 nmem record id / source_thread_id / title / timestamp / labels 去重。
- Hermes 写入 domain memory 时应尽量带 domain label 和 dedupe key。
- 导入前先抽样检查重复率，不直接全量导入。
- 冲突时保留本地主副本，NAS 记录进入 archive 或人工 review。

### Supported Config Surface

官方配置可支撑的部分：

- CLI 和 remote clients 可以通过 `--api-url` / `NMEM_API_URL` 指向某个 Mem 实例。
- CLI 可以通过 `--space "<space name>"` 在指定 space 内执行命令。
- HTTP/MCP API 沿用 `space_id` 字段，也可直接传可见 space 名称。
- Spaces 可以设置检索范围：当前 space、当前 + shared spaces、或全空间搜索。
- Memories/Threads 支持 move 到其他 space，并提供 bulk move preview。
- Data Transfer 支持 export/import，import mode 有 `merge`、`skip`、`overwrite`，默认应使用 `merge`。

官方配置不能直接支撑的部分：

- 不支持 NAS Mem 和 Mac Mem 两套独立数据库的自动双向同步。
- shared context 不会把记录复制到 `hermes` 或合并 domain spaces。
- export/import 是备份、迁移或人工/任务同步机制，不是实时多主复制。

### What Not To Sync

不建议从 NAS domain space 同步回本地的内容：

- 临时运行日志
- 失败重试噪音
- 纯 prompt 中间态
- 含敏感信息或未脱敏 payload
- 已经转成 Markdown/Library 的长原文

---

## Cleanup Rules

Do:

- dedupe exact duplicate runtime memories after backup
- archive stale test memories
- export source-like long records to Library/Markdown before deletion

Do not:

- delete entire spaces before inventory
- merge domain spaces into `hermes`
- import overwrite without approval
- clean data while service write path is unstable and unbacked

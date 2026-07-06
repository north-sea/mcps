# Routing Policy: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01

---

## Decision Summary

- NAS nmem 数据 **不直接清理**。数据已迁到本机 NowledgeGraph，NAS 目录当前按旧副本/回滚源处理；先做只读审计和 export/volume 备份，再决定是否归档、合并或删除。
- NAS nmem 重新开启后，默认只作为 **Hermes runtime memory**。
- 本机 Codex/Claude Code 不写 NAS nmem remote API/MCP。
- Hermes 写入默认进入 `hermes` space；公众号、小说、小红书已有 domain space 时，保留 domain space，不强制合并到 `hermes`。

---

## Endpoint Policy

| Endpoint | Owner | Read | Write | Mode | Timeout Policy | Notes |
|---|---|---:|---:|---|---|---|
| `nas-nmem-hermes` | Hermes | yes | yes | runtime-only | fail-open | 如恢复运行，作为 Hermes 默认 memory runtime；写失败不能阻塞主流程 |
| `nas-nmem-domain-spaces` | Hermes domain workflows | yes | yes | runtime-only | fail-open | 公众号/小说/小红书等已有 space 可继续使用 |
| `mac-codex-claude-to-nas-nmem` | Codex/Claude Code | no | no | disabled | fail-open | 不使用 NAS remote write path |
| `mac-local-nmem` | local tools | optional | disabled until healthy | local-primary-data | fail-open | 本机 NowledgeGraph 是当前主数据副本，但服务 degraded/database disconnected，不作为自动写入必需路径 |
| `markdown-library-main` | shared | yes | yes | primary | manual-retry | 长期资料主库 |
| `karakeep-source-inbox` | shared | yes | manual | inbox | manual-retry | 来源收藏和资料暂存 |

---

## Space Policy

### Default Rule

Hermes 通用运行记忆写入 `hermes` space。

适合进入 `hermes` 的内容：

- Hermes 自身运行决策
- 跨领域 SOP
- NAS / provider / deploy / auth / fallback 经验
- 与多个业务线共享的 agent 操作记忆

### Domain Space Rule

已有领域 space 不合并、不清空：

- 公众号 / WeChat 内容生产相关记忆保留在对应公众号或内容 space
- 小说相关记忆保留在小说 / 书名 / novel space
- 小红书相关记忆保留在 xhs / 小红书 space

适合进入 domain space 的内容：

- 单账号内容偏好
- 选题风格和历史表现
- 小说书籍设定、章节生产经验
- 小红书平台约束、封面/标签策略

### Cross-Space Retrieval Rule

如果 nmem spaces 支持 shared retrieval，推荐：

```text
hermes space:
  retrieval = shared
  share-with = content / novel / xhs domain spaces where appropriate

domain spaces:
  keep domain-specific writes local
  expose summaries or selected links back to hermes only when cross-domain useful
```

如果 shared retrieval 不稳定或不可用，则使用 export/derived-summary：

```text
domain space -> periodic export/summary -> markdown-library-main
markdown-library-main -> selected durable summaries -> hermes runtime memory
```

官方文档确认：shared context 只影响检索范围，不移动记录，不合并 spaces。因此它适合让 `hermes` 读取公众号/小说/小红书上下文，但不能替代数据同步。

### NAS Domain Write Rule

如果 Hermes 必须写 NAS 上的 domain space，NAS 写入只视为 **runtime delta**，不直接成为长期主库。

推荐同步方向：

```text
Hermes writes NAS domain space
  -> scheduled NAS nmem export
  -> archive raw export
  -> import/merge into matching local space only after review
  -> durable summaries go to Markdown/Library/Git
```

硬约束：

- 不做 Mac <-> NAS 双向自动同步。
- 不使用 overwrite 作为默认导入模式。
- NAS domain space 写入必须带可去重线索，例如 source agent、domain、dedupe key 或标题前缀。
- 如果本机已有同名/同类 domain space，优先 merge/skip；如果 space ID 不一致，先建立 mapping，不直接导入。
- 重要长期资料应从 NAS export 派生到 Markdown/Library/Git，而不是只停留在 NAS nmem。

---

## Cleanup Policy

NAS nmem 旧副本清理顺序：

1. **Snapshot first**: volume/export 备份。
2. **Compare second**: 与本机 NowledgeGraph/备份确认迁移状态，不把 NAS 当唯一源。
3. **Inventory third**: 列出 spaces、memory counts、recent writes、large/source-like records。
4. **Classify fourth**:
   - keep runtime memory
   - export to Library/Markdown
   - archive old duplicate
   - delete only after replacement proof
5. **No bulk delete by default**。

不允许：

- 直接删 NAS `data/`。
- 因为要给 Hermes 用就把公众号/小说/小红书 space 合并到 `hermes`。
- 在没有 export 的情况下做 import overwrite。

---

## Verification

- NAS container can be stopped while policy is written.
- Before restart, confirm backup exists.
- After restart, run read-only space inventory before any cleanup.
- Before syncing NAS domain writes, create a NAS-to-local space mapping.
- Confirm local Codex/Claude Code config does not point at NAS nmem remote write.

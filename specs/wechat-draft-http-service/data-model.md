# Data Model: WeChat Draft MCP Service (Streamable HTTP)

**Workspace**: `wechat-draft-http-service` | **Date**: 2026-06-26

---

## Entities

### Draft Job (table: `jobs`)

**描述**: 记录一次 WeChat draft 创建流程的状态、幂等键、微信 media_id 和失败信息。该表替代旧 JSONL JobStore。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| job_id | TEXT | PRIMARY KEY | job 标识，形如 `job_<timestamp>_<random>` |
| artifact_id | TEXT | NOT NULL, INDEX | hermes-db workflow artifact id |
| account | TEXT | NOT NULL, UNIQUE(account, idempotency_key) | WeChat account id |
| status | TEXT | NOT NULL, INDEX | job 当前状态 |
| media_id | TEXT | NULL | 微信草稿 media_id |
| idempotency_key | TEXT | NOT NULL, UNIQUE(account, idempotency_key) | 调用方提供或由 `account:artifact_id` 派生 |
| idempotency_expires_at | TEXT | NOT NULL, INDEX | 幂等窗口过期时间，ISO datetime |
| created_at | TEXT | NOT NULL, INDEX | 创建时间，ISO datetime |
| updated_at | TEXT | NOT NULL | 最近更新时间，ISO datetime |
| error_code | TEXT | NULL | 失败错误码 |
| error_message | TEXT | NULL | 可读错误信息 |
| error_details | TEXT | NULL | JSON string，保存结构化细节 |

**索引**:
- `sqlite_autoindex_jobs_1` on `(job_id)` via primary key
- `sqlite_autoindex_jobs_2` on `(account, idempotency_key)` via unique constraint
- `idx_jobs_artifact_id` on `(artifact_id)`
- `idx_jobs_status` on `(status)`
- `idx_jobs_created_at` on `(created_at)`
- `idx_jobs_idempotency_expires_at` on `(idempotency_expires_at)`

**状态转换**:

```text
queued
  -> artifact_validation
  -> adapter_check
  -> payload_build
  -> draft_creating
  -> ledger_update
  -> saved

queued / artifact_validation / payload_build
  -> invalid_artifact

adapter_check / draft_creating
  -> needs_operator_action

any in-progress state
  -> failed
```

终态：
- `saved`
- `failed`
- `invalid_artifact`
- `needs_operator_action`

非终态：
- `queued`
- `artifact_validation`
- `adapter_check`
- `payload_build`
- `draft_creating`
- `ledger_update`

---

## Relationships

```text
jobs.artifact_id  -> hermes-db workflow_artifacts.artifact_id
jobs.media_id     -> WeChat draft media_id
jobs.account      -> accounts.yaml accounts[].account_id
```

`jobs` 不维护外键。hermes-db 和 WeChat 都是外部系统，服务通过客户端调用验证引用是否有效。

---

## DDL Scripts

```sql
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  account TEXT NOT NULL,
  status TEXT NOT NULL,
  media_id TEXT,
  idempotency_key TEXT NOT NULL,
  idempotency_expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  error_code TEXT,
  error_message TEXT,
  error_details TEXT,
  UNIQUE(account, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_jobs_artifact_id
  ON jobs(artifact_id);

CREATE INDEX IF NOT EXISTS idx_jobs_status
  ON jobs(status);

CREATE INDEX IF NOT EXISTS idx_jobs_created_at
  ON jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_jobs_idempotency_expires_at
  ON jobs(idempotency_expires_at);
```

---

## Idempotency Algorithm

```text
createOrGetJob(account, artifactId, idempotencyKey):
  BEGIN IMMEDIATE
  DELETE FROM jobs
    WHERE idempotency_expires_at <= now
      AND status IN ('saved', 'failed', 'invalid_artifact', 'needs_operator_action')

  INSERT OR IGNORE INTO jobs (...)
    VALUES (..., 'queued', expires_at = now + 7 days)

  SELECT * FROM jobs
    WHERE account = ? AND idempotency_key = ?

  COMMIT
  return { job, created: insertedRowCount === 1 }
```

并发调用同一 `account + idempotency_key` 时，只有第一个调用继续执行外部副作用。其他调用返回已有 row 的当前状态。

---

## Migration Notes

- 旧 JSONL job files 不做自动迁移；当前 feature 尚未投入使用，允许从空 SQLite 数据库开始。
- 数据库初始化由服务启动执行 `CREATE TABLE IF NOT EXISTS`。
- 回滚策略：保留旧 stdio 入口和旧 JSONL JobStore 代码作为 7 天迁移兜底；Docker 服务不使用旧 store。
- 过期清理策略：只在创建 job 的事务内清理终态过期 row，避免删除正在进行的 job。

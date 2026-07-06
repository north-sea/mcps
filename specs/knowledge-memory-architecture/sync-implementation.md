# Sync Implementation Plan: NAS Domain Spaces To Local nmem

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01  
**Scope**: 规划单向同步实现；默认 dry-run，不执行真实导入。

---

## Goal

把 Hermes 写入 NAS nmem domain spaces 的增量同步回本机 matching spaces，同时保持：

- NAS -> local 单向
- dry-run first
- merge/skip only
- no overwrite
- no bidirectional sync
- no Codex/Claude Code NAS write path

---

## Proposed Artifacts

```text
scripts/nmem-nas-domain-sync.sh           # orchestration wrapper
scripts/nmem-space-map.example.json       # mapping template, no secrets
specs/knowledge-memory-architecture/sync-runs/  # optional audit records
```

如果后续决定不在 repo 放脚本，也可以把脚本放到 NAS ops 目录；但 mapping、dry-run 输出和 audit 规则仍由本 feature 定义。

Current scaffold status:

- `scripts/nmem-space-map.example.json` exists and contains selfmedia/novel/xhs/hermes mappings.
- `scripts/nmem-nas-domain-sync.sh` exists as a safety-first scaffold.
- `preview` writes a local report and does not modify local nmem.
- `import` requires explicit confirm and still exits before real import until production import is implemented.

---

## Commands Shape

```bash
# Inventory only
scripts/nmem-nas-domain-sync.sh inventory --nas nas

# Generate preview, no local import
scripts/nmem-nas-domain-sync.sh preview --domain selfmedia --map scripts/nmem-space-map.json

# Import only after preview and explicit confirmation
scripts/nmem-nas-domain-sync.sh import --domain selfmedia --map scripts/nmem-space-map.json --run-id <run-id>
```

No command should accept `overwrite` as a default path.

Current safety check evidence:

```text
rtk bash scripts/nmem-nas-domain-sync.sh --help -> PASS
rtk bash scripts/nmem-nas-domain-sync.sh preview --domain selfmedia --map scripts/nmem-space-map.example.json -> blocked because NAS space is still TBD; preview report created
rtk bash scripts/nmem-nas-domain-sync.sh import --domain selfmedia --map scripts/nmem-space-map.example.json --run-id dummy -> rejected because confirm is missing
rtk bash scripts/nmem-nas-domain-sync.sh import --domain selfmedia --map scripts/nmem-space-map.example.json --run-id dummy --confirm I_UNDERSTAND_THIS_IMPORTS_TO_LOCAL_NMEM -> gate passed, then exits before real import
```

---

## Flow

### 1. Inventory

```text
ssh nas -> nmem spaces list / export metadata
local nmem spaces list
produce mapping candidates
```

Output:

- NAS spaces list
- local spaces list
- suggested mapping
- unknown spaces

### 2. Preview

```text
resolve mapping
export NAS data for mapped domain
store raw export archive
compare with local target space
produce preview report
stop
```

Output:

- raw export path
- preview report
- duplicate estimate
- import command suggestion

### 3. Import

```text
require preview run-id
require explicit confirm flag
import with merge or skip
write audit record
run post-import count/search smoke
```

Output:

- import status
- records seen/imported/skipped
- duplicates detected
- post-import smoke

---

## Mapping Template

```json
{
  "version": 1,
  "default_import_mode": "merge",
  "mappings": [
    {
      "domain": "selfmedia",
      "nas_space": "TBD",
      "local_space": "sp_selfmedia_87f9f87e",
      "import_mode": "merge",
      "auto_import_allowed": false
    },
    {
      "domain": "novel",
      "nas_space": "TBD",
      "local_space": "TBD",
      "import_mode": "skip",
      "auto_import_allowed": false
    },
    {
      "domain": "xhs",
      "nas_space": "TBD",
      "local_space": "TBD",
      "import_mode": "skip",
      "auto_import_allowed": false
    }
  ]
}
```

---

## Safety Gates

- NAS container must be running only for inventory/export, not required for local import.
- Raw NAS export must be archived before import.
- Mapping must resolve to exactly one local space.
- `overwrite` is rejected.
- Import requires preview run id.
- Import requires explicit confirm.
- Secrets are not printed or written to audit.
- If duplicate ratio is high or unknown, block import and ask for review.

---

## Open Implementation Questions

- Does `nmem export` support space-scoped export directly, or do we export full archive and filter/import by space?
- Does `nmem import` support selecting a target space by name/id, or must exported records already carry source space metadata?
- Should audit records live in repo specs, `/tmp`, or a persistent NAS/Mac ops directory? Current scaffold writes preview reports under `${TMPDIR:-/tmp}/nmem-nas-domain-sync`.
- Should Hermes write include explicit dedupe labels to improve import preview?

These should be answered by dry-run exploration before writing a production sync script.

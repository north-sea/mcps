# Acceptance Record: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)

---

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001..FR-003: nmem/Library/Hermes/local client boundary and single-writer strategy | Routing policy disables local Codex/Claude Code NAS writes, keeps NAS nmem Hermes-only, and routes durable knowledge to Markdown/Library/Git. | `routing-policy.md`; `knowledge-classes.md` | PASS |
| FR-004: data sync strategy | Sync strategy defines NAS old-copy backup, domain delta sync, merge/skip imports, no default overwrite, and no bidirectional sync. | `sync-strategy.md` | PASS |
| FR-005: current nmem risk/data state | Plan/spec record local NowledgeGraph as current primary copy, NAS as old copy/rollback source, local nmem restored to v0.10.6 ok. | `plan.md`; `verify-evidence.md` | PASS |
| FR-006..FR-007: nmem recommendation and alternative gates | Recommendation is to keep nmem as runtime memory; Mem0/Zep/Graphiti are future POC gates only. | `tool-evaluation-gates.md` | PASS |
| FR-008: Hermes write timeout fallback | Fallback policy says fail open, do not block Hermes, do not blindly retry, confirm possible side effects first. | `fallback-policy.md` | PASS |
| FR-009: roadmap/content runtime alignment | Roadmap current and content runtime evidence include this feature as dependency. | `roadmap.md`; `wechat-content-runtime-contracts/verify-evidence.md` | PASS |
| FR-010: no destructive or live side effects | No NAS restart/export/import, no live write, no note skill deletion. | `verify-evidence.md` | PASS |
| FR-011: sensitive info handling | Secret-pattern scan passed; docs use placeholders and rules only. | `verify-evidence.md` | PASS |
| FR-012..FR-014: one-way sync implementation planning | Space mapping, sync implementation plan, preview scaffold, and import gate exist. Real import intentionally disabled. | `sync-implementation.md`; `scripts/nmem-space-map.example.json`; `scripts/nmem-nas-domain-sync.sh` | PASS |

---

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | SDD artifacts, strategy docs, mapping template, and safety-first script scaffold are present. |
| Workflow closure | PASS | The NAS-domain-to-local sync workflow is defined and guarded: inventory -> preview -> mapping/dedupe -> confirmed import gate. |
| User-visible outcome | PASS | User has a clear operating model: Hermes may write NAS nmem, local remains primary, sync is one-way and gated. |

**Overall**: PASS for planning/scaffold scope.

---

## Completion Record

- **最终结论**: PASS。
- **完成依据**: [verify-evidence.md](verify-evidence.md); policy docs; script scaffold safety checks.
- **阻塞项**: 无 SDD 规划阻塞项。
- **延后项**: 真实 NAS restart、NAS export、本机 import、cron/scheduler、production import implementation。
- **退役结论**: 不退役 nmem；退役“NAS/Mac 双主同步”想法；本机 Codex/Claude Code 不使用 NAS nmem write path。
- **提交结论**: not_submitted。
- **后续动作**: 回到 `wechat-content-runtime-contracts` closeout，或若要真实同步，先补 production import implementation feature。

---

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | Keep nmem as runtime memory, not durable source of truth | nmem remains useful for Hermes runtime memory, but durable knowledge belongs in Markdown/Library/Git. | `routing-policy.md`; `plan.md` | note skill migration | recorded-only | Library ingestion |
| decision | NAS domain sync is one-way and gated | NAS writes are runtime deltas; sync to local requires export/archive/preview/mapping/dedupe and merge/skip import. | `sync-strategy.md`; script scaffold | nmem operations | recorded-only | Real import implementation if needed |
| safety | No overwrite by default | `overwrite` is disallowed by policy and rejected by scaffold unless a future explicitly approved implementation changes it. | `scripts/nmem-nas-domain-sync.sh` | nmem sync | recorded-only | none |

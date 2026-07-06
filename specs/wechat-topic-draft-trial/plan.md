# Implementation Plan: WeChat Topic / Draft Trial

**Workspace**: `wechat-topic-draft-trial` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)

---

## Trial Mode

本 feature 是投入使用阶段，不是新建大块代码。它把已经完成的契约和生产 smoke 组合成低风险试用流程：

1. 选题进入 `hermes-db` topic / topic plan 契约。
2. 人工或 agent 选择一个候选题进入草稿准备。
3. 文章内容可以人工提供或由 runtime 辅助生成，但完整写作自动化不在本 feature。
4. 草稿链路使用 `packages/wechat-draft` 已验证的 article artifact / draft handoff。
5. 试用记录沉淀到本 feature evidence，作为后续写作 feature 和 Library ingestion 的输入。

## Source Contracts

| Contract | Source | Status |
|---|---|---|
| Topic plan storage | `specs/hermes-db-topic-plan-contract/acceptance.md` | PASS, deployed as `hermes-db-v0.2.28` |
| Topic adopt / inbox dry-run | `specs/wechat-content-runtime-contracts/verify-evidence.md` T006 | PASS |
| Article-to-draft handoff | `specs/wechat-content-runtime-contracts/verify-evidence.md` T004-T005 | PASS |
| Image handoff optional | `specs/wechat-content-runtime-contracts/verify-evidence.md` T007 | PASS dry-run; live provider optional |
| Memory / Library boundary | `specs/knowledge-memory-architecture/acceptance.md` | PASS |

## Operating Rules

- `topic` 和 `topic_plan` 状态写 `hermes-db`。
- 来源材料、参考文章、平台规则进入 Library / Markdown / Git，Memory 只保存决策摘要。
- NAS nmem 若恢复，只给 Hermes runtime 使用；本机 Codex/Claude Code 不写 NAS nmem。
- 发草稿前必须有人确认目标账号、标题、封面/素材状态和是否 live。
- 选题必须先过 account-fit gate：明确匹配某一个账号/track 后，才能进入实际草稿链路；泛 AI 基建题只允许做链路 smoke，不作为真实运营题。
- `moon-sleeping` 按母婴 / 孕产 / 3-9 月宝宝照护定位处理，优先关注辅食、哄睡、夜醒、作息、出牙/发育、喂养焦虑和妈妈情绪支持，不按泛睡眠号生成选题。
- 试用中遇到缺口，优先记录为 trial finding，不马上扩大成写作 feature。

## Evidence

试用期间新增证据统一写入：

- `specs/wechat-topic-draft-trial/trial-log.md`
- `specs/wechat-topic-draft-trial/acceptance.md`

## Rollback

- 旧 note skills 保留。
- 若草稿链路失败，回退到现有手工草稿流程。
- 若 topic plan 写入失败，回退到人工 Markdown 选题清单，并记录 contract 缺口。

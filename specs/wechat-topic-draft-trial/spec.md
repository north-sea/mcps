# Feature Specification: WeChat Topic / Draft Trial

**Workspace**: `wechat-topic-draft-trial`  
**Created**: 2026-07-01  
**Status**: Trial Active  
**Input**: 用户决定先投入使用选题和发草稿链路，文章写作 feature 暂后置，先试用一段时间。

---

## Goal

把当前已验证的 topic planning、topic adopt/inbox、WeChat draft handoff 能力投入日常试用。试用期优先验证“选题是否好用、草稿创建是否稳定、人工决策记录是否清楚”，暂不推进完整自动写文章能力。

## Scope

- 使用 `hermes-db-topic-plan-contract` 作为 topic planning 稳定契约。
- 使用 `wechat-content-runtime-contracts` 已通过的 topic/image/article-to-draft dry-run evidence 作为试用前置。
- 允许人工或 agent 生成文章内容后发草稿；不要求本 feature 自动完成正文写作。
- 试用期只做 dry-run 或明确人工确认后的发草稿动作。
- 试用反馈写回本 feature 的 trial log / acceptance，不直接删除旧 note skills。

## Out of Scope

- 不做完整“自动写文章”feature。
- 不把正文生成、润色、审稿、标题改写下沉到 MCP。
- 不清理、删除、归档 `/Users/yqg/learning/biji/note` 中旧 skill。
- 不做批量发布、定时发布、自动运营闭环。

## Trial Success Criteria

| Criteria | Gate |
|---|---|
| 选题可用 | 至少完成一轮 topic plan / shortlist / adopt 或明确记录阻塞原因 |
| 草稿可用 | 至少完成一轮 article artifact 到 WeChat draft 的人工确认或可复放 dry-run |
| 状态可追踪 | topic、draft、人工决策、失败原因能在 hermes-db / SDD evidence 中追踪 |
| 边界不漂移 | 写作生成仍在 Hermes/Codex/agents runtime，MCP 只做契约和状态 |
| 试用可回滚 | 旧 note skills 保持可用，不做删除或迁移破坏 |

## Deferred Feature

完整写文章能力后置，等试用期确认选题和草稿链路稳定后，再决定是否启动独立 feature，例如 `wechat-writing-runtime-contracts` 或 agents 仓对应写作 runtime feature。

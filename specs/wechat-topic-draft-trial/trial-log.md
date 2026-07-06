# Trial Log: WeChat Topic / Draft Trial

**Workspace**: `wechat-topic-draft-trial`  
**Started**: 2026-07-01  
**Mode**: operational trial; manual-confirmed live actions only.

---

## Runs

### 2026-07-01 Run 001: topic plan + shortlist

| Field | Value |
|---|---|
| Mode | production hermes-db MCP write; no external publish/upload; no draft creation |
| Account / Track | `after-work` / `skill-upgrade` |
| Candidate | `AI Agent 的记忆系统为什么应该先有边界再谈工具` |
| Candidate ID | `625a39ed-1c65-4d9f-a3bf-6f636a332a85` |
| Candidate Status | `shortlisted` |
| TopicPlan ID | `68f1fcde-80a5-402e-b3e0-1e952a9da4c9` |
| TopicPlan Status | `planned` |
| Recommended title | `AI Agent 的记忆系统，别急着换工具` |
| Adopt decision | Deferred. The candidate is shortlisted and planned, but not adopted into a final topic yet. |
| Draft decision | Deferred. No WeChat draft was created in this run. |
| Editorial fit | Test-only acceptable; not suitable for actual use across the four configured public accounts. |

Evidence:

- `health` on NAS hermes-db returned `version=0.2.28`, `schema_revision=0010_topic_plans`, `pg=ok`, `topic_plans=true`, `topic_candidates=true`.
- `upsert_topic_candidate` created the candidate with `source=codex-trial`.
- `upsert_topic_plan(mark_candidate_shortlisted=true)` created the TopicPlan and moved the candidate to `shortlisted`.
- `list_topic_plans(account_id=after-work, track_id=skill-upgrade, status=planned)` returned the plan.
- `get_topic_candidate` confirmed `candidate_status=shortlisted`.

### 2026-07-01 Run 002: moon-sleeping topic plan + shortlist

| Field | Value |
|---|---|
| Mode | production hermes-db MCP write; no external publish/upload; no draft creation |
| Account / Track | `moon-sleeping` / `postpartum-survival` |
| Candidate | `凌晨三点喂完奶后，怎么让自己别陷进清醒和自责` |
| Candidate ID | `f25d88b6-1548-4636-9976-05f15b7ce698` |
| Candidate Status | `shortlisted` |
| TopicPlan ID | `6561acf2-123e-41c3-be80-71d6e52fb202` |
| TopicPlan Status | `planned` |
| Recommended title | `凌晨三点醒着的人，也值得被轻轻放过` |
| Editorial fit | Closer to maternal/postpartum care than Run 001, but user clarified `moon-sleeping` should more broadly cover maternal/infant topics, especially 3-9 month baby care such as complementary food and soothing to sleep. |
| Adopt decision | Deferred. |
| Draft decision | Deferred. No WeChat draft was created in this run. |

Evidence:

- `upsert_topic_candidate` created the candidate with `source=codex-trial`.
- `upsert_topic_plan(mark_candidate_shortlisted=true)` created the TopicPlan and moved the candidate to `shortlisted`.
- `get_topic_candidate` confirmed `candidate_status=shortlisted` for `moon-sleeping:postpartum-survival`.

### 2026-07-06 Run 003: article-to-draft dry-run replay

| Field | Value |
|---|---|
| Mode | local fixture / dry-run replay; no live WeChat draft creation |
| Source | `packages/wechat-draft` offline test suite |
| Article artifact | Fixture `article_document` -> publish-ready artifact path covered by tests |
| Draft result | Dry-run / mocked adapter path only; no external publish/upload |
| Command | `rtk pnpm --filter @mcps/wechat-draft test` |
| Result | PASS: 67 passed |

Evidence:

- `WechatDraftService.importArticleMarkdown converts markdown to article_document` passed.
- `WechatDraftService.buildPublishReadyArtifact returns hermes upsert payload` passed.
- `WechatDraftService.createDraftFacade creates a draft from an existing publish_ready artifact` passed.
- `WechatDraftService.createDraftFacade builds, upserts, validates, and creates from article_document` passed.
- `DraftWorkflow creates a draft once and returns existing job for duplicate idempotency key` passed.
- No live WeChat draft, live upload, or publish action was performed.

## Findings

- 2026-07-01: 用户确认先投入使用选题和发草稿；完整写文章 feature 后置。
- 2026-07-01: 第一轮选题试用成功。当前链路已经能把一个真实候选写入生产 hermes-db、生成 TopicPlan，并进入 shortlisted 状态。下一步需要人工确认是否采用该选题进入草稿链路。
- 2026-07-01: 用户反馈 Run 001 作为测试选题可以接受，但实际运营上和四个公众号都不搭。结论：当前链路证明了 topic_plan 写入可用，但选题生成/筛选必须增加 account-fit gate，不能用泛 AI 基建题默认投给所有账号。
- 2026-07-01: Run 002 写入 `moon-sleeping/postpartum-survival` 后，用户进一步校准账号定位：`moon-sleeping` 是母婴类账号，尤其应补充宝宝 3-9 月期间辅食、哄睡等关注度大的话题。后续不应只按“夜间情绪/睡眠陪伴”生成。
- 2026-07-06: 草稿链路已完成可复放 dry-run replay，证明 `article_document -> publish_ready artifact -> create draft facade` 在离线测试路径闭合；live 草稿仍需人工确认和 `draft_target` 配置澄清后再执行。

## Account-Fit Gate

后续试用选题进入 `planned` 或草稿链路前，必须先判断是否匹配具体公众号定位：

- `after-work`: 下班成长、副业、技能升级、普通人可执行的行动方案。
- `micro-rain-spring`: 情绪韧性、关系、生活感受、温和陪伴。
- `moon-sleeping`: 母婴 / 孕产 / 产后陪伴 / 3-9 月宝宝照护。高关注话题包括辅食、哄睡、夜醒、作息、出牙、翻身/坐爬发育、喂养焦虑、妈妈情绪支持；避免泛睡眠号或泛情绪号定位。
- `smart-life`: 智能生活、工具使用、消费/效率场景。

泛 AI 基建、agent 内部架构、知识库工具选型类题目默认只允许作为链路测试，不进入实际发草稿。

### `moon-sleeping` Topic Pool Notes

`moon-sleeping` 不是泛睡眠/情绪号，实际应按母婴赛道生成选题。推荐优先覆盖：

| 子方向 | 适合的题目形态 |
|---|---|
| 3-9 月辅食 | 第一口辅食、米粉/泥糊、过敏观察、吃得少、辅食和奶量关系 |
| 哄睡 / 夜醒 | 抱睡、奶睡、落地醒、频繁夜醒、小睡短、白天睡太少 |
| 作息建立 | 3-9 月清醒窗口、睡前流程、黄昏闹、白天小睡安排 |
| 发育里程碑 | 翻身、坐、爬、出牙、抓握、分离焦虑 |
| 妈妈状态 | 产后疲惫、睡眠剥夺、喂养焦虑、被建议淹没后的自我稳定 |

选题口吻应“具体月龄 + 具体场景 + 温和解决”，不要抽象成泛知识或泛情绪鸡汤。

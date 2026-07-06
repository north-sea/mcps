# Account Config Audit: WeChat Topic / Draft Trial

**Workspace**: `wechat-topic-draft-trial`  
**Date**: 2026-07-01  
**Mode**: read-only audit of production hermes-db topic track config plus local agents account config.

---

## Summary

Current production hermes-db has four enabled public accounts and eight enabled topic tracks. The high-level account/track structure matches local agents config, but production track rows are thinner: `description` is empty for every track and several local keywords / negative keywords are not synced into hermes-db.

There is also one important product mismatch: production topic candidate account config still has `draft_target=youmind` for all four accounts, while the roadmap has recorded YouMind as no further investment. Before actual draft handoff, draft target semantics must be clarified.

## Production Accounts

| account_id | display_name | enabled | production draft_target | Audit |
|---|---|---:|---|---|
| `after-work` | 下班不躺平 | true | `youmind` | Track shape OK; needs richer fit rules |
| `micro-rain-spring` | 微雨成春 | true | `youmind` | Track shape OK; needs clearer emotional/growth boundary |
| `moon-sleeping` | 月亮睡了 | true | `youmind` | Must be treated as maternal/infant, not generic sleep/emotion |
| `smart-life` | 精明生活家 | true | `youmind` | Track shape OK; needs guard between AI/productivity and after-work skill topics |

## Track Audit

| Account | Track | Production Keywords | Gaps / Drift |
|---|---|---|---|
| `after-work` | `side-hustle-lab` | 副业, 变现, 赚钱, 接单, 自媒体, 下班 | Local config also includes 搞钱, 兼职, 个人IP. Description missing. |
| `after-work` | `skill-upgrade` | 技能, 职场, 跳槽, 作品集, 简历, AI工具 | Local config also includes AI, 人工智能, 就业, 裁员, 专业, 高考志愿 and sports/game negatives. The Run 001 test showed this track can admit generic AI infrastructure topics unless account-fit is stricter. |
| `micro-rain-spring` | `emotional-resilience` | 情绪, 内耗, 焦虑, 自我接纳, 松弛感, 关系 | Local config also includes 压力, 亲密关系, 情绪价值. Description missing. |
| `micro-rain-spring` | `gentle-growth` | 个人成长, 反内卷, 职场, 阅读, 复盘, 慢一点 | Local config also includes 大学生, 就业, 专业, 高考志愿 and stronger news/sports negatives. Needs guard from becoming generic career content. |
| `moon-sleeping` | `postpartum-survival` | 产后, 新手妈妈, 宝宝睡眠, 哺乳, 妈妈情绪, 育儿 | Local config also includes 孩子, 亲子, 宝妈 and extra negatives. User added 3-9 month baby topics: 辅食, 哄睡, 夜醒, 作息, 出牙, 翻身/坐爬发育, 喂养焦虑. These are not yet explicit in production keywords. |
| `moon-sleeping` | `pregnancy-night-talk` | 怀孕, 孕期, 产检, 胎动, 孕妈, 待产 | Local config also includes 备孕, 宝妈, 妈妈. Description missing. |
| `smart-life` | `minimalist-living` | 极简, 省钱, 消费, 收纳, 生活方式, 低成本 | Local config also includes 酒店, 退房, 性价比 and sports negatives. |
| `smart-life` | `productivity-systems` | 效率, 生产力, 自动化, AI工具, 复盘, 工作流 | Local config also includes AI, 人工智能, 工具, 数字化 and sports negatives. Needs guard from overlapping with `after-work/skill-upgrade`: smart-life should prefer systems, comparison, workflows, and practical household/work efficiency; after-work should prefer career leverage and earning ability. |

## Account-Fit Rules

| Account | Good Topics | Reject / Test-only Topics |
|---|---|---|
| `after-work` | 副业实验、技能变现、求职跳槽、作品集、AI 工具提升个人竞争力、打工人下班后可执行方案 | 母婴、泛情绪疗愈、纯工具架构、无职业/变现落点的 AI 基建 |
| `micro-rain-spring` | 情绪洞察、慢成长、反内卷、关系、自我接纳、温柔复盘、书和生活经验带来的心理支撑 | 暴富/带货、母婴育儿、强行动鸡血、纯职业攻略 |
| `moon-sleeping` | 母婴、孕期、产后、3-9 月宝宝照护、辅食、哄睡、夜醒、作息、出牙/发育、喂养焦虑、妈妈情绪支持 | 泛睡眠、泛情绪鸡汤、副业/投资/AI 工具、缺少月龄或母婴场景的内容 |
| `smart-life` | 系统化生活、效率工具、低成本生活、收纳/消费决策、AI/自动化用于日常与工作流优化 | 育儿、情绪陪伴、单纯职业焦虑、只讲赚钱/接单的副业内容 |

## Findings

1. **Production config is structurally complete but semantically thin.** Four accounts and eight tracks exist, but empty `description` fields mean topic planning must infer too much from sparse keywords.
2. **`moon-sleeping` needs immediate enrichment.** User clarified it should include high-attention 3-9 month baby topics such as complementary food and soothing to sleep. Current production keywords do not explicitly include 辅食, 哄睡, 夜醒, 作息, 出牙, 翻身/坐爬.
3. **AI/productivity overlap needs a split rule.** `after-work/skill-upgrade` and `smart-life/productivity-systems` both include AI/tooling; the former should map to career leverage, the latter to system/life/workflow efficiency.
4. **`draft_target=youmind` conflicts with roadmap direction.** This may be a stale field or still-needed bridge, but it cannot be ignored before draft handoff.
5. **Next topic trial should use account-specific gates before writing to production.** Run 001 proved write path, but editorial fit must be checked before draft trial.

## Recommended Follow-up

- Add descriptions / fit rules to production topic track config, or make the planning runtime load local agents account profiles before writing plans.
- For `moon-sleeping`, update `postpartum-survival` keywords with explicit 3-9 month baby care terms.
- Clarify whether `draft_target=youmind` is a stale config field, a temporary staging target, or should be replaced before T005 draft trial.
- Add account-fit validation to the topic planning prompt/runtime before auto-writing `planned` TopicPlans.

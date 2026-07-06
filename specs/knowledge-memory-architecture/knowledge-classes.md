# Knowledge Classes: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01

---

## Class Table

| Class | Examples | Source of Truth | Runtime Index | Sync Method | Retention | Deletion Gate Impact |
|---|---|---|---|---|---|---|
| Durable decision | 架构选型、迁移结论、删除门禁 | Markdown/Library/Git | Optional `hermes` summary | derived-summary | long-term | 删除 note skill 前必须可追溯 |
| Procedure / SOP | NAS deploy、nmem backup、Hermes fallback | Markdown/Library/Git | Optional `hermes` summary | derived-summary | long-term | 替代入口文档必须引用 |
| Source material | 平台规则、参考文章、长文档 | Library/Markdown/Git | none | future-pipeline | long-term | 不允许只存在 nmem |
| Bookmark inbox | 网页收藏、待读材料 | Karakeep | none | manual-import | archive | 不作为已迁移证据 |
| Hermes runtime memory | Hermes 运行偏好、跨领域经验 | NAS nmem `hermes` | NAS nmem `hermes` | export | runtime | 可辅助，但不能单独证明删除 |
| WeChat domain memory | 公众号账号偏好、内容复盘摘要 | WeChat/content space + Library summary | domain space | export/summary | runtime + long-term summary | 内容 skill 删除需有 route/evidence |
| Novel domain memory | 小说设定、风格、章节生产经验 | novel/book space + Library summary | domain space | export/summary | runtime + long-term summary | 小说 skill 删除需另有 novel contract |
| XHS domain memory | 小红书平台策略、封面/标签经验 | xhs space + Library summary | domain space | export/summary | runtime + long-term summary | 仍需用户确认是否正式业务线 |
| Codex session evidence | SDD specs、acceptance、verify logs | Git-tracked specs | none | none | long-term | 作为 roadmap 证据 |
| Fallback memory write | 超时写入待处理摘要 | fallback queue/log | none | manual-import | temporary | 不能长期堆积，需处理门禁 |

---

## Rules

- 来源材料不进 nmem 做唯一主库。
- domain memory 不强制合并到 `hermes`。
- `hermes` space 保存跨领域运行经验，不保存完整原始资料。
- Codex/Claude Code 产生的正式结论优先写 SDD 文档和 Git 文件，而不是 NAS nmem。
- 任何 fallback record 必须有 dedupe key，避免超时后重复写入。

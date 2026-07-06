# 能力对账：Agents 能力对账

**工作区**: `agents-capability-reconciliation`  
**创建日期**: 2026-06-28  
**状态**: 完整草稿  
**范围**: 只做能力对账；不迁移、不删除、不归档任何 note skill；不修改 agents 或 note 运行代码。

---

## 状态规则

| 状态 | 含义 |
|---|---|
| `verified` | 本地代码路径存在，且有测试、验收记录或 roadmap 完成证据；能力范围覆盖当前 skill 的触发语义。 |
| `partial` | 有可复用代码或 spec，但能力范围不完整、缺少 live smoke、缺少验收记录，或只覆盖 skill 的一部分。 |
| `absent` | 未发现可信的本地 app、package 或 spec 承接路径。 |
| `stale` | 旧 plan/spec 存在，但当前 app/package 现实或 roadmap 显示需要重新评估。 |
| `contradictory` | tasks、acceptance、roadmap 或源代码状态互相冲突。 |
| `not-applicable` | 候选落点是错误层级，例如把纯写作 runtime 误落到 MCP。 |
| `needs-user-decision` | 是否保留业务线、归属或价值无法从仓库证据推断，需要用户决策。 |

**证据优先规则**：`candidate` 和 `needs reconciliation` 不等于完成。没有本地证据路径时不能标记为 `verified`。模型写作、润色、审稿、标题改写等运行时能力不得用 MCP 契约替代执行层。

---

## 边界摘要

| 领域 | 执行归属 | 数据 / 契约归属 | 知识归属 | 薄入口 | 门禁 |
|---|---|---|---|---|---|
| 公众号 / 内容 | `agents/apps/wechat-agent`，以及 Hermes/Codex 写作 runtime | `mcps/packages/hermes-db`、`mcps/packages/wechat-draft` | Nowledge Library 保存来源和规则 | Codex/Claude skill 只做路由 | 内容类行必须有 owner 和 smoke 后才能删除旧入口 |
| 博客 | WeChat/content agent runtime，或薄路由到内容 workflow | 通常无；仅在需要 topic 存储时使用 | Library 保存来源和参考材料 | thin-skill | 不单独建设 blog MCP |
| 小说 | `agents/apps/novel-agent` | `mcps/packages/hermes-db` 的 novel tools | Library/Wiki 保存平台规则；Memory 保存萃取后的决策 | thin-skill | retrospective/handoff 仍在推进中 |
| 小红书 | 未验证；`agents/apps/xhs-agent` 只是骨架 | 暂无已知归属 | 若保留平台规则，则进入 Library | thin-skill | 投入前需要用户确认 |
| Hermes 个人运维 | Hermes/NAS runtime | mcps 仅承接稳定存储或工具契约 | Memory 保存决策和摘要 | WeChat/Hermes 薄入口 | 外部副作用必须有 smoke |
| note 工具 | 薄本地 skill 或后续归档 | 仅当稳定来源导入 / 配置契约存在时进入 Library/MCP | Library 保存来源索引 | thin-skill | 低价值本地工具需要用户决策 |

---

## 对账表

| Skill | 优先级 | 类别 | 来源路径 | 原候选落点 | 执行归属 | 数据 / 契约归属 | 知识归属 | 薄入口 | 能力状态 | 证据 | 证据缺口 | 建议动作 | 后续门禁 | 删除门禁状态 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `blog-optimizer` | P1 | 内容 / 博客 | `.agents/skills/blog-optimizer` | `apps/wechat-agent` / content pipeline | agents 内容 runtime | 无 | Library 保存源文章引用 | 是 | `partial` | `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/content-ops-service.ts`; `writer-service.ts` | 缺少博客专项 smoke | 改为薄路由 | `wechat-content-runtime-contracts` | 阻塞：等待旧文章样例 smoke | 模型生成保留在 runtime |
| `blog-series-optimizer` | P1 | 内容 / 博客 | `.agents/skills/blog-series-optimizer` | content pipeline | agents 内容 runtime | 无 | Library 保存系列索引 | 是 | `partial` | `apps/wechat-agent/src/app/content-ops-service.ts`; `packages/workflow-core/src/orchestrator.ts` | 缺少系列 workflow 证据 | 改为薄路由 | `wechat-content-runtime-contracts` | 阻塞：等待系列 smoke | 大概率复用 blog writer/reviewer |
| `blog-topic-advisor` | P1 | 内容 / 博客 | `.agents/skills/blog-topic-advisor` | topic workflow | agents topic/content runtime | `packages/hermes-db/src/hermes_db_mcp/tools/topics.py` | Library 保存调研输入 | 是 | `partial` | `apps/wechat-agent/src/app/topic-service.ts`; `topic-radar-service.ts`; `tools/topics.py` | 博客专项 topic intake 未证明 | 拆分归属 | `wechat-content-runtime-contracts`; `knowledge-library-ingestion-plan` | 阻塞：等待 shortlist smoke | 调研来源不要进入 Memory |
| `blog-workflow` | P1 | 内容 / 博客 | `.agents/skills/blog-workflow` | content app router | 薄路由到 agents | 无 | Library 保存引用 | 是 | `partial` | `apps/wechat-agent/src/app/content-ops-service.ts`; `apps/wechat-agent/src/cli/index.ts` | 缺少 blog 聚合命令证据 | 改为薄路由 | `wechat-content-runtime-contracts` | 阻塞：等待路由文档 | 应只保留路由职责 |
| `blog-writer` | P1 | 内容 / 博客 | `.agents/skills/blog-writer` | content writer pipeline | agents/Codex runtime | 无 | Library 保存来源引用 | 是 | `partial` | `apps/wechat-agent/src/app/writer-service.ts`; `packages/adapters/src/llm/index.ts` | 缺少博客专项 fixture | 改为薄路由 | `wechat-content-runtime-contracts` | 阻塞：等待单篇文章 smoke | prompt/model 留在 runtime |
| `content-ops` | P0 | 内容 / 共享底座 | `.agents/skills/content-ops` | `packages/workflow-core`, `packages/style-anchor` | agents 共享包 | 可能承接 workflow/artifact 契约 | Memory 仅保存决策 | 否 | `partial` | `packages/workflow-core/src/index.ts`; `packages/workflow-core/src/gates.ts`; `packages/style-anchor/src/index.ts` | caller 覆盖尚未完整映射 | 复用 | `wechat-content-runtime-contracts` | 阻塞：等待调用方对账 | 高复用底座 |
| `content-reviewer` | P1 | 内容 / 质量 | `.agents/skills/content-reviewer` | review gate/style package | agents/Codex runtime | 无 | 可复用 style docs | 是 | `partial` | `packages/workflow-core/src/gates.ts`; `packages/style-anchor/src/index.ts`; `packages/adapters/src/llm/index.ts` | 缺少 review smoke | 改为薄路由 | `wechat-content-runtime-contracts` | 阻塞：等待 review 样例 | 模型相关能力强 |
| `gemini-image-provider` | P2 | 内容 / 图片 provider | `.agents/skills/gemini-image-provider` | image provider adapter | agents 图片 adapter/runtime | 仅 asset upload contract | 无 | 是 | `partial` | `packages/adapters/src/image/provider.ts`; `packages/adapters/src/image/index.ts` | provider 凭据 / live call 未验证 | credential-gated 可选增强 | `wechat-content-runtime-contracts` | 不阻塞：fixture / dry-run 必测，live smoke 可选 | 可排在 imagegen 之后 |
| `opencli-integration` | P0 | 内容 / 数据源 | `.agents/skills/opencli-integration` | adapters package | agents adapters | 无 | 无 | 是 | `partial` | `packages/adapters/src/web-search/index.ts`; `exa.ts`; `jina.ts`; `topic-radar/index.ts` | OpenCLI 专项 adapter 未证明 | 补缺口 | `wechat-content-runtime-contracts`; `novel-runtime-contracts` | 阻塞：等待平台 adapter smoke | 共享依赖 |
| `topic-radar` | P0 | 内容 / 公众号 | `.agents/skills/topic-radar` | wechat topic radar + hermes-db topic tools | `agents/apps/wechat-agent` | `packages/hermes-db/src/hermes_db_mcp/tools/topics.py` | Library 保存调研引用 | 是 | `verified` | `apps/wechat-agent/src/app/topic-radar-service.ts`; `tests/topic-radar-shortlist.test.ts`; `specs/agents-roadmap/roadmap.md` completion log for `wechat-topic-radar-online` | 本 feature 未重新检查 live availability | 复用 | `wechat-content-runtime-contracts` | 阻塞：等待替代路由文档 | 本地证据强 |
| `wechat-article-pipeline` | P0 | 内容 / 公众号 | `.agents/skills/wechat-article-pipeline` | `apps/wechat-agent`, `packages/wechat-draft`, hermes-db artifacts | `agents/apps/wechat-agent` | `packages/wechat-draft`, `packages/hermes-db` artifacts/articles | Library 保存引用 | 是 | `partial` | `apps/wechat-agent/src/workflows/wechat/runtime.ts`; `packages/wechat-draft/src/workflow/DraftWorkflow.ts`; `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py`; `wechat_articles.py` | 尚未在此记录端到端替代路由 | 拆分归属 | `wechat-content-runtime-contracts` | 阻塞：等待 E2E 路由和草稿 smoke | 执行 / 数据边界清晰 |
| `wechat-cover` | P1 | 内容 / 公众号图片 | `.agents/skills/wechat-cover` | image workflow + asset upload | agents 图片 runtime | `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | 无 | 是 | `partial` | `packages/adapters/src/image/manifest.ts`; `packages/wechat-draft/src/service/WechatDraftService.uploadAsset.test.ts` | 缺少封面 dry-run / fixture smoke | 补缺口 | `wechat-content-runtime-contracts` | 阻塞：等待封面 + 上传 dry-run smoke | MCP 只承接 asset contract |
| `wechat-illustration` | P1 | 内容 / 公众号图片 | `.agents/skills/wechat-illustration` | image workflow + asset upload | agents 图片 runtime | `packages/wechat-draft` asset upload | 无 | 是 | `partial` | `packages/adapters/src/image/index.ts`; `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | 缺少插图插入 dry-run / fixture smoke | 补缺口 | `wechat-content-runtime-contracts` | 阻塞：等待插图插入 dry-run smoke | 与 image generator 配套 |
| `wechat-image-generator` | P1 | 内容 / 公众号图片 | `.agents/skills/wechat-image-generator` | image orchestration + asset manifest | agents 图片 runtime | asset manifest/storage contract | 无 | 是 | `partial` | `packages/adapters/src/image/manifest.ts`; `packages/adapters/src/image/transform.ts`; `packages/wechat-draft/src/wechat/AssetSourceLoader.test.ts` | 缺少 provider orchestration dry-run / fixture smoke | 拆分归属 | `wechat-content-runtime-contracts` | 阻塞：等待 manifest schema + dry-run provider orchestration；live provider 可选 | source note tree 有 dirty 文件 |
| `wechat-writer` | P0 | 内容 / 公众号 | `.agents/skills/wechat-writer` | `apps/wechat-agent`, draft facade consumes artifact | agents/Codex runtime | `packages/wechat-draft` 消费 publish-ready artifact | Library 保存引用 | 是 | `partial` | `apps/wechat-agent/src/app/writer-service.ts`; `packages/wechat-draft/src/render/MarkdownArticleImporter.ts`; `ArticleDocumentToWechatArtifactBuilder.ts` | generation-to-draft handoff smoke 未在此捕获 | 拆分归属 | `wechat-content-runtime-contracts` | 阻塞：等待文章生成 smoke | MCP 不承接写作 runtime |
| `youmind-publisher` | P2 | 内容 / 发布 | `.agents/skills/youmind-publisher` | publishing adapter | 不再投入 | 无 | 无 | 是 | `stale` | `packages/adapters/src/publish/index.ts`; 用户确认 YouMind 后续不会使用 | 无需补 YouMind live upload | 后续归档 | `note-thin-shell-and-archive` | 阻塞：等待归档批次处理 | 不再作为内容发布目标 |
| `content-brainstorm` | P1 | 内容 / 公众号 | `.hermes/skills/content-brainstorm` | content ideation runtime | Hermes/Codex runtime | 可选 topic storage | Memory 仅保存决策 | 是 | `partial` | `apps/wechat-agent/src/app/topic-suggestion-service.ts`; `topic-service.ts` | Hermes 薄入口未实现 | 改为薄路由 | `wechat-content-runtime-contracts` | 阻塞：等待 brainstorm handoff route | 对话优先 |
| `topic-inbox` | P0 | 内容 / 公众号 | `.hermes/skills/topic-inbox` | topic workflow + hermes-db bucket | Hermes runtime | `packages/hermes-db/src/hermes_db_mcp/tools/topics.py` | Memory 可选保存决策 | 是 | `partial` | `tools/topics.py`; `repositories/topic_repo.py`; `apps/wechat-agent/src/app/topic-service.ts` | WeChat/Hermes entry smoke 缺失 | 拆分归属 | `wechat-content-runtime-contracts` | 阻塞：等待 inbox-to-storage smoke | 被动捕获 |
| `topic-scout` | P0 | 内容 / 公众号 | `.hermes/skills/topic-scout` | topic radar workflow + storage | Hermes/agents topic runtime | `packages/hermes-db` topics | Library 保存调研引用 | 是 | `partial` | `apps/wechat-agent/src/app/topic-radar-service.ts`; `packages/adapters/src/web-search/index.ts`; `tools/topics.py` | adoption-to-inbox smoke 缺失 | 拆分归属 | `wechat-content-runtime-contracts` | 阻塞：等待 scout + adopt smoke | 与 topic-radar 重叠 |
| `novel-analyzer` | P1 | 小说 | `.agents/skills/novel-analyzer` | `apps/novel-agent` | `agents/apps/novel-agent` | 可选 hermes-db novel tools | Library 保存分析产物 | 是 | `verified` | `apps/novel-agent/src/app/txt-analysis-orchestrator.ts`; `tests/txt-analysis-orchestrator.test.ts`; agents roadmap `novel-agent-txt-analysis-mvp` PASS | NotebookLM/Library handoff 未决 | 复用 | `novel-runtime-contracts` | 阻塞：等待薄路由文档 | analyzer 证据强 |
| `novel-memory-workflow` | P1 | 小说 | `.agents/skills/novel-memory-workflow` | novel memory workflow + hermes-db state | novel-agent runtime | `packages/hermes-db` novel tools | Memory 保存萃取决策 | 是 | `partial` | `packages/hermes-db/src/hermes_db_mcp/tools/novel_books.py`; `novel_reports.py`; `apps/novel-agent/src/retrospective/orchestrator.ts` | Memory 双写路由缺失 | 拆分归属 | `novel-runtime-contracts` | 阻塞：等待 memory/storage policy | 原始材料不要进 Memory |
| `novel-platform-rules` | P2 | 小说 | `.agents/skills/novel-platform-rules` | novel agent reference | 无 | 无 | Library/Wiki | 是 | `not-applicable` | 不需要执行路径；矩阵已判定规则事实来源 | Library 目标页尚未创建 | 转 Library | `knowledge-library-ingestion-plan` | 阻塞：等待 Library page/search route | 规则事实属于 Library |
| `novel-trend-scout` | P1 | 小说 | `.agents/skills/novel-trend-scout` | novel trend module | agents adapter/runtime | 无 | Library 保存采样来源 | 是 | `partial` | `packages/adapters/src/web-search/index.ts`; `apps/novel-agent` exists | 未找到 trend 专项 module | 补缺口 | `novel-runtime-contracts` | 阻塞：等待 trend scout smoke | 外部平台风险 |
| `novel-workflow` | P1 | 小说 | `.agents/skills/novel-workflow` | `apps/novel-agent` | `agents/apps/novel-agent` | 按需使用 mcps novel contracts | Library/Memory 拆分 | 是 | `partial` | `apps/novel-agent/src/cli/index.ts`; `src/planning/orchestrator.ts`; `src/production/orchestrator.ts` | 聚合薄路由未文档化 | 改为薄路由 | `novel-runtime-contracts` | 阻塞：等待 route map | 应只做路由 |
| `novelist` | P1 | 小说 | `.agents/skills/novelist` | novel chapter production | `agents/apps/novel-agent` | hermes-db novel state/artifact contracts | Memory 保存决策 | 是 | `verified` | `apps/novel-agent/src/production/orchestrator.ts`; `src/production/actors/draft-actor.ts`; `specs/agents-roadmap/roadmap.md` `novel-agent-chapter-production` PASS | 缺少薄 skill 路由 | 复用 | `novel-runtime-contracts` | 阻塞：等待替代路由文档 | 写作留在 agent runtime |
| `plot-insertion-router` | P2 | 小说 | `.agents/skills/plot-insertion-router` | novel planning workflow + project state | `agents/apps/novel-agent` planning | `packages/hermes-db/src/hermes_db_mcp/tools/novel_planning.py` | Memory 可选 | 是 | `partial` | `apps/novel-agent/src/planning/orchestrator.ts`; `packages/hermes-db/src/hermes_db_mcp/tools/novel_planning.py` | 缺少插入专项 writeback gate | 补缺口 | `novel-runtime-contracts` | 阻塞：等待人工确认的 writeback smoke | 有写入副作用 |
| `qidian-scraper` | P2 | 小说 | `.agents/skills/qidian-scraper` | adapters package | agents adapter/runtime | 无 | 若合法则 Library 保存捕获来源 | 是 | `absent` | 仅有通用 web-search adapters，未发现 qidian scraper 路径 | 合规、登录、smoke 未知 | 重写 | `novel-runtime-contracts` | 阻塞：等待用户 / 法务决策 + smoke | 平台风险高 |
| `novel-capture` | P1 | 小说 | `.hermes/skills/novel-capture` | novel memory workflow | Hermes + novel-agent runtime | 可选 hermes-db novel tools | Memory 保存萃取决策 | 是 | `partial` | `apps/novel-agent/src/retrospective/orchestrator.ts`; `packages/hermes-db/src/hermes_db_mcp/tools/novel_reports.py` | Hermes capture entry 缺失 | 拆分归属 | `novel-runtime-contracts` | 阻塞：等待 capture route + no-write mode | brainstorm 模式不得自动持久化 |
| `novel-rules-ask` | P2 | 小说 | `.hermes/skills/novel-rules-ask` | thin QA wrapper | 无 | 无 | Library/Wiki | 是 | `not-applicable` | rule QA 应消费 Library，不需要执行层 | Library page 未创建 | 转 Library | `knowledge-library-ingestion-plan` | 阻塞：等待 Library retrieval smoke | 与 platform rules 合并 |
| `xhs-creator` | P2 | 小红书 | `.agents/skills/xhs-creator` | `apps/xhs-agent` skeleton | 未验证 | 无 | 若保留规则则进入 Library | 是 | `needs-user-decision` | `apps/xhs-agent/src/index.ts` placeholder from explorer finding | 业务线未确认；无 workflow tests | 需要用户决策 | `xhs-workflow-definition` | 阻塞：等待用户确认 XHS 范围 | 默认不投入 |
| `daily-capture` | P2 | Hermes 个人运维 | `.hermes/skills/daily-capture` | none / event storage | Hermes runtime | 未来可能有 event schema | Memory 保存萃取后的每日决策 | 是 | `absent` | 未发现 agents 路径；未发现 mcps daily event contract | WeChat entry/storage schema 缺失 | 补缺口 | `hermes-personal-ops-migration` | 阻塞：等待 storage + entry smoke | 个人自动化 |
| `goal-setting` | P2 | Hermes 个人运维 | `.hermes/skills/goal-setting` | possible OKR/event schema | Hermes runtime | 未来可能有 OKR contract | Memory 保存决策 | 是 | `absent` | 未发现本地 OKR schema/tool | owner 和 schema 缺失 | 补缺口 | `hermes-personal-ops-migration` | 阻塞：等待 OKR contract decision | 关联 period digest |
| `link-inbox` | P2 | Hermes 个人运维 | `.hermes/skills/link-inbox` | Karakeep adapter | Hermes runtime | 未来可能有 Karakeep MCP | Memory 不保存原始 links | 是 | `absent` | `mcps/packages` 未发现本地 Karakeep adapter | 外部写入 smoke 缺失 | 补缺口 | `hermes-personal-ops-migration` | 阻塞：等待 Karakeep save smoke | 外部写入 |
| `media-download` | P3 | Hermes 个人运维 | `.hermes/skills/media-download` | 无 | Hermes/NAS runtime | 无 | 无 | 是 | `needs-user-decision` | 未发现本地安全 adapter | 高副作用策略缺失 | 需要用户决策 | `hermes-personal-ops-migration` | 阻塞：等待 NAS confirmation flow | 不能直接薄删除 |
| `nas-ops` | P2 | Hermes 个人运维 | `.hermes/skills/nas-ops` | possible ops MCP | Hermes/NAS runtime | 可能进入 ops MCP | 无 | 是 | `partial` | 环境中存在 `nas-service-deploy` / `hermes-nas-ssh-ops` skill，但不是本 roadmap 的 feature artifact | 直接替代路由不属于本 roadmap | 改为薄路由 | `hermes-personal-ops-migration` | 阻塞：等待读取状态 smoke | 与 deploy ops 分开 |
| `period-digest` | P2 | Hermes 个人运维 | `.hermes/skills/period-digest` | event/OKR storage | Hermes runtime | 未来可能有 event/OKR storage | Memory 保存摘要 | 是 | `absent` | 未发现本地 period digest contract | 依赖 daily-capture/goal-setting | 补缺口 | `hermes-personal-ops-migration` | 阻塞：等待输入数据 contract | 依赖上游个人运维 |
| `account-config` | P0 | note 工具 / 配置 | `.agents/skills/account-config` | `packages/config`, config contracts | agents config package | 可选 mcps config contract | 无 | 是 | `partial` | `packages/config/src/index.ts`; `packages/config/src/wechat/index.ts`; `packages/config/src/env/index.test.ts` | caller 迁移图不完整 | 复用 | `wechat-content-runtime-contracts` | 阻塞：等待调用方对账 | 共享依赖 |
| `acp-note-taker` | P3 | note 工具 / 学习 | `.agents/skills/acp-note-taker` | 无 | 薄本地 skill | 无 | 若保留课程笔记则进入 Library | 是 | `needs-user-decision` | 未发现 agents/mcps 候选 | 用户保留价值未知 | 需要用户决策 | `note-thin-shell-and-archive` | 阻塞：等待用户决策 | 大概率在迁移主线外 |
| `notion-media-orchestrator` | P2 | note 工具 / Notion 编排 | `.agents/skills/notion-media-orchestrator` | content orchestration | 不再投入 | 无 | 无 | 是 | `stale` | 用户确认 Notion 已不再使用 | 无需补 Notion workflow | 后续归档 | `note-thin-shell-and-archive` | 阻塞：等待归档批次处理 | 不再作为内容链路范围 |
| `repo-bootstrap` | P3 | note 工具 | `.agents/skills/repo-bootstrap` | 无 | 薄本地工具 | 无 | 无 | 是 | `needs-user-decision` | 未发现 agents/mcps 候选 | 保留价值未知 | 后续归档 | `note-thin-shell-and-archive` | 阻塞：等待替代 / 保留说明 | 大概率是本地 utility |
| `source-import` | P1 | note 工具 / 来源索引 | `.agents/skills/source-import` | Library import | 薄导入路由 | 可能有 Library ingestion contract | Library | 是 | `partial` | roadmap 有 `knowledge-library-ingestion-plan`；尚无具体 import manifest | Library metadata/import smoke 缺失 | 转 Library | `knowledge-library-ingestion-plan` | 阻塞：等待 import manifest + smoke | 来源材料不进 Memory |
| `workspace-repair` | P3 | note 工具 | `.agents/skills/workspace-repair` | 无 | 薄本地工具 | 无 | 无 | 是 | `needs-user-decision` | 未发现 agents/mcps 候选 | 是否仍需要未知 | 后续归档 | `note-thin-shell-and-archive` | 阻塞：等待用户决策 | 大概率是本地修复工具 |
| `monthly-review` | P1 | 质量 / 文风 | `.agents/skills/monthly-review` | analytics/retrospective specs + hermes-db analytics | WeChat content runtime 的内容表现复盘 | hermes-db analytics | Memory 只保存决策 | 是 | `partial` | `apps/wechat-agent/src/app/retrospective-report-service.ts`; `analytics-import-service.ts`; `packages/hermes-db/src/hermes_db_mcp/tools/wechat_analytics.py`; 用户确认归属建议 | 缺少内容月报样例报告 | 复用并收窄范围 | `wechat-content-runtime-contracts` | 阻塞：等待公众号 / 内容表现月报样例 | 个人月报留给 `hermes-personal-ops-migration` |
| `style-analyzer` | P1 | 质量 / 文风 | `.agents/skills/style-analyzer` | `packages/style-anchor`, style profile storage | agents style package/runtime | 未来可能有 style storage | Library 保存样例 | 是 | `partial` | `packages/style-anchor/src/index.ts`; `apps/novel-agent/src/app/style-profile-service.ts` | 跨领域 style storage contract 缺失 | 拆分归属 | `wechat-content-runtime-contracts`; `novel-runtime-contracts` | 阻塞：等待 style profile smoke | 内容 / 小说共享能力 |

---

## 后续门禁

| Feature | 就绪度 | 必需覆盖行 | 阻塞缺口 | 建议下一阶段 |
|---|---|---|---|---|
| `wechat-content-runtime-contracts` | tasks complete | content/blog/WeChat/topic/style/image 的 P0/P1 行 | 替代路由文档、文章生成到草稿的 smoke、图片 dry-run/provider 可选 live smoke、调用方对账 | execute-plan |
| `knowledge-library-ingestion-plan` | 有条件就绪 | `source-import`、`blog-topic-advisor`、`novel-platform-rules`、`novel-rules-ask`、来源 / 参考资料相关行 | Library metadata 和 import smoke 缺失 | specify |
| `novel-runtime-contracts` | 有条件就绪 | novel P1/P2 行 | retrospective/handoff 未完成、trend/qidian 缺口、capture route 缺失 | specify |
| `xhs-workflow-definition` | 阻塞 | `xhs-creator` | 用户尚未确认 XHS 是否保留为正式业务线；app 只是骨架 | ideate |
| `hermes-personal-ops-migration` | 有条件就绪 | daily/goal/link/media/nas/period 行 | 多个契约缺失，且高外部副作用需要 smoke 或确认 | specify |
| `note-thin-shell-and-archive` | 阻塞 | 全部行 | 每个旧 skill 都必须先具备替代路径和 smoke 证据，之后才能删除 | 上游门禁完成后进入 plan |

---

## 数量校验

| 检查项 | 数值 |
|---|---:|
| 来源矩阵行数 | 44 |
| 对账表行数 | 44 |
| 空状态行 | 0 |
| 空删除门禁行 | 0 |

## 当前已知缺口

- 本 feature 只验证本地证据路径和决策边界，不对外部服务执行 live smoke。
- 多行仍为 `partial` 或 `needs-user-decision`；这些是后续门禁，不阻塞本次对账交付。
- 在后续 feature 补齐替代路径和 smoke 证据前，不应删除、移动或归档任何 note skill。

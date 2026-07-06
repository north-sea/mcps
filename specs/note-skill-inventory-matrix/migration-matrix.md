# Note Skill Migration Matrix

**Workspace**: `note-skill-inventory-matrix`  
**Created**: 2026-06-27  
**Status**: Draft inventory  
**Scope**: 只盘点和标注候选归属；不迁移、不删除、不归档。

## Inventory Summary

| Source | Count |
|---|---:|
| `/Users/yqg/learning/biji/note/.agents/skills` | 33 |
| `/Users/yqg/learning/biji/note/.hermes/skills` | 11 |
| Total | 44 |

## Matrix

| Skill | 当前路径 | 类别 | 当前触发条件 | 是否模型生成 | 是否 NAS 依赖 | agents 既有落点 | mcps 既有落点 | 目标归属 | 优先级 | 删除门禁 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `blog-optimizer` | `.agents/skills/blog-optimizer` | 内容 / 博客 | 明确优化旧博客文章 | 是 | 否 | candidate: `apps/wechat-agent` / content pipeline, needs reconciliation | none known | agents + thin-skill | P1 | 替代 blog 优化入口、样例旧文 smoke、README 指针 | 模型写作能力不进 MCP |
| `blog-series-optimizer` | `.agents/skills/blog-series-optimizer` | 内容 / 博客 | 优化或恢复博客系列 | 是 | 否 | candidate: content pipeline, needs reconciliation | none known | agents + thin-skill | P1 | 系列扫描/优化 smoke、索引产物对照、README 指针 | 复用 blog-optimizer/blog-writer/content-reviewer |
| `blog-topic-advisor` | `.agents/skills/blog-topic-advisor` | 内容 / 博客 | 规划博客选题或系列主题 | 是 | 否 | candidate: topic workflow, needs reconciliation | possible topic storage, needs reconciliation | agents + nowledge-library + thin-skill | P1 | 选题 shortlist smoke、资料落点说明、README 指针 | 联网调研规则需后续对账 |
| `blog-workflow` | `.agents/skills/blog-workflow` | 内容 / 博客 | 博客综合任务总入口 | 是 | 否 | candidate: content app router, needs reconciliation | none known | thin-skill + agents | P1 | 新路由入口可覆盖 blog 子任务、README 指针 | 应变成薄入口 |
| `blog-writer` | `.agents/skills/blog-writer` | 内容 / 博客 | 明确写单篇博客 | 是 | 否 | candidate: content writer pipeline, needs reconciliation | none known | agents + thin-skill | P1 | 单篇生成 smoke、风格档案加载证据、README 指针 | 写作生成留 runtime |
| `content-ops` | `.agents/skills/content-ops` | 内容 / 共享底座 | 被内容类 skill 调用的共享流程 | 是 | 否 | candidate: `packages/workflow-core`, `packages/style-anchor`, needs reconciliation | possible artifact/status contracts, needs reconciliation | agents + mcp | P0 | 共享流程替代库、调用方对账、测试证据 | 高复用底座，不能直接删除 |
| `content-reviewer` | `.agents/skills/content-reviewer` | 内容 / 质量 | 润色、审查、去 AI 味 | 是 | 否 | candidate: review gate/style package, needs reconciliation | none known | agents + thin-skill | P1 | 审稿 smoke、风格输入证据、README 指针 | 模型强相关 |
| `gemini-image-provider` | `.agents/skills/gemini-image-provider` | 内容 / 图片 provider | Gemini 生图 provider 被调用 | 是 | 否 | candidate: image provider adapter, needs reconciliation | none known | agents + thin-skill | P2 | 新 provider 调用 smoke、凭证/权限说明、README 指针 | 可能被 imagegen skill 或服务替代 |
| `opencli-integration` | `.agents/skills/opencli-integration` | 内容 / 数据源 | 被 topic-radar/novel/xhs 引用抓平台数据 | 否 | 否 | candidate: adapters package, needs reconciliation | none known | agents + thin-skill | P0 | 平台数据 adapter smoke、调用方迁移清单、README 指针 | 共享依赖，先对账 |
| `topic-radar` | `.agents/skills/topic-radar` | 内容 / 公众号 | 联网找热点和选题 | 是 | 否 | candidate: wechat topic radar specs, needs reconciliation | candidate: hermes-db topic/artifact tools, needs reconciliation | agents + mcp + thin-skill | P0 | 选题入池 smoke、topic storage 证据、README 指针 | P0 内容线 |
| `wechat-article-pipeline` | `.agents/skills/wechat-article-pipeline` | 内容 / 公众号 | 选题到发布完整生产线 | 是 | 可能 | candidate: `apps/wechat-agent`, needs reconciliation | candidate: `packages/wechat-draft`, hermes-db artifacts | agents + mcp + thin-skill | P0 | 端到端替代入口、draft facade smoke、README 指针 | 不在 mcps 重做业务流程 |
| `wechat-cover` | `.agents/skills/wechat-cover` | 内容 / 公众号图片 | 生成无文字封面图 | 是 | 否 | candidate: image workflow, needs reconciliation | candidate: asset preflight/upload only | agents + thin-skill | P1 | 封面生成 smoke、资产上传 smoke、README 指针 | MCP 只管资产契约 |
| `wechat-illustration` | `.agents/skills/wechat-illustration` | 内容 / 公众号图片 | 生成文中插图 | 是 | 否 | candidate: image workflow, needs reconciliation | candidate: asset preflight/upload only | agents + thin-skill | P1 | 插图生成/插入 smoke、README 指针 | 与 wechat-image-generator 对账 |
| `wechat-image-generator` | `.agents/skills/wechat-image-generator` | 内容 / 公众号图片 | 公众号配图编排底层 | 是 | 否 | candidate: image orchestration package, needs reconciliation | candidate: asset manifest/storage contract, needs reconciliation | agents + mcp + thin-skill | P1 | image manifest schema、provider smoke、README 指针 | 底层编排，应先抽契约 |
| `wechat-writer` | `.agents/skills/wechat-writer` | 内容 / 公众号 | 起草公众号文章 | 是 | 否 | candidate: `apps/wechat-agent`, needs reconciliation | candidate: draft facade consumes publish-ready artifact | agents + thin-skill | P0 | 文章生成 smoke、publish-ready handoff、README 指针 | 写作生成留 agent/runtime |
| `youmind-publisher` | `.agents/skills/youmind-publisher` | 内容 / 发布 | 上传公众号 Markdown 到 YouMind board | 否 | 否 | candidate: publishing adapter, needs reconciliation | none known | agents + thin-skill | P2 | YouMind 上传 smoke、远程 URL 图片验证、README 指针 | 外部发布副作用需门禁 |
| `content-brainstorm` | `.hermes/skills/content-brainstorm` | 内容 / 公众号 | 对话式选题脑暴 | 是 | 否 | candidate: content ideation runtime, needs reconciliation | none known | hermes-agent + thin-skill | P1 | Hermes 入口可用、topic handoff 证据、README 指针 | 纯对话，不落盘 |
| `topic-inbox` | `.hermes/skills/topic-inbox` | 内容 / 公众号 | 快速记录公众号选题灵感 | 否 | 可能 | candidate: topic workflow, needs reconciliation | candidate: hermes-db topic bucket, needs reconciliation | hermes-agent + mcp + thin-skill | P0 | 入池 smoke、存储路径证据、README 指针 | 被动入口 |
| `topic-scout` | `.hermes/skills/topic-scout` | 内容 / 公众号 | 主动联网调研选题候选 | 是 | 否 | candidate: topic radar workflow, needs reconciliation | candidate: topic storage | hermes-agent + agents + mcp | P0 | 联网调研 smoke、采纳后入池证据、README 指针 | 与 topic-radar 合并评估 |
| `novel-analyzer` | `.agents/skills/novel-analyzer` | 小说 | 分析小说并生成写作规则 | 是 | 否 | candidate: `apps/novel-agent`, needs reconciliation | possible Library artifact storage, needs reconciliation | agents + nowledge-library + thin-skill | P1 | 分析样例 smoke、规则产物落点、README 指针 | NotebookLM/Library 边界待定 |
| `novel-memory-workflow` | `.agents/skills/novel-memory-workflow` | 小说 | 小说项目长期灵感和知识沉淀 | 是 | 否 | candidate: novel memory workflow, needs reconciliation | candidate: hermes-db state/memory contracts | agents + mcp + memory | P1 | 双写替代路径、检索 smoke、README 指针 | Memory 只放决策/提炼 |
| `novel-platform-rules` | `.agents/skills/novel-platform-rules` | 小说 | 网文平台规则事实源 | 否 | 否 | candidate: novel agent reference, needs reconciliation | none known | nowledge-library + thin-skill | P2 | Library/Wiki 规则页、检索入口、README 指针 | 只读规则适合资料库 |
| `novel-trend-scout` | `.agents/skills/novel-trend-scout` | 小说 | 扫榜和趋势分析 | 是 | 否 | candidate: novel-agent trend module, needs reconciliation | none known | agents + thin-skill | P1 | 榜单采样 smoke、趋势报告样例、README 指针 | 依赖外部平台数据 |
| `novel-workflow` | `.agents/skills/novel-workflow` | 小说 | 小说综合任务总入口 | 是 | 否 | candidate: `apps/novel-agent`, needs reconciliation | none known | thin-skill + agents | P1 | 新路由入口覆盖子任务、README 指针 | 应变成薄入口 |
| `novelist` | `.agents/skills/novelist` | 小说 | 小说写作、续写、扩写、审稿 | 是 | 否 | candidate: novel chapter production, needs reconciliation | candidate: state/artifact contracts | agents + mcp + thin-skill | P1 | 章节生产 smoke、状态写入证据、README 指针 | 写作生成留 agent |
| `plot-insertion-router` | `.agents/skills/plot-insertion-router` | 小说 | 判断情节点插入位置并回写大纲 | 是 | 否 | candidate: novel planning workflow, needs reconciliation | candidate: project state contract | agents + mcp + thin-skill | P2 | 插入建议 smoke、确认后写入门禁、README 指针 | 有写盘副作用，需确认 gate |
| `qidian-scraper` | `.agents/skills/qidian-scraper` | 小说 | 下载起点小说章节和段评 | 否 | 否 | candidate: adapters package, needs reconciliation | none known | agents + thin-skill | P2 | 抓取 smoke、合规/登录边界说明、README 指针 | 外部平台风险高 |
| `novel-capture` | `.hermes/skills/novel-capture` | 小说 | 小说灵感快速捕获与情节讨论 | 是 | 否 | candidate: novel-agent memory workflow, needs reconciliation | candidate: memory/state storage | hermes-agent + agents + memory | P1 | 捕获双写 smoke、脑暴模式不落盘验证、README 指针 | 与 novel-memory-workflow 对账 |
| `novel-rules-ask` | `.hermes/skills/novel-rules-ask` | 小说 | 微信问网文平台规则 | 否 | 否 | candidate: thin QA wrapper, needs reconciliation | none known | nowledge-library + thin-skill | P2 | Library 检索入口、问答 smoke、README 指针 | 可合并到 rules fact source |
| `xhs-creator` | `.agents/skills/xhs-creator` | 小红书 | 小红书图文内容创作 | 是 | 否 | candidate: `apps/xhs-agent` skeleton, needs reconciliation | none known | agents + thin-skill | P2 | 用户确认业务线、图文生成 smoke、README 指针 | 是否继续投入待确认 |
| `daily-capture` | `.hermes/skills/daily-capture` | Hermes 个人运维 | 每晚日记采集 | 是 | 否 | none known | possible hermes-db event storage, needs reconciliation | hermes-agent + mcp + memory | P2 | 微信入口 smoke、DailyTasks 写入证据、README 指针 | 个人自动化线 |
| `goal-setting` | `.hermes/skills/goal-setting` | Hermes 个人运维 | OKR 目标设定和调整 | 是 | 否 | none known | possible OKR/event schema, needs reconciliation | hermes-agent + mcp + memory | P2 | OKR 产物 smoke、事件-KR 映射证据、README 指针 | 和 period-digest 相关 |
| `link-inbox` | `.hermes/skills/link-inbox` | Hermes 个人运维 | 微信发链接收藏到 Karakeep | 否 | 可能 | none known | possible Karakeep adapter, needs reconciliation | hermes-agent + mcp | P2 | Karakeep 保存 smoke、标签规则、README 指针 | 外部写入副作用 |
| `media-download` | `.hermes/skills/media-download` | Hermes 个人运维 | 搜 BT 并下载到 NAS | 否 | 是 | none known | none known | hermes-agent | P3 | NAS 下载 smoke、目录权限、确认交互、README 指针 | 高副作用，不能薄删 |
| `nas-ops` | `.hermes/skills/nas-ops` | Hermes 个人运维 | 查询 NAS 服务/磁盘/容器状态 | 否 | 是 | none known | possible ops MCP, needs reconciliation | hermes-agent + mcp | P2 | NAS status smoke、只读权限说明、README 指针 | 与 nas-service-deploy skill 分工待定 |
| `period-digest` | `.hermes/skills/period-digest` | Hermes 个人运维 | 周/月复盘生成 | 是 | 否 | none known | possible event/OKR storage | hermes-agent + mcp + memory | P2 | 复盘生成 smoke、输入数据契约、README 指针 | 依赖 daily-capture/goal-setting |
| `account-config` | `.agents/skills/account-config` | note 工具 / 配置 | 被其他 skill 自动调用加载账号配置 | 否 | 否 | candidate: `packages/config`, needs reconciliation | candidate: config contracts | agents + mcp + thin-skill | P0 | 配置加载替代库、调用方对账、README 指针 | 共享依赖，优先级高 |
| `acp-note-taker` | `.agents/skills/acp-note-taker` | note 工具 / 学习 | ACP 课程学习笔记整理 | 是 | 否 | none known | none known | thin-skill / archive | P3 | 用户确认保留价值、替代说明或归档 README | 是否属于迁移主线不清晰 |
| `notion-media-orchestrator` | `.agents/skills/notion-media-orchestrator` | note 工具 / Notion 编排 | 接管 Notion 自媒体流水线 | 是 | 否 | candidate: content orchestration, needs reconciliation | none known | agents + thin-skill | P2 | Notion workflow smoke、与 content skills 边界、README 指针 | 是否并入内容线待确认 |
| `repo-bootstrap` | `.agents/skills/repo-bootstrap` | note 工具 | 创建 vault 项目/资料骨架 | 否 | 否 | none known | none known | thin-skill / archive | P3 | 替代脚本或保留说明、README 指针 | 可能保留本地工具 |
| `source-import` | `.agents/skills/source-import` | note 工具 / 来源索引 | 增量复制资料到 13-来源索引 | 否 | 否 | none known | possible Library import, needs reconciliation | nowledge-library + thin-skill | P1 | Library/source import smoke、manifest 证据、README 指针 | 与 Library ingestion feature 相关 |
| `workspace-repair` | `.agents/skills/workspace-repair` | note 工具 | 修复 repo_id 到 local_path 映射 | 否 | 否 | none known | none known | thin-skill / archive | P3 | 替代脚本或保留说明、README 指针 | 可能不属于业务迁移 |
| `monthly-review` | `.agents/skills/monthly-review` | 质量 / 文风 | 分析账号真实数据并优化 prompt | 是 | 否 | candidate: analytics/retrospective specs, needs reconciliation | candidate: hermes-db analytics, needs reconciliation | agents + mcp + memory | P1 | 数据读取 smoke、复盘报告样例、README 指针 | owner 需后续确认 |
| `style-analyzer` | `.agents/skills/style-analyzer` | 质量 / 文风 | 提取或更新写作风格档案 | 是 | 否 | candidate: `packages/style-anchor`, needs reconciliation | candidate: style profile storage | agents + mcp + thin-skill | P1 | 风格档案生成 smoke、存储路径、README 指针 | 内容/小说/公众号共享能力 |

## Count Check

- Expected skills: 44
- Matrix rows: 44
- Status: PASS draft count check

## Current Known Gaps

- `agents 既有落点` 只是候选，不代表已验证可用。
- `mcps 既有落点` 只是候选，不代表已有完整契约。
- 每个 deletion gate 都需要后续 feature 补充真实 smoke 或验收证据。

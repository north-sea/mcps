# Tasks: WeChat Topic / Draft Trial

**Workspace**: `wechat-topic-draft-trial` | **Date**: 2026-07-01

---

## Phase 1: Trial Activation

- [x] T001 切换 roadmap 当前目标
  - scope: `specs/note-skill-migration-roadmap/roadmap.md`, `specs/.active`
  - verify: roadmap current 与 `.active` 都指向 `wechat-topic-draft-trial`

- [x] T002 固化试用边界
  - scope: `spec.md`, `plan.md`
  - verify: 明确“先选题和发草稿，完整写文章 feature 后置”

- [x] T003 绑定已验证前置契约
  - scope: `plan.md`, upstream acceptance/evidence
  - verify: 引用 topic plan、topic adopt/inbox、article-to-draft、memory boundary 的 PASS 证据

## Phase 2: Trial Use

- [x] T003A 审计四个公众号选题配置
  - verify: `account-config-audit.md` 记录 production hermes-db accounts/tracks、本地 agents profile/topic-tracks 差异、account-fit gate 和 draft target 风险
  - evidence: 发现 production track `description` 全为空；`moon-sleeping` 缺 3-9 月宝宝高关注关键词；四个账号 production `draft_target=youmind` 与 roadmap 决策冲突，需在 T005 前澄清

- [x] T004 完成第一轮 topic plan / shortlist / adopt 试用
  - verify: `trial-log.md` 记录输入、候选、采纳结果、topic/topic_plan id 或阻塞原因
  - evidence: Run 001 已创建 production candidate `625a39ed-1c65-4d9f-a3bf-6f636a332a85` 和 TopicPlan `68f1fcde-80a5-402e-b3e0-1e952a9da4c9`；candidate 已进入 `shortlisted`。adopt 暂缓，等待人工确认。

- [x] T005 完成第一轮草稿链路试用
  - verify: `trial-log.md` 记录 article artifact / draft result / dry-run result；live 发草稿需人工确认
  - evidence: Run 003 记录 `article_document -> publish_ready artifact -> create draft facade` dry-run replay；`rtk pnpm --filter @mcps/wechat-draft test` PASS（67 passed）；无 live 草稿、上传或发布动作

- [x] T006 记录试用反馈和后续 feature 判断
  - verify: `acceptance.md` 更新是否继续 trial、启动写作 feature、或先补 Library ingestion
  - partial evidence: Run 001 证明链路可写，但用户确认选题与四个公众号实际定位不匹配；已在 `trial-log.md` 增加 account-fit gate。
  - evidence: `acceptance.md` 记录 trial verdict：继续保留选题/草稿 dry-run 链路，不启动完整自动写文章 feature；下一步优先补 `knowledge-library-ingestion-plan` 和 account-fit / Library sources，live draft 保持人工确认门禁

## Phase 3: Trial Closeout

- [x] T007 试用期验收
  - verify: 至少一轮 topic 和草稿链路有 evidence，或明确阻塞并回退 roadmap
  - evidence: `acceptance.md` 记录 topic plan / shortlist production evidence、draft dry-run replay evidence、remaining manual gates 和 final verdict

- [x] T008 更新后续 roadmap
  - verify: 根据试用结果决定 `knowledge-library-ingestion-plan`、写作 feature、或 `wechat-content-runtime-contracts` closeout 的顺序
  - evidence: `specs/note-skill-migration-roadmap/roadmap.md` 更新当前 feature 和推荐顺序；`specs/.active` 切到 `knowledge-library-ingestion-plan`

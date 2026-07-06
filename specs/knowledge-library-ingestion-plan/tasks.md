# Tasks: Knowledge Library Ingestion Plan

## Phase 1: Classification

- [x] T001 Define source classes and routing table
  - scope: `source-classification.md`
  - verify: covers all `KnowledgeSourceClass` values from `data-model.md`
  - evidence: `source-classification.md` covers account-profile, platform-rule, reference-article, writing-sample, source-inbox, runtime-decision, execution-state

- [x] T002 Build four-account source plan
  - scope: `account-fit-source-plan.md`
  - verify: covers `after-work`, `micro-rain-spring`, `moon-sleeping`, `smart-life`; `moon-sleeping` includes 3-9 month baby care sources
  - evidence: `account-fit-source-plan.md` covers all four accounts and defines `moon-sleeping` first source pack for feeding, night waking, routine, and mother-support tone

## Phase 2: Dry-Run Manifest

- [x] T003 Create ingestion dry-run manifest example
  - scope: `ingestion-dry-run-manifest.example.json`
  - verify: valid JSON, `no_side_effects=true`, includes at least one `moon-sleeping` source candidate
  - evidence: `rtk node -e "JSON.parse(...)"` PASS; manifest has `no_side_effects=true` and `moon-sleeping-3-9m-feeding-rules`

- [x] T004 Define content skill deletion gates
  - scope: `deletion-gates.md`
  - verify: P0/P1 content note skills have replacement target, smoke/evidence requirement, and delete/keep/archive decision gate
  - evidence: `deletion-gates.md` covers topic scout/radar, topic inbox, wechat writer/pipeline/image skills, youmind publisher, and blog skills; deletion remains user-gated

## Phase 3: Verification and Closeout

- [x] T005 Verify no live side effects
  - scope: git diff + command log
  - verify: no Library import, NAS import, note skill deletion, or remote write was performed
  - evidence: only specs/roadmap/docs artifacts were added/updated; no Library import, NAS import, note skill deletion, live upload, publish, or remote write command was run

- [x] T006 Update roadmap and acceptance
  - scope: `acceptance.md`, `../note-skill-migration-roadmap/roadmap.md`
  - verify: roadmap records next recommended feature after Library ingestion planning
  - evidence: `acceptance.md` added; roadmap updated to mark this feature done and recommend `wechat-content-runtime-contracts` closeout next

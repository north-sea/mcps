# Deletion Gates

## Content P0/P1 Skills

| Skill / Area | Target Route | Gate Before Delete | Current Decision |
|---|---|---|---|
| `topic-scout` / `topic-radar` | agents topic planning + hermes-db topic candidates/plans | production topic plan evidence + account-fit source ids | keep until Library/account-fit dry-run is verified |
| `topic-inbox` | hermes-db topic inbox/adopt + Library source queue | inbox route smoke + source metadata manifest | keep |
| `wechat-writer` | future agents writing runtime | writing runtime spec + account source packs + draft dry-run | defer delete |
| `wechat-article-pipeline` | wechat-content-runtime-contracts + wechat-draft MCP | article-to-draft evidence + replacement route docs | thin-shell candidate only after route docs |
| `wechat-cover` / `wechat-illustration` / `wechat-image-generator` | wechat-draft asset/preflight + future image provider route | asset dry-run + provider gate + account visual sources | keep |
| `youmind-publisher` | no further investment / archive | explicit archive notice + no active draft_target dependency | archive candidate; do not delete before `draft_target` clarified |
| `blog-writer` / `blog-workflow` | future blog runtime or Library-backed writing route | separate blog route decision | keep |

## Universal Gate

A note skill can be deleted only when all are true:

- Replacement route exists in specs or README.
- Required source materials are represented by Library/Markdown/Git metadata.
- Dry-run or test evidence proves the replacement route.
- User has approved deletion or archive.

This feature does not delete any note skill.

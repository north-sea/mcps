# Source Classification

## Routing Table

| Source Class | Target | Owner | Import Shape | Delete Gate Impact |
|---|---|---|---|---|
| `account-profile` | Library/Wiki + Markdown/Git | content runtime | account positioning, audience, columns, tone, visual rules | Required before deleting account-config skill material |
| `platform-rule` | Library/Wiki | mcps / agents caller docs | platform limits, API behavior, draft/image constraints | Required before deleting platform-rule notes |
| `reference-article` | Library/Wiki | Library | title, source URL/path, excerpt metadata, tags | Delete only after route points to Library source id |
| `writing-sample` | Library/Wiki + Markdown/Git | agents writing runtime | article sample metadata, style tags, account id | Keep originals unless explicit archive gate passes |
| `source-inbox` | Karakeep/source inbox -> Library queue | human/operator | pending link/material metadata | Never delete automatically |
| `runtime-decision` | Memory + specs | SDD / operator | compact decision/procedure summary | Memory summary allowed; original spec remains source |
| `execution-state` | specs / hermes-db / workflow artifact | runtime owner | job state, trial log, acceptance evidence | Not a Library source |

## Rules

- Full source materials do not go into nmem.
- Memory entries may reference Library ids, Markdown paths, specs, or roadmap rows.
- Library ingestion is dry-run until a later importer feature explicitly approves live import.
- Deletion gates must name the replacement route and evidence; no replacement, no deletion.

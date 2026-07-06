# Data Model: Knowledge Library Ingestion Plan

## KnowledgeSourceClass

| Class | Target | Examples | Memory Handling |
|---|---|---|---|
| `account-profile` | Library/Wiki + Markdown/Git | 公众号定位、受众、栏目、语气、禁写规则 | summary only |
| `platform-rule` | Library/Wiki | 微信草稿、图片、平台限制、发布规则 | decision/procedure summary |
| `reference-article` | Library/Wiki | 参考文章、拆解样例、爆款结构 | no full text in memory |
| `writing-sample` | Library/Wiki + Markdown/Git | 账号历史文章、风格样例 | style summary only |
| `source-inbox` | Karakeep/source inbox -> Library queue | 待处理链接、网页、PDF、收藏 | capture metadata only |
| `runtime-decision` | Memory + specs | 架构决策、route 选择、删除门禁 | durable memory allowed |
| `execution-state` | specs / hermes-db / workflow artifact | 单次任务状态、job、trial log | not Library |

## LibraryMetadata

```ts
interface LibraryMetadata {
  source_id: string;
  source_class: KnowledgeSourceClass;
  domain: "wechat" | "blog" | "novel" | "xhs" | "ops" | "general";
  account_id?: string;
  track_id?: string;
  title: string;
  origin_path?: string;
  origin_url?: string;
  owner: "library" | "markdown-git" | "karakeep" | "memory" | "archive";
  retention: "keep" | "archive-after-import" | "delete-after-gate" | "do-not-delete";
  deletion_gate_refs: string[];
  status: "candidate" | "dry-run" | "ready" | "imported" | "blocked";
  notes?: string;
}
```

## DryRunManifest

```ts
interface DryRunManifest {
  run_id: string;
  created_at: string;
  scope: string;
  sources: LibraryMetadata[];
  blocked: Array<{ source_id: string; reason: string; next_action: string }>;
  no_side_effects: true;
}
```

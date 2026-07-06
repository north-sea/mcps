# Risk Gates: XHS Workflow Definition

**Workspace**: `xhs-workflow-definition`  
**Date**: 2026-07-07

| Risk | Gate | Current Status |
|---|---|---|
| Platform publishing | explicit user approval and manual/live smoke | blocked |
| Login/session automation | explicit security/compliance decision | blocked |
| Scraping/source capture | platform compliance and Library provenance route | blocked |
| Image generation/provider cost | provider dry-run and credential gate | blocked |
| Note skill deletion | replacement route or explicit archive/delete instruction | blocked |

## Safety Result

This feature performs no XHS publishing, scraping, login automation, image generation, external write, or note deletion.

# Config Checklist: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01

---

## Before Restarting NAS nmem

- [ ] NAS data directory or Docker volume backed up.
- [ ] Confirm local NowledgeGraph primary copy exists before treating NAS data as cleanup candidate.
- [ ] Existing NAS spaces inventory plan prepared.
- [ ] No plan to delete or merge spaces before backup.
- [ ] Secrets will be referenced by env var names only, not copied into docs.
- [ ] Local Codex/Claude Code config will not be changed to NAS nmem.

---

## After Restarting NAS nmem

- [ ] Confirm container running.
- [ ] Run read-only status check.
- [ ] Run read-only spaces inventory.
- [ ] Run export backup.
- [ ] Verify `hermes` space exists or create it intentionally.
- [ ] Verify domain spaces for WeChat/novel/XHS are preserved if present.
- [ ] Create NAS-to-local space mapping before any import.
- [ ] Confirm domain imports use `merge` or `skip`, never default `overwrite`.
- [ ] Confirm Hermes endpoint uses NAS nmem.
- [ ] Confirm Codex/Claude Code do not use NAS nmem remote write.

---

## Cleanup Gate

Cleanup may start only after:

- [ ] Backup exists.
- [ ] Spaces inventory exists.
- [ ] Candidate records are classified as keep/export/archive/delete.
- [ ] Domain spaces are not being collapsed into `hermes`.
- [ ] Deletion list has explicit replacement proof.

---

## Security Gate

- [ ] No token/API key/cookie/bearer in docs.
- [ ] Command outputs containing secrets are not pasted into evidence.
- [ ] Any exposed token from previous shell output is rotated or removed from default shell environment.
- [ ] Public route and internal route are documented using placeholders only.

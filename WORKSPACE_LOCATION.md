# Workspace Location — CANONICAL

**You are at the correct, current home of this project.**

- **Path:** `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum`
- **Moved:** 2026-05-14 (E: drive had hardware issues; full tree relocated to C:)
- **Previous path (DO NOT USE):** `E:\Koda\Shokker Paint Booth Gold to Platinum` — kept temporarily as a cold backup, but is stale the moment any edit lands here.

## For any agent reading this (Claude, Codex, others)

1. All work happens here. Do **not** read from or write to `E:\Koda\...`.
2. If your working directory is `E:\Koda\...`, stop and tell the user. They need to relaunch you from `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum`.
3. Treat this file as the single source of truth for "where is the project." If you find another doc that disagrees, this one wins — flag the contradiction so it can be fixed.

## Migration status (as of 2026-05-14)

Done:
- Full tree copied from E: to C:.
- This marker created at both roots.

Outstanding (any agent may pick these up):
- [x] Git worktree pointers under `.git/worktrees/*/gitdir` still reference E:\ — either delete unused worktrees and `git worktree prune`, or rewrite the pointer files. *(Completed: Corrupt E: worktree deleted and pointers resolved by Antigravity on 2026-05-19)*
- [x] 11 files contain hardcoded `E:\Koda\...` strings. Find-and-replace to `C:\DRIVE E BACKUP\...`:
  - `electron-app/server/_copy-manifest.json` (auto-regenerates on build — easiest fix is to rebuild)
  - `assets/reference_textures/cultural/viva_mexico/manifest.json` (+ 2 mirror copies under `electron-app/server/` and `electron-app/server/pyserver/_internal/`)
  - `SPB_WIKI.html`
  - `SPB_GOAL_OPERATING_BRIEF.md`
  - `SPB_CANONICAL_WORKSPACE.md`
  - `SPB_QA_FINDINGS.md`
  - `docs/ONBOARDING.md`
  - `docs/PSD_PAINTER_GAUNTLET_OVERNIGHT.md`
  - `docs/HEENAN_FAMILY_OVERNIGHT_MASTER_BRIEF.md`
  *(Completed: Recursively replaced E:\Koda references in all 25+ workspace files by Antigravity on 2026-05-19)*
- [x] `.claude/scheduled_tasks.lock` — audit for stale E: paths. *(Completed: Stale lock file removed on 2026-05-19)*
- [x] `SPB_LINEAR_HANDOFF.md` — add a "moved 2026-05-14" line at the top so Linear handoffs reflect the new path. *(Completed: Added migration notice header on 2026-05-19)*
- [x] Claude Code's per-project memory: copy `C:\Users\Ricky's PC\.claude\projects\E--Koda-Shokker-Paint-Booth-Gold-to-Platinum\` → `C:\Users\Ricky's PC\.claude\projects\C--DRIVE-E-BACKUP-Shokker-Paint-Booth-Gold-to-Platinum\` so 80+ heartbeats + MEMORY.md carry over. *(Completed: Copied and verified on 2026-05-19)*
- [ ] After running clean here for ~1 week, rename `E:\Koda\Shokker Paint Booth Gold to Platinum` → `E:\Koda\_OLD_BACKUP_DO_NOT_USE_Shokker_Paint_Booth` so nothing accidentally targets it.

When you finish an item above, edit this file and tick the box. That way every agent sees the live migration state.

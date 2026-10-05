# Git LFS Plan — Repo-Weight Remediation (~14 GB)

Status: **PLAN ONLY — NOT EXECUTED.**
This document describes a *safe, owner-coordinated* path to shrink the
repository. It is paired with the config-only `.gitattributes` at the repo
root (WIN #15). No LFS install, no `git lfs track`, no history rewrite has
been run as part of this document.

> ⚠️ **DO NOT run any command in this file unsupervised.** Several steps
> (history migration) are **destructive and irreversible** for everyone
> who has a clone or worktree. They MUST be scheduled and run by the repo
> **owner** with all collaborators notified. See "DANGER" below.

---

## 1. The problem

The working tree is roughly **14 GB**. That weight comes from two very
different sources, and they have very different fixes:

1. **Untracked / ignored bulk** — regenerated engine output and tooling
   caches. These are *already* in `.gitignore` and (if never committed)
   contribute to disk size but **not** to Git history size. Fixing these
   is non-destructive.
2. **Committed binary blobs in history** — large binaries that were
   committed at some point. These inflate the `.git` pack files *forever*,
   even if the file is later deleted. Removing them requires rewriting
   history (destructive).

Before deciding anything, **measure** (read-only):

```bash
# Working-tree size by top-level dir (PowerShell or bash du):
du -sh ./*            2>/dev/null | sort -h

# How big is history itself:
git count-objects -vH

# The largest blobs ever committed (top 40):
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '/^blob/ {print $3, $4}' \
  | sort -nr | head -40
```

If `git count-objects -vH` (the `size-pack` line) is small (e.g. tens/low
hundreds of MB) while the working tree is 14 GB, then **most weight is
untracked output** and you likely DO NOT need a history rewrite at all —
just confirm `.gitignore` coverage (Section 2). Only pursue the destructive
rewrite (Section 4) if large blobs are genuinely *committed in history*.

---

## 2. Classification — what goes where

Inventory of top-level directories observed in this repo, classified.

### A. KEEP IN GIT, as normal text (no LFS)
Source code and small config. These are the project; they are tiny and
diffable. Already covered by `.gitattributes` (LF-normalized).
- `*.py` engine + tooling (`animation_engine.py`, `paint_v2.py`,
  `paint_v3.py`, `base_registry_data.py`, `spec_patterns.py`,
  `build_spec.py`, etc.)
- `paint-booth-0-finish-data.js` and other JS source
- `tests/`, `tools/`, `scripts/`, `conftest.py`, `pytest.ini`
- `src/`, `frontend/` source (non-built)
- `paint_v2/`, `paint_v3/`, `expansions/`, `spec_pattern_families/`,
  `spec_patterns/` (source data modules)
- `requirements*.txt`, `package.json`, `package-lock.json`, `setup.py`,
  `README.md`, `.python-version`, this `docs/` tree

### B. SHOULD BE TRACKED IN GIT LFS (committed but binary + large)
Binary assets that are genuinely part of the product and must be versioned,
but should NOT live as raw blobs in pack history. Move these to LFS
*only if they are actually committed and sizable* (verify with the blob
scan in Section 1).
- `assets/`   — images / textures (`*.png *.jpg *.jpeg *.tga *.psd`)
- `fonts/`    — font binaries (`*.ttf *.otf *.woff *.woff2`)
- `icons/`    — `*.ico *.png`
- `models/`   — model/weight files (`*.mat *.npz *.dat *.pak` and similar)
- `data/`     — large committed data payloads, if any (`*.dat *.npz *.mat`)
- `static/`, `public/` — only the *binary* media inside them (not HTML/CSS)

### C. DO NOT TRACK AT ALL (untracked / ignored — regenerated or local)
These are already in `.gitignore`. Confirm they are *not* in history; if
they are, they are prime targets for the Section 4 rewrite. They should
never go into LFS — LFS still versions them and still costs storage.
- `renders/`, `output/`, `exports/`  — engine output, regenerated
- `build/`, `dist/`                    — build artifacts
- `node_modules/`, `.venv/`, `venv/`   — installable dependencies
- `__pycache__/`, `.pytest_cache/`, `cache/`, `tmp/`, `temp/`, `logs/`
- `.codex-worktrees/`                  — local worktrees
- `.specstory/`, `.claude/`            — local tooling state (review first)

### D. DELETE / ARCHIVE OUT-OF-BAND (backup-bloat dirs)
Snapshot/backup copies that should not be in the repo at all. Move them to
external storage, then remove from the working tree. If they are committed
in history they are top candidates for the destructive rewrite.
- `spec_patterns_BACKUP_BLOAT/`
- `paint_v2_BACKUP/`
- `spec_pattern_families.backup/`

---

## 3. Exact LFS track patterns (config step — non-destructive)

This step (installing LFS hooks and adding `filter=lfs` rules to
`.gitattributes`) is **non-destructive for history**: it only changes how
*future* commits store matching files. It is still owner-coordinated
because every collaborator must `git lfs install` to clone/pull correctly.

> The `binary` rules already in the root `.gitattributes` and the
> `filter=lfs` rules below are complementary: `git lfs track` appends its
> own lines. After running it, **review the diff** so the LFS lines do not
> duplicate or contradict the existing `binary` lines. LFS-tracked
> patterns should carry `filter=lfs diff=lfs merge=lfs -text` (the `-text`
> supersedes the plain `binary` marker for the same glob).

```bash
# One-time per machine (owner + every collaborator):
git lfs install

# Image / texture assets:
git lfs track "*.png"
git lfs track "*.jpg"
git lfs track "*.jpeg"
git lfs track "*.tga"
git lfs track "*.psd"

# Archives & native binaries (only if committed & large):
git lfs track "*.zip"
git lfs track "*.exe"
git lfs track "*.dll"
git lfs track "*.pyd"

# Fonts & icons:
git lfs track "*.ico"
git lfs track "*.ttf"
git lfs track "*.otf"
git lfs track "*.woff"
git lfs track "*.woff2"

# Engine model / data payloads:
git lfs track "*.pak"
git lfs track "*.dat"
git lfs track "*.mat"
git lfs track "*.npz"

# Then commit the updated .gitattributes (LFS appends its rules here):
git add .gitattributes
git commit -m "chore: track large binary assets via Git LFS"
```

To scope LFS to a single directory instead of repo-wide (recommended if
e.g. `*.dat` also appears as small tracked source somewhere), use a path
prefix: `git lfs track "assets/**/*.png"`.

Verify what LFS will manage (read-only):
```bash
git lfs track          # lists current patterns
git lfs ls-files       # lists files currently stored as LFS pointers
```

---

## 4. Shrinking EXISTING history — ⚠️ DANGER: DESTRUCTIVE ⚠️

Everything above only affects *new* commits. To actually reclaim the GBs
already baked into `.git`, history must be **rewritten**, which changes
every commit SHA from the rewrite point forward.

> ### THIS IS DESTRUCTIVE AND MUST BE OWNER-COORDINATED
> - It **rewrites commit hashes**, so every existing clone, fork, and
>   **worktree** is invalidated and must re-clone or hard-reset.
> - The **`codex/` and `SpecBuilder` branches** and all
>   **`.codex-worktrees/`** worktrees will break — they MUST be merged,
>   landed, or abandoned *before* the rewrite, and recreated *after*.
> - Open PRs / outstanding branches will need to be rebased or recreated.
> - It is **irreversible** once force-pushed. Take a full backup first.
>
> **Required pre-flight checklist (owner runs, with team notified):**
> 1. Announce a freeze window; no pushes during the rewrite.
> 2. **Full backup**: `git clone --mirror` the repo to a safe location,
>    and archive the network-drive working copy.
> 3. Land or explicitly abandon every active branch, including
>    `codex/*`, `SpecBuilder`, and every entry under `.codex-worktrees/`.
>    Run `git worktree list` and `git worktree remove` for each before
>    rewriting.
> 4. Confirm via the blob scan (Section 1) exactly which paths to purge.

Recommended tool: **`git filter-repo`** (faster and safer than the old
`filter-branch`; BFG is an alternative for pure "strip big blobs").

```bash
# DRY-RUN style analysis first (read-only):
git filter-repo --analyze
# -> writes a report under .git/filter-repo/ ; review before any rewrite.

# EXAMPLE rewrite (DO NOT run without the checklist above):
#   strip backup-bloat dirs and never-needed output from ALL history
git filter-repo \
  --path spec_patterns_BACKUP_BLOAT/ \
  --path paint_v2_BACKUP/ \
  --path spec_pattern_families.backup/ \
  --path renders/ --path output/ --path exports/ \
  --invert-paths

# Migrate already-committed binaries into LFS across ALL history
# (also a rewrite — same danger, same checklist):
git lfs migrate import --everything \
  --include="*.png,*.jpg,*.jpeg,*.tga,*.psd,*.zip,*.exe,*.dll,*.pyd,*.ico,*.pak,*.dat,*.mat,*.npz"
```

**After a rewrite (owner):**
```bash
git push --force-with-lease --all
git push --force-with-lease --tags
# Then: every collaborator deletes their clone and re-clones.
# Recreate any needed worktrees / codex branches from the new history.
```

---

## 5. Recommended order of operations (safest first)

1. **Measure** (Section 1) — decide if a rewrite is even needed.
2. **Non-destructive cleanup first:**
   - Confirm `.gitignore` covers all of category C (it currently does).
   - `git rm -r --cached` any category-C/D dir that was *accidentally
     committed* but is still in the working tree, then commit. This stops
     future bloat without a full history rewrite (history stays, but the
     tree shrinks for new clones at HEAD).
   - Archive category-D backup dirs out of the repo entirely.
3. **Adopt LFS for new commits** (Section 3) — config only.
4. **Only if history is still huge:** schedule the **destructive** rewrite
   (Section 4) with the full owner checklist and team freeze.

---

## 6. Quick reference — current `.gitignore` already covers

`__pycache__/`, `*.py[cod]`, `*.egg-info/`, `.venv/`, `venv/`,
`.pytest_cache/`, `node_modules/`, `build/`, `dist/`, `logs/`, `cache/`,
`tmp/`, `temp/`, `renders/`, `output/`, `exports/`, `.DS_Store`,
`Thumbs.db`, `.vscode/`, `.idea/`, `.codex-worktrees/`, `.env`, `*.env`.

So the untracked-bulk side is largely handled. The remaining work is:
(a) verify none of the above were committed historically, and
(b) decide LFS vs rewrite for any genuinely-committed large binaries.

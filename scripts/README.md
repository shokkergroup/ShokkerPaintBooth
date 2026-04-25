# `scripts/` — Shokker Paint Booth helper scripts

Utility scripts used by SPB's build, packaging, and content pipelines.

Everything in this folder is standalone — you can invoke each script directly
via `node` or `python` (depending on file extension). The key Node script
(`sync-runtime-copies.js`) is also exposed via `npm run sync-runtime` and
`npm run check-runtime-sync` in both the repo-root `package.json` and
`electron-app/package.json`.

---

## Directory map

| File | Lang | Purpose |
|------|------|---------|
| [`sync-runtime-copies.js`](./sync-runtime-copies.js) | Node | Keep root-level UI/runtime files mirrored into `electron-app/server/` and `electron-app/server/pyserver/_internal/`. See **RUNTIME_SYNC.md**. |
| [`runtime-sync-manifest.json`](./runtime-sync-manifest.json) | JSON | Declarative input for `sync-runtime-copies.js`: which files and which target directories. |
| [`RUNTIME_SYNC.md`](./RUNTIME_SYNC.md) | Docs | Explains the 3-copy layout and when to run sync. |
| [`build_special_groups.py`](./build_special_groups.py) | Python | Generates special-group metadata JS output from the registry (produces `special_groups_output.js`). |
| [`special_groups_output.js`](./special_groups_output.js) | JS (gen) | Output of `build_special_groups.py`. Do not edit by hand. |
| [`export_finish_ids.py`](./export_finish_ids.py) | Python | Dump finish ID list from the active registry — useful for diffing schema drift. |
| [`extract_finish_colors.py`](./extract_finish_colors.py) | Python | Extract base colors for every finish (used during color-audit passes). |
| [`extract_spec_paint.py`](./extract_spec_paint.py) | Python | Extract spec-paint material values for auditing the R/G/B channel conventions. |
| [`generate_smilexx_upgraded.py`](./generate_smilexx_upgraded.py) | Python | Generator for upgraded SMILEXX swatch data. |
| [`import_abstract_experimental_patterns.py`](./import_abstract_experimental_patterns.py) | Python | Import abstract/experimental pattern definitions into the registry. |
| [`list_patterns_by_category.py`](./list_patterns_by_category.py) | Python | Print patterns grouped by category (debug / QA helper). |
| [`remove_cs_block.py`](./remove_cs_block.py) | Python | One-shot removal of a deprecated ColorShift block. |
| [`remove_spec_paint_block.py`](./remove_spec_paint_block.py) | Python | One-shot removal of a deprecated spec-paint block. |
| [`split_engine.py`](./split_engine.py) | Python | Helper used during `shokker_engine_v2.py` module split. |
| [`validate_registry.py`](./validate_registry.py) | Python | Sanity checks for `FINISH_REGISTRY` entries (missing fns, dupe ids, etc.). |
| [`bake_pattern_thumbnails.{sh,bat}`](./bake_pattern_thumbnails.sh) | Shell | Platform wrappers that regenerate pattern thumbnail PNGs. |
| [`mono_ids_backend.txt`](./mono_ids_backend.txt) | Text | Supporting data — monolithic ID list used by build generators. |

> **Ownership note.** The root-level UI files (`paint-booth-*.js`,
> `paint-booth-v2.{html,css}`, `fusion-swatches.js`, etc.) are the source of
> truth. Never edit the mirrored copies under `electron-app/server/` by hand —
> run `npm run sync-runtime` from repo root instead.

---

## `sync-runtime-copies.js` — quick reference

```
node scripts/sync-runtime-copies.js --check           # report drift (CI-safe)
node scripts/sync-runtime-copies.js --write           # copy drifted files
node scripts/sync-runtime-copies.js --write --dry-run # preview what --write would do
node scripts/sync-runtime-copies.js --list            # enumerate every (source, target) pair
node scripts/sync-runtime-copies.js --help            # full flag list
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success — no drift, or drift fixed with `--write`. |
| 1 | Hard error — missing source, corrupt manifest, failed copy, lock conflict. |
| 2 | Warning — orphan copies found via `--check-orphans` (unless `--force`). |

Useful flags:

- `--verbose` / `-v` — per-file detail + timings.
- `--quiet` / `-q` — errors only.
- `--verify` — post-copy SHA-256 verification.
- `--check-orphans` — flag files present in target directories but not in the manifest (likely stale copies of removed files).
- `--history` — append one JSON line per run to `scripts/.runtime-sync-history.log`.
- `--jobs <n>` — parallel worker count (default: 4).
- `--manifest <path>` / `SPB_RUNTIME_MANIFEST=<path>` — use an alternate manifest.
- `--no-color` / `NO_COLOR=1` — disable ANSI colors.
- `--force` — skip non-fatal safety checks and clear stale lock files.

Programmatic use (from `electron-app/copy-server-assets.js`):

```js
const { loadManifest, syncRuntimeCopies } =
  require('./scripts/sync-runtime-copies.js');

const files = loadManifest().files;
const { driftCount, missingSources } =
  syncRuntimeCopies({ write: true, verbose: true });
```

### `runtime-sync-manifest.json` shape

```jsonc
{
  "schema_version": 1,
  "version": "2026.04.17-1",
  "source_of_truth": "repo_root",
  "targets": [ "electron-app/server", "electron-app/server/pyserver/_internal" ],
  "files":   [ "paint-booth-v2.html", /* ... */ ]
}
```

- `targets` are directories relative to repo root; each listed `file` is
  copied into every target, keyed by basename.
- `schema_version` is bumped whenever the layout changes.
- `version` is a free-form stamp written to the history log.

### Optional config file — `scripts/.spbconfig.json`

Lowest-priority defaults. CLI flags and env vars always win.

```jsonc
{
  "jobs": 8,
  "verbose": true,
  "history": true,
  "manifest": "runtime-sync-manifest.json"
}
```

---

## Python helpers

Most `.py` files in this folder are one-shot generators/auditors run by hand
during engine refactors. They're safe to re-run — none of them mutate the
registry in-place; they print to stdout or write to generated `.js`/`.txt`
outputs. Before running any of them, ensure your Python path points at the
repo-root `electron-app/server/engine/` package (they import from there).

See individual script headers for each one's specific usage.

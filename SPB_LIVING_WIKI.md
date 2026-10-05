# SPB LIVING WIKI — the single source of truth for Shokker Paint Booth

> ## ⚠️ READ THIS FIRST — which wiki is canonical?
>
> **`SPB_WIKI.html` (the Living Wiki) is the single source of truth.** It is the one CLAUDE.md points at,
> the one that carries the **Agent Coordination Board**, the **Daily Work Log**, **The Laws**, and
> **Hard-Won Lessons**, and the one you must claim your lane in and log to. Open that first.
>
> **This file is the deep-reference companion.** It holds long-form PART I reference material that
> pre-dates the HTML wiki. Where the two disagree, **`SPB_WIKI.html` wins** — it is maintained every
> session; this file is not. Its `Smart Separate, Car Intelligence & the AI Separation Model` section
> was lifted into the Living Wiki on 2026-09-04; the rest remains here as background.
>
> *Last substantive edit to this file: 2026-08-20.*

---


> **This file is the be-all/end-all build guide for SPB.** A coding agent should be able to read THIS ONE
> FILE and know exactly what SPB is, how it's built, how to run/test/ship it, the laws it must obey, every
> major subsystem, the big bugs we've already chased, where the app has been, and where it's going.
>
> **PART I (below the TOC)** is the durable REFERENCE — architecture, file map, doctrines, subsystems, bug
> war-stories, roadmap, tooling. **PART II** is the running history — releases, the audit system, and the
> dated DAILY LOG (append what you did every session). Read the relevant PART I section before working;
> append to the DAILY LOG after. Keep it honest, dated, specific. When this Wiki and an older doc/README
> disagree, **the Wiki wins.**
>
> Sibling docs: `CLAUDE.md` (agent rules), `PRIORITIES.md`, `CHANGELOG.md`, `docs/METRICS.md`,
> `RELEASE_NOTES_8.0.3.md`, plus the deep dossiers `CAR_INTEL_MISSION.md`,
> `SMART_SEPARATE_HANDOFF_FOR_CODEX.md`, `DEPLOY_SMART_SEPARATE_MODEL.md`, `OOM_FIX_PLAN.md`,
> `CATALOG_HEALTH_REPORT.md`. Rebuilt 2026-06-29.

## Table of Contents — PART I (Reference)
 1. [Overview & Identity](#overview-identity)
 2. [Architecture & Render Pipeline](#architecture-render-pipeline)
 3. [Repository & File Map](#repository-file-map)
 4. [Build · Run · Test · Deploy](#build-run-test-deploy)
 5. [Doctrines & Laws (the quality bar)](#doctrines-and-laws)
 6. [Finishes, Patterns, Bases & Color Science](#finishes-patterns-bases-color-science)
 7. [Spec Sculpt (the standalone sculpt tool + its engine)](#spec-sculpt)
 8. [Smart Separate, Car Intelligence & the AI Separation Model](#smart-separate-car-intelligence)
 9. [Zones, Layers, Live Preview & the Front-end](#zones-layers-live-preview-frontend)
10. [Big Bugs Chased & Fixed (war stories)](#big-bugs-chased-and-fixed)
11. [Licensing, Distribution & Roadmap (where it's been / where it's going)](#licensing-distribution-roadmap)
12. [Dev Tooling, Gotchas & How to Work in This Repo](#dev-tooling-gotchas-how-to-work)
13. [PART II — Releases, Audits & Daily Log (history)](#part-ii-history)

---
<a id="overview-identity"></a>

## Overview & Identity

### What SPB is, in one sentence

Shokker Paint Booth (SPB) is a **Windows-only desktop application for authoring iRacing livery SPEC MAPS** — the PBR material maps that make a car's paint react to in-sim light (flake, flip, iridescence, chrome bend, candy glow, color-shift). It is an **Electron shell** wrapping a **local Python/Flask render server** and a **massive procedural render engine**. The official product string in `electron-app/package.json` is literally `"Shokker Paint Booth V8 — iRacing Spec Map Tool"` (verified: `package.json` line 3), and that phrase — *Spec Map Tool* — is the most accurate one-line identity in the whole repo.

### The single most important identity rule: SPEC-MAP app, NOT a painting app

This is the load-bearing product decision a future agent must internalize before pitching or building anything. Stated emphatically by the owner on 2026-06-14 (`memory/spb-is-a-spec-map-app.md`):

> **"SPB is a SPEC-MAP app for iRacing — NOT a painting app."**

- **The value proposition is the spec map, not pixels.** Photoshop already paints pixels; SPB must not compete there. What SPB does that nothing else does is author *sophisticated PBR spec maps that create optical magic in-sim*. Build tools around **authoring/understanding the iRacing PBR material spec** (metalness / roughness / clearcoat → angle-reactive optical effects), not around drawing/compositing.
- **The product IS the M/R/Cc channels.** Every finish in SPB ships two things: a base-paint TGA and a **spec map** carrying three independently-meaningful channels — **M = metalness** (hot flakes, metal cores, energetic sparks), **R = roughness** (matte shadows, satin valleys, low-gloss recessed zones), **Cc = clearcoat** (gloss ridges, glassy highlights, wet pockets, hot edges). The `SPB_GOAL_OPERATING_BRIEF.md` "Spec Map Rule" (lines 99–163) is the canonical doctrine for what each channel must carry. The owner's quality bar is that the spec map must "trace design elements: sun rays, dragon bodies, devil eyes, shrine edges… small local material changes that make the design feel almost 3D." A flat green/yellow spec is a failure. Channels must also be **decorrelated** (`|corr| < 0.85`, see the spec-decorrelation doctrine) so each does distinct optical work.
- **Exported in the exact iRacing format:** TGA at 2048×2048 (base paint + spec map baked and ready to drop into iRacing's `paint/<car>/` folder).

### Hard product NO-GOs (do not re-pitch — the owner has already said no)

From `memory/spb-is-a-spec-map-app.md` (these have been suggested before and rejected):

1. **❌ NO 3D car preview / turntable / orbit-in-app.** Every iRacing car uses a different UV template; every in-app 3D attempt "looks like bullshit" and is not feasible. *Nuance:* a template-independent generic lit material **chip/sphere** was NOT rejected and may be acceptable — it's the **car model** that is the hard no-go.
2. **❌ NO numbers / sponsors / contingency decals / text-as-livery as a painting feature.** "Right now this is NOT a painting app." (Note: a *separate* engineering track — auto-separating an existing flat TGA into NUMBERS/SPONSORS/PAINT layers so spec sculpting can be layer-aware — does exist per recent memory, but that is spec-intelligence tooling, **not** "let the user paint numbers.")
3. **❌ NO generic Photoshop-equivalent tools** (brush/fill/lasso/etc. as the headline) — redundant with Photoshop.

**What the owner DOES want instead:** SPB-specific tools that are impossible or pointless in Photoshop — tools that *reveal, diagnose, or directly author MATERIAL BEHAVIOR under iRacing light*, leveraging SPB's exclusive knowledge of the M/R/Cc model and angle-reactive physics (e.g. Spec Sculpt = paint→spec, Shokker-ize = auto angle spec, Spec Overlay picker, channel dock). Do not duplicate those.

> ⚠️ **README contradiction to flag:** `README.md` is older marketing copy (v6.1 era) and describes SPB as "the painter's painter… paints *paint* not pixels… all previewed in real time on a **3D-aware canvas**" with "**Real-time PBR preview** — A 3D-aware car-shape preview." This **conflicts** with the binding 2026-06-14 spec-map identity and the explicit NO-3D-preview directive. When README and the owner's directive disagree, the **directive (and the Wiki) win** — the README's own header says "When this README and the Wiki disagree, the Wiki wins." Treat README feature claims (e.g. "192 spec overlay patterns across 19 PBR categories", "30+ new finishes in v6.1") as **stale**; verify against the live registry (numbers below).

### The user

**iRacing livery painters** — the person who "has hand-painted a spec map in Photoshop at 2 a.m. wondering whether `G=120` was matte enough" (README line 10). They want premium, angle-reactive optical finishes ("this is special," not "another swapped-color generator" — `SPB_GOAL_OPERATING_BRIEF.md` Mission). Windows-only because **iRacing is Windows-only**; no Mac/Linux builds planned (README line 46).

### Tech stack (verified against current code)

- **Electron shell** — `electron-app/` (Node `child_process.spawn`). `package.json`: name `shokker-paint-booth-v6`, version **`8.0.3`**, `main: main.js`, author "Shokker Group", license UNLICENSED, private. Version is read at runtime via `app.getVersion()` (e.g. `main.js:162`, `:967`, `:2292`).
- **Python/Flask backend served by `server_v5.py`** (repo root, ~43.8 KB) — **this is the confirmed entry point.** Its module docstring (`server_v5.py:1-39`) describes it as "Shokker Engine V5 — Local Flask Server (main entry point)." Default URL **`http://localhost:59876`**; env overrides `SHOKKER_PORT`, `SHOKKER_DEV` (hot reload), `SHOKKER_NO_CLEAN` (second instance). Uses Flask + flask_cors (`server_v5.py:45-46`). Boot sequence (docstring lines 15–25): clear `__pycache__` (stale-`.pyc` protection after auto-updates) → import `config.CFG` → import V5 engine registries and **patch the legacy engine to use them** → wire UI-catalog fallbacks → build Flask app → **inherit unmodified routes from `server.py`** → `clean_boot.clean_boot` → `server_health.run_startup_checks` → start Flask.
  - **`server.py`** (repo root, ~413 KB) is the **legacy route handler** that `server_v5.py` inherits from — the bulk of the HTTP API lives here; V5 only adds `/api/registry-check`, `/api/finish-data`, `/api/health`, `/build-check`.
  - `main.js` spawns it as `python server_v5.py` (bundled Python in the packaged build, plain `python` in dev) at `main.js:1969-1991`, resolves the server dir at `main.js:1277-1279`, and has zombie-reaping logic that greps the process table for `server_v5.py` (`main.js:1244-1250`).
- **The procedural render engine** — `shokker_engine_v2.py` (repo root, **~1.32 MB**, the "legacy pipeline") plus the modular **`engine/`** package (`engine.registry`, `engine/paint_v2/`, `engine/expansions/`, `engine/spec_sculpt/`, etc.). `server_v5.py` patches `shokker_engine_v2`'s registries to point at the V5 modular registries. Renders are **2048×2048** (the full-car canvas) and must complete in **2–3 s** (hard budget; >5 s red flag, >10 s unacceptable).
- **Two-copy sync rule:** core data files live in BOTH the repo root (source of truth) AND `electron-app/server/` (packaged into the installer); `node scripts/sync-runtime-copies.js --write` syncs root → `electron-app/server/` and the build hard-fails on drift. (Was three copies until 2026-06-09; the third `electron-app/server/pyserver/_internal/` was deleted — do not recreate it.)

### Catalog scale (LIVE, booted & counted 2026-06-29 — supersedes any stale doc/README number)

I booted the engine and counted both registry layers directly. **The number depends on which layer you measure — flag this, it is a real and confusing discrepancy:**

- **V5 modular registry** (`engine.registry`, what the boot banner reports): **843 monolithics · 682 bases · 201 fusions · 588 patterns.** Boot line verbatim: `[V5 Registry] READY - 682 bases, 588 patterns, 843 monolithics (201 fusions)`.
- **Fully-merged legacy registry** (`shokker_engine_v2.*` after lazy-loading ALL expansions — the dicts the render pipeline actually serves from): **1759 monolithics · 695 bases · 650 fusions · 716 patterns** (`se.MONOLITHIC_REGISTRY=1759`, `se.BASE_REGISTRY=695`, `se.FUSION_REGISTRY=650`, `se.PATTERN_REGISTRY=716`). The extra mass comes from late merges: the **24K Arsenal** (508 entries: 97 bases / 169 patterns / 242 specials), **Color Monolithics** (134), **651 Paradigm Shift Fusions** across 15 categories, plus FRACTURED families (Flames 135, Themes 100, Forge 78, Minds/Souls), Cultural sets (Viva Mexico 58, Rising Sun 52, Union Jacked 45, Grunge & Fun 48), etc.
- **The prompt's "~1525+ monolithic / 682 bases / 201 fusions" is approximately right:** **682 bases ✓** and **201 fusions ✓** match the V5 layer exactly; the monolithic count is bracketed by **843 (V5 registry) and 1759 (fully-merged engine)** — ~1525 is a mid-point estimate. Cite the layer when you quote a number, or you'll be "wrong" against the other one.
- **Patterns:** 588 (V5) / 716 (merged engine). "192 spec overlay patterns" in the README is badly stale.

> **Picker truth caveat:** the user-facing picker/search run off the STATIC JS catalogs (`paint-booth-0-finish-data.js`, ~721 KB, + SPECIAL_GROUPS), reconciled to registry truth at runtime. A finish registered in Python but absent from the static catalog is INVISIBLE in the UI. So "catalog scale" as the *user sees it* is governed by the JS catalog, not the raw registry count.

### Version / release status

- **Code version: `8.0.3`** (verified `electron-app/package.json:3`; surfaced via `app.getVersion()`). The "**8.0.3-beta**" label in memory is the **R2 release-channel tag** (the build shipped on the beta channel on R2, 2026-06-17), not a string baked into `package.json` — package.json carries the plain `8.0.3`.
- Distribution: Windows-only, ships as a single all-in-one R2 download with Electron auto-update from R2 (every finish baked in, 7.0.8+). License is UNLICENSED/private during the "Gold to Platinum" phase.

### Verification notes

- ✅ Verified directly in code: `server_v5.py` is the Flask entry point + port 59876; `main.js` spawns it; `package.json` version 8.0.3 and the "iRacing Spec Map Tool" description; `shokker_engine_v2.py` size ~1.32 MB; all catalog counts (booted the engine on 2026-06-29).
- ⚠️ Flagged as stale/contradictory: README's "3D-aware canvas / real-time PBR preview" and "192 patterns / 30+ v6.1 finishes" (older marketing — contradicts the binding spec-map identity and NO-3D-preview directive).
- ⚠️ Could not fully verify from first principles: the exact RGBA→channel byte order of the exported iRacing spec TGA (docs consistently describe three authored channels M/R/Cc; the precise R=?, G=?, B=? mapping should be confirmed against the export code before relying on it).

---

<a id="architecture-render-pipeline"></a>

## Architecture & Render Pipeline

This is the end-to-end map of how Shokker Paint Booth (SPB) boots, where finishes are defined, and how a zone payload becomes a paint PNG + spec PNG. All file:line refs below were verified against the live tree at `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum` on this pass (engine monolith dated Jun 23, JS dated Jun 28–29). Where a number comes only from memory and could not be re-confirmed, it is flagged.

### 1. The 30,000-ft shape

SPB is an **Electron desktop shell** (`electron-app/`) that **spawns a local Flask/Python server** (`server_v5.py`) and points a Chromium window at `http://localhost:59876/`. There is no cloud render — everything runs on the buyer's machine. Two languages, one data contract:

- **Python** = the render engine + registries (the truth about what a finish *is*).
- **Browser JS** (`paint-booth-*.js`) = the UI, the zone editor, the picker, and the static finish *catalog* (the truth about what the UI *shows*).
- The two are bridged by `/api/finish-data` (registry → catalog merge) and `/preview-render` + `/render` (zones → engine).

The single most important architectural gotcha lives in that split: **the picker/search run off static JS arrays, not the live registry** (see §6). Registering a finish in Python alone leaves it invisible.

### 2. Electron → Flask boot

`electron-app/main.js`:
- `startServer(port)` (`main.js:1960`) spawns the server. It prefers the **bundled Python** (`getBundledPythonPath()` → `process.resourcesPath/server/python/python.exe` or `__dirname/server/python/python.exe`, `main.js:1260`), else falls back to system `python`. Args are always `['server_v5.py']`, cwd = `getServerDir()` (packaged `resourcesPath/server`, else dev `__dirname/server`, resolved by presence of `server_v5.py`, `main.js:1277`).
- Env injected: `SHOKKER_PORT=<port>` and `SPB_USER_IMPORTS_DIR=<APP_DATA>/user_imports` (`main.js:1972`).
- Port negotiation: `findFreePort` tries `[59876, 59877, 59878, 59879, 60876, 60877, 60878, 60879, 61876, 0]` (`main.js:1939`); default 59876.
- Readiness: it polls a raw TCP socket to `127.0.0.1:port` every 250 ms, resolves on connect, and has a **60 s timeout** that resolves-anyway if the process is still alive (`main.js:2026`–2048).
- Zombie/orphan hygiene: kills `shokker-paint-booth-v5.exe`, sweeps orphan `python.exe` whose command line contains `server_v5.py` (`main.js:1239`), and kills whatever owns `:59876` via `killPortHolders` — because a relaunch reconnecting to a stale engine on 59876 was a real failure mode (`main.js:1064`).

`server_v5.py` startup sequence (documented in its own header `server_v5.py:14`–25, verified):
1. `_clear_pycache()` (`server_v5.py:81`, called at `:106`) — walks the module root and `rmtree`s every `__pycache__`. This exists because the auto-updater rewrites `.py` but not `.pyc`, causing phantom AttributeErrors (see `[[spb-network-drive-cache]]`).
2. `from config import CFG` (`:112`) — single source of truth for port/paths/debug/version.
3. `import engine` + `import shokker_engine_v2 as _legacy_engine` (`:116`–118). **Importing `engine.registry` builds every registry as an import side-effect** (§4).
4. `_sync_final_legacy_registries()` (`server_v5.py:126`, called `:143`) — re-points the module-level `BASE_REGISTRY/PATTERN_REGISTRY/MONOLITHIC_REGISTRY/FINISH_REGISTRY/FUSION_REGISTRY` at the **final** loaded `_legacy_engine.*` dicts. The comment at `:120` warns: importing registry globals directly here can capture a *half-built* snapshot (the monolith does final catalog wiring after a circular merge), which would make shipping IDs fall back to generic looks.
5. `full_render_pipeline = _legacy_engine.full_render_pipeline`, `preview_render = _legacy_engine.preview_render` (`:150`–151) — the V5 server **reuses the legacy monolith's pipeline functions unchanged**.
6. Flask app + CORS (`:154`), rotating `server_log.txt` (5 MB × 3, `:172`), observability hooks (`:196`).
7. **Route inheritance from `server.py`**: `server_v5.py:838`–874 iterates `server.app.url_map`, re-binds every rule except `{'/', '/build-check', '/status', '/<path:filename>'}` under a `*_v4` endpoint suffix, and **hard-fails boot if fewer than 50 routes inherit** (`:867`). So `/render`, `/preview-render`, `/config`, `/api/swatch/*` etc. are *defined in `server.py`* and merely re-exported by `server_v5.py`. This is why both files matter.
8. `__main__` (`:955`): `clean_boot()` frees the port (unless `SHOKKER_NO_CLEAN=1`), `_spb_pick_runtime_port()` picks an actual port, writes `.server_port`, runs `server_health.run_startup_checks`, prints the banner, launches the **boot swatch warm** thread (`:1013`, disable with `SPB_NO_BOOT_SWATCH_WARM=1`), and `app.run(host, port, debug=CFG.DEBUG, threaded=CFG.THREADED)`.

Env switches worth knowing: `SHOKKER_PORT` (pin port), `SHOKKER_DEV=1` (hot reload + verbose; `START_V5_DEV.bat` sets this on port 59877), `SHOKKER_NO_CLEAN=1` (second instance), `SPB_NO_BOOT_SWATCH_WARM=1` (`START_SERVER.bat` sets this for normal painting). **Dev runs from the repo ROOT** via `START_SERVER.bat`/`SPB_FRESH_START.bat` (cwd = repo root, NOT `electron-app/server`), which is why dev edits to root `.py`/`.js` take effect without a sync (`[[spb-rework-base-vs-monolithic]]`).

### 3. The static script load order (browser side)

`paint-booth-v2.html` loads the JS in a strict, dependency-ordered sequence. Verified tags + cache tokens:

| Order | File | Token (current) | Role |
|---|---|---|---|
| 0 | `paint-booth-0-finish-data.js` | `?v=spb-souls30-20260612` | **SINGLE SOURCE OF TRUTH** for the static catalog arrays: `BASES` (`:15`), `PATTERNS` (`:908`), `MONOLITHICS` (`:1652`), `SPECIALS_SECTIONS` (`:1548`), `SPECIAL_GROUPS` (`:1614`), `BASE_GROUPS` (`:3591`), `PATTERN_GROUPS` (`:3637`), and the `pruneUnresolvedSpecialGroups()` IIFE (`:4021`). |
| 0 | `paint-booth-0-finish-tags.js`, `-0-finish-metadata.js`, `-0-catalog-scorecard.js`, `-0-picker-owner-ratings.js` | mixed | fuzzy search tags, rich metadata, scorecard, owner star ratings. |
| 1 | `paint-booth-1-data.js` | `?v=spb-registry-sync-20260611` | TGA decoder (`decodeTGA`, `:91`), `loadDecodedImageToCanvas` (`:187`), and the registry→catalog merge `_mergeFinishDataFromServer` (`:255`). Depends on the 0-files' arrays existing. |
| 2 | `paint-booth-2-state-zones.js` | `?v=spb-oom-fix-20260628` | zone state model, picker/zone-popout rendering, swatch versioning (`_SHOKKER_SWATCH_V`), flash/material map overlays. |
| 3 | `paint-booth-3-canvas.js` | `?v=spb-smarttga-...-20260629` | canvas/region painting, zoom, eyedropper, masks. (Preceded by `js/canvas/dispatch.js` — SPB-93 Zone vs Layer routing.) |
| 4 | `paint-booth-4-pattern-renderer.js` | `?v=spb-oom-fix-20260628` | client-side pattern preview rendering. |
| 5 | `paint-booth-5-api-render.js` | `?v=spb-oom-fix-20260628` | builds the zone payload + calls `/preview-render` and `/render`. (Preceded by `spb-recipe-card-logo.js`.) |
| 6 | `paint-booth-6-ui-boot.js` | `?v=spb-wholecar2-20260623` | top-level UI bootstrap/wiring. |
| 7 | `paint-booth-7-shokk.js` | — | SHOKK-the-World / Shokk Drop features. |
| 8 | `paint-booth-8-autoseparate.js` | — | flat-TGA auto-separation (numbers/sponsors/paint). |

**Cache-token rule** (`[[spb-css-cache-tokens]]`): Electron will serve stale JS unless the `?v=` token is bumped (or a new tokened filename is added). Note `server_v5.py:388` serves `.js/.css` with `Cache-Control: no-store` (always-fresh) — but the *packaged* Electron build and the browser disk cache still rely on the token, so always bump it.

### 4. The registries (Python truth)

`engine/registry.py` is the declared "ONLY place where finish IDs map to functions" (`:1`). `_build_registries()` (`:37`) runs once at import (`:603`) and returns five dicts:

- **`BASE_REGISTRY`** — combinable base finishes. Source: `engine/base_registry_data.py` `BASE_REGISTRY` (`:330`, "96 bases") + `shokker_engine_v2.BLEND_BASES` (10). **Entry shape = a dict**, e.g. `"ceramic": {"M":10,"R":15,"CC":16,"paint_fn":paint_none,"desc":...,"perlin":True,"noise_M":10,...}` (`base_registry_data.py:335`). Optional keys: `base_spec_fn` (e.g. `piano_black` → `spec_cg_glass`, `:347`), perlin/noise dials. The base path reads `M/R/CC` to synthesize the spec and calls `paint_fn` for color.
- **`PATTERN_REGISTRY`** — overlay patterns. Entry = a dict with `paint_fn`/`texture_fn`/`image_path`. Built from `engine.pattern_registry_data` + `engine.pattern_expansion.NEW_PATTERNS` + staging decades + a **dynamic filesystem scan** of `assets/patterns/**` and `basespatterns_examples/patternexamples/**` (registers any `.png/.jpg` not already claimed procedurally, `registry.py:110`–191) + a 23-id case-collision dedup (`registry.py:588`).
- **`MONOLITHIC_REGISTRY`** — one-shot finishes (Color Shift, Fusions, FABLE, cultural sets, COLORSHOXX, Living, Spectrum, FRACTURED, etc.). **Entry = a `(spec_fn, paint_fn)` tuple.**
- **`FINISH_REGISTRY`** — legacy IDs (back-compat, PATH 3).
- **`FUSION_REGISTRY`** — the fusion subset of monolithics (also merged into `MONOLITHIC_REGISTRY`).

**Expansions self-load on import.** After the base/mono/fusion seed, `_build_registries()` runs ~30 guarded `try/import; reg.update(...)` blocks — each expansion module exposes a dict (e.g. `FABLE_MONOLITHICS`, `LFR_MONOLITHICS`, `LIVING_FINISH_REGISTRY`, `HYPERFLIP_MONOLITHICS`, `VIVA_MEXICO_MONOLITHICS`) or an `integrate_*(reg_mod)` function (paradigm, color_clash). Each is fail-soft (prints a warning, continues) EXCEPT `pattern_expansion` which `raise`s (`:69`). Adding a finish family = drop a module that exports a `*_MONOLITHICS` dict and add one `mono_reg.update(...)` block here. The final line prints `[V5 Registry] READY - N bases, N patterns, N monolithics (N fusions)`.

CS overrides (`registry.py:197`–305): `cs_*` adaptive/preset/duo entries are replaced with `engine.color_shift` V5 implementations, then `engine.micro_flake_shift` converts CS-duos to micro-flake versions. The order matters — later `.update()`s win.

### 5. The render path (zones → engine → PNGs)

**Routes** (defined in `server.py`, inherited by `server_v5.py`):
- `POST /preview-render` (`server.py:4181`) — low-res live preview, returns base64 PNGs inline (no job dir). Rate-limited to 10/s/IP (`:4205`), single-flight via `_preview_render_lock` with a 2 s acquire timeout + `_preview_abort` cooperative cancel (`:4213`). Body: `{paint_file | paint_image_base64, zones:[...], seed, preview_scale (0.25 default), changed_zone, zone_hashes, force_refresh, import_spec_map}`. Calls `engine.preview_render(...)` (`server.py:4636`). Zones run through `_convert_zone_keys` + `_repair_base_overlay_pattern_reactive_payload` (`:4231`) and are capped at `MAX_ZONES_PER_REQUEST` (`:4249`). It dumps the exact payload to `_LAST_PREVIEW_PAYLOAD.json` for offline replay (`:4239`, the live-preview whole-car-tiling diagnostic).
- `POST /render` (`server.py:4765`) — full-res job; calls `engine.full_render_pipeline(...)` (`server.py:5082`), writes to a job directory.

**Three pipeline entry points in the monolith** (`shokker_engine_v2.py`):
- `build_multi_zone(...)` (`:16968`) — the core multi-zone compositor (signature at `:16968` lists ~30 params incl. `zones, seed=51, import_spec_map, decal_*, abort_event, progress_callback, generate_normal_map, export_layers`).
- `preview_render(...)` (`:19490`).
- `full_render_pipeline(...)` (`:21620`).

**Per-zone dispatch (the PATH tree)** inside the compositor — a zone's `base`/`finish`/`finish_colors`/`pattern` decide the path (verified labels):
- **PATH 0** — `custom_*` mix finishes (`:17812`).
- **PATH ZSPEC** — imported zone spec source (`:17930`).
- **PATH 1 (compositing)** — `base` + optional pattern/pattern-stack. Logs `[... ] => base + pattern (...) [compositing]` (`:18289`). Calls `compose_finish`/`compose_paint_mod` (single pattern, `:18367`/`:18370`) or `compose_finish_stacked`/`compose_paint_mod_stacked` (multi, `:18267`). Each zone uses `seed + i*13`. This is the path for everything assigned as a **base** (incl. rework finishes — see §7). There is a fast-path optimizer for flat/bbox-noise bases (`:18315`–18362).
- **PATH 4 (client gradient)** — `grad_/gradm_/grad3_/ghostg_/mc_` with client `finish_colors` (`:18374`); client colors override the registry.
- **PATH 2 (monolithic)** — `finish in MONOLITHIC_REGISTRY` (`:18397`). Pulls `spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]` (`:18400`). Logs `[...] => finish (...) [monolithic]` (`:18412`). Renders inside the zone mask via `placement_context` (`set_zone_placement`, `:18477`) so scale/rotate/offset transform the plate and it never paints the full canvas.
- **PATH 3 (legacy)** — `FINISH_REGISTRY` (`:18799`).
- **PATH 4 (generic fallback)** — client-defined finish with color data (`:18815`).

**Function signatures (the contract):**
- Monolithic **`spec_fn(shape, mask, seed, sm)`** → packed **HxWx4 uint8** (verified call sites `shokker_engine_v2.py:18482`/`18496`/`18496`; also `server_v5.py:536`). `sm` = spec strength multiplier.
- Monolithic **`paint_fn(paint, shape, mask, seed, pm, bb)`** → HxWx3 float in [0,1] (`:18485`/`18498`; `server_v5.py:541` calls `paint_fn(paint, shape, mask, seed, 1.0, 0.10)`). `pm` = pattern/paint mix, `bb` = base bleed.
- Base **`paint_fn`** is the SAME signature as monolithic paint. Base **`base_spec_fn(shape, seed, sm, base_m, base_r)`** returns a **3-tuple `(M, R, Cc)`** of HxW arrays 0–255 (per `[[spb-rework-base-vs-monolithic]]`; the 5-arg form was not directly re-verified this pass — confirm before relying on it).

### 6. The spec map contract (the actual product)

SPB is a **spec-map app** — the spec PNG is the deliverable, not a 3D preview. The spec is an **HxWx4 uint8 RGBA** array (`engine/SPEC_MAP_REFERENCE.md`, enforced in `_enforce_iron_rules`, `shokker_engine_v2.py:185`):

| Channel | Meaning | 0 | 255 |
|---|---|---|---|
| **R = M** | Metallic | dielectric/dark | chrome-like |
| **G = R** | Roughness | smooth/glossy | rough/matte |
| **B = CC** | Clearcoat | **16 = MAX clearcoat** | 255 = dullest; **never output 0–15** |
| **A** | spec mask | — | 255 |

Iron rules (`_enforce_iron_rules`, `:185`): where CC>0 force `>= CC_FLOOR`(16); roughness floor on non-mirror pixels (`M < CHROME_M_THRESHOLD` → `R >= ROUGHNESS_FLOOR_NONMIRROR`); NaN/Inf scrub; clip 0–255. Engine default neutral spec = **M=5, R=100, CC=16, A=255** (`_default_spec_array`, `:219`; outside-mask M default `SPEC_DEFAULT_OUTSIDE_M`). The "16 = max clearcoat, 17–255 = progressively less" inversion is the #1 thing that trips up new spec authors — high CC numbers are DULLER, not glossier.

### 7. The cross-cutting traps (each is a "fix every copy" lesson)

These four memories all describe the SAME failure shape — **an override/bypass applied to one of N duplicated locations** — and are the things most likely to bite a future agent:

1. **Static catalog vs registry** (`[[spb-static-catalog-vs-registry]]`). The picker, category lanes, and search read the static JS arrays in `paint-booth-0-finish-data.js`. Registering in `MONOLITHIC_REGISTRY` alone = **invisible** in the UI. The bridge is `_mergeFinishDataFromServer` (`paint-booth-1-data.js:255`): it fetches `/api/finish-data` (which serves `MONOLITHIC_REGISTRY` keys as `specials`, `server_v5.py:589`), treats the `specials` payload as **registry truth** — `_merge(MONOLITHICS, data.specials, 'monolithic', allowAdd=true)` (`:299`), **prunes** static IDs no longer in the registry (`:309`), and **regroups** any `SPECIAL_GROUPS` whose name matches a server category (`:323`). Bases/patterns stay curated (`allowAdd=false`, `:297`). **WRONG-ARRAY TRAP**: new `{id,name,desc,swatch}` rows MUST land inside the `MONOLITHICS` array (or be `MONOLITHICS.push(...)`-ed before `pruneUnresolvedSpecialGroups()` at `:4021`); rows that slip into the adjacent `SPEC_PATTERNS` array register server-side but render 0 items in the picker. New category = add the group name to `SPECIALS_SECTIONS` (`:1548`) once. Swatch staleness has a second layer — the browser HTTP cache keyed by `_SHOKKER_SWATCH_V`/`/api/swatch-version` (the engine fingerprint).

2. **Base vs monolithic dual-registration** (`[[spb-rework-base-vs-monolithic]]`). The ~74 colorshift-rework finishes (e.g. `butterfly_monarch`) live in BOTH `MONOLITHIC_REGISTRY` and `BASE_REGISTRY`. The picker offers them as **bases**, so they render via PATH 1 (compositing), which reads `BASE_REGISTRY[id]['base_spec_fn']`/`['paint_fn']` — NOT the monolithic. An override that only patches `MONOLITHIC_REGISTRY` makes the audit swatch (monolithic) show the new look while the booth (base) renders the old one. **Rule: an override must cover every registry the ID lives in.** Diagnose via the `[compositing]` vs `[monolithic]` tag in the render log, or `/api/swatch/base/<id>` vs `/api/swatch/monolithic/<id>`.

3. **Three duplicate monolithic render blocks** (`[[spb-authored-spec-triple-block]]`). The PATH-2 monolithic code is **copy-pasted into all three pipeline functions**: `build_multi_zone` (authored bypass at `shokker_engine_v2.py:18428`, `_sm_effective` at `:18440`, post-pass guard `if not _mono_is_authored` at `:18524`), `preview_render` (`:20322`/`:20328`), and `full_render_pipeline` (`:21009`/`:21015`). (Memory's older line numbers ~17772/19682/20357 are stale — file has grown; the *count* of three and the *functions* are confirmed.) A fix applied to one block leaves the other two wrong. The authored-spec case: `is_authored_spec(finish_name)` (from `engine.paint_v2.user_imports`, populated only by `reload_user_imports()` reading manifest `spec_mode=="authored_set"`) forces `sm=1.0` and skips `_apply_base_spec_strength_to_zone_spec`, so the guest's exact uploaded M/R/CC channels export verbatim instead of being multiplied (the 136→237 roughness boost bug).

4. **Mono 2nd-base phase offset** (`[[spb-mono-2nd-base-phase-offset]]`). A monolithic used as a 2nd base lines up in SIZE but not POSITION because the rebuilt-pattern wrapper derives a spatial **phase from the seed** (`_spb_rebuilt_tech_pattern_value` ~`:10564`, `_spb_rebuilt_pattern_value` ~`:12760`), and the mono 2nd-base's geometry seed is offset (`seed + i*13 + abs(hash(second_base))%10000` at `:18013`; `seed + i*13 + 7777` at `:18126/18142`; `(seed+999)+...` in `engine/compose.py:2993`) while the primary pattern uses plain `seed + i*13`. Same-size lattice, translated. Do not "fix" (re-align) without owner sign-off — finishes change only on request.

### 8. The 2-copy structure (root ↔ electron-app/server)

`[[spb-2copy-consolidation]]` — verified. As of 2026-06-09 SPB is **2-copy**, not 3-copy (the vestigial `electron-app/server/pyserver/_internal` PyInstaller mirror was deleted, ~585 MB; it was `!pyserver/**`-excluded from the installer and shipped to nobody).

- **Source of truth = repo root.** The single mirror = `electron-app/server/` (the tree packaged into the installer). Confirmed: `scripts/runtime-sync-manifest.json` `"targets": ["electron-app/server"]` (exactly **1** target).
- Sync: `node scripts/sync-runtime-copies.js --write` copies root → `electron-app/server` (`--check` exits 0/1 on drift). The manifest is fully `targets`-driven, and it now mirrors the 4 hot-path Python modules (incl. `engine/base_registry_data.py`) plus image-authored cultural texture directories so backend edits reach the Electron runtime per-edit, not just per-build.
- **Build gate**: `electron-app/copy-server-assets.js` re-runs a check after its sync-write and **HARD-FAILS the build** if any managed-code mirror is still drifted (a silently-failed/locked copy can no longer ship). `engine/` drift stays owner-managed (check-only), not a build blocker.
- **Dev vs packaged**: the dev server runs from ROOT (`START_SERVER.bat`/`SPB_FRESH_START.bat`, cwd=root), so root edits are live immediately — a Python change still needs a **server restart**; a JS/CSS change needs a **cache-token bump**. For the packaged app you must `sync-runtime-copies --write` (or rebuild) so `electron-app/server` carries the change. Use the `spb-ship-check` skill, which does parse-check + gate battery + drift-verified sync + token bump in one ritual.

### 9. Quick "where do I touch X" index

- New monolithic finish → add `(spec_fn, paint_fn)` to a `*_MONOLITHICS` dict + a `mono_reg.update()` block in `engine/registry.py`, AND add the `{id,name,desc,swatch}` row to the `MONOLITHICS` array (+ a `SPECIALS_SECTIONS`/`SPECIAL_GROUPS` lane) in `paint-booth-0-finish-data.js`. Sync + token bump.
- New base → `engine/base_registry_data.py` (`{M,R,CC,paint_fn,...}`) + `BASES`/`BASE_GROUPS` in finish-data.js.
- Spec/render behavior → the monolith `shokker_engine_v2.py` (remember: edit ALL THREE PATH-2 blocks; base path = `engine/compose.py`).
- Spec channel meaning → `engine/SPEC_MAP_REFERENCE.md` + `_enforce_iron_rules` (`shokker_engine_v2.py:185`).
- A finish renders the wrong look only on the car (not the swatch) → it's the base/compositing path, not the monolithic (§7.2).

**Verification caveats:** memory line numbers for the three monolithic blocks and the mono-phase seeds were re-checked and several have shifted (the engine file is now ~1.3 MB / dated Jun 23) — the *current* refs above were grepped this pass. The base `base_spec_fn(shape, seed, sm, base_m, base_r)` 5-arg signature comes from memory and was not independently re-derived from a call site in this session; verify against `engine/compose.py` before depending on the exact argument order.

---

<a id="repository-file-map"></a>

## Repository & File Map

This is the canonical directory map of Shokker Paint Booth (SPB): an Electron desktop shell wrapping a Python/Flask render server that authors iRacing livery **spec maps** (the R/G/B `_spec.tga` metalness/roughness/clearcoat channels) and finish/paint designs. Read this first to know *where* anything lives; deeper subsystem behavior is in the other wiki sections.

### 0. Canonical location & the two-copy rule (READ FIRST)

- **Repo root (the only live tree):** `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum` (verified `SPB_CANONICAL_WORKSPACE.md`). The old `E:\Koda\...` and the sibling `C:\DRIVE E BACKUP\KODA ...` / `... UNLIMITED` folders are **stale backups — do not edit or run from them**.
- The shell cwd resets to `C:\Users\Ricky's PC` between commands, so **always use absolute paths** (memory `spb-active-project-path`).
- **SPB ships as a 2-copy tree** (memory `spb-2copy-consolidation`): the authoritative source is the repo **root**, and a *mirror* of all runtime-managed code lives under **`electron-app/server/`** (the dir that actually gets packaged). Every front-end JS, `engine/`, `server_routes/`, `server.py`, etc. exists **twice** — e.g. `./paint-booth-3-canvas.js` AND `./electron-app/server/paint-booth-3-canvas.js`. **Edit the root copy, then sync** via `scripts/sync-runtime-copies.js` (driven by `scripts/runtime-sync-manifest.json`; docs in `scripts/RUNTIME_SYNC.md`). The packaging step `electron-app/copy-server-assets.js` **hard-fails the build on managed-code drift**. The old vestigial 3rd copy (`electron-app/server/pyserver/_internal`) was deleted — do not recreate it.

### 1. Top-level layout

```
Shokker Paint Booth Gold to Platinum/
├─ server.py                 # 8,586 lines / 413KB — the Flask app + ALL @app.route handlers
├─ server_v5.py              # 43KB — REAL entry point (V5). Inherits server.py, adds V5-only routes
├─ server_health.py          # tiny standalone health probe server
├─ shokker_engine_v2.py      # 1.3MB MONOLITH — legacy finish engine + MONOLITHIC_REGISTRY (L9781)
├─ config.py                 # paths, ports, feature flags, load_config/save_config
├─ deploy_r2.py              # R2 release uploader (--hold-latest/--only-latest)
├─ engine/                   # the V5 render engine (registry, paint, spec, compositing)
├─ server_routes/            # ~45 register_*_routes(app,…) blueprint-style modules
├─ js/                       # extracted front-end modules (zones/, features/, canvas/, finishes/, diagnostics/)
├─ paint-booth-*.js          # the 17 monolithic front-end script files (loaded in order 0→8)
├─ paint-booth-v2.html       # 322KB — the main app SHELL (loads every script; spec-sculpt.html = 2nd page)
├─ scripts/                  # 353 files — gates, harnesses, audit builders, metric scorers, sync
├─ tests/  tests_v2/         # pytest suites (144 + 20 files)
├─ docs/                     # ~90 design/process docs (ARCHITECTURE, RELEASE_PROCESS, AUDIT_PAGE_SPEC…)
├─ electron-app/             # the Electron wrapper + the server/ MIRROR + build scripts
├─ assets/ decals/ helmets/ suits/ fonts/ leagues/ palettes/ psd_templates/ text_templates/
├─ image_forge/              # drop-in art → verbatim paint finishes
├─ _dev_asset_masters/       # dev-only master textures (NOT shipped)
├─ _car_intel/  _logo_data/  # AI/ML training data (car masks, CLIP logo embeddings)
├─ _gpuenv/  _clipenv/       # Python 3.13 venvs for GPU/AI models (SAM, CLIP, easyOCR)
├─ output/  thumbnails/  swatches/   # render outputs + baked preview caches
└─ (many _scratch / _audit / handoff dirs — see §10 DEAD/IGNORE)
```

Root also holds a large number of **`_*.py` throwaway harness/probe scripts** (`_separate_image.py`, `_bignum_harness.py`, `_car_intel_*.py`, `_approach_*.py`, `_train_*.py`, `_specsculpt_*.py`, etc.) — these are one-off experiment drivers for the Smart-Separate / Car-Intel / Spec-Sculpt ML work, **not** part of the shipped app. The `rw_fableC_b*.py` and `shokker_*_expansion.py` files at root are legacy finish-pack generators.

### 2. The server (`server.py` + `server_v5.py` + `server_routes/`)

- **`server_v5.py` is the real entry point** (memory `spb-server-v5-topology`). It wires the V5 engine registries, **inherits `server.py`'s route handlers** (so edits to `server.py`/`server_routes/`/`engine/` are picked up), adds V5-only routes (`/api/registry-check`, `/api/finish-data`, `/api/health` → reports `version 7.0.0`, `/build-check`), `clean_boot`s the port, and binds `0.0.0.0:59876`. A bare `python server.py` reports `6.3.0-alpha`, is missing V5 routes, and if it grabs `127.0.0.1:59876` it **silently shadows** the real server — kill ghosts before restarting. Restarting Python is required for `.py` changes; HTML/JS only needs a reload + a bumped `?v=` cache token.
- **`server.py`** (L872 `app = Flask(__name__)`): one giant module that defines every render/IO route inline as `@app.route(...)` AND imports each `server_routes/*` module's `register_*_routes(app, …)` to attach the rest (pattern starts ~L1081 `register_asset_routes`, runs through ~L1517+). Key routes verified: `/api/auto-separate-livery` (L6513) and `/api/auto-layers` (L6621) — the flat-TGA Smart-Separate endpoints.
- **`server_routes/`** (~45 modules, each exposing `register_*_routes(app, …)` per `server_routes/__init__.py`). Notable owners:
  - Render/swatch: `swatch_routes.py`, `finish_viewer_render_routes.py`, `render_file_routes.py`, `render_monitoring.py`, `legacy_apply_finish_routes.py`
  - Catalog/lookup: `finish_catalog_routes.py` (also exports `id_to_display_name`), `finish_lookup_routes.py`, `finish_viewer_recent_routes.py`
  - Spec/export: `spec_channel_export_routes.py`, `photoshop_export_routes.py`, `photoshop_import_routes.py`, `psd_import_routes.py`, `psd_layer_export_routes.py`, `pattern_layer_routes.py`, `sun_sweep_routes.py`
  - Mega-features: `livery_designer_routes.py` (prompt→livery), `shokkerize_routes.py`, `photo_livery_routes.py`, `shokk_routes.py`, `guest_designer_routes.py`, `dual_shift_routes.py`, `custom_finish_mixer_routes.py`, `custom_finish_routes.py`
  - Infra: `static_pages.py` (serves `paint-booth-v2.html` etc.), `server_bootstrap.py`, `license_routes.py`, `config_routes.py`, `system_status.py`, `diagnostics.py`/`diagnostics_report_routes.py`, `observability.py`, `job_cleanup.py`, `cache_admin_routes.py`, `thumbnail_status.py`, `validation_routes.py`, `workbench_routes.py`, `june_audit_routes.py` (persists audit verdicts), `user_import_routes.py`, `paint_upload_routes.py`, `file_picker_routes.py`, `iracing_utility_routes.py`.

### 3. The engine (`engine/`)

The V5 render core. Subsystems:

- **`registry.py`** — the catalog hub. `_build_registries()` (L37) assembles and exports the five registries (L603): `BASE_REGISTRY` (combinable bases), `PATTERN_REGISTRY` (overlays), `MONOLITHIC_REGISTRY` (one-shot finishes — CS/fusions/effects), `FINISH_REGISTRY`, `FUSION_REGISTRY` (subset of monolithics). It pulls base data from `engine/base_registry_data.py`, patterns from `engine/pattern_registry_data.py`, and re-exports onto `engine.registry` + `engine.compose`. **Gotcha (memory `spb-rework-base-vs-monolithic`):** many finishes live in BOTH `MONOLITHIC_REGISTRY` and `BASE_REGISTRY`; an override must patch both. `engine.registry.BASE_REGISTRY` is a distinct object and `_ensure_expansions_loaded()` re-wires shokk bases on first render (memory `spb-wild-spec-lab`).
- **`shokker_engine_v2.py`** (root, 1.3MB) — the legacy monolith engine; defines stub finish fns then the big `MONOLITHIC_REGISTRY = {…}` literal (L9781) and patches chameleon/color-shift fns over the stubs. Still the source of truth for hundreds of monolithic finishes. There are **three duplicate monolithic render blocks** in here (memory `spb-authored-spec-triple-block`) — bypasses must be applied to all three.
- **`compose.py`** — the compositing path that stacks base + pattern + spec-pattern overlays, with spec caches (`_cached_base_spec_result` L146, `_get_cached_tex` L320, `_set_compose_profile` L291). This is where base/pattern blend and the spec channels combine.
- **`render.py`** — image-backed pattern loading/caching (`_load_image_pattern` L144, `_open_pattern_rgba` L121, `clear_image_pattern_cache` L27, LRU helpers).
- **`core.py`, `pipeline.py`, `spec_paint.py`, `overlay.py`/`overlay_context.py`** — core render orchestration, spec painting, overlay application.
- **`color_science.py`** (OKLab ramps, Beer-Lambert candy absorption, interference) + `color_shift.py`, `dual_color_shift.py`, `perceptual_color_shift.py`, `hyperflip_angle_reveal.py`, `micro_flake_shift.py`, `chameleon.py` — color/optical math.
- **`base_registry_data.py` / `pattern_registry_data.py` / `expansion_patterns.py` / `pattern_expansion.py` / `spec_patterns.py` / `spec_pattern_aliases.py`** — the data tables.
- **`engine/expansions/`** (51 `.py` modules) — **the dated finish/pattern drops**, each typically a generator that registers into the registries on import. Examples: `fractured_forge_2026.py`, `fractured_minds*_2026.py`, `fractured_souls_2026.py`, `fractured_themes_2026.py`, `spectrum_shift_2026.py`, `spectrum_arsenal_2026.py`, `flames_catalog_2026.py`, `anime_catalog_2026.py`, `neon_catalog_2026.py`, `optics_catalog_2026.py`, `materials_catalog_2026.py`, `gradients_*_2026.py`, `ghost_shift_2026.py`/`ghost_lab_2026.py`, `image_forge_2026.py`, `wild_spec_lab.py`, `color_science_rebuild_2026.py`, `colorshift_rework_2026.py`, `patterns_rebuild_2026.py`, plus `owner_review_*.py` audit-batch modules. Subfolder `wild_specs/` and data `grad_designs.json`.
- **`engine/paint_v2/`** (~90 files) — the **paint-design implementations** grouped by family: `flame_math.py`/`flames_2026.py`/`flame_spec*.py`, `fractured_math.py`/`fractured_motifs.py`, `candy_pearl_2026.py`/`candy_special.py`, `carbon_composite*.py`, `ceramic_glass*.py`, `metallic_*.py`, `chrome_mirror.py`, `neon_math.py`/`neon_underground.py`, `optics_math.py`, `materials_math.py`, `gradient_math.py`, `marble_onyx_2026.py`, `cultural_*.py` (Viva Mexico, Let Freedom Ring, Forbidden Dragon, Mortal/Money Shokk, Union Jacked, Rising Sun, Grunge), `money_shokk*.py`, `guest_designers.py`, `reference_pattern_plates.py`, and the **`user_imports*.py`** family (Shokk Drop / DNA import: `user_imports.py`, `user_imports_ingest.py`, `user_imports_spec_dna.py`, `user_imports_shokk_world.py`, etc.). Subfolder `exotic_packs/`.
- **`engine/paint_v3/`** — newer primitive layer: `primitives.py`, `paradigm_v3*.py`.
- **`engine/registry_patches/`** (19 `*_reg.py`) — registration shims that wire a `paint_v2` module's fns into the registries (`metallic_flake_reg.py`, `carbon_composite_reg.py`, `shokk_series_reg.py`, etc.).
- **`engine/spec_sculpt/`** — the **Spec Sculpt** subsystem (turn a flat livery into a layer-aware spec map). Key files: `core.py` (`load_paint_rgb_float01` L13), `smart_separate.py` (the OCR/flat-TGA separator: `separate_livery_layers_smart` L335, `_classify` L130, `_big_number_rescue` L253, `ocr_available` L42 — uses easyOCR), `car_layers.py`, `auto_sculpt_suggest.py`, `paint_trace.py`, `generate.py`, `fracture.py`, `catalog_blend.py`, `material_profiles.py`, `logo_clip.py` (CLIP logo detect), `smart_tga_gpu_bridge.py`, `sun_sweep.py`, `export.py`, `preview.py`, `presets*.py` (+ `presets_bespoke50_2026.py`, `presets_overnight_2026.py`), `spec_index.py`/`spec_index.json`, `world_denylist.json`/`world_denylist`. 
- **`engine/spec_pattern_families/`** — spec-pattern catalogs (`optical.py`, `mechanical.py`, `artistic.py`, `abstract_art.py`, `sparkle.py`, `weather_track.py`, `racing_pivot_v*.py`, `rate10_codex_*.py` audit loops, `ricky_reference_*.py`).
- Other engine: `asset_packs.py` (bundled-else-`%APPDATA%` resolver for excluded reference textures — memory `spb-finish-pack-downloader`), `gpu.py`, `livery_designer.py`/`livery_themes.py`/`photo_livery.py`/`shokkerize.py` (mega-feature backends), `recipe_kit.py`, `arsenal.py`, `prizm.py`, `paradigm.py`, `shokk_series.py`. Reference: `engine/SPEC_MAP_REFERENCE.md`.

### 4. Front-end: the `paint-booth-*.js` monoliths (loaded in numeric order)

These are concatenated, globally-scoped scripts (not modules) loaded by `paint-booth-v2.html` in order. The header comment in each states ownership (verified):

| File | Owns |
|---|---|
| `paint-booth-0-finish-data.js` (721KB) | **STATIC catalog source of truth** — `BASES`, `PATTERNS`, `MONOLITHICS` arrays + `PATTERN_GROUPS`/`SPECIAL_GROUPS`. **Registry registration alone = invisible; a finish must be here too** (memory `spb-static-catalog-vs-registry`). |
| `paint-booth-0-finish-tags.js` / `-finish-metadata.js` / `-catalog-scorecard.js` / `-picker-owner-ratings.js` | Fuzzy search tags, per-finish metadata, scorecard, owner ratings. |
| `paint-booth-1-data.js` | UI logic, **TGA decoder** (`decodeTGA`), `loadDecodedImageToCanvas`, runtime registry-truth sync `_mergeFinishDataFromServer`. |
| `paint-booth-2-state-zones.js` (1.15MB) | **App state + Zones**: `zones[]`, `selectedZoneIndex`, `init()`, zone list/detail render (`renderZones`, `renderZoneDetail`), setters (`setZoneBase`, `setZoneIntensity`, `duplicateZone`), favorites, finish library, config/autosave, script gen, undo (`pushZoneUndo`). Color-lock logic lives at top. **This is the live home of zone behavior — the `js/zones/*` modules are mostly dead (see §10).** |
| `paint-booth-3-canvas.js` (1.5MB) | File picker, **paint preview canvas**, eyedropper/brush/magic-wand/spatial mask tools, canvas zoom/pan (`canvasZoom`), Smart-TGA undo. |
| `paint-booth-4-pattern-renderer.js` (468KB) | **Client-side finish preview renderers** (`baseFns`/`patternFns`/specials) for the small swatch tiles (96/48/24px). Consults `window._fusionSwatchRenderers` first. |
| `paint-booth-5-api-render.js` (308KB) | **`ShokkerAPI`** (all server calls), the render pipeline (`doRender`, `safeDoRender`, preview), history gallery, and the single `_mapSpecPatternEntry` payload serializer. |
| `paint-booth-6-ui-boot.js` (298KB) | Modals (finish browser, compare, templates, presets), NLP chat bar, color harmony, keyboard shortcuts, and **boot** (`init()`, autoRestore, `ShokkerAPI.startPolling`). Runs last among 1–6. |
| `paint-booth-7-shokk.js` | Shokk-the-World / SHOKK DROP UI. |
| `paint-booth-8-autoseparate.js` | Auto-Separate (flat-image → numbers/sponsors/paint) panel glue. |
| `paint-booth-flashmap.js` / `-materialmap.js` / `-specstats.js` / `-layer-flow.js` | Flash-map overlay, material-map overlay, spec channel stats readout, PSD layer-flow import. |

`paint-booth-v2.html` is the shell (script tags ~L3054–3174, each with a `?v=` cache token that **must be bumped** for Electron to reload — memory `spb-css-cache-tokens`). `spec-sculpt.html` is the second page; `spec-sculpt-audit.html` its audit view.

### 5. Front-end: `js/` extracted modules

- **`js/zones/`** (73 files) — control-module extraction. **Only ~3 are ever `.install()`ed** (`SPBZoneSourceColorApplyControls`, `SPBZoneBaseOverlayHsbControls`, `SPBSwatchPopupFilterControls`); the other ~58 are **DEAD CODE** whose globals are assigned *inside* an un-called `install()` (memory `spb-dead-zone-modules`). **Editing a `js/zones/*` file to fix the UI does nothing — fix the monolith `paint-booth-2-state-zones.js` instead.** Loaded anyway via `<script>` tags at HTML L3060–3110+.
- **`js/features/`** — the mega-feature panels (live): `livery-designer.js` (Design-It prompt→livery), `shokkerize.js`, `photo-livery.js`, `smart-separate.js` (right-side flat-TGA Layers panel → numbers/sponsors/paint, calls `/api/auto-layers`), `smart-separate-studio.js` (guided pop-out workspace), `spec-sculpt-layers.js` (4-layer auto-build + car-detection showcase on the Spec Sculpt page), `experimental-menu.js`.
- **`js/canvas/`** — `dispatch.js` (canvas tool dispatch).
- **`js/finishes/`** — Shokk Drop / user-import / guest-designer UI (`user-imports.js`, `user-import-dna-*.js`, `user-import-gallery.js`, `finish-packs.js`, `guest-designers.js`).
- **`js/diagnostics/`** — `spb-diag-recorder.js`, `spb-diag-report.js`.

### 6. `scripts/` (353 files) — gates, harnesses, audit, build

- **Quality GATES** (the CLAUDE.md ship battery): `spb_uniqueness_gate.py` (≥80% structural sim = redo — the Uniqueness Law), `perf_gate.py` + `arm_perf_gate.py` (render-time budget), `mip_survival_gate.py` (track-distance detail survival), `spb_pattern_gate.py` (pattern anti-recycle), `fm_spec_physics_gate.py`, `spb_gestalt_gate.py`. JS release gate: `spb_release_gate_status.js`.
- **Harness:** `render_time_harness.py` (the canonical real-size 2048/1024 timing tool — 512² swatch timing once hid a 57s blowup; memory `spb-render-time-doctrine`).
- **Audit builders / metric scorers:** `build_june_audit.py` (the category-agnostic audit-page backend per `docs/AUDIT_PAGE_SPEC.md`), `build_audit_dashboard.py`, `build_auditv2_status.py`, `spb_catalog_scorecard.py`, `spb_pattern_quality_metric.py`, `spb_spm7/8/9/10_score.py`, `audit_render_perf.py`, `overnight_catalog_audit.py`, plus per-category `*_build_audit_page.py` and `*_audit_meta.json`.
- **Sync/build:** `sync-runtime-copies.js` + `runtime-sync-manifest.json` + `RUNTIME_SYNC.md` (root→`electron-app/server` mirror). Inventory: `docs/SCRIPTS_INVENTORY.md`.

### 7. Tests

- **`tests/`** (144 entries) — pytest regression suite. Anchors include `regression_flame_uniqueness_test.py` (the 4 fail-closed uniqueness/render/coverage/fineness tests — memory `spb-coverage-fine-nolazy-mandate`), `regression_base_scale_no_whole_canvas_tile_test.py`, `regression_spec_sculpt_api_test.py`, `regression_server_v5_route_inherit_test.py`, `regression_version_truth_contract_test.py`, `smoke_test.py`, `conftest.py`, `_runtime_harness/`. NOTE: `test_*.py` is broadly gitignored with negations (memory `spb-test-suites-gitignored`).
- **`tests_v2/`** (20) — newer contract tests: `test_registry_integrity.py`, `test_engine_render_contract.py`, `test_spec_sculpt_quality_gate.py`, `test_smart_separate_guided.py`, `test_autoprotect_textline.py`, `test_sync_integrity.py`, `test_route_registration_and_mirror.py`, snapshot `_spec_sculpt_snapshot.json`.

### 8. Asset directories

- **`assets/`** — shipped runtime assets: `defaults/` (`blank_canvas_2048_white.tga`, the Chevy-truck starter PSD), `patterns/`, `generated_pattern_overrides/`, `reference_textures/` (image-backed finish plates: `colorshoxx/`, `cultural/`, `grunge_fun/`, `guest_designers/`, `mortal_shokk/`, `pattern_plates/`, `spec_overlays/`), `branding/`.
- **`_dev_asset_masters/reference_textures/`** — dev-only high-res masters, **NOT shipped** (excluded by `copy-server-assets.js`; buyers download packs via `engine/asset_packs.py`).
- **`image_forge/`** — drop-in art workflow (`<finish_id>.jpg` → verbatim paint, spec derived from the image; memory `spb-image-forge`). Holds `_originals/`, `neon underground/`, `spectrum shift/`.
- **iRacing asset dirs:** `decals/`, `helmets/`, `suits/`, `fonts/`, `leagues/`, `palettes/`, `psd_templates/`, `text_templates/`, `basespatterns_examples/`.
- **Output/cache:** `output/` (`recent_renders/` ring-buffer for forensics, `shokker_spec_sculpt/`, `temp/`), `thumbnails/` (baked picker thumbnails), `swatches/`, `_workbench/` (the audit DB `spb_workbench.db`), `_audit/` (june-audit JSON verdicts).

### 9. AI/ML data + envs (Smart-Separate / Car-Intel)

- **`_car_intel/`** — per-car-model learned separation data (folders per iRacing car: `bmwm4gt3/`, `dallara/`, etc.) + `_layers_progress.jsonl`; the 67-car HTML library is `_car_intel/index.html` (memory `spb-car-intelligence-mission`).
- **`_logo_data/`** — CLIP logo-detector training data (`_emb_pos*.npz`/`_emb_neg*.npz` embeddings, `harvest*/`).
- **`_gpuenv/`** — a **Python 3.13 venv** (verified `pyvenv.cfg`) hosting the GPU/AI model stack (SAM, CLIP, easyOCR) used by the `_*.py` Smart-Separate experiments and `engine/spec_sculpt/smart_separate.py`. `_clipenv/` is a sibling venv for CLIP work. These are **environments, not source** — don't sync or ship them.
- Supporting scratch: `_smart_tga_runs/`, `_bignum_test/`, `_logo_bench/`, `_logo_review/`, `_sep_out_demo/`, `_shokk_trace/`, `_visual_diff/`.

### 10. DEAD / vestigial — ignore these

- **~58 of 73 `js/zones/*` modules** are dead (only 3 installed) — fix the monolith, not the module (§5; memory `spb-dead-zone-modules`). Specifically dead: `zone-detail-polish-controls.js` (`pulsePreviewFrame` no-op), `zone-config-zone-map-controls.js` (not loaded).
- **`js/swatch-popup*` / `js/state-zones` inline-vs-module split:** the standalone `js/zones` swatch-popup modules are dead; the live swatch-popup code is inline in `state-zones` (memory `spb-thumbnail-cache-chain`).
- **`.git.corrupt-backup-20260514-094027/`** — old broken git metadata, backup only.
- **Throwaway root files:** `C:tempv2_at_0081f1d.py` (0 bytes, junk filename), the dozens of `_approach_*.py`/`_run_*_bench.py`/`_gen_*.py`/`_train_*.py` experiment drivers, `rw_fableC_b*.py` legacy generators, and the many `SPB_AUDIT_*.html` / `_*_scratch/` / `_rw*_scratch/` audit artifacts.
- **Stale sibling project folders** under `C:\DRIVE E BACKUP\` and the `E:\Koda` tree (§0).

### Flags / could-not-fully-verify

- Exact line numbers were verified for: `engine/registry.py` (`_build_registries` L37, exports L603), `server.py` (`app=Flask` L872, route registers ~L1081+, `/api/auto-separate-livery` L6513, `/api/auto-layers` L6621), `shokker_engine_v2.py` `MONOLITHIC_REGISTRY` L9781, `engine/compose.py`/`render.py`/`spec_sculpt/core.py`/`smart_separate.py` def lines. Front-end file *ownership* is quoted from each file's own header comment.
- File **counts** (`js/zones`=73, `engine/expansions`=51 `.py`, `scripts`=353, `tests`=144, `tests_v2`=20, `thumbnails`=18, `swatches`=0) are point-in-time `ls | wc -l` snapshots and will drift.
- The memory index referenced a `spb-canonical-workspace` topic file; the actual files are repo doc `SPB_CANONICAL_WORKSPACE.md` and memory `spb-active-project-path.md` (used here). There is also a pre-existing `SPB_LIVING_WIKI.md` / `SPB_WIKI.html` at root that this wiki supersedes/extends.

---

<a id="build-run-test-deploy"></a>

## Build · Run · Test · Deploy

The complete operational runbook for Shokker Paint Booth (SPB). Everything here is verified against the live tree at `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum` as of the **8.0.3-beta ("Spring Catalogue")** release. Where a repo doc disagrees with reality, the doc is flagged as STALE — trust this section.

> **STALE-DOC WARNING (read first).** Two checklist files in the repo root predate the current delivery model and will mislead you:
> - `LAUNCH_CHECKLIST.md` still describes a **3-copy sync** (`electron-app/server/pyserver/_internal/`), a canonical `VERSION.txt`, and **GitHub** release hosting with code-signing. All three are wrong now: sync is **2-copy**, there is no `VERSION.txt` truth surface, delivery is **Cloudflare R2 + nsis-web**, and alpha/beta builds ship **unsigned** (SmartScreen "More info → Run anyway").
> - `WINDOWS_SANDBOX_TEST_GUIDE.md` (written for 6.2.0-alpha) tells you to set `<VGpu>Enable</VGpu>` and lists "black render window → VGpu not enabled" as a bug. **This is inverted for the current all-in-one build.** The heavy ~3.8 GB app makes Sandbox's vGPU virtualization force-close the session ("forcibly closed by host"); the fix is `<VGpu>Disable</VGpu>`. Use the live `SPB_<ver>_sandbox.wsb` files, not the guide's example XML.

---

### 1. Run in dev

The backend is a Flask app, `server_v5.py` (modular; the older monolith `server.py` still exists and shares the version/route contracts). Both serve the Paint Booth at `/` only.

- **Default backend (port 59876):** `START_SERVER.bat` — kills stale SPB Python listeners on the SPB port range, sets `SHOKKER_PORT=59876`, then runs `C:\Python313\python.exe server_v5.py`. Per `server_v5.py:10`, default URL is `http://localhost:59876`.
- **Dev/hot-reload backend (port 59877):** `START_V5_DEV.bat` — sets `SHOKKER_DEV=1` (Flask `use_reloader=debug`, so every `.py` save auto-restarts) and `SHOKKER_PORT=59877`. Use this when iterating on Python so you don't fight the production port.
- **Electron shell:** `cd electron-app && npm start` (= `electron .`). Or launch the installed `Shokker Paint Booth V6.exe`. The Electron `main.js` spawns its own bundled `server/python/python.exe server_v5.py` child — in dev you typically run the server yourself and point Electron at it.

**The owner's "Fresh Start" ritual — kills the orphaned backend.** The #1 dev/launch failure is an **orphaned old `server_v5.py` Python process still holding the TCP port**, so a new server silently binds elsewhere or the app talks to stale code. Two layers handle this:
- `SPB_FRESH_START.bat` (repo root): force-`taskkill /F /T` every SPB python/node/electron process whose command line matches this repo path or SPB markers (explicitly **excludes** `review_server.py`), sweeps the whole SPB port range (`59876–62876` set), deletes stale `scripts/.runtime-sync.lock` and `.spb_server.pid` markers, then calls `START_SERVER.bat`. It starts the **backend only** — you still launch the Electron app afterward.
- In the packaged app, `main.js:953` "PORT-OWNER KILL (TOTAL FRESH START core)" finds whoever owns the SPB port via `Get-NetTCPConnection`/`netstat` and `taskkill /F /PID <pid> /T` (the `/T` also kills the orphan's child Python), waits for the LISTENING entry to clear, then boots clean. This is what "Fresh Start now fully clears any hung/orphaned process" in the 8.0.3 notes refers to.

### 2. The `?v=` CACHE TOKEN rule (JS/CSS edits won't load in Electron without a bump)

Every `<link rel="stylesheet">` and many `<script>` tags in `paint-booth-v2.html` carry a `?v=<token>` cache-buster (verified: **117** versioned references; e.g. `css/ui-modernization-20260509.css?v=spb-toolbar-fix-20260616`, `js/diagnostics/spb-diag-recorder.js?v=spb-diag-recorder-20260604`). Electron/Chromium caches by the **full URL including the token**.

**Consequence:** editing a CSS/JS file's *contents* changes **nothing** in the running app on a plain refresh — even Ctrl+Shift+R can re-serve the tokened cache. To make a front-end change actually load you must do one of:
1. **Bump the `?v=` token** on that file's tag in `paint-booth-v2.html` (use a dated, intent-named token like `spb-cursor-fixed-20260616`), or
2. Add a **new** file linked LAST with a fresh token (the `css/zone-scroll-emergency.css?v=...` pattern), then
3. **Re-sync** (Section 3) so the token edit reaches the Electron mirror.

This has burned the project repeatedly ("my fix did nothing") — see the 8.0.1 brush-cursor and 8.0.2 toolbar fixes, both of which required token bumps to land. The `spb-ship-check` skill bumps the token as part of its ritual.

### 3. The 2-COPY runtime sync (root → `electron-app/server` only)

**Topology (since 2026-06-09):** ONE source of truth = repo root; ONE mirror = `electron-app/server/` (the tree packaged into the installer). The vestigial third copy `electron-app/server/pyserver/_internal/` was **deleted** and removed from the manifest — it was excluded from the installer (`!pyserver/**`) so it shipped to nobody and only created 3-way drift. **Do not recreate it.** The manifest confirms a single target: `scripts/runtime-sync-manifest.json` `"targets": ["electron-app/server"]`.

**Commands** (`scripts/sync-runtime-copies.js`, also exposed as npm scripts in `electron-app/package.json`):
- `node scripts/sync-runtime-copies.js --write`  → copy drifted files root → mirror (npm: `npm run sync-runtime` from `electron-app/`).
- `node scripts/sync-runtime-copies.js --check`  → report-only; **exits 1 on drift** (CI gate; npm: `npm run check-runtime-sync`).
- `--list` (enumerate pairs, no I/O), `--dry-run`, `--verify` (post-copy SHA-256), `--check-orphans` (exit 2 if stray mirror files), `--force` (override stale lock). Uses an O_EXCL lock file `scripts/.runtime-sync.lock`.

**Edit-then-sync workflow:** edit the file at **repo root**, then `--write`. Never hand-edit the `electron-app/server/` copy — it gets clobbered.

**The `js/features/*.js` manual-copy gotcha.** The manifest is a **hand-maintained allowlist** (`files[]`), not a glob. The four current feature modules ARE listed — `js/features/livery-designer.js`, `js/features/shokkerize.js`, `js/features/photo-livery.js`, `js/features/experimental-menu.js` (manifest lines 218–230). **If you add a NEW `js/features/*.js` (or any new front-end/Python module), it will NOT sync until you add it to `runtime-sync-manifest.json` `files[]`.** A new file silently absent from the mirror is the classic "works in dev, missing in the packaged build" bug. (`engine/` is walked as a `check_only_directories` tree: drift there is *reported* but never auto-copied — converging finish-output modules is the owner's manual call.)

**Build HARD-FAILS on managed-code drift.** `electron-app/copy-server-assets.js` runs `prebuild`. It does `syncRuntimeCopies({write:true})` (line ~390), then **re-runs a check-only pass** and if `writableDriftCount > 0` it prints `[copy-server] FATAL: ... managed-code mirror file(s) STILL drifted` and `process.exit(1)` (lines ~400–407). So a copy that silently failed or was file-locked can no longer slip into a release — the build dies instead.

### 4. The GATE BATTERY (quality gates before "done")

Run before declaring any new/rebuilt finish, pattern, or spec finished (CLAUDE.md rule #0; automated by the `spb-finish-gate` skill). Live scripts under `scripts/`:
- **Uniqueness Law** — `python scripts/spb_uniqueness_gate.py --module <module>` (or `--ids a,b,c`); `--report` lists existing duplicate pairs as the rebuild worklist. Fails any finish ≥0.80 structural similarity to a catalog finish.
- **Render-time budget** — `scripts/render_time_harness.py` (≤3 s @2048; ~1 s/finish ideal). Verify at REAL sizes — a 512² swatch hid a 57 s blowup.
- **MIP-survival (track-distance detail)** — `scripts/mip_survival_gate.py`.
- **Pattern anti-recycle** — `scripts/spb_pattern_gate.py`. **Perf gate** — `scripts/perf_gate.py` / `arm_perf_gate.py` (the gate is built but must be *armed* to block).
- **Reference implementation** (the model the catalog gate extends): `tests/regression_flame_uniqueness_test.py` — four fail-closed checks: uniqueness <0.80, render <3 s @2048, coverage ≥ MIN_COVERAGE, fineness ≥ MIN_FINENESS, auto-gating new structures.
- **Backend regression suite:** `pytest` from repo root. Sync-integrity is covered by `tests_v2/test_sync_integrity.py`, `tests_v2/test_route_registration_and_mirror.py` (638 passed / 5 skipped baseline).

### 5. VERSION-BUMP CHECKLIST (all surfaces move together)

A mismatch produces the "app vX vs UI vY" toast and a stale version pill. The canonical value for 8.0.3 is `8.0.3-beta` (note: package.json uses the bare semver `8.0.3` because electron-updater requires it). **Verified surfaces:**

| # | Surface | File:line (verified) | 8.0.3 value |
|---|---------|----------------------|-------------|
| 1 | Auto-update semver (drives the feed) | `electron-app/package.json` `"version"` (line 3) | `8.0.3` |
| 2 | Server version (UI-facing) | `server.py:81` `SPB_VERSION` | `8.0.3-beta` |
| 3 | Pill / `/status` / `/build-check` | `config.py:213` `VERSION` | `8.0.3-beta` |
| 4 | Client constant | `paint-booth-5-api-render.js:699` `CLIENT_VERSION` | `8.0.3-beta` |
| 5 | Truth-contract test | `tests/regression_version_truth_contract_test.py` | asserts all four |

**Plus the build codename** (the test asserts it too): `config.py:214` `BUILD_TAG` and `server.py:83` `SPB_BUILD_ID`, both `"Spring Catalogue"`; `config.py:215` `APP_NAME = "Shokker Paint Booth V8"`. The version-truth test (`tests/regression_version_truth_contract_test.py`) hits `/status`, `/build-check`, and `/api/server-info` on **both** `server.py` and `server_v5.py`, asserting `version == "8.0.3-beta"` AND `build == "Spring Catalogue"` across all three, and greps the literal `const CLIENT_VERSION = '8.0.3-beta';`. Historically the stale surface was `config.py VERSION` (caused the 8.0.2 mismatch toast) — the live `/status` reads `CFG.VERSION`, **not** `SPB_VERSION`, so #3 is the easy one to forget.

### 6. R2 DEPLOY PIPELINE (build → stage → sandbox-test → activate)

SPB ships as **ONE all-in-one Cloudflare R2 download** (every finish baked in, 7.0.8+) with electron-updater auto-update from R2. This **supersedes** the old GitHub-release + in-app pack-downloader model. Delivery is `nsis-web`: a tiny `*-Web-Setup.exe` stub + a separate multi-GB `*-x64.nsis.7z` payload + `latest.yml` feed. nsis-web exists because 32-bit `makensis` can't mmap a >2 GB payload and GitHub caps assets at 2 GiB — the stub sidesteps both.

**Packaging config** (`electron-app/package.json`, verified): `win.target: "nsis-web"`, `artifactName: "ShokkerPaintBoothV8-${version}-Web-Setup.${ext}"`, `differentialPackage: false` (the `true` setting caused a redownload loop), `publish: {provider:"generic", url:"https://pub-9969ab01838a4d69bb55822f42553904.r2.dev", channel:"latest"}`. `appId: com.shokker.paintbooth.v6` and `name: shokker-paint-booth-v6` are **KEPT** even at V8 so licenses + saved paints (hardcoded `%APPDATA%\ShokkerPaintBooth`, `main.js`) don't move; only `productName: "Shokker Paint Booth V8"` rebrands.

**Step A — Build (~30 min).** From `electron-app/`, with the bundle flag on:
- bash: `SPB_BUNDLE_ALL=1 npm run build`
- PowerShell: `$env:SPB_BUNDLE_ALL=1; npm run build`

`build` = `electron-builder --win --x64`; `prebuild` runs `copy-server-assets.js` (sync write + hard-fail drift check). `SPB_BUNDLE_ALL=1` (read at `copy-server-assets.js:75` `BUNDLE_ALL_PREMIUM`) bakes the 7 premium finry families SLIM (2048-max, 4K dropped) into `server/assets/reference_textures`. Output lands in **`electron-app/dist/nsis-web/`** (NOT `dist/` root — `dist/latest.yml` is a STALE old-oneClick file; never feed from it): the stub `.exe`, the `shokker-paint-booth-v6-<ver>-x64.nsis.7z` payload (~3.8 GB), `latest.yml`, and `.7z.blockmap`.

**Step B — STAGE (upload payload + stub, do NOT activate).**
```
py -3 deploy_r2.py "electron-app\dist" --hold-latest
```
`deploy_r2.py` (repo root, a KEEPER tool) auto-descends into `dist/nsis-web`, reads the target version from `latest.yml`, and uploads **only this release's** payload + stub, **skipping `latest.yml`** so the live auto-update feed still points at the current version. Reads creds from env only (never written to disk): `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` (default `shokkerpaintbooth`), `R2_PUBLIC_URL` (optional, for printing links). It forces `BotoConfig(request_checksum_calculation="when_required", response_checksum_validation="when_required")` because botocore ≥1.36 otherwise adds an `x-amz-checksum-crc32` trailer that **R2's S3 multipart endpoint rejects** (aborts the multi-GB upload). Uploads in 64 MiB chunks, 4 concurrent; verifies each object with `head_object`.

**Step C — Sandbox-test the staged build (clean room).** Use the per-release `SPB_<ver>_sandbox.wsb` (e.g. `SPB_8.0.3_sandbox.wsb`): `<VGpu>Disable</VGpu>` (the host-force-close fix — see warning at top), `<MemoryInMegabytes>16384</MemoryInMegabytes>`, maps `_sandbox_share` containing the stub. The stub pulls the payload **from R2** = the real buyer flow. Windows Sandbox is already a clean room (fresh Windows each boot, no inherited `%APPDATA%`/registry). Verify: install completes (no hang), app launches, splash shows the right version, smoke-render works, and the version **pill matches**. Packaged-only bugs that only surface here (all fixed by 7.0.9): lab "← Paint Booth" back-nav 404/2nd-instance, DNA picker cold-baking 75 swatches, first-launch "does nothing" splash timing, NSIS extract "looks frozen". For upgrade-path / licensing tests, use a persistent Hyper-V VM instead (Sandbox reissues machine IDs each boot).

**Step D — ACTIVATE (publish the feed).**
```
py -3 deploy_r2.py "electron-app\dist\nsis-web" --only-latest
```
Publishes `latest.yml` **only**, and **refuses** unless the referenced payload is already on R2 with a matching size (`head_object` check at `deploy_r2.py:185–195`) — so the feed can never point at a missing/half-uploaded package. After this, in-app auto-update fires for older installs. `--hold-latest` and `--only-latest` are mutually exclusive (the script rejects both).

**R2 facts:** bucket `shokkerpaintbooth`, account `dcdedf1b696ea520d672ffcc49dcf26f`, public dev URL `pub-9969ab01838a4d69bb55822f42553904.r2.dev`. **Free tier = 10 GB** — keep only **current + previous** payloads (each ~3.8 GB; two = ~7.6 GB), owner deletes older ones via the Cloudflare dashboard. The `r2.dev` URL is rate-limited / "not for production"; a custom domain (`downloads.shokkergroup.com`) is the pre-wide-launch move. **Credentials ROTATE after each deploy** — do not reuse pasted keys. **Payhip** hosts only the ~0.69 MB stub (packaged in `ShokkerPaintBoothV8-<ver>-Payhip.zip` with READ-ME + CLEANUP.bat); buyers get the 3.8 GB payload from R2 at install.

**Gotchas worth re-stating:** a raw byte-grep of the stub for the r2.dev URL returns nothing — the URL is LZMA-compressed inside the NSIS exe (not a bug; verify the chain instead: `latest.yml` version correct + the `.nsis.7z` returns 200 at the public URL + size matches). After clicking "Enable" on the r2.dev URL there's ~1 min propagation, so a 403 immediately after is normal. The installer force-kills running SPB processes via `installer.nsh` (`killShokker` macro in `customInit`) so upgrades don't hang on file locks; buyer rescue tool = `Shokker-Paint-Booth-CLEANUP.bat` (never touches `%APPDATA%\ShokkerPaintBooth`).

---

**Reminders flagged for verification:** `LAUNCH_CHECKLIST.md` and `WINDOWS_SANDBOX_TEST_GUIDE.md` are confirmed stale (3-copy / GitHub / VGpu-Enable) — the accurate process is documented in `SPB_LIVING_WIKI.md` "RELEASES & SHIP STATUS" and codified in the `spb-deploy` skill (`docs/RELEASE_PROCESS.md`). The canonical version surfaces, deploy flags, sync topology, and the build hard-fail were all re-verified against current code for this section.

---

<a id="doctrines-and-laws"></a>

## Doctrines & Laws (the quality bar)

These are the binding rules a finish/pattern/spec must satisfy before it is "done." The owner's core grievance is that **memory alone fails** ("HOW THE HELL do we get you to follow these mandates?"), so the doctrines that matter most are backed by **mechanical, fail-closed gates** — run the gate, get a non-zero exit, you are not done. Where a rule is enforced only by self-discipline or an advisory check, that is called out explicitly. Every claim below was verified against the live code in `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum` unless flagged "[unverified]".

The two top-level laws live verbatim in `CLAUDE.md` (loaded every session) as **UNIVERSAL RULE #0** (Uniqueness) and **#0b** (Coverage + Fine-Detail + No-Laziness), under the header "UNIVERSAL RULES — owner mandate 2026-05-16 (SPB-105)". `CLAUDE.md` is at the repo root (`CLAUDE.md:36-83`). Related owner doctrine is duplicated in `AGENTS.md`.

---

### 1. The Uniqueness Law — "no clones, ever" (HARD LINE)

**WHAT.** A finish that is **≥80% structurally similar to ANY other finish in the WHOLE catalog** (cross-category) FAILS and must be redone with a *different idea*, not a tweak. The similarity is **color-independent**, so a recolor of an existing design is caught even with a completely different palette. Companion rule: a finish's **spec must mirror the paint's structure** (same geometry — if paint is 2300 shards, the spec lights those 2300 shards) unless its id is deliberately listed in `scripts/uniqueness_exemptions.json`.

**WHY.** Shipped recolor-clone finishes with flat two-color specs once too often (owner meltdown 2026-06-15). This is "the enforceable line in the sand so it can't recur." Statistical variety ≠ visual diversity; a template + parameter dials = laziness in the owner's vocabulary.

**HOW ENFORCED (mechanical, non-zero exit = FAIL):**
- Gate script: `scripts/spb_uniqueness_gate.py`. Hard threshold `SIM_FAIL = 0.80` (`spb_uniqueness_gate.py:46`). Usage: `--ids new1,new2`, `--module <module>` (gates every `paint_<id>` that also has a `spec_<id>` in `engine/paint_v2/<module>`), or `--report` (lists existing dup pairs ≥ threshold = the rebuild worklist). Exits 1 if any candidate FAILs.
- Index builder: `scripts/spb_catalog_fingerprint.py` renders every base + monolithic + pattern at `FP_RES` (256), computes a color-independent structural fingerprint (normalized-luma pHash + a multi-scale structural descriptor) on the **structure-carrying channel** (paint OR spec — FRACTURED finishes carry their structure in the spec over flat dark albedo). Caches to `_workbench/catalog_fp.npz` + `catalog_fp_meta.json`, keyed by per-finish source mtime (incremental). Must be fully baked (no args) for the gate to mean "vs whole catalog."
- Similarity math: `structural_similarity(a,b)` = `abs(corrcoef(...))` of 48×48 normalized luma vectors (`engine/paint_v2/flame_math.py:191-193`); combined gate score is `0.5*struct_cos + 0.5*phash_sim` (`spb_uniqueness_gate.py:72-78`).
- **SOLID escape hatch (legitimate):** a finish is "solid" only when BOTH paint AND spec are near-flat (`SOLID_STD = 0.012`, `spb_catalog_fingerprint.py:43`). Gloss vs matte share flat paint and differ only by spec, so they are exempt from the structural rule (else gloss≈matte=100% would false-FAIL). Solids are excluded from comparison on both sides (`spb_uniqueness_gate.py:114-118,143-145`).
- **Spec-traces-paint is ADVISORY only**, not a hard fail: `TRACE_MIN = 0.20` (`spb_uniqueness_gate.py:50`). The linear "spec mirrors paint" cosine over-flags legitimately-complementary specs (it flagged owner-APPROVED Tactical 17/17, Ceramic 14/15 on 2026-06-15), so it only prints "⚠ spec-trace low (advisory — eyeball it)"; the 80% clone rule is the only HARD teeth.
- Exemption file `scripts/uniqueness_exemptions.json` currently has an EMPTY `intentional_spec` list — nothing is exempt from the 80% rule (that rule has no exemptions); the file only exempts ids from the advisory spec-trace check.
- Surfaces: the same baked index powers the **Similarity** slider tab in `/SPB_WORKBENCH.html` (route `/api/workbench/similarity`).
- Full law + rationale: `docs/UNIQUENESS_LAW.md` (verified present, 2026-06-15) and `CLAUDE.md:40-49` (rule #0).

---

### 2. The Coverage + Fine-Detail + No-Laziness Law (HARD LINE, GATED)

**WHAT.** Three binding defaults for every finish/pattern/spec on the 2048×2048 whole-car canvas, plus a creativity charge: (1) **FULL-CANVAS COVERAGE** — no dead corners, no lonely centered motif, no big empty regions; (2) **CRUSHED FINE DETAIL** — high-octave busy premium detail, never a smooth ramp / fat blob / single recolored primitive; (3) **NO LAZINESS — EVER** — a recolor of an existing field is NOT new work; (4) **BE CREATIVE** — invent new generative math ("you have the UNIVERSE — you don't live in a box").

**WHY.** Owner mandate 2026-06-18. The `char_px` fineness check alone did NOT catch sparseness (a few fine motifs on an empty field passes "char" while looking barren) — that was the repeated failure mode. Rules must be MECHANICAL FAIL-CLOSED GATES because memory alone keeps failing.

**HOW ENFORCED (reference implementation, 4 fail-closed pytests):** `tests/regression_flame_uniqueness_test.py` over `flame_math.FLAME_STRUCTURES`. Run: `py -3 -m pytest tests/regression_flame_uniqueness_test.py -q`. New structures auto-gate. The four checks (verified):
1. **Uniqueness** — every pair of distinct structures `< MAX_STRUCT_SIMILARITY = 0.80` (`flame_math.py:181`).
2. **Render-time** — `< 3s @ 2048²`, but **load-normalized**: interleaved best-of-3, budget = `max(3.0, 8.0 × fastest structure)` so the absolute 3s applies when idle and scales together under CPU contention (`regression_flame_uniqueness_test.py:41-70`).
3. **Coverage** — `coverage_score >= MIN_COVERAGE = 0.60` (`flame_math.py:214`). `coverage_score` = fraction of an 8×8 grid whose **99th-percentile** luma clears `floor=0.18` (high percentile so a spread ember-shower passes but a centered blob with dark corners does not) (`flame_math.py:241-251`).
4. **Fine detail** — `fineness_score >= MIN_FINENESS = 0.15` (`flame_math.py:215`). `fineness_score` = RMS of the S/64 Gaussian high-pass over RMS of the signal, measured **on the lit region only** so a mostly-dark fire field is judged on its flames (`flame_math.py:254-264`).

**Exceptions must be DELIBERATE + DOCUMENTED** — opt out only by naming the id WITH a written reason in `flame_math.COVERAGE_EXEMPT` / `FINE_DETAIL_EXEMPT` (name→reason dicts, `flame_math.py:218-233`; e.g. `candle`="a single upright flame is intentionally a lone centered motif", `radial`="a smooth radiating fireball is intentionally low-frequency"). Silently dodging the bar is forbidden; adding a name is a reviewable act. When a gate flags too-smooth/lazy, **CRUSH IN real detail** rather than exempt (it caught `tongues` 0.06→0.19 and `dragon_jet` 0.05→0.18). Codified as `CLAUDE.md` **rule #0b** (`CLAUDE.md:51-62`).
- **NEXT STEP (flagged, not yet done):** fold the same coverage + fineness teeth into the catalog-wide `scripts/spb_uniqueness_gate.py` so ALL finishes auto-gate, not just flames. [unverified in current code — `spb_uniqueness_gate.py` as read does NOT yet contain coverage/fineness checks.]

---

### 3. Render-Time Doctrine — ≤1s ideal, >3s unacceptable @2048

**WHAT.** Every single finish/spec/pattern, rendered BY ITSELF at REAL sizes, must complete in **~1s optimal, 3s hard fail**. Finishes timed at paint_fn+spec_fn `(2048,2048)`; spec overlays at `(2048,2048)`; patterns at `(1024,1024)` work grid.

**WHY.** Owner: "you MUST pay attention to render times — that's VITAL." Trigger: LFR Old Glory Flux took **51s** in the app while the 512² harness looked fine. Small-swatch timing hides O(count × full-grid) blowups — per-splat full-grid math (arctan2/sqrt/exp over the whole grid per scatter point) multiplies 4–16× from a 512 test. The #1 fix is **windowed splats** (compute each scatter motif only in its local bounding box) and `cKDTree` for neighbor queries.

**HOW ENFORCED:**
- Harness: `scripts/render_time_harness.py` — times all new items at real sizes, prints `ok` (≤1.0s) / `warn` (1–3s) / `FAIL` (>3.0s), writes `scripts/perf_results.json` (`render_time_harness.py:14-21,67-71`).
- The flame gate's render test (check #2 above) is the fail-closed CI version.
- `CLAUDE.md` rule #2 states "Standard finish renders must complete in **2-3 seconds at 2048²**"; layer stacking / zone overlays are allowed exceptions but bare paint+spec must stay in budget. Profile engine changes with `audit_render_perf.py --trials 3` (`CLAUDE.md:77-78`). Note the slight band difference: the *doctrine* target is ≤1s ideal / >3s fail; `CLAUDE.md` phrases the standard-finish budget as 2–3s.
- "render time too long" is a standing audit-page reason chip; audit pages show a measured per-item ⏱ render-time badge.
- Related companion gates: `scripts/mip_survival_gate.py` (does detail survive 4× mip-down to track distance — metric `engine.color_science.mip_survival`, exit 1 below threshold), `scripts/perf_gate.py` / `arm_perf_gate.py` (perf regression net — note: built but historically NOT armed by default).

---

### 4. Wovenlight / Ignition Doctrine — spec TRACES paint + decorrelation by ASPECT

**WHAT.** Two coupled rules: (a) **the spec must work WITH the paint** — build paint and spec from **one shared `_fields(h,w,seed)` geometry function, same seed**, so the spec traces the paint's exact geometry; if the paint shows hot red lines, the spec lights those EXACT red lines so they blow off the car in motion. (b) Every finish needs its **own** angle-gated "holy shit" ignition moment: a subset of the geometry painted DARK in albedo while a spec channel is near-MAX on those *same* pixels (invisible at most angles → explodes at the right sun angle), surrounded by calm/restraint. **ALL of them** get a bespoke ignition choreography — not every finish maxed-colorful, not a Wovenlight clone, but every one individually designed.

**WHY.** Owner's FABLE round-3 verdict (2026-06-10): the rebuilds **overcompensated on spec-channel coloring** with geometry divorced from the paint. "We can't just throw random colors at the spec channels and call it a day." The effect only impresses in motion when light reveals a motif the eye already half-sees in the paint; random spec color over unrelated paint reads as noise.

**HOW ENFORCED (architecture + discipline, not a standalone CI gate):**
- Exemplar mechanism verified in `engine/paint_v2/fable_collection.py` (`_wovenlight_fields`, ~L1418 per memory): shared fields feed both `paint_fn` and `spec_fn` via `_seed_of`; the violet weft ribbons are dark albedo + M≈232 on the same pixels; the emerald warp stays calm (~34·prof satin). This shared-fields architecture already exists for every FABLE finish — USE it, don't bypass it.
- **Channel decorrelation = different ASPECTS of the SAME motif system** (e.g. M = weft checker, R = crossing corridors + threads, Cc = third-angle sheen pools), NEVER unrelated random geometry per channel.
- The Uniqueness Gate's advisory spec-trace score (§1, `TRACE_MIN=0.20`) is the closest mechanical proxy, but it is advisory only. Otherwise this is enforced by build discipline + visual eyeball + the SPM9/M7 spec-stats bar.
- Supersedes blind `H≥2.0` hue-diversity chasing; diversity gates are sanity FLOORS, never targets.

---

### 5. Spec-Diversity Doctrine + Wild-Spec Channel Decorrelation (|corr| < 0.85)

**WHAT.** NO LAZINESS / NO DUPLICATION across ALL content: every finish/pattern/spec gets its OWN identity AND its OWN algorithm/geometry — never borrow, recycle, or recolor a shared skeleton. Spec "color" comes from **triplet variation**: 3–5 motif zones per finish, each with its own M/R/Cc combination carrying DIFFERENT geometry (in the R=M, G=R, B=Cc composite: M→red, R→green, Cc→blue, M+R→yellow, M+Cc→magenta, R+Cc→cyan). The hardest mechanical bar when rebuilding wild-spec finishes is **max absolute channel correlation < 0.85**.

**WHY.** Owner rejected the v1 Wild Spec Lab on sight ("VERY LAZY… NO SPEC DIVERSITY") despite it passing every statistical gate, because it was ONE pipeline (`make_wild_spec`) with scalar dials and M/R/Cc all derived from the SAME underlying fields → channels correlated → every map read as a single hue.

**HOW ENFORCED (per-build self-test harness convention, not a committed CI file):**
- Probe per-PAIR (MR/MC/RC), not just the max. The #1 correlation source is a shared band/zone STEP function used by all three channels; different per-band scalars are NOT enough — give each channel a **structurally different primary geometry** (e.g. M=weave valleys, R=signed sheen rib, Cc=seam/stitch corridor as its own sparse structure), and anti-align at least one band so R and Cc disagree on a third.
- Self-test recipe (scratch `_*.py`, delete after): direct-call `(768,768)` sm=2.0 → each channel `std≥20`, `clip<1%`, `max|corr|<0.85`; then `(2048,2048)` `<2.5s`; then the render recipe via `shokker_engine_v2.build_multi_zone` preview_mode. ALWAYS eyeball the composite (R=M,G=R,B=Cc) + the M|R|CC grayscale strip — stats passing ≠ motif reading.
- Reference standard for spec creation: `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md` (gold per `CLAUDE.md`). [The `max|corr|<0.85` value is a per-build harness convention from memory; it is NOT a standalone committed gate script. The SPM9 metric uses a related `>0.85 cosine` catalog-similarity penalty, §8.]

---

### 6. Canvas-Design-Not-Spec + Full-Coverage (design FIRST, ≥0.80 coverage)

**WHAT.** The CANVAS PAINT DESIGN matters as much as the spec. Stop recoloring a handful of shared pattern primitives (micro_voronoi, ring_swarm, filament_web, halftone, flow_grain, micro_scatter) — every finish needs a truly UNIQUE, ambitious design "50–100× better." Process: **design FIRST (write a one-line concrete visual brief), code second.** A category's finishes must look like 10 different artists made them while still reading the theme. Unless a finish SPECIFICALLY calls for sparseness, the canvas must be **NEARLY FULLY COVERED** in detail with everything crushed smaller — "if you think it's right, it still needs to be 3–5× finer." Sparse = automatic reject.

**WHY.** Owner 2026-06-10: "You created a handful of pattern designs and went with variations off them — VERY LAZY across the board." A married spec on a boring blobby canvas is still boring; the `char_px` fineness gate does NOT catch sparseness (it passes a few fine motifs on an empty field).

**HOW ENFORCED:**
- **COVERAGE gate ≥ 0.80** (distinct from the flame gate's 0.60): fraction of pixels with local high-frequency detail (`|gray − blur|` above threshold) must be `>= 0.80` (most canvases ~0.95+); hard-FAIL below unless the id is on an explicit SPARSE_OK list. Implemented in `scripts/b10_render_and_page.py`; fold the same gate into every finish harness. [Memory citation; the script exists — `scripts/b10_render_and_page.py` is present in the repo — exact 0.80 constant not re-verified line-by-line.]
- ALWAYS WIRE into the live engine so the owner judges ON THE CAR (his preferred review surface). Build dense first; verify coverage + char + a visual montage BEFORE showing the owner (review-discovered failures waste tokens, which the owner is furious about).
- Render trace for debugging: `build_multi_zone` (in `shokker_engine_v2.py`, ~L16497 per memory) dumps the exact per-zone recipe to `_audit/last_render_trace.json` on every car render — read that file instead of asking the owner to reconstruct his setup.

---

### 7. Fineness Doctrine + Pattern-Scale-Finer (the swatch LIES)

**WHAT.** A 2048² canvas wraps a WHOLE car, so a 60px motif is a dinner plate. Primary motif elements should be **~2–10px at 2048 (counts in the 100s–1000s)**, mid-structure 10–32px, and anything >48px is a low-contrast MACRO carrier only — never the visible design. Procedural patterns specifically render TOO BIG: **design 2–4× FINER than the swatch looks** ("the swatch LIES"). When unsure, CRUSH FINER — the owner has never once said "too fine."

**WHY.** FABLE round-1: 17 of 20 marked "Too blobby / macro" + "Not enough fine detail"; the only two keepers (Velvet Eclipse 80, Wovenlight 85) were the two flake/micro-scale finishes. FRACTURED MINDS ratings confirmed it: every ≥80 keeper is a fine/dense texture (Basketweave 91, Tide Glass 87), every "rebuild — too big" was macro/blobby (diamond_plate 49, riverine 34, thousand_eyes 28). Cause is intrinsic: "it's just the canvas and the way the program operates."

**HOW ENFORCED:**
- The flame `fineness_score >= 0.15` gate (§2) is the mechanical floor; `CLAUDE.md` "Quality bar" section mandates octaves at minimum 128/256/512/1024+ and **≥3 distinct frequency bands** with the highest legitimately fine (`CLAUDE.md:89-91`). `docs/METRICS.md` gives the exact three-band recipe (Macro 32/64/128 → M8, Fine 256/512 → M6, Micro 1024/2048 → car-scale sparkle) (`METRICS.md:51-73`).
- Knob multipliers to crush finer: voronoi cells ×3–4, grid-per-side n ×2, scatter counts ×3–4, frequency k ×2, 1D counts ×2–2.5. For single-motif/centred engines with no count knob, use `fm._tile_finer(field, k)` in `engine/paint_v2/fractured_math.py` (2×2 tile → 4 smaller copies). Accept that crushing finer can DROP the uniqueness-gate trace score (fine ≈ periodic) — finer wins over trace.
- Eyeball at 25% zoom (car distance) AND 1:1. Fineness must come WITH mid-scale support (MIP-survival, §3) so it survives the 1/4 view.

---

### 8. M7 ≥85 ship-bar vs ≥80 keeper, and SPM9

**WHAT.** SPB has TWO distinct M7 finish-quality thresholds that are intentionally different — do NOT collapse them to one number:
- **≥85 = OWNER SHIP-BAR** (SPB-105 mandate, `CLAUDE.md` rule #1 + `AGENTS.md`): the bar a finish must clear before you stop iterating. `CLAUDE.md:64-75`.
- **≥80 = CODE "keeper" tier**: `final >= 80` → `tier="keeper"`, and `"tierThresholds": {"keeper": 80, ...}` in `scripts/spb_workbook_compute_m7.py:154-155,226`. A finish at 80–84 is a code-classified keeper but BELOW the owner ship-bar — keep iterating to ≥85.

**SPM9** (`scripts/spm9_score.py`) — "Spec Pattern Master 9," the pattern-specific composite that replaced SPM8 after the owner verdict "they look exactly the fucking same" (SPM8 drove recipe-stamping). Built on the owner's FOUR PILLARS — Uniqueness/Weirdness, Spec Color Diversity, Render Time, Wow Factor — as 12 axes (UNQ 0.22, SCD 0.20, RT 0.13, WOW 0.10, then PFV/FSC/ED/CR/CV/MFS/BRU) with 3 penalties: **MP** macro-pollution −0.10 (energy in >32px features), **RP** repetitive-periodicity −0.04, **SIM** catalog-similarity −0.06 (>0.85 cosine sim to another finish). Tiers: 90+ masterpiece, 80–89 keeper, 70–79 ok, 60–69 watch, 50–59 fix, <50 critical. Output `_workbook_metrics/spm9_spec_pattern.json` (`spm9_score.py:1-55`). [Note: later scorers `scripts/spm9_score.py`'s successors `scripts/spb_spm10_score.py` and `scripts/spb_spm8_score.py` also exist in-tree — SPM9 is the owner-blessed pattern metric; confirm which is current before relying on it.]

**WHY.** Earlier confusion treated `CLAUDE.md` (85) and the code (80) as contradictory; they are not — they are different on purpose (docs updated 2026-05-30 to state both with a code citation).

**HOW ENFORCED / WORKFLOW (`CLAUDE.md` rule #1):** edit renderer → rebake thumbnail → `python scripts/spb_workbook_compute_m1.py && python scripts/spb_workbook_compute_m7.py` → read per-finish composite from `_workbook_metrics/m7_composite.json` → if <85, iterate. **Exception:** spec_driven intent finishes have M1 dropped from the composite by design (SPB-95) — for those, score spec channel stats directly (M_std, R_std, CC_std each ≥20, range spanning most of [0,255]); if M7<85 but spec stats are strong, flag "metric-blind, owner-approve-only." **When the owner's eye and M7 disagree, the EYE wins** (M7's B_structure axis wrongly rewards macro features) — `AGENTS.md`.

---

### 9. UV-Orientation-Agnostic Design

**WHAT.** Finishes/patterns/spec overlays MUST be abstract/rotated/omnidirectional/radial/scattered — **never straight up-and-down**. Literal vertical stripes, an upright flag, centered text, or a single upright emblem DO NOT WORK.

**WHY.** The paint canvas is 2048×2048 UV, and EVERY iRacing car template lays its body panels out differently (reversed, flipped, rotated, scattered across the square). A motif that depends on a fixed global orientation lands at random angles on most cars.

**HOW ENFORCED (mental test, no automated gate):** "does it still look intentional rotated 90° / 180° / mirrored?" If no, redesign. Use radial bursts, all-over grain/flake/carbon, scattered star fields, omnidirectional brocade (`fd_phoenix_fenghuang`), filigree, marble veins, multi-directional (not single-axis) anisotropic sheen. Theme feel comes from **palette + spec behavior + abstracted motifs**, NOT literal flag geometry.

---

### 10. Finishes Change ONLY on Owner Request

**WHAT.** Finishes, bases, and patterns are NOT frozen — the owner adds/removes/tweaks them daily — but you change a finish/base/pattern (or anything affecting rendered output) **only when the owner explicitly says to**. No unrequested finish/base/pattern changes, especially during audits, reviews, refactors, or cleanups.

**WHY.** The owner owns the creative direction and curates the catalog himself. An autonomous or incidental finish change pollutes work he's actively managing and he can't tell what he changed vs. what an agent changed. Finish curation is the Codex/owner lane.

**HOW ENFORCED (process rule):** codebase/infra/tooling/test/doc changes are fair game when authorized; treat anything that alters a finish's definition or rendered output as requiring an explicit, specific instruction. When a good idea would touch rendered output, surface it and WAIT. Consequently, quality "gates" are framed as **change-review/diff tools, not blocking lockdowns** (e.g. a golden-image regression net is a diff surface, not a freeze).

---

### How to actually run the gate battery (the "is it done?" checklist)

The `spb-finish-gate` skill runs this battery; manually it is:

```bash
# 1. Uniqueness (HARD: non-zero exit = clone)
python scripts/spb_catalog_fingerprint.py                    # refresh whole-catalog index (incremental)
python scripts/spb_uniqueness_gate.py --module <your_module> # or --ids a,b,c ; --report for dup worklist

# 2. Coverage + Fineness + Uniqueness + Render-time (the 4 fail-closed flame pytests, the model gate)
py -3 -m pytest tests/regression_flame_uniqueness_test.py -q

# 3. Render-time budget at REAL sizes (≤1s ideal, >3s FAIL @2048)
python scripts/render_time_harness.py                        # writes scripts/perf_results.json

# 4. MIP survival (does detail survive track distance)
py -3 scripts/mip_survival_gate.py thumbnails/audit/<category>

# 5. M7 composite (owner ship-bar ≥85; code keeper ≥80)
python scripts/spb_workbook_compute_m1.py && python scripts/spb_workbook_compute_m7.py
#   then read _workbook_metrics/m7_composite.json
# 5b. SPM9 for patterns/specs
python scripts/spm9_score.py
```

Any non-zero exit, any M7 <85, or any eyeball-rejected motif = **not done**. The owner's enforcement philosophy: gates are mechanical because memory keeps failing — never ship on "I think it's fine."

---

### Things flagged / not fully verified (be careful)
- **`spb_uniqueness_gate.py` does NOT yet carry the coverage/fineness teeth** — that extension is a documented NEXT STEP (CLAUDE.md #0b, coverage-fine memory). Only the flame test enforces coverage/fineness mechanically today.
- **`max|corr|<0.85` decorrelation** is a per-build self-test harness convention (scratch `_*.py`), not a committed CI gate file. The committed analog is SPM9's `SIM` penalty (>0.85 cosine, −0.06).
- **The ≥0.80 coverage gate** (canvas-design doctrine) is separate from the flame gate's 0.60; it lives in `scripts/b10_render_and_page.py` (file present; exact constant not re-verified line-by-line this pass).
- **`_wovenlight_fields` ~L1418** in `engine/paint_v2/fable_collection.py` and **`build_multi_zone` ~L16497** in `shokker_engine_v2.py` are memory line-cites — directionally correct (files present) but line numbers may have drifted.
- Render-time phrasing differs slightly between sources: the doctrine is "≤1s ideal / >3s fail," while `CLAUDE.md` rule #2 says "2–3 seconds at 2048²" for a standard finish. Treat >3s as the hard fail either way.

---

<a id="finishes-patterns-bases-color-science"></a>

## Finishes, Patterns, Bases & Color Science

This section is the definitive map of SPB's catalog *content*: the registries that hold it, the exact function contracts every finish/pattern/base must satisfy, the generative engine + color-science libraries that author it, the major finish families, and the precise wiring needed to add a new item so it actually renders AND shows in the picker. All file:line refs were verified against `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum` on read; where a memory claim could not be confirmed it is flagged.

### 1. The data model — five registries

`engine/registry.py` is the single source of truth doc and `_build_registries()` (returns at `engine/registry.py:603`) assembles five module-level globals. It delegates to `shokker_engine_v2` for the base set, then layers V5 modules on top:

- **`BASE_REGISTRY`** — combinable base finishes. **Each entry is a DICT**, not a tuple: `{"M": int, "R": int, "CC": int, "paint_fn": fn, "base_spec_fn": fn (optional), "desc": str}` (see real rows at `engine/base_registry_data.py:335-365`, e.g. `ceramic`, `gloss`, `piano_black`). The authoritative import is `from engine.base_registry_data import BASE_REGISTRY` (`engine/registry.py:41`). M/R/CC are the baseline metallic / roughness / clearcoat scalars (0–255); `paint_fn` paints the albedo; `base_spec_fn` (when present) authors a married spec.
- **`PATTERN_REGISTRY`** — pattern overlays. `engine/registry.py` reassigns this module global to the merged set at load; the render path `overlay_pattern_on_spec` reads it. ~588 entries (407 procedural + 180 image + 1 stub) per the pattern audit.
- **`MONOLITHIC_REGISTRY`** — one-shot finishes (color-shift, fusions, FRACTURED, effects). **Each entry is a 2-TUPLE `(spec_fn, paint_fn)` — spec FIRST, paint SECOND** (confirmed by the FORGE module's own contract comment, `engine/expansions/fractured_forge_2026.py:13`). The static catalog has ~1548 monolithic rows.
- **`FUSION_REGISTRY`** — a subset of monolithics; also the prefix-keyed source the picker group-map reads (see §10). Lives in `engine/expansions/fusions.py` as a module global AND is mirrored onto `shokker_engine_v2.FUSION_REGISTRY`.
- **`FINISH_REGISTRY`** — legacy backward-compat IDs.

### 2. The function contracts (memorize these — every item satisfies one)

**Monolithic finish — `mono_reg[id] = (spec_fn, paint_fn)`** (canonical example: `engine/expansions/fractured_forge_2026.py:444-472`):
- `paint_fn(paint, shape, mask, seed, pm, bb) -> HxWx3 float in [0,1]`. `paint` = the composited input canvas (user's paint, RGB; may be 0–255 or 0–1 — normalize if `.max()>1.5`), `shape=(h,w)`, `mask` = the zone mask (HxW or HxWx_, resize to shape), `seed` = render seed, `pm` = paint multiplier/strength (0..1; finishes blend `src*(1-mask*pm) + art*(mask*pm)`), `bb` = a "blackboard" dict for cross-stage data (e.g. patterns stash `pattern_val` in it).
- `spec_fn(shape, mask, seed, sm) -> HxWx4 uint8 = (M, R, Cc, A)`. `sm` = spec multiplier/strength. Channel order is **0=Metallic, 1=Roughness, 2=Clearcoat, 3=Alpha(255)** — confirmed at `engine/spec_sculpt/fracture.py:100-105`.

**Base finish — dict in `BASE_REGISTRY`** with optional `base_spec_fn(shape, seed, sm, base_m, base_r) -> (M, R, Cc)` (full-res tuple of channel arrays). Verified signatures: `engine/expansions/color_science_rebuild_2026.py:878`, `engine/paint_v2/cultural_mortal_shokk.py:388`, `engine/paint_v2/cultural_colorshoxx_ai.py:290`. Note bases receive `base_m`/`base_r` (the base's own M/R, after the user's HSB/foundation modulation) — NOT a `mask` — that is the key signature difference vs monolithic `spec_fn`.

**Pattern overlay — `texture_fn(shape, mask, seed, sm) -> dict`** with keys: `{"pattern_val": HxW float 0..1, "R_range": float, "M_range": float, "CC": int|array|None}` (verified return sites throughout `engine/expansion_patterns.py`, e.g. `:739`, `:3038`, `:3542`). `pattern_val` is the relief/coverage field the paint_fn colors; `R_range` negative carves roughness down; `M_range` positive raises metallic; `CC` sets clearcoat. Helper field-builders: `get_mgrid`, `multi_scale_noise` (in `engine/core.py`, `engine/spec_patterns.py`). Image patterns instead carry an `"image_path"` and auto-load from `assets/patterns/*.png|jpg` and `basespatterns_examples/patternexamples/`.

**THE BINDING DOCTRINE: the spec must TRACE the paint.** Paint and its married spec share one seed and one geometry; ignition (near-mirror spec) fires on the SAME pixels as a dark-albedo motif while surroundings stay calm. Decorrelate M/R/Cc so `|corr|<0.85` by riding each channel on a *different aspect of the same motif* — never alien geometry, never `1-x` of the same field (that scores 0.999 and fails). See the FRACTURE/Wovenlight ignition rules below.

### 3. `engine/paint_v2/fractured_math.py` — "the math is the asset" engine library

296 `def`s (the largest generative library). Every engine has signature `name(h, w, seed, *, ...kwargs) -> HxW float field` computed low-res then `_up`-scaled, deterministic by seed, ≤~1.9s at 1024². Examples (verified line numbers): `reaction_diffusion:58`, `strange_attractor:84`, `curl_flow:114`, `worley:135`, `quasicrystal:201`, `marble:223`, `truchet:240`, plus the Wave-2 advanced set (`gabor_weave:312`, `phyllotaxis:324`, `apollonian:347`, `pentagrid:370`, `harmonograph:397`, `caustics:418`, `gyroid:511`...) and the **5 invented "calling-card" engines**: `phase_reliquary:539`, `mycelinth:566`, `hyperflora:580`, `soliton_reef:603`, `aurora_loom:634`. Later named engines (magma, herringbone, dragonscale, chladni, stormfork, croc_hide, python_scales, ebru, damascus...) back the MINDS/SOULS rebuilds.

The colorizer is **`colorize(field, base_rgb, glow_rgb, edge_rgb, *, gamma, fill_gain, edge_gain, edge_sigma, ambient, ambient_floor) -> HxWx3 [0,1]`** (`engine/paint_v2/fractured_math.py:170`). It maps a 0..1 field to FRACTURE-ready dark-albedo RGB: dark base + glow on field intensity + crisp edge highlights on the gradient. `ambient`/`ambient_floor` add a wide-blur bloom so SPARSE engines (attractor webs) still reach full-canvas coverage — this fixed the owner's #1 complaint ("blank corners = a whole bumper with nothing on it"; ANY blank region must carry structure edge-to-edge).

A second, newer arsenal lives in **`engine/paint_v2/exotic_engines_2026.py`** (`ENGINES` dict, `field(name,h,w,seed)`, `names()` at `:19/:40/:52`) — 156 consolidated "edgy/race-car" engines aggregated from `engine/paint_v2/exotic_packs/` (14 packs: complex_dynamics, attractors, aperiodic_sacred, automata_reaction, curves_harmonic, optical_material, physical_fields, recursive_curves, grunge_decay, gothic_ornate, tactical_armor, depth_stack, street_graffiti, aggressive_damage). These were taste-curated to the owner's profile: **LOVES multi-hue iridescent flow + fine crisp detail (schlieren, thin-film, opal, nacre, peacock, dichroic, moiré); finds BORING uniform grids/weaves, flat mono, sparse dust, and big blobby reaction/CA.** The color-science rebuild pulls from BOTH `exotic_engines_2026` and the old `fractured_math`.

### 4. `engine/color_science.py` — the color/physics API

Cycle-safe (no `engine.*` imports inside). Verified functions:
- `oklch_ramp(stops_srgb, t, flatten_lightness, hue_dir)` (`:157`) — perceptual OKLCH ramps, shortest-arc hue, bisection chroma gamut-clamp. **Expensive (~2s/call full-grid); always wrap in a 1-D LUT over t** (`_opt_oklch_ramp` pattern in fable_collection). 80% of wave2 render time was unwrapped ramps.
- `candy_absorb(metal_srgb, tint_srgb, depth, density)` (`:198`) — Beer–Lambert: `out_lin = metal_lin · tint_lin^depth`. **The tint is TRANSMISSION at depth 1 (brighter than the target color), NOT the target color.** Replaced the old lerp-toward-tint candy (chalky-pink → real amber-over-metal).
- `interference_palette(thickness, orders, quantize, brightness, base_srgb)` (`:222`) — quantized Newton's-ring orders. **It MODULATES its base → a black base yields black output** (same trap as candy transmission); dark designs need an emissive ramp.
- `tri_partition(shape, seed, cells, soften_px)` (`:254`) — Voronoi 3-coloring → decorrelation by construction.
- `flip_lattice(shape, seed, scale_px, balance)` (`:300`) — perceptual color-flip micro-interleave.
- Gate metrics: `feature_fineness(:323)`, `spec_hue_diversity(:367)`, `mip_survival(:398)` (detail retention at 1/4 view; healthy ≥0.45, mush <0.25).

There is also a heavier `engine/paint_v2/color_science_2026.py` (candy_depth + 7 "looks" + `compose_cs_spec`) and `engine/paint_v2/depth3d_2026.py` (`traveling_colorshift`, `decorrelate_envelope`, `enforce_iron_rules`) used by the 2026 rebuild.

### 5. `engine/spec_sculpt/fracture.py::fracture_spec` — the canonical spec-from-paint engine

`fracture_spec(tex_rgb_hwc, mask_hw, *, ignition=1.0, angle_gate=1.0, trace_strength=1.0, calm_floor, decorrelation=0.0, as_uint8=True) -> HxWx4` (`:39`). It traces the paint's own geometry (`paint_graphic_weight` → graphic/gray/edge/dark-interior/streak fields), then builds M (near-chrome lit-structure), R (roughness lane gated `14..140`), Cc (Fresnel-maxed clearcoat with a faint decorrelated motif). This is the universal **"keep the owner's paint, give it a unique married spec"** tool: PRIZM and COLOR CLASH keepers were fixed by running `fracture_spec` on existing paint with per-finish dials (`ig/ag/cf/dc` from id-hash); FORGE finishes call it with `decorrelation=0.18`. `fracture_spec_from_any_paint` (`engine/spec_sculpt/generate.py:2403`) is the arbitrary-paint variant used by the app's Spec Sculpt / auto-spec features.

### 6. The FRACTURED universe

The flagship content area. Picker section "FRACTURED" (`SPECIALS_SECTION_ORDER` lists it first, `paint-booth-0-finish-data.js:1547`). Sub-groups + their ID prefixes + modules:

- **🧠 FRACTURED MINDS (`fm_`)** — `engine/expansions/fractured_minds_2026.py` (+ `_v3.py` round-3 replacements + `fractured_minds_soul_2026.py` "FM-Soul-Retune" wrapper that re-specs all 55 onto the Blood-Marble winner physics from each finish's own paint art). Bespoke geometry per finish.
- **💀 FRACTURED SOULS (`fs_`)** — `engine/expansions/fractured_souls_2026.py`, the APEX color-shift category (30 finishes). Drag-and-drop: paint ships PRE-CRUSHED (value 0.07–0.13), spec at proven dials (M~252 / G floor 30 + design lanes ~78 / B railed 255) so it color-shifts with zero setup. The G (roughness) channel IS the design canvas (aperture lanes). `_soul_spec`/`_soul_spec_v2` is an intentionally shared contract.
- **⚛ FRACTURED FORGE (`ff_`)** — `engine/expansions/fractured_forge_2026.py`. STANDALONE procedural finishes (paint = `colorize(engine field)`, spec = `fracture_spec(art, decorrelation=0.18)`), NOT color-shift. `FORGE` recipe dict (`id -> {engine, seed, palette, colorize dials}`) is the single source of truth; `_art_work_cached` (`@lru_cache`, `:433`) shares one compute between paint_fn and spec_fn; `install_into_engine(:475)` registers into mono + both FUSION registries and applies an owner pre-ship cull set (`_removed`, `:488`). ~33 original + ~60 later (memory says FORGE settled as ONE category of ~93).
- **Themed 100 (`fd_` Deep, `fc_` Cryptid, `fu_` UFO, `fr_` Rainbow, `fo_` Occult)** — `engine/expansions/fractured_themes_2026.py` (+ `_fix_2026.py`), 20 each. Engine prefixes in fractured_math: `dpx_/cry_/ufx_/rbw_/occ_`.
- **🔥 FRACTURED FLAMES (Ignite/Topo/Dance, `flm_`)** — catalog groups `_SPECIALS_FRACTURED_FLAMES_*` (`paint-booth-0-finish-data.js:1606-1608`), backed by `engine/expansions/flames_catalog_2026.py`.
- **Rebuild override** — `engine/expansions/fractured_rebuild_2026.py` overrides earlier `fm_`/`fs_` entries (installed LAST in the colorshift block so it wins). Lessons baked in: fine high-freq textures need LOW `edge_gain` or edge color floods; large smooth patterns get a `_TRACE_BOOST` (ts=2.0/cf=19) for spec trace.

### 7. The Ghost Shift recipe (iRacing color-shift physics)

`engine/expansions/ghost_shift_2026.py`. The owner's empirically-discovered iRacing color-shift: GHOST FRACTURE used as a BASE with the zone color crushed near-black produces genuine angle-driven env flashes. `GHOST_SHIFT_DEFS` (`:158`) maps `id -> (mode, base_m, base_g, seed_off)`. The measured contract (`:118-120`): `M = clip(base_m + detail*56*smf + edge*72*smf)`, `G = clip(base_g + (1-detail)*54 - edge*18)`, B(clearcoat) carved by the pattern. The honest physics: crushed paint → diffuse≈0 → only specular lobes show; the metal lobe is paint-tinted (dark on dark = "off"), the clearcoat lobe is paint-INDEPENDENT white that mirrors the environment (teal sky ↔ gold sun = two-color travel). **The four-dial doctrine:** ① Clearcoat(B)=power supply (max ~246+ fires color through); ② Roughness(G)=aperture (G≈0–25 = laser-pin glints, G≈45–90 = whole designs flash; G≥+33 = dead); ③ Metal(R)=amplifier (keep ~242+); ④ Paint crush=mixer (−60..−45 sweet spot). **Complementary-flash law:** perceived flash hue ≈ complement of the crushed base; pick base hues OFF the daytime gold↔teal axis for max pop. The Ghost Lab (`engine/expansions/ghost_lab_2026.py`, `gl_` ids) is the single-variable experiment set.

### 8. Image Forge — owner art in, derived spec out

`engine/expansions/image_forge_2026.py`. The owner's preferred creation loop: **he makes the art, the engine makes the spec.** Drop `image_forge/<finish_id>.jpg` (any size — `_ingest_file:250` center-crops → 1024² JPG q90, fuzzy-resolves the name, archives the original to `image_forge/_originals/`). `install_into_engine(mono_reg, base_reg)` (`:285`) scans `FORGE_DIR` (`:36`, = repo-root `image_forge/`) and registers each image. Paint = the art VERBATIM (no grain/strength scaling — see the authored-spec verbatim doctrine). Spec is DERIVED via `_forge_fields`/`forge_spec_channels` (`:57/:115`): structure-tensor stroke-flow → M = lit-structure trace + edge·coherence; R = directional brush noise signed by flow polarity + grain + saturation (NEVER luminance, which gave the |corr|=0.97 decorrelation trap); Cc = hue-banded sequential ignition (each color family gets its own gate, brightest strokes pin near-max). New `spectrum_*` ids also flow into `FUSION_REGISTRY` (`:363`); `get_forge_group_map` (`:222`) routes forge categories into the picker via `server_routes/finish_catalog_routes.py`. The `image_forge/` folder is synced to the mirror and SHIPS in the installer (it is under `server/**` and not excluded). Stale mirror copies must be deleted manually (sync ADDS but does not DELETE). `sin_orchid_2026.py` is the third "reference-image → bespoke procedural" lane.

### 9. Image-backed finish families + the asset-pack downloader

Several families render from reference image PLATES, not procedural code: Mortal/Money Shokk, Forbidden Dragon, ColorShoxx, Grunge Fun, Pattern Plates, Guest Designers, Viva/Rising Sun/Union Jacked. Their ~4.8GB `assets/reference_textures/` is EXCLUDED from the installer (`electron-app/copy-server-assets.js`, `excludeAssets` ~line 257) to stay under size caps — so for buyers these preview-fail unless their pack is bundled or downloaded. **The fix is `engine/asset_packs.py`:** `resolve_ref_dir(rel)` (`:94`) returns the first existing of bundled `assets/reference_textures/<rel>` else `APP_DATA_DIR/asset_packs/reference_textures/<rel>` (downloaded) else bundled. `APP_DATA_DIR = %APPDATA%/ShokkerPaintBooth` (`:64`, same as license). `PACKS` manifest (`:123`), `pack_installed(:209)`, `install_pack` (urllib download + path-traversal-safe extract, `_safe_extract:246`), hosted on GitHub release tag `asset-packs-v1`. **EVERY family loader must route its asset root through `resolve_ref_dir`** (the easy-to-miss step). Backend: `GET /api/finish-packs` + `POST /api/finish-packs/install` (returns `{status:'ok'}`); frontend modal `js/finishes/finish-packs.js`. Loaders scan at IMPORT → a freshly-downloaded pack needs an app RESTART.

### 10. The base-category rebuild doctrine + override stack

Weak "param-dict on shared generic paint_fn, no married spec" bases were rebuilt into bespoke married `paint_<id>` + `spec_<id>` pairs (modules `engine/paint_v2/candy_pearl_2026.py`, `carbon_composite_2026.py`, `ceramic_glass_2026.py`, `military_tactical.py` family, `metallic_standard_2026.py`). Binding design doctrines (hard-won): **~10× finer than instinct** (SPB crushes finishes; judge on a contact sheet rendered at 1024+ THEN downscaled, never rendered small); NO recolor-and-flip clones; NO sheen baked into albedo (angle response lives in the spec, iRacing drives it); full-res fine flake/fleck (not work-res-capped noise); color-diverse across the wheel; married pair shares one seed; decorrelate `|corr|<0.85`; R floor 15; Cc=16 wet/high=flat; M≤255 (clip!); render <3s @2048.

**The base override stack is DEEP** — to make a base actually render you may have to win several layers (in order): (1) `engine/base_registry_data.py` block (both engine copies — this file is report-only, NOT auto-synced); (2) the lazy `overrides` dict in `shokker_engine_v2.py` (`_spb_wire_regular_base_v2_overrides`, ~L14438) that re-points bases to old `_v2` fns at render time and WINS over base_registry_data — add your block right before `wired = 0`; (3) `_spb_apply_wild_specs` (`engine.expansions.wild_spec_lab.apply_wild_specs`) which reclaims `base_spec_fn` for any id in its `CONFIG` — either re-assert after it or comment the id out of `CONFIG` (both copies). **NEW-id shortcut:** brand-new ids nothing else claims need ONLY the base_registry_data block + catalog — no override/wild_spec dance. Verify with `shokker_engine_v2.BASE_REGISTRY[id]['base_spec_fn'].__module__`. WARNING: `shokker_engine_v2.BASE_REGISTRY` is a DIFFERENT object from `engine.registry.BASE_REGISTRY` — write base overrides to the module global the render path uses.

### 11. The 2026 color-science final-authority rebuild

`engine/expansions/color_science_rebuild_2026.py` is the dead-last override module for the 8 owner categories (Chameleon, Prizm, Color Clash, Gradients, Prism Forge, Money Shokk, Color Science cs_, Shokk Series). `REBUILD_MONOLITHICS` (`:625`), `install_prizm_spec_traces`/`install_colorclash_spec_traces` (keep-paint + `fracture_spec`), `_mk_base_pair` (`:873`, the base-registry adapter). It is applied via the hook **`_spb_apply_color_science_rebuild_2026()`** which is called at three points in `shokker_engine_v2.py` (lazy path `:10043/:10073`, module-load tail `:14060`, and again `:15830` as "final authority — beats wild_spec re-wire"). Prism Forge and Shokk Series have their own locked modules (`engine/expansions/prism_forge_rebuild_2026.py` → `install_prism_forge`; `shokk_series_rebuild_2026.py` → `install_shokk_series`; called at `:14031/:14051`); Gradients/Money Shokk/cs_ have `gradients_rebuild_2026.py`/`money_shokk_rebuild_2026.py`/`cs_shift_rebuild_2026.py`. **The uniqueness-metric lesson (critical):** the coarse 32×32 pixel-cosine gate has a blind spot — same-design/different-position scores LOW = "unique". The fix is a WHITENED FFT-log-magnitude + edge-orientation gestalt (`scripts/spb_gestalt_gate.py` for finishes, `scripts/spb_pattern_gate.py` for patterns) — raw FFT-cosine baselines ~0.97 for all textures (common 1/f falloff) and MUST be whitened (subtract dataset-mean feature vector). Pattern de-dupe lives in `engine/expansions/patterns_rebuild_2026.py` (`install_pattern_dedupe`, called at `shokker_engine_v2.py:15840`).

### 12. The install-hook chain (where everything gets wired into the engine)

`_spb_apply_colorshift_rework_2026()` (`shokker_engine_v2.py:13754`, also self-invoked at `:13968`) calls each family's `install_into_engine` in this verified order: redesign_b10 (`:13798`) → redesign_wave2 (`:13812`) → spectrum_shift_2026 (`:13828`) → **image_forge_2026 (`:13839`)** → sin_orchid (`:13846`) → fractured_minds (`:13854`) → fractured_minds_v3 (`:13863`) → fractured_souls (`:13874`) → fractured_minds_soul (`:13883`) → fractured_forge (`:13892`) → fractured_themes (`:13899`) → fractured_themes_fix (`:13906`) → fractured_rebuild (`:13914`) → flames (`:13921`) → gradients (`:13928`) → neon (`:13935`) → anime (`:13943`) → optics (`:13951`) → materials (`:13960`). **FLAG:** memory claims image_forge runs LAST so owner art overrides procedural finishes of the same id; in the current code it installs at `:13839`, BEFORE fractured/flames/etc., so a colliding `fm_`/`ff_`/`flm_` id would now win over forge art. Verify ordering before relying on forge-overrides-everything.

### 13. EXACT wiring map to add a new finish (the static-catalog sync requirement)

A registry-registered finish that is NOT in the static JS catalog is **INVISIBLE** in the picker/search — the UI runs off static catalogs, and the runtime registry-truth sync will PRUNE static rows whose ids aren't server-registered. To add a finish:

1. **Author the functions** in a module under `engine/paint_v2/` (or an `engine/expansions/<family>_2026.py` with an `install_into_engine(mono_reg, base_reg=None)`). Honor the contract from §2 and the spec-traces-paint doctrine.
2. **Register in the engine.** Monolithic: `mono_reg[id] = (spec_fn, paint_fn)` inside your `install_into_engine`, and add the install call into the `_spb_apply_colorshift_rework_2026` chain (§12). Base: add to `engine/base_registry_data.py` + win the override stack (§10). For prefix-keyed picker groups (`fm_/fs_/gl_/spectrum_`...) also push into `FUSION_REGISTRY` (mono + `fusions.FUSION_REGISTRY` + `shokker_engine_v2.FUSION_REGISTRY`) so `get_fusion_group_map()` (`engine/expansions/fusions.py:8802`, dynamic on id prefix) sees it.
3. **Wire the static catalog `paint-booth-0-finish-data.js`** (BOTH root and `electron-app/server/` copies): add the `{id,name,desc,swatch}` row to `MONOLITHICS` (`:1652`) or `BASES` (`:15`); add the id to the right group — `BASE_GROUPS` (`:3591`, the authoritative base→category map, NOT metadata `family`), `PATTERN_GROUPS` (`:3637`, the picker shows ONLY patterns listed here), or a `_SPECIALS_*` group folded into `SPECIAL_GROUPS` (`:1614`) and listed under `SPECIALS_SECTIONS`/`SPECIALS_SECTION_ORDER` (`:1547-1548`).
4. **Sync + bust cache:** `node scripts/sync-runtime-copies.js --write` copies the JS to the mirror; the 13 report-only engine files are NOT copied (edit those in both trees manually). **Bump the JS `?v=` cache token** or Electron won't load the change. **Add any new `engine/expansions/*.py` module to `scripts/runtime-sync-manifest.json` `files`** or the packaged build won't ship it (recurring trap — verified that several recent modules are present, e.g. `fractured_souls_2026.py:214`, `spectrum_arsenal_2026.py:232`; CONFIRM your new module is listed).
5. **Restart the Python server** (Python changes need a restart; boot re-bakes changed thumbnails) and verify: `shokker_engine_v2.MONOLITHIC_REGISTRY[id]` (or `BASE_REGISTRY[id]['paint_fn'].__module__`) points at your module — overrides clobber, so introspect the *shipping* closure, not just the source.

### 14. Gates a new finish must clear (mechanical, fail-closed)

Run before declaring done: uniqueness `<0.80` structural sim (`scripts/spb_uniqueness_gate.py`, plus the whitened gestalt gate `scripts/spb_gestalt_gate.py`); decorrelation `|corr|<0.85`; iron rules (M ch0; R ch1 15–255; Cc ch2 16–255, {0}∪{≥16}); render `<3s @2048` (`scripts/render_time_harness.py` — verify at REAL sizes, 512² swatch timing hid a 57s blowup); `M.std ≥ ~20`; coverage + fineness (CLAUDE.md rule #0b; `mip_survival ≥0.45` healthy); spec-physics (`scripts/fm_spec_physics_gate.py` for FM/FS). **FM/FS ship at M251/B255 rails → any test pushing spec UP reads ~0 movement; use a non-railed finish like "singularity" for headroom tests.**

### Caveats / could-not-fully-verify
- All memory files carry "11–21 days old" staleness banners; I re-verified the contracts, registry shapes, file paths, hook line numbers, and the catalog structure directly, but exact finish COUNTS drift constantly (the catalog currently has ~1548 monolithic and ~982 base rows; treat per-category counts in memory as approximate).
- The image_forge "installs LAST" claim is stale (now `:13839`, before fractured/flames) — see §12 flag.
- `runtime-sync-manifest.json` does NOT list every recent expansion module (only 2 of the ones I grepped matched); a future agent adding a module must explicitly add it to `files` and verify the others are covered by a directory walk vs check-only.

---

<a id="spec-sculpt"></a>

## Spec Sculpt (the standalone sculpt tool + its engine)

Spec Sculpt is SPB's most-developed subsystem: a standalone page (`/spec-sculpt.html`, served by `server_routes/static_pages.py:70`) that takes ANY livery paint (TGA/PSD/PNG/JPG) and authors an iRacing **spec map** (Metallic / Roughness / Clearcoat, packed RGBA with A=255) for it — without the user owning a layered PSD or knowing PBR. The same generator powers the in-app "Shokk the World" gallery. The campaign log lives in `SPB_LIVING_WIKI.md` (§"SPEC SCULPT — Melt Minds 50-campaign", lines 248-440) and the build queue in `SPECSCULPT_50_ROADMAP.md`. All 50 roadmap items are marked ✅ done.

### The real generator: `scratch_spec_from_any_paint`
Source of truth: `engine/spec_sculpt/generate.py:2229`. BOTH Auto-Sculpt and Shokk-the-World call it. Signature (verified):
```python
def scratch_spec_from_any_paint(
    tex_rgb_hwc,                       # HxWx3 (or 4) uint8/float paint
    *, seed=9101, chromatic_shift=True,
    dark_interior_flatten=0.38,
    void_metallic_max=92.0, void_roughness_min=158.0, void_clearcoat_max=44.0,
    spec_multiplier=1.0,               # clamped 0..1; "Drama" maps here (route allows 0.5–2.0 ceiling)
    preset_stack=None, catalog_stack=None,   # list[(id, weight)]
    fusion_mix=None, fusion_mix_m/r/cc=None, fusion_strategy="linear",  # or "gloss_win_metallic"
    paint_emphasis="uniform", paint_emphasis_strength=0.0,  # highlights|shadows|saturated|desaturated
    hue_focus_deg=None, hue_focus_width=60.0, hue_focus_strength=0.0,
    vm_detail_scale=None,              # maps to Viva-Mexico DS intensity (~1.59 default)
    pattern_tile=1.0,
) -> np.ndarray  # HxWx4 uint8 RGBA, A=255
```
It has **two distinct code paths**:

1. **Catalog/preset path** (`generate.py:2319-2375`) — used whenever the user picks real finishes or presets (the normal Shokk-the-World/Style-Gallery case). It blends up to `MAX_FINISH_BLEND=5` registered finish spec functions via `blend_registered_specs_float`, then runs the **paint-trace** pipeline from `engine/spec_sculpt/paint_trace.py` so the catalog look TRACES the actual livery panels instead of reading as full-frame wallpaper: `edge_gated_catalog_detail` → `imprint_scratch_highpass` (mix 0.48) → `spatial_envelope_catalog` (0.92) → `apply_paint_linked_emphasis` → `apply_paint_trace_prepass` (detail_scale 1.48) → (`_inject_uniform_paint_detail_floor` only if `tex.std()<0.04`, i.e. blank/solid liveries) → `finalize_traced_spec_u8`. **Critically it does NOT decorrelate or add clearcoat depth** — a 2026-06-25 fix (`generate.py:2370-2375`): those authored finish specs (FRACTURED, carbon weave, fs_blood_marble) are owner-tuned and decorrelation would rewrite their roughness ~180 levels. Returns here.

2. **Legacy paint-derived scratch path** (`generate.py:2377-2396`) — when no preset/catalog is selected. Builds spec from paint via `_scratch_spec_from_paint` → `apply_paint_linked_emphasis` → `_pre_adjust_viva_mexico_spec` (the shared Viva-Mexico DNA grid pass, see `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md`) → masked composite + iron-safe floors → `_post_adjust_viva_mexico_spec` (DNA void clamp on dark paint) → finally `_clearcoat_depth(_decorrelate_roughness(out, tex, seed), tex, seed)`. This is the ONLY path that runs decorrelation + clearcoat depth, because it's the path where Roughness was historically just inverted Metallic.

**Paint-aware by default:** `generate.py:2292-2296` — when the caller asks for `uniform`/strength≤0, it auto-derives a per-seed emphasis from `(HIGHLIGHTS, SATURATED, SHADOWS, HIGHLIGHTS, DESATURATED)[seed%5]` at strength 0.5, so the spec adapts to the car AND preview↔final stay byte-identical for a given finish+seed. `apply_paint_linked_emphasis` (`generate.py:89`, 5 modes in `VALID_PAINT_EMPHASIS`, `generate.py:28-40`) ties M/Cc up where the chosen luminance/saturation cue fires.

### Decorrelation: `_decorrelate_roughness` (generate.py:1930)
Gives Roughness its OWN geometry from an independent paint cue and **adaptively solves the amplitude** so `|corr(M,R)|` lands at the band centre `TARGET=0.785` (inside the <0.85 doctrine). CUE A = local high-frequency detail energy (Gaussian mean/var, percentile-normalized); CUE B = a fine brushed micro-grain (`cv2.GaussianBlur(raw,(9,1),0)`, detail-gated so it's brushed not speckle). It solves a quadratic in `s` for `corr(M, R+s·u)=TARGET` (`generate.py:1999-2005`), clips scale 0..120, spares glossy/mirror pixels (`M≥240→gate 0`), and is iron-safe inline. Metallic is untouched. No-op when already decorrelated. ~160 ms @1024. `_clearcoat_depth` (`generate.py:2027`) then adds paint-anchored clearcoat DEPTH peaking on specular crests (white-tophat on luma + bright-ridge), gloss-readiness gated, additive, mirror-safe; ~95 ms @1024.

### Auto-Sculpt — analyze → pick material → generate
Two layers exist; mind which is wired:
- **`zoned_auto_spec` (generate.py:2151) — the SHIPPED headline "Auto-Zone" one-click** (mode='zoned' in the generate route; UI button `#btnAutoZone`, `spec-sculpt.html:1088`). It k-means-segments the paint into color regions and assigns a fitting material per region via `_zone_classify` (`generate.py:2117`) using mean color + texture busyness + **coverage** (the key intelligence: a small bright-neutral cluster = chrome trim, but a BIG bright-neutral field = satin body, so a white car doesn't become a whole-car mirror). Materials resolve through the `HUE_MATERIALS` table (`generate.py:1518` — chrome `(238,30,232)`, matte `(40,205,18)`, carbon `(70,150,55)`, candy `(116,40,250)`, gold, pearl, gunmetal, etc., all iron-safe by construction). Feathered, detail-modulated, iron-safe, deterministic, ~0.12-0.13 s, ~9 distinct materials/livery.
- **`engine/spec_sculpt/auto_sculpt_suggest.py` — a PROTOTYPE, explicitly UNWIRED** (its own docstring says so). `suggest_materials()` maps paint features (luma/saturation/edge_density/hue_spread) → 8 archetypes → safe preset ids with reasons; `suggest_materials_by_region()` is a grid version. Flag: it renders nothing and is not called by any route — the production "intelligence" is `zoned_auto_spec` + the per-seed auto-emphasis, not this file.

### Shokk-the-World — N diverse looks from one paint
Route `POST /api/spec-sculpt/batch` (`server.py:6008`). Renders up to 24 small spec PREVIEWS from one paint in a single request (no TGAs/jobs written; the user picks one, then full-res via `/generate`). Default variation list comes from `_spec_sculpt_world_variations` (`server.py:5978`) → `engine/spec_sculpt/spec_index.py` `pick_diverse(n, seed, star_ids=...)` which selects N maximally-different above-quality finishes from the **whole ~2,145-finish library** (owner-KEEP ids from the preset audit are weighted up via `_spec_sculpt_star_ids`, `server.py:5963`); falls back to the curated `SPEC_SCULPT_WORLD_RECIPES` (`server.py:5934`, 24 named looks). Each look gets its own finish (catalog or preset stack) + a rotating per-look emphasis `("highlights","saturated","shadows","highlights","desaturated")[i%5]` and seed `base_seed + i*17` (`server.py:6193-6206`). It also renders an **on-car preview** of each look on the USER'S livery (`_on_car_render`, `server.py:6169`) by relighting via `sun_sweep.derive_micro_normal`/`relight_frame`. `GET /api/spec-sculpt/world` (`server.py:5996`) returns just the look list. Re-roll tracks shown ids so each "Re-roll 20 more" walks new finishes. Layer-aware: a PSD + `protect_layers`, or auto-protect on a flat paint, shields decals across the whole gallery (`build_protect_mask`/`auto_protect_mask_from_paint` + `apply_sculpt_mask`, `server.py:6080-6128`).

### Iron-legality — the 3 iRacing spec rules
`iron_validate` (`generate.py:1747`) / `iron_fix` (`generate.py:1770`). Only violating pixels change; legal specs pass through unchanged. The three rules (exact thresholds):
1. **clearcoat_band** — Clearcoat in the illegal 1–15 "whitewash" band is forbidden (`iron_fix` snaps `Cc<8→0`, else `→16`).
2. **low_roughness** — Roughness `<15` on non-mirror pixels (`M<240`) is forbidden (floor to 15).
3. **chrome_plate** — mirror-chrome (`M≥240`) over >55% of the car is forbidden (`iron_fix` demotes `M≥240→239`).
Wired so EVERY sculpt is legal: `/generate` iron_fixes at both the preview and 2048 save sites, plus `_decorrelate_roughness`/`_clearcoat_depth` apply the same caps inline. Surfaced in the UI as the green "🛡 Physically valid" badge. Verified clean by the real-file QA (only 2/52 raw chrome-plate cases, both auto-corrected).

### The generate route + its modes
`POST /api/spec-sculpt/generate` (`server.py:7654`) is the full-res (2048) builder + iRacing deploy (writes `car*.tga`, optional live-link to `Documents/iRacing/paint/<folder>/`). `_run_sculpt_spec` (`server.py:7888`) dispatches on `mode`:
- `zoned` → `zoned_auto_spec` (Auto-Zone).
- `hue_rules`/`tone_bands` present → `hue_material_spec`/`tone_material_spec` (Color→Material / Tone→Material).
- `candy_depth` → `candy_depth_spec_from_any_paint`.
- `fracture` → `fracture_spec_from_any_paint` (`engine/spec_sculpt/fracture.py`; 5 dials: ignition/angle_gate/trace_strength/calm_floor `FRACTURE_CALM_FLOOR_DEFAULT=30`/decorrelation).
- default → `scratch_spec_from_any_paint` (scratch/catalog/fusion).
Post-pipeline knobs all flow through here: `auto_levels`, `hsb_shift`, `apply_channel_gain` (per-channel M/R/Cc gain), `weather_spec` (detail injector), auto-protect, mask grow/feather. `/analyze` (`server.py:7599`) inspects dimensions + returns a preview.

### Other engine functions + routes (all under `/api/spec-sculpt/`)
- `hue_material_spec`/`tone_material_spec`/`layer_material_spec`/`gradient_material_spec` (`generate.py:1566/1636/1667/1906`) via `POST /api/spec-sculpt/hue-map` (`server.py:7147`) — one endpoint, four modes (rules / tone_bands / layer_materials / gradient).
- `brush_material_spec` (`generate.py:1786`) via `POST /api/spec-sculpt/brush-map` (`server.py:7237`) — the Region Brush (stamp painted material masks, later strokes win, iron-safe).
- `weather_spec` (`generate.py:1826`) — swirls/scratches/brushed/grime/orangepeel micro-texture on Roughness+Clearcoat.
- `auto_protect_mask_from_paint` (`generate.py:657`) + `separate_livery_layers`/`_guided` + `build_protect_mask`/`refine_sculpt_mask` — flat-paint decal protection (numbers/sponsors) with `_glyph_textline_mask` text-line detection (`generate.py:539`) that rejects textures; previewed via `/api/spec-sculpt/auto-protect-preview` (`server.py:6425`).
- `/api/spec-sculpt/presets` (GET, `server.py:5903`), `/world`, `/batch-folder` (batch a folder, ≤64), `/open-folder`, `/audit` (owner KEEP/REBUILD/RENAME triage), `/catalog-index`.

### Presets library
`engine/spec_sculpt/presets.py`: ~125 curated presets built via `_p()` (each maps a clean slug → real registered finish id(s), `MAX_PRESET_STACK=5`), PLUS `presets_bespoke50_2026.register()` (+50 designer cross-family fusions, e.g. Liquid Obsidian/Venom Candy/Wormhole Chrome, guarded against unshipped sources) and `presets_overnight_2026`, all appended into `SPEC_SCULPT_PRESETS` at import (`presets.py:410-420`). Helpers: `normalize_preset_stack`, `preset_stack_to_catalog` (resolves via `PRESET_CATALOG_BY_ID`), `PRESET_TILE_BY_ID` (per-preset pattern fineness for the "renders too big" fix). The preset audit reported 388/388 resolved ids OK after remapping 10 dead spectrum_* ids.

### The 50-feature campaign (highlights, all ✅)
From `SPECSCULPT_50_ROADMAP.md` + wiki §248-440. Server-engine features: Auto-Zone (`zoned`), Color→Material (#7), Tone→Material (#9), Per-PSD-layer material (#10), Physically-Valid badge + iron auto-fix (#11), preset audit/repair (#12), Region Brush (#13), Material Weathering (#13j), Material Gradient (#13l/#41), +50 bespoke designer blends (#17), Batch-sculpt-a-folder (#30), flat-paint decal auto-protect (#51/#52). Client-only features: Style Gallery + "Fresh from catalog" tiles (#4/#6a), Drama master slider → spec_multiplier 0.5–2.0 (#5), Material Spotlight (#6), Surprise Me (#6c), **Text→Material "Sculpt from Words"** (#13i — `_parseTextScheme`, `spec-sculpt.html:2686`: phrase-splits NL like "aggressive matte black, chrome accents, wet-candy lows" into base + hue-rules + tone-bands + Drama, posts to `/hue-map`; vocab tables `_TEXT_MAT/_TEXT_HUE/_TEXT_DARK/_TEXT_LIGHT/_TEXT_DRAMA` at `:2672`), Reference-photo material match (#13k), **Channel Decorrelation Meter** (#20 — client `_pearson` of composite R/G/B=M/R/Cc, 3 bars + verdict, `spec-sculpt.html:1592`), Macro Loupe (#14, ~5.8× pixel magnifier + plain-English material readout), Material Probe (#27), Style Blend (#15), Symmetry Mirror (#23), Mask Refine (#24), Smart Layer Auto-Material (#25, `_inferLayerMaterial`), Shimmer preview (#21), Theme Packs (#22), Undo/Redo timeline (#18), import/export `.shokklook` (#29), render-time budget meter (#28), share proof card (#16).

### QA / audit status
`SPECSCULPT_QA_FINDINGS_2026-06-25.md` (real-file harness `_specsculpt_qa_harness.py` over `C:/1Shokker Paint Car Examples`, 52 files): zero crashes/NaN/flat/>3s renders (1.09–1.98 s @1024, mean 1.30). Decorrelation fix landed `|corr(M,R)|` from **0.92→0.79 mean, max 0.98→0.85 (0/52 over the line), CORRELATED 33→0**. Round-2 (2026-06-26) added `_clearcoat_depth` (Cc_mean 38→53, Cc_std 23→44, flat-Cc files 22→4), confined decorrelation to the legacy scratch path, added text-line auto-protect recall, shipped Auto-Zone, and locked **108 gate tests** (`tests_v2/test_spec_sculpt_snapshot.py`, `scripts/spec_sculpt_qa_diff.py`, property gates). Regression harness: the `spb-spec-sculpt-qa` skill. The conclusion that the generator is GOOD (decorrelated, paint-tracing, diverse) is supported by this QA.

### Flags / discrepancies (verify before trusting)
- **"sun_sweep.py REMOVED" is INACCURATE as stated.** The file `engine/spec_sculpt/sun_sweep.py` still exists (7,382 bytes, Jun 19) and is still imported by the batch route for the on-car relit preview tiles (`server.py:6163`), and `register_sun_sweep_routes` is still wired in `server.py:8554` (it registers `/sun-sweep` + `/api/sun-sweep`, a separate finish-relight surface). What was actually removed (owner, 2026-06-24, "relight is a dead end") is the **Spec-Sculpt Sun-Sweep FEATURE** and its `/api/spec-sculpt/sun-sweep` route (live relight, Before/After wipe, Hero GIF — roadmap items #1/#2/#3/#26, all marked ❌). Do not rebuild relight as a Spec Sculpt feature, but the engine module is not deleted.
- **"decorrelated mean 0.73"** — I could not locate a 0.73 figure; the verified number is **mean ~0.79 (max 0.85), CORRELATED 33→0** from `SPECSCULPT_QA_FINDINGS_2026-06-25.md`. `CATALOG_HEALTH_REPORT.md` (2026-06-28) is about the broader **catalog** (render perf, uniqueness de-dupe), not the Spec Sculpt generator specifically, and does not state 0.73. Treat 0.73 as unverified; 0.79 is the documented value.
- **"Auto-Sculpt (analyze→pick→generate)"**: the analyze→pick-material classifier in `auto_sculpt_suggest.py` is an unwired prototype; the production one-click intelligence is `zoned_auto_spec` (Auto-Zone) plus the per-seed auto-emphasis inside `scratch_spec_from_any_paint`.
- Three runtime copies must stay synced after engine edits (root → `electron-app/server/...`); use the `spb-ship-check` ritual (parse-check, gate battery, sync, bump cache token) or fixes won't reach Electron.

---

<a id="smart-separate-car-intelligence"></a>

## Smart Separate, Car Intelligence & the AI Separation Model

**One-paragraph orientation.** SPB lets a user load a *flat* iRacing livery texture (`car_*.tga`, no PSD) and have the app figure out, by itself, what is a **car number**, a **sponsor / wordmark**, a **graphic brand logo**, the **car template** (glass / grills / headlights / fixed bits), and the **base paint design** — then build those as real, restrict-able layers so a PSD-less buyer still gets layer-aware sculpting. There are **two engines**: (1) a **shipped, CPU heuristic+OCR engine** (EasyOCR + a per-car "learned" template prior + car identification), and (2) a **research-grade trained AI model** (SAM + multi-scale OCR + CLIP multi-class head, 85.7% on priority families) that is **not shipped to buyers** — it runs only on a GPU machine and is wired in as an *optional, graceful* local hybrid. This section maps every file, function, route, and the exact shipped-vs-research boundary. The single most detailed running history lives in the repo at `CAR_INTEL_MISSION.md` (144-line ROUND LOG, newest entries are Codex's `2026-06-29` autonomous-loop cycles) plus `SMART_SEPARATE_HANDOFF_FOR_CODEX.md` and `DEPLOY_SMART_SEPARATE_MODEL.md`. **Codex now owns this feature** (it can live-test the Electron UI; Claude was told to stay out of `paint-booth-*.js` / `smart-separate*.js` to avoid collisions — see handoff §10).

---

### 1. The shipped heuristic engine (CPU — what every buyer gets)

Two engine modules under `engine/spec_sculpt/`, both **additive and graceful** (degrade to empty layers, never throw on missing deps):

**`car_layers.py` — car identification + the 4/5-layer assembler.** (Verified; this file is newer than the memory and already contains all the Codex cycle changes.)
- `separate_into_layers(tex, car_slug=None, auto_id=True, use_template=True, use_ocr=True, car_family_hint=None, source_slug_hint=None, brand_graphics_merge="sponsors")` — the top-level entry (`car_layers.py:277`). Returns `{"layers": {numbers, sponsors, template, brand_graphics, paint} (uint8, 255=member at input res), "car": [matches], "size": (H,W), "brand_graphics_merge": <mode>, "template_guard": {...}}`. **PAINT is the complement** of everything else (`paint = where(decals, 0, 255)`, `:367`) so the five masks **partition the car** — that partition property is what makes the front-end real-layer trick valid (see §4).
- `identify_car(tex, topk=5, family_hint=None)` (`:200`) — scores the livery against learned per-car "signatures" with `score = 0.45*ZNCC(luma) + 0.55*ZNCC(edges)` (`:214`). The edge term (`_edges`, Sobel gradient magnitude, `:68`) captures the **UV panel layout** which is colour-independent and shared across every livery of a given car. Memory's quoted accuracy: **EXACT top-1 ~0.79, FAMILY top-1 ~0.86** (up from a luma-only v1 at 0.12). `_family()` (`:78`) buckets slugs into `dirt_late_model / nascar_stockcar / dirt_modified / dirt_open_wheel / gt_road / truck / late_model / cup_road / other …`.
- `_template_prior(slug, H, W)` (`:221`) — the TEMPLATE layer. It is the **intersection** of three signals from the per-car learned data: (a) **low-variance** mask (`template_mask.png`, regions painters never change), (b) **template tone in the consensus median** (`med_dark` = dark+desaturated glass/grills, OR `med_light` = bright headlights/chrome, `:244-246`), and (c) a **median-smoothness gate** (low Laplacian — glass/grills are flat in the median, dark *textured* paint is not, `:250-252`). The colour of *this* livery never enters, so it cannot grab green/dark paint. Result is **capped to `0.002 ≤ frac ≤ 0.10`** (`:333`); anything bigger is dropped to empty (better no template than a paint flood).
- **Template guards** (Codex 2026-06-28/29): a template only applies when `conf ≥ _TEMPLATE_CONF_MIN = 0.20` (`car_layers.py:26`, raised from 0.15 to stop weak GT4→wrong-GT3 swaps) AND `template_brand_compatible(source_slug, matched_slug)` is true. The latter (`:151`) uses `_vehicle_make_tokens()` (`:118`, a make→token dictionary: chevy/ford/toyota/bmw/ferrari/porsche…) to **block** a template when the source folder advertises one make but the inferred car is a different make (e.g. `nwcamaro2014` matching `nwford2013`). The decision is exposed as `template_guard` metadata `{status: applied|blocked|skipped, reason: make_mismatch|low_confidence|no_match|area_rejected, source_slug, matched_slug, score, template_frac}` (`:307-336`) which the route returns and the UI surfaces as an amber "Template blocked" line.
- `hint_from_path(path)` (`:162`) — when the front-end sends the original iRacing paint path, this resolves the folder slug to an exact learned car, else a **narrow same-line alias** (`aliases` dict, `:180-190`: e.g. `trucks_silverado→trucks_silverado2019`, `ferrari488gte→ferrari488gt3`, `stockcars2_chevy_cot→stockcars2_chevy_gen4cup`), else a family hint. The aliases are deliberately conservative — "a wrong template is worse than an empty template."
- `_characteristic_template()` (`:258`) still exists but is **no longer used by the assembler** — it was the dark-paint-flood culprit on low-confidence dirt cars and was removed from the path (`:319-328` only uses the learned `_template_prior`).

**`smart_separate.py` — OCR glyph separation (NUMBERS / SPONSORS).** (Verified.)
- `separate_livery_layers_smart(tex, *, min_conf=0.30, want_overlay_boxes=False, rotations=(0,1,2,3))` (`:335`) — the OCR entry that `separate_into_layers` calls (when `use_ocr=True`). Returns `{numbers, sponsors, paint}` uint8 masks, or `None` if EasyOCR is unavailable (caller falls back). Pipeline: `_ocr_boxes` (`:56`, multi-scale, runs OCR at each 90° rotation and maps polys back — iRacing UV unwraps rotate/mirror panels, so this catches vertical/upside-down sponsor text like a vertical MENARDS) → `_classify` (digits→NUMBERS, words→SPONSORS) → tight **Otsu glyph masks within each OCR polygon** (`_tight_glyph_mask`, not bounding boxes). **~13s/livery CPU** at the full `rotations=(0,1,2,3)`; pass `(0,2)` for a ~7s pass.
- **Two correctness passes** layered on top, both precision-first:
  - **Word-demotion** (audit #2, `:354-368`): each NUMBER candidate's crop is re-read; if it positively reads as a WORD (`_crop_reads_as_word`, `:281`), it is moved to SPONSORS. Only positive word-reads move, so a real (even stylized) number is never lost. Fixes the number↔sponsor confusion.
  - **Big-number rescue** (`:373-376`, `_big_number_rescue` → `_proposals_for_big_numbers` at `:154` + `_confirm_digit_crop` at `:216`): MSER **shape-proposes** large isolated glyph blobs the global OCR detector misses (a door number too big for the detector's sweet spot), then **re-OCRs each crop at its own scale** and accepts **only a short (≤3) purely-numeric token** at conf ≥ 0.45. The digit-only *allowlist* was rejected because it forced bold sponsor letters (e.g. "NATIONWIDE") to read as digits; the shipped version uses a FREE read + numeric-token filter. Validated **0/16 false positives** on real NASCAR liveries; fires rarely by design (precision over recall — mislabeling a sponsor as a number corrupts the #1 layer). The clamp bug `max(96/h, 1.0)` → `max(96/h, 0.12)` lets a HUGE number shrink to the detector sweet spot.

**Brand-graphics (graphic logos with no readable text) — the 3-way layer.** Graphic logos (m&m characters, Monster claw, Bass Pro fish) are **ambiguous** (paint design vs sponsor decal) and OCR can't see them. `separate_into_layers` adds a 5th `brand_graphics` layer fed by `logo_clip.detect_logo_mask()` (`car_layers.py:350-358`), and `brand_graphics_merge` chooses `"separate"` (own layer) / `"paint"` (leave in paint) / `"sponsors"` (fold in). **The default is now `"sponsors"`** (Codex cycle 48) so the default output is the owner's four target buckets. **Critically: the CLIP detector `engine/spec_sculpt/logo_clip.py` is OFF by default** (opt-in `SPB_LOGO_CLIP=1`, requires `open_clip` which the **shipped app env does not have**) — so on a buyer machine `brand_graphics` is **empty** and output is identical to the old 4-layer result. The 3-way *UI/route/merge plumbing* ships; the *detector* does not.

**The per-car "learned" intel — `_car_intel/`.** Built offline by `_car_intel_learn.py` (`learn_car()`) + the kill-safe driver `_car_intel_all.py`. For each car it stacks that car's liveries at 512², takes the per-pixel **median** (consensus) and **stdev** (variance), and writes `_car_intel/<slug>/` = `median.png`, `stdev.png`, `template_mask.png` (low-variance), `signature.npz` (`med` 64×64 luma, `std` 64×64, `template_frac`), `meta.json`. **Verified: exactly 67 cars learned** (`ls _car_intel/*/signature.npz` = 67). Breadth is **data-capped at 67** — the other ~113 iRacing folders in the owner's local paint dir have too few liveries to learn. There is also an HTML reference library: `_car_intel/index.html` (master dashboard, verified present) + per-car pages with 4-layer overlay galleries (67 cars, 268 overlays) built by `_car_intel_html.py` + `_car_intel_layers.py`.

**`auto_protect_mask_from_paint` (Spec Sculpt's lighter cousin).** Separate from the layer separator: `engine/spec_sculpt/generate.py:657` `auto_protect_mask_from_paint(tex, strength=1.0, max_protect_frac=0.55)` returns a **uint8 sculpt mask (255=SCULPT, 0=PROTECT, None when unsure)** that protects detected decals while sculpting the base paint, for PSD-less Spec Sculpt users. v2 fuses standout-edge + base-color-deviation + extreme-luminance + a color-agnostic SWT/MSER glyph detector + a local periodic grill-mesh detector + a smooth dark-housed light-cluster cue, all behind global-busy / patterned-base / cap guards so a busy carbon/flake/camo **base** is not mistaken for decals. Wired into Spec Sculpt `/generate` via an `auto_protect` flag (only when no PSD) + a `🪄 Auto-detect decals` toggle + `/auto-protect-preview`. The mask convention mirrors `build_protect_mask(psd_path, protect_names)` (`generate.py:1442`). The guided Studio variant `separate_livery_layers_guided(...)` (scribble-seeded GrabCut grow + edge-snapped include/exclude brushes) also lives in `generate.py`.

---

### 2. The Flask routes (server.py)

- **`POST /api/auto-layers`** (`server.py:6621`, `api_auto_layers`) — the **"🧩 Auto-build layers"** button. Accepts a multipart upload (`paint_file`/`file`/`image`) OR, internal-only (`_require_spb_internal_request`), a `paint_file` path (added because a real 2048² RGBA TGA is ~16.7 MB and direct multipart hits Flask 413 — see cycle 38). Params: `preview_size` (default 1024, clamped 256..2048), `brand_graphics_merge`, `car_hint_path`/`paint_file_hint`. **It runs the GPU hybrid if available, else the heuristic.** `:6700` calls `smart_tga_gpu_bridge.separate_file_if_available(...)`; if that returns masks it uses the model's `numbers/text/logos` + the *existing learned template prior* (`separate_into_layers(..., use_ocr=False)`) and stamps `r["engine"]="gpu_hybrid"`; otherwise it calls the full `separate_into_layers(...)` and stamps `r["engine"]="heuristic_ocr"` (`:6740-6744`). Layer priority on overlap: **numbers > template > sponsors > brand > paint** (`:6728-6730`, `car_layers.py:338-342`). Returns `{success, car:[{slug,family,score,template_frac}], layers:{numbers,sponsors,template,brand_graphics,paint} each a white-on-black PNG data URL, overlay (tinted: numbers=red, sponsors=blue, template=green), fractions, size:[H,W], engine, gpu_cache, source:{mode,label,bytes}, template_guard, companion_*}`.
  - **Companion-file boosts** (Codex, optional, env-gated): `_companion_number_mask` (`:6754`, env `SPB_SMART_TGA_COMPANION_NUMBERS`) pulls numbers from a sibling `car_num_<id>.tga`, and `_companion_decal_mask` (`:6851`, env `SPB_SMART_TGA_COMPANION_DECALS`) pulls sponsors from `car_decal_<id>.tga` — **only** when the delta is sparse/component-limited and not whole-canvas (strict gates: source-RGB match, alpha-area, component/large-shape, whole-canvas bbox reject), so a full alternate livery is never carved into a layer.
- **`POST /api/auto-separate-livery`** (`server.py:6513`) — the **older 3-layer** route (NUMBERS/SPONSORS/PAINT only, no template/car-ID) used by the right-panel "Protect" path (`SmartSep.run()`). Smart-OCR is the default (`gv("smart","1")`), classic `separate_livery_layers` fallback.
- **`POST /api/smart-separate/refine`** (`server.py:7004`) — the guided **Studio** brush-refine route. JSON: image b64 + `preview_size` (768) + `sensitivity` + `number_size` + `active_layer` + `number_hint`/`sponsor_hint`/`include_mask`/`exclude_mask` (b64) + `base_masks` echo → `{success, detected, overlay, masks{numbers,sponsors,paint}, fractions}`. Reuses the prior result via `base_masks` so brush strokes don't re-OCR.

---

### 3. The GPU bridge (local-only, graceful) — `engine/spec_sculpt/smart_tga_gpu_bridge.py`

This is the **opt-in hook** that lets the AI model run *on the owner's own GPU machine* without bundling 2 GB of models into the buyer app. (Verified; mirrored to `electron-app/server/`.)
- `separate_file_if_available(image_path, target_shape)` (`:238`) — checks `_availability()`; if the `_gpuenv` python and model files are present it **shells out** to the root-only worker `_separate_image.py` (`subprocess.run([gpu_python, _SCRIPT, image_path, tmp], cwd=_ROOT, …, timeout=SPB_SMART_TGA_GPU_TIMEOUT default 240s)`), reads back `numbers/text/logos/paint` PNGs, resizes to `target_shape`, and returns the dict — or **`None`** for graceful fallback to the heuristic engine. Env knobs: `SPB_SMART_TGA_GPU=0` disables, `SPB_SMART_TGA_GPU_CACHE=0` disables caching, `SPB_SMART_TGA_ROOT` / module-walk locates the runtime root so the Electron mirror (which lacks the big assets) can still reach the canonical workspace `_gpuenv`.
- **SHA-256 cache** (`_smart_tga_runs/gpu_cache/`, keyed by image hash + target size + `SEP_WORK`/`SEP_OCR_MODE`/thresholds + model/script mtimes, cache version `smart_tga_gpu_v2`): a cold pass is ~50–170 s; a warm hit is ~0.1–0.6 s. `last_info()` (`:113`) reports `{available, cache: hit|miss|off|unavailable, cache_key, elapsed_sec, runtime_root, reason: disabled|missing:*}`, surfaced by the route as `gpu_cache` and by the UI as "Engine: gpu_hybrid / Cache: hit / Reason: …".

---

### 4. The front-end — `js/features/smart-separate.js` (+ studio + spec-sculpt mirror)

- **The right-panel launcher.** `renderLayerPanel()` (paint-booth-3-canvas.js `:17871` per handoff) calls `SmartSep.renderInto()` when `_psdLayers` is empty and a flat TGA is loaded. The card shows **"🧩 Auto-build layers"** (`Lyr.run`) which POSTs to `/api/auto-layers`, plus the older "Protect" flow and a "Open Smart Separate Studio" button.
- **Auto-build now builds REAL stacked layers, not just zones** (the key 2026-06-28 fix). On a successful response, `Lyr.run` calls `Lyr.buildLayers()` (`smart-separate.js:432` → `:597`). `buildLayers` decodes the 5 masks and constructs **virtual `_psdLayers`** entries bottom→top: **Paint → Car Template → Sponsors → Brand Graphics → Numbers** (`:608-614`), each layer's `img` built by `buildMaskedLayerCanvas(livery, decoded, W, H)` (`:504`) = the **livery pixels masked to that region, transparent elsewhere**. It honors the brand-graphics 3-way merge client-side (`:618-625`), sets `window._psdLayers` + `window._psdLayersLoaded=true` + `_selectedLayerId`, pushes an **undo** (`_pushLayerStackUndo('Smart TGA auto-build layers')`, Codex cycle 48), then `invalidateLayerVisibleContributionCache()` + `recompositeFromLayers()` + `renderLayerPanel()` (`:640-651`). **Why this is safe:** because the masks partition the car, a layer stack whose images are the livery-masked-to-region **reconstructs the identical livery** — verified at runtime by `summarizeLayerRoundtrip` (sampled-RGB roundtrip diff must be 0) and `summarizeDecodedAutoLayers` (coverage 1.0, 0 gap, 0 overlap), reported as `layerCheck.restrictReady`.
- **The payoff — restrict-to-layer for free.** Because the auto-built layers are real `_psdLayers`, the **Zone Popout "Restrict to layer" dropdown** (`paint-booth-2-state-zones.js:1573` `renderZoneDetail`, only shown when `_psdLayers.length>0`; `setZoneSourceLayer(i, layerId)` `:4811`) lists them, and the render path's `source_layer` masking works unchanged: `paint-booth-5-api-render.js` resolves `_psdLayers.find(l=>l.id===z.sourceLayer)` → `getLayerVisibleContributionMask` (alpha-based: a layer contributes where its `img` alpha>8 and no higher opaque layer covers it — this is why the virtual `img` must carry the mask as ALPHA) → `source_layer_mask` RLE in the payload (preview/HD/export paths ≈ `:2257/2497/2759` per handoff). So a zone restricted to "Numbers" only paints the numbers. **Zero changes** to the zone/render files were needed — the whole PSD-layer machinery is reused.
- **Studio.** `js/features/smart-separate-studio.js` (`window.SmartSepStudio`, `#ssStudioModal`): a 768² 3-canvas stage (source/overlay/brush) with mode tabs Auto / Mark Numbers / Mark Sponsors / Refine Include / Exclude, brush+hardness, undo/redo, `_refine()` → `/api/smart-separate/refine`, `ST.protect()` (`:548`), and `ST.makeZones()` → `shokkTraceImportZones` (the selling-feature flow). `ST.open()` draws `#paintCanvas`→`ssSourceCanvas`.
- **Spec Sculpt parity.** `js/features/spec-sculpt-layers.js` is the mirror of the auto-layers UI inside the Spec Sculpt page (`#ssLayersCard` button → POSTs `#imgPaintSrc` to `/api/auto-layers`). Owner wanted **both** apps; both are wired.
- **Sync / cache gotchas (binding):** `js/features/*.js` are **NOT** in `scripts/sync-runtime-copies.js` — copy them to `electron-app/server/js/features/` **manually** and `cmp` to verify (`copy-server-assets.js` hard-fails the packaged build on managed-code drift). Every JS/CSS edit needs a **`?v=` cache-token bump** in `paint-booth-v2.html`/`spec-sculpt.html` or Electron serves stale; current tokens evolve fast (e.g. `spb-smarttga-templateguard-20260629`, `spb-smarttga-sourcetelemetry-20260629`). Python route changes need a **Fresh Start** of `server_v5.py`.

---

### 5. The 3 owner-reported UX issues + status (Codex owns the file)

Surfaced 2026-06-28; the owner clicked "Auto-build layers" and reported "VERY POOR" sorting. Root cause per handoff §0: the button runs the **heuristic engine**, whose hard limits are (1) graphic logos with no text are invisible to OCR → fall into PAINT, (2) OCR recall on flat UV maps is fragile, (3) TEMPLATE only exists for the 67 learned cars. The first diagnostic is to run the AI model on the owner's exact car (`python _separate_image.py "<car>.tga" _sep_out` in `_gpuenv`) — if it sorts correctly, the **engine, not the UI**, is the problem.

| # | Issue | Status |
|---|---|---|
| 1 | Auto-build made only zones, not real stacked **Layers** in the right panel | **DONE** — `Lyr.buildLayers()` builds real `_psdLayers` (§4), enabling restrict-to-layer. Implemented but flagged "implemented, unverified in Electron" by Claude; Codex has since route-proven + roundtrip-verified it across many real TGAs. |
| 2 | "Open Smart Separate Studio" button text unreadable (dark `#04121a` on bright gradient) | **DONE** — white text + shadow (`smart-separate.js` ~`:178`). |
| 3 | Studio drawing janky (full 768² `rebuildOverlay()` on every pointermove) **and** draw didn't update the live preview | **DONE (a+b)** — `onMove` rAF-coalesced (`scheduleOverlay()`); `onUp` debounce-pushes marks through `ST.protect()`→`triggerPreviewRender()`. **OPEN (3c)** — the owner's chosen direction is to **draw directly on the MAIN `#paintCanvas` with a small floating tools strip (no modal)**; the Studio is still a modal. This is the main remaining build (handoff §7: add a transparent overlay canvas over `#paintCanvas`, track its rect on `applyZoom`/resize — **avoid `ResizeObserver`**, it caused a prior view-jump bug — map CSS→canvas px like `stagePoint()`, reuse `dabAt`/`strokeBetween`, repurpose the Studio button to enter in-canvas mode; coordinate mapping under zoom/pan is the #1 live-test risk). |

Codex's ongoing autonomous loop (`CAR_INTEL_MISSION.md` cycles 1–48) has additionally shipped: the GPU hybrid path + cache + telemetry badges (Engine/Cache/Reason/Source), `car_hint_path` plumbing, the template brand-conflict guard + `template_guard` UI line, large-TGA JSON-path posting (avoids 413), companion `car_num_*`/`car_decal_*` boosts, adaptive OCR speedups, and undo safety — all additive, gates 40–46/46 green, root↔Electron hash-equal, each needing a Fresh Start.

---

### 6. The AI separation model (RESEARCH — NOT shipped to buyers)

Built overnight 2026-06-28 after the owner reframed: *"train on thousands, NAIL 80%, screw the fringe 20%."* It massively outperforms the heuristic on graphic logos. **Status: trained + validated; the 80% goal is met; whether/how to ship is an OWNER DECISION.**

- **Why a trained model at all:** every off-the-shelf approach **failed** on flat UV maps (documented dead-ends in the ROUND LOG): U-Net on synthetic composites (domain gap), zero-shot CLIPSeg, OWLv2, GroundingDINO, SAM+binary-CLIP-probe — all either grabbed paint or inverted (fired *more* on paint cars than logo cars). Root cause: a UV-unwrapped livery is **out-of-distribution** for natural-image models (logos are warped, split across UV islands). The unlock was the owner's **own thousands of liveries** as training data.
- **Architecture** (`_separate_image.py`, verified): **SAM (Segment Anything, ViT-B)** auto-masks the flat texture into clean per-object masks (`SamAutomaticMaskGenerator`, points_per_side=24, `:46-49`) → **multi-scale + rotation EasyOCR** reads numbers (digit boxes) and sponsor TEXT (word boxes), default `SEP_OCR_MODE=adaptive` (`:24`) → **CLIP ViT-L-14** (`open_clip`, `laion2b_s32b_b82k`, 768-d, per `_logo_data/model.json`) + a **trained 4-class head** (`768-256-128-4`, per `_logo_data/maskcls.json`, classes `{0:PAINT, 1:NUMBER, 2:TEXT, 3:LOGO}`) classifies every remaining mask **logo-vs-paint**. **Hybrid assembly:** OCR owns numbers/text (the model's NUMBER axis was weak — digits look like letters in CLIP space); the model decides logo-vs-paint only on non-OCR masks (its strong axis). Tuning constants (`:16-18`): `LOGO_MIN=0.30`, `LOGO_MARGIN=0.20`, `LOGO_MAX_AREA=0.04` (the area cap kills large-gradient-panel over-grabs without hurting real-logo recall).
- **Entrypoint:** `separate_image(path_or_rgb) -> {numbers, text, logos, paint}` (boolean masks at full image res). CLI: `python _separate_image.py "<image.tga>" [out_dir]` writes `numbers.png`, `text.png`, `logos.png`, `paint.png`, `overlay.png`, `layers.json`. Runs only in **`_gpuenv`** (isolated venv: torch 2.6+cu124, open_clip, segment-anything, easyocr, opencv; owner's RTX 4060 Ti). `SEP_PROFILE=1` dumps stage timings; cold worker ~40–58 s @1024.
- **Model files (verified in `_logo_data/`):** `sam_vit_b.pth` (375 MB), `maskcls.npz` (the shipped **909-livery model**, restored from `maskcls_909.npz` — see below), `maskcls.json`, `model.json` (ViT-L-14), plus the binary-probe artifacts (`probe.npz`, `probe_samneg.npz`) and the full harvest. The training/eval chain (auto-labels masks via OCR+geometry+surround-contrast, **no manual labels**): `_sample_liveries.py` → `_harvest_masks.py` → `_collate_harvest.py` → `_train_maskcls.py` → `_assemble_eval.py`.
- **Results** (independent 7-agent review panel, held-out cars): **85.7% of priority-family cars** (dirt / stock / truck / late-model) fully correct (24/28); **base paint kept clean 96%**; numbers 82–96%; **overall incl. fringe GT/road 66%** (the accepted 20%). Corpus: 3092 body TGAs / 181 folders; 909 liveries harvested → 11,570 masks; per-mask held-out acc 0.884, LOGO prec/rec 0.82/0.84. Data-scaling was proven (172→680 liveries lifted *every* class). A bonus full-data retrain (1737 liveries / 26,679 masks) **plateaued** per-mask and tested slightly *worse* on priority families (78.6%), so the **909-model was kept** as the shipped artifact (better on the owner's cars).
- **Deployment = owner decision** (`DEPLOY_SMART_SEPARATE_MODEL.md`): the model needs SAM (375 MB) + CLIP ViT-L (~1.7 GB) + a GPU — the shipped CPU app (EasyOCR only) cannot host it. Three options: **(A)** optional "Smart Separate Pro" GPU download (mirrors the existing finish-pack-downloader pattern, gate behind a GPU check, fall back to OCR+brand-3way+brush), **(B)** a small **cloud GPU endpoint** the app POSTs the TGA to (thin client, per-call cost), **(C)** **bundle** for GPU machines (biggest installer). **One-hook wiring** when a path is chosen: in `car_layers.separate_into_layers`, when the model is present + enabled (env `SPB_LOGO_MASKCLS=1`), replace the brand-graphics/sponsor feeders with `separate_image()`'s `logos`/`text`; keep numbers/template on the existing reliable paths. The local **GPU-hybrid bridge (§3) is essentially option (C) for the owner's own machine** — already wired and graceful. Visual report: `SPB_SMART_SEPARATE_MODEL_REPORT.html`. Next accuracy levers (diminishing past 85%): harvest the remaining ~2,200 liveries, broaden the LOGO label, a second hard-neg round on paint over-grabs.

---

### 7. Gates, sync, and key file map (quick reference)

- **Gate battery (must stay green):** `python -m pytest tests_v2/test_spec_sculpt_quality_gate.py tests_v2/test_autoprotect_textline.py tests_v2/test_spec_sculpt_snapshot.py tests_v2/test_smart_separate_guided.py tests/regression_base_scale_no_whole_canvas_tile_test.py -q` (Codex's "handoff gate battery" is the same set, reported as 40–46/46).
- **Backend:** `engine/spec_sculpt/car_layers.py` (id + assembler), `smart_separate.py` (OCR), `smart_tga_gpu_bridge.py` (GPU hook), `logo_clip.py` (opt-in CLIP brand detector, OFF), `generate.py` (`auto_protect_mask_from_paint:657`, `separate_livery_layers_guided`, `build_protect_mask:1442`). Routes in `server.py`: `/api/auto-layers:6621`, `/api/auto-separate-livery:6513`, `/api/smart-separate/refine:7004`.
- **Frontend:** `js/features/smart-separate.js` (launcher + `buildLayers:597`/`buildMaskedLayerCanvas:504`), `smart-separate-studio.js` (guided modal), `spec-sculpt-layers.js` (Spec Sculpt mirror); restrict-to-layer in `paint-booth-2-state-zones.js` (`renderZoneDetail:1573`, `setZoneSourceLayer:4811`), render masking in `paint-booth-5-api-render.js`, layer machinery (`_psdLayers`, `recompositeFromLayers`, `getLayerVisibleContributionMask`, `renderLayerPanel`) in `paint-booth-3-canvas.js`.
- **Research / data (root, gitignored / not shipped):** `_separate_image.py`, `_logo_data/`, `_gpuenv`, `_car_intel/` (67 learned cars + `index.html` library), `_car_intel_learn.py`/`_car_intel_all.py`/`_car_intel_html.py`/`_car_intel_layers.py`, the training chain scripts, `_smart_tga_runs/` (Codex cycle artifacts).

**Verification notes / caveats.** I verified against the live code: `car_layers.py` (full read — signatures, `_TEMPLATE_CONF_MIN=0.20`, the 0.45/0.55 ZNCC blend, the 0.002–0.10 template cap, `template_guard`, `brand_graphics_merge="sponsors"` default), `smart_separate.py` (`separate_livery_layers_smart` signature + the word-demotion + big-number-rescue passes), `server.py:6621-6760` (the GPU-hybrid branch, `engine` field, companion masks), `smart_tga_gpu_bridge.py` (subprocess shell-out to `_separate_image.py`, cache, `last_info`), `_separate_image.py` (SAM+CLIP+OCR, the LOGO/NUMBER constants, `maskcls` 768-256-128-4), `smart-separate.js:597-656` (`buildLayers` real-layer build + roundtrip checks), and confirmed file existence/sizes (`sam_vit_b.pth` 375 MB, `maskcls.json`/`model.json` contents, **exactly 67** `_car_intel/*/signature.npz`). The `paint-booth-*.js` line numbers for restrict-to-layer / render-masking / layer machinery are taken from `SMART_SEPARATE_HANDOFF_FOR_CODEX.md` §5 (marked there as verified, but a few `~approx`); I confirmed the *symbols* exist and `_psdLayersLoaded` is read across `paint-booth-5-api-render.js` at lines 2331/2568/2781/2987/3194 — treat the exact restrict-dropdown/render-mask line numbers as approximate. `smart-separate-studio.js` internal line numbers (`stagePoint`, `dabAt`, `_refine`) were not independently re-read and come from the handoff.

---

<a id="zones-layers-live-preview-frontend"></a>

## Zones, Layers, Live Preview & the Front-end

The painting UI is a set of monolithic, globally-scoped browser scripts loaded in order by `paint-booth-v2.html`. There is no module system: every function/`let`/`var` is a top-level global, and load order matters. The five workhorse files (verified line counts):

| File | Lines | Role |
|---|---|---|
| `paint-booth-2-state-zones.js` | 19,573 | zone state model, undo stacks, zone-detail/popout panel, swatch picker, finish library |
| `paint-booth-3-canvas.js` | 26,962 | the source canvas, brushes/tools, PSD layer system, **the live-preview pipeline** |
| `paint-booth-4-pattern-renderer.js` | 8,026 | client-side swatch/thumbnail rendering + image caches |
| `paint-booth-5-api-render.js` | 5,566 | the canonical `buildServerZonesForRender` payload builder + full `/render` flow |
| `paint-booth-6-ui-boot.js` | 8,026 | boot wiring, the **separate decal Layer-Flow** system (`decalLayers`) |

All paths below are relative to the repo root `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum/`. Line numbers are from the state on 2026-06-29; `paint-booth-3-canvas.js` is also Codex's active file (per `OOM_FIX_PLAN.md`), so its line numbers drift — grep the function name to relocate.

---

### 1. The Zone model

`zones` is a single global array declared at `paint-booth-2-state-zones.js:200` (`let zones = []`), with `selectedZoneIndex` (:201) and `placementLayer` (:203, `'none'|'pattern'|'second_base'|'third_base'` — which layer a map-drag repositions). A zone is a plain JS object; there is no class. Every zone carries an `id` (`_newZoneId()` → `zone_<uuid>`, :362) which is load-bearing for undo (see §6).

Key per-zone fields (the renderer/payload reads these in `getZoneConfigHash` at canvas:7925 and `buildServerZonesForRender` at api-render:2689):

- **Identity / scope**: `id`, `name`, `muted` (disabled — skipped from render), `hardEdge` (defaults ON: `renderZones` forces `hardEdge=true` when undefined, state-zones:1065).
- **Color selection (which pixels)** — three independent mechanisms:
  - `color` / `colors[]` / `colorMode` (`'multi'`) / `pickerColor` / `pickerTolerance` — **color match**: pixels near these RGBs in the source paint belong to the zone. `color:'everything'` is the sentinel for a whole-car/template zone that covers all pixels (the "car template").
  - `regionMask` (Uint8Array, canvas-res, 1=belongs) — **positional mask** painted by the spatial brush (numbers/sponsors/artwork where colors overlap body paint). Large; gets *dedicated* brush undo (`undoStack`), and is intentionally **excluded** from zone-config undo snapshots.
  - `spatialMask` (Uint8Array, up to 2048²≈4MB) + `patternStrengthMap` (`{width,height,data:Uint8Array}`) — authored masks that **must** survive zone undo/redo, so they ARE deep-cloned into every snapshot (the OOM root cause, §6).
- **Material**: `base` (procedural base id) OR `finish` (monolithic finish id), `pattern` (+ `patternStack[]` of `{id,opacity,scale,rotation}`), `intensity`, `patternIntensity`, `scale`/`rotation`, `baseScale`/`baseRotation`/`baseStrength`/`baseSpecStrength`/`baseOffsetX/Y`/`baseFlipH/V`.
- **Base color system**: `baseColorMode` (`'source'|'solid'|'gradient'|'special'`), `baseColor`, `baseColorSource`, `baseColorStrength`, `gradientStops[]`/`gradientDirection`, `baseHueOffset`/`baseSaturationAdjust`/`baseBrightnessAdjust`.
- **Base overlay layers 2–5**: prefixed `secondBase…`, `thirdBase…`, `fourthBase…`, `fifthBase…` — each a full sub-material (`<prefix>Base`, `<prefix>Strength`, `<prefix>SpecStrength`, `<prefix>BlendMode`, `<prefix>Pattern`, `<prefix>HueShift/Saturation/Brightness`, etc.) gated by `<prefix>Enabled !== false` (default undefined = enabled).
- **Spec**: `specPatternStack[]`, `overlaySpecPatternStack[]`, `third/fourth/fifthOverlaySpecPatternStack[]`, `specShiftR/G/B`, `baseSpecBlendMode`, `zoneSpecMapPath`/`zoneSpecMapStrength`, `specScale`/`specRotation`.
- **`sourceLayer`** (RESTRICT-TO-LAYER): a PSD-layer id (see §2/§3). When set, the zone only paints where that layer visibly contributes.

`renderZones()` (state-zones:1059) is the master repaint of the LEFT zone list + Source canvas: it sanitizes zones, auto-saves, rebuilds the `#zoneList` HTML, and is the function every slider/toggle must call so the Source composite isn't left stale.

---

### 2. PSD Layers (`_psdLayers`)

Declared at `paint-booth-3-canvas.js:17159`: `var _psdLayers = []` of objects `{id, name, path, visible, opacity, img, bbox, groupName, blendMode, locked}`; gated by `_psdLayersLoaded` (:17160) and `_selectedLayerId` (:17161). `clearPSDDocumentState()` (:17162) resets all of it and nulls every `zone.sourceLayer` when the flat paint source changes.

- **`recompositeFromLayers()`** (canvas:17833): redraws `#paintCanvas` bottom-to-top from `_psdLayers`, honoring `visible`, `opacity/255`, `blendMode`, `bbox` offset, and `renderLayerEffects(ctx,layer,'before'|'after')` (drop-shadow/glow before, stroke/overlay/bevel after). It then refreshes the global `paintImageData` so eyedropper/wand see the new composite, and calls `invalidateLayerVisibleContributionCache()`. Uses `willReadFrequently:true` to avoid GPU readback on every layer tweak.
- **`buildLivePaintCompositeCanvas()`** (canvas:8227): builds the composite sent to the server for preview. If a layer is the active edit target it draws `_activeLayerCanvas` instead of `layer.img` (so in-progress brush strokes appear).
- Layers are **auto-created** in several places, not just from a PSD import: e.g. text layers (`_psdLayers.push(newLayer)` at canvas:14342 with `groupName:'Text'`, `id:'psd_text_...'`), and the **Smart Separate** flow. When a flat TGA is loaded (no PSD tree), `renderLayerPanel()` (canvas:17902) hosts `window.SmartSep.renderInto(container)` (:17914) — the numbers/sponsors/paint auto-separation tools — directly in the Layers column instead of a dead message. (I verified the SmartSep hook and text-layer auto-build; the full auto-separation→layers pipeline lives in the `SmartSep` module / `/api/auto-layers`, outside these four files — treat the exact builder as un-verified here.)

**RESTRICT-TO-LAYER** (`zone.sourceLayer`): set via a `<select>` in the zone-detail panel (state-zones:1576-1582, options built from `_psdLayers`; `setZoneSourceLayer` writes `zones[index].sourceLayer` at :4814). `zoneHasMissingSourceLayer(zone)` (:16477) flags a dangling reference. When the payload is built, the restriction becomes a `source_layer_mask`:

- **`getLayerVisibleContributionMask(srcLayer,w,h)`** (canvas:17603) is **alpha-based** (a deliberate bug fix, documented in-code at :17609-17620): the old impl diffed composite-with vs composite-without the layer, which returned 0 (and wrongly excluded pixels) whenever the layer's color matched lower layers. The correct rule: a pixel is "contributed by this layer" if (1) the layer's own alpha there is `> 8`, AND (2) no HIGHER source-over/normal layer fully covers it (`aboveA < 250`). Exotic blend modes above are skipped so multiply/overlay layers don't hide it. Result is a `Uint8Array(w*h)` of 0/255.
- Cached in `_layerVisibleContributionCache` (Map, canvas:17595) keyed `${_layerCompositeRevision}:${id}:${w}x${h}`; `invalidateLayerVisibleContributionCache()` (:17598) bumps `_layerCompositeRevision` so the key changes (cheap invalidation). OOM-bounded: evict oldest when `size > 24` (:17670).
- The mask is RLE-encoded (`encodeRegionMaskRLE`) into `zoneObj.source_layer_mask`, plus the layer's own unblended pixels go to `source_layer_rgb_png` (api-render:2806-2827) for Photoshop-correct color matching. A **missing** source layer emits an all-zero mask (paints nothing) plus a throttled warn toast (api-render:2780-2805) — fail-safe, never broadens the restriction.

---

### 3. The decal Layer-Flow system (separate from zones AND PSD layers)

`decalLayers` is a **third, distinct** stack declared at `paint-booth-6-ui-boot.js:118` (`let decalLayers = []` of `{name,img,x,y,scale,rotation,opacity,visible,flipH,flipV,...}`). This is the sponsors/numbers/decals/text overlay system (module `paint-booth-layer-flow.js`, "LAYER FLOW MODULE v3", alpha-based hit-testing `findTopmostLayerAt` uses `alpha > 16`). **The owner's mental model** (from `spb-zone-ux-and-selfimprove-2026.md`): zones = paint regions; car template = a zone with `color:'everything'`; **decals/sponsors/numbers/text = this Layer-Flow system, NOT zones** — which is why a bulk "shokk all zones" op must never touch them. Decals are migrated into `_psdLayers` for compositing, so the live PSD canvas already includes them.

When previewing, decals contribute two extra payload fields (canvas:8702-8724): `paint_image_base64` (the composited decal paint via `compositeDecalsForRender()`) and **`decal_mask_base64`** (the decal alpha mask via `compositeDecalMaskForRender()`, so the engine knows WHERE decals are and can apply per-decal `specFinish`). In the full-render path the same mask flows through `extras.decal_mask_base64` (api-render:1674, 3180), with a `window.SmartSep.renderPayload()` fallback (api-render:1679).

---

### 4. The Live Preview pipeline

Entry point **`triggerPreviewRender()`** (canvas:8110) — called from dozens of slider `oninput`/toggle handlers. Flow:

1. **Dedup**: computes `getZoneConfigHash()` (canvas:7925) — a hash of *every* render-relevant zone field across all valid zones (a field missing from this hash = a silent "preview didn't update" bug; e.g. `baseSpecBlendMode` and the spec sliders were explicitly added, :7960-7966). If `hash === lastPreviewZoneHash`, return (nothing changed). Empty hash → clears both preview panes.
2. **Boot guard**: if a PSD import is still rasterizing (`window._spbPsdImportInFlight && !_psdLayersLoaded`) it returns; the rasterize-complete path re-triggers once layers are in (fixes the "garbled-on-restart, only fixes after clicking Source" bug, :8140-8154).
3. **3-stage progressive debounce** (:8186-8224), all timers cleared on a new trigger:
   - **Stage 1** — 300 ms debounce → `doPreviewRender(hash, 0.25)` (512², ultra-fast).
   - **Stage 2** — 1 s idle → re-render at **0.5** (1024²) if hash unchanged; retries up to 5× while a render is in flight.
   - **Stage 3** — 3 s idle → up to `LIVE_PREVIEW_MAX_SCALE = 0.5` (1024², :8100). **Live preview is hard-capped at 0.5**; full 1.0/2048² is reserved for the explicit Render button.

**`doPreviewRender(zoneHash, previewScale, options)`** (canvas:8320):
- Aborts any in-flight request (`previewAbortController`), bumps `previewVersion` to discard stale responses, shows the spinner, and arms a watchdog (`PREVIEW_REQUEST_TIMEOUT_MS`) that aborts + schedules recovery (`_schedulePreviewRecovery`, exponential-ish backoff, max `PREVIEW_MAX_AUTO_RETRIES`).
- Builds `serverZones` via the shared `window.buildServerZonesForRender(zones)` (api-render:2689) — same builder as the full render, so preview paint matches final paint — with an inline fallback builder if that global is missing (:8363-8617).
- Assembles `body = { paint_file, zones, seed:51, preview_scale:_pScale }` (:8621), plus **incremental hints**: `body.changed_zone = selectedZoneIndex` and `body.zone_hashes[]` (per-zone JSON hashes, :8634-8688) so the server can serve unchanged zones from `build_multi_zone`'s zone-level cache.
- Attaches `import_spec_map`, decal `paint_image_base64`/`decal_mask_base64`/`decal_spec_finishes`, and — critically — when PSD layers exist OR the path has no real on-disk `.tga`, it sends the **live composite canvas as base64** (`_attachLivePaintCanvasToPreviewBody`, :8265; final fallback :8752) so layer edits actually show and the server never 404s "Paint file not found".
- `POST {baseUrl}/preview-render` (:8771) with an `AbortSignal.any([controller, timeout])`. 429 = busy → silent retry; `!data.success` → error; on success updates `#livePreviewImg` (paint) + `#livePreviewSpecImg` (spec) simultaneously, revokes old `data:` URLs for GC, and recomputes the material-map overlay + spec channel dock. Server-side this lands in `build_multi_zone(paint_file, output_dir, zones, …, preview_mode, decal_mask_base64, …)` (`shokker_engine_v2.py:16968`).

Preview liveness fixes baked into this path: `window.spbKickLivePreview()` (:8105) clears `lastPreviewZoneHash` so the offline→online transition force-re-renders (the 2026-06-12 preview-deadlock fix).

---

### 5. The full-render path

`doRender()` (api-render:3061) is the explicit Render button: `buildServerZonesForRender(zones)` (:3114) → `POST /render` (:1713) at full 2048², then polls `/api/render-status` (:3287). The canonical builder applies overlays via **`_applyExtraBaseOverlay(zoneObj, z, prefix, key)`** (api-render:247), called for all four overlay tiers by `_applyAllExtraBaseOverlays` (:320). That helper hard-gates `if (z[prefix+'Enabled'] === false) return;` (:250) and `if (!(baseId||colorSrc) || strength<=0) return;` (:258) — so a disabled or zero-strength overlay emits nothing. This is the same code path preview and render share, which is why per-layer overlay ON/OFF was "backend-ready, UI-only" (`spb-overlay-hsb-and-cache-tokens.md` #3).

---

### 6. Undo systems (FOUR stacks) and the OOM fix

There are four independent undo stacks, plus a coalescer:

| Stack | Decl | Cap | Snapshots |
|---|---|---|---|
| `zoneUndoStack` / `zoneRedoStack` | state-zones:356 | `MAX_ZONE_UNDO = 15` (:358) | **ALL zones** deep-cloned (incl. `spatialMask`+`patternStrengthMap`) |
| `undoStack` / `redoStack` (draw/region masks) | state-zones:351 | `MAX_UNDO = 30` | `{zoneIndex, prevMask}` |
| `_pixelUndoStack` | canvas | `_PIXEL_UNDO_MAX = 6` (:5354) | full 2048² canvas ImageData (~16MB each) |
| `_layerUndoStack` | canvas:20154 | `_LAYER_UNDO_MAX = 5` (:20156) | per-layer canvas snapshots |

**`pushZoneUndo(label, isDrag)`** (state-zones:505): on EVERY zone property change (dozens of callers) it `zones.map(z => _cloneZoneState(z, {includeRegionMask:false, includeSpatialMask:true, includePatternStrengthMap:true}))` (:517-527). `_cloneZoneState` (:395) does a `JSON.parse(JSON.stringify(...))` of scalars + typed-array clones of the masks. RegionMask is excluded (it has its own `undoStack`); spatialMask + strengthMap are INCLUDED because they're authored state. `isDrag` coalesces rapid drags via a 500ms timer; `pushZoneUndoCoalesced(label, windowMs)` (:17045) is the time-windowed variant.

Undo/redo (`undoZoneChange` :554, `redoZoneChange` :590, `jumpToUndoState` :625) restore by **zone `id`, not positional index** (BUG #62, :570-581): they rebuild a `masksById` Map before swapping `zones`, so adding/deleting/reordering zones between snapshots can't corrupt masks. `pushZoneUndo` also invalidates ALL redo stacks via `window._clearAllRedos()` (BUG #75, :515) so a stale Ctrl+Y can't fire.

**The OOM root cause** (`OOM_FIX_PLAN.md`, fixed 2026-06-28, Tier 1): `spatialMask` (~4MB) × N zones × 50-deep `zoneUndoStack` = multiple GB → Electron renderer (Chromium ~2-4GB heap) OOMs cumulatively over a session (not on launch). Tier-1 fix (all tagged `2026-06-28 OOM fix`, token `spb-oom-fix-20260628`):
- `MAX_ZONE_UNDO 50→15` (the dominant consumer, ~70% cut).
- `_PIXEL_UNDO_MAX 10→6`; `_LAYER_UNDO_MAX 8→5`.
- Cache eviction added (previously unbounded): `_layerVisibleContributionCache` evict `>24` (canvas:17670); `_imagePatternCache` evict `>80` (pattern-renderer:57-60); `_previewCache` evict `>400` (pattern-renderer:8009) and `>200` (api-render:1218-1221, a *separate* object in that file's scope).
- **Tier-2 (not yet done)**: RLE-compress spatialMask/strengthMap in `pushZoneUndo` (near-binary → 10-50× smaller) to restore 50-deep undo at a fraction of the memory. No Python touched, so the pytest gate battery is unaffected. To reach users it needs a version bump + `deploy_r2.py`.

---

### 7. The Zone popout / zone-detail panel

`renderZoneDetail(index)` (state-zones:1481) builds the floating editor `#zoneEditorFloat` (or fallback `#zoneDetailPanel`), injecting `panel.innerHTML = html`. Sections are `.section-collapsible` with ids `section{Color,Base,Pattern,Overlays,SpecPatterns,SpecPreview,ZoneSpecSource}` + index. **On-demand population** (`spb-zone-popout-on-demand.md`): the panel shows Base first and only populates Spec Overlay / Patterns / Base Overlays 2-5 **after a base/finish is assigned** — empty-below-Base with no base is *normal, not broken* (this caused a false 4-alarm once; verify a base is assigned before diagnosing).

**Classic/Tabbed layout toggle** (opt-in, default Classic, zero-regression): a pure post-render layer `_spbApplyZoneLayout(panel,index)` tags each section into a tab via `SPB_ZONE_TABS` (color/base/pattern/overlay/spec) and shows one at a time with `.spb-tab-shown`; toggle is `#zonePanelLayoutSelect` in Settings▸Options (`getZonePanelLayout`/`setZonePanelLayout`). The base/pattern dropdown is `.swatch-trigger` → `openSwatchPicker()` (state-zones:6022) → the big searchable grouped `#swatchPopup` picker (`filterSwatchPopup`, vibe chips, `_SPB_SEARCH_SYNONYMS` query expansion).

Two recurring panel bugs (both fixed) are worth knowing because they recur:
- **Short popout sliders** (`spb-popout-slider-length-fix.md`): Strength/Fine-Tuning range rows rendered ~90px vs ~200px for HSB. Root cause was **layout budget**, not a broken cascade — the 6-col grid's fixed overhead (labels/buttons/value/gaps/padding) ate ~250px of a ~340px row so `1fr` resolved to ~90px. Fix: give the range rows the same flex recipe as `.hsb-controls` (appended to the end of `css/ui-modernization-20260509.css`, token `spb-popout-slider-20260609`). Don't re-fix this with more grid rules.
- **View-jump on hover** (`spb-view-jump-hover-lock.md`): the Source/Preview panes jump vertically on mouse hover (no click) in eyedropper/layer-pick modes. Chain: `canvas.onmousemove` layer-hover-preview → `renderContextActionBar()` reflow → ResizeObserver on `#canvasViewport` → `_sizePreviewSquares()` (~canvas:7235) → `canvasZoom('fit')` → `applyZoom()` marginTop re-center. Fixed in `_sizePreviewSquares` with a width-changed guard + `_NON_FIT_HOVER_MODES` whitelist. **The guard is a MODE WHITELIST** — a NEW pick/hover mode not in that list reintroduces the jump; harden the trigger if it recurs.

---

### 8. Swatch / thumbnail caching and overlay-HSB / cache-token traps

- **Overlay HSB sliders MUST call `renderZones()` in their `oninput`** (state-zones), exactly like base HSB sliders — a prior session removed it (thinking it caused drag jank), leaving the Source composite stale so sliders "did nothing." Contract locked by `tests/test_layer_system.py::test_overlay_hsb_range_sliders_redraw_source_and_live_preview` (asserts BOTH `renderZones();` and `triggerPreviewRender();`). Don't remove it again.
- **Thumbnail cache chain** (`spb-thumbnail-cache-chain.md`): the picker is supposed to load swatches once and keep them. Four stacked busters were fixed: (1) Electron boot `clearCache()` removed; (2) the grid tint-key mismatch — callers now pass `getSwatchUrl(finishId, colorHex || fallbackColor)` with lowercase-6-hex normalization so the grid key byte-matches the warm-baked file; (3) `Date.now()` busters replaced with `_SHOKKER_SWATCH_V`; (4) swatch `_cache_headers` 24h→1yr immutable (fingerprint-keyed URLs). **Trap**: the live `getSwatchUrl`/`renderSwatchSquare`/lazy-loader implementations are the **inline copies in `paint-booth-2-state-zones.js`** — the `js/zones/swatch-popup-*-controls.js` modules are DEAD CODE (register `{install}` that nothing calls). Edit the inline copies.
- **Stale pre-bakes ≠ cache bug**: the picker grid requests `/api/swatch/<type>/<id>?mode=split&prefer=live`, which serves the static snapshot `thumbnails/picker_split/<type>/<id>.png` first. After ANY finish/category rebuild you must run `python rebuild_picker_swatches.py --force` (NOT `rebuild_thumbnails.py`, which only writes `thumbnails/base/`) then Fresh Start, or the picker shows month-old swatches even though the registry is correct.
- **Cache tokens for JS**: server_v5 serves HTML/JS/CSS `no-store/no-cache` (~line 395) and the boot `clearCache()` was removed, so a normal reload picks up JS edits. The historical ritual of bumping the `?v=` token on `<script src=…?v=>` in `paint-booth-v2.html` persists (and `OOM_FIX_PLAN.md`/release docs still call for it), but for JS it is effectively a no-op — the truly cached, fingerprinted assets are the swatch PNGs. Note `paint-booth-2-state-zones.js?v=spb-zone-boot-bridge-3-20260522` is **PINNED** by `scripts/spb_guard_zone_extracted_boot_contract.js` — never bump that one.

---

### Verification notes
Verified directly in code: the zone fields (`getZoneConfigHash`/`buildServerZonesForRender`), `pushZoneUndo`+`_cloneZoneState`, all four undo caps, the 3-stage debounce constants (300ms/1s/3s, 0.25/0.5/0.5, `LIVE_PREVIEW_MAX_SCALE=0.5`), `/preview-render` + `/render` payload assembly, `decal_mask_base64`, `source_layer_mask`, the alpha-based `getLayerVisibleContributionMask`, `recompositeFromLayers`, `_applyExtraBaseOverlay` enable-gating, `build_multi_zone`'s signature (`shokker_engine_v2.py:16968`), and every OOM-fix line in `OOM_FIX_PLAN.md`. **Not fully verified**: the exact flat-TGA→`_psdLayers` "virtual/auto-built layers" builder (the `SmartSep`/`/api/auto-layers` pipeline lives outside the four cited files — I confirmed the hook at canvas:17914 and the text-layer auto-build at canvas:14342 but not the auto-separation internals). Line numbers in `paint-booth-3-canvas.js` drift because Codex actively edits it — grep the function name to relocate.

---

<a id="big-bugs-chased-and-fixed"></a>

## Big Bugs Chased & Fixed (war stories)

Institutional memory of the hardest problems SPB has hit. Each: **SYMPTOM → ROOT CAUSE → FIX → guarded now.** Grouped by subsystem. File:line refs were verified against the current tree where noted; engine line numbers drift upward as files grow, so trust the **function names** over the exact line. A recurring meta-lesson runs through almost all of these: *a leaf-function fix is not proof — verify end-to-end (`build_multi_zone` / real export / real app), clear the caches, and remember SPB is a 2-copy tree.*

---

### A. The render engine — the "tiling the whole car" saga (the #1 recurring war)

This is THE bug the owner has hit 5+ times ("a bitch to fix," "STILL FUCKING TILING THE WHOLE CAR"). Multiple distinct root causes wearing the same symptom. Source: `spb-base-scale-whole-canvas-tiling.md`, `spb-pattern-scale-tiles-whole-car.md`.

**A1. Base scale < 1 renders mini-cars (decals + number "55" + logos in a 2×2 grid).**
- SYMPTOM: dropping the **Base Scale slider** (`base-material-controls.js:123`) below 1.0 tiled shrunken copies of the *entire composited canvas* instead of just the base material. Doctrine: "anything scaled down tiles ONLY what's scaled down, NOT the whole canvas." (Linear **SPB-41** family.)
- ROOT CAUSE: `engine/compose.py` `_apply_base_placement_to_paint` (verified at **compose.py:1183**) transformed the FULL `paint` buffer — which already held the composited decals — via `_transform_base_color_source` (**compose.py:1114**) → `_tile_fractional` per RGB channel. So it tiled the whole composite. `base_scale` is a DISTINCT field from the pattern-size slider (`z.scale`/server `scale`, which only tiles `pv` and is fine); base_scale lives at `paint-booth-5-api-render.js:508`.
- FIX (2026-06-02, "source-safe delta"): when `background_paint` is provided (call sites pass `_paint_before_base_placement`, captured pre-material), tile/scale/rotate ONLY the base-MATERIAL delta `rgb − background_rgb` (≈0 over decals → decals NOT replicated), then `out = where(mask, clip(bg + transformed_delta), bg)`. Added `clip01=False` to `_transform_base_color_source` so the signed delta survives. scale==1.0 still early-returns byte-identical. *"Tile the FIELD, not the CANVAS."*
- GUARDED: `tests/regression_base_scale_no_whole_canvas_tile_test.py` — now **8/8** (decal-not-replicated, quadrants-not-identical, base-material-STILL-tiles, scale==1 no-op, no-background no-op, real-composite integration via `engine.preview_render`, plus the two 2026-06-26 holes below). Run vs both engine copies.

**A2. Why it kept coming back (the structural lesson).** Three reasons it recurred: (1) **family-scoped fixes** — earlier cures (SPB-31 gradient, SPB-36 monolithic) seeded the source-safe path only for their finish family; the default material path never got it. (2) **pattern-rebuild churn** hardcoded `scale=1.0` in rebuilt paint_fns. (3) **2-copy + uncommitted working-tree drift** — the live server runs the working tree; a fix in one copy silently reverts in the copy the server loads. The permanent answer is *structural* (always tile a source-safe delta), the regression guard, sync-all-copies-and-commit.

**A3. The recurrences, by render path (each a genuinely different code path):**
- **PATH 2, monolithic primary base (2026-06-17):** assigning a FRACTURED finish to a color selection + Base Scale 0.5 gave mini-CARS. Instrumentation proved it was *intent*, not a leak: scale<1 was correctly shrink-repeating, but repeating the *zone-masked (car-shaped) render*. FIX in `shokker_engine_v2.py build_multi_zone`: re-render the finish ONCE with a ones mask + native placement over a clean decal-free seed (`_monolithic_transform_seed_paint`) = a PURE full-canvas pattern, tile THAT down, confine to `zone_mask`. **CRITICAL ORDERING:** the finer pass MUST run immediately after the raw render, BEFORE HSB/override/overlays — the first attempt ran it after, so re-rendering discarded the HSB edits ("it scales but reverts to the original color"). Guard: `test_hsb_holds_on_scale.py` (HSB drift 0.0156 = held).
- **PATH 1, regular base (2026-06-23):** **Silver Sequin** (`sequin_silver`, a real BASE) tiled the silhouette. PATH 1 delegates to `compose_finish`→`compose.py`, whose placement tiled the zone-confined (car-body-shaped) delta. FIX (both `compose_paint_mod` + `compose_paint_mod_stacked`): render the base over a clean flat zone-mean seed, tile that finer, confine to the zone.
- **2026-06-26, the last two holes (suite went 7/8 → 8/8):** **HOLE A** — `base_color_source` = a migrated-to-BASE finish (every PRISM FORGE `pf_*`, MONEY SHOKK `cs_*` live in `BASE_REGISTRY` not `MONOLITHIC_REGISTRY`) hit a reverse-fallback in `_apply_base_color_override` that rendered with the zone silhouette + left `_src_needs_placement=True`. **HOLE B** — a PASS-THROUGH base (gloss/clear, `paint_fn IS paint_none`) skipped the `_op<0.045` deactivation check (it lives inside `if base_paint_fn is not paint_none:`), so `_finer_base_active` stayed True and tiled the real composite. This was ALSO the "restart → numbers/sponsors scrambled" report. FIX: add `and base_paint_fn is not paint_none` to `_finer_base_active` in both functions; hardened with an **opacity gate** (gloss/matte `_op`≈0.0 = pass-through, sequin/metallic `_op`≈0.22-0.28 = opaque).

**A4. Procedural PATTERN scale-down tiled the whole car (DISTINCT path).** SYMPTOM (2026-06-10): scaling a *procedural* tex_fn pattern to 0.35 replicated the TRES COMAS logo 3×; image patterns were fine. ROOT: the scale<1 branches in `compose.py` (`compose_paint_mod`, `_get_pattern_mask`, `compose_finish`) — a mid-session "regenerate at 4096² + resize" approach removed the tiling but cost **23.8–36s** (violates the ≤3s render doctrine). FIX: scale<1 = generate the PURE pattern ONCE at output res (`tex_fn(shape, np.ones(shape), seed)` — ones mask, no zone contamination), then `_tile_fractional(pv, 1/scale)`. Result: 0.35 render = **7.77s vs 7.56s at 1.0**. *Tile the fresh pure-pattern array; never regenerate at a huge virtual canvas.*

**A5. THE VERIFICATION TRAP that makes every tiling fix "look unfixed."** `build_multi_zone._zone_cache` (verified live: a blake2b-keyed 24-entry LRU, `shokker_engine_v2.py:17105` init, store ~17887, evict-over-24 ~17903) returns `CACHE HIT (skipped re-render)` for an identical zone payload. This made a BEFORE/AFTER look identical (AFTER reused the BEFORE image) AND is almost certainly why the owner saw "STILL tiles" after restart. **When verifying ANY engine fix: `build_multi_zone._zone_cache.clear()` (or vary the seed) AND bump JS `?v=` tokens.** `build_multi_zone` also writes `output/job_*/zones_payload.json` per render so any case is replayable (use the `spb-render-replay` skill).

> **Still open (flagged, supervised):** `test_preview_render_real_composite_no_whole_car_tile` (gloss + base_scale 0.5 + snake_skin) was seen leaking an off-quadrant marker even with gloss confirmed a no-op in base placement — isolated to a SEPARATE composite-tiling path, likely pre-existing. The owner's actual reported bugs (opaque sequin, PRISM FORGE) are fixed + verified.

---

### B. Authored spec — the SHOKK DROP "render my exact channels" saga (3 stacked layers)

A guest/dev uploads their own R/G/B spec plates (Metallic/Roughness/Clearcoat) via SHOKK DROP "Paint + spec maps (exact)". They must render **verbatim, pixel-for-pixel** to the iRacing `car_spec` export. Took three rounds because each fix exposed the next layer. Sources: `spb-shokkdrop-authored-spec-fix.md`, `spb-authored-base-spec-strength.md`, `spb-authored-spec-triple-block.md`, `spb-spec-channel-view-grayscale.md`.

**B1. Layer 1 — uploaded channels ignored, procedural red/green noise shown.** ROOT: `engine/paint_v2/user_imports.py` `_make_spec_fn` (verified **user_imports.py:286**) had no case for `spec_mode=="authored_set"`; it fell through to `_spec_from_combined`, which unconditionally runs the Viva-Mexico spec polish (`_pre_adjust_viva_mexico_spec`/`_post`) that re-tunes all 3 channels against the *paint* → obliterates the authored black-R/gray-G. (The upload/ingest pipeline — `shokk-drop.html`, `user_import_routes.py`, `user_imports_ingest.py resolve_authored_spec`/`combine_channel_specs` — is 100% correct; do NOT touch it. Ground truth: `%APPDATA%\ShokkerPaintBooth\user_imports\ui_bjeans1_spec.png` measured R≈0.4 / G=136 / B=0.) FIX: route `authored_set` (and `dna_plate`) to `_spec_from_dna_plate` (loads `{id}_spec.png` verbatim, SKIPS Viva pre/post). Empirically proven: old path R=69.5 (the red noise) → new path R=0.1, G=136, B=0.

**B2. Layer 2 — verbatim as a FINISH (G=136) but BOOSTED as a zone BASE (G=237).** Ground truth: `car_spec_23371.tga` (base usage) G=237; `SPB_COMBINED1.tga` (finish usage) G=136. ROOT: a user-import monolithic used as a primary base routes to the monolithic render path, which computed `_sm_effective = sm * base_spec_strength` and called `spec_fn(...,_sm_effective)` where `_spec_from_dna_plate` does `G = G_authored * sm`. So `136 × 2.0 = 237`. **The v1/v2 fixes silently FAILED** because (a) the `[Monolithic Contract]` wrapper `_spb_wrap_monolithic_spec_contract` STRIPS custom `spec_fn` attributes → a `__spec_mode__` tag never survived, and (b) `sm` arriving at the mono path was ALREADY 2.0 (the slider was applied upstream), so even `_sm_effective = sm` doubled it. FINAL FIX (verified in `shokker_engine_v2.py`): build a wrapper-proof id-set `_AUTHORED_SPEC_IDS` exposed as `user_imports.is_authored_spec(fid)` (**user_imports.py:384**); the mono path does `_mono_is_authored = is_authored_spec(finish_name)` (~18431) → `_sm_effective = 1.0 if _mono_is_authored else (sm * _mono_spec_strength)` (verified **shokker_engine_v2.py:18440**, a HARD 1.0, not `sm`) + skip the post-pass `_apply_base_spec_strength_to_zone_spec`.

**B3. Layer 3 — "we fixed it but it's STILL off" = THREE duplicate render blocks.** ROOT: `shokker_engine_v2.py` has **three near-identical monolithic render blocks** (preview / car-render / garage-world). The verbatim fix was applied to only the first; guests on the other two still saw the boost. FIX: all three now compute `_mono_is_authored` and gate `_sm_effective` + the post-pass identically.

**B4. The display half — "G ROUGH channel still looks bright green."** Two separate causes, neither "just a tint." (1) `renderSpecChannelDock()` in `paint-booth-2-state-zones.js` multiplied each channel by `SPEC_DOCK_TINTS` = `{r:[1,0.3,0.3]...}` (washed). A pure-grayscale interim ALARMED the owner pre-Alpha ("ALL gray = broken"). FINAL per owner mandate ("match Photoshop. Period."): `SPEC_DOCK_TINTS = {r:[1,0,0], g:[0,1,0], b:[0,0,1]}` = Photoshop "Show Channels in Color." (2) The 237 the owner kept seeing was a **STALE render**, not a live boost — a soft reload (Ctrl+R) reloads JS but NOT the Python engine module, so the live preview kept showing the pre-fix spec.

> **REUSABLE (this whole saga):** verbatim/authored assets must bypass ALL strength sliders end-to-end; any override must cover EVERY registry the asset lives in AND EVERY duplicate render block; **unit-testing the leaf spec_fn is NOT proof** — the bug lived in the wrapper + the upstream `sm`. Always render END-TO-END via `build_multi_zone` and measure the real `car_spec_<id>.tga`. SPB writes `car_spec_<id>.tga` and `PREVIEW_spec.png` from the SAME `combined_spec_u8` array — if they differ on disk it's two different renders (stale vs fresh), not a transform. Python engine fixes need a FULL app restart. Guard: `tests/test_regression_overlay_hsb.py`.

---

### C. Spec channels — the "this knob does nothing" family

**C1. Metallic clearcoat (CC) = 0 — patterns lost their whole color-shift dimension on metallic bases.** SYMPTOM (2026-06-03): diffraction/holographic/iridescent/heat_discoloration showed zero CC variation on `f_metallic` (dCC std 0.0), but fine on non-metallic `acid_etch` (dCC 15-87). ROOT (NOT the floor-clip the stale comment blamed — that fix was dead code): in `compose_finish`, bases whose `base_spec_fn` returns a 2-tuple (M,R) get `CC_arr = None`; `f_metallic`'s factory returns a 2-tuple, `acid_etch`'s returns a 3-tuple. Inside `_apply_spec_pattern_to_channels` the CC block is guarded by `CC_arr is not None`, so with None the entire CC branch (incl. the polarize/amplify fix) is skipped, then `final_CC = effective_base_CC` = flat scalar 16. FIX (surgical, only the None case): added `cc_fallback=None`; when a layer targets "C" but CC_arr is None, materialize `xp.full(..., effective_base_CC)` so the existing CC math runs. Result: heat_discoloration dCC 0.0→49.7, knurled 0.0→34.6. Residual (physics, not a bug): one-directional-glossy patterns (diffraction_grating) stay 0 on a base pinned at the gloss floor — fixing it would raise every metallic finish's baseline (a finish change, left alone).

**C2. Spec Blend dropdown was a literal no-op on monolithic bases.** SYMPTOM (2026-06-12): owner asked if the Zones→Bases Spec Blend (normal/multiply/screen/overlay…) did anything. Answer: on any monolithic-as-base it's a no-op; elsewhere near-useless. ROOT: engine reads `base_spec_blend_mode` only in compositing PATH 1 + two PATH 4 fallbacks; a monolithic-as-base is rerouted to the mono path which never reads it. Even on PATH 1 it fired only inside the pattern loop (no pattern = nothing blends), only on M and R — **CC was always plain additive**. And `_apply_spec_blend_mode` (compose.py) math was weak (global-max normalize kills authored amplitude; overlay≈hardlight≈identity; ΔCC=0.00 measured in every mode). FIX (SHIPPED, owner: "do them all"): replaced the Photoshop vocabulary with **6 physical cross-channel modes** built on ghost-shift physics — `ghost_carve`, `chrome_inlay`, `frost_etch`, `angle_flip`, `ember_gate`, `depth_press` — wired into BOTH render paths (incl. `overlay_pattern_on_spec`, all 10 call sites), made CC-aware, dropped global-max normalize. Added a PATTERN-LESS mode (owner: "should effect the ZONE as-is") driven by the zone's own structure, hooked right before the zone-cache store so it covers all paths incl. cache replay. GUARDED: `tests/test_regression_overlay_hsb.py` now 12 tests; legacy PS modes kept as aliases.

**C3. Rework finishes: audit swatch new, booth render OLD (no restart fixed it).** SYMPTOM (2026-06-10): the 74 colorshift-rework finishes (insects/anime/neon/chameleon/prizm, e.g. `butterfly_monarch`) showed the NEW look as a swatch but the OLD spec when assigned as a base. ROOT: they're registered in BOTH `MONOLITHIC_REGISTRY` AND `BASE_REGISTRY`; `_spb_apply_colorshift_rework_2026()` overrode only the monolithic. Assigned as a base → the **compositing** path pulls the stale `BASE_REGISTRY[id]` entry. FIX: the hook now also overrides the base entry — BASE `paint_fn` is identical (swap directly); BASE `base_spec_fn` returns a 3-tuple (M,R,Cc) while the monolithic returns packed HxWx4, so adapt `packed[:,:,0/1/2]`. DIAGNOSE BY: the `[compositing]` vs `[monolithic]` tag in the render log, and `/api/swatch/base/<id>` vs `/api/swatch/monolithic/<id>` returning different specs.

**C4. Overlay HSB sliders dead on monolithic-primary zones.** SYMPTOM (2026-06-12): hue/sat/brightness on the 2nd-base overlay did nothing — for the owner's FM/fusion daily drivers. ROOT: a zone whose PRIMARY base is a monolithic takes the mono-path "2nd base overlay" block, which built `paint_overlay` WITHOUT reading `second_base_hue_shift/saturation/brightness`. The compositing path applied them fine — and that's the only path the audit tested. FIX: apply `_apply_hsb_adjustments` to `paint_overlay` before the blend; extracted `_apply_mono_path_base_overlay(tier,...)` and looped all four tiers through it (per-tier seed offsets 0/1013/2026/3039). **AUDIT LESSON: the zone's PRIMARY base TYPE switches the entire render branch — test every overlay feature with BOTH a classic-base primary AND a monolithic primary.**

**C5. Mono 2nd-base "0.20 doesn't line up" = seed-phase, not scale.** SYMPTOM: right SIZE, wrong POSITION for a monolithic 2nd base (e.g. Crystal Lattice). ROOT (NOT tiling math — that's pixel-identical at equal scale+seed): the rebuilt-pattern wrapper derives a spatial grid ORIGIN ("phase") from the SEED (`_spb_rebuilt_pattern_value`: `phase=(family&1023)/1023`). The 2nd base's geometry seed is OFFSET from the primary (`seed + i*13 + abs(hash(second_base))%10000` for spec; `+7777` for color; compose.py `+999`), so same-size lattice, translated. PROVEN by monkeypatch: forcing the same seed → xcorr 1.0, overlay goes split-red/green → pure yellow. STATUS: **proposed, NOT auto-applied** (finishes change only on owner say-so). Long-term fix = carry a dedicated `pattern_offset/phase` from the primary so the geometry seed can stay decoupled.

**C6. Wild-spec channel decorrelation (passing the max|corr|<0.85 gate).** Not a bug per se but the hardest gate. The #1 correlation source is a band/zone STEP function shared by all 3 channels (R and Cc both ride "high on the verde side" → corr ~0.92). Different per-band scalars are NOT enough — give each channel a structurally different primary geometry (M=weave valleys, R=signed sheen rib, Cc=the seam/stitch corridor as its OWN sparse structure dropped R↔Cc 0.92→0.68), and anti-align ≥1 band. Probe per-PAIR (MR/MC/RC), not just the max. The clip<1% trap is usually micro-pins landing on an already-bright channel.

---

### D. Live preview & UI — the "it's just dead / it always reloads / it jumps"

**D1. Live preview goes dead; only clicking RENDER unsticks it.** SYMPTOM (2026-06-12): "changing the pattern doesn't work — it's just dead. Clicking RENDER (even grayed out) fixes it." ROOT CHAIN: after any engine-source change, the boot swatch warm (detached `rebuild_picker_swatches.py --warm-cache`) re-bakes every swatch whose renderer hash changed — an engine-wide edit ≈1700 swatches ≈18 min of CPU saturation. During the storm `/status` misses the **2s** `API_TIMEOUT_STATUS_MS` → `ShokkerAPI.online=false` → `doPreviewRender` hits `if (!ShokkerAPI.online) return;` and dies SILENTLY with nothing re-triggering it. RENDER works because `doRender` doesn't gate on the flag. THREE-LAYER FIX: (1) `API_TIMEOUT_STATUS_MS` 2000→8000 (busy ≠ offline); (2) reconnect revive — `checkStatus()` detects offline→online and calls `window.spbKickLivePreview()` (clears `lastPreviewZoneHash` + `triggerPreviewRender()`); the offline path now pokes `checkStatus()` instead of dying; (3) warm-storm governor — preview/render routes touch `_spb_user_active.heartbeat` (gitignored, root); the warm loop sleeps while the heartbeat is <20s old (cross-process via file mtime). RECURRENCE WATCH: any new background bake job must respect the heartbeat; any new "skip if offline" guard needs a revive path. (The famous "dead HSB sliders" turned out to be THIS bug wearing a different hat + the C4 mono-path gap — a full-chain audit proved the compositing HSB pipeline healthy at every link.)

**D2. Thumbnails "always lazy-load" — never cache.** SYMPTOM (2026-06-12): "load ONCE then stay forever... but every dropdown open is ALWAYS loading." ROOT = **FOUR stacked busters** (fixing any one alone never worked): (1) Electron boot `clearCache()` ("BUILD 23") wiped the HTTP cache every launch — REMOVED (HTML/JS/CSS are served no-store, swatch URLs carry the engine `?v=` fingerprint); (2) **tint-key mismatch** — grid callers pass `renderSwatchSquare(id, item.swatch, desc)` so `item.swatch` landed in `fallbackColor` while `getSwatchUrl` got `color=888888`, never hitting the warm-baked `item.swatch` keys — fixed with `getSwatchUrl(finishId, colorHex || fallbackColor)` + lowercase 6-hex normalization; (3) `Date.now()` busters in `openSwatchPreviewModal` → use `_SHOKKER_SWATCH_V`; (4) `_cache_headers` max-age 24h → 1-year immutable (`swatch_routes.py`). Also memoized `_picker_finish_renderer_hash` (2.12ms→0.006ms). **TRAP:** the `js/zones/swatch-popup-*.js` modules are DEAD CODE — the LIVE implementations are inline in `paint-booth-2-state-zones.js`; edit THOSE. **DISTINCT issue (2026-06-26):** "thumbnails not updating after a category rebuild" was NOT the serving chain — the pre-baked PNGs themselves were month-old. The picker serves `thumbnails/picker_split/<type>/<id>.png` (NOT `thumbnails/base/`). FIX = re-bake with `python rebuild_picker_swatches.py --force` then Fresh Start. `rebuild_thumbnails.py` is the WRONG tool (writes `thumbnails/base/` only).

**D3. Source/preview panes JUMP UP just from HOVERING (no click).** SYMPTOM: in unified split view, the square panes shift vertically from hovering in EYEDROPPER + Layer-toolbar mode. Took 3+ failed attempts (each guarded the wrong state). ROOT CHAIN (verified): `canvas.onmousemove` enters the Layer Element Hover Preview block → calls `renderContextActionBar()` which rewrites `#contextActionsBar.innerHTML` → a transient reflow nudges `#canvasViewport` height ≥2px → trips the ResizeObserver → `_sizePreviewSquares()` → the square size key changes → `setTimeout(()=>canvasZoom('fit'))` → `applyZoom()` rewrites `inner.style.marginTop` re-centering `#canvasInner` = the visible jump. Prior fixes guarded brush/free-transform state and `#hoverInfo`, but never the eyedropper/pick state. FIX (verified `paint-booth-3-canvas.js`): `_sizePreviewSquares` now captures row WIDTH each call (`_widthChanged = Math.abs(_prevFitW - cvW) >= 2`, **:7510**) and a `_NON_FIT_HOVER_MODES = ['eyedropper','wand','selectall','edge','lasso','selection-move','pick-item','layer-pick','zone-pick']` whitelist (**:7543**); logic: `if (_ftActive||_brushActive) return; if (_hoverPickActive && !_widthChanged) return;` then re-fit. A real re-fit reason changes WIDTH; a pure hover only churns HEIGHT. RECURRENCE WATCH: the guard is a **MODE WHITELIST** — a new pick/hover mode not in the list reintroduces the jump; the recurrence-proof fix targets the TRIGGER (stop the context-bar repaint tripping the RO). Needs a FULL restart to load (soft reload serves stale JS).

**D4. "Out of Memory" after a long session.** SYMPTOM (2026-06-28): the Electron renderer (Chromium ~2-4GB heap) OOMs cumulatively over a session; restart clears it. Not one action. ROOT (`OOM_FIX_PLAN.md`, confirmed in code): `pushZoneUndo()` (verified **paint-booth-2-state-zones.js:505**) runs on EVERY zone property change and snapshots ALL zones with `includeSpatialMask:true` + `includePatternStrengthMap:true` (each up to a 2048² Uint8Array ~4MB) × N zones × `MAX_ZONE_UNDO` (was 50) = multiple GB. Compounded by three caches with no eviction (`_previewCache`, `_imagePatternCache`, `_layerVisibleContributionCache`) + pixel/layer undo stacks. FIX (TIER 1, shipped 2026-06-28, verified): `MAX_ZONE_UNDO` 50→15 (**:358**), `_PIXEL_UNDO_MAX` 10→6 (**canvas:5354**), `_LAYER_UNDO_MAX` 8→5 (**canvas:20156**), + LRU eviction caps on the three caches (`_layerVisibleContributionCache`>24, `_imagePatternCache`>80, `_previewCache`>400/>200). Tokens bumped to `spb-oom-fix-20260628`, synced root↔electron (cmp identical), no Python touched. TIER 2 (not yet done): RLE-compress the spatial mask + strength map in `pushZoneUndo` to keep 50-deep undo at a fraction of the memory. CAVEAT to confirm with the user: does it OOM on launch (→ different cause, boot swatch baking / DNA picker) or after working a while (→ this is it). **Coordination note:** `paint-booth-3-canvas.js` is also Codex's active file — the 3 OOM edits are on stable lines tagged "2026-06-28 OOM fix" to survive Codex's next save.

---

### E. Desktop app — license & installer (only break in the packaged/real-network world)

**E1. License dialog stuck FOREVER on "Verifying…".** SYMPTOM (2026-06-07, Alpha VM): a valid key, dialog hangs indefinitely on a network that can't reach payhip.com (sandbox, captive wifi, blackholed DNS). ROOT (`electron-app/main.js`): `requestPayhipViaHttps` (verified **main.js:496**) guarded its timeout ONLY with `req.setTimeout(LICENSE_REQUEST_TIMEOUT_MS,…)` — a SOCKET-idle timer that only arms AFTER a socket connects. If **DNS or TCP-connect hangs**, no socket exists, the timer never fires, the Promise never resolves → the whole chain hangs → the offline-activation fallback is never reached. FIX (verified): a HARD wall-clock `guard=setTimeout(..., LICENSE_REQUEST_TIMEOUT_MS+500)` (**:517**) that destroys the req and resolves regardless of socket state, with a `settled` flag so all outcomes route through one `finish`; plus `verifyWithPayhip` (**:588**) wraps `Promise.race` against a ~22s `overallGuard` (**:609**) resolving `{valid:false, networkError:true}` so the offline-activation branch engages. Tag `license-verify-hang-fix 2026-06-07`. The BACKEND was fine (a 40-line host probe returned HTTP 200, valid:true in 356ms). REUSABLE diagnostic: test the activation backend independent of the GUI; call only `/verify` (not `/usage`, which burns a usage increment); delete the probe before building (it would bundle into app.asar). A green sandbox weather widget ≠ full outbound HTTPS.

**E2. Buyers can't upgrade — "V6 is running," hung 7z, redownload loop.** SYMPTOM (2026-06-07): installer says version 6 running, hangs "installing 7z," then re-downloads. ROOT: the nsis-web `oneClick:true` installer refuses to overwrite a running app, and the running app + its bundled **Python server child** hold file locks on the install dir → extraction of the 1.6GB `.nsis.7z` hangs; `differentialPackage:true` caused the redownload loop. FIX (v7.0.2): new `electron-app/installer.nsh` (verified) with a `killShokker` macro running `taskkill /F /T /IM` on every Shokker exe name (V8/V7/V6, shokker-server, v5, ag) in BOTH `customInit` (`.onInit`, before extraction — the critical spot) and `customInstall`; `/T` kills the child Python server; `differentialPackage:false`. Rebranded productName to "V7/V8" but **kept `appId com.shokker.paintbooth.v6` + package name** — license + saved work live in a hardcoded `%APPDATA%\ShokkerPaintBooth` (main.js, "DO NOT CHANGE"), so the rebrand can't orphan licenses. Buyer cleanup tool `Shokker-Paint-Booth-CLEANUP.bat` taskkills + removes the Programs dirs but NEVER touches `%APPDATA%\ShokkerPaintBooth`. Test trick: nsis-web stub uses a LOCAL package if the `.nsis.7z` sits in the same folder as the Web-Setup.exe → install clean, launch (app+server running), run installer AGAIN /S while running, assert exit 0 ~63s no hang.

---

### F. Meta-traps that made bugs look fixed/unfixed (read before debugging anything)

These wasted the most time chasing phantom bugs. Internalize them.

- **Network-drive caches (`spb-network-drive-cache.md`).** SPB lives on `C:\DRIVE E BACKUP\…`. (1) Stale Python `.pyc` in `__pycache__` → a test "fails" against code you already fixed. (2) Stale Bash tool output returns a previous command's text. FIXES: trust process EXIT CODES over printed output; read via PowerShell when Bash looks stale; purge `__pycache__` / `PYTHONDONTWRITEBYTECODE=1`; a failing test on this drive is guilty-until-proven a cache artifact — re-run isolated + bytecode-purged.
- **Soft reload ≠ Python reload.** Ctrl+R reloads JS only; the Python engine module loads once. A live preview can keep showing a STALE/old spec while the engine is fixed. **Python changes need a FULL app restart.**
- **The 2-copy tree.** A fix in one copy silently reverts in the copy the server loads. Sync root→`electron-app/server` via `node scripts/sync-runtime-copies.js --write` and verify by MD5; the live dev server runs from repo ROOT (`SPB_FRESH_START`, working dir = root).
- **The zone cache (D/A5).** `build_multi_zone._zone_cache` serves a stale render for an identical payload — clear it (or vary seed) when verifying engine fixes.
- **JS `?v=` cache tokens.** A JS fix won't reach Electron unless the `paint-booth-v2.html` script-tag token bumps. NOTE `paint-booth-2-state-zones.js?v=spb-zone-boot-bridge-3-20260522` is PINNED by `scripts/spb_guard_zone_extracted_boot_contract.js` — never bump it.
- **Verify a render-engine fix END-TO-END.** Unit-testing a leaf function (the B2/B3 saga, the A1 placement fn) is NOT proof — the bug repeatedly lived in a wrapper, an upstream `sm`, a duplicate render block, or a cache. Render via `build_multi_zone` / measure the real `car_spec_<id>.tga` / look at the actual image (the `spb-render-replay` skill exists for exactly this).

---

<a id="licensing-distribution-roadmap"></a>

## Licensing, Distribution & Roadmap (where it's been / where it's going)

This is the business/ship side of SPB: how a paying customer gets the app, how the license is checked, the per-key device-cap that's **built but not yet shipped**, the architecture history that got us here, and the open roadmap. Everything below is verified against the live repo `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum` (current `electron-app/package.json` version = **8.0.3**) unless explicitly flagged as "from memory."

### 1. Distribution: Payhip storefront → all-in-one R2 download → electron auto-update

SPB ships as **ONE all-in-one download** — the whole Electron app + EVERY finish family baked in — hosted on Cloudflare R2, with `electron-updater` pulling future versions from the same R2 feed. This is the model since **7.0.8** (2026-06-08); it superseded both the old GitHub-release feed and the in-app finish-pack downloader.

The chain, verified in `electron-app/package.json`:
- `build.win.target` = **`nsis-web`** (line ~34), NOT plain `nsis`. This is load-bearing: `makensis` only compiles a tiny ~0.69 MiB web-installer **stub**; the multi-GB app payload is `7za`-compressed into a separate `*-x64.nsis.7z` that the stub downloads at install time. This is what sidesteps the 32-bit `makensis` ~2 GB mmap ceiling entirely (see History below).
- `artifactName` = `ShokkerPaintBoothV8-${version}-Web-Setup.${ext}` (line ~36) — the stub Ricky uploads to **Payhip** is `ShokkerPaintBoothV8-8.0.3-Web-Setup.exe`.
- `build.publish` (lines ~88-90): `provider: "generic"`, `url: "https://pub-9969ab01838a4d69bb55822f42553904.r2.dev"`, `channel: "latest"`. Verify `app-update.yml` regenerates to this generic R2 url (NOT github) before every ship — a github value here bricks auto-update.
- **Identity is deliberately pinned to V6 for continuity**: `appId: "com.shokker.paintbooth.v6"` (line ~24) and package `name: "shokker-paint-booth-v6"` (line 2) are KEPT across the V7/V8 rebrand so existing buyers' license files and saved paints (under `%APPDATA%/ShokkerPaintBooth`) don't move. Only `productName` advances — currently **"Shokker Paint Booth V8"** (line ~25).

**Customer flow:** buy on Payhip → download the ~0.69 MiB Web-Setup stub → stub fetches the ~3 GB `.nsis.7z` from R2 at install → app runs fully offline thereafter, auto-updating from R2. (Install requires internet because the payload is fetched at install — a known trade-off of nsis-web.)

**Build + deploy tooling:**
- Build: `SPB_BUNDLE_ALL=1 npm run build` in `electron-app/`. `copy-server-assets.js` in `SPB_BUNDLE_ALL` mode bakes the premium families slim (2048-max, 4K dropped) into `server/assets/reference_textures`. Output lands in **`dist/nsis-web/`** (NOT `dist/` root — `dist/latest.yml` is a STALE old-oneClick file; never source the feed from there).
- Upload: **`deploy_r2.py`** (repo root, 12 KB, a KEEPER not scratch). It auto-descends into `dist/nsis-web`, reads the target version from `latest.yml`, and uploads ONLY that release's trio (stub + `.nsis.7z` + `latest.yml`), payload-before-feed, then `head_object`-verifies each key. Env vars (secrets never written to disk): `R2_ENDPOINT` (`https://<accountid>.r2.cloudflarestorage.com`), `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` (default **`shokkerpaintbooth`**, verified in script), `R2_PUBLIC_URL` (for printing links). Account id `dcdedf1b696ea520d672ffcc49dcf26f` and bucket name are from memory + the script default.
- The official release ritual lives in `docs/RELEASE_PROCESS.md` and the **`spb-deploy`** skill: version-bump → all-in-one build → **two-phase R2 upload** (`deploy_r2.py --hold-latest` → clean-VM sandbox smoke test → `--only-latest`) so the auto-update feed never points at an untested/missing package.

**Deploy gotchas (each cost real debugging time, from `spb-r2-oneshot-deploy.md`):**
- **boto3 ≥1.36** defaults `request_checksum_calculation` to `when_supported`, adding `x-amz-checksum-crc32` that R2's S3 multipart REJECTS → multi-GB upload aborts. Fix is `BotoConfig(request_checksum_calculation="when_required", response_checksum_validation="when_required")` (in `deploy_r2.py`).
- r2.dev public URL has **~1 min propagation** after Enable — a 403 immediately after enabling is NORMAL, not a misconfig. r2.dev is also rate-limited & "not for production"; map a custom domain (Ricky owns `shokkergroup.com` on Cloudflare, e.g. `downloads.shokkergroup.com`) before a wide launch.
- The stub's download URL is LZMA-compressed inside the NSIS exe, so a raw byte-grep for the r2.dev URL returns nothing — that's compression, not a missing URL.

### 2. License verify flow + offline fallback (the Payhip path, live in 8.0.3)

All license logic is in **`electron-app/main.js`**. Today's flow (verified by reading the functions, not memory):
- **Secrets are off the source tree** (`spb-license-secret-and-passwords.md`, confirmed): `loadLicenseSecrets()` (main.js ~191-211) reads **`electron-app/spb-license-secrets.json`** — **gitignored**, so it must exist on the build PC, and is bundled into `app.asar` via the `package.json` `build.files` whitelist. Holds `payhipProductSecret` (the Payhip merchant API secret), `ENCRYPTION_KEY` (AES key for the local license file), `earlyAccessHashes`, and `_CURRENT_PASSWORDS`. Env `SPB_PAYHIP_PRODUCT_SECRET` / `SPB_ENCRYPTION_KEY` override. If the file is missing, Payhip verify silently no-ops (main.js logs the warning at ~211) — back it up. **Caveat:** the secret is still in git history + the shipped asar; rotating it stays owner-only and was deliberately deferred ("no one has caught it").
- **Early-access bypass:** `verifyBypassCode` accepts a legacy `BYPASS_HASH` OR any SHA-256 in the config's `earlyAccessHashes` (the license.html "Have a developer/contributor code?" UI). Owner adds/revokes a dev/friend password by editing the JSON — no code change.
- **Machine binding:** `getMachineId()` (main.js **line 302**) = `sha256(os.hostname() + os.userInfo().username + os.homedir())` truncated to **16 hex chars**. The local license file (`%APPDATA%/ShokkerPaintBooth`, AES-256-CBC encrypted via `encryptData`/`decryptData`) stores `machineId`; `readLocalLicense()` (~310) invalidates the activation if `data.machineId !== getMachineId()`. **This is still the weak hostname-hash — NOT yet the Windows MachineGuid upgrade planned for 8.0.4** (verified: no MachineGuid reference in main.js).
- **Payhip verify:** `verifyWithPayhip(licenseKey)` (~588) calls `requestPayhipViaHttps(url)` (~496) first, then `requestPayhipViaElectronNet` (electron:net) as backup, then — if both report `networkError` — the dialog's **offline-activation** branch saves `offlineActivated:true` and lets the user in (~695, ~715). Endpoint: `GET https://payhip.com/api/v2/license/verify?license_key=...` with header `product-secret-key:<secret>`. On success it bumps Payhip's usage counter via `incrementPayhipUsage` (~627).
- **The "Verifying… forever" hang fix** (`license-verify-hang.md`, tagged `license-verify-hang-fix 2026-06-07`, verified present at main.js ~498 and ~604): Node's `request.setTimeout` is a SOCKET-idle timer that only arms after a socket connects — so a hung DNS/TCP-connect (captive wifi, Windows Sandbox, blackholed DNS) meant the promise NEVER resolved and the offline fallback never engaged. Fix: `requestPayhipViaHttps` now has a `settled` guard + a HARD wall-clock `setTimeout(..., LICENSE_REQUEST_TIMEOUT_MS + 500)` (= 10500 ms, `LICENSE_REQUEST_TIMEOUT_MS = 10000` at line 215) that destroys the request and resolves `{ok:false,code:TIMEOUT}` regardless of socket state; `verifyWithPayhip` adds a belt-and-suspenders `Promise.race` against a ~22 s `overallGuard` resolving `{valid:false, networkError:true}` so offline activation always engages. Any dead-network machine now reaches offline-activation in ≤~22 s instead of hanging forever. Reusable diagnostic: a ~40-line host-side Node probe that replays the exact `https.request` against `/verify` only (never `/usage`, which would burn a usage increment) — for the real key it returned HTTP 200 in 356 ms, `valid:true`. Roadmap #35 ("graceful offline/license-server handling — no infinite Verifying hangs") is this, shipped.

### 3. 8.0.4 device licensing — BUILT, NOT shipped (the headline of the next release)

Owner flagged 2026-06-17: "anyone could give their code to friends." The 2026-06-23 roadmap then made the **no-trial / buy-first** decision (fear of reverse-engineering) and explicitly **elevated device licensing as the real anti-piracy lever** (roadmap #91, starred). Today's app has **no central record of distinct PCs per key** — Payhip's `uses` counts activations (incl. reinstalls/sandbox), not devices — so a friend's PC has no idea a key is already in use. Owner decisions (locked): **cap = 2 devices per key, HARD BLOCK over the cap, self-service deactivate + owner reset, owner/test keys unlimited.**

**What's already built** (verified on disk in `license-worker/`, syntax-checked, last touched 2026-06-17 — NOT deployed, NOT integrated):
- `license-worker/src/worker.js` (10.4 KB) — a Cloudflare Worker + KV activation service. Verified endpoints/constants:
  - `DEFAULT_CAP = 2`, `DEVICE_IDLE_EXPIRY_DAYS = 60`, `TOKEN_DAYS = 30`, `PAYHIP_VERIFY_URL = 'https://payhip.com/api/v2/license/verify'`.
  - `POST /activate {key,fingerprint,label?}` → `payhipVerify()` server-side (mirrors the app's exact `product-secret-key` call) → registers the device in KV up to the cap → returns a signed offline token (`makeToken` = HMAC-SHA256 over `key|fp|exp`). Returns `status: activated | already_active | cap_exceeded | invalid_key | disabled | verify_unavailable`.
  - `POST /heartbeat {key,fingerprint}` (re-validate, refresh `lastSeen`, re-issue token), `POST /deactivate {key,fingerprint}` (self-service free a slot), `GET /admin/key?key=` + `POST /admin/reset {key,action}` (Bearer `ADMIN_SECRET`; actions `clear|disable|enable|unlimited|limited`), `GET /health`.
  - KV shape `lic:<KEY>` → `{devices:[{fp,firstSeen,lastSeen,label}], disabled, unlimited, email, productName, createdAt, updatedAt}`. `pruneIdle()` drops devices idle >60 days. `OWNER_KEYS` env = unlimited test keys; cap from `DEVICE_CAP` env (default 2).
  - **Security bonus:** the Payhip secret moves INTO the Worker (`PAYHIP_SECRET` binding) — off the shipped/extractable client bundle.
- `license-worker/wrangler.toml` — `name = "spb-license"`, `[vars] DEVICE_CAP = "2"`, KV binding `LICENSES` with id still a **placeholder `PASTE_KV_NAMESPACE_ID_HERE`** (proof it was never deployed). Secrets `PAYHIP_SECRET / TOKEN_SECRET / ADMIN_SECRET / OWNER_KEYS` are set via `wrangler secret put`, not committed.
- `license-worker/README.md` — the deploy runbook + admin/support curl recipes.

**Exact pending steps to actually ship 8.0.4:**
1. **Deploy the Worker.** Needs a Cloudflare API token scoped **Workers Scripts:Edit + Workers KV Storage:Edit** (the R2-only token from the deploy work will NOT work), OR Ricky runs the 4 commands in `license-worker/README.md`: `wrangler kv namespace create LICENSES` → paste the returned id into `wrangler.toml` (replacing the placeholder) → `wrangler secret put PAYHIP_SECRET/TOKEN_SECRET/ADMIN_SECRET/OWNER_KEYS` → `wrangler deploy`. Yields a `spb-license.<subdir>.workers.dev` URL (optional later: custom route `activate.shokkergroup.com`).
2. **App integration in `electron-app/main.js`** (none of this exists yet — grep confirms no `workers.dev`/`/activate`/`heartbeat`/`deactivate` references): upgrade `getMachineId()` from the weak hostname-hash to a salted hash of the **Windows MachineGuid** (`HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` — stable per real PC; note each fresh sandbox = a new MachineGuid, hence the owner-key exemption); call the Worker `/activate` on activation; handle `cap_exceeded`/`disabled`/`invalid_key`; store the signed token; add a periodic **heartbeat**; add a **"Deactivate this PC"** button (self-service slot free). Then remove the bundled Payhip secret once the Worker owns verification.
3. **Sandbox-test the full flow** (activate → 2nd PC ok → 3rd PC blocked → deactivate frees a slot) THEN ship as **8.0.4** via the standard version-bump + two-phase R2 deploy.
Build inline, NO swarm (token mandate). Caveat: KV is eventually-consistent — a same-second double-activate could beat the cap by one; negligible at this scale (swap to D1 if it ever matters).

### 4. History / milestones (where it's been)

- **3-copy → 2-copy consolidation** (CHANGELOG 2026-06-09, verified): the runtime had THREE synced code trees (repo root, `electron-app/server/`, and a `electron-app/server/pyserver/_internal/` PyInstaller mirror). The third shipped to NOBODY (excluded via `!pyserver/**`) yet had to be kept in sync — a recurring "edited one copy, shipped a stale other" drift source (the class of bug behind Money/Mortal Shokk breakage). It was DELETED (~585 MB recovered), removed from `scripts/runtime-sync-manifest.json`, and `copy-server-assets.js` now HARD-FAILS the build if any managed-code mirror is still drifted. **Sync is now root → `electron-app/server/` ONLY.** This SUPERSEDES every older "3-copy" reference in PRIORITIES.md/CHANGELOG (those are left intact as historical record).
- **Installer size ceilings → nsis-web + R2** (`spb-installer-size-and-ceilings.md`): two stacked hard ceilings forced the delivery rewrite — (A) electron-builder's cached 32-bit `makensis.exe` mmaps the compressed app .7z → ~2 GB cap (`makensis: failed creating mmap` when the app hit 3.4 GB), and (B) the hidden one, **GitHub Releases' 2 GiB per-asset limit** (electron-updater downloads a single asset). LAA-patching makensis alone couldn't beat (B); switching `win.target` to `nsis-web` beat both. ~401 MB of safe shrink levers were also applied (dead `server.exe`/`shokker-paint-booth-v5.exe` PyInstaller freezes = 314 MB, unused Electron locales = 39 MB, Python test/pip prune = 35 MB, byte-identical asset dups = 13 MB) plus a lossless cultural-JPEG re-save (PIL `quality='keep'`, 73 MB, PSNR 50-53 dB — bigger compression REJECTED by measurement as catastrophic on spec maps which carry material data).
- **GitHub-feed + finish-pack downloader → R2 one-shot.** The interim model (v7.0.4) excluded the ~4.8 GB `reference_textures` plates from the installer (GitHub asset cap) and shipped an **in-app downloader**: `engine/asset_packs.py` `resolve_ref_dir(rel)` (bundled-else-`%APPDATA%/ShokkerPaintBooth/asset_packs/...`), backend `GET /api/finish-packs` + `POST /api/finish-packs/install`, frontend `js/finishes/finish-packs.js`, packs hosted on GitHub release `asset-packs-v1`. Image-backed families (Mortal/Money Shokk, Forbidden Dragon, ColorShoxx, Grunge, Pattern Plates, Guest Designers) previewed but wouldn't render for buyers without their pack. This whole model was **superseded by the R2 all-in-one bake (7.0.8)** where every family ships in the download — the downloader still exists but its bundle-aware `pack_installed` auto-suppresses the nag.
- **v7.0.1 "Spring Catalogue" ALPHA** (CHANGELOG 2026-06-07): first nsis-web delivery, Wild Spec v2 (33 SHOKK SERIES + 11 EXTREME rebuilt), authored-spec verbatim rendering, one-click "Report a Problem" diagnostics, the license-verify-hang fix.
- **Current shipped: 8.0.3** (package.json). The 8.0.x line added themed FRACTURED finishes and the SPB CAR INTELLIGENCE / auto-layers work. **8.0.4 = device licensing, next.**

### 5. Roadmap & open items (where it's going)

The master plan is **`SPB_ROADMAP_100.md`** (2026-06-23, sales-driven, 100 tasks). Governance is built into it: a `/loop` automation pulls the lowest-ID task from the file (never re-plans), classified into tiers — **🟢 LOOP-SAFE (40 tasks)** additive/non-breaking/no-finish-changes/no-deploys the loop does autonomously; **🟡 OWNER-REVIEW (36)** built inline but STOP before shipping; **🔴 OWNER-ONLY (24)** deploys/licensing/pricing/content/marketing the loop may draft but never executes. Progress is appended to `SPB_ROADMAP_PROGRESS.jsonl`. Hard identity NO-GOs are restated: no 3D car preview, no number/sponsor editor — it's a spec-map / material-finish tool.

Key open items:
- **No-trial decision (2026-06-23, OWNER):** buy-first only; tasks #1/#5/#8/#10 (anything handing a non-buyer a working app) are DEFERRED. #2 sample car is kept but reframed as post-purchase first-run wow. This makes **device licensing the priority anti-piracy lever** and Section 2 ("make a brand-new BUYER succeed in 5 min" — refund-prevention + word-of-mouth) the growth focus.
- **Device licensing (#91, ★):** ship the already-built 2-device cap — see Section 3 for the exact pending steps. Highest-priority OWNER-ONLY item.
- **Spec Sculpt vision (open, task #16 in the live task list):** "streamline Spec Sculpt UX + make it more intelligent" is ongoing; QA is guarded by the `spb-spec-sculpt-qa` skill (real-file harness over `C:/1Shokker Paint Car Examples`, diffs per-channel stats against a baseline so a regression can't hide). The geometry-aware Auto-Spec engine is the "Track B build" option the catalog-health report offers as a better use of time than triaging an already-solid catalog.
- **Smart Separate AI-model deploy decision (`DEPLOY_SMART_SEPARATE_MODEL.md`, 2026-06-28, OWNER):** a model that separates ANY flat livery into NUMBERS / SPONSOR-TEXT / GRAPHIC-LOGOS / base PAINT was trained on the owner's own liveries and **hit 85.7% on priority families** (dirt/stock/truck/late-model; target was 80%). The graphic-logo separation is the piece no off-the-shelf model (CLIPSeg/OWL-ViT/U-Net) could do. Entrypoint `_separate_image.py` `separate_image()`, classifier head `_logo_data/maskcls.npz`, SAM checkpoint `_logo_data/sam_vit_b.pth` (375 MB), isolated `_gpuenv` (torch+cu124, RTX 4060 Ti). **Engine ready, deployment is the owner call:** (A) optional "Smart Separate Pro" GPU pack download (mirrors the finish-pack pattern), (B) cloud GPU endpoint (thin client, per-call cost), or (C) bundle for GPU machines (biggest installer). Wiring is one additive hook in `car_layers.separate_into_layers` gated on `SPB_LOGO_MASKCLS=1`.
- **Catalog health = GOOD (`CATALOG_HEALTH_REPORT.md`, 2026-06-28):** render perf is essentially compliant — of 1,525 finishes, only **3 are genuinely >3 s and barely** (`cx_burgundy_wine_gold` 3.31 s, `holographic_wrap` 3.13 s, `aurora` 3.12 s; the raw sweep's "199 FAILs" was memory-pressure measurement noise). Uniqueness flagged 127 pairs but **83 are intentional FRACTURED FLAMES spec-variants** (same flame paint, three spec treatments — Ignite/Dance/Topo) and 44 are deliberate color-variant families (carbon/glass/candy/aurora); only ~6 are genuine cross-name look-alikes worth a redesign (`piano_black≈smoked_glass` 99%, `obsidian≈piano_black` 95%, `chameleon≈iridescent` 95%, etc.). Pending owner decisions: make the uniqueness gate spec-aware vs. add exemptions for the flame variants; keep color-variant families as offerings vs. redesign; redesign the ~6 look-alikes. Reusable tooling built: `_catalog_perf_sweep.py`, `_retime.py`, `_profile_finish.py`, log `CATALOG_HARDENING_LOG.md`.
- **Live-preview tiling capture (open, task #22):** capture + fix the live-preview whole-car tiling in the current 10-zone state — the last known render-correctness loose end (distinct from the already-fixed base-scale tiling bugs). The `spb-render-replay` skill (replays `output/job_*/zones_payload.json` through `preview_render` with the zone cache cleared and views the actual image) is the tool for it.
- **Reliability/refund-prevention roadmap (§4):** opt-in crash telemetry (#31), auto-save/crash-recovery (#32), pre-deploy sandbox smoke test (#33, partly enforced by `spb-deploy`), export validation (#34), offline/license graceful handling (#35, shipped), update integrity/resume for R2 downloads (#38).

**Flagged as unverifiable here:** the R2 account id `dcdedf1b696ea520d672ffcc49dcf26f` (from memory; only the public r2.dev subdomain is confirmed in package.json) and the exact `CHANGELOG.md` version-by-version history below 8.0.3 (CHANGELOG was read only at the head; 3-copy→2-copy and v7.0.1 entries were directly verified). The 8.0.4 worker integration's absence from `main.js` IS verified (grep returned nothing).

---

<a id="dev-tooling-gotchas-how-to-work"></a>

## Dev Tooling, Gotchas & How to Work in This Repo

This is the operator's manual for a coding agent. It covers the standing dev **skills** you should reach for (not re-derive), the **gates/harnesses** that decide whether work is "done," the **Workbench** + **audit-page** review loops, how to **see the UI** without a browser tool, and the **gotchas** that have repeatedly burned agents on this repo. Repo root is `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum` (the old `E:\Koda\...` path is dead — if your cwd is there, stop and tell the owner). The shell cwd resets between Bash calls, so **always use absolute paths** and prefix multi-step Bash with `cd "C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum" || exit 1`.

### 0. First moves every session

1. **Read `SPB_WIKI.html`** (the Living Wiki) — `CLAUDE.md` and `AGENTS.md` both make this mandatory and constant for *every* agent. Its sections are markdown inside `<script type="text/markdown" data-section="...">` blocks: read the **Agent Coordination Board** (who's on what + file lanes) and **Working Conventions**, **claim** your lane on the board, **log** to the **Daily Work Log** as you go. A stale board/log means the task wasn't finished. (Note: `CLAUDE.md` also points at `WORKSPACE_LOCATION.md`; both exist at root and are verified.)
2. **Don't trust the 32KB+ `MEMORY.md` index blindly** — memory entries are point-in-time and often weeks stale; the system-reminders on each topic file say so explicitly. Verify any file:line claim against current code before editing (the render-perf memory documents an agent nearly "fixing" pristine code from a remembered/guessed source — see §8).

### 1. The 7 global dev SKILLS — use them, don't re-derive

Seven SPB-dev skills live GLOBALLY in `C:/Users/Ricky's PC/.claude/skills/` (verified present: `spb-render-replay`, `spb-ship-check`, `spb-finish-gate`, `spb-audit`, `spb-spec-sculpt-qa`, `spb-deploy`, `spb-new-category`). They're global (not project `.claude/`) so they load even though the owner launches Claude Code from the home dir. Invoke via the Skill tool. Each one bakes in a recurring ritual + the trap that ritual avoids:

- **spb-render-replay** — reproduce/verify ANY render, tiling, or "finish looks wrong on the car" bug. Replays `output/job_*/zones_payload.json` (schema `{zones, iracing_id, seed, car_prefix, paint_file}`, auto-saved on every non-preview render) through `shokker_engine_v2.preview_render` rendering the reported `base_scale` vs a `base_scale=1.0` control side-by-side, then **VIEWs the PNG with the Read tool**. Two traps it exists to avoid: (1) the **stale `build_multi_zone._zone_cache`** (24-entry LRU keyed by zone JSON) re-serves the OLD render for an identical payload — you must `E.build_multi_zone._zone_cache.clear()` or you "confirm" the already-fixed bug; (2) the **quadrant self-diff metric is diluted** for partial-car zones and reads "fine" while the image is visibly tiled — never trust metrics, look. Regression guard after a fix: `python -m pytest tests/regression_base_scale_no_whole_canvas_tile_test.py -q` (verified present). The tiling family lives in `engine/compose.py` and `shokker_engine_v2.py` (`build_multi_zone`); the skill cites approximate line numbers (`_apply_base_color_override` ~2057, `_transform_base_color_source` ~1114, `_apply_base_placement_to_paint` ~1183) — treat those as hints and re-Read exact bytes before editing.

- **spb-ship-check** — the pre-"done" ritual for ANY code change. (1) parse-check changed files (`python -c "import ast; ast.parse(...)"` for `.py`, `node --check` for `.js`); (2) run the gate battery matching the change; (3) **sync root → `electron-app/server/` via `node scripts/sync-runtime-copies.js --write` then `--check`** (SHA-256 drift-verified — use this, NOT hand-`cp`); (4) **bump the `?v=` cache token** in `paint-booth-v2.html` for any changed JS/CSS or Electron won't load it. Skipping sync or token = the phantom "my fix didn't take" report.

- **spb-finish-gate** — the CLAUDE.md rule #0/#0b battery before declaring any new/rebuilt finish or pattern done: Uniqueness Law (≥80% structural sim = redo), render-time ≤3s @2048, pattern anti-recycle, MIP-survival, iron-safe spec, coverage+fineness. Mechanical, never eyeballed. (Exact commands in §2.)

- **spb-audit** — the build→rate→fix→regenerate audit-page loop on the `june_audit` backend (§4). Reads `docs/AUDIT_PAGE_SPEC.md` first.

- **spb-spec-sculpt-qa** — real-file spec regression after ANY change to the spec pipeline (`engine/spec_sculpt/*`, auto-protect, zoned_auto_spec, decorrelation, clearcoat, iron rules). Runs `python _specsculpt_qa_harness.py scratch 0` (verified at root; kill-safe append-JSONL, skips already-snapshotted files, `FORCE=1` re-renders all; modes `scratch|fracture|candy|catalog:<id>`) over the owner's real liveries at `C:/1Shokker Paint Car Examples`, then `python scripts/spec_sculpt_qa_diff.py` (`--save-baseline` to freeze `_qa_diag_baseline.json`) to flag per-file/per-channel drift. Lock wins with `pytest tests_v2/test_spec_sculpt_quality_gate.py tests_v2/test_autoprotect_textline.py tests_v2/test_spec_sculpt_snapshot.py -q` (all verified present; re-baseline snapshot via `SNAPSHOT_UPDATE=1`).

- **spb-deploy** — owner-triggered release. Version bump in `electron-app/package.json` → `SPB_BUNDLE_ALL=1 npm run build` (artifacts in `electron-app/dist/nsis-web/`, NOT `dist/`) → **two-phase R2 upload**: `py -3 deploy_r2.py "electron-app\dist" --hold-latest` (stages payload+stub, feed held) → **sandbox-test the stub in Windows Sandbox** (`SPB_<version>_sandbox.wsb`, `<VGpu>Disable</VGpu>`) → `py -3 deploy_r2.py "electron-app\dist" --only-latest` to publish `latest.yml`. **Never publish `latest.yml` before the sandbox passes** or the auto-update feed points at an untested/missing package. `deploy_r2.py` verified at root; needs `boto3>=1.36` with the CRC32 workaround (R2 rejects CompleteMultipartUpload with CRC trailers) and rotating R2 creds. Confirm with the owner before the activation step.

- **spb-new-category** — AI-as-compiler new finish family (honors the token mandate, §7): write the generator library ONCE, author each finish as a ~15-line recipe, append-only `<CATEGORY>_PROGRESS.jsonl`, ≤2 subagents. Wire into BOTH the engine registry AND the **static JS catalog** (`paint-booth-0-finish-data.js`/`paint-booth-1-data.js`) — registry-only registration = INVISIBLE finishes — AND add the module to `scripts/runtime-sync-manifest.json` (verified) or it never ships. End on the audit loop.

### 2. Gates & harnesses (the "is it done" battery)

All gates exit non-zero on FAIL (CI-friendly). Run them OUTSIDE the work loop, one batched process, read verdict lines only. Verified present in `scripts/` unless noted:

- **Uniqueness Law** (CLAUDE.md rule #0; full law in `docs/UNIQUENESS_LAW.md`): a finish ≥80% structurally similar (color-INDEPENDENT, so recolors count) to ANY catalog finish FAILS and gets a *different idea*, not a tweak; and a finish's spec must mirror its paint's geometry unless its id is listed in `scripts/uniqueness_exemptions.json` (verified).
  ```
  python scripts/spb_catalog_fingerprint.py            # refresh whole-catalog index (incremental/cached); --ids a,b,c
  python scripts/spb_uniqueness_gate.py --module <mod> # gate a module; or --ids a,b,c; --report = all dup pairs
  ```
  The same fingerprint index powers the Workbench **Similarity** tab.
- **Render-time budget** (≤1s optimal, >3s @2048 = broken): `python scripts/render_time_harness.py` (writes `_perf_results.json`). Verify at REAL sizes — a 512 swatch hid a 57s blowup historically. There's also `python scripts/audit_render_perf.py --trials 3` (verified in `scripts/`, NOT root) cited by CLAUDE.md for post-engine-change profiling.
- **Pattern anti-recycle** (procedural patterns; same-design FFT/edge gestalt ≥0.95 = FAIL): `python scripts/spb_pattern_gate.py --ids <...>`.
- **MIP-survival** (does detail survive track distance; fail <0.25, warn <0.45): `py -3 scripts/mip_survival_gate.py thumbnails/audit/<category> --split half`.
- **Iron-safe spec** — every spec must pass `iron_validate` after `iron_fix` (CC 0 or ≥16; R≥15 non-mirror; no >55% chrome plate); covered by `tests_v2/test_spec_sculpt_quality_gate.py`.
- **Coverage + fineness** (rule #0b, mechanically gated): reference impl `tests/regression_flame_uniqueness_test.py` runs four fail-closed checks in one — uniqueness <0.80, render <3s @2048, `coverage_score >= MIN_COVERAGE`, `fineness_score >= MIN_FINENESS` — over `flame_math.FLAME_STRUCTURES`. Opt-outs must be NAMED with a written reason in an EXEMPT list (e.g. `flame_math.COVERAGE_EXEMPT`), never silently dodged.
- **M-metric scorers** (the 85% rule): `python scripts/spb_workbook_compute_m1.py && python scripts/spb_workbook_compute_m7.py`, then read the per-finish composite from `_workbook_metrics/m7_composite.json`. **85 = owner ship-bar; 80 = code "keeper" tier** (`tierThresholds.keeper == 80` in `spb_workbook_compute_m7.py`) — they are intentionally different, don't collapse them. spec_driven intents drop M1 from the composite (SPB-95) — score `M_std/R_std/CC_std` directly (each ≥20, range spanning most of [0,255]). **Owner doctrine (`AGENTS.md`) trumps M7**: fine 8-32px features, many spec shades, density>size, no lazy finishes — when the owner's eye and M7 disagree, the eye wins.
- **Identity / LSB pixel-identity verifiers** (prove a perf optimization changed NOTHING visually): `scripts/identity_snapshot.py` (`save` then `check`; snapshots LFR+FABLE monolithics/overlays/patterns at 512/seed42 to `_opt_baseline.npz`, asserts max abs diff ≤0.02 ≈ 5/255) and `scripts/spb_color_fn_verify.py` (`capture --tag pre|post` + `compare pre post --tol 1` for ≤1 LSB). Profiler: `scripts/spb_color_fn_profiler.py` (`--tag`, `--compare`, `--kinds`, `--size`, `--repeat`; run with `SPB_DISABLE_GPU=1`; full catalog at 1024 HANGS on the network drive — use `--size 256 --repeat 1 --kinds monolithic`). RULE for any perf edit: Read exact bytes immediately before editing, claim a win only when the verifier is SHA/byte-identical AND the profiler delta beats run-to-run noise, then grep your marker to confirm the edit landed.
- **Catalog audit tooling** (run after any big rebuild instead of finding bugs one screenshot at a time): `scripts/preflight.py` (boot/ship gate — server imports in a subprocess, route count ≥50, classifies 2-copy drift, resolves every `?v=` token; `--no-server` skips the heavy import), `scripts/overnight_catalog_audit.py` (renders the WHOLE catalog via the server's own helpers → incremental `_overnight_audit/catalog_audit.json`), `scripts/overnight_audit_analyze.py` (buckets into `_overnight_audit/FINDINGS.md`), `scripts/build_audit_dashboard.py` (rich `_overnight_audit/audit_dashboard.html`), `scripts/md_to_html.py` (generic MD→dark-HTML; owner prefers HTML). Plus the CONTRIBUTING verification stack: `scripts/spb_doctor.py` (one-shot env/import/registry health — verified), `scripts/spb_catalog_report.py` (duplicate ids / ungrouped / JS-only ids — verified), `scripts/check-js-lint.mjs` (in `scripts/`, NOT root — `node scripts/check-js-lint.mjs`), `python -m pytest tests_v2/`, `node scripts/sync-runtime-copies.js --check`. Authoritative checklist: `docs/HOW_TO_VERIFY.md`.

### 3. The Workbench (persistent audit tool — supersedes throwaway audit HTML for whole-library review)

`SPB_WORKBENCH.html` (verified at root) is a dark SPA covering the WHOLE live library, served by `server_routes/workbench_routes.py` (verified). Launch: restart the app/server, open `http://127.0.0.1:59876/SPB_WORKBENCH.html` (fallback `:59877`). Tabs: Finishes / Patterns / Spec Overlays / Bugs / Worklog, with lazy PAINT|SPEC swatches, a per-item 1-100 rating panel (keep/replace/rebuild/rename/remove + reason chips + notes + history), filters, and a **Similarity** tab on the uniqueness fingerprint index. APIs under `/api/workbench` (`GET catalog`, `GET swatch/<kind>/<id>` render-on-demand cached by mtime, `POST rating`, bugs/worklog). Verdict/bug/worklog data persists in SQLite at `_workbench/spb_workbench.db` (gitignored; tables `ratings`/`bugs`/`bug_comments`/`worklog`/`meta_kv`; current rating = MAX(ts) per item_id). On first init it idempotently migrates `_audit/june_*_audit.json` verdicts in. **Killer feature: `edited_since_rated`** = item's source-file mtime newer than your last rating ts → re-audit only what moved. When the owner says "look through the workbench," read the SQLite DB. Caveat from memory: the `server.py` registration block for these routes was applied live but historically not committed cleanly — verify it's wired if a fresh checkout loses the Workbench.

### 4. The audit-page loop (`docs/AUDIT_PAGE_SPEC.md` + june_audit backend)

When the owner says "make an audit page for X," follow `docs/AUDIT_PAGE_SPEC.md` (verified) — he built this rule so he never re-explains it. Backend already exists: `server_routes/june_audit_routes.py` (verified), `POST/GET /api/june-audit/<category>` where `<category>` is any `^[a-z0-9_]{1,40}$` key (zero backend change for a new audit). Verdicts persist to `electron-app/server/_audit/june_<category>_audit.json` (+ history `.jsonl`); read them back when he says "look through the audit." Verdicts: **keep | replace | rebuild | rename | remove** + 1-100 rating + reason chips + notes. Page behavior: `GET` on load hides keep/remove/rename items; rebuild/replace stay VISIBLE with a re-review banner (re-rate the rework). Render swatches via the real render path into `thumbnails/audit/<category>/<id>.png`.

**Serving gotcha (cost a broken link, verified in memory):** audit pages are served ONLY from `electron-app/server/` (= `CFG.ROOT_DIR`/`SERVER_DIR` in `server_v5.py`), via the generic `@app.route("/SPB_AUDIT_<name>.html")` in `june_audit_routes.py`. The catch-all `/<path:filename>` serves ONLY `.js/.css/.png/.svg/.ico` and **404s any `.html`**. So (1) if you write `SPB_AUDIT_*.html` to repo root you MUST also copy it into `electron-app/server/` (route reads fresh — no restart needed once the file is there); (2) ANY standalone HTML you want the owner to open in-browser must be named `SPB_AUDIT_<name>.html` AND live in `electron-app/server/` — a name like `SPB_REWORK_REVIEW.html` is unreachable. **Standing rules:** EVERY finish build/rebuild round gets an HTML audit page without being asked (only exception: ≤~6 items where he says chat feedback is fine), AND every finish audit gets logged as one table row in `SPB_WIKI.html` section `finish_audits`.

### 5. Headless visual verification (there is NO browser/computer-use tool here)

ToolSearch finds no computer-use tool. To SEE the SPB UI: the **Read tool renders PNG/JPG**, so screenshot the running app and Read it. Drive headless Chrome over CDP using Node 22's built-in `fetch`+`WebSocket` (no npm install): launch `"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu --no-sandbox --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=<FRESH clean dir> --window-size=1600,1000 http://localhost:59876` in the BACKGROUND. Two non-obvious must-haves: a **FRESH `--user-data-dir`** (else it attaches to the owner's running Chrome and writes no screenshot) and **`--remote-allow-origins=*`** (else the WS is refused). Then GET `http://127.0.0.1:9222/json` → page target `webSocketDebuggerUrl` → `Page.enable`+`Runtime.enable` → `Runtime.evaluate({expression, awaitPromise, returnByValue})` to script state → `Page.captureScreenshot({format:'png'})` → write base64 → Read it. Gotchas: **output paths must avoid spaces/apostrophes** (the username is "Ricky's PC" — `$env:TEMP` has an apostrophe that breaks `chrome --screenshot`; use `C:\Users\Public\spb_shots\`); a LIVE on-car render needs a paint file that EXISTS ON DISK (the auto-restored example sets `#paintFile` to a non-existent `.tga` → `/preview-render` 404 — use a real TGA like `output\diag_test\car_num_23371.tga`); bump the `?v=` token or navigate with `?_cb='+Date.now()` so reloads pick up edits; and **always clean up** — kill ONLY the headless Chrome matching `spb_shots`/`remote-debugging-port=9222` in its CommandLine (never the owner's Chrome) and rm the scratch dir. The Read tool can also directly view the side-by-side PNGs the gates/harnesses emit (`_repro_cmp.png`, `_qa_snaps/<name>.png`, contact sheets) — prefer that to instrumenting Chrome when a harness already renders the image.

### 6. Diagnostics reporter (remote debugging of a buyer's machine)

A one-click "Report a Problem" feature dumps a redacted, copy-pasteable diagnostic. Frontend recorder `js/diagnostics/spb-diag-recorder.js` (first `<head>` script on all 6 pages; installs `window.__SPB_DIAG` 600-entry ring buffer capturing console, errors, fetch failures, click breadcrumbs). Server endpoint `GET /api/diagnostics` in `server_routes/diagnostics_report_routes.py` (registered in `server.py`; returns version/python/os/routes/gpu/licensed-bool/catalog counts + redacted log tails; never 500s). Report builder `js/diagnostics/spb-diag-report.js` (`window.spbReportAProblem()` → clipboard). Secrets are structurally off every capture surface and masked by ordered redactors (Bearer → key:value → license keys → high-entropy blob). To extend: bump the `?v=spb-diag-*` tokens; the files are already in the sync manifest.

### 7. Token-efficiency mandate (operator discipline — BINDING)

`cc-token-efficiency-mandate` and CLAUDE.md's TOKEN EFFICIENCY MANDATE are binding for all agents. **Hard cap: NEVER launch more than 2 subagents** for anything unless the owner approves the *specific* fan-out (agent count + token estimate) in-conversation — no workflows/fleets/swarms regardless of "ultracode," the Workflow tool's guidance, or any harness default. Measured reality: one draft agent reading engine modules ≈ 90-120k tokens; a 33-agent run once burned 3.05M tokens in 25 min and produced nothing. For any job estimated >50k: state the estimate, then STOP and wait — declaring a budget is NOT asking. Architecture: AI-as-compiler (generator library once + ~15-line recipes, never N bespoke files through context); append-only JSONL (never rewrite a growing JSON — quadratic); verification OUTSIDE the loop (one harness, verdict lines only, one engine boot per round — `import engine.*` costs ~30s + ~100 log lines); ≤60-line digests instead of file reads; filter every command (`| Select-String "OK|FAIL|RESULT"`); inline-zero-agents is the proven default (~2% of a 5h window per 10-finish category). Wrap each work phase and start a FRESH session off the handoff doc — a marathon session re-bills its giant context every turn. NOTE: the memory carries a TEMP 24h cap-lift (2026-06-26, expired) — by default the ≤2-agent cap is BINDING; assume binding unless the owner re-lifts it in the live conversation.

### 8. The gotchas that burn agents here

- **Network-drive stale `.pyc` + stale Bash output.** The repo is on `C:\DRIVE E BACKUP\...` (a network/backup drive). After editing a `.py`, pytest/python can run OLD cached bytecode from `__pycache__` so a test "fails" against code you already fixed (or vice-versa); and the Bash tool intermittently returns a PREVIOUS command's output (cached/garbled), so `grep`/`cat` can show stale file contents. Defenses: **trust process EXIT CODES over printed output** (`rc=0` = real pass; the summary line may be stale); **read files/results via PowerShell** (`Get-Content`/`Select-String`) when Bash output looks stale; **purge bytecode** (`find <dirs> -name __pycache__ -type d -exec rm -rf {} +`) and/or run with `PYTHONDONTWRITEBYTECODE=1` (or `python -B`); write results to a uniquely-named file and read that. A failing test on this drive is guilty-until-proven a cache artifact — re-run isolated + bytecode-purged before concluding the source is wrong. (`server_v5.py` itself clears `__pycache__` on boot for exactly this reason.)
- **DON'T kill the live server.** The running app server is `server_v5.py` (main entry, default port **59876**; `server.py` provides the inherited legacy routes; dev launch `START_V5_DEV.bat` forces port 59877 with `SHOKKER_DEV=1` hot reload). The Workbench/audit pages are served by THIS server. If you must restart, prefer `SPB_FRESH_START.bat` (force-kills stale SPB python/node/electron from THIS repo by matching `server_v5.py|server.py|pyserver|Shokker Paint Booth` in the CommandLine — and explicitly excludes `review_server.py`). A server restart is required to load server-side Python or a newly-tokened front-end change; `SHOKKER_NO_CLEAN=1` runs a second instance without the boot clean.
- **Codex may be editing concurrently.** The owner has recurring "Codex shouldn't be running" anxiety. To check whether Codex is actually touching the Paint Booth: `Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'kernel.js' } | select CommandLine` and read each kernel's `--working-dir` (a Codex session on a *different* project ≠ touching SPB); and check engine mtimes: `Get-ChildItem '<root>\engine' -Recurse -File -Filter *.py | ? { $_.LastWriteTime -gt (Get-Date).AddMinutes(-30) }` (0 = not touching it). The scheduled task **"SPB HERMES Recon"** (`HERMES_RECON_TASK_RUN.bat`, 15-min repeat) is the real paint-booth auto-runner — last seen Disabled; re-check its State if engine files start changing on their own. **Don't entangle your commits with concurrent work** (the Workbench routes weren't committed cleanly for this reason).
- **Cache tokens (the #1 "I changed it but the app shows the old thing").** Electron caches JS/CSS aggressively (immutable max-age). A `.js`/`.css` edit won't load until its `?v=` token in `paint-booth-v2.html` is bumped (date-stamp/feature tag), then re-sync `paint-booth-v2.html`. Pages without a token (e.g. `spec-sculpt.html`) need `?_cb='+Date.now()` to bust. There's a related thumbnail cache chain (boot warm + hash-keyed re-bake) — see memory `spb-thumbnail-cache-chain`.
- **Static-catalog vs registry sync.** The picker/search run off STATIC JS catalogs (`paint-booth-0-finish-data.js` BASE_GROUPS/SPECIAL_GROUPS, `paint-booth-1-data.js` monolithics) — **registering a finish in the engine registry alone makes it INVISIBLE**. Wire BOTH, and add new expansion modules to `scripts/runtime-sync-manifest.json` or they silently never ship. Also: displayed NAME ≠ id (e.g. `spec_diamond_plate_micro` shows as "Micro Diamond Plate") — searching the audit by id-words gives false "missing" reports.
- **Dead `js/zones/*` modules.** The app loads ~61 `js/zones/*` control modules but only ~3 are ever `.install()`ed; the other ~58 are DEAD CODE (their globals are assigned inside `install()`). The LIVE implementation is duplicated in the monolith `paint-booth-2-state-zones.js`. **Editing a `js/zones/*` module to "fix the UI" does NOTHING** — fix the monolith. Verify a finish renders by replicating `getFinishType` (BASES→base, PATTERNS→pattern, else monolithic) and hitting `/api/swatch/<type>/<id>?color=888888&mode=split` with the CORRECT type and `color=` (wrong type/omitted color = false 404/500).
- **2-copy sync rule (was 3 until 2026-06-09).** Core files must stay in sync across exactly TWO trees: repo root (source of truth) and `electron-app/server/` (packaged into the installer). The old third copy `electron-app/server/pyserver/_internal/` was deleted — **do NOT recreate it.** Sync with `node scripts/sync-runtime-copies.js --write` then `--check` (flags verified: `--check` report-only/error-exit on drift, `--write` atomic-rename copy, `--dry-run`, `--verify` SHA-256, `--check-orphans`). The build hard-fails on managed-code drift. **`engine/` is check-only by design** (`check_only_directories` are never copied by `--write`) — if `--check` reports engine drift, copy those specific files deliberately and re-verify with `cmp`. Applies to `base_registry_data.py`, `paint-booth-0-finish-data.js`, `spec_patterns.py`, `viva_mexico/manifest.json`, and `paint-booth-*.js`.
- **Windows shell specifics.** Username path contains an apostrophe (`Ricky's PC`) — quote carefully; it breaks `chrome --screenshot` output paths and apostrophe-sensitive commands. PowerShell here is Windows PowerShell 5.1 (no `&&`/`||` chaining, no ternary; default file encoding UTF-16 — pass `-Encoding utf8` when other tools read the file). The Bash tool is Git Bash (POSIX) — use `/dev/null`, forward slashes, `$VAR`. cwd resets between Bash calls — absolute paths only.

### 9. Things I could NOT verify (flag before relying on them)

- `scripts/make_swatch.py` — referenced in `CONTRIBUTING.md` "Adding a New Finish" step 5 but **does not exist** in `scripts/` (the CONTRIBUTING flow appears partly aspirational; use the audit/swatch render paths the skills describe instead).
- `benchmark_finishes.py` — referenced in `CONTRIBUTING.md` "Testing Requirements" but **not found** at root or in `scripts/` (use `scripts/render_time_harness.py` / `scripts/audit_render_perf.py` / `scripts/spb_color_fn_profiler.py`).
- The compose.py/`build_multi_zone` line numbers cited in `spb-render-replay` (~2057/~1114/~1183) come from the skill/memory, not a fresh read — Read exact bytes before editing.
- The M7 keeper threshold (`== 80`) and per-script behaviors are quoted from CLAUDE.md/AGENTS.md/memory; the files exist but I did not execute the gates this session — run them to confirm current numbers before quoting them to the owner.

---

<a id="part-ii-history"></a>

# PART II — RELEASES, AUDITS & DAILY LOG (running history)

## RELEASES & SHIP STATUS (newest first)

SPB ships as **ONE all-in-one Cloudflare R2 download** (every finish baked in) with in-app
auto-update. Build: `SPB_BUNDLE_ALL=1 npm run build` in `electron-app/` → an nsis-web stub +
a ~3.8 GB `.nsis.7z` payload. The Payhip product file is the `…-Payhip.zip` (stub + READ ME).

| Version | Date | Status | Headline |
|---|---|---|---|
| **8.0.3-beta** | 2026-06-17 | **LIVE on R2** | 100 new FRACTURED themed finishes (🌊Deep/👣Cryptid/🛸UFO/🌈Rainbow/🔮Occult, 20 each); base/color/spec **scale<1 = FINER pattern** (not whole-car "mini-cars"); **HSB holds through scale-down**; brightness slider → **+200%**; Fresh Start kills orphaned backend + smart thumbnail cache; SHOKK DROP exact-spec fidelity confirmed. |
| 8.0.2-beta | 2026-06-16 | superseded | Toolbar grid→flex-wrap (Layer toggle + brush-size were collapsed); brush-stutter (blurred box-shadow); Shokk Drop roughness-floor-15 verbatim fix; version pill (stale `config.py VERSION`). |
| 8.0.1-beta | 2026-06-16 | superseded | Brush cursor visible (`#centerPanel > *` had killed `position:fixed`); Tool Guide hints; Select-All color fix. |
| 8.0.0 | mid-June 2026 | superseded | V8 line; all-in-one R2 bundle baseline. |

### DEPLOY pipeline (R2 + Payhip) — `deploy_r2.py`
- **Stage without activating:** `py -3 deploy_r2.py <dist> --hold-latest` → uploads payload + stub, **SKIPS `latest.yml`** so auto-update stays on the live version. Sandbox-test the stub first (`SPB_<ver>_sandbox.wsb`, with `<VGpu>Disable</VGpu>` — that's the fix for the "host force-closed the sandbox" quirk).
- **Activate:** `py -3 deploy_r2.py <dist>/nsis-web --only-latest` → publishes `latest.yml` only; **refuses** unless the payload is already verified on R2.
- **R2 free tier = 10 GB.** Keep only current + previous payload (each ~3.8 GB); delete older ones in the dashboard. Endpoint/bucket/public-URL are in the deploy env; creds are rotated after each deploy.
- **VERSION-BUMP CHECKLIST (move all together):** `electron-app/package.json` `version` · `server.py SPB_VERSION` · `config.py VERSION` · `paint-booth-5-api-render.js CLIENT_VERSION` · `tests/regression_version_truth_contract_test.py`.

### NEXT — 8.0.4: per-key device licensing (BUILT, not shipped)
Stops key-sharing. `license-worker/` is a Cloudflare Worker + KV service that caps each key to
**2 PCs (hard block + self-service deactivate; owner keys unlimited)** and verifies via Payhip
server-side (moving the secret off the client). **Pending:** deploy the Worker + app integration
(MachineGuid fingerprint, call Worker on activate, heartbeat, "Deactivate this PC") + sandbox
test. Deferred a few days after 8.0.3.

---

## JUNE COMPLETE AUDIT (started 2026-06-02)

**Goal:** one hard, honest pass over **every** base, spec overlay, and regular pattern
before the next ALPHA release. Whittle down the catalog, kill the half-assed ones, and
keep only the best bases, the best spec overlays, and the best patterns. Quality bar over
quantity.

### The three living audits

| Page (open via the running server) | Covers | Count | Worst AI now | Rating source |
|---|---|---|---|---|
| `/SPB_JUNE_AUDIT_SPEC_OVERLAYS.html` | Spec overlays | 262 | 25 | SPM9 (`_workbook_metrics/spm9_spec_pattern.json`) |
| `/SPB_JUNE_AUDIT_BASES.html` | Bases | 369 | 20 | M7 composite (`_workbook_metrics/m7_composite.json`) |
| `/SPB_JUNE_AUDIT_PATTERNS.html` | Regular patterns | 276 | 22 | M7 composite |

Open them through the server (e.g. `http://localhost:59876/SPB_JUNE_AUDIT_BASES.html`) so
thumbnails and the submit endpoint work. Cards are sorted **worst-AI-first** so the weakest
finishes surface immediately.

### What each card shows
- **Thumbnail + spec preview** (spec overlays: pattern + M/R/CC + on-metal; bases: paint +
  base-spec preview; patterns: paint).
- **Current AI rating (1–100)** + tier, baked in at build time, so the owner can see how far
  off the engine is from their eye.
- **Objections** — auto-derived from the weakest sub-metrics (e.g. "Misses its intended look
  (M6 50)", "Too similar to the rest of the catalog (UNQ 0) — nearest: crystal_shimmer",
  "Not enough fine detail at car scale").

### What the owner does (per card)
1. **Rate 1–100** (slider, step 1; defaults to the AI rating so it's easy to nudge).
2. Pick a **verdict**: `KEEP` · `REBUILD` · `REPLACE` · `REMOVE`.
3. **Notes** (especially for REPLACE — describe the new finish you want — or REBUILD — what to fix).
4. **SUBMIT** → the card disappears and the verdict is logged.

### The submit → backend loop (how verdicts persist)
- Each SUBMIT POSTs to **`/api/june-audit/<category>`** (`spec_overlay` | `base` | `pattern`).
- Server (`server_routes/june_audit_routes.py`) merges it into:
  - `_audit/june_<category>_audit.json` — current verdict per finish id
  - `_audit/june_<category>_audit_history.jsonl` — append-only submit log
- The page also keeps a `localStorage` backup and retries if the server is down, so nothing
  is lost if you rate before restarting the server.
- On reload, the page preloads saved verdicts (GET) and **hides already-decided finishes**, so
  progress persists across sessions.

### The work loop (dev side)
1. Owner reviews + submits in the HTML (cards vanish as they go).
2. Dev reads `_audit/june_<category>_audit.json` to see verdicts + ratings + notes.
3. Dev **acts**: REBUILD → fix the renderer to ≥ owner bar; REPLACE → build the new finish from
   the notes; REMOVE → pull it from the registries/picker; KEEP → leave it.
4. Dev re-runs **`python scripts/build_june_audit.py`** to rebuild the living pages with fresh
   AI scores. (Decided items stay hidden from the saved verdict store, so the queue keeps
   shrinking.) Re-bake thumbnails + re-run the metric scripts first if renderers changed.

### Files
- Generator: `scripts/build_june_audit.py` (build all, or `... spec_overlay|base|pattern`)
- Backend: `server_routes/june_audit_routes.py` (registered in `server.py`)
- Verdict stores: `_audit/june_*_audit.json` + `*_history.jsonl`
- Pages: `SPB_JUNE_AUDIT_{SPEC_OVERLAYS,BASES,PATTERNS}.html` (3-copy synced)

> ⚠️ The new route requires a **server restart** to go live. Until then, ratings save to the
> browser and sync on the next restart.

---

## HOW THE AI RATES (quick reference)

Full doctrine: `docs/METRICS.md`. Short version:

**Bases / regular patterns / monolithics → M7 composite** (`m7_composite.json`,
`byFinish["base:<id>"].composite`, 0–100). Surface-aware blend of:
- **M1** sibling differentiation · **M2** intent-fit (ID tokens) · **M5** spec↔paint coherence
  · **M6** intent floor/ceiling. Weights vary by intent (full / spec_driven / pattern_design).
- Tiers: keeper ≥80 · ok 65–79 · watch 50–64 · fix 35–49 · critical <35.

**Spec overlays (spec patterns) → SPM9** (`spm9_spec_pattern.json`,
`by_finish["<id>"].composite`, 0–100). Owner's pillars: uniqueness (UNQ), spec-color diversity
(SCD), render time (RT), wow (WOW) + fine-detail axes (PFV/FSC/MFS), minus penalties
(macro-pollution MP, repetition RP, catalog-similarity SIM).
- Tiers: masterpiece ≥90 · keeper 80–89 · ok 70–79 · watch 60–69 · fix 50–59 · critical <50.

**Regenerate scores** (after renderer changes; re-bake thumbnails first):
```
python scripts/spb_workbook_compute_m1.py   # ~30s (walks thumbnails)
python scripts/spb_workbook_compute_m2.py && python scripts/spb_workbook_compute_m5.py && python scripts/spb_workbook_compute_m6.py
python scripts/spb_workbook_compute_m7.py   # composite
python scripts/spm9_score.py                # spec patterns
python scripts/build_june_audit.py          # rebuild the living pages
```

> Owner mandate (`MEMORY.md`): the **eye wins over the metric** when they disagree. M7's
> B-structure axis rewards macro features the owner explicitly does NOT want — fine detail,
> dense small features, and wide spec-color variety beat big blobs every time.

---

## CONVENTIONS (so future audits match)

- **Interactive audit template lineage:** `SPEC_OVERLAY_DEFINITIVE_AUDIT.html` /
  `SPB_RATE_10.html` / the Spec Sculpt audit (`build_spec_sculpt_audit.py` + `/api/spec-sculpt/audit`).
  Cards disappear on decision; verdicts merge server-side by timestamp; localStorage is the
  offline backup.
- **Thumbnail URLs:** `/thumbnails/base/<id>.png`, `/thumbnails/base_spec_preview/<id>.png`,
  `/thumbnails/pattern/<id>.png`, `/thumbnails/spec_patterns_visual/<id>_160.png`,
  `/api/spec-pattern-preview/<id>` (on-demand M/R/CC), `/api/spec-pattern-visual-preview/<id>`.
- **2-copy rule (since 2026-06-09 — supersedes the old 3-copy rule):** core files live at
  root + `electron-app/server/` ONLY. The vestigial `electron-app/server/pyserver/_internal/`
  3rd copy was DELETED. Sync root → `electron-app/server` via `npm run sync-runtime` (in
  `electron-app/`); the build's `prebuild`/`copy-server-assets.js` **HARD-FAILS on managed-code
  drift**. The running dev server still uses the **root** copy.

---

## DAILY LOG (newest first — append every session, dated)

### 2026-07-16 — EASY MODE full-screen view SHIPPED (Claude, owner mandate)
- Owner: *"People buy it and think it's rocket science and give up on it."* Built the real Easy Mode: a
  **full-screen takeover** (`body.spb-easy-on`, z 20000 opaque cover — Pro UI untouched underneath) that is
  the **DEFAULT for new installs** (`localStorage spb_view_mode`, unset → easy). One screen: 17 curated look
  cards (HERO_BASES + combo recipes + chameleon special, server `/api/swatch` thumbs live-tinted), 11 color
  chips + Original + custom, Gloss/Satin/Matte/Chrome shine row ("your color survives every change"),
  🎲 curated surprise, SAVE TO iRACING. Drives the REAL `zones`/preview/render machinery — one
  `{color:'everything'}` zone, `pushZoneUndo` first, PRO switch carries everything into the full editor.
  The 🎓 coach is renamed **"Tutorial"** (strings only); Easy links to it via "Teach me the full app".
- Files: NEW `js/spb-easy-mode.js` + `css/spb-easy-mode-20260716.css`; `paint-booth-v2.html` (link/script/
  buttons, tokens `spb-easy-20260716b` + `spb-guide-tutorial-20260716`); manifest +2 (v2026.07.16-1). Synced.
- Live-verified end to end incl. a real render: **car_num_23371.tga + car_spec_23371.tga in 4.13s** with
  Easy's own success card (Pro results modal suppressed). Two live bugs found+fixed: author `display:flex`
  beating `[hidden]` (invisible backdrop ate every click), and phantom preset pattern ids (`tron`,
  `cracked_ice`) → real ids (`decade_80s_neon_grid`, `voronoi_shatter`). Full detail: SPB_WIKI.html Daily Log.

### 2026-07-01
- Session recheck: all prior fixes intact + synced root↔electron (compose.py, state-zones.js, canvas.js, CSS)
  — syntax clean, markers present. Added **base-adopt-on-pick** (unlocked base pick now takes the base's own
  swatch color; `state-zones.js` `_spbApplyPickedBaseToZone` `shouldAutoFill=!!(base && base.swatch)`) and the
  earlier **Exclude/spatial brush perf** fix (incremental `_fastSpatialOverlayArc` instead of per-frame full
  overlay rebuild). Verified **base scale is exact** via FFT (0.5×→×2.00 finer, 2.0×→×0.51 coarser) — not a bug.
- **NEW open bug → handed off (`HANDOFF_NEXT_THREAD_2026-07-01.md`, Task #1):** APPLY AREA box doesn't
  constrain the finish. Root cause: `region_mask` is only sent when `z.useRegion===true`
  (`paint-booth-5-api-render.js:36-39`); drawing a box sets `zone.regionMask` but NOT `zone.useRegion` (only the
  "Use Region" button does, `canvas.js:7233`), so the finish hits all color-matched pixels. Server intersect is
  correct (`shokker_engine_v2.py:17217/17229`). Fix dir: auto-enable `useRegion` on box/lasso commit. Also the
  "N pixels marked" note sums values×255 (`state-zones.js:1285`) — display bug.

### 2026-06-29
- **BETA UX FIX SWEEP (6 owner-reported bugs, pre-beta).** Diagnosed via a 5-agent read-only swarm,
  integrated serially (Codex concurrently editing canvas.js). (1) **Base color regression** — solid/gradient
  base colors vanished on the rebuilt OPAQUE bases (only "From special" worked): `engine/compose.py`
  `_base_color_replaces_source_before_material` returned True for solid/gradient → they were preseeded as the
  substrate and the opaque material painted over them. Fix = return False so they apply via the SAME
  post-material override 'special' uses (color shows, base SPEC preserved). Verified green renders on 6 opaque
  bases; 16 base regression tests green. (2) **Lock Base Color** toggle (per-zone `z.lockBaseColor`) replaced
  the broken Fit-to-Selection control; `_spbApplyPickedBaseToZone`/`_spbApplyPickedMonolithicToZone` now skip
  the color carry when locked → swap a base for its SPEC, keep your color. (3) **Base Fine Tuning** moved up
  inline under Base/Color/Spec Strength (no collapsible/scroll). (4) **Spec Sliders** — Auto-Pop moved into the
  row, Spec Preset select made readable, + 6 built-in spec feels (`_BUILTIN_SPEC_FEELS`). (5) **Live preview
  half-load on reopen/refresh** — all 4 paint-load paths now clear `lastPreviewZoneHash` + trigger preview
  (source identity isn't in the zone hash). (6) **Shokk Zones hover jank** — removed `:hover` from the wrap
  trigger in `ui-modern-polish-20260613.css` (hover grew the card → list reflow → pointer jump). All synced
  root↔electron, tokens bumped (`spb-zone-hover-noreflow-20260629`, `spb-livepreview-matmap-20260629`). Needs
  a server Fresh Start (compose.py). DEFERRED: source-paint whole-canvas tiling (overlaps uncommitted compose.py
  tiling work — verify via render-replay, don't hand-edit blind).
- **THIS WIKI MASSIVELY REBUILT** into the be-all/end-all source of truth. Added **PART I (Reference)** — 12
  code-verified sections (Overview/Identity, Architecture & Render Pipeline, Repository & File Map,
  Build·Run·Test·Deploy, Doctrines & Laws, Finishes/Patterns/Bases/Color Science, Spec Sculpt, Smart Separate
  + AI Model, Zones/Layers/UI, Big Bugs Chased & Fixed, Licensing/Distribution/Roadmap, Dev Tooling/Gotchas) —
  synthesized from 60+ memory files + the session dossiers + the live code (12-agent authoring swarm, claims
  verified against the tree). PART II below = the preserved release/audit/daily-log history. Old wiki backed
  up at `SPB_LIVING_WIKI.md.bak` (49KB → 302KB). **Read PART I before working; append here after.**
- **FOLDER CLEANUP: 117 GB → 44 GB** (~73 GB reclaimed, app verified intact). Deleted only build output
  (`electron-app/dist*` 24.6G), overnight render scratch (`_NIGHTLY` 26G), test temp (9.8G), old audit/perf
  runs, `_rate_*`/`_proof`/pycache scratch, and 2 abandoned April agent worktrees (WIP salvaged). Kept source,
  `.git` history, assets, masters, marketing, Workbench data. Audit trail: `CLEANUP_LOG.md`. Flagged (owner OK
  needed): AI env `_gpuenv` 5.7G, `thumbnails` 553M, old PayHip V5 zip.
- **OOM FIX (production bug) implemented + synced, ready to ship.** A user hit "Out of Memory" — root cause:
  `pushZoneUndo` (paint-booth-2-state-zones.js:504) snapshots ALL zones' spatialMask+strengthMap, kept 50 deep
  (`MAX_ZONE_UNDO=50`) → multiple GB on a multi-zone livery → Chromium renderer cap. Fix (tokens
  `spb-oom-fix-20260628`): MAX_ZONE_UNDO 50→15, _PIXEL_UNDO_MAX 10→6, _LAYER_UNDO_MAX 8→5, + eviction on the 3
  unbounded caches (_layerVisibleContributionCache / _previewCache / _imagePatternCache). node-checked, synced
  root↔electron. NEEDS an R2 deploy to reach the user. Plan: `OOM_FIX_PLAN.md`.
- **AI SEPARATION MODEL** (SAM + multi-scale OCR + CLIP multi-class) hit **85.7%** full-separation on priority
  car families; `_separate_image.py` in `_gpuenv`, NOT shipped — deployment is an owner decision (GPU pack /
  cloud / bundle). Dossier: `DEPLOY_SMART_SEPARATE_MODEL.md` + `CAR_INTEL_MISSION.md`.
- **CATALOG HEALTH AUDIT** (perf + uniqueness + spec-coupling): catalog is **HEALTHY** — perf within doctrine,
  "dupes" are mostly intentional flame spec-variants + color families, spec channel-coupling is a metric
  artifact (visually fine when relit). Real Spec Sculpt generator (`scratch_spec_from_any_paint`) confirmed
  decorrelated + paint-tracing + diverse. Report: `CATALOG_HEALTH_REPORT.md`.
- **Smart Separate** UX (real layers + restrict-to-layer, button contrast, draw-jank) handed to Codex who can
  live-test; see `SMART_SEPARATE_HANDOFF_FOR_CODEX.md`.

### 2026-06-18
- Base-layer **Spec Scale** now has an explicit **🔗 Match Base / 🔓 Independent** toggle (renderZoneDetail in `paint-booth-2-state-zones.js`). Moving the spec slider → Independent; ↺ reset → re-link. All render-payload `spec_scale` unified through `_spbResolveSpecScale` (api-render ×4 + canvas ×1; canvas had used `?? 1` = inconsistent → preview could disagree with export). Backward-compatible (resolver tested 6/6). Engine already applied divergent spec scale; this exposes the choice + makes payloads consistent. **SHOKK DROP verbatim path untouched.** Tokens `spb-specscale-mode-20260618`; both trees synced. *(Base 1.0 + Spec 0.5 = traced-interference offset.)*
- Kicked off a **7-hour overnight loop (15-min cadence)** to additively improve Spec Sculpt + SHOKK DROP — sacred exact-import path off-limits. Roadmap/rules/log in `_spec_shokk_overnight/PROGRESS.md`.

### 2026-06-17
- **8.0.3-beta BUILT → STAGED → SHIPPED to R2.** Auto-update live (feed verified `version: 8.0.3`).
  Pipeline used: version bump (5 surfaces) → `sync-runtime` → `SPB_BUNDLE_ALL=1 npm run build` →
  `deploy_r2.py --hold-latest` (stage) → Windows-Sandbox install test → `deploy_r2.py --only-latest`
  (activate). Payhip kit = `ShokkerPaintBoothV8-8.0.3-Payhip.zip`; notes = `RELEASE_NOTES_8.0.3.md`.
- **Base/Color/Spec Scale < 1 = FINER pattern (the recurring "tiles the whole car / mini-cars" bug — RESOLVED).**
  Root cause: monolithic FRACTURED finishes don't consume the thread-local zone placement, so the
  fallback transform tiled the **zone-masked (car-shaped) render** → shrunken car silhouettes.
  Fix in `build_multi_zone` (shokker_engine_v2.py): when scale<1, re-render the finish ONCE with a
  ONES mask over a clean decal-free seed = a PURE full-canvas pattern, tile THAT down
  (`_finer_base_paint_from_pure`), confine to the zone. Placed **immediately after the raw render,
  BEFORE all color ops** so HSB/override/strength survive. Proofs: `_fractured_proof/test_finer_scale.py`,
  `test_hsb_holds_on_scale.py`; official guard `regression_base_scale_no_whole_canvas_tile_test.py` 8/8.
- **HSB holds through scale-down** (was reverting to raw finish color) — same fix, by ordering the
  finer pass before `_apply_hsb_adjustments`.
- **`deploy_r2.py` gained staging:** `--hold-latest` (payload+stub, skip `latest.yml`) and
  `--only-latest` (publish feed, refuses unless payload already on R2).
- **Device-licensing service BUILT** (`license-worker/`, Cloudflare Worker + KV; 2-device cap, hard
  block, self-service deactivate, owner-key unlimited) for **8.0.4** — deploy + app integration pending.

### 2026-06-16
- **8.0.1-beta + 8.0.2-beta shipped** (R2 auto-update). 8.0.1: brush-cursor visibility
  (`#centerPanel > *` overrode inline `position:fixed`), Tool Guide hints, Select-All color (Wand
  `contiguous` hijack). 8.0.2: toolbar grid→flex-wrap (Layer toggle + brush-size slider were
  collapsed to 0 width), brush-stutter (blurred box-shadow repaint), Shokk Drop roughness-floor-15
  verbatim fix, version pill (stale `config.py VERSION`).
- **FRACTURED themed categories built** — 5 new picker groups × 20 = **100** generative finishes
  (🌊Deep/👣Cryptid/🛸UFO/🌈Rainbow/🔮Occult) in `engine/expansions/fractured_themes_2026.py`;
  FORGE consolidated to 78. **FRACTURED universe now = 263 finishes across 8 collections**
  (MINDS 55 · SOULS 30 · FORGE 78 · + 5×20 themed). Binding scale rule confirmed: procedural
  patterns render TOO BIG on the 2048 car — design 2-4× finer than the swatch.

### 2026-06-03 → 2026-06-15  (catch-up — the wiki was neglected through here)
- **SHOKK DROP authored-spec saga RESOLVED** (the big one): uploaded R/G/B spec channels
  (Metallic/Roughness/Clearcoat) now render **VERBATIM end-to-end, pixel-for-pixel to the iRacing
  `car_spec` export** — no procedural re-tune, no `base_spec_strength` boost, no roughness floor,
  no scaling, across every render path (finish AND base; preview AND export). The trap was THREE
  duplicate monolithic render blocks + the strength baked into `sm` upstream; fixed with a
  wrapper-proof `is_authored_spec()` id-set + hard `sm=1.0` for authored specs.
- **FRACTURED MINDS (55) + SOULS (30)** built and rebuilt with bespoke per-finish patterns; owner
  ship-audits drove a crush-finer quality pass. Earlier in the window: Spectrum Shift (50
  optical-physics finishes), Wave2 PRIZM/LFR rebuilds, FABLE + Let Freedom Ring categories, the
  Image Forge loop (art-verbatim paint + structure-derived spec).
- **All-in-one Cloudflare R2 delivery** (7.0.8+) with in-app auto-update — supersedes the GitHub
  feed + pack-downloader. Installer-hang, license-verify-hang, and packaged-build gotchas fixed
  across 7.0.2–7.0.9.
- **Uniqueness Gate** (`scripts/spb_uniqueness_gate.py`) made rule #0 (≥80% structural similarity
  to any catalog finish = redo); **render-time doctrine** (~1s, never >3s) enforced via
  `scripts/render_time_harness.py`.


- **Base-color override regression FIXED** (the #1 feature). Solid / from-special / gradient
  color was being applied only as an *underpaint* on monolithic finishes (Blue Vortex, Pearl
  Chaser, Paradigm…) and the finish painted over it, so the override was silently discarded;
  plain bases (Metallic) worked because they apply it to the final paint. Fix: monolithic
  PATH 2 in `shokker_engine_v2.py` now re-applies `_apply_base_color_override` to the FINAL
  paint (spec untouched), mirroring regular bases. Plus the UI half (Codex catch): the color
  picker (`js/zones/zone-base-color-controls.js` `setZoneBaseColor`) now forces
  `baseColorMode='solid'` + clears the auto `mono:<finish>` source, so a solid pick actually
  reaches the engine as solid. Verified: Pearl Chaser + solid red → red paint, spec byte-identical.
- **QoL UI batch:** hard-edge now defaults ON for every zone (render payload `hardEdge !== false`);
  source-canvas hover jitter fixed (the eyedropper `#hoverInfo` bar was in-flow → made absolute
  overlay); first-launch default paint → `SPB Chevy Truck Starting Example PSD.psd`
  (`server.py` `_default_asset_path` now also checks the project root); BASE FINE TUNING `−`
  steppers restored (CSS: they render in `.zone-fine-tuning-stack`, not `#fineTuningBody`, so the
  fixed-width rule never reached them); spec-overlay SCALE moved out of "Advanced Spec Overlay
  Tools" to under RANGE with ±5% steppers.
- **JUNE COMPLETE AUDIT system built:** 3 living HTML audits (262 spec overlays / 369 bases /
  276 patterns) with baked-in AI ratings, auto-objections, 1–100 owner slider,
  KEEP/REBUILD/REPLACE/REMOVE + notes, submit→`/api/june-audit/<cat>`→`_audit/june_*_audit.json`.
  Generator `scripts/build_june_audit.py`; backend `server_routes/june_audit_routes.py`. **Needs
  a server restart to activate the route.** This wiki created.
- **Spec overlays refreshed (SPM9, fresh render at 1024).** Distribution came out harsh: 240
  scored, median **32.6**, 236 critical. Per-axis diag shows the killer is **UNQ (uniqueness)
  + SIM penalty**, NOT individual quality (FSC/SCD/WOW often strong). The catalog is full of
  **near-duplicate pairs** (similarity 1.00): `spec_diamond_plate_micro`≡`spec_knurled_socket_grip`,
  `alligator_hide`≡`abstract_hard_edge_field`, `spec_mud_crackle_dried`≈`gold_flake`(0.99).
  SPM9 (owner's uniqueness-first "REJECT THE RECIPE" design) is working as intended — it flags
  sameness, which matches the owner's "they look the same / how did these pass" read. Scale
  confirmed SOLID + REALISTIC (14 metrics, full 0-100 headroom). The May→now drop (53→32) also
  means the catalog got *more* samey — a diversity regression worth watching.
  > NEXT: build a matching 10-15 metric scorer for BASES + PATTERNS (today they only have the
  > 4-component M7). Plan: generalize SPM9's render-and-analyze to paint+spec (≈12 visual axes:
  > fine-scale content, spec-color diversity, contrast richness, edge-direction diversity,
  > multi-feature scale, per-feature variance, brightness range, macro-pollution penalty) +
  > intent-fit (M2/M6) + catalog uniqueness/similarity, intent-aware weights per family. Then
  > refresh-score all 645 and rebuild those two audits.

## SPEC SCULPT — "Melt Minds" 50-campaign (2026-06-24, in progress)
6-hour inline loop (cron d77d9a48, */20) implementing a rated 50-improvement roadmap
(`SPECSCULPT_50_ROADMAP.md`) to make Spec Sculpt a standalone $30-worthy "sculpt your car like
Van Gogh" tool. Token mandate honored (inline, no fleets, despite ultracode).
- **Temp hygiene:** uploaded PSDs now keep only the newest 10 in temp (auto-cycle), no disk bloat.
- **#1 Sun Sweep (DONE):** `/api/spec-sculpt/sun-sweep` sculpts the spec then RELIGHTS it under a
  virtual sun swept across azimuths (`engine/spec_sculpt/sun_sweep.py`), 24 frames @384² in ~1.2s;
  Lab gains a "🌅 Sun Sweep" button + play/pause/scrub stage. You SEE the chrome ignite / candy
  deepen / matte stay flat — the angle-flash iRacing shows that a flat paint can't. Honors layer
  protection. Needs a full app restart (server route). Next in queue: #2 Before/After wipe slider.
- **#2 Before/After wipe (DONE):** "🪄 Before / After" button + a draggable wipe stage — left = flat
  paint, right = the same car RELIT with the sculpt (hero frame from the relight engine, not the
  false-color spec). Mouse + touch drag + slider. Reuses the sun-sweep route (client-only). The
  universal "ohhh": one handle turns a flat decal into a wet show-car finish in real time.
- **#3 Hero GIF export (DONE):** "⬇ GIF" in the Sun Sweep card -> /api/spec-sculpt/sun-sweep gif=true
  assembles the relit frames into a looping GIF (engine frames_to_gif), ~2.7MB in ~1.7s, downloads as
  shokker_sun_sweep.gif. Lazy (only built on request). The shareable reveal: one click → a Discord-ready
  loop of your car igniting under the sun. Server route changed → full app restart.
- **#4 Style Gallery (DONE):** a 12-tile curated gallery (Chrome Show / Liquid Mercury / Wet Candy /
  Carbon Race / Stealth Matte / Gunmetal / Holographic / Chameleon Flip / Galaxy Flake / Fracture Ignite
  / Oil Slick / Pearl Glow). Each tile maps to a real preset/mode (all ids validated against live
  /presets) + a themed gradient. Tap one → applies the look and auto-relights (Sun Sweep) so it appears
  instantly. The "no-knobs, sculpt like Van Gogh" centerpiece. Client-only.
- **#5 Drama slider (DONE):** one friendly '🎚️ Drama' knob (Subtle→Insane) under the Style Gallery that
  drives spec_multiplier. Raised the ceiling: spec strength now 0–200% (was capped at 100), so
  spec_multiplier spans 0.5–2.0 and "Insane" really hits. Live test: 0.5× and 2.0× both render ~0.45s and
  differ. Client-only. The no-knobs intensity dial: pick a style, then crank the drama.
- **#6 Material Spotlight (DONE):** '🔦 Material Spotlight' chips (Chrome / Wet-gloss / Matte / Show car)
  read the live spec composite client-side and glow the chosen material on the actual car (rest dimmed) +
  a plain-English readout "NN% reads chrome". Turns the abstract M/R/Cc map into "here's where your chrome
  is." Pure client.
- **RELIGHT REMOVED + Shokk-the-World diversity (2026-06-24, owner redirect):** the sun-sweep/relight
  approach was a dead end — REMOVED from Spec Sculpt entirely (Sun Sweep, Before/After wipe, Hero GIF,
  and the /api/spec-sculpt/sun-sweep route). Do NOT rebuild relight. Shokk the World now draws 20 looks
  from the FULL 2,145-finish catalog (state.catalogEntries) via _worldVariationsFromCatalog — Math.random
  shuffle + family spread, fresh every click — instead of the same ~20 scratch-preset archetypes. Verified:
  catalog=2145, batch renders catalog picks 8/8 distinct. Full app restart (server route removed).
- **#6a Style Gallery catalog tiles (DONE):** below the 12 curated tiles, a '🎲 Fresh from the catalog'
  row of 12 tiles SAMPLED from the full 2,145-finish catalog (random shuffle + family spread, hash-color
  gradients, prettified names) with a 🔀 Shuffle to re-roll. Click → applyCatalogStyle switches to Catalog
  mode + applies that finish + live-previews. 24+ one-click named looks now, ever-changing. Pure client.
- **#6b Shokk-the-World vibe chips (DONE):** Surprise / Chrome / Candy / Carbon-Matte / Holo-Shift / Flake
  chips in the StW card bias the 20-look catalog shuffle toward a vibe (keyword filter on id+name+category,
  then random sample), still reshuffled each click. Coverage verified (chrome155/holo198/candy94/carbon93/
  flake56 of 2145). Pure client.
- **#6c Surprise Me (DONE):** '🎰 Surprise Me' at the top of the Style Gallery — a slot-machine roll
  (flashes 9 random finish names, then lands) that applies one random finish from the 2,145-finish catalog
  instantly. Tap again for a new one. Also removed the last stale 'relight' copy. Pure client.
- **#7 Color → Material (DONE):** new engine hue_material_spec + /api/spec-sculpt/hue-map + a 🎨 rule
  builder. Each paint color family (reds/blues/.../darks/lights) gets its own finish behavior
  (chrome/matte/wet/satin/carbon/gloss); unruled pixels keep a base. "Reds chrome, blacks matte" is now
  literal + per-color on the user's livery. Iron-safe by construction (verified: 0 illegal clearcoat/
  chrome-plate/sub-15 roughness), 0.3s render. Server route added → full app restart.
- **#8 My Looks library (DONE):** '💾 My Looks' card (main, easy-mode visible) — save the current sculpt
  as a named look with a 120px thumbnail (snapped from the live spec preview), shown as a tile grid with
  Apply / rename / delete. Reuses the existing recipe store + captureSnapshot/applyRecipe plumbing (stays
  in sync with the advanced 'Saved looks'). One-tap reapply to any livery. Pure client.
- **#9 Tone → Material (DONE):** tonal sibling of #7. New engine tone_material_spec maps luminance bands
  (shadows..highlights) to finishes; the /api/spec-sculpt/hue-map route gained a tone_bands mode (no new
  endpoint). '🌗 Tone → Material' card = 5 brightness rows + material selects. "Shadows deep candy,
  highlights satin" shadow-pop. Iron-safe, 0.35s. Server route changed → full app restart.
- **#10 Per-layer material (DONE):** each PSD layer row gets a finish dropdown; '🧱 Apply layer materials'
  sculpts each named layer with its assigned material (engine layer_material_spec, doc-order so upper
  layers win). Perf: switched composite()->L.numpy() + max_size build = 0.62s @2048 (was 3.05s), iron-safe.
  Route /api/spec-sculpt/hue-map gained a layer_materials mode. "Body satin, trim chrome, sponsors matte"
  per layer. Server route changed → full app restart.
- **#11 Physically Valid badge + iron auto-fix (DONE):** engine iron_validate + iron_fix; the
  /api/spec-sculpt/generate route now iron_fixes spec_u8 at both spec sites (preview + 2048 save) so every
  sculpt/TGA is iRacing-legal (no-op on already-legal specs — existing finishes untouched). Live
  '🛡 Physically valid' badge under the preview reads #imgC + checks the 3 iron rules. Verified: violations
  caught + fixed, valid specs unchanged, live generate validates clean. Server route changed → full restart.
- **#12 Preset audit + repair (DONE):** new scripts/specsculpt_preset_audit.py renders EVERY wired Spec
  Sculpt preset and flags error/dead/degenerate/iron-illegal. Found 10 broken (pointed at spectrum_* finish
  ids removed in the Spectrum-Shift rebuild, incl. the gallery's Oil Slick tile); remapped all 10 in
  engine/spec_sculpt/presets.py to valid thematically-matched spectrum finishes. Re-audit: 388/388 OK, 0
  broken. Did NOT touch finishes/compose.py. presets cached at boot → full app restart.
- **#13 Region Brush (DONE) — S+A TIER COMPLETE:** '🖌️ Region Brush' lets you paint finishes straight
  onto the car (material chips + brush size + undo/clear, mouse+touch). engine brush_material_spec +
  /api/spec-sculpt/brush-map stamp per-material painted masks (iron-safe, 0.14s). With #13 the whole S+A
  tier (1-13) is done; the 6h campaign loop was stopped. Server route added → full app restart.
- **#13i Text → Material — NATURAL-LANGUAGE SPEC AUTHORING (DONE):** '✨ Sculpt from Words' — type
  "aggressive matte black, chrome accents, wet-candy lows" → _parseTextScheme (phrase-split, per-phrase
  material+qualifier+drama) → base/hue-rules/tone-bands → sets Drama + the /hue-map route → spec + an
  "I heard:" readout. First spec tool with plain-English authoring. Parser node-unit-tested (v2 phrase-based
  after a cross-phrase bug). Client-only. Also: B/C loop armed (cron 1f76671b), roadmap got 4 🚀 rows.
- **#13j Material Weathering / Detail (DONE):** engine weather_spec (swirls / scratches / brushed / grime /
  orange-peel) modulates Roughness+Clearcoat for hyper-real micro-texture; BAKED into the generate route
  (live preview + 2048 deploy), iron-safe, 0.03-0.06s. Client '✨ Detail' chips + amount slider in the Style
  Gallery. Polisher swirls / brushed grain / road grime on any sculpt. Server route changed → full restart.
- **#13k Reference-photo material match (DONE):** '🖼️ Match a Photo' — drop a real photo, _analyzeReference
  reads gloss(highlights)/contrast(std)/sparkle(high-freq)/tone client-side and derives a material + drama,
  sets Drama + applies via /hue-map, with a "Reads as: mirror-metal → chrome 95%" readout + reference thumb.
  Node-unit-tested with a stubbed canvas (chrome/matte/satin all correct). Client-only. Supersedes #19.
- **#13l Material Gradient (DONE) — all 4 🚀 innovations complete:** engine gradient_material_spec lerps
  two finishes across the car (horizontal/vertical/diagonal/radial), iron-safe by construction; /hue-map
  gained a gradient mode; '🌈 Material Gradient' card = A→B selects + direction chips. Chrome→matte fade in
  one tap. Server route changed → full restart. The innovation block (Text→Material, Weathering, Photo-match,
  Gradient) is done; loop continues into B-tier (#14 macro loupe, #15 style blend, ...).
- **#15 Style Blend (DONE):** one slider mixes two finishes — 60% Chrome + 40% Carbon — for a look that's
  all your own. Client-only: rides the engine's weighted preset-stack blend (applyQuickPresetStack); the 10
  blendable finishes are derived from the audited Style Gallery tiles, so every pick is real. Drag the slider
  → the car morphs A→B live (debounced). No server change → no restart. B-tier rolls on (#16 proof card next).
- **#16 Share Proof Card (DONE):** one click → a branded 16:9 social card — BEFORE (your paint) | AFTER (the
  material spec) twin panels + the M/R/Cc channel filmstrip + the green Physically-Valid badge + SPB branding,
  downloadable PNG. Client-only canvas; pure cover-fit math extracted + unit-tested (no distortion). No server
  change → no restart. B-tier continues (#17 +50 bespoke presets next).
- **#17 +50 Bespoke Designer Blends (DONE):** engine/spec_sculpt/presets_bespoke50_2026.py adds 50 DESIGNED
  cross-family material recipes (Liquid Obsidian, Venom Candy, Stealth Gold, Tesla Obsidian, Wormhole Chrome…)
  in 6 new "Designer · *Fusion" picker categories. Each blends 2 already-shipped finishes (guaranteed
  resolvable for buyers; register() refuses any blend with an unshipped source), validated 50/50 by the #12
  audit gate (distinct + non-degenerate + iron-legal). 1.83s @1024 work grid (faster than the existing
  3-blend). Engine change → FULL APP RESTART. B-tier continues (#14 macro loupe next).
- **#14 Macro Loupe (DONE):** hover the composite preview → a floating pixelated magnifier (~5.8x) follows the
  cursor with a crosshair AND a plain-English material readout (mirror chrome / wet candy gloss / dead matte / …)
  + the raw M/R/Cc values, because the composite's RGB literally IS the spec. Pure _materialLabel classifier
  unit-tested 6/6 on the real palette. '🔬 loupe' toggle, client-only, no relight, no restart. B-tier continues
  (#18 undo/redo next).
- **#18 Undo/Redo + History Timeline (DONE):** a coalescing snapshot stack (max 60) over the live-preview
  state — every sculpt change is checkpointed (800ms debounce = one step per slider drag), dedup'd, with a
  proper redo-branch truncation and a suppress-window so restores don't corrupt redo. '↶ History' card with
  Undo/Redo buttons + clickable numbered timeline + Ctrl+Z / Ctrl+Shift+Z (guarded around text fields).
  Reuses captureSnapshot/applySnapshot/restoreBlendStacksPhase. Client-only, no restart. State-machine sim
  6/6. B-tier continues (#20 channel decorrelation meter next).
- **#20 Channel Decorrelation Meter (DONE):** surfaces the engine's |corr|<0.85 decorrelation science to the
  user — samples the composite, splits R/G/B=M/R/Cc, computes pairwise Pearson correlation + stdev, and shows
  3 color-coded bars (M·R/M·Cc/R·Cc) + a verdict (Rich & decorrelated ✓ … Too correlated → flat look ⚠) with a
  fix hint. Auto-updates on every render. Pure _pearson unit-tested 5/5. Client-only, no restart. B-tier
  continues (#21 flake/sparkle shimmer preview next).
- **#21 Flake/Sparkle Shimmer Preview (DONE):** an overlay canvas twinkles the metallic-flake zones of the
  composite — pure _flakeScore (metallic*low-roughness*gloss) picks the 400 strongest seeds, each sparkles via
  sin(phase+t*speed) with a radial glow + glint cross (additive blend). NOT relight — localized pinpoint
  twinkle, not a moving light. '✨ Shimmer preview' toggle, re-seeds per render, client-only, no restart.
  _flakeScore unit-tested 5/5. B-tier continues (#22 theme packs next).
- **#22 Theme Packs (DONE):** '🎭 Theme Packs' card with 6 vibe tabs (Show Car / Race Day / Stealth Ops /
  Candy Shop / Holo Lab / Heat & Glow), each 6 one-tap named looks curated from the gallery presets + the new
  Designer Fusions. All 35 ids validated against the registry (no dead chips). Client-only over
  applyQuickPresetStack. B-tier continues (#23 symmetry mirror next).
- **#23 Symmetry Mirror (DONE):** the region material brush gains a Symmetry chip row — Off / ⇄ Vertical /
  ⇅ Horizontal / ⧉ Quad. Pure _mirrorPt reflects stroke points; copies are committed on _brushUp AND previewed
  live at 0.4 alpha in _brushRedraw, so paint one side and the other(s) mirror under your cursor. Flows through
  the existing rasterize→brush-map path. Geometry unit-tested 9/9. Client-only, no restart. B-tier continues
  (#24 mask refine next).
- **#24 Mask Refine (DONE):** engine refine_sculpt_mask(mask,grow) erodes/dilates the protected region —
  + grows a protective halo around logos, − sculpts closer to the edges; apply_sculpt_mask feather now
  exposed (0-12px). Route (/generate + Shokk-the-World) parses mask_grow + mask_feather; 'Protect edge' +
  'Feather' sliders in the PSD layer panel live-refine via the preview. Behavior test PASS (400→1296 grow /
  →16 contract). Engine+route change → FULL APP RESTART. B-tier continues (#25 smart layer auto-material next).
- **#25 Smart Layer Auto-Material (DONE):** an '✨ Auto-assign' button reads each PSD layer's NAME and proposes
  a material via the pure _inferLayerMaterial classifier (body→satin, sponsor/number/text→matte, chrome
  trim→chrome, carbon wing→carbon, glass→wet, unknown→keep). Fills the #10 per-layer selects for review, then
  Apply. Classifier unit-tested 16/16. Client-only, no restart. B-tier continues (#27 real-time material
  readout next).
- **#27 Material Probe / real-time readout (DONE):** click the composite to pin numbered sample points; each
  shows a false-color swatch + plain-English material + exact M/R/Cc in the '📍 Material Probe' table, and all
  pins live-resample on every re-sculpt. Reuses the loupe's pixel reader + _materialLabel (DRY); markers are
  %-positioned so they scale. Sampling pipeline unit-tested 6/6. Client-only, no restart. B-tier continues
  (#28 render-time budget meter next).
- **#28 Render-time Budget Meter (DONE):** a one-hook global fetch tee reads the X-Render-Time-Ms header
  (already stamped by after_request) off every spec-sculpt render call and shows a 3s-budget bar under the
  decorrelation meter — green ≤2s / amber 2-3s / red >3s with a plain hint. Surfaces the ≤3s render doctrine
  live. Pure _budgetState unit-tested 5/5; header presence confirmed. Client-only, no restart. B-tier continues
  (#29 import/export .shokklook next).
- **#29 Import/Export .shokklook (DONE):** export the current sculpt as a portable versioned JSON .shokklook
  (identity stripped) and import one back — _coerceShokkLook parses the envelope OR a raw snapshot, then
  applySnapshot + restoreBlendStacksPhase apply it (keeping your car identity) and auto-save to My Looks.
  Buttons in the My Looks card. Parser unit-tested 6/6. Client-only, no restart. B-tier continues (#30 batch
  sculpt next).
- **#30 Batch Sculpt a Folder (DONE) — B-TIER COMPLETE:** new internal route /api/spec-sculpt/batch-folder
  applies the current scratch/catalog look to every paint in a folder (capped 64), writing a spec .tga per
  file to <folder>/_spec; reuses scratch_spec_from_any_paint + iron_fix. '📦 Batch Sculpt a Folder' card posts
  the current preset/catalog stacks with the internal header + shows a per-file report. Route smoke test PASS
  (3/3 written, guard=403). Engine+route change → FULL APP RESTART. All B-tier items (#14–#30) are now ✅;
  the campaign moves to C-tier (#31 auto-save/restore next).
- **#31 Auto-save/restore HARDENED (DONE):** 4 fixes on the existing session persistence — corrupt-session key
  now self-clears (no more boot-loop failures), save-on-tab-hidden (mobile-safe), a '↩ Restored your last
  session' bar with Start-fresh/dismiss, and a 30s periodic backstop save. Client-only, no restart. C-tier
  continues (#32 keyboard shortcuts next).
- **#32 Keyboard Shortcuts (DONE):** global keys — Ctrl+Enter/G = Sculpt, V = variations, D = Deploy, W = Shokk
  the World, R = Surprise, ? = help overlay, Esc = close; routes through _kbClick (respects disabled buttons),
  skipped while typing in inputs. Complements the #18 undo/redo keys. Client-only, no restart. C-tier continues
  (#33 open iRacing folder next).
- **#33 Open iRacing Folder (DONE):** new internal route /api/spec-sculpt/open-folder opens a folder in the OS
  explorer (os.startfile/open/xdg-open, file→parent, validates isdir); '📂 Open folder' button by Deploy opens
  the last deployed folder (j.output_dir.path / j.path) or the configured #outputDir. Route guard/validation
  verified (403/400/404). Engine+route change → FULL APP RESTART. C-tier continues (#34 paste/drag-drop next).
- **#34 Paste + Drop-Anywhere (DONE):** refactored the dropzone logic into one DRY _acceptPaintFile, then added
  document-level drag-drop ANYWHERE (dedicated zones excluded; dropzone stopPropagation prevents double-load)
  and Ctrl+V clipboard paste (image files only, so text paste is untouched). Client-only, no restart. C-tier
  continues (#35 animated sculpt loader next).
- **#35 Animated Sculpt Loader (DONE):** a floating scan-line toast with cycling phrases (Reading your paint →
  Tracing material zones → Igniting the chrome → Checking iRacing legality → …) shown during generate()
  (start→finally). CSS keyframe injected at runtime; client-only, no restart. C-tier continues (#36 first-run
  guided tour next).
- **#36 First-run Guided Tour (DONE):** 4 coachmarks ring the real UI (Load → Pick a look → Sculpt → Deploy)
  with a floating tip (Back/Next/Skip + progress); pure _tourClampPos positions it below/above with viewport
  clamping (unit-tested 4/4). Auto-runs once on first visit; re-triggerable via '🎓 Take the guided tour' in the
  ? help. Client-only, no restart. C-tier continues (#37 favorites/recently-used rail next).
- **#37 Favorites Rail (DONE):** the recently-used rail already existed (renderRecent); added the missing
  Favorites half — a '⭐ Favorite this look' button + a pinned '⭐ Favorites' strip (reuses .recent-item),
  signature-keyed toggle (star/un-star), persistent (max 24, no aging), click to re-apply, × to remove.
  Three tiers now: My Looks (named) · Recent (auto) · Favorites (starred). Toggle logic unit-tested 5/5.
  Client-only, no restart. C-tier continues (#38 per-series templates next).
- **#38 Per-Series Templates (DONE):** '🏁 Series Templates' card with 8 one-tap looks tuned to a racing
  series' real material feel (NASCAR gloss, GT3 carbon+gunmetal, Dirt matte-flat, Formula, Rally, IndyCar,
  Drift, GT Sports) over applyQuickPresetStack; all 9 source ids registry-validated. Client-only, no restart.
  C-tier continues (#39 copy/share settings as a short code next).
- **#39 Share-as-Short-Code (DONE):** '🔗 Copy code' emits a SHOKK1: UTF-8-safe base64 of the current look
  (identity stripped) to the clipboard; a paste field + Apply runs pure _parseLookCode (prefix/whitespace
  tolerant) → applySnapshot keeping your car identity. Sibling to .shokklook (#29), reuses _coerceShokkLook.
  Round-trip unit-tested 6/6 (emoji survives). Client-only, no restart. C-tier continues (#40 eyedropper
  glossy-everywhere next).
- **#40 Eyedropper → color-everywhere (DONE):** hue_material_spec gained a color-target rule
  {color:[r,g,b],material,tol} (hue within tol°, S-gated; greyscale samples match by low-sat). The 🎯 eyedropper
  now reveals a swatch + material select + 'everywhere →' that POSTs a /hue-map color rule. Engine test PASS
  (red→chrome, blue untouched, grey→matte). Engine change → FULL APP RESTART. C-tier continues (#42 progress+ETA
  next).
- **#42 Progress + ETA (DONE):** the #35 sculpt loader gains a gradient progress bar + '~Ns left' driven by a
  LEARNED median of recent wall-clock render durations (persisted, last 7; default 8s first time). Eases to 96%
  then snaps to 100%/'Done!' on response; self-calibrates per machine. ETA helpers unit-tested 6/6. Client-only,
  no restart. C-tier continues (#43 premium UI pass next).
- **#43 Premium UI Polish (DONE):** additive, non-structural CSS — button hover-lift/active/disabled states,
  :focus-visible accent rings, input focus glow, card hover elevation, <code> chips, refined custom scrollbars
  (accent-on-hover), prefers-reduced-motion guard. Nothing shifts (no padding/layout changes); all new cards
  inherit it. Verified balanced (<style> 1/1, braces 21/21, head 282/282). Client-only, no restart. C-tier
  continues (#44 surprise-within-a-vibe next).
- **#44 Surprise within a Vibe (DONE):** '🎲 Surprise within a Vibe' card with 7 vibe buttons (Chrome/Candy/
  Carbon/Holo/Glow/Stealth/Flake), each a rich curated pool (gallery presets + Designer Fusions); tap applies a
  random look from that vibe with no-immediate-repeat. All 66 ids registry-validated. Client-only, no restart.
  C-tier continues (#45 iRacing-look accuracy note next).
- **#45 iRacing-look Notes (DONE):** pure _iracingLookNote maps each material to how it renders in iRacing's PBR
  (chrome=mirror reflects sky, matte=dead flat, wet=glints on turn, …). Surfaced as a collapsible '🏁 How each
  material looks in iRacing' guide (8 materials + swatch) AND as hover titles on Material Probe rows. Note fn
  unit-tested 6/6. Client-only, no restart. C-tier continues (#46 achievement micro-moments next).
- **#46 Achievement Micro-moments (DONE):** celebratory bottom-center badge toasts fire once per first-time
  milestone (First Sculpt 🎨, 10 sculpts 🔥, First Deploy 🏁, First Chrome 🪞, First Favorite ⭐) via _unlockAch
  (localStorage, dedup). Client-only, no restart.
- **2026-06-25 OWNER PIVOT:** authorized 24h swarms (overrides token mandate) + headline ask = TGA auto-protect
  (decipher numbers/sponsors/decals vs base paint, NO PSD). Launched background workflow tga-autoprotect
  (design→build→adversarial-vet, writes+self-tests engine/spec_sculpt/_autoprotect_draft.py). Integrate when done.
  C-tier remaining: #47 compare, #48 auto-levels, #49 channel trims, #50 onboarding.
- **#47 Side-by-side Compare (DONE):** '🔬 Compare Looks' — '➕ Add current' snapshots imgC into up to 4 slots
  shown side by side with labels + ×; click a slot to re-apply that look. Client-only, no restart. C-tier
  remaining: #48 auto-levels, #49 channel trims, #50 onboarding (+ TGA auto-protect swarm in flight).
- **#48 Auto-levels Source (DONE):** engine auto_levels(tex) per-channel percentile stretch (float/uint8, alpha
  preserved, guarded); /generate applies it when the '📊 Auto-levels source paint' toggle is on (both preview
  sizes). Washed-out liveries → richer spec. Engine test PASS (0.4-0.6 → 0-1). Engine+route change → FULL APP
  RESTART. C-tier remaining: #49 channel trims, #50 onboarding (+ TGA auto-protect swarm landing soon).
- **#49 Per-channel Gain Trims (DONE):** engine apply_channel_gain(spec,gm,gr,gcc) scales M/R/Cc (clamped
  0.3-2.0, iron_fix after keeps it legal); collapsible '🎛️ Channel trims' 3 sliders → /generate spec_gain_*.
  Engine test PASS. Engine+route change → FULL APP RESTART (shared w/ #48). C-tier remaining: #50 onboarding
  (+ TGA auto-protect swarm integration pending).
- **#50 Onboarding Empty-state (DONE) — ROADMAP COMPLETE:** friendly '🏎️ No car loaded yet' card with
  'Try an example car' (loads the bundled example PSD) + 'Take the tour'; shows when no paint, auto-hides on
  load. Client-only. **The entire SPECSCULPT_50_ROADMAP (all B/C + 🚀 innovation items) is now ✅.** Focus
  shifts to the owner's TGA auto-protect feature (swarm draft built + self-tested; integrating next).
- **🚀 TGA AUTO-PROTECT (no PSD) — owner headline feature DONE 2026-06-25:** engine
  auto_protect_mask_from_paint(tex) deciphers numbers/sponsors/logos/decals from a FLAT paint and builds a
  best-effort protect mask (so PSD-less buyers get layer-aware sculpting). Fuses standout-edge islands +
  local base-color deviation + extreme-luminance text; hard guards keep busy carbon/flake/candy/polka/camo
  BASES from being mistaken for decals. Swarm-designed+built+vetted (10 agents); applied adversarial fixes
  (patterned-base guard, NaN/range robustness). '🪄 Auto-detect decals (no PSD needed)' toggle → /generate
  auto_protect flag (used when no PSD mask; Mask-refine #24 sliders apply). Synthetic 6/6, 0.18s @2048.
  ENGINE+ROUTE → FULL APP RESTART. Roadmap #51 (🚀 9.5).
- **🚀 Auto-protect PREVIEW + strength dial (DONE 2026-06-25):** new /api/spec-sculpt/auto-protect-preview
  returns a magenta-tinted overlay of the detected decals + protect %; the '🪄 Auto-detect decals' toggle now
  reveals a Detect-strength slider + '👁 Preview' so PSD-less users SEE what gets protected and tune recall.
  /generate respects auto_protect_strength. Route smoke PASS (numbered→8.8%, solid→none, guard 403).
  ENGINE+ROUTE → FULL APP RESTART. Roadmap #52 (🚀 8.6).
- **Auto-Sculpt auto-protects flat paints (DONE 2026-06-25):** the one-click ✨ Auto-Sculpt now auto-enables
  🪄 decal protection when there's NO PSD (and previews what it shields), so novices dropping a flat TGA get
  numbers/sponsors kept flat automatically. Safe (detector no-ops on plain cars). Client-only.
- **Protected-decal finish choice (DONE 2026-06-25):** protected regions (PSD or auto-detected decals) can now
  read as Matte/Satin/Gloss/Wet/Carbon instead of forced dead-matte — real sponsor decals are usually satin.
  Route parses protect_material → apply_sculpt_mask neutral (default matte = legacy, no change); '[Decal finish]'
  dropdown under Mask-refine. Engine test PASS. ENGINE+ROUTE → FULL APP RESTART.
- **Auto-protect across the gallery (DONE 2026-06-25):** the /api/spec-sculpt/batch route (Shokk-the-World 20
  looks + live preview) now honors auto_protect + protect_material — the decal mask is computed once from the
  shared tex and reused for every look, so a flat-paint novice sees protected numbers/sponsors across the whole
  gallery, consistent with generate. Batch smoke 200. ROUTE change → FULL APP RESTART.
- **Auto-protect real-livery validation + busy-base recall fix (DONE 2026-06-25):** validated on the REAL
  example Chevy livery (busy grid + dark panels + decals) — found it bailed (None) and missed decals. Fixed:
  on a busy base (cand_frac>0.34), re-select only the boldest standouts + WHITE-only extremes (dark panels
  aren't decals) + erode thin grid lines, proceed only if sparse else bail. Over-protect matrix still 6/6;
  real livery now catches the white sponsor text (None→~1%), visually confirmed. Colored-numbers-on-busy-base
  remains the honest limit (preview+strength+manual cover it). ENGINE → FULL APP RESTART.
- **New-controls session persistence (DONE 2026-06-25):** auto-levels, auto-detect-decals toggle, detect
  strength, decal finish, and M/R/Cc channel trims now save/restore with the session (were resetting on
  reload). Client-only, no restart. The auto-protect feature suite is now complete + persistent end-to-end.
- **Fresh decal preview on load (DONE 2026-06-25):** loading a new paint (drop/paste/pick) now re-runs the
  auto-protect preview when the toggle is on, so it never shows the previous car's detection. Client-only.
- **OWNER UX feedback batch 1 (DONE 2026-06-25):** Easy Mode was overwhelming. Removed Shimmer + Sculpt-from-
  Words entirely; decluttered Easy Mode (10 power cards + Match-a-Photo now data-advanced-only, hidden via
  'body.easy [data-advanced-only]'); Shokk-the-World now auto-scrolls to its results + has a prominent
  '🎲 Re-roll 20 more' button; Style Gallery expanded 12→28 one-click tiles (all registry-valid). Client-only.
  Open: Series Templates 'don't work' (advanced-mode investigate), Style Blend more blends, Match-a-Photo UX.
- **Style Gallery expanded to 65 one-click tiles (DONE 2026-06-25):** owner wanted ≥50; went 28→65 across all
  families + Designer Fusions, every id registry-validated (no dead tiles), vibe-matched gradients. Client-only.
  (Diagnosis swarm in parallel for Series Templates / Style Blend / Match-a-Photo fixes.)
- **Fixed Series/Theme/Vibe + Style Blend + Match-a-Photo (DONE 2026-06-25, swarm-diagnosed):** root cause of
  'Series don't work' = one-tap looks clicked before the async preset checkboxes loaded → silent no-op. Fixed by
  making applyQuickPresetStack SELF-HEAL (retry until #presetMount loads) + always scheduleLivePreview. Style
  Blend now offers 63 A/B finishes (gallery expansion) + clearer copy; Match-a-Photo rewritten as a clear ①②③.
  Client-only.
- **Color/Tone→Material now GENERATE for real + 32 material types (DONE 2026-06-25):** was a preview island —
  Generate ignored it. Now HUE_MATERIALS 6→32 iron-safe types; /generate parses hue_rules/tone_bands/
  material_base → builds the spec via hue/tone_material_spec; client pushes the map into the main preview +
  arms Generate (state.activeColorMap) + dropdown shows 32 types. ENGINE+ROUTE → FULL APP RESTART.
  Queued: Region Brush cursor+snap, auto-protect detection ↑, FRACTURED finishes + HSB sliders.
- **APPLY AREA box now constrains in TGA/layer workflows (DONE 2026-07-01):** owner's box drew yellow but the
  finish still hit ALL matched pixels. Root cause: rect/lasso commits DO auto-activate the apply area, but
  autoActivateZoneApplyArea bails in LAYER toolbar mode (a rect there is a layer selection) - so TGA/layer
  sessions silently never set zone.useRegion and region_mask never left the client (server intersect was
  already correct). Fix: one-shot draw INTENT armed by the APPLY AREA panel's Box/Lasso buttons
  (source-color-apply-controls.js) honored regardless of toolbar mode + activation now happens BEFORE
  triggerPreviewRender in both rect+lasso commits (first preview used to race the flag) + apply-area-intent
  commits skip maybeAutoTransformLayerSelection. Also: zone pixel note counted mask VALUES not pixels
  (~255x inflation, state-zones getColorStatusText) and _audit/last_render_trace.json now records
  has_region_mask/has_spatial_mask/apply_area_shape_only (the key filter dropped arrays, so the trace could
  never answer "was the box sent?"). Tokens: canvas.js + source-color-apply-controls.js chained
  -spb-applyarea-auto-20260701. Gates: node --check x3, ast.parse, base-scale regression 8/8, sync 5/5 clean.
  JS = reload; trace = FULL RESTART. NOTE: spb_guard_zone_source_color_apply_controls has 11 PRE-EXISTING
  failures at HEAD (half-finished color-selector extraction, apply-area fns are module-only so unaffected);
  fixed its 12th false-trip (comment at html:2340 mentioned the state-zones filename before the script tag).
- **OVERNIGHT UI-VNEXT POLISH RUN (DONE 2026-07-02 00:03-07:30, owner-directed):** modernize look +
  snappier feel, zero behavior change. ALL changes in ONE additive file css/ui-vnext-polish-20260702.css
  (loads LAST, token spb-vnext-20260702h; delete its single <link> to revert the night). SHIPPING BUG
  FOUND+FIXED: the 4 premium-feel css packs (glow/motion/depth/accent 20260613) were never added to
  runtime-sync-manifest.json -> missing from electron-app/server AND every installer since June 13
  (buyers never saw them); manifest fixed, synced (+zone-scroll-emergency drift converged). PERF: retired
  ~18 always-on decorative animation loops (worst: body::before/::after FIXED full-viewport
  mix-blend-mode:screen shimmers, preview-frame showroom sweep, per-section EKG rails in the Zone Popout)
  keeping CTAs/progress/status/wordmark + all body[data-look] opt-in effects; backdrop-filter diet
  (invisible blur behind 0.96-alpha fills on .zone-toolbar + .swatch-group-label = picker-scroll jank fix;
  radius cuts elsewhere). LOOK/FEEL: instant :active press feedback, keyboard-only focus rings
  (!important), modern thin scrollbars, on-brand ::selection, tabular-nums, global color-scheme:dark
  (native selects/autofill dark app-wide), accent-color, entrance fade+settle on toasts/modals/popovers
  (opacity+independent scale, transform-safe), --text-dim 8893ad->96a3c0 legibility floor,
  overscroll-behavior:contain on all main scrollers, user-select:none on controls,
  paint-booth-pro-theme.css got its missing ?v= token. Ledger with per-burst detail + revert cheatsheet:
  UI_VNEXT_OVERNIGHT_20260702.md. JS/DOM/engine/finishes untouched. Reload to see it.
- **ZONE POPOUT SIMPLIFY PASS (DONE 2026-07-04, owner-directed):** Showroom Mode experiment scrapped
  (files deleted, tags/manifest reverted). COLOR section: 12 quick-color pill tabs REMOVED, replaced by
  primary "PICK COLOR FROM CAR" button -> arms eyedropper AUTO-APPLY (canvas.js hook after
  lastEyedropperColor: first click SETS zone color, further clicks ADD multi-colors; disarmed on tool
  switch via setCanvasMode; state window._spbPickFromCarZone). Color-wheel input widened + hex kept;
  Remaining/Everything specials kept; setQuickColor/QUICK_COLORS untouched for compat. TOL row:
  Exact/Tight/Std/Loose preset buttons removed (setTolerancePreset stays). APPLY AREA: starts collapsed
  unless drawn/active, halved paddings, footnote dropped, ON/drawn hint in header. BASE: 🔒 Lock Base
  Color moved inline onto Base Color row (explainer row deleted); HSB rows nowrap + slider flex so reset
  ↺ stays on the slider line. BUG FIX: _spbApplyPickedBaseToZone — bases WITHOUT .swatch now auto-adopt
  their own color via _spbDefaultBaseColorToFinish special-source path (owner: "ANY base should adopt
  unless locked; still not always doing that"). Tokens: canvas -spb-pickfromcar-20260704,
  apply-controls -spb-simplify-20260704. All node --check green, synced 4/4.
- **GAUNTLET ROUND 1 APPLIED (2026-07-04, owner-directed multi-agent run; 19 agents, findings in
  C:\Users\...\tasks\wipvrjusr.output + _gauntlet_20260704/):** (1) ALL 3 ANALYSIS MAPS REPLACED with
  validated v2 cores (flashmap: old model classified pure chrome as DEAD — 6/9 materials wrong, new
  GGX-based core 9/9 + albedo/mask support; materialmap: 5/10 -> 10/10 incl. new satin archetype +
  alpha handling; specstats: median/bimodal-aware labels, engine-calibrated bands, flash verdict —
  18/18 harness). Originals recoverable from git; harnesses in _gauntlet_20260704/. Tokens -v2-20260704.
  (2) TOOL FIXES: selection-move misclick data loss (undo+preview in _clearActivePixelSelection),
  Invert Mask now true complement 255-v (was binarizing feathered masks), Transform Pattern/Base honors
  z.finish zones, Cool/Warm label un-inverted, spatial/ellipse/invert no-zone toasts, guard split
  (image vs zone), Shift+Z ghost hotkey removed from tooltip. (3) SPEED: _LAST_PREVIEW_PAYLOAD.json
  TEMP dump (every preview+render tick!) now opt-in via SPB_CAPTURE_PREVIEW_PAYLOAD=1; compose.py
  dither noise cache (_DitherPlanes, BIT-IDENTICAL proven via np.array_equal, ~3.6x/channel, ~0.5s off
  a 4-zone render). compose.py manually mirrored (engine check-only), hash MATCH; base-scale 8/8 green.
  QUEUED (findings verified, not yet applied): Copy Mask dead-dropdown relocation, Adjust-on-composite
  silent revert guard, transform session clobber, clone aligned fix, Retouch layer-only graying,
  zone_hashes/spec_delta dead payload removal, preview paint re-upload cache, leading-edge debounce,
  gamma LUT, fast_percentile, flame luma reuse, mono spec LRU. Feature builders (torch-mode 92,
  spec-time-machine 88, finish-shootout 85, dead-zone-coach 82, track-pop-tiers 80) running.
- **5 EXPERIMENTAL FEATURES LIVE (2026-07-04 gauntlet round 2, default OFF, Settings -> 🧪 EXPERIMENTS):**
  pit-lane-live (⛽ LIVE->SIM: renders auto-deploy to Documents/iRacing/paint/<car> + sim hot-reload),
  recipe-card-boomerang (recipe card PNGs carry the full recipe steganographically — drag a shared card
  back in to restore the whole build), torchlight-garage (WebGL torch beam over live preview; metallics
  flare, matte stays dead; Canvas2D fallback), blame-the-dial (render-history A/B forensics: names the
  exact dial that changed + per-zone revert), spec-blink-diff (2Hz blink comparator + M/R/Cc heat +
  impact sentences + revert). All modules self-register into window.SPB_EXPERIMENTS, are NO-OPs until
  toggled, individually removable (delete script tag + file). Loader: js/experiments/spb-experiments-loader.js
  (toggles persist, localStorage spb_experiments_enabled). All in manifest, synced 9/9, tags spb-exp-20260704a.
  Full risk notes per feature: _gauntlet_20260704/features_meta.json + the workflow output. Round-2 QA also
  re-audited tools (new finds: clone Alt+click layer-guard bypass, once-per-tool warn throttle = silent
  dead tools, Retouch layer-only menu confusion) — queued with round-1 leftovers.
- **OPENRASTER (.ora) IMPORT LIVE = GIMP/Krita layered import (DONE 2026-07-04, owner request):**
  GIMP guy saving .xcf -> tell him File > Export As > yourcar.ora (layers preserved), then SPB Import PSD
  button (now "Open Layered File", filter .psd,.ora). Implementation: server_routes/ora_import.py — pure
  stdlib (zipfile+ElementTree+PIL) psd_tools-compatible facade (OraImage/OraGroup/OraLayer quack like
  PSDImage: bottom-up iteration, opacity 0-255, bbox, composite(), settable visible) plugged into
  _get_cached_psd (server.py) -> ALL THREE psd routes + entire booth layer system work for .ora untouched.
  18/18 facade tests green (synthetic GIMP-style .ora incl. nested stack, hidden layer, offsets, multiply).
  Also: file-picker filter now accepts comma lists (.psd,.ora — endswith tuple), upload branch accepts
  .ora + temp cleanup covers both. NATIVE .xcf deferred: needs gimpformats pip dep bundled into the
  packaged build (owner decision, post-beta). "OCN" format from the other user = unidentified; likely
  PDN (Paint.NET) / ORA / KRA — ask for a screenshot; Krita exports .ora natively too. FULL RESTART needed.
- **NATIVE GIMP .xcf IMPORT LIVE (DONE 2026-07-04, owner: "full functionality built in"):**
  server_routes/xcf_import.py — psd_tools-compatible facade over the `gimpformats` pip package
  (XcfImage/XcfGroup/XcfLayer; walkTree->reversed for bottom-up parity; opacity 0-1 -> 0-255; doc.render
  for composite with manual-flatten fallback). Plugged into _get_cached_psd beside .ora; extension checks/
  upload/temp-cleanup accept .psd/.ora/.xcf; picker: "Open Layered File — .psd · .xcf · .ora". 18/18 tests
  green on REAL GIMP files (two_layers, layer_groups incl. nested group, testComplexImage 16-bit).
  DEPENDENCY: gimpformats added to requirements.txt + installed in dev env. If missing at runtime,
  XcfSupportMissing surfaces a clean toast steering to GIMP File > Export As > .ora/.psd (no crash).
  ⚠ BETA CHECKLIST: build env MUST `pip install gimpformats` (or -r requirements.txt) before packaging,
  else packaged .xcf import degrades to that message by design. FACT: Photoshop cannot open .xcf; GIMP
  exports .psd natively — so users also have GIMP->psd/ora as no-new-software paths. FULL RESTART needed.
- **SPEC SCALE <1 WHOLE-CANVAS TILING FIXED (DONE 2026-07-05, owner: "this bug KEEPS coming up"):**
  the INDEPENDENT 🔓 Spec Scale post-pass (fires only when spec_scale != base_scale;
  _transform_spec_for_base_controls, shokker_engine_v2.py ~16691) handed the FINISHED zone-shaped spec
  plate to the global placement transform -> scale<1 shrank+tiled the whole plate (hall of mirrors on
  M/R/CC). The 2026-06-17 paint cure never reached the spec limb. FIX: in-zone masked cure + "tile the
  FIELD" upgrade — strong-in-zone source, mean-fill soft/foreign pixels, then tile the zone's own BBOX
  crop phase-aligned across the canvas before transforming, composite back through the SOFT mask (outside
  the zone byte-untouched). Also: _apply_base_transform_to_zone_output now passes zone_mask to the spec
  transform (same latent bug). NEW FAIL-CLOSED GATE: tests/regression_spec_scale_no_whole_canvas_tile_test.py
  (5 tests: outside untouched / no foreign import / still scales finer / guard skips matched scales /
  all-soft fallback) — run it with the base-scale battery on ANY placement/tiling change. 13/13 green;
  visual before/after proof eyeballed (mirrors gone, zone texture uniformly finer). FULL RESTART needed.
- **SPEC PATTERN OVERLAY SCALE-DOWN 10x SPEEDUP (DONE 2026-07-07, owner: "overlays destroy render
  times, ESPECIALLY scaling down to 0.25"):** MEASURED root cause (254-pattern bench, 2048²): top spec
  generators cost 3-5s EACH and _scale_down_spec_pattern ALWAYS generated at full canvas res then
  stride-decimated (cost scale-independent, features aliased); every scale-slider tick = new cache key =
  full regen. FIX (engine/compose.py): scale<1 now generates ONE TILE at canvas×scale res and np.tiles it
  (handles 2D AND (H,W,3) per-channel M/R/CC generator outputs — the 3D case silently fell back at first
  cut!); canvas-res+gather kept as fallback for tile-res-hostile generators. Measured: hexagonal_tiles/
  pvd_coating/prismatic_shatter etc 3.5-4s -> 0.25-0.4s @0.25 (9-11.5x), quality IMPROVED (native-res
  features vs decimation mush — A/B eyeballed). Also _SPEC_PATTERN_ARRAY_CACHE_MAX_ITEMS 12->24 (5-layer
  stack × 3 preview stages = 15 entries thrashed the LRU). NEW GATES in regression_pattern_perf_budget_test:
  tile-res contract + cost-shrinks-with-scale + fallback. NOTE appearance change at spec-scale<1 (crisper,
  phase differs) — intended. PRE-EXISTING failures found in that test file (NOT mine): shokk_fracture 1.68s
  over budget + KeyErrors sparkle_comet/flake_scatter/plasma_turbulence missing from PATTERN_CATALOG (id
  drift, investigate). QUEUED: scale-1.0 overlay cost (3-5s generators) via top-20 optimization list from
  the bench. compose.py mirrored MATCH. FULL RESTART needed.
- **THREE BASE-COLOR/UI REGRESSIONS FIXED (DONE 2026-07-08, owner report):** (1) BASE PICK ADOPT:
  unlocked base picks were setting mode='Use solid color' + one flat swatch hex (2026-06-30 rule) —
  owner: "NOT making the base color THE base I picked (Ghost Graphic)". ALL base picks now adopt via
  _spbDefaultBaseColorToFinish -> "From special: <base>" (the base's own rendered color); 🔒 Lock is
  the opt-out. (2) USE SOURCE PAINT: base_color_mode='source' let art-producing base paint_fns
  (ghost_graphic) OVERWRITE the source colors (repro: 4-hue source rendered gray; gloss was fine).
  Owner semantics: source mode = base contributes SPEC ONLY. compose.py now skips the base paint pass
  in source mode (_source_paint_lock, BOTH compose paths); patterns still draw later on the source
  substrate; HSB sliders still apply. NOTE: pass-through tint bases (candy) also no longer tint in
  source mode — owner-literal "colors remain exactly the same". NEW GATE:
  tests/regression_source_mode_keeps_colors_test.py (gloss + ghost_graphic through build_multi_zone,
  quadrant hue preservation). (3) 2nd-5th BASE OVERLAY HSB sliders inflated: my 2026-07-04 §16 vnext
  CSS flexed ALL popout .hsb-controls — but overlay ones are multi-row CONTAINERS. Rescoped to new
  .spb-base-hsb-row class carried only by the three Base Color H/S/B rows (token spb-vnext-20260708a).
  15/15 batteries green (source-mode 2 + base-scale 8 + spec-scale 5). compose mirrored MATCH.
  FULL RESTART for the engine change; reload for JS/CSS.
- **SPEC OVERLAY CHANNEL-VALUE DRIFT FIXED (DONE 2026-07-08, owner: "spec colors are off, especially
  Metallic — did something change?"):** YES — my 2026-07-07 tile-res scale-down speedup. Statistics-
  dependent spec generators self-normalize PER CALL, so a 512² tile carries different channel means/stds
  than the 2048² generation the old decimate path sampled (measured: spec_laser_etched M +9.9/255,
  R 15.2/255; pvd_coating ~5/255; most patterns <4/255). ONLY affects scale<1 overlays rendered since
  07-07; scale 1.0 never changed. FIX (engine/compose.py): moment-match the tile to canvas-res reference
  stats — _spec_scale_ref_stats cache (keyed WITHOUT scale: one full-res gen per pattern+canvas, shared
  across the whole slider drag; LRU 64, stores only (mean,std) per channel). Post-fix drift: worst
  2.4/255, laser_etched 0.1/255 — sub-visible; tile speedup retained for every tick after the first.
  NEW GATES: tests/regression_spec_scale_value_parity_test.py (drift <2/255 incl. 3-channel M/R/CC case +
  ref-generated-once-per-drag cache contract); the 07-07 tile-contract tests amended to the new contract.
  21/21 battery green. compose mirrored MATCH. FULL RESTART needed.
- **LIVE COLOR PICKING, NO EXTRA STEP (DONE 2026-07-08, owner: "click ON the color = SAVE IT; slide the
  wheel and let go = that's the color; no click-outside-the-box"):** both color wheels (zone COLOR
  colorPickerInput + BASE COLOR solid baseColorPicker) now apply LIVE on `input` (every wheel movement:
  state + preview, deliberately NO panel re-render — a DOM rebuild mid-gesture closes the OS color
  dialog) with ONE undo per gesture (_spbBeginColorGesture) and full commit + refresh on `change`
  (dialog close). The dialog's built-in eyedropper fires the same events -> auto-applies. BONUS: ✓ Apply
  button (now redundant) replaced with 💉 Pick — native EyeDropper API screen picker: click it, click any
  color on the car, base color applies instantly (typeof-guarded with a toast fallback). state-zones is
  no-store; reload only.
- **BETA 8.0.4 PUNCH LIST + FIRST BLOCKER SWEEP (2026-07-08 Wed):** BETA_804_PUNCHLIST.md created — 100
  items (A blockers / B owner click-test matrix / C gauntlet fix queue / D perf queue / E polish / F comms /
  G build+deploy / H deferred-to-8.0.5), target weekend ship. FIRST SWEEP RESULTS: full tests_v2 run found
  28 failures — 23 were PRE-EXISTING since the ~Jun 21-22 color-science rebuild (its generated spec closures
  dropped legacy default args; test probes only knew old conventions). FIXED TEST-SIDE ONLY: _render_mono_spec
  (test_regressions_2026_05) falls back to the live spec_fn(shape, mask, seed, sm) convention on arity
  TypeError; _probe_spec (test_engine_structure_guards) gained the live-convention attempt. 246 passed after.
  Remaining 5 = Codex mid-cycle (test_smart_separate_guided, car_layers.py edited Jul 8 18:57 — suite grew
  83->346 tests; 341 green). Item 2 diagnosed (racing_pivot root=truth, converge gated by spec-sculpt QA);
  item 3 diagnosed (3 spec-pattern ids retired without aliases — saved projects silently skip; aliases next).
- **SOL HANDOFF WRITTEN (2026-07-09):** HANDOFF_SOL_BETA804.md — GPT 5.6 SOL joins for the 8.0.4 push.
  Lanes to avoid 3-agent collisions: SOL = LIVE click-test matrix B16-40 (full expected-behavior contracts
  written per item) + UI fix queue C41-55 (minus engine items) + build/sandbox prep G84-91 (feed flip
  stays owner-gated); Claude = blockers A2/A3/A4/A5 + perf D-queue; Codex = land smart-TGA green + freeze
  Thu EOD. Hard rails encoded: no finish changes, no git commits, 2-copy+manifest+token rituals, engine
  check-only mirror, Codex file ownership, Pit Lane Live only on throwaway folders, wiki logging mandatory.
  SOL reports into SOL_CLICKTEST_RESULTS.md + punch list statuses.

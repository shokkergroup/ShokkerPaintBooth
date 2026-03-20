# ╔══════════════════════════════════════════════════════════════════╗
# ║         SHOKKER PAINT BOOTH — THE BIBLE                         ║
# ║         THE ALPHA AND OMEGA. READ THIS FIRST. ALWAYS.           ║
# ╚══════════════════════════════════════════════════════════════════╝

> **⚠️ MANDATORY FOR ALL AI AGENTS (CURSOR, ANTIGRAVITY, ANY OTHER):**
> Before touching ANY file in this project, read this document top to bottom.
> Before adding ANY finish, pattern, or base, **READ `FINISH_WIRING_CHECKLIST.md` FIRST.**
> Before renaming ANY ID anywhere, check the sync rules in this document.
> This is not optional. Skipping this document WILL cause bugs.

**Last Updated:** 2026-03-08  
**Maintained by:** Antigravity (AI assistant) + Ricky (owner)  
**Location:** `d:\Cursor - Shokker Paint Booth GOLD\Shokker Paint Booth V5\SHOKKER_BIBLE.md`

---

## 📚 TABLE OF CONTENTS

1. [What This Project Is](#1-what-this-project-is)
2. [The Golden Rule — The ID Contract](#2-the-golden-rule--the-id-contract)
3. [Architecture Overview](#3-architecture-overview)
4. [The Two Registries — How Finishes Are Loaded](#4-the-two-registries--how-finishes-are-loaded)
5. [Pattern System Deep Dive](#5-pattern-system-deep-dive)
6. [Base System Deep Dive](#6-base-system-deep-dive)
7. [Post-Incident Reports — What Went Wrong & How We Fixed It](#7-post-incident-reports--what-went-wrong--how-we-fixed-it)
8. [The Checklist — Do This Every Time](#8-the-checklist--do-this-every-time)
9. [Key File Map](#9-key-file-map)
10. [Reference Documents Index](#10-reference-documents-index)

---

## 1. What This Project Is

Shokker Paint Booth V5 is a desktop Electron app for applying custom paint finishes to NASCAR-style race car images. It uses:

- **Electron** (front-end shell) wrapping a Python **Flask server** (backend rendering engine)
- **Canvas-based JS** for live UI previews and swatch thumbnails
- **Python PIL/NumPy** for actual pixel-level render output (TGA/PNG)
- A **dual-registry** system: legacy `shokker_engine_v2.py` + modern `engine/` folder modules

The user applies "finishes" to color zones on a car image. A finish = **Base** (material, e.g. gloss, chrome, carbon) + optional **Pattern** (overlay texture) + optional **Special/Monolithic** (full artistic effect).

---

## 2. The Golden Rule — The ID Contract

### 🚨 THIS IS THE #1 RULE. EVERY BUG WE'VE EVER HAD VIOLATED THIS.

**Every finish ID must exist in ALL of the following places simultaneously:**

| Layer | File | What it controls |
|---|---|---|
| **Python engine registry** | `engine/registry.py` or `shokker_engine_v2.py` | Actual rendering happens here |
| **`paint-booth-0-finish-data.js` — array** | `paint-booth-0-finish-data.js` | **THE ONLY PLACE TO EDIT FINISH DATA** — UI picker shows the item |
| **`paint-booth-0-finish-data.js` — GROUPS** | `paint-booth-0-finish-data.js` | UI categorizes and groups the item |

### File Roles (Updated 2026-03-11)

- **`paint-booth-0-finish-data.js`** — SINGLE SOURCE OF TRUTH for all finish arrays: `BASES`, `PATTERNS`, `MONOLITHICS`, `BASE_GROUPS`, `PATTERN_GROUPS`, `SPECIAL_GROUPS`, `CLR_PALETTE`, `GRADIENT_DEFS`, `PRESETS`. **Edit this file to add/change finishes.**
- **`paint-booth-1-data.js`** — Logic only: TGA decoder, onboarding hints, `_mergeFinishDataFromServer()`. **DO NOT put finish data here.**
- **`_ui_finish_data.js`** — DELETED (was an orphaned duplicate that was never loaded by the app). It no longer exists.

**If an ID exists in the engine but NOT in `paint-booth-0-finish-data.js` → invisible (user can't pick it)**  
**If an ID exists in `paint-booth-0-finish-data.js` but NOT in the engine → picker shows it but renders as fallback (silent failure)**  
**If an ID is in PATTERN_GROUPS but NOT in the PATTERNS array → picker category shows it but has no name/desc/swatch**

### The Law of ID Renaming

**NEVER rename an ID in ONE place without updating ALL three places above.**

When you rename:
```
OLD_ID → NEW_ID
```
You must update:
1. Python engine registration (the dict key)
2. Any `if "old_id" in variant:` string-match checks in dispatcher functions
3. The JS PATTERNS / BASES / MONOLITHICS array entry `{ id: "old_id" ... }`
4. The JS grouping array entries (`PATTERN_GROUPS`, `_SPECIALS_EFFECTS`, etc.)

Run the audit script after every rename: `python C:\tmp\pattern_audit.py`

---

## 3. Architecture Overview

```
paint-booth-v2.html          ← Single HTML entry point
  ├── paint-booth-0-finish-data.js  ← SINGLE SOURCE OF TRUTH: all finish arrays, groups, palettes, presets
  ├── paint-booth-1-data.js  ← TGA decoder, server merge, onboarding logic
  ├── paint-booth-2-state-zones.js  ← Zone state, UI rendering, pickers
  ├── paint-booth-3-canvas.js       ← Canvas drawing, eyedropper, region masks
  ├── paint-booth-4-pattern-renderer.js  ← CLIENT-SIDE swatch preview renderers (JS only)
  ├── paint-booth-5-api-render.js   ← Communicates with Python server for real renders
  └── paint-booth-6-ui-boot.js      ← App initialization, config, toolbar

Python Server (Flask):
  server_v5.py               ← Entry point, routes
  engine/registry.py         ← THE ENGINE SOURCE OF TRUTH — builds all registries
  engine/base_registry_data.py      ← Base PBR data (M/R/CC values)
  engine/expansion_patterns.py     ← Dispatcher for decade/flame/music/astro patterns
  engine/pattern_expansion.py      ← Lists all NEW_PATTERN_IDS for expansion engine
  engine/expansions/               ← ALL expansion satellite modules (consolidated)
    arsenal_24k.py             ← 24K pattern/finish expansion (~625K)
    fusions.py                 ← 150 FUSIONS hybrid materials (~124K)
    paradigm.py                ← Paradigm impossible physics (~107K)
    specials_overhaul.py       ← Dark/Gothic, Effects, Shokk Series (~54K)
    color_monolithics.py       ← 260+ color-changing finishes (~45K)
  shokker_engine_v2.py       ← Legacy engine (~414K, 6.5K lines). Has TABLE OF CONTENTS at top.
  shokker_*.py (root)        ← Backward-compat shims → engine/expansions/
```

### Two Parallel JS Trees (IMPORTANT)

There are **two copies** of the JS files:
- `Shokker Paint Booth V5/electron-app/server/` ← **PRODUCTION** (what the built EXE runs)
- `Shokker Paint Booth V5/` (root) ← **DEVELOPMENT** (what the dev server serves)

**Always edit both or confirm which one is active.** The dev server reads from root; the production EXE reads from `electron-app/server/`. In practice, `npm run dev` / `START_V5_DEV.bat` uses the root copy.

---

## 4. The Two Registries — How Finishes Are Loaded

### Registry 1: Legacy (shokker_engine_v2.py)
- Contains `BASE_REGISTRY`, `PATTERN_REGISTRY`, `MONOLITHIC_REGISTRY`, `FUSION_REGISTRY`
- Loads `shokker_24k_expansion.py` (patterns, paradigm, fusions, etc.)
- Loads `shokker_specials_overhaul.py` (new specials)
- This handles ~95% of all patterns (carbon fiber, chainmail, etc.)

### Registry 2: V5 Engine (engine/registry.py)
- The modern modular registry, delegates to legacy + extends it
- Loads `engine/base_registry_data.py` for base PBR data
- Loads `engine/pattern_expansion.py` → `engine/expansion_patterns.py` for new decade/flame/music/astro patterns
- Loads `engine/color_shift.py` for CS finishes
- Handles image-based patterns (PNG files in `assets/patterns/`)

### How Image-Based Patterns Work
PNG files in `assets/patterns/<category>/<id>.png` are registered in `engine/registry.py` as:
```python
pattern_reg[pid] = {
    "image_path": f"assets/patterns/{cat}/{pid}.png",
    "paint_fn": paint_none,
    "desc": f"Image-based pattern — {pid}",
}
```
The JS PATTERNS entry must have `swatch_image: "/assets/patterns/<cat>/<id>.png"` for the thumbnail.

### How Procedural Expansion Patterns Work (decade_*, flame_*, music_*, astro_*)
These are registered via `engine/pattern_expansion.py` (the ID list) + `engine/expansion_patterns.py` (the actual texture/paint functions). The dispatcher in `expansion_patterns.py` uses **string matching** (`if "keyword" in variant`) — not exact equality. This means:

**When you rename an ID you must also update the keyword checks in `_texture_expansion()` and `_paint_expansion()` in `expansion_patterns.py`.**

---

## 5. Pattern System Deep Dive

### Pattern ID Vocabulary

| Prefix | Registry | Example |
|---|---|---|
| No prefix | Legacy (24k expansion / engine_v2) | `carbon_fiber`, `chainmail` |
| `decade_50s_`, `decade_60s_` etc. | V5 expansion_patterns.py | `decade_50s_starburst` |
| `flame_`, `tribal_flame_` | V5 expansion_patterns.py | `long_flame_sweep` |
| `music_`, `astro_`, `hero_` | V5 expansion_patterns.py | `music_blues`, `astro_moon_phases` |
| `reactive_` | V5 expansion_patterns.py | `reactive_iridescent_flake` |
| Image IDs (50s/60s/70s/80s/90s) | engine/registry.py image loader | `atomicstarburst_gradient` |
| `shokk_` | Legacy 24k expansion | `shokk_bolt`, `shokk_hex` |

### Decade Groups — Two Parallel Systems

The decades (50s–90s) have **TWO separate sets** that BOTH live in each decade's PATTERN_GROUP:

1. **Image-based** (PNG files): `atomicstarburst_gradient`, `discofever_pure`, `grungehex`, etc.
   - Registered in `engine/registry.py` `_img_pats` list
   - Require the actual PNG file to exist at `assets/patterns/<decade>/<id>.png`

2. **Procedural** (generated): `decade_50s_starburst`, `decade_70s_disco`, `decade_90s_grunge`, etc.
   - Registered in `engine/pattern_expansion.py` `NEW_PATTERN_IDS` list
   - Dispatched through `engine/expansion_patterns.py`
   - No image file needed — generated by numpy math

**Both types must have JS PATTERNS array entries AND appear in the PATTERN_GROUPS for their decade.**

### Reactive Shimmer Patterns
The `reactive_*` patterns (10 total) are designed specifically for **Pattern-Reactive** and **Pattern-Pop** blend modes. They generate gradient masks 0.0→1.0 that drive specular interplay between two bases. They're registered in `pattern_expansion.py` and rendered via `_texture_reactive()` + `_reactive_*()` functions in `expansion_patterns.py`.

---

## 6. Base System Deep Dive

### Base PBR Values
All base PBR data lives in `engine/base_registry_data.py`. Format:
```python
"base_id": {
    "spec_fn": spec_function,
    "paint_fn": paint_function,
    "M": 0.0–1.0,    # Metallic
    "R": 0.0–1.0,    # Roughness  
    "CC": 0–255,     # Clearcoat
    "desc": "...",
}
```

### PBR Physics Rules (Non-Negotiable)
- **Matte finishes**: CC = 0, R = 0.7–0.9, M = 0.0
- **Gloss finishes**: CC = 240–255, R = 0.05–0.15, M = 0.0
- **Chrome/Mirror**: M = 1.0, R = 0.0–0.05, CC = 255
- **Satin**: CC = 80–140, R = 0.3–0.5
- **Metallic paint** (not chrome): M = 0.6–0.9, R = 0.15–0.4, CC = 200–240
- **Carbon fiber**: M = 0.05–0.15, R = 0.1–0.2, CC = 200–220

Full audited base values: See `BASE_AUDIT_2026-03-08.md`

### Base Categories
See `paint-booth-0-finish-data.js` `CATEGORIES` array and `BASES` array for all registered bases.  
See `engine/base_registry_data.py` for PBR data.  
Any base in JS but not in base_registry_data.py renders as fallback gloss.

---

## 7. Post-Incident Reports — What Went Wrong & How We Fixed It

### 🔴 INCIDENT 2026-03-08: Pattern ID Rename Desync (Cursor)

**What happened:**  
Cursor performed a "pattern audit" session and renamed several IDs in the Python engine files without updating the corresponding JS data file. It also added 50 new `decade_*` procedural patterns to the engine without adding them to the JS at all.

**Specific breaks:**

| Old ID (left in JS) | New ID (Cursor used in engine) | Effect |
|---|---|---|
| `music_star_burst` | `music_blues` | Fallback render |
| `music_circle_ring` | `music_strat` | Fallback render |
| `music_slash_bold` | `music_the_artist` | Fallback render |
| `music_chain_heavy` | `music_smilevana` | Fallback render |
| `music_flame_ribbon` | `music_licked` | Fallback render |
| `astro_cosmic_dust` | `astro_nebula_drift` | Fallback render |
| (50 `decade_*` IDs) | Added to engine only | Invisible to UI |
| (10 `reactive_*` IDs) | In PATTERN_GROUPS | No PATTERNS entry |
| `tweed_weave`, `burlap`, `coral_reef` | In PATTERN_GROUPS | No PATTERNS entry |

**Secondary break:**  
`expansion_patterns.py` still had `if "music_star_burst" in variant:` checks — the old string keywords — so even properly renamed IDs would have still hit the fallback dispatcher.

**Fix applied (Antigravity, 2026-03-08):**
1. Updated finish data JS — renamed 6 IDs in PATTERNS array and PATTERN_GROUPS
2. Added all 50 `decade_*` IDs to PATTERNS array with names/descs/swatches
3. Added all 10 `reactive_*` IDs to PATTERNS array
4. Added `tweed_weave`, `burlap`, `coral_reef` to PATTERNS array
5. Updated decade PATTERN_GROUPS to include the new procedural IDs alongside image-based ones
6. Updated `expansion_patterns.py` to recognize BOTH old and new name keywords in all dispatchers

**Audit tool:** `C:\tmp\pattern_audit.py` — Run this after any pattern changes.

---

### 🔴 INCIDENT 2026-03-04: Swatch Rendering Uniform Silver/Gray

**What happened:**  
Base renders were appearing as uniform silver/gray with no contrast. The PBR values for many bases were wrong (e.g., matte bases had CC=240 which is gloss-level clearcoat).

**Fix:** Full PBR audit of all bases in `engine/base_registry_data.py`.  
**Reference:** `BASE_AUDIT_2026-03-08.md`

---

### 🔴 INCIDENT 2026-03-10: snake_skin_2/3/4 — No Thumbnails, No Renders

**What happened:**
Three new snake skin pattern variations were added across **6 out of 7 wiring points** — JS data arrays, JS group arrays, JS pattern renderers, PBR channel hints — but the **Python engine `PATTERN_REGISTRY`** was never updated. The patterns appeared in the picker but rendered as gray placeholders and produced no visible pattern on render.

**Root cause:**
The previous session treated `patternFns` in `paint-booth-4-pattern-renderer.js` as the main renderer. It is NOT — it's a cosmetic client-side fallback. The **actual rendering** goes through `shokker_engine_v2.py` → `PATTERN_REGISTRY` → `texture_fn` + `paint_fn`. The server's `/api/swatch/pattern/{id}` endpoint checks `engine.PATTERN_REGISTRY` at line 967 of `server.py`. If the ID isn't there, no thumbnail and no render.

**Fix:** Added `snake_skin_2`, `snake_skin_3`, `snake_skin_4` to `PATTERN_REGISTRY` in `shokker_engine_v2.py` line ~3489.

**Prevention:** Created `FINISH_WIRING_CHECKLIST.md` — a comprehensive 7-point (patterns) / 6-point (bases) checklist that documents every wiring location with what-breaks-if-missing for each.

**Time wasted:** Multiple debugging sessions across 3 conversations.

---

### 🔴 INCIDENT 2026-02-25: Paint Bases Not Applying (Only Spec Changes Visible)

**What happened:**  
Paint functions weren't being called — only the spec map was changing. Root cause was a broken pipeline call order in the V5 engine migration.

**Fix:** Restored correct pipeline order in `engine/render.py` and `engine/pipeline.py`.  
**Reference:** KI `shokker_paint_booth_engine` → `rendering/color_shift_overhaul.md`

---

## 8. The Checklist — Do This Every Time

> ### 🚨 THE FULL CHECKLIST IS IN `FINISH_WIRING_CHECKLIST.md`
>
> **READ THAT FILE.** It has the complete 7-point pattern / 6-point base /
> 5-point monolithic wiring list, copy-paste templates, an architecture
> diagram, a diagnostic table, and an incident log.
>
> The summary below is a quick reminder. **DO NOT use this summary as the
> only reference — use `FINISH_WIRING_CHECKLIST.md` for the full details.**

### Quick Summary — Pattern (5 points):
1. `shokker_engine_v2.py` → `PATTERN_REGISTRY` **(MOST CRITICAL — actual rendering)**
2. `paint-booth-0-finish-data.js` → `PATTERNS` array (UI picker)
3. `paint-booth-0-finish-data.js` → `PATTERN_GROUPS` (category grouping)
4. `paint-booth-4-pattern-renderer.js` → `patternFns` (client-side preview)
5. `paint-booth-5-api-render.js` → `channelHints` (PBR hover text)
+ Sync JS to `electron-app/server/` + restart server + verify

### Quick Summary — Base (4 points):
1. `engine/base_registry_data.py` → `BASE_REGISTRY` **(MOST CRITICAL)**
2. `paint-booth-0-finish-data.js` → `BASES` array
3. `paint-booth-0-finish-data.js` → `BASE_GROUPS` / `CATEGORIES`
4. `paint-booth-5-api-render.js` → `channelHints`
+ Sync + restart + verify

### Before Renaming ANY ID:
- [ ] Search entire codebase for the old ID string before touching anything
- [ ] Update ALL 7 (pattern) or 6 (base) wiring points
- [ ] Run audit tool: `python C:\tmp\pattern_audit.py`

### After Any Session:
- [ ] Test in the running app — picker → category → thumbnail → select → render
- [ ] If thumbnails look wrong: restart server or run `python rebuild_thumbnails.py`

---

## 9. Key File Map

### The Most Dangerous Files (Most Likely to Desync)

| File | What it controls | Risk |
|---|---|---|
| **`paint-booth-0-finish-data.js`** | **THE ONE SOURCE OF TRUTH — all finish arrays and groups** | 🔴 HIGH — edit ONLY this file to add/change finishes |
| `paint-booth-1-data.js` | TGA decode, server merge, startup logic (NO finish data) | 🟡 MEDIUM — do NOT add BASES/PATTERNS here |
| `engine/pattern_expansion.py` | ID list for procedural expansion patterns | 🔴 HIGH — adding here without the JS data file = invisible |
| `engine/expansion_patterns.py` | String-match dispatchers for pattern rendering | 🔴 HIGH — rename without updating = fallback |
| `engine/base_registry_data.py` | PBR values for all bases | 🟡 MEDIUM — wrong values = visual bugs |
| `engine/registry.py` | The main V5 registry builder | 🟡 MEDIUM — load order matters |
| `shokker_engine_v2.py` | Legacy registry (~500K). Most patterns live here. | 🟡 MEDIUM — massive, easy to break |
| `shokker_24k_expansion.py` | Main pattern library (~625K). | 🟡 MEDIUM — do not edit without auditing |

### Sync Command

After editing files in root, sync to Electron prod build:
```
npm run copy-server
```

### Safe Files (Isolated Changes)
- `engine/color_shift.py` — CS finishes only
- `engine/fusions.py` — Fusion finishes only  
- `shokker_specials_overhaul.py` — New specials only
- `paint-booth-4-pattern-renderer.js` — Client-side swatch preview only (doesn't affect actual renders)
- `paint-booth-v2.html` — UI layout only

---

## 10. Reference Documents Index

| Document | What It Covers |
|---|---|
| **`SHOKKER_BIBLE.md`** ← YOU ARE HERE | Master rules, incidents, checklist |
| **`FINISH_WIRING_CHECKLIST.md`** | **THE WIRING BIBLE** — 7-point pattern / 6-point base checklist with templates, diagnostics, architecture diagram, incident log. READ THIS BEFORE ADDING ANY FINISH. |
| **`CURSOR_HANDOFF_2026-03-09.md`** | Direct letter to Cursor — what it broke, what was fixed, the new rules |
| `PROJECT_STRUCTURE.md` | File-by-file breakdown of what each module does |
| `PAINT_BOOTH_V5_STRATEGY.md` | V5 migration strategy, dual-registry rationale |
| `BASE_AUDIT_2026-03-08.md` | Full PBR audit of every base — correct M/R/CC values |
| `WORK_IN_PROGRESS.md` | Active work log — what's done, what's next |
| `MANUAL_PATTERN_AND_BASES_DISCUSSION.md` | Philosophy on pattern design and the manual vs auto approach |
| `CURSOR_TASK_IMAGE_PATTERN_PIPELINE.md` | Spec for image-based pattern pipeline (PNG workflow) |
| `PATTERN_PLACEMENT_DESIGN.md` | How patterns overlay on bases (blend modes, opacity, scale) |
| `AUDIT_STATUS_2026-03-07.md` | Base/special audit status from March 2026 |
| `docs/` folder | Additional technical docs |

### KI Documents (Antigravity Knowledge Items)
These are maintained in Antigravity's memory system and contain distilled research:
- **`shokker_paint_booth_engine`** KI — Architecture, color shift overhaul, dual layer base, pattern pop logic, image-based pattern system, PBR audit, swatch system
- Path: `C:\Users\Ricky's PC\.gemini\antigravity\knowledge\shokker_paint_booth_engine\artifacts\`

---

## Appendix A: Common Fallback Behaviors (How to Diagnose)

| Symptom | Likely Cause | Check |
|---|---|---|
| Pattern shows in picker but renders as flat ripple | ID in JS not in engine OR dispatcher string check doesn't match | Run audit script; check `expansion_patterns.py` |
| Pattern completely missing from picker | ID in engine not in JS PATTERNS array | Run audit script |
| Pattern shows in wrong category or not at all | ID in PATTERNS but not in PATTERN_GROUPS | Run audit script |
| All bases look the same silver/gray | PBR values wrong (CC too high on matte, wrong R/M) | Check `base_registry_data.py` against audit |
| Swatch thumbnail is generic gray square | Missing thumbnail PNG or wrong `swatch_image` path | Run `rebuild_thumbnails.py` |
| Server returns 500 on render | Python exception in finish function | Check `server_log.txt` |
| Render takes 20-30 seconds | GPU fallback to CPU; or too many zones | Normal for complex renders |
| Pattern renders but completely ignores pattern opacity | Pattern intensity control not wired in zone state | Check `paint-booth-2-state-zones.js` zone.patternIntensity |

---

## Appendix B: The Audit Script

Save as `C:\tmp\pattern_audit.py` and run with `python C:\tmp\pattern_audit.py` from the V5 root.

It checks:
- Engine IDs not in JS (invisible patterns)
- JS IDs not in engine (broken/fallback patterns)
- PATTERN_GROUPS IDs not in PATTERNS array (no swatch data)
- JS PATTERNS IDs not in any group (orphaned, uncategorized)
- All `decade_*` IDs specifically

**Run this after every session that touches patterns.**

---

*This document was created 2026-03-08 by Antigravity after the pattern ID desync incident. Update the Post-Incident Reports section whenever a new bug is found and fixed. This document is the contract between all contributors — human and AI — on this project.*

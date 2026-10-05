<!-- ARCHIVED FROM SPB_WIKI.html on 2026-07-19. Content verbatim — nothing rewritten, reordered or removed.
     (Double-encoded UTF-8 from an earlier bad save was repaired with ftfy.fix_encoding; no wording changed.)
     The Living Wiki (SPB_WIKI.html) now carries only current/active material.
     Index: SPB_WIKI_ARCHIVE.md at the repo root. -->

# Let Freedom Ring — Next Big Update (campaign doc, archived)

# 🎆 "Let Freedom Ring" — Next Big Alpha Roadmap & Mindboard

> **Codename:** Let Freedom Ring · **Status:** PLANNING (build starts after 7.0.9 ships) · **Author:** overnight roadmap loop, started 2026-06-09 01:30. This is a *living mind‑board + strategy guide* — a plan of action, a risk map, and a wall of ideas (including deliberately bizarre ones). It gets deeper every loop cycle; see the **Build Log** at the bottom for what each pass added.

## 🧭 North Star

Ship a **patriotic "Let Freedom Ring" content drop** as the marquee feature, while turning SPB into a **must‑buy** with two structural upgrades — **real iRacing template jump‑starts** and a **modern coat of paint on the UI** — and do it as **small weekly add‑on updates that ride the new auto‑updater and DON'T break what already works.** That last clause is the whole game now. We have ~50 alpha buyers and a reputation to rebuild after the pack mess; every weekly drop has to *add* without *regressing*.

**The three pillars + the discipline that holds them up:**

| | Pillar | One‑line goal | Risk if rushed |
|---|--------|---------------|----------------|
| 1 | 🇺🇸 **Let Freedom Ring content** | A new patriotic SPECIAL category — finishes, spec overlays, patterns | Brick the picker for all 2,400 finishes |
| 2 | 🏁 **iRacing templates / Jump Start** | Built‑in liveries + import real templates + single‑zone guest finishes | iRacing IP takedown; wrong‑car masks |
| 3 | 🎨 **UI/UX modernization** | Less clunky, more modern — without rewrites | `!important` war; cache‑token invisibility |
| 0 | 🛡️ **Anti‑breakage doctrine** | Stop "change one thing, break another" | *This is why the others are safe — read it first* |

---

## 🚀 Start Here Monday (the 60‑second version)

**Thesis:** turn SPB into a must‑buy by shipping a knockout patriotic content drop on a **weekly, non‑breaking** cadence — and never break what already works again.

**Build these three, in this order:**
1. **The safety harness FIRST** (~half a day) — `npm run release-check` + `packaged_render_smoke.py` + `spb_what_depends.js`. This ends the "fixed one thing, broke another" cycle, and every week after rides on it. *(Doctrine #0 + Appendix A · Week 1.)*
2. **5–8 procedural "Let Freedom Ring" finishes** — additive new category, zero downloads, renders for every buyer. *(Appendix A · Week 1 + Appendix B math.)*
3. **Jump Start v1 gallery** — wire the dead `LIVERY_TEMPLATES` wall to real seed‑ref zones using the Shokk Trace machinery you ALREADY have. *(Appendix C.)*

**The one rule that prevents all the pain:** **ADD, never mutate** (new file / new block / append‑only) and **`release-check` must be green before every ship — tested in the *packaged build*, not just dev.**

**Aim it at July 4th.** Let Freedom Ring is a holiday gift to the alpha; work the timeline back from Independence Day (see the launch‑plan appendix).

---

## 🗂️ Table of Contents

**Strategy & plan**
- **🧭 North Star** — the goal in one frame
- **🚀 Start Here Monday** — the 3‑step Monday plan
- **🛡️ Doctrine #0 — Stop Breaking Shit** — why we break things + the gate
- **🇺🇸 Pillar 1 — Content Drop** — patriotic finishes, specs, patterns
- **🏁 Pillar 2 — Templates & Jump Start** — built‑in liveries + single‑zone guests
- **🎨 Pillar 3 — UI/UX Modernization** — low‑risk token re‑skin
- **🗓️ Weekly Release Train** — small non‑breaking weekly drops
- **🥊 Competitive Positioning** — where SPB beats the alternatives
- **💎 What Makes It a Must‑Buy** — the 3 threshold features
- **🎆 July‑4 Launch Timeline** — week‑by‑week to Independence Day
- **🚪 First‑Run Onboarding** — the first 60 seconds
- **🧑‍🎨 Guest Builder Program** — community as content engine
- **🧹 Tech‑Debt Paydown** — what to fix, ranked
- **📊 KPIs / Metrics** — what to measure, where to hook
- **✏️ Closing the Editing Gap** — the post‑July‑4 priority

**Appendices (the deep build detail)**
- **🔧 Appendix A** — per‑week file‑level task lists (additive)
- **🧪 Appendix B** — procedural engine math (decorrelated M/R/Cc)
- **📦 Appendix C** — unified template‑pack manifest schema
- **🎨 Appendix D** — `ui-refresh` token table (exact values)
- **⚠️ Appendix E** — per‑pillar risk register

**Idea wall**
- **🤪 Mindboard 1–4** — ~70 ideas (wild → community/money → iRacing/physics → moonshots)
- **📋 Build Log** — the overnight cycle tracker

---

## 🛡️ Doctrine #0 — STOP BREAKING SHIT (read before any pillar)

You flagged this as the thing we *must* do better. Here's the honest root cause and the fix. The breakage isn't random — it's **four coupled mechanisms**, and we already own tools that catch all four; we just don't run them as a gate.

**Why "change one thing, break another" happens:**
1. **Mirror drift.** Root is the source of truth; it's mirrored to `electron-app/server/` (the tree packaged into the installer). Edit a root file, test in dev (reads root → works), ship the build (reads the *stale mirror*) → it breaks **only for buyers**. This was the #1 historical cause — it's literally why Money/Mortal Shokk broke. Fix: `node scripts/sync-runtime-copies.js --write` after edits, and **gate on `--check`** (now enforced — the build hard-fails on drift). *(2026-06-09: the old third mirror `pyserver/_internal` was deleted → this is now a 2-copy system, which removed a whole class of this drift.)*
2. **Dev‑vs‑packaged divergence.** The shipped server is `server_v5.py` (it inherits most routes from `server.py`). Bugs hide in *path/asset resolution* — present at root, stale/missing in the mirror → 404 only when packaged. (Exactly the 4 Sandbox bugs we just fixed.)
3. **Lazy‑load registry order.** `_ensure_expansions_loaded()` re‑wires SHOKK bases on first render; `_spb_apply_wild_specs()` must run LAST or it reverts. Overrides must patch **both** `BASE_REGISTRY` and the engine globals. Stats look right *before* the first render and wrong *after*.
4. **Stale caches.** CSS/JS edits don't reach Electron unless the `?v=` token bumps; Python edits don't take unless `__pycache__` is purged + the server fully restarts. → "I fixed it but it's still broken" loops + false regressions.

**The fix — one command before every weekly ship (all pieces already exist and pass):**

```
npm run release-check    # to be added — wraps the three below, fail-fast:
  1. python -B scripts/preflight.py        # boots server, >=50 routes, 3-copy CODE drift,
                                            #   ?v= tokens resolve, JS parse, finish-data EVALUATES,
                                            #   SPECIALS_SECTIONS -> group dangling-ref check
  2. python -m pytest tests_v2/ -q          # 12 finish-NEUTRAL contracts: sync byte-identity,
                                            #   manifest<->mirror existence, route inheritance
  3. node scripts/sync-runtime-copies.js --check   # drift (engine = report-only, code = blocker)
```

**Three guardrails to BUILD this release (high ROI, low effort):**
- **`scripts/packaged_render_smoke.py`** — spawn `server_v5.py` *from the shipped mirror*, render 1 base + 1 spec overlay to a real `.tga`, assert 200 + non‑dead output. **This is the single gate that would have caught all 4 Sandbox bugs.** Wire it into the prebuild.
- **`scripts/spb_what_depends.js <file>`** — a 5‑second reflex: prints "is it in the sync manifest? (→ `--write`) is it inherited by server_v5? is it in the lazy‑load order? which `?v=` token references it?" So nobody forgets the propagation step.
- **`spb_color_fn_verify.py` for engine‑math edits** — capture pre → change → capture post → prove unrelated finishes are LSB‑identical. The direct defense against "I added one finish and another changed."

**Golden rule for this whole release: ADD, never mutate.** New `const`, new `try/except` block, append‑only array push, new last‑loaded CSS sheet, new engine module. Never touch an existing id, group array, or shared math. Additive changes can't regress what they don't touch.

> ⚠️ **Live debt to clear first:** 26 engine modules are drifted in the mirrors *right now* (e.g. `engine/asset_packs.py`, `owner_review_gradients.py`). Audit + converge them, and consider promoting stable engine modules from `check_only_directories` to writable `files` so `--write` fixes them automatically.

---

## 🇺🇸 Pillar 1 — "Let Freedom Ring" Content Drop

A new **SPECIAL category** (its own section, sibling to *Cultural*) carrying patriotic **finishes + spec‑overlay layers + patterns**. The *Cultural* pack (Rising Sun / Viva Mexico / Union Jacked / Forbidden Dragon) is the exact, proven template.

**The two‑sided contract (every entry needs BOTH sides or it 404s / fails `validateFinishData`):**
- **JS side** (`paint-booth-0-finish-data.js`): a group object → merged into `SPECIAL_GROUPS`; a new `SPECIALS_SECTION_ORDER` entry + `SPECIALS_SECTIONS["Let Freedom Ring"]`; a tile `{id,name,desc,swatch}` in `MONOLITHICS[]` (desc ≥20 chars).
- **Engine side**: a new module `engine/paint_v2/cultural_let_freedom_ring.py` exporting `LET_FREEDOM_RING_MONOLITHICS = { id:(spec_fn, paint_fn) }`, registered with its own `try/except` block in `engine/registry.py` (next to Forbidden Dragon ~line 471). **Cultural monolithics are plain dict entries — no `_spb_apply_*` pass touches them, so they survive the lazy‑load passes. This is the SAFEST possible shape.**

**Decision that de‑risks everything: ship PROCEDURAL‑first.** A from‑scratch patriotic engine (gradients, star fields, stripe corridors, firework bursts — pure math, no image plates) **renders for every buyer with zero downloads** and dodges the "image pack not bundled → blank car" trap entirely. Image plates can come later as a downloadable pack (the asset‑packs‑v1 path) once the procedural core proves out.

**Anti‑laziness mandate (your #1 rule):** NOT one gradient recolored 20 ways. Each finish gets its **own primary geometry** and a **decorrelated M/R/Cc spec triplet** (M = one design, R = signed sheen, Cc = separate corridor, `max|corr| < 0.85`). Verify in a render grid + eyeballs before showing you.

**Concept seeds (finishes):** `lfr_old_glory` (navy star‑field + 13 red/white sheen‑flip stripe corridors) · `lfr_faded_freedom` (sun‑bleached weathered‑flag lacquer w/ road‑grime micro‑grit) · `lfr_liberty_torch` (bronze/gold flame field, verdigris ground) · `lfr_eagle_ascendant` (charcoal‑on‑silver eagle brocade, gold‑linework feathers read as metal) · `lfr_rocket_red_glare` (dark sky + bursting firework starbursts, micro‑flake stars) · `lfr_midnight_militia` (matte OD‑green/tan tactical americana, anisotropic brushed sheen) · `lfr_chrome_glory` (liquid‑chrome stars + brushed‑grain stripes) · `lfr_we_the_people` (aged‑parchment, engraved‑script relief, gold‑leaf flecks).

**Concept seeds (spec overlays — pure procedural, work on ANY base):** `spec_lfr_star_field` (50‑star constellation as low‑roughness pearl glints) · `spec_lfr_stripe_sheen` (13 stripe corridors, alternating signed R so adjacent stripes flip bright/dark) · `spec_lfr_firework_burst` (radial comet‑streak gloss flashes) · `spec_lfr_engraved_eagle` (currency‑style guilloche + eagle relief, minted‑coin reveal).

**Concept seeds (patterns):** `lfr_stars_tiled` (procedural multi‑scale 5‑point star array) · `lfr_stripe_bands` (procedural angled 13‑stripe banding) · `lfr_distressed_flag` (image alpha‑stamp, weathered flag) · `lfr_eagle_crest` (image alpha‑stamp crest — NOT full‑bleed, so it overlays without filling the zone).

**Namespacing:** every id gets `lfr_` (finishes/patterns) or `spec_lfr_` (overlays) — verified collision‑free. Note `grad_patriot`, `faded_glory`, `five_point_star` already exist — do **not** reuse those bare names.

**Open questions for you:** (a) Procedural‑only v1, or image plates too? (b) How many finishes — 20 (Forbidden Dragon size) up to ~50 (Viva)? (c) Own top‑level section vs. a 5th group inside *Cultural*? (d) Any sponsor‑safety constraints on flag/eagle/military imagery? (e) You mentioned **building some via your own image prompting** — that becomes the image‑plate pack feeding `assets/reference_textures/cultural/let_freedom_ring/` + a manifest; we can wire a "prompt → plate → finish" pipeline (see Mindboard).

---

## 🏁 Pillar 2 — iRacing Templates & "Jump Start"

**The big realization: most of this already exists and is disconnected.** We don't need to build a template engine — we need to *wire three half‑systems into one.*

- **Shokk Trace** (`auto-painter.html` + `engine/paint_v2/shokk_trace.py`) **already** imports a real iRacing template and cuts it into named, editable zones via per‑car *seed‑refs*, emitting a `shokk-trace.handoff/0` bundle that `shokkTraceImportZones()` turns into live zones (headless‑verified on the 11‑zone 2026 Chevy Truck).
- **`zone.regionMask`** (per‑pixel spatial mask, RLE‑encoded) is **already honored by the render engine end‑to‑end.** So restricting a finish to a tiny region (a Sprint Car roll bar = ~2% of the UV) is *already supported at the data‑model level.* The only gap is **authoring + shipping** that region.
- The dead weight: `LIVERY_TEMPLATES` (hardcoded JS presets, no geometry), `recipes/*.json` (no wired loader), `psd_templates/*.json` (metadata only). Three half‑systems pretending to be a template library.

**🚨 IP guardrail (non‑negotiable):** iRacing's template ART is **iRacing's IP** — do **not** bundle or host their `.tga`/`.psd` template images. Ship only **derived, non‑infringing data**: per‑car **seed‑ref JSON** (zone names + normalized coords) and zone **region masks** (RLE geometry, no art). The user supplies their own legally‑obtained template — which Shokk Trace already assumes. *Confirm iRacing's redistribution policy before hosting any of their images; default to "user brings the template."*

**Plan:**
- **Jump Start v1 (ship‑safe, no IP risk):** turn the dead `LIVERY_TEMPLATES` wall into a real **"Pick your car" gallery** backed by *template packs = seed‑ref JSON only*. On pick → run `zones_from_separators()` against the user's own loaded template → `shokkTraceImportZones()`. One click → correctly‑named, geometry‑aware zones. Zero new render code.
- **Jump Start v2 (built‑in liveries):** bind a **recipe** (base/pattern/finish/baseColor per named zone) to a `template_id`. After zones import, overlay the recipe by matching zone NAME via the existing `_recipeSnapshotToZones()`. Result: *open app → pick 2026 Chevy Truck → "Patriot Throwback" → render* in three clicks. Pre‑bake the per‑car handoff so the click is a fetch, not a compute.
- **Single‑zone Guest finish (the Sprint Car roll bar):** extend the `guest_designers` manifest with `target_zone` + a baked `region_rle` + `template_id`. On apply, stamp ONE zone whose `regionMask` = that RLE and whose finish = the guest plate. **Reuses `zone.regionMask` — no new render code, just a manifest field + a tiny applier.**
- **Contributor authoring loop (zero new geometry math):** Guest Builder loads the car template, uses the **existing spatial‑include brush** to paint the roll‑bar region, exports the mask via the **existing `encodeRegionMaskRLE()`** + their finish plate = a shippable single‑zone pack.
- **Unify:** collapse `LIVERY_TEMPLATES` + `recipes/` + `psd_templates/` into ONE template‑pack manifest (seed‑ref geometry + recommended zones + optional bound liveries + optional region‑scoped guest finishes), resolved through `asset_packs.py` like Finish Packs. One loader, one schema.

**Guardrail:** every template‑bound asset carries a `template_id`; on load, reuse Shokk Trace's existing `zonemap.fit` verdict (good/weak/mismatch) to **block/warn when the wrong car is loaded** — so a roll‑bar mask never silently lands on the wrong panel. Watch `MAX_ZONES` (warns at 30): built‑in liveries reuse the template's cut zones; single‑zone finishes add a zone only on apply.

---

## 🎨 Pillar 3 — UI/UX Modernization (low‑risk, no rewrites)

The frontend already has a **full semantic design‑token system** (`look-theme-prelude.css :root` — colors, radius, shadow, font, focus, glass tokens) AND wired theme switching (`body.theme-light`, `body[data-look=…]`). That means we can re‑skin **app‑wide by changing token VALUES — zero selector changes, zero specificity war.**

**The trap:** ~5,000 `!important` declarations across a deeply layered override stack, ~1,650+ `getElementById` calls, and the cache‑token gotcha (edits invisible unless `?v=` bumps). So the rules are strict.

**Safe approach — ONE new last‑loaded sheet:**
- Create `css/ui-refresh-20260609.css`, add it as the **FINAL** `<link …?v=ui-refresh-20260609>` in `<head>` (after `zone-scroll-emergency.css`). Last‑in‑cascade wins at equal specificity; you bump exactly one token. (Mirrors how `zone-scroll-emergency.css` was already added.)
- **Re‑skin via token VALUES only** inside `:root` — no specificity battles because every component reads `var(--token)`. Never *rename* a token (inline markup references `--accent-pink`, `--bg-panel`).
- **CSS‑ONLY.** Never rename an id/class, never remove a class JS toggles, never change the **box model** of anything JS measures (`.main-container`, `.left-panel` 226px, the canvas, `#zoneEditorFloat`, anything feeding a `ResizeObserver` — that's the hover‑lock/view‑jump bug class).

**Concrete upgrades:** clean monotonic elevation ramp (panels currently a muddy flat navy) · lift `--text-dim`/`--text-muted` to AA contrast · **calm the accent chaos** (cyan+pink+gold+orange+blue all at once → pick ONE primary + one warm secondary via tokens) · global `:where(...):focus-visible` ring (0 specificity, instant keyboard a11y) · unify radius to the existing tokens · type‑scale tokens for the cramped inline 9–10px micro‑text · flatten the heavy button gradient + drop the jittery hover translate · slimmer slider glow + crisp focus ring · cohesive panel chrome (border + radius + `--shadow-panel`, optional glass on modals) · neutral/translucent ~8px scrollbars (the pink 5px reads cheap) · short (<180ms) micro‑transitions gated under `:not(.fx-off)` · merge `.header` + `.shokker-workbench-strip` into one command‑bar language.

**Lowest‑risk shipping mode:** ship the whole refresh as an **opt‑in `body[data-look="refresh"]`** so it A/Bs against Classic with zero regression, then promote to default once you sign off via the grid‑and‑eyes check.

---

## 🗓️ Proposed Weekly Release Train (small, non‑breaking, auto‑updates)

Each week = one additive drop that passes `release-check` + `packaged_render_smoke`. Order front‑loads the *safety harness* so every later week ships on rails.

- **Week 1 — Harness + the headline tease.** Build `npm run release-check` + `packaged_render_smoke.py` + `spb_what_depends.js`; converge the 26 drifted engine modules. Ship the first **5–8 procedural Let Freedom Ring finishes** (new section, additive). Small, safe, proves the pipeline.
- **Week 2 — Content depth.** Remaining LFR finishes + the **procedural spec‑overlay set** (star field, stripe sheen, firework, engraved eagle) + the LFR pattern lane. Now it's a *real* category.
- **Week 3 — Jump Start v1.** "Pick your car" gallery on seed‑refs → one‑click geometry‑aware zones. Onboard 2–3 cars beyond the Chevy Truck (incl. the Sprint Car so the roll‑bar example is real). No IP art shipped.
- **Week 4 — Guest single‑zone + built‑in liveries.** `target_zone`/`region_rle` in the guest manifest + the applier; 2–3 built‑in LFR liveries bound to `template_id`. The contributor authoring loop.
- **Rolling — UI refresh.** Ship `ui-refresh` as opt‑in `data-look` in Week 1, refine weekly from feedback, promote to default when you bless it.

*(If your own image‑prompted LFR plates are ready, slot an image‑plate pack as a Week‑2/3 downloadable add‑on via asset‑packs‑v1.)*

---

## 🤪 Mindboard — Bizarre / Unique / What‑the‑F*** Ideas (batch 1)

*Pure idea wall. Some are genius, some are insane, some are both. Loop cycles keep adding.*

1. **Photo‑to‑Paint.** Drop in a photo (a sunset, a galaxy, your dog, a Monster can) → extract its palette + texture energy → generate a matching finish + spec. "Paint my car like *this*."
2. **Prompt‑to‑Finish forge.** You already prompt images — bake a built‑in "type a vibe → get a Shokk finish" pipeline (your prompt → plate → auto‑traced spec → registered finish). This *is* how the LFR image plates get made; make it a feature, not a chore.
3. **Telemetry liveries.** Feed a real lap's telemetry (brake zones, throttle, g‑load) → a finish whose intensity *maps to where you push hardest.* A car painted by how you drive.
4. **The Shokk Forge (daily generative challenge).** App posts a daily prompt + constraints; community builds + votes; winner gets featured "Finish of the Day." A reason to open the app *every day*.
5. **Livery DNA marketplace.** Users sell/trade `.spbdrop` recipes. Take a cut. Turns buyers into a supply side. (Guest Builders = the seed of this.)
6. **Hidden‑message paint.** Embed a scannable QR or a steganographic easter egg in the spec map — a secret only visible at a certain angle/zoom. Sponsors would pay for this.
7. **Lenticular finishes that flip the DESIGN, not just color.** Multi‑design spec so the car shows one motif head‑on and a different one in profile.
8. **Team Kit Generator.** Input team colors + a logo → auto‑generate a *coordinated multi‑car set* (lead car bold, support cars subtle variants). League gold.
9. **Era packs.** '70s muscle, '80s synthwave (you already have synthwave bones), '90s CART, gulf/martini throwbacks — one‑click decade aesthetics.
10. **"I'm Feeling Lucky."** One button → a fully‑composed, genuinely‑good random pro paint. For the paralyzed‑by‑choice crowd. Great onboarding + great screenshots.
11. **Track‑aware chrome.** Pre‑bake a track's reflection/lighting into a "chrome that reflects Daytona at night" spec variant. Sells the realism.
12. **Twitch overlay integration.** Chat votes the next finish; `!shokk red` recolors live between sessions. Streamers become your marketing.
13. **Battle‑damage / season‑wear simulator.** A finish that ages — scuffs, sponsor peel, brake dust — dialable from "fresh" to "end of a brutal season."
14. **Co‑op paint room.** Two people edit the same car live (the regionMask + recipe model makes this more feasible than it sounds).
15. **Typography‑to‑livery.** Type a word/number → it wraps the body as a designed graphic element, not a flat decal.
16. **Sponsor‑safe fake‑sponsor packs.** Pre‑cleared fictional sponsor decal sets so cars look "real" without legal risk — a classic sim‑racing want.

---

## 🔧 Appendix A — Per‑Week File‑Level Task Lists (exact files, ADDITIVE only)

*Every item below is a NEW file or an APPEND to an existing one — nothing mutates an existing id, group, or shared math. Each week ends green on `release-check` + `packaged_render_smoke` (and `spb_color_fn_verify` on engine‑math weeks).*

### Week 1 — Safety harness + first 5–8 procedural finishes
**New files:**
- `scripts/packaged_render_smoke.py` — spawn `server_v5.py` from `electron-app/server/` (the shipped mirror), GET `/api/health` + `/api/registry-check` + `/api/finish-data`, render 1 base + 1 spec overlay to a real `.tga`, assert 200 + variance > DEAD_EPS.
- `scripts/spb_what_depends.js` — input a path, print: in sync manifest? inherited by `server_v5`? in lazy‑load order? which `?v=` token references it?
- `engine/paint_v2/cultural_let_freedom_ring.py` — exports `LET_FREEDOM_RING_MONOLITHICS = { id:(spec_fn, paint_fn) }` (procedural, 5–8 finishes).

**Append‑only edits:**
- `package.json` (root) → add `"release-check"` script = `preflight.py` + `pytest tests_v2 -q` + `sync-runtime-copies.js --check`.
- `electron-app/copy-server-assets.js` → after `syncRuntimeCopies({write:true})`, add a `--check` assertion that aborts on managed‑code drift.
- `engine/registry.py` (~line 471, beside Forbidden Dragon) → new `try/except` block: `mono_reg.update(LET_FREEDOM_RING_MONOLITHICS)`.
- `paint-booth-0-finish-data.js` → new `const _SPECIALS_LET_FREEDOM_RING`; add to `Object.assign(SPECIAL_GROUPS,…)` (~1372); new `SPECIALS_SECTION_ORDER` entry + `SPECIALS_SECTIONS["Let Freedom Ring"]`; push tiles into `MONOLITHICS[]`.
- `scripts/runtime-sync-manifest.json` → add `cultural_let_freedom_ring.py` to the `files` list (avoid the forbidden_dragon omission).

**Then:** `node scripts/sync-runtime-copies.js --write` → `--check` → `npm run release-check`. **Also this week:** audit + converge the 26 drifted engine modules.

### Week 2 — Content depth (spec overlays + pattern lane)
**New (optional):** `engine/spec_pattern_families/let_freedom_ring_overlays.py` (if image‑backed) modeled on `ricky_reference_overlays.py`.
**Append‑only:**
- `engine/paint_v2/cultural_let_freedom_ring.py` → add remaining finishes to the dict.
- `engine/spec_patterns.py` → add `lfr_*_spec` functions (procedural = pure math, no assets) + wire each into `SPEC_PATTERN_REGISTRY` (import ~31609, dict entry ~32046).
- `engine/pattern_expansion.py` → `NEW_PATTERNS` entries (`lfr_stars_tiled`, `lfr_stripe_bands`).
- `assets/patterns/let_freedom_ring/*.png` → image patterns (auto‑scanned by `registry.py` 110‑136; zero engine code).
- `paint-booth-0-finish-data.js` → `SPEC_PATTERNS[]` + `SPEC_PATTERN_GROUPS["Let Freedom Ring"]`; `PATTERNS[]` tiles + `PATTERN_GROUPS` lane (**must be grouped or line‑2848 splice drops it**).
- sync‑manifest + `--write`. **Gate adds:** `spb_color_fn_verify` (prove unrelated finishes LSB‑identical) + `overnight_catalog_audit.py --sample`.

### Week 3 — Jump Start v1 (seed‑refs, no IP art)
**New:** `engine/template_packs.py` (clone of `guest_designers.py` scan loop).
**Append‑only:**
- `server.py` → `/api/templates/list` + `/api/templates/load` near the shokk‑trace routes (~6179); `load` runs `zones_from_separators()` → returns a cached `shokk-trace.handoff/0`.
- `paint-booth-6-ui-boot.js` → augment `applyLiveryTemplate()`/`openTemplateLibrary()` into a "Pick your car" gallery that calls `window.shokkTraceImportZones()`.
- `_shokk_trace/seed_refs/*.json` → add 2–3 cars incl. **Sprint Car** (via `seeds-from-labels` OCR).
- All 3 copies (root + 2 mirrors) for `server.py`, the JS, and `shokk_trace.py`. sync‑manifest for the new module.

### Week 4 — Guest single‑zone finishes + built‑in liveries
**Append‑only:**
- `engine/paint_v2/guest_designers.py` → read optional `target_zone` + `region_rle` + `template_id` from the manifest.
- `server_routes/guest_designer_routes.py` → surface region‑scoped entries.
- `paint-booth-2-state-zones.js` → a new applier beside `shokkTraceImportZones()` that stamps ONE masked zone (reuses `decodeResize()`/`regionMask`).
- `recipes/*.json` → add `template_id`; merge fn beside `_recipeSnapshotToZones()` (~5359) in `paint-booth-5-api-render.js`.
- Reuse `zonemap.fit` (good/weak/mismatch) to block/warn on wrong‑car loads.

### Rolling — `ui-refresh` (opt‑in `data-look`)
- **New:** `css/ui-refresh-20260609.css`. **Append:** ONE `<link …?v=ui-refresh-20260609>` as the FINAL stylesheet in `paint-booth-v2.html` `<head>` — **in all 3 copies** of the HTML. Token‑VALUE overrides only; bump the `?v=` on every edit.

### Definition of Done (every week)
✅ `npm run release-check` green · ✅ `packaged_render_smoke.py` green (renders from the *shipped mirror*, not root) · ✅ `sync-runtime-copies.js --check` = no managed‑code drift · ✅ engine‑math weeks: `spb_color_fn_verify` LSB‑identical on the curated high‑traffic finish list · ✅ new ids grepped for collisions · ✅ tested in the **packaged build / Sandbox**, not just dev.

---

## 🧪 Appendix B — Procedural Patriotic Engine Math (decorrelated M/R/Cc)

*How to actually generate the LFR spec triplets so they PASS the decorrelation gate (`max|corr| < 0.85` across M/R/Cc) and your anti‑laziness bar. The killer mistake is a **shared band‑step**: if stars, stripes, and gloss all ride the same mask, the three channels correlate and it reads as "one gradient recolored." The cure is the doctrine: **each channel gets its OWN primary geometry**, anti‑aligned on ≥1 band, with micro‑pins to dodge the flat‑clip trap.*

**Signature (cultural monolithic):** `spec_fn(shape, mask, seed, sm) -> uint8 HxWx4` = `(M, R, Cc, A)`. Build each channel as an independent float field in `[0,1]`, then `np.clip(...*255).astype(uint8)`.

**Universal recipe (apply to every LFR finish):**
1. **Three geometries, never one scaled.** Choose a distinct primary structure per channel.
2. **Anti‑align ≥1 band.** Where M peaks on a band, force R's profile to cross zero or invert on that band (signed sheen).
3. **Cc is a separate corridor.** Give clearcoat its own orientation/structure (a sweep, halo, or vignette) — not the M motif.
4. **Dodge clip<1%.** Never pin an already‑bright channel flat at 255 — add low‑amplitude grain so it isn't a clipped plane.
5. **Verify:** run the corr harness on the rendered plate (require <0.85) + eyeball the 8×8 grid before showing Ricky. Seed all noise off `seed` so it's deterministic.

### ⭐ `spec_lfr_star_field` (stars)
- **M = blobs.** 50‑star canton grid (9 rows alt 6/5). `M = field_floor + Σ_i gauss(center_i, σ)` → bright low‑roughness pearl glints at star cores.
- **R = directional grain (own geometry).** Fine anisotropic brush at angle θ across the whole canton, modulated by low‑freq value noise: `R = 0.5 + amp*sin((x·cosθ + y·sinθ)·f) * noise` — NOT the star disks. Pull R **low at star cores** (mask‑gated) so stars read glossy, but the field grain is unrelated to the blob positions.
- **Cc = boundary corridor.** A soft halo around the constellation envelope (distance‑to‑canton‑edge falloff) + a faint vignette — a third structure entirely.
- *Why it passes:* blobs ⟂ directional grain ⟂ boundary falloff → low pairwise corr by construction.

### 🟥 `spec_lfr_stripe_sheen` (13 stripes — the correlation TRAP)
- **M = smooth band.** `M = 0.5 + 0.4*sin(2π·stripe_idx/period)` — gentle metallic undulation across 13 stripes.
- **R = SIGNED square, phase‑shifted.** `R = 0.5 + 0.45*sign(sin(2π·stripe_idx/period + φ))` with `φ≈π/2` so adjacent stripes flip glossy/matte AND R is anti‑aligned with M on the bands (this is the "anti‑align ≥1 band" rule made literal). Hard square ≠ M's smooth sine → different profile shape on the same frequency kills the correlation.
- **Cc = diagonal sweep.** One broad gloss highlight crossing the stripes at ~30° (`Cc = smoothstep(d_diag)`), a different orientation → decorrelated from the vertical stripe frequency.
- *Key insight:* same spatial frequency is fine IF the **profile shape + phase + orientation differ per channel**. Shared frequency + shared profile = the trap.

### 🎆 `spec_lfr_firework_burst` (radial)
- **M = comet streaks.** Reuse the `sparkle_comet` streak math: `M = Σ_j taper(r)·gauss_perp(angle_j)` — tapered rays from each burst center.
- **R = point sparkles.** A scattered high‑freq sparkle field (Poisson‑disk points), low roughness at sparkle points — point geometry, not rays.
- **Cc = sky glow.** Smooth radial falloff from burst centers (`Cc = 1 - smoothstep(r/R_glow)`) — the third, smooth geometry.
- *Why it passes:* rays ⟂ points ⟂ smooth glow.

### Reusable primitives already in the engine to lean on
`gauss`/blob summation · `sparkle_comet` streaks + sparkle fields (Sparkle Systems family) · `banded_rows`/`chevron_bands` for stripe math · `jeweled_guilloche` for the `spec_lfr_engraved_eagle` currency‑relief overlay · the wild‑spec corr‑harness used for the SHOKK SERIES rebuild (reuse it verbatim as the gate). **Paint side** (`paint_fn`) is independent: it lays the literal red/white/navy color so the spec only carries the *light behavior*, not the color — keeping paint and spec decoupled (so a buyer can recolor and the patriotic sheen still works).

---

## 📦 Appendix C — Unified Template‑Pack Manifest (`shokk-template-pack/1`)

*ONE schema to replace the three half‑systems — `LIVERY_TEMPLATES` (hardcoded JS, no geometry), `recipes/*.json` (no wired loader), `psd_templates/*.json` (metadata only). One loader (`engine/template_packs.py`, modeled on `guest_designers.py`), one source of truth, resolved through `asset_packs.py` like Finish Packs. **Ships ZERO iRacing pixel art** — only derived geometry (seed‑refs + RLE masks), so it's IP‑safe.*

```json
{
  "schema": "shokk-template-pack/1",
  "template_id": "2026-nascar-chevy-truck",
  "display_name": "2026 NASCAR Chevy Truck",
  "iracing_class": "Trucks",
  "geometry": {
    "source": "seedref",                      // existing shokk-trace.seedref/0
    "seed_ref": "2026-nascar-chevy-truck.json", // zone NAMES + NORMALIZED seed coords (no art)
    "uv_size": [2048, 2048],
    "zones": ["Hood","Roof","Cab","Doors","Quarter","Bumper","RollBar", "..."]
  },
  "recommended_zones": ["Hood","Doors","Quarter"],   // from old psd_templates metadata, optional
  "liveries": [                                       // built-in jump-starts (was recipes/*.json)
    {
      "id": "lfr_patriot_throwback",
      "display_name": "Patriot Throwback",
      "credit": "Shokker",
      "zones": {                                      // per NAMED zone: base/pattern/finish/baseColor
        "Hood":   { "finish": "lfr_old_glory",   "baseColor": "#0a3161" },
        "Doors":  { "pattern": "lfr_stripe_bands","baseColor": "#b22234" },
        "Roof":   { "base": "satin_white" }
      }
    }
  ],
  "guest_zone_finishes": [                            // single-zone Guest contributions
    {
      "id": "gd_sprint_rollbar_carbon",
      "designer": "ContributorName",
      "credit_line": "Sprint roll-bar carbon — by ContributorName",
      "target_zone": "RollBar",
      "region_rle": { "width": 2048, "height": 2048, "runs": [/* baked mask, geometry only */] },
      "finish_plate": "gd_sprint_rollbar_carbon.png",  // + _metallic.png + _roughness.png (whole-finish art)
      "template_id": "2026-nascar-sprint-car"          // binds the mask to ITS car
    }
  ]
}
```

**Field roles:**
- `geometry.seed_ref` — the ONLY geometry input; feeds the existing `zones_from_separators()` → `shokk-trace.handoff/0` → `window.shokkTraceImportZones()`. No iRacing image needed; user supplies their own template.
- `liveries[].zones` — exactly the `recipes/*.json` shape; applied after zone import by matching zone **NAME** via the existing `_recipeSnapshotToZones()`. (Migration: every current `recipes/*.json` becomes one `liveries[]` entry + a `template_id`.)
- `guest_zone_finishes[].region_rle` — the same `{width,height,runs}` RLE the engine already decodes (`decodeResize()`); the *application* is masked to ~2% of the car while the finish art stays whole‑finish. Authored with the existing spatial‑include brush + `encodeRegionMaskRLE()`.

**The guard (prevents the wrong‑car‑mask bug):** every `livery` and `guest_zone_finish` carries a `template_id`. On apply, reuse Shokk Trace's existing `zonemap.fit` verdict — **good** → apply, **weak** → apply + warn, **mismatch** → block with "this is built for the {X} template." A 2% roll‑bar mask never silently lands on the wrong panel.

**Loader contract:** `engine/template_packs.py` scans `assets/reference_textures/template_packs/<template_id>/manifest.json` (bundled‑else‑download via `resolve_ref_dir`); a new `/api/templates/{list,load}` surfaces them; the JS gallery replaces the dead `LIVERY_TEMPLATES` wall. `MAX_ZONES` safety: liveries reuse the template's cut zones; guest finishes add a zone only on apply.

---

## 🎨 Appendix D — `ui-refresh` Token Table (exact `:root` values)

*The whole modern skin is **token‑VALUE overrides only** — no selectors, no IDs, no box‑model. Ships as opt‑in `body[data-look="refresh"]` so it A/Bs against Classic with zero regression, then promotes to default when Ricky blesses it via the grid‑and‑eyes check. All of this goes in `css/ui-refresh-20260609.css` (loaded LAST, fresh `?v=` token). Values are a starting proposal — tune in the live render.*

### Elevation ramp — monotonic luminance ladder (panels currently read as a flat muddy navy)
| Token | Current | → Proposed | Why |
|-------|---------|-----------|-----|
| `--bg-dark` | `#080818` | `#0a0e17` | cleaner near‑black navy, less purple cast |
| `--bg-secondary` | (close to dark) | `#10151f` | step 2 |
| `--bg-tertiary` | — | `#161c28` | step 3 |
| `--bg-card` | muddy | `#1b2230` | cards read as a real raised surface |
| `--bg-hover` | — | `#232c3d` | clear hover lift |
| `--border-subtle` | mixed | `#26304360` | one translucent border for all chrome |

*Each step ≈ +6–8 luminance → surfaces visibly stack instead of blending.*

### Text contrast — lift dim/muted to ~AA on dark
| Token | Current | → Proposed | Contrast |
|-------|---------|-----------|----------|
| `--text-bright` | `#eaf2ff` | keep | headings |
| `--text` (body) | varies | `#cdd6e6` | primary body |
| `--text-dim` | `#7080a0` | `#97a6c2` | now AA‑legible |
| `--text-muted` | `#606078` | `#828cab` | labels/meta no longer mud |

### Accent — ONE primary + ONE warm secondary (kill the rainbow)
| Token | Current | → Proposed | Role |
|-------|---------|-----------|------|
| `--accent` (primary) | `#ff3366` pink | `#00e5ff` cyan | buttons, sliders, focus — the brand note |
| `--accent-warm` (secondary) | scattered | `#E87A20` Shokker orange | primary CTAs / "go" actions only |
| `--accent-pink` / `-gold` / `-blue` | used app‑wide | demote → rare highlight only | stop the cyan+pink+gold+orange+blue cacophony |
| `--focus-ring-strong` | per‑component | `#00e5ffcc` | one global `:where(...)`:focus-visible ring |

*(Primary‑accent choice is the one real judgment call — cyan = current brand‑doc note; orange = splash/installer identity. Opt‑in `data-look` means you decide live, no risk.)*

### Radius — repoint controls/cards to the existing tokens (rules currently hardcode 6/7/8 ad hoc)
| Token | Current | → Proposed |
|-------|---------|-----------|
| `--radius-sm` | `4px` | `6px` |
| `--radius-md` | `8px` | `10px` |
| `--radius-lg` | `14px` | `16px` |

### Type scale — replace the cramped inline 9–10px micro‑text
| New token | Value | Use |
|-----------|-------|-----|
| `--fs-xs` | `11px` | meta/badges |
| `--fs-sm` | `12.5px` | secondary labels |
| `--fs-base` | `14px` | body / controls |
| `--fs-md` | `15.5px` | panel headers |
| `--fs-lg` | `18px` | section titles |
| `--fs-xl` | `23px` | page titles |
| `--space-1..6` | `4·8·12·16·24·32` | one spacing rhythm |

**Motion:** new transitions ≤180ms on `color/box-shadow/transform` only, gated under `:not(.fx-off)` + `@media (prefers-reduced-motion: no-preference)`. **Never** touch widths/heights/padding of `.main-container`, `.left-panel` (226px), the canvas, or `#zoneEditorFloat` (ResizeObserver math). Mirror the new `<link>` across all 3 copies of `paint-booth-v2.html`.

---

## ⚠️ Appendix E — Risk Register (per pillar)

*Every risk has an **early‑warning signal** — the thing to watch for that means it's happening, so we catch it before a buyer does. L/I = Likelihood / Impact (H/M/L).*

### Pillar 1 — Content
| Risk | L | I | Mitigation | Early‑warning |
|------|---|---|-----------|---------------|
| Brick the picker for all ~2,400 finishes (syntax err / phantom id in shared single‑source file) | M | H | Additive only; run `validateFinishData`; `lfr_` prefix | Picker renders nothing; `validateFinishData` console error |
| id collision (`grad_patriot`/`faded_glory`/`five_point_star` exist) | L | M | Namespace every id `lfr_`/`spec_lfr_`; grep before commit | Duplicate‑name validation failure |
| Image plates not bundled → blank car for buyers | M | M | **Ship procedural‑first** (zero assets) | Finish renders blank ONLY in packaged build |
| Lazy / one‑gradient‑recolored (violates #1 rule) | M | M | Own geometry per finish + decorrelated M/R/Cc (`<0.85`) + eyeball | Corr harness `>0.85`; "this looks lazy" |

### Pillar 2 — Templates / Jump Start
| Risk | L | I | Mitigation | Early‑warning |
|------|---|---|-----------|---------------|
| iRacing IP takedown (redistributing their template art) | M | H | Ship ONLY seed‑refs + RLE masks (derived geometry); user brings the template | Any iRacing pixel art inside a pack |
| Wrong‑car mask drift (2% roll‑bar lands off‑panel) | H | M | `template_id` binding + `zonemap.fit` block/warn; author mask at full 2048 res | Mask visibly off the intended panel |
| 3‑copy drift on new template/zone code | H | H | Apply to all 3 copies + manifest + **packaged** test | Works in dev, breaks packaged |
| Building UI on the dead half‑systems (recipes/psd have no loader) | M | L | Treat as import‑only until unified manifest exists | Gallery wired to a loader that returns nothing |
| `MAX_ZONES` blow‑out (templates cut ~11 + guest sub‑zones) | M | M | Liveries reuse cut zones; guest finishes add a zone only on apply | `addZone` warning at 30 zones |

### Pillar 3 — UI/UX
| Risk | L | I | Mitigation | Early‑warning |
|------|---|---|-----------|---------------|
| `!important` war (new rules silently lose) | H | M | Token‑VALUE overrides; last‑loaded sheet; match base `!important` | Edit has zero visible effect |
| Cache token not bumped → edits invisible | H | M | Fresh `?v=` per edit; new tokened filename | "No change" on reload |
| Touch an id / state class → JS breaks | M | H | CSS‑only; never rename/remove a class JS toggles | A control stops responding |
| Box‑model change → hover‑lock / view‑jump | M | H | Visual props only; leave measured nodes (`.left-panel` 226px, canvas, `#zoneEditorFloat`) | Panes jump on hover |
| Edited the wrong copy of `paint-booth-v2.html` (3 exist) | M | M | Confirm which `server_v5` serves; edit all 3 | Edit has no effect |

### Pillar 0 — Engineering discipline (the meta‑pillar)
| Risk | L | I | Mitigation | Early‑warning |
|------|---|---|-----------|---------------|
| **3‑copy mirror drift on managed code** (the #1 historical breakage) | H | H | `release-check` gates on `--check`; `copy-server` post‑write `--check` | `--check` reports code drift |
| Engine drift intentionally NOT auto‑fixed (26 drifters live now) | H | H | Audit + converge; promote stable modules to writable `files` | `--check` engine‑drift list grows |
| Lazy‑load ordering revert (wild‑spec reverts on 1st render) | M | H | `_spb_apply_wild_specs()` LAST; patch both registries; post‑render assertion | Finish's `spec_fn` name = fallback after first render |
| `server_v5` route count drops <50 → boot fail | L | H | Route‑inherit test in the gate | Packaged app won't start |
| Build verifies imports but never RENDERS | M | M | `packaged_render_smoke.py` | NaN/dead finish ships clean |
| Manifest omission (new file invisible to sync) | M | M | Add to manifest + a completeness test | File present in dev, absent packaged |

**Top 3 to fear most (H×H):** managed‑code mirror drift · engine drift · template 3‑copy drift. All three are the *same root cause* (the mirror), and all three are killed by making `npm run release-check` non‑optional + the packaged render‑smoke. **Build the harness in Week 1 and most of this register collapses.**

---

## 🤪 Mindboard — Batch 2 (new territory)

*No repeats from Batch 1. Grouped loosely; ⭐ = unusually high upside‑to‑effort.*

**Community / social**
1. ⭐ **Garage Walls** — a public profile page per user: their liveries, follower count, likes. Turns painters into creators with an audience → free retention + word‑of‑mouth.
2. **Remix lineage tree** — every shared `.spbdrop` shows *who built on whose* (a visible remix graph). Credit + viral chains.
3. **Gift‑a‑livery** — finish a car and send it to a friend's account, gift‑wrapped. Built‑in referral.

**Monetization / business model**
4. ⭐ **Shokker Pro tier** — free core stays generous; Pro unlocks premium packs, the marketplace, and priority generative jobs. Recurring revenue without paywalling the thing they fell in love with.
5. **Finish bounties** — leagues/teams post "paint this, $X budget"; Guest Builders bid. Shokker takes a cut. Turns the Guest program into a gig economy.
6. **Seasonal pack drops (battle‑pass energy)** — a new themed pack every month (Let Freedom Ring is literally the template). FOMO + a reason to keep the sub.
7. **White‑label for leagues/teams** — their branded paint tool, their roster of cars pre‑loaded. B2B revenue, zero acquisition cost.

**Generative / AI**
8. **"Describe your sponsor → livery"** — text prompt → a full coordinated design with believable sponsor blocking that respects iRacing UV safe areas.
9. ⭐ **AI Finish Critic** — scores a paint on *readability at speed*, contrast, realism, and brand cohesion, then suggests one concrete fix. Teaches taste; reduces "why does mine look bad."
10. **Real‑car style transfer** — drop a photo of any real race car → adapt its *design language* (not a copy) onto your iRacing car.

**Gamification**
11. **Achievements + paint streaks** — badges (used every category, painted 100 cars), a daily‑paint streak. Cheap dopamine, real retention.
12. **Shokk Forge leaderboards** — the daily challenge (Batch 1 #4) gets weekly winners, a hall of fame, and a "champion's pack."

**Accessibility (also just good UX)**
13. ⭐ **Readability checker** — simulate the car at track distance/speed + colorblind modes, and flag when your number/sponsor won't read. Solves a real racer pain *and* differentiates from every other tool.
14. **"Explain this finish"** — plain‑language tooltip describing what a spec actually does to the light, for non‑technical buyers (your original "friend who can't use Photoshop" persona).

**Cross‑platform / reach**
15. ⭐ **Web 3D viewer + share links** — a `shokker.gg/c/<id>` link that spins your finished car in 3D in any browser. The single best viral/marketing primitive — every shared car markets the app.
16. **Export to other sims** — translate the spec maps to ACC / LMU / rFactor formats. 10× the addressable market with mostly a remapping layer.
17. **Phone companion** — browse/queue finishes and fire off generative jobs from your phone; they're waiting on desktop when you sit down.

**Data / partnerships / viral**
18. **"What's hot this week"** feed — trending finishes + a usage heatmap of which car parts people paint most (also informs smarter default zones).
19. **Streamer signature packs** — a known painter's official pack with rev‑share; their audience becomes yours.
20. ⭐ **Auto‑reveal clip** — one click generates a slick rotating‑car video/GIF sized for Twitter/Discord/TikTok. Make sharing the default, not a chore.

**Pure bizarre (because you asked)**
21. **Synesthesia mode** — feed it a song; it paints the car from the audio (tempo→pattern density, key→palette, energy→gloss).
22. **The Shokk Oracle** — answer 5 weird questions about your driving "personality"; it designs *your* signature livery.
23. **Cursed Pack** — a deliberately hideous/funny meme pack (clown, dial‑up‑error, "my‑kid‑drew‑this"). The community will make it go viral *for* you.
24. **Livery time capsule** — paints that unlock or visibly change on a future date (a Daytona‑week skin that "ages in" the morning of the race).

---

## 🥊 Competitive Positioning — where SPB wins

*The key reframe: **Trading Paints is distribution; SPB is creation.** They're complementary, not competitors — you make it in SPB, export, and Trading Paints syncs it in‑sim. SPB's real rivals are "hire a painter" and "learn Photoshop," and it beats both on the thing 95% of racers can't do: the spec maps.*

| Capability | **Paint Booth (SPB)** | Trading Paints | Hire a painter | Photoshop DIY |
|------------|----------------------|----------------|----------------|---------------|
| Start from a blank canvas (original art from scratch) | ❌ **you import a base** (TGA min, **PSD preferred**) | ❌ you bring the paint | ✅ | ✅ |
| **Transform / re‑spec an imported paint into looks nobody's seen** (no Photoshop skill) | ✅ ***the whole point*** | ❌ | ⚠️ pay each time | ❌ hard |
| **Spec maps** (metal/rough/clearcoat) handled | ✅ automatic | ❌ | ✅ | ❌ manual + hard |
| Cost | one‑time, low | free / sub | $20–100+ *each* | software + your time |
| Speed to a finished car | **minutes** | n/a (distribution) | days | hours |
| Distribute to others in‑sim | export → TP syncs it | ✅ *its whole job* | n/a | export → TP |
| Precise hands‑on editing (exact logo placement) | ⚠️ weak — *next build* | n/a | ✅ | ✅ full control |
| Learning curve | near‑zero | low | none (you pay) | steep |

**The wedge (corrected 2026-06-09 — SPB is a *transformer*, not a from-scratch art tool):** *"Take a paint you already have and flip it on its head — re‑spec and recolor it into looks nobody's ever seen, including the spec maps everyone else gets wrong, without ever opening Photoshop."* You **import** a base (TGA minimum, **PSD preferred** — PSD's layers/zones unlock the most); SPB's job is the **transformation**, not original art. The moat is the spec maps + insane‑spec authoring — a DIYer can recolor in Photoshop, but metallic/roughness/clearcoat is where their car looks like plastic and yours looks *alive*. **Do NOT market SPB as "make a paint from nothing" — it takes an existing livery and shatters reality with it.**

**Honest weakness (own it, it's the roadmap):** precise freeform editing — exact decal/logo placement, freehand shapes — is thin today. That's literally the "next thing I'm building" you already tell buyers. The single‑zone Guest finishes + better spatial brush (Pillar 2 + the editor work) start closing it.

**Strategic takeaway:** don't fight Trading Paints — *integrate* with it (the more SPB‑made cars on TP, the more SPB markets itself). Position against "I can't paint" and "painting costs me money/time," where SPB is 10× faster and a fraction of the cost.

---

## 💎 What Makes It a MUST‑BUY (the 3 threshold features)

*"Nice‑to‑have" = "I'd use it if it were free." "Must‑buy" = "I saw a friend's car and I NEED this." Three features cross that line — and notably, **all three are already on the Let Freedom Ring roadmap.***

**1. Automatic spec maps — the moat.** Every no‑skill alternative produces *flat plastic* cars. SPB makes cars look **real** — metallic, gloss, clearcoat — with zero skill. *Why it's must‑buy:* it delivers a result (believable light behavior) that is otherwise locked behind expert Photoshop skill or paying a painter. This is the one thing the buyer literally **cannot** get elsewhere at this price. Protect it, lead with it, show it in every screenshot (matte vs. your candy‑metallic, side by side).

**2. Jump‑start → finished car in minutes — kills the blank page.** The #1 reason people bounce off paint tools is *"I don't know where to start."* Open app → pick your car → pick a livery → render → it's in your iRacing folder. Under five minutes, zero to track‑ready. *Why it's must‑buy:* **time‑to‑value is the conversion driver.** A tool that gives a *win in the first 5 minutes* gets bought and kept; one that shows a blank canvas gets refunded. (This is exactly Pillar 2 — and the reason to ship Jump Start v1 early.)

**3. A living library that compounds — auto‑updates + weekly/seasonal/Guest content.** The app they buy today isn't the app they'll have next month: finishes flow in automatically, themed drops land (Let Freedom Ring → era packs → …), and Guest Builders add more. *Why it's must‑buy:* it reframes the purchase from a static product to **buying into a growing thing** — kills buyer's remorse, justifies the price, and the seasonal cadence keeps them opening the app. The new auto‑updater is what makes this *possible*; the content cadence is what makes it *felt*.

**The must‑buy test (use it on every feature):** *Would a racer who sees a friend's SPB car feel they NEED it?* → only if the car looks **real** (#1), they realize they could make one in **minutes** (#2), and it's cheap and **keeps growing** (#3). Everything else is polish.

**The one gap still holding it back from universal must‑buy:** precise hands‑on editing (exact logo/decal placement). It caps the ceiling for *power users* — but the three above already make it a must‑buy for the **95% who can't/won't Photoshop**, which is the whole target market. Close the editing gap *after* the content + jump‑start land.

---

## 🎆 July‑4 Launch Timeline (work back from Independence Day)

*Today = **Tue 2026‑06‑09**. Target = **Sat 2026‑07‑04** (Independence Day). ~3.5 weeks. Each week ships a real, additive, gated increment so the launch build is just "the last green weekly," not a big‑bang risk. **Gate = `release-check` green + Sandbox dress‑rehearsal (the `SPB-CleanTest.wsb` rig).***

| Week | Dates | Build deliverable | Gate (must be green) | Marketing beat |
|------|-------|-------------------|----------------------|----------------|
| **0 — Foundation** | Mon 6/9 → Sun 6/14 | Safety harness (`release-check` + `packaged_render_smoke` + `spb_what_depends`); converge the 26 drifted engine modules; **first 5–8 procedural LFR finishes** (new category) | release-check green; render‑smoke on the new finishes | Quiet tease in Discord: *"something star‑spangled is coming 🇺🇸… 7/4"* |
| **1 — Content depth** | Mon 6/15 → Sun 6/21 | Remaining LFR finishes + the **procedural spec‑overlay set** (star field, stripe sheen, firework, engraved eagle) + the LFR pattern lane | release-check + `spb_color_fn_verify` (unrelated finishes LSB‑identical) | First **beauty‑shot reveal** — one finish (`lfr_old_glory`) rotating; *"this is one of them."* |
| **2 — Jump Start** | Mon 6/22 → Sun 6/28 | **Jump Start v1 gallery** (seed‑ref zones, one‑click) + harden the Sandbox/packaged gate | release-check + **full Sandbox install dress‑rehearsal** | **Zero‑to‑car demo clip** (≤60s): pick car → patriot livery → rendered. *"You'll do this in a minute."* |
| **3 — Polish + arm** | Mon 6/29 → Fri 7/3 | Bug‑bash, opt‑in `ui-refresh` skin, build + sign‑off the **launch build**; stage it on R2 (don't flip latest.yml yet) | release-check + Sandbox + a real end‑to‑end buyer test | **Countdown + auto‑reveal clip** of a *full* patriotic car; *"drops July 4th."* Pin it. |
| **🚀 LAUNCH** | Fri 7/3 eve → Sat 7/4 | Flip `latest.yml` → auto‑update pushes to all installed apps; new Payhip ZIP live | Post‑publish smoke: public URLs 200, a fresh Sandbox install pulls + runs | **Drop:** Payhip + Discord announce + the reveal clip. Kick off **"Paint Your July 4th Car"** community event (post your LFR car → best wins a Pro/Guest perk). |

**Launch‑day checklist (Sat 7/4 AM):**
1. `release-check` green on the launch build · 2. Sandbox install pulls 7.x from R2 + renders an LFR finish · 3. `latest.yml` flipped → confirm an *existing* install sees the update · 4. Payhip ZIP swapped + description/email updated · 5. Discord drop + reveal clip + event post · 6. Watch `#bugs` for 2 hours, hotfix‑ready.

**Slip rule:** if Week 2 (Jump Start) isn't rock‑solid by 6/28, **ship Let Freedom Ring content ALONE on 7/4** (it's the headline anyway) and trail Jump Start the following week. The content is the holiday gift; the templates can follow. Never ship a shaky Jump Start just to hit the date — that's how we got the pack mess.

---

## 🚪 First‑Run Onboarding — the first 60 seconds

*The persona: the friend who can't use Photoshop. Their first 60 seconds decide whether they feel "I can do this!" or "this is too much." The whole goal: **produce something they're proud to screenshot, fast** — because that screenshot is your marketing.*

**Already working in our favor:** the starter Chevy‑truck PSD **auto‑loads on first launch** (the `_spbFetchDefaultAssets` chain). So new users see a *real car*, never a scary blank canvas. Build the onboarding on top of that.

**The Golden Path (3 clicks → a track‑ready car):**
1. **Pick a look** — one prominent action. A "Quick Looks" row (or, once it exists, the Jump Start "pick your car" gallery) where one click applies a great finish to the whole car. No zones, no specs, no decisions.
2. **Render** — the car visibly transforms with real metallic/gloss. *This is the dopamine hit* — the spec‑map moat doing its thing in one click.
3. **Save to iRacing** — it lands in their folder. Done. They made a car in under a minute.

**3 dismissable coachmarks (first launch only, "skip tour" always visible):**
- ① *"👉 Pick a look here"* → highlights the Quick Looks / finish picker.
- ② *"Hit Render to see it on your car"* → highlights the render button.
- ③ *"Save it straight to iRacing"* → highlights save. (Reuse the existing `?v=`‑tokened pattern; coachmarks are additive markup + a `localStorage` "seen" flag — no JS rewiring.)

**What to HIDE on first run** (reveal behind a "Go deeper / Advanced" affordance): per‑zone painting, Spec Sculpt, the Layers panel, Shokk Drop import, base/pattern/overlay stacking. The first session should feel like a **toy that makes cool things**, not a CAD program. Depth is a *reward for engagement*, not a barrier to entry.

**Success metric: Time‑To‑First‑Rendered‑Car (TTFRC).** Target **< 60 s** from first launch. Secondary: **activation rate** = % of first‑session users who render ≥1 car. If TTFRC creeps past ~2 min or activation is low, the onboarding is failing — instrument it (the diagnostics reporter already has a breadcrumb channel to piggyback on).

**Bonus instant‑win lever:** a single **"🎲 Surprise Me"** button on first run that auto‑picks a genuinely good finish + renders in one tap (Mindboard Batch 1 #10). For the paralyzed‑by‑choice newcomer, that's the *fastest* possible path from install to a shareable result.

---

## 🧑‍🎨 Guest Builder Program

*Turns the community into a content engine. The plumbing already exists (`engine/paint_v2/guest_designers.py` + the `guest_designers/<key>/manifest.json` pattern, today shipping only `lyons_designs`) — this is the **process + tooling** to scale it from one designer to many, including the hyper‑specific single‑zone case.*

**① Join** — application or invite. A prospective Guest submits their best finish (paint + spec, or a Shokk Drop `.spbdrop`). Low‑friction but gated: we want quality + iRacing‑appropriate, not volume.

**② Credit / attribution** — every contribution carries `designer_display_name` + `credit_line` (already in the manifest). Their name shows on each tile in the picker (*"by ContributorName"*), grouped under a **Guest Designers** section. Credit is the primary currency for the free tier — clout in the sim‑racing scene is real.

**â‘¢ QA / approval gate (nothing ships unreviewed):**
1. **Render‑smoke** — the finish renders 200 + non‑dead variance (reuse `packaged_render_smoke.py`).
2. **Visual check** — Ricky eyeballs the 8×8 grid against the **owner ship‑bar (≥85)**; AI scores are advisory only (per the spec‑rating doctrine — AI is blind to quality).
3. **IP / name check** — no copyrighted logos/sponsors; unique display name (no `validateFinishData` dup).
4. **Registration** — added to the manifest + the 3‑copy sync + a `release-check` run. *A contribution that skips this is exactly the packaged‑only‑404 bug — so the gate is mandatory.*

**â‘£ Revenue (tiered, optional):**
- **Free tier** — contribute for credit + a Guest badge. Most contributors, zero overhead.
- **Premium designers** — a paid guest pack with a **rev share** (e.g., 70/30 to the designer) or a per‑download bounty. Feeds the **Finish Bounties** model (Mindboard B2 #5): leagues/teams fund a specific paint, a Guest builds it, everyone's paid.

**⑤ The single‑zone pipeline (the Sprint Car roll‑bar case):** a contributor whose finish only fits ~2% of one car contributes cleanly via Appendix C:
1. Load the car template in the editor → use the **existing spatial‑include brush** to paint the roll‑bar region.
2. Export the mask with the **existing `encodeRegionMaskRLE()`** → `{width,height,runs}`.
3. Drop the finish plate (`albedo` + `_metallic` + `_roughness`) + a manifest entry with `target_zone`, `region_rle`, `template_id`.
4. On apply, it stamps **one masked zone** bound to that car (guarded by `zonemap.fit`). No new render code — `zone.regionMask` is already honored.

**Tooling to BUILD (small):** a guided **"Contribute a finish"** flow (wraps the QA steps into a checklist), an **"export sub‑zone finish"** button (wraps steps ⑤.1–⑤.3), and a lightweight reviewer view (grid + accept/reject). Everything else already exists. **Why it matters:** content is the living‑library moat (Must‑Buy #3); Guests make the library grow without Ricky painting every finish himself.

---

## 🤪 Mindboard — Batch 3 (deeper cuts)

*No repeats from B1/B2. New angles: in‑sim integration, finish physics, education, B2B/esports, hardware, seasonal automation.*

**In‑sim / iRacing‑API**
1. ⭐ **Auto‑detect your car & series** — read the iRacing API/registry, pre‑select the right template + car_num slot automatically. Kills the "which car am I painting?" friction entirely.
2. **Schedule‑aware suggestions** — it knows your next race; suggests a livery themed to that track/event ("Daytona this week — try a throwback").
3. **Contingency‑decal auto‑placement** — number + required contingency stickers placed to iRacing's series rules, in the legal spots, automatically.
4. **One‑click to the paint slot** — generate → drop straight into the correct `car_num_<id>.tga` slot; never touch the folder.

**Finish physics tricks**
5. ⭐ **Angle‑true multi‑sun preview** — render the car under several sun angles so you SEE the color‑shift/metallic flip before committing (you already have color‑shift finishes — show them off).
6. **UV‑aware carbon** — anisotropic weave grain auto‑aligned to each panel's flow direction (real carbon follows the part).
7. **Faked‑sculpt liveries** — vents/ducts/gills *implied* purely via spec maps so a flat panel reads as 3D. Free visual depth.
8. **Wear zones** — exhaust/brake areas get a subtly different spec (soot/heat) for built‑in realism.

**Education / tutorials (also sells the moat + cuts support)**
9. ⭐ **"Why does this look real?" toggle** — flip M / R / Cc on and off live to SEE what each spec channel does. Teaches the magic *and* demonstrates the thing competitors can't do.
10. **Paint School** — 5 bite‑size lessons → badges; novices become power users, support tickets drop.
11. **"Steal this look"** — open any finish, see its recipe broken down, learn by remixing.

**B2B / esports**
12. **League field generator** — a league commissions one template → SPB spits out 40 coordinated‑but‑distinct car variants. Huge time‑save, B2B revenue.
13. ⭐ **Broadcast‑safe mode** — high‑contrast, camera‑legible numbers/sponsors validated for stream readability. Esports orgs will pay for this.

**Hardware tie‑ins**
14. **Rig RGB sync** — match your sim‑rig lighting to your car's livery palette.
15. **Stream Deck plugin** — swap finishes / render / save on physical buttons without alt‑tabbing.

**Seasonal / event automation**
16. ⭐ **Holiday auto‑drops** — themed packs auto‑surface around holidays (Let Freedom Ring = July 4, then Halloween, Christmas…) on the seasonal cadence — a calendar that runs itself.
17. **Race‑week reactive packs** — the week of a big real‑world race, surface a matching throwback/tribute pack.
18. **Mileage patina** — pull iRacing miles via API; the car visibly ages the more you drive it. A livery that earns its scars.

---

## 🧹 Tech‑Debt Paydown (prioritized)

*Pay these down opportunistically as the weekly work touches them — don't stop the world for a refactor. Effort S/M/L; payoff is mostly "fewer 3am breakages."*

| Debt | Effort | Payoff | Action |
|------|--------|--------|--------|
| **26 drifted engine modules** (mirrors out of sync, report‑only) | M | ⭐ HIGH — kills the #1 breakage class | Audit the 26; converge to both mirrors; **promote stable modules** from `check_only_directories` → writable `files` so `--write` fixes them. Keep only genuinely owner‑curated finish modules (`money_shokk*`, `rate10`) manual. Do in **Week 1**. |
| **3 half‑template‑systems** (`LIVERY_TEMPLATES` + `recipes/` + `psd_templates/`) | M | ⭐ HIGH — unblocks Jump Start | Unify into `shokk-template-pack/1` (Appendix C); migrate each `recipes/*.json` → a `liveries[]` entry; delete the dead‑loader confusion. Folds into **Pillar 2 / Week 3**. |
| **update‑check.js GitHub poll vs the R2 feed** | S | MED — removes a confusing "no update" banner | Auto‑update is now R2/electron‑updater. Repoint `update-check.js` + the two `github.com/...releases` links to the Payhip/R2 download, OR neuter the manual GitHub banner so it can't contradict the real updater. Quick win. |
| **Cache‑token manual bumping** (`?v=`) | S | MED — ends "I fixed it but it's stale" | Add a build step that hashes each CSS/JS into its `?v=` token automatically; strengthen `preflight` check #4 to assert the token changed when the file did. |
| ~~**Vestigial `pyserver/_internal`**~~ ✅ **DONE 2026-06-09** | — | — | **Cut.** Deleted (~585 MB) + removed from `runtime-sync-manifest.json`; 3-copy → 2-copy; build now hard-fails on drift; contract tests updated + green. (See CHANGELOG 2026-06-09.) |
| **5,000+ `!important` CSS stack** | L | MED — but DON'T big‑bang it | **Freeze growth** (no new `!important`; token‑value discipline per Appendix D); retire dead override sheets opportunistically; never escalate specificity. A full audit is a someday‑project, not now. |

**The leverage move:** items #1 and #4 are the two that actually cause buyer‑facing breakage, and both are **S–M effort**. Knock them out in Week 1 alongside the harness and the recurring "change one thing, break another" pain largely ends. Everything else is housekeeping that can ride along with the weekly cadence.

---

## 📊 KPIs / Metrics to Instrument

*You can't improve what you don't measure — and right now we ship on vibes. A handful of anonymous, **opt‑in** signals would turn "I think people like it" into "activation jumped 12% when we added Jump Start." Hook them onto the existing diagnostics plumbing (`window.__SPB_DIAG` breadcrumb channel + `GET /api/diagnostics`) rather than bolting on a heavy analytics SDK.*

| Metric | What it tells us | Target | Where to hook |
|--------|------------------|--------|---------------|
| **TTFRC** (time‑to‑first‑rendered‑car) | Is onboarding working? | **< 60 s** | breadcrumb: first‑launch → first `/render` success |
| **Activation rate** | % of first sessions that render ≥1 car | **> 70%** | first‑session flag + render event |
| **Save‑to‑iRacing rate** | Do they actually USE the output? | high | the export/save event |
| **WAU** (weekly active) | Retention / health trend | grow WoW | anonymous app‑open ping |
| **Finishes per user / week** | Engagement depth | grow | count render events per anon id |
| **Share rate** | Virality (reveal clips, `.spbdrop`) | grow | share/export‑clip button events |
| **Update‑adoption %** | How fast auto‑updates land | **> 80% in 7 days** | version string on launch ping |
| **Crash / 500 rate** | Stability (the thing that burned us) | ≈ 0 | already captured by `__SPB_DIAG` errors + `/api/diagnostics` 500 tail |

**Implementation note:** the diagnostics reporter already records errors, fetch‑500s, and breadcrumbs locally. Extend it to emit a *tiny, anonymous* event beacon to a counter endpoint (a simple Cloudflare Worker + the R2/D1 you already have, or a privacy‑first analytics service). **Keep it anonymous + opt‑in + aggregate** — no PII, a clear toggle, respect the indie ethos (it's also a trust signal you can market: "we don't spy on your paints").

**The two that matter most right now:** **Activation rate** (is the first session a win?) and **Update‑adoption %** (did the auto‑updater actually replace manual downloads?). Those two validate the entire 7.0.9 + Let Freedom Ring thesis. Instrument them first.

---

## ✏️ Closing the Editing Gap (the post‑July‑4 priority)

*SPB's only real competitive weakness is precise hands‑on editing — the one thing Photoshop still wins. It's literally what you tell buyers ("the hands‑on editing tools aren't where I want them yet — that's the very next thing I'm building"). Let Freedom Ring + Jump Start are the July‑4 headline; **this is the headline AFTER.** Good news: a lot is reusable — the canvas, the layer/overlay system, image import, `zone.regionMask`, and the spatial brush all already exist. The gap is interaction polish, not a new engine.*

**Phase 1 — Precise decal / logo placement** *(the #1 ask)*
- *Reusable:* the image‑import pipeline (Shokk Drop ingests images), the overlay/layer system, `zone.regionMask` for masking.
- *New:* an **interactive transform gizmo** on the canvas — drag / scale / rotate handles, snap‑to‑center/edge, numeric nudge; a per‑decal layer carrying `{x, y, scale, rotation, opacity}`; canvas hit‑testing.
- *Outcome:* "drop my sponsor logo exactly here, this big, at this angle." Closes the most common complaint.

**Phase 2 — Better spatial brush / freeform masking**
- *Reusable:* the existing `spatial-include` / `spatial-exclude` brush (`canvasMode`, `spatialBrushRadius`) + `encodeRegionMaskRLE()` (already round‑trips and is engine‑honored).
- *New:* brush size/hardness UI, per‑stroke undo, **lasso + polygon select**, magic‑wand fill by color region (the `pickerColor`/`pickerTolerance` fields already exist), edge feathering, live mask preview.
- *Outcome:* paint a zone *exactly* where you want, freehand — the precision Photoshop users expect.

**Phase 3 — Spec Sculpt depth (per‑stroke spec authoring)**
- *Reusable:* the Spec Sculpt Lab (paint → spec) already exists.
- *New:* **brush the spec channels directly** — paint M/R/Cc per stroke, gradient tools on the spec, "copy this finish's spec behavior here." For power users who want to hand‑author the light, not just pick it.
- *Outcome:* the ceiling rises from "pick great looks" to "author anything," without ever needing Photoshop.

**Sequencing:** Phase 1 alone closes ~70% of the gap and is mostly a canvas‑interaction layer over things that exist. Do it **right after the July‑4 drop**, instrument the activation/engagement lift (KPIs section), then Phase 2/3 as the data justifies. Keep the additive discipline — these are new tools/layers, not rewrites of the render path.

---

## 🚀 Mindboard — Batch 4 (moonshots)

*The truly weird / big‑swing tier. No repeats from B1–B3. Most are "someday," a few are "sooner than you'd think."*

1. ⭐ **Agentic paint** — describe your dream livery in a sentence; an AI agent designs, renders, iterates, and asks *"more chrome or more matte?"* until you love it. The whole app becomes a conversation. (Your prompt‑to‑finish idea, taken all the way.)
2. **Cinematic reveal films** — not just a rotating clip: a 15‑second auto‑generated reveal (camera moves, lighting, track flyby) per car, sized for socials. Every share is an ad.
3. **AR preview** — point your phone at any surface (or a die‑cast) and see your livery wrapped on a 3D car in AR before you race.
4. ⭐ **VR Paint Booth** — paint your car in VR, walking around it, brushing finishes by hand. The ultimate "no Photoshop" expression of the whole thesis.
5. ⭐ **Physical merch from liveries** — one click turns a finished car into a print‑on‑demand poster, die‑cast, hoodie, or mousepad. New revenue + the buyer becomes a walking billboard.
6. **Cross‑game export** — design once → iRacing + ACC + LMU + (moddable) Forza/GT. One paint, every garage. 10× the market.
7. **Collectible finishes (no blockchain)** — limited numbered runs ("only 100 Founder's Chrome ever"). Scarcity + status via a simple ledger, zero crypto.
8. **Paint by voice** — fully voice‑driven painting for users who can't use a mouse (*"candy red hood, stars on the roof"*). An accessibility moonshot that doubles as a party trick.
9. **"Made in Shokker" certificate** — a verifiable, shareable watermark/cert proving a car's provenance. NFT energy, none of the baggage.
10. **AI Art Director** — drop your team's brand kit (colors, logo, vibe) once; every future car auto‑conforms to your identity.
11. **Community pack vote** — the community votes the next themed pack; top vote gets built. Governance without crypto, engagement for free.
12. ⭐ **"Paint the real car"** — partner with a real race team; fans design liveries, the winner runs on the ACTUAL car at a real event. A PR moonshot that prints headlines.
13. **Generative new categories** — train on the finish library so the engine *invents* finish categories nobody designed; a human curates the best. Infinite content.
14. **Sim‑to‑street** — output a cut‑ready vinyl‑wrap file from your iRacing livery so you can wrap your real car / laptop / helmet to match.
15. **The Shokk API** — open an endpoint so leagues, bots, and other tools generate paints programmatically. The platform play — SPB becomes infrastructure, not just an app.

---

## ✅ The Whole Plan in 5 Sentences

1. Ship a patriotic **"Let Freedom Ring"** content drop — finishes, spec overlays, and patterns, **procedural‑first** so it renders for every buyer with zero downloads — as the **July‑4** headline.
2. Build the **safety harness FIRST** (`release-check` + a packaged render‑smoke) so weekly add‑on updates stop breaking each other — the discipline that fixes the thing that's been hurting us.
3. Turn the three dead template half‑systems into a real **Jump Start** that delivers a finished car in *three clicks*, reusing the **Shokk Trace + `regionMask` machinery already in the codebase** (incl. the single‑zone Guest case).
4. **Modernize the UI** with token‑value‑only overrides (no rewrites), and **instrument activation + update‑adoption** so decisions stop being guesses.
5. Then close the only real competitive gap — **precise hands‑on editing** — and grow the **living library** through Guest Builders, keeping **every change additive** so nothing that works ever breaks again.

> **The throughline:** *additive, gated, weekly.* Add value without mutating what works, gate every ship on `release-check` + Sandbox, and let the auto‑updater carry small wins to everyone — that's how SPB becomes a must‑buy *and* stops setting itself on fire.

---

## 🗣️ Appendix F — Owner Reactions & New Directions (2026-06-09)

*Captured live from Ricky's review of the overnight doc. These reflect what HE wants — they override earlier framing where they conflict.*

### F0. CORRECTION — what SPB actually is
SPB is **not** a from-scratch paint creator. You **import** a finished base (TGA minimum, **PSD preferred** — PSD layers/zones unlock the most), and SPB **transforms** it: recolor, re-spec, flip it into looks nobody's seen. **The selling point is the transformation / insane spec authoring**, not original art. (Competitive Positioning + wedge above are fixed to match. Never market "make a paint from nothing.")

### F1. ⭐ Living / lighting-reactive finishes — the showpiece (HIGH priority for Let Freedom Ring)
Ricky wants finishes that **appear/disappear and change color with the light**, fireworks that "go off," and the holy grail: a finish that makes the car look **3D / living / like it shatters reality** — a 30-second video that trips people's brains. **This is real and it's SPB's superpower** — here's the mechanism:
- iRacing lights the car in **real time** from the **spec map** (R=metallic, G=roughness, B=clearcoat) + the live sun/track lights + camera angle. SPB authors that spec map. So motion in the *lighting/view* drives the effect — we don't animate; iRacing does, for free, as the car turns.
- **Hidden-flare (appear/disappear):** make a motif (stars, eagle, firework burst) **identical to its surroundings in the ALBEDO** (invisible flat / in shade) but **mirror-metallic vs matte in the SPEC**. In diffuse light it's hidden; when the sun hits the right angle it throws a hot specular highlight and the image **flares into view**, then vanishes as the car rotates. (The "engraved/hidden" effect.)
- **Color-shift:** clearcoat + interference treatment so the specular tint flips hue with angle — SPB **already has color-shift finishes**; lean in hard for LFR (Old Glory that shifts red↔white↔blue as it turns).
- **Fireworks bloom:** burst motifs as high-metallic comet streaks on a dark matte sky albedo + a color-shift clearcoat → as the car arcs through a corner under the sun, bursts flare and shift one after another → looks like they're going off.
- **Fake 3D / reality-shatter:** spec gradients that mimic bevels/curvature so flat panels read as sculpted under moving light; stack with hidden-flare + color-shift for the "alive" combo.
- **Honest limit:** it only "moves" when the LIGHT or VIEW changes (car turning, sun, camera) — a parked car in flat light stays still. Perfect for a track/spin/replay video; not a static screenshot. **Engine already has the primitives** (the wild-spec decorrelation work, color-shift, the "angle-reveal structure" in Appendix B) — LFR is where we push them to showpiece level. **Needs a moving-light preview to author (see F3).**

### F2. ⭐ NEW FEATURE — drag-a-finish-onto-an-area (scale/stretch to fit)
Grab any finish in the MAIN app, **drag it onto the source canvas, and drop/stretch it over an exact area** (e.g. a Prism Forge over a truck decklid) — it **scales that finish down to fit the box you drew** (stretch H/V or uniform), and **its spec follows it**. This unifies cleanly with the editing-gap Phase-1 "transform gizmo": the SAME drag/scale/rotate gizmo, but the "stamp" is a **full finish (paint+spec)** instead of a logo. *Build the gizmo once → it works for logos AND finishes.* Under the hood it's: a new zone whose `regionMask` is the dragged box + the finish placed via the existing base-placement/scale system, fit to that box. The render pieces (per-zone finish+spec, region masks, base_scale placement) **already exist** — the new part is the on-canvas drag/resize interaction that creates the box and auto-fits the scale. **This is the most-wanted hands-on feature; slot it into the Editing-Gap Phase 1.**

### F3. Tokens (Appendix D) — clarified
Design tokens are the **app's** paint job, not the cars'. They make the **program UI** modern/cohesive (one named palette/spacing/type set the whole interface reads from); they do **NOT** change how finishes render. The thing that would make **all finishes look better in-app** is a **separate** idea worth doing: upgrade the in-app **preview lighting** (a "preview under moving track sun" toggle) so finishes show their angle-reveal/metallic magic in the app the way they do in iRacing — which is *also* required to author the F1 living finishes. Two different systems; do both.

### F4. Synesthesia mode — how it'd work (attention play)
Ingest a song → analyze tempo/BPM, key (major/minor), energy/loudness, spectral brightness → map to design: tempo→pattern density, key→palette mood, energy→gloss/metallic, brightness→hue → re-spec/recolor the **imported** car to match the song's mood. Low everyday use, **high attention** ("I painted my car with [song]" clip). Cheap to prototype with an audio-analysis lib.

### F5. Community = FREE sharing, growth-first (reframes Mindboard "marketplace")
Goal: grow ~35 buyers + 50 lurkers → **100–125 buyers in a month**, then exponential. Sharing SHOKK DROP recipes / template finishes is a **free community thing** (paid only if a user chooses to sell their own). Discord reality: ~2–3 of 85 active = the normal **90-9-1 rule** (1% create, 9% react, 90% lurk) — don't fight it, **design for lurkers**:
- **One-click "Share" IN the app** → exports a `.spbdrop` + an **auto-reveal clip** (Mindboard B2 #20) → people post to THEIR socials → every share markets SPB (the growth engine).
- **Web 3D viewer + share link** (Mindboard B2 #15) → a non-buyer sees a friend's car spin in a browser, no install → "how'd you make that?" → conversion. This is the single highest-leverage growth primitive.
- **Seed it yourself**: a weekly Shokk Forge challenge / finish-of-the-week gives lurkers something to **react** to (a 👍 / "remix this" is lower friction than posting).
- **Remix culture**: make taking someone's shared finish and tweaking it trivial (credit chain) — creative play, not "posting."

---

## 📋 Build Log (cycle tracker — keeps the loop additive, not repetitive)

| Cycle | When | What was added |
|-------|------|----------------|
| 0 | 2026-06-09 ~02:00 | v1: north star, the 4 pillars (incl. anti‑breakage doctrine), grounded plans w/ real files + risks, weekly release train, Mindboard batch 1. Grounded by a 4‑agent codebase research sweep. |
| 1 | 2026-06-09 ~02:01 | **Appendix A** — per‑week file‑level task lists (exact additive new/edited files for Weeks 1–4 + rolling UI) + a per‑week Definition of Done. Queue item (1) ✓. |
| 2 | 2026-06-09 ~02:18 | **Appendix B** — procedural patriotic engine‑math sketch: decorrelated M/R/Cc recipes for star‑field, stripe‑sheen (the correlation trap + cure), firework‑burst; reusable primitives; paint/spec decoupling. Queue item (2) ✓. |
| 3 | 2026-06-09 ~02:35 | **Appendix C** — unified `shokk-template-pack/1` manifest (full JSON): seed‑ref geometry + bound liveries (ex‑recipes) + single‑zone guest finishes (region_rle) + template_id + zonemap.fit guard; collapses the 3 half‑systems; IP‑safe. Queue item (3) ✓. |
| 4 | 2026-06-09 ~02:52 | **Appendix D** — `ui-refresh` token table: exact before/after `:root` values (elevation ramp, AA text, one primary+warm accent, radius, type/space scale); opt‑in `data-look="refresh"`, token‑value‑only. Queue item (4) ✓. |
| 5 | 2026-06-09 ~03:09 | **Appendix E** — per‑pillar risk register (L×I×mitigation×early‑warning) for Content/Templates/UI/Engineering; identifies the top‑3 H×H risks as one root cause (mirror drift) killed by the Week‑1 harness. Queue item (5) ✓. |
| 6 | 2026-06-09 ~03:26 | **Mindboard Batch 2** — 24 fresh ideas across community/social, monetization (Pro tier, bounties, seasonal drops, white‑label), generative AI, gamification, accessibility (readability checker), cross‑platform (web 3D viewer, other sims), data/viral (auto‑reveal clip). Queue item (7) ✓. |
| 7 | 2026-06-09 ~03:43 | **🚀 Start Here Monday** exec summary placed at top (after North Star): thesis + the 3 things to build in order (harness → procedural finishes → Jump Start v1) + the one rule (ADD never mutate; release-check green) + the July‑4 aim. Queue item (8) ✓. |
| 8 | 2026-06-09 ~03:59 | **🥊 Competitive Positioning** — SPB vs Trading Paints (complementary, not rival) vs hire-a-painter vs Photoshop-DIY; capability table; the spec-map moat is the wedge; own the hands-on-editing weakness; integrate with TP. Queue item (9) ✓. |
| 9 | 2026-06-09 ~04:16 | **💎 Must-Buy thesis** — the 3 threshold features (automatic spec maps = the moat; jump-start = time-to-value; living library = compounding value), the must-buy test, and the one gap (hands-on editing) capping the ceiling. All 3 already on the roadmap. Queue item (10) ✓. |
| 10 | 2026-06-09 ~04:33 | **🎆 July-4 Launch Timeline** — week-by-week (6/9→7/4) build+gate+marketing table, launch-day checklist, and a slip rule (ship content alone if Jump Start isn't solid). Each week gated on release-check + Sandbox. Queue item (11) ✓. |
| 11 | 2026-06-09 ~04:50 | **🚪 First-Run Onboarding** — the 60-second golden path (3 clicks: pick look → render → save), 3 dismissable coachmarks, what to hide, the TTFRC<60s + activation-rate metrics, and the "Surprise Me" instant-win lever. Queue item (12) ✓. |
| 12 | 2026-06-09 ~05:07 | **🧑‍🎨 Guest Builder Program** — join/credit/QA-gate (render-smoke + ≥85 owner check + IP + 3-copy registration)/tiered revenue (free-for-credit vs premium rev-share + bounties)/the single-zone pipeline (brush→encodeRegionMaskRLE→manifest). Queue item (13) ✓. |
| 13 | 2026-06-09 ~05:24 | **🤪 Mindboard Batch 3** — 18 ideas: iRacing-API (auto-detect car, schedule-aware, contingency auto-place), finish physics (multi-sun preview, UV carbon, faked-sculpt), education (M/R/Cc toggle, Paint School), B2B/esports (league field gen, broadcast-safe), hardware (RGB/Stream Deck), seasonal auto-drops + mileage patina. Queue item (14) ✓. |
| 14 | 2026-06-09 ~05:41 | **🧹 Tech-Debt Paydown** — prioritized table (effort×payoff): 26 drifted engine modules, 3 half-template-systems, update-check.js GitHub-vs-R2, cache-token auto-hash, pyserver/_internal cut, !important freeze; leverage = items #1+#4 (S-M effort) end most buyer-facing breakage. Queue item (15) ✓. |
| 15 | 2026-06-09 ~05:58 | **📊 KPIs/Metrics** — instrument table (TTFRC, activation, save-rate, WAU, finishes/user, share, update-adoption, crash rate) hooked to the existing __SPB_DIAG + /api/diagnostics plumbing; anonymous+opt-in; prioritize activation rate + update-adoption to validate the 7.0.9 thesis. Queue item (16) ✓. |
| 16 | 2026-06-09 ~06:15 | **✏️ Editing-Gap plan** — the post-July-4 priority: Phase 1 precise decal/logo placement (transform gizmo, reuses image-import + regionMask), Phase 2 freeform brush/lasso masking (reuses spatial brush + encodeRegionMaskRLE), Phase 3 per-stroke Spec Sculpt; reusable-vs-new per phase; Phase 1 closes ~70%. Queue item (17) ✓. |
| 17 | 2026-06-09 ~06:32 | **🚀 Mindboard Batch 4 (moonshots)** — 15 big swings: agentic paint, cinematic reveals, AR preview, VR paint booth, physical merch, cross-game export, collectibles (no crypto), paint-by-voice, AI art director, paint-the-real-car, generative categories, sim-to-street vinyl, the Shokk API. Queue item (18) ✓. |
| 18 | 2026-06-09 ~06:49 | **🗂️ Table of Contents** (after Start-Here) + **✅ Whole Plan in 5 Sentences** synthesis. Queue item (19) ✓. **DOC COMPLETE** — 24 sections + Appendices A-E + 4 Mindboard batches (~70 ideas). Overnight loop finished. |
| 19 | 2026-06-09 (owner review) | **🗣️ Appendix F — Owner Reactions:** corrected positioning (SPB = transform imported art, NOT from-scratch); added ⭐ living/lighting-reactive finishes (hidden-flare + color-shift + fireworks, the real iRacing-spec mechanism) as HIGH-priority LFR showpiece; added ⭐ drag-a-finish-onto-an-area feature (unify with Editing-Gap Phase 1 gizmo); clarified tokens vs preview-lighting; synesthesia how-to; community = FREE sharing + growth-first (90-9-1, share-clip + web-viewer engine). Also: 3-copy → 2-copy consolidation shipped (see CHANGELOG 2026-06-09). |

> **Next cycles will deepen:** concrete file‑level task lists per week · the procedural patriotic *engine math* sketch (how to actually generate stars/stripes/fireworks decorrelated) · the template‑pack manifest schema · the `ui-refresh` token table (exact values) · more Mindboard batches · a per‑pillar risk register · "definition of done / `release-check` green" per week.

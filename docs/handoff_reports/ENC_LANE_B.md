# Encyclopedia v2 - Lane B report (bases & finishes, patterns, spec map, Spec Sculpt, generated pages)

Updated 2026-10-04.

## Hand-written articles (authored by `scripts/ai_atlas/enc_B_part6/7/8/9.py` through `enc_B_lib.py`, append-safe)

| Part | File | Articles | Plan |
|---|---|---|---|
| VI Bases and finishes | `data/encyclopedia/finishes.json` | 21 | 21 |
| VII Patterns | `data/encyclopedia/patterns.json` | 7 | 7 |
| VIII The spec map | `data/encyclopedia/spec.json` | 21 | 20 |
| IX Spec Sculpt Lab | `data/encyclopedia/spec_sculpt.json` | 13 | 11 |

Total 62 articles (plan said 59; the extras are one spec article on how base/pattern/spec combine, and two Spec Sculpt reference articles that exist to cover every control). Gate (`--files spec_sculpt,patterns,finishes,spec`): all PASS.

## Code vs wiki (code wins)
- Wiki says the Spec Sculpt look library has 12 families / "8 scratch presets"; code (`engine/spec_sculpt/presets.py`) has 125 presets in 6 categories. Articles use the code numbers.
- Wiki and `engine/SPEC_MAP_REFERENCE.md` say the normal full render floors a non-authored Cc 0 to 16; only the authored-set path keeps 0. Articles teach "0 or 16 and up".
- The inventory says per-zone Wear is not seen in the live panel of 10.0.3; the engine has it and the left-column Season batch exposes it. The wear article says so plainly.
- Plan counts (317 patterns, 181 spec patterns) differ from the atlas: 319 pattern rows and 301 spec rows (181 hand-made + 120 `spov2_*` overlays). Finish pages = 4,179 (bases + monolithics); the quoted 4,799 also counts patterns and spec patterns.

## Update after Parts VI-IX and the generator

Final hand-written counts: finishes 21, patterns 7, spec 22 (added `spec.pattern_groups`), spec_sculpt 13 = **63 articles** (plan 59). Ids that other lanes already link to were aligned: `finishes.four_kinds`, `spec_sculpt.what_is_spec_sculpt`.

## Generated pages (`scripts/ai_atlas/enc_gen_B.py`, deterministic, atomic, re-run writes 0 files)

| Set | Pages | Manifest | Part files (<=95 KB each) | Size |
|---|---|---|---|---|
| Finishes (4,179 = 1,144 bases + 3,035 specials) | 4,179 | `data/encyclopedia/finish_pages.json` | 169 in `data/encyclopedia/pages/finish_<shelf>_<n>.json` | ~11.6 MB |
| Patterns | 319 | `pattern_pages.json` | 17 | ~0.8 MB |
| Spec patterns (181 + 120 `spov2_*`) | 301 | `spec_pattern_pages.json` | 46 | ~0.8 MB |

Each page has the full schema (summary, what, when, how, tips, pitfalls, 3-4 related pages, action, sources) plus extra fields the gate ignores: `key`, `thumb` (only when the png exists), `swatch`, `shelves`/`group`, measured metal/rough/coat, palette, ratings, mood/era/use. Page ids are `<part stem>.<base|mono|pattern|spec>.<id>` and depend on the partition. Lookup: manifest `parts[]` has `group`, `firstKey`, `lastKey` (parts of one shelf/group are sorted by key; finish primary shelf = atlas item `s[0]`).
Part files live in `pages/`, not next to the manifests, because the shared gate caps every top-level domain file at 100 KB. The manifests have `articles: []` and pass the gate. I ran the gate over `pages/` through a temporary copy pointing at that folder: 232 files, 4,799 articles, all PASS, also with `--final` (all related ids resolve).

## Gate
`node _easy_claude_work/enc_v2_test.js`: my 7 files PASS; whole run only fails on `controls.json` (another lane, over its size cap at the time). Coverage of my inventory domains (bases, finishes, patterns, spec, spec_sculpt): 516 of 546 records named by my articles (the rest are Easy-mode and Gradient shelf records I also cover, see below); overall run 77.0%.

## More code vs wiki / UI findings
- **B COAT slider direction.** The engine adds the slider number straight to the coat byte (`shokker_engine_v2.py` ~20231, floor 16), so a negative B COAT is glossier and Auto-Pop correctly moves it negative. The slider tooltip ("Higher = stronger env mirror") and the built-in Feels (Wet Candy +45, Deep Gloss +85...) assume the opposite. Articles follow the engine; the Feels article warns to judge by eye. This is a real app bug/ambiguity worth a decision.
- Spec Sculpt defaults were read from `spec-sculpt.html`, not the wiki: Auto-detect decals is OFF by default (wiki implies auto-protect), Protect material defaults to Matte (flat), Drama 35, Detail amount 55, detail intensity 159 (105-205), spec strength 0-200.
- Wiki says Spec Sculpt "121 scratch styles"/"8 scratch presets"; code presets: 125 in 6 groups.
- Wear: per-zone slider not in the 10.0.3 panel; the Season batch exposes wear.

## Gaps
- No `figures` exist for lane B pages yet (lane D); articles reference plan ids only.
- Generated pages carry no aliases (titles are searched instead).

## FINAL
63 hand-written articles + 4,799 generated pages (232 part files), all schema-valid. Only my files were touched: `data/encyclopedia/{finishes,patterns,spec,spec_sculpt,finish_pages,pattern_pages,spec_pattern_pages}.json`, `data/encyclopedia/pages/`, `scripts/ai_atlas/enc_B_*.py`, `scripts/ai_atlas/enc_gen_B*.{py,js}`, this report. Open decision for the orchestrator: how the index merge should read `pages/` (or relax the gate cap for `*_pages`).

## V3 FINAL
Counts: 63 hand-written articles deepened (finishes 21, patterns 7, spec 22, spec_sculpt 13). Each has level, deep >= 2, examples >= 2, combos, faq >= 3, mistakes >= 2, protips >= 1, plus sources. The four domain files are 128 / 71 / 145 / 110 KB (cap 320). Generated pages (finishes 4,179, patterns 319, spec patterns 301) now carry spec character, category intent, paint colours and contrast, combos, similar finishes, level and a screens slot keyed `car_<id>` / `cat_<category>`.
Gate: `enc_v2_test.js` default run = all lane B files PASS, `--final` adds nothing for lane B. `--depth` for lane B fails only on `screens>=1` for 56 of 63 articles (the 7 patterns articles carry the placeholder `ui_window_tour`). No `screens.json` entry names a finishes, spec or spec_sculpt article or any `car_<finish_id>` yet; lane S must add them. The one remaining gate FAIL in the whole run is `screens.json` itself (the gate expects the domain-file header `articles:[]`; lane A/S).
Spec map (`spec.*`): how iRacing reads each channel, the order of operations from the engine, iron rules and why, floors, what makes a finish pop, worked M/R/CC examples (chrome, satin, candy, pearl, matte, carbon, flake, brushed, etc.).
Code vs wiki / code vs code (code wins):
- Foundation values: base_registry_data.py lists Soft Gloss 0/42/22, Baked Enamel 0/18/20, Silk, Clear Satin 0/100/75, Soft Matte 0/200/165, but BASE_ID_ALIASES (applied last) maps those to gloss, wet_look, satin, matte. Runtime values used everywhere in my articles: Gel Coat 0/15/16, Gloss 0/30/16, Semi Gloss 0/55/40, Satin 0/95/70, Eggshell 0/140/100, Matte 0/200/160, Primer 0/215/200, Flat Black 0/250/255.
- The alpha-union docstring in the engine is not implemented; `_enforce_iron_rules` is not on the build path (floors are inline at the end of `build_multi_zone`); surface_intent is used only by QA/metrics/thumbnail scripts, not by the render; two TGA docstrings are swapped.
- Engine anomaly (not fixed, not my lane): `apply_wear` clips the clearcoat to <= 16, so wear can turn a matte coat glossy.
- Possible dead controls (from the patterns and spec_sculpt writers, need a real-render check): per-layer Blend list and Strength Map in the patterns path; Showroom, Mix strategy and some per-channel controls in some Spec Sculpt paths. The flat-image Smart Separate is switched off in the beta; the article now teaches the PSD layer picker route.
- Lab material tables in Spec Sculpt have a clearcoat direction that disagrees with 16 = max gloss; no clearcoat bytes quoted from them.
V2 corrections kept: coat floor, alpha handling and the iron-rule wording fixed from the verified pipeline digest.
Hidden feature scrub: the inventory id `sculpt.btnEasyMode` no longer exists and is removed from my covers; the old `easy.adjust` note in this file is deleted; the gate line "no user-facing text names the hidden Easy mode" PASSES.
Subagents used: 4 (pipeline digest, knowledge digest, spec_sculpt, patterns), all sonnet.
Scratch: `_dumpB.json` deleted (regenerate with `node scripts/ai_atlas/enc_gen_B_dump.js <out>`).

# Encyclopedia DATA (2026-10-04)

Offline-helper keyword encyclopedia: DATA only, no UI. New files only; no existing js/html/server file touched; no restart; live app (port 59876) not touched.

## Step 1 - sources + extractor (done)
- `scripts/ai_atlas/enc_extract.js` (NEW): reads shipped data in a vm and cuts the private tables out of `js/spb-pro-edit.js` statement by statement (LOOKS, TEXTURES, PLAIN, TINT_COLOURS, PART_WORDS, LAYERWORDS, NUMBERS/SPONSORS/ACCENT/BODY/HOLO/UNKNOWN_PART/SHADE/REL_UP/REL_DOWN/POP regexes, WORD_TYPOS) + design colours + `spb-colours-ext.js`. Exports `parserTerms(root)` = 930 words/phrases the offline parser understands (the gate's coverage list). A table another worker renames shows up as an "extractor gap" in the gate, not a crash.
- Sources used: `js/spb-ai-atlas-data.js` (4,799 finishes, 59 shelves, tags), `js/spb-ai-cards-data.js` (buyer words + appeal/hero/risk ratings, for ranking choices), `js/spb-pro-design.js` (LOOK_CURATED 64 words, COLOURS, ELEMENTS, PRESETS, 75 PALETTES), `js/spb-pro-edit.js` (parser tables), `js/spb-colours-ext.js`, `js/spb-lexicon-ext.js` (painter slang), `js/spb-support-answers.js` (FAQ + error ids), `js/spb-self-help.js` (UI_DATA control ids, TOPICS), `scripts/ai_atlas/app_controls.json`, `GETTING_STARTED.html` (headings + facts), `scripts/ai_atlas/README.md`. `js/spb-support.js` was only inspected (its ids are intent buckets; the answers live in spb-support-answers.js).

## Step 2 - generator (done)
- `scripts/ai_atlas/build_encyclopedia.py` (NEW, deterministic: same inputs -> same version hash) + `scripts/ai_atlas/encyclopedia_recipes.py` (NEW, the hand-written one-liner recipes: 53 info, 18 flow, 58 look families). Everything else is derived: finish choices (ranked from card words/tags/names/ratings, 3-8 per term, never invented), colours, parts, shelves, atlas tags, slang, schemes, graphics, and every parser word nobody owns yet (auto-absorbed into the nearest term so "flagged == understood").
- Output `js/spb-encyclopedia-data.js` -> `window.SPB_ENCYCLOPEDIA = {version, meta, flows, terms, index, phrases, maxWords, weak}`. Rebuild: `python scripts/ai_atlas/build_encyclopedia.py` (also runs enc_extract.js). Stats: `_easy_claude_work/enc/build_stats.json`, lost-alias log `_easy_claude_work/enc/conflicts.txt`.

## Step 3 - gate (done)
- `_easy_claude_work/enc_test.js`: `node _easy_claude_work/enc_test.js` -> 26 checks, one verdict line each + total. Re-derives link targets and the parser word list itself (independent of the generator).

## Data contract (for the UI worker)
- Normalise buyer text: lowercase, delete `'`, other non `a-z0-9#` runs -> one space. Matching is leftmost-longest: try `phrases` (longest first, <= `maxWords` words) then the single word in `index`. Aliases in `weak` are common English words (`car`, `make`, `flat`, `change`...): underline only with context.
- Term: `{id,title,kind,tier,aliases,summary,details?,choices?,flow?,colour?|colours?,palette?,part?,adjust?,links?,related}`. `tier` 1 = hand core, 2 = derived from catalogue/parser tables, 3 = vocabulary (show softly).
- `choices[]`: `{label, finish_id}` (catalogue key `base::`/`monolithic::`) or `{label, pattern_id}` (bare id) or `{label, spec_id}` (bare, kept only for snake/croc/dragon/fish textures the parser already knows); `hex` present only on items that take the zone colour (thumbnail template in `meta.choice`).
- `flow`: `{name, steps?}`; a flow without steps uses top-level `flows[name]` (shared by parts/graphics/schemes). Step types: ask_target ask_colour ask_look ask_part ask_choice open_control tell confirm.
- `links[]`: `{label, target}`; target = `support:<faq/error id>` | `help:<self-help topic id>` | `control:<UI control id>` | `doc:GETTING_STARTED.html#<heading start>`. All verified by the gate.
- Long-tail CSS/racing colour names (361) share ONE entry `colour:names` with a `colours` {name: hex} map (keeps the file small); the ~100 core colour names have an entry each.

## Term counts (501 terms, 4,495 aliases, 2,484 multi-word phrases, 434 KB)
- By kind: info 53, action 327, flow 121.
- By tier: 1 hand core 138, 2 derived 271 (9 parts, 18 parser looks, 91 core colours + `colour:names`, 13 graphics/bands, 5 schemes, 71 livery palettes, 59 shelves, 11 tags, 3 modifiers), 3 vocabulary 92 (46 painter-slang, 45 card words, `colour:names` is counted in tier 2 colours above).
- 250 terms carry real catalogue choices (874 finish choices, 155 pattern choices, 5 spec choices).
- Parser coverage: all 930 words/phrases from spb-pro-edit.js tables + all 64 design look words + all 75 palettes resolve (82 absorbed automatically: typos, a few texture words).

## Coverage gaps (things buyers will type with no good entry yet)
- Colour + finish combos ("pink chrome", "blue chrome", "rainbow chrome"): composed by the parser; the encyclopedia flags the two words separately.
- Photo-editor jargon with no help topic: clone stamp, blend mode, smart object, curves, levels; and ~150 of 566 tiny UI control labels (Grow 1 px, Xform, Excl, End cap, Range Remapper...). Generate them from UI_DATA when the UI wants control-level help.
- Individual finish NAMES (4,799) are not terms: they stay with the finish search. Famous team/brand liveries beyond the 75 shipped palettes.
- Generic words are ambiguous by nature (glass = window info vs glass look, mirror = chrome vs car part, shine = spec vs gloss): one owner each; see `_easy_claude_work/enc/conflicts.txt` (431 lost aliases, all lower-priority terms).
- "my car" / "the car" are parser words (whole car) and can out-match "car number" in leftmost-longest matching; UI should treat `weak` hits as low confidence.
- Size is 434 KB vs the 400 KB target (gate hard cap 450 KB). Fastest cuts if needed: drop tier-3 `word:` terms (~20 KB) or palettes (~30 KB).

## Gate result
`node _easy_claude_work/enc_test.js` -> TOTAL 26/26 checks passed - GREEN (shape, unique aliases, index==aliases, phrases longest-first, all catalogue ids exist, all 208 link targets exist, 930 parser words covered, owner kinds, 40 flagging sentences + chatter negative).

## FINAL
Done and verified. Files: `js/spb-encyclopedia-data.js`, `scripts/ai_atlas/build_encyclopedia.py`, `scripts/ai_atlas/encyclopedia_recipes.py`, `scripts/ai_atlas/enc_extract.js`, `_easy_claude_work/enc_test.js`, this report. Not wired into `paint-booth-v2.html` (no existing html/js edited; the UI worker adds the `<script>` + cache token). Re-run the generator after adding finishes, colours or parser words; then the gate.

# -*- coding: utf-8 -*-
"""enc_plan.py - writes docs/handoff_reports/ENCYCLOPEDIA_V2_PLAN.md from enc_inventory.json + enc_coverage.json (numbers are computed, never typed).
Run AFTER enc_inventory.py:  python scripts/ai_atlas/enc_plan.py
The article TREE below is the hand-designed part (titles only; '*' = also an AI-panel quick card)."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / 'scripts' / 'ai_atlas'
inv = json.load(open(AI / 'enc_inventory.json', encoding='utf8'))
cov = json.load(open(AI / 'enc_coverage.json', encoding='utf8'))
R = inv['records']
META = inv['meta']

# lane -> domains it owns (one data/encyclopedia/<domain>.json per domain; no file is shared between lanes)
LANES = {
    'A': ('UI shell, tools, zones, layers, shortcuts', ['ui_shell', 'tools', 'zones', 'layers', 'history', 'shortcuts']),
    'B': ('finishes, bases, patterns, spec map, Spec Sculpt', ['finishes', 'bases', 'patterns', 'spec', 'spec_sculpt']),
    'C': ('render/export/iRacing, cars, Shokk Drop, Easy/Chat/AI, settings, workflows, troubleshooting', ['preview_render', 'cars', 'shokk_drop', 'easy_mode', 'ai_copilot', 'settings', 'workflows', 'support', 'concepts']),
}
DOM_LANE = {d: l for l, (_, ds) in LANES.items() for d in ds}

# ------------------------------------------------------------------ the TOC of the standalone SPB Encyclopedia (hand-written core articles)
# (part title, lane, domain file, [(chapter, [article, ...])]) ; trailing '*' = AI-panel quick card
TOC = [
    ('Part I - Getting started', 'C', 'workflows', [
        ('The big picture', ['What Shokker Paint Booth is*', 'How a paint gets onto your iRacing car*', 'Zones, bases, patterns, spec, finishes: the six words you need*', 'PRO, CHAT or EASY: which door to use*', 'The paint is ONE flat sheet of the whole car']),
        ('First steps', ['Your first paint in ten minutes*', 'Loading a paint: TGA / PNG / JPEG vs a layered PSD*', 'Your iRacing User ID and car folder*', 'Installing, updating and the update banner', 'The Tutorial and quests']),
    ]),
    ('Part II - The window, panel by panel', 'A', 'ui_shell', [
        ('Tour', ['The window tour (header, toolbar, zones, centre, right column, render)*', 'The PRO / CHAT / EASY pill', 'Collapsing panels and making the UI smaller or larger']),
        ('Header and file rows', ['Source Paint box and its buttons', 'iRacing Car Folder and Browse', 'Custom Number vs Sim-Stamped Number', 'Top-bar buttons (Spec Sculpt, Shokk Drop, Fracture this paint, gear, guide)', 'Update banner']),
        ('Centre column', ['The canvas and its overlays', 'Preview and spec channel views', 'Wire / Mask / Car Mandatory views', 'The render results panel', 'Tool options bar', 'Selection / mask bar', 'Placement map overlay']),
        ('Dialogs and menus', ['Zones > More menu', 'Dialogs reference (what each pop-up is for)', 'Save, Open, Import Recipe and projects', 'Undo History panel']),
    ]),
    ('Part III - Tools', 'A', 'tools', [
        ('Painting', ['Brush and eraser (size, hardness, opacity, smoothing)*', 'Fill bucket', 'Eyedropper / pick item', 'Color brush, Recolor, Healing, Smudge, Burn']),
        ('Selecting', ['Marquee, Lasso and Magic Wand', 'Selection modes: Add / Replace / Subtract*', 'Grow, shrink, feather, invert, mirror', 'Zone mask and layer: how they relate']),
        ('Moving and fixing', ['Move and Transform', 'Mirror Mask and symmetry', 'Undo, redo and history*', 'Zoom and pan', 'Keyboard shortcuts (quick reference)']),
    ]),
    ('Part IV - Zones', 'A', 'zones', [
        ('The zone model', ['What a zone is*', 'How a zone picks its pixels: colour, region, layer, part*', 'Zone priority: lower index wins*', 'Everything Else: the safety net*', 'Zone card controls (mute, lock, reset, delete, duplicate)']),
        ('Building zones', ['Add a zone and pick a colour from the car*', 'Colour tolerance and refining a colour', 'Draw box, lasso and region: using a region*', 'Exclude, set, and use region', 'Restricting a zone to layers', 'Named car parts (left side, hood, roof ...)']),
        ('Working with zones', ['The zone popout panel', 'Zone presets and templates', 'Why my zone does not show (visible ownership)*', 'Recipe: split a car into body, hood, roof and trim']),
    ]),
    ('Part V - Layers and PSD templates', 'A', 'layers', [
        ('Layers', ['The Layers panel*', 'Layer roles: body paint, numbers, decals, tape*', 'Layer card buttons: DUPE, MIRROR, STROKE FX, MERGE, RENAME, DELETE', 'Opacity, blend mode, hue / saturation / brightness', 'Layer effects (stroke, colour overlay and more)', 'Merge down and merge visible']),
        ('Templates', ['Open Layered PSD*', 'Turn Off Before Exporting TGA*', 'Paintable Area*', 'Wire, Mask and Car Mandatory', 'Lock zone to layer', 'Export to Photoshop (layer ZIP)', 'Decal rescue']),
    ]),
    ('Part VI - Bases and finishes', 'B', 'finishes', [
        ('What a finish is', ['Base, monolithic, pattern and spec overlay: four kinds of look*', 'Colour source modes: finish, source, solid, special, gradient*', 'Foundation: change only the shine, keep your paint*', 'Surface intent: spec-driven, pattern-driven and full finishes']),
        ('The catalogue map', ['How the catalogue is organised (shelves)*', 'Foundation and Foundation EFX', 'ASTRA', 'Ghost Geometry and Clearcoat', 'ColorShoxx and colour-shift finishes', 'Fractured, Mortal Shokk and Neon Underground', 'Source pattern plates and Houdini / X-Lab', 'Retro, decades and cultural shelves', 'Nature, tactical and cyberpunk shelves']),
        ('Choosing and tuning', ['The finish picker, library, browser and compare*', 'Finish cards: mood, era, use, fit', 'What makes a finish pop on a car*', 'Base colour strength, hue, saturation, brightness', 'Gradients, colour flip, colour depth, underglow', 'Base scale and rotation (what "crushed" means)*', 'Second base and dual shift', 'Wear and aging']),
    ]),
    ('Part VII - Patterns', 'B', 'patterns', [
        ('Patterns', ['What a pattern is and how it differs from a base*', 'Pattern groups: a map of the 9 groups', 'Pattern scale, rotation, opacity and strength', 'Pattern placement, offsets, fit-to-zone, flips', 'Pattern layers and stacking', 'Pattern paint mode: overlay vs blend', 'Choosing patterns that read at car scale*']),
    ]),
    ('Part VIII - The spec map', 'B', 'spec', [
        ('Spec basics', ['What the spec map is*', 'R = Metallic*', 'G = Roughness*', 'B = Clearcoat (and why it is backwards)*', 'A = Spec mask', 'Reading a spec picture by colour', 'Metallic x roughness: the material grid']),
        ('Rules', ['Iron rules: clearcoat 0 or 16+, roughness floor*', 'Paint and spec: how they marry', 'Colour space: paint vs spec bytes', 'Export and preview truth: what iRacing really shows']),
        ('Controls', ['Spec strength and independent spec', 'Spec scale and rotation', 'Spec channel shift (R/G/B)', 'Spec material override, remap and lighting mask', 'Spec patterns and spec pattern stacks', 'Spec presets: save and reuse', 'Auto pop', 'The Spec Map Inspector', 'Colour-shift and angle-reveal finishes']),
    ]),
    ('Part IX - Spec Sculpt Lab', 'B', 'spec_sculpt', [
        ('Spec Sculpt', ['Why Spec Sculpt exists*', 'The three modes', 'Scratch presets', 'Paint response: tie spec to your colours', 'Generation DNA', 'Smart Separate and car intelligence', 'Auto-protect (numbers and sponsors)', 'Power features', 'Diagnostics in the preview', 'Iron rules on export', 'Spec Sculpt recipes']),
    ]),
    ('Part X - Preview, render and export', 'C', 'preview_render', [
        ('Preview and render', ['Preview vs render*', 'The Render button and render size (2048 / 1024)*', 'Render history and render stats', 'Why a render is slow, and what to do']),
        ('Files and iRacing', ['Output files: car_num_ID.tga, car_ID.tga and car_spec_ID.tga*', 'Custom Number vs Sim-Stamped, Hide Car Numbers*', 'Where the files go: the iRacing car folder*', 'Seeing it in iRacing: Alt+Tab and Ctrl+R*', 'Auto-deploy / live link', 'Trading Paints and .mip files*', 'PSD / XCF / ORA export', 'Saving projects, recipes and reloading later']),
    ]),
    ('Part XI - Cars and templates', 'C', 'cars', [
        ('Cars', ['Supported cars and templates (the car atlas)*', 'Reading the unwrapped car sheet', 'Teaching Shokker the parts of your car', 'Choosing the right template for your car', 'Sponsor and number safe areas']),
    ]),
    ('Part XII - Shokk Drop and Fracture', 'C', 'shokk_drop', [
        ('Shokk', ['Shokk Drop: what it is*', 'The SHOKK library and saving a .shokk file', 'Fracture this paint', 'Image Forge and trace tools']),
    ]),
    ('Part XIII - Easy mode, Chat and the AI helper', 'C', 'ai_copilot', [
        ('Easy and Chat', ['Easy mode: tap a part, pick a look*', 'Chat mode: say what you want*', 'The offline helper vs AI', 'Edit what is already on the car*', 'Picking colours and looks in words']),
        ('AI and connectors', ['The gear: key, model, daily cap', 'Claude and ChatGPT via MCP', 'What the AI can and cannot see', 'Car learning: ask, propose, learn']),
        ('Settings', ['Settings overview (gear)', 'File picker setting', 'Performance and speed settings', 'Activation and licence']),
    ]),
    ('Part XIV - Recipes and workflows', 'C', 'workflows', [
        ('Recipes', ['Make the whole car matte black*', 'Chrome with your source colours (spec only)*', 'Retro stripes and numbers', 'A two-tone livery in six zones', 'Colour-shift paint that moves in the sun', 'Carbon fibre hood', 'Candy colours: how to get depth', 'Edit one thing without touching sponsors', 'Camo with a pattern layer', 'Gradient from roof to rocker', 'Metal flake and pearl', 'Flames and graphics', 'Mirror one side to the other', 'Match a photo or reference livery', 'Night and day variants', 'Team liveries: one scheme, many cars', 'Wet look and glass looks', 'Weathered and aged paint', 'Matching helmet and suit', 'From PSD template to iRacing in one pass']),
    ]),
    ('Part XV - Troubleshooting', 'C', 'support', [
        ('Problems', ['It does not show up in iRacing*', 'My colours look different in iRacing*', 'The finish looks flat or too shiny*', 'My zone does not show / nothing changed*', 'Render is slow or fails', 'I lost my file / where did my files go*', 'Numbers or sponsors vanished or got painted over*', 'The car looks smeared or blobby', 'Preview and render do not match', 'The app will not start or update', 'Error messages explained (pasted-error helper)*', 'Reporting a problem', 'Trading Paints questions*', 'PSD will not open or has wrong layers', 'Everything looks tiny or huge (base scale)']),
    ]),
    ('Part XVI - Reference (mostly generated)', 'A', 'shortcuts', [
        ('Reference pages', ['Keyboard shortcuts table', 'Control index (every slider, toggle, dropdown)', 'Glossary (existing 501 terms)', 'Colour name list', 'Finish shelf index', 'Spec value cheat sheet (R/G/B quick table)']),
    ]),
]

# ------------------------------------------------------------------ numbers
dom_n = META['by_domain']
tot = len(R)
core = []
for pt, lane, dom, chs in TOC:
    for ch, arts in chs:
        for a in arts:
            core.append((pt, ch, a.rstrip('*'), a.endswith('*'), lane, dom))
n_core = len(core); n_quick = sum(1 for c in core if c[3])
lane_core = {l: sum(1 for c in core if c[4] == l) for l in LANES}
lane_rec = {l: sum(dom_n.get(d, 0) for d in ds) for l, (_, ds) in LANES.items()}
kinds = META['by_kind']
gen_controls = sum(kinds.get(k, 0) for k in ('slider', 'number input', 'dropdown', 'toggle', 'text input', 'picker', 'radio', 'search box', 'file input', 'button', 'tab', 'menu', 'zone_param'))
gen = {'finishes (atlas rows -> finish page)': 4799, 'finish shelves': kinds.get('finish_shelf', 0) + kinds.get('finish_category', 0), 'patterns': 317, 'pattern groups': kinds.get('pattern_group', 0),
       'spec patterns': 181, 'spec pattern groups': kinds.get('spec_pattern_group', 0), 'cars': kinds.get('car', 0), 'UI controls (sliders/buttons/etc.)': gen_controls, 'keyboard shortcuts (1 table + rows)': kinds.get('shortcut', 0),
       'FAQ / error answers (wrapped by Troubleshooting)': kinds.get('faq', 0) + kinds.get('error_answer', 0)}
per = cov['per_domain']

L = []
w = L.append
w('# Encyclopedia v2 - knowledge inventory, coverage and plan (2026-10-04)')
w('')
w('Generated by `scripts/ai_atlas/enc_plan.py` from `scripts/ai_atlas/enc_inventory.json` (built by `enc_inventory.py`) and `enc_coverage.json`. Re-run both scripts to refresh; every number below is computed. New files only; no existing js/html/py edited; no server touched.')
w('')
w('## 1. What was measured')
w('')
w('- **%d knowable things** in %d domains (table below). Each record is `{id, domain, kind, label, source:"file:line", topic, facts}`; sources resolve to real file:line (%d unresolved JS-built controls fall back to the building module).' % (tot, len(dom_n), META['n_sources_unresolved']))
w('- Current encyclopedia: **%d terms**, glossary-grade only (summary of at most two sentences, aliases, links, finish choices). It has **no article-grade entry at all** (no what / when / steps / every-control / pitfalls structure).' % cov['terms'])
w('- **Knowledge coverage: (a) things with ANY entry = %.1f%% (%d of %d); (b) things with a real article = %.1f%% (0 of %d).** Counting loose mentions (a term name appears inside the label but the thing is not explained) would give %.1f%%, which is not real coverage.' % (cov['coverage_any_pct'], cov['covered_glossary'] + cov['covered_deep'], tot, cov['coverage_article_pct'], tot, cov['coverage_any_incl_loose_pct']))
w('- Matching rule: a record is "glossary" if a term links to its control / support / help id, or the record label equals a non-weak alias AND the term title shares a word with it (or the label is a multi-word phrase, shelf, group, FAQ or car). Single generic words (Zoom, Redo, Burn, Activate) that only hit an unrelated alias are NOT counted. The "(b) article" test needs a term with a body of real length; none exists, so it is 0.')
w('- Honest read: the owner estimate "5 to 10 percent" is about right for **depth** (0%% have an article); the glossary does touch ~%.0f%% of the things by name, mostly finish shelves, support answers and a few controls.' % cov['coverage_any_pct'])
w('')
w('### Inventory and coverage by domain')
w('')
w('| domain | lane | records | glossary entry | uncovered | what it holds |')
w('|---|---|---:|---:|---:|---|')
DESC = {'spec_sculpt': 'Spec Sculpt page + SPEC TOOLS panel: sliders, buttons, wiki topics', 'workflows': 'how-do-I (118), self-help topics, Getting Started headings, ai_knowledge cards',
        'ui_shell': 'header rows, modes, centre column, dialogs, wiki overview', 'finishes': '59 shelves, categories, intents, finish picker/library controls, catalogue counts, cards',
        'tools': 'toolbar, tool options, selection bar, transform, placement, eyedropper', 'layers': 'LAYERS tab, layer card buttons, Layer Effects, template groups', 'spec': 'spec channels, iron rules, spec controls, spec pattern groups, spec guide topics',
        'support': '"Talk to Shokker" FAQs + pasted-error answers', 'zones': 'zone cards, selectors, tolerance, priority, region tools', 'shokk_drop': 'Shokk Drop page, SHOKK library, save dialog', 'shortcuts': 'keyboard shortcut overlay rows',
        'preview_render': 'preview, render, export files, iRacing folder, Ctrl+R, .mip, PS export', 'bases': 'base groups, colour mode / strength / hue / gradient zone controls', 'cars': '38 cars in the car atlas',
        'easy_mode': 'Easy panels and part panel', 'patterns': 'pattern groups + pattern zone controls', 'ai_copilot': 'AI panel, MCP tools, chat', 'settings': 'gear/settings panel', 'concepts': 'wiki hard-won-lesson groups', 'history': 'undo history panel'}
for d, n in sorted(dom_n.items(), key=lambda x: -x[1]):
    p = per.get(d, {})
    w('| %s | %s | %d | %d | %d | %s |' % (d, DOM_LANE.get(d, '?'), n, p.get('covered_glossary', 0) + p.get('covered_deep', 0), p.get('uncovered', 0), DESC.get(d, '')))
w('| **total** | | **%d** | **%d** | **%d** | |' % (tot, cov['covered_glossary'] + cov['covered_deep'], cov['uncovered']))
w('')
w('Record kinds: ' + ', '.join('%s %d' % (k, v) for k, v in sorted(kinds.items(), key=lambda x: -x[1])) + '.')
w('')
w('Not in the record list on purpose (generated from data at read time, see section 4): the **4,799 individual finishes** (atlas rows + cards, counted in `catalog.finish_cards`), the **317 patterns** and **181 spec patterns** (counted per group), and the colour-name long tail (existing glossary).')
w('')
w('Source mix: ui_map.json curated items (does / when / mistakes) re-anchored to paint-booth-v2.html lines and enriched with the HTML scan (min/max/step/default/handler/engine field); app_controls.json (zone/engine params, range, default, effect); the shipped JS data files read in a vm (catalogue, atlas, cards, car atlas); engine docstrings (spec channels, iron rules); support / self-help modules; docs/ai_knowledge; GETTING_STARTED.html; and **user-relevant sections of SPB_WIKI.html** (%d wiki topics: spec guide, finish doctrine, Spec Sculpt, Smart Separate, lessons; source `SPB_WIKI.html#<section>:<line>`).' % kinds.get('wiki_topic', 0))
w('')
w('**Wiki borrow policy (owner 2026-10-04):** only user-relevant knowledge (how spec channels / iron rules / clearcoat / finishes / zones / layers / render really work, lessons that change what a user does). Never the Agent Coordination Board, Daily Work Log, Known Trouble Spots, post-mortem internals, build / CI / registry plumbing, or dev-only paths. A writer who borrows a wiki fact still cites the code line that proves it (`sources[]`); the wiki section is a lead, not a source of truth.')
w('')
w('## 2. The standalone SPB Encyclopedia (product)')
w('')
w('A **top-bar button** (next to SPEC SCULPT / SHOKK DROP; a UI worker adds it) opens a full-window reader: left = table of contents tree, centre = article, right = "related" + "Do it" actions; `/` searches titles, aliases and body text. The **AI-panel helper** keeps its keyword flagging and shows **quick cards** (the starred articles: title, one-paragraph summary, the first 3 steps, Do-it buttons, "Open in Encyclopedia").')
w('')
w('Table of contents (**%d hand-written core articles**, %d starred as AI-panel quick cards; lane = writer lane, file = `data/encyclopedia/<domain>.json`):' % (n_core, n_quick))
w('')
for pt, lane, dom, chs in TOC:
    na = sum(len(a) for _, a in chs)
    w('### %s  (lane %s, `%s.json`, %d articles)' % (pt, lane, dom, na))
    for ch, arts in chs:
        w('- **%s**' % ch)
        for a in arts:
            w('  - %s' % (a[:-1] + ' (quick card)' if a.endswith('*') else a))
    w('')
w('Appendix (all generated, no writer): glossary of the existing 501 terms, colour names, control index, finish shelf index, spec cheat sheet.')
w('')
w('## 3. Writer lanes (3 + graphics lane D), NO file overlap')
w('')
w('| lane | scope | domain files it owns | inventory records | core articles |')
w('|---|---|---|---:|---:|')
for l, (desc, ds) in LANES.items():
    w('| %s | %s | %s | %d | %d |' % (l, desc, ', '.join('`%s.json`' % d for d in ds), lane_rec[l], lane_core[l]))
w('| D | graphics (SVG diagrams + engine renders), see section 5 | `img/*.svg`, `img/*.png`, `graphics.json` | - | 0 (about 35 assets) |')
w('')
w('Note: Part XVI (reference) is Lane A because the shortcuts table is its data; Part I and XIV (workflows) and XV (troubleshooting) are Lane C. A starred article in another lane may be a quick card; the **card is generated from the article** (no second copy).')
w('')
w('Lane rules (all lanes): (1) every fact needs a `sources[]` entry that is a real `file:line`; the wiki only points you where to look. (2) `controls[]` entries must come from inventory records (`covers[]` holds the inventory ids), so nothing is invented and ranges/defaults are copied from `facts`. (3) Write after EVERY article (append JSON lines to `data/encyclopedia/_drafts/<domain>.jsonl`; a script assembles `<domain>.json`). (4) Run the gate (section 4) before reporting; one verdict line. (5) Max 2 subagents per lane, model sonnet for plumbing, no swarms. (6) Finish pages follow the Finish Law: describe, never re-author finishes; never touch PROTECTED finishes.')
w('')
w('### Which entries are GENERATED vs hand-WRITTEN')
w('')
w('| generated from data (no writer) | count |')
w('|---|---:|')
for k, v in gen.items():
    w('| %s | %d |' % (k, v))
w('')
w('- **Control pages** are built from the inventory record + `ui_map` curated text: label, where, range / default / step (from the HTML), what it drives (`facts.drives`, `facts.control.zone_field`, `payload_field`), does / when / mistakes, related controls. Only the %d controls with curated `does` get a polished card; the rest show the tooltip + range.' % sum(1 for r in R if r['facts'].get('curated')))
w('- **Finish pages**: name, shelf, intent, blurb, card words / ratings, live swatch (`/api/swatch/...`), "Apply" action. **Pattern / spec-pattern pages**: group, thumbnail, scale/rotation advice from the group article. **Car pages**: folders + parts known.')
w('- **Hand-written (%d core articles)** cover the concepts: what, when, steps, every control (by id), tips, pitfalls. Target 150 to 250: this tree is %d; writers may add up to ~20 more where the generated pages show a gap.' % (n_core, n_core))
w('')
w('## 4. Proposed v2 data layout (keeps flagging fast)')
w('')
w('```')
w('js/spb-encyclopedia-data.js          small INDEX (today 434 KB; target <= 450 KB): terms {id,title,kind,tier,summary<=2 sentences, aliases, links, choices, art:"<domain>#<id>"}, index, phrases, weak')
w('data/encyclopedia/manifest.json       {version, domains:{name:{file,count,bytes,lane}}, idIndex:{articleId:domain}}   (loaded once, < 40 KB)')
w('data/encyclopedia/<domain>.json       {domain, version, articles:[...]}  one file per domain, 20 files, each <= ~80 KB, fetched on demand and cached in memory')
w('data/encyclopedia/img/                 SVG + PNG graphics (lane D) referenced by article.figures[]')
w('data/encyclopedia/graphics.json       {id, file, alt, caption, sources[], producer}')
w('```')
w('')
w('Flagging stays on the small index (alias -> term id -> `art` pointer). Opening a chip or the reader loads ONE domain file. Generated pages (finishes, patterns, cars, controls) are rendered at read time from `js/spb-ai-atlas-data.js`, `js/spb-ai-cards-data.js`, `js/spb-car-atlas-data.js`, `ui_map.json` / `js/spb-self-help.js` UI_DATA: **no stored copy, so they cannot drift**. Packaging check for the UI worker: `data/encyclopedia/` must be served by the Flask static route AND listed in `electron-app/copy-server-assets.js` (two-copy rule: root + `electron-app/server/`, then `node scripts/sync-runtime-copies.js --write`).')
w('')
w('Article schema (`data/encyclopedia/<domain>.json -> articles[]`):')
w('')
w('```json')
w('{ "id": "zones.priority", "title": "Zone priority: lower index wins", "domain": "zones", "summary": "one or two sentences (quick card text)",')
w('  "what": "plain paragraph(s)", "when": ["situations where a buyer needs this"],')
w('  "how": [ "step 1 naming the exact control and where it is", "step 2" ],')
w('  "controls": [ { "label": "...", "range": "0-100%", "default": "100%", "effect": "...", "inv": "<inventory id>" } ],')
w('  "tips": [], "pitfalls": [], "related": ["article ids"],')
w('  "actions": [ { "do": "finish", "id": "base::f_chrome" }, { "do": "flow", "id": "..." }, { "do": "control", "id": "<UI control id>" } ],')
w('  "figures": [ "g05_zone_priority_stack" ],')
w('  "covers": [ "<inventory record ids this article explains>" ],')
w('  "sources": [ "paint-booth-2-state-zones.js:1167" ],   // REQUIRED, file:line, must exist')
w('  "quick": true, "lane": "A", "updated": "2026-10-04" }')
w('```')
w('')
w('Gate (to build with the first lane output, `scripts/ai_atlas/enc_articles_gate.py`, one verdict line per check): schema keys present; ids unique; every `sources[]` file exists and the line number is inside the file; every `controls[].inv` and `covers[]` id exists in `enc_inventory.json`; every `related` / `figures` / `actions` target exists; every inventory record is `covers`-ed by an article OR is a generated kind; summary <= 2 sentences; no domain file over 100 KB. The same script recomputes **article coverage (b)** as `records covered by articles / records`, so progress is measurable: today 0%, target >= 95% (100% of generated kinds are covered by definition).')
w('')
w('## 5. Lane D - graphics for the encyclopedia')
w('')
w('One script per kind, deterministic, outputs under `data/encyclopedia/img/`, each asset registered in `graphics.json` with alt text, caption and the `sources[]` the numbers came from. SVGs use CSS variables for light/dark and carry no external fonts.')
w('')
w('**(a) Generated SVG explainer diagrams** (`scripts/ai_atlas/enc_gfx/make_diagrams.py`, pure string templates; numbers read from the engine docstring / inventory so they cannot drift):')
w('')
w('| id | diagram | used by | data source |')
w('|---|---|---|---|')
for r_ in [
    ('g01_spec_channels', 'Spec map R / G / B / A channels: tiles + value ranges', 'Part VIII', 'shokker_engine_v2.py (SPEC-MAP CHANNEL SEMANTICS)'),
    ('g02_roughness_scale', 'Roughness bar 0 (mirror) to 255 (matte) with named stops', 'G = Roughness', 'engine/SPEC_MAP_REFERENCE.md'),
    ('g03_clearcoat_scale', 'Clearcoat 0-15 none / 16 max gloss / up to 255 dull, inversion arrow, iron-rule band', 'B = Clearcoat, iron rules', 'shokker_engine_v2.py CC_FLOOR'),
    ('g04_metal_rough_grid', 'Metallic x roughness grid with labelled corners (chrome, brushed, satin, matte, dielectric gloss)', 'material grid', 'SPB_WIKI spec_guide coordinate system (lead) + engine'),
    ('g05_zone_priority', 'Zone priority stack: lower index wins, Everything Else last, visible-ownership', 'Part IV', 'paint-booth-2-state-zones.js, mcp/server/index.js'),
    ('g06_zone_selectors', 'Four ways a zone picks pixels: colour, region, layer, part', 'Part IV', 'ui_map zone.* items'),
    ('g07_layer_stack_roles', 'Layer stack with roles, Turn Off Before Exporting TGA group, Paintable Area, Wire/Mask/Car Mandatory', 'Part V', 'paint-booth-3-canvas.js, support answers'),
    ('g08_uv_sheet_parts', 'Car UV sheet cut open: named parts (sides, hood, roof, trunk, bumpers, spoiler)', 'Part XI', 'js/spb-pro-carmap.js part words + car atlas'),
    ('g09_render_export_flow', 'Shokker > Render > car_num_ID.tga + car_spec_ID.tga > iRacing paint folder > Alt+Tab > Ctrl+R', 'Part X', 'server.py (car_num_), support answers'),
    ('g10_file_naming', 'car_num_ID vs car_ID (Custom Number vs Sim-Stamped, Hide Car Numbers)', 'Part X', 'js/spb-support-answers.js F(number_modes)'),
    ('g11_mip_pipeline', 'TGA -> iRacing compiles .mip; Trading Paints spec = .mip only', 'Trading Paints', 'server.py (iRacing compiles paint)'),
    ('g12_window_tour', 'Annotated wireframe of the Pro window with the 24 ui_map panels numbered', 'Part II', 'ui_map.json panels'),
    ('g13_four_kinds_of_look', 'Base / monolithic / pattern / spec overlay: what each controls (paint vs spec)', 'Part VI', 'docs/ai_knowledge/02_spec_and_finishes.md'),
    ('g14_colour_modes', 'Colour source modes: finish / source / solid / special / gradient', 'Part VI', 'app_controls.json zone_base_colour_mode'),
    ('g15_surface_intent', 'Surface intent families (spec_driven, pattern_design, pattern_image, fine_structural_color, full) with category names', 'Part VI', 'engine/paint_v2/surface_intent.py CATEGORY_INTENT'),
    ('g16_foundation_spec_only', 'Foundation finish: paint unchanged, only shine changes (before/after bars)', 'Part VI', 'spb_* tool guide + base registry'),
    ('g17_pick_a_door', 'PRO / CHAT / EASY decision picture', 'Part I', 'ui_map modes'),
    ('g18_iron_rules', 'Iron rules infographic (CC >= 16 or 0, roughness floor 15 unless M >= 240, alpha follows zones)', 'iron rules', 'shokker_engine_v2.py'),
    ('g19_scale_on_car', '2048 canvas over a whole car: what 32 px and 256 px features look like on a mirror / door', 'what "crushed" means', 'CLAUDE.md quality bar, finish doctrine'),
    ('g20_selection_modes', 'Add / Replace / Subtract selection with before/after masks', 'Part III', 'ui_map pro.selection_bar'),
]:
    w('| %s | %s | %s | %s |' % r_)
w('')
w('**(b) REAL engine renders** (where a picture beats words; ONE engine boot per script, filtered output, results written to disk as they finish; payload shape copied from a real `output/job_render_*/zones_payload.json`, not guessed):')
w('')
w('| id | picture | how to produce it |')
w('|---|---|---|')
for r_ in [
    ('r01_spec_sweep_RxG', '8 x 8 swatches: metallic 0..255 across, roughness 0..255 down, clearcoat 16', '`scripts/ai_atlas/enc_gfx/render_spec_grid.py`: `shokker_engine_v2.preview_render(paint_file=<flat grey 256px TGA>, zones=[{... "spec_material_override": {R,G,B}}])` per tile (spec_material_override is the exact per-channel zone control, see app_controls.json zone_spec_material_override_remap_lightingmask); iron rules applied by the engine'),
    ('r02_clearcoat_sweep', 'one metallic paint with B = 0, 16, 32, 64, 128, 255 side by side', 'same script, vary B only'),
    ('r03_roughness_sweep', 'chrome to matte ladder, same colour', 'same script, vary G only'),
    ('r04_foundation_before_after', 'Foundation chrome / satin / matte on the same livery, paint identical', '`preview_render` with `base::f_chrome`, `base::f_satin_chrome`, `base::f_soft_matte`, colour mode source'),
    ('r05_shelf_tiles', 'one hero tile per shelf (59 shelves)', 'REUSE existing thumbnails: `thumbnails/` + `swatches/` (rebuild_thumbnails.py / swatch routes `/api/swatch/{base|monolithic}/{id}?size=200&color=hex`); pick the card with the best `hero` rating in js/spb-ai-cards-data.js; no new render needed'),
    ('r06_pattern_scale', 'one pattern at scale 0.25x / 1x / 4x on a car-size field', '`preview_render` with `scale` zone param (zone_pattern_scale 0.10-4.0)'),
    ('r07_pattern_rotation', 'rotation 0 / 45 / 90 on a directional pattern', 'same, vary `rotation`'),
    ('r08_pattern_opacity_strength', 'pattern opacity vs pattern spec strength (paint fade vs spec fade)', 'same, vary `pattern_opacity` and `pattern_spec_mult`'),
    ('r09_base_scale', 'base scale 0.25x / 1x / 5x on a texture base (what "crushed" means)', 'same, vary `base_scale`'),
    ('r10_colour_modes', 'one finish under the five colour modes', 'same, vary `base_color_mode`'),
    ('r11_colour_tolerance', 'zone tolerance 6 / 30 / 100 on a two-colour car (selection mask overlay)', 'zone mask from `build_multi_zone` debug masks (save_debug_images=True) on a sample livery'),
    ('r12_zone_priority_demo', 'two overlapping zones, swap their order', '`preview_render` with zones reordered'),
    ('r13_spec_channel_views', 'one livery: paint, R, G, B, A channel views', 'the app preview "spec channels" endpoint or split `build_multi_zone` spec output into channels'),
    ('r14_sculpt_before_after', 'Spec Sculpt scratch preset before/after', 'spec_sculpt engine presets on a sample skin'),
]:
    w('| %s | %s | %s |' % r_)
w('')
w('Lane D rules: every real render is judged at 1:1 by eye before it is registered (a gate is not a look); render at <= 512 px for sweeps; budget **one engine boot per script**; store PNG at <= 200 KB each (quantise), keep total `img/` under ~8 MB; never render a PROTECTED finish with altered params. Diagrams first (cheap, no engine), renders second.')
w('')
w('## 6. Order of work')
w('')
w('1. (done here) inventory + coverage + this plan. 2. Lane D diagrams g01-g04, g09, g10, g18 first (most reused). 3. Lanes A / B / C write core articles in order of starred quick cards, then the rest; the gate script is written with the first drafts. 4. UI worker: manifest loader, top-bar button, reader, quick-card renderer, `art` pointers in the index (generator `build_encyclopedia.py` change, not done here). 5. Re-run `enc_inventory.py` + gate: article coverage must reach >= 95%.')
w('')
w('Token estimate for the whole writing job (declared per CLAUDE.md before launch): about 230 articles x ~4k output tokens = ~1M output tokens across 3 lanes if written bespoke; with generated pages and AI-as-compiler recipes (a small helper that turns a topic + inventory facts into a draft the writer edits) it should land well below that. Run lanes in waves of at most 3 concurrent, sonnet writers, one opus review pass per lane.')
w('')
w('## FINAL')
w('')
w('- **Coverage: (a) any entry %.1f%% (%d of %d things); (b) real article 0.0%% (0 of %d).**' % (cov['coverage_any_pct'], cov['covered_glossary'] + cov['covered_deep'], tot, tot))
w('- Inventory: %d records. Per domain: %s.' % (tot, ', '.join('%s %d' % (d, n) for d, n in sorted(dom_n.items(), key=lambda x: -x[1]))))
w('- Lane split (records / core articles): ' + '; '.join('%s %d / %d' % (l, lane_rec[l], lane_core[l]) for l in LANES) + '; D graphics 20 SVG + 14 renders.')
w('- Hand-written core articles: %d (%d quick cards); generated from data: finishes 4,799, patterns 317, spec patterns 181, cars %d, controls %d.' % (n_core, n_quick, kinds.get('car', 0), gen_controls))
w('- Files: `scripts/ai_atlas/enc_inventory.py`, `enc_inventory_js.js`, `enc_plan.py`, `enc_inventory.json`, `enc_coverage.json`, this plan.')
Path(ROOT / 'docs' / 'handoff_reports' / 'ENCYCLOPEDIA_V2_PLAN.md').write_text('\n'.join(L) + '\n', encoding='utf8')
print('PLAN written: core articles %d (quick %d), lanes %s, records %d' % (n_core, n_quick, lane_core, tot))

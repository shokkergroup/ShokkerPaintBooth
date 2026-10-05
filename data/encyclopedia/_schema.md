# Encyclopedia v2 - article schema (agreed 2026-10-04, enforced by `node _easy_claude_work/enc_v2_test.js`)

One file per domain: `data/encyclopedia/<domain>.json` = `{ "domain": "<domain>", "version": 1, "articles": [ ... ] }`.
Files starting with `_` and `manifest.json` / `graphics.json` are not article files. Domain files stay under 320 KB (v3 depth); generated page sets (finish, pattern, spec-pattern and control pages) live in `pages/<part>.json` part files (cap 128 KB each) listed in a small manifest (`finish_pages.json`, `pattern_pages.json`, `spec_pattern_pages.json`, `controls_pages.json`).

## Article

```json
{ "id": "zones.priority",            // "<domain>.<slug>"; unique across ALL files; the prefix MUST equal the file's domain
  "title": "Zone priority: lower index wins",
  "domain": "zones",
  "summary": "1-2 sentences, <= 330 chars. This is the quick-card text.",
  "what": "Plain paragraph(s). Never empty.",
  "when": ["situations where a buyer needs this"],
  "how": ["1. Step naming the real button and where it is", "2. ..."],      // quick:true needs >= 3 steps
  "controls": [ { "label": "Size", "range": "1-500 px", "default": "40", "effect": "what it does", "inv": "<inventory id>" } ],
  "tips": [], "pitfalls": [],
  "related": ["zones.everything_else"],     // article ids; a target in a domain file not written yet = PENDING (fails only with --final)
  "actions": [ { "do": "finish", "id": "base::f_chrome" },  { "do": "pattern", "id": "<pattern id>" },
               { "do": "spec", "id": "<spec pattern id>" }, { "do": "flow", "id": "<flow name>" }, { "do": "control", "id": "<UI control id>" } ],
  "figures": ["g05_zone_priority"],         // ids from plan section 5 (or graphics.json)
  "covers": ["<inventory record id>"],      // enc_inventory.json ids this article explains = article coverage
  "sources": ["paint-booth-2-state-zones.js:1167", "SPB_WIKI.html#spec_guide"],   // REQUIRED. file:line (or file:a-b); the line must exist
  "aliases": ["zone order", "zone priorty"], // OPTIONAL. what a buyer types. Normalised: lowercase a-z 0-9 # and single spaces. Unique across all files.
  "quick": true,                             // true = AI-panel quick card (needs >= 3 how steps)
  "lane": "A", "updated": "2026-10-04",
  "generated": true }                        // OPTIONAL. true for script-made pages (finishes, patterns, controls, cars)
```

## Rules the gate enforces

- Every key of the example above except `aliases` and `generated` must be present (empty arrays are fine).
- `sources[]` entries resolve: file exists in the project, line inside the file. `SPB_WIKI.html#<section>` must be a real section name. The wiki is a lead only; also cite the code line that proves the fact.
- `actions[]` / `covers[]` / `controls[].inv` / `related[]` / `figures[]` must point at things that exist.
- No dev words or paths in user text (title, summary, what, when, how, tips, pitfalls, controls[] fields): no file names such as `x.js`, no `/api/`, no `fn()`, no "payload", "endpoint", "JSON", "handler", "inventory", ticket numbers.
- `summary` is at most two sentences.
- Ids: letters, digits, dots, underscores and dashes only; the domain prefix equals the file name.

## Writing style

Buyer language, short sentences, name the exact on-screen label (UPPERCASE as shown), copy every number from the source, never from memory.
Generated control pages: one per slider / button / toggle / dropdown / input, `covers` = [that inventory id]. They live in `pages/controls_<area>_<n>.json` (part domain `controls_<area>_<n>`, page id `<part domain>.<inventory id>`) with the small manifest `controls_pages.json`, the same layout as the finish pages. Part files are capped at 128 KB; top-level domain files at 100 KB.


## Schema v3 (2026-10-04 evening, additive: every field below is OPTIONAL in the default gate, REQUIRED by the depth bar for hand-written articles)

```json
{ "level": "beginner | intermediate | pro",
  "deep":     [ { "heading": "How it really works", "body": "Engine-level truth in buyer words, real numbers (ranges, defaults, channel values, order of operations, what overrides what)." } ],
  "examples": [ { "title": "Chrome hood, matte car", "goal": "what the buyer wants",
                  "settings": { "Base": "Chrome", "Strength": "100%" },   // label: value, EXACT and copyable
                  "result": "what they will see", "screen": "<screens.json id, optional>" } ],
  "combos":   [ { "with": "zones.priority", "why": "what pairs well or clashes, and why" } ],   // "with" = article id, or an atlas key (base::..., pattern::..., spec::...)
  "faq":      [ { "q": "A real buyer question", "a": "Short direct answer" } ],
  "mistakes": [ { "symptom": "what they see", "cause": "why", "fix": "what to do" } ],
  "protips":  [ "Non-obvious knowledge: the 'I did not know it could do that' layer" ],
  "screens":  [ "<id of a REAL app screenshot in data/encyclopedia/screens.json>" ] }
```

Gate (default mode): the shapes above are checked when present; `combos[].with` follows the `related` rule (PENDING, a FAIL only with `--final`); `screens[]` and `examples[].screen` must resolve in `screens.json` once that file exists; all v3 text goes through the same jargon and hidden-feature (Easy mode) checks as v2 text.

Depth bar (`node _easy_claude_work/enc_v2_test.js --depth [--lane A] [--files a,b]`), per hand-written (not `generated:true`) article:
summary + what, `how` >= 3, `deep` >= 2, `examples` >= 2, `faq` >= 3, `mistakes` >= 2, `protips` >= 1, `screens` >= 1 (enforced only once `screens.json` exists), sources present, every number sourced.
Help-style pages (id contains `.help_`): `how` >= 3, `deep` >= 1, `mistakes` >= 2, `related` >= 1.
Output: one `DEPTH-FAIL id missing: ...` line per article below the bar, one `DEPTH lane X: ok/total` summary per lane, exit 1 when a checked article (all, or `--lane X`, or `--files`) misses the bar.

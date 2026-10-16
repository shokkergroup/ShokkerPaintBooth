# HELPER ARCHITECTURE V3: one intent frame, a planner, a verifier, and a loop that learns

- **Status:** design only (2026-10-05). No code was changed. Written by an Opus 5.5 architect pass.
- **Inputs read:**
  - `HELPER_BLIND_EVAL_5.md` and `HELPER_BLIND_EVAL_6.md`;
  - the `OFFLINE_HELPER_V2.md` sections FINAL 6, 7 and 8;
  - the owner's live turns in `output/ai_logs/copilot_turns.jsonl` (records 1938-1946);
  - the scenario bank in progress, `_easy_claude_work/eval/bank/bank_A.jsonl` (250 items) and `bank_B.jsonl` (195 items);
  - the code cited below as `file:line`, with line numbers as of today. Another worker is editing four of these files, so the numbers will drift; the anchors are the function names.
- **Owner brief (2026-10-05):** people will ask all kinds of things. Build 500-1,000 real-world scenarios and train on them every time, so the helper learns. The beta must amaze people, not annoy them.

---

## 1. Diagnosis: why fixing phrases has stopped paying off

### 1.1 The numbers

| round | how-to | question | vague | edit | back-and-forth | good+ok | good only | HARMFUL |
|---|---|---|---|---|---|---|---|---|
| blind 5 (R5) | 73 | 50 | 75 | 75 | 40 | 63% | 23% | 5 |
| blind 6 (R6) | 100 | 90 | 88 | **50** | **53** | 69% | 37% | **5** |

**Meanwhile, the in-house sets scored perfectly:**
- fix7 dev: 58/58 in Node and 56/58 in-app;
- in-app specs: 43/43;
- helper_eval: 297/297.

**What R5 → R6 shows:**
- **Retrieval-style turns climbed to 88-100%:** how-to, questions and vague asks. The search ranker and the topic pins fix those.
- **Compositional turns stayed at 50-53%:** edits and conversations.
- **HARMFUL stayed at 5 per round.**

The fixes beat whatever set they were tuned on, then miss the next blind set. That is overfitting at the phrase level.

### 1.2 Why: six structural causes, each tied to code

**1. The edit reader is an ordered cascade of regex readers that return early.**

| measure | value | where |
|---|---|---|
| fix-pass tags | 77 | `js/spb-offline-answer.js` |
| `*_RE` constants | 69 | same file |
| regex literals | about 139 | same file |
| fixed-order readers in `pre7` | 15 | `:1253-1270` (`p7Save → p7Pick → p7List → p7Topic → p7Compare → p7Other → p8Copy → p7Else → p7Grad → p7Outline → p7Somewhere → p7Tone`) |
| early returns in `route1` | about 40 | `:1381-1540` |

Every fix adds a reader in front of others, so each new pass breaks something in an older one:
- **b5-020:** "will my paint look the same in iracing" was read as a copy-look request. The same-side reader fired before the question guard. It was fixed by a special guard (FINAL 7 late fix).
- **"make the hood look mean":** this put the look on the whole car (FINAL 6). `lookStep` ran before the part reader.
- **b6-020:** "same on the right" fell through, because `P7_OTHER_RE` (`:1201`) covers "the other side" but not "on the right".

The real space is roughly 10 actions × 8 target kinds × 6 look slots × keep-clauses × references. Readers that each enumerate a slice of that product can never cover it.

**2. There are three brains, three representations, and guards spread across them.**
- **The three representations:**
  - offline builder steps, `{what, act, colour, finish, tex, extra}` (`js/spb-offline-builder.js:219`);
  - pro-edit plan ops, `{target, colour, look, texture, outline, gradient, copy}` (`js/spb-pro-edit.js:592` `plan`, `:645` `planCore`, `:980` `compile`);
  - DeepSeek's free tool calls (`refinish`, `edit_zone`, `add_zone`, `apply_scheme`, ...) in `js/spb-pro-ai.js:352` `makeTools`.
- **Each safety rule lives in one path only:**
  - `scopeGuard` (builder `:868`) guards only the offline ▶ Run;
  - `protectDecals` (`pro-ai:307`), `specOnlyGuard` (`:233`), `refinishAskFirst` (`:1947`), `objectCard` (called at `:635`, defined at `:2446`) and `ownColourZone` guard only model tool calls;
  - the in-app `postCheck` returns early for offline results (`pro-ai:3567`: `r.offline`).

So a fix in one path does not carry over. Pass 8 had to touch five files to teach one idea, copy-look (FINAL 8, "What changed").

**3. App guards argue with the model after the fact.**
- **Owner record 1944:** DeepSeek did the right thing: `refinish {target:"yellow", object:"spray can", layer:"Logos", colour:"#a600ff", look:"chrome"}`.
- **What the app did:** the named-object guard in `compile` turned it into `needs_the_buyer_to_choose`, and the reply said "Nothing changed yet".
- **Same pattern elsewhere:**
  - record 1941: the model could only say `look:"chrome"` (= `f_chrome`), never the numbers' real `fo_saturday_chrome` at scale 0.15;
  - records 1940 and 1943: the offline reader produced an answer card, then "Brushed metal shine on the Logos layer".

A free tool-caller with a rule check after each call is the wrong contract. The model cannot see the rules until it breaks one, and each break costs a whole round.

**4. Conversation state is scattered over at least seven stores, written only by some paths:**
- `CS {pending, topic, list}` (`offline-answer:1635`);
- `env.last` from `lastCtx()` (`:1539`), which re-reads the pro-ai log;
- `colMem` (`:1545`);
- `lastEditCtx()` (`pro-ai:1587`): it returns `null` when the newest AI log entry has no `editCtx`;
- `_offlineLast`, `_advLast` (`pro-ai:36`, `:3029`);
- `_cmpAsk`.

So a pinstripe drawn by the element designer, an answer card or a list leaves "the last change" empty. That is b6-020's "no earlier change" and b6-018's "second one on the front bumper" with no list. The DeepSeek STATE (`pro-ai:136` `state()`) has no conversation block at all: no last target, no last change set, no list just offered.

**5. Words get normalised away before they are understood.**
- `fuzz()` (`pro-edit:171`) replaces any word of 6 or more letters that is one edit from a vocab word.
- So "crushed" became "brushed". The FINAL 8 sweep found 30+ more real words eaten the same way: nearly→pearly, mellow→yellow, violent→violet, strikes→stripes...
- The fix was a deny-list (`SAFE_WORDS`, `pro-edit:158`). That is the same whack-a-mole one level down.

**6. Verification sits in the test harness, not in the product.**
- **What the harness has:** the checks that catch HARMFUL turns, the in-app codes E, K, O and G (FINAL 7 "Harness upgrades"): kept parts untouched, the refinement keeps the earlier change, an outline is no fill, a gradient exists.
- **What the app has:**
  - a mask probe on offline Run only (`scopeGuard`);
  - on the model path, a colour-share check, a spec-only paint diff and a vision critic (`pro-ai:3560-3627` `postCheck`). It runs only when `deep`, and its repair is another free model turn.
- **The gap:**
  - nothing in the app measures decal pixels or outside-scope pixels before it commits;
  - nothing checks the reply against what was measured. b5-044 claimed "the red is now burgundy" when only 58-150 pixels changed.

### 1.3 The failure classes and where each lives

| class | evidence | cause above |
|---|---|---|
| Follow-ups bleed scope: "make it white instead" → whole car | b6-008, b6-020 T3, b5-060 | 1, 4 |
| A finish-only request with "except X" repaints the paint and decals | b6-040 (90% of the car pink, decals wiped, reply claims finish-only) | 2, 6 |
| Pinlines, outlines and flames not applied | b6-008, b6-009, b6-012, b5-049; there is no flames graphic kind (`spb-pro-graphics.js:38-162` = outline, rings, speed_lines, strokes, stripes, waves, chevrons, checker, dots, rays, lightning) | 1, missing primitive |
| A pinline "between colours" recolours both colours | b6-042 | missing primitive, 6 |
| Relative follow-ups go unresolved: same on the right / the second one / thinner / flip it / less red | b6-003, b6-010, b6-018, b6-020, b5-050 | 4, missing primitives |
| Copy-look unsupported | owner 1940-1946 (patched in pass 8 across 5 files) | 2 |
| A named layer is overridden by a guard | owner 1944 | 3 |
| The owner's words are spell-corrected ("crushed" → "brushed") | owner 1943 | 5 |
| DeepSeek is blocked by guards; STATE is missing (scale) | records 1941, 1944, 1945 | 3, 4 |
| A question is run as an edit, or a list request is applied | b5-019, b5-052, b6-003 | 1 |
| Overclaims in the reply | b5-044, b5-042, b6-040 | 6 |

**Conclusion:** the helper does not lack phrases. It lacks:
1. one representation of what the buyer meant;
2. one place that turns that meaning into operations;
3. one memory of the conversation;
4. a measurement gate that sits between "planned" and "committed".

Without those, every new phrase is a new reader, and every reader is a new way to collide.

---

## 2. The proposed architecture

```
 buyer text ─┬─ OFFLINE READER (rules + lexicon) ─┐
             ├─ DEEPSEEK (frame-filler, forced) ──┼─► INTENT FRAME ─► PLANNER ─► OP LIST ─► VERIFIER ─► COMMIT ─► REPORTER
 MCP client ─┴─ spb_do {frame} ───────────────────┘        ▲          (rules)   (zone-kit,   (static mask   (applyQueue  (from the
                                                           │                     graphics)   + rendered     + undo)      measurements)
                                          CONVERSATION STATE (one store, written only after a commit or an offer)
```

**The rule:** every producer writes the same frame. Only the planner turns meaning into app operations. Nothing is committed until the verifier has measured it against the frame.

### 2.1 The INTENT FRAME (v1 schema)

```jsonc
IntentFrame {
  "v": 1,
  "turn": "t-0193",                 // id; the conversation store keys on it
  "producer": "offline|deepseek|mcp|chip",
  "act": "change|answer|list|ask_back|undo|redo|save|nothing",
  "ops": [Op],                      // act=change: one per clause, in the order said
  "question": { "topic": "spec.roughness", "text": "..." },                       // act=answer
  "list": { "of": "finishes|colours|patterns", "query": "gold", "for": Target },  // act=list
  "keep": [Target],                 // sentence-level keep-clauses ("but leave the doors")
  "decals": "protect|include",      // default protect; "include" only on explicit words
  "confidence": 0.0,                // the producer's own, 0..1
  "missing": ["colour"],            // slots the producer could not fill -> the planner asks ONE question
  "alts": [{ "slot": "look.finish", "said": "crushed", "maybe": "brushed" }],  // never applied silently
  "said": "raw buyer text"
}
Op {
  "verb": "recolour|refinish|restyle|outline|pinline|stripe|gradient|pattern|graphic|copy_look|adjust|retarget|hide|show",
  "target": Target,
  "except": [Target],               // op-level keep
  "look": Look,                     // what it should become (absent slots = unchanged)
  "source": Target,                 // copy_look: where to copy FROM
  "copy": ["colour","finish","spec","scale","pattern"],
  "relative": { "prop": "width|scale|lightness|saturation|hue|gloss|metal|strength|stops", "dir": -1, "amount": "little|lot|half|0.3" },
  "ref": Ref                        // the target or op comes from earlier turns
}
Target {
  "kind": "body|part|layer|colour|element|object|zone|box|graphic",
  "parts": ["left side"],           // car-map names (CAR.parts); "both sides" -> two names
  "portion": "front half|lower third|...",
  "layers": ["Logos"],              // PSD layer names, exact
  "colour": { "word": "yellow", "hex": "#fff200" },  // with layers/parts = "the yellow IN Logos"
  "element": "numbers|sponsors|stripes|logos",
  "object": "spray can",            // a descriptor only: it never overrides a named layer
  "zone": "zone_25a5...",           // an exact zone id (follow-ups, copy sources)
  "between": [Target, Target]       // pinline: the seam between two colour regions
}
Look {
  "colour": { "word": "candy red", "hex": "#9b0f1a" },
  "gradient": { "stops": ["#ff0000", "#000000"], "axis": "front_to_rear|top_to_bottom|radial", "start": 0.0 },
  "finish": { "family": "chrome", "key": "base::f_chrome", "keep_colour": true },   // keep_colour => spec-only
  "pattern": { "id": "<catalogue id>", "concept": "flames", "opacity": 0.4, "scale": 0.5 },
  "spec": { "metal": 230, "rough": 30, "clearcoat": 16, "patterns": ["holographic_flake"] },
  "scale": 0.15, "rotation": 0,
  "stroke": { "width": "thin|medium|thick", "px": 10, "sides": "both|inner|outer" }
}
Ref { "to": "last_change|last_target|offered_item|opposite_side|last_colour_region|turn", "index": 1, "turn": "t-0191" }
```

**How it maps to today's code:**
- **Adapters are cheap.** The frame deliberately mirrors today's builder step (`what` = target, `act` = verb, `colour` / `finish` / `tex` = look) and the pro-edit op. The step's `extra.outline`, `extra.gradient` and `extra.exclude` and the op's `op.copy` become `stroke`, `gradient`, `except` and `copy`. So adapters in both directions cost little (stage S1).
- **The builder's step cards become the frame editor for offline users.**
- **One validator:** `SpbIntent.validate(frame, env)` checks that the part names exist in the car map, that the layers exist and that every hex is well-formed.

### 2.2 The PLANNER: frame to operations (deterministic, no model)

`js/spb-intent-planner.js` (new) is one table of verb × target-kind handlers. Each handler returns app operations built from the primitives that already exist, plus the new primitives the failures show are missing.

| verb | target kinds | today's primitive (reused) | NEW primitive |
|---|---|---|---|
| recolour / refinish | body, part, layer, colour, element | `SpbProEdit.compile` (`pro-edit:980`) / `compileRequest` (`:1148`), then zone-kit `edit` (`zone-kit:668`) | none |
| refinish + `keep_colour` | any | the documented Foundation path: `base::f_*` + colour `source` (MCP server instructions; `pro-ai` prompt rule 16c, `:70`) | **`finishOnly(target, except)`**: one primitive that always (a) picks an `f_` Foundation, (b) keeps colour `source`, (c) limits to the body-paint layers minus `except`, (d) declares a paint-diff ceiling of 0.5% for the verifier. Kills b6-040. |
| outline | part, layer | graphics `outline` (`graphics:38`, `outlineMask` `:218`, `layerMask` `:212`), reached via `pro-edit:1122-1123` | **outline of an element / object / box** (number panel = numbers-layer alpha, dilated); **stroke width stored on the zone** (`px`), so "thinner" can edit it |
| pinline | `between:[A, B]` | none | **`seamMask(A, B, w)`** = dilate(mask A, w/2) ∩ dilate(mask B, w/2), minus decals. Paints only the seam, never recolours A or B. Kills b6-042. |
| stripe / graphic | part | `add_graphic` kinds (`graphics:43-162`); element designer `SpbProDesign.offlineElement` | **a `flames` graphic kind** (part-space u/v, licks running back from the front). Fallback: a catalogue flame pattern clipped to the part. |
| gradient | part, layer | `partGradient` (`pro-edit:974`) + the zone-kit fit | **`gradientEdit(zone, {reverse, stopShift})`** for "flip it" and "less red" |
| copy_look | any, from `source` | `zoneRef` / `copyLook` / `lookLine` (`zone-kit:656-667`), `lookSource` (`pro-edit:1188`) | none: one entry point for both of today's copies |
| adjust (relative) | ref to a zone | hue / sat / bright, `scale` and the strength fields in the zone-kit `SCHEMA` | **`relativeEdit(zone, prop, dir, amount)`** with fixed steps: thinner = px × 0.6; "half that" = × 0.5; "less red" = red stop moved 25% toward the other stop |
| retarget | ref to the last change set | pass 8 `retarget8` (offline only) | **`moveChange(set, newTarget)`**: undo the set, re-plan the same ops on the new target, keep it as one undo entry |
| hide / show | element, layer | `edit_layer` (`pro-ai:464`) | none |

**Precedence rules.** Written once and tested once (today they are spread across guards):
1. **A named layer beats a named object.**
   - `object` is only a descriptor.
   - When the colour sits in several layers and the buyer named none, the frame gets `missing:["layer"]` and the ask lists `colourLayers(word)` (`pro-ai:2476`). That is owner case A.
2. **`keep`, `except` and `decals:"protect"` are subtracted from every op's region in the planner,** not in a guard after the tool call. The planner uses zone-kit `excludedUnion` (`zone-kit:563`) and the body-layer limit that `protectDecals` computes today (`pro-ai:307`).
3. **A follow-up with `ref` inherits the previous op's target and changes only the slots it names.** "make it white instead" swaps the colour on the same outline zone; the scope never widens (b6-008).
4. **A `finish` without a `colour` on a part or the body means `keep_colour: true`,** unless the buyer named a colour.
5. **A question never produces ops.** `act:"answer"` carries no `ops`. This makes today's `qGuard` structural.
6. **`alts` are never applied.**
   - The original word stays.
   - When it fills no slot, it goes into `missing`, and the planner asks.

### 2.3 CONVERSATION STATE (one store)

`js/spb-convo-state.js` (new) = `window.SpbConvo`.
- **Who writes it:** only the executor, after a commit, and the reporter, when it shows a list or chips.
- **Who reads it:** all three producers. DeepSeek's STATE gets it as a `convo` block next to `zones`.

```jsonc
{
  "last_change": { "turn": "t-0191", "frame": {}, "zone_ids": ["zone_..."], "undo_id": "e42",
                   "targets": [], "look": {}, "verbs": ["outline"] },
  "last_target": {},                // also set by a question about a part
  "last_offer": { "kind": "finishes|colours|chips|layers", "items": [{ "label": "...", "key": "..." }], "turn": "t-0190", "ttl_s": 600 },
  "last_colour_region": { "word": "red", "hex": "#c8102e", "layers": ["Body"] },
  "pending": { "frame": {}, "missing": ["colour"], "asked": "Which colour for the trim?" },
  "history": [ { "turn": "...", "frame": {}, "committed": true } ]      // last 12
}
```

**Resolution.** `SpbConvo.resolve(ref, frame)` is deterministic:

| the buyer says | resolves to |
|---|---|
| "same on the right" | `opposite_side(last_change.targets)` |
| "the second one" | `last_offer.items[1]` |
| "both" | the parts of `last_change` plus the new part |
| "it / that / them" | `last_target` |
| "thinner", "flip it", "less X" | `relative` on `last_change.zone_ids` |
| "that's not the hood, that's the roof" | `retarget` |
| "go back" | undo `last_change.undo_id` |

**Migration of the old readers.** This store replaces, one at a time:
- `lastEditCtx` (`pro-ai:1587`);
- `lastCtx` (`offline-answer:1539`);
- `CS.list` (`:1635`);
- `_offlineLast`.

Each old reader becomes a thin shim over `SpbConvo`.

### 2.4 The pre-commit VERIFIER (renders and measures)

`js/spb-intent-verify.js` (new) runs on every path (offline, online, MCP), between "planned" and "kept".

**Stage A: static, no render, about 5-20 ms.**
- **Regions.** Each planned zone's region mask comes from `Z.probeRegion` (`zone-kit:841`).
- **Allowed area.** `allowed` = the union of the target masks (parts / layers / colour regions / seam / outline band), minus `keep`, minus `except`, minus the decal mask when `decals:"protect"`.
- **Measures:**

  | measure | meaning |
  |---|---|
  | `outside_pct` | region outside `allowed`, as % of the car |
  | `decal_px` | region ∩ decal layers |
  | `fill_ratio` | outline / pinline: region as a share of the part; must be ≤ 0.6 |
  | `empty` | 0 visible pixels |

This generalises `scopeGuard` (`builder:868`), which today covers only the offline Run and only "named parts".

**Stage B: rendered, existing preview, about 1-3 s.**
1. Apply the queue as `applyQueue` does (`pro-ai:772`), with the undo snapshot.
2. Wait for `Z.whenSettled`.
3. Diff `previewImage(768)` and `specPreviewImage` against the snapshot taken before.

Measures:
- `paint_changed_in_allowed_pct`, `paint_changed_outside_pct`, `spec_changed_pct`;
- `decal_px_changed`;
- gradient monotonicity along its axis;
- each wanted colour's visible % inside the target, from the existing `previewPalette` and `zoneColourProblems` (`pro-ai:3488`).

These are the harness codes E / K / O / G from FINAL 7, moved into the product.

**Verdicts.** A deterministic repair is tried before any model is involved:

| finding | repair (one try) | if it still fails |
|---|---|---|
| outside_pct > 1% | intersect the zone region with `allowed` (add `exclude` / `island`) | roll back, ask: "This would also change X% outside the roof. Do it anyway?" |
| decal_px > 0 with protect | add the body-layer limit (the `protectDecals` logic) | roll back, say which layer blocks it |
| `keep_colour` and paint diff > 0.5% | swap to the `f_` Foundation of the same family + colour source | roll back |
| outline fill_ratio > 0.85 | re-plan as an outline band | roll back |
| wanted colour < 1% visible | raise priority above the covering zones (`probeRegion` knows which they are) | commit; the reporter says what is hidden |
| empty | drop the op | the reporter says "not done: ..." |

The model `critic` (`pro-ai:3540-3557`) stays as an optional extra on design and scheme turns only. It is never the gate.

### 2.5 The honest REPORTER

`js/spb-intent-report.js` (new). The reply is built from the verifier's numbers, never from intentions:

```
Done: thin gold outline on the left door (6 px, 0 px outside the door).
Untouched: numbers, sponsors (0 px changed).  Not done: spoiler (no body paint on this car).
[Undo] [Thicker] [Same on the right]
```

- **Chips** are the verb's natural follow-ups. They are written to `SpbConvo.last_offer`, so "the second one" works.
- **Online path:**
  - DeepSeek may rephrase the reply in a friendlier voice.
  - A post-filter drops any sentence that names a part, colour or count that is not in the report.
  - Today's `REVIEW` prompt (`pro-ai:95`) asks the model to audit itself; this makes the audit structural.
- **Under 2% changed:** the reply says so, with the real number. This replaces the pass-7 honesty notes and closes the b5-044 overclaim class.

### 2.6 DeepSeek becomes a frame-filler

**Today:** a free tool-caller with about 30 tools, `REVIEW` and `REFINE` rounds, and guard fights (records 1941-1945).

**New contract:** one forced call, `submit_frame(frame)`, with `tool_choice` set to that function.
- The server already forwards `tool_choice` (`server_routes/ai_copilot_routes.py:587`), so no server change is needed.
- Before submitting, the model may call these read-only tools, unchanged:
  - `find_finishes`, `finish_details`, `suggest_finishes`;
  - `describe_paint`, `get_help`, `look_at_paint`.

**What DeepSeek receives:**
- STATE: zones with scale (pass 8, `zonesForModel`, `zone-kit:936`), the layers, the `colourLayers` index and the car parts;
- `SpbConvo`;
- the frame schema, the 10 worked examples in §2.8, and the planner's precedence rules as text.

**What it is for:** what offline rules cannot do.
- Paraphrase: "make it look like it's been through hell" becomes a weathered pattern plus a matte finish.
- Taste: "something Gulf-ish".
- Long sentences.

The planner, verifier and reporter are identical for both producers.

**Cost:** one call plus 0-2 lookups per turn, instead of 3-4 calls (records 1939/1941/1942: 3 calls, about $0.0012 per turn). The prompt also shrinks, because the tool descriptions (`pro-ai:464-687`) leave the default turn.

**Fallback:** the legacy tool loop stays behind a flag, for Codex and for design jobs (`apply_scheme`, `add_graphic`).
- A frame with verb `graphic` can carry `{tool, args}` as an escape hatch.
- The planner passes that through, and the verifier still checks it.

### 2.7 MCP

- **New tools:**
  - `spb_do {frame}`;
  - a dry run, `spb_check {frame}`, which returns the planner ops and the stage-A verifier numbers.
- **Where they are defined:** in the app's tool list. `mcp/server/tools.json` is generated by `scripts/build_mcpb.py` (`mcp/server/index.js:23`).
- **Existing tools:** the 22 current tools (`spb_refinish`, `spb_add_zone`, ...) stay.
- **New server instructions:** "describe the change as a frame with `spb_do`; use the low-level tools only for schemes and graphics".
- **Same verifier:** MCP edits pass the same verifier as the app. That closes the MCPSCEN class of "problems_found_by_app: []" (`pro-ai:924`, `:998`).

### 2.8 Ten worked examples from the real failures (frame → plan → verifier)

Frames are abbreviated: `T` = target, `L` = look.

| # | turn(s) | frame | plan / verifier |
|---|---|---|---|
| 1 | **b6-040** "everything except the roof gets a pearl finish" | `{act:change, ops:[{verb:refinish, T:{kind:body}, except:[{kind:part, parts:[roof]}], L:{finish:{family:pearl, keep_colour:true}}}]}` | `finishOnly` gives `base::f_pearl` + colour source on the body layers minus the roof. Verifier: paint diff 0.0%, decal_px 0. Today: 90% of the car turned pink. |
| 2 | **b6-020** "red pinstripe on the left door" | `{verb:stripe, T:{kind:part, parts:[left door]}, L:{colour:red, stroke:{width:thin}}}` | Committed. `SpbConvo.last_change` = that zone. |
| | T2 "same on the right" | `{verb:stripe, ref:{to:opposite_side}}` | Resolves to the right door with the same look. Today: "no earlier change", because `lastEditCtx` was null. |
| | T3 "change both to gold" | `{verb:adjust, T:{ref:last_change ∪ previous}, L:{colour:gold}}` | Edits 2 zones' colour. Verifier: outside_pct 0. Today: the whole car went gold. |
| 3 | **b6-042** "fine silver pinline between the red and white" | `{verb:pinline, T:{kind:colour, between:[{colour:red},{colour:white}]}, L:{colour:silver, finish:{family:metallic}, stroke:{width:thin}}}` | `seamMask(red, white, 6px)` minus decals. Verifier: fill_ratio < 0.05 of each region, sponsors 0 px. |
| 4 | **b6-008** "outline the number panel in gold" | `{verb:outline, T:{kind:element, element:numbers}, L:{colour:gold, stroke:{width:medium}}}` | Outline of the dilated numbers alpha. |
| | T2 "thinner" | `{verb:adjust, ref:{to:last_change}, relative:{prop:width, dir:-1}}` | px 10 → 6. |
| | T3 "make it white instead" | `{verb:adjust, ref:{to:last_change}, L:{colour:white}}` | The same zone. Today: the whole car went white. |
| 5 | **b6-009** "orange hood stripe" | `{verb:stripe, T:{parts:[hood]}, L:{colour:orange}}` | — |
| | T2 "thin black line each side of it" | `{verb:outline, T:{kind:zone, ref:last_change}, L:{colour:black, stroke:{width:thin, sides:outer}}}` | Outline of the stripe zone's mask. Verifier: outside the hood 0. Today: both side panels were painted black. |
| 6 | **owner B, 11:45** "In the Logos layer make the yellow on the spray can the same color and finish that's on the numbers now - the purple with Saturday chrome crushed down" | `{verb:copy_look, T:{kind:colour, colour:yellow, layers:[Logos], object:"spray can"}, source:{kind:element, element:numbers}, copy:[colour,finish,spec,scale], alts:[]}` | "crushed down" is a scale word, never fuzzed. Plan: `copyLook(numbers zone)`. The named layer wins over the object (rule 1). Verifier: 0 px outside Logos (the pass-8 gate measured 1.13% changed, 0 outside). |
| 7 | **owner A, 11:44** the same, with no layer named | `missing:[layer]`, `T.object:"spray can"` | One ask with chips from `colourLayers('yellow')` (Logos, Car_Decal, Contingency Decals, White Accent) plus "draw a box". Nothing changes. |
| 8 | **b6-003** "show me gold options" | `{act:list, list:{of:finishes, query:gold}}` | The reporter lists 4 real keys and writes `last_offer`. |
| | T2 "the second one" | `{verb:refinish, L:{finish:{key: last_offer[1]}}, T:{ref:last_target or body}}` | Today: it applied gold, then asked "which one?". |
| 9 | **b6-010** a gradient on the hood, then T2 "flip it" | `{verb:adjust, ref:last_change, relative:{prop:stops, dir:-1}}` | `gradientEdit(reverse)`. |
| | T3 "less red" | `{verb:adjust, relative:{prop:hue, amount:little}, T:{kind:colour, colour:red, ref:last_change}}` | The red stop moves 25% toward the other stop, and the gradient is kept. Today: flattened to a solid colour. |
| 10 | **b5-053** "thats not the hood thats the roof" | `{verb:retarget, ref:last_change, T:{parts:[roof]}}` | `moveChange` = undo + re-plan as one undo entry. |
| | **b5-060** "just a little on the hood" (after a whole-car stealth black) | `{verb:refinish, T:{parts:[hood]}, L:{finish:{family:gloss, keep_colour:true}}, ref:{to:last_target}}` | Additive. The planner never undoes a committed change unless `verb:retarget` or `act:undo`. |

### 2.9 What each of today's modules becomes

| file | becomes | stays | goes (after parity) |
|---|---|---|---|
| `js/spb-offline-answer.js` (1,648 lines) | **Offline reader**: Q&A retrieval + a frame emitter | search, cards, topic pins, `casualCore`, `qGuard` (as `act:answer`), `tidy` | `pre7` readers (`p7*`, `p8Copy`, `retarget8`), `convo`, `followup`, `relx`, `CS`: replaced by lexicon → frame slots + `SpbConvo.resolve` |
| `js/spb-offline-builder.js` | **Frame editor UI** (a step card = an op) | the UI, `readAs`, the turn log `tl*` | `toPlan` (→ planner), `scopeGuard` (→ verifier stage A) |
| `js/spb-pro-edit.js` | **Resolver library** the planner calls | `parseClause` (as a slot-filler), `resolveColour`, `wantFor`, `lookScan`, `regionFor`, `compile`, `lookSource`, `partGradient` | `fuzz` as a rewriter (it becomes `alts`), the router heuristics inside `plan` |
| `js/spb-pro-ai.js` (Codex-shared) | **Online frame-filler + executor host** | `applyQueue`, undo/redo, `state()` (+ `convo`), the read-only tools, the legacy loop behind a flag, `window.spbProAI` API | `protectDecals`, `specOnlyGuard` and `refinishAskFirst` move into planner rules / verifier repairs (thin shims remain); `postCheck` becomes verifier stage B |
| `js/spb-pro-zone-kit.js` | executor primitives | everything | — |
| `js/spb-pro-graphics.js` | primitive library | everything | — (+ `seam`, `flames`, stored stroke `px`) |
| `mcp/server/tools.json` | generated | the 22 tools | — (+ `spb_do`, `spb_check`) |
| `server_routes/ai_copilot_routes.py` | unchanged proxy | `/api/ai/chat` (tool_choice already passed, `:587`), `/api/ai/turn-log` (`:646`) | — (+ `/api/ai/feedback`, local only) |
| new | `spb-intent-frame.js`, `spb-intent-planner.js`, `spb-convo-state.js`, `spb-intent-verify.js`, `spb-intent-report.js` | — | — |

---

## 3. The learning loop

### 3.1 The bank: format as written today, plus the normalisation it needs

`_easy_claude_work/eval/bank/` currently holds 445 of the planned 1,000 items:

| file | items | kinds |
|---|---|---|
| `bank_A.jsonl` | 250 | edit 125 / convo 125, 471 turns |
| `bank_B.jsonl` | 195 | howto 90 / question 70 / trouble 35 |

There is also `bank_A_tags.jsonl`, which tags each item with:
- `act`: recolour 59, finish 41, pattern 25, theme 18, numbers 13, stripes 12, layer_scoped 10, unpaintable 10, spec_only 10, gradient 9, copy_look 6, except 6, scale 5, ...;
- `fu`: refine 32, reverse 16, propagate 16, correction 12, swap 10, choose 9, ...

**Expected outcome per turn:**
- **A turns:** `{do: change|answer|ask|nothing, must_change[], must_not_change[], colour, finish_class, spec_only, refers_to_turn, note}`.
- **B turns:** `{do: answer|offer_options|ask, answer_must_cover[], gold_ids[], must_not, refers_to_turn}`.
- **Every item:** a `harmful_if` sentence.

**Normalisation needed:**
- **Scope strings.** 95% of the 3,377 scope strings map directly onto car-map names, element names or `<name> layer`. 107 distinct strings do not ("cab", "hood stripe", "trim", "lower doors", "numbers outline", ...).
  - `bank_norm.py` maps them to frame `Target`s.
  - Anything still unmapped is graded by the judge only.
- **Frame-level expectations.** `expect.frame` is filled from the turn's fields: `do` → `act`, `must_change` → `T`, `colour`, `finish_class` and `spec_only` → `L`, `refers_to_turn` → `ref`.

### 3.2 Grading: four tiers, cheapest first

| tier | what | how | cost | items |
|---|---|---|---|---|
| G0 frame | the producer's frame vs `expect.frame`: act, target set, colour family, finish class, keep_colour, ref | Node, no app (`convo_test.js` style; `OA_FILE` / `SX=1` loaders) | ~5 ms/turn | all 1,000, every commit |
| G1 plan | planner ops + stage-A numbers on a recorded car env (owner V6 payload + ARCA + a flat sheet) | Node with a recorded `probeRegion` mask pack per car | ~50 ms/turn | all |
| G2 pixels | in-app: paint/spec diff inside/outside `must_change`, decals, codes E/K/O/G, undo exactness, panel text vs `answer_must_cover` keywords + `gold_ids` | `pw/convo_inapp.py` on test server 59879 | 26-33 s per change turn (measured: final6 51.8 min/120 turns = 25.9 s; blind6 29.1 s; fix7_after 32.8 s) | nightly subset |
| G3 judge | a blind model reads the reply + before/after sheet, grades good/ok/bad/HARMFUL against `harmful_if` | Sonnet, explicit `model`, writes JSONL as it goes | ~6-10k tokens/turn | 10% sample + every G2 harmful/disagreement |

- **Machine-checkable share:** about 85% of A turns (scope, colour, spec_only, ref) and about 70% of B turns (gold_id hit + keywords). The rest is judge-only.
- **The judge is calibrated**, the same way the Finish Law fits thresholds: its verdicts are compared monthly with the owner's on 30 items, and agreement must stay ≥ 85%.

### 3.3 Splits, rotation, contamination

| split | share | who may read the item text |
|---|---|---|
| `train` | 50% | fixers (tuning set, like `eval/fix7/dev.jsonl`) |
| `dev` | 20% | fixers see per-class scores and failing ids, not the text, until a stage closes |
| `sealed` | 30% | **nobody except the nightly runner**, which prints aggregates per class only |

- **Rotation:** after each blind round (about every 2 weeks), 1/3 of `sealed` moves to `train` and is replaced by new items written blind by a fresh author (persona mix kept: newbie, ESL, angry, artist, league, truck, dirt...).
- **Contamination:** an item's text shown to a fixer is tagged `seen:true` and can never be used for scoring again (blind5 is already tagged CONTAMINATED in FINAL 7).

### 3.4 The regression bank: it only grows

- **Location:** `_easy_claude_work/eval/bank/regress.jsonl`. It uses the same format plus `origin` (owner log record id, blind id, beta feedback id) and `fixed_in` (stage/pass).
- **Rule:** every failure that gets fixed adds its turn(s) here, and they never leave.
- **Seeds (about 40 items):**
  - the 10 HARMFUL items from blind 5/6;
  - owner records 1940/1943 (spray can A/B);
  - the owner's 2026-10-04 T1 pink-numbers sentence;
  - b5-034 (hexagon);
  - the fix7 dev failures n01/n03.
- **Gate:** 100% of G0+G1 on every commit, 100% of G2 nightly. One harmful = red build.

### 3.5 The nightly in-app run

- **Projected size and runtime:**
  - **Turns:** at the current mix, 1,000 items ≈ 940 change/convo turns (A averages 1.88 turns/item) + about 500 answer turns.
  - **Change turns:** 940 × 28 s ≈ 7.3 h.
  - **Answer turns:** skipping the preview wait brings these to about 6 s, so 500 × 6 s ≈ 50 min.
  - **Total:** about 8 h on one app.
- **Nightly plan (about 3 h on one test server):**
  - the whole `regress` bank (~40 items, 25 min);
  - all `sealed` change turns in rotation: 1/3 per night, about 300 turns, 2.3 h;
  - G0+G1 over all 1,000 (2 min).
- **Weekly:** the full bank on two app instances (59879 + a second test port, about 4 h each).
- **Run settings:**
  - the offline helper always;
  - an online pass with DeepSeek on the same items on Sunday: about 1,440 turns × about $0.0015 ≈ $2.2.
- **Output:** one `SUMMARY` line per class into `eval/nightly/<date>.jsonl`, plus a diff against the previous night. A drop of 3 points or more in any class, or any harmful result, opens a row in the wiki trouble spots.
- **Scheduling:** through the existing scheduled-tasks mechanism, with `model` set explicitly to Sonnet for the G3 sample. The runner prints verdict lines only (the token mandate).

### 3.6 Beta telemetry (local first, opt-in out)

- **Local log, always on.** `output/ai_logs/copilot_turns.jsonl` already records every turn (`server_routes/ai_copilot_routes.py:44`, `:646`; 5 MB rotation). Add to each record:
  - `frame`;
  - `plan` (op verbs + zone ids);
  - `verify` (the stage A/B numbers, repairs, verdict);
  - `report` (the reply text).
  No images. Nothing leaves the machine.
- **"This didn't do what I asked" button,** on every AI reply bubble. One tap does two things:
  - it writes `output/ai_logs/feedback.jsonl`: the turn texts of this conversation (≤ 6 turns), frames, verify numbers, zone diff, app version, an optional one-line note;
  - it offers **Undo** right there (b6-067: "not feeling it" got no undo).
- **Opt-in sharing:**
  - a settings toggle, "Help improve the helper", off by default;
  - before the first send, a dialog shows the exact payload.
- **The payload is scrubbed:**
  - `SENSITIVE_RE` (`pro-ai:33`) is applied, and digit runs (iRacing IDs), paths and user names are blanked, as `check_setup` already does;
  - no paint pixels, no PSD, no layer names beyond the role (`numbers`/`logos`/`body`/`other`);
  - the car is identified by its folder id only.
- **Ingest** (owner decision: a small endpoint next to the R2 update feed). The feedback becomes a draft scenario:
  1. A Sonnet worker turns it into bank format, with `expect` drafted and `origin:feedback`.
  2. The owner or an agent confirms it.
  3. It lands in `regress` once fixed, or in `train` if it is new behaviour.

  This closes the "every single time, train it to be better" loop without any personal data.

### 3.7 BETA SHIP GATE (all must hold on the latest nightly + weekly)

| metric | where | gate | today |
|---|---|---|---|
| HARMFUL | sealed G2+G3 and regress | **0** | 5 per blind round |
| regress bank | G0+G1+G2 | **100%** | n/a |
| good+ok, all kinds | sealed, judge | **≥ 90%** | 69% (R6) |
| good+ok, edit | sealed | ≥ 85% | 50% |
| good+ok, back-and-forth | sealed | ≥ 80% | 53% |
| good+ok, how-to / question | sealed | ≥ 95% | 100 / 90 |
| strict good, all | sealed | ≥ 60% | 37% |
| decal pixels changed when not asked | G2, all change turns | 0 on ≥ 99.5% of turns | not measured in-app |
| paint outside the frame's scope | G2 | ≤ 0.5% of the car on ≥ 99% of turns | not measured in-app |
| reply claims vs measurements | reporter self-check | 100% match | overclaims seen (b5-044, b6-040) |
| asks on a clear request | G0 (`do:change` items with no ambiguity tag) | ≤ 10% | not measured |
| undo exact | `undo_inapp.py` | 8/8 + every regress undo | 8/8 |
| offline turn latency p95 (text → preview settled) | G2 timings | ≤ 4 s | ~26 s per harness turn, mostly harness waits; measure app-only |
| online cost per turn (mean) | turn log | ≤ $0.003 | about $0.0012-0.002 |

---

## 4. Migration plan: small stages, each one ships

**Applies to every stage:**
- **Gates (all must pass):** `helper_eval.js` (also with `SX=1`), `builder_test`, `ft2_corpus`, `edit_corpus`, `stack_test`, `convo_test` (default, `--held`, `--file=eval/fix7/dev.jsonl`, `--specs`), `garble_test`, the in-app gate `pw/convo_inapp.py specs=specs.json` (0 harmful), `pw/undo_inapp.py` 8/8, `hidden_feature_check -q`, and from S0 onward G0+G1 over the bank plus `regress` at 100%.
- **Intended behaviour changes** update corpus expectations with a `why` field (the `why7` precedent).
- **Two-copy rule:** sync with `node scripts/sync-runtime-copies.js --write`, bump each changed file's `?v=` in **both** `paint-booth-v2.html` files, and add new `<script>` tags to both.
- **Sequencing:**
  - One agent per stage; at most 2 stages in flight, and only when their files don't overlap.
  - Nothing starts on the four files the other worker holds (`spb-offline-answer.js`, `spb-offline-builder.js`, `spb-pro-edit.js`, `spb-pro-ai.js`) until that pass lands and the wiki board frees the lane.

| stage | what ships | files | effort | tokens | risk | kills |
|---|---|---|---|---|---|---|
| **S0** Measure first | `bank_norm.py` (scope strings → Targets, `expect.frame`); G0 frame grader + G1 plan grader with recorded mask packs (V6 owner payload, ARCA, flat sheet); `regress.jsonl` seeded (~40); `convo_inapp.py` reads bank format; answer turns skip the preview wait | `_easy_claude_work/eval/` only | 4 h | ~180k | none | none; it makes every later stage measurable |
| **S1** Frame + shadow log | `SpbIntent` schema, `validate`, adapters `stepsToFrame` / `opsToFrame` / `toolCallsToFrame`; every turn logs its frame. **No behaviour change** (byte-identical gate results) | new `js/spb-intent-frame.js`; 1 hunk each in `offline-answer` `route` (log), builder `tlStart` record, `pro-ai` `finish` (log); turn-log record +`frame` | 5 h | ~250k | low | none; G0 can now score the live producers |
| **S2** Verifier A (static), all paths | Stage-A mask verdicts + repairs before commit on offline Run, the model `applyQueue`, MCP. Ships as **warn** (logged, reply note), then **enforce** once false rejections are under 2% on the bank | new `js/spb-intent-verify.js`; builder `run` (replaces the `scopeGuard` call, `:868`); `pro-ai` `applyQueue` pre-commit hook (1 hunk, `:772`) | 8 h | ~400k | medium (false rejects; hence warn first) | **HARMFUL scope bleed**, "except X" wiping decals (b6-040), pinline recolouring both colours (b6-042 → refused rather than wrong), b6-009, b5-047 |
| **S3** Verifier B + reporter | Rendered diff (paint/spec/decal/outside), gradient and outline checks, honest report + undo chip on every change; `postCheck` delegates | `spb-intent-verify.js`; new `js/spb-intent-report.js`; `pro-ai` `postCheck` (1 hunk, `:3560`) | 7 h | ~350k | medium (+1-2 s per turn) | overclaims (b5-044, b6-040 reply), spec-only paint drift, silent "nothing showed" |
| **S4** One conversation store | `SpbConvo` written by every commit (offline, model, element designer, MCP) and every offer; old readers become shims; STATE gains `convo` | new `js/spb-convo-state.js`; shims in `offline-answer` `lastCtx` / `CS` (`:1539`, `:1635`), `pro-ai` `lastEditCtx` + `state()` (`:1587`, `:136`, 2 hunks) | 7 h | ~350k | medium | "same on the right" / "the second one" / "no earlier change" (b6-018, b6-020, b6-003), follow-up scope bleed (with S2), DeepSeek missing state |
| **S5** Planner + new primitives | `finishOnly`, `seamMask` pinline, element/object outline, stored stroke `px` + `relativeEdit` (thinner / half that), `gradientEdit` (flip / less red), `flames` graphic, `moveChange` retarget, unified `copy_look` | new `js/spb-intent-planner.js`; `spb-pro-graphics.js` (+seam, +flames); `spb-pro-zone-kit.js` (stroke px, additive SCHEMA); `pro-edit` outline-element branch | 14 h | ~650k | medium-high (new pixels; finish-law look check on flames) | pinlines/outlines/flames not applied (b6-008/009/012, b5-049), pinline between colours, thinner/flip/less red (b6-010, b5-050), finish-only + except, part correction (b5-053) |
| **S6** Offline reader emits frames | Lexicon → slots (parts, layers, colours, looks, stroke words, scale words, ref words) for the covered classes; frame → planner; legacy `route1` stays as the fallback for the rest; `fuzz` becomes `alts` | `offline-answer` (frame path before `pre7`), `pro-edit` `fixText` / `fuzz` (`:171`), builder renders ops | 12 h | ~600k | medium (routing changes) | spelling "corrections" (crushed → brushed + 30 words), reader-order collisions (b5-020 type), question-as-edit, list-as-edit (b5-019, b5-052) |
| **S7** DeepSeek frame-filler | `submit_frame` forced by `tool_choice`; read-only lookups allowed; prompt = schema + §2.8 examples + rules; flag `frameMode`, A/B on the bank (offline vs online), default on when online ≥ offline on every class | `pro-ai` (tool + prompt + one branch in `runTurn` `:1068`); **no server change** (`ai_copilot_routes.py:587` already forwards `tool_choice`) | 8 h | ~400k | medium (model drift; a pinned prompt test in G0) | DeepSeek blocked by guards, the named layer overridden (owner 1944), copy-look online, 3-4 calls → 1-2 |
| **S8** MCP frames | `spb_do` / `spb_check`; server instructions updated; tools.json regenerated | `pro-ai` tool list, `scripts/build_mcpb.py` run, `mcp/server/tools.json` | 4 h | ~150k | low (additive) | MCP scope and decal slips (MCPSCEN class) |
| **S9** Learning loop live | the "didn't do what I asked" button + Undo; local `feedback.jsonl`; opt-in share dialog + scrubber; feedback → draft scenario; nightly and weekly runners; split rotation scripts | builder or `pro-ai` bubble UI (1 hunk), `ai_copilot_routes.py` (`/api/ai/feedback`, local write), `_easy_claude_work/eval/nightly/` | 7 h | ~300k | low | the "learns every time" mandate; the b6-067 no-undo case |
| **S10** Retire legacy readers | Delete one `p7*` / `cv*` reader family per change, once G0-G2 show the frame path at parity on its class | `offline-answer`, `pro-edit`, `pro-ai` (guard shims) | ~2 h each | ~80k each | low per step | maintenance cost: 77 fix tags, 69 `_RE` constants |

**Totals:**
- S0-S9: about 76 agent-hours and about 3.6M tokens, spread over 10 stages. The largest is S5, at about 650k.
- Projected beta-ready point: after S7, with S9's button and local log pulled forward into the beta build.

**Order rationale:**
- Measurement comes first (S0-S1).
- Then the safety net that removes HARMFUL, whatever the parse (S2-S3).
- Then memory (S4), then capability (S5).
- Only then do the producers switch to frames (S6-S7). By that point the planner, verifier and reporter they feed are already proven on the legacy paths.

### 4.1 What must stay Codex-compatible (`js/spb-pro-ai.js` is shared)

1. **`window.spbProAI`** (`:4350`): every existing export name and its signature (`ask`, `finish`, `log`, `colourLayers`, `refresh`, ...). Additions only.
2. **Tool names and parameter schemas** in `makeTools` (`:352`). `mcp/server/tools.json` is generated from them, and Codex's MCP runs (MCPSCEN) call them. New tools (`submit_frame`, `spb_do`, `spb_check`) are added; none are renamed or removed.
3. **Log entry shapes:** the `_log` entries (`role`, `undoable`, `undone`, `zdiff`, `editCtx`, `lines`) and the undo snapshot path (`undoSnapTake` / `undoRestore`, `:3922-3999`). The verifier commits through `applyQueue`, never around it.
4. **`mcpContext` / `elementRunIdentity` stale-paint checks.** The verifier passes them through.
5. **Turn-log record keys** (`/api/ai/turn-log`). New fields are added (`frame`, `plan`, `verify`, `report`); existing ones are never renamed.
6. **Shape of the edits:**
   - new logic lives in the new `js/spb-intent-*.js` / `spb-convo-state.js` files, loaded before `spb-pro-ai.js`;
   - each change in `pro-ai` is a small hunk tagged `HELPER V3 S<n>`;
   - `SPB_AI_FRAME=0` (a settings flag) restores the legacy loop exactly.
7. **The zone-kit `SCHEMA` and the graphics kinds** change additively only (`stroke_px`, `seam`, `flames`). Old payloads and saved projects must load unchanged.

### 4.2 Open owner decisions

1. **Where opt-in feedback is sent.** One option is an endpoint beside the R2 update feed; the alternative is email export only.
2. **Ship-gate thresholds in §3.7.** These are proposals. Like the Finish Law, they should be fitted to the owner grading about 30 sealed items once.
3. **Flames.** Either a new procedural graphic (S5), or catalogue flame patterns clipped to a part as the beta stopgap.
4. **What "silver accent" / "trim" means by default** (b5-034, still open from FINAL 7). The frame needs one default: outline of the named part or layer, thin, metallic.

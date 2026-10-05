# RETOUCH deep functional test — 2026-07-19

Owner ask: *"TEST the tools and if they don't make sense or do not work correctly I'd like you to fix them."*

Method: real `MouseEvent` strokes dispatched on `#paintCanvas` (the actual `canvas.onmousedown` /
`onmousemove` / `onmouseup` path), pixels sampled from the composite canvas before/after each stroke.
Test bed painted **through the app's own tools**, never by writing to a layer canvas directly.

## Result: 11/12 already correct, 1 real defect found and fixed

| Tool | Verdict | Evidence (R channel) |
|---|---|---|
| Color Brush | WORKS | paints, 4/4 sample points change |
| Pencil | WORKS | paints, 4/4 sample points change |
| Dodge | WORKS | mid-gray 128 -> 151/154/154/145 (+23/+26/+26/+17) |
| Burn | WORKS | mid-gray 128 -> 105/102/102/111 (-23/-26/-26/-17) |
| Recolor | WORKS | 128,128,128 -> 255,1,1 with fg=red |
| Smudge | WORKS | smears white edge into gray, -124/-76/-7 |
| Blur Brush | WORKS | hard edge 128/255 -> 136/208 (softens) |
| **Sharpen Brush** | **WAS BROKEN -> FIXED** | before: 3 strokes moved 201 -> 201 (nothing). after: blurred edge 128/159/200/235/255 snaps back to 128/255/255/255/255 (+96/+55/+20) |
| Clone Stamp | WORKS | after Alt+click source: gray 128 -> cloned red 255,0,0 |
| Healing Brush | WORKS | blemish 16 -> 23 / 16 -> 0 |
| History Brush | WORKS | gray 128 -> painted 255 -> **exactly** 128 restored |
| Save History Snapshot | WORKS | enables History Brush (`_getHistoryBrushSourceSnapshot()` true) |

## The one real defect: Sharpen Brush was a no-op

`paintSharpenBrush()` in `paint-booth-3-canvas.js`. Two compounding causes:

1. The low-pass sampled only the **4 touching neighbours** (a cross), so on any soft ramp
   neighbour ~= centre and `(centre - average)` collapsed to ~0.
2. The already-small result was **halved again** by a stray `* 0.5`.

Max possible move was `(centre - avg) * 0.25` ~= 1 pixel value, i.e. invisible. Blur, by contrast,
uses a real `blurR` box neighbourhood and mixes at full `localStr` (it moved 47 in one pass).

Fix: Sharpen now reuses **Blur's own box radius** (`sharpR = clamp(round(radius/80), 1, 2)`) for the
low-pass and mixes at the same `localStr`, making it the true inverse of Blur.

## Second finding (UX, not a defect): the whole menu is inert on a flat TGA

Every one of the 11 brushes requires **LAYER mode + a selected editable layer**:

- in ZONE mode -> *"<Tool> only edits layers in Layer Mode - switch the toolbar to LAYER"*
- in LAYER mode with no layer -> *"<Tool> needs an editable selected layer in LAYER mode"*

A flat TGA (the normal workflow) has no layers, so the biggest remaining menu in the toolbar does
nothing but emit warning toasts until the user imports a PSD or adds a layer. The tools are correct;
the *discoverability* is the problem — the user only learns the requirement after picking a tool and
dragging. Clone / Heal / History Brush additionally require a source or snapshot, and those three
already say so clearly, which is the model the menu itself should follow.

## MASK menu — 11 ops, all mathematically exact

Test bed: a 300x150 rect region committed to Zone 1 via `useRegionForZone()` (46,354 px).

| Op | Measured | Verdict |
|---|---|---|
| Grow 1px / 2px | +914 / +1836 px | correct, scales linearly |
| Shrink 1px / 2px | -906 / -1804 px | correct, scales linearly |
| Feather 2px | +3696 px, coverage sum +8 | correct — adds soft partial-value edge, total coverage held |
| Invert | 46,354 -> 4,147,950 | **exact**: 4,194,304 - 46,354 |
| Mirror | px identical, centroid 848 -> 1199 | **exact**: 2047 - 848 |
| Fill Holes | punched 1,875 px in 3 holes, recovered **exactly** 1,875 | exact |
| Smooth Edges | ragged comb edge -> -1,575 px | correct — trims teeth, fills notches |

Fill Holes and Smooth Edges first measured 0 change against a clean rectangle — that is *correct*
(no holes, no rough edge), not a bug. They were re-tested against a punched block and a comb edge.

## SELECT menu — 6 tools, all functional

| Tool | Measured |
|---|---|
| Select All Color | 4,073,468 px sampled |
| Smart Region Fill | 4,069,812 bounded px |
| Elliptical Marquee | 36,026 px for a 300x150 drag — vs pi*150*75 = 35,343. A true **ellipse**, not a rect (which would be 45,000) |
| Move Selection Border | activates, mode `selection-move` |
| Pick Layer Element | activates, mode `layer-pick`, with guidance toast |
| Zone Pick | activates, mode `zone-pick` |

## Undo / Redo — works on the data; one display question left UNVERIFIED

| Check | Result |
|---|---|
| Undo fires | yes — *"Undid layer: color brush on layer"* |
| Redo fires | yes — *"Redid layer: color brush on layer"* |
| Redo restores painted pixel **exactly** | yes — back to `[0,255,0,255]` |
| Layer data after undo | correctly emptied (layer coverage 0%) |
| Any permanent data loss | **no** — re-committing the paint path restores the car to 100% coverage |

**Left unverified (needs a human eyeball in a real foreground browser):** after painting on a layer,
the composite `paintCanvas` in my test tab held *only the isolated layer* — the car was not visible
underneath, and the SOURCE pane rendered blank. This is almost certainly the hidden-tab artifact
again, and the code says so by construction:

- `_flushPaintImageDataToCurrentSurface()` keeps `paintImageData` **pinned to the editable layer**
  while a layer stroke is in progress — that is deliberate, so retouch engines edit isolated pixels.
- It then calls `_scheduleActiveLayerCompositePreview()`, whose own comment reads: *"the visible
  canvas must remain the whole PSD stack ... RAF-batch one composite preview"*.
- That restore runs inside `requestAnimationFrame`, **which never fires in a hidden tab**.

So in a normal visible browser the composite should be rebuilt on the next frame and the car should
remain visible. I could not confirm it: both automated browser surfaces available here report
`document.visibilityState === 'hidden'`, so no animation frame ever runs. Given three earlier
"defects" this session all traced to this same root cause, this is reported as **not confirmed** —
worth one manual check: add a layer, paint a stroke, and see whether the car stays visible in SOURCE.

## Round 2 — Layers panel, shortcuts, transform commit, money path (all verified)

| Area | Result |
|---|---|
| Layer card tools (10) | ALL work — MIRROR pixel-exact at `2047-x`, MERGE keeps both patches, OUTLINE laid 1,160 px, RENAME/DELETE/DUPE/FLATTEN/FX/PICK ITEM verified |
| Card curation | 9 -> 6: PICK ITEM + FX cut (3-4 duplicate entry points), FLATTEN -> panel header; new **+ Blank** button (panel had NO blank-layer path) |
| Keyboard shortcuts | 10/10 correct: C/S/Q/I/D/J/F/H/B/E all arm the advertised tool; X swaps fg/bg; Ctrl+T opens layer transform; Cancel ends it |
| Transform commit | geometrically exact: 180° about bbox center (1174.5,1011) — green dab predicted (847,1272) measured (852,1276); red predicted (1047,1372) measured (1051,1375) |
| Money path | eyedropper click -> Add Color -> chip stored with tolerance 40 + toast "(3 colors stacked)" |
| Spec Tools dialogs | all 4 open with a selection, 1-24 ms |
| Copy Mask | dropdown builds 9 rows; copyMaskToZone copies **exactly** 46,354 px |
| Move Selection Border | +199 px centroid for a 200 px drag |
| FX dialog | 5 effects store `{enabled,color,opacity}` correctly; visual compositing rides on Codex's QA'd SPB-93 lane (not pixel-verifiable in a hidden tab) |
| NEW warning | stroke starting outside the active selection now toasts guidance (was a silent no-op — brushes clip to selection); verified warns outside / silent inside |

Test residue cleaned: #000000 test chip removed, test layers deleted, test region masks cleared —
owner's zone state restored to `#f70202`, `#ff0000`.

## Test-methodology traps hit along the way (recorded so the next agent doesn't repeat them)

1. **Background-tab timer throttling.** `document.visibilityState === 'hidden'` makes Chrome defer
   `setTimeout` to roughly once a minute. A **300 ms** sleep measured **>45 s**. Every apparent
   "renderer freeze" in this session was this, not the app. Fix: drive tools **synchronously** with
   no timers, since the brush path is synchronous anyway.
2. **`requestAnimationFrame` does not fire in a hidden tab** either — pixel-sampling anything that
   goes through `schedulePreview()` falsely reads as "no change".
3. **The layer canvas object is replaced when it grows.** Caching `layer.img` / `bbox` and its 2D
   context yields a detached canvas: reads show stale pixels forever. This produced a completely
   false "dodge/burn/recolor are silently broken" result. Always re-resolve the layer per read, or
   sample the composite `#paintCanvas` (stable, never replaced).
4. **Confounded test beds.** Blur/sharpen do nothing on a *uniform* region (correct), dodge/burn
   cannot move pure black (correct), and recolor with fg == the existing colour is a no-op (correct).
   Always run a **control** (Color Brush over the identical region) before calling a tool broken.

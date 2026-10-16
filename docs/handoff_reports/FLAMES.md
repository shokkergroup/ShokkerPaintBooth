# FLAMES (2026-10-05) - real flame licks placed on a car PART

Owner decision 2026-10-05: "Build real flame licks" before the beta. The 20 finishes on the Flames shelf are fire TEXTURES
(blobs, clouds, rings, stars - ENC_READER_FIX.md section 10); none draws a lick. This lane adds real lick GEOMETRY that is
drawn on a named part (hood, each side, roof...) and applied as ordinary zones, so every existing engine path (spec, decals
on top, undo, export) is reused.

## 1. Findings (what exists)
- Flames shelf = BASE_GROUPS["Flames"] in paint-booth-0-finish-data.js (20 ids flame_*), engine engine/paint_v2/flames_2026.py
  (paint_<id>/spec_<id>, whole-canvas fields). A base finish has no idea which part it is on or where the front is: its
  spec fn does not even get the zone mask (compose._invoke_base_spec_compat) and is cached per seed. => licks cannot be
  done right as a base finish.
- js/spb-pro-graphics.js already draws crisp DESIGN GRAPHICS in PART space (u front->rear, v roof-line->rocker) from the car
  library (SpbProCar.findIsland: box + front + up) and turns each colour into a sheet mask that SpbProZone uses as a zone
  region (region.graphic). KINDS is a shared object, so a new kind can be registered from a separate file.
- Numbers / sponsors on top: zone-kit region.exclude ["numbers","sponsors"] (PSD roles or the elements finder on flat paints).

## 2. Design
- New file **js/spb-pro-flames.js** (loaded right after js/spb-pro-graphics.js). It registers graphic kind `flames` into
  SpbGraphics.KINDS (no edit to spb-pro-graphics.js) and exposes `window.SpbFlames` (plan / apply / check / STYLES).
- Geometry (part space, x = front -> rear, y = roof-line -> rocker): a solid band at the FRONT (trailing edge a flat arc), then
  N licks. Each lick integrates a heading along its centre line: a shared-phase S-wave (neighbours flow together instead of
  crossing; sway capped to ~half a spacing on long panels) plus a tip hook (curl * smoothstep^2), width = fat root tapering
  to a point ((1-t)^taper with a belly), root cap melting into the band. Long panels (sides, L/H > 2.4): fewer, fatter
  licks, hooks all sweep toward the roof-line (1 in 5 down). Squat panels (hood): longer reach, hooks alternate.
  Tribal adds 1-3 barbs per blade (short hooks curling the other way). True fire = 3 nested layers (outer + forked wisps,
  mid, core) with their own phases.
- Each colour role is a zone (SpbProZone.batch, one undo step "Flames"): outline ring (stroke of every lick minus the union
  = a ring OUTSIDE the flame, outline_w px), fill (gradient front->rear, mirrored for parts whose front is on the right),
  true-fire outer / mid / core. region.exclude ["numbers","sponsors"] keeps decals stamped on top.
- Spec per role = the zone finish: hotrod fill base::f_candy (200/15/16), outline base::wet_look, tribal base::wet_look,
  ghost base::f_pearl (100/40/16), true fire f_candy outer/mid + wet_look core. Flames therefore read glossy candy against a
  satin body in the sim.

## 3. App bug found + fixed on the way (paint-booth-2-state-zones.js)
normalizeBaseGradientStopsForPayload decided percent-vs-fraction PER STOP (`pos > 1 ? pos/100 : pos`). A gradient fitted to a
part that starts 1% into the sheet (zone-kit remaps stops to sheet positions, e.g. 1 / 23 / 46) sent the stop at 1 as the
fraction 1.0, sorted it LAST, and the zone rendered flat in its middle colour (measured: the side flames came out exactly
#ff8a00). Now decided once for the whole list. Affects ANY fitted gradient whose first stop lands at 1%.


## 4. Second pass after looking at 1:1 (owner's ARCA PSD, 2048 native renders)
What the eye found on the first in-app contact sheet, and the fix for each (all in js/spb-pro-flames.js, geometry spliced from _easy_claude_work/flames/geom.js):
- 8 px staircase wherever a flame met a panel edge (the car map's part mask is a 256 grid). Fix: the clip is the part mask SOFTENED (box blur + threshold, grows `bleed` px, rounds the stairs) AND the PSD's template **Mask layer read at full resolution** (real panel edges, +2 px seam bleed; `uv:false` turns it off; flat paints without a Mask layer use the softened clip alone). Hood edge now follows the real curved panel line.
- Straight vertical cut in every gap between two licks (the band's flat trailing edge). Fix: band trailing edge is SCALLOPED (an arc behind each lick root, shallow floor in the gaps), same for the true-fire mid / core bands. Every crotch is now a curved U.
- Ghost flames came out the SOURCE paint's yellow on a navy Body zone. Fix: `bodyColour` reads the top-most solid zone that repaints the part (catch-all, or a colour pick of the paint's body colour) before the paint file.
- Tribal on a long side panel read as tangled tentacles. Fix: tribal blades on a long panel are capped at ~6.5 lick spacings long (stubby hooked claws like on the hood).
- Every style: the side's front read as a solid slab ~27% of the panel. Fix: on long panels the band is 45% shorter, roots thinner (0.5 spacing), less belly, so licks part sooner.
- Tribal auto colour: black on any strong colour (white blades on red vanished into the white decal bars), white only on dark dull bodies.
- New: `replace` (default true): pressing another style on the same parts SWAPS the flames in the same undo step (verified: hot rod -> tribal -> Undo = hot rod back).
- New: `ok:false` + warning when a part is unknown on this car (nothing landed).

## 5. API for the helper / MCP (window.SpbFlames, js/spb-pro-flames.js; no edits needed in the helper files to use it)
```
SpbFlames.apply({ part: 'hood' | 'left side' | 'right side' | 'roof' | 'sides' | [list], style: 'hotrod'|'tribal'|'ghost'|'truefire',
                  colours?: ['#rrggbb',...], outline?: '#rrggbb'|false, outline_w?: px@2048, licks?, length?, base?, scale?, curl?, band?, seed?,
                  finish?: 'base::<id>', keep_decals?: true, replace?: true, uv?: true, bleed?: 8, label?: 'Flames' })
  -> { ok, applied[], warnings[], zones[names], removed[names], notes[] }        ONE undo step; zones go on top of the stack
SpbFlames.plan(opts)  -> { ok, ops (SpbProZone.batch ops), zones, notes }      no side effects (preview the zone list / explain before doing)
SpbFlames.check(opts) -> error string | null      SpbFlames.STYLES -> per-style about + defaults
region.graphic {kind:'flames', part, style, colours:[fill, outline, mid, core], ...}  works in any zone-kit spec (colour index 0..3)
```
Style aliases accepted: 'hot rod', 'classic', 'traditional' -> hotrod; 'real fire', 'realistic', 'fire' -> truefire.
Suggested helper wording: "flames on the hood" -> part 'hood'; "down the sides" -> 'sides'; "hot rod" -> hotrod; "tribal" -> tribal; "ghost" -> ghost; "realistic/real fire" -> truefire. A colour named by the buyer goes in `colours` (tribal/ghost: one colour; hot rod: fade front->tips).
Zones per job: tribal 1, ghost 1, hot rod 3 (outline + one fade per sheet orientation), true fire 4.

## 6. Encyclopedia Do-it (via the sanctioned build)
- New hand-written article `data/encyclopedia/flame_licks.json` (`flame_licks.flame_job`, aliases "flame licks", "flames on the hood", "flames down the sides", "hot rod flame job", "real flame licks", "true fire flames") with four Do-it buttons `{do:'flow', id:'flames', style, part}`; `python scripts/ai_atlas/build_encyclopedia.py` re-run (js/spb-encyclopedia-data.js regenerated, not hand-edited).
- js/spb-encyclopedia.js: `normAct` keeps `style`/`part`; `runAction` sends a flow action that carries a `style` to `SpbFlames.apply` (draws at once, one Undo); without SpbFlames it falls back to the old flow path.
- Verified in-app (59879): Start Hot rod -> 3 flame zones; Start Tribal -> swapped to 1 zone; Undo -> hot rod back.
- `node _easy_claude_work/enc_v2_test.js`: flame_licks.json PASS; the one FAIL (`NO ANCHOR paint-booth-2-state-zones.js:12221`, cited by finishes.json) is pre-existing in HEAD, not from this lane.

## 7. Gates and timings
- No catalogue finish was added (flame zones use existing base::f_candy / wet_look / f_pearl), so Finish Law / uniqueness have nothing new to score. Coverage/fine-detail opt-out is DELIBERATE and DOCUMENTED in the module: `SpbFlames.COVERAGE_EXEMPT` / `FINE_DETAIL_EXEMPT` with written reasons (CLAUDE.md 0b). Engine exempt dicts (flame_math.COVERAGE_EXEMPT) were not touched: no engine change, no restart.
- Baseline for the record: `python scripts/spb_finish_law.py --group "Flames"` -> the existing Flames shelf (20 base finishes, untouched) fails 19/20 law axes (the "blobs / rings" problem that started this lane); Fractured Flames 11/75. Output: _easy_claude_work/flames/finish_law_flames.txt.
- Render at 2048 (/preview-render replayed at preview_scale 1.0 on the shared TEST server 59879; noisy, 3 runs): body only 1.6-2.1 s; + tribal or ghost (1 zone) 2.1-2.9 s; + hot rod (3 zones) 2.3-4.9 s; + true fire (4 zones) 4.3-4.9 s; hood-only hot rod 2.9-3.5 s. Each zone costs ~0.5-1 s server-side (region mask + finish at 2048). Tribal / ghost sit inside the 3 s budget; hot rod / true fire on three parts go over it on this loaded server. Client-side apply (mask drawing) 430-1050 ms. Lever if needed: `outline:false` (hot rod -1 zone) or one part at a time.
- Server quirk seen while measuring (not a flames bug): replaying the app's own preview body at preview_scale 1.0 sometimes returned a render WITHOUT the zones (~1 s, the untouched car); deleting `changed_zone`/`zone_hashes` and a fresh `preview_nonce` per request fixed the harness.

## 8. Contact sheets looked at (1:1, paint over spec), all in _easy_claude_work/flames/inapp/
hoods_v5.png (hood x4 styles, final geometry), sides_v6.png (left side x4), tribal_v7_* + v7_check.png (tribal black on red; logos ON: SHOKKER hood logo, spray-can decal and numbers stay on top of the hot rod flames), hotrod_v4_hood_1x.png (UV-edge clip), truefire_v4_leftfull_1x.png, roof_small.png (hot rod on the roof, behind the roof number and the Menards strip).
Verdict by eye: hood - all four styles clean and distinct (hot rod fade + blue pinstripe, tribal hooked blades, ghost subtle same-hue pearl, true fire 3-layer wisps). Sides - hot rod and true fire good; ghost fine (subtle by design); tribal now compact claws at the front fender. Not judged: the 3D sim view (the flat sheet shows UV dead space around panels; edges follow the PSD Mask layer).

## 9. Files touched (two-copy rule done: root -> electron-app/server/, `sync-runtime-copies.js --check` clean except a report-only engine file that is not mine)
js/spb-pro-flames.js (new, ?v=20261005fl9) · paint-booth-2-state-zones.js (gradient stop fix, ?v=spb-stable-zone-seed-v1-fl1) · js/spb-encyclopedia.js (?v=20261005rf1-fl2) · js/spb-encyclopedia-data.js (rebuilt, ?v=20261005gap1-fl1) · paint-booth-v2.html (both copies) · data/encyclopedia/flame_licks.json (new). Client JS only: no server/engine restart needed, a Ctrl+R picks it up. No commits.

## POLISH 1 (2026-10-05, opus worker; js/spb-pro-flames.js only, no server / engine code changed, 59879 not restarted)

### Render budget: measured, hood + both sides, logos on, owner's ARCA PSD, test server 59879
Round-robin, 5 rounds, the app's own preview body re-posted at scale 1.0 (2048), server `elapsed_ms`. "old" is the pre-polish module loaded into the same page for an A/B comparison.

| case | zones | runs (ms) | median |
|---|---|---|---|
| no flames (base) | 0 | 923 655 696 655 712 | 696 |
| hot rod (fill + outline, default) | 2 | 1983 1890 2006 1968 1956 | 1968 |
| hot rod, outline:false | 1 | 1376 1344 1288 1425 1422 | 1376 |
| tribal | 1 | 1141 1208 1113 1228 1284 | 1208 |
| ghost | 1 | 1357 1191 1104 1221 1249 | 1221 |
| true fire (default layers:1) | 1 | 1364 1360 1280 1457 1514 | 1364 |
| true fire layers:2 | 2 | 2146 2211 1896 2049 2279 | 2146 |
| OLD hot rod | 3 | 2242 2535 2455 2750 2455 | 2455 |
| OLD true fire | 4 | 2961 2774 2789 3265 3281 | 2961 |

The server was less loaded in this run than in an earlier one: base 1.47 s, old hot rod 3.2 s, old true fire 4.0 s, new hot rod 2.8 s. The ratios held. Every style is now at or under 2.0 s, and the worst run was 2.0 s. The old true fire went over 3 s in 2 of 5 runs.

### What changed
- **Zone model.** Each flame zone costs about 0.6 s of server time at 2048, whatever its size, because a solid or gradient base colour sends the engine down the full-canvas paint path.
  - Now one colour role = one zone across all parts.
  - The front-to-rear fade is ONE gradient zone with sheet-percent stops (`fit:false`), one stretch per part orientation, which works because the hood's front is on the right and the sides' front on the left. It falls back to one zone per orientation only when the stretches overlap.
  - True fire defaults to **`layers:1`**: one zone. Its 5-stop fire gradient (yellow-white front, orange, red, deep-red tips) colours nested tongues. Thin body-colour channels (`gap` px, default 4) are cut around the mid tongues and re-closed inside the front band.
  - `layers:2` gives outer + inner zones. `layers:3` (or `core:true`) gives the old 3 layer zones.
  - The hot rod outline stays ON by default (2.0 s).
- **Despeck.** The flames mask drops 8-connected specks under ~250 px. Wisp crumbs had pushed the spec crop fast path (more than 12 regions) onto a full render.
- **Side front slab.**
  - On long panels, hot rod, ghost and true fire are now sized in lick spacings, like the hood: 5 licks, the longest reaching 7.5 spacings (true fire 9.5) past a base of about 3–5% of the panel.
  - Bodies are fat (belly 0.45, half-width 0.42 spacing).
  - The hooks fan out: the upper half hooks up and the lower half hooks down, so no hook closes an "eye" over a neighbour.
  - The hood geometry is unchanged: same random stream, verified identical.
- **Tribal.** A new `tribalGeometry`: separate sickle blades with a thin root, a thick shoulder at about 1/4 of the length, and a long taper to a crisp point that hooks over. The convex side bulges and carries 1–2 thorn barbs leaning toward the tip. There is no front band by default, blades are 0.31 spacing wide, and there is body colour between every pair.
- One Undo per press and swap-not-stack were re-checked in-app with `polish/undo_check.js`: hot rod, then true fire, then Undo brings hot rod back, then Undo leaves no flames. Decals stay on top, panel-edge masking and the ghost body colour are unchanged, and paint-booth-2-state-zones.js was not touched.
- Two-copy rule: `electron-app/server/js/spb-pro-flames.js` is synced, and `?v=20261005fl10` is set in both paint-booth-v2.html copies.

### Looked at 1:1
- `_easy_claude_work/flames/inapp/polish_hoods.png`: hood × hot rod / tribal / ghost / true fire. Top row logos on, bottom row logos off. With logos on, the big hood logo covers most of the hood flames, which is correct decal-on-top behaviour.
- `_easy_claude_work/flames/inapp/polish_sides.png`: left side × the 4 styles, logos on.
- On the ARCA side, the white heart-rate bars are part of the paint artwork, not decals, so the flames paint over them. The "32" and the spray-can art stay on top.

### Left / ideas
- **Engine-side win, not done here.** The paint path for a solid or gradient zone could be cropped to the zone's bbox. That would cut every zone's ~0.6 s, help all multi-zone liveries, and let true fire `layers:3` back under budget. It needs engine work and a server restart.
- The hot rod outline draws a pinstripe between neighbouring licks where they nearly touch. That reads as the classic look, but `outline:false` gives a plain fill.
- The small channel hooks at the extreme top and bottom corners of the true-fire front band are visible at 1:1 but minor.
- The existing Flames base-finish shelf failing the Finish Law (19/20) is still a separate lane.

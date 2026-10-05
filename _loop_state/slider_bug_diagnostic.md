# SPB Scale/Rotation Slider Regression — Diagnostic (Read-Only Pass)

Owner symptom: BASE/COLOR/SPEC SCALE + ROTATION sliders no longer go below 1.00x; suspected zone-scope leak.

## Summary verdict

- **Failure mode 1 (clamping): CONFIRMED for Base Scale.** The runtime setter `setZoneBaseScale` (in `paint-booth-2-state-zones.js`) clamps to `Math.max(SCALE_BASE_MIN, …)` where the constant **`SCALE_BASE_MIN = 1.0`** is declared at L194. So even though the slider HTML now correctly emits values down to 0.05, the JS handler immediately snaps anything < 1.0 back up to 1.0.
- **Failure mode 1b (handlers missing): CONFIRMED for Color Scale + Spec Scale.** The HTML calls `setZoneBaseColorScale`, `setZoneSpecScale`, `stepZoneBaseColorScale`, `resetZoneBaseColorScale`, `stepZoneSpecScale`, `resetZoneSpecScale`. **None of these functions are defined in the monster file.** They exist ONLY in the modular file `js/zones/base-material-controls.js`, but that module's `install()` is never invoked anywhere — `SPBZoneBaseMaterialControls.install(...)` appears in zero source files. Moving the Color Scale / Spec Scale slider therefore does nothing (or throws `ReferenceError` if the inline `oninput` is parsed strictly). This explains why the owner perceives "things changed in the past few days messed it up" — those two sliders were just re-added to the HTML on 2026-05-22 but their backing handlers were never wired up.
- **Failure mode 2 (zone-scope leak): NOT happening.** Every setter operates on `zones[index].*` (per-zone state). `paint-booth-5-api-render.js` emits per-zone `base_scale` / `base_color_scale` / `spec_scale` (L88, L481, L518, L2012, L2025, L2255, L2268, L2533, L2649). `server.py` clamps per-zone with `SCALE_MIN=0.01` (L103) — allows sub-1.0. No globals shadow these. The owner's perception of "leaks to whole canvas" is most likely the **clamp-to-1.0** symptom: when you can't go below 1.0, the base/color/spec stays at full canvas scale and looks "untiled-down", which reads as "applies everywhere". When the clamp is removed and the handlers exist, per-zone tiling will work as expected.
- **Rotation sliders**: WORKING. Base Rotation handler clamps `0..359` correctly (paint-booth-2-state-zones.js:7550). Color Rotation / Spec Rotation handlers exist only in the modular file (also un-installed), but they are **not currently exposed in the HTML** (no Color Rotation / Spec Rotation sliders are rendered — see slider grep at L1720-1881; the only rotation slider in this row is Base Rotation). So no active rotation regression. Note: owner said there are "rotation" sliders for color/spec too — those slots currently render NOTHING (handlers absent + HTML never restored). The 2026-05-22 restore comment mentions "three paired sliders" but only scale variants got restored, not rotation.

## Slider definitions (current working tree)

All 3 sliders live inside `renderZoneDetail()` in `paint-booth-2-state-zones.js`. Each is followed by step/reset buttons that call the same family of handlers.

| Slider | File:Line | min | max | step | Handler called | Handler defined? |
|---|---|---|---|---|---|---|
| Base Rotate | paint-booth-2-state-zones.js:1720 | 0 | 359 | 1 | `setZoneBaseRotation` | YES — monster file L7550 (also modular L68, not installed) |
| Base Scale | paint-booth-2-state-zones.js:1741 | **5** | **500** | 5 | `setZoneBaseScale` | YES — monster file L7502, **but clamps to SCALE_BASE_MIN=1.0** |
| Color Scale | paint-booth-2-state-zones.js:1751 | **5** | **500** | 5 | `setZoneBaseColorScale` | **NO** — only in modular L147, un-installed |
| Spec Scale | paint-booth-2-state-zones.js:1761 | **5** | **500** | 5 | `setZoneSpecScale` | **NO** — only in modular L202, un-installed |
| Pattern Scale | paint-booth-2-state-zones.js:1875 | 10 | 400 | 5 | `setZoneScale` | YES — monster file L7473 (clamps SCALE_PATTERN_MIN=0.10, fine) |
| Pattern Rotate | paint-booth-2-state-zones.js:1881 | 0 | 359 | 1 | `setZoneRotation` | YES — monster file L7525 |

There are NO color-rotation or spec-rotation sliders rendered in the current HTML. If owner wants them, they need to be added back (HTML + ensure handlers exist).

## Value flow

```
slider input (HTML, min=5 means 0.05x)
  → oninput="setZoneBaseScale(i, value/100)"
  → JS handler (monster L7502)  -- THIS IS WHERE THE BUG IS
      v = max(SCALE_BASE_MIN=1.0, min(SCALE_BASE_MAX=10.0, v))   <-- clamps 0.05 -> 1.0
      zones[index].baseScale = v   (per-zone, correctly scoped)
      triggerPreviewRender()
  → paint-booth-5-api-render.js
      builds zone_obj per zone; emits base_scale only if !== 1.0
      (L481: if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;)
  → POST /render to server.py
      _clamp(z["base_scale"], SCALE_MIN=0.01, SCALE_MAX=10.0, 1.0)   (per-zone, fine)
  → engine renders per-zone with that scale
```

The break is at the **handler layer (client JS)**. Server + render layers handle sub-1.0 correctly.

## Breaking commit / what changed

`git log` on the project shows the latest commits touching `paint-booth-2-state-zones.js`:
- `5c1fa47` (2026-05-07, "feat: update paint booth app runtime") — large 4075-line refactor of this file. This is when `SCALE_BASE_MIN = 1.0` ended up in the runtime (it was actually first introduced in `0ecf74c` 2026-03-19 but got carried forward).

The most recent material change is **uncommitted** in the working tree (commit `5c1fa47`..WORKTREE diff). Specifically (git diff HEAD):

```diff
 paint-booth-2-state-zones.js | 273 +++++++++++-----
 paint-booth-v2.html          | 761 +++++++++++++++++++++++++++++++++----------
```

Inside `paint-booth-2-state-zones.js` at L~1731-1767, the diff shows the **Base Scale slider HTML was changed from `min="100" max="1000"` (committed) → `min="5" max="500"` (working tree)**, AND two new sliders (Color Scale + Spec Scale) with identical `min="5" max="500"` were added. The comment block left in the file (L1731-1737) reads:

> SPB-2026-05-22 (restore Color Scale + Spec Scale sliders, per owner): the handlers setZoneBaseScale/setZoneBaseColorScale/setZoneSpecScale in js/zones/base-material-controls.js were orphaned — the HTML that called them got stripped at some earlier point. Restored here as three paired sliders, all 0.05x–5.0x range, baseline 1.0x.

So the slider HTML was restored on 2026-05-22 — but the author **assumed** the handlers in `js/zones/base-material-controls.js` were live. They aren't, because the module's `install()` is never called. And the surviving handler for Base Scale in the monster file still uses the old `SCALE_BASE_MIN = 1.0` constant from when the slider went 1.0–10.0x.

The guard script at `scripts/spb_guard_base_color_scale.js:44` literally flags this exact condition: it expects `paint-booth-2-state-zones.js` to include `SPBZoneBaseMaterialControls.install` — it does not. Guard is currently failing for anyone who runs it.

## Fix proposal (do NOT apply this tick — Tick 2 will)

Smallest viable repair, ordered low-risk first:

### Fix A (1 line) — unclamp Base Scale floor
File: `paint-booth-2-state-zones.js`
Line: **194**
Change:
```
const SCALE_BASE_MIN = 1.0, SCALE_BASE_MAX = 10.0;
```
to:
```
const SCALE_BASE_MIN = 0.05, SCALE_BASE_MAX = 10.0;
```
This restores sub-1.0 Base Scale via the existing monster-file handler. Slider HTML already emits 0.05.

### Fix B (3 functions) — wire up Color Scale + Spec Scale handlers
File: `paint-booth-2-state-zones.js`
After L7523 (`resetZoneBaseScale` closes), add monster-file copies of the missing handlers. Smallest patch:

```js
function setZoneBaseColorScale(index, val) {
    pushZoneUndo('Set base color scale', true);
    let v = parseFloat(val) || 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].baseColorScale = Math.max(0.05, Math.min(10.0, v));
    const label = document.getElementById('detBaseColorScaleVal' + index);
    if (label) label.textContent = zones[index].baseColorScale.toFixed(2) + 'x';
    document.querySelectorAll(`input[type="range"][oninput*="setZoneBaseColorScale(${index},"]`).forEach(sl => { sl.value = Math.round(zones[index].baseColorScale * 100); });
    triggerPreviewRender();
}
function stepZoneBaseColorScale(index, delta) {
    const cur = zones[index].baseColorScale || 1.0;
    setZoneBaseColorScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function resetZoneBaseColorScale(index) {
    pushZoneUndo('Reset base color scale');
    zones[index].baseColorScale = 1.0;
    renderZones();
    triggerPreviewRender();
}

function setZoneSpecScale(index, val) {
    pushZoneUndo('Set spec scale', true);
    let v = parseFloat(val) || 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].specScale = Math.max(0.05, Math.min(10.0, v));
    const label = document.getElementById('detSpecScaleVal' + index);
    if (label) label.textContent = zones[index].specScale.toFixed(2) + 'x';
    document.querySelectorAll(`input[type="range"][oninput*="setZoneSpecScale(${index},"]`).forEach(sl => { sl.value = Math.round(zones[index].specScale * 100); });
    triggerPreviewRender();
}
function stepZoneSpecScale(index, delta) {
    const cur = zones[index].specScale || 1.0;
    setZoneSpecScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function resetZoneSpecScale(index) {
    pushZoneUndo('Reset spec scale');
    zones[index].specScale = 1.0;
    renderZones();
    triggerPreviewRender();
}
```

(Alternative B': add a single line `if (window.SPBZoneBaseMaterialControls) SPBZoneBaseMaterialControls.install({ getZones: () => zones, pushZoneUndo });` somewhere late in the monster file. This wires the existing modular handlers in one shot and also fixes Base Rotation / matchZone* / setZoneBaseColorRotation / setZoneSpecRotation. Cleaner but introduces order-of-evaluation risk because the modular handler then has to be loaded BEFORE the install call, which it already is per `paint-booth-v2.html:2613` vs `:2689`.)

### Three-copy reminder
All edits must be replicated to:
- `paint-booth-2-state-zones.js` (root)
- `electron-app/server/paint-booth-2-state-zones.js`
- `electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js`

## Evidence checklist

- [x] HTML sliders use `min="5"` (0.05x) — sub-1.0 is intended at the UI layer.
- [x] Monster file `SCALE_BASE_MIN = 1.0` clamps post-input — bug confirmed.
- [x] Monster file has no `setZoneBaseColorScale` / `setZoneSpecScale` — bug confirmed.
- [x] Modular handlers exist with correct `0.05` floor but `install()` is never called — root cause.
- [x] Server clamps to `0.01` — server is fine.
- [x] Per-zone state confirmed (`zones[index].baseScale = …`) — no zone-scope leak.
- [x] Guard script `spb_guard_base_color_scale.js` independently asserts this exact failure mode.

---

## TICK 2 (FIX LANDED)

Date: 2026-05-27.

**Files touched** (all three copies identical, md5 = `26f8439bafa4db11fc1356b44db2e1b4`):
- `paint-booth-2-state-zones.js` (root)
- `electron-app/server/paint-booth-2-state-zones.js`
- `electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js`

**Changes** (Fix A + Fix B per Tick 1 proposal):
- L194: `SCALE_BASE_MIN = 1.0` → `SCALE_BASE_MIN = 0.05` (unblocks sub-1.0 Base Scale).
- After `resetZoneBaseScale` (post-L7523): added 6 new zone-scoped functions — `setZoneBaseColorScale`, `stepZoneBaseColorScale`, `resetZoneBaseColorScale`, `setZoneSpecScale`, `stepZoneSpecScale`, `resetZoneSpecScale`. All mirror the existing `setZoneBaseScale` / `stepZoneBaseScale` / `resetZoneBaseScale` template: per-zone writes to `zones[index].baseColorScale` / `zones[index].specScale`, clamp range `[0.05, 10.0]`, snap to `SCALE_STEP=0.05`, sync label + slider DOM, call `triggerPreviewRender()`. Each setter has the same invalid-index guard `setZoneScale` uses.

**Verification**:
- `node --check paint-booth-2-state-zones.js` → SYNTAX OK.
- All 6 new function names + the new `SCALE_BASE_MIN = 0.05` line confirmed present via grep at L194 / L7533 / L7549 / L7553 / L7560 / L7576 / L7580.
- md5 across all 3 mirror copies matches.

**Smoke test** (`_loop_state/slider_fix_smoke_test.js` → `_loop_state/slider_fix_smoke_test_results.txt`): **40/40 PASS**.
- All 3 setters land values on `zones[index].<field>`, never on a global. PASS for all 6 input values per setter (0.25, 0.50, 0.75, 1.0, 1.5, 2.0).
- Sub-1.0 (0.05, 0.25) inputs are NOT clamped to 1.0 on any setter. PASS.
- Setting on zone A does not affect zone B; setting on B does not retroactively change A. PASS across all 3 setters.
- `resetZoneBaseColorScale` / `resetZoneSpecScale` return the zone field to 1.0. PASS.
- Step deltas walk by `SCALE_STEP=0.05` and respect the 0.05 floor. PASS.

**Owner-facing summary**: Base / Color / Spec Scale sliders now go down to 0.05x per zone and stay zone-local — fine-detail tiling restored on the three scale sliders restored 2026-05-22.

---

## TICK 1 (DIAGNOSIS)

Confirmed two related failure modes, no zone-scope leak. Failure 1: Base Scale's runtime clamp `SCALE_BASE_MIN = 1.0` at `paint-booth-2-state-zones.js:194` snaps anything below 1.0 back up — slider HTML allows 0.05 but the setter immediately overrides. Failure 2: the Color Scale and Spec Scale sliders restored in the HTML on 2026-05-22 call handlers (`setZoneBaseColorScale`, `setZoneSpecScale`, plus their step/reset siblings) that exist ONLY in `js/zones/base-material-controls.js`, which is loaded but whose `install()` bridge is never invoked — so dragging those sliders is a no-op. Slider HTML is in the uncommitted working tree (post-`5c1fa47`); the regression is the live working state. No commit pinpoints exactly when the install bridge was dropped — see `scripts/spb_guard_base_color_scale.js` which already detects this exact missing-bridge condition. Server-side clamps (`SCALE_MIN=0.01`) and per-zone serialization in `paint-booth-5-api-render.js` are correct. Tick 2 should land Fix A (one-line constant change at L194) + Fix B (add 6 missing setter/step/reset functions after L7523), then replicate to all three mirror copies of `paint-booth-2-state-zones.js`.

## DONE — 2026-05-27T06:43:42Z

SCALE_BASE_MIN 1.0 → 0.05 + 6 missing per-zone handlers (setZoneBaseColorScale / step / reset and setZoneSpecScale / step / reset). 3-copy md5-identical (26f8439b...). Smoke test 40/40 PASS: sub-1.0 values land per-zone unclamped, A/B isolated, reset returns to 1.0, step walks by 0.05 against the 0.05 floor.

Optional next-tick: visual confirm in-app — drop Base Scale to 0.25 on a tiled monolithic and verify it tiles tighter on the active zone only.

# SPB TRAINING WHEELS — Quest Engine Design

**Status:** ✅ SHIPPED 2026-07-18 — phases 1+2 built and verified (see "As-built notes" at bottom; CHANGELOG 2026-07-18 entry "TRAINING WHEELS quest engine")
**Supersedes:** the 2026-06 in-HTML `TUTORIAL_STEPS` overlay — removed when this shipped.
**Doctrine:** *Training wheels on a bike.* Same bike (the real app), with support (guardrails + guidance), that comes off gradually (per-concept graduation). Not a separate bike — the retired Easy-Mode-as-parallel-app approach.

---

## 1. What this is

A quest engine that runs **on the real UI** and teaches the app by having the user *do* the app. Three user-facing pieces:

1. **Quest checklist** — ~10 short quests, each teaching exactly one concept, completable in (mostly) any order.
2. **Next-move chip** — a persistent, dismissible corner chip that reads live app state and always offers ONE obvious next action with a "Show me" spotlight.
3. **Graduation** — wheels come off per concept: hints for a skill retire after the user demonstrates it N times; finishing the core loop offers to turn Training Wheels off entirely.

Non-goals: no separate simplified UI, no auto-driving the app, no modal slideshows, no new file formats. The engine never *does* a step for the user — it points, the user clicks, the engine verifies.

Existing machinery reused from `js/spb-guided-mode.js` (231 lines, keep the patterns): defensive state probes, `findByText()`, the spotlight ring (`.spb-guide-ring` + `scrollIntoView`), 800ms poll refresh, `localStorage` persistence, `showToast()` for feedback.

---

## 2. Architecture

### 2.1 Files

| File | Change |
|---|---|
| `js/spb-quests.js` | **New.** The quest engine: quest definitions, probe API, chip, checklist panel, celebration, persistence. Loads right after `spb-guided-mode.js`. |
| `js/spb-guided-mode.js` | **Refactored, not rewritten.** Its STEPS_TGA/STEPS_PSD become quests `q-load`–`q-render` inside the engine. `window.spbGuide` API kept as a thin shim calling `spbQuests` so the existing `🎓 TUTORIAL` toolbar button (`#spbGuideToggle`, paint-booth-v2.html:1384) and Easy Mode's "Teach me the full app" link keep working. |
| `paint-booth-v2.html` | Add one `<script src="js/spb-quests.js"></script>` tag. Remove the stale `TUTORIAL_STEPS` overlay block (lines ~3778–3787 — wrong catalog numbers, superseded). |
| `paint-booth-v2.css` | Append quest styles (`spb-quest-*` classes). Reuse existing `.spb-guide-ring` spotlight CSS. |

### 2.2 Runtime shape

```
spbQuests
 ├─ state: { wheelsOn, questsDone:{qid:true}, skillCount:{skill:n},
 │           activeQuest, chipDismissed, graduated }
 ├─ probes: { paintLoaded, psdLayerCount, zone, zoneHasColor, zoneHasFinish,
 │            zoneHasPattern, zoneHasOverlay, zoneHasSpec, hasRendered, ... }
 ├─ engine: pickNextMove() → {quest, step} | null
 ├─ ui: renderChip(), renderChecklist(), spotlight(el), celebrate(quest)
 └─ api: on/off/toggle, startQuest(qid), showMe(), dismissChip(), reset()
```

- **Boot:** off = checklist closed, chip visible (first run only). `localStorage` key `spb_training_wheels` (JSON blob below). No migration from `spb_guided_mode` needed beyond reading `'on'` once.
- **Poll:** keep the 800ms `setInterval` pattern; each tick re-evaluates only the *active* quest's `done()` and the chip's next move. Probes must stay cheap and defensive (every probe wrapped in try/catch, missing globals → `false`).
- **Events (phase 2):** where cheap, swap poll for hooks — wrap `renderZones()` and `pushZoneUndo()` the same way Easy Mode already wraps `spbKickLivePreview`.

### 2.3 Persistence

```json
// localStorage["spb_training_wheels"]
{ "wheelsOn": true,
  "questsDone": { "q-load": true, "q-zone": true },
  "skillCount": { "zone": 3, "finish": 1 },
  "chipDismissed": false,
  "graduated": false,
  "firstWinDone": false }
```

`skillCount` increments each time a `done()` flips true for a quest tagged with that skill. Skill retires at **3** — its hints stop appearing even if the quest list is reopened.

---

## 3. Probe API

Probes are the engine's only window into app state. All read existing globals/DOM — **zero changes to app code**. Confirmed-against-source (2026-07-18):

| Probe | Implementation sketch | Source of truth |
|---|---|---|
| `paintLoaded()` | `#paintFile.value` non-empty | paint-booth-v2.html:836 |
| `psdLayerCount()` | `_psdLayers.filter(l => l && l.img).length` | existing coach probe |
| `zone(i?)` | `zones[selectedZoneIndex]` (guarded `typeof zones !== 'undefined'`) | paint-booth-2-state-zones.js |
| `zoneHasColor()` | `colorMode` ∈ {picker, multi, special} **or** `colors.length > 0` | existing coach probe |
| `zoneHasFinish()` | `!!(z.base || z.finish)` | zone factory, state-zones.js:1039 |
| `zoneHasPattern()` | `z.pattern && z.pattern !== 'none'` | zone factory field |
| `zoneHasOverlay()` | any of `z.secondBase … z.fifthBase` set | overlay layer fields |
| `zoneHasSpec()` | `!!z.zoneSpecMapPath` **or** non-empty spec-pattern stack | zone fields |
| `zoneRestricted()` | `!!(z.regionMask || z.sourceLayer)` | region/layer restrict fields |
| `previewLive()` | `#livePreviewImg` has a non-blank `src` | paint-booth-v2.html:2468 |
| `hasRendered()` | engine-set flag: wraps `btnRender` click + successful render toast; fallback — probe iRacing output via existing render-status endpoint | `#btnRender`, html:2518 |
| `undoUsed()` | hook `pushZoneUndo()` once, count calls | existing global fn |

New probes follow the existing coach convention: pure, defensive, return `false` on any doubt.

---

## 4. The quests

Order is the *suggested* path. Only the first four (the **Core Loop**) are strictly sequential — everything after `q-render` unlocks at once. Copy voice: pit crew, not manual. Short verbs, one idea per bubble, "you" not "the user".

| # | id | Title | Teaches | Chip/hint copy (draft) | `target()` | `done()` |
|---|---|---|---|---|---|---|
| 1 | `q-load` | Get your car in here | Load TGA or import PSD | "Everything starts with your car. Load the paint you race with." | `#paintFile` browse button | `paintLoaded() \|\| psdLayerCount()>0` |
| 2 | `q-zone` | Claim your pixels | Zones by color-pick | "A zone is just 'the pixels this finish applies to.' Pick a color on the car." | `PICK COLOR FROM CAR` button (findByText) | `zoneHasColor()` |
| 3 | `q-finish` | Drop a finish | Finish picker on a zone | "Now the fun part. Click Base and pick anything shiny." | `.zone-editor-float .swatch-trigger` | `zoneHasFinish()` |
| 4 | `q-render` | Send it to the track | RENDER + where files land | "Hit RENDER — paint + spec files land in your iRacing folder. Check the garage." | `#btnRender` | `hasRendered()` |
| 5 | `q-pattern` | Break up the surface | Patterns on a zone | "Solid finishes are half the catalog. Add a pattern — carbon, sunray, flames." | PATTERN section of zone popout | `zoneHasPattern()` |
| 6 | `q-spec` | Feel the material | M/R/CC channels | "Metallic, Roughness, Clearcoat — the three dials that make chrome chrome. Open the Spec Channels dock and move one." | `#specChannelDock` / spec sliders | `zoneHasSpec()` or channel-dock interaction flag |
| 7 | `q-overlay` | Stack a second material | Overlay layers 2–5 | "Overlays layer one material over another — pearl over candy, wear over chrome." | OVERLAYS section | `zoneHasOverlay()` |
| 8 | `q-restrict` | Paint inside the lines | Region/layer restrict | "Restrict a zone to a box, a lasso, or one PSD layer. Sponsors stay safe." | APPLY AREA / RESTRICT TO LAYER controls | `zoneRestricted()` |
| 9 | `q-touchup` | Fix it by hand | Brush touch-up | "One stray pixel? The brush tools work right on the canvas." | top-toolbar Brush `🖌️` | canvas stroke hook (phase 2) — until then, manual Next |
| 10 | `q-recipe` | Keep it forever | Save a recipe/design | "Save the whole build as a recipe — reapply it to next week's car in one click." | `💾 SAVE SHOKK` / recipe save (findByText) | recipe-save hook or manual Next |

**Celebration line on each completion** (toast + checklist check): q-render gets the big one — the existing coach's *"You just painted a car. 🏁 That is the whole loop"* message, extended: *"…Everything else is depth on those four moves. Quests unlocked: patterns, spec, overlays."*

**First-Win bridge:** when Easy Mode (or first-run flow) completes a whole-car finish, set `firstWinDone` + mark `q-load`/`q-zone`/`q-finish` done, land the user in the real editor, and auto-start `q-render` with the chip: *"That finish you picked lives in this zone. One step left — send it to the track. [Show me]"*

---

## 5. UI components

### 5.1 Next-move chip (the training wheels)

Bottom-right corner, above canvas chrome, `z-index` under modals. One move only. Never blocks.

```
┌───────────────────────────────────────────┐
│ 🎓 Next: Drop a finish on Body Color 1    │
│    Click Base, pick anything shiny.       │
│    [ 🔍 Show me ]   [ Open quests ]   ✕   │
└───────────────────────────────────────────┘
```

- Content comes from `pickNextMove()`: first incomplete Core Loop quest; if Core Loop done, the first quest whose `done()` is false and whose prerequisites (none after q-render) are met; if all done → chip shows graduation offer once, then retires.
- `✕` sets `chipDismissed` (reopen from the 🎓 button). Chip auto-undismisses on new quest unlocks.
- **Show me** → existing spotlight ring on `target()`, scroll-into-view, 4.5s.

### 5.2 Quest checklist panel

Same floating panel shell as today's coach (`#spbGuidePanel` styling), but a checklist, not a pager:

```
┌─ 🎓 TRAINING WHEELS ──────────────── ✕ ─┐
│ THE CORE LOOP                           │
│  ✅ Get your car in here                │
│  ✅ Claim your pixels                   │
│  ▶ Drop a finish          [ Show me ]   │
│  ○ Send it to the track                 │
│ GO FURTHER (unlocks after first render) │
│  ○ Break up the surface (patterns)      │
│  ○ Feel the material (M/R/CC)           │
│  ○ Stack a second material              │
│  ○ Paint inside the lines               │
│  ○ Fix it by hand                       │
│  ○ Keep it forever                      │
│ ─────────────────────────────────────── │
│  Wheels off when you finish the loop →  │
└──────────────────────────────────────────┘
```

Clicking any unlocked quest makes it active → its full instruction body + Show me (today's coach body layout, reused verbatim).

### 5.3 Graduation moment

When `q-render` completes (Core Loop done): checklist gets a one-time banner — *"You know the loop. Want the full cockpit? [Turn Training Wheels off] [Keep them on]"*. Wheels-off = `wheelsOn:false`, chip gone, panel reachable from 🎓 forever. Reversible in Settings (add one toggle row: *Training Wheels — on/off*).

---

## 6. Level-system hooks (Phase 2 tie-in, do not build yet)

Quests are also the **unlock currency** for progressive disclosure, when that lands: `q-render` → Level 2 sections (PATTERN / OVERLAYS / SPEC) stop being collapsed-by-default in the zone popout; spec quests → spec dock hints. The engine exposes `spbQuests.level()` (1|2|3) from `questsDone` so the future `data-level` CSS work reads one function. No DOM tagging in this phase.

---

## 7. Build plan

1. **Probe + engine core** (`js/spb-quests.js`): state, persistence, probes, `pickNextMove()`. Pure logic, no UI — testable from DevTools console.
2. **Checklist panel + chip**: renderers, spotlight reuse, celebration toasts, Settings toggle row.
3. **Coach refactor**: `spb-guided-mode.js` → shim over engine; STEPS_TGA/PSD → quest defs; verify `🎓` button and Easy Mode "Teach me" link still work.
4. **First-Win bridge**: Easy Mode completion → `firstWinDone` + land in editor + auto-start `q-render`.
5. **Retire**: delete `TUTORIAL_STEPS` overlay from paint-booth-v2.html; remove its CSS.
6. Phase 2 (separate effort): event hooks replacing poll, `data-level` disclosure, canvas-stroke probe for `q-touchup`.

**Rollback:** remove the one script tag + the Settings row. The shim keeps every existing entry point alive; no app-code changes, so nothing else can break.

## 8. Test checklist

- [ ] Fresh profile (cleared localStorage): chip appears, quest 1 active, Show-me spotlights `#paintFile`.
- [ ] Complete q-load → q-render in order: each auto-checks within ~1s of the real action, no manual Next needed (except q-touchup/q-recipe until phase 2).
- [ ] Do steps out of order (finish before zone): no crash; chip still suggests the right next move.
- [ ] Reload mid-quest: state restores, checklist checks persist.
- [ ] Core Loop completion shows graduation banner exactly once; wheels-off hides chip; Settings toggle brings it back.
- [ ] Easy Mode completion → lands in editor with q-render armed.
- [ ] 🎓 toolbar button + "Teach me the full app" link (old coach entry points) still open the panel.
- [ ] All probes return `false` (not exceptions) with no car loaded, no zones, server offline.
- [ ] Zero changes to paint-booth-*.js app logic — diff touches only: new file, coach file, 1 script tag, CSS append, overlay removal, Settings row.

---

## As-built notes (2026-07-18, phases 1+2 shipped)

What changed vs. the plan above, and what to know before touching it:

- **Level disclosure is engine-side, no zone-file edits.** `paint-booth-2-state-zones.js` was never touched: the popout's section ids are predictable (`sectionPattern{i}`, `sectionOverlays{i}`, `sectionSpecPatterns{i}`, `sectionSpecPreview{i}`, `sectionZoneSpecSource{i}`), so `applyLevelDisclosure()` in `js/spb-quests.js` collapses them from outside after every zone re-render. Peek tracking is a capture-phase document click listener; overrides persist in `userToggledSections`. The 🎓 note is re-injected into `.zone-detail-body` after each `renderZoneDetail`.
- **q-touchup / q-recipe are hook-driven, not manual.** `pushUndo` (gated on a brush-family `canvasMode`) and `_pushLayerUndo` complete q-touchup; a resolved `confirmSaveShokk` completes q-recipe. The "✓ I did it" button remains on every quest as an escape hatch.
- **q-pattern / q-overlay targets** use `findByText('.zone-editor-float .section-header', 'PATTERN'|'OVERLAY')` (the real generated markup) instead of the heading classes guessed above.
- **First run auto-opens the checklist once** (no saved `spb_training_wheels` blob). The auto-loaded demo PSD silently completes q-load/q-zone/q-finish at baseline, so a fresh user starts 3/4 through the Core Loop with only "Send it to the track" left — intentional.
- **Event hooks replace most polling**: `renderZones`/`renderZoneDetail` are wrapped (60 ms debounce) for instant sync; the 800 ms poll remains as a fallback for state paths with no hook.
- **Verification**: 31/31 + 18/18 node smoke tests; 24/24 live in headless Chromium against the running server — kept as `tests/_probe_training_wheels_live.py` (needs the server on 59876; screenshots in `_quest_live/`).
- **Toolbar disclosure shipped too**: at level 1 the 6 deep `<details class="spb-tb-menu">` menus hide via CSS on `body[data-spb-wheels-level="1"]:not([data-spb-toolbar-peek="1"])`; a dashed-gold **🎓 Menus** peek button (injected by `applyToolbarDisclosure()`) reveals them and retires itself. CSS-only hiding — fail-open if selectors ever miss.
- **Verification**: 31/31 + 18/18 node smoke tests; 28/28 live in headless Chromium against the running server — kept as `tests/_probe_training_wheels_live.py` (needs the server on 59876; screenshots in `_quest_live/`). Runtime mirror synced; the two new files were added to `scripts/runtime-sync-manifest.json`.
- **Not done yet (phase 3 candidates)**: first-run funnel rework beyond the `notifyFirstWin` bridge; retiring the old Easy Mode rails (owner decision — Easy Mode stays as the first-run experience); toast-spam audit interplay with quest toasts.

## As-built notes, round 2 (2026-07-19 overnight iteration)

- **Core Loop is 5 quests, not 4.** `q-setup` ("Point SPB at iRacing") sits between q-finish and q-render — probe requires `iracingId` matching 4–7 digits AND `outputDir` non-empty. This was the #1 new-buyer save issue (folder-vs-file) and is now taught before the first render.
- **Probes tightened against demo-car freebies.** `zoneHasColor`/`zoneHasFinish` only count zones with user-picked colors (picker/multi/colors) — the demo PSD's "Everything Else" (special + default gloss) no longer auto-completes q-zone/q-finish. New-user first run now teaches 3 real skills (pick, finish, render) instead of skipping to render.
- **gradOfferDismissed.** "Keep them on" at graduation no longer dismisses the chip forever (that orphaned the 6 further quests); it just retires the offer.
- **Stuck nudge.** chipDismissed + no completion for 5 min + core loop incomplete → chip resurfaces once per 30 min max ("Still here if you want the next step. 🎓"). Boot-time fallback for brand-new profiles.
- **Takeover parking.** chip/panel park (CSS, state preserved) under: Easy Mode (`body.spb-easy-on`), and any of swatch picker / Finish Library fullscreen / SHOKK Library modal (`body.spb-picker-open`, toggled per tick by computed display).
- **Easy Mode fork teach link.** "Teach me the full app" previously existed only inside the save block; a new fork-screen link (`#spbEasyTeachFork`) routes lost users to the wheels before they've picked anything.
- **A11y**: chip is `role=status aria-live=polite`; panel `role=dialog`; spotlight moves keyboard focus to the target; ring is aria-hidden; reduced-motion respected.
- **Level note never churns** (recreate-on-missing only) and only appears when managed sections actually exist — the 800 ms rebuild could eat clicks on its link.
- **Tests**: `tests/test_quest_engine_smoke.js` (node, 32 checks) + `tests/_probe_training_wheels_live.py` (playwright, 34 checks, needs server on 59876). Real-click dogfood verified: PICK COLOR FROM CAR → canvas click → Base swatch → finish tile completes quests through the true event path.


### 2026-09-07 — Current guide truth
Zone claim/finish completion accepts either color picking or an enabled nonempty drawn region; default Everything Else and empty masks do not count. Completed lessons can be reopened without recounting progress. Spotlight geometry follows nested scroll/resize and cleans up listeners after its4500ms lifetime. Executed contract: `tests/quest_zone_claim_contract.cjs`; native evidence in `docs/TOOLS_SIMPLIFICATION_2026-09-07.md`.

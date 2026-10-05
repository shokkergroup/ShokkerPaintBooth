# SELF-BRAIN: the offline helper that knows the app (js/spb-self-help.js)

Owner (2026-10-03): "people will never feel stuck or frustrated not knowing how to do whatever they may want to their paint schemes."
`window.SpbSelfHelp` answers **how do I / what is / where is / why didn't that work / I'm stuck / can I / what do I have loaded** from the app's own map plus the buyer's live state. No AI, no key, no network.

## Where things live
| Piece | File |
|---|---|
| Module (state reader, intent rules, answer builder, why-not checks, chips, do-it actions) | `js/spb-self-help.js` |
| Embedded data (575 UI controls + 118 how-to entries) between `/*@@UI_DATA_START*/ ... /*@@UI_DATA_END*/` | rebuilt by `python _easy_claude_work/selfhelp_build.py` from `scripts/ai_atlas/ui_map.json`, `scripts/ai_atlas/app_controls.json`, `docs/ai_knowledge/how_do_i.md` (SELF-MAP) |
| Router hooks | `js/spb-pro-ai.js`: `selfHelpClaim` / `selfHelpResult` / `selfHelpSig` (next to `supportClass`), `send()`, `offlineAskCore` (before `offlineHowto`), `offlineCanHandle`, `chips()`, `get_help` tool (`steps_for_this_buyer`) |
| Gate | `node _easy_claude_work/selfhelp_test.js` (`-f` failures, `-v` answers, `--seed` my 45 state seeds) |
| Steal audit | `node _easy_claude_work/selfhelp_claims.js` (2,155 phrases of the other harnesses: what self-help would claim, what the designer also claims) |
| In-app | `python _easy_claude_work/pw/selfhelp_inapp.py flat|psd` (own Chrome CDP 9623, test server 59879) -> `eval/selfhelp_inapp.jsonl`, `eval/selfhelp_<car>_NN.png`, `eval/selfhelp_<car>_sheet.png` |

## Routing order (send)
chip redirect / "Do it:" action -> pick from list -> teach -> `help` -> **self-help** (yields to: start over / undo, the support checklist for pasted errors + ingame / render / preview / off-topic, the finish advisor, the edit brain's ops / describe / variants / revert, the designer's compound orders; and `classify` returns null for any imperative order) -> support -> offline brains / AI.
Exception: "show my layers" / "what do I have loaded" is answered by the state reader before the edit brain's palette describe.

## Answers
- how-to entries are the source of truth (SELF-MAP `how_do_i.md`); a buyer-word HINTS table and a typo fixer (`preveiw wont chnage`) map loose wording onto them; my own TOPICS / GLOSS tables are the fallback.
- State-adapted: preconditions first (no paint -> load; flat paint + layer task -> "you have a flat paint, no layers - here is the alternative"; no zones -> + Add Zone; Easy -> switch to Pro), the selected zone is named, load-paint steps are skipped once a paint is loaded, Easy-only controls are hidden in Pro.
- Ends with ONE forward question; chips: the "Do it" action (if any), the next-best entry, "I'm still stuck" (-> simplest path + support checklist).
- Why-not checks (16): no paint, Easy mode, no zones, none selected, muted, covers no pixels, no finish, colour mode source/finish, solid colour on a brings-its-own-colours finish, pattern Overlay hides the base, pattern opacity 0, covered by a higher catch-all, spec-only change invisible in the flat preview, restricted to a hidden layer, last order changed nothing (zone/layer signature unchanged), intensity <= 25. The last-order check is first when it fires.

## Do-it actions (safe, reversible)
select a zone (`selectZone`), switch a muted zone back on (`toggleZoneMute`), refresh the preview (`triggerPreviewRender`), "Find my numbers" (-> "What colours do I have?", the edit brain's describe that runs the elements finder on a flat paint).

## State-aware starter chips
no paint -> Load a paint; last order changed nothing -> Why didn't that work?; flat -> Find my numbers; PSD -> Show my layers, Hide the wireframe (when Wire/Mask/Car_Mandatory are visible), Recolour the Numbers layer (when a numbers layer exists); a zone selected -> What can I do with this zone?; no zones -> Where do I start?

## Traps
- Patch files with the Write tool: bash heredocs ate `\b` four times in this lane.
- `norm()` strips punctuation, so comma-based rules must read the raw text.
- The typo fixer only touches words >= 4 letters not in the vocabulary and not in `KEEPW` (it once turned "messed" into "missed").

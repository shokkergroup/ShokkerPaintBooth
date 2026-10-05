# PUSH-VISIBLE: make an applied stack show on the car (2026-10-03, 17:27-17:42)

Lane: `js/spb-pro-advisor.js` stack planner defaults only (stackPlan / stAdjust / stackAnswer) + `_easy_claude_work/stack_test.js`.
Cache token `spb-pro-advisor-20261003msrA6` -> `spb-pro-advisor-20261003visible`; synced to electron-app/server (no drift).

## Defaults changed (before -> after, why)
| control | before | after | evidence |
|---|---|---|---|
| pattern layer strength | 40% when a colour + base were named, 45 calm, 70 else | **65%** for any named pattern; 40 for calm asks; "subtle" words still 35 | MSR_VERIFY mode 2: M517 / M084 / M159 / M329 / owner ask patterns invisible at 40% |
| pattern layer size | flat x1 | from the card's busyness: busy>=4 -> **x0.7**, busy<=2 -> **x1.1**, else **x0.85** (explicit size words still win) | K_app_controls R3: x0.5 = dense mesh, so fine patterns stay above it |
| "like X but in colour" alt pattern | x1 / 40% | card size / 65% | same |
| hue nudge source | palette slot 0 | TRIED saturation-weighted palette mean (`stDomHsl`), **REVERTED**: owner ask went hue +97 = purple/olive (cpv_OWNER). Slot 0 is back; `stDomHsl` is left unused | MSR_VERIFY mode 3 still open |
| saturation on a neutral ask | -100 whenever the asked colour is a neutral | -100 only when the text says black-and-white / grey / mono / silver / charcoal; else -40 | M537 "aqua and white" went black-and-white |
| spec-only stacks | no note | reply adds "Shine textures do not show in the flat preview - check the 3D view." | MSR_VERIFY mode 6 (M346 / M458) |

Blend mode was NOT changed: the stack apply path never sets a blend mode (it uses the zone default), so there was nothing in-lane to switch off Overlay.

## Suites
stack_test 82/82 (75 old + 7 new: 4 opacity/scale asserts, aqua-and-white no -100, black-and-white keeps -100, spec-only 3D-view line); convo_test 52/52; tool_test 15/15; adv_fp unchanged claim totals (344/344, classify untouched). node --check OK, scan_ctrl 0 control chars.

## Known limit found while testing
"Hologram Metal in pink" / "#ff69b4 pink with a black camo pattern" still pick **Neon Rush** as the base; its palette data is mostly pink/red (new hue nudge = -27 / -31), so the lime seen in-app is NOT in the palette the planner reads. The fix is base choice / palette data, not the hue formula.

## In-app verdicts
Driver: `_easy_claude_work/pw/pv_verify.py` (copy of msr_verify on CDP 9641, re-hides any layer named wire/mask/mandatory right before the preview; `hidden` = Car_Mandatory, Mask, Wire on every run). Images `_easy_claude_work/eval/push_visible/`.
| ask | VERIFY before | now | what the preview shows |
|---|---|---|---|
| owner "a pink camo rattlesnake look" (cpv2) | partial, no snake read | **partial (better)** | snake scales clearly visible at 65% x1.1; colours magenta / teal / blue camo, pink not dominant |
| M517 pink camo rattlesnake in chrome + carbon | fail, scales invisible | **partial** | Wavy Carbon moire clearly visible over a lilac chrome; no snake / camo (planner picked carbon only) |
| M084 bubblegum pink + barbed wire | fail, invisible | **pass** | diagonal barbed-wire lines visible over a pink-magenta gradient |
| M278 Hologram Metal in pink | fail, lime | **partial (better)** | hot pink dominant, lime bands still ~30% (Neon Rush base) |
| M537 aqua and white, light shimmer | fail, B&W at sat -100 | **pass** | aqua + white contour field (sat -40); reply carries the 3D-view line; shimmer not judgeable flat |

Not verified: the green wire-grid outline still shows on the number / sponsor art in every preview even with Wire / Mask / Car_Mandatory hidden (looks like the art's own layer, not confirmed); gloss / shine / 3D view; M159 / M329 / M423 / M457 / M346 / M458 in-app; other cars; blend mode; bubblegum-vs-magenta tone.

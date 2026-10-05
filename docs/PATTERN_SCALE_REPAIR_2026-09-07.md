# Spec overlay controls and pattern scaling repair

Owner report: spec placement controls collapse after edits, Size seems ineffective,
Ammonite Chambers seems to disappear at 0.70x, and removing a pattern is hard to find.

## Changes

- Replaced the native details disclosure in each spec overlay with a permanent
  placement section. Size, X/Y and coverage show numeric feedback while dragging;
  release commits the setting through the existing Undo and preview path.
- Primary and additional paint patterns now have a visible **None** button beside
  their selector. Existing assignment/removal handlers preserve Undo and spec layers.
- Direct rebuilt paint patterns previously lost their direct rendering path whenever
  size, rotation or position changed. A separate transformed texture then masked
  the untransformed paint; the visibility fallback could substitute a different
  texture. `engine/pattern_paint_placement.py` now transforms the authored signed
  ink once, before applying the destination zone mask. It never tiles source paint.
  Primary and stacked paint paths share this helper. Native settings remain exact.
- Spec overlay math was already applying feature scale correctly. It remains
  unchanged; Size changes feature frequency while Coverage box controls the area.

## Verification

- 14 placement regression tests, including real Ammonite Chambers, exact 1.00x
  preservation, smaller features at .70/.40/.25, enlarged features, both public
  paint compositors, source/zone preservation, and spec transform cache behavior.
- 35 existing spec contract/export and base/spec isolation tests pass; all 235
  legacy spec golden fixtures unchanged. UI serialization checks pass for all five
  base stacks, including Size, offsets, seed and coverage.
- An isolated Edge page running the production controller, serializer and actual
  pattern selector/assignment code passes repeated size/rotation/position/variation/
  channel edits and visible None. Placement remains visible, values survive panel
  rebuilds, preview triggers fire, and None records the existing Undo action.
- Actual 2048 Ammonite paint: 1.00x before/after byte-identical; .70x paint pass
  2.570 → 1.091 seconds, .40x 1.997 → 1.132 seconds. All current direct-pattern
  paint renderers use the same authored additive factory; its geometry is unchanged.
- Basalt Prisms native 2048 check: M/R/Cc std at size 1 = 30.80/26.24/29.78;
  size .40 = 30.07/25.53/29.19. Finer detail retains material contrast.
- All 240 live spec thumbnail assets match their accepted bakes on isolated port
  59878; no finish designs or thumbnails were rebuilt.
- Live `/preview-render` checks pass for seven Basalt settings (native, Size,
  X, Y, rotation, variation, coverage) with exact paint preservation and distinct
  spec pixels. Real Ammonite paint output differs at 1.00/.70/.40 and stays visible.

Evidence: `_spec_overlays_v2_work/scale_repair/` contains browser, native rendering
and HTTP checks, JSON results and native pixel comparisons. Browser verification
uses a separate headless profile and synthetic source paint, never the owner's recipe.

## Runtime handoff

**Later owner-directed recovery on09-07:** the old installed background instance
was positively identified and stopped; canonical Fresh Start now serves the current
10.0.1-beta project on the normal59876 again (supervisor137212, child71820).
The overlay controller served there matches source and the new Basalt thumbnail
returns200. The port observations below describe the earlier repair session.

Port 59876 currently belongs to the older installed app under
`AppData/Local/Programs/shokker-paint-booth-v6/resources/server`, which has no
new overlay controller. Port 59877 belongs to another canonical development process.
Neither process was restarted. Isolated verification on 59878 uses the current
canonical source, disables iRacing live linking and writes only to its own
`_release_evidence/overlay-scale-20260907` directory. The verification booth is
`http://127.0.0.1:59878/paint-booth-v2.html`; live iRacing writes are disabled.
Root and packaged-runtime changes use the scoped seven-file sync manifest in the
evidence directory. CSS/JS tokens are `spb-pattern-size-20260907`.
All seven copies verified with no drift. Served JS/CSS match source, and the
browser-parsed HTML contains the new tokens and all checked canvas/layer scripts.

Cache-token follow-up: an initially broad replacement also matched a historical
unquoted filename in an HTML comment, swallowing its closing marker and the next
script opener. Final inspection caught it; restored the exact nine comment/tag
lines and verified executable script elements. Future bumps must match quoted
`src`/`href` attributes only, never arbitrary filename occurrences.

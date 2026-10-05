# Pattern controls hotfix — 2026-09-08

Owner report: None opens the picker instead of clearing; Hue/Saturation/Spec Amount throw `setPatternMaterialControl is not defined`; Blend appears ineffective.

## Actual causes and correction

- `pattern-transform-controls.js` rendered the new sliders but only defined their setters inside an installer the live page never called. A dedicated material-controls installer now runs on fresh/deferred boot without replacing legacy transform/opacity setters.
- `paint-booth-5-api-render.js` added the four material fields to an extracted `_applyZoneRenderCore` helper, but the active normal/preview, Fleet and Season builders bypassed it. Those builders now share `_applyPatternMaterialControls` directly, including explicit zero values.
- The canvas preview configuration hash also omitted all four primary material fields. It now includes them, so settled previews and their serialized-body cache invalidate on Hue, Saturation, Spec Amount and Paint Mode changes. Additional patterns already hash their full stack records.
- Primary None is now a sibling of the swatch trigger, matching additional-pattern removal. It cannot inherit the picker click target. Fresh pre-fix sessions cleared None correctly; the owner's specific popup failure was not reproduced. Fresh post-fix native clicks clear it, keep the picker closed, and Undo restores it.
- Cache tokens updated for all four affected client scripts. The existing owner's tab must reload after saving its project. No server restart is needed for these client-only changes.

## Executed evidence

- `node tests/pattern_controls_boot_contract.cjs`: fresh and deferred boot, primary/stack setters, no-op history, preview scheduling, legacy setters preserved.
- `node tests/pattern_material_persistence.cjs`: saved settings, explicit-zero defaults, shared material serialization and active builder call sites. The prior assertion against the unused helper was corrected.
- `python tests/spb_pattern_controls_browser_smoke.py`: real stdio MCP, fresh headless app on isolated59880, normal flat PNG import, no manual setter installation. Actual controls change primary Hue120/Saturation−100/Spec50; Reset works; all four fields change the real preview hash; Blend disables only H/S and reaches the live preview request; None keeps picker closed; Undo restores it; additional-pattern Spec75 works. No script errors. Evidence: `_tools_simplification_work/mcp-review/bug-browser-pass.json`.
- `python -m pytest tests/test_pattern_material_controls.py -q -k blend_keeps_source`: source hue/saturation and masked pixels preserved while pattern value detail changes.
- Five actual59876 HTTP previews of Sega Blast over Soul Core Crimson: mean RGB change from Overlay is64.69/255 for Blend and51.98 for Hue120. Spec100 changes spec by60.64/255 while paint is exactly unchanged; Hue/Blend keep spec unchanged. None removes the pattern contribution. Evidence: `bug-live-render.json` and `probe-pattern-live.py` in the same work folder.

The browser audit initially exposed the missing live serialization despite the helper-level tests passing. This regression must stay on the fresh app path. Early layered-fixture attempts were interrupted by crash-recovery prompts; they are not counted as passing evidence. The completed test uses a disposable flat image; no customer document or output was modified.

No finish artwork, geometry, material design, or spec renderer changed. No new M7 claim. No installer build, deployment, or unrelated MCP repair. Runtime files and Wiki synchronize root → `electron-app/server` using the narrow `pattern-runtime-manifest.json` in the evidence directory.

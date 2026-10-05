# COPILOT-PAGE (2026-10-04): view strip, layer bar, Lock to layer in the chat studio

Owner ask: on the big copilot page, still see SOURCE, LIVE PREVIEW and the Combined / Red / Green / Blue boxes; a layer bar down the right when there are layers; lock the copilot to a layer ("all of the pink in the NUMBERS layer turn metallic silver").

## What was built (js/spb-chat-studio.js, css/spb-chat-studio-20261001.css; token spb-chat-studio-20261004page2)
- **View strip** under the big car: Source, Live preview, Combined, Red (metal), Green (rough), Blue (coat). Click a box = it shows big in the frame (the orange outline marks the big one; Combined = the Shine tab, Live preview = the Paint tab). A small arrow collapses the strip to one "Source / Live / Channels" button (localStorage `spb_cs_strip_min`).
- **Mirrors the Full Editor, no second render:** Source = `#paintCanvas` drawn down to 160 px (redrawn about every 2 s; the canvas has no change event); Live preview = `#livePreviewImg.src`; the four channel boxes = `window.spbRenderSpecProofSet(#livePreviewSpecImg, ...)`, the same renderer as the editor's `#specChannelDock`, refreshed on that image's `load` event + the 700 ms studio tick. The big Source / single-channel views draw into `#spbCsBigCv` (1024 px) the same way.
- **Layer bar** (right, 228 px; 196 px under 1250 px) only when `_psdLayers` has layers: top of the stack first, eye = the editor's `toggleLayerVisible()`, thumbnail = the editor's `SPBLayerThumbnail.draw()`, role chip from `SpbProCar.roles()` (Numbers / Logos / Sponsors / Tape / Body / Template / Art). Hidden for a flat TGA.
- **Lock to layer:** a Lock button per row. Locked = orange row, "Working in: <layer>" in the bar header and a chip just above the copilot's input (x clears it). While locked, a capture-phase listener rewrites the typed request before the copilot's own Enter / Send handler reads it: `in the <layer> layer, <text>`. Not prefixed: recipes, undo / yes / no / numbers / "use ..." style replies, text that already names the layer. Typing a layer name while unlocked offers "Keep working in the <layer> layer? [Lock to it]".
- Also hidden inside the studio: the editor's X/Y/hex pixel readout (`#platinumCoordReadout`), which floated over the copilot input.
- API for tests: `SpbChatStudio.lock(id|null)`, `.locked()`, `.prefix(text)`, `.lastSent()`, `.currentView()`.

## Evidence (_easy_claude_work/eval/copilot_page/, test `_easy_claude_work/pw/copilot_page_test.py [out] all|psd|flat`, private Chrome `pw/copilot_page_chrome.py` on CDP 9693, test server 59879, built-in brain only)
- ARCA PSD (15 layers incl. 3 templates): `cp_1600_default.png`, `cp_1600_big_red.png`, `cp_1600_big_source.png`, `cp_1600_locked.png`, `cp_1100_locked.png`, `cp_1100_big_green.png`, `cp_1100_suggest.png`. No horizontal scroll at 1600 or 1100; every strip box and Lock button hit-tests as on top (elementFromPoint).
- Locked Numbers, typed "all the pink to metallic silver": the brain received `in the Numbers layer, all the pink to metallic silver`. Zones after: `Numbers Layered Cut Foil` (limited to layer Numbers), `Pink metallic, in silver` (NOT layer-limited: covers #c908c7 / #fe0397 on the whole car), then the original zones.
- Flat TGA (owner_ss sheet): `cp_1100_flat.png`, `cp_1100_flat_combined.png`: layer bar hidden, strip works.

## Open (not this lane)
- **The edit brain reads the prefix's word "layer" as the look "Layered Cut Foil"** (and "make the Numbers layer gold" answers "I do not know a look called layer"). Until the layer-scoped colour target lands in js/spb-pro-edit.js, a locked request also puts Layered Cut Foil on that layer, and the pink is changed car-wide. The parser should consume `in the <name> layer,` as a layer target first.
- Not verified: the owner's live app (port 59876), a real AI key path (prefix happens before the brain, so it should be the same), very short windows (< 800 px high: the frame gets small; the strip can be collapsed).

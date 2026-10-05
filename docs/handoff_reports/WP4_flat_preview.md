# WP4 - Why is the flat-load preview stale? (W-C Preview detective) - 2026-10-03

Status: DONE. Verdict: **REAL BUG (Pro preview shows the PREVIOUS car after a flat paint load) + two harness artefacts.** No app file was changed.

## Finding 1 (code reading): the harness does NOT load a flat paint the way the app does

Real owner flat-load path (Source Paint box / native file dialog / Load by path):
`loadPaintPreviewFromServer(path)` paint-booth-3-canvas.js:1226 -> after the pixel commit,
lines ~1301-1306:
```js
setTimeout(function () {
    if (!_spbIsCurrentSourceLoad(transaction)) return;
    try { lastPreviewZoneHash = ''; } catch (_) {}          // break the dedupe
    if (!splitViewActive) { toggleSplitView(); }
    else if (typeof triggerPreviewRender === 'function') { triggerPreviewRender(); }
}, 200);
```
Callers: js/spb-native-file-dialogs.js:297, paint-booth-3-canvas.js:500 / 1114 / 1336 (loadPaintByPath), paint-booth-2-state-zones.js:17280.

Harness path (`_easy_claude_work/pw/car.py` boot_car, kind 'flat'):
`setCurrentSourcePaintFile(path)` -> `window.loadPaintImageFromFile(File)` -> `setCurrentSourcePaintFile(path, {clearPSD:false})` -> `triggerPreviewRender()`.
`window.loadPaintImageFromFile` is `loadPaintImageFromFileAsync` (paint-booth-3-canvas.js:9102, exported at :9182), which, unlike its sync twin `loadPaintImageFromFile` (:9039, has the "[restore-preview fix 2026-06-29]" hash reset) and `loadPaintImage` (:8917), does NOT reset `lastPreviewZoneHash`; it only calls `toggleSplitView()` when split view is off (:9150-9152). Also the second `setCurrentSourcePaintFile` call runs `clearFlatPaintLiveSource` (:21427), wiping `window._spbFlatPaintLiveSource` that the load just set.
Its only in-app caller is paint-booth-7-shokk.js:588 (SHOKK file import) and `loadPaintImageFromPath` (:9014, SHOKK URL import).

Gates on the render trigger path (all must pass for a POST):
- triggerPreviewRender :10823 - returns if `!isPreviewSurfaceVisible()` (:9724, canvasDisplayMode must be 'rendered'/'split') and placementLayer==='none'; returns while `_spbPsdImportInFlight && !_psdLayersLoaded`.
- _schedulePreviewStages settle :10961-10964 - `getZoneConfigHash() === lastPreviewZoneHash` -> return (source identity is NOT in the hash, per the comment at :9086).
- doPreviewRender :11269 - returns on `SPBRenderReadiness.reason()`, empty `#paintFile`, `!ShokkerAPI.online`.

## Finding 2 (measured, harness path, `pw/t262_flat_preview_probe.py`, Chrome 9444, server 59879)
All triggerPreviewRender gates are OPEN after the harness flat load (split on, surface visible, no PSD import in flight, readiness '', paintFile set, online). But `getZoneConfigHash() === lastPreviewZoneHash` is TRUE right after the load -> the settle dedupe (:10963) drops the render. Preview image hash unchanged (still the Chevy truck example). After `refinish` a `POST /preview-render` DOES go out (200, 1.5 MB) and - in this run - showed the Ferrari.
**t261 artefact:** t261 logs only URLs containing `/api/` or `.tga`; the preview endpoint is `/preview-render` (paint-booth-3-canvas.js:11846), so t261 can never see a render request. It also compares only naturalWidth + the first 60 chars of a `data:image/png` src, which are identical for every preview.

## Finding 3 (measured, REAL app paths, `pw/t262_real_ui.py drop|server`) - REAL BUG
Both real flat-load paths send the OLD paint to the preview when the load lands < 30 s after the previous preview encode:
```
drop   (real DragEvent 'drop' on .center-panel -> browsePaintFile TGA branch -> loadDecodedImageToCanvas)
  boot:        rev 1  memoRev '1:2048x2048' memoAge 14.1 s   img = truck
  after load:  NO POST at all (hashEq true), rev still 1, memoAge 23.3 s, img unchanged (truck)
  refinish:    POST pf=...car_206066.tga tok=True sig=rev:1:2048x2048:1791036871 img=0 -> 200, img = TRUCK (eval/wp4_drop_2refinish.png)
server (Source Paint box path: loadPaintByPath -> loadPaintPreviewFromServer)
  after load:  POST pf=ferrari488gt3\car_206066.tga tok=True sig=rev:1:...930 img=0 -> 200, img unchanged (TRUCK)
  refinish:    same stale token -> img = TRUCK + edit (eval/wp4_server_2refinish.png)
```
`tok=True img=0` = the request carried the cached server token of the previous paint, no new pixels.

Root cause: the preview PNG memo fast path is keyed on `window._spbLayerRev + ':' + WxH` with a 30 s TTL
(js/canvas/preview-png-encoder.js:14-16; same rule in `_encodedPngForCanvas` paint-booth-3-canvas.js:11099-11102).
Its own comment says `_spbLayerRev` "bumps on every destructive layer/pixel undo-push ... A missed mutation path ... can now be stale for at most 30s".
A flat source load IS such a missed path: neither `_spbCommitSourceFile` (paint-booth-3-canvas.js:21675, `publish:` at :21682 - used by every File/TGA/drop/SHOKK loader incl. loadDecodedImageToCanvas paint-booth-1-data.js:195) nor `loadPaintPreviewFromServer` (:1271-1274, the Source Paint box / native dialog / restore path) bumps `_spbLayerRev`. Same-size sheet (2048x2048, every iRacing paint) -> same rev key -> the encoder returns the previous car's PNG/sig -> `_attachEncodedPaintSource` (:11148) reuses its server token.
Because `getZoneConfigHash` also folds in `_spbLayerRev` (:10505), the missing bump is ALSO why the drop / async-file loaders' post-load `triggerPreviewRender` is deduped away (they do not reset lastPreviewZoneHash; only loadPaintPreviewFromServer / browsePaintFile-PNG / loadPaintImageFromFile-sync do).
Stale lasts until an edit made >= 30 s after the last real encode (then the content signature mismatches and the new paint is encoded); no render is triggered at that moment by itself.

Corroboration: Easy mode already hit this and patched it locally - js/spb-easy-auto.js:2071-2074 ("Pro memoizes the uploaded paint PNG for 30 s keyed on window._spbLayerRev; inside Easy a paint switch does not bump it, so every render in that window re-sent the PREVIOUS car (measured: stale for ~40 s, then fresh)"). Pro never got the fix.

## Finding 4 (measured): the 30 s window and the fix, proven
```
server_late (wait 32 s after boot, memoAge 44.6 s, then loadPaintByPath)
  after load: POST tok=False sig=2048x2048:a27d32c1:8874b69 img=928742 -> 200, img CHANGED (Ferrari)   <- content-signature path, correct
dropfix (page-side simulation of the fix: wrap window._spbCommitSourceFile, bump _spbLayerRev after it)
  after load: POST tok=False sig=rev:2:2048x2048:... img=928742 -> 200, img CHANGED (Ferrari) immediately; refinish -> token of the NEW paint, img changed
flatload (pw/flatload.py: real loadPaintByPath + the same rev bump right after the commit)
  {'ok': True, 'rendered': True, 'posts': [200], 'img_changed': True}; refinish -> POST + img changed
```
Images: `_easy_claude_work/eval/wp4_fixproof.png` (dropfix after load | flatload after load | flatload after refinish: all the pink Ferrari car_206066) vs `wp4_drop_2refinish.png` / `wp4_server_2refinish.png` (still the Chevy truck example).

## Minimal repro (owner's own app, Pro)
1. Pro with any 2048x2048 paint/PSD loaded and the split preview on; make any edit so the preview renders.
2. Within 30 s, load a different flat TGA via the Source Paint box / Browse (native dialog) / drag-and-drop onto the canvas.
3. SOURCE shows the new car; the live preview still shows the old car (drop: no request at all; Source Paint box: a request carrying the old paint token - `paint_source_token` set, no `paint_image_base64`).
4. Edits in the next ~30 s (typed edits, AI `refinish`, sliders) render the new zones ON THE OLD CAR. The first edit after the window self-heals.
Likelihood: high whenever the owner switches paints while working (every preview render re-arms the window); AI chat flows make it worse because an AI edit right after "load this paint" lands inside the window.

## Proposed minimal fix (NOT applied) - bump the paint revision when a new source paint is committed
`_spbLayerRev` is documented as the choke point for paint-pixel mutations (zone hash :10505, live composite memo :11003, PNG memo :11099 / preview-png-encoder.js). Source loads are the one mutation that skips it. Two commit sites cover every flat loader (Source Paint box, native dialog, boot restore, SHOKK, drag-drop, Change File, TGA decode); the restore-on-failure site is included for symmetry.

```diff
--- a/paint-booth-3-canvas.js
+++ b/paint-booth-3-canvas.js
@@ -1273,6 +1273,10 @@
                     canvas.height = img.naturalHeight || img.height;
                     ctx.drawImage(img, 0, 0);
                     paintImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
+                    // [WP4 2026-10-03] new source pixels = paint mutation: bump the rev so the
+                    // 30 s preview PNG memo / server token and the zone-hash dedupe cannot
+                    // serve the PREVIOUS car (measured: stale preview after a flat load).
+                    window._spbLayerRev = (window._spbLayerRev || 0) + 1;
 
                     // Identity is intentionally after pixel commit.
                     _spbCommittedSourcePath = normalizedPath;
@@ -21679,7 +21683,8 @@ function _spbCommitSourceFile(width, height, draw, options) {
         capture: _spbCaptureSourceDocumentState,
         restore: _spbRestoreSourceDocumentState,
         resizeMasks: _spbTransitionSourceMasks,
-        publish: data => { paintImageData = data; },
+        // [WP4 2026-10-03] source swap = paint mutation (see loadPaintPreviewFromServer).
+        publish: data => { paintImageData = data; window._spbLayerRev = (window._spbLayerRev || 0) + 1; },
         clearPSD: () => clearPSDDocumentState('direct source import', { clearZoneSourceLayers: true })
     }, width, height, draw, !options || options.clearPSD !== false);
 }
@@ -21791,6 +21796,7 @@ function _spbRestoreSourceDocumentState(snapshot) {
     if (!snapshot) return;
     _spbRestoreCanvasSnapshot(document.getElementById('paintCanvas'), snapshot.paintCanvas);
     _spbRestoreCanvasSnapshot(document.getElementById('regionCanvas'), snapshot.regionCanvas);
+    window._spbLayerRev = (window._spbLayerRev || 0) + 1;   // [WP4] restored pixels are a mutation too
     const paintCanvas = document.getElementById('paintCanvas');
```
(Line numbers from the working tree on 2026-10-03; re-anchor on the quoted context.) Then sync to electron-app/server via the lane manifest and bump paint-booth-3-canvas.js's own `?v=` token in paint-booth-v2.html. Once shipped, the Easy-mode local bump (spb-easy-auto.js:2074) becomes redundant but harmless.

Blast radius: small and one-directional - a rev bump can only cause MORE work, never stale pixels. Per source load: one zone-hash recompute, one fresh PNG encode + upload (~90-450 ms, 1-9 MB, the same cost as any first render of a new paint) and one guaranteed preview render (the desired behaviour; it also makes the drop / SHOKK / async-file loaders render without their own `lastPreviewZoneHash = ''`). Readers of `_spbLayerRev`: getZoneConfigHash + its memo, buildLivePaintCompositeCanvas memo, `_encodedPngForCanvas`, preview-png-encoder (via revision()), doPreviewRender `currentPaint()` (a bump during an in-flight encode marks it stale and reschedules - correct); spb-easy-auto.js only writes it. It is not an undo-stack index. Full Render does not use the memo (unaffected); the PSD import path already bumps at :22181 (untouched).

## Harness: what was wrong and what to use now
1. **`pw/t261_flat_preview.py` cannot see the render**: it filters on `/api/` and `.tga`; the endpoint is `/preview-render`. And `naturalWidth + src[:60]` never differs between previews - compare pixels (canvas hash of `#livePreviewImg`).
2. **`pw/car.py` boot_car('flat')** does not use the owner's load path: it calls `window.loadPaintImageFromFile` (= `loadPaintImageFromFileAsync`, the SHOKK loader, no dedupe reset), then `setCurrentSourcePaintFile` twice (the second call wipes `_spbFlatPaintLiveSource`). On top of that the app bug makes any flat load within 30 s of the last render stale.
3. **New helper `_easy_claude_work/pw/flatload.py`** (harness-only; car.py is imported only by scripts inside `_easy_claude_work/pw`, verified by grep): `flatload.load_flat(pg, r'<path>.tga')` = the real Source Paint box path (`loadPaintByPath`) + the proposed fix applied page-side (rev bump right after the commit); waits for the `/preview-render` response; returns `{'ok','rendered','posts','img_changed'}`. Proven above. WP6: `boot_pro(pg)` (wait for the example PSD as boot_car does), then `load_flat(pg, tga_path)`; pass the original .tga (the server decodes it). car.py was NOT modified (shared by many t1xx scripts); swap its 'flat' branch to `flatload.load_flat` if the orchestrator wants every old script fixed.
4. Test scripts: `pw/t262_flat_preview_probe.py` (gate dump), `pw/t262_real_ui.py drop|dropfix|server|server_late|harness|flatload` (one mode per run; prints payload kind `tok=/img=` and image-changed per stage; images `_easy_claude_work/eval/wp4_*`). Run with `SPB_CDP_PORT=9444`, server 59879.

## Not verified
- The owner's Electron build (headless Chrome against server 59879 with the same JS). Electron drag-drop delivers the same DOM `drop` event, so the drop path should match, but it was not run.
- Native file dialog path (`js/spb-native-file-dialogs.js:297`) not driven; it calls the same `loadPaintPreviewFromServer` measured above.
- The fix was only simulated page-side (wrapping `_spbCommitSourceFile`; rev bump after `loadPaintByPath`); the source diff was not applied, and no pytest/node suites were run.
- Non-2048 paints: a size change already changes the memo key, so they should be unaffected (inferred, not run).


## APPLIED by the orchestrator (2026-10-03 ~10:25 local) and verified on both real paths
- The 3-line patch above is now in `paint-booth-3-canvas.js` (3 `[WP4 2026-10-03]` comments), `node --check` ok, `scan_ctrl.py` 0 control chars, cache token `paint-booth-3-canvas.js?v=spb-wp4-flatrev-20261003`, synced root -> `electron-app/server` (`--check`: no drift).
- Re-ran `pw/t262_real_ui.py drop` and `server` on Chrome 9444 / server 59879 (loads made within the 30 s window, the failing case):
  - drop: after load rev 1 -> 2, `POST /preview-render` with fresh pixels (sig `rev:2:...`, 928,742 bytes), preview image changed; after `refinish` another render (token reuse, image bytes 0 = correct, same paint), image changed.
  - server (Source Paint box, `loadPaintByPath`): identical result (rev 2, fresh pixels sent, image changed after load and after refinish).
- Not verified: the owner's Electron build (needs their restart / Ctrl+R), paints that are not 2048x2048.

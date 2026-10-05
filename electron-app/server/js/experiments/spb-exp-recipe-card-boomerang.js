/* ============================================================================
 * SPB EXPERIMENT — Recipe Card Boomerang (executable recipe cards)
 * File: js/experiments/spb-exp-recipe-card-boomerang.js   (NEW FILE — no repo edits)
 *
 * "That recipe card he posted in Discord IS the paint file — drag the PNG into
 *  the booth and get his exact zones, finishes, and dials back in two seconds."
 *
 * What it does when ENABLED (total no-op until enable() is called):
 *   EXPORT SIDE — wraps the two existing card-export globals
 *     (window.exportRecipeCardPNG / window.copyRecipeCardToClipboard, defined
 *     in paint-booth-5-api-render.js:4761/4780, wired to the modal buttons in
 *     paint-booth-v2.html:2463/2465). The wrapped versions render the SAME
 *     card canvas (window._recipeCardCanvas, set at paint-booth-5:4751), then
 *     splice one PNG tEXt chunk (keyword "shokker-recipe", base64(UTF-8 JSON))
 *     right after IHDR before download/clipboard. The card LOOKS identical —
 *     it just silently carries the full zoneSnapshot (renderHistory[0]
 *     .zoneSnapshot, mirroring _buildRecipeFileObject at paint-booth-5:4861).
 *     regionMask blobs are stripped (masks are car-specific); which zones had
 *     masks is recorded in meta.maskedZones so the restore toast can say so.
 *   IMPORT SIDE —
 *     (a) document-level capture drop handler: drop a stamped card PNG
 *         anywhere in the booth → confirm → restore via window.spbApplyZones
 *         (the canonical external-script zone installer, paint-booth-5:5435,
 *         which runs _recipeSnapshotToZones + renderZones +
 *         triggerPreviewRender + autoSave in bundle scope). Plain PNGs dropped
 *         on the canvas area are FORWARDED untouched to the existing
 *         paint-file drop handler (paint-booth-3-canvas.js:9593) via a marked
 *         synthetic drop event, so normal paint-loading keeps working.
 *         Import-sidebar drop zones ([data-sidebar-drop-bound] /
 *         [data-ui-drop-bound] / aside[aria-label*="Import sidebar"] — see
 *         js/finishes/user-imports.js:503, user-import-gallery.js:29,
 *         user-import-shokk-world.js:690) are never intercepted.
 *     (b) wraps window.importRecipeFile (paint-booth-5:4916) so the existing
 *         "📥 Import Recipe" header button (paint-booth-v2.html:882) also
 *         accepts .png recipe cards next to .shokkerrecipe/.json.
 *
 * Zero server changes. The sacred SHOKK path is untouched. disable() restores
 * every wrapped global (only if still ours) and removes every listener/DOM node.
 * ==========================================================================*/
(function () {
    'use strict';

    var EXP_ID = 'recipe-card-boomerang';
    var CHUNK_KEYWORD = 'shokker-recipe';           // PNG tEXt keyword (Latin-1, 1-79 chars)
    var PAYLOAD_FORMAT = 'shokker-recipe-card';     // this experiment's payload format tag
    var LEGACY_FORMAT = 'shokker-recipe';           // accept .shokkerrecipe payloads too
    var MAX_EMBED_CHARS = 6 * 1024 * 1024;          // hard cap on the base64 text we embed
    var MAX_STRING_FIELD = 300000;                  // deep-drop any absurd string field (safety)

    var _enabled = false;
    var _orig = { exportPNG: null, copyCard: null, importRecipe: null };
    var _hadOwn = { exportPNG: false, copyCard: false, importRecipe: false };
    var _docDropHandler = null;
    var _docDragoverHandler = null;
    var _styleEl = null;
    var _hintEl = null;
    var _pickerInput = null;

    /* ------------------------------------------------------------------ *
     * Defensive access to app globals (classic-script lexical globals may
     * or may not be visible here depending on how experiments are loaded).
     * ------------------------------------------------------------------ */
    function _toast(msg, isErr) {
        try { if (typeof showToast === 'function') { showToast(msg, !!isErr); return; } } catch (_) { /* fall through */ }
        try { if (typeof window.showToast === 'function') { window.showToast(msg, !!isErr); return; } } catch (_) { /* fall through */ }
        try { console[isErr ? 'warn' : 'log']('[boomerang] ' + msg); } catch (_) { /* ignore */ }
    }

    function _liveSnapshot() {
        // Mirrors _buildRecipeFileObject (paint-booth-5-api-render.js:4861-4863):
        // last render's zoneSnapshot first, live zones as fallback.
        try {
            if (typeof renderHistory !== 'undefined' && renderHistory && renderHistory[0] &&
                Array.isArray(renderHistory[0].zoneSnapshot) && renderHistory[0].zoneSnapshot.length) {
                return renderHistory[0].zoneSnapshot;
            }
        } catch (_) { /* ignore */ }
        try {
            if (typeof window.renderHistory !== 'undefined' && window.renderHistory && window.renderHistory[0] &&
                Array.isArray(window.renderHistory[0].zoneSnapshot) && window.renderHistory[0].zoneSnapshot.length) {
                return window.renderHistory[0].zoneSnapshot;
            }
        } catch (_) { /* ignore */ }
        try { if (typeof zones !== 'undefined' && Array.isArray(zones) && zones.length) return zones; } catch (_) { /* ignore */ }
        try { if (Array.isArray(window.zones) && window.zones.length) return window.zones; } catch (_) { /* ignore */ }
        return null;
    }

    /* ------------------------------------------------------------------ *
     * PNG chunk plumbing (pure JS, ~CRC32 + one tEXt chunk after IHDR)
     * ------------------------------------------------------------------ */
    var _crcTable = null;
    function _crc32(bytes, start, end) {
        if (!_crcTable) {
            _crcTable = new Uint32Array(256);
            for (var n = 0; n < 256; n++) {
                var c = n;
                for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
                _crcTable[n] = c >>> 0;
            }
        }
        var crc = 0xFFFFFFFF;
        for (var i = start; i < end; i++) crc = _crcTable[(crc ^ bytes[i]) & 0xFF] ^ (crc >>> 8);
        return (crc ^ 0xFFFFFFFF) >>> 0;
    }

    var PNG_SIG = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
    function _isPngBytes(b) {
        if (!b || b.length < 8 + 25) return false; // sig + minimal IHDR chunk
        for (var i = 0; i < 8; i++) { if (b[i] !== PNG_SIG[i]) return false; }
        return true;
    }
    function _u32(b, o) { return ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) >>> 0; }
    function _chunkType(b, o) { return String.fromCharCode(b[o], b[o + 1], b[o + 2], b[o + 3]); }

    function _b64EncodeUtf8(str) {
        var bytes = new TextEncoder().encode(str);
        var bin = '';
        for (var i = 0; i < bytes.length; i += 8192) {
            bin += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + 8192, bytes.length)));
        }
        return btoa(bin);
    }
    function _b64DecodeUtf8(b64) {
        var bin = atob(b64);
        var bytes = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        return new TextDecoder('utf-8').decode(bytes);
    }

    /** length(4BE) + 'tEXt' + keyword + NUL + ascii text + crc32(type+data). */
    function _buildTextChunk(keyword, text) {
        var dataLen = keyword.length + 1 + text.length;
        var chunk = new Uint8Array(12 + dataLen);
        chunk[0] = (dataLen >>> 24) & 0xFF; chunk[1] = (dataLen >>> 16) & 0xFF;
        chunk[2] = (dataLen >>> 8) & 0xFF; chunk[3] = dataLen & 0xFF;
        chunk[4] = 0x74; chunk[5] = 0x45; chunk[6] = 0x58; chunk[7] = 0x74; // 'tEXt'
        var p = 8;
        for (var i = 0; i < keyword.length; i++) chunk[p++] = keyword.charCodeAt(i) & 0xFF;
        chunk[p++] = 0;
        for (var j = 0; j < text.length; j++) chunk[p++] = text.charCodeAt(j) & 0xFF;
        var crc = _crc32(chunk, 4, 8 + dataLen);
        chunk[p++] = (crc >>> 24) & 0xFF; chunk[p++] = (crc >>> 16) & 0xFF;
        chunk[p++] = (crc >>> 8) & 0xFF; chunk[p] = crc & 0xFF;
        return chunk;
    }

    /** Splice our tEXt chunk immediately after IHDR. Returns new bytes or null. */
    function _embedChunk(pngBytes, jsonText) {
        if (!_isPngBytes(pngBytes)) return null;
        var ihdrLen = _u32(pngBytes, 8);
        if (_chunkType(pngBytes, 12) !== 'IHDR') return null;
        var b64 = _b64EncodeUtf8(jsonText);
        if (b64.length > MAX_EMBED_CHARS) return null;
        var insertAt = 8 + 12 + ihdrLen;
        if (insertAt >= pngBytes.length) return null;
        var chunk = _buildTextChunk(CHUNK_KEYWORD, b64);
        var out = new Uint8Array(pngBytes.length + chunk.length);
        out.set(pngBytes.subarray(0, insertAt), 0);
        out.set(chunk, insertAt);
        out.set(pngBytes.subarray(insertAt), insertAt + chunk.length);
        return out;
    }

    /** Walk chunks; return the decoded JSON string from our tEXt chunk, or null. */
    function _extractChunk(pngBytes) {
        if (!_isPngBytes(pngBytes)) return null;
        var off = 8;
        while (off + 12 <= pngBytes.length) {
            var len = _u32(pngBytes, off);
            if (len > pngBytes.length) break; // corrupt guard
            var type = _chunkType(pngBytes, off + 4);
            if (type === 'tEXt' && len > CHUNK_KEYWORD.length + 1) {
                var ds = off + 8;
                var match = true;
                for (var i = 0; i < CHUNK_KEYWORD.length; i++) {
                    if (pngBytes[ds + i] !== CHUNK_KEYWORD.charCodeAt(i)) { match = false; break; }
                }
                if (match && pngBytes[ds + CHUNK_KEYWORD.length] === 0) {
                    var ts = ds + CHUNK_KEYWORD.length + 1;
                    var te = ds + len;
                    if (te > pngBytes.length) return null;
                    var b64 = '';
                    for (var s = ts; s < te; s += 8192) {
                        b64 += String.fromCharCode.apply(null, pngBytes.subarray(s, Math.min(s + 8192, te)));
                    }
                    try { return _b64DecodeUtf8(b64); } catch (_) { return null; }
                }
            }
            if (type === 'IEND') break;
            off += 12 + len;
        }
        return null;
    }

    /* ------------------------------------------------------------------ *
     * Payload build (export) / apply (import)
     * ------------------------------------------------------------------ */
    function _sanitizeSnapshot(snap) {
        var maskedZones = [];
        var out = [];
        for (var i = 0; i < snap.length; i++) {
            var z = snap[i];
            if (!z || typeof z !== 'object') continue;
            if (z.regionMask) maskedZones.push(z.name || ('Zone ' + (i + 1))); // masks are car-specific — do not travel
            var shallow = {};
            for (var k in z) { if (k !== 'regionMask') shallow[k] = z[k]; }
            var clean = null;
            try {
                clean = JSON.parse(JSON.stringify(shallow, function (key, v) {
                    if (typeof v === 'string' && v.length > MAX_STRING_FIELD) return undefined; // deep blob guard
                    if (typeof v === 'function') return undefined;
                    return v;
                }));
            } catch (_) { clean = null; }
            if (clean) out.push(clean);
        }
        return { zones: out, maskedZones: maskedZones };
    }

    function _buildPayload() {
        var snap = _liveSnapshot();
        if (!snap) return null;
        var s = _sanitizeSnapshot(snap);
        if (!s.zones.length) return null;
        var model = window._recipeCardModel || {};
        return {
            format: PAYLOAD_FORMAT,
            version: 1,
            app: 'Shokker Paint Booth',
            savedAt: new Date().toISOString(),
            meta: {
                zoneCount: s.zones.length,
                elapsed_seconds: (model.elapsed != null ? model.elapsed : null),
                paintFile: model.paintFile || '',
                maskedZones: s.maskedZones
            },
            zoneSnapshot: s.zones
        };
    }

    /** Restore zones from a decoded payload. Returns true if applied. */
    function _applyPayload(payload, sourceLabel) {
        var snap = payload && (payload.zoneSnapshot || payload.zones);
        if (!Array.isArray(snap) || !snap.length) {
            _toast('No recipe data found in ' + sourceLabel, true);
            return false;
        }
        if (!window.confirm('Import this recipe (' + snap.length + ' zones) from "' + sourceLabel + '"? Your current zones will be replaced.')) return false;
        if (typeof window.spbApplyZones !== 'function') {
            // spbApplyZones is the canonical external-scope installer (paint-booth-5:5435).
            _toast('Recipe restore unavailable in this build (spbApplyZones missing)', true);
            return false;
        }
        var ok = false;
        try { ok = window.spbApplyZones(snap); } catch (e) { _toast('Restore failed: ' + (e && e.message || e), true); return false; }
        if (ok) {
            var masked = (payload.meta && Array.isArray(payload.meta.maskedZones)) ? payload.meta.maskedZones : [];
            var msg = 'Recipe card imported — ' + snap.length + ' zones restored';
            if (masked.length) {
                msg += '. Zone masks are car-specific and did not travel — repaint masks for: ' +
                    masked.slice(0, 4).join(', ') + (masked.length > 4 ? ' (+' + (masked.length - 4) + ' more)' : '');
            }
            _toast(msg);
        }
        return ok;
    }

    /* ------------------------------------------------------------------ *
     * Blob/file byte helpers
     * ------------------------------------------------------------------ */
    function _blobBytes(blob) {
        if (blob && typeof blob.arrayBuffer === 'function') {
            return blob.arrayBuffer().then(function (buf) { return new Uint8Array(buf); });
        }
        return new Promise(function (resolve, reject) {
            var r = new FileReader();
            r.onload = function () { resolve(new Uint8Array(r.result)); };
            r.onerror = function () { reject(r.error || new Error('read failed')); };
            r.readAsArrayBuffer(blob);
        });
    }

    /** Stamp the recipe chunk into a card PNG blob; resolves the ORIGINAL blob on any failure. */
    function _stampBlob(blob) {
        return _blobBytes(blob).then(function (bytes) {
            var payload = _buildPayload();
            if (!payload) return blob;
            var stamped = _embedChunk(bytes, JSON.stringify(payload));
            return stamped ? new Blob([stamped], { type: 'image/png' }) : blob;
        }).catch(function () { return blob; });
    }

    /** Try to import a PNG File; resolves true if it contained an SPB recipe chunk. */
    function _tryImportPngFile(file) {
        return _blobBytes(file).then(function (bytes) {
            var json = _extractChunk(bytes);
            if (!json) return false;
            var payload = null;
            try { payload = JSON.parse(json); } catch (_) { payload = null; }
            if (!payload || (payload.format !== PAYLOAD_FORMAT && payload.format !== LEGACY_FORMAT)) return false;
            _applyPayload(payload, file.name || 'recipe card');
            return true; // chunk was present + valid — handled (even if the user cancels the confirm)
        });
    }

    function _looksLikePng(file) {
        if (!file) return false;
        if ((file.type || '') === 'image/png') return true;
        return /\.png$/i.test(file.name || '');
    }

    /* ------------------------------------------------------------------ *
     * EXPORT wrappers (mirror paint-booth-5-api-render.js:4761/4780 flows)
     * ------------------------------------------------------------------ */
    function _wrappedExportPNG() {
        var canvas = window._recipeCardCanvas;
        if (!canvas) { _toast('No recipe card to save yet', true); return; }
        var model = window._recipeCardModel || {};
        var stamp = new Date(model.timestamp || Date.now()).toISOString().replace(/[:.]/g, '-').slice(0, 19);
        var name = 'shokker-recipe-' + stamp + '.png';
        try {
            canvas.toBlob(function (blob) {
                if (!blob) { _toast('Could not export card image', true); return; }
                _stampBlob(blob).then(function (finalBlob) {
                    var stamped = (finalBlob !== blob);
                    var url = URL.createObjectURL(finalBlob);
                    var a = document.createElement('a'); a.href = url; a.download = name;
                    document.body.appendChild(a); a.click();
                    setTimeout(function () { try { URL.revokeObjectURL(url); a.remove(); } catch (_) { /* ignore */ } }, 1500);
                    _toast(stamped
                        ? '🪃 Recipe card saved: ' + name + ' — the PNG carries the FULL recipe. Share it as a FILE (Discord attachment); screenshots/embeds strip the data.'
                        : 'Recipe card saved: ' + name + ' (plain image — recipe data could not be embedded)');
                });
            }, 'image/png');
        } catch (e) { _toast('Export failed (canvas may be tainted): ' + (e && e.message || e), true); }
    }

    function _wrappedCopyCard() {
        var canvas = window._recipeCardCanvas;
        if (!canvas) { _toast('No recipe card to copy yet', true); return; }
        if (!navigator.clipboard || typeof window.ClipboardItem === 'undefined') {
            _toast('Image clipboard not supported here — use Save PNG instead', true); return;
        }
        new Promise(function (r) { canvas.toBlob(r, 'image/png'); }).then(function (blob) {
            if (!blob) { _toast('Could not render card image', true); return null; }
            return _stampBlob(blob).then(function (finalBlob) {
                return navigator.clipboard.write([new window.ClipboardItem({ 'image/png': finalBlob })]).then(function () {
                    _toast(finalBlob !== blob
                        ? '🪃 Recipe card copied with embedded recipe. Heads-up: some apps re-encode pasted images — Save Card PNG + attach as a file is bulletproof.'
                        : 'Recipe card copied — paste it into Discord!');
                });
            });
        }).catch(function (e) {
            _toast('Copy failed: ' + (e && e.message || e) + ' — try Save PNG', true);
        });
    }

    /* ------------------------------------------------------------------ *
     * IMPORT — wrapped picker (adds .png next to .shokkerrecipe/.json)
     * ------------------------------------------------------------------ */
    function _importJsonRecipeFile(file) {
        // Replicates _applyImportedRecipeFile (paint-booth-5:4933) via spbApplyZones.
        var reader = new FileReader();
        reader.onload = function () {
            var data = null;
            try { data = JSON.parse(reader.result); } catch (_) { _toast('That file is not a valid Shokker recipe', true); return; }
            _applyPayload(data, file.name || 'recipe file');
        };
        reader.onerror = function () { _toast('Could not read that file', true); };
        reader.readAsText(file);
    }

    function _wrappedImportRecipeFile() {
        if (!_pickerInput || !document.body.contains(_pickerInput)) {
            var inp = document.createElement('input');
            inp.type = 'file';
            inp.id = 'spbExpBoomerangImportInput';
            inp.accept = '.shokkerrecipe,.json,.png,application/json,image/png';
            inp.style.display = 'none';
            inp.addEventListener('change', function (ev) {
                var f = ev.target.files && ev.target.files[0];
                ev.target.value = '';
                if (!f) return;
                if (_looksLikePng(f)) {
                    _tryImportPngFile(f).then(function (handled) {
                        if (!handled) {
                            _toast('No SPB recipe found in that PNG — if it came from Discord, download the ORIGINAL attachment (embedded/preview images strip the recipe).', true);
                        }
                    }).catch(function (err) { _toast('Could not read that PNG: ' + (err && err.message || err), true); });
                } else {
                    _importJsonRecipeFile(f);
                }
            });
            document.body.appendChild(inp);
            _pickerInput = inp;
        }
        _pickerInput.click();
    }

    /* ------------------------------------------------------------------ *
     * IMPORT — document-level drag & drop
     * ------------------------------------------------------------------ */
    function _isExcludedTarget(t) {
        if (!t || typeof t.closest !== 'function') return false;
        // Never hijack the import-sidebar drop zones or file inputs:
        //   user-imports.js:503 → data-sidebar-drop-bound
        //   user-import-gallery.js:29 → data-ui-drop-bound
        //   user-import-shokk-world.js:690 → aside[aria-label*="Import sidebar"]
        return !!t.closest('[data-sidebar-drop-bound],[data-ui-drop-bound],aside[aria-label*="Import sidebar"],input[type="file"]');
    }

    function _centerPanel() {
        var vp = document.getElementById('canvasViewport');
        if (!vp) return null;
        return (typeof vp.closest === 'function' && vp.closest('.center-panel')) || vp;
    }

    /** Re-dispatch a plain PNG to the existing center-panel paint-drop handler
     *  (paint-booth-3-canvas.js:9593) via a marked synthetic drop event. */
    function _forwardDropToCenterPanel(cp, file) {
        try {
            var dt = new DataTransfer();
            dt.items.add(file);
            var evt = new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt });
            evt._spbBoomerangForwarded = true;
            cp.dispatchEvent(evt);
        } catch (e) {
            _toast('Could not hand that PNG to the paint loader — use the Load Paint button instead (' + (e && e.message || e) + ')', true);
        }
    }

    function _onDocumentDrop(e) {
        if (!_enabled || e._spbBoomerangForwarded) return;
        var dt = e.dataTransfer;
        var file = dt && dt.files && dt.files[0];
        if (!file || !_looksLikePng(file)) return;           // non-PNG drops: untouched
        if (_isExcludedTarget(e.target)) return;             // import sidebar etc.: untouched
        var cp = _centerPanel();
        var onCenter = !!(cp && e.target && cp.contains(e.target));
        e.preventDefault();
        e.stopPropagation(); // capture phase — the center-panel PNG→paint handler must not also fire
        if (cp) { cp.style.outline = ''; cp.style.outlineOffset = ''; } // replicate canvas.js:9589 cleanup
        _tryImportPngFile(file).then(function (handled) {
            if (handled) return;
            if (onCenter && cp) {
                _forwardDropToCenterPanel(cp, file);         // plain PNG on canvas → normal paint load
            } else {
                _toast('No SPB recipe found in that PNG — if it came from Discord, download the ORIGINAL attachment (previews/screenshots strip the recipe).', true);
            }
        }).catch(function (err) {
            _toast('Could not read that PNG: ' + (err && err.message || err), true);
        });
    }

    function _onDocumentDragover(e) {
        if (!_enabled) return;
        var dt = e.dataTransfer;
        if (!dt) return;
        var hasPng = false;
        try {
            var items = dt.items || [];
            for (var i = 0; i < items.length; i++) {
                if (items[i].kind === 'file' && items[i].type === 'image/png') { hasPng = true; break; }
            }
        } catch (_) { /* ignore */ }
        if (!hasPng) return;
        if (_isExcludedTarget(e.target)) return;
        e.preventDefault(); // makes the whole booth a legal drop surface for card PNGs
        try { dt.dropEffect = 'copy'; } catch (_) { /* ignore */ }
    }

    /* ------------------------------------------------------------------ *
     * Small UI hint inside the render-recipe modal (pure addition)
     * ------------------------------------------------------------------ */
    function _injectStyle() {
        if (_styleEl) return;
        _styleEl = document.createElement('style');
        _styleEl.id = 'spbExpBoomerangStyle';
        _styleEl.textContent =
            '.spb-exp-boomerang-hint{font-size:10px;color:var(--text-dim,#8b93a7);' +
            'border:1px dashed var(--accent-gold,#e8b64c);border-radius:6px;' +
            'padding:4px 10px;margin:4px 0 6px;line-height:1.5;opacity:.85;}' +
            '.spb-exp-boomerang-hint b{color:var(--accent-gold,#e8b64c);font-weight:700;}';
        document.head.appendChild(_styleEl);
    }

    function _injectHint() {
        if (_hintEl) return;
        var stage = document.getElementById('recipeCardStage'); // paint-booth-v2.html:2480
        if (!stage || !stage.parentNode) return;
        _hintEl = document.createElement('div');
        _hintEl.id = 'spbExpBoomerangHint';
        _hintEl.className = 'spb-exp-boomerang-hint';
        _hintEl.innerHTML = '<b>🪃 BOOMERANG ON</b> — “Save Card PNG” / “Copy Card” now embed the full recipe ' +
            'invisibly in the image. Anyone can drag that PNG back into their booth (or use 📥 Import Recipe) ' +
            'to restore every zone, finish, and dial. Share the PNG as a <b>file</b> — screenshots strip it.';
        stage.parentNode.insertBefore(_hintEl, stage);
    }

    /* ------------------------------------------------------------------ *
     * enable() / disable()
     * ------------------------------------------------------------------ */
    function _wrapGlobal(prop, key, wrapped) {
        _hadOwn[key] = (typeof window[prop] === 'function');
        _orig[key] = _hadOwn[key] ? window[prop] : null;
        window[prop] = wrapped;
    }

    function _unwrapGlobal(prop, key, wrapped) {
        if (window[prop] !== wrapped) return; // someone else re-wrapped — leave it alone
        if (_hadOwn[key] && _orig[key]) { window[prop] = _orig[key]; }
        else { try { delete window[prop]; } catch (_) { window[prop] = undefined; } }
        _orig[key] = null;
    }

    function enable() {
        if (_enabled) return;
        _enabled = true;
        _wrapGlobal('exportRecipeCardPNG', 'exportPNG', _wrappedExportPNG);      // paint-booth-5:4798
        _wrapGlobal('copyRecipeCardToClipboard', 'copyCard', _wrappedCopyCard); // paint-booth-5:4799
        _wrapGlobal('importRecipeFile', 'importRecipe', _wrappedImportRecipeFile); // paint-booth-5:4960
        _docDropHandler = _onDocumentDrop;
        _docDragoverHandler = _onDocumentDragover;
        document.addEventListener('drop', _docDropHandler, true);
        document.addEventListener('dragover', _docDragoverHandler, true);
        _injectStyle();
        _injectHint();
        _toast('🪃 Recipe Card Boomerang enabled — exported cards now carry the full recipe; drag a card PNG into the booth to restore it.');
    }

    function disable() {
        if (!_enabled) return;
        _enabled = false;
        _unwrapGlobal('exportRecipeCardPNG', 'exportPNG', _wrappedExportPNG);
        _unwrapGlobal('copyRecipeCardToClipboard', 'copyCard', _wrappedCopyCard);
        _unwrapGlobal('importRecipeFile', 'importRecipe', _wrappedImportRecipeFile);
        if (_docDropHandler) { document.removeEventListener('drop', _docDropHandler, true); _docDropHandler = null; }
        if (_docDragoverHandler) { document.removeEventListener('dragover', _docDragoverHandler, true); _docDragoverHandler = null; }
        if (_hintEl) { try { _hintEl.remove(); } catch (_) { /* ignore */ } _hintEl = null; }
        if (_styleEl) { try { _styleEl.remove(); } catch (_) { /* ignore */ } _styleEl = null; }
        if (_pickerInput) { try { _pickerInput.remove(); } catch (_) { /* ignore */ } _pickerInput = null; }
        _toast('Recipe Card Boomerang disabled — card export/import back to stock.');
    }

    /* ------------------------------------------------------------------ *
     * Self-registration (NO-OP until enable() is called)
     * ------------------------------------------------------------------ */
    window.SPB_EXPERIMENTS = window.SPB_EXPERIMENTS || [];
    var already = false;
    for (var r = 0; r < window.SPB_EXPERIMENTS.length; r++) {
        if (window.SPB_EXPERIMENTS[r] && window.SPB_EXPERIMENTS[r].id === EXP_ID) { already = true; break; }
    }
    if (!already) {
        window.SPB_EXPERIMENTS.push({
            id: EXP_ID,
            name: 'Recipe Card Boomerang (executable recipe cards)',
            pitch: 'That recipe card he posted in Discord IS the paint file — drag the PNG into the booth and get his exact zones, finishes, and dials back in two seconds.',
            enable: enable,
            disable: disable
        });
    }

    // Test-only hook (inert in the app: only exposed when __SPB_EXP_TEST__ is preset).
    if (window.__SPB_EXP_TEST__) {
        window.__SPB_EXP_BOOMERANG_TEST__ = {
            embedChunk: _embedChunk, extractChunk: _extractChunk,
            crc32: _crc32, sanitizeSnapshot: _sanitizeSnapshot, isPngBytes: _isPngBytes
        };
    }
})();

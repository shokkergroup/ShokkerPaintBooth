/* ============================================================================
 * SPB EXPERIMENT — "Blame the Dial" (two-render forensic diff)
 * File: js/experiments/spb-exp-blame-the-dial.js        (NEW file, additive)
 * ----------------------------------------------------------------------------
 * WHAT IT DOES
 *   The render-history gallery (openHistoryGallery, paint-booth-5-api-render.js
 *   :5232) already lets the painter pick two renders to compare
 *   (historyCompareA/B, :5228-5229) but only shows the two paint images side by
 *   side (:5311-5322). This experiment injects a third "WHAT CHANGED?" pane
 *   into that compare view with:
 *     1. a structured diff of the two full zoneSnapshots (captured per render
 *        at :3736-3746, 178 flat fields/zone verified against
 *        output/recent_renders/<slot>/recipe.json) rendered as human chips —
 *        "Body Color 1 · Finish: Metaball Plumes → Holographic Drift",
 *        "Base Scale: 1 → 0.5", "Spec stack 2: 1 → 2 layers (+hex_mesh)";
 *     2. a per-pixel deltaE heat overlay of the two paint_url images
 *        (redmean deltaE → SPB_FlashMap.heat ramp, paint-booth-flashmap.js:63);
 *     3. the same heat overlay for spec_url with per-channel (M/R/Cc/A)
 *        changed-pixel stats so invisible spec drift is caught;
 *     4. one-click "revert this zone" that rebuilds the zone list through
 *        window.spbApplyZones (:5435-5452, the sanctioned out-of-bundle way to
 *        reassign the top-level `let zones`, which normalizes through
 *        _recipeSnapshotToZones :5398).
 *
 * HOW IT HOOKS IN (no repo files edited)
 *   buildGalleryHTML() rewrites #historyGalleryOverlay.innerHTML on every
 *   selection click (:5356-5357), so we watch the overlay with a childList
 *   MutationObserver and (re)inject our pane into .history-compare-view
 *   whenever both compare slots are filled. Everything is created by enable()
 *   and torn down by disable(); until enable() runs this file only pushes its
 *   registry entry.
 *
 * GLOBALS USED (all behind typeof/try guards — module degrades gracefully):
 *   renderHistory        (const, paint-booth-2-state-zones.js:329)  read-only
 *   historyCompareA/B    (let,   paint-booth-5-api-render.js:5228)  read-only
 *   zones                (let,   paint-booth-2-state-zones.js:200)  read-only
 *   window.spbApplyZones (paint-booth-5-api-render.js:5452)         revert
 *   window.SPB_FlashMap.heat (paint-booth-flashmap.js:63)           heat ramp
 *   window.MONOLITHICS_BY_ID / BASES_BY_ID / PATTERNS_BY_ID
 *                        (paint-booth-0-finish-data.js:4873-4876)   id → name
 *   ShokkerAPI.baseUrl   (paint-booth-5-api-render.js:1513)         swatch URLs
 *   showToast            (paint-booth-2-state-zones.js:15300)       feedback
 *   /api/swatch/monolithic/<id>?color=888888&size=N                 finish thumbs
 * ========================================================================== */
(function () {
    'use strict';

    var EXP_ID = 'blame-the-dial';
    var PANE_ID = 'spbBtdPane';
    var STYLE_ID = 'spbBtdStyle';
    var ZOOM_ID = 'spbBtdZoom';
    var OVERLAY_ID = 'historyGalleryOverlay';   // built by openHistoryGallery (:5242)

    var enabled = false;
    var bodyObserver = null;
    var overlayObserver = null;
    var hookedOverlay = null;
    var injectQueued = false;
    var runToken = 0;                            // invalidates stale async work

    // ------------------------------------------------------------------ caches
    // Pixel diffs are ~1M px passes; buildGalleryHTML() re-runs on EVERY card
    // click, so cache finished diff canvases keyed by url pair (FIFO, cap 8).
    var diffCache = Object.create(null);
    var diffCacheOrder = [];
    var DIFF_CACHE_MAX = 8;

    /* =====================================================================
     * SECTION 1 — defensive accessors for bundle globals
     * =================================================================== */

    function getHistory() {
        try { if (typeof renderHistory !== 'undefined' && Array.isArray(renderHistory)) return renderHistory; } catch (_) {}
        try { if (Array.isArray(window.renderHistory)) return window.renderHistory; } catch (_) {}
        return null;
    }

    /** [idxA, idxB] of the gallery compare pair, or null if not both chosen. */
    function getComparePair() {
        try {
            if (typeof historyCompareA !== 'undefined' && typeof historyCompareB !== 'undefined' &&
                historyCompareA >= 0 && historyCompareB >= 0) {
                return [historyCompareA, historyCompareB];
            }
        } catch (_) {}
        // Fallback: parse "Comparing #3 vs #7" out of the compare bar the
        // gallery renders at paint-booth-5-api-render.js:5307.
        try {
            var span = document.querySelector('#' + OVERLAY_ID + ' .history-compare-bar span');
            if (span) {
                var m = /#(\d+)\s+vs\s+#(\d+)/.exec(span.textContent || '');
                if (m) return [parseInt(m[1], 10) - 1, parseInt(m[2], 10) - 1];
            }
        } catch (_) {}
        return null;
    }

    function getLiveZones() {
        try { if (typeof zones !== 'undefined' && Array.isArray(zones)) return zones; } catch (_) {}
        try { if (Array.isArray(window.zones)) return window.zones; } catch (_) {}
        return null;
    }

    function apiBase() {
        try {
            if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && ShokkerAPI.baseUrl) return ShokkerAPI.baseUrl;
        } catch (_) {}
        try { return window.location.origin || ''; } catch (_) { return ''; }
    }

    function toast(msg, isErr) {
        try { if (typeof showToast === 'function') { showToast(msg, !!isErr); return; } } catch (_) {}
        try { console.log('[blame-the-dial] ' + msg); } catch (_) {}
    }

    // Heat ramp: prefer the live SPB_FlashMap.heat (paint-booth-flashmap.js:63);
    // fall back to a byte-identical copy of its stops so the look matches.
    var FALLBACK_STOPS = [[24, 48, 130], [24, 168, 205], [235, 200, 45], [235, 45, 32]];
    function heat(t) {
        try {
            if (window.SPB_FlashMap && typeof window.SPB_FlashMap.heat === 'function') {
                return window.SPB_FlashMap.heat(t);
            }
        } catch (_) {}
        t = t < 0 ? 0 : (t > 1 ? 1 : t);
        var s = t * (FALLBACK_STOPS.length - 1);
        var i = Math.min(FALLBACK_STOPS.length - 2, Math.floor(s));
        var f = s - i;
        var a = FALLBACK_STOPS[i], b = FALLBACK_STOPS[i + 1];
        return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
    }

    /* =====================================================================
     * SECTION 2 — humanizing snapshot fields (labels + id → catalog names)
     * =================================================================== */

    // Curated labels for the dials painters actually blame. Everything else
    // falls through to humanizeKey().
    var LABELS = {
        finish: 'Finish', base: 'Base', pattern: 'Pattern', intensity: 'Intensity',
        scale: 'Pattern Scale', rotation: 'Pattern Rotation', patternOpacity: 'Pattern Opacity',
        patternIntensity: 'Pattern Intensity', patternSpecMult: 'Pattern Spec Mult',
        baseScale: 'Base Scale', baseStrength: 'Base Strength', baseSpecStrength: 'Base Spec Strength',
        baseRotation: 'Base Rotation', baseColor: 'Base Color', baseColorMode: 'Base Color Mode',
        baseColorStrength: 'Base Color Strength', baseHueOffset: 'Base Hue',
        baseSaturationAdjust: 'Base Saturation', baseBrightnessAdjust: 'Base Brightness',
        colors: 'Colors', colorMode: 'Color Mode', pickerColor: 'Picker Color',
        pickerTolerance: 'Picker Tolerance', wear: 'Wear', muted: 'Muted',
        ccQuality: 'Clearcoat Quality', blendBase: 'Blend Base', blendDir: 'Blend Direction',
        blendAmount: 'Blend Amount', usePaintReactive: 'Paint-Reactive Spec',
        paintReactiveColor: 'Paint-Reactive Color', hardEdge: 'Hard Edge',
        specScale: 'Spec Scale', specScaleMode: 'Spec Scale Mode',
        baseSpecBlendMode: 'Base Spec Blend', zoneSpecMapStrength: 'Zone Spec Map Strength',
        zoneSpecMapName: 'Zone Spec Map', gradientDirection: 'Gradient Direction',
        gradientStops: 'Gradient Stops', linkGroup: 'Link Group', name: 'Zone Name'
    };

    // The six layer stacks captured per zone (verified in recipe.json).
    var STACK_LABELS = {
        patternStack: 'Paint pattern stack',
        specPatternStack: 'Spec stack 1',
        overlaySpecPatternStack: 'Spec stack 2',
        thirdOverlaySpecPatternStack: 'Spec stack 3',
        fourthOverlaySpecPatternStack: 'Spec stack 4',
        fifthOverlaySpecPatternStack: 'Spec stack 5'
    };

    // Keys whose string values are catalog ids we can resolve to pretty names.
    function lookupName(key, id) {
        if (!id || typeof id !== 'string') return null;
        try {
            if (key === 'finish') {
                var mm = window.MONOLITHICS_BY_ID;
                if (mm && mm[id] && mm[id].name) return mm[id].name;
                if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) {
                    for (var i = 0; i < MONOLITHICS.length; i++) {
                        if (MONOLITHICS[i] && MONOLITHICS[i].id === id) return MONOLITHICS[i].name || id;
                    }
                }
            }
            if (/base/i.test(key) && window.BASES_BY_ID && window.BASES_BY_ID[id] && window.BASES_BY_ID[id].name) {
                return window.BASES_BY_ID[id].name;
            }
            if (/pattern/i.test(key) && window.PATTERNS_BY_ID && window.PATTERNS_BY_ID[id] && window.PATTERNS_BY_ID[id].name) {
                return window.PATTERNS_BY_ID[id].name;
            }
        } catch (_) {}
        return null;
    }

    /** camelCase → "Title Case", with 2nd/3rd/4th/5th tier prefixes. */
    function humanizeKey(key) {
        if (LABELS[key]) return LABELS[key];
        if (STACK_LABELS[key]) return STACK_LABELS[key];
        var s = String(key)
            .replace(/^second/, '2nd ').replace(/^third/, '3rd ')
            .replace(/^fourth/, '4th ').replace(/^fifth/, '5th ')
            .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
            .replace(/_/g, ' ');
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    function fmtNum(n) { return String(Math.round(n * 1000) / 1000); }

    /** One human string for a snapshot value (chips are textContent — safe). */
    function fmtVal(key, v) {
        if (v === null || v === undefined || v === '') return '—';
        if (typeof v === 'boolean') return v ? 'ON' : 'OFF';
        if (typeof v === 'number') return fmtNum(v);
        if (typeof v === 'string') {
            var pretty = lookupName(key, v);
            return pretty ? pretty : v;
        }
        if (Array.isArray(v)) {
            if (key === 'colors' || key === 'color') {
                var hexes = [];
                for (var i = 0; i < v.length; i++) hexes.push((v[i] && v[i].hex) ? v[i].hex : '?');
                return hexes.length ? hexes.join(' ') : 'none';
            }
            try { var j = JSON.stringify(v); return j.length > 48 ? j.slice(0, 45) + '…' : j; } catch (_) { return '[…]'; }
        }
        try { var js = JSON.stringify(v); return js.length > 48 ? js.slice(0, 45) + '…' : js; } catch (_) { return '{…}'; }
    }

    /** Short description of one layer stack: "2 layers: Swirl, Hex Mesh". */
    function describeStack(key, arr) {
        if (!Array.isArray(arr) || arr.length === 0) return 'empty';
        var names = [];
        for (var i = 0; i < arr.length; i++) {
            var l = arr[i] || {};
            var id = l.id || l.pattern || l.name || 'layer';
            names.push(lookupName('pattern', id) || id);
        }
        return arr.length + (arr.length === 1 ? ' layer: ' : ' layers: ') + names.join(', ');
    }

    /* =====================================================================
     * SECTION 3 — structured zoneSnapshot diff
     * =================================================================== */

    function deepEq(a, b) {
        if (a === b) return true;
        try { return JSON.stringify(a) === JSON.stringify(b); } catch (_) { return false; }
    }

    /**
     * Pair up zones between two snapshots: by id first (zone_<uuid>, stable
     * across renders of the same session), then by name, then leftovers are
     * added/removed. Returns [{a, b}] where either side may be null.
     */
    function pairZones(A, B) {
        A = Array.isArray(A) ? A : [];
        B = Array.isArray(B) ? B : [];
        var used = [];
        for (var k = 0; k < B.length; k++) used.push(false);
        var pairs = [];
        A.forEach(function (za) {
            var j = -1, k;
            if (za && za.id) {
                for (k = 0; k < B.length; k++) if (!used[k] && B[k] && B[k].id === za.id) { j = k; break; }
            }
            if (j < 0 && za) {
                for (k = 0; k < B.length; k++) if (!used[k] && B[k] && B[k].name === za.name) { j = k; break; }
            }
            if (j >= 0) { used[j] = true; pairs.push({ a: za, b: B[j] }); }
            else pairs.push({ a: za, b: null });
        });
        for (var k2 = 0; k2 < B.length; k2++) if (!used[k2]) pairs.push({ a: null, b: B[k2] });
        return pairs;
    }

    /**
     * Diff one paired zone. Returns change records:
     *   { key, label, aText, bText, kind: 'field'|'stack'|'finish' }
     * `id` is skipped (identity, not a dial); the stacks get one summarized
     * record each instead of a raw JSON chip.
     */
    function diffZonePair(a, b) {
        var out = [];
        var keys = {};
        var k;
        for (k in a) if (Object.prototype.hasOwnProperty.call(a, k)) keys[k] = 1;
        for (k in b) if (Object.prototype.hasOwnProperty.call(b, k)) keys[k] = 1;
        delete keys.id;
        Object.keys(keys).forEach(function (key) {
            var va = a[key], vb = b[key];
            if (deepEq(va, vb)) return;
            if (STACK_LABELS[key]) {
                var la = Array.isArray(va) ? va.length : 0;
                var lb = Array.isArray(vb) ? vb.length : 0;
                var extra = (la === lb) ? ' (layer params changed)' : '';
                out.push({
                    key: key, label: STACK_LABELS[key], kind: 'stack',
                    aText: describeStack(key, va), bText: describeStack(key, vb) + extra
                });
                return;
            }
            out.push({
                key: key, label: humanizeKey(key),
                kind: key === 'finish' ? 'finish' : 'field',
                aText: fmtVal(key, va), bText: fmtVal(key, vb),
                aRaw: va, bRaw: vb
            });
        });
        // Finish first, then stacks, then alphabetical — the blame usually
        // lives at the top.
        out.sort(function (x, y) {
            var rank = function (c) { return c.kind === 'finish' ? 0 : (c.kind === 'stack' ? 1 : 2); };
            var d = rank(x) - rank(y);
            return d !== 0 ? d : (x.label < y.label ? -1 : 1);
        });
        return out;
    }

    /* =====================================================================
     * SECTION 4 — pixel diff (paint deltaE / spec per-channel) + heat canvas
     * =================================================================== */

    function loadImage(url) {
        return new Promise(function (resolve, reject) {
            if (!url) { reject(new Error('no url')); return; }
            var img = new Image();
            img.crossOrigin = 'anonymous';   // same pattern as showRenderDiff (:3922)
            img.onload = function () { resolve(img); };
            img.onerror = function () { reject(new Error('image load failed: ' + url)); };
            img.src = url;
        });
    }

    /**
     * Compute a heat-map diff canvas for two same-car images.
     * mode 'paint': perceptual redmean deltaE drives the heat.
     * mode 'spec' : max per-channel byte delta drives the heat + per-channel
     *               changed-pixel percentages (R=Metallic, G=Roughness,
     *               B=Clearcoat, A=Spec mask — shokker_engine_v2.py channel
     *               semantics, same labels as showSpecChannels :3775).
     * Resolves { canvas, stats:{ pct, chPct? , w, h } }. Cached per url pair.
     */
    function computePixelDiff(urlA, urlB, mode) {
        var cacheKey = mode + '|' + urlA + '|' + urlB;
        if (diffCache[cacheKey]) return Promise.resolve(diffCache[cacheKey]);
        return Promise.all([loadImage(urlA), loadImage(urlB)]).then(function (imgs) {
            var iA = imgs[0], iB = imgs[1];
            var w0 = Math.min(iA.naturalWidth, iB.naturalWidth);
            var h0 = Math.min(iA.naturalHeight, iB.naturalHeight);
            if (!w0 || !h0) throw new Error('zero-size image');
            // Cap the diff pass at 1024 on the long edge — plenty for a heat
            // overlay, keeps the pass ~1M px (fast even on weak iGPUs).
            var sc = Math.min(1, 1024 / Math.max(w0, h0));
            var w = Math.max(1, Math.round(w0 * sc));
            var h = Math.max(1, Math.round(h0 * sc));

            function toData(img) {
                var c = document.createElement('canvas');
                c.width = w; c.height = h;
                var ctx = c.getContext('2d', { willReadFrequently: true });
                ctx.drawImage(img, 0, 0, w, h);
                return ctx.getImageData(0, 0, w, h).data;
            }
            var dA = toData(iA), dB = toData(iB);

            var out = document.createElement('canvas');
            out.width = w; out.height = h;
            var oCtx = out.getContext('2d');
            var oImg = oCtx.createImageData(w, h);
            var oD = oImg.data;

            var changed = 0;
            var chChanged = [0, 0, 0, 0];   // M(R) / R(G) / Cc(B) / A
            var n = w * h;
            for (var i = 0; i < dA.length; i += 4) {
                var t;
                if (mode === 'spec') {
                    var d0 = Math.abs(dA[i] - dB[i]);
                    var d1 = Math.abs(dA[i + 1] - dB[i + 1]);
                    var d2 = Math.abs(dA[i + 2] - dB[i + 2]);
                    var d3 = Math.abs(dA[i + 3] - dB[i + 3]);
                    if (d0 > 10) chChanged[0]++;
                    if (d1 > 10) chChanged[1]++;
                    if (d2 > 10) chChanged[2]++;
                    if (d3 > 10) chChanged[3]++;
                    var dm = Math.max(d0, d1, d2, d3);
                    if (dm > 10) changed++;
                    t = dm / 96; if (t > 1) t = 1;
                } else {
                    // redmean deltaE — perceptual, cheap, no colorspace tables
                    var dr = dA[i] - dB[i];
                    var dg = dA[i + 1] - dB[i + 1];
                    var db = dA[i + 2] - dB[i + 2];
                    var rbar = (dA[i] + dB[i]) / 2;
                    var dE = Math.sqrt(
                        (2 + rbar / 256) * dr * dr + 4 * dg * dg +
                        (2 + (255 - rbar) / 256) * db * db
                    );
                    if (dE > 12) changed++;
                    t = dE / 180; if (t > 1) t = 1;
                }
                if (t <= 0.04) {
                    // unchanged: dim grayscale of render B for spatial context
                    var lum = (dB[i] * 0.299 + dB[i + 1] * 0.587 + dB[i + 2] * 0.114) * 0.22;
                    oD[i] = lum; oD[i + 1] = lum; oD[i + 2] = lum; oD[i + 3] = 255;
                } else {
                    var rgb = heat(t);
                    oD[i] = rgb[0]; oD[i + 1] = rgb[1]; oD[i + 2] = rgb[2]; oD[i + 3] = 255;
                }
            }
            oCtx.putImageData(oImg, 0, 0);

            var stats = { pct: (changed / n) * 100, w: w, h: h };
            if (mode === 'spec') {
                stats.chPct = {
                    M: (chChanged[0] / n) * 100,
                    R: (chChanged[1] / n) * 100,
                    Cc: (chChanged[2] / n) * 100,
                    A: (chChanged[3] / n) * 100
                };
            }
            var result = { canvas: out, stats: stats };
            diffCache[cacheKey] = result;
            diffCacheOrder.push(cacheKey);
            while (diffCacheOrder.length > DIFF_CACHE_MAX) {
                delete diffCache[diffCacheOrder.shift()];
            }
            return result;
        });
    }

    /* =====================================================================
     * SECTION 5 — revert one zone through spbApplyZones
     * =================================================================== */

    // Mirror of the render-time snapshot skip list (paint-booth-5:3739-3740)
    // so live zones survive a JSON round-trip when we rebuild the array.
    var SKIP_KEYS = {
        regionMask: 1, spatialMask: 1, sourceLayerMask: 1,
        sourceLayerRgb: 1, pattern_strength_map: 1
    };
    function serializeLiveZone(z) {
        var o = {};
        for (var k in z) {
            if (!Object.prototype.hasOwnProperty.call(z, k)) continue;
            if (SKIP_KEYS[k] || k.charAt(0) === '_') continue;
            var v = z[k];
            if (typeof v === 'function' || v === undefined) continue;
            o[k] = v;
        }
        return JSON.parse(JSON.stringify(o));
    }

    /**
     * Replace ONE live zone's dials with its snapshot from history entry
     * `histIdx`, leaving every other zone as it currently is, then apply via
     * window.spbApplyZones (renders zones, kicks the preview, autosaves —
     * paint-booth-5:5435-5452). Same caveat as the built-in double-click
     * restore: region masks are transient and reset (snapshot never carries
     * them, _recipeSnapshotToZones nulls them at :5425).
     */
    function revertZoneToHistory(histIdx, zoneId, zoneName) {
        var hist = getHistory();
        var entry = hist && hist[histIdx];
        if (!entry || !Array.isArray(entry.zoneSnapshot)) { toast('No zone snapshot on render #' + (histIdx + 1), true); return; }
        var snapZone = null;
        for (var i = 0; i < entry.zoneSnapshot.length; i++) {
            var sz = entry.zoneSnapshot[i];
            if (!sz) continue;
            if ((zoneId && sz.id === zoneId) || (!snapZone && sz.name === zoneName)) { snapZone = sz; if (zoneId && sz.id === zoneId) break; }
        }
        if (!snapZone) { toast('Zone "' + zoneName + '" not found in render #' + (histIdx + 1), true); return; }

        var live = getLiveZones();
        if (!live || !live.length) { toast('Live zones unavailable — cannot revert', true); return; }
        var apply = (typeof window.spbApplyZones === 'function') ? window.spbApplyZones : null;
        if (!apply) { toast('spbApplyZones missing — cannot revert (needs paint-booth-5 build ≥ 2026-06-13)', true); return; }

        var raw = [];
        var targetIdx = -1;
        for (var j = 0; j < live.length; j++) {
            raw.push(serializeLiveZone(live[j]));
            if (targetIdx < 0 && ((zoneId && live[j].id === zoneId) || live[j].name === zoneName)) targetIdx = j;
        }
        if (targetIdx < 0) { toast('Zone "' + zoneName + '" is not in your current config — nothing to revert', true); return; }

        if (!window.confirm('Revert zone "' + zoneName + '" to its dials from render #' + (histIdx + 1) +
            '?\n\nOther zones keep their current settings. (Region masks reset — same as a history restore.)')) return;

        raw[targetIdx] = JSON.parse(JSON.stringify(snapZone));
        var ok = false;
        try { ok = apply(raw); } catch (e) { try { console.error('[blame-the-dial] revert failed:', e); } catch (_) {} }
        if (ok) {
            toast('Zone "' + zoneName + '" reverted to render #' + (histIdx + 1));
            try { if (typeof closeHistoryGallery === 'function') closeHistoryGallery(); } catch (_) {}
        } else {
            toast('Revert did not apply — see console', true);
        }
    }

    /* =====================================================================
     * SECTION 6 — DOM: the "WHAT CHANGED?" pane
     * =================================================================== */

    function el(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined && text !== null) e.textContent = text;   // textContent only — no HTML injection
        return e;
    }

    function swatchImg(finishId) {
        var img = document.createElement('img');
        img.className = 'spb-btd-swatch';
        img.loading = 'lazy';
        img.alt = '';
        img.onerror = function () { img.style.display = 'none'; };
        img.src = apiBase() + '/api/swatch/monolithic/' + encodeURIComponent(finishId) + '?color=888888&size=28';
        return img;
    }

    function colorDots(container, key, raw) {
        if ((key !== 'colors' && key !== 'color') || !Array.isArray(raw)) return false;
        for (var i = 0; i < Math.min(raw.length, 6); i++) {
            var hex = raw[i] && raw[i].hex;
            if (!hex) continue;
            var dot = el('span', 'spb-btd-dot');
            dot.style.background = hex;
            dot.title = hex;
            container.appendChild(dot);
        }
        return raw.length > 0;
    }

    /** One chip: [label] old → new (with swatches for finish, dots for colors). */
    function buildChip(change) {
        var chip = el('div', 'spb-btd-chip');
        chip.appendChild(el('span', 'spb-btd-chip-label', change.label));
        var vals = el('span', 'spb-btd-chip-vals');

        var aWrap = el('span', 'spb-btd-val spb-btd-val-a');
        if (change.kind === 'finish' && typeof change.aRaw === 'string' && change.aRaw) aWrap.appendChild(swatchImg(change.aRaw));
        if (!colorDots(aWrap, change.key, change.aRaw)) { /* dots or text below */ }
        aWrap.appendChild(el('span', null, change.aText));

        var bWrap = el('span', 'spb-btd-val spb-btd-val-b');
        if (change.kind === 'finish' && typeof change.bRaw === 'string' && change.bRaw) bWrap.appendChild(swatchImg(change.bRaw));
        if (!colorDots(bWrap, change.key, change.bRaw)) { /* dots or text below */ }
        bWrap.appendChild(el('span', null, change.bText));

        vals.appendChild(aWrap);
        vals.appendChild(el('span', 'spb-btd-arrow', '→'));
        vals.appendChild(bWrap);
        chip.appendChild(vals);
        return chip;
    }

    function buildZoneBlock(pair, changes, idxOld, idxNew) {
        var name = (pair.a && pair.a.name) || (pair.b && pair.b.name) || 'Zone';
        var zid = (pair.a && pair.a.id) || (pair.b && pair.b.id) || null;
        var block = el('div', 'spb-btd-zone');
        var head = el('div', 'spb-btd-zonehead');
        head.appendChild(el('span', 'spb-btd-zonename', name));

        if (!pair.a || !pair.b) {
            head.appendChild(el('span', 'spb-btd-badge', !pair.a ? 'ZONE ADDED' : 'ZONE REMOVED'));
            block.appendChild(head);
            return block;
        }

        // Revert buttons — one per side of the compare, oldest first.
        var canRevert = typeof window.spbApplyZones === 'function' && getLiveZones();
        if (canRevert) {
            [idxOld, idxNew].forEach(function (hIdx) {
                var btn = el('button', 'btn btn-sm spb-btd-revert', '⟲ #' + (hIdx + 1));
                btn.title = 'Set this zone back to its dials from render #' + (hIdx + 1);
                btn.addEventListener('click', function (ev) {
                    ev.stopPropagation();
                    revertZoneToHistory(hIdx, zid, name);
                });
                head.appendChild(btn);
            });
        }
        block.appendChild(head);

        var chipsWrap = el('div', 'spb-btd-chips');
        var SHOW = 10;
        changes.forEach(function (c, i) {
            var chip = buildChip(c);
            if (i >= SHOW) chip.classList.add('spb-btd-hidden');
            chipsWrap.appendChild(chip);
        });
        if (changes.length > SHOW) {
            var more = el('button', 'btn btn-sm spb-btd-more', '+ ' + (changes.length - SHOW) + ' more dials');
            more.addEventListener('click', function () {
                var hidden = chipsWrap.querySelectorAll('.spb-btd-hidden');
                for (var i = 0; i < hidden.length; i++) hidden[i].classList.remove('spb-btd-hidden');
                more.remove();
            });
            chipsWrap.appendChild(more);
        }
        block.appendChild(chipsWrap);
        return block;
    }

    /** Fullscreen zoom of a diff canvas (click-to-open, click/Esc to close). */
    function openZoom(canvas, title) {
        closeZoom();
        var wrap = el('div', null);
        wrap.id = ZOOM_ID;
        wrap.appendChild(el('div', 'spb-btd-zoom-title', title));
        var img = document.createElement('img');
        try { img.src = canvas.toDataURL('image/png'); } catch (e) { toast('Zoom failed (canvas tainted?)', true); return; }
        img.alt = title;
        wrap.appendChild(img);
        wrap.appendChild(el('div', 'spb-btd-zoom-hint', 'click anywhere or press Esc to close'));
        wrap.addEventListener('click', closeZoom);
        document.body.appendChild(wrap);
    }
    function closeZoom() {
        var z = document.getElementById(ZOOM_ID);
        if (z) z.remove();
    }
    function onKeyDown(ev) {
        if (ev.key === 'Escape') closeZoom();
    }

    function buildMapCell(label, promise, pane, token) {
        var cell = el('div', 'spb-btd-map');
        cell.appendChild(el('div', 'spb-btd-map-label', label));
        var slot = el('div', 'spb-btd-map-slot', 'computing…');
        cell.appendChild(slot);
        promise.then(function (res) {
            if (token !== runToken || !pane.isConnected) return;   // stale gallery pass
            slot.textContent = '';
            res.canvas.classList.add('spb-btd-canvas');
            res.canvas.title = 'Click to zoom';
            res.canvas.addEventListener('click', function () { openZoom(res.canvas, label); });
            slot.appendChild(res.canvas);
            var statLine = res.stats.pct.toFixed(2) + '% of pixels changed';
            slot.appendChild(el('div', 'spb-btd-map-stat', statLine));
            if (res.stats.chPct) {
                var c = res.stats.chPct;
                slot.appendChild(el('div', 'spb-btd-map-stat spb-btd-map-ch',
                    'M ' + c.M.toFixed(1) + '% · R ' + c.R.toFixed(1) + '% · Cc ' + c.Cc.toFixed(1) + '% · A ' + c.A.toFixed(1) + '%'));
            }
        }).catch(function (e) {
            if (token !== runToken || !pane.isConnected) return;
            slot.textContent = 'diff unavailable (' + ((e && e.message) || 'error') + ')';
            slot.classList.add('spb-btd-map-err');
        });
        return cell;
    }

    /** Build the full pane for compare pair [idxA, idxB]. */
    function buildPane(pair) {
        var token = ++runToken;
        var hist = getHistory();
        var a = hist ? hist[pair[0]] : null;
        var b = hist ? hist[pair[1]] : null;

        var pane = el('div', 'history-compare-pane spb-btd-pane');
        pane.id = PANE_ID;
        pane.appendChild(el('div', 'compare-label spb-btd-title', 'WHAT CHANGED? — BLAME THE DIAL'));

        if (!a || !b) {
            pane.appendChild(el('div', 'spb-btd-note',
                'Render history entries unreachable — snapshot diff unavailable. (Pixel diff needs the history too.)'));
            return pane;
        }

        // Chronology: renderHistory is unshift()-newest-first (:3748), but use
        // timestamps so the arrow always reads OLD -> NEW.
        var aIsOlder = (a.timestamp || 0) <= (b.timestamp || 0);
        var idxOld = aIsOlder ? pair[0] : pair[1];
        var idxNew = aIsOlder ? pair[1] : pair[0];
        var oldE = aIsOlder ? a : b;
        var newE = aIsOlder ? b : a;
        var apart = Math.abs(pair[0] - pair[1]);

        pane.appendChild(el('div', 'spb-btd-sub',
            '#' + (idxOld + 1) + ' (older) → #' + (idxNew + 1) + ' (newer) · ' + apart + ' render' + (apart === 1 ? '' : 's') + ' apart'));

        // ---------------- structured snapshot diff ----------------
        var body = el('div', 'spb-btd-body');
        pane.appendChild(body);

        var snapOld = oldE.zoneSnapshot, snapNew = newE.zoneSnapshot;
        if (Array.isArray(snapOld) && Array.isArray(snapNew)) {
            var pairs = pairZones(snapOld, snapNew);
            var totalDials = 0, zonesTouched = 0;
            var blocks = [];
            pairs.forEach(function (zp) {
                if (zp.a && zp.b) {
                    var changes = diffZonePair(zp.a, zp.b);
                    if (changes.length) {
                        totalDials += changes.length;
                        zonesTouched++;
                        blocks.push(buildZoneBlock(zp, changes, idxOld, idxNew));
                    }
                } else {
                    zonesTouched++;
                    blocks.push(buildZoneBlock(zp, [], idxOld, idxNew));
                }
            });
            // Global (non-zone) dials that ride on the entry metadata (:3729)
            var mOld = (oldE.metadata || {}), mNew = (newE.metadata || {});
            if (!deepEq(mOld.wear, mNew.wear)) {
                totalDials++;
                var gBlock = el('div', 'spb-btd-zone');
                var gHead = el('div', 'spb-btd-zonehead');
                gHead.appendChild(el('span', 'spb-btd-zonename', 'Global'));
                gBlock.appendChild(gHead);
                var gChips = el('div', 'spb-btd-chips');
                gChips.appendChild(buildChip({
                    key: 'wear', label: 'Wear Level', kind: 'field',
                    aText: fmtVal('wear', mOld.wear), bText: fmtVal('wear', mNew.wear)
                }));
                gBlock.appendChild(gChips);
                blocks.push(gBlock);
            }

            body.appendChild(el('div', 'spb-btd-summary',
                totalDials === 0
                    ? 'No dial changes found — any pixel drift below is render variance.'
                    : totalDials + ' dial' + (totalDials === 1 ? '' : 's') + ' changed across ' +
                      zonesTouched + ' zone' + (zonesTouched === 1 ? '' : 's') + ':'));
            blocks.forEach(function (blk) { body.appendChild(blk); });
        } else {
            body.appendChild(el('div', 'spb-btd-note', 'One of the two renders has no zone snapshot — showing pixel diff only.'));
        }

        // ---------------- pixel heat maps (paint + spec) ----------------
        var maps = el('div', 'spb-btd-maps');
        pane.appendChild(maps);
        if (oldE.paint_url && newE.paint_url) {
            maps.appendChild(buildMapCell('PAINT Δ (deltaE heat)',
                computePixelDiff(oldE.paint_url, newE.paint_url, 'paint'), pane, token));
        }
        if (oldE.spec_url && newE.spec_url) {
            maps.appendChild(buildMapCell('SPEC Δ (M/R/Cc/A heat)',
                computePixelDiff(oldE.spec_url, newE.spec_url, 'spec'), pane, token));
        } else {
            maps.appendChild(el('div', 'spb-btd-note', 'No spec image on one of these renders — spec drift check skipped.'));
        }

        return pane;
    }

    /* =====================================================================
     * SECTION 7 — injection lifecycle (gallery rebuilds innerHTML per click)
     * =================================================================== */

    function injectPanel() {
        if (!enabled) return;
        var overlay = document.getElementById(OVERLAY_ID);
        if (!overlay) return;
        if (document.getElementById(PANE_ID)) return;             // already injected this pass
        var view = overlay.querySelector('.history-compare-view');  // built at :5311
        var cmpPair = getComparePair();
        if (!view || !cmpPair) return;
        try {
            view.appendChild(buildPane(cmpPair));
        } catch (e) {
            try { console.error('[blame-the-dial] pane build failed:', e); } catch (_) {}
        }
    }

    function scheduleInject() {
        if (injectQueued || !enabled) return;
        injectQueued = true;
        // rAF debounce: buildGalleryHTML replaces the WHOLE overlay innerHTML on
        // every card click (:5356-5357); coalesce bursts into one inject.
        window.requestAnimationFrame(function () {
            injectQueued = false;
            injectPanel();
        });
    }

    function hookOverlay() {
        var overlay = document.getElementById(OVERLAY_ID);
        if (!overlay) {
            if (overlayObserver) { overlayObserver.disconnect(); overlayObserver = null; }
            hookedOverlay = null;
            return;
        }
        if (hookedOverlay === overlay) { scheduleInject(); return; }
        if (overlayObserver) overlayObserver.disconnect();
        hookedOverlay = overlay;
        overlayObserver = new MutationObserver(scheduleInject);
        // childList only (no subtree): our own pane lands INSIDE
        // .history-compare-view, so appending it never re-fires this observer.
        overlayObserver.observe(overlay, { childList: true });
        scheduleInject();
    }

    function injectStyle() {
        if (document.getElementById(STYLE_ID)) return;
        var css = '' +
            '.spb-btd-pane{flex:1.15;min-width:300px;text-align:left;background:var(--bg-card,#12151c);' +
            'border:1px solid var(--accent-gold,#fa0);border-radius:6px;padding:10px 12px;' +
            'overflow-y:auto;max-height:100%;box-shadow:0 0 14px rgba(255,170,0,0.12);}' +
            '.spb-btd-title{color:var(--accent-gold,#fa0)!important;text-align:left;}' +
            '.spb-btd-sub{font-size:10px;color:var(--text-dim,#8892a4);margin-bottom:6px;}' +
            '.spb-btd-summary{font-size:11px;color:#eee;margin:6px 0;}' +
            '.spb-btd-note{font-size:10px;color:var(--text-dim,#8892a4);font-style:italic;margin:6px 0;}' +
            '.spb-btd-zone{border:1px solid var(--border,#2a3040);border-radius:5px;padding:6px 8px;margin:6px 0;background:rgba(255,255,255,0.02);}' +
            '.spb-btd-zonehead{display:flex;align-items:center;gap:6px;margin-bottom:4px;}' +
            '.spb-btd-zonename{font-size:11px;font-weight:700;color:var(--accent-blue,#36f);letter-spacing:0.5px;}' +
            '.spb-btd-badge{font-size:8px;font-weight:700;padding:1px 5px;border-radius:3px;background:rgba(255,102,102,0.18);color:#ff6666;}' +
            '.spb-btd-revert{font-size:9px!important;padding:1px 6px!important;margin-left:auto;}' +
            '.spb-btd-revert+.spb-btd-revert{margin-left:4px;}' +
            '.spb-btd-chips{display:flex;flex-direction:column;gap:3px;}' +
            '.spb-btd-chip{display:flex;align-items:center;gap:6px;font-size:10px;background:rgba(255,170,0,0.06);' +
            'border:1px solid rgba(255,170,0,0.25);border-radius:4px;padding:2px 6px;flex-wrap:wrap;}' +
            '.spb-btd-chip-label{color:var(--accent-gold,#fa0);font-weight:600;white-space:nowrap;}' +
            '.spb-btd-chip-vals{display:flex;align-items:center;gap:5px;flex-wrap:wrap;min-width:0;}' +
            '.spb-btd-val{display:inline-flex;align-items:center;gap:3px;color:#ddd;word-break:break-word;}' +
            '.spb-btd-val-a{color:#9aa5b8;}' +
            '.spb-btd-val-b{color:#fff;font-weight:600;}' +
            '.spb-btd-arrow{color:var(--accent-gold,#fa0);font-weight:700;}' +
            '.spb-btd-swatch{width:16px;height:16px;border-radius:3px;border:1px solid var(--border,#2a3040);object-fit:cover;}' +
            '.spb-btd-dot{display:inline-block;width:10px;height:10px;border-radius:50%;border:1px solid rgba(255,255,255,0.4);}' +
            '.spb-btd-hidden{display:none;}' +
            '.spb-btd-more{font-size:9px!important;padding:1px 6px!important;align-self:flex-start;}' +
            '.spb-btd-maps{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;}' +
            '.spb-btd-map{flex:1;min-width:130px;}' +
            '.spb-btd-map-label{font-size:9px;color:var(--text-dim,#8892a4);letter-spacing:0.5px;margin-bottom:3px;}' +
            '.spb-btd-map-slot{font-size:9px;color:var(--text-dim,#8892a4);}' +
            '.spb-btd-map-err{color:#ff6666;}' +
            '.spb-btd-canvas{width:100%;height:auto;border:1px solid var(--border,#2a3040);border-radius:4px;cursor:zoom-in;display:block;}' +
            '.spb-btd-map-stat{font-size:9px;color:#eee;margin-top:2px;}' +
            '.spb-btd-map-ch{color:var(--text-dim,#8892a4);}' +
            '#' + ZOOM_ID + '{position:fixed;inset:0;background:rgba(0,0,0,0.94);z-index:10050;display:flex;' +
            'flex-direction:column;align-items:center;justify-content:center;gap:8px;cursor:zoom-out;padding:20px;}' +
            '#' + ZOOM_ID + ' img{max-width:92vw;max-height:84vh;border:1px solid var(--border,#2a3040);border-radius:4px;image-rendering:auto;}' +
            '#' + ZOOM_ID + ' .spb-btd-zoom-title{color:var(--accent-gold,#fa0);font-size:12px;letter-spacing:1px;}' +
            '#' + ZOOM_ID + ' .spb-btd-zoom-hint{color:var(--text-dim,#8892a4);font-size:10px;}';
        var style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = css;
        document.head.appendChild(style);
    }

    /* =====================================================================
     * SECTION 8 — experiment registry contract
     * =================================================================== */

    function enable() {
        if (enabled) return;
        enabled = true;
        injectStyle();
        try {
            bodyObserver = new MutationObserver(hookOverlay);
            bodyObserver.observe(document.body, { childList: true });
        } catch (e) {
            try { console.error('[blame-the-dial] observer setup failed:', e); } catch (_) {}
        }
        document.addEventListener('keydown', onKeyDown);
        hookOverlay();   // gallery may already be open with a pair selected
    }

    function disable() {
        if (!enabled) return;
        enabled = false;
        runToken++;                                   // orphan any in-flight diffs
        if (bodyObserver) { bodyObserver.disconnect(); bodyObserver = null; }
        if (overlayObserver) { overlayObserver.disconnect(); overlayObserver = null; }
        hookedOverlay = null;
        injectQueued = false;
        document.removeEventListener('keydown', onKeyDown);
        closeZoom();
        var pane = document.getElementById(PANE_ID);
        if (pane) pane.remove();
        var style = document.getElementById(STYLE_ID);
        if (style) style.remove();
        diffCache = Object.create(null);
        diffCacheOrder = [];
    }

    window.SPB_EXPERIMENTS = window.SPB_EXPERIMENTS || [];
    window.SPB_EXPERIMENTS.push({
        id: EXP_ID,
        name: 'Blame the Dial (two-render forensic diff)',
        pitch: 'Pick any two renders in the history gallery and get told exactly which sliders changed between them ' +
               '("Body Color 1 · Finish: A → B", "Base Scale: 1 → 0.5"), with deltaE heat overlays of the ' +
               'paint AND the spec so invisible M/R/Cc drift is caught — plus one-click per-zone revert.',
        enable: enable,
        disable: disable
    });
})();

/* spb-easy-autoparts.js — Easy Mode AUTO: "ready-made parts" for FLAT paints (TGA/PNG/JPEG).
 *
 * [2026-09-19, autoparts lane — PROTOTYPE, not yet wired into the AUTO layer]
 * Wraps the server's existing POST /api/auto-separate-livery (server.py ~7751) so the Easy Mode
 * AUTO layer can offer NUMBERS and SPONSORS as parts a buyer finishes separately, even when the
 * paint is a flat TGA with no PSD layers.
 *
 *   window.spbEasyAutoParts.detect(paintFilePath [, opts]) -> Promise<result>
 *       result = { detected, size, ms, overlayDataUrl, message,
 *                  numbers:  { maskDataUrl, coverage },
 *                  sponsors: { maskDataUrl, coverage },
 *                  paint:    { maskDataUrl, coverage } }
 *       - paintFilePath: the ABSOLUTE path of the paint already loaded in the app
 *         (window.getCurrentSourcePaintFile() / #paintFile). Sent as JSON with the
 *         X-Shokker-Internal header, exactly like js/features/smart-separate.js does, so the
 *         16 MB TGA is never re-uploaded. opts.file (a File/Blob) switches to multipart upload.
 *       - opts: { previewSize (256..1024, default 768), smart (default true), sensitivity, numberSize }
 *       - masks come back at previewSize x previewSize (NOT the paint's 2048), 0/255 PNGs.
 *
 *   window.spbEasyAutoParts.maskToBytes(maskDataUrl, w, h) -> Promise<Uint8Array>
 *       Resamples the endpoint mask to the paint canvas size (w x h = #paintCanvas.width/height,
 *       which equals the paint's own pixel size) and thresholds to 0/255. THIS is what goes into
 *       zone.regionMask (the app keeps the byte mask on the zone and RLE-encodes it at payload
 *       time in _encodeZoneApplyMasks, paint-booth-5-api-render.js:55). Set zone.useRegion = true
 *       or the mask is silently ignored.
 *
 *   window.spbEasyAutoParts.maskToRLE(maskDataUrl, w, h [, asString]) -> Promise<{width,height,runs}>
 *       Same, but returns the app's RLE payload format ({ width, height, runs: [[value,count],..] })
 *       using the app's own global encodeRegionMaskRLE (paint-booth-2-state-zones.js:18715) when
 *       present, else an identical local encoder. asString=true gives the JSON string (the server's
 *       _decode_rle_mask_payload accepts either). The server REQUIRES width x height to equal the
 *       source paint's own size (server.py _image_rle_shape), so always pass the paint canvas size.
 *
 *   window.spbEasyAutoParts.paintCanvasSize() -> { w, h } | null
 *
 * ES5, IIFE, no dependencies (needs fetch + Promise + canvas, all present in the Electron runtime).
 */
(function (global) {
    'use strict';
    if (!global || global.spbEasyAutoParts) return;

    var ENDPOINT = '/api/auto-separate-livery';
    var PART_KEYS = ['numbers', 'sponsors', 'paint'];

    function clamp(v, lo, hi, dv) {
        var n = Number(v);
        if (v === undefined || v === null || v === '' || isNaN(n)) return dv;
        return Math.max(lo, Math.min(hi, n));
    }

    function paintCanvasSize() {
        try {
            var pc = global.document && global.document.getElementById('paintCanvas');
            if (pc && pc.width > 0 && pc.height > 0) return { w: pc.width, h: pc.height };
        } catch (e) {}
        return null;
    }

    function normalise(json, ms) {
        var fr = json.fractions || {};
        var masks = json.masks || {};
        var out = {
            detected: !!json.detected,
            ms: ms,
            size: null,
            overlayDataUrl: json.overlay || null,
            message: json.message || null,
            sensitivity: json.sensitivity,
            numberSize: json.number_size
        };
        for (var i = 0; i < PART_KEYS.length; i++) {
            var k = PART_KEYS[i];
            out[k] = { maskDataUrl: masks[k] || null, coverage: Number(fr[k] || 0) };
        }
        return out;
    }

    /** detect(paintFilePath, opts) — see header. Rejects with an Error on transport / server failure. */
    function detect(paintFilePath, opts) {
        opts = opts || {};
        var previewSize = Math.round(clamp(opts.previewSize, 256, 1024, 768));
        var smart = opts.smart === undefined ? true : !!opts.smart;
        var req;
        if (opts.file) {
            var fd = new FormData();
            fd.append('paint_file', opts.file, opts.file.name || 'paint.png');
            fd.append('preview_size', String(previewSize));
            fd.append('smart', smart ? '1' : '0');
            if (opts.sensitivity !== undefined) fd.append('sensitivity', String(clamp(opts.sensitivity, 0.3, 2.0, 1.0)));
            if (opts.numberSize !== undefined) fd.append('number_size', String(clamp(opts.numberSize, 0.4, 2.5, 1.0)));
            req = { method: 'POST', headers: { 'X-Shokker-Internal': '1' }, body: fd };
        } else {
            var path = String(paintFilePath || '').trim();
            if (!path) return Promise.reject(new Error('spbEasyAutoParts.detect: paintFilePath is required (or pass opts.file)'));
            var body = { paint_file: path, preview_size: previewSize, smart: smart ? '1' : '0' };
            if (opts.sensitivity !== undefined) body.sensitivity = clamp(opts.sensitivity, 0.3, 2.0, 1.0);
            if (opts.numberSize !== undefined) body.number_size = clamp(opts.numberSize, 0.4, 2.5, 1.0);
            req = { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' }, body: JSON.stringify(body) };
        }
        var t0 = Date.now();
        return fetch(ENDPOINT, req).then(function (r) {
            return r.json().then(function (j) { return { status: r.status, json: j || {} }; }, function () {
                throw new Error('auto-separate: HTTP ' + r.status + ' (non-JSON reply)');
            });
        }).then(function (x) {
            if (x.status !== 200 || !x.json.success) {
                throw new Error('auto-separate: ' + (x.json.error || ('HTTP ' + x.status)));
            }
            var res = normalise(x.json, Date.now() - t0);
            res.size = previewSize;
            return res;
        });
    }

    function loadImage(dataUrl) {
        return new Promise(function (resolve, reject) {
            var img = new Image();
            img.onload = function () { resolve(img); };
            img.onerror = function () { reject(new Error('spbEasyAutoParts: mask image failed to decode')); };
            img.src = dataUrl;
        });
    }

    /** maskToBytes(maskDataUrl, w, h) -> Promise<Uint8Array(w*h)> with values 0 / 255.
     *  Bilinear resample (smoothing ON) then threshold at 128: at 768 -> 2048 (2.67x) this gives
     *  clean glyph edges instead of the staircase nearest-neighbour would produce. */
    function maskToBytes(maskDataUrl, w, h) {
        w = Math.max(1, Math.round(Number(w) || 0)); h = Math.max(1, Math.round(Number(h) || 0));
        if (!maskDataUrl) return Promise.reject(new Error('spbEasyAutoParts.maskToBytes: no mask'));
        return loadImage(maskDataUrl).then(function (img) {
            var c = global.document.createElement('canvas');
            c.width = w; c.height = h;
            var ctx = c.getContext('2d', { willReadFrequently: true });
            ctx.imageSmoothingEnabled = true;
            try { ctx.imageSmoothingQuality = 'high'; } catch (e) {}
            ctx.drawImage(img, 0, 0, w, h);
            var px = ctx.getImageData(0, 0, w, h).data;
            var out = new Uint8Array(w * h);
            for (var i = 0, p = 0; i < out.length; i++, p += 4) {
                if (px[p] >= 128) out[i] = 255;   // R == G == B in the server PNGs
            }
            return out;
        });
    }

    /** Identical format to the app's encodeRegionMaskRLE: { width, height, runs: [[value, count], ...] }. */
    function encodeRLELocal(mask, width, height) {
        if (!mask || !mask.length) return null;
        var runs = [], cur = mask[0], n = 1;
        for (var i = 1; i < mask.length; i++) {
            if (mask[i] === cur) { n++; }
            else { runs.push([cur, n]); cur = mask[i]; n = 1; }
        }
        runs.push([cur, n]);
        return { width: width, height: height, runs: runs };
    }

    /** maskToRLE(maskDataUrl, w, h, asString) -> Promise<{width,height,runs}> (or JSON string). */
    function maskToRLE(maskDataUrl, w, h, asString) {
        return maskToBytes(maskDataUrl, w, h).then(function (bytes) {
            var enc = (typeof global.encodeRegionMaskRLE === 'function') ? global.encodeRegionMaskRLE : encodeRLELocal;
            var rle = enc(bytes, Math.round(Number(w)), Math.round(Number(h)));
            return asString ? JSON.stringify(rle) : rle;
        });
    }

    /** countBytes(mask) -> number of set pixels (cheap, for the "N pixels (x%)" status line). */
    function countBytes(mask) {
        var n = 0;
        if (mask) for (var i = 0; i < mask.length; i++) if (mask[i] > 0) n++;
        return n;
    }

    global.spbEasyAutoParts = {
        ENDPOINT: ENDPOINT,
        PART_KEYS: PART_KEYS.slice(),
        detect: detect,
        maskToBytes: maskToBytes,
        maskToRLE: maskToRLE,
        paintCanvasSize: paintCanvasSize,
        countBytes: countBytes,
        _encodeRLELocal: encodeRLELocal
    };
})(typeof window !== 'undefined' ? window : this);

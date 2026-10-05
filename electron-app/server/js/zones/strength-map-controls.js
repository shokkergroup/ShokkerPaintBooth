(function(global) {
    'use strict';

    var STRENGTH_MAP_SIZE = 256;

    function install(deps) {
        deps = deps || {};
        var getZones = typeof deps.getZones === 'function' ? deps.getZones : function() { return []; };
        var pushZoneUndo = typeof deps.pushZoneUndo === 'function' ? deps.pushZoneUndo : function() {};
        var renderZoneDetail = typeof deps.renderZoneDetail === 'function' ? deps.renderZoneDetail : function() {};
        var triggerPreviewRender = typeof deps.triggerPreviewRender === 'function' ? deps.triggerPreviewRender : function() {};

        if (typeof global._strengthMapBrushSize === 'undefined') global._strengthMapBrushSize = 20;
        if (typeof global._strengthMapBrushValue === 'undefined') global._strengthMapBrushValue = 0;
        if (typeof global._strengthMapPainting === 'undefined') global._strengthMapPainting = false;

        function zoneAt(zoneIdx) {
            var zones = getZones();
            return zones && zones[zoneIdx] ? zones[zoneIdx] : null;
        }

        global.encodeRegionMaskRLE = function encodeRegionMaskRLE(mask, width, height) {
            if (!mask) return null;
            var length = Number(mask.length) || 0;
            var encodedWidth = Math.max(0, Math.round(Number(width) || 0));
            var encodedHeight = Math.max(0, Math.round(Number(height) || 0));
            // SPB-93 T52 (2026-08-09), browser proof: a 4096-square mask retained
            // after a source swap was labelled 2048x2048. The exact RLE then
            // covered more pixels than its advertised dimensions, so every Zone
            // preview failed and LIVE PREVIEW silently showed its last good frame.
            // Preserve the authored pixels and report their truthful dimensions;
            // the render engine already resamples valid masks to preview size.
            if (length && encodedWidth * encodedHeight !== length) {
                var squareSide = Math.sqrt(length);
                if (Number.isInteger(squareSide)) {
                    encodedWidth = squareSide;
                    encodedHeight = squareSide;
                } else if (encodedWidth > 0 && length % encodedWidth === 0) {
                    encodedHeight = length / encodedWidth;
                } else if (encodedHeight > 0 && length % encodedHeight === 0) {
                    encodedWidth = length / encodedHeight;
                } else {
                    encodedWidth = length;
                    encodedHeight = 1;
                }
            }
            var runs = [];
            var currentVal = mask[0];
            var count = 1;
            for (var i = 1; i < mask.length; i++) {
                if (mask[i] === currentVal) {
                    count++;
                } else {
                    runs.push([currentVal, count]);
                    currentVal = mask[i];
                    count = 1;
                }
            }
            runs.push([currentVal, count]);
            return { width: encodedWidth, height: encodedHeight, runs: runs };
        };

        global.hasAnyRegionMasks = function hasAnyRegionMasks() {
            var zones = getZones();
            return zones.some(function(z) {
                return z.regionMask && z.regionMask.some(function(v) { return v > 0; });
            });
        };

        global.toggleStrengthMap = function toggleStrengthMap(zoneIdx) {
            var z = zoneAt(zoneIdx);
            if (!z) return;
            pushZoneUndo('Toggle strength map');
            z.patternStrengthMapEnabled = !z.patternStrengthMapEnabled;
            if (z.patternStrengthMapEnabled && !z.patternStrengthMap) {
                z.patternStrengthMap = {
                    width: STRENGTH_MAP_SIZE,
                    height: STRENGTH_MAP_SIZE,
                    data: new Uint8Array(STRENGTH_MAP_SIZE * STRENGTH_MAP_SIZE).fill(255)
                };
            }
            renderZoneDetail(zoneIdx);
            if (z.patternStrengthMapEnabled) {
                global.requestAnimationFrame(function() { global.strengthMapRedraw(zoneIdx); });
            }
            triggerPreviewRender();
        };

        global.strengthMapRedraw = function strengthMapRedraw(zoneIdx) {
            var z = zoneAt(zoneIdx);
            if (!z || !z.patternStrengthMap) return;
            var canvas = global.document && global.document.getElementById('strengthMapCanvas' + zoneIdx);
            if (!canvas) return;
            var ctx = canvas.getContext('2d');
            var w = z.patternStrengthMap.width;
            var h = z.patternStrengthMap.height;
            canvas.width = w;
            canvas.height = h;
            var imgData = ctx.createImageData(w, h);
            var data = z.patternStrengthMap.data;
            for (var i = 0; i < data.length; i++) {
                var v = data[i];
                imgData.data[i * 4] = v;
                imgData.data[i * 4 + 1] = v;
                imgData.data[i * 4 + 2] = v;
                imgData.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(imgData, 0, 0);
        };

        global.strengthMapStartPaint = function strengthMapStartPaint(event, zoneIdx) {
            pushZoneUndo('Strength map paint', true);
            global._strengthMapPainting = true;
            global.strengthMapPaint(event, zoneIdx);
        };

        global.strengthMapPaint = function strengthMapPaint(event, zoneIdx) {
            if (!global._strengthMapPainting) return;
            var z = zoneAt(zoneIdx);
            if (!z || !z.patternStrengthMap) return;
            var canvas = global.document && global.document.getElementById('strengthMapCanvas' + zoneIdx);
            if (!canvas) return;
            var rect = canvas.getBoundingClientRect();
            var scaleX = canvas.width / rect.width;
            var scaleY = canvas.height / rect.height;
            var cx = (event.clientX - rect.left) * scaleX;
            var cy = (event.clientY - rect.top) * scaleY;
            var brushR = (global._strengthMapBrushSize || 20) / 2;
            var val = global._strengthMapBrushValue ?? 0;
            var w = z.patternStrengthMap.width;
            var h = z.patternStrengthMap.height;
            var data = z.patternStrengthMap.data;
            var x0 = Math.max(0, Math.floor(cx - brushR));
            var y0 = Math.max(0, Math.floor(cy - brushR));
            var x1 = Math.min(w - 1, Math.ceil(cx + brushR));
            var y1 = Math.min(h - 1, Math.ceil(cy + brushR));
            var rSq = brushR * brushR;
            for (var y = y0; y <= y1; y++) {
                for (var x = x0; x <= x1; x++) {
                    var dx = x - cx;
                    var dy = y - cy;
                    var distSq = dx * dx + dy * dy;
                    if (distSq <= rSq) {
                        var t = Math.sqrt(distSq) / brushR;
                        var alpha = t < 0.7 ? 1.0 : 1.0 - ((t - 0.7) / 0.3);
                        var idx = y * w + x;
                        data[idx] = Math.round(data[idx] * (1 - alpha) + val * alpha);
                    }
                }
            }
            global.strengthMapRedraw(zoneIdx);
        };

        global.strengthMapStopPaint = function strengthMapStopPaint() {
            var wasPainting = !!global._strengthMapPainting;
            global._strengthMapPainting = false;
            if (wasPainting) triggerPreviewRender();
        };

        global.strengthMapFill = function strengthMapFill(zoneIdx, value) {
            var z = zoneAt(zoneIdx);
            if (!z || !z.patternStrengthMap) return;
            pushZoneUndo('Strength map fill');
            z.patternStrengthMap.data.fill(value);
            global.strengthMapRedraw(zoneIdx);
            triggerPreviewRender();
        };

        global.strengthMapGradient = function strengthMapGradient(zoneIdx, direction) {
            var z = zoneAt(zoneIdx);
            if (!z || !z.patternStrengthMap) return;
            pushZoneUndo('Strength map gradient');
            var w = z.patternStrengthMap.width;
            var h = z.patternStrengthMap.height;
            var data = z.patternStrengthMap.data;
            for (var y = 0; y < h; y++) {
                for (var x = 0; x < w; x++) {
                    var v;
                    if (direction === 'tb') {
                        v = 1.0 - (y / (h - 1));
                    } else if (direction === 'lr') {
                        v = 1.0 - (x / (w - 1));
                    } else if (direction === 'center') {
                        var cx = (x / (w - 1)) * 2 - 1;
                        var cy = (y / (h - 1)) * 2 - 1;
                        var dist = Math.sqrt(cx * cx + cy * cy) / Math.SQRT2;
                        v = 1.0 - dist;
                    } else {
                        v = 1.0;
                    }
                    data[y * w + x] = Math.round(Math.max(0, Math.min(1, v)) * 255);
                }
            }
            global.strengthMapRedraw(zoneIdx);
            triggerPreviewRender();
        };

        global.encodeStrengthMapRLE = function encodeStrengthMapRLE(strengthMap) {
            if (!strengthMap || !strengthMap.data) return null;
            var data = strengthMap.data;
            var runs = [];
            var currentVal = data[0];
            var count = 1;
            for (var i = 1; i < data.length; i++) {
                if (data[i] === currentVal) {
                    count++;
                } else {
                    runs.push([currentVal, count]);
                    currentVal = data[i];
                    count = 1;
                }
            }
            runs.push([currentVal, count]);
            return { width: strengthMap.width, height: strengthMap.height, runs: runs };
        };
    }

    global.SPBZoneStrengthMapControls = {
        install: install,
        STRENGTH_MAP_SIZE: STRENGTH_MAP_SIZE
    };
})(typeof window !== 'undefined' ? window : globalThis);

(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBLayerTransformRaster = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // SPB-93 tick 41 (2026-07-16), owner verdict: tools feel "jinky/off".
    // A moved layer element must vacate its source pixels before the transformed
    // alpha is composited. Linked elements also preserve their relative offsets.
    function eraseSourceAlpha(ctx, sourceCanvas, sx, sy, sw, sh) {
        if (!ctx || !sourceCanvas || !(sw > 0) || !(sh > 0)) return false;
        ctx.save();
        ctx.globalCompositeOperation = 'destination-out';
        ctx.drawImage(sourceCanvas, sx, sy, sw, sh, sx, sy, sw, sh);
        ctx.restore();
        return true;
    }

    function linkedPlacement(masterRect, memberRect, masterDrawX, masterDrawY) {
        if (!masterRect || !memberRect) return null;
        return {
            x: Number(masterDrawX) + Number(memberRect.x1) - Number(masterRect.x1),
            y: Number(masterDrawY) + Number(memberRect.y1) - Number(masterRect.y1),
        };
    }

    // SPB-93 Pass 138 (2026-07-17): compose picked-element transforms on a
    // union surface. The legacy in-canvas path sized the destination from the
    // picked glyph and clipped siblings or artwork moved beyond the old bbox.
    function transformedAabb(item) {
        if (!item) return null;
        const width = Math.max(1, Math.abs(Number(item.width) || 0));
        const height = Math.max(1, Math.abs(Number(item.height) || 0));
        const centerX = Number(item.centerX);
        const centerY = Number(item.centerY);
        if (!Number.isFinite(centerX) || !Number.isFinite(centerY)) return null;
        const radians = (Number(item.rotation) || 0) * Math.PI / 180;
        const rotated = Math.abs((Number(item.rotation) || 0) % 180) > 1e-7;
        const pad = rotated ? 2 : 0;
        const aabbWidth = Math.max(1, Math.ceil(width * Math.abs(Math.cos(radians)) + height * Math.abs(Math.sin(radians)) - 1e-9) + pad * 2);
        const aabbHeight = Math.max(1, Math.ceil(width * Math.abs(Math.sin(radians)) + height * Math.abs(Math.cos(radians)) - 1e-9) + pad * 2);
        const x1 = Math.floor(centerX - aabbWidth / 2);
        const y1 = Math.floor(centerY - aabbHeight / 2);
        return { x1: x1, y1: y1, x2: x1 + aabbWidth, y2: y1 + aabbHeight, width: aabbWidth, height: aabbHeight };
    }

    function composeElementTransforms(options) {
        const opts = options || {};
        const source = opts.source;
        const bbox = Array.isArray(opts.sourceBbox) ? opts.sourceBbox.map(Number) : null;
        const items = Array.isArray(opts.items) ? opts.items : [];
        const createCanvas = opts.createCanvas;
        if (!source || !bbox || bbox.length < 4 || !items.length || typeof createCanvas !== 'function') return null;
        const sourceWidth = Math.max(1, Number(source.naturalWidth || source.width) || 0);
        const sourceHeight = Math.max(1, Number(source.naturalHeight || source.height) || 0);
        const bboxWidth = Math.max(1, bbox[2] - bbox[0]);
        const bboxHeight = Math.max(1, bbox[3] - bbox[1]);
        const scaleX = sourceWidth / bboxWidth;
        const scaleY = sourceHeight / bboxHeight;

        const prepared = [];
        for (let index = 0; index < items.length; index++) {
            const item = items[index];
            const rect = item && item.sourceRect;
            const target = transformedAabb(item);
            if (!rect || !target) continue;
            const rx1 = Math.max(bbox[0], Math.min(bbox[2], Number(rect.x1)));
            const ry1 = Math.max(bbox[1], Math.min(bbox[3], Number(rect.y1)));
            const rx2 = Math.max(rx1, Math.min(bbox[2], Number(rect.x2)));
            const ry2 = Math.max(ry1, Math.min(bbox[3], Number(rect.y2)));
            if (!(rx2 > rx1) || !(ry2 > ry1)) continue;
            prepared.push({
                item: item,
                sourceCanvasRect: { x1: rx1, y1: ry1, x2: rx2, y2: ry2 },
                sx: (rx1 - bbox[0]) * scaleX,
                sy: (ry1 - bbox[1]) * scaleY,
                sw: (rx2 - rx1) * scaleX,
                sh: (ry2 - ry1) * scaleY,
                drawWidth: Math.max(1, Math.abs(Number(item.width) || 0)),
                drawHeight: Math.max(1, Math.abs(Number(item.height) || 0)),
                target: target,
            });
        }
        if (!prepared.length) return null;

        let unionX1 = Math.floor(bbox[0]);
        let unionY1 = Math.floor(bbox[1]);
        let unionX2 = Math.ceil(bbox[2]);
        let unionY2 = Math.ceil(bbox[3]);
        prepared.forEach(function(entry) {
            unionX1 = Math.min(unionX1, entry.target.x1);
            unionY1 = Math.min(unionY1, entry.target.y1);
            unionX2 = Math.max(unionX2, entry.target.x2);
            unionY2 = Math.max(unionY2, entry.target.y2);
        });

        const destination = createCanvas(Math.max(1, unionX2 - unionX1), Math.max(1, unionY2 - unionY1));
        if (!destination) return null;
        if (destination.width !== Math.max(1, unionX2 - unionX1)) destination.width = Math.max(1, unionX2 - unionX1);
        if (destination.height !== Math.max(1, unionY2 - unionY1)) destination.height = Math.max(1, unionY2 - unionY1);
        const destCtx = destination.getContext && destination.getContext('2d', { willReadFrequently: true });
        if (!destCtx) return null;
        destCtx.drawImage(source, 0, 0, sourceWidth, sourceHeight,
            bbox[0] - unionX1, bbox[1] - unionY1, bboxWidth, bboxHeight);

        // Remove every original alpha footprint before adding transformed
        // pieces, so Move never becomes Clone and linked instances do not smear.
        prepared.forEach(function(entry) {
            const rect = entry.sourceCanvasRect;
            // SPB-93: this is a crop of the Layer itself. Alpha-weighted
            // destination-out left a*(1-a) ghosts at antialiased edges.
            destCtx.clearRect(rect.x1 - unionX1, rect.y1 - unionY1,
                rect.x2 - rect.x1, rect.y2 - rect.y1);
        });

        prepared.forEach(function(entry) {
            const item = entry.item;
            const target = entry.target;
            const piece = createCanvas(target.width, target.height);
            if (!piece) return;
            if (piece.width !== target.width) piece.width = target.width;
            if (piece.height !== target.height) piece.height = target.height;
            const pieceCtx = piece.getContext && piece.getContext('2d', { willReadFrequently: true });
            if (!pieceCtx) return;
            pieceCtx.translate(target.width / 2, target.height / 2);
            if (item.flipH || item.flipV) pieceCtx.scale(item.flipH ? -1 : 1, item.flipV ? -1 : 1);
            const radians = (Number(item.rotation) || 0) * Math.PI / 180;
            if (radians) pieceCtx.rotate(radians);
            pieceCtx.imageSmoothingEnabled = true;
            pieceCtx.imageSmoothingQuality = 'high';
            pieceCtx.drawImage(source, entry.sx, entry.sy, entry.sw, entry.sh,
                -entry.drawWidth / 2, -entry.drawHeight / 2,
                entry.drawWidth, entry.drawHeight);
            destCtx.drawImage(piece, target.x1 - unionX1, target.y1 - unionY1);
        });

        return {
            canvas: destination,
            bbox: [unionX1, unionY1, unionX2, unionY2],
            items: prepared.map(function(entry) { return { item: entry.item, bbox: entry.target }; }),
        };
    }

    // SPB-93 tick 43 (2026-07-16), owner verdict: tools must feel Photoshop-quality.
    // Draw the exact active whole-layer transform into an arbitrary destination.
    // Layer-selection -> Zone-mask baking uses this so its alpha follows the
    // live move/scale/rotate/flip instead of stale pre-transform bounds.
    function drawSourceRect(ctx, source, rect, sourceBbox, width, height) {
        if (rect && Array.isArray(sourceBbox)) {
            const scaleX = Number(source.naturalWidth || source.width) / Math.max(1, sourceBbox[2] - sourceBbox[0]);
            const scaleY = Number(source.naturalHeight || source.height) / Math.max(1, sourceBbox[3] - sourceBbox[1]);
            ctx.drawImage(source, (rect.x1 - sourceBbox[0]) * scaleX, (rect.y1 - sourceBbox[1]) * scaleY,
                (rect.x2 - rect.x1) * scaleX, (rect.y2 - rect.y1) * scaleY,
                -width / 2, -height / 2, width, height);
        } else ctx.drawImage(source, -width / 2, -height / 2, width, height);
    }

    function drawTransformedSource(ctx, source, state) {
        if (!ctx || !source || !state) return false;
        const width = Math.max(1, Math.abs(Number(state.boxW) || 0));
        const height = Math.max(1, Math.abs(Number(state.boxH) || 0));
        const centerX = Number(state.centerX);
        const centerY = Number(state.centerY);
        if (!Number.isFinite(centerX) || !Number.isFinite(centerY)) return false;

        ctx.save();
        ctx.translate(centerX, centerY);
        if ((Number(state.scaleX) || 1) < 0 || (Number(state.scaleY) || 1) < 0) {
            ctx.scale((Number(state.scaleX) || 1) < 0 ? -1 : 1, (Number(state.scaleY) || 1) < 0 ? -1 : 1);
        }
        const radians = (Number(state.rotation) || 0) * Math.PI / 180;
        if (radians) ctx.rotate(radians);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        drawSourceRect(ctx, source, state.sourceRect || state.origSubRect, state.sourceBbox || state.origBbox, width, height);
        ctx.restore();
        return true;
    }

    function rasterizeTransformedAlpha(state, width, height, createCanvas) {
        const w = Math.max(1, Math.floor(Number(width) || 0));
        const h = Math.max(1, Math.floor(Number(height) || 0));
        if (!state || !state.origImg || typeof createCanvas !== 'function') return null;
        const canvas = createCanvas(w, h);
        if (!canvas) return null;
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext && canvas.getContext('2d');
        if (!ctx || !drawTransformedSource(ctx, state.origImg, state)) return null;
        const rgba = ctx.getImageData(0, 0, w, h).data;
        const alpha = new Uint8Array(w * h);
        let nonZero = 0;
        for (let i = 0; i < alpha.length; i++) {
            const value = rgba[(i * 4) + 3] || 0;
            alpha[i] = value;
            if (value) nonZero++;
        }
        return { mask: alpha, nonZero };
    }

    function combineZoneMask(existing, source, mode) {
        if (!source || typeof source.length !== 'number') return null;
        const current = existing && existing.length === source.length
            ? existing
            : new Uint8Array(source.length);
        const next = new Uint8Array(source.length);
        const operation = String(mode || 'add').toLowerCase();
        let changed = 0;
        for (let i = 0; i < source.length; i++) {
            const before = current[i] || 0;
            const value = source[i] || 0;
            let after;
            if (operation === 'replace') after = value;
            else if (operation === 'subtract') after = Math.max(0, before - value);
            else if (operation === 'intersect') after = Math.min(before, value);
            else after = Math.max(before, value); // add / union
            next[i] = after;
            if (after !== before) changed++;
        }
        return { mask: next, changed };
    }

    return Object.freeze({
        eraseSourceAlpha,
        linkedPlacement,
        transformedAabb,
        composeElementTransforms,
        drawSourceRect,
        drawTransformedSource,
        rasterizeTransformedAlpha,
        combineZoneMask,
    });
});

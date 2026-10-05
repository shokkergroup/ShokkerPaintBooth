/* SPB-93 2026-09-07: show one temporary composite during Transform.
   The old overlay stacked transformed art and ghosts over committed pixels.
   Buffers belong to the session; document pixels and layer records stay immutable. */
(function(root) {
    'use strict';
    const sessions = new WeakMap(), visibility = new WeakMap();
    function prepare(canvas, width, height, readFrequently = false) {
        if (canvas.width !== width) canvas.width = width;
        if (canvas.height !== height) canvas.height = height;
        const ctx = canvas.getContext('2d', { willReadFrequently: readFrequently });
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
        ctx.clearRect(0, 0, width, height);
        return canvas;
    }
    function whole(state, createCanvas) {
        // Match the established whole-layer Apply rounding and filtering.
        const w = Math.max(1, Math.round(state.boxW)), h = Math.max(1, Math.round(state.boxH));
        const rad = (state.rotation || 0) * Math.PI / 180;
        const pad = state.rotation && state.rotation % 180 !== 0 ? 2 : 0;
        const width = Math.max(1, Math.ceil(w * Math.abs(Math.cos(rad)) + h * Math.abs(Math.sin(rad)))) + pad * 2;
        const height = Math.max(1, Math.ceil(w * Math.abs(Math.sin(rad)) + h * Math.abs(Math.cos(rad)))) + pad * 2;
        const canvas = createCanvas(width, height), ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'low';
        ctx.translate(width / 2, height / 2);
        ctx.scale(state.scaleX < 0 ? -1 : 1, state.scaleY < 0 ? -1 : 1);
        ctx.rotate(rad);
        ctx.drawImage(state.origImg, -w / 2, -h / 2, w, h);
        const x = Math.round(state.centerX - width / 2), y = Math.round(state.centerY - height / 2);
        return { canvas, bbox: [x, y, x + width, y + height] };
    }
    function render(state, options) {
        if (!state || state.target !== 'layer' || !state.origImg) return null;
        const o = options, layer = o.layers.find(l => l.id === state.layerId);
        if (!layer) return null;
        const rects = state.origSubRect ? (state.sourceMembers || [state.origSubRect]).concat(o.instanceRects || []) : [];
        const key = JSON.stringify([o.width,o.height,o.revision,state.centerX,state.centerY,state.boxW,state.boxH,
            state.rotation,state.scaleX,state.scaleY,rects]);
        let cache = sessions.get(state);
        if (cache?.valid && cache.key === key) return cache.composite;
        if (!cache) {
            cache = { pool: [], composite: o.createCanvas(o.width, o.height) };
            // Use the native export compositor's context settings for
            // comparable pixel audits without touching its memoized output.
            cache.composite.getContext('2d', { willReadFrequently: true });
            sessions.set(state, cache);
        }
        cache.valid = false;
        let cursor = 0;
        const createCanvas = (w,h) => {
            const canvas = cache.pool[cursor] || (cache.pool[cursor] = o.createCanvas(w,h));
            cursor++;
            return prepare(canvas,w,h,!!state.origSubRect);
        };
        let candidate = null;
        if (!o.geometry.unchanged(state)) {
            if (state.origSubRect) {
                const unique = new Map(rects.map(r => [[r.x1,r.y1,r.x2,r.y2].join(','),r]));
                candidate = o.raster.composeElementTransforms({
                    source: state.origImg, sourceBbox: state.origBbox,
                    items: [...unique.values()].map(r => o.geometry.item(state,r)), createCanvas,
                });
            } else candidate = whole(state,createCanvas);
            if (!candidate) return null;
        }
        let previewLayers = candidate ? o.layers.map(l => l.id === state.layerId
            ? { ...l, img: candidate.canvas, bbox: candidate.bbox } : l) : o.layers;
        // A lifted selection is baked back into its source on Apply. Preview
        // that same merge so group/clipping/opacity/effects apply once, to the
        // same combined source shape, instead of treating the lift as a decal.
        const parent = layer.sourceLayerId && String(layer.id).startsWith('selxform_')
            ? o.layers.find(l => l.id === layer.sourceLayerId) : null;
        if (parent?.img && parent.bbox) {
            const part = candidate ? { img: candidate.canvas, bbox: candidate.bbox } : layer;
            const [sx1,sy1,sx2,sy2] = parent.bbox, [tx1,ty1,tx2,ty2] = part.bbox;
            const x = Math.min(sx1,tx1), y = Math.min(sy1,ty1);
            const w = Math.max(1,Math.round(Math.max(sx2,tx2)-x)), h = Math.max(1,Math.round(Math.max(sy2,ty2)-y));
            const merged = createCanvas(w,h), ctx = merged.getContext('2d');
            ctx.drawImage(parent.img,Math.round(sx1-x),Math.round(sy1-y));
            ctx.drawImage(part.img,Math.round(tx1-x),Math.round(ty1-y));
            previewLayers = o.layers.filter(l => l.id !== layer.id).map(l => l.id === parent.id
                ? { ...l, img: merged, bbox: [Math.round(x),Math.round(y),Math.round(x)+w,Math.round(y)+h] } : l);
        }
        prepare(cache.composite,o.width,o.height);
        const result = o.compose(cache.composite.getContext('2d'),previewLayers);
        if (!result?.ok) throw new Error(result?.issues?.[0]?.reason || 'Layer stack could not be previewed');
        cache.key = key;
        cache.valid = true;
        return cache.composite;
    }
    function show(sourceCanvas) {
        if (!sourceCanvas) return;
        if (!visibility.has(sourceCanvas)) visibility.set(sourceCanvas,sourceCanvas.style.visibility);
        sourceCanvas.style.visibility = 'hidden';
    }
    function restore(sourceCanvas) {
        if (!sourceCanvas || !visibility.has(sourceCanvas)) return;
        sourceCanvas.style.visibility = visibility.get(sourceCanvas);
        visibility.delete(sourceCanvas);
    }
    function peek(state) { const cache = state ? sessions.get(state) : null; return cache?.valid ? cache.composite : null; }
    const api = { render, show, restore, peek };
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.SPBLayerTransformPreview = api;
})(typeof window === 'object' ? window : globalThis);

/* SPB-93 tools 2026-09-07: a4096px selection allocated/uploaded64MB of
   transparent overlay every frame. Keep native mask coordinates and edges;
   allocate only the union of the selected region/spatial bounds. */
(function (root) {
    'use strict';
    function create(ctx, canvasWidth, canvasHeight, boxes) {
        let x = canvasWidth, y = canvasHeight, right = -1, bottom = -1;
        for (const box of boxes) {
            if (!box || box.any === false) continue;
            x = Math.min(x, Math.max(0, box.minX));
            y = Math.min(y, Math.max(0, box.minY));
            right = Math.max(right, Math.min(canvasWidth - 1, box.maxX));
            bottom = Math.max(bottom, Math.min(canvasHeight - 1, box.maxY));
        }
        const empty = right < x || bottom < y;
        if (empty) x = y = 0;
        const width = empty ? 1 : right - x + 1;
        const height = empty ? 1 : bottom - y + 1;
        return {
            x, y, imageData: ctx.createImageData(width, height),
            index: i => ((Math.floor(i / canvasWidth) - y) * width + i % canvasWidth - x) * 4,
        };
    }
    function regionEdge(mask, i, x, y, width, height) {
        return x === 0 || x === width - 1 || y === 0 || y === height - 1 ||
            mask[i - 1] === 0 || mask[i + 1] === 0 || mask[i - width] === 0 || mask[i + width] === 0;
    }
    function paint(surface, width, height, zone, color, opacity, regionBounds, spatialBounds) {
        if (!zone) return;
        const data = surface.imageData.data, stride = surface.imageData.width * 4;
        const region = zone.regionMask, spatial = zone.spatialMask;
        const alpha = Math.min(255, Math.round(color[3] * opacity));
        // SPB-93 2026-09-07: prior overlay40-45ms on4096px documents.
        // Fuse each mask's fill/edge pass and advance local RGBA indices by row.
        if (region && regionBounds && regionBounds.any !== false) {
            const b = regionBounds;
            for (let y = b.minY; y <= b.maxY; y++) {
                let i = y * width + b.minX;
                let pi = (y - surface.y) * stride + (b.minX - surface.x) * 4;
                for (let x = b.minX; x <= b.maxX; x++, i++, pi += 4) {
                    if (!(region[i] > 0)) continue;
                    if (regionEdge(region, i, x, y, width, height)) {
                        data[pi] = data[pi + 1] = data[pi + 2] = data[pi + 3] = 255;
                    } else {
                        data[pi] = color[0]; data[pi + 1] = color[1]; data[pi + 2] = color[2]; data[pi + 3] = alpha;
                    }
                }
            }
        }
        if (spatial && spatialBounds && spatialBounds.any !== false) {
            const b = spatialBounds;
            for (let y = b.minY; y <= b.maxY; y++) {
                let i = y * width + b.minX;
                let pi = (y - surface.y) * stride + (b.minX - surface.x) * 4;
                for (let x = b.minX; x <= b.maxX; x++, i++, pi += 4) {
                    const v = spatial[i]; if (v !== 1 && v !== 2) continue;
                    const edge = x === 0 || x === width - 1 || y === 0 || y === height - 1 ||
                        spatial[i - 1] !== v || spatial[i + 1] !== v || spatial[i - width] !== v || spatial[i + width] !== v;
                    if (edge) {
                        data[pi] = data[pi + 3] = 255;
                        data[pi + 1] = data[pi + 2] = v === 1 ? 255 : 220;
                    } else if (!(region && region[i] > 0 && regionEdge(region, i, x, y, width, height))) {
                        // Region edges originally overwrite spatial fill; preserve that precedence.
                        data[pi] = v === 1 ? 24 : 255; data[pi + 1] = v === 1 ? 255 : 72;
                        data[pi + 2] = v === 1 ? 166 : 72; data[pi + 3] = 196;
                    }
                }
            }
        }
    }
    const api = { create, paint };
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.SPBRegionOverlaySurface = api;
})(typeof window === 'object' ? window : globalThis);

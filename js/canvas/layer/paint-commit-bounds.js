// SPB-93 tools 2026-09-07: reuse the scanned active surface and inspect only
// the surviving off-canvas strips. Avoid rereading/scanning the merged sheet.
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPaintCommitBounds = api;
})(typeof window === 'object' ? window : globalThis, function () {
    'use strict';
    function collector(initial) {
        let bounds = initial ? { ...initial } : null;
        return {
            add(x, y) {
                if (!bounds) bounds = { minX: x, minY: y, maxX: x, maxY: y };
                else {
                    bounds.minX = Math.min(bounds.minX, x); bounds.minY = Math.min(bounds.minY, y);
                    bounds.maxX = Math.max(bounds.maxX, x); bounds.maxY = Math.max(bounds.maxY, y);
                }
            },
            result: () => bounds
        };
    }
    function alphaBounds(image, offsetX = 0, offsetY = 0) {
        let minX = image.width, minY = image.height, maxX = -1, maxY = -1;
        // SPB-93 2026-09-08: sparse4096 Layers spent93ms in commit analysis.
        // Skip transparent groups of eight before refining the row endpoints.
        // Derive the alpha mask in native byte order; hidden RGB is irrelevant
        // to bounds but remains significant in exact change detection below.
        const packed = words(image.data);
        const alphaMask = new Uint32Array(new Uint8Array([0, 0, 0, 255]).buffer)[0];
        const transparent = i => !((packed[i] | packed[i + 1] | packed[i + 2] | packed[i + 3]
            | packed[i + 4] | packed[i + 5] | packed[i + 6] | packed[i + 7]) & alphaMask);
        for (let y = 0; y < image.height; y++) {
            const row = y * image.width * 4 + 3;
            const packedRow = y * image.width;
            let first = 0;
            if (packed) while (first + 8 <= image.width && transparent(packedRow + first)) first += 8;
            while (first < image.width && !image.data[row + first * 4]) first++;
            if (first === image.width) continue;
            let last = image.width - 1;
            if (packed) while (last - 7 > first && transparent(packedRow + last - 7)) last -= 8;
            while (last > first && !image.data[row + last * 4]) last--;
            minX = Math.min(minX, first); maxX = Math.max(maxX, last);
            minY = Math.min(minY, y); maxY = y;
        }
        return maxX < 0 ? null : { minX: minX + offsetX, minY: minY + offsetY,
            maxX: maxX + offsetX, maxY: maxY + offsetY };
    }
    function words(data) {
        return data.buffer && data.byteOffset % 4 === 0 && data.byteLength % 4 === 0
            ? new Uint32Array(data.buffer, data.byteOffset, data.byteLength / 4) : null;
    }
    function pixel(data, index) {
        const i = index * 4;
        return (data[i] | data[i + 1] << 8 | data[i + 2] << 16 | data[i + 3] << 24) >>> 0;
    }
    function matches(active, original, originX, originY) {
        const a = words(active.data), b = words(original.data);
        function span(first, end, source) {
            if (a && b && source >= 0) {
                for (; first + 8 <= end; first += 8, source += 8) {
                    if ((a[first] ^ b[source]) | (a[first + 1] ^ b[source + 1])
                        | (a[first + 2] ^ b[source + 2]) | (a[first + 3] ^ b[source + 3])
                        | (a[first + 4] ^ b[source + 4]) | (a[first + 5] ^ b[source + 5])
                        | (a[first + 6] ^ b[source + 6]) | (a[first + 7] ^ b[source + 7])) return false;
                }
            }
            for (; first < end; first++) {
                const av = a ? a[first] : pixel(active.data, first);
                const bv = source < 0 ? 0 : b ? b[source] : pixel(original.data, source);
                if (av !== bv) return false;
                if (source >= 0) source++;
            }
            return true;
        }
        const left = Math.max(0, Math.min(active.width, originX));
        const right = Math.max(0, Math.min(active.width, originX + original.width));
        for (let y = 0; y < active.height; y++) {
            const row = y * active.width, sourceY = y - originY;
            if (sourceY < 0 || sourceY >= original.height) {
                if (!span(row, row + active.width, -1)) return false;
            } else if (!span(row, row + left, -1)
                || !span(row + left, row + right, sourceY * original.width + left - originX)
                || !span(row + right, row + active.width, -1)) return false;
        }
        return true;
    }
    // SPB-93 2026-09-07: row endpoints replace per-opaque-pixel bounds work;
    // packed RGBA comparison preserves hidden RGB and exact no-op detection.
    function analyze(active, original, originX, originY, originalAlpha) {
        if (originalAlpha) {
            for (let i = 0; i < originalAlpha.length; i++) active.data[i * 4 + 3] = originalAlpha[i];
        }
        const bounds = alphaBounds(active);
        return {
            pixelsChanged: !original || !matches(active, original, originX, originY),
            minX: bounds ? bounds.minX : active.width,
            minY: bounds ? bounds.minY : active.height,
            maxX: bounds ? bounds.maxX : 0,
            maxY: bounds ? bounds.maxY : 0
        };
    }
    function unionOffCanvas(activeBounds, original, originX, originY, width, height) {
        const out = collector(activeBounds);
        const leftEnd = Math.max(0, Math.min(original.width, -originX));
        const rightStart = Math.max(0, Math.min(original.width, width - originX));
        function scan(y, first, end) {
            for (let x = first, i = (y * original.width + first) * 4 + 3; x < end; x++, i += 4) {
                if (original.data[i]) out.add(x + originX, y + originY);
            }
        }
        for (let y = 0; y < original.height; y++) {
            const globalY = y + originY;
            if (globalY < 0 || globalY >= height) scan(y, 0, original.width);
            else { scan(y, 0, leftEnd); scan(y, rightStart, original.width); }
        }
        return out.result();
    }
    return Object.freeze({ alphaBounds, unionOffCanvas, analyze });
});

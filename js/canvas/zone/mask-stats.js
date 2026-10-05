/* ============================================================================
 * SPB MASK STATS — stop rescanning 4.2 million pixels to draw a label
 *                                                        2026-07-30, Claude
 *
 * THE BUG THIS FIXES (measured, CPU-profiled, not guessed)
 *   renderZones() cost ~8ms on a fresh page and ~335ms after a single brush
 *   stroke — a third of a second of frozen UI every time a painter clicks a zone
 *   once they have actually painted something. The V8 profile put 28.6% of it in
 *   getColorStatusText and the rest in the zone status/diagnostic helpers.
 *
 *   Every one of them does this to a 2048x2048 mask (4,194,304 entries):
 *       const hasRegion   = mask.some(v => v > 0);            // full scan if empty
 *       const regionPixels = mask.reduce((s,v) => s + (v>0?1:0), 0);   // full scan
 *   Two passes, per zone, per render — and the SAME mask is scanned again by
 *   _zoneApplyAreaPixelCount, _zoneApplyAreaSummary, getZoneStatus,
 *   getZoneDiagnostic and hasActivePixelSelection inside the very same call.
 *
 * THE FIX, AND WHY IT CANNOT GO STALE
 *   One tight loop computes `any` and `count` together (a single pass, and a
 *   plain for-loop rather than .reduce with a closure, which V8 does not optimise
 *   over a typed array anywhere near as well).
 *
 *   Results are memoised in a WeakMap that is dropped in a MICROTASK. That is
 *   the whole trick: JavaScript is single-threaded, so a mask cannot change
 *   while synchronous code runs. Everything inside one render pass shares the
 *   cache; the moment control returns to the event loop the cache is gone. So
 *   there is no invalidation to get wrong — no version counters, no touch()
 *   calls to forget at a mutation site, no possibility of showing a stale count.
 *   Caching across frames would be faster still and is deliberately NOT done:
 *   `any` gates real behaviour (whether a zone applies only inside its region),
 *   and a missed invalidation there would mis-render a car.
 * ==========================================================================*/
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBMaskStats = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    let cache = new WeakMap();
    let sumCache = new WeakMap();
    let fingerprintCache = new WeakMap();
    let clearQueued = false;
    let hits = 0, misses = 0, scanned = 0;

    function queueClear() {
        if (clearQueued) return;
        clearQueued = true;
        // BOTH caches drop together. Painting mutates masks IN PLACE
        // (zone.regionMask[i] = 255 — the array object is never replaced), so any
        // cache that outlives the current synchronous burst would return stale
        // values for a repainted mask. For the sum that means a frozen zone hash
        // and silently skipped preview renders — the exact "silent drop" bug
        // class this codebase has hit three times already.
        const drop = function () {
            cache = new WeakMap();
            sumCache = new WeakMap();
            fingerprintCache = new WeakMap();
            clearQueued = false;
        };
        if (typeof queueMicrotask === 'function') queueMicrotask(drop);
        else Promise.resolve().then(drop);
    }

    /**
     * Count non-zero bytes, reading four at a time.
     *
     * A region mask is overwhelmingly ZEROS — a decal or a drawn shape is a few
     * percent of a 2048x2048 sheet, so ~97% of it is empty. Reading it as
     * Uint32 lets one comparison skip four empty bytes, which is where the win
     * comes from; only non-empty words are unpacked. Falls back to a byte loop
     * when the buffer is not 4-byte aligned (a subarray view can start anywhere).
     */
    function countNonZero(mask) {
        const n = mask.length;
        let count = 0;
        let i = 0;
        if (mask.BYTES_PER_ELEMENT === 1 && mask.buffer && (mask.byteOffset % 4) === 0) {
            const words = new Uint32Array(mask.buffer, mask.byteOffset, n >>> 2);
            const wn = words.length;
            for (let w = 0; w < wn; w++) {
                const v = words[w];
                if (v === 0) continue;                       // four empty bytes at once
                if (v & 0x000000ff) count++;
                if (v & 0x0000ff00) count++;
                if (v & 0x00ff0000) count++;
                if (v & 0xff000000) count++;
            }
            i = wn << 2;                                     // then the tail
        }
        for (; i < n; i++) if (mask[i] > 0) count++;
        return count;
    }

    /**
     * @returns {{any: boolean, count: number}} — `count` is the number of
     *          NON-ZERO entries, not their sum. (Summing values once inflated a
     *          user-facing note by 255x: a 376k-pixel box reported 95,890,455.)
     */
    function stats(mask) {
        if (!mask || typeof mask.length !== 'number') return { any: false, count: 0 };
        const hit = cache.get(mask);
        if (hit) { hits++; return hit; }

        const count = countNonZero(mask);
        const out = { any: count > 0, count: count };

        misses++; scanned += mask.length;
        if (typeof mask === 'object') { cache.set(mask, out); queueClear(); }
        return out;
    }

    function any(mask) { return stats(mask).any; }
    function count(mask) { return stats(mask).count; }

    /**
     * Byte SUM of the mask — the zone-config hash's mask fingerprint.
     *
     * This must stay a SUM, not a nonzero count: the hash uses it to detect that
     * a mask changed, and painting the same pixels at a different value (128 vs
     * 255) changes the sum but not the count. Word-wise with zero-skip, same as
     * the other passes; memoised per synchronous burst in its own WeakMap slot
     * (the hash reads regionMask AND spatialMask for every zone back to back).
     */
    function sum(mask) {
        if (!mask || typeof mask.length !== 'number') return 0;
        const hit = sumCache.get(mask);
        if (hit !== undefined) { hits++; return hit; }
        const n = mask.length;
        let total = 0;
        let i = 0;
        if (mask.BYTES_PER_ELEMENT === 1 && mask.buffer && (mask.byteOffset % 4) === 0) {
            const words = new Uint32Array(mask.buffer, mask.byteOffset, n >>> 2);
            const wn = words.length;
            for (let w = 0; w < wn; w++) {
                const v = words[w];
                if (v === 0) continue;
                total += (v & 0xff) + ((v >>> 8) & 0xff) + ((v >>> 16) & 0xff) + (v >>> 24);
            }
            i = wn << 2;
        }
        for (; i < n; i++) total += mask[i];
        misses++; scanned += n;
        if (typeof mask === 'object') {
            sumCache.set(mask, total);
            queueClear();
        }
        return total;
    }

    /**
     * Position-sensitive content fingerprint for render-cache keys.
     *
     * A byte sum is not an identity: moving the same selected pixels elsewhere
     * keeps the sum unchanged and used to leave Live Preview on the old mask.
     * Two independent 32-bit streams make order/content collisions vanishingly
     * unlikely while retaining the same one-pass O(n) cost as the old sum.
     */
    function fingerprint(mask) {
        if (!mask || typeof mask.length !== 'number') return '0:0:0';
        const hit = fingerprintCache.get(mask);
        if (hit !== undefined) { hits++; return hit; }

        const n = mask.length;
        let h1 = 0x811c9dc5;
        let h2 = 0x9e3779b9;
        // [SPB SPEED-TUNEUP 2026-08-30] Inline zero-run-skipping word hash.
        // The old per-word `mix()` closure cost 1-4M calls per mask (Float32
        // spatial masks even fell into a 4.2M per-ELEMENT path) — live-profiled
        // at ~250ms per preview settle in the owner's session, felt as a
        // click/release stall. Masks are ~97% zeros: zero WORDS are folded in
        // as run lengths (still fully position-sensitive — any repaint changes
        // the run structure), nonzero words get the full mix inline. The output
        // format changed with the algorithm; that only invalidates the compare
        // key once. Works on ANY typed array via its raw buffer bytes.
        if (mask.buffer && (mask.byteOffset % 4) === 0) {
            const byteLen = mask.byteLength != null ? mask.byteLength : n;
            const words = new Uint32Array(mask.buffer, mask.byteOffset, byteLen >>> 2);
            const wn = words.length;
            let zrun = 0;
            for (let w = 0; w < wn; w++) {
                const v = words[w];
                if (v === 0) { zrun++; continue; }
                if (zrun !== 0) {
                    h1 = Math.imul((h1 ^ zrun) >>> 0, 0x01000193) >>> 0;
                    h2 = (h2 + zrun) >>> 0;
                    zrun = 0;
                }
                h1 = Math.imul((h1 ^ v) >>> 0, 0x01000193) >>> 0;
                h2 = Math.imul((h2 ^ ((v + Math.imul(w + 1, 0x85ebca6b)) >>> 0)) >>> 0, 0xc2b2ae35) >>> 0;
                h2 = ((h2 << 13) | (h2 >>> 19)) >>> 0;
            }
            if (zrun !== 0) {
                h1 = Math.imul((h1 ^ zrun) >>> 0, 0x01000193) >>> 0;
                h2 = (h2 + zrun) >>> 0;
            }
            // tail bytes (byteLen not divisible by 4)
            const tailStart = wn << 2;
            for (let b = tailStart; b < byteLen; b++) {
                const tv = new Uint8Array(mask.buffer, mask.byteOffset + b, 1)[0];
                h1 = Math.imul((h1 ^ tv) >>> 0, 0x01000193) >>> 0;
                h2 = Math.imul((h2 ^ ((tv + Math.imul(b + 1, 0x85ebca6b)) >>> 0)) >>> 0, 0xc2b2ae35) >>> 0;
            }
        } else {
            for (let i = 0; i < n; i++) {
                const v = Number(mask[i]) >>> 0;
                h1 = Math.imul((h1 ^ v) >>> 0, 0x01000193) >>> 0;
                h2 = Math.imul((h2 ^ ((v + Math.imul(i + 1, 0x85ebca6b)) >>> 0)) >>> 0, 0xc2b2ae35) >>> 0;
                h2 = ((h2 << 13) | (h2 >>> 19)) >>> 0;
            }
        }
        h1 = Math.imul((h1 ^ n) >>> 0, 0x01000193) >>> 0;

        const result = n + ':' + h1.toString(16).padStart(8, '0') + ':' + h2.toString(16).padStart(8, '0');
        misses++; scanned += n;
        if (typeof mask === 'object') {
            fingerprintCache.set(mask, result);
            queueClear();
        }
        return result;
    }

    // A preview-triggering mutation can happen in the same JS turn as an earlier
    // stats read. Give the caller an explicit hard invalidation instead of waiting
    // for the microtask cache drop.
    function invalidate(mask) {
        if (mask && typeof mask === 'object') {
            cache.delete(mask);
            sumCache.delete(mask);
            fingerprintCache.delete(mask);
            return;
        }
        cache = new WeakMap();
        sumCache = new WeakMap();
        fingerprintCache = new WeakMap();
    }

    /**
     * Bounding box of the set pixels, in the SAME memoised pass as any/count.
     *
     * _getActiveSelectionInfo() used a nested x/y loop over all 4,194,304 pixels
     * to find this box — and hasActivePixelSelection() called it purely to ask
     * "is anything selected?", then threw the box away. That was 76ms of the
     * remaining freeze, spent computing a rectangle nobody wanted.
     *
     * @returns {{any, count, minX, minY, maxX, maxY}} — box fields are -1/0 when
     *          nothing is set; callers should check `any` first.
     */
    function bounds(mask, width) {
        if (!mask || !width) return { any: false, count: 0, minX: 0, minY: 0, maxX: -1, maxY: -1 };
        const memo = cache.get(mask);
        if (memo && memo.boundsWidth === width) { hits++; return memo; }

        const n = mask.length;
        let count = 0, minX = width, minY = (n / width) | 0, maxX = -1, maxY = -1;
        const aligned = mask.BYTES_PER_ELEMENT === 1 && mask.buffer && (mask.byteOffset % 4) === 0;
        const wn = aligned ? (n >>> 2) : 0;
        const words = aligned ? new Uint32Array(mask.buffer, mask.byteOffset, wn) : null;

        for (let w = 0; w < wn; w++) {
            const word = words[w];
            if (word === 0) continue;                        // skip four empty pixels
            const base = w << 2;
            // SPB-93 2026-09-07: solid rectangles repeatedly located every
            // pixel during overlay settlement. Four opaque bytes on a width
            // divisible by four share a row; update their exact bounds once.
            // Cache lifetime and in-place mutation invalidation stay unchanged.
            if (word === 0xffffffff && (width & 3) === 0) {
                const x = base % width, y = (base - x) / width;
                count += 4;
                if (x < minX) minX = x;
                if (x + 3 > maxX) maxX = x + 3;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
                continue;
            }
            for (let k = 0; k < 4; k++) {
                if (!mask[base + k]) continue;
                const i = base + k;
                const x = i % width, y = (i - x) / width;
                count++;
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
        }
        for (let i = wn << 2; i < n; i++) {                  // tail
            if (!mask[i]) continue;
            const x = i % width, y = (i - x) / width;
            count++;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }

        const out = { any: count > 0, count: count, boundsWidth: width,
                      minX: maxX < 0 ? 0 : minX, minY: maxY < 0 ? 0 : minY,
                      maxX: maxX, maxY: maxY };
        misses++; scanned += n;
        cache.set(mask, out); queueClear();
        return out;
    }

    /** Seed exact bounds calculated by the producer of a freshly allocated mask.
     * SPB-93 2026-09-07, owner: remove laggy drags. Rectangle activation spent
     * another8–16ms scanning a hard Replace mask whose area is already known.
     * This shares ONLY the existing synchronous cache, never a later frame.
     * The producer guarantees pixel correspondence; mutations must invalidate.
     */
    function primeBounds(mask, width, value) {
        if (!(mask instanceof Uint8Array) || !Number.isInteger(width) || width <= 0 ||
            !value || !Number.isInteger(value.count) || value.count <= 0 || value.count > mask.length ||
            !['minX', 'minY', 'maxX', 'maxY'].every(key => Number.isInteger(value[key])) ||
            value.minX < 0 || value.minY < 0 || value.maxX < value.minX || value.maxY < value.minY ||
            value.maxX >= width || value.maxY >= mask.length / width ||
            value.count > (value.maxX - value.minX + 1) * (value.maxY - value.minY + 1)) return false;
        invalidate(mask);
        cache.set(mask, { any: true, count: value.count, boundsWidth: width,
            minX: value.minX, minY: value.minY, maxX: value.maxX, maxY: value.maxY });
        queueClear();
        return true;
    }

    /** Diagnostic only — how much rescanning are we actually avoiding? */
    function debugStats() {
        return { hits: hits, misses: misses, scannedPixels: scanned,
                 hitRate: (hits + misses) ? +(100 * hits / (hits + misses)).toFixed(1) : 0 };
    }

    return {
        stats: stats,
        any: any,
        count: count,
        sum: sum,
        fingerprint: fingerprint,
        invalidate: invalidate,
        bounds: bounds,
        primeBounds: primeBounds,
        debugStats: debugStats
    };
});

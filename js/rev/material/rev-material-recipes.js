/* [SPB-REV-MATERIAL 2026-10-10] Material recipes: spec presets + Wear & Weathering textures.
 * Pure functions (no DOM), loaded before rev-material-core.js; also runs under node for tests.
 *
 * iRacing spec: R = metallic, G = roughness (0 = mirror), B = clearcoat (16 = max gloss, 255 = dull).
 * PRESET values were read from engine.BASE_REGISTRY on 2026-10-10
 * (_easy_claude_work/rev_tools/material/dump_registry.py -> registry_subset.json); the
 * lane test re-checks them against the live registry. Never hand-tune them from memory.
 *
 * Every wear texture is a deterministic function of the CANVAS pixel (x, y), the stroke
 * direction and a seed, so overlapping dabs agree and a re-stroke continues the same grain.
 * Feature sizes target the 2048 car sheet: 8-32 px structure, 1-3 px grit, 2-10 px chips.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBRevMatRecipes = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // ---- presets (M, R, CC straight from BASE_REGISTRY; chan = which spec channels the preset writes) ----
    const PRESETS = [
        { id: 'gloss', name: 'Gloss', src: 'gloss', m: 0, r: 30, cc: 16, chan: [1, 1, 1], grain: 0 },
        { id: 'satin', name: 'Satin', src: 'satin', m: 0, r: 95, cc: 70, chan: [1, 1, 1], grain: 15 },
        { id: 'matte', name: 'Matte', src: 'matte', m: 0, r: 200, cc: 160, chan: [1, 1, 1], grain: 20 },
        { id: 'chrome', name: 'Chrome', src: 'chrome', m: 255, r: 2, cc: 0, chan: [1, 1, 1], grain: 0 },
        { id: 'brushed', name: 'Brushed Metal', src: 'brushed_aluminum', m: 200, r: 55, cc: 16, chan: [1, 1, 1], grain: 60, grainKind: 'brushed' },
        { id: 'patina', name: 'Patina', src: 'patina_bronze', m: 160, r: 90, cc: 100, chan: [1, 1, 1], grain: 70, grainKind: 'patina' },
        // Clearcoat Fade = sun-dead clear: ONLY the clearcoat channel moves (to clear_matte's CC);
        // metallic and roughness underneath are kept exactly.
        { id: 'ccfade', name: 'Clearcoat Fade', src: 'clear_matte', m: 0, r: 215, cc: 200, chan: [0, 0, 1], grain: 25 },
        { id: 'raw', name: 'Custom', src: null, m: 0, r: 30, cc: 16, chan: [1, 1, 1], grain: 0 }
    ];
    const PRESET_BY_ID = {};
    PRESETS.forEach(function (p) { PRESET_BY_ID[p.id] = p; });

    const WEAR = [
        { id: 'dirt', name: 'Dirt & Grime', tip: 'road film: darker, rougher, clearcoat dulled' },
        { id: 'rubber', name: 'Rubber Marks', tip: 'tyre marbles + rub streaks along your stroke' },
        { id: 'chips', name: 'Stone Chips', tip: 'chips to primer, bare metal at the cores' }
    ];

    // ---- deterministic noise ----
    function hash(ix, iy, s) {
        let h = Math.imul(ix | 0, 374761393) ^ Math.imul(iy | 0, 668265263) ^ Math.imul((s | 0) + 1013, 1442695041);
        h = Math.imul(h ^ (h >>> 13), 1274126177);
        h ^= h >>> 16;
        return (h >>> 0) / 4294967296;
    }
    function vnoise(x, y, s) {
        const ix = Math.floor(x), iy = Math.floor(y);
        const fx = x - ix, fy = y - iy;
        const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
        const a = hash(ix, iy, s), b = hash(ix + 1, iy, s), c = hash(ix, iy + 1, s), d = hash(ix + 1, iy + 1, s);
        return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy;
    }
    // anisotropic fBm: u runs ALONG the stroke (stretched), v across. sizes in px.
    function fbmA(u, v, s, sizes, stretch) {
        let sum = 0, wsum = 0, w = 1;
        for (let i = 0; i < sizes.length; i++) {
            const sz = sizes[i];
            sum += w * vnoise(u / (sz * stretch), v / sz, s + i * 31);
            wsum += w; w *= 0.62;
        }
        return sum / wsum;
    }
    function smooth(a, b, x) { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); }
    function clamp255(v) { return v < 0 ? 0 : (v > 255 ? 255 : v); }

    /** A stroke context: direction (radians) + seed. Returns {sampleWear, sampleSpec}. */
    function makeContext(angle, seed) {
        const ca = Math.cos(angle || 0), sa = Math.sin(angle || 0);
        const sd = seed | 0;
        function uv(x, y, o) { o.u = x * ca + y * sa; o.v = -x * sa + y * ca; return o; }
        const _uv = { u: 0, v: 0 };

        // out fields: pr pg pb pa (paint + alpha 0..1) | m r cc (spec) | am ar ac (spec alpha per channel)
        function dirt(x, y, A, o) {
            uv(x, y, _uv);
            const D = fbmA(_uv.u, _uv.v, sd, [32, 16, 8], 3.2);               // patchy film, streaked along the stroke
            const st = vnoise(_uv.u / 56, _uv.v / 3.5, sd + 7);               // fine airflow streaks (~3 px wide)
            const tone = vnoise(x / 14, y / 14, sd + 11);                      // dust vs grime colour
            const grit = hash(x, y, sd + 19);                                  // 1 px particles
            let t = smooth(0.30, 0.78, 0.62 * D + 0.38 * st);
            let a = A * (0.25 + 0.75 * t);
            let pr = 118 - 52 * tone, pg = 104 - 46 * tone, pb = 84 - 38 * tone; // light dust -> dark grime
            if (grit > 0.955 && A > 0.15) { a = Math.max(a, 0.85 * Math.min(1, A * 1.4)); pr *= 0.55; pg *= 0.55; pb *= 0.55; }
            o.pr = pr; o.pg = pg; o.pb = pb; o.pa = Math.min(1, a * 0.82);
            // spec: dirt kills metal + gloss even when the film is thin (spec alpha leads paint alpha)
            const sA = Math.min(1, Math.pow(a, 0.7));
            o.m = 22; o.r = 178 + 58 * D; o.cc = 196 + 52 * D;
            o.am = sA; o.ar = sA; o.ac = sA;
            return o;
        }

        function rubber(x, y, A, o) {
            uv(x, y, _uv);
            // tyre marbles: a few px blobs on a 14 px cell lattice, presence gated by stroke density
            const cs = 14, cx = Math.floor(x / cs), cy = Math.floor(y / cs);
            let blob = 0, bk = 1;
            for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
                const gx = cx + i, gy = cy + j;
                const k = hash(gx, gy, sd + 41);
                if (k > 0.62) continue;
                const px = (gx + hash(gx, gy, sd + 43)) * cs, py = (gy + hash(gx, gy, sd + 47)) * cs;
                const rr = 1.3 + 3.6 * Math.pow(hash(gx, gy, sd + 53), 2);
                const dx = x + 0.5 - px, dy = y + 0.5 - py;
                const d = Math.sqrt(dx * dx + dy * dy) * (1 + 0.3 * (hash(x, y, sd + 59) - 0.5));
                if (d < rr && k < bk) { bk = k; blob = d < rr - 0.8 ? 1 : (rr - d) / 0.8; }
            }
            const marble = (blob > 0 && bk / 0.62 < A) ? blob : 0;
            // rub streaks: long thin smears along the stroke, banded
            const s1 = vnoise(_uv.u / 70, _uv.v / 2.4, sd + 61);
            const band = vnoise(_uv.u / 140, _uv.v / 11, sd + 67);
            const smear = smooth(0.55, 0.86, s1) * smooth(0.32, 0.70, band) * 0.88 * A;
            const a = Math.max(marble, smear);
            const lite = marble > smear ? 0 : 14 * (1 - s1);
            o.pr = 25 + lite; o.pg = 24 + lite; o.pb = 26 + lite; o.pa = a;
            o.m = 0; o.r = 150 + 28 * s1; o.cc = 205 + 25 * band;
            o.am = a; o.ar = a; o.ac = a;
            return o;
        }

        function chips(x, y, A, o) {
            // stone chips: 11 px lattice, irregular ellipses 1-5.5 px, primer ring + bare-metal core
            const cs = 11, cx = Math.floor(x / cs), cy = Math.floor(y / cs);
            let best = 9, bmetal = 0, bk = 1, lip = 0;
            for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
                const gx = cx + i, gy = cy + j;
                const k = hash(gx, gy, sd + 71);
                if (k / 0.8 >= A) continue;                      // density follows the stroke (soft edge = sparser)
                const px = (gx + hash(gx, gy, sd + 73)) * cs, py = (gy + hash(gx, gy, sd + 79)) * cs;
                const rr = 1.0 + 4.5 * Math.pow(hash(gx, gy, sd + 83), 2.2);
                const th = hash(gx, gy, sd + 89) * Math.PI, asp = 1 + 0.8 * hash(gx, gy, sd + 97);
                const ct = Math.cos(th), st = Math.sin(th);
                const dx = x + 0.5 - px, dy = y + 0.5 - py;
                const a1 = dx * ct + dy * st, a2 = (-dx * st + dy * ct) * asp;
                const jag = 1 + 0.34 * (hash(x, y, sd + 101) - 0.5) + 0.22 * (vnoise(x / 2.2, y / 2.2, sd + 103) - 0.5);
                const dn = Math.sqrt(a1 * a1 + a2 * a2) * jag / rr;
                if (dn < best) { best = dn; bk = k; bmetal = hash(gx, gy, sd + 107) < 0.55 && rr > 1.6 ? 1 : 0; }
            }
            if (best < 0.5 && bmetal) {                          // bare metal core
                const v = vnoise(x / 3, y / 3, sd + 109);
                const g = 170 + 22 * v;
                o.pr = g; o.pg = g + 2; o.pb = g + 6; o.pa = 1;
                o.m = 228; o.r = 62 + 26 * v; o.cc = 255; o.am = 1; o.ar = 1; o.ac = 1;
            } else if (best < 1) {                               // primer ring
                const v = hash(x, y, sd + 113);
                const g = 116 + 14 * v;
                o.pr = g + 2; o.pg = g + 1; o.pb = g - 4; o.pa = 1;
                o.m = 0; o.r = 205 + 20 * v; o.cc = 255; o.am = 1; o.ar = 1; o.ac = 1;
            } else if (best < 1.38) {                            // chipped-paint lip: a faint dark edge, no spec change
                lip = 1 - (best - 1) / 0.38;
                o.pr = 0; o.pg = 0; o.pb = 0; o.pa = 0.24 * lip;
                o.m = 0; o.r = 0; o.cc = 0; o.am = 0; o.ar = 0; o.ac = 0;
            } else {
                o.pa = 0; o.am = 0; o.ar = 0; o.ac = 0;
            }
            return o;
        }

        function sampleWear(type, x, y, A, o) {
            if (type === 'rubber') return rubber(x, y, A, o);
            if (type === 'chips') return chips(x, y, A, o);
            return dirt(x, y, A, o);
        }

        /** Spec Brush value at (x,y): preset/custom values + optional fine grain (0..100). */
        function sampleSpec(p, x, y, o) {
            let m = p.m, r = p.r, cc = p.cc;
            const g = (p.grain || 0) / 100;
            if (g > 0) {
                if (p.grainKind === 'brushed') {
                    uv(x, y, _uv);
                    const s = vnoise(_uv.u / 46, _uv.v / 0.85, sd + 131) - 0.5;         // ~1 px wide, 46 px long
                    const s2 = vnoise(_uv.u / 120, _uv.v / 6, sd + 137) - 0.5;
                    r += g * (52 * s + 18 * s2); m += g * 14 * s;
                } else if (p.grainKind === 'patina') {
                    const f = fbmA(x, y, sd + 139, [32, 16, 8], 1) - 0.5;
                    const sp = hash(x, y, sd + 149) - 0.5;
                    m -= g * 90 * Math.max(0, f); r += g * (70 * f + 16 * sp); cc += g * 60 * f;
                } else {
                    const f = vnoise(x / 8, y / 8, sd + 151) - 0.5;
                    const sp = hash(x, y, sd + 157) - 0.5;
                    r += g * (22 * f + 14 * sp); cc += g * 18 * f;
                }
            }
            o.m = clamp255(m); o.r = clamp255(r); o.cc = clamp255(cc);
            return o;
        }
        return { sampleWear: sampleWear, sampleSpec: sampleSpec };
    }

    /** iRacing output floors, as the engine writes them (CC >= 16; R >= 15 unless chrome M >= 240). */
    function floored(m, r, cc) {
        return { m: m, r: (m < 240 ? Math.max(15, r) : r), cc: Math.max(16, cc) };
    }
    /** Nearest preset name for a picked material (for the eyedropper readout). */
    function nearestPreset(m, r, cc) {
        let best = null, bd = 1e9;
        PRESETS.forEach(function (p) {
            if (p.id === 'raw' || p.id === 'ccfade') return;
            const f = floored(p.m, p.r, p.cc);
            const d = (f.m - m) * (f.m - m) + (f.r - r) * (f.r - r) + 0.5 * (f.cc - cc) * (f.cc - cc);
            if (d < bd) { bd = d; best = p; }
        });
        return best;
    }

    return { PRESETS: PRESETS, PRESET_BY_ID: PRESET_BY_ID, WEAR: WEAR, makeContext: makeContext, hash: hash, vnoise: vnoise, floored: floored, nearestPreset: nearestPreset };
});

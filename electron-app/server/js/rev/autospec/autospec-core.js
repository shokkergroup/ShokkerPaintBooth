/* [SPB-REV-AUTOSPEC 2026-10-10] Spec Autopilot core: look at a layer's pixels, name, role and car parts, decide what the thing IS
 * (body paint, numbers, sponsor / logo vinyl, tape / stripes, silver metal art, black trim, carbon texture ...) and propose ONE existing
 * SPB material for it. No DOM. Runs in the page (window.SPBAutoSpecCore) and in Node for calibration (module.exports).
 * This module only CHOOSES among materials that already exist (Layer Materials presets + Foundation finishes). It authors no spec.
 *
 * iRacing spec semantics (never get these wrong): R = metallic, G = roughness (0 = mirror), B = clearcoat (0-15 none, 16 = max gloss,
 * 255 = dull), A = specular mask. Every number in MATERIALS below was read from engine.BASE_REGISTRY (dump_registry.py ->
 * _easy_claude_work/rev_tools/autospec/registry_all.json, checked by check_materials.py), never typed from memory.
 * Design + calibration: _easy_claude_work/rev_tools/autospec/DESIGN.md. */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBAutoSpecCore = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';
    const VERSION = 'rev-autospec-2026-10-10a';

    // ------------------------------------------------------------------ the materials Autopilot may assign
    // ref = what SPBRevLayerMat.normalize() accepts. m / r / cc = BASE_REGISTRY M / R / CC. cce = the clearcoat the engine really writes
    // (it floors CC below 16 to 16). Foundation (f_*) finishes keep the layer's own paint colours; they only write spec.
    const MATERIALS = [
        { id: 'zones',        name: 'Leave To The Zones',   ref: null,                          src: null,               m: null, r: null, cc: null, cce: null, tip: 'No layer material: the zones decide this layer\'s spec' },
        { id: 'gel',          name: 'Gel Coat Gloss',       ref: { finishId: 'f_gel_coat' },     src: 'f_gel_coat',       m: 0,   r: 15,  cc: 16,  tip: 'Deepest wet-look gloss' },
        { id: 'gloss',        name: 'Gloss Vinyl',          ref: { preset: 'gloss' },           src: 'gloss',            m: 0,   r: 30,  cc: 16,  tip: 'Glossy printed vinyl under clear' },
        { id: 'satin',        name: 'Satin Vinyl',          ref: { preset: 'satin' },           src: 'satin',            m: 0,   r: 95,  cc: 70,  tip: 'Soft semi-gloss vinyl, with a little grain' },
        { id: 'matte',        name: 'Matte Vinyl',          ref: { preset: 'matte' },           src: 'matte',            m: 0,   r: 200, cc: 160, tip: 'Flat matte vinyl, no shine' },
        { id: 'chrome',       name: 'Chrome Foil',          ref: { preset: 'chrome' },          src: 'chrome',           m: 255, r: 2,   cc: 0,   tip: 'Mirror chrome foil' },
        { id: 'satin_chrome', name: 'Satin Chrome',         ref: { finishId: 'f_satin_chrome' }, src: 'f_satin_chrome',   m: 250, r: 45,  cc: 40,  tip: 'Soft, hazy chrome' },
        { id: 'brushed',      name: 'Brushed Metal',        ref: { preset: 'brushed' },         src: 'brushed_aluminum', m: 200, r: 55,  cc: 16,  tip: 'Brushed aluminium foil with a grain' },
        { id: 'carbon',       name: 'Carbon Fibre Clear',   ref: { finishId: 'f_carbon_fiber' }, src: 'f_carbon_fiber',   m: 55,  r: 30,  cc: 16,  tip: 'Lacquered carbon weave' },
        { id: 'pearl',        name: 'Pearl',                ref: { finishId: 'f_pearl' },        src: 'f_pearl',          m: 100, r: 40,  cc: 16,  tip: 'Soft pearl sheen' },
        { id: 'metallic',     name: 'Metallic',             ref: { finishId: 'f_metallic' },     src: 'f_metallic',       m: 200, r: 50,  cc: 16,  tip: 'Metallic flake paint' },
        { id: 'candy',        name: 'Candy',                ref: { finishId: 'f_candy' },        src: 'f_candy',          m: 200, r: 15,  cc: 16,  tip: 'Deep candy gloss' }
    ];
    MATERIALS.forEach(function (mt) { mt.cce = mt.cc == null ? null : (mt.cc < 16 ? 16 : mt.cc); });
    const MAT = {}; MATERIALS.forEach(function (mt) { MAT[mt.id] = mt; });

    const KINDS = {
        body: 'Body Paint', numbers: 'Numbers', sponsor: 'Sponsor / Logo Decals', stripe: 'Tape / Stripes', metal: 'Silver Metal Art',
        trim: 'Black Trim', carbon: 'Carbon Texture', other: 'Printed Art', guide: 'Template Guide (Not Printed)', tiny: 'Too Small To See'
    };
    const T = {
        minPx: 400,            // below this a layer is invisible at sim distance (same floor the Spec Doctor uses)
        neutralS: 0.16,        // HSV saturation under this = neutral grey
        darkV: 0.20,           // HSV value under this = near black
        chromeMin: 0.55,       // chromeScore at or above this = silver metal art
        carbonMin: 0.50,       // carbonScore at or above this = carbon weave
        trimDark: 0.85,        // fraction of near-black pixels for black trim
        bodyCov: 0.20,         // a layer covering this share of the whole sheet is body-sized
        trimPartShare: 0.5     // share of a dark layer's pixels on bumper / splitter / spoiler parts
    };

    // ------------------------------------------------------------------ pixel features
    function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
    /** rgba: RGBA bytes (non-premultiplied), own: Uint8 visible-ownership alpha (0-255), W x H. opt.stride = sample step; opt.up = full-size px per sheet px. */
    function features(rgba, own, W, H, opt) {
        opt = opt || {};
        const st = opt.stride || (W >= 1536 ? 2 : 1), up = opt.up || (2048 / W);       // up = full-size pixels per sample pixel (per axis)
        const unit = up * up * st * st;                                                 // full-size pixels one sample stands for
        const gw = Math.ceil(W / st), gh = Math.ceil(H / st), G = gw * gh;
        const Lg = new Float32Array(G), Mg = new Uint8Array(G);                         // luminance grid + "this layer owns it" grid
        const HB = 64, hist = new Float64Array(HB), nhist = new Float64Array(HB), cbin = new Float64Array(4096);
        let n = 0, sumL = 0, sumS = 0, sumV = 0, nNeutral = 0, nDark = 0, nLight = 0, nSat = 0, nMidN = 0, sr = 0, sg = 0, sb = 0;
        let x0 = W, y0 = H, x1 = -1, y1 = -1;
        for (let gy = 0, y = 0; gy < gh; gy++, y += st) {
            const row = y * W;
            for (let gx = 0, x = 0; gx < gw; gx++, x += st) {
                const i = row + x;
                if (own[i] < 128) continue;
                const j = i * 4, r = rgba[j], g = rgba[j + 1], b = rgba[j + 2];
                const mx = r > g ? (r > b ? r : b) : (g > b ? g : b), mn = r < g ? (r < b ? r : b) : (g < b ? g : b);
                const V = mx / 255, S = mx ? (mx - mn) / mx : 0, L = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
                Lg[gy * gw + gx] = L; Mg[gy * gw + gx] = 1;
                n++; sumL += L; sumS += S; sumV += V; sr += r; sg += g; sb += b;
                if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
                const hb = Math.min(HB - 1, (L * HB) | 0); hist[hb]++;
                cbin[((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)]++;
                if (S < T.neutralS) { nNeutral++; nhist[hb]++; if (L > 0.22 && L < 0.78) nMidN++; }
                if (V < T.darkV) nDark++;
                if (V > 0.85 && S < T.neutralS) nLight++;
                if (S > 0.45) nSat++;
            }
        }
        const f = { n: 0, px: 0, cov: 0, bbox: null, W: W, H: H };
        if (!n) return f;
        // smooth-ramp fraction: the tone changes by 0.02-0.35 over ~12 px but by < 0.05 between neighbours, in x or y (gradients; not flat fills, not noise, not hard edges)
        const K = Math.max(2, Math.round(12 / st));
        let ramp = 0, cmp = 0;
        for (let gy = 0; gy + K < gh; gy++) for (let gx = 0; gx + K < gw; gx++) {
            const a = gy * gw + gx, b = a + K, c = a + K * gw;
            if (!Mg[a]) continue;
            const dx = Mg[b] && Mg[a + 1] ? Math.abs(Lg[b] - Lg[a]) : -1, dy = Mg[c] && Mg[a + gw] ? Math.abs(Lg[c] - Lg[a]) : -1;
            if (dx < 0 && dy < 0) continue;
            cmp++;
            const ok = function (far, near) { return far >= 0.02 && far <= 0.35 && near < 0.05; };
            if ((dx >= 0 && ok(dx, Math.abs(Lg[a + 1] - Lg[a]))) || (dy >= 0 && ok(dy, Math.abs(Lg[a + gw] - Lg[a])))) ramp++;
        }
        const q = function (h, tot, p) { let c = 0; for (let k = 0; k < HB; k++) { c += h[k]; if (c >= tot * p) return (k + 0.5) / HB; } return 1; };
        let top = 0, nCol = 0; for (let k = 0; k < 4096; k++) { if (cbin[k] > top) top = cbin[k]; if (cbin[k] >= n * 0.025) nCol++; }
        f.n = n; f.px = Math.round(n * unit); f.cov = f.px / (W * H * up * up);
        f.bbox = [x0 * up, y0 * up, (x1 + st) * up, (y1 + st) * up];
        f.fill = f.px / Math.max(1, (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]));
        f.lum = sumL / n; f.sat = sumS / n; f.val = sumV / n; f.mean = [Math.round(sr / n), Math.round(sg / n), Math.round(sb / n)];
        f.fNeutral = nNeutral / n; f.fDark = nDark / n; f.fLight = nLight / n; f.fSat = nSat / n;
        f.p05 = q(hist, n, 0.05); f.p50 = q(hist, n, 0.5); f.p95 = q(hist, n, 0.95);
        f.nCol = nCol; f.domShare = top / n;
        f.rampFrac = cmp ? ramp / cmp : 0;
        // neutral-pixel luminance spread + how much of it sits in the mid tones (a gradient, not just black and white)
        f.nSpread = nNeutral > 30 ? Math.max(0, q(nhist, nNeutral, 0.95) - q(nhist, nNeutral, 0.05)) : 0;
        f.nMid = nNeutral ? nMidN / nNeutral : 0;
        // silver / chrome art: mostly neutral, a wide luminance spread, real mid tones, and smooth ramps between them
        const smooth = clamp01((f.rampFrac - 0.10) / 0.30);
        f.chromeScore = f.fNeutral >= 0.55 && f.lum > 0.30
            ? clamp01((f.nSpread - 0.28) / 0.30) * clamp01((f.nMid - 0.10) / 0.25) * smooth * clamp01((f.fNeutral - 0.45) / 0.35) : 0;
        f.carbonScore = 0;
        return f;
    }

    /** Carbon weave: a fine periodic texture. Lwin = Float32Array(w*h) luminance of a fully-owned crop. Autocorrelation of the mean-removed
     *  signal along x, y and the diagonal; a weave shows a clear secondary peak (period 4-27 px) after a valley. Returns {score 0..1, peak, lag, std}. */
    function periodicity(Lwin, w, h) {
        let m = 0; for (let i = 0; i < Lwin.length; i++) m += Lwin[i]; m /= Lwin.length;
        let v = 0; for (let i = 0; i < Lwin.length; i++) { const d = Lwin[i] - m; v += d * d; } v /= Lwin.length;
        if (v < 2e-4) return { score: 0, peak: 0, lag: 0, std: Math.sqrt(v) };
        const MAXL = 28, r = new Float64Array(MAXL + 2);
        for (let lag = 1; lag <= MAXL; lag++) {
            let acc = 0, cnt = 0;
            for (let y = 0; y + lag < h; y += 2) for (let x = 0; x + lag < w; x += 2) {
                const a = Lwin[y * w + x] - m;
                acc += a * (Lwin[y * w + x + lag] - m) + a * (Lwin[(y + lag) * w + x] - m) + a * (Lwin[(y + lag) * w + x + lag] - m) * 0.5; cnt += 2.5;
            }
            r[lag] = acc / cnt / v;
        }
        let best = 0, bestLag = 0;
        for (let lag = 4; lag < MAXL; lag++) {
            if (!(r[lag] > r[lag - 1] && r[lag] >= r[lag + 1])) continue;
            let valley = 1; for (let k = 1; k < lag; k++) if (r[k] < valley) valley = r[k];
            const sc = r[lag] - Math.max(0.0, valley);
            if (r[lag] >= 0.30 && sc > best) { best = sc; bestLag = lag; }
        }
        return { score: clamp01((best - 0.12) / 0.35), peak: best, lag: bestLag, std: Math.sqrt(v) };
    }

    /** Scan the layer for fully-owned 96 x 96 crops that carry real texture and measure how periodic it is. Only meaningful on dark, fairly
     *  neutral art (carbon is never saturated or bright); anything else returns 0 without scanning. Sets and returns f.carbonScore. */
    function carbonFor(rgba, own, W, H, f) {
        f.carbonScore = 0; f.carbonLag = 0;
        if (!f.n || W < 1024 || f.val > 0.6 || f.sat > 0.4 || f.fDark < 0.25) return 0;
        const CW = 96, step = 128, wins = [];
        for (let y0 = 0; y0 + CW <= H && wins.length < 8; y0 += step) for (let x0 = 0; x0 + CW <= W && wins.length < 8; x0 += step) {
            let ok = true;
            for (let y = y0; y < y0 + CW && ok; y += 4) { const row = y * W; for (let x = x0; x < x0 + CW; x += 4) if (own[row + x] < 230) { ok = false; break; } }
            if (!ok) continue;
            const L = new Float32Array(CW * CW);
            let m = 0, k = 0;
            for (let y = 0; y < CW; y++) for (let x = 0; x < CW; x++) { const j = ((y0 + y) * W + x0 + x) * 4; const l = (0.2126 * rgba[j] + 0.7152 * rgba[j + 1] + 0.0722 * rgba[j + 2]) / 255; L[k++] = l; m += l; }
            m /= L.length; let v = 0; for (let i = 0; i < L.length; i++) v += (L[i] - m) * (L[i] - m);
            if (Math.sqrt(v / L.length) < 0.012) continue;           // flat crop: nothing to measure
            wins.push(L);
        }
        let best = 0, lag = 0;
        wins.forEach(function (L) { const r = periodicity(L, CW, CW); if (r.score > best) { best = r.score; lag = r.lag; } });
        f.carbonScore = best; f.carbonLag = lag; f.carbonWins = wins.length;
        return best;
    }

    // ------------------------------------------------------------------ what is it
    function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9#]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    function nameKind(name, role, group) {
        const n = norm(name), r = String(role || ''), g = norm(group);
        if (/^template/.test(r) || /turn off|export|template|guide/.test(g) || /(^| )(mask|wire|wireframe|mandatory|template|guide|outline|uv|legend|safe area|bleed)( |$)/.test(n)) return 'guide';
        if (/carbon|kevlar|weave|twill/.test(n)) return 'carbon';
        if (/chrome|metal|silver|foil|mirror finish|brushed|alumin|steel|titanium/.test(n)) return 'metal';
        if (/number|(^| )num( |$)|(^| )#/.test(n) || r === 'numbers') return 'numbers';
        if (/sponsor/.test(n) || r === 'sponsors') return 'sponsor';
        if (/tape|stripe|band( |$)|racing line/.test(n) || r === 'tape / stripes') return 'stripe';
        if (/trim|bumper|splitter|spoiler|valance|rocker|grille|grill( |$)|window frame|wheel|rim( |$)/.test(n)) return 'trim';
        if (/logo|decal|sticker|badge|banner|pitbox|pit box|windshield|contingency|manufacturer|crest|emblem/.test(n) || r === 'decals / logos') return 'sponsor';
        if (/car paint|(^| )body( |$)|base paint|livery|^paint$|(^| )base( |$)|base (coat|layer|colou?r)/.test(n) || r === 'body paint') return 'body';
        return null;
    }
    const TRIM_PARTS = /bumper|splitter|spoiler|valance|rocker|skirt|diffuser|wing/;
    /** meta = { name, role, group, parts: {partName: share 0..1}, zoneCustom: bool }.  f from features(). */
    function classify(f, meta) {
        meta = meta || {};
        const nk = nameKind(meta.name, meta.role, meta.group);
        const out = { name: nk, ev: [], look: null, what: null, conf: 0.5 };
        if (nk === 'guide') { out.what = 'guide'; out.conf = 0.97; out.ev.push('template layer'); return out; }
        if (!f || !f.n || f.px < T.minPx) { out.what = 'tiny'; out.conf = f && f.n ? 0.9 : 0.97; out.ev.push(f && f.n ? ('only ' + f.px + ' px visible') : 'nothing visible'); return out; }
        const parts = meta.parts || {}, partNames = Object.keys(parts);
        let trimShare = 0; partNames.forEach(function (p) { if (TRIM_PARTS.test(p)) trimShare += parts[p]; });
        const S = { body: 0, numbers: 0, sponsor: 0, stripe: 0, other: 0.15 };
        if (nk && S[nk] !== undefined) S[nk] += 0.65;
        // size / spread: a layer that covers a big share of the sheet and has a few flat colours is body-sized
        if (f.cov >= T.bodyCov) { S.body += 0.30; out.ev.push('covers ' + Math.round(f.cov * 100) + '% of the sheet'); }
        if (f.nCol >= 5) S.sponsor += 0.15;
        if (f.nCol <= 3 && f.domShare > 0.5 && f.cov < T.bodyCov) S.stripe += 0.10;
        // looks (pixel evidence): these can override a vague name, never a strong one
        const look = [];
        if (f.chromeScore >= T.chromeMin) look.push(['metal', f.chromeScore]);
        if (f.carbonScore >= T.carbonMin) look.push(['carbon', f.carbonScore]);
        const darkFlat = f.fDark >= T.trimDark && f.sat < 0.45 && f.val < 0.35;
        const bodyish = nk === 'body' || (!nk && f.cov >= T.bodyCov);
        if (darkFlat && !bodyish) look.push(['trim', clamp01(0.6 + 0.4 * (f.fDark - T.trimDark) / (1 - T.trimDark)) * (trimShare >= T.trimPartShare ? 1 : 0.9)]);
        if (nk === 'carbon') look.push(['carbon', 0.7 + 0.3 * f.carbonScore]);
        if (nk === 'metal' && f.sat < 0.45) look.push(['metal', 0.6 + 0.4 * f.chromeScore]);
        if (nk === 'trim' && f.val < 0.45) look.push(['trim', 0.7]);
        look.sort(function (a, b) { return b[1] - a[1]; });
        const w = Object.keys(S).sort(function (a, b) { return S[b] - S[a]; });
        out.what = w[0]; out.conf = clamp01(0.55 + 0.9 * (S[w[0]] - S[w[1]]));
        if (nk === out.what || (nk === null && out.what === 'body' && f.cov >= T.bodyCov)) out.conf = Math.max(out.conf, 0.82);
        if (look.length) {
            const lk = look[0];
            // a body-paint layer stays body (its zones decide); numbers / stripes / sponsors can still be metal or carbon
            if (!(out.what === 'body' && lk[0] === 'trim')) {
                out.look = lk[0]; out.lookScore = lk[1];
                out.conf = clamp01(Math.max(0.55, Math.min(0.97, 0.5 + 0.5 * lk[1])) * 0.6 + out.conf * 0.4 + (nk === lk[0] ? 0.08 : 0));
                out.ev.push(lk[0] === 'metal' ? 'grey gradient art (' + Math.round(f.nSpread * 100) + '% tone spread)' : lk[0] === 'carbon' ? 'fine woven texture' : 'near-black flat art');
            }
        }
        if (!out.look && trimShare >= T.trimPartShare && darkFlat === false && f.fDark > 0.6 && !bodyish) { out.look = 'trim'; out.lookScore = 0.55; out.ev.push('dark art on bumper / spoiler parts'); out.conf = Math.max(out.conf, 0.6); }
        if (partNames.length) {
            const top = partNames.sort(function (a, b) { return parts[b] - parts[a]; }).filter(function (p) { return parts[p] >= 0.12; }).slice(0, 2);
            if (top.length) out.ev.push('on ' + top.join(' + '));
        }
        out.kind = out.look === 'metal' ? 'metal' : out.look === 'carbon' ? 'carbon' : out.look === 'trim' ? 'trim' : out.what;
        out.conf = Math.min(0.96, out.conf);      // an agreement score between name, size and pixels, not a probability: never claim certainty
        out.trimShare = trimShare;
        return out;
    }

    // ------------------------------------------------------------------ what material
    /** style 0 = Showroom (glossier, more chrome) ... 1 = Race-Worn (satin, matte, brushed, some grain). Returns {id, why}. */
    function pick(c, style, ctx) {
        ctx = ctx || {};
        const s = clamp01(style == null ? 0.3 : style), kind = c.kind || c.what;
        const race = s >= 0.5;
        if (kind === 'guide') return { id: 'zones', why: 'Template guide: it is switched off before export, so it carries no spec.' };
        if (kind === 'tiny') return { id: 'zones', why: 'Too few pixels to matter in the sim, so the zones keep it.' };
        if (kind === 'carbon') return { id: 'carbon', why: 'A fine woven texture on dark pixels: lacquered carbon reads as low metal, medium-low roughness, full clearcoat.' };
        if (kind === 'metal') {
            if (s < 0.45) return { id: 'chrome', why: 'Silver-grey gradient art reads as polished metal, so it becomes mirror chrome foil.' };
            if (s < 0.75) return { id: 'satin_chrome', why: 'Silver-grey gradient art, worn down: hazy satin chrome instead of a mirror.' };
            return { id: 'brushed', why: 'Silver-grey art on a hard-used car: brushed metal with a grain, not a mirror.' };
        }
        if (kind === 'trim') {
            const art = c.name !== 'trim' && (c.trimShare || 0) < T.trimPartShare && c.what && c.what !== 'other' && c.what !== 'body';   // black printed art, not a trim part
            if (!race) return { id: 'satin', why: art ? 'Near-black printed art: satin black vinyl, which separates it from the gloss paint.' : 'Near-black trim pieces are satin black on real cars, which separates them from the gloss paint.' };
            return { id: 'matte', why: art ? 'Near-black decals on a worn car: flat matte vinyl, no shine.' : 'Near-black trim on a worn car: flat matte, no shine.' };
        }
        if (kind === 'body') {
            if (ctx.zoneCustom) return { id: 'zones', why: 'Your zones already set a finish on the paint, so Autopilot leaves the body alone.' };
            if (s < 0.2) return { id: 'gel', why: 'Fresh showroom paint: a deep wet-look clearcoat with the sharpest reflections.' };
            if (s < 0.55) return { id: 'zones', why: 'The zones already give this paint a clean gloss clearcoat.' };
            return { id: 'satin', why: 'Race-worn paint: the clearcoat has dulled to satin and picks up fine roughness variation.' };
        }
        if (kind === 'numbers') {
            if (s < 0.2) return { id: 'gel', why: 'Showroom numbers: fresh vinyl under deep clear.' };
            if (s < 0.45) return { id: 'gloss', why: 'Numbers are gloss vinyl under the same clear as the paint.' };
            if (s < 0.72) return { id: 'satin', why: 'Race numbers: vinyl that has lost some shine, so satin.' };
            return { id: 'matte', why: 'Worn race numbers: dull matte vinyl.' };
        }
        if (kind === 'stripe') {
            if (s < 0.2) return { id: 'gel', why: 'Showroom stripes: fresh vinyl under deep clear.' };
            if (s < 0.45) return { id: 'gloss', why: 'Tape and stripes are gloss vinyl under the same clear as the paint.' };
            if (s < 0.72) return { id: 'satin', why: 'Tape that has aged in the sun: satin vinyl.' };
            return { id: 'matte', why: 'Worn tape: flat matte, no shine.' };
        }
        // sponsor / logo / decal / printed art
        if (s < 0.2) return { id: 'gel', why: 'Showroom decals: fresh vinyl under deep clear.' };
        if (s < 0.55) return { id: 'gloss', why: 'Printed decals are glossy vinyl, which keeps their colours sharp under the clear.' };
        if (s < 0.8) return { id: 'satin', why: 'Decals that have been through races: aged vinyl loses its shine, so satin.' };
        return { id: 'matte', why: 'Heavily worn decals: matte vinyl.' };
    }

    /** One call for a layer: classification + material + a plain-words row. */
    function analyze(f, meta, style, ctx) {
        const c = classify(f, meta), p = pick(c, style, ctx), mt = MAT[p.id];
        return {
            kind: c.kind || c.what, what: c.what, trimShare: c.trimShare || 0, name: c.name,
            kindLabel: (c.kind === 'trim' && c.name !== 'trim' && (c.trimShare || 0) < T.trimPartShare && c.what && c.what !== 'other') ? 'Near-Black Art' : (KINDS[c.kind || c.what] || 'Printed Art'), look: c.look, ev: c.ev, conf: c.conf,
            material: p.id, mat: mt, why: p.why, px: f ? f.px : 0, cov: f ? f.cov : 0
        };
    }

    return { VERSION: VERSION, MATERIALS: MATERIALS, MAT: MAT, KINDS: KINDS, T: T, features: features, periodicity: periodicity, carbonFor: carbonFor, nameKind: nameKind, classify: classify, pick: pick, analyze: analyze, clamp01: clamp01 };
});

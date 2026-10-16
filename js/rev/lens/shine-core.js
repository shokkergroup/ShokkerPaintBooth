/* ============================================================================
 * [SPB-REV-LENS 2026-10-10] SHINE CORE - pure data + shader source for the
 * Shine Lens (live PBR view of paint + spec) and Material Select.
 *
 * iRacing spec semantics (never change these):
 *   R = metallic 0..255, G = roughness (0 mirror .. 255 rough),
 *   B = clearcoat (0-15 none, 16 = max gloss .. 255 dull), A = spec mask
 *   (255 keeps reflections/specular, 0 kills them).
 * Material thresholds below were read from engine/base_registry_data.py on
 * 2026-10-10 (chrome M255 R2 CC16, candy M200 R15 CC16, gloss M0 R30 CC16,
 * satin M0 R95 CC70, matte M0 R200 CC160, flat_black M0 R250 CC255,
 * carbon_weave M70 R35 CC16, metallic M200 R50 CC16).
 *
 * View only: nothing here writes paint, spec, zones or files.
 * Kill switch: window.SPB_REV_LENS_OFF = true or localStorage SPB_REV_LENS_OFF='1'.
 * ==========================================================================*/
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBShineCore = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function killed() {
        try {
            if (typeof window !== 'undefined' && window.SPB_REV_LENS_OFF) return true;
            if (typeof localStorage !== 'undefined' && localStorage.getItem('SPB_REV_LENS_OFF') === '1') return true;
        } catch (_) { }
        return false;
    }

    // ------------------------------------------------------------ material model
    // Decode one spec texel the way the shader does (kept in lockstep with FRAG).
    function decode(m, g, b, a) {
        const metal = m / 255;
        const rough = g / 255;
        const alpha = Math.max(rough * rough, 0.0025);
        const ct = Math.max(0, Math.min(1, (b - 16) / 239));
        const coat = b >= 16 ? 1 - 0.7 * ct : 0;           // clearcoat strength (16 = full, 255 = 0.3)
        const coatRough = b >= 16 ? 0.03 + 0.5 * ct : 0;   // 16 = max gloss, 255 = dull
        return { metal, rough, alpha, coat, coatRough, mask: a / 255 };
    }

    // Plain-words name for a spec sample (panel readout). Order matters.
    function nameOf(m, g, b) {
        // same bounds as the fitted All Chrome preset (a chrome finish renders with a B 16+ clear on top)
        if (m >= 200 && g <= 40) return b >= 16 && b <= 120 ? 'Chrome / mirror metal (clear)' : 'Chrome / mirror metal';
        if (m >= 150 && g <= 30 && b >= 16 && b <= 40) return 'Candy / wet metallic';
        if (m >= 150 && g <= 80) return 'Metallic';
        if (m >= 150) return 'Satin / brushed metal';
        if (g >= 160 && (b < 16 || b >= 120)) return 'Matte';
        if (g >= 70 && g < 160) return 'Satin';
        if (b >= 16 && b <= 40 && g <= 60) return m >= 40 ? 'Gloss clear (carbon / pearl)' : 'Gloss clear';
        if (b < 16) return 'No clearcoat';
        return 'Semi-gloss';
    }

    // ------------------------------------------------------------ selection presets
    // Each returns true when a texel belongs. Thresholds documented in HOWTO.md.
    const PRESETS = {
        // fitted 2026-10-10 on the rendered specs of 5 real finishes (proof: rev_tools/lens/preset_fit.json):
        // passes 100% of chrome, 0% of satin / matte / candy, 25% of carbon_weave (its mirror threads).
        // The first guess (M >= 220, G <= 30) caught only 37% of the chrome finish.
        chrome: { label: 'All Chrome', test: (m, g) => m >= 200 && g <= 40, why: 'mirror metal: Metallic >= 200 and Roughness <= 40' },
        matte: { label: 'All Matte', test: (m, g, b) => g >= 160 && (b < 16 || b >= 120), why: 'Roughness >= 160 and a dull or no clearcoat (B >= 120 or B < 16)' },
        glossclear: { label: 'All Gloss Clear', test: (m, g, b) => b >= 16 && b <= 40, why: 'clearcoat at max gloss: B 16-40' },
        roughLt: { label: 'Roughness <', test: (m, g, b, a, n) => g < n, why: 'G below N' },
        metalGt: { label: 'Metallic >', test: (m, g, b, a, n) => m > n, why: 'R above N' },
    };

    // Coverage at spec resolution (Uint8 0/255) for a preset over RGBA bytes.
    function presetCoverage(spec, w, h, id, n) {
        const p = PRESETS[id];
        if (!p || !spec) return null;
        const out = new Uint8Array(w * h);
        let c = 0;
        for (let i = 0, o = 0; i < w * h; i++, o += 4) {
            if (p.test(spec[o], spec[o + 1], spec[o + 2], spec[o + 3], n)) { out[i] = 255; c++; }
        }
        return { cover: out, count: c };
    }

    // Same-material coverage: per-channel distance to the sample, max-norm over the
    // chosen channels. tol = hard core, fuzz = linear falloff (0..255 coverage).
    function sameCoverage(spec, w, h, sample, tol, fuzz, chans) {
        const out = new Uint8Array(w * h);
        const use = chans || [1, 1, 1, 0];
        const s = [sample.m, sample.r, sample.cc, sample.a];
        const t = Math.max(0, tol | 0), f = Math.max(0, fuzz | 0);
        let c = 0;
        for (let i = 0, o = 0; i < w * h; i++, o += 4) {
            let d = 0;
            for (let k = 0; k < 4; k++) {
                if (!use[k]) continue;
                const v = Math.abs(spec[o + k] - s[k]);
                if (v > d) d = v;
            }
            let cov;
            if (d <= t) cov = 255;
            else if (f > 0 && d < t + f) cov = Math.round(255 * (1 - (d - t) / f));
            else cov = 0;
            if (cov) { out[i] = cov; if (cov > 127) c++; }
        }
        return { cover: out, count: c };
    }

    // ---- Texture-aware "same material" (REV-LENS 2026-10-10) -------------------------------
    // A carbon weave, metal flake or candy is ONE material but thousands of different pixel
    // values (scene proof: carbon_weave M 103..245, G 15..85). Matching single pixels picks one
    // thread (IoU 0.0002 on the scene's carbon zone). So: compare LOCAL AVERAGES (box r px),
    // then win back the r-px boundary band with a raw-value envelope taken from the matched core.
    function boxAvg(spec, w, h, r) {
        const tmp = new Float32Array(w * h * 3), out = new Float32Array(w * h * 3);
        for (let y = 0; y < h; y++) {            // horizontal running sums
            for (let k = 0; k < 3; k++) {
                let s = 0, n = 0;
                for (let x = 0; x <= Math.min(r, w - 1); x++) { s += spec[(y * w + x) * 4 + k]; n++; }
                for (let x = 0; x < w; x++) {
                    tmp[(y * w + x) * 3 + k] = s / n;
                    const a = x + r + 1, b = x - r;
                    if (a < w) { s += spec[(y * w + a) * 4 + k]; n++; }
                    if (b >= 0) { s -= spec[(y * w + b) * 4 + k]; n--; }
                }
            }
        }
        for (let x = 0; x < w; x++) {            // vertical running sums
            for (let k = 0; k < 3; k++) {
                let s = 0, n = 0;
                for (let y = 0; y <= Math.min(r, h - 1); y++) { s += tmp[(y * w + x) * 3 + k]; n++; }
                for (let y = 0; y < h; y++) {
                    out[(y * w + x) * 3 + k] = s / n;
                    const a = y + r + 1, b = y - r;
                    if (a < h) { s += tmp[(a * w + x) * 3 + k]; n++; }
                    if (b >= 0) { s -= tmp[(b * w + x) * 3 + k]; n--; }
                }
            }
        }
        return out;
    }
    const avgCache = typeof WeakMap === 'function' ? new WeakMap() : null;
    function avgOf(spec, w, h, r) {
        const c = avgCache && avgCache.get(spec);
        if (c && c.r === r && c.w === w) return c.a;
        const a = boxAvg(spec, w, h, r);
        if (avgCache) avgCache.set(spec, { r, w, a });
        return a;
    }
    function avgSample(spec, w, h, x, y, r) {
        const A = avgOf(spec, w, h, r || 4), i = (y * w + x) * 3;
        return { m: Math.round(A[i]), r: Math.round(A[i + 1]), cc: Math.round(A[i + 2]), a: spec[(y * w + x) * 4 + 3], x, y };
    }
    function dilate(bin, w, h, r) {           // separable box max of a 0/1 map
        const t = new Uint8Array(w * h), o = new Uint8Array(w * h);
        for (let y = 0; y < h; y++) { let last = -1e9; for (let x = 0; x < w; x++) { if (bin[y * w + x]) last = x; if (x - last <= r) t[y * w + x] = 1; } last = 1e9; for (let x = w - 1; x >= 0; x--) { if (bin[y * w + x]) last = x; if (last - x <= r) t[y * w + x] = 1; } }
        for (let x = 0; x < w; x++) { let last = -1e9; for (let y = 0; y < h; y++) { if (t[y * w + x]) last = y; if (y - last <= r) o[y * w + x] = 1; } last = 1e9; for (let y = h - 1; y >= 0; y--) { if (t[y * w + x]) last = y; if (last - y <= r) o[y * w + x] = 1; } }
        return o;
    }
    function materialCoverage(spec, w, h, x, y, tol, fuzz, chans, r) {
        r = r || 4;
        const A = avgOf(spec, w, h, r), use = chans || [1, 1, 1, 0];
        const i0 = (y * w + x) * 3, s = [A[i0], A[i0 + 1], A[i0 + 2]], sa = spec[(y * w + x) * 4 + 3];
        const t = Math.max(0, tol | 0), f = Math.max(0, fuzz | 0), n = w * h;
        const out = new Uint8Array(n), core = new Uint8Array(n);
        const hist = [new Uint32Array(256), new Uint32Array(256), new Uint32Array(256), new Uint32Array(256)];
        let nc = 0;
        for (let i = 0; i < n; i++) {
            let d = 0;
            for (let k = 0; k < 3; k++) { if (!use[k]) continue; const v = Math.abs(A[i * 3 + k] - s[k]); if (v > d) d = v; }
            if (use[3]) { const v = Math.abs(spec[i * 4 + 3] - sa); if (v > d) d = v; }
            const cov = d <= t ? 255 : (f > 0 && d < t + f) ? Math.round(255 * (1 - (d - t) / f)) : 0;
            if (cov) out[i] = cov;
            if (cov > 127) { core[i] = 1; nc++; for (let k = 0; k < 4; k++) hist[k][spec[i * 4 + k]]++; }
        }
        if (!nc) return { cover: out, count: 0 };
        // raw envelope of the matched core: 1st..99th percentile per channel, widened by tol
        const lo = [0, 0, 0, 0], hi = [255, 255, 255, 255];
        for (let k = 0; k < 4; k++) {
            let acc = 0; const a = nc * 0.01, b = nc * 0.99; let gotLo = false;
            for (let v = 0; v < 256; v++) { acc += hist[k][v]; if (!gotLo && acc > a) { lo[k] = v - t; gotLo = true; } if (acc >= b) { hi[k] = v + t; break; } }
        }
        const band = dilate(core, w, h, r + 1);
        let c = 0;
        for (let i = 0; i < n; i++) {
            if (out[i] < 255 && band[i]) {
                let ok = true;
                for (let k = 0; k < 4 && ok; k++) { if (!use[k]) continue; const v = spec[i * 4 + k]; if (v < lo[k] || v > hi[k]) ok = false; }
                if (ok) out[i] = 255;
            }
            if (out[i] > 127) c++;
        }
        return { cover: out, count: c, core: nc, envelope: { lo, hi } };
    }

    // 4-connected flood from (x,y) over a coverage map (keeps only the clicked island).
    function keepConnected(cover, w, h, x, y) {
        const start = y * w + x;
        const out = new Uint8Array(w * h);
        if (!cover[start]) {
            // nearest covered seed within 4 px (click landed on a 1 px seam)
            let best = -1;
            for (let r = 1; r <= 4 && best < 0; r++) {
                for (let dy = -r; dy <= r && best < 0; dy++) for (let dx = -r; dx <= r; dx++) {
                    const xx = x + dx, yy = y + dy;
                    if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
                    if (cover[yy * w + xx]) { best = yy * w + xx; break; }
                }
            }
            if (best < 0) return { cover: out, count: 0 };
            return keepConnected(cover, w, h, best % w, (best / w) | 0);
        }
        const q = new Int32Array(w * h);
        let head = 0, tail = 0, c = 0;
        q[tail++] = start; out[start] = cover[start];
        while (head < tail) {
            const i = q[head++];
            if (out[i] > 127) c++;
            const px = i % w;
            const nb = [px > 0 ? i - 1 : -1, px + 1 < w ? i + 1 : -1, i - w, i + w];
            for (let k = 0; k < 4; k++) {
                const j = nb[k];
                if (j < 0 || j >= w * h || out[j] || !cover[j]) continue;
                out[j] = cover[j]; q[tail++] = j;
            }
        }
        return { cover: out, count: c };
    }

    // Bilinear upscale of a coverage map (spec res -> canvas res) so a 1024 preview
    // spec gives smooth 2048 selection edges instead of 2 px stairs.
    function upscale(cover, sw, sh, tw, th) {
        if (sw === tw && sh === th) return new Uint8Array(cover);
        const out = new Uint8Array(tw * th);
        const fx = sw / tw, fy = sh / th;
        for (let y = 0; y < th; y++) {
            let sy = (y + 0.5) * fy - 0.5; if (sy < 0) sy = 0;
            const y0 = Math.min(sh - 1, sy | 0), y1 = Math.min(sh - 1, y0 + 1), wy = sy - y0;
            const r0 = y0 * sw, r1 = y1 * sw, ro = y * tw;
            for (let x = 0; x < tw; x++) {
                let sx = (x + 0.5) * fx - 0.5; if (sx < 0) sx = 0;
                const x0 = Math.min(sw - 1, sx | 0), x1 = Math.min(sw - 1, x0 + 1), wx = sx - x0;
                const a = cover[r0 + x0] + (cover[r0 + x1] - cover[r0 + x0]) * wx;
                const b = cover[r1 + x0] + (cover[r1 + x1] - cover[r1 + x0]) * wx;
                out[ro + x] = (a + (b - a) * wy + 0.5) | 0;
            }
        }
        return out;
    }

    function iou(a, b, thr) {
        const t = thr == null ? 127 : thr;
        let i = 0, u = 0;
        for (let k = 0; k < a.length; k++) {
            const x = a[k] > t, y = b[k] > t;
            if (x && y) i++;
            if (x || y) u++;
        }
        return u ? i / u : 1;
    }

    // ------------------------------------------------------------ shaders
    const VERT = `#version 300 es
in vec2 aPos;
out vec2 vLocal;
void main(){ vLocal = vec2(aPos.x*0.5+0.5, 0.5-aPos.y*0.5); gl_Position = vec4(aPos,0.0,1.0); }`;

    // Flat 2048 UV sheet seen from a camera above it, gently convex so the studio
    // reflections sweep across panels. Studio env: 3 overhead softbox strips,
    // horizon glow, sky/ground, plus a movable key light (GGX). Env blur is an
    // analytic box (*) gaussian convolution whose width follows GGX alpha, so
    // narrow strips blur into wide dim glows (energy kept), mirror stays sharp.
    const FRAG = `#version 300 es
precision highp float;
uniform sampler2D uPaint;
uniform sampler2D uSpec;
uniform sampler2D uSel;
uniform vec4 uUvRect;
uniform vec2 uSize;
uniform vec3 uLight;
uniform float uEnvRot;
uniform vec3 uCircle;
uniform float uSelOn;
uniform float uExposure;
uniform float uCurv;
uniform float uRing;
in vec2 vLocal;
out vec4 o;
const float PI = 3.14159265;
float erfa(float x){ return tanh(1.202760580 * x * (1.0 + 0.0891 * x * x)); }
// box of half-width w at c, convolved with a gaussian of width s
float band(float x, float c, float w, float s){ float k = 0.70710678 / max(s, 1e-4); return 0.5 * (erfa((x - c + w) * k) - erfa((x - c - w) * k)); }
vec3 env(vec3 d, float a){
  float ca = cos(uEnvRot), sa = sin(uEnvRot);
  vec3 r = vec3(ca * d.x - sa * d.y, sa * d.x + ca * d.y, d.z);
  float s = 0.02 + 1.45 * a;
  float el = asin(clamp(r.z, -1.0, 1.0));
  vec3 col = mix(vec3(0.022, 0.022, 0.025), vec3(0.11, 0.12, 0.14), smoothstep(-0.10 - s, 0.25 + s, el));
  col += vec3(1.25, 1.15, 1.0) * band(el, 0.03, 0.03, 0.5 * s + 0.004);
  if (r.z > 0.02) {
    float sx = r.x / r.z, sy = r.y / r.z;
    float ss = s * (1.0 + 0.5 * (sx * sx + sy * sy));
    float len = band(sy, 0.0, 1.4, ss);
    float strips = band(sx, -1.2, 0.028, ss) + band(sx, -0.6, 0.028, ss) + band(sx, 0.0, 0.036, ss) * 1.2 + band(sx, 0.6, 0.028, ss) + band(sx, 1.2, 0.028, ss);
    col += vec3(6.0, 6.0, 6.2) * strips * len * smoothstep(0.02, 0.15, r.z);
    col += vec3(0.22, 0.23, 0.25) * band(sx, 0.0, 0.9, ss) * band(sy, 0.0, 0.9, ss);
  }
  return col;
}
vec3 envBRDF(vec3 f0, float rough, float nv){
  const vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022);
  const vec4 c1 = vec4(1.0, 0.0425, 1.04, -0.04);
  vec4 r = rough * c0 + c1;
  float a004 = min(r.x * r.x, exp2(-9.28 * nv)) * r.x + r.y;
  vec2 ab = vec2(-1.04, 1.04) * a004 + r.zw;
  return f0 * ab.x + ab.y;
}
float ggx(float nh, float a){ float a2 = a * a; float d = nh * nh * (a2 - 1.0) + 1.0; return a2 / (PI * d * d); }
float vis(float nv, float nl, float a){ float k = a * 0.5; return 0.25 / ((nv * (1.0 - k) + k) * (nl * (1.0 - k) + k)); }
vec3 aces(vec3 x){ return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
void main(){
  vec2 px = vec2(vLocal.x * uSize.x, vLocal.y * uSize.y);
  float edge = 1.0;
  if (uCircle.z > 0.0) {
    float dd = length(px - uCircle.xy);
    if (dd > uCircle.z + 0.5) {
      // soft drop halo outside the lens (width follows the ring thickness, i.e. the device pixel ratio)
      float hw = 7.0 * max(uRing, 1.0);
      float h = 1.0 - clamp((dd - uCircle.z - 0.5) / hw, 0.0, 1.0);
      if (uRing <= 0.0 || h <= 0.0) discard;
      o = vec4(0.0, 0.0, 0.0, 0.42 * h * h); return;
    }
    edge = clamp(uCircle.z + 0.5 - dd, 0.0, 1.0);
  }
  vec2 uv = uUvRect.xy + vLocal * uUvRect.zw;
  if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) { o = vec4(vec3(0.07, 0.07, 0.08) * edge, edge); return; }
  vec3 albedo = pow(texture(uPaint, uv).rgb, vec3(2.2));
  vec4 sp = texture(uSpec, uv) * 255.0;
  float metal = sp.r / 255.0;
  float rough = sp.g / 255.0;
  float a = max(rough * rough, 0.0025);
  float ct = clamp((sp.b - 16.0) / 239.0, 0.0, 1.0);
  float coat = sp.b >= 15.5 ? 1.0 - 0.7 * ct : 0.0;
  float cr = 0.03 + 0.5 * ct;
  float ca = max(cr * cr, 0.0012);
  float mask = sp.a / 255.0;
  vec3 P = vec3(uv.x - 0.5, 0.5 - uv.y, 0.0);
  vec3 N = normalize(vec3(P.xy * uCurv, 1.0));
  vec3 V = normalize(vec3(0.0, 0.0, 1.15) - P);
  float nv = max(dot(N, V), 1e-3);
  vec3 R = reflect(-V, N);
  vec3 L = normalize(uLight);
  vec3 H = normalize(L + V);
  float nl = max(dot(N, L), 0.0), nh = max(dot(N, H), 0.0), vh = max(dot(V, H), 0.0);
  vec3 f0 = mix(vec3(0.04), albedo, metal);
  vec3 Fk = f0 + (1.0 - f0) * pow(1.0 - vh, 5.0);
  vec3 keyRad = vec3(2.6, 2.5, 2.35);
  vec3 spec = env(R, a) * envBRDF(f0, rough, nv) + ggx(nh, a) * vis(nv, nl, a) * Fk * nl * keyRad;
  vec3 diff = albedo * (1.0 - metal) * (vec3(0.30, 0.31, 0.33) + nl * keyRad * (1.0 - Fk) / PI);
  vec3 col = diff + spec * mask;
  if (coat > 0.0) {
    float Fc = (0.04 + 0.96 * pow(1.0 - nv, 5.0)) * coat;
    vec3 cspec = env(R, ca) * envBRDF(vec3(0.04), cr, nv) + ggx(nh, ca) * vis(nv, nl, ca) * (0.04 + 0.96 * pow(1.0 - vh, 5.0)) * nl * keyRad;
    col = col * (1.0 - Fc) + cspec * coat * mask;
  }
  col = aces(col * uExposure);
  col = pow(col, vec3(1.0 / 2.2));
  if (uSelOn > 0.5) {
    float s = texture(uSel, uv).r;
    float l = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(l * 0.32), col, 0.12 + 0.88 * s);
  }
  if (uRing > 0.0 && uCircle.z > 0.0) {
    float dd = length(px - uCircle.xy);
    float ring = smoothstep(uRing + 1.0, uRing, abs(dd - (uCircle.z - uRing)));
    col = mix(col, vec3(0.92, 0.95, 0.97), ring * 0.85);
  }
  o = vec4(col * edge, edge);
}`;

    return {
        version: 'rev-lens-2026-10-10a',
        killed, decode, nameOf, PRESETS, presetCoverage, sameCoverage, materialCoverage, avgSample, keepConnected, upscale, iou,
        VERT, FRAG,
    };
});

/* Material Map v2 — ACCURACY pass (2026-07-04). LIVE core (2026-07-04 gauntlet swap) of
 * paint-booth-materialmap.js: same public API (computeMaterialMap(rgba, w, h, opts) ->
 * { grid, regions:[{row,col,bbox,archetype,label,preset,reason,color,score,features}], legend },
 * plus ARCHETYPES), same global (SPB_MaterialMap), same module.exports.
 *
 * WHY v2 — concrete inaccuracies in v1 (paint-booth-materialmap.js):
 *   1. NEAR-BLACK SATURATION EXPLOSION (v1 line 44): HSV sat=(mx-mn)/mx blows up to ~1.0 on
 *      near-black pixels (RGB 4,0,0 -> sat=1), so dark panels with faint color noise scored
 *      candy/flake instead of matte. Mirrors the engine truth that gloss verdicts need REAL
 *      albedo (cf. flash needing M+smoothness AND visible paint): v2 stabilizes sat with a
 *      value floor and gates every chromatic archetype by mean chroma (chromaOk).
 *   2. "hue_spread" WAS CHROMA STD, NOT HUE DIVERSITY (v1 lines 49-52): std(mx-mn) is high for
 *      any SINGLE-hue paint whose saturation/luminance flows (i.e., the candy_flow look itself!),
 *      so flowing candy classified HOLO (holo weight x8). v2 measures true multi-hue via
 *      chroma-weighted CIRCULAR hue statistics (1 - |mean hue vector|): rainbow ~1, one-hue ~0.
 *   3. EDGE SCALE 2x OFF vs THE VERIFIED PYTHON (v1 lines 55-58 vs auto_sculpt_suggest.py:43-44):
 *      Python uses np.gradient (central differences, /2); v1 used forward diffs (no /2), so JS
 *      edge ~= 2x Python for identical paint and edgey=min(1,edge*30) saturated twice as early ->
 *      carbon(x1.6)/flake over-trigger in the booth relative to the tuned Python weights.
 *      v2 uses central differences (np.gradient scale).
 *   4. ALPHA IGNORED (v1 lines 37-45): transparent/void UV-layout pixels averaged in as black,
 *      skewing tiles dark+desaturated (phantom Matte). v2 weights by alpha (a>=8) and skips
 *      tiles with <3% opaque coverage.
 *   5. BRUSHED NEEDED NO DIRECTIONAL EVIDENCE (v1 line 76): any smooth neutral mid-tone scored
 *      Brushed (or even Chrome), but brushed metal is DIRECTIONAL (material_profiles.py
 *      "Brushed & machined": texture="brushed"). v2 requires structure-tensor coherence, and adds
 *      the missing SATIN archetype (preset gunmetal_satin, presets.py:90) for smooth neutral
 *      mid-tone with NO streaks — the satin-vs-brushed/pearl confusion case.
 *   6. FLAKE = ANY SATURATED EDGES (v1 line 79): sparse strong graphic edges (decal borders,
 *      stripes) scored flake; real flake is DENSE fine ISOTROPIC speckle (material_profiles.py
 *      "Flake & interference": texture="flake", tex_amp=0.92). v2 uses texture DENSITY
 *      (fraction of pixels with micro-gradient) x isotropy, not mean gradient magnitude.
 *   7. CHROME = ANY BRIGHT NEUTRAL (v1 line 75): flat matte-white and satin grays read Chrome.
 *      Mirror-chrome art carries a broad smooth reflection ramp; v2 boosts chrome with luma-std
 *      ("smoothRamp") and damps it on textured tiles, while satin absorbs the flat mid-grays.
 *   8. MATTE IGNORED TEXTURE (v1 line 73): matte is dark + desaturated + FLAT
 *      (material_profiles.py "Matte & velvet": r_base=232, texture="micrograin", tex_amp=0.05);
 *      v2 adds the flatness term so dark woven/speckled tiles fall to carbon/flake correctly.
 *
 * Channel truth used for the archetype->preset targets (shokker_engine_v2.py:24-28):
 *   spec R = Metallic (0 dielectric .. 255 mirror), G = Roughness (0 mirror-smooth .. 255 matte),
 *   B = Clearcoat (16 = MAX gloss, 16..255 progressively duller, 0-15 = none — counter-intuitive).
 * Still a SUGGESTION heuristic on the PAINT (never spec authoring, never touches SHOKK DROP).
 */
(function (global) {
  function clamp01(x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }

  // archetype -> { display label, an existing Spec-Sculpt preset id, overlay tint, short reason }
  // All preset ids verified present in engine/spec_sculpt/presets.py.
  var ARCH = {
    matte:   { label: 'Matte',   preset: 'frozen_matte',     color: [70, 72, 84],    reason: 'dark + desaturated + flat' },
    satin:   { label: 'Satin',   preset: 'gunmetal_satin',   color: [190, 186, 178], reason: 'neutral mid-tone + smooth, no streaks' },
    carbon:  { label: 'Carbon',  preset: 'carbon_fiber',     color: [38, 40, 50],    reason: 'dark neutral + dense weave texture' },
    chrome:  { label: 'Chrome',  preset: 'mirror_chrome',    color: [200, 212, 230], reason: 'neutral + bright + reflection ramp' },
    brushed: { label: 'Brushed', preset: 'brushed_titanium', color: [150, 156, 168], reason: 'neutral + directional streaks' },
    candy:   { label: 'Candy',   preset: 'candy_flow',       color: [232, 44, 92],   reason: 'one vivid hue + real chroma' },
    pearl:   { label: 'Pearl',   preset: 'circle_pearl',     color: [226, 184, 236], reason: 'bright soft pastel (mid-sat)' },
    flake:   { label: 'Flake',   preset: 'metal_flake',      color: [255, 162, 44],  reason: 'dense isotropic speckle' },
    holo:    { label: 'Holo',    preset: 'holographic',      color: [120, 232, 200], reason: 'vivid + many hues (diffraction)' },
  };

  var TWO_PI_OVER_6 = Math.PI / 3; // 60 deg per HSV hue sextant, in radians

  // Per-region features v2: alpha-aware, black-stable saturation, circular hue spread,
  // np.gradient-scale edges, texture density + structure-tensor coherence.
  function regionFeatures(rgba, w, x0, y0, x1, y1) {
    var rw = x1 - x0, rh = y1 - y0;
    if (rw <= 1 || rh <= 1) return null;
    var n = rw * rh;
    var lum = new Float32Array(n);
    var op = new Uint8Array(n); // 1 = opaque enough to count
    var sumL = 0, sumL2 = 0, sumS = 0, sumC = 0, hx = 0, hy = 0, sumCw = 0, cnt = 0;
    for (var y = y0; y < y1; y++) {
      for (var x = x0; x < x1; x++) {
        var p = (y - y0) * rw + (x - x0);
        var i = (y * w + x) * 4;
        var r = rgba[i] / 255, g = rgba[i + 1] / 255, b = rgba[i + 2] / 255;
        var l = 0.299 * r + 0.587 * g + 0.114 * b;
        lum[p] = l;
        if (rgba[i + 3] < 8) continue; // FIX #4: void/transparent UV pixels don't vote
        op[p] = 1; cnt++;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), c = mx - mn;
        sumL += l; sumL2 += l * l;
        sumS += c / Math.max(mx, 0.15); // FIX #1: value-floored saturation (black-stable)
        sumC += c;
        if (c > 1e-4) { // FIX #2: true hue, chroma-weighted circular stats
          var hd;
          if (mx === r) hd = ((g - b) / c) % 6;
          else if (mx === g) hd = (b - r) / c + 2;
          else hd = (r - g) / c + 4;
          var th = hd * TWO_PI_OVER_6;
          hx += c * Math.cos(th); hy += c * Math.sin(th); sumCw += c;
        }
      }
    }
    if (cnt < Math.max(4, n * 0.03)) return null; // FIX #4: skip near-empty tiles
    var luma = sumL / cnt;
    var lumaStd = Math.sqrt(Math.max(0, sumL2 / cnt - luma * luma));
    var sat = sumS / cnt, chroma = sumC / cnt;
    // 0 = single hue, ->1 = hues spread all around the wheel (rainbow/diffraction)
    var hue = sumCw > 1e-4 ? (1 - Math.sqrt(hx * hx + hy * hy) / sumCw) : 0;

    // FIX #3: central differences (np.gradient scale). FIX #5/#6: tensor + texture density.
    var eSum = 0, eCnt = 0, tex = 0, Exx = 0, Eyy = 0, Exy = 0;
    for (var yy = 1; yy < rh - 1; yy++) {
      for (var xx = 1; xx < rw - 1; xx++) {
        var idx = yy * rw + xx;
        if (!op[idx] || !op[idx - 1] || !op[idx + 1] || !op[idx - rw] || !op[idx + rw]) continue;
        var gx = (lum[idx + 1] - lum[idx - 1]) * 0.5;
        var gy = (lum[idx + rw] - lum[idx - rw]) * 0.5;
        var gm = Math.abs(gx) + Math.abs(gy);
        eSum += gm; eCnt++;
        if (gm > 0.035) tex++; // above downsample/noise floor => real surface texture
        Exx += gx * gx; Eyy += gy * gy; Exy += gx * gy;
      }
    }
    var edge = eCnt ? eSum / eCnt : 0;
    var texDensity = eCnt ? tex / eCnt : 0;
    var tr = Exx + Eyy;
    // 1 = one dominant gradient direction (brushed streaks), 0 = isotropic (flake/speckle)
    var coherence = tr > 1e-9 ? Math.sqrt((Exx - Eyy) * (Exx - Eyy) + 4 * Exy * Exy) / tr : 0;

    return {
      // v1-compatible keys (same names, better estimates):
      luma: luma, saturation: sat, edge_density: edge, hue_spread: hue,
      // v2 additions:
      chroma: chroma, luma_std: lumaStd, tex_density: texDensity,
      coherence: coherence, opaque_frac: cnt / n,
    };
  }

  // Archetype scores v2 — each material requires the feature COMBINATION that defines it
  // (mirrors the per-family baselines in engine/spec_sculpt/material_profiles.py).
  function scoreArchetypes(f) {
    var luma = f.luma, sat = f.saturation, chroma = f.chroma, hue = f.hue_spread;
    var lumaStd = f.luma_std, edge = f.edge_density, coh = f.coherence;

    var bright     = clamp01((luma - 0.40) / 0.35);
    var dark       = clamp01((0.45 - luma) / 0.35);
    var midTone    = 1 - clamp01(Math.abs(luma - 0.5) * 2.2);
    var neutral    = 1 - clamp01(sat / 0.18);
    var vivid      = clamp01((sat - 0.10) / 0.55);
    var chromaOk   = clamp01(chroma / 0.10);        // FIX #1: near-black albedo can't sell color
    var smoothRamp = clamp01(lumaStd / 0.10);       // broad reflection-style ramp (chrome art)
    // continuous micro-texture energy (edge is np.gradient-scale; 0.008 = downsample noise floor)
    var textured   = clamp01((edge - 0.008) / 0.035);
    var flat       = 1 - textured;                  // no surface texture
    var isotropic  = 1 - clamp01((coh - 0.35) / 0.45);
    // FIX #5: brushed needs streak evidence = one dominant gradient direction WITH real edge
    // energy, and NOT just one broad reflection ramp (that is chrome, not hairline brushing).
    var directional = clamp01((coh - 0.45) / 0.40) * clamp01(edge * 80) * (1 - 0.75 * smoothRamp);
    var singleHue  = 1 - clamp01(hue * 2.0);
    var multiHue   = clamp01((hue - 0.18) / 0.40);  // FIX #2: holo = many hues, not chroma std

    var satBand = clamp01((sat - 0.06) / 0.06) * (1 - clamp01((sat - 0.40) / 0.25)); // pastel band

    return {
      // dark + desaturated + FLAT (matte micrograin is near-invisible at booth res) — FIX #8
      matte:   dark * (1 - sat) * (0.35 + 0.65 * flat) * 1.35,
      // NEW: smooth neutral mid-tone, no streaks, no big ramp — the satin decal case — FIX #5
      satin:   neutral * midTone * flat * (1 - 0.6 * smoothRamp) * (1 - 0.75 * directional) * 1.15,
      // dark-to-mid neutral + dense weave texture (not brightness-agnostic edges)
      carbon:  neutral * (0.30 + 0.70 * (1 - bright)) * textured * (0.5 + 0.5 * isotropic) * 1.45,
      // bright neutral, boosted by a smooth reflection ramp, damped by micro-texture — FIX #7
      chrome:  neutral * bright * (0.50 + 0.50 * smoothRamp) * (1 - 0.6 * textured) * 1.35,
      // neutral + REQUIRED directional streak evidence (structure-tensor coherence) — FIX #5
      brushed: neutral * (0.35 + 0.65 * midTone) * directional * 1.7,
      // one vivid hue with real chroma; still saturation-driven (deep candy stays dark) — v1.1 kept
      candy:   Math.pow(sat, 1.2) * (0.55 + 0.45 * luma) * (0.45 + 0.55 * singleHue) * chromaOk * 1.5,
      // bright soft pastel: mid-sat band + brightness + softness (not just sat*(1-sat))
      pearl:   satBand * clamp01((luma - 0.50) / 0.25) * (0.45 + 0.55 * flat) * chromaOk * 1.2,
      // dense fine ISOTROPIC speckle; silver flake allowed (brightness can stand in for chroma) — FIX #6
      flake:   textured * (0.5 + 0.5 * isotropic) * (0.40 + 0.60 * Math.max(vivid, bright * 0.7)) * 1.3,
      // vivid + genuinely multi-hue — FIX #2
      holo:    vivid * multiHue * (0.55 + 0.45 * bright) * chromaOk * 1.9,
    };
  }

  /** rgba: Uint8(Clamped)Array RGBA of the PAINT (not the spec). Returns
   *  { grid, regions:[{row,col,bbox,archetype,label,preset,reason,color,score,features}], legend }. */
  function computeMaterialMap(rgba, w, h, opts) {
    opts = opts || {};
    var grid = Math.max(1, Math.floor(opts.grid || 4));
    var gh = Math.max(1, Math.floor(h / grid)), gw = Math.max(1, Math.floor(w / grid));
    var regions = [], tally = {};
    for (var r = 0; r < grid; r++) {
      for (var c = 0; c < grid; c++) {
        var y0 = r * gh, y1 = (r === grid - 1) ? h : (r + 1) * gh;
        var x0 = c * gw, x1 = (c === grid - 1) ? w : (c + 1) * gw;
        var f = regionFeatures(rgba, w, x0, y0, x1, y1);
        if (!f) continue;
        var sc = scoreArchetypes(f);
        var best = null, bestv = -1;
        for (var a in sc) { if (sc[a] > bestv) { bestv = sc[a]; best = a; } }
        var meta = ARCH[best];
        regions.push({
          row: r, col: c, bbox: [x0, y0, x1, y1], archetype: best,
          label: meta.label, preset: meta.preset, reason: meta.reason,
          color: meta.color, score: bestv, features: f,
        });
        tally[best] = (tally[best] || 0) + 1;
      }
    }
    var legend = Object.keys(tally).map(function (k) {
      return { archetype: k, label: ARCH[k].label, color: ARCH[k].color, count: tally[k] };
    });
    legend.sort(function (p, q) { return q.count - p.count; });
    return { grid: grid, regions: regions, legend: legend };
  }

  var api = { computeMaterialMap: computeMaterialMap, ARCHETYPES: ARCH };
  global.SPB_MaterialMap = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Flash Map IMPROVED core (2026-07-04, LIVE core — swapped in from the 2026-07-04 gauntlet after validation) — accuracy rebuild of
 * paint-booth-flashmap.js:computeFlashMap. Same public API: SPB_FlashMap.{computeFlashMap, heat,
 * clearcoatStrength}, same computeFlashMap(spec, w, h, opts) signature and return shape
 * { heat, coveragePct, deadPct, hotPct }.
 *
 * WHY the old model was inaccurate (each grounded in the engine's own physics — the Cook-Torrance
 * GGX reference in engine/spec_sculpt/sun_sweep.py:89-125 and the channel semantics in
 * shokker_engine_v2.py:20-37):
 *
 *  1. ADDITIVE potential (old line 38: 0.50*(1-R) + 0.32*M + 0.18*Cc) ignores channel
 *     interaction. Flash needs smoothness AND reflectivity TOGETHER (GGX: spec = D*G*F — a
 *     product). Old model: rough-as-sandpaper metal (M=255,R=255) still scores 0.32 and can be
 *     pushed to "pops" by contrast; it never flashes in iRacing (GGX D peak at rough=1 is 1/pi
 *     vs ~7.8e4 at rough=0.045 — five orders of magnitude).
 *  2. CONTRAST GATE crushes uniform chrome to DEAD (old line 58: pot*(0.10+1.5*contrast)).
 *     A uniform mirror panel (M=255,R=0,Cc=16) got flash=0.10 < deadThreshold 0.12 => "dead".
 *     Pure chrome is the flashiest thing you can put on a car. Contrast (flake/pin twinkle)
 *     should BOOST, never gate the physical potential to zero.
 *  3. LINEAR smoothness credit: satin (G~120) got 53% of chrome's smoothness term. GGX peak
 *     intensity is ~1/(pi*rough^4): satin's sharp-flash ability is orders of magnitude below
 *     gloss. We use a log-compressed GGX peak so the scale is perceptual but ordered correctly.
 *  4. NO ALBEDO interaction. Engine: F0 = (1-M)*0.04 + M*albedo (sun_sweep.py:112) — metals
 *     reflect their own color. Near-black metallic reads dark head-on but STILL flashes white
 *     at grazing (Schlick F->1; this is the documented Ghost Shift / FRACTURED SOULS mechanism),
 *     so albedo scales the metal term with a grazing floor rather than killing it. Optional
 *     opts.paint (RGBA, same size) supplies albedo; without it a neutral 0.5 is assumed
 *     (backward compatible — the booth calls with opts={}).
 *  5. SPEC MASK (A) ignored: engine defines spec[...,3]=A, 255=active / 0=transparent
 *     (shokker_engine_v2.py:28). Old core scored transparent pixels at full potential. Also
 *     all-zero (M=0,G=0,B=0) pixels are empty/illegal per iron rule 2 (roughness floor 15 when
 *     M<240) — that's background in the booth's spec preview PNG; old model scored that
 *     "smooth dielectric" at pot=0.50. Both are now inactive.
 *  6. MASK LEAK: masked-out pixels still contributed to their neighbors' contrast windows
 *     (old lines 46-53 iterate the window with no mask check), inflating heat along mask
 *     borders. Window stats now only include active pixels.
 *
 * MODEL (per pixel, all 0..1):
 *   gloss  = ln(1 + 1/(pi*max(G/255,0.045)^4)) / ln(1 + 1/(pi*0.045^4))   // log GGX peak
 *   F0     = 0.04*(1-m) + m*albedoLum                                     // engine line 112
 *   refl   = F0 + (1-F0)*(0.20 + 0.45*m)   // grazing Fresnel lift: Schlick F->1 at grazing
 *                                          // for ANY F0; curved car panels at speed spend a
 *                                          // big angle share near grazing, and metals carry
 *                                          // it visibly (Ghost Shift / SOULS mechanism)
 *   sheen  = 0.18*(1-max(G/255,0.045))*refl                               // broad soft highlight
 *   ccLobe = 0.22 * clearcoatStrength(B)      // sharp albedo-independent secondary lobe
 *                                             // (sun_sweep.py:115-119, acc=0.06^2, F0=0.04)
 *   pot    = clamp01(gloss*refl + sheen + ccLobe)
 *   flash  = clamp01(pot * (0.65 + 0.85*contrast))   // contrast boosts, never gates
 *
 * Recalibrated default thresholds for the new scale: dead<0.045, hot>=0.55, coverage>=0.25.
 */
(function (global) {
  function clamp01(x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }

  // Cc channel: 16 = max clearcoat .. 255 = dull, 0 = none. Kept byte-identical to the old
  // export (and to engine/spec_sculpt/sun_sweep.py:53-57) for API compatibility. Note: B in
  // 1..15 is the illegal GGX-whitewash band (iron rule 1) — it genuinely blows out bright
  // in-sim, so treating it as ~max clearcoat is the honest flash prediction.
  function clearcoatStrength(cc) { return cc < 1 ? 0 : clamp01((255 - cc) / (255 - 16)); }

  // cold-blue -> cyan -> amber -> hot-red ramp (unchanged)
  var HEAT_STOPS = [[24, 48, 130], [24, 168, 205], [235, 200, 45], [235, 45, 32]];
  function heat(t) {
    t = clamp01(t);
    var s = t * (HEAT_STOPS.length - 1), i = Math.min(HEAT_STOPS.length - 2, Math.floor(s)), f = s - i;
    var a = HEAT_STOPS[i], b = HEAT_STOPS[i + 1];
    return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
  }

  var R_MIN = 0.045; // engine clamps roughness here in the GGX (sun_sweep.py:95)
  var GLOSS_LN_MAX = Math.log(1 + 1 / (Math.PI * Math.pow(R_MIN, 4)));

  /** Physical flash potential of one pixel. albedoLum in 0..1 or null (-> neutral 0.5). */
  function flashPotential(M, G, B, albedoLum) {
    var m = M / 255;
    var r01 = G / 255; if (r01 < R_MIN) r01 = R_MIN;
    var a2 = r01 * r01 * r01 * r01;                       // GGX alpha^2 with alpha = rough^2
    var gloss = Math.log(1 + 1 / (Math.PI * a2)) / GLOSS_LN_MAX;
    var lum = (albedoLum == null) ? 0.5 : albedoLum;
    var F0 = 0.04 * (1 - m) + m * lum;                    // metals reflect their own color
    var refl = F0 + (1 - F0) * (0.20 + 0.45 * m);         // grazing-angle Fresnel lift
    var sheen = 0.18 * (1 - r01) * refl;                  // broad-lobe "life" (satin sheen)
    var ccLobe = 0.22 * clearcoatStrength(B);             // sharp lobe, albedo-independent
    return clamp01(gloss * refl + sheen + ccLobe);
  }

  /** spec: Uint8(Clamped)Array RGBA (R=Metallic,G=Roughness,B=Clearcoat,A=SpecMask). Returns
   *  { heat: Uint8ClampedArray RGBA overlay, coveragePct, deadPct, hotPct }.
   *  opts: window, deadThreshold, hotThreshold, coverageThreshold, mask (as before) +
   *        paint: optional Uint8(Clamped)Array RGBA albedo, same w*h (metal tint accuracy). */
  function computeFlashMap(spec, w, h, opts) {
    opts = opts || {};
    var win = opts.window != null ? opts.window : 2;       // radius (2 -> 5x5)
    var deadT = opts.deadThreshold != null ? opts.deadThreshold : 0.045;
    var hotT = opts.hotThreshold != null ? opts.hotThreshold : 0.55;
    var covT = opts.coverageThreshold != null ? opts.coverageThreshold : 0.25;
    var maskOn = opts.mask || null;                        // optional Uint8 length w*h (0 = ignore)
    var paint = opts.paint || null;                        // optional RGBA albedo
    var n = w * h;
    var pot = new Float32Array(n);
    var active = new Uint8Array(n);
    for (var i = 0; i < n; i++) {
      var M = spec[i * 4], G = spec[i * 4 + 1], B = spec[i * 4 + 2], A = spec[i * 4 + 3];
      // inactive: external mask, transparent spec mask, or empty/illegal all-zero pixel
      // (background of the spec preview — iron rule 2 forbids G<15 when M<240 on real paint)
      if ((maskOn && maskOn[i] === 0) || A < 8 || (M === 0 && G === 0 && B === 0)) {
        active[i] = 0; pot[i] = 0; continue;
      }
      active[i] = 1;
      var lum = null;
      if (paint) {
        lum = (0.299 * paint[i * 4] + 0.587 * paint[i * 4 + 1] + 0.114 * paint[i * 4 + 2]) / 255;
      }
      pot[i] = flashPotential(M, G, B, lum);
    }
    var heatRGBA = new Uint8ClampedArray(n * 4);
    var cov = 0, dead = 0, hot = 0, counted = 0;
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var idx = y * w + x;
        if (!active[idx]) { heatRGBA[idx * 4 + 3] = 0; continue; }
        var sum = 0, sum2 = 0, cnt = 0;
        for (var dy = -win; dy <= win; dy++) {
          var yy = y + dy; if (yy < 0 || yy >= h) continue;
          for (var dx = -win; dx <= win; dx++) {
            var xx = x + dx; if (xx < 0 || xx >= w) continue;
            var j = yy * w + xx; if (!active[j]) continue;   // no mask leak into the window
            var p = pot[j]; sum += p; sum2 += p * p; cnt++;
          }
        }
        var mean = sum / cnt, varc = sum2 / cnt - mean * mean; if (varc < 0) varc = 0;
        var contrast = clamp01(Math.sqrt(varc) * 4.0);
        // Contrast BOOSTS (flakes/pins/edges twinkle harder as the sun travels) but never
        // gates: a uniform mirror still owns a huge moving highlight -> stays hot.
        var flash = clamp01(pot[idx] * (0.65 + 0.85 * contrast));
        counted++;
        if (flash >= hotT) hot++;
        if (flash < deadT) dead++;
        if (flash >= covT) cov++;
        var c = heat(flash), o = idx * 4;
        heatRGBA[o] = c[0]; heatRGBA[o + 1] = c[1]; heatRGBA[o + 2] = c[2];
        heatRGBA[o + 3] = Math.round(40 + 195 * flash);
      }
    }
    counted = counted || 1;
    return {
      heat: heatRGBA,
      coveragePct: 100 * cov / counted,
      deadPct: 100 * dead / counted,
      hotPct: 100 * hot / counted,
    };
  }

  var api = { computeFlashMap: computeFlashMap, heat: heat, clearcoatStrength: clearcoatStrength };
  global.SPB_FlashMap = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

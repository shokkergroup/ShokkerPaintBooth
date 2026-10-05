/* Zone Spec-Channel Analyzer — ACCURACY-IMPROVED core (2026-07-04, LIVE since 2026-07-04 gauntlet swap).
 * Drop-in replacement for paint-booth-specstats.js. SAME public API:
 *   SPB_SpecStats.computeZoneSpecStats(spec, w, h, opts) -> { pixels,
 *     metallic:{mean,min,max,std,label}, roughness:{...}, clearcoat:{...} } | null
 *   SPB_SpecStats.metallicLabel / roughnessLabel / clearcoatLabel (byte -> string)
 * Existing fields keep their exact meaning; NEW fields are additive (median, p05, p95,
 * mixed, clearcoat.pctNone/pctForbidden/activeMean/activeMedian, top-level material + flash).
 *
 * WHY (all calibrated against the engine, not vibes):
 *  - Channel semantics: engine/SPEC_MAP_REFERENCE.md + _enforce_iron_rules
 *    (shokker_engine_v2.py:185): R=Metallic 0..255; G=Roughness 0=smooth..255=matte with a
 *    FLOOR of 15 on non-mirror pixels (M < 240); B=Clearcoat 16=MAX gloss..255=dull,
 *    0=no clearcoat at all, 1..15 FORBIDDEN (iron-ruled away). CC=0 is NOT the mirror path —
 *    the engine's own mirror chrome base is M=255,R=2,CC=16 (engine/base_registry_data.py:434).
 *  - Label thresholds recalibrated to the engine's own base definitions:
 *    chrome M255/R2/CC16 (:434), candy M200/R15/CC16 (:454), frozen_matte M60/R210/CC175 (:531),
 *    satin_wrap M0/R130/CC60 (:611), deep_pearl M88/R58/CC16 (:838),
 *    gunmetal_satin R=110 "true satin range" (:848-849).
 *  - Mean-only labels lie on bimodal zones (half chrome + half matte -> "satin"): labels now
 *    come from the MEDIAN, and strongly bimodal channels are reported as an explicit split.
 *  - Channel interactions: "chrome/mirror" needs high M AND low R (high M + high R = brushed
 *    metal); track flash needs high M AND low R AND a glossy clearcoat (CC near 16); with a
 *    near-black albedo the METALLIC lobe is albedo-crushed and surviving flash rides the
 *    clearcoat (the ghost_carve mechanism — clearcoat reflection is albedo-independent).
 *  - Mask sampling now samples pixel CENTERS ((x+0.5)*scale) instead of top-left corners,
 *    and fully transparent spec pixels (A===0, the spec-mask channel) are excluded —
 *    canvas getImageData un-premultiplication makes their RGB meaningless anyway.
 * Read-only diagnosis. Never authors a spec. Never touches SHOKK DROP.
 */
(function (global) {
  // ---- calibrated per-channel label functions (same signatures as the old API) ----
  function metallicLabel(m) {
    if (m >= 240) return 'chrome-range metal';       // mirror ONLY if roughness is also low
    if (m >= 150) return 'strong metallic';          // candy bases live at 175-230
    if (m >= 45) return 'semi-metallic (pearl-range)'; // deep_pearl M=88
    if (m >= 20) return 'low-metal';
    return 'dielectric (non-metal)';
  }
  function roughnessLabel(g) {
    if (g >= 205) return 'flat matte';               // frozen_matte R=210
    if (g >= 155) return 'matte';
    if (g >= 95) return 'satin';                     // engine "true satin range" 110-130
    if (g >= 30) return 'soft gloss (pearl sheen)';  // deep_pearl R=58
    if (g >= 8) return 'wet gloss';                  // candy floor R=15 (non-mirror floor)
    return 'polished mirror-smooth (chrome-only)';   // <15 only legal on M>=240 pixels
  }
  // Cc: 16 = MAX gloss, higher = duller, 0 = NO clearcoat (raw/matte), 1-15 = forbidden band.
  function clearcoatLabel(b) {
    if (b <= 0) return 'no clearcoat (raw surface)';
    if (b < 16) return 'forbidden band 1–15 (engine never outputs this)';
    if (b <= 24) return 'max wet clearcoat (16 = wettest)';
    if (b <= 48) return 'gloss clear';
    if (b <= 120) return 'satin clear';              // satin_wrap film CC=60
    if (b <= 200) return 'dull clear';               // frozen_matte CC=175
    return 'dead-dull clear';
  }

  // ---- histogram helpers ----
  function _percentile(hist, n, q) {
    var target = q * (n - 1), acc = 0;
    for (var v = 0; v < 256; v++) { acc += hist[v]; if (acc > target) return v; }
    return 255;
  }
  function _medianOfRange(hist, lo, hi, count) {
    var target = count / 2, acc = 0;
    for (var v = lo; v < hi; v++) { acc += hist[v]; if (acc >= target) return v; }
    return hi - 1;
  }
  // Strong two-population detector on a 16-bucket coarse histogram. Returns null unless
  // BOTH populations hold >=25% of pixels and the modes are >=48 levels apart.
  function _bimodal(hist, n) {
    var coarse = new Array(16), i;
    for (i = 0; i < 16; i++) coarse[i] = 0;
    for (var v = 0; v < 256; v++) coarse[v >> 4] += hist[v];
    var i1 = -1, s1 = -1;
    for (i = 0; i < 16; i++) if (coarse[i] > s1) { s1 = coarse[i]; i1 = i; }
    var i2 = -1, s2 = -1;
    for (i = 0; i < 16; i++) if (Math.abs(i - i1) >= 3 && coarse[i] > s2) { s2 = coarse[i]; i2 = i; }
    if (i2 < 0 || s1 / n > 0.75 || s2 / n < 0.18) return null;
    var lo = Math.min(i1, i2), hi = Math.max(i1, i2);
    var mid = ((lo + hi + 1) >> 1) << 4;                       // split at the midpoint level
    var nLo = 0; for (v = 0; v < mid; v++) nLo += hist[v];
    var nHi = n - nLo;
    if (nLo / n < 0.25 || nHi / n < 0.25) return null;
    return {
      loMedian: _medianOfRange(hist, 0, mid, nLo), hiMedian: _medianOfRange(hist, mid, 256, nHi),
      loShare: nLo / n, hiShare: nHi / n,
    };
  }
  function _pct(x) { return Math.round(x * 100); }

  function _channelStats(hist, n, labelFn) {
    var sum = 0, sum2 = 0, mn = -1, mx = 0, v;
    for (v = 0; v < 256; v++) {
      var c = hist[v];
      if (!c) continue;
      if (mn < 0) mn = v;
      mx = v;
      sum += v * c; sum2 += v * v * c;
    }
    var mean = sum / n;
    var vr = sum2 / n - mean * mean; if (vr < 0) vr = 0;
    var med = _percentile(hist, n, 0.5);
    var mixed = _bimodal(hist, n);
    var label;
    if (mixed) {
      label = 'mixed: ' + labelFn(mixed.loMedian) + ' (' + _pct(mixed.loShare) + '%) + ' +
              labelFn(mixed.hiMedian) + ' (' + _pct(mixed.hiShare) + '%)';
    } else {
      label = labelFn(med);
    }
    return {
      mean: Math.round(mean), min: mn < 0 ? 0 : mn, max: mx, std: Math.round(Math.sqrt(vr)),
      median: med, p05: _percentile(hist, n, 0.05), p95: _percentile(hist, n, 0.95),
      mixed: mixed, label: label,
    };
  }

  /** SAME signature/contract as the old core. spec: Uint8(Clamped)Array RGBA rendered spec
   *  (R=Metallic, G=Roughness, B=Clearcoat, A=spec mask), w,h = spec size.
   *  opts.mask (+maskW/maskH) = optional zone regionMask at canvas res.
   *  NEW optional: opts.paint (+paintW/paintH, default maskW/maskH) = paint RGBA to gate the
   *  flash verdict on albedo darkness. Returns null if no pixels counted. */
  function computeZoneSpecStats(spec, w, h, opts) {
    opts = opts || {};
    var mask = opts.mask || null;
    var maskW = opts.maskW || w, maskH = opts.maskH || h;
    var sx = maskW / w, sy = maskH / h;
    var paint = opts.paint || null;
    var paintW = opts.paintW || maskW, paintH = opts.paintH || maskH;
    var px = paintW / w, py = paintH / h;

    var hM = new Uint32Array(256), hR = new Uint32Array(256), hC = new Uint32Array(256);
    var n = 0, flashCap = 0, darkPaint = 0, paintN = 0;
    for (var y = 0; y < h; y++) {
      var cy = y + 0.5;
      for (var x = 0; x < w; x++) {
        if (mask) {
          // pixel-CENTER nearest-neighbour (old code sampled top-left corners → edge bias)
          var mx = ((x + 0.5) * sx) | 0; if (mx >= maskW) mx = maskW - 1;
          var my = (cy * sy) | 0; if (my >= maskH) my = maskH - 1;
          if (mask[my * maskW + mx] === 0) continue;
        }
        var i = (y * w + x) * 4;
        if (spec[i + 3] === 0) continue;               // A=0: outside the spec mask; RGB unreliable
        var M = spec[i], R = spec[i + 1], C = spec[i + 2];
        n++;
        hM[M]++; hR[R]++; hC[C]++;
        // per-pixel JOINT flash test (marginals can't see this): metal + smooth + wet coat
        if (M >= 150 && R <= 40 && C >= 16 && C <= 48) flashCap++;
        if (paint) {
          var qx = ((x + 0.5) * px) | 0; if (qx >= paintW) qx = paintW - 1;
          var qy = (cy * py) | 0; if (qy >= paintH) qy = paintH - 1;
          var j = (qy * paintW + qx) * 4;
          var luma = 0.299 * paint[j] + 0.587 * paint[j + 1] + 0.114 * paint[j + 2];
          paintN++;
          if (luma < 32) darkPaint++;
        }
      }
    }
    if (!n) return null;

    var metallic = _channelStats(hM, n, metallicLabel);
    var roughness = _channelStats(hR, n, roughnessLabel);

    // ---- clearcoat: population-aware (0 = "no coat" is a different STATE, not a level) ----
    var ccZero = hC[0], ccForbidden = 0, v;
    for (v = 1; v < 16; v++) ccForbidden += hC[v];
    var nActive = n - ccZero;
    var clearcoat = _channelStats(hC, n, clearcoatLabel);
    clearcoat.pctNone = ccZero / n;
    clearcoat.pctForbidden = ccForbidden / n;
    if (nActive > 0) {
      var hA = new Uint32Array(256);
      for (v = 1; v < 256; v++) hA[v] = hC[v];
      var aSum = 0; for (v = 1; v < 256; v++) aSum += v * hC[v];
      clearcoat.activeMean = Math.round(aSum / nActive);
      clearcoat.activeMedian = _percentile(hA, nActive, 0.5);
    } else {
      clearcoat.activeMean = 0; clearcoat.activeMedian = 0;
    }
    if (clearcoat.pctNone >= 0.98) {
      clearcoat.label = 'no clearcoat (raw surface)';
    } else if (clearcoat.pctNone >= 0.3) {
      // mean/median across a 0/16+ mix lands in the forbidden 1-15 band — say what's really there
      clearcoat.label = clearcoatLabel(clearcoat.activeMedian) + ' on ' + _pct(1 - clearcoat.pctNone) +
        '% · no-coat on ' + _pct(clearcoat.pctNone) + '%';
    }
    if (clearcoat.pctForbidden > 0.02) {
      clearcoat.label += ' ⚠ ' + _pct(clearcoat.pctForbidden) + '% in forbidden 1–15 band';
    }

    // ---- channel interactions (the honest part) ----
    var Mmed = metallic.median, Rmed = roughness.median;
    if (!metallic.mixed && Mmed >= 240) {
      if (Rmed <= 10) metallic.label = 'chrome / mirror metal';
      else if (Rmed >= 60) metallic.label = 'rough metal (brushed — NOT chrome: roughness ' + Rmed + ')';
      // else keep 'chrome-range metal'
    }
    if (!roughness.mixed && Rmed < 15 && Mmed < 240) {
      roughness.label += ' ⚠ below non-mirror floor 15 — engine clamps this';
    }

    // ---- material verdict (median-based, engine-calibrated bands) ----
    var ccMedEff = nActive > 0 ? clearcoat.activeMedian : 0;
    var material;
    if ((metallic.mixed && Math.min(metallic.mixed.loShare, metallic.mixed.hiShare) >= 0.3) ||
        (roughness.mixed && Math.min(roughness.mixed.loShare, roughness.mixed.hiShare) >= 0.3)) {
      material = { name: 'mixed materials (two-tone zone)', reason: 'strongly bimodal spec — per-channel splits above' };
    } else if (Mmed >= 240 && Rmed <= 10) {
      material = { name: 'mirror chrome', reason: 'M≥240 + roughness ≤10 (engine chrome = M255/R2/CC16)' };
    } else if (Rmed >= 205) {
      material = { name: 'flat matte', reason: 'roughness ≥205 (frozen_matte = 210)' };
    } else if (Rmed >= 155) {
      material = { name: 'matte', reason: 'roughness 155–204' };
    } else if (Mmed >= 150 && Rmed >= 60) {
      material = { name: 'brushed / satin metal', reason: 'high metal + mid roughness (gunmetal_satin = M205/R110)' };
    } else if (Rmed >= 95) {
      material = { name: 'satin', reason: 'roughness 95–154 (engine "true satin range" 110–130)' };
    } else if (Mmed >= 150 && Rmed <= 30 && ccMedEff > 0 && ccMedEff <= 48) {
      material = { name: 'wet candy / deep-gloss metallic', reason: 'high metal + wet-gloss roughness + CC near 16 (candy = M200/R15/CC16)' };
    } else if (Mmed >= 150) {
      material = { name: 'gloss metallic', reason: 'high metal + low roughness, coat not wet' };
    } else if (Mmed >= 45 && Rmed >= 30) {
      material = { name: 'pearl / tri-coat', reason: 'mid metal + pearl-sheen roughness (deep_pearl = M88/R58/CC16)' };
    } else if (Mmed < 45 && Rmed <= 30) {
      material = { name: 'gloss solid (dielectric)', reason: 'low metal + wet-gloss roughness' };
    } else if (Mmed < 45) {
      material = { name: 'soft-gloss solid', reason: 'low metal + soft-gloss roughness' };
    } else {
      material = { name: 'custom / in-between', reason: 'no engine archetype matches the medians' };
    }

    // ---- track-flash verdict (joint per-pixel, albedo-gated when paint provided) ----
    var fs = flashCap / n, flashLabel;
    if (fs >= 0.6) flashLabel = 'strong track-flash potential';
    else if (fs >= 0.25) flashLabel = 'partial flash — ' + _pct(fs) + '% of zone is flash-capable';
    else if (fs >= 0.08) flashLabel = 'localized flash accents (' + _pct(fs) + '%)';
    else flashLabel = 'minimal flash (needs M↑, roughness↓, CC→16)';
    if (paint && paintN > 0 && fs >= 0.08 && darkPaint / paintN >= 0.6) {
      flashLabel += ' — near-black paint crushes the METALLIC lobe (F0 = albedo); surviving flash rides the clearcoat (CC→16)';
    }

    return {
      pixels: n,
      metallic: metallic,
      roughness: roughness,
      clearcoat: clearcoat,
      material: material,
      flash: { score: Math.round(fs * 1000) / 1000, label: flashLabel },
    };
  }

  var api = {
    computeZoneSpecStats: computeZoneSpecStats,
    metallicLabel: metallicLabel, roughnessLabel: roughnessLabel, clearcoatLabel: clearcoatLabel,
  };
  global.SPB_SpecStats = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

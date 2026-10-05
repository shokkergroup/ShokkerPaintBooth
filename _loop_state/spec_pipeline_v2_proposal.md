# Spec Pipeline V2 — Pushing Past the Viva Mexico Gold Standard

**Author:** SPB analysis agent
**Date:** 2026-05-27
**Sources read (all paths absolute under `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\`):**
- `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md`
- `engine\paint_v2\cultural_viva_mexico.py` (the actual implementation — 561 lines)
- `engine\paint_v2\prism_forge.py` (top-tier procedural base)
- `engine\paint_v2\paradigm_scifi.py` (sci-fi base family)
- `engine\spec_pattern_families\racing_pivot_v1.py` and `racing_pivot_v2.py` (latest pattern doctrine)
- `engine\spec_patterns.py` (catalog index)
- `~/.claude/.../MEMORY.md` (OWNER'S UNIVERSAL LAW — 8-32 px, multi-shade, no lazy finishes)

---

## 1. VM pipeline summary — 5-bullet distillation

1. **DNA-aware sculpting, not blind procedural noise.** VM derives `luma`, `edge_n`, `dark_paint` (< 34/255), `dark_interior`, and `protect_lw` (dilated ridge halo) from the **paint plate itself**. Every subsequent spec move is gated on those masks. Result: motifs read; dark voids stay dark; ridges stay shiny.
2. **Chroma steers spec triplets (warm/cool/green/yellow weights).** The paint RGB is decomposed into `warm_w`, `cool_w`, `green_dom`, `yellow_hint` — these are then injected into M/R/Cc in *correlated* (not random) directions. Adjacent pixels diverge in PBR read, not noise.
3. **Layered frequency stack (low → mid → high → nano).** Low: chroma steering + green phase-split. Mid: ridge relief + 3 independent sparse dot grids (different grid sizes, tonal gates, thresholds). High: 3-sine octaves + diagonal weave + curl. Nano: hi-freq fringe orthogonal to octaves for mip-0 sparkle.
4. **Deterministic per-finish variety from a `blake2s(finish_id)` seed.** Same finish renders identically across runs; different finishes get different grids without per-finish branches. One code path, data-driven variation.
5. **One global tuning knob (`DS = 1.59`) + a hard DNA safety net (`_post_adjust`).** Pre-pass does the artistic lift, post-pass clamps dark-paint voids to `M≤11, R≥222, Cc≤15` while explicitly excluding ridges + crest corridors. Tuning happens in *one* place; safety happens last.

---

## 2. What VM does NOT do — gaps found in the code

Reading `cultural_viva_mexico.py` end-to-end, here are the techniques VM is missing or treats lightly:

1. **No cross-channel physical coupling.** VM does correlate M/R/Cc via chroma weights, but the deltas are still **additive scalars per channel**. There is no underlying *physical property* (e.g. emboss depth, oxidation, film thickness) that drives all three in one synchronized model. Each channel can still drift apart.
2. **No multi-octave phase locking.** The three octaves (`oct_a/b/c`) are **independent sine products** at fixed frequencies. They're summed, not phase-locked. Real surface noise has each octave's phase modulated by the lower octave (turbulence / domain warping). VM uses pure FBM-style summing.
3. **No sub-pixel anti-aliasing on micro features.** Sparse dot grids resize via `INTER_NEAREST` (line 355, 366, 378) which is correct for crispness but **rejects sub-pixel positioning**. At 8-12 px micro-features the AA cost would lift perceived quality measurably.
4. **No thin-film interference math.** VM mentions pearlescence (Cc snap to 16), but there is no `sin²(thickness × band_freq × π)` term — it cannot produce true rainbow shift bands. The chroma steering is a fake substitute.
5. **No spatial weathering / panel-aware aging gradient.** VM treats every pixel equally. A real car gets more sun fade on the roof, more rocker scuff at the bottom. The spec map has no body-position awareness even though the engine knows where each pixel is on the canvas.
6. **No curvature-aware highlight steering.** VM has no concept of surface gradient direction. Brushed metals get spec elongation along the grain direction; VM's `aniso_ripple` (line 472) uses a fixed screen-space angle, not paint-luminance-gradient direction.
7. **No spec chroma in Cc.** Cc is treated as a single scalar (gloss weight). Real iridescent coats carry a slight chroma shift in the specular reflection itself. VM's Cc is monochromatic.
8. **Three-pass dot grids use the same primitive (binary dot).** Each pass varies size/threshold but they're all the same *shape*. No variation in feature *type* between passes.
9. **No edge-direction-aware ridge relief.** `pop = edge_n^0.72` (line 340) is the **magnitude** of the Laplacian. It ignores the **direction** of the gradient. A ridge running NE-SW gets the same treatment as one running E-W — but real polished ridges catch light directionally.
10. **No spectral / wavelength-band thinking.** Everything happens in M/R/Cc value space. There's no notion of "this feature reflects yellow-band differently than blue-band" — which is exactly what makes iridescent coats and prismatic flakes magical.
11. **No history / wear layer.** VM produces a "new car" finish. There's no procedural pass that adds micro-scratches in directional swirl patterns (the actual physical history of a car wash + polish).
12. **No correlated jitter across the three dot grids.** `rng`, `rng_b`, `rng_c` are independent (good for variety) but a *physically* coherent pattern would have these correlated — e.g., dust settles in low areas, polish marks cluster on raised areas. VM scatters all three uniformly.

---

## 3. Top 11 concrete enhancements

### 3.1 — Physical Property Coupling (PPC)

**What it adds.** Define a single hidden field per pixel — call it `depth` (emboss depth, range [-1, +1]) — and derive all three channel deltas from it via a coupled physics model: raised features (`depth > 0`) get M↑ R↓ Cc↑ (polished crest); recessed (`depth < 0`) get M↓ R↑ Cc↓ (shadow valley); flat gets the substrate untouched. The coupling matrix is **shared across all features**, so every primitive obeys the same physical law instead of three independent per-channel rolls.

**Why it lifts perceived quality.** This is the single biggest "real surface vs noise" lift. Right now VM's features can drift incoherently: a sparkle dot might land with high M, mid R, low Cc — fine if intentional, but inconsistent across the canvas. PPC enforces that *every* raised speck is a polished crest, *every* dent is a roughened pocket. The eye reads "this is one material" instead of "this is a noisy spec map."

**Cost.** LOW. ~30 lines. Same render cost; just remap existing deltas through a coupling function.

**Code sketch:**
```python
def couple_from_depth(depth, base_m, base_r, base_cc):
    # depth in [-1, +1]; positive = raised polished, negative = recessed rough
    raised = np.clip(depth, 0, 1)
    recessed = np.clip(-depth, 0, 1)
    dM = raised * 0.42 - recessed * 0.18
    dR = -raised * 0.36 + recessed * 0.48        # roughness inverts
    dCc = raised * 0.30 - recessed * 0.22
    return base_m + dM, base_r + dR, base_cc + dCc

# Usage: instead of three independent rolls per sparkle dot,
# generate ONE depth field per feature pass and couple it.
depth = (dots_a * 0.6 + dots_b * 0.3 - acc_recessed * 0.5).astype(np.float32)
M, R, Cc = couple_from_depth(depth, M, R, Cc)
```

**Best candidates first.** All VM finishes; Union Jacked, Rising Sun, Mortal Shokk (same code family); then PRISM FORGE spec carrier.

---

### 3.2 — Phase-Locked Multi-Octave Turbulence (PLMOT)

**What it adds.** Replace VM's three independent sines (`oct_a/b/c`, lines 423-427) with a **domain-warped** stack: octave 2 is sampled at coordinates that octave 1 has perturbed; octave 3 sampled at coordinates octave 2 perturbed; etc. Same total cost (3 sines), but the high-frequency detail "rides" the low-frequency contours — exactly how real surface micro-roughness folds into macro-deformation.

**Why it lifts perceived quality.** Owner's eye complaint about "single-frequency shimmer" — independently-summed octaves produce a flat aggregate spectrum. Phase locking creates *coherent micro-structures* (whorls, ridges, valleys) at every scale. It's the difference between TV static and woodgrain.

**Cost.** LOW. ~15 lines. Compute time roughly equal — same 3 sines, just chained.

**Code sketch:**
```python
def phase_locked_turbulence(xs, ys, seed):
    # Each octave's input coords are perturbed by the previous octave
    p0 = float(seed % 4096) * (np.pi / 2048.0)
    oct1 = np.sin(xs * 31.0 + ys * 23.0 + p0)
    # warp coords by oct1
    xs2 = xs + oct1 * 0.012
    ys2 = ys + oct1 * 0.012
    oct2 = np.sin(xs2 * 89.0 + ys2 * 71.0 + p0 * 2.1)
    xs3 = xs2 + oct2 * 0.006
    ys3 = ys2 + oct2 * 0.006
    oct3 = np.sin(xs3 * 211.0 + ys3 * 179.0 + p0 * 3.7)
    return oct1 * 0.50 + oct2 * 0.32 + oct3 * 0.18
```

**Best candidates first.** VM (replace `oct_a/b/c`), PARADIGM `plasma_core`, anything using `multi_scale_noise`.

---

### 3.3 — Thin-Film Interference Bands (TFIB)

**What it adds.** Implement actual physics: `intensity(λ) = sin²(2π × n × thickness × cos(θ) / λ)` where `λ` runs over R/G/B bands. Modulate Cc (and slightly chroma in a future RGB-spec channel) with a `thickness` field driven by gray-level + a slow turbulence. Result: real rainbow shifts that move with viewing angle (approximated by edge gradient direction).

**Why it lifts perceived quality.** This is what makes Hot Toys collectibles and Pokemon holos pop. VM's `phase_g` (line 333) is a fake substitute — a single sine. Real thin-film interference produces *three correlated bands* that sweep through hue as thickness varies. The eye reads "oil slick" instead of "noise."

**Cost.** MEDIUM. ~25 lines. Needs three sin² evaluations per pixel; ~2-3 ms extra at 2048².

**Code sketch:**
```python
def thin_film_bands(thickness_field, theta_field):
    # thickness_field in [0,1] normalized to nm-scale; theta_field is view angle proxy
    # Returns 3 band intensities (R/G/B) for spec hue shift
    nm = thickness_field * 0.6 + 0.2  # 200-800 nm range
    cos_t = np.clip(theta_field, 0.3, 1.0)
    lam_r, lam_g, lam_b = 0.65, 0.55, 0.45  # microns
    n = 1.34  # film IOR
    phase_r = (2 * np.pi * n * nm * cos_t / lam_r)
    phase_g = (2 * np.pi * n * nm * cos_t / lam_g)
    phase_b = (2 * np.pi * n * nm * cos_t / lam_b)
    return (np.sin(phase_r)**2,
            np.sin(phase_g)**2,
            np.sin(phase_b)**2)

# Inject into Cc (and into M slightly for metal shimmer)
br, bg, bb = thin_film_bands(gray * 0.7 + warm_w * 0.3, 1.0 - edge_n * 0.5)
Cc = Cc + 28.0 * (br + bg + bb - 1.5) * mic_g
```

**Best candidates first.** VM `vm_quetzal_sunset` (already pearlescent name), CANDY PEARL, PRISM FORGE, any CHAMELEON / IRIDESCENT base.

---

### 3.4 — Curvature-Aware Spec Anisotropy (CASA)

**What it adds.** Compute the **gradient direction** of paint luma (`atan2(grad_y, grad_x)`), then stretch the ripple / weave / nano terms *along* that direction rather than at a fixed screen-space angle. Brushed steel looks brushed because highlights elongate **perpendicular** to the brush; right now VM's `aniso_ripple` (line 472) doesn't know which way the brush ran.

**Why it lifts perceived quality.** Painters and detailers obsess about this — "the brushing direction." A car panel with directional polish reads totally differently from one with uniform polish. VM currently produces uniform polish because every ripple is screen-space. CASA lets the same code produce direction-aware highlights that follow the paint art's actual geometry.

**Cost.** MEDIUM. ~20 lines + one Sobel pass (~4 ms at 2048²). Cache the gradient since `_viva_lru` is already wired.

**Code sketch:**
```python
def curvature_aniso(gray, ripple_freq=54.7, ripple_amp=18.0):
    # Sobel gradients give the local "grain" direction
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx*gx + gy*gy) + 1e-6
    # unit vectors along the gradient
    nx, ny = gx / mag, gy / mag
    # build coordinates in the rotated frame at every pixel
    h, w = gray.shape
    xs = np.arange(w, dtype=np.float32)[None, :] / w
    ys = np.arange(h, dtype=np.float32)[:, None] / h
    # project onto local tangent (perpendicular to gradient)
    u = xs * ny - ys * nx   # tangent coord
    # ripple along the tangent, sharp falloff away from edges
    edge_w = np.clip(mag * 4.0, 0.0, 1.0)
    return np.sin(u * ripple_freq) * ripple_amp * edge_w
```

**Best candidates first.** Anything with directional motif: VM (especially `vm_aztec_sunfire`), brushed-family patterns (`brushed_linear`, `brushed_radial`, `hairline_polish`), CARBON COMPOSITE (the weave should highlight along weft).

---

### 3.5 — Spatial Weathering Gradient (SWG)

**What it adds.** A canvas-space modulation field that knows "top of canvas = sun-faded, bottom = rocker-scuff." Implementation: a soft vertical gradient (with mild perlin warp to break linearity) that increases R, drops Cc, and adds occasional micro-scratch streaks at the bottom; lifts R and dulls Cc slightly at the top. Optional per-finish "weathering age" knob (0=new, 1=patina'd).

**Why it lifts perceived quality.** Cars get hit by sun, rain, road grit asymmetrically. Every finish currently looks brand-new across the whole panel. Even a 5% weathering gradient — barely perceptible per-pixel — adds the *story* of a real surface. Owner-eye reads this as "lived in" vs "freshly composited."

**Cost.** LOW. ~12 lines. Single vertical interpolation + one noise call.

**Code sketch:**
```python
def weathering_gradient(shape, seed, age=0.35):
    h, w = shape
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    # warp the gradient so it's not razor-straight
    warp = multi_scale_noise(shape, [96, 192], [0.6, 0.4], seed + 5511) * 0.08
    sun_top = np.clip((1.0 - ys + warp) * 0.7, 0.0, 1.0)  # strongest at top
    scuff_bot = np.clip((ys + warp) * 0.85, 0.0, 1.0)     # strongest at bottom
    dR = (sun_top * 0.18 + scuff_bot * 0.10) * age
    dCc = -(sun_top * 0.06 + scuff_bot * 0.04) * age
    dM = -scuff_bot * 0.08 * age
    return dM, dR, dCc
```

**Best candidates first.** Any "weathered" or "patina" base. Foundational bases (PARADIGM, PRISM FORGE) could opt-in via a single `age=` param.

---

### 3.6 — Directional Micro-Scratch Layer (DMSL)

**What it adds.** A thin (1-px wide) procedural layer of swirl-pattern scratches in the gloss carrier — the actual physical signature of an orbital buffer/polisher. Implementation: pick 12-24 swirl centers, draw faint logarithmic spiral arcs from each (R↑ Cc↓ along the arc, ~0.5-1.5 px wide). Sparse enough that you only see them in raking light — exactly like real car polish.

**Why it lifts perceived quality.** This is the "$80k detail job" signal. Real polished cars have these. Procedural finishes don't. Owner-eye reads it instantly: "that has been touched by human hands." It's also a feature *type* VM doesn't have, addressing gap #11 + #8.

**Cost.** MEDIUM. ~25 lines + 200-400 cv2.ellipse calls per finish (~5-8 ms).

**Code sketch:**
```python
def micro_swirl_layer(M, R, Cc, seed, intensity=0.5):
    h, w = M.shape
    rng = np.random.default_rng(seed ^ 0xC0FFEE)
    n_centers = int(rng.integers(14, 26))
    for _ in range(n_centers):
        cx = int(rng.integers(0, w))
        cy = int(rng.integers(0, h))
        radius = int(rng.uniform(40, 110))
        # 6-12 swirl arms per center
        for arm in range(int(rng.integers(6, 13))):
            a0 = rng.uniform(0, 2*np.pi)
            for step in range(int(radius * 0.7)):
                r = step * 1.2
                a = a0 + step * 0.05  # logarithmic spiral
                x = int(cx + r * np.cos(a))
                y = int(cy + r * np.sin(a))
                if 0 <= x < w and 0 <= y < h:
                    R[y, x] = min(R[y, x] + 0.012 * intensity, 1.0)
                    Cc[y, x] = max(Cc[y, x] - 0.008 * intensity, 0.0)
    return M, R, Cc
```

**Best candidates first.** Any "show car" / "polished" finish; foundation enhanced; brushed family (as a *second* layer on top of brushing); VM "lowrider" finishes (`vm_guadalupe_lowrider`).

---

### 3.7 — Sub-Pixel AA on Micro Features (SPAA)

**What it adds.** Switch the sparse dot grids from `INTER_NEAREST` to a sub-pixel positioned stamp: instead of resizing a binary grid, splat each dot at a *floating-point* position with bilinear weights. At 8-12 px features, this is the difference between staircase-edged dots and silky-edged dots.

**Why it lifts perceived quality.** Owner says "fine details on just about everything." Sub-pixel AA on micro features is what separates "this was rendered in Photoshop" from "this was made by Pixar." The cost is real but the perceptual lift on tiny features is huge — they stop looking like compression artifacts and start looking like real specks of material.

**Cost.** MEDIUM. ~20 lines per pass. ~3-5 ms extra per dot pass (3 passes in VM → ~10 ms total).

**Code sketch:**
```python
def splat_dots_aa(M, R, Cc, n_dots, seed, dM, dR, dCc, radius=2.0):
    h, w = M.shape
    rng = np.random.default_rng(seed)
    # Floating-point dot positions
    xs = rng.uniform(0, w-1, n_dots).astype(np.float32)
    ys = rng.uniform(0, h-1, n_dots).astype(np.float32)
    # 2x2 bilinear footprint per dot
    x0 = np.floor(xs).astype(np.int32); fx = xs - x0
    y0 = np.floor(ys).astype(np.int32); fy = ys - y0
    for i in range(n_dots):
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                yy, xx = y0[i]+dy, x0[i]+dx
                if 0 <= yy < h and 0 <= xx < w:
                    # Gaussian-ish weight
                    d2 = (dx - fx[i])**2 + (dy - fy[i])**2
                    w_ij = np.exp(-d2 / (2 * radius**2))
                    M[yy, xx] += dM * w_ij
                    R[yy, xx] += dR * w_ij
                    Cc[yy, xx] += dCc * w_ij
    return M, R, Cc
# (Vectorize the inner loops with np.add.at for production.)
```

**Best candidates first.** All sparkle/flake patterns (`flake_scatter`, `micro_sparkle`, `diamond_dust`), VM dot passes, anything where current owner ratings flag "looks pixelated."

---

### 3.8 — Spec Chroma Layer (SCL — partial 4th channel)

**What it adds.** Carry a slight RGB tint inside the Cc carrier by computing a `cc_tint` field (paint-derived hue weight) and modulating Cc not as a scalar but as **R-band/G-band/B-band** intensities that get baked into the consuming shader's spec color slot. For shaders that take a uniform spec color, average back. For shaders that read RGB-spec, you get tinted highlights.

**Why it lifts perceived quality.** Real metallic paints have *colored* highlights — gold metallic doesn't reflect white, it reflects gold. Current VM (and almost all spec patterns) produce grayscale highlights because Cc is a scalar. Even a 6% tint in the spec carrier dramatically lifts perceived realism.

**Cost.** MEDIUM-HIGH. ~30 lines code is cheap, but requires either (a) shader change to consume RGB-spec or (b) a "tint-bake" pass that mixes the tint back into the base color appropriately. Decide the shader path first.

**Code sketch:**
```python
def spec_chroma_layer(Cc, paint_rgb, warm_w, cool_w, green_dom, strength=0.08):
    # Produce a (h, w, 3) tinted version of the highlight
    # Returns (Cc_r, Cc_g, Cc_b) — if shader takes one channel, mix later.
    base_r, base_g, base_b = paint_rgb[:,:,0], paint_rgb[:,:,1], paint_rgb[:,:,2]
    # tint follows paint hue but stays bright (Cc is highlight strength)
    tint_r = 1.0 + (warm_w - cool_w) * strength
    tint_g = 1.0 + (green_dom - cool_w * 0.5) * strength * 0.7
    tint_b = 1.0 + (cool_w - warm_w * 0.5) * strength
    return Cc * tint_r, Cc * tint_g, Cc * tint_b
```

**Best candidates first.** PRISM FORGE (already philosophy-aligned), CANDY PEARL, HOLOGRAPHIC bases, VM (`vm_aztec_sunfire` would catch warm-gold highlights instead of white).

---

### 3.9 — Cross-Feature Correlation (CFC)

**What it adds.** Right now each VM dot grid uses its own RNG (`rng`, `rng_b`, `rng_c`). Real surfaces don't have independent dust + polish + dent patterns — they're correlated by gravity, by wear paths, by panel curvature. Implement a single **shared seed field** that *biases* all three grids: low areas attract dust + dents, high areas attract polish + scratches.

**Why it lifts perceived quality.** Coherence. Currently a polish spot can land *inside* a dust patch, which looks fake. CFC ensures dust avoids polish and polish avoids damage — features cluster the way they do on real panels.

**Cost.** LOW. ~15 lines. One additional noise field; rest is reweighting existing dot rolls.

**Code sketch:**
```python
def correlated_grid_field(shape, seed):
    # one shared low-freq field: high = "polish zone", low = "dust zone"
    field = multi_scale_noise(shape, [48, 96], [0.6, 0.4], seed + 7777)
    return np.clip(field, 0.0, 1.0)

corr = correlated_grid_field((h, w), seed)
# bias dot acceptance: polish grid prefers high corr, dust grid prefers low
acc_polish = dots * mid_tone * m * flat_w * corr               # was uncorrelated
acc_dust   = dots_b * shadow_band * m * flat_w * (1.0 - corr)  # anti-correlated
acc_dent   = dots_c * flat_rig * m * np.clip(0.5 - corr + 0.4, 0.0, 1.0)
```

**Best candidates first.** VM (immediate drop-in), racing_pivot_v2 patterns (most already have 3+ feature types), any pattern with multi-pass features.

---

### 3.10 — Edge-Direction-Aware Ridge Relief (EDARR)

**What it adds.** VM's `pop = edge_n^0.72` uses Laplacian magnitude only. Replace with `pop_directional` that knows which side of the ridge is "uphill" — using `Sobel` gradient direction the bright crest gets the M↑ R↓ treatment while the darker shadow side gets a complementary R↑ M↓ treatment. Creates a *directional* highlight that catches light on one side, shadows on the other.

**Why it lifts perceived quality.** This is the difference between a stamped emboss and a debossed groove — real surfaces have one side lit and one side shadowed. Currently VM treats both sides of every ridge identically, producing the "flat ridge" look the owner has flagged.

**Cost.** LOW-MEDIUM. ~18 lines + one Sobel (can cache).

**Code sketch:**
```python
def directional_ridge(gray, edge_n, mask):
    # gx, gy give where the gradient points (toward bright)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx*gx + gy*gy)
    # bright side = where gradient points; dark side = opposite
    # shift the highlight slightly toward the bright side
    h, w = gray.shape
    nx = gx / (mag + 1e-6)
    ny = gy / (mag + 1e-6)
    # sample a tiny offset along the gradient
    yi = np.clip((np.arange(h)[:, None] + ny * 1.5).astype(np.int32), 0, h-1)
    xi = np.clip((np.arange(w)[None, :] + nx * 1.5).astype(np.int32), 0, w-1)
    bright_side = gray[yi, xi] > gray
    # Apply pop only where this pixel is the LIT side of the ridge
    pop_lit = edge_n * bright_side.astype(np.float32) * mask
    pop_shadow = edge_n * (~bright_side).astype(np.float32) * mask
    return pop_lit, pop_shadow
```

**Best candidates first.** VM ridge relief, all engine_turn / brushed / hairline / damascus patterns, anything with directional motifs.

---

### 3.11 — Mip-Aware Detail Budget (MADB)

**What it adds.** The render engine knows the canvas resolution (`shape`). Right now VM crams the same density of nano-detail into 2048² and 256² renders. At 256² half that detail aliases away into noise that looks like JPEG mosquito artifacts. Implement a `detail_budget = min(1.0, max(0.45, shape[0] / 768.0))` and gate nano + weave + ripple amplitudes by it. At 256², nano fades out; at 2048², it's full strength.

**Why it lifts perceived quality.** Stops thumbnail/preview renders from looking noisier than full renders. Owner's QA workflow uses thumbnails — every preview that looks "noisy" gets a worse score. Same finish at full size would rate higher. This closes the perceptual gap.

**Cost.** TRIVIAL. ~5 lines. Pure scalar.

**Code sketch:**
```python
def detail_budget(shape):
    # Less nano detail at small canvases (it would alias to noise)
    h = shape[0] if isinstance(shape, (tuple, list)) else shape.shape[0]
    return float(np.clip(h / 768.0, 0.40, 1.0))

db = detail_budget(shape)
# Scale the highest-frequency terms by db
nano_amp = 14.0 * DS * db
weave_amp = 11.0 * DS * (0.6 + 0.4 * db)
ripple_amp = 18.0 * DS * db
```

**Best candidates first.** VM (immediately), every spec_pattern_families pattern (they all render at multiple resolutions in QA contact sheets).

---

## 4. Recommended sequencing — if you only land 3

If only 3 enhancements ship in the next month, pick:

1. **PPC (Physical Property Coupling)** — biggest perceptual lift per line of code. Forces every feature into one material law. Affects every existing pattern, costs nothing at render time, lifts coherence everywhere. **Build it first as a shared utility in `engine/spec_sculpt/coupling.py`, then port VM + racing_pivot_v2 to it.**

2. **DMSL (Directional Micro-Scratch Layer)** — most visible "wow" delta. Adds a feature *type* the entire library is missing (real polish swirl), and it's a single self-contained pass that bolts onto any finish. Hits the owner-eye "lazy finish" complaint directly.

3. **CASA (Curvature-Aware Spec Anisotropy)** — unlocks every directional motif. Brushed metals, hairline polish, engine turn, damascus, carbon weave all currently look generic because their anisotropy is screen-space, not paint-space. One Sobel pass cached in `_VIVA_LUMA_CACHE` and you have direction-aware highlights everywhere.

**Why this trio.** PPC = global coherence baseline. DMSL = new feature type owner can immediately see. CASA = unlocks the biggest existing family (brushed/directional). They compose: PPC normalizes the channels, CASA orients the relief, DMSL writes a coherent history on top. Six lines of integration between them; no conflicts.

Phase order, with calendar:
- **Week 1:** PPC utility + port VM. QA review against current VM outputs side-by-side.
- **Week 2:** DMSL implementation + apply to top-3 VM finishes + 3 PARADIGM bases. Owner review.
- **Week 3:** CASA + cache integration + port to brushed family. Performance benchmark.
- **Week 4:** Roll PPC + CASA to all foundation_enhanced + racing_pivot_v2 patterns. Refresh QA contact sheets.

Skip TFIB and SPAA in the first round — too much shader/integration cost to justify before the easier wins land.

---

## 5. Moonshot — "Latent Material Embedding" (LME)

**The idea.** Train a tiny CNN (~50k params, fits in <1 MB) on a curated set of 200-500 *physical* car-paint photos — macro shots of real polished panels, brushed metals, candy pearls, holos, weathered patinas. Output: a learned 8-dimensional **material latent** that, when fed back through a small decoder, produces (M, R, Cc) micro-detail that *cannot be hand-coded*. The model captures the statistical signature of real surfaces — the specific co-occurrences of features that make eyes go "that's real."

**How it would slot in.** At render time, pick a latent (or interpolate between two for blending), feed it through the decoder with the existing chroma/edge masks as conditioning, and use the output as a **+15% modulation layer** on top of the procedural VM stack. VM remains the artistic skeleton; the network adds the "captured-from-reality" texture humans can't articulate.

**Why it could be transformative.** Every hand-coded technique above is the agent's best guess at what makes real materials look real. A model trained on actual material photos *measures* it. The first time a SPB finish gets owner reaction "that looks like an actual photograph of metal" — that's LME. Could also let users **prompt** for materials ("show me 1970s Cadillac lacquer") and get a procedural finish that matches.

**Why it's risky.**
- **Training data.** Need permissions-clear macro photos at consistent lighting, ~500 minimum. Curation is weeks.
- **Inference cost.** Even a tiny CNN adds 30-100 ms per finish at 2048². May force render-time tradeoffs.
- **Style collapse.** Models trained on too narrow a dataset produce one look; trained on too broad, they average to mush. The whole point is the eye-catching specifics — if it can't deliver them, it's worse than VM.
- **Indeterminism.** Owner currently can predict what a finish will look like from the code; a learned layer introduces "why did this finish render slightly different today?" risk. Mitigate with strict latent freezing per-finish.
- **Cultural / IP risk.** Training on photos of branded paints (Lamborghini, Porsche colors) without licensing could create derivative-work concerns. Stick to generic / commissioned / public-domain refs.

**Honest assessment.** 40% chance this ships and lifts perceived quality meaningfully; 30% chance the perceptual lift is real but inconsistent and we end up using it as a niche optional layer; 30% chance the training data and inference cost kill it. Even in the failure modes, the experiment teaches us *which* hand-coded techniques are most missing — a kind of free ablation study.

If it works, SPB becomes the first paint booth in the industry with **learned-from-reality** material synthesis on top of procedural control. That's a moat nobody else can copy without doing the same data work.

---

## Honest assessment — where VM is already further than I assumed

Before reading the code I assumed VM might be a single-pass procedural stack with chroma noise. It is much more than that:

- VM **does** correlate channels via chroma weights (though not via a physical coupling — gap #1 remains).
- VM **does** layer 4 frequency bands (low chroma steering, mid ridge+dots, high octaves, nano fringe).
- VM **does** protect ridges from void-flatten via `protect_lw` — a sophisticated 2-stage mask design.
- VM **has** per-render LRU caches on the expensive luma/edge and crest computations — performance was already considered.
- VM **uses** `blake2s(finish_id)` for deterministic variety — no per-finish if-branches, exactly the right architecture.

So the "envelope push" is genuinely *push* — not "fix the obvious omissions." VM's omissions are deeper-physics, learned-from-reality, and direction-aware things, not naive gaps. That earned my respect.

---

## File location

`C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\_loop_state\spec_pipeline_v2_proposal.md` (this file)

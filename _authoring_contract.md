# SPB FINISH AUTHORING CONTRACT — 2026-09-04

Read this completely before writing a single line. Every rule here was paid for
by a failure earlier today. Following it is the difference between landing on
try 1 and burning ten rounds.

---

## 1. WHAT YOU ARE WRITING

One finish = **three things**, all in the same module file:

```python
def paint_<fid>(paint, shape, mask, seed, pm, bb):   # -> HxWx3 float32 in 0..1
def spec_<fid>(shape, seed, sm, base_m, base_r):     # -> (M, R, CC) each HxW float32 in 0..255
```
plus one entry in `CATALOG` and one in `SPACE`.

- `shape` is `(H, W)`, always square, **2048x2048 at ship time**. It is rendered
  over a WHOLE CAR. A 64px feature is the size of a door handle.
- `paint` is the painter's own base colour, HxWx3 float 0..1. Usually flat.
- `pm` / `sm` are user strength multipliers (0..2, nominally 1.0). Multiply your
  *modulation* by them, never your base level.
- `mask` is where the finish applies; end every paint fn with `_finish(out, src, mask)`.
- `bb` is unused. Accept it.
- **Determinism:** everything derives from `seed`. Never call an unseeded RNG.

### Spec channel semantics — MEMORISE, they are counter-intuitive
| Ch | Meaning | Low value | High value |
|----|---------|-----------|------------|
| M  | Metallic | 0 = dielectric | 255 = metal |
| R  | Roughness | 0 = mirror | 255 = dead matte |
| CC | Clearcoat | **16 = MAX GLOSS** | 255 = dull. **Never go below 16.** |

---

## 2. THE GATES — exact numbers, all of them enforced mechanically

A finish is not done until every one passes. Non-zero exit = not done.

| Gate | Threshold | What it actually measures |
|------|-----------|---------------------------|
| SCALE | `max(paint_band, spec_band) >= 0.20` | **RATIO** of car-window energy to coarse energy |
| FOLLOW | `amp_corr >= 0.35` | correlation of band-limited AMPLITUDE ENVELOPES of paint vs spec |
| STORY | shelf ratio `>= 0.90` | distinct quantised (M,R,CC) material sets per finish |
| COVERAGE | `dead <= 0.70` | fraction near-black or near-white |
| UNIQUENESS | `< 0.80` vs the WHOLE catalog | colour-independent structural similarity |
| RENDER | `< 3s at 2048` | paint + spec together |
| AMPLITUDE | `sd/mean >= 0.10`, `band_abs >= 0.010` | it must actually be visible |
| GRIT | incoherent HF energy, low | the anti-confetti term |

### 2a. SCALE — the EXACT gate, read from the source (scripts/spb_finish_law.py)

    band = (FFT power inside the 8-32px annulus) / (total FFT power)
    PASS requires band >= 0.20.  The owner's five gold standards reach only
    0.218 - 0.443, so there is almost no headroom.

Three consequences that decide whether a finish lives:

* **Energy BELOW 8px does not count.** Fine speckle, 1-3px grain and hash are
  DILUTION — they add to the denominator and nothing to the numerator. Adding
  fine detail to rescue SCALE actively makes it worse.
* **Energy ABOVE 32px does not count** either, and macro layout is where most
  of a naive finish's power sits.
* **A BLUR CANNOT BE THE LOAD-BEARING MECHANISM.** Thermal diffusion, a lens
  PSF, an MTF rolloff, a box wick — every low-pass moves power across the 32px
  cutoff by definition. You cannot build the signal out of the operator the
  gate punishes.

So: put the DOMINANT SPECTRAL PEAK at 12-24px, and keep both the macro layout
and any sub-8px grain deliberately low-contrast.

### 2a-bis. SCALE is a RATIO. This is the one that wastes days.
It is **not** "add more fine detail". `SCALE = fine / (fine + coarse)`. If your
finish has strong macro structure (big cells, wide bands, broad blobs), adding
fine detail does **nothing** because the coarse term grows with it.

Two finishes died today exactly here: a body swage line and a 56px composite
platelet. Six rounds of adding fine detail and quieting the coarse moved SCALE
from 0.14 to 0.18 against a 0.20 floor, and both had to be cut.

**Therefore: do not build a finish whose primary structure is larger than ~40px.**
Macro layout is allowed only as a *low-contrast* organiser (amplitude <= ~20% of
the fine layer's). Put the real contrast in the **10-30px** band.

### 2b. FOLLOW cannot be reasoned about. Measure it, or construct it.
FOLLOW correlates *where the paint has detail* with *where the spec has detail*.
Four separate rounds of physically-correct reasoning ("the groove should be
duller, so roughness rises where the paint darkens") scored **-0.12, -0.47,
-0.49 and -0.62**. The sign of your material logic is irrelevant to this metric.

**The reliable construction — use it unless you have measured otherwise:**

```python
# in spec_<fid>: rebuild the SAME field combination the paint used, then drive
# all three channels off it. This makes FOLLOW true by construction (~+1.0).
mod = _norm(<the exact expression paint_<fid> used to modulate src>)
M  = np.clip(<base_m> + <amp> * mod * sm, 0, 255)
R  = np.clip(<base_r> - <amp> * mod, 15, 255)
CC = np.clip(<base_cc> + <amp> * (1.0 - mod), 16, 255)
```
Whether roughness rises or falls with `mod` is a free choice — pick what the
material wants. What matters is that the spec reads the **same field**.

### 2c. STORY: give your finish its own material cell
The signature quantises each channel to 6 levels (`v/255*6`, boundaries at
42.5 / 85 / 127.5 / 170 / 212.5) and keeps cells covering >=1% of canvas.
Two finishes whose *background* lands in the same (M,R,CC) bucket triple share a
story and fail the shelf ratio. **So pick a background M/R/CC that is distinctly
yours** — e.g. don't make yet another finish that sits at M~20 / R~86 / CC~44.
State your intended background bucket in a comment.

### 2d. Anti-confetti (owner, verbatim)
> "NO CONFETTI LOOKS where you put random 'noise' in just to pass gates. I'd
> rather have CLEAN looking specs that are interesting. Don't need a lot of grit."

Sharp is fine. *Incoherent* is not. A punched lattice, a moulded channel grid and
printer head-bands are all hard-edged and all pass, because their high-frequency
content correlates with its own neighbours. A field of 1px hash does not.
**Never sprinkle noise to pass a gate.**

---

## 3. THE HELPERS YOU MAY USE (already in the module — do not redefine)

```python
_norm(a)                      # -> 0..1
_box(a, r)                    # box blur, summed-area. r is a RADIUS in px.
_mid(shape, feature_px, seed, octaves=3, falloff=0.55)
                              # value noise with features at an EXACT pixel size.
                              # THE workhorse. octaves=1 is nearly single-band.
_streak(a, length, axis=1)    # long directional blur (motion blur). axis=1 -> X.
_ladder(a, steps, lo, hi)     # quantise 0..1 into `steps` flat levels in lo..hi.
                              # THE clean-shades operator: many distinct spec
                              # values with zero grain. Use it liberally.
_px(shape)                    # -> (py, px) PIXEL coordinates, 0..h-1 / 0..w-1
_warp(shape, seed, amp, px_scale)  # domain-warped pixel coords
_cache(key, build)            # memoise an expensive field
_finish(out, src, mask)       # ALWAYS the last line of a paint fn
_incoming(paint, shape)       # the painter's colour, resized to shape
```

### `_px` — READ THIS
`get_mgrid` **already returns pixel indices**, not normalised 0..1. The old
`yy = y * h` idiom found across older shelves multiplies by the size a SECOND
time, putting every feature at **1/512 of intended size**. `_px` is already
correct — just use it, and never multiply its output by `h` or `w`.

### `_mid` frequency facts (measured, not assumed)
`multi_scale_noise` cannot serve this band: its `scale=8` lands at ~72px features
and only grows. That is why `_mid` exists. `_mid(shape, 12.0, seed)` gives ~12px
features. Author in absolute pixels.

---

## 4. RENDER BUDGET — under 3s at 2048 (a 4.2M-pixel canvas)

- Budget roughly **20-25 full-canvas array operations**. Each is ~15-40ms.
- **No Python loop over features.** A per-rivet loop was ~300 full-canvas
  gaussians = minutes. Fold the coordinate instead:
  `da = along - pitch * np.round(along / pitch)` gives an infinite periodic row
  of features in ONE pass.
- **Avoid `np.exp` / `np.sin` inside loops.** A polynomial falloff
  (`q = clip(d2/r2, 0, 1); q -= 1; out = q*q`) is 3-4x cheaper and looks the same.
- A loop over N straight cuts/lines is fine up to ~25 iterations **if** each
  iteration is 3-4 ops and uses precomputed warped coords.
- `scipy.ndimage` is available (`grey_dilation`, `gaussian_filter`) — wrap the
  import in try/except and provide a numpy fallback.
- Cache any field used by BOTH the paint and spec fn via `_cache`.

---

## 5. THE SPACE TABLE (mandatory)

Every finish declares 3-6 knobs that **materially change the look**:

```python
"<fid>": {"pitch": (11.0, 26.0), "depth": (0.30, 0.62), "cuts": [8, 12, 16]},
```
Tuples = float range. Lists = categorical. `scripts/spb_variant_search.py`
samples 10 points, scores them and writes the winner to a sidecar JSON — this is
how the owner's "iterate 10x, pick the best" is satisfied mechanically.

**Include at least one AMPLITUDE knob with a wide range** (e.g. `(0.4, 1.6)`).
Hand-tuning amplitude oscillated between invisible and blown-out for five rounds
today; a wide knob lets the search find the level.

---

## 6. WORKED EXAMPLE — copy this shape exactly

```python
# ════════════════════════════════════════════════════════ NN · PERF WINDOW ══
def _perf(shape, seed, P):
    """One-way vision film: a REGULAR punched lattice, the shelf's periodic member."""
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        dy = (_mid((h, w), 300.0, seed + 61, octaves=2) - 0.5) * float(P["drift"])
        dx = (_mid((h, w), 300.0, seed + 62, octaves=2) - 0.5) * float(P["drift"])
        pitch = float(P["pitch"])
        u, v = (px + dx) / pitch, (py + dy) / pitch
        fu = (u - np.floor(u) - 0.5) * pitch
        fv = (v - np.floor(v) - 0.5) * pitch
        d = np.sqrt((fu * 1.06) ** 2 + (fv * 0.94) ** 2)      # slightly elliptical punch
        rad = pitch * float(P["fill"])
        hole = np.clip((rad - d) / 1.2, 0, 1).astype(np.float32)
        lip = np.clip(1.0 - np.abs(d - rad) / 1.6, 0, 1).astype(np.float32)
        return hole, lip

    return _cache(("perf", h, w, int(seed), _k(P)), build)


def paint_wrap_perf_window(paint, shape, mask, seed, pm, bb):
    """The print survives on the web between the holes; the holes go to black."""
    P = _P("wrap_perf_window")
    src = _incoming(paint, shape)
    hole, lip = _perf(shape, seed, P)
    out = src * (1.0 - hole)[:, :, None] + lip[:, :, None] * 0.22 * float(pm)
    return _finish(out, src, mask)


def spec_wrap_perf_window(shape, seed, sm, base_m, base_r):
    """GRAMMAR: hard duotone. Two materials only - printed web and dead black pit."""
    hole, lip = _perf(shape, seed, _P("wrap_perf_window"))
    sel = (hole > 0.5).astype(np.float32)
    M = np.clip(34.0 * (1 - sel) + 4.0 * sel + 60.0 * lip * sm, 0, 255)
    R = np.clip(38.0 * (1 - sel) + 232.0 * sel, 15, 255)
    CC = np.clip(20.0 * (1 - sel) + 200.0 * sel, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)
```

Note what makes it work: pitch ~13px (in the car window), the geometry is
periodic and coherent (not noise), the spec reads the *same* `hole`/`lip` fields
the paint used, and the two materials it deals are far apart in every channel.

---

## 7. HOUSE STYLE (the owner reads this code)

- Every finish gets a **section banner comment** and a one-line docstring saying
  what the material physically IS.
- The spec fn's docstring starts `"""GRAMMAR: ...` and names its mapping strategy
  (quantised ladder / dual population / domain-constant palette / hard duotone /
  smooth ramp / edge-driven / depth ladder / anisotropic).
  **No two finishes on a shelf may use the same grammar.**
- When you make a non-obvious choice, write the *evidence* in the comment
  ("measured X, so Y"), not a restatement of the code.
- Comment density: match the worked example. Explain WHY, never WHAT.

## 8. THE OWNER'S STANDING RULES

> "Our #1 rule - above ALL ELSE - is NO LAZINESS, NO REPEATS."
> "ALL finishes MUST be unique. Don't reuse the same math for finishes OR specs."
> "Everything that we do needs purpose. No throwaways."
> "Make sure the finish matches the name and the description on what it's
> SUPPOSED to be doing. Ensure it does it."

A recolour of an existing field is not new work. Two finishes that differ only in
parameters are one finish. If your mechanism is "noise, thresholded", stop and
invent something.

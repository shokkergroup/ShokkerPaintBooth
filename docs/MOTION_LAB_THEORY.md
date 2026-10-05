# FRACTURED MOTION — making a static spec map look ALIVE

Owner mission 2026-08-10: *"finishes that look like they dance/move/shift within the light…
running water, bullet travel, lightning striking… tricks that would trick the iRacing paint
rendering system into making these finishes LOOK like they are alive/3D."*

Sibling of `docs/NIGHTSHIFT_LAB_THEORY.md`. NIGHTSHIFT exploits a change in **lighting
condition** (day vs night). MOTION exploits a change in **angle** — the car rotating relative to
a fixed light and camera. Different lever, same shader.

---

## 1. What actually moves

From the established model (NIGHTSHIFT theory, confirmed against `shokker_engine_v2` install notes):

```
pixel ≈ diffuse(albedo · N·L · ambient) + specular(N, V, L, M, G, Cc)
```

We have **no normal map**. `N` is fixed per pixel by the car's geometry. So as the car moves, the
only thing changing per pixel is the angular relationship — `N·H`, where `H = normalize(V + L)`.

The set of pixels where `N·H ≈ 1` is the **highlight locus**, and it *sweeps across the body* as
the car turns. That sweep is the only motion the sim gives us for free.

**So the entire craft of this category is: control WHICH pixels respond as the sweep passes over
them, HOW SHARPLY, and IN WHAT ORDER.** We are not animating anything. We are choreographing a
response to a moving stimulus.

The owner's four-dial physics is the control surface:

| dial | what it does | what it buys us for motion |
|---|---|---|
| **G — roughness = aperture** | angular WIDTH of the response | **dwell time.** Low G = brief bright flash as the sweep passes. High G = broad, dim, always-on. |
| **M — metal = amplifier** | response amplitude, and tints it by albedo | brightness + **colour** of the travelling highlight |
| **Cc — clearcoat = power** | a SECOND, independent, **WHITE** lobe with its own sharpness | a second highlight that can be spatially offset from the first |
| **pre-crushed paint** | dark albedo so specular dominates | contrast; without it the diffuse term washes the effect out |

---

## 2. The seven motion mechanisms

Each finish must be built on at least one of these, stated explicitly in its recipe.

### M1 · TRAVELLING PULSE (the chase-light) — *the workhorse*
Quantize G into **narrow discrete bands** arranged along a path, each band a step further along an
aperture ladder. As the sweep advances, band *k* fires, then *k+1*, then *k+2*. The eye integrates
sequential discrete activation as a **pulse running along the path** — this is literally how
theatre-marquee chase lights work.

> **Discreteness is the whole trick.** A smooth G gradient reads as a smear. Quantized razor steps
> read as travel. The existing **CRUSH LAW** machinery (6+ quantized razor-terraced ladders,
> `_TIERS` in the nightshift module) was invented for colour flip and is *already* a motion engine.
> Reuse it, do not reinvent it.

### M2 · PARALLAX DEPTH (two lobes sliding) — *the 3D cue*
Base spec (M/G) and clearcoat (Cc) are **separate lobes with different sharpness**. Give them
spatially **offset** patterns. Both track the same sweep, but because the patterns are displaced,
the two highlights appear at different places and **cross and separate** as the angle changes.

Two highlights sliding past each other is the strongest depth cue obtainable without a normal map.
Reads as *"the paint has layers"* / *"something is under the surface."*

### M3 · COLOUR-SHIFTING TRAIL
Metal specular is **albedo-tinted**; clearcoat/dielectric specular is **WHITE**. Alternate
metal-dominant and clearcoat-dominant zones **along the path**, and the travelling highlight
*changes hue as it moves*: coloured → white-hot → coloured. A lightning bolt whose strike point
goes white. A tracer with a hot tip.

### M4 · ACCELERATION (aperture ramp)
Vary G **monotonically** along the path. Where G is small the pixel flashes briefly (reads fast);
where G is large it dwells (reads slow). A pulse crossing the ramp appears to **accelerate or
decelerate**. Water slowing as it spreads; a round snapping past.

### M5 · COUNTER-SHIMMER (boil)
Two interleaved populations at **2–6 px** carrying **opposite** flow directions. One lights on the
leading edge of the sweep, the other on the trailing edge, so the surface **churns** instead of
translating. Running water, heat haze, roiling smoke.

### M6 · GRAZE MIGRATION (the Fresnel band)
Dielectric reflectance rises steeply at grazing incidence. A car body presents a continuous range
of incidence angles, so there is always a near-grazing band around the silhouette. Structure Cc to
align with it and the lit band **migrates across panels** as the car turns — a slow, large-scale
wave over the whole car, deliberately different in scale from the fine pulses of M1.

### M7 · STROBE LATTICE (crawl)
Isolated near-mirror points (**M high, G very low, 2–4 px**) on a lattice where each point carries a
**phase offset from its neighbours**. Only a few satisfy the angle at any moment, so you get sparse
sparkle whose *population* shifts as the car turns → **crawling** glitter. Distinct from ordinary
flake: normal flake twinkles randomly, this migrates along a direction because the lattice phase has
a gradient.

---

## 3. Two hard design laws for THIS category

### Law A — omnidirectional flow (non-negotiable)
**UV is reversed / rotated / scattered per car** (memory `spb-uv-orientation-agnostic-design`). A
single global left-to-right flow will appear vertical on one panel, mirrored on another, and
diagonal on a third. A category built on one global direction would look broken on most cars.

So: **no global straight-line flow.** Every flow field must be *locally coherent, globally
omnidirectional*:
- curl / divergence-free noise flow (locally smooth, globally isotropic)
- radial, spiral, or vortex flows (defined by a centre, not a direction)
- multi-domain flows where each cell has its own direction (Voronoi-partitioned)

The motion then reads correctly *locally* wherever the UV lands it.

### Law C — SHARP edges, not merely small periods (learned the hard way 2026-08-10)
The fine-detail gate rewards **sharp edges**, not spatial frequency. Measured on the moire
flagship: its fine carrier scored **0.143** — *worse than the coarse beat it was meant to fix* —
even at a 35 px period, because **a sine is smooth** and carries almost no energy below 3 px.
Three passes to learn it: raising the frequency did nothing; thresholding the carrier to near-binary
lines moved it 0.158 -> 0.184; only a crisp **cross-hatch of both carriers** + a micro dither
cleared the bar at 0.216.

Consequences for every future flow here:
- Any trig-based structure (`sin`/`cos` grids, ripples, spirals) MUST be thresholded to crisp
  lines before it becomes a `path`. A soft `_aa` ramp over a sine is a blob however short its period.
- Design finer than the target on the 1024 work grid: the 1024->2048 bilinear upsample softens
  edges, so structure that measures fine on the work grid loses some of it on the canvas.
- **CONCRETE NUMBER (cost me this mistake three times):** every `cell` and every trig frequency is
  in WORK-GRID units, and the canvas is 2x that. So target a period **<= 16 px on the work grid**
  to land <= 32 px on the car, i.e. **frequency >= 64 cycles** per normalised unit and Worley
  `cell <= 16`. A "22 px" band written at 46 cycles is really 44 px on the car and fails the gate.
- **`trail` trades M_std for the colour shift.** It converts the lit lane from albedo-tinted metal
  to the WHITE dielectric lobe, so above ~0.5 it will fail the metal-strength gate.
- **A thin `path` needs a textured SKIN.** If `path_mean` is ~0.1 then ~90% of the canvas is
  off-path, and if that skin is uniform the strength gate fails no matter how good the lit lane is.
  The factory now bands the off-path M and Cc for exactly this reason (and the doctrine wanted many
  distinct shades anyway).
- This is the same failure mode as the half-res Worley "optimisation" — anything that blurs a mask
  costs the sharpness the law is actually measuring.

### Law B — fine bands, always
The 8–32 px fine-detail law is not in tension with motion here, it *helps*: finer bands = more
discrete steps across the same panel = a smoother, more convincing chase. Bands coarser than ~32 px
read as stripes that flicker, not as a pulse that travels.

---

## 4. What we can and cannot verify here

**Can verify mechanically (in-repo):** the spec channels carry the intended structure (band count,
aperture ladder separation, offset between the M/G and Cc patterns, population interleave scale),
uniqueness < 0.80, render ≤ 3 s @ 2048, coverage + fineness, MIP survival, iron-safe.

**Cannot verify here — only the owner, in sim:** whether it actually *reads as motion*. The illusion
depends on the real sweep of a real light across real curved geometry at speed. No static render can
confirm it. Every finish therefore ships with its **mechanism named** so that when the owner says
"this one moves, this one doesn't", the verdict maps back to a mechanism and we learn something
transferable instead of guessing per finish.

That feedback loop is the actual deliverable: 50 finishes spanning 7 mechanisms, labelled, so one
in-sim session tells us which mechanisms work.

---

## 5. Theme → mechanism map (the build plan)

| theme family | primary mechanism | why it fits |
|---|---|---|
| Running water / liquid | M5 counter-shimmer + M4 ramp | churn, not translation; slows as it spreads |
| Bullet / tracer / velocity | M1 pulse + M3 colour trail + M4 | discrete travel with a hot tip |
| Lightning / arc / discharge | M1 + M3 (white strike point) | branching path, white-hot core |
| Depth / substrate / "under glass" | M2 parallax | two lobes sliding = layers |
| Silhouette wave / breathing | M6 graze migration | large-scale, slow, whole-car |
| Crawling glitter / swarm | M7 strobe lattice | population migration |
| Mixed / exotic | 2–3 stacked | the flagships |

Full per-finish recipes live in the generator module; progress in
`_motion_lab/MOTION_PROGRESS.jsonl`.

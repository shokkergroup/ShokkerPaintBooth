# NIGHTSHIFT LAB — the true-color-flip theory (2026-08-01)

**Mission (owner):** FRACTURED finishes flip color → near-white at night under lights.
Goal: TRUE hue flips — blue→purple, blue→red, red→yellow, orange→green, pink→blue,
red→black. "It's ALL mathematical equations… maybe there's something that's just
never been exploited."

## 1. Why the current finishes flip to WHITE (mechanism, from evidence)

Owner screenshots (ShareX 2026-08): same livery reads dark navy in flat light and
near-pure white under direct trackside light (shots 1/2/5). At night (shot 9) only
the patterned regions fire — and the purple graffiti lines glow PURPLE, not white.

iRacing's custom-paint shader is standard PBR fed by our spec map:
`R = metallic, G = roughness, B = clearcoat (16 = max gloss, 255 = dull)`.

Final pixel ≈ `diffuse(albedo · N·L · ambient)  +  specular`.

- **Dielectric specular and the clearcoat lobe are WHITE** (colorless Fresnel).
- **Metal specular is TINTED BY ALBEDO** (metals reflect their own color) — and
  metallic=1 KILLS the diffuse term entirely.
- Day: ambient/diffuse dominates → you see albedo hue.
- Night under point lights: specular dominates → you see the SPECULAR color.

So the catalog's white-flip = carved-low clearcoat (B→16) + gloss firing a WHITE
lobe over a crushed dark base. The engine already knows this as the owner's
four-dial physics (shokker_engine_v2.py install comments): *"clearcoat = power,
roughness = aperture, metal = amplifier, pre-crushed paint"* and the Blood Marble
forensics *"M252 / B255 / G-lanes"* — high metal, clearcoat suppressed, roughness
lanes deciding where it fires. The purple night-glow in shot 9 is the proof that
**albedo-tinted metal specular already survives iRacing's night lighting.**

## 2. The unexploited trick — split day and night onto different PIXELS

Every existing finish gives a region ONE albedo, so its night flash is the same
hue family as its day color (or white). But we control 2048² pixels
independently, and the eye spatially averages anything finer than ~4–8 px at
viewing distance. So: **interleave two pixel populations with DIFFERENT hues and
OPPOSITE lighting responses.**

| population | albedo | M | G | B | day | night |
|---|---|---|---|---|---|---|
| A — "day carrier" | day hue | 0 | 190–235 (matte) | 235–255 (no lobe) | shows its hue (diffuse) | goes dark (no gloss, no light) |
| B — "night carrier" | night hue | 245–255 | 8–70 lanes | 230–255 (**suppress white lobe**) | near-invisible (metal has no diffuse; mirror reflects dark env) | FIRES its albedo hue (tinted metal specular) |

Day = A's hue. Night = B's hue. **That is a true color flip**: blue→red, red→yellow,
orange→green, pink→blue — any pair. red→black is the degenerate case (no B
population, or B = black metal which fires nothing).

Bonus dials nobody has combined:
- **Roughness split inside population B** → tight-mirror pixels strobe under
  headlight beams while mid-rough pixels glow under broad floodlights: the night
  hue can CHANGE with light type.
- **Deliberate B=16 accents** → a third state: thin razor lines that flash WHITE
  on top of the two-hue flip (tri-state finishes).
- **Ratio field**: the A:B mix ratio follows a generative macro field → different
  car zones flip with different strength (impossible-by-hand look).

## 3. Physics risks (what the track test must answer)

1. **Mip-averaging**: at distance the game averages paint + spec mips; A/B mix
   tends toward (mid albedo, M≈0.5). Counter: interleave at 2–6 px scale (fine
   but above single texel), keep populations in coherent micro-shapes (veins,
   cell walls, dashes) instead of 1px noise.
2. **Day tint pollution from B**: mirror metal reflects the sky → could read
   sky-tinted in day. Counter: keep B ≤ ~45% area, push G lanes so only part of
   B is mirror-tight.
3. **sRGB/compression**: TGA is uncompressed; fine.
4. **The booth preview is not iRacing** — final verdict is on-track (owner's
   plan: special test category, track test tomorrow).

## 4. Test fleet — NIGHTSHIFT LAB (category ⚗️, 10 finishes, one flip-pair + one
   geometry + one mechanism-variant each; uniqueness law honored)

| id | flip | geometry / mechanism twist |
|---|---|---|
| ns_ember_reversal | red → black + ember veins | Lichtenberg branching; night = body vanishes, veins smolder |
| ns_indigo_inferno | indigo → red | diagonal twill + blue-noise dash dither, 50/50 |
| ns_violet_verdict | cobalt → violet | Worley shatter: walls metal-violet, cells matte-cobalt |
| ns_solar_betrayal | red → gold-yellow | interfering ring ripples; rings are the night carrier |
| ns_toxic_handshake | orange → acid green | reptile scale lattice; scale EDGES fire green |
| ns_bubblegum_abyss | pink → electric blue | micro-dot day field over interstitial night web |
| ns_ghost_prism | white → rainbow | night hue varies spatially via flow field (hue-wheel metal) |
| ns_dead_channel | teal → magenta | glitch scanline blocks; slivers between blocks carry night |
| ns_triple_cross | slate → crimson + WHITE razor | tri-state: argyle metal diamonds + B=16 edge lines |
| ns_furnace_glass | molten orange → ice blue | crackle glaze; cracks carry the night hue |

Spec mirrors paint geometry per SPB-105; features 8–32 px; full coverage; 3+
frequency bands (macro ratio field, micro population shapes, sub-pixel sparkle).

## 5. Status log (append-only)

- 2026-08-01 01:15 — theory locked, mechanism confirmed from screenshots + engine
  forensics comments. Building `engine/expansions/nightshift_lab_2026.py`.
- 2026-08-01 02:00 — SHIPPED iteration 1: all 10 finishes live end-to-end
  (registry → server → picker group 🌗 FRACTURED NIGHTSHIFT in the FRACTURED
  section → applied to zone → preview render 2.5s). Uniqueness gate 10/10 PASS
  (nearest 34–41%). Structural harness 10/10 (popB 0.12–0.66, matte G≈214,
  metal G-lanes 38–53, Cc≈241, coverage 64/64). Bugs killed: soft-mask metal
  dilution, `_aa` descending-ramp degeneration (3 inverted geometries), cv2.line
  wrap streaks, razor-mask 0.9 cap. Server restarted, booth verified.
- 2026-08-01 11:35 — WAVE 2 SHIPPED per owner ("a hit — expand to 100, go
  CRAZY"): +91 experiments = **101 total live in the booth** (verified: picker
  zoom shows "101 finishes", monolithic registry 1866). Eight themes: ocean,
  sky/storm, fire/earth, grunge, racing, tech/glitch, animal, exotic-math.
  91/91 structural harness pass under production hash; worst 2.89s @2048.
  Lessons: adaptive-dilation wrapper for stamped art; PYTHONHASHSEED=0 required
  for deterministic field salts (server sets it — packaged app env needs audit);
  one structural clone (iris_reactor←hyper_rings) caught + replaced.
  Uniqueness gate over the full new fleet running at time of writing.
- NEXT (loop): gate results + fix any dupes; ratio/scale variants of the
  flagship flip; the all-mechanisms TEST CARD finish; baked-thumbnail check.

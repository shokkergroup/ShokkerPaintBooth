"""
heat_molten.py - wild-spec-v2 dedicated spec generators for the HEAT/MOLTEN family.

wild-spec-v2 2026-06-07. Owner rejected v1 as LAZY (no spec diversity: one
make_wild_spec template + per-finish scalar dials -> M/R/Cc all derived from the
SAME fields -> every composite read as ONE hue). This redo is the opposite:
EVERY finish below has its OWN algorithm + motif, and its M, R, Cc channels carry
GEOMETRICALLY DIFFERENT structures (many-hue triplet zones per the
VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS doctrine). In the owner's composite view
Red=M, Green=R, Blue=Cc: high M reads red, high R green, high Cc blue, M+R yellow,
M+Cc magenta, R+Cc cyan, all-high white, all-low black.

Finishes in this family (11): burnt_headers, volcanic, shokk_inferno,
plasma_metal, plasma_core, shokk_reactor, shokk_surge, shokk_blood,
shokk_fusion_base. (electric_ice/shokk_static etc. live in other families.)

CONTRACT (identical to v1 base_spec_fn):
    spec_<id>(shape, seed, sm, base_m, base_r) -> (M, R, CC) float32 (h,w) arrays
    clipped M[0,255], R[15,255], CC[16,255].
sm is treated as a DAMPED contrast knob via SM_CONTRAST_GAIN (x2.0-aware), never
a raw multiply, so post-sm output stays varied with <1% clip at 255.

PERF: macro/mid bands built at a ~768px work shape then upscaled; the FINEST band
(micro-flake / sparkle / ember pins) is added at FULL resolution after upscale so
fine detail is real. All vectorized - no Python pixel loops.

SAFETY (#9): paint_fn untouched, compose.py never edited (T13), determinism from
(seed, finish-id hash) only - no runtime randomness.
"""

import numpy as np

try:
    import cv2
    _HAVE_CV2 = True
except Exception:  # pragma: no cover - cv2 is always present in this app
    _HAVE_CV2 = False

# Reuse v1 helpers (do NOT edit wild_spec_lab.py - just import from it).
from engine.expansions.wild_spec_lab import (
    _wild_work_shape,
    _wild_upscale,
    SM_CONTRAST_GAIN,
)

# Structural-color primitives for angle-reveal gates (available per doctrine #5).
from engine.paint_v2.structural_color import (
    _cx_directional_mask,
    _cx_fine_spec_pins,
    _cx_buried_reveal_gate,
)


# ════════════════════════════════════════════════════════════════════════════
# Shared low-level helpers. These are GEOMETRY PRIMITIVES, not a spec template -
# each finish composes them into its OWN channel structures.
# ════════════════════════════════════════════════════════════════════════════

# x2.0-awareness (#6): the app passes sm (~2.0 default) straight into us and uses
# our output directly. We treat sm as a damped contrast knob, NOT a raw multiply.
def _sm_contrast(sm):
    sm_f = float(sm) if sm and sm > 0 else 1.0
    c = 1.0 + (sm_f - 1.0) * SM_CONTRAST_GAIN
    return float(np.clip(c, 0.55, 1.75))


def _fid_seed(seed, finish_id):
    """Deterministic per-(seed, finish) base seed - no runtime randomness (#9)."""
    h = 2166136261
    for ch in finish_id:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return (int(seed) * 2654435761 + h) & 0x7FFFFFFF


def _coords(shape):
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _hash01(shape, seed, salt=0):
    """Per-pixel deterministic uniform-ish hash in [0,1]."""
    x, y = _coords(shape)
    s = float(seed + salt) * 0.00137
    n = np.sin((x * (127.1 + (salt % 11) * 3.7) +
                y * (311.7 + (salt % 7) * 5.1) + s) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _value_noise(shape, seed, freq):
    """Smooth bilinear value noise at a given cell frequency (one octave)."""
    h, w = shape
    gh = max(2, int(round(freq)) + 1)
    gw = max(2, int(round(freq * w / max(h, 1))) + 1)
    rng = np.random.RandomState(int(seed) & 0x7FFFFFFF)
    grid = rng.uniform(0.0, 1.0, (gh, gw)).astype(np.float32)
    if _HAVE_CV2:
        up = cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
    else:
        yi = np.linspace(0, gh - 1, h).astype(np.int32)
        xi = np.linspace(0, gw - 1, w).astype(np.int32)
        up = grid[yi][:, xi]
    return np.clip(up.astype(np.float32), 0.0, 1.0)


def _fbm(shape, seed, base_freq=4.0, octaves=4, lac=2.0, gain=0.5):
    """Fractal value noise - multi-band so even a 'smooth' field has fine detail."""
    acc = np.zeros(shape, dtype=np.float32)
    amp = 1.0
    tot = 0.0
    f = float(base_freq)
    for o in range(octaves):
        acc += _value_noise(shape, seed + o * 101 + 7, f) * amp
        tot += amp
        amp *= gain
        f *= lac
    return acc / max(tot, 1e-6)


def _blur(arr, sigma):
    if sigma <= 0:
        return arr.astype(np.float32, copy=False)
    if _HAVE_CV2:
        return cv2.GaussianBlur(arr.astype(np.float32), (0, 0), sigmaX=float(sigma))
    return arr.astype(np.float32, copy=False)


def _norm(a):
    """Stretch to [0,1] robustly (1st-99th pct) so std stays high after sm."""
    a = a.astype(np.float32)
    lo = np.percentile(a, 1.0)
    hi = np.percentile(a, 99.0)
    if hi - lo < 1e-6:
        return np.clip(a - lo, 0.0, 1.0)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def _voronoi(shape, seed, n_sites):
    """Return (cell_id, d1, d2) - nearest-site id, dist to nearest, to 2nd.
    Edges where (d2 - d1) is small. Vectorized over a fixed jittered site set.
    """
    h, w = shape
    rng = np.random.RandomState(int(seed) & 0x7FFFFFFF)
    sx = rng.uniform(0.0, 1.0, n_sites).astype(np.float32)
    sy = rng.uniform(0.0, 1.0, n_sites).astype(np.float32)
    x, y = _coords(shape)
    d1 = np.full((h, w), 1e9, dtype=np.float32)
    d2 = np.full((h, w), 1e9, dtype=np.float32)
    cid = np.zeros((h, w), dtype=np.int32)
    aspect = w / float(max(h, 1))
    for i in range(n_sites):
        dx = (x - sx[i])
        dy = (y - sy[i]) / max(aspect, 1e-6)
        d = dx * dx + dy * dy
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        cid = np.where(closer, np.int32(i), cid)
        d1 = np.where(closer, d, d1)
    return cid, np.sqrt(d1), np.sqrt(d2)


def _sparse_pins_full(shape, seed, density, sharp=0.0):
    """FULL-RES crisp single-pixel-ish sparkle via NEAREST-upsampled hash grid.
    `sharp` (0..1) thins the dots. Added AFTER upscale so specks stay crisp (#8).
    """
    h, w = shape
    cell = 2
    gh = max(1, h // cell)
    gw = max(1, w // cell)
    rng = np.random.RandomState(int(seed) & 0x7FFFFFFF)
    grid = rng.uniform(0.0, 1.0, (gh, gw)).astype(np.float32)
    thr = 1.0 - density * (1.0 - 0.6 * sharp)
    hot = (grid > thr).astype(np.float32)
    if _HAVE_CV2:
        up = cv2.resize(hot, (w, h), interpolation=cv2.INTER_NEAREST)
    else:
        yi = np.linspace(0, gh - 1, h).astype(np.int32)
        xi = np.linspace(0, gw - 1, w).astype(np.int32)
        up = hot[yi][:, xi]
    return up.astype(np.float32)


def _nano_fringe(shape, seed):
    """mip-0 single-pixel shimmer for glint (#3 nano fringe). Full res."""
    return _hash01(shape, seed, 313)


def _ridge_corridor(shape, seed, freq, wander, thick):
    """A meandering 1D ridge centerline field in [0,1]: 1 on the seam, falling off.
    Implements the Viva ridge-protect trick: a hard core + a protected halo.
    Returns (core, halo) - core is narrow/sharp, halo is the wider falloff glow.
    """
    x, y = _coords(shape)
    # centerline meanders across the canvas (sine-perturbed, axis x)
    wob = (_value_noise(shape, seed + 5, 6.0) - 0.5) * 2.0
    center = 0.5 + wander * np.sin((x * freq + y * 1.7 + seed * 0.01) * np.pi) \
        + wander * 0.6 * wob
    dist = np.abs(y - center)
    core = np.clip(1.0 - dist / max(thick, 1e-4), 0.0, 1.0)
    core = core * core  # sharpen the core
    halo = np.exp(-(dist * dist) / max((thick * 3.0) ** 2, 1e-6))
    return core.astype(np.float32), halo.astype(np.float32)


def _soft_knee(a, knee=222.0, ceil=255.0):
    """Asymptotically compress values above `knee` toward `ceil` (never reaching
    it for broad fields) so sm-contrast expansion does not produce broad clipping.
    Values below the knee pass through untouched, preserving channel variety/std.
    Sparse full-res sparkle/white-core features are added AFTER this and may still
    hit 255 - that is intended (true highlights), the knee only tames broad fields.
    """
    a = a.astype(np.float32)
    span = ceil - knee
    over = np.maximum(a - knee, 0.0)                          # only compress highs
    comp = knee + span * (over / (over + span + 1e-6))
    return np.where(a > knee, comp, a).astype(np.float32)


def _assemble(M, R, CC, shape, sm):
    """Apply damped sm contrast around 128, soft-knee the broad highs, upscale to
    full res. M/R/CC come in on the WORK shape in [0,255]. Returns full-res arrays.
    The finest full-res bands (sparkle / white-core) are added by each finish AFTER
    this call and are allowed to hit a true 255.
    """
    h, w = shape
    c = _sm_contrast(sm)
    M = _soft_knee(128.0 + (M - 128.0) * c)
    R = _soft_knee(128.0 + (R - 128.0) * c)
    CC = _soft_knee(128.0 + (CC - 128.0) * c)
    M = _wild_upscale(M, h, w)
    R = _wild_upscale(R, h, w)
    CC = _wild_upscale(CC, h, w)
    return M, R, CC


def _finalize(M, R, CC):
    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.clip(R, 15, 255).astype(np.float32)
    CC = np.clip(CC, 16, 255).astype(np.float32)
    return M, R, CC


# ════════════════════════════════════════════════════════════════════════════
# 1) burnt_headers - tempered exhaust steel, flow-aligned heat-tint CONTOUR bands
#    wrapping a meandering protected weld-bead ridge.
# ════════════════════════════════════════════════════════════════════════════
def spec_burnt_headers(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. burnt_headers = flow-aligned temper-CONTOUR
    # bands perpendicular to a pipe-axis vector field, around a protected weld
    # ridge. Cc=peacock band gradient, M=weld-bead seam ridge, R=anisotropic soot
    # streaks - three different geometries. Hues: magenta+blue+green+red+cyan.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "burnt_headers")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)
    x, y = _coords(ws)

    # --- pipe-axis flow field: rotated coords define pipe direction (Band A) ---
    ang = 0.62  # pipe runs diagonally
    u = x * np.cos(ang) + y * np.sin(ang)          # along-pipe
    v = -x * np.sin(ang) + y * np.cos(ang)         # across-pipe
    flow_wob = (_fbm(ws, s + 11, base_freq=2.0, octaves=3) - 0.5) * 0.18
    # flow-distance field = how far along the pipe (drives perpendicular bands)
    flow_dist = u * 6.0 + flow_wob + 0.9 * np.sin(v * np.pi * 3.0)

    # --- temper CONTOUR bands: thresholded bands of the flow-distance field ---
    band_phase = (flow_dist % 1.0)
    # Cc carries the SMOOTH peacock band gradient (broad oxide bloom contours)
    peacock = 0.5 + 0.5 * np.sin(flow_dist * np.pi * 2.0)        # smooth contour
    oxide_mottle = (_fbm(ws, s + 23, base_freq=12.0, octaves=3) - 0.5) * 0.30  # Band C
    cc = 40.0 + peacock * 195.0 + oxide_mottle * 80.0           # blue where hot
    # straw-gold zone (low Cc, high M) is the band trough

    # zone selector along the band for Z1/Z2/Z3 color identity
    straw = np.clip(1.0 - np.abs(band_phase - 0.15) / 0.18, 0.0, 1.0)   # gold
    blue = np.clip(1.0 - np.abs(band_phase - 0.50) / 0.22, 0.0, 1.0)    # peacock
    soot = np.clip(1.0 - np.abs(band_phase - 0.85) / 0.20, 0.0, 1.0)    # cold

    # --- R carries the SOOT grain: anisotropic streaks stretched ALONG flow ----
    # directional Gaussian: smooth along u, rough across v -> streaky
    soot_streak = _fbm((wh, ww), s + 31, base_freq=18.0, octaves=3)
    soot_streak = _blur(soot_streak, 0.4)
    # stretch along pipe by blurring more along-axis (cheap directional)
    soot_streak_along = _blur(soot_streak, 1.2)
    soot_grain = soot_streak * 0.45 + soot_streak_along * 0.55
    r = 40.0 + soot * 170.0 + soot_grain * 60.0 + blue * 15.0
    r = r + straw * 0.0  # gold zone stays low R (shiny)

    # --- M carries the WELD-BEAD SEAM ridge (separate meandering corridor) -----
    core, halo = _ridge_corridor(ws, s + 41, freq=2.0, wander=0.16, thick=0.012)
    # M base from temper zones + bright weld seam (M-dominant red)
    m = 70.0 + straw * 150.0 + blue * 40.0 + soot * 0.0
    m = m + core * 185.0 + halo * 45.0                          # weld bead bright

    # --- angle gates (#5): weld-seam M flashes at diag_a, peacock Cc at v -------
    seam_gate = _cx_directional_mask(ws, "diag_a", s + 7, freq=58.0)
    cc_gate = _cx_directional_mask(ws, "v", s + 9, freq=42.0)
    m = m + core * (seam_gate - 0.5) * 60.0
    cc = cc + blue * (cc_gate - 0.5) * 70.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)

    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- Band D FULL-RES: crisp scale-flake sparkle on R+Cc + nano fringe Cc ----
    flake = _sparse_pins_full((h, w), s + 71, density=0.010, sharp=0.6)
    R = R + flake * 90.0                                        # crusty oxide R
    CC = CC + flake * 80.0                                      # + cyan flakes
    CC = CC + (_nano_fringe((h, w), s + 77) - 0.5) * 18.0       # mip-0 glint
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 2) volcanic - cooling basalt with THREE-WAY PLATE-ZONE IDENTITY. Every Voronoi
#    cell is typed obsidian / lava / ash-crust and carries its OWN (M,R,Cc)
#    triplet, so the composite shows distinct magenta + yellow + cyan zones
#    instead of one green field. Crack network is a fourth, separate geometry.
# ════════════════════════════════════════════════════════════════════════════
def spec_volcanic(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. JUDGE-FIX (round 1): v2a collapsed to a
    # GREEN R-field with thin red veins (~1.5 hues) because R was a broad
    # crust_mottle blanket. REDO: assign EACH columnar plate one of three zone
    # TYPES, each with its OWN triplet so channel MEANS vary region-to-region ->
    #   obsidian plates  = M+Cc (cooled glass, reads MAGENTA, R held LOW/shiny)
    #   lava windows      = M+R  (white-hot rock, reads YELLOW->white)
    #   ash crust plates  = R+Cc (rough oxidised ash, reads CYAN)
    # The crack corridors run M+R (hot fissures). Four DECORRELATED geometries:
    # plate-type voronoi (zone id), crack distance field (M), per-zone roughness
    # (R), lava-window + cooling-halo (Cc). No single channel paints the tile.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "volcanic")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)

    # --- Band A: primary Voronoi columnar plates + per-cell ZONE TYPE ----------
    cid, d1, d2 = _voronoi(ws, s + 3, n_sites=34)
    edge = d2 - d1                                              # small on edges
    crack = np.clip(1.0 - edge / 0.045, 0.0, 1.0)              # fissure mask
    crack = crack * crack
    plate = 1.0 - crack                                        # cell interiors
    n_sites = int(cid.max()) + 1
    rng = np.random.RandomState((s + 51) & 0x7FFFFFFF)
    # deterministically label each cell 0=obsidian 1=lava 2=ash (~45/20/35)
    roll = rng.uniform(0.0, 1.0, n_sites)
    zone = np.where(roll < 0.45, 0, np.where(roll < 0.65, 1, 2)).astype(np.int32)
    z_obs = (zone[cid] == 0).astype(np.float32) * plate        # magenta plates
    z_lav = (zone[cid] == 1).astype(np.float32) * plate        # white-hot windows
    z_ash = (zone[cid] == 2).astype(np.float32) * plate        # cyan crust
    z_obs = _blur(z_obs, 0.8); z_lav = _blur(z_lav, 0.8); z_ash = _blur(z_ash, 0.8)

    # --- Band B: secondary sub-cracks within large plates (smaller Voronoi) ----
    cid2, e1, e2 = _voronoi(ws, s + 17, n_sites=110)
    subedge = e2 - e1
    subcrack = np.clip(1.0 - subedge / 0.022, 0.0, 1.0)
    subcrack = (subcrack * subcrack) * plate * 0.6             # only inside plates
    fissure = np.clip(crack + subcrack, 0.0, 1.0)

    # per-zone roughness micro-texture (Band C, own field) - DOES NOT blanket R;
    # it only adds variance INSIDE each zone, weighted by that zone's R appetite.
    obs_grain = _fbm(ws, s + 29, base_freq=16.0, octaves=3)    # glassy fine grain
    ash_grain = _fbm(ws, s + 33, base_freq=9.0, octaves=4)     # coarse ash grain
    lava_swirl = _fbm(ws, s + 37, base_freq=6.0, octaves=3)    # flowing magma

    # --- M = crack fissures (hot, M+R) + lava plates + a touch in obsidian ------
    m = 30.0
    m = m + fissure * 175.0                                     # bright hot cracks
    m = m + z_lav * (150.0 + lava_swirl * 60.0)                # molten plate body
    m = m + z_obs * (70.0 + obs_grain * 30.0)                  # obsidian carries M
    m = m - z_ash * 10.0                                        # ash low M

    # --- R = ROUGH only in ash/crust + crack walls; obsidian & lava are SHINY ---
    # this is the key monopoly-breaker: R is now zone-gated, NOT a global field.
    r = 32.0
    r = r + z_ash * (150.0 + ash_grain * 80.0)                # rough oxidised ash
    r = r + z_lav * (40.0 + lava_swirl * 70.0)                # crusting lava skin
    r = r + fissure * 60.0                                     # crack walls rough
    r = r - z_obs * 8.0                                        # obsidian glass-shiny

    # --- Cc = obsidian gloss (magenta) + ash sheen (cyan) + lava cooling rim ----
    is_lava_window = (zone == 1)
    lava_cell = is_lava_window[cid].astype(np.float32)
    if _HAVE_CV2:
        dil = cv2.dilate(lava_cell, np.ones((5, 5), np.uint8))
        rim = np.clip(dil - lava_cell, 0.0, 1.0)
        rim = _blur(rim, 0.8)
    else:
        rim = np.zeros_like(lava_cell)
    cc = 28.0
    cc = cc + z_obs * (165.0 + obs_grain * 45.0)              # cooled-glass clearcoat
    cc = cc + z_ash * (70.0 + ash_grain * 35.0)               # ash micro-sheen (cyan)
    cc = cc + rim * 120.0                                      # cooling-rim halo glow
    cc = cc + z_lav * 35.0

    # --- angle reveal (#5): obsidian Cc flips, lava rim ignites at reveal -------
    obs_gate = _cx_directional_mask(ws, "diag_b", s + 7, freq=50.0)
    cc = cc + z_obs * (obs_gate - 0.5) * 70.0
    reveal = _cx_buried_reveal_gate(ws, s, 7310, density=0.006, layers=5)
    m = m + z_lav * (reveal - 0.4) * 60.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- Band D FULL-RES: ember pin grid along fissures + micro-vesicle pits ----
    fissure_full = _wild_upscale(fissure, h, w)
    lav_full = _wild_upscale(z_lav, h, w)
    embers = _sparse_pins_full((h, w), s + 83, density=0.018, sharp=0.7)
    embers = embers * ((fissure_full > 0.25) | (lav_full > 0.4))   # cracks + lava
    M = M + embers * 150.0
    R = R + embers * 80.0                                       # ember = yellow-hot
    CC = CC + embers * 30.0
    pits = _sparse_pins_full((h, w), s + 91, density=0.006, sharp=0.5)
    R = R + pits * 55.0                                         # vesicle roughness
    CC = CC + (_nano_fringe((h, w), s + 95) - 0.5) * 14.0       # obsidian glint
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 3) shokk_inferno - OWNER HERO. Heat-diffusion-grown crack corridors with a
#    narrow Cc WHITE-HOT core nested inside a wider M glow halo. TRUE all-high
#    white crack core (only all-high zone in heat_molten) + BLACK cooling skin.
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_inferno(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. shokk_inferno = OWNER HERO molten: magma
    # plates + white-hot crack corridors. Cc=narrow white-hot CORE, M=wider glow
    # HALO (core != halo geometry, grown by iterative diffusion dilation),
    # R=cooling BLACK skin anti-correlated with cracks. Arbiter: TRUE all-high
    # white core (verify 255) + black-skin anchor. Hues: white+red/magenta+green.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "shokk_inferno")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)

    # --- Band A: magma convection plates + primary crack skeleton --------------
    cid, d1, d2 = _voronoi(ws, s + 3, n_sites=22)
    skel = np.clip(1.0 - (d2 - d1) / 0.05, 0.0, 1.0)
    skel = (skel * skel)                                       # sharp seed cracks

    # --- heat-diffusion grow: iterative max-blur dilation (3-4 passes) ---------
    hot = skel.copy()
    for _ in range(4):
        if _HAVE_CV2:
            grown = cv2.dilate(hot, np.ones((3, 3), np.float32))
            grown = _blur(grown, 1.1)
        else:
            grown = _blur(hot, 1.1)
        hot = np.maximum(hot * 0.5, grown * 0.92)              # diffused glow
    glow = _norm(hot) ** 1.4                                    # wide M halo, headroom
    # narrow Cc core: only the HOTTEST sliver of the skeleton -> a THIN white line.
    # skel peaks at 1.0 exactly on the Voronoi edge; threshold near the top keeps
    # the all-high white corridor to ~1-2% of pixels (verified in self-test).
    core = np.clip((skel - 0.90) * 9.0, 0.0, 1.0)            # narrow Cc core
    core_full_intent = core.copy()

    # plate-body warmth (deep orange) inside plates
    plate_warm = _fbm(ws, s + 13, base_freq=5.0, octaves=3)
    crack_dist = glow                                          # near 1 on cracks

    # --- M = broad GLOW HALO + plate-body warmth (red-magenta) -----------------
    m = 55.0 + glow * 135.0 + plate_warm * 35.0
    # secondary orange vein network (thinner 2nd crack gen) -> M only
    cid2, v1, v2 = _voronoi(ws, s + 27, n_sites=70)
    veins = np.clip(1.0 - (v2 - v1) / 0.02, 0.0, 1.0)
    veins = (veins * veins) * (1.0 - glow)                     # away from main
    m = m + veins * 90.0

    # --- Cc = narrow WHITE-HOT CORE (sharpest, highest -> TRUE 255) -------------
    # broad magma-plate Cc warmth so the plate body reads red-MAGENTA (M+Cc), not
    # pure red; the thin core sits far above this and blows to true white. The
    # broad warmth rides plate_warm + its OWN independent bloom field (NOT glow)
    # so Cc geometry diverges from M's glow-halo (keeps |M,Cc| well under 0.85).
    bloom = _fbm(ws, s + 47, base_freq=4.0, octaves=3)        # own Cc body field
    cc = 55.0 + core * 200.0                                   # core blows white
    cc = cc + (plate_warm * 0.5 + bloom * 0.5) * 95.0          # warm magenta body

    # --- R = COOLING BLACK SKIN on plate centers AWAY from cracks (green) -------
    # anti-correlated with crack distance field, computed independently
    skin_blob = _fbm(ws, s + 37, base_freq=6.0, octaves=3)
    skin = np.clip((skin_blob - 0.4) * 2.0, 0.0, 1.0) * (1.0 - glow)
    r = 40.0 + skin * 200.0                                    # high-rough charred
    r = r - glow * 30.0                                        # cracks shiny-hot
    # BLACK anchor: cooling skin also drags M+Cc hard down to near-black there
    # (the cooling-black-skin BLACK zone the arbiter calls for: high R, low M/Cc).
    black = skin * (1.0 - core)
    m = m - black * 90.0
    cc = cc - black * 110.0

    # --- angle reveal (#5): Cc core gated axis u, M halo gated axis v -----------
    cc_gate = _cx_directional_mask(ws, "u", s + 5, freq=60.0)
    m_gate = _cx_directional_mask(ws, "v", s + 8, freq=44.0)
    cc = cc + core * (cc_gate - 0.5) * 50.0
    m = m + glow * (m_gate - 0.5) * 55.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- Band D FULL-RES: spark ejecta + ENFORCE true-255 white-hot crack core --
    core_full = _wild_upscale(core_full_intent, h, w)
    # along the THIN crack core push BOTH M and Cc to a true all-high white (=255)
    # -> the only all-high zone in heat_molten (arbiter requirement). Thin so the
    # broad-clip stays well under 1%; verified true 255 in the self-test below.
    white_line = (core_full > 0.90)
    M = np.where(white_line, 255.0, M)
    CC = np.where(white_line, 255.0, CC)
    R = np.where(white_line, np.minimum(R, 28.0), R)           # core not rough
    # spark ejecta: sparse crisp pins, but only let them blow to white where the
    # surrounding glow is NOT already near-max (so they read as discrete sparks,
    # not broad saturation).
    sparks = _sparse_pins_full((h, w), s + 73, density=0.010, sharp=0.7)
    spark_room = np.clip((230.0 - M) / 60.0, 0.0, 1.0)
    M = M + sparks * 120.0 * spark_room
    CC = CC + sparks * 130.0 * np.clip((230.0 - CC) / 60.0, 0.0, 1.0)  # magenta-white
    CC = CC + (_nano_fringe((h, w), s + 79) - 0.5) * 16.0
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 4) plasma_metal - anodized titanium under plasma arc. Per-channel PHASE-OFFSET
#    interference sine-sheets -> rainbow hues emerge from M/R/Cc band OVERLAP.
# ════════════════════════════════════════════════════════════════════════════
def spec_plasma_metal(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. JUDGE-FIX (round 2): v2a read as a soft
    # low-frequency PASTEL BLOB field - multi-hue but the most generic-noise tile
    # in the grid, no sharp 'plasma' (arc filaments) or 'metal' (flake) structure,
    # frequency dominated by low/mid octaves. REDO per judge: KEEP the pastel
    # thin-film interference as the MACRO base but knock its amplitude down, then
    # layer TWO sharper higher-frequency bands ON TOP so the name reads:
    #   'plasma' = a BRANCHING ARC-FILAMENT network (Lichtenberg-style random-walk
    #              corridors with HARD white-hot cores + violet halos), and
    #   'metal'  = dense crisp metallic micro-FLAKE sparkle (full-res NEAREST dots)
    #              + anisotropic brushed grain on R.
    # Channels stay decorrelated: interference sheets each have their OWN
    # orientation, the arc network owns its own geometry (core=Cc white, halo=M
    # violet, R suppressed on arcs), flake rides M+Cc, brush rides R.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "plasma_metal")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)
    x, y = _coords(ws)

    # ---- MACRO BAND A: thin-film interference pastel, AMPLITUDE REDUCED so it is
    # a backdrop the sharper bands sit on, not the whole motif. Each channel gets
    # its OWN orientation so the rainbow stays (decorrelation engine), but the
    # sheets are pushed to higher freq than v2a so even the backdrop is less blobby.
    warp = (_fbm(ws, s + 11, base_freq=3.0, octaves=3) - 0.5) * 0.6
    def sheet(phase, fa, fb, ori):
        co, si = np.cos(ori), np.sin(ori)
        p1 = x * co + y * si
        p2 = -x * si + y * co
        a = np.sin((p1 * fa + warp + phase) * np.pi)
        b = np.sin((p2 * fb + warp * 0.7 + phase * 1.3) * np.pi)
        c = np.sin((p1 * (fb * 2.1) + p2 * (fa * 1.7) + phase * 0.6) * np.pi)
        return 0.5 + 0.5 * (a * 0.5 + b * 0.35 + c * 0.15)

    # higher base freqs than v2a (7->11 etc) so the macro field carries mid detail
    m_sheet = sheet(phase=0.00, fa=11.0, fb=14.0, ori=0.20)
    r_sheet = sheet(phase=0.62, fa=12.6, fb=11.0, ori=1.30)
    cc_sheet = sheet(phase=1.27, fa=9.7, fb=15.4, ori=2.45)

    # ---- MID BAND B: BRUSHED anisotropic metal grain baked into R (own geometry)
    brush = _fbm((wh, ww), s + 23, base_freq=26.0, octaves=2)
    brush = _blur(brush, 0.3)
    brush_h = _blur(brush, 2.2)                                # horizontal streak
    brush_grain = brush * 0.4 + brush_h * 0.6

    # pastel backdrop is now ~140 amplitude (was 200/205) -> headroom for arcs and
    # so the broad Cc field stays clear of 255 even at small preview work-shapes
    # (the white-hot arc CORE is the only thing that should reach 255).
    m = 48.0 + m_sheet * 150.0
    r = 44.0 + r_sheet * 120.0 + brush_grain * 60.0
    cc = 46.0 + cc_sheet * 138.0

    # ---- MID BAND C: PLASMA ARC FILAMENT NETWORK -----------------------------
    # a branching Lichtenberg random-walk arc tree rasterised into `arc`; this is
    # the hard 'plasma' structure the judge wanted (sharp filaments, not blobs).
    arc = np.zeros(ws, dtype=np.float32)
    rng = np.random.RandomState((s + 61) & 0x7FFFFFFF)

    def arc_walk(x0, y0, ang0, length, width, depth):
        n = max(6, int(length * 70))
        xs = np.empty(n, np.float32); ys = np.empty(n, np.float32)
        ang = ang0; px, py = x0, y0
        for i in range(n):
            ang += rng.uniform(-0.30, 0.30)
            px += np.cos(ang) * (length / n)
            py += np.sin(ang) * (length / n)
            xs[i] = px; ys[i] = py
        ix = np.clip((xs * (ww - 1)).astype(np.int32), 0, ww - 1)
        iy = np.clip((ys * (wh - 1)).astype(np.int32), 0, wh - 1)
        vals = np.linspace(1.0, 0.30, n).astype(np.float32) * width
        np.maximum.at(arc, (iy, ix), vals)
        if depth > 0:
            for _ in range(rng.randint(1, 4)):
                k = rng.randint(n // 4, n)
                arc_walk(xs[k], ys[k], ang0 + rng.uniform(-1.2, 1.2),
                         length * rng.uniform(0.4, 0.65), width * 0.72, depth - 1)

    # several independent strikes seeded across the canvas for full coverage
    arc_walk(0.12, 0.10, 0.65, 1.05, 1.0, 3)
    arc_walk(0.88, 0.18, 2.45, 0.85, 0.9, 3)
    arc_walk(0.45, 0.92, -1.15, 0.80, 0.85, 2)
    arc_walk(0.05, 0.70, 0.10, 0.75, 0.8, 2)
    arc_walk(0.70, 0.55, 3.0, 0.70, 0.8, 2)
    arc = _blur(arc, 0.5)
    arc = _norm(arc)
    arc_core = np.clip((arc - 0.55) * 3.2, 0.0, 1.0)          # thin white-hot core
    if _HAVE_CV2:
        arc_halo = cv2.dilate(arc, np.ones((5, 5), np.float32))
        arc_halo = _blur(arc_halo, 2.2)
    else:
        arc_halo = _blur(arc, 2.2)
    arc_halo = _norm(arc_halo)

    # M = violet CORONA halo (wide) + a touch of core ; Cc = white CORE (thin);
    # R is SUPPRESSED on the arcs so filaments read shiny/hot (M+Cc -> magenta-white)
    m = m + arc_halo * 150.0 + arc_core * 80.0
    cc = cc + arc_core * 190.0 + arc_halo * 50.0
    r = r - arc_halo * 95.0 - arc_core * 40.0

    # ---- angle reveal (#5): 3 sheets + arc slide at DIFFERENT rates (axes differ)
    m = m + m_sheet * (_cx_directional_mask(ws, "u", s + 5, freq=64.0) - 0.5) * 45.0
    r = r + r_sheet * (_cx_directional_mask(ws, "diag_a", s + 8, freq=58.0) - 0.5) * 45.0
    cc = cc + cc_sheet * (_cx_directional_mask(ws, "v", s + 12, freq=52.0) - 0.5) * 45.0
    cc = cc + arc_core * (_cx_directional_mask(ws, "diag_b", s + 15, freq=78.0) - 0.5) * 50.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # ---- HIGH BAND D FULL-RES: metallic micro-FLAKE sparkle (the 'metal' read) --
    # dense crisp NEAREST dots so single-pixel flake survives at mip-0; rides M+Cc
    # (flake catches light = bright magenta-white specks) plus a sparser coarse set.
    # flake rides M+Cc but with HEADROOM gating so dense flake does not push the
    # broad-clip over 1% on Cc at ANY resolution: a speck only blows bright where
    # Cc has room (knee well below 255 so even NEAREST upsample stays sub-1%).
    flake = _sparse_pins_full((h, w), s + 71, density=0.022, sharp=0.55)
    cc_room = np.clip((222.0 - CC) / 80.0, 0.0, 1.0)
    M = M + flake * 105.0
    CC = CC + flake * 78.0 * cc_room
    R = R - flake * 25.0                                       # flake face = shiny
    flake2 = _sparse_pins_full((h, w), s + 75, density=0.008, sharp=0.35)
    M = M + flake2 * 70.0
    CC = CC + flake2 * 48.0 * cc_room
    # enforce a true white-hot pixel on the brightest arc cores, but INTERSECTED
    # with a sparse full-res pin mask so the forced-255 set is always a thin
    # sliver (a few % of the already-narrow core) regardless of resolution -> the
    # broad Cc clip stays under 1% even at tiny preview work-shapes, while the
    # true white-hot glint character of the plasma arc is preserved.
    arc_core_full = _wild_upscale(arc_core, h, w)
    glint = _sparse_pins_full((h, w), s + 79, density=0.25, sharp=0.0)
    white_arc = (arc_core_full > 0.94) & (glint > 0.5)
    CC = np.where(white_arc, 255.0, CC)
    M = np.where(white_arc, np.maximum(M, 235.0), M)
    R = R + (_nano_fringe((h, w), s + 77) - 0.5) * 14.0
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 5) plasma_core - ARBITER: off-center SPIRAL filaments (M dominant) + radius-
#    scaled turbulent haze (R), spiral+turbulence (soft churning), NOT rings.
# ════════════════════════════════════════════════════════════════════════════
def spec_plasma_core(shape, seed, sm, base_m, base_r):
    # wild-spec-v2-straggler-fix 2026-06-07: owner rejected v1 as lazy and flagged
    # the v2 plasma_core SPIRAL geometry as a DUPLICATE of shokk_vortex (vortex now
    # owns spirals exclusively). REBUILD per directive = MAGNETIC CONTAINMENT CORE,
    # a "star in a bottle" with NO spiral and NO rings:
    #   * one blinding central CORE ORB (all-high triplet -> the only white zone),
    #   * 2-3 NESTED OFF-AXIS ELLIPTICAL containment SHELLS (true ellipses with
    #     their own centre/aspect/tilt -> NOT circular rings, which neutron_star /
    #     shokk_pulse own; the off-axis nesting is the key non-circular tell),
    #   * smooth curved plasma filament ARCS that follow field lines BETWEEN shells
    #     (a tangential-flow sine field, smooth -> NOT the branching lightning that
    #     shokk_surge owns), and
    #   * fine plasma-turbulence GRAIN inside the shells as the high band.
    # TRIPLET ZONES: core ORB = M+Cc (magenta-white blinding read); the shells
    # ALTERNATE triplet identity by index (shell 0 = R+Cc cyan magnetic skin,
    # shell 1 = M+R yellow ionised wall, shell 2 = M+Cc magenta confinement) so the
    # composite carries cyan/yellow/magenta bands; arcs are R-LOW hot corridors
    # (M+Cc) threading the field; the inter-shell void is the green/low rest field.
    # FOUR DECORRELATED GEOMETRIES: elliptical-radius shell field (drives shells),
    # tangential field-line arc field (drives arcs), radial-falling Gaussian orb
    # (drives core), and an independent fbm turbulence (drives grain) -> M, R, Cc
    # each combine these differently so channel correlations stay well under 0.85.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "plasma_core")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)
    x, y = _coords(ws)
    rng = np.random.RandomState((s + 3) & 0x7FFFFFFF)

    # --- Band A: ELLIPTICAL containment field. An off-centre, TILTED, aspect!=1
    # radius so iso-contours are ellipses (not circles). A low-freq domain warp
    # makes the shells breathe/pinch like a confined plasma. ---------------------
    cx = 0.42 + rng.uniform(-0.04, 0.04)                      # off-centre core
    cy = 0.46 + rng.uniform(-0.04, 0.04)
    tilt = 0.55 + rng.uniform(-0.12, 0.12)                    # ellipse major axis tilt
    aspect = 1.7 + rng.uniform(-0.2, 0.2)                     # elongation (>1 -> ellipse)
    ct, st = np.cos(tilt), np.sin(tilt)
    dx = x - cx
    dy = y - cy
    ex = (dx * ct + dy * st)                                  # along major axis
    ey = (-dx * st + dy * ct) * aspect                        # across (squeezed)
    warp = (_fbm(ws, s + 11, base_freq=2.5, octaves=3) - 0.5) * 0.10
    e_rad = np.sqrt(ex * ex + ey * ey) + warp                # elliptical radius
    e_rad_n = np.clip(e_rad / 0.62, 0.0, 1.0)
    theta_e = np.arctan2(ey, ex)                             # angle in ellipse frame

    # --- nested elliptical SHELLS: pick 3 radii; each is a soft elliptical band.
    shell_radii = (0.20, 0.355, 0.52)
    shell_w = (0.045, 0.050, 0.058)                          # band half-thickness
    shell_band = []
    for rr, hw_ in zip(shell_radii, shell_w):
        b = np.clip(1.0 - np.abs(e_rad - rr) / hw_, 0.0, 1.0)
        b = b * b                                            # crisp band walls
        shell_band.append(b.astype(np.float32))
    shellA, shellB, shellC = shell_band                     # 0=inner 1=mid 2=outer
    shells_any = np.clip(shellA + shellB + shellC, 0.0, 1.0)

    # --- Band B: smooth field-line ARCS BETWEEN shells. Magnetic field lines run
    # TANGENTIALLY around the core; a smooth sine in the ellipse angle, phase-
    # advanced by radius, gives curved corridors that hug the shells WITHOUT being
    # spirals (no radius->angle winding term) and without branching. The arcs live
    # in the gaps BETWEEN shells (suppressed on the shells themselves). -----------
    field_line = np.sin((theta_e * 6.0 + warp * 6.0) * 1.0) \
        + 0.5 * np.sin((theta_e * 11.0 - warp * 4.0) * 1.0)
    arc_raw = 1.0 - np.clip(np.abs(field_line) * 0.85, 0.0, 1.0)
    arc = np.clip((arc_raw - 0.40) * 2.4, 0.0, 1.0)
    inter_shell = np.clip(1.0 - shells_any, 0.0, 1.0)        # gaps between shells
    # arcs only inside the confinement envelope, fading past the outer shell
    envelope = np.clip(1.0 - np.clip((e_rad - 0.55) / 0.18, 0.0, 1.0), 0.0, 1.0)
    arc = arc * inter_shell * envelope
    arc = _blur(arc, 0.5)

    # --- Band C: fine plasma turbulence GRAIN, gated to live INSIDE the shells ---
    turb = _fbm(ws, s + 29, base_freq=22.0, octaves=4)       # high-band churn
    turb2 = _fbm(ws, s + 37, base_freq=9.0, octaves=3)       # mid swirl
    grain = (turb * 0.6 + turb2 * 0.4)
    shell_grain = grain * shells_any                         # roughens shell walls

    # --- central CORE ORB: tight elliptical Gaussian -> the all-high white zone --
    orb = np.exp(-(e_rad * e_rad) / (2.0 * 0.085 ** 2))
    orb_halo = np.exp(-(e_rad * e_rad) / (2.0 * 0.17 ** 2))  # wider magenta halo

    # ---- M = core orb + field-line arcs (hot) + shell-B/C ionised+confine walls -
    # arcs read M+Cc (hot corridors, R held low); core orb M-dominant (with Cc).
    m = 38.0
    m = m + orb * 175.0 + orb_halo * 55.0                    # blinding core (M)
    m = m + arc * (150.0 + grain * 30.0)                     # hot field-line arcs
    m = m + shellB * (135.0 + turb2 * 35.0)                  # ionised wall (yellow w/ R)
    m = m + shellC * (95.0 + turb2 * 25.0)                   # confinement (magenta w/ Cc)
    m = m - shellA * 10.0                                    # inner skin low M (cyan)

    # ---- R = shell-A magnetic skin roughness + shell-B ionised grit; LOW on arcs
    # and on the core (hot/shiny). Driven by its OWN turbulence field so R is
    # decorrelated from M's orb/arc geometry. ----------------------------------
    r = 36.0
    r = r + shellA * (150.0 + grain * 70.0)                  # rough magnetic skin (cyan w/ Cc)
    r = r + shellB * (95.0 + turb * 60.0)                    # ionised grit (yellow w/ M)
    r = r + shell_grain * 35.0                               # general shell-wall grain
    r = r + inter_shell * (turb2 * 55.0)                     # void micro-roughness (own field)
    r = r - arc * 95.0                                       # arcs = shiny hot corridors
    r = r - orb * 120.0                                      # core mirror-shiny
    r = r - orb_halo * 30.0

    # ---- Cc = core gloss + shell-A skin sheen + shell-C confinement glaze; arcs
    # carry a wet sheen too (so arcs read M+Cc magenta-hot). LOW on shell-B (yellow)
    cc = 30.0
    cc = cc + orb * 185.0 + orb_halo * 70.0                  # core clearcoat blooms white
    cc = cc + shellA * (140.0 + grain * 35.0)               # magnetic skin sheen (cyan w/ R)
    cc = cc + shellC * (120.0 + turb2 * 30.0)               # confinement glaze (magenta w/ M)
    cc = cc + arc * 80.0                                     # arc wet-hot corridor sheen
    cc = cc - shellB * 12.0                                  # ionised wall low Cc (yellow)

    # --- angle reveal (#5): arcs flash on one axis, shell skin sheen on another
    # (opposing senses) so the field lines and shells light at different pan angles
    m = m + arc * (_cx_directional_mask(ws, "diag_a", s + 5, freq=70.0) - 0.5) * 55.0
    cc = cc + shellA * (_cx_directional_mask(ws, "v", s + 9, freq=52.0) - 0.5) * 50.0
    r = r + shellB * (_cx_directional_mask(ws, "u", s + 13, freq=60.0) - 0.5) * 40.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- Band D FULL-RES: plasma sparks along the field-line arcs + ENFORCE a true
    # all-high white core orb. Sparks are crisp full-res pins gated to the arcs so
    # the hot corridors twinkle; the orb is forced to true 255 on M+Cc only on its
    # tight peak (thin -> broad clip stays <1%), the lone all-high zone. ---------
    orb_full = _wild_upscale(orb, h, w)
    arc_full = _wild_upscale(arc, h, w)
    sparks = _sparse_pins_full((h, w), s + 73, density=0.018, sharp=0.7)
    sparks = sparks * (arc_full > 0.25)                      # twinkle along field lines
    M = M + sparks * 125.0
    CC = CC + sparks * 130.0
    white_core = (orb_full > 0.86)                           # tight blinding core
    M = np.where(white_core, 255.0, M)
    CC = np.where(white_core, 255.0, CC)
    R = np.where(white_core, np.minimum(R, 30.0), R)         # core not rough
    CC = CC + (_nano_fringe((h, w), s + 79) - 0.5) * 14.0
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 6) shokk_reactor - STRICT SQUARE lattice driven by THREE INDEPENDENT reactor
#    sub-motifs on OFFSET grids: control-rod busbars (M), coolant lattice (R),
#    fuel-pellet cores with bloom (Cc). Per-cell TYPE spans the full gamut
#    (white-hot cells -> all-high white, scram/graphite -> all-low black).
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_reactor(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. JUDGE-FIX (round 1): v2a read GREEN with
    # faint dots (R mean ~176) because R was a broad coolant fbm + cell-gap fill
    # blanketing the whole tile. REDO per judge: drive the three channels from
    # THREE DIFFERENT reactor sub-motifs on OFFSET grids so each owns its own
    # geometry, and TYPE each cell so the grid spans the full hue gamut:
    #   M  = control-rod VERTICAL BUSBARS (offset half-cell in x)
    #   R  = COOLANT LATTICE channels (thin lines between rods, NOT a blanket)
    #   Cc = fuel-PELLET cores with bloom halo (Gaussian nodes)
    #   cell types: white-hot (all-high white) / amber (M+R yellow) /
    #               cool-coolant (R+Cc cyan) / scram-graphite (all-low black).
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "shokk_reactor")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)
    x, y = _coords(ws)

    cells = 9.0                                                # ~side-mirror spacing
    cu = (x * cells) % 1.0
    cv = (y * cells) % 1.0
    du = cu - 0.5; dv = cv - 0.5
    node_d = np.sqrt(du * du + dv * dv)                        # to cell centre

    # --- per-cell TYPE field (the gamut-spanner) -------------------------------
    iu = np.floor(x * cells).astype(np.int32)
    iv = np.floor(y * cells).astype(np.int32)
    cell_hash = ((iu * 73856093) ^ (iv * 19349663) ^ (s + 31)) & 1023
    t_white = (cell_hash < 200).astype(np.float32)            # ~20% all-high white
    t_amber = ((cell_hash >= 200) & (cell_hash < 480)).astype(np.float32)  # ~27%
    t_cool = ((cell_hash >= 480) & (cell_hash < 840)).astype(np.float32)   # ~35%
    t_scram = (cell_hash >= 840).astype(np.float32)           # ~18% black graphite
    # cell-body fill (a soft rounded square covering most of each cell, so a cell's
    # triplet identity colours its WHOLE area, not just the thin motif lines) -----
    cell_body = np.clip(1.0 - (np.maximum(np.abs(du), np.abs(dv)) - 0.18) / 0.30,
                        0.0, 1.0)

    # --- Cc sub-motif = FUEL-PELLET CORES (Gaussian bloom at cell centre) -------
    node_glow = np.exp(-(node_d * node_d) / (2.0 * 0.20 ** 2))
    pellet = node_glow
    # Cc lives in white + cool cells (Cherenkov/clearcoat), dark in amber/scram
    cc = 30.0
    cc = cc + pellet * (t_white * 210.0 + t_cool * 175.0 + t_amber * 25.0)
    cc = cc + cell_body * (t_white * 90.0 + t_cool * 95.0)    # broad cell clearcoat

    # --- M sub-motif = CONTROL-ROD BUSBARS (vertical bars, OFFSET grid in x) -----
    bu = ((x + 0.5 / cells) * cells) % 1.0                    # half-cell x offset
    busbar = np.clip(1.0 - np.abs(bu - 0.5) / 0.22, 0.0, 1.0)
    busbar = busbar * busbar                                  # crisp vertical rods
    rod_mottle = _fbm(ws, s + 19, base_freq=20.0, octaves=2)  # rod-surface fine grain
    m = 28.0
    m = m + busbar * (t_white * 200.0 + t_amber * 195.0 + t_cool * 40.0) \
          * (0.78 + 0.22 * rod_mottle)
    m = m + cell_body * (t_white * 120.0 + t_amber * 110.0)   # broad cell metal fill
    m = m + t_white * pellet * 60.0                           # white cores glow M too

    # --- R sub-motif = COOLANT LATTICE (thin channel lines on a 2nd offset grid) -
    # horizontal + vertical thin coolant channels: a LATTICE, not a blanket field.
    lu = (x * cells) % 1.0
    lv = ((y + 0.5 / cells) * cells) % 1.0                    # half-cell y offset
    chan = np.maximum(np.clip(1.0 - np.abs(lu - 0.0) / 0.09, 0.0, 1.0),
                      np.clip(1.0 - np.abs(lv - 0.5) / 0.11, 0.0, 1.0))
    chan = chan * chan
    cool_grain = _fbm(ws, s + 23, base_freq=15.0, octaves=3)  # turbulent coolant
    r = 34.0
    r = r + chan * (70.0 + cool_grain * 70.0)                 # coolant channel roughness
    r = r + t_cool * cell_body * (130.0 + cool_grain * 50.0)  # cool cells = wet rough (cyan w/ Cc)
    r = r + t_amber * cell_body * 150.0                       # amber rods rough (yellow w/ M)
    r = r + t_white * cell_body * 120.0                       # white cells fully lit
    r = r - t_scram * 6.0                                     # scram graphite = matte-dark all

    # scram/graphite cells pull EVERYTHING down (black anchor) ------------------
    black = t_scram * cell_body
    m = m - black * 36.0
    cc = cc - black * 36.0

    # --- angle reveal (#5): pellets ignite at reveal, busbars flash on axis u ----
    reveal = _cx_buried_reveal_gate(ws, s, 7320, density=0.006, layers=5)
    cc = cc + pellet * t_white * (reveal - 0.4) * 60.0
    m = m + busbar * (_cx_directional_mask(ws, "u", s + 7, freq=82.0) - 0.5) * 45.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- Band D FULL-RES: Cherenkov sparkle pins inside lit rod centers --------
    pellet_full = _wild_upscale(pellet * (t_white + t_cool), h, w)
    cher = _sparse_pins_full((h, w), s + 73, density=0.016, sharp=0.7)
    cher = cher * (pellet_full > 0.35)
    CC = CC + cher * 130.0
    M = M + cher * 40.0
    bub = _sparse_pins_full((h, w), s + 81, density=0.007, sharp=0.5)
    R = R + bub * 50.0                                         # coolant bubble flecks
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 7) shokk_surge - captured lightning. Recursive LICHTENBERG branching filament
#    tree. Cc=sharp white bolt CORE, M=violet CORONA (wider), R=dielectric+static.
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_surge(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. shokk_surge = Lichtenberg fractal branching:
    # a recursive 1D filament tree (tapering arcs that bifurcate). Cc=sharp white
    # bolt CORE (thinnest), M=violet CORONA (dilated, wider -> M+Cc=magenta),
    # R=dark dielectric body + static speckle. Hues: green dielectric, white core,
    # magenta corona, cyan static. Built by deterministic random-walk channels.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "shokk_surge")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)

    # --- Lichtenberg branching tree via iterated random-walk segments ----------
    bolt = np.zeros(ws, dtype=np.float32)
    rng = np.random.RandomState((s + 3) & 0x7FFFFFFF)

    def walk(x0, y0, ang0, length, width, depth):
        # rasterize a tapering random walk into `bolt` (vectorized per-step stamp)
        n = max(4, int(length * 60))
        xs = np.empty(n, np.float32)
        ys = np.empty(n, np.float32)
        ang = ang0
        px, py = x0, y0
        for i in range(n):
            ang += rng.uniform(-0.35, 0.35)
            px += np.cos(ang) * (length / n)
            py += np.sin(ang) * (length / n)
            xs[i] = px
            ys[i] = py
        ix = np.clip((xs * (ww - 1)).astype(np.int32), 0, ww - 1)
        iy = np.clip((ys * (wh - 1)).astype(np.int32), 0, wh - 1)
        vals = np.linspace(1.0, 0.35, n).astype(np.float32) * width  # taper
        np.maximum.at(bolt, (iy, ix), vals)
        # spawn branches
        if depth > 0:
            nb = rng.randint(1, 4)
            for _ in range(nb):
                k = rng.randint(n // 4, n)
                walk(xs[k], ys[k], ang + rng.uniform(-1.0, 1.0),
                     length * rng.uniform(0.35, 0.6), width * 0.7, depth - 1)

    # main trunk + a couple of independent strikes
    walk(0.1, 0.15, 0.7, 1.0, 1.0, 3)
    walk(0.85, 0.2, 2.3, 0.7, 0.85, 2)
    walk(0.4, 0.9, -1.2, 0.6, 0.8, 2)

    bolt = _blur(bolt, 0.6)
    bolt = _norm(bolt)
    core = np.clip((bolt - 0.55) * 3.0, 0.0, 1.0)             # thin sharp core
    # corona = dilated glow wider than core
    if _HAVE_CV2:
        corona = cv2.dilate(bolt, np.ones((5, 5), np.float32))
        corona = _blur(corona, 2.0)
    else:
        corona = _blur(bolt, 2.0)
    corona = _norm(corona)

    # --- JUDGE-FIX (round 1): v2a was a flat GREEN dielectric bed (r=70+diel*165)
    # with thin magenta worms -> ~2 hues, "one field + a decal". REDO: the space
    # BETWEEN bolts is now broken into surge ENERGY ZONES, each carrying its OWN
    # (M,R,Cc) triplet so the background itself shows many hues:
    #   charged pools   = M+Cc (built-up potential, reads MAGENTA)
    #   discharge fronts = M+R (ionised shock, reads YELLOW)
    #   calm dielectric  = R+Cc (un-stressed insulator, reads CYAN)
    # A smooth low-freq potential field selects the zone; an independent mid-freq
    # turbulence breaks each zone internally so no zone is flat. -------------------
    pot = _fbm(ws, s + 17, base_freq=2.5, octaves=3)          # macro potential field
    pot = _norm(pot)
    z_charge = np.clip(1.0 - np.abs(pot - 0.82) / 0.30, 0.0, 1.0)   # high potential
    z_front = np.clip(1.0 - np.abs(pot - 0.50) / 0.26, 0.0, 1.0)    # discharge front
    z_calm = np.clip(1.0 - np.abs(pot - 0.16) / 0.30, 0.0, 1.0)     # relaxed insulator
    field_turb = _fbm(ws, s + 53, base_freq=11.0, octaves=4)  # Band C internal break

    # --- M = discharge fronts + charged pools + violet CORONA ------------------
    m = 26.0
    m = m + z_charge * (130.0 + field_turb * 40.0)            # charged glow (magenta w/ Cc)
    m = m + z_front * (150.0 + field_turb * 50.0)             # discharge front (yellow w/ R)
    m = m + corona * 180.0                                    # bolt violet corona
    m = m + bolt * 25.0

    # --- R = calm dielectric roughness + discharge-front ionisation (NOT a bed) --
    # R is now ZONE-GATED, not a global fbm blanket, so it no longer paints green.
    r = 32.0
    r = r + z_calm * (130.0 + field_turb * 70.0)             # rough insulator (cyan w/ Cc)
    r = r + z_front * (120.0 + field_turb * 50.0)            # ionised shock rough (yellow w/ M)
    r = r - corona * 150.0                                    # bolts not rough
    static = _fbm(ws, s + 41, base_freq=20.0, octaves=2)
    static_mask = np.clip((static - 0.6) * 2.5, 0.0, 1.0)
    r = r + static_mask * 25.0

    # --- Cc = charged-pool sheen + calm clearcoat + sharp WHITE bolt CORE -------
    cc = 28.0
    cc = cc + z_charge * (150.0 + field_turb * 35.0)         # charged sheen (magenta w/ M)
    cc = cc + z_calm * (95.0 + field_turb * 30.0)            # insulator clearcoat (cyan w/ R)
    cc = cc + core * 225.0 + corona * 55.0                   # white bolt core
    cc = cc + static_mask * 80.0                             # blue-cyan static

    # --- angle reveal (#5): core Cc gated diag_b, corona M gated diag_a (opposite)
    cc = cc + core * (_cx_directional_mask(ws, "diag_b", s + 5, freq=80.0) - 0.5) * 55.0
    m = m + corona * (_cx_directional_mask(ws, "diag_a", s + 9, freq=72.0) - 0.5) * 50.0
    cc = cc + z_charge * (_cx_directional_mask(ws, "v", s + 13, freq=46.0) - 0.5) * 55.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- Band D FULL-RES: micro-ARC sparkle (full-res crisp) + static discharge --
    front_full = _wild_upscale(z_front, h, w)
    micro_arc = _sparse_pins_full((h, w), s + 67, density=0.012, sharp=0.7)
    micro_arc = micro_arc * (front_full > 0.25)              # arcs on discharge fronts
    M = M + micro_arc * 120.0
    CC = CC + micro_arc * 120.0                              # micro-arc = white-hot
    spk = _sparse_pins_full((h, w), s + 73, density=0.014, sharp=0.6)
    CC = CC + spk * 110.0
    M = M + spk * 40.0
    CC = CC + (_nano_fringe((h, w), s + 79) - 0.5) * 14.0
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 8) shokk_blood - arterial blood / living tissue. Reaction-diffusion METABALL
#    cell blobs: M=plasma body, Cc=membrane rims + wet sheen, R=venous clots.
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_blood(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. JUDGE-FIX (round 2): v2a was heavily
    # MAGENTA/PURPLE-DOMINANT across the whole tile (the least hue-diverse map in
    # the grid) - close to single-hue, the v1 failure mode - because M was held
    # HIGH EVERYWHERE (min ~85) so M+Cc painted magenta everywhere; the motif was
    # a soft smoky swirl with weak zone structure. REDO per judge: build at least
    # TWO STRONGLY CONTRASTING triplet zones so hue (not just brightness) diverges:
    #   (1) dark VENOUS CORRIDORS - a real vascular network where M is DRIVEN LOW
    #       and R+Cc are high -> reads CYAN (R+Cc), the opposite hue from the body.
    #   (2) oxygenated bright-red CLOT CORES - compact metaball nodes that are
    #       M-DOMINANT with R+Cc held LOW -> reads pure RED/SCARLET.
    # against a magenta arterial PLASMA bed (M+Cc) between them. The key change is
    # M is NO LONGER high everywhere: the corridor mask SUBTRACTS M hard, pushing
    # R_std and CC_std apart from M and giving the composite genuine cyan+red+
    # magenta zones. High band = fine cellular/platelet micro-texture.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "shokk_blood")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)
    x, y = _coords(ws)

    # --- VENOUS CORRIDOR network (own geometry): Voronoi cell EDGES form the dark
    # vessel channels that wind between tissue plates. This is a sharp distinct
    # structure, NOT a smooth swirl. d2-d1 small => on a vessel wall. -----------
    cid, d1, d2 = _voronoi(ws, s + 5, n_sites=26)
    vwarp = (_fbm(ws, s + 11, base_freq=4.0, octaves=3) - 0.5) * 0.020
    vessel = np.clip(1.0 - (d2 - d1 + vwarp) / 0.030, 0.0, 1.0)  # narrower vessels
    vessel = vessel * vessel                                   # crisp vessel walls
    # secondary capillary net inside plates (finer Voronoi) for mid-freq detail
    cid2, e1, e2 = _voronoi(ws, s + 19, n_sites=85)
    cap = np.clip(1.0 - (e2 - e1) / 0.018, 0.0, 1.0)
    cap = (cap * cap) * (1.0 - vessel) * 0.55
    venous = np.clip(vessel + cap, 0.0, 1.0)                   # full venous mask

    # --- CLOT CORE nodes (own geometry): compact bright metaballs sitting on the
    # plate interiors, FAR from vessels (so cores != corridors). -----------------
    clotfield = _blur(_fbm(ws, s + 31, base_freq=6.0, octaves=3), 1.2)
    clot = np.clip((clotfield - 0.62) * 4.0, 0.0, 1.0)        # sparse compact cores
    clot = clot * (1.0 - venous)                              # cores avoid vessels
    clot_glow = _blur(clot, 1.5)                               # soft oxygenated halo

    # --- arterial plasma bed selector (the magenta backdrop between features) ---
    bed = (1.0 - venous) * (1.0 - clot)
    # mid-freq corpuscle texture so the bed itself is not flat (Band C)
    corpuscle = _fbm(ws, s + 23, base_freq=13.0, octaves=4)
    # independent membrane sheen field for cell rims
    cellblob = _blur(_fbm(ws, s + 41, base_freq=8.0, octaves=3), 1.0)
    cellmask = np.clip((cellblob - 0.5) * 3.0, 0.0, 1.0)
    if _HAVE_CV2:
        gx = cv2.Sobel(cellmask, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(cellmask, cv2.CV_32F, 0, 1, ksize=3)
        rim = np.sqrt(gx * gx + gy * gy)
    else:
        rim = np.abs(np.gradient(cellmask)[0]) + np.abs(np.gradient(cellmask)[1])
    rim = np.clip((_norm(_blur(rim, 0.7)) - 0.3) * 2.0, 0.0, 1.0)

    # --- M = HAEMOGLOBIN body, but DRIVEN LOW in venous corridors (the fix) -----
    # bed is magenta (mid M), clot cores are bright red (HIGH M), vessels are DARK
    # (LOW M) -> M now spans the full range instead of being high everywhere.
    # bed is crimson-DOMINANT (kept high so blood reads red-family), clot cores are
    # bright scarlet (HIGH M), vessels DARKEN M moderately (enough to read cyan
    # there, not so much the whole tile loses its blood identity).
    m = 46.0
    m = m + bed * (132.0 + corpuscle * 48.0)                  # crimson arterial plasma bed (magenta w/ Cc)
    m = m + clot_glow * 65.0                                  # oxygenated halo around cores
    m = m + clot * (155.0)                                    # bright-red clot CORE (M-dominant)
    m = m + rim * 35.0
    m = m - venous * 78.0                                     # <-- DARK venous corridors (key)

    # --- R = PLASMA VISCOSITY: an INDEPENDENT viscosity blob field DOMINATES R's
    # variance so R is decorrelated from M (which is driven by venous/clot). The
    # venous mask only ADDS a moderate wet-wall roughness on top, and clot is held
    # low; this keeps vessels reading R+Cc=cyan and clot M-only=red without making
    # R a mirror of -M (the v2b |M,R|=0.94 failure). ----------------------------
    visc_blob = _fbm(ws, s + 37, base_freq=4.5, octaves=3)    # own macro viscosity (decorrelator)
    visc_fine = _fbm(ws, s + 43, base_freq=15.0, octaves=3)   # own fine grain
    r = 60.0 + visc_blob * 95.0 + visc_fine * 50.0           # R's OWN field is the dominant term
    r = r + venous * (70.0 + corpuscle * 40.0)              # wet vessel walls add roughness (cyan)
    r = r + cap * 22.0
    r = r - clot * 50.0                                       # clot core SHINY-red (low R)
    r = r - rim * 20.0

    # --- Cc = WET SHEEN: HIGH on vessels (purple-cyan) + bed glaze, LOW on clot --
    # vessels carry strong Cc so vessel = R+Cc = CYAN; clot cores LOW Cc so they
    # stay pure red. Bed has mild Cc -> magenta. Own broad gloss + serum fields.
    wet = _fbm(ws, s + 51, base_freq=2.6, octaves=2)
    serum = _fbm(ws, s + 57, base_freq=10.0, octaves=3)
    cc = 34.0 + serum * 42.0
    cc = cc + venous * (120.0 + wet * 40.0)                  # venous wet sheen (cyan w/ R), toned down
    cc = cc + bed * (72.0 + wet * 38.0)                      # arterial glaze (magenta w/ M), raised
    cc = cc - clot * 65.0                                     # clot core matte-red (low Cc)
    cc = cc + rim * 55.0                                      # membrane gloss

    # --- angle reveal (#5): venous Cc sheen sweep, clot M flash (opposing axes) --
    sheen = _cx_directional_mask(ws, "u", s + 7, freq=42.0)
    cc = cc + venous * (sheen - 0.5) * 75.0
    m = m + clot * (_cx_directional_mask(ws, "diag_a", s + 9, freq=60.0) - 0.5) * 55.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- HIGH BAND D FULL-RES: platelet sparkle on vessel walls + clot core glint
    venous_full = _wild_upscale(venous, h, w)
    clot_full = _wild_upscale(clot, h, w)
    plat = _sparse_pins_full((h, w), s + 73, density=0.018, sharp=0.65)
    plat = plat * (venous_full > 0.3)                         # platelets line vessels
    R = R + plat * 70.0                                       # platelet = rough (cyan-ish)
    CC = CC + plat * 80.0
    oxy = _sparse_pins_full((h, w), s + 85, density=0.012, sharp=0.6)
    oxy = oxy * (clot_full > 0.25)                            # bright cells in clot cores
    M = M + oxy * 120.0                                       # oxy fleck = bright scarlet
    # fine corpuscle stipple across the bed so the magenta plasma is not flat
    corp = _sparse_pins_full((h, w), s + 91, density=0.006, sharp=0.4)
    M = M + corp * 45.0
    CC = CC + (_nano_fringe((h, w), s + 79) - 0.5) * 16.0
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# 9) shokk_fusion_base - tokamak. Over-under WOVEN helical flux-rope braid (two
#    interleaved diagonal rope sets). M=ropes, R=gaps, Cc=haze+island knots@crossings.
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_fusion_base(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. shokk_fusion_base = over-under WOVEN braid:
    # two interleaved diagonal rope sets (sine corridors along (x+y) and (x-y)).
    # M=rope strands, R=inter-rope GAPS (negative space of M), Cc=deuterium haze
    # + magnetic-island knots placed at weave CROSSING points (derived geometry
    # neither M nor R has). Hues: red/magenta ropes, green gaps, blue haze, white
    # knots, yellow neutron flashes - widest in the family.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    s = _fid_seed(seed, "shokk_fusion_base")
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)
    x, y = _coords(ws)

    # torus curvature warp so ropes braid (Band A)
    warp = (_fbm(ws, s + 11, base_freq=2.5, octaves=3) - 0.5) * 0.5
    freq = 16.0
    # two interleaved diagonal rope sets
    a = np.sin((((x + y) * freq) + warp) * np.pi)             # set A along x+y
    b = np.sin((((x - y) * freq) + warp + 0.5) * np.pi)       # set B along x-y
    ropeA = np.clip(1.0 - np.abs(a) * 1.6, 0.0, 1.0)          # bright on rope A
    ropeB = np.clip(1.0 - np.abs(b) * 1.6, 0.0, 1.0)          # bright on rope B
    # over-under weave: which rope is "on top" alternates by a coarse checker
    over = (np.sin((x + y) * freq * 0.5 * np.pi) > 0).astype(np.float32)
    rope = np.maximum(ropeA * (0.6 + 0.4 * over),
                      ropeB * (0.6 + 0.4 * (1.0 - over)))
    # rope-internal twist striations (Band B)
    twist = 0.5 + 0.5 * np.sin(((x - y) * 70.0 + warp * 3.0) * np.pi)
    rope = np.clip(rope * (0.75 + 0.25 * twist), 0.0, 1.0)

    # --- M = ROPE STRANDS ------------------------------------------------------
    m = 45.0 + rope * 200.0

    # --- R = INTER-ROPE GAPS (negative space of M). The gap mask sets WHERE the
    # roughness lives but an INDEPENDENT mottle field drives its variance, so R is
    # not merely M's inverse rescaled (decorrelates R from M).
    gap = np.clip(1.0 - (ropeA + ropeB), 0.0, 1.0)            # weave holes
    gap_mottle = _fbm(ws, s + 29, base_freq=13.0, octaves=4)  # Band C, own field
    # let the independent mottle dominate R's variance; gap only softly gates,
    # so R is geometrically the weave-holes but statistically decorrelated from M.
    r = 55.0 + gap_mottle * 165.0                           # own variance (dominant)
    r = r * (0.62 + 0.38 * gap)                             # soft gate to gaps
    r = r - rope * 18.0

    # --- Cc = DEUTERIUM HAZE (broad low-freq) + ISLAND KNOTS at CROSSINGS -------
    haze = _fbm(ws, s + 51, base_freq=3.0, octaves=2)
    # crossings = where BOTH rope sets are bright simultaneously (derived geom)
    crossing = ropeA * ropeB
    crossing = np.clip((crossing - 0.4) * 3.0, 0.0, 1.0)
    knots = _blur(crossing, 0.8)
    cc = 35.0 + haze * 160.0 + knots * 130.0
    # island knots also pump M (white all-high knots)
    m = m + knots * 120.0
    r = r - knots * 40.0

    # --- angle reveal (#5): braid sets get opposing diagonal gates; knots flash --
    m = m + ropeA * (_cx_directional_mask(ws, "diag_a", s + 7, freq=76.0) - 0.5) * 50.0
    m = m + ropeB * (_cx_directional_mask(ws, "diag_b", s + 9, freq=76.0) - 0.5) * 50.0
    knot_reveal = _cx_buried_reveal_gate(ws, s, 7324, density=0.006, layers=6)
    cc = cc + knots * (knot_reveal - 0.4) * 60.0

    M = np.clip(m, 0, 255).astype(np.float32)
    R = np.clip(r, 15, 255).astype(np.float32)
    CC = np.clip(cc, 16, 255).astype(np.float32)
    M, R, CC = _assemble(M, R, CC, (h, w), sm)

    # --- Band D FULL-RES: neutron-flash yellow pins at island knots ------------
    knots_full = _wild_upscale(knots, h, w)
    flash = _sparse_pins_full((h, w), s + 73, density=0.020, sharp=0.7)
    flash = flash * (knots_full > 0.3)
    M = M + flash * 150.0                                     # yellow = M+R
    R = R + flash * 110.0
    CC = CC + (_nano_fringe((h, w), s + 79) - 0.5) * 14.0
    return _finalize(M, R, CC)


# ════════════════════════════════════════════════════════════════════════════
# EXPORTS — one DEDICATED function per finish in this family.
# ════════════════════════════════════════════════════════════════════════════
EXPORTS = {
    "burnt_headers":     spec_burnt_headers,
    "volcanic":          spec_volcanic,
    "shokk_inferno":     spec_shokk_inferno,
    "plasma_metal":      spec_plasma_metal,
    "plasma_core":       spec_plasma_core,
    "shokk_reactor":     spec_shokk_reactor,
    "shokk_surge":       spec_shokk_surge,
    "shokk_blood":       spec_shokk_blood,
    "shokk_fusion_base": spec_shokk_fusion_base,
}

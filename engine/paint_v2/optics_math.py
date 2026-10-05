"""LIGHT & OPTICS ENGINE (2026-06-19) — total rework: physically-grounded optical PHENOMENA, not
colour swaps of one gradient.

Each structure is a different piece of real optics math:
  - diffraction_dvd  : radial micro-grating (CD/DVD surface) splitting white light into spectral orders
  - thin_film_oil    : thin-film interference over a flowing thickness field (oil-on-water / soap)
  - caustics_pool    : refractive caustic web (Laplacian focusing of a wavy water surface)
  - newton_rings     : scattered lens-contact Newton's rings (phase proportional to r^2), overlapping

Spectral colour comes from a real wavelength->sRGB map (_wav_rgb). Full-canvas, crushed-fine
(dense grooves / thin caustic filaments / tight rings), <3s @1152. Self-contained (numpy+cv2);
reuses flame_math noise + gate helpers.
"""
from __future__ import annotations
import numpy as np
import cv2

from engine.paint_v2.flame_math import _fbm, _norm, _rng


# ----------------------------------------------------------------------------- spectral colour
def _wav_rgb(t):
    """Map t in [0,1] -> visible wavelength 380..720nm -> approx linear sRGB (Bruton), vectorised.
    Returns (...,3) float in 0..1. The backbone of every optical colour here."""
    t = np.clip(np.asarray(t, np.float32), 0.0, 1.0)
    wl = 380.0 + t * (720.0 - 380.0)
    R = np.zeros_like(wl); G = np.zeros_like(wl); B = np.zeros_like(wl)
    m = (wl >= 380) & (wl < 440); R[m] = -(wl[m] - 440) / 60.0; B[m] = 1.0
    m = (wl >= 440) & (wl < 490); G[m] = (wl[m] - 440) / 50.0; B[m] = 1.0
    m = (wl >= 490) & (wl < 510); G[m] = 1.0; B[m] = -(wl[m] - 510) / 20.0
    m = (wl >= 510) & (wl < 580); R[m] = (wl[m] - 510) / 70.0; G[m] = 1.0
    m = (wl >= 580) & (wl < 645); R[m] = 1.0; G[m] = -(wl[m] - 645) / 65.0
    m = (wl >= 645) & (wl <= 720); R[m] = 1.0
    rgb = np.stack([R, G, B], axis=-1)
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def _coords(shape):
    H, W = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return H, W, xx, yy


# ----------------------------------------------------------------------------- 1. diffraction (DVD)
def diffraction_dvd(shape, seed=7):
    """A CD/DVD optical surface: a tight logarithmic SPIRAL micro-grating whose diffraction order
    sweeps the full spectrum along multi-armed spiral tracks (NOT concentric — distinct from
    newton_rings). Swirling spectral spiral + fine groove tracks, full-canvas."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    cx, cy = W * (0.42 + 0.16 * rng.random()), H * (0.40 + 0.18 * rng.random())
    dx, dy = xx - cx, yy - cy
    r = np.sqrt(dx * dx + dy * dy) / (0.5 * np.hypot(H, W)) + 1e-3
    th = np.arctan2(dy, dx)
    arms = 5.0
    spiral = np.log(r + 0.04) * 4.2 + th * (arms / (2.0 * np.pi)) * 2.0 * np.pi  # log-spiral coord
    # spectral diffraction order climbs along the spiral -> rainbow arms
    spec = _wav_rgb(np.mod(spiral * 0.16 + r * 1.2, 1.0))
    grooves = 0.5 + 0.5 * np.cos(spiral * 7.0)                    # fine spiral data-track grooves
    micro = np.power(0.5 + 0.5 * np.cos(r * 520.0), 1.6)          # very tight radial tracks (fine)
    inten = (0.45 + 0.55 * grooves) * (0.6 + 0.4 * micro)
    img = spec * inten[..., None]
    img = img * 1.5 + spec * 0.14                                 # lift, keep hue, no dead black
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 2. thin-film oil
def thin_film_oil(shape, seed=7):
    """Thin-film interference over a flowing thickness field — oil-on-water / soap-bubble iridescence.
    Colour = interference order of 2*n*d; flow-warped for an oily swirl. Full-canvas, fine streaks."""
    H, W, xx, yy = _coords(shape)
    # SMOOTH flowing thickness map: low-freq body strongly curl-warped for the oily swirl. Keep it
    # smooth so the interference reads as broad iridescent BANDS, not per-pixel rainbow noise.
    warp = _fbm((H, W), seed + 11, octaves=3, freq=2.6)
    gx = cv2.Sobel(warp, cv2.CV_32F, 1, 0, ksize=7)
    gy = cv2.Sobel(warp, cv2.CV_32F, 0, 1, ksize=7)
    xs = np.clip(xx + gy * 130.0, 0, W - 1).astype(np.float32)    # curl: swap+sign, strong smear
    ys = np.clip(yy - gx * 130.0, 0, H - 1).astype(np.float32)
    base = _fbm((H, W), seed, octaves=4, freq=2.2)
    thick = cv2.remap(base, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    thick = cv2.GaussianBlur(thick, (0, 0), 1.6)                  # keep bands clean
    # gentle fine ripple ON TOP for micro-iridescence (the 25%-finer detail), small amplitude
    thick = thick + 0.06 * np.sin(_fbm((H, W), seed + 5, octaves=2, freq=22.0) * 6.28)
    order = np.mod(thick * 3.1, 1.0)                              # interference order -> hue cycle
    spec = _wav_rgb(order)
    grad = np.abs(cv2.Sobel(thick, cv2.CV_32F, 1, 0, ksize=3)) + np.abs(cv2.Sobel(thick, cv2.CV_32F, 0, 1, ksize=3))
    sheen = _norm(grad)                                          # specular glint on band edges
    img = spec * (0.62 + 0.38 * sheen)[..., None]
    img = img * (0.78 + 0.30 * _norm(thick))[..., None] + spec * 0.18
    return np.clip(img * 1.22, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 3. caustics
def caustics_pool(shape, seed=7):
    """Refractive caustics — the bright focused light web on a pool floor. Light focuses where the
    wavy surface is concave (negative Laplacian); thin bright filaments on dark water. Full-canvas."""
    H, W, xx, yy = _coords(shape)
    # wavy water surface = a few big sweeping swells + finer chop (so the caustic has BOLD curved
    # filaments plus fine secondary folds, not uniform stipple)
    surf = (_fbm((H, W), seed, octaves=3, freq=2.6)
            + 0.35 * _fbm((H, W), seed + 9, octaves=3, freq=8.0))
    surf = cv2.GaussianBlur(surf, (0, 0), 2.2)
    # Refraction caustics = ray FOLD lines: brightness ~ 1/|Jacobian| of the deflection map.
    # Where the refracted ray bundle compresses (Jacobian -> 0), light piles up into bright curved
    # caustic FILAMENTS that connect into the classic pool-floor web.
    gx = cv2.Sobel(surf, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(surf, cv2.CV_32F, 0, 1, ksize=5)
    gxx = cv2.Sobel(gx, cv2.CV_32F, 1, 0, ksize=5)
    gyy = cv2.Sobel(gy, cv2.CV_32F, 0, 1, ksize=5)
    gxy = cv2.Sobel(gx, cv2.CV_32F, 0, 1, ksize=5)
    a = 900.0                                                    # ray-deflection strength
    jac = (1.0 + a * gxx) * (1.0 + a * gyy) - (a * gxy) ** 2
    caustic = 1.0 / (np.abs(jac) + 0.25)
    hi = np.percentile(caustic, 98.0)                            # tame 1/|jac| outliers at folds
    caustic = np.clip(caustic / (hi + 1e-6), 0.0, 1.0)
    web = np.power(caustic, 0.5)                                 # broaden the bright filaments
    web = _norm(web + 0.45 * _norm(cv2.GaussianBlur(caustic, (0, 0), 3.0)))  # soft halo fills canvas
    tint = _wav_rgb(np.mod(_norm(surf) * 1.6 + 0.5, 1.0)) * 0.28  # chromatic dispersion on filaments
    water = np.array([0.06, 0.26, 0.34], np.float32)            # lit teal pool floor (no dead black)
    caustic_col = np.array([0.80, 0.97, 1.0], np.float32)       # bright cyan-white focus
    img = (water[None, None, :] * (0.66 + 0.34 * web[..., None])
           + (caustic_col[None, None, :] + tint) * np.power(web, 1.4)[..., None])
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 4. Newton's rings
def newton_rings(shape, seed=7, centers=13):
    """Scattered lens-contact Newton's rings — interference phase proportional to r^2 from many
    contact points, overlapping into a full-canvas iridescent quilt. Tight concentric spectral rings."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    diag = np.hypot(H, W)
    acc_phase = np.zeros((H, W), np.float32)
    acc_amp = np.zeros((H, W), np.float32)
    for _ in range(centers):
        cx, cy = rng.random() * W, rng.random() * H
        scale = (0.05 + 0.11 * rng.random()) * diag
        r2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (scale * scale)
        ph = r2 * 2.4                                            # Newton: phase ~ r^2, tight rings
        amp = 1.0 / (1.0 + 0.6 * r2)                            # each lens fades outward
        acc_phase += ph * amp
        acc_amp += amp
    phase = acc_phase / (acc_amp + 1e-5)
    spec = _wav_rgb(np.mod(phase, 1.0))
    fringe = 0.5 + 0.5 * np.cos(phase * 2.0 * np.pi)            # bright/dark interference fringes
    glass = _norm(acc_amp)
    img = spec * (0.4 + 0.6 * fringe)[..., None] * (0.45 + 0.55 * glass)[..., None]
    img = img * 1.5 + spec * 0.08
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 5. prism dispersion
def prism_dispersion(shape, seed=7, prisms=6):
    """White light shot through scattered prisms — each splits into a SPECTRAL FAN (wavelength sweeps
    across the fan angle, bright white core at the apex). Crossing rainbow shafts, full-canvas."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    diag = np.hypot(H, W)
    spread = 0.6
    # accumulate a brightness-weighted WAVELENGTH + a white-core layer, then ONE _wav_rgb (fast)
    wav_acc = np.zeros((H, W), np.float32)
    w_acc = np.zeros((H, W), np.float32)
    white = np.zeros((H, W), np.float32)
    # fine chromatic grain shifts each shaft's wavelength a touch -> fine spectral shimmer
    grain = (_fbm((H, W), seed + 4, octaves=3, freq=110.0) - 0.5)
    inv_d2 = 1.0 / (0.5 * diag) ** 2
    for _ in range(prisms):
        ox, oy = rng.random() * W, rng.random() * H
        ang = rng.random() * 2 * np.pi
        ca, sa = np.cos(ang), np.sin(ang)
        dx, dy = xx - ox, yy - oy
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        front = u > 0
        d2 = dx * dx + dy * dy
        fan = np.arctan2(v, np.abs(u) + 1e-3)
        infan = np.clip(1.0 - np.abs(fan) / spread, 0, 1)
        falloff = np.exp(-d2 * inv_d2)
        stripe = 0.6 + 0.4 * np.cos(fan * 58.0 + grain * 5.0)   # fine spectral striations in the fan
        bw = falloff * (infan ** 1.6) * front * stripe
        wav = np.clip((fan / spread) * 0.5 + 0.5 + 0.10 * grain, 0, 1)
        wav_acc += wav * bw
        w_acc += bw
        white += np.exp(-(v * v) * (1.0 / (2 * (0.7 * diag * 0.03) ** 2))) * falloff * front  # white apex core
    wav_mean = wav_acc / (w_acc + 1e-4)
    spec = _wav_rgb(wav_mean)
    # fine prismatic line-grain across the shafts (lifts fineness, reads as glassy facets)
    facet = 0.8 + 0.2 * (0.5 + 0.5 * np.cos((xx * 0.7 + yy * 1.1) * 0.9 + grain * 6.0))
    img = spec * (_norm(w_acc) * facet)[..., None] + np.array([1, 1, 1], np.float32) * (0.5 * _norm(white))[..., None]
    # faint prismatic ambient haze so the dark gaps/corners aren't pure dead black (no dead corners)
    haze = _wav_rgb(np.mod(_norm(_fbm((H, W), seed + 8, octaves=3, freq=3.0)) + 0.1, 1.0))
    ambient = 0.05 + 0.06 * _norm(_fbm((H, W), seed + 6, octaves=3, freq=24.0))
    img = img * 1.25 + haze * ambient[..., None]
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 6. moire interference
def moire_interference(shape, seed=7):
    """Overlaid fine line-gratings rotated by small angles beat into large MOIRE fringes, tinted by
    the spectral beat phase. Fine line micro-texture + sweeping macro fringe bands, full-canvas."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    cx, cy = W * 0.5, H * 0.5
    gx, gy = (xx - cx) / W, (yy - cy) / H
    # each grating is WARPED by its own low-freq field so the moire beats into organic blobs/swirls
    # (not a regular plaid) — then the beat envelope drives a FULL-spectrum hue sweep.
    layers = []
    for i in range(2):
        ang = rng.random() * np.pi
        k = 168.0 + 10.0 * i                                    # near-equal freq -> long beat
        warp = 0.22 * _fbm((H, W), seed + 17 + i, octaves=3, freq=2.4)
        u = gx * np.cos(ang) + gy * np.sin(ang) + 0.20 * (gx * gx + gy * gy) + warp
        layers.append(0.5 + 0.5 * np.cos(u * k))
    g0, g1 = layers
    moire = g0 * g1                                             # product -> beat envelope + fine lines
    beat = _norm(cv2.GaussianBlur(moire, (0, 0), 11.0))        # slow organic moire fringe field
    spec = _wav_rgb(np.mod(beat * 1.9 + 0.05 + 0.15 * gx, 1.0))  # full-spectrum sweep across blobs
    fine = _norm(moire)                                        # crisp fine line micro-texture
    img = spec * (0.4 + 0.6 * fine)[..., None]
    img = img * (0.5 + 0.6 * beat)[..., None] + spec * 0.14
    return np.clip(img * 1.25, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 7. aurora veil
def aurora_veil(shape, seed=7, curtains=7):
    """Flowing auroral curtains — luminous draped sheets with fine vertical ray striations, colour
    climbing green->magenta->violet up the veil, on a deep night sky. Diagonal flow (not upright)."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    u = (xx / W); vv = (yy / H)
    shear = 0.35                                                # tilt so curtains aren't vertical
    field = np.zeros((H, W), np.float32)
    for _ in range(curtains):
        x0 = rng.random()
        wob = 0.10 * _fbm((H, W), int(rng.random() * 1000), octaves=3, freq=3.0)
        cx = x0 + shear * (vv - 0.5) + wob                      # curtain centre drifts with height
        width = 0.018 + 0.03 * rng.random()
        amp = 0.7 + 0.5 * rng.random()
        field = field + amp * np.exp(-((u - cx) ** 2) / (2 * width * width))
    field = _norm(field)
    rays = 0.7 + 0.3 * (0.5 + 0.5 * np.cos((u + 0.2 * vv) * 220.0))   # fine vertical ray striations
    height_hue = np.clip(0.30 + vv * 0.45, 0, 1)                # green(low)->magenta/violet(high)
    spec = _wav_rgb(np.mod(0.95 - height_hue, 1.0))            # invert so bottom=green top=violet
    glow = field * rays
    sky = np.array([0.02, 0.03, 0.07], np.float32)             # deep night
    stars = (_fbm((H, W), seed + 21, octaves=2, freq=120.0) > 0.93).astype(np.float32) * 0.6
    img = sky[None, None, :] + spec * glow[..., None] * 1.5 + stars[..., None]
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 8. soap-bubble cluster
def soap_bubble_cluster(shape, seed=7, bubbles=46):
    """A froth of soap bubbles — each a sphere of thin-film interference rings (phase ~ rho^2) with a
    bright specular glint and a Fresnel rim. Packed, overlapping, full-canvas iridescent foam."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    diag = np.hypot(H, W)
    img = np.array([0.03, 0.04, 0.06], np.float32)[None, None, :] * np.ones((H, W, 3), np.float32)
    for _ in range(bubbles):
        cx, cy = rng.random() * W, rng.random() * H
        R = (0.05 + 0.13 * rng.random()) * diag
        x0, x1 = max(0, int(cx - R)), min(W, int(cx + R) + 1)
        y0, y1 = max(0, int(cy - R)), min(H, int(cy + R) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        sx, sy = xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy
        rho = np.clip(np.sqrt(sx * sx + sy * sy) / R, 0, 1.0)
        inside = (rho < 1.0)
        nx, ny = sx / R, sy / R
        nz = np.sqrt(np.clip(1.0 - rho * rho, 0, 1))            # sphere normal -> 3D read
        # light upper-left, view from front: diffuse body shade makes it a SPHERE not a flat target
        Lx, Ly, Lz = -0.5, -0.5, 0.7
        diffuse = np.clip(nx * Lx + ny * Ly + nz * Lz, 0, 1)
        body = 0.18 + 0.55 * diffuse
        spec_h = np.power(diffuse, 22.0)                        # tight specular hotspot
        thick = 0.4 + 0.6 * rng.random()
        order = np.mod(rho * rho * 3.4 + thick, 1.0)            # thin-film interference sheen
        sheen = _wav_rgb(order)
        rim = np.clip((rho - 0.82) / 0.18, 0, 1) ** 1.5         # bright Fresnel rim
        bub = (np.array([0.30, 0.36, 0.46], np.float32) * body[..., None]      # dim soapy body
               + sheen * (0.62 * body * (0.5 + 0.6 * rim))[..., None]          # strong iridescent film
               + np.array([1, 1, 1], np.float32) * (0.9 * spec_h + 0.5 * rim)[..., None])  # glint + rim
        # translucent: see THROUGH the centre, opaque at the bright rim (classic bubble)
        alpha = ((0.18 + 0.82 * rim) * inside)[..., None]
        sub = img[y0:y1, x0:x1]
        img[y0:y1, x0:x1] = sub * (1 - alpha) + np.clip(bub, 0, 1) * alpha
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 9. fiber optic
def fiber_optic(shape, seed=7, fibers=150, steps=70):
    """A bundle of glowing optical fibres — thin curl-flow strands each carrying a colour that
    blazes into a bright point TIP, scattered tips lighting the dark bundle. Full-canvas, fine."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    fx = _fbm((H, W), seed + 1, octaves=3, freq=2.6)              # flow potential -> curl field
    gx = cv2.Sobel(fx, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(fx, cv2.CV_32F, 0, 1, ksize=5)
    inten = np.zeros((H, W), np.float32)
    colmap = np.zeros((H, W, 3), np.float32)
    for i in range(fibers):
        x = rng.random() * W; y = rng.random() * H
        hue = rng.random()
        col = _wav_rgb(np.array([[hue]]))[0, 0]
        pts = []
        for s in range(steps):
            ix, iy = int(min(W - 1, max(0, x))), int(min(H - 1, max(0, y)))
            vx, vy = gy[iy, ix], -gx[iy, ix]                      # curl = perpendicular to gradient
            n = np.hypot(vx, vy) + 1e-5
            x += 3.0 * vx / n; y += 3.0 * vy / n
            if x < 0 or x >= W or y < 0 or y >= H:
                break
            pts.append((int(x), int(y)))
        if len(pts) < 4:
            continue
        arr = np.array(pts, np.int32)
        cv2.polylines(inten, [arr], False, float(0.55), 1, cv2.LINE_AA)        # thin glowing strand
        cv2.polylines(colmap, [arr], False, tuple(float(c) for c in col), 2, cv2.LINE_AA)
        tx, ty = pts[-1]
        cv2.circle(inten, (tx, ty), 2, float(1.0), -1, cv2.LINE_AA)            # bright fibre TIP
        cv2.circle(colmap, (tx, ty), 3, tuple(float(c) for c in col), -1, cv2.LINE_AA)
    glow_i = cv2.GaussianBlur(inten, (0, 0), 1.4)
    glow_c = cv2.GaussianBlur(colmap, (0, 0), 1.8)
    halo = glow_c / (glow_i[..., None] + 0.05) * _norm(glow_i)[..., None]
    core = np.clip(inten, 0, 1)[..., None] * np.array([1, 1, 1], np.float32)
    img = np.clip(halo * 1.2 + core * 0.85, 0, 1)
    return img.astype(np.float32)


# ----------------------------------------------------------------------------- 10. holographic foil
def holographic_foil(shape, seed=7):
    """Embossed holographic foil — a fine diamond-embossed micro-tessellation whose facets throw a
    full-spectrum directional sheen that shifts across the sheet (the classic holo-sticker flash)."""
    H, W, xx, yy = _coords(shape)
    cellpx = 15.0
    kx = 2 * np.pi / cellpx
    emboss = np.abs(np.sin(xx * kx)) * np.abs(np.sin(yy * kx))    # fine diamond emboss cells
    ex = cv2.Sobel(emboss, cv2.CV_32F, 1, 0, ksize=3)
    ey = cv2.Sobel(emboss, cv2.CV_32F, 0, 1, ksize=3)
    # CELLULAR flash: each emboss cell holds its own discrete spectral hue (holo-glitter mosaic),
    # only slowly drifting with view position -> a sparkly tessellated foil, NOT smooth diagonal bands.
    cx = np.floor(xx / cellpx); cy = np.floor(yy / cellpx)
    cell_hue = np.mod(cx * 0.137 + cy * 0.219 + (xx + yy) * (1.0 / 360.0)
                      + 0.3 * _norm(_fbm((H, W), seed + 2, octaves=3, freq=10.0)), 1.0)
    spec = _wav_rgb(cell_hue)
    facet = 0.5 + 0.5 * emboss
    glint = np.power(np.clip(np.abs(ex) + np.abs(ey), 0, 1), 0.6)
    img = spec * facet[..., None] + spec * 0.18 + np.array([1, 1, 1], np.float32) * (0.28 * glint)[..., None]
    return np.clip(img * 1.18, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 11. lenticular flip
def lenticular_flip(shape, seed=7):
    """A lenticular lens sheet — fine cylindrical lenslets (wavy, not ruler-straight) each showing a
    parallax band that flips spectral colour across the lens width, with bright lens-crown ridges."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    ang = 0.6 + 0.3 * rng.random()
    wob = 26.0 * _fbm((H, W), seed + 3, octaves=3, freq=2.2)      # wave the lens axis (UV-agnostic)
    axis = (xx * np.cos(ang) + yy * np.sin(ang)) + wob
    pitch = 16.0
    within = np.mod(axis, pitch) / pitch                         # 0..1 across each lenslet
    crown = np.sin(np.pi * within)                              # rounded lens cylinder crown
    # parallax: the colour seen shifts across the lens width AND with the slow position -> flip bands
    scene = (xx * np.cos(ang) - yy * np.sin(ang)) * (1.0 / 140.0)
    phase = scene + within * 1.6 + 0.2 * _norm(_fbm((H, W), seed + 6, octaves=2, freq=5.0))
    spec = _wav_rgb(np.mod(phase, 1.0))
    ridge = np.power(crown, 2.0)                                # bright lens crown highlight
    img = spec * (0.4 + 0.6 * crown)[..., None] + spec * 0.14 + np.array([1, 1, 1], np.float32) * (0.22 * np.power(crown, 6.0))[..., None]
    return np.clip(img * 1.2, 0.0, 1.0).astype(np.float32)


OPTICS_STRUCTURES = {
    "diffraction_dvd":    diffraction_dvd,
    "thin_film_oil":      thin_film_oil,
    "caustics_pool":      caustics_pool,
    "newton_rings":       newton_rings,
    "prism_dispersion":   prism_dispersion,
    "moire_interference": moire_interference,
    "aurora_veil":        aurora_veil,
    "fiber_optic":        fiber_optic,
    "holographic_foil":   holographic_foil,
    "lenticular_flip":    lenticular_flip,
    "soap_bubble_cluster": soap_bubble_cluster,
}

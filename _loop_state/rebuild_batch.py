"""Rebuild 12 spec patterns in engine/spec_patterns.py — owner doctrine compliant."""
import re

FILE = 'engine/spec_patterns.py'

# Each entry: (name, signature_line, new_body_lines)
# The body must NOT include the def line; it starts with the docstring.
REBUILDS = {}


REBUILDS['hand_polished'] = '''def hand_polished(shape, seed, sm, num_regions=25, **kwargs):
    """Hand-polished panel — overlapping circular sweep arcs and buffer marks.

    identity: a craftsman has gone over the panel by hand with random circular
    motions. Stacked features: regional FBM base modulation, sweeping curved
    polish arcs (16-28 px chord), dense fine buff strokes (6-14 px), tiny
    micro-flecks where the cloth bunched. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('hand_polished') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    fM = _fbm(701, 6.0); fR = _fbm(703, 6.0); fCC = _fbm(705, 6.0)
    M  = (0.55 + (fM  - 0.5) * 0.28).astype(np.float32)
    R  = (0.30 + (fR  - 0.5) * 0.26).astype(np.float32)
    CC = (0.22 + (fCC - 0.5) * 0.30).astype(np.float32)
    if _CV2_OK:
        # Sweeping polish arcs (curves rendered as poly-lines)
        n_arcs = max(int(num_regions * 6), 90)
        for _ in range(n_arcs):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = int(rng.uniform(10, 22) * scale)
            a0 = float(rng.uniform(0, 360))
            a1 = a0 + float(rng.uniform(35, 80))
            thick = max(1, int(rng.uniform(1, 3) * scale))
            mv  = float(rng.uniform(0.62, 0.96))
            rv  = float(rng.uniform(0.10, 0.32))
            cv_ = float(rng.uniform(0.08, 0.40))
            _cv2.ellipse(M,  (cx, cy), (rr, rr), 0, a0, a1, mv,  thickness=thick, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R,  (cx, cy), (rr, rr), 0, a0, a1, rv,  thickness=thick, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rr, rr), 0, a0, a1, cv_, thickness=thick, lineType=_cv2.LINE_AA)
        # Fine buff strokes — short straight 6-14 px lines
        n_buff = max(int(h * w / 1100), 380)
        for _ in range(n_buff):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            ang = float(rng.uniform(0, 2 * np.pi))
            ll = int(rng.uniform(4, 9) * scale)
            x1 = int(x0 + np.cos(ang) * ll); y1 = int(y0 + np.sin(ang) * ll)
            _cv2.line(M,  (x0, y0), (x1, y1), float(rng.uniform(0.55, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R,  (x0, y0), (x1, y1), float(rng.uniform(0.08, 0.28)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.10, 0.42)), 1, lineType=_cv2.LINE_AA)
        # Micro flecks where cloth bunched
        n_fl = max(int(h * w / 220), 2200)
        ys = rng.integers(0, h, n_fl); xs = rng.integers(0, w, n_fl)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.70, 0.99, n_fl).astype(np.float32))
        R[ys, xs]  = np.minimum(R[ys, xs],  rng.uniform(0.05, 0.20, n_fl).astype(np.float32))
        CC[ys, xs] = np.minimum(CC[ys, xs], rng.uniform(0.05, 0.30, n_fl).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['heat_discoloration'] = '''def heat_discoloration(shape, seed, sm, num_zones=12, **kwargs):
    """Heat-discolored metal — annealed tempering zones with banded edges.

    identity: localized heated regions on metal show banded temper colors as
    M/R/CC drops/jumps. Stacked: cool base, 8-18 oval heat zones with
    feathered edges, secondary halo rings around hottest cores, scattered
    pinhole oxide specks. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('heat_discoloration') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    fM = _fbm(811, 7.0); fR = _fbm(813, 7.0); fCC = _fbm(815, 7.0)
    M  = (0.48 + (fM  - 0.5) * 0.18).astype(np.float32)
    R  = (0.42 + (fR  - 0.5) * 0.20).astype(np.float32)
    CC = (0.38 + (fCC - 0.5) * 0.22).astype(np.float32)
    if _CV2_OK:
        n_zones = max(num_zones, 8) + int(rng.integers(0, 8))
        for _ in range(n_zones):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ra = int(rng.uniform(14, 26) * scale)
            rb = int(rng.uniform(10, 22) * scale)
            ang = float(rng.uniform(0, 180))
            mv  = float(rng.uniform(0.30, 0.78))
            rv  = float(rng.uniform(0.55, 0.92))
            cv_ = float(rng.uniform(0.50, 0.95))
            _cv2.ellipse(M,  (cx, cy), (ra, rb), ang, 0, 360, mv,  -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R,  (cx, cy), (ra, rb), ang, 0, 360, rv,  -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (ra, rb), ang, 0, 360, cv_, -1, lineType=_cv2.LINE_AA)
            # halo temper ring (slightly bigger, thin)
            ra2 = ra + max(2, int(3 * scale))
            rb2 = rb + max(2, int(3 * scale))
            _cv2.ellipse(R,  (cx, cy), (ra2, rb2), ang, 0, 360, float(rng.uniform(0.30, 0.65)), max(1, int(2 * scale)), lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (ra2, rb2), ang, 0, 360, float(rng.uniform(0.20, 0.55)), max(1, int(2 * scale)), lineType=_cv2.LINE_AA)
        # Pinhole oxide specks
        n_pin = max(int(h * w / 320), 1600)
        ys = rng.integers(0, h, n_pin); xs = rng.integers(0, w, n_pin)
        M[ys, xs]  = np.minimum(M[ys, xs],  rng.uniform(0.10, 0.30, n_pin).astype(np.float32))
        R[ys, xs]  = np.maximum(R[ys, xs],  rng.uniform(0.75, 0.98, n_pin).astype(np.float32))
        CC[ys, xs] = np.maximum(CC[ys, xs], rng.uniform(0.60, 0.95, n_pin).astype(np.float32))
        # Soft blur on M to feather zones
        M = _cv2.GaussianBlur(M, (0, 0), sigmaX=1.4, sigmaY=1.4)
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['heat_distortion'] = '''def heat_distortion(shape, seed, sm, wave_count=12, turbulence=4.0, **kwargs):
    """Heat-shimmer distortion — wavy mirage bands warping the spec field.

    identity: rising heat warps the panel reflectivity in vertical wavy
    columns. Stacked: warped sine bands (12-20 columns), turbulent FBM warp
    offsets, fine horizontal shimmer streaks (8-22 px), scattered hot specks.
    Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('heat_distortion') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    fM = _fbm(821, 5.0); fR = _fbm(823, 5.0); fCC = _fbm(825, 5.0)
    warp = _fbm(827, float(turbulence)) - 0.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    band = np.sin((xx / max(w, 1) * np.pi * 2 * float(wave_count)) + warp * 4.0 + (yy / max(h, 1) * 1.5))
    band2 = np.sin((xx / max(w, 1) * np.pi * 2 * float(wave_count) * 1.7) + warp * 2.5)
    M  = (0.50 + 0.18 * band + 0.18 * (fM  - 0.5)).astype(np.float32)
    R  = (0.36 + 0.20 * band2 + 0.18 * (fR  - 0.5)).astype(np.float32)
    CC = (0.30 + 0.22 * band + 0.20 * (fCC - 0.5)).astype(np.float32)
    if _CV2_OK:
        # Fine horizontal shimmer streaks
        n_streak = max(int(h * w / 900), 480)
        for _ in range(n_streak):
            y = int(rng.integers(0, h)); x = int(rng.integers(0, w))
            ll = int(rng.uniform(5, 12) * scale)
            ang = float(rng.uniform(-0.18, 0.18))
            x1 = int(x + np.cos(ang) * ll); y1 = int(y + np.sin(ang) * ll)
            _cv2.line(M,  (x, y), (x1, y1), float(rng.uniform(0.55, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R,  (x, y), (x1, y1), float(rng.uniform(0.10, 0.35)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x, y), (x1, y1), float(rng.uniform(0.08, 0.42)), 1, lineType=_cv2.LINE_AA)
        # Hot specks
        n_hot = max(int(h * w / 350), 1400)
        ys = rng.integers(0, h, n_hot); xs = rng.integers(0, w, n_hot)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.68, 0.97, n_hot).astype(np.float32))
        R[ys, xs]  = np.minimum(R[ys, xs],  rng.uniform(0.05, 0.22, n_hot).astype(np.float32))
        CC[ys, xs] = np.minimum(CC[ys, xs], rng.uniform(0.05, 0.30, n_hot).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['holographic_flake'] = '''def holographic_flake(shape, seed, sm, density=0.004, freq_x=12.0, freq_y=9.0):
    """Holographic flake — iridescent rainbow flake in two sub-pixel populations.

    identity: tiny holo flakes that shift M/R/CC like a diffraction grating.
    Stacked: subtle rainbow-band base modulation (two interfering sine
    gratings), fine flake population (1-3 px) very dense, medium flakes
    (4-7 px) sparse, accent prism sparks. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('holographic_flake') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g1 = 0.5 + 0.5 * np.sin(xx / max(w, 1) * np.pi * 2 * float(freq_x))
    g2 = 0.5 + 0.5 * np.sin(yy / max(h, 1) * np.pi * 2 * float(freq_y))
    fM = _fbm(901, 6.0); fR = _fbm(903, 6.0); fCC = _fbm(905, 6.0)
    M  = (0.38 + 0.20 * g1 + 0.16 * (fM  - 0.5)).astype(np.float32)
    R  = (0.38 + 0.18 * g2 + 0.18 * (fR  - 0.5)).astype(np.float32)
    CC = (0.30 + 0.16 * (g1 * g2) + 0.20 * (fCC - 0.5)).astype(np.float32)
    if _CV2_OK:
        # Fine flake population (1-3 px) very dense
        n_fine = max(int(h * w * float(density) * 4.0), 6000)
        ys = rng.integers(0, h, n_fine); xs = rng.integers(0, w, n_fine)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.70, 0.99, n_fine).astype(np.float32))
        R[ys, xs]  = np.minimum(R[ys, xs],  rng.uniform(0.05, 0.25, n_fine).astype(np.float32))
        CC[ys, xs] = np.maximum(CC[ys, xs], rng.uniform(0.55, 0.95, n_fine).astype(np.float32))
        # Medium flakes 4-7 px sparse
        n_med = max(int(h * w * float(density) * 0.4), 600)
        for _ in range(n_med):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = int(rng.uniform(2, 4) * scale)
            if rr < 1: rr = 1
            _cv2.circle(M,  (cx, cy), rr, float(rng.uniform(0.72, 0.97)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R,  (cx, cy), rr, float(rng.uniform(0.04, 0.20)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.60, 0.95)), -1, lineType=_cv2.LINE_AA)
        # Accent prism sparks
        n_spark = max(int(h * w / 5500), 280)
        for _ in range(n_spark):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            ang = float(rng.uniform(0, 2 * np.pi))
            ll = int(rng.uniform(3, 7) * scale)
            x1 = int(x0 + np.cos(ang) * ll); y1 = int(y0 + np.sin(ang) * ll)
            _cv2.line(M,  (x0, y0), (x1, y1), float(rng.uniform(0.82, 0.99)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.70, 0.96)), 1, lineType=_cv2.LINE_AA)
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['jeweling_circles'] = '''def jeweling_circles(shape, seed, sm, spacing=14, circle_radius_frac=0.55, **kwargs):
    """Jeweling — overlapping fine circular swirl marks like a watch dial.

    identity: hundreds of small swirl circles (8-22 px) overlap in a loose
    grid, each rotated/sized slightly differently for the engine-turn jewel
    look. Stacked: brushed base, primary swirl ring grid, secondary smaller
    interstitial rings, accent center dots. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('jeweling_circles') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    fM = _fbm(941, 6.0); fR = _fbm(943, 6.0); fCC = _fbm(945, 6.0)
    M  = (0.62 + (fM  - 0.5) * 0.20).astype(np.float32)
    R  = (0.24 + (fR  - 0.5) * 0.20).astype(np.float32)
    CC = (0.18 + (fCC - 0.5) * 0.22).astype(np.float32)
    if _CV2_OK:
        sp = max(8, int(spacing * scale * 1.5))
        rad = max(4, int(sp * float(circle_radius_frac)))
        # Primary swirl rings on staggered grid
        for j, cy in enumerate(range(rad, h + rad, sp)):
            row_off = (sp // 2) if (j % 2) else 0
            for cx in range(rad + row_off, w + rad, sp):
                jcx = int(cx + rng.integers(-2, 3))
                jcy = int(cy + rng.integers(-2, 3))
                rr = int(rad + rng.integers(-1, 2))
                thick = max(1, int(rng.uniform(1, 2.2) * scale))
                _cv2.circle(M,  (jcx, jcy), rr, float(rng.uniform(0.72, 0.97)), thick, lineType=_cv2.LINE_AA)
                _cv2.circle(R,  (jcx, jcy), rr, float(rng.uniform(0.06, 0.22)), thick, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (jcx, jcy), rr, float(rng.uniform(0.06, 0.30)), thick, lineType=_cv2.LINE_AA)
        # Secondary smaller interstitial rings
        n_sec = max(int((h * w) / (sp * sp)), 240)
        for _ in range(n_sec):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rad * rng.uniform(0.35, 0.6)))
            _cv2.circle(M,  (cx, cy), rr, float(rng.uniform(0.68, 0.94)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.08, 0.32)), 1, lineType=_cv2.LINE_AA)
        # Center dots
        n_dot = max(int((h * w) / 380), 1100)
        ys = rng.integers(0, h, n_dot); xs = rng.integers(0, w, n_dot)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.78, 0.99, n_dot).astype(np.float32))
        R[ys, xs]  = np.minimum(R[ys, xs],  rng.uniform(0.04, 0.18, n_dot).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['knurl_diamond'] = '''def knurl_diamond(shape, seed, sm, frequency=30.0, angle_deg=45.0, **kwargs):
    """Knurled diamond — crossed sharp ridge grid like a gun grip.

    identity: two crossed sine ridge sets at +/- angle create a diamond
    pyramid grid. Stacked: dual crossed sharp ridges, regional R/CC FBM
    modulation, peak-bright highlights at pyramid apex points, micro
    machining specks in the valleys. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('knurl_diamond') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.deg2rad(float(angle_deg))
    u1 =  np.cos(a) * xx + np.sin(a) * yy
    u2 = -np.sin(a) * xx + np.cos(a) * yy
    f = float(frequency) / max(w, 1.0) * np.pi * 2.0
    rid1 = np.abs(np.sin(u1 * f))
    rid2 = np.abs(np.sin(u2 * f))
    ridge = np.maximum(rid1, rid2)  # diamond peaks
    apex  = (rid1 * rid2)            # pyramid apex strength
    fR = _fbm(1001, 6.0); fCC = _fbm(1003, 6.0)
    M  = (0.55 + 0.30 * ridge).astype(np.float32)
    R  = (0.55 - 0.32 * ridge + 0.18 * (fR  - 0.5)).astype(np.float32)
    CC = (0.40 - 0.28 * ridge + 0.20 * (fCC - 0.5)).astype(np.float32)
    # Pyramid apex bright highlights
    apex_mask = (apex > 0.78).astype(np.float32)
    M  = np.clip(M  + apex_mask * 0.25, 0.0, 1.0)
    CC = np.clip(CC - apex_mask * 0.25, 0.0, 1.0)
    if _CV2_OK:
        # Apex bright dots
        idxs = np.argwhere(apex > 0.85)
        if len(idxs) > 0:
            pick = rng.choice(len(idxs), size=min(len(idxs), max(800, int(h * w / 700))), replace=False)
            for p in pick:
                y, x = idxs[p]
                M[y, x]  = float(rng.uniform(0.85, 0.99))
                R[y, x]  = float(rng.uniform(0.04, 0.15))
                CC[y, x] = float(rng.uniform(0.04, 0.20))
        # Valley machining specks
        n_v = max(int(h * w / 380), 1400)
        ys = rng.integers(0, h, n_v); xs = rng.integers(0, w, n_v)
        R[ys, xs]  = np.maximum(R[ys, xs],  rng.uniform(0.55, 0.92, n_v).astype(np.float32))
        CC[ys, xs] = np.maximum(CC[ys, xs], rng.uniform(0.45, 0.88, n_v).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['knurl_straight'] = '''def knurl_straight(shape, seed, sm, frequency=40.0, sharpness=3.0, **kwargs):
    """Knurled straight — parallel sharp ridges like a tool grip.

    identity: tight parallel sharp metal ridges marching across the panel.
    Stacked: sharpened sinusoidal ridges (M peaks/R troughs), regional FBM
    modulation breaking the perfection, tiny crisp top-of-ridge highlights,
    valley machining specks. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('knurl_straight') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = float(rng.uniform(0, np.pi))
    u = np.cos(ang) * xx + np.sin(ang) * yy
    f = float(frequency) / max(w, 1.0) * np.pi * 2.0
    raw = np.abs(np.sin(u * f))
    ridge = np.power(raw, max(0.5, float(sharpness)))
    fM = _fbm(1051, 7.0); fR = _fbm(1053, 7.0); fCC = _fbm(1055, 7.0)
    M  = (0.50 + 0.32 * ridge + 0.10 * (fM  - 0.5)).astype(np.float32)
    R  = (0.55 - 0.30 * ridge + 0.18 * (fR  - 0.5)).astype(np.float32)
    CC = (0.42 - 0.30 * ridge + 0.20 * (fCC - 0.5)).astype(np.float32)
    if _CV2_OK:
        # Crisp top-of-ridge highlights at ridge crests
        peak = (ridge > 0.88)
        idxs = np.argwhere(peak)
        if len(idxs) > 0:
            n_pick = min(len(idxs), max(900, int(h * w / 600)))
            pick = rng.choice(len(idxs), size=n_pick, replace=False)
            for p in pick:
                y, x = idxs[p]
                M[y, x] = float(rng.uniform(0.88, 0.99))
                R[y, x] = float(rng.uniform(0.04, 0.14))
                CC[y, x] = float(rng.uniform(0.04, 0.20))
        # Valley specks
        n_v = max(int(h * w / 420), 1300)
        ys = rng.integers(0, h, n_v); xs = rng.integers(0, w, n_v)
        R[ys, xs] = np.maximum(R[ys, xs], rng.uniform(0.55, 0.90, n_v).astype(np.float32))
        # Fine cross-ridge machining streaks
        n_str = max(int(h * w / 1800), 240)
        for _ in range(n_str):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            a2 = ang + np.pi / 2 + float(rng.uniform(-0.2, 0.2))
            ll = int(rng.uniform(3, 8) * scale)
            x1 = int(x0 + np.cos(a2) * ll); y1 = int(y0 + np.sin(a2) * ll)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.05, 0.30)), 1, lineType=_cv2.LINE_AA)
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['lathe_concentric'] = '''def lathe_concentric(shape, seed, sm, **kwargs):
    """Lathe-turned concentric — tight concentric grooves from a center.

    identity: a metal disc just off the lathe, dense concentric circular
    grooves around an off-center pivot. Stacked: concentric ridge field
    (radius-based sine), angular FBM modulation (groove drift), tiny chatter
    burrs along grooves, accent shiny apex points. Per-feature INDEPENDENT
    M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('lathe_concentric') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = w * float(rng.uniform(0.3, 0.7))
    cy = h * float(rng.uniform(0.3, 0.7))
    rdist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    # Tight groove frequency — adapt to canvas (small features 4-12 px period)
    period_px = max(3.0, 7.0 * scale)
    ridge = np.abs(np.sin(rdist / period_px * np.pi))
    fM = _fbm(1101, 5.0); fR = _fbm(1103, 5.0); fCC = _fbm(1105, 5.0)
    M  = (0.52 + 0.30 * ridge + 0.10 * (fM  - 0.5)).astype(np.float32)
    R  = (0.46 - 0.28 * ridge + 0.18 * (fR  - 0.5)).astype(np.float32)
    CC = (0.34 - 0.24 * ridge + 0.18 * (fCC - 0.5)).astype(np.float32)
    if _CV2_OK:
        # Chatter burrs — fine specks along grooves
        peak = (ridge > 0.85)
        idxs = np.argwhere(peak)
        if len(idxs) > 0:
            n_pick = min(len(idxs), max(1400, int(h * w / 400)))
            pick = rng.choice(len(idxs), size=n_pick, replace=False)
            for p in pick:
                y, x = idxs[p]
                M[y, x] = float(rng.uniform(0.82, 0.99))
                R[y, x] = float(rng.uniform(0.04, 0.16))
                CC[y, x] = float(rng.uniform(0.05, 0.22))
        # Random groove chatter streaks (radial)
        n_str = max(int(h * w / 1600), 280)
        for _ in range(n_str):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            ang = np.arctan2(y0 - cy, x0 - cx) + np.pi / 2
            ll = int(rng.uniform(3, 8) * scale)
            x1 = int(x0 + np.cos(ang) * ll); y1 = int(y0 + np.sin(ang) * ll)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.45, 0.85)), 1, lineType=_cv2.LINE_AA)
        # Accent shiny apex points
        n_apex = max(int(h * w / 1100), 500)
        ys = rng.integers(0, h, n_apex); xs = rng.integers(0, w, n_apex)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.76, 0.98, n_apex).astype(np.float32))
        CC[ys, xs] = np.minimum(CC[ys, xs], rng.uniform(0.05, 0.25, n_apex).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['lava_crack'] = '''def lava_crack(shape, seed, sm, num_plates=35, glow_width=4.0, **kwargs):
    """Lava crack — cooled crust cracking with hot glow showing through.

    identity: irregular plate tessellation with bright "lava" fractures
    between cooled crust plates. Stacked: dark crust base (low M, mid R),
    bright fracture lines following voronoi-like seam paths, secondary thin
    branch cracks, accent hot spots clustered at crack junctions. Per-feature
    INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('lava_crack') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    fM = _fbm(1201, 8.0); fR = _fbm(1203, 8.0); fCC = _fbm(1205, 8.0)
    M  = (0.20 + (fM  - 0.5) * 0.18).astype(np.float32)
    R  = (0.78 + (fR  - 0.5) * 0.20).astype(np.float32)
    CC = (0.72 + (fCC - 0.5) * 0.20).astype(np.float32)
    if _CV2_OK:
        # Voronoi-like fracture lines between plate seeds
        n_plates = max(int(num_plates), 30) * 2
        seeds_x = rng.uniform(0, w, n_plates).astype(np.float32)
        seeds_y = rng.uniform(0, h, n_plates).astype(np.float32)
        # Connect each seed to ~2 nearest neighbors to form fracture network
        from scipy.spatial import cKDTree
        pts = np.stack([seeds_x, seeds_y], axis=1)
        tree = cKDTree(pts)
        gw = max(1, int(float(glow_width) * scale * 0.6))
        # Walls between adjacent seeds — midpoint perpendicular segments
        _, nbrs = tree.query(pts, k=4)
        for i in range(n_plates):
            for j in nbrs[i, 1:]:
                if j <= i: continue
                mx = (pts[i, 0] + pts[j, 0]) / 2
                my = (pts[i, 1] + pts[j, 1]) / 2
                dx = pts[j, 0] - pts[i, 0]; dy = pts[j, 1] - pts[i, 1]
                d = float(np.hypot(dx, dy)) + 1e-6
                # Perp direction
                px = -dy / d; py = dx / d
                ll = min(d * 0.45, 40 * scale)
                x0 = int(mx - px * ll); y0 = int(my - py * ll)
                x1 = int(mx + px * ll); y1 = int(my + py * ll)
                _cv2.line(M,  (x0, y0), (x1, y1), float(rng.uniform(0.78, 0.99)), gw, lineType=_cv2.LINE_AA)
                _cv2.line(R,  (x0, y0), (x1, y1), float(rng.uniform(0.05, 0.22)), gw, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.04, 0.20)), gw, lineType=_cv2.LINE_AA)
        # Secondary thin branch cracks
        n_branch = max(int(h * w / 4500), 200)
        for _ in range(n_branch):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            a = float(rng.uniform(0, 2 * np.pi))
            ll = int(rng.uniform(6, 18) * scale)
            x1 = int(x0 + np.cos(a) * ll); y1 = int(y0 + np.sin(a) * ll)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.68, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.08, 0.30)), 1, lineType=_cv2.LINE_AA)
        # Accent hot spots
        n_hot = max(int(h * w / 1800), 380)
        ys = rng.integers(0, h, n_hot); xs = rng.integers(0, w, n_hot)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.78, 0.99, n_hot).astype(np.float32))
        CC[ys, xs] = np.minimum(CC[ys, xs], rng.uniform(0.05, 0.25, n_hot).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['magnetic_field'] = '''def magnetic_field(shape, seed, sm, num_poles=3, line_density=20.0, **kwargs):
    """Magnetic field — flowing iron-filing curves around magnetic poles.

    identity: curving streamlines flow between magnetic poles like iron
    filings on glass. Stacked: smooth pole-influenced flow field base, dense
    short streamline strokes (8-22 px) traced along the field, pole concentration
    bright accents, scattered iron speck dust. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('magnetic_field') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    # Pole placement
    np_poles = max(int(num_poles), 2) + int(rng.integers(0, 3))
    pxs = rng.uniform(0, w, np_poles)
    pys = rng.uniform(0, h, np_poles)
    signs = rng.choice([-1.0, 1.0], np_poles)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    flow = np.zeros((h, w), dtype=np.float32)
    for i in range(np_poles):
        dx = xx - pxs[i]; dy = yy - pys[i]
        d2 = dx * dx + dy * dy + 100.0
        flow += float(signs[i]) * (1.0 / d2) * 8000.0
    flow = _normalize(flow)
    fM = _fbm(1301, 6.0); fR = _fbm(1303, 6.0); fCC = _fbm(1305, 6.0)
    M  = (0.35 + 0.28 * flow + 0.16 * (fM  - 0.5)).astype(np.float32)
    R  = (0.55 - 0.20 * flow + 0.18 * (fR  - 0.5)).astype(np.float32)
    CC = (0.32 + 0.20 * flow + 0.20 * (fCC - 0.5)).astype(np.float32)
    if _CV2_OK:
        # Streamlines — short curves tracing the field
        n_lines = max(int(h * w / 700), 600)
        for _ in range(n_lines):
            x = float(rng.integers(0, w)); y = float(rng.integers(0, h))
            mv  = float(rng.uniform(0.62, 0.96))
            rv  = float(rng.uniform(0.06, 0.30))
            cv_ = float(rng.uniform(0.06, 0.35))
            pts = [(int(x), int(y))]
            for _step in range(int(rng.integers(3, 7))):
                # gradient ascent through flow field
                vx = vy = 0.0
                for i in range(np_poles):
                    dx = x - pxs[i]; dy = y - pys[i]
                    d2 = dx * dx + dy * dy + 25.0
                    s = float(signs[i]) / d2
                    vx += s * dx; vy += s * dy
                m = (vx * vx + vy * vy) ** 0.5 + 1e-6
                step = 2.0 * scale
                x += vx / m * step; y += vy / m * step
                if not (0 <= x < w and 0 <= y < h): break
                pts.append((int(x), int(y)))
            for k in range(len(pts) - 1):
                _cv2.line(M,  pts[k], pts[k + 1], mv,  1, lineType=_cv2.LINE_AA)
                _cv2.line(R,  pts[k], pts[k + 1], rv,  1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, pts[k], pts[k + 1], cv_, 1, lineType=_cv2.LINE_AA)
        # Pole concentration bright accents
        for i in range(np_poles):
            rr = max(3, int(8 * scale))
            _cv2.circle(M, (int(pxs[i]), int(pys[i])), rr, float(rng.uniform(0.82, 0.98)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (int(pxs[i]), int(pys[i])), rr, float(rng.uniform(0.06, 0.22)), -1, lineType=_cv2.LINE_AA)
        # Iron-speck dust
        n_dust = max(int(h * w / 280), 2000)
        ys = rng.integers(0, h, n_dust); xs = rng.integers(0, w, n_dust)
        M[ys, xs] = np.maximum(M[ys, xs], rng.uniform(0.55, 0.92, n_dust).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['marble_vein'] = '''def marble_vein(shape, seed, sm, vein_freq=6.0, turbulence=3, vein_sharpness=3.0):
    """Marble vein — branching dark vein network through stone matrix.

    identity: a polished marble slab — soft mottled stone base with thin
    branching dark veins twisting across. Stacked: mottled base FBM, primary
    vein network (turbulent ridged noise), secondary thinner cross-veins,
    accent quartz crystal flecks. Per-feature INDEPENDENT M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('marble_vein') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    base_M = _fbm(1401, 8.0)
    base_R = _fbm(1403, 8.0)
    base_CC = _fbm(1405, 8.0)
    # Ridged turbulence for veins
    warp = _fbm(1411, float(turbulence)) - 0.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx / max(w, 1) * float(vein_freq) + warp * 6.0)
    v = (yy / max(h, 1) * float(vein_freq) + warp * 6.0)
    vein_raw = np.abs(np.sin(u + np.sin(v) * 1.5))
    vein = 1.0 - np.power(vein_raw, max(0.5, float(vein_sharpness)))  # sharp dark
    # Threshold to thin
    vein = np.clip((vein - 0.55) / 0.45, 0.0, 1.0)
    M  = (0.30 + 0.18 * base_M  - 0.18 * vein).astype(np.float32)
    R  = (0.55 + 0.18 * base_R  + 0.18 * vein).astype(np.float32)
    CC = (0.32 + 0.18 * base_CC + 0.20 * vein).astype(np.float32)
    if _CV2_OK:
        # Secondary thin cross-veins (random curves)
        n_x = max(int(h * w / 3500), 200)
        for _ in range(n_x):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            a = float(rng.uniform(0, 2 * np.pi))
            pts = [(x0, y0)]
            xx_, yy_ = float(x0), float(y0)
            for _s in range(int(rng.integers(3, 7))):
                a += float(rng.uniform(-0.4, 0.4))
                ll = float(rng.uniform(4, 9) * scale)
                xx_ += np.cos(a) * ll; yy_ += np.sin(a) * ll
                pts.append((int(xx_), int(yy_)))
            mv = float(rng.uniform(0.18, 0.40))
            rv = float(rng.uniform(0.62, 0.92))
            cvv = float(rng.uniform(0.45, 0.85))
            for k in range(len(pts) - 1):
                _cv2.line(M, pts[k], pts[k + 1], mv, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, pts[k], pts[k + 1], rv, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, pts[k], pts[k + 1], cvv, 1, lineType=_cv2.LINE_AA)
        # Quartz crystal flecks (bright tiny)
        n_q = max(int(h * w / 480), 1100)
        ys = rng.integers(0, h, n_q); xs = rng.integers(0, w, n_q)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.72, 0.97, n_q).astype(np.float32))
        R[ys, xs]  = np.minimum(R[ys, xs],  rng.uniform(0.05, 0.22, n_q).astype(np.float32))
        CC[ys, xs] = np.minimum(CC[ys, xs], rng.uniform(0.05, 0.25, n_q).astype(np.float32))
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


REBUILDS['metallic_sand'] = '''def metallic_sand(shape, seed, sm, block_size=2, flow_angle=0.18):
    """Metallic sand — drifting fine metallic grain in flow streaks.

    identity: a dense bed of fine metallic grains (1-3 px) with directional
    drift streaks visible. Stacked: dense fine grain field (3 size tiers),
    flow-directional micro-streaks (5-14 px) along the flow_angle, regional
    M FBM (clumping), accent bright grain clusters. Per-feature INDEPENDENT
    M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash('metallic_sand') % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    fM = _fbm(1501, 7.0); fR = _fbm(1503, 7.0); fCC = _fbm(1505, 7.0)
    M  = (0.42 + (fM  - 0.5) * 0.26).astype(np.float32)
    R  = (0.42 + (fR  - 0.5) * 0.22).astype(np.float32)
    CC = (0.40 + (fCC - 0.5) * 0.24).astype(np.float32)
    if _CV2_OK:
        # Tier 1: very dense fine grain (1 px)
        n1 = max(int(h * w / 60), 16000)
        ys = rng.integers(0, h, n1); xs = rng.integers(0, w, n1)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.55, 0.95, n1).astype(np.float32))
        R[ys, xs]  = np.minimum(R[ys, xs],  rng.uniform(0.10, 0.40, n1).astype(np.float32))
        CC[ys, xs] = np.maximum(CC[ys, xs], rng.uniform(0.45, 0.92, n1).astype(np.float32))
        # Tier 2: medium grain 2-3 px
        n2 = max(int(h * w / 800), 1800)
        for _ in range(n2):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1, 2) * scale))
            _cv2.circle(M,  (cx, cy), rr, float(rng.uniform(0.65, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R,  (cx, cy), rr, float(rng.uniform(0.05, 0.25)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)
        # Flow-directional micro-streaks
        ang = float(flow_angle) * np.pi + float(rng.uniform(-0.05, 0.05))
        n_st = max(int(h * w / 1400), 380)
        for _ in range(n_st):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            ll = int(rng.uniform(4, 9) * scale)
            x1 = int(x0 + np.cos(ang) * ll); y1 = int(y0 + np.sin(ang) * ll)
            _cv2.line(M,  (x0, y0), (x1, y1), float(rng.uniform(0.62, 0.94)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R,  (x0, y0), (x1, y1), float(rng.uniform(0.08, 0.30)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.45, 0.88)), 1, lineType=_cv2.LINE_AA)
        # Accent bright clusters
        n_c = max(int(h * w / 4500), 140)
        for _ in range(n_c):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(2, 4) * scale))
            _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.80, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.04, 0.15)), -1, lineType=_cv2.LINE_AA)
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
'''


def main():
    with open(FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    import re
    for name, new_func in REBUILDS.items():
        # Match: def NAME(... possibly multi-line ...):  ... until next ^def or EOF
        pat = re.compile(r'^def ' + re.escape(name) + r'\(.*?(?=^def |\Z)', re.DOTALL | re.MULTILINE)
        m = pat.search(content)
        if not m:
            print('MISS', name)
            continue
        # Ensure new func ends with \n\n\n if not at EOF
        repl = new_func
        if not repl.endswith('\n\n\n'):
            if repl.endswith('\n\n'):
                repl = repl + '\n'
            elif repl.endswith('\n'):
                repl = repl + '\n\n'
            else:
                repl = repl + '\n\n\n'
        content = content[:m.start()] + repl + content[m.end():]
        print('REPLACED', name)
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print('WROTE', FILE)


if __name__ == '__main__':
    main()

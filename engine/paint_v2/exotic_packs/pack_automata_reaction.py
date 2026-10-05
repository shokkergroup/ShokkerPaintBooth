"""AUTOMATA & REACTION-SYSTEMS field-generator pack for Shokker Paint Booth.

Each engine produces a full-coverage, FINE-detailed scalar FIELD in [0,1], shape (h, w),
computed at low `res` then upscaled. These are GENUINELY DISTINCT algorithms from the
cellular-automata / reaction-systems math family — not recolors of one another and NOT
in the already-covered list (basic reaction-diffusion is the only RD cousin; everything
here is a different organism / rule / dynamical regime).

Engines:
  conway_density      — Conway's Game of Life; per-cell time-averaged live density (a
                        spacetime occupancy field crushed onto the plane).
  eca_spacetime       — elementary 1-D cellular automaton (rule 30/90/110/etc.) evolved
                        row-by-row into a 2-D spacetime triangle field.
  cyclic_ca           — cyclic cellular automaton (Greenberg-Hastings-ish); rock-paper-
                        scissors waves that crystallize into spiral demons.
  bz_spirals          — Belousov-Zhabotinsky three-species oscillating chemistry; rotating
                        excitable spiral waves.
  lenia               — Lenia continuous-state, continuous-kernel life; smooth gliders and
                        living blobs via an FFT growth convolution.
  hodgepodge          — Gerhardt-Schuster hodgepodge machine; discrete excitable medium
                        (healthy/ill/infected) giving target & spiral fronts.
  gray_scott_uskate   — Gray-Scott U-Skate-world / mitosis / worms regimes (dynamical RD
                        regimes distinct from the basic coral RD already shipped).
  anisotropic_turing  — direction-biased Turing morphogenesis; oriented stripe/maze
                        fingerprints via an anisotropic diffusion tensor.
  brians_brain        — Brian's Brain 3-state CA; firing/refractory medium that breeds
                        gliders and noisy excitation lace.
  larger_than_life    — Larger-than-Life CA (Bosco's rule family); big-radius totalistic
                        life giving bubbling cellular foam.
  neural_ca_worms     — neural / multi-neighborhood CA ("MNCA" worm rule); self-organizing
                        worm/loop networks from a learned-style activation curve.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy.ndimage import uniform_filter, convolve


# ----------------------------------------------------------------------------- helpers
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xffffffff)


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _finalize(field, h, w):
    return _norm(_up(_norm(field), h, w))


def _neighbor_sum8(B):
    """Toroidal 8-neighbour count for a binary/float grid (vectorised, no python loop)."""
    return (
        np.roll(B, 1, 0) + np.roll(B, -1, 0) + np.roll(B, 1, 1) + np.roll(B, -1, 1)
        + np.roll(np.roll(B, 1, 0), 1, 1) + np.roll(np.roll(B, 1, 0), -1, 1)
        + np.roll(np.roll(B, -1, 0), 1, 1) + np.roll(np.roll(B, -1, 0), -1, 1)
    )


def _lap(Z):
    """9-point wrapped Laplacian (toroidal)."""
    return (
        0.20 * (np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1))
        + 0.05 * (np.roll(np.roll(Z, 1, 0), 1, 1) + np.roll(np.roll(Z, 1, 0), -1, 1)
                  + np.roll(np.roll(Z, -1, 0), 1, 1) + np.roll(np.roll(Z, -1, 0), -1, 1))
        - Z
    )


# ----------------------------------------------------------------------------- 1. Conway
def conway_density(h, w, seed, *, res=384, gens=140, warm=12) -> np.ndarray:
    """Conway's Game of Life: accumulate per-cell live-density over many generations.

    The temporal average of a chaotic Life soup is a crushed, full-coverage field of
    still-lifes, blinkers and glider trails — high frequency everywhere, never a blob."""
    rng = _rng(seed)
    B = (rng.random((res, res)) < 0.42).astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    age = np.zeros((res, res), np.float32)
    for g in range(gens):
        n = _neighbor_sum8(B)
        B = ((n == 3) | ((B > 0.5) & (n == 2))).astype(np.float32)
        age = (age + 1.0) * B          # consecutive generations alive
        if g >= warm:
            acc += B + 0.25 * np.tanh(age * 0.15)
    # blend density with a phase term so dead vacuum is not perfectly flat
    field = acc + 0.6 * np.cos(age * 0.9) * (acc > 0)
    field = cv2.GaussianBlur(field.astype(np.float32), (0, 0), 0.6)
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 2. ECA
def eca_spacetime(h, w, seed, *, res=512) -> np.ndarray:
    """Elementary 1-D cellular automaton spacetime diagram (Wolfram rules).

    Picks a chaotic/complex rule (30/45/73/90/105/110/150/182) and evolves a single
    seeded row downward, stacking rows into the classic fractal spacetime triangle."""
    rng = _rng(seed)
    rules = [30, 45, 73, 90, 105, 110, 150, 182, 22, 126]
    rule = int(rules[int(rng.integers(0, len(rules)))])
    table = np.array([(rule >> k) & 1 for k in range(8)], np.uint8)  # index = 4*l+2*c+1*r
    rows = np.zeros((res, res), np.uint8)
    # seed: random start so it isn't always one cell -> guarantees full coverage
    if rng.random() < 0.5:
        rows[0] = (rng.random(res) < 0.5).astype(np.uint8)
    else:
        rows[0, res // 2] = 1
    cur = rows[0].copy()
    for r in range(1, res):
        left = np.roll(cur, 1)
        right = np.roll(cur, -1)
        idx = (left << 2) | (cur << 1) | right
        cur = table[idx]
        rows[r] = cur
    field = rows.astype(np.float32)
    # add a soft spacetime "glow" so the binary stays premium (fine detail kept by add)
    glow = cv2.GaussianBlur(field, (0, 0), 1.4)
    field = 0.7 * field + 0.5 * glow
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 3. cyclic CA
def cyclic_ca(h, w, seed, *, res=320, states=14, gens=70, thresh=1) -> np.ndarray:
    """Cyclic cellular automaton (rock-paper-scissors on a ring of `states`).

    A cell at state s advances to s+1 (mod N) if enough von-Neumann neighbours are
    already at s+1. Random soup self-organizes into rotating spiral 'demons'."""
    rng = _rng(seed)
    grid = rng.integers(0, states, (res, res)).astype(np.int16)
    for _ in range(gens):
        nxt = (grid + 1) % states
        cnt = (
            (np.roll(grid, 1, 0) == nxt).astype(np.int16)
            + (np.roll(grid, -1, 0) == nxt)
            + (np.roll(grid, 1, 1) == nxt)
            + (np.roll(grid, -1, 1) == nxt)
        )
        grid = np.where(cnt >= thresh, nxt, grid)
    # phase -> continuous field via complex unit circle of the state index
    phase = grid.astype(np.float32) * (2.0 * np.pi / states)
    field = 0.5 + 0.5 * np.cos(phase + 0.0)
    # add a second harmonic so spiral arms get crushed micro-banding
    field = 0.6 * field + 0.4 * (0.5 + 0.5 * np.cos(2.0 * phase))
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 4. BZ
def bz_spirals(h, w, seed, *, res=260, gens=110) -> np.ndarray:
    """Belousov-Zhabotinsky reaction: 3-species excitable oscillating chemistry.

    Discrete BZ (a/b/c activator-inhibitor-catalyst) on a 3x3 neighbourhood produces
    rotating chemical spiral waves and target patterns across the whole sheet."""
    rng = _rng(seed)
    a = rng.random((res, res)).astype(np.float32)
    b = rng.random((res, res)).astype(np.float32)
    c = rng.random((res, res)).astype(np.float32)
    k = np.ones((3, 3), np.float32) / 9.0
    alpha, beta, gamma = 1.0, 1.0, 1.0
    for _ in range(gens):
        ca = convolve(a, k, mode="wrap")
        cb = convolve(b, k, mode="wrap")
        cc = convolve(c, k, mode="wrap")
        a2 = ca + ca * (alpha * cb - gamma * cc)
        b2 = cb + cb * (beta * cc - alpha * ca)
        c2 = cc + cc * (gamma * ca - beta * cb)
        a = np.clip(a2, 0.0, 1.0)
        b = np.clip(b2, 0.0, 1.0)
        c = np.clip(c2, 0.0, 1.0)
    field = a - c  # excitation front contrast
    field = cv2.GaussianBlur(field.astype(np.float32), (0, 0), 0.7)
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 5. Lenia
def lenia(h, w, seed, *, res=192, gens=90) -> np.ndarray:
    """Lenia: continuous-state continuous-kernel generalization of Life.

    A smooth annular growth kernel convolved (via FFT) with a continuous world, gated by
    a Gaussian growth function, breeds gliders/orbium and living cellular tissue."""
    rng = _rng(seed)
    R = 13
    # smooth ring kernel
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    rad = np.sqrt(xx * xx + yy * yy) / R
    bell = lambda x, m, s: np.exp(-((x - m) ** 2) / (2.0 * s * s))
    K = bell(rad, 0.5, 0.15)
    K[rad > 1.0] = 0.0
    K /= K.sum() + 1e-9
    # embed kernel for fft conv
    Kf = np.zeros((res, res), np.float32)
    kh = K.shape[0]
    Kf[:kh, :kh] = K
    Kf = np.roll(Kf, -R, 0)
    Kf = np.roll(Kf, -R, 1)
    Kfft = np.fft.rfft2(Kf)
    A = rng.random((res, res)).astype(np.float32)
    A = cv2.GaussianBlur(A, (0, 0), 3.0)
    A = _norm(A)
    mu, sig, dt = 0.15, 0.017, 0.12
    for _ in range(gens):
        U = np.fft.irfft2(np.fft.rfft2(A) * Kfft, s=A.shape).astype(np.float32)
        G = 2.0 * bell(U, mu, sig) - 1.0   # growth in [-1,1]
        A = np.clip(A + dt * G, 0.0, 1.0)
    field = A + 0.4 * np.cos(A * 6.2831)   # fine micro-banding on the smooth tissue
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 6. hodgepodge
def hodgepodge(h, w, seed, *, res=300, gens=90, n=120, g=22, k1=2.0, k2=3.0) -> np.ndarray:
    """Gerhardt-Schuster hodgepodge machine: discrete excitable medium.

    Cells run healthy(0) -> infected(1..n-1) -> ill(n). Infection spreads from infected &
    ill 8-neighbours; ill cells reset. Produces target waves and rotating spirals."""
    rng = _rng(seed)
    s = rng.integers(0, n + 1, (res, res)).astype(np.float32)
    for _ in range(gens):
        ill = (s >= n).astype(np.float32)
        infected = ((s > 0) & (s < n)).astype(np.float32)
        a = _neighbor_sum8(ill) + ill          # count incl self ill
        b = _neighbor_sum8(infected) + infected
        sum_inf = _neighbor_sum8(s) + s
        cnt_inf = b
        avg = sum_inf / np.maximum(cnt_inf, 1.0)
        nxt = s.copy()
        # healthy cells
        healthy = (s == 0)
        nxt[healthy] = np.floor(a[healthy] / k1) + np.floor(b[healthy] / k2)
        # infected cells advance by average + g
        inf_mask = (s > 0) & (s < n)
        nxt[inf_mask] = np.minimum(avg[inf_mask] + g, n)
        # ill cells recover
        nxt[s >= n] = 0
        s = np.clip(nxt, 0, n)
    field = s.astype(np.float32)
    field = cv2.GaussianBlur(field, (0, 0), 0.6)
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 7. Gray-Scott regimes
GS_REGIMES = {
    "uskate":  (0.0620, 0.0610),
    "mitosis": (0.0367, 0.0649),
    "worms":   (0.0540, 0.0630),
    "solitons":(0.0300, 0.0560),
}


def gray_scott_uskate(h, w, seed, *, res=240, iters=2000, du=0.16, dv=0.08) -> np.ndarray:
    """Gray-Scott in its exotic U-Skate-world / mitosis / worm / soliton regimes.

    These (F,k) regimes give self-replicating spots, dividing cells and crawling worms —
    dynamically distinct from the basic coral RD already in the catalog."""
    rng = _rng(seed)
    regime = list(GS_REGIMES)[int(rng.integers(0, len(GS_REGIMES)))]
    feed, kill = GS_REGIMES[regime]
    U = np.ones((res, res), np.float32)
    V = np.zeros((res, res), np.float32)
    for _ in range(int(28)):
        cy, cx = int(rng.integers(0, res)), int(rng.integers(0, res))
        r = int(rng.integers(3, 8))
        U[max(0, cy - r):cy + r, max(0, cx - r):cx + r] = 0.5
        V[max(0, cy - r):cy + r, max(0, cx - r):cx + r] = 0.25
    V += rng.random((res, res)).astype(np.float32) * 0.05
    for _ in range(int(iters)):
        uvv = U * V * V
        U += du * _lap(U) - uvv + feed * (1.0 - U)
        V += dv * _lap(V) + uvv - (feed + kill) * V
        np.clip(U, 0.0, 1.0, out=U)
        np.clip(V, 0.0, 1.0, out=V)
    # combine V spots with the U depletion shells + a gradient term so even sparse
    # soliton regimes keep full-coverage variance (never a near-flat plate)
    gy, gx = np.gradient(U.astype(np.float32))
    field = V + 0.8 * (1.0 - U) + 0.6 * np.hypot(gx, gy)
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 8. anisotropic Turing
def anisotropic_turing(h, w, seed, *, res=288, iters=130) -> np.ndarray:
    """Anisotropic Turing morphogenesis: direction-biased activator-inhibitor system.

    A linearised Turing reaction with an anisotropic (elongated) diffusion stencil makes
    oriented fingerprint stripes and oriented mazes instead of isotropic spots."""
    rng = _rng(seed)
    theta = float(rng.uniform(0, np.pi))
    ax = 0.5 + 1.4 * np.cos(theta) ** 2
    ay = 0.5 + 1.4 * np.sin(theta) ** 2
    A = (rng.random((res, res)).astype(np.float32) - 0.5)
    I = (rng.random((res, res)).astype(np.float32) - 0.5)
    da, di = 0.12, 0.30
    for _ in range(iters):
        # anisotropic Laplacian: separate x/y weights
        lapA = (ay * (np.roll(A, 1, 0) + np.roll(A, -1, 0))
                + ax * (np.roll(A, 1, 1) + np.roll(A, -1, 1))
                - 2.0 * (ax + ay) * A)
        lapI = (ay * (np.roll(I, 1, 0) + np.roll(I, -1, 0))
                + ax * (np.roll(I, 1, 1) + np.roll(I, -1, 1))
                - 2.0 * (ax + ay) * I)
        rA = A - A ** 3 - I + 0.0
        rI = (A - I)
        A = A + 0.18 * (da * lapA + rA)
        I = I + 0.18 * (di * lapI + 0.12 * rI)
        np.clip(A, -1.5, 1.5, out=A)
        np.clip(I, -1.5, 1.5, out=I)
    field = A
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 9. Brian's Brain
def brians_brain(h, w, seed, *, res=384, gens=120, warm=14) -> np.ndarray:
    """Brian's Brain: 3-state CA (off / firing / refractory).

    An off cell fires iff exactly 2 neighbours fired; firing -> refractory -> off. Breeds
    fast gliders and a restless excitation lace; time-averaged to a crushed field."""
    rng = _rng(seed)
    state = rng.integers(0, 3, (res, res)).astype(np.int8)   # 0 off,1 firing,2 refractory
    acc = np.zeros((res, res), np.float32)
    for g in range(gens):
        firing = (state == 1).astype(np.int16)
        nf = _neighbor_sum8(firing)
        new = np.zeros_like(state)
        new[(state == 0) & (nf == 2)] = 1   # birth
        new[state == 1] = 2                 # firing -> refractory
        new[state == 2] = 0                 # refractory -> off
        state = new
        if g >= warm:
            acc += (state == 1) * 1.0 + (state == 2) * 0.45
    field = acc
    field = cv2.GaussianBlur(field.astype(np.float32), (0, 0), 0.5)
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 10. Larger than Life
def larger_than_life(h, w, seed, *, res=256, gens=60, R=4) -> np.ndarray:
    """Larger-than-Life CA (Bosco's-rule family): big-radius totalistic life.

    A cell's fate depends on the count of live cells in a radius-R box neighbourhood with
    birth/survival intervals — gives bubbling cellular foam and large gliders."""
    rng = _rng(seed)
    B = (rng.random((res, res)) < 0.5).astype(np.float32)
    area = (2 * R + 1) ** 2
    # "bugs"-style LtL intervals tuned to stay alive in a bubbling foam regime
    b_lo, b_hi = 0.21, 0.40
    s_lo, s_hi = 0.18, 0.55
    acc = np.zeros((res, res), np.float32)
    fcc = np.zeros((res, res), np.float32)
    nframes = 0
    for g in range(gens):
        # box neighbour count via uniform filter (toroidal via wrap mode)
        cnt = uniform_filter(B, size=2 * R + 1, mode="wrap") * area - B
        frac = cnt / (area - 1)
        born = (B < 0.5) & (frac >= b_lo) & (frac <= b_hi)
        surv = (B > 0.5) & (frac >= s_lo) & (frac <= s_hi)
        B = (born | surv).astype(np.float32)
        if g >= gens // 4:
            acc += B
            fcc += frac          # smooth neighbour-density carries structure even if B thins
            nframes += 1
    # combine crisp occupancy + density foam; density guarantees full-coverage variance
    acc /= max(nframes, 1)
    fcc /= max(nframes, 1)
    field = 0.45 * acc + fcc + 0.25 * B
    field = cv2.GaussianBlur(field.astype(np.float32), (0, 0), 0.4)
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- 11. Neural / MNCA
def neural_ca_worms(h, w, seed, *, res=288, gens=80) -> np.ndarray:
    """Neural / multi-neighbourhood CA ('worms' rule).

    A continuous state is convolved with two concentric ring kernels; the difference is
    pushed through a smooth activation that self-organizes into worm/loop networks —
    a continuous, learned-style cousin of Life distinct from RD."""
    rng = _rng(seed)
    A = rng.random((res, res)).astype(np.float32)
    R1, R2 = 3, 8
    def ring(r_in, r_out):
        s = 2 * r_out + 1
        yy, xx = np.mgrid[-r_out:r_out + 1, -r_out:r_out + 1]
        d = np.sqrt(xx * xx + yy * yy)
        k = ((d >= r_in) & (d <= r_out)).astype(np.float32)
        return k / (k.sum() + 1e-9)
    k_in = ring(0, R1)
    k_out = ring(R1 + 1, R2)
    for _ in range(gens):
        ni = convolve(A, k_in, mode="wrap")
        no = convolve(A, k_out, mode="wrap")
        d = ni - no
        # smooth "neural" activation: encourages thin connected worms
        act = np.tanh(8.0 * (d - 0.0))
        A = np.clip(A + 0.45 * (0.5 + 0.5 * act - A), 0.0, 1.0)
    field = A + 0.35 * np.cos(A * 9.4)   # crushed micro-detail along worms
    return _finalize(field, h, w)


# ----------------------------------------------------------------------------- registry
ENGINES = {
    "conway_density": conway_density,
    "eca_spacetime": eca_spacetime,
    "cyclic_ca": cyclic_ca,
    "bz_spirals": bz_spirals,
    "lenia": lenia,
    "hodgepodge": hodgepodge,
    "gray_scott_uskate": gray_scott_uskate,
    "anisotropic_turing": anisotropic_turing,
    "brians_brain": brians_brain,
    "larger_than_life": larger_than_life,
    "neural_ca_worms": neural_ca_worms,
}


# ----------------------------------------------------------------------------- self-test
def _fineness(f):
    return float((f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6))


if __name__ == "__main__":
    H = Wd = 1024
    print(f"{'engine':22s} {'secs':>6s} {'fine':>6s} {'std':>6s} {'min':>5s} {'max':>5s}  ok")
    allok = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, Wd, seed=12345)
        secs = time.time() - t0
        fine = _fineness(f)
        std = float(f.std())
        finite = bool(np.isfinite(f).all())
        inrange = (f.min() >= -1e-5) and (f.max() <= 1 + 1e-5)
        ok = (secs < 2.5) and (fine >= 0.12) and (std > 0.06) and finite and inrange
        allok = allok and ok
        print(f"{name:22s} {secs:6.2f} {fine:6.3f} {std:6.3f} "
              f"{f.min():5.2f} {f.max():5.2f}  {'PASS' if ok else 'FAIL'}")
    print("ALL PASS" if allok else "SOME FAILED")

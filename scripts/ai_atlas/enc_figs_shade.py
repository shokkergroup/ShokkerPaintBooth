"""Encyclopedia v2 lane D - a small illustrative "studio light" shader.

Turns the engine's spec values (R metal, G rough, B clearcoat) plus a paint colour into a lit
sphere, so a buyer can SEE what a spec number does. It is an illustration (one soft studio, no
track lighting): iRacing's own lighting differs. The numbers fed in always come from the engine
(preview_render output), never from memory.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG = (11, 14, 23)
PANEL = (17, 21, 36)
TEXT = (195, 204, 221)
HI = (238, 242, 249)
DIM = (135, 148, 173)
ORANGE = (245, 118, 26)
CYAN = (0, 229, 255)

_FONTS = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _FONTS:
        for p in (r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
            try:
                _FONTS[key] = ImageFont.truetype(p, size)
                break
            except Exception:
                continue
        else:
            _FONTS[key] = ImageFont.load_default()
    return _FONTS[key]


def _norm(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def env(d):
    """Studio environment radiance for unit directions d[...,3] (y up, z toward camera)."""
    dx, dy, dz = d[..., 0], d[..., 1], d[..., 2]
    up = np.clip(dy, 0, 1) ** 0.6
    sky = (0.22 + 0.45 * up)[..., None] * np.array([0.92, 0.97, 1.08])
    gr = np.clip(-dy, 0, 1) ** 0.5
    ground = (0.20 - 0.17 * gr)[..., None] * np.array([1.0, 0.95, 0.9])
    col = np.where((dy >= 0)[..., None], sky, ground)
    # overhead softbox
    sb = _smooth(0.70, 0.78, dy) * _smooth(0.9, 0.6, np.abs(dx) * 1.2)
    # left strip light
    ss = _smooth(0.45, 0.52, -dx) * _smooth(0.65, 0.5, np.abs(dy - 0.1)) * _smooth(-0.4, 0.0, dz)
    # horizon line and a warm kicker on the right
    hz = _smooth(0.05, 0.0, np.abs(dy - 0.02))
    kk = _smooth(0.55, 0.62, dx) * _smooth(0.4, 0.3, np.abs(dy + 0.1)) * _smooth(-0.3, 0.1, dz)
    col = col + (sb * 3.4)[..., None] + (ss * 2.3)[..., None] * np.array([1.0, 1.0, 1.0]) + (hz * 0.35)[..., None] \
        + (kk * 1.2)[..., None] * np.array([1.0, 0.85, 0.65])
    return col


def blurred_env(r, rough, k=40, seed=3):
    """Average the environment over a Gaussian cone around r (cone width grows with roughness 0..1).
    Deterministic Fibonacci/inverse-CDF sampling: no grain, same picture every run."""
    sigma = 0.012 + 0.95 * float(rough) ** 1.7
    helper = np.where((np.abs(r[..., 1:2]) < 0.9), np.array([0, 1, 0], np.float32), np.array([1, 0, 0], np.float32))
    t1 = _norm(np.cross(r, helper))
    t2 = np.cross(r, t1)
    acc = np.zeros(r.shape, np.float32)
    ga = np.pi * (3 - np.sqrt(5))
    for i in range(k):
        u = (i + 0.5) / k
        rad = np.sqrt(-2 * np.log(1 - u * 0.999)) * sigma
        ang = i * ga
        acc += env(_norm(r + t1 * (rad * np.cos(ang)) + t2 * (rad * np.sin(ang))))
    return acc / k


def shade_sphere(albedo, M, G, B, size=120, ss=2, bg=BG, texture=None):
    """Return an RGB uint8 square image with a lit sphere.

    albedo: (r,g,b) 0..255 paint colour, or None when `texture` (HxWx3 uint8) is given.
    M, G, B: spec channel values 0..255 (R metal, G rough, B clearcoat as iRacing reads them).
    """
    n_ = size * ss
    ys, xs = np.mgrid[0:n_, 0:n_].astype(np.float32)
    x = (xs + 0.5) / n_ * 2 - 1
    y = -((ys + 0.5) / n_ * 2 - 1)
    r2 = x * x + y * y
    mask = r2 <= 0.94
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    n = np.stack([x, y, nz], -1)
    v = np.array([0, 0, 1], np.float32)
    refl = _norm(2 * nz[..., None] * n - v)
    if texture is not None:
        tex = np.asarray(Image.fromarray(texture).resize((n_, n_), Image.LANCZOS), np.float32) / 255
        alb = tex
    else:
        alb = np.broadcast_to(np.array(albedo, np.float32) / 255, (n_, n_, 3))
    alb_lin = alb ** 2.2
    m = float(M) / 255
    rough = float(G) / 255
    cc = 0.0 if B <= 0 else float(np.clip((255 - B) / (255 - 16), 0, 1))
    light = _norm(np.array([-0.45, 0.65, 0.62], np.float32))
    ndl = np.clip(np.sum(n * light, -1), 0, 1)
    amb = (0.55 + 0.45 * n[..., 1])
    diff = alb_lin * (0.95 * ndl[..., None] + 0.32 * amb[..., None]) * (1 - m)
    f0 = 0.04 * (1 - m) + alb_lin * m
    fres = ((1 - nz) ** 5)[..., None] * (1 - rough) * (1 - f0)
    spec = (f0 + fres) * blurred_env(refl, rough)
    col = diff + spec
    if cc > 0:
        crough = 0.02 + 0.22 * (1 - cc)
        fc = (0.05 + 0.95 * (1 - nz) ** 4)[..., None] * (0.15 + 0.5 * cc) * 0.6
        coat = fc * blurred_env(refl, crough, seed=11)
        col = col * (1 - 0.35 * cc * fc) + coat
    col = 1 - np.exp(-1.05 * col)
    col = np.clip(col, 0, 1) ** (1 / 2.2)
    img = (col * 255 + 0.5).astype(np.uint8)
    base = np.zeros((n_, n_, 3), np.uint8)
    base[:] = bg
    a = _smooth(0.94, 0.90, r2)[..., None]
    out = (img * a + base * (1 - a)).astype(np.uint8)
    return Image.fromarray(out).resize((size, size), Image.LANCZOS)


def text(draw, xy, s, size=14, fill=TEXT, bold=False, anchor="la"):
    draw.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor)


def canvas(w, h, bg=BG):
    im = Image.new("RGB", (w, h), bg)
    return im, ImageDraw.Draw(im)

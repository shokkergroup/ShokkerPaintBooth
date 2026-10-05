# -*- coding: utf-8 -*-
"""
Shokker Paint Booth — 60s Facebook Alpha-Launch Video Ad builder.
Owner request 2026-06-10: edgy, high-impact, hook in first seconds, $20 alpha urgency.

Pure PIL/numpy frame renderer (no engine import) + numpy-synth soundtrack + ffmpeg encode.
Deterministic per-frame (seeded by frame index) -> safe to resume; frames written
incrementally and skipped if already on disk (token-efficiency mandate).

Usage:
  python build_video.py curate     # pick assets, build caches (curation.json + wall.png)
  python build_video.py stills     # render ~20 representative frames to stills/ for review
  python build_video.py frames     # render all 1800 frames (resumable)
  python build_video.py audio      # synthesize soundtrack wav
  python build_video.py encode     # ffmpeg mux -> spb_alpha_ad_1080.mp4
  python build_video.py all
"""
import json
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(HERE, "frames")
STILLS_DIR = os.path.join(HERE, "stills")
CACHE_DIR = os.path.join(HERE, "cache")
W = H = 1080
FPS = 30
DUR = 60.0
N_FRAMES = int(DUR * FPS)  # 1800
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"

BG = (8, 9, 12)
WHITE = (245, 247, 250)
ORANGE = (255, 122, 0)
ORANGE_HI = (255, 176, 48)
CYAN = (43, 200, 255)
DIM = (150, 155, 165)

FONT_DIR = r"C:\Windows\Fonts"


def font(name, size):
    f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    return f


def bahn(size, variation="Bold"):
    f = ImageFont.truetype(os.path.join(FONT_DIR, "bahnschrift.ttf"), size)
    try:
        f.set_variation_by_name(variation)
    except Exception:
        pass
    return f


# ----------------------------------------------------------------------------
# Timeline — single source of truth for video AND audio events (frame numbers)
# ----------------------------------------------------------------------------
EV = {
    # S1 hook (strobe + word slams)
    "hook_start": 0,
    "w_still": 4,
    "w_running": 26,
    "w_boring": 48,
    "w_paint": 70,
    "hook_end": 96,
    # S2 brand slam
    "logo_slam": 104,
    "logo_sub": 142,
    "brand_end": 216,
    # S3 wall of finishes
    "wall_start": 216,
    "c_finishes": 246,
    "c_patterns": 318,
    "c_overlays": 388,
    "c_combos": 458,
    "c_color": 492,
    "wall_end": 522,
    # S4 hero tour: 8 heroes x 70f
    "heroes_start": 522,
    "hero_len": 70,
    "heroes_end": 1082,
    # S5 control
    "livery_start": 1082,
    "channels_start": 1196,
    "punch_start": 1316,
    "control_end": 1392,
    # S6 CTA
    "cta_start": 1392,
    "ekg_start": 1396,
    "alpha_open": 1428,
    "price_slam": 1462,
    "price_up": 1532,
    "lock_in": 1592,
    "logo_out": 1652,
    "get_it": 1712,
    "end": N_FRAMES,
}

HERO_CATS = [
    ("CANDY & PEARL", "_candy_pearl_thumbs"),
    ("EXOTIC METAL", "_exotic_metal_thumbs"),
    ("PRIZM", "_rate_prizm_thumbs"),
    ("CHAMELEON", "_rate_chameleon_thumbs"),
    ("COLORSHOXX", "_rate_colorshoxx_thumbs"),
    ("FORBIDDEN DRAGON", "_rate_forbidden_dragon_thumbs"),
    ("MONEY SHOKK", "_rate_money_shokk_thumbs"),
    ("LIGHT OPTICS", "_rate_light_optics_thumbs"),
]

# ----------------------------------------------------------------------------
# Curation — choose the real assets the ad shows
# ----------------------------------------------------------------------------

def colorfulness(img):
    """Hasler & Süsstrunk colorfulness, on a small copy."""
    a = np.asarray(img.convert("RGB").resize((64, 64)), dtype=np.float32)
    rg = a[..., 0] - a[..., 1]
    yb = 0.5 * (a[..., 0] + a[..., 1]) - a[..., 2]
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2)
                 + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
                 + 0.4 * a.std())


def load_m7():
    try:
        d = json.load(open(os.path.join(ROOT, "_workbook_metrics", "m7_composite.json")))
        return {k.split(":", 1)[1]: v.get("composite", 0) for k, v in d.get("byFinish", {}).items()}
    except Exception:
        return {}


def curate():
    os.makedirs(CACHE_DIR, exist_ok=True)
    scores = load_m7()
    rng = random.Random(55)

    # --- hero per category: best blend of M7 score + colorfulness ---
    heroes = []
    for label, folder in HERO_CATS:
        d = os.path.join(ROOT, folder)
        cands = [f for f in os.listdir(d) if f.lower().endswith(".png")] if os.path.isdir(d) else []
        best, best_v = None, -1
        for f in cands:
            stem = os.path.splitext(f)[0]
            try:
                c = colorfulness(Image.open(os.path.join(d, f)))
            except Exception:
                continue
            v = c + 0.8 * scores.get(stem, 60)
            if v > best_v:
                best, best_v = f, v
        if best:
            heroes.append({"cat": label, "path": os.path.join(folder, best),
                           "name": os.path.splitext(best)[0].replace("_", " ").upper()})
        print(f"HERO {label}: {best}")

    # --- strobe set: most colorful across category folders + rate10 ---
    cat_pool = []
    for _, folder in HERO_CATS:
        d = os.path.join(ROOT, folder)
        if os.path.isdir(d):
            cat_pool += [folder + "/" + f for f in os.listdir(d) if f.endswith(".png")]
    cat_ranked = sorted(cat_pool, key=lambda p: -colorfulness(Image.open(os.path.join(ROOT, p))))

    r10 = os.path.join(ROOT, "_rate10_thumbs")
    pool = [f for f in os.listdir(r10) if f.endswith(".png")]
    rng.shuffle(pool)
    pool = pool[:320]  # sample for speed
    ranked = sorted(pool, key=lambda f: -colorfulness(Image.open(os.path.join(r10, f))))
    strobe = cat_ranked[:10] + ["_rate10_thumbs/" + f for f in ranked[:6]]
    rng.shuffle(strobe)

    # --- wall mosaic: 24x24 = 576 thumbs at 120px -> 2880px image, cached ---
    wall_n = 24
    cell = 120
    picks = [("_rate10_thumbs", f) for f in ranked[:240]]
    picks += [(p.rsplit("/", 1)[0], p.rsplit("/", 1)[1]) for p in cat_ranked[:240]]
    picks = (picks * 3)[: wall_n * wall_n]
    rng.shuffle(picks)
    wall = Image.new("RGB", (wall_n * cell, wall_n * cell), BG)
    for i, (fold, f) in enumerate(picks):
        try:
            t = Image.open(os.path.join(ROOT, fold, f)).convert("RGB").resize((cell - 4, cell - 4), Image.LANCZOS)
            t = vivid(t, 1.45, 1.28, 1.08)
        except Exception:
            continue
        x, y = (i % wall_n) * cell, (i // wall_n) * cell
        wall.paste(t, (x + 2, y + 2))
        if i % 96 == 0:
            print(f"wall {i}/{len(picks)}")
    wall.save(os.path.join(CACHE_DIR, "wall.png"))

    cur = {"heroes": heroes, "strobe": strobe}
    json.dump(cur, open(os.path.join(HERE, "curation.json"), "w"), indent=1)
    print("curation done:", len(heroes), "heroes,", len(strobe), "strobe")


# ----------------------------------------------------------------------------
# Effect helpers
# ----------------------------------------------------------------------------

def ease_out_cubic(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_out_back(t, s=2.2):
    t = min(max(t, 0.0), 1.0)
    t -= 1
    return 1 + t * t * ((s + 1) * t + s)


def ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


_VIGNETTE = None

def vignette():
    global _VIGNETTE
    if _VIGNETTE is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _VIGNETTE = np.clip(1.0 - 0.42 * np.clip(d - 0.55, 0, None) ** 1.6, 0, 1)[..., None]
    return _VIGNETTE


def post(img, frame, grain=8.0, vig=True):
    """Film grain + vignette, deterministic per frame."""
    a = np.asarray(img, dtype=np.float32)
    if vig:
        a *= vignette()
    if grain > 0:
        g = np.random.default_rng(frame).normal(0, grain, (H // 2, W // 2, 1)).astype(np.float32)
        g = np.repeat(np.repeat(g, 2, 0), 2, 1)
        a += g
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def rgb_split(img, dx):
    if dx <= 0:
        return img
    a = np.asarray(img)
    out = a.copy()
    out[:, :, 0] = np.roll(a[:, :, 0], dx, axis=1)
    out[:, :, 2] = np.roll(a[:, :, 2], -dx, axis=1)
    return Image.fromarray(out)


def glitch(img, frame, strength=1.0):
    rng = np.random.default_rng(frame * 7 + 3)
    a = np.asarray(img).copy()
    for _ in range(int(6 * strength)):
        y = rng.integers(0, H - 40)
        h = int(rng.integers(8, 46))
        off = int(rng.integers(-90, 90) * strength)
        a[y:y + h] = np.roll(a[y:y + h], off, axis=1)
    img = Image.fromarray(a)
    return rgb_split(img, int(6 * strength))


def text_size(draw, txt, fnt):
    b = draw.textbbox((0, 0), txt, font=fnt)
    return b[2] - b[0], b[3] - b[1], b


_MEAS = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def fit_blk(txt, start, max_w=1000):
    """Largest ariblk size <= start that fits max_w."""
    s = start
    while s > 16 and _MEAS.textlength(txt, font=font("ariblk.ttf", s)) > max_w:
        s = int(s * 0.94)
    return s


def fit_bahn(txt, start, max_w=1000, variation="Bold"):
    s = start
    while s > 14 and _MEAS.textlength(txt, font=bahn(s, variation)) > max_w:
        s = int(s * 0.94)
    return s


def vivid(img, color=1.5, bright=1.18, contrast=1.06):
    img = ImageEnhance.Color(img).enhance(color)
    img = ImageEnhance.Brightness(img).enhance(bright)
    return ImageEnhance.Contrast(img).enhance(contrast)


def clean_name(stem):
    toks = stem.replace("-", "_").split("_")
    if toks and toks[0] in ("msh", "cx", "fd", "efx", "spec", "spb"):
        toks = toks[1:]
    while toks and toks[-1] in ("paint", "base"):
        toks = toks[:-1]
    return " ".join(toks).upper()


def big_text(img, txt, fnt, cx, cy, fill=WHITE, glow=None, glow_r=22, stroke=0,
             stroke_fill=(0, 0, 0), anchor="mm"):
    """Text with optional glow layer."""
    if glow:
        lay = Image.new("RGB", img.size, (0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.text((cx, cy), txt, font=fnt, fill=glow, anchor=anchor)
        lay = lay.filter(ImageFilter.GaussianBlur(glow_r))
        img = Image.fromarray(np.clip(np.asarray(img, np.int16) + np.asarray(lay, np.int16), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.text((cx, cy), txt, font=fnt, fill=fill, anchor=anchor,
           stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def add_img(base, lay):
    return Image.fromarray(np.clip(np.asarray(base, np.int16) + np.asarray(lay, np.int16), 0, 255).astype(np.uint8))


def slam_scale(img_draw_fn, t_since, dur=8.0):
    """Returns scale + rgb-split px for a slam that lands with overshoot."""
    p = min(t_since / dur, 1.0)
    sc = 1.0 + 0.55 * (1 - ease_out_back(p))
    split = int(10 * (1 - p)) if t_since < dur else 0
    return sc, split


def fit_cover(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS)


def ken_burns(img, t, zoom_from, zoom_to, pan=(0, 0)):
    """img is preloaded larger than W,H. t in [0,1]."""
    z = zoom_from + (zoom_to - zoom_from) * ease_in_out(t)
    iw, ih = img.size
    cw, ch = int(W / z * iw / W * 1), int(H / z * ih / H * 1)
    cw = int(iw / z)
    ch = int(ih / z)
    cx = iw // 2 + int(pan[0] * t * iw * 0.08)
    cy = ih // 2 + int(pan[1] * t * ih * 0.08)
    x0 = min(max(cx - cw // 2, 0), iw - cw)
    y0 = min(max(cy - ch // 2, 0), ih - ch)
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)


def ekg_path(progress, base_y, amp=1.0):
    """Heartbeat polyline points across screen width for given draw progress."""
    pts = []
    # normalized EKG shape segments: (x, y) y in units of amp*px
    shape = [(0.00, 0), (0.30, 0), (0.34, -28), (0.38, 18), (0.42, 0),
             (0.46, 0), (0.50, -190), (0.54, 130), (0.58, 0), (0.66, 0),
             (0.70, -34), (0.74, 0), (1.00, 0)]
    maxx = progress
    for i in range(len(shape) - 1):
        (x0, y0), (x1, y1) = shape[i], shape[i + 1]
        for s in range(0, 14):
            x = x0 + (x1 - x0) * s / 13.0
            if x > maxx:
                return pts
            y = y0 + (y1 - y0) * s / 13.0
            pts.append((int(x * W), int(base_y + y * amp)))
    return pts


# ----------------------------------------------------------------------------
# Asset preload (lazy singleton)
# ----------------------------------------------------------------------------
class Assets:
    _inst = None

    @classmethod
    def get(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def __init__(self):
        cur = json.load(open(os.path.join(HERE, "curation.json")))
        self.strobe = [vivid(fit_cover(Image.open(os.path.join(ROOT, p)), W, H), 1.5, 1.15)
                       for p in cur["strobe"]]
        self.heroes = []
        for h in cur["heroes"]:
            im = Image.open(os.path.join(ROOT, h["path"])).convert("RGB")
            im = im.resize((1500, 1500), Image.LANCZOS)
            stem = os.path.splitext(os.path.basename(h["path"]))[0]
            self.heroes.append({"img": im, "cat": h["cat"], "name": clean_name(stem)})
        self.wall = Image.open(os.path.join(CACHE_DIR, "wall.png")).convert("RGB")
        # logo: crop to content, key out black-ish border is fine on dark bg
        lg = Image.open(os.path.join(ROOT, "assets", "branding", "ShokkerPaintBooth Logo 2 PNG.png")).convert("RGBA")
        bbox = lg.getbbox()
        lg = lg.crop(bbox) if bbox else lg
        self.logo = lg
        liv = Image.open(os.path.join(ROOT, "output", "_latest_render", "preview.png")).convert("RGB")
        lw, lh = liv.size
        # crop to the quilted hood/55 zone (left-center of the UV sheet)
        self.livery = liv.crop((int(0.03 * lw), int(0.10 * lh), int(0.72 * lw), int(0.97 * lh)))
        rw = os.path.join(ROOT, "Ricky Whittenburg")
        self.channels = []
        for nm, f in [("METALLIC", "spec_metallic.png"), ("ROUGHNESS", "spec_roughness.png"),
                      ("CLEARCOAT", "spec_clearcoat.png"), ("COMBINED", "spec_full.png")]:
            self.channels.append((nm, Image.open(os.path.join(rw, f)).convert("RGB").resize((534, 534), Image.LANCZOS)))

    def logo_on(self, img, cx, cy, width, alpha=1.0):
        lg = self.logo.resize((width, int(width * self.logo.size[1] / self.logo.size[0])), Image.LANCZOS)
        if alpha < 1.0:
            a = lg.split()[3].point(lambda v: int(v * alpha))
            lg.putalpha(a)
        img.paste(lg, (cx - lg.size[0] // 2, cy - lg.size[1] // 2), lg)
        return img


# ----------------------------------------------------------------------------
# Scenes
# ----------------------------------------------------------------------------

def scene_hook(f, A):
    """Strobe finishes + word slams."""
    idx = (f // 4) % len(A.strobe)
    img = A.strobe[idx].copy()
    # darken for text pop, pulse brightness on strobe switch
    dark = 0.55 if (f % 4) else 0.72
    img = Image.fromarray((np.asarray(img, np.float32) * dark).astype(np.uint8))
    words = [("STILL", EV["w_still"]), ("RUNNING", EV["w_running"]),
             ("BORING", EV["w_boring"]), ("PAINT?", EV["w_paint"])]
    fnt = font("ariblk.ttf", 178)
    ys = [250, 460, 670, 880]
    for i, (wd, t0) in enumerate(words):
        if f < t0:
            break
        ts = f - t0
        p = min(ts / 7.0, 1.0)
        sc = 1.0 + 0.6 * (1 - ease_out_back(p))
        fz = font("ariblk.ttf", int(178 * sc)) if sc != 1.0 else fnt
        col = WHITE if wd != "PAINT?" else ORANGE_HI
        glow = (60, 30, 0) if wd == "PAINT?" else None
        img = big_text(img, wd, fz, W // 2, ys[i], fill=col, glow=glow, stroke=10, stroke_fill=(0, 0, 0))
        if ts < 4:
            img = rgb_split(img, 8 - 2 * ts)
    return post(img, f, grain=11)


def scene_brand(f, A):
    img = Image.new("RGB", (W, H), BG)
    t0 = EV["logo_slam"]
    if f < t0:
        return post(img, f, grain=5)
    ts = f - t0
    p = min(ts / 10.0, 1.0)
    sc = 1.6 - 0.6 * ease_out_back(p)
    width = int(980 * sc) if p < 1 else 980
    # shockwave ring
    if 0 <= ts < 26:
        d = ImageDraw.Draw(img)
        r = 80 + ts * 34
        al = int(200 * (1 - ts / 26.0))
        d.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r],
                  outline=(al, int(al * 0.6), 0), width=max(2, 14 - ts // 2))
    img = A.logo_on(img, W // 2, H // 2 - 60, min(width, 1040))
    if ts < 5:
        img = rgb_split(img, 10 - 2 * ts)
    if f >= EV["logo_sub"]:
        a = min((f - EV["logo_sub"]) / 10.0, 1.0)
        line1 = "THE CUSTOM FINISH ENGINE FOR PEOPLE WHO PAINT."
        line2 = "iRACING-READY SPEC MAPS  |  REAL PAINT PHYSICS"
        sub = bahn(fit_bahn(line1, 46, 960), "Bold")
        col = tuple(int(c * a) for c in WHITE)
        img = big_text(img, line1, sub, W // 2, H // 2 + 330, fill=col)
        col2 = tuple(int(c * a) for c in ORANGE)
        img = big_text(img, line2, bahn(fit_bahn(line2, 34, 880, "SemiBold"), "SemiBold"),
                       W // 2, H // 2 + 392, fill=col2)
    # shine sweep across logo
    if 24 <= ts <= 60:
        sp = (ts - 24) / 36.0
        x = int(-300 + (W + 600) * sp)
        lay = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(lay)
        d.polygon([(x, 0), (x + 140, 0), (x - 160, H), (x - 300, H)], fill=70)
        lay = lay.filter(ImageFilter.GaussianBlur(18))
        img = add_img(img, Image.merge("RGB", (lay, lay, lay)))
    return post(img, f, grain=6)


COUNTERS = [
    ("c_finishes", 2000, "+ CUSTOM FINISHES"),
    ("c_patterns", 750, "+ PATTERNS"),
    ("c_overlays", 400, "+ SPEC MAP OVERLAYS"),
]


def scene_wall(f, A):
    t = (f - EV["wall_start"]) / float(EV["wall_end"] - EV["wall_start"])
    # zoom out 3.2 -> 1.0 across the wall mosaic with diagonal drift
    z = 3.2 - 2.2 * ease_in_out(min(t * 1.25, 1.0))
    iw, ih = A.wall.size
    cw, ch = int(iw / z), int(ih / z)
    cx = int(iw * (0.36 + 0.14 * t))
    cy = int(ih * (0.40 + 0.10 * t))
    x0 = min(max(cx - cw // 2, 0), iw - cw)
    y0 = min(max(cy - ch // 2, 0), ih - ch)
    img = A.wall.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)
    img = Image.fromarray((np.asarray(img, np.float32) * 0.82).astype(np.uint8))

    # rolling counters (suppressed once the combos card takes over)
    for key, target, suffix in COUNTERS if f < EV["c_combos"] else []:
        t0 = EV[key]
        if f < t0:
            continue
        ts = f - t0
        if ts > 64 and key != "c_overlays":
            continue
        p = min(ts / 14.0, 1.0)
        val = int(target * ease_out_cubic(p))
        sc = 1.0 + 0.45 * (1 - ease_out_back(min(ts / 8.0, 1.0)))
        # soft dark band for legibility over the bright wall
        band = Image.new("L", (W, H), 0)
        ImageDraw.Draw(band).rectangle([0, 290, W, 630], fill=150)
        band = band.filter(ImageFilter.GaussianBlur(40))
        img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, band)
        num_f = font("ariblk.ttf", int(150 * sc))
        suf_f = bahn(54, "Bold")
        ypos = 430
        img = big_text(img, f"{val:,}{'+' if p >= 1 else ''}", num_f, W // 2, ypos,
                       fill=WHITE, glow=(70, 34, 0), glow_r=26, stroke=8, stroke_fill=(0, 0, 0))
        img = big_text(img, suffix.strip("+ "), suf_f, W // 2, ypos + 130, fill=ORANGE_HI,
                       stroke=4, stroke_fill=(0, 0, 0))
        if ts < 4:
            img = rgb_split(img, 8 - 2 * ts)
        break  # show one counter at a time

    if f >= EV["c_combos"]:
        ts = f - EV["c_combos"]
        ov = Image.new("RGB", (W, H), (0, 0, 0))
        a = min(ts / 6.0, 1.0) * 0.72
        img = Image.blend(img, ov, a)
        sc = 1.0 + 0.5 * (1 - ease_out_back(min(ts / 9.0, 1.0)))
        sz1 = fit_blk("27 MILLION+", 168, 1000)
        sz2 = fit_blk("COMBINATIONS", 96, 860)
        img = big_text(img, "27 MILLION+", font("ariblk.ttf", int(sz1 * sc)), W // 2, 420,
                       fill=ORANGE_HI, glow=(90, 40, 0), glow_r=30, stroke=8, stroke_fill=(0, 0, 0))
        img = big_text(img, "COMBINATIONS", font("ariblk.ttf", int(sz2 * sc)), W // 2, 560,
                       fill=WHITE, stroke=6, stroke_fill=(0, 0, 0))
        if f >= EV["c_color"]:
            a2 = min((f - EV["c_color"]) / 8.0, 1.0)
            img = big_text(img, "...before you even pick a color.", bahn(52, "SemiBold"),
                           W // 2, 700, fill=tuple(int(c * a2) for c in CYAN))
        if ts < 4:
            img = rgb_split(img, 10 - 2 * ts)
    return post(img, f, grain=7)


def scene_heroes(f, A):
    rel = f - EV["heroes_start"]
    hl = EV["hero_len"]
    i = min(rel // hl, len(A.heroes) - 1)
    ts = rel - i * hl
    h = A.heroes[int(i)]
    zin = (i % 2 == 0)
    img = ken_burns(h["img"], ts / float(hl),
                    1.35 if zin else 1.0, 1.0 if zin else 1.35,
                    pan=((-1) ** i * 0.6, 0.3 * (-1) ** (i // 2)))
    # gradient floor for text legibility
    grad = np.ones((H, W, 1), np.float32)
    yy = np.linspace(0, 1, H)[:, None, None].astype(np.float32)
    grad = 1.0 - 0.55 * np.clip((yy - 0.62) / 0.38, 0, 1)
    top = 1.0 - 0.35 * np.clip((0.25 - yy) / 0.25, 0, 1)
    img = Image.fromarray(np.clip(np.asarray(img, np.float32) * grad * top, 0, 255).astype(np.uint8))

    # category chip top-left
    chip_p = ease_out_cubic(min(ts / 8.0, 1.0))
    d = ImageDraw.Draw(img)
    cf = bahn(44, "Bold")
    tw, th, _ = text_size(d, h["cat"], cf)
    cx = int(-tw - 80 + (110 + tw + 80) * chip_p)
    d.rectangle([cx - 26, 92, cx + tw + 26, 92 + th + 34], fill=ORANGE)
    d.text((cx, 104), h["cat"], font=cf, fill=(12, 8, 4))
    # index
    d.text((W - 70, 104), f"{int(i) + 1:02d} / 2,000+", font=bahn(36, "SemiBold"), fill=DIM, anchor="ra")
    # finish name bottom
    img = big_text(img, h["name"], font("ariblk.ttf", fit_blk(h["name"], 74, W - 150)), 70, H - 150,
                   fill=WHITE, stroke=6, stroke_fill=(0, 0, 0), anchor="lm")
    d = ImageDraw.Draw(img)
    d.rectangle([70, H - 100, 70 + 240, H - 92], fill=ORANGE)

    if int(i) >= 6:
        img = big_text(img, "EVERY SINGLE ONE — INCLUDED.", bahn(54, "Bold"), W // 2, 320,
                       fill=CYAN, glow=(0, 50, 70), glow_r=22, stroke=4, stroke_fill=(0, 0, 0))
    # glitch transition at hero boundaries
    if ts >= hl - 4 or ts < 3:
        img = glitch(img, f, strength=0.9)
    return post(img, f, grain=8)


def scene_control(f, A):
    img = Image.new("RGB", (W, H), BG)
    if f < EV["channels_start"]:
        # real livery render
        ts = f - EV["livery_start"]
        t = ts / float(EV["channels_start"] - EV["livery_start"])
        liv = ken_burns(fit_cover(A.livery, 1500, 1500), t, 1.0, 1.28, pan=(0.4, -0.4))
        liv = Image.fromarray((np.asarray(liv, np.float32) * 0.85).astype(np.uint8))
        img = liv
        h1 = "REAL LIVERIES. REAL OUTPUT."
        img = big_text(img, h1, font("ariblk.ttf", fit_blk(h1, 84, 1000)), W // 2, 170,
                       fill=WHITE, glow=(60, 30, 0), stroke=8, stroke_fill=(0, 0, 0))
        a = min(max((ts - 12) / 10.0, 0.0), 1.0)
        h2 = "GAME-READY SPEC MAPS, STRAIGHT OUT OF THE BOOTH."
        img = big_text(img, h2, bahn(fit_bahn(h2, 44, 1000), "Bold"), W // 2, 950,
                       fill=tuple(int(c * a) for c in ORANGE_HI),
                       stroke=4, stroke_fill=(0, 0, 0))
    elif f < EV["punch_start"]:
        ts = f - EV["channels_start"]
        hc = "CONTROL EVERY CHANNEL."
        img = big_text(img, hc, font("ariblk.ttf", fit_blk(hc, 76, 1000)), W // 2, 105,
                       fill=WHITE, glow=(60, 30, 0), stroke=6, stroke_fill=(0, 0, 0))
        pos = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for k, (nm, ch) in enumerate(A.channels):
            t0 = k * 7
            if ts < t0:
                continue
            p = ease_out_back(min((ts - t0) / 8.0, 1.0))
            gx, gy = pos[k]
            x = int(6 + gx * 540)
            y0 = int(190 + gy * 444)
            xoff = int((1 - p) * (-700 if gx == 0 else 700))
            tile = fit_cover(ch, 534, 408)
            img.paste(tile, (x + xoff, y0))
            d = ImageDraw.Draw(img)
            d.rectangle([x + xoff, y0 + 408 - 56, x + xoff + 534, y0 + 408], fill=(0, 0, 0))
            d.text((x + xoff + 16, y0 + 408 - 48), nm, font=bahn(34, "Bold"),
                   fill=ORANGE_HI if nm != "COMBINED" else CYAN)
    else:
        ts = f - EV["punch_start"]
        lines = [("PATTERN-PER-CHANNEL CONTROL.", 0, WHITE),
                 ("ZONE-BY-ZONE PAINTING.", 24, WHITE),
                 ("NOBODY ELSE HAS THIS.", 48, ORANGE_HI)]
        # dim spec backdrop
        bk = vivid(A.channels[3][1].resize((W, W), Image.BILINEAR).crop((0, 0, W, H)), 1.3, 1.0)
        img = Image.fromarray((np.asarray(bk, np.float32) * 0.30).astype(np.uint8))
        ys = [350, 540, 730]
        for k, (txt, t0, col) in enumerate(lines):
            if ts < t0:
                break
            p = min((ts - t0) / 7.0, 1.0)
            sc = 1.0 + 0.5 * (1 - ease_out_back(p))
            sz = fit_blk(txt, 64 if k < 2 else 86, 980)
            img = big_text(img, txt, font("ariblk.ttf", int(sz * sc)), W // 2, ys[k],
                           fill=col, glow=(70, 34, 0) if k == 2 else None,
                           stroke=6, stroke_fill=(0, 0, 0))
            if ts - t0 < 4:
                img = rgb_split(img, 8 - 2 * (ts - t0))
    return post(img, f, grain=7)


def scene_cta(f, A):
    img = Image.new("RGB", (W, H), (5, 5, 8))
    d = ImageDraw.Draw(img)
    # EKG pulse line (logo motif)
    if f >= EV["ekg_start"]:
        prog = min((f - EV["ekg_start"]) / 26.0, 1.0)
        base_y = 150 if f >= EV["alpha_open"] else H // 2
        pts = ekg_path(prog, base_y, amp=1.0 if base_y == H // 2 else 0.45)
        if len(pts) > 1:
            lay = Image.new("RGB", (W, H), (0, 0, 0))
            dl = ImageDraw.Draw(lay)
            dl.line(pts, fill=CYAN, width=10)
            lay = lay.filter(ImageFilter.GaussianBlur(10))
            img = add_img(img, lay)
            d = ImageDraw.Draw(img)
            d.line(pts, fill=ORANGE_HI, width=5)
        # continuing small pulse blip after draw completes
    if f >= EV["alpha_open"]:
        ts = f - EV["alpha_open"]
        sc = 1.0 + 0.4 * (1 - ease_out_back(min(ts / 8.0, 1.0)))
        ha = "ALPHA ACCESS IS OPEN."
        img = big_text(img, ha, font("ariblk.ttf", int(fit_blk(ha, 78, 980) * sc)), W // 2, 300,
                       fill=WHITE, stroke=6, stroke_fill=(0, 0, 0))
    if f >= EV["price_slam"]:
        ts = f - EV["price_slam"]
        p = min(ts / 9.0, 1.0)
        sc = 1.0 + 0.8 * (1 - ease_out_back(p))
        pulse = 1.0 + 0.018 * math.sin(ts * 0.45)
        img = big_text(img, "$20", font("ariblk.ttf", int(430 * sc * pulse)), W // 2, 590,
                       fill=ORANGE_HI, glow=(120, 55, 0), glow_r=44, stroke=10, stroke_fill=(0, 0, 0))
        img = big_text(img, "TODAY:", bahn(48, "Bold"), W // 2, 385, fill=DIM)
        if ts < 4:
            img = rgb_split(img, 12 - 3 * ts)
    if f >= EV["price_up"]:
        a = min((f - EV["price_up"]) / 8.0, 1.0)
        l1 = "AT FULL RELEASE, THE PRICE GOES WAY UP."
        img = big_text(img, l1, bahn(fit_bahn(l1, 48, 960), "Bold"),
                       W // 2, 830, fill=tuple(int(c * a) for c in WHITE))
    if f >= EV["lock_in"]:
        a = min((f - EV["lock_in"]) / 8.0, 1.0)
        l2 = "BUY ONCE. LOCK IT IN. KEEP EVERY UPDATE."
        img = big_text(img, l2, bahn(fit_bahn(l2, 46, 960), "Bold"),
                       W // 2, 905, fill=tuple(int(c * a) for c in CYAN))
    if f >= EV["logo_out"]:
        ts = f - EV["logo_out"]
        # fade overlay then logo card
        fade = min(ts / 8.0, 1.0)
        card = Image.new("RGB", (W, H), (5, 5, 8))
        card = A.logo_on(card, W // 2, 400, 880)
        card = big_text(card, "WE DON'T DO BORING.", font("ariblk.ttf", 72), W // 2, 720,
                        fill=WHITE, stroke=6, stroke_fill=(0, 0, 0))
        if f >= EV["get_it"]:
            tp = f - EV["get_it"]
            bp = 1.0 + 0.03 * math.sin(tp * 0.35)
            btxt = "GET THE ALPHA  —  LINK IN POST"
            bf = bahn(int(44 * bp), "Bold")
            tw = _MEAS.textlength(btxt, font=bf)
            bw, bh = int(tw + 110), int(110 * bp)
            dc = ImageDraw.Draw(card)
            dc.rounded_rectangle([W // 2 - bw // 2, 880 - bh // 2, W // 2 + bw // 2, 880 + bh // 2],
                                 radius=18, fill=ORANGE)
            card = big_text(card, btxt, bf, W // 2, 880, fill=(14, 9, 4))
        img = Image.blend(img, card, fade)
    return post(img, f, grain=6)


def render_frame(f, A):
    if f < EV["hook_end"]:
        return scene_hook(f, A)
    if f < EV["brand_end"]:
        return scene_brand(f, A)
    if f < EV["wall_end"]:
        return scene_wall(f, A)
    if f < EV["heroes_end"]:
        return scene_heroes(f, A)
    if f < EV["control_end"]:
        return scene_control(f, A)
    return scene_cta(f, A)


# ----------------------------------------------------------------------------
# Drivers
# ----------------------------------------------------------------------------

def do_frames(only=None):
    os.makedirs(FRAMES_DIR, exist_ok=True)
    A = Assets.get()
    todo = only if only is not None else range(N_FRAMES)
    done = 0
    for f in todo:
        path = os.path.join(FRAMES_DIR, f"f_{f:05d}.jpg")
        if only is None and os.path.exists(path):
            continue
        img = render_frame(f, A)
        img.save(path, quality=92)
        done += 1
        if done % 100 == 0:
            print(f"frame {f}/{N_FRAMES}")
    print(f"frames done ({done} rendered)")


STILL_FRAMES = [10, 32, 56, 78, 116, 150, 250, 324, 396, 470, 500, 560, 700, 1000,
                1070, 1120, 1240, 1350, 1440, 1480, 1560, 1700]


def do_stills():
    os.makedirs(STILLS_DIR, exist_ok=True)
    A = Assets.get()
    for f in STILL_FRAMES:
        render_frame(f, A).save(os.path.join(STILLS_DIR, f"s_{f:05d}.jpg"), quality=92)
        print("still", f)


# ----------------------------------------------------------------------------
# Audio — 128 BPM synth driven off the same EV timeline
# ----------------------------------------------------------------------------
SR = 44100


def _t(n):
    return np.arange(n, dtype=np.float32) / SR


def place(buf, snd, at_s, gain=1.0):
    i = int(at_s * SR)
    j = min(i + len(snd), len(buf))
    if i < len(buf):
        buf[i:j] += snd[: j - i] * gain


def kick():
    n = int(0.30 * SR)
    t = _t(n)
    f = 150 * np.exp(-t * 22) + 46
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 9)
    s[: int(0.004 * SR)] += np.linspace(0.8, 0, int(0.004 * SR))
    return s.astype(np.float32)


def hat(open_=False):
    n = int((0.16 if open_ else 0.05) * SR)
    rng = np.random.default_rng(7 if open_ else 3)
    s = rng.normal(0, 1, n).astype(np.float32)
    s = np.diff(s, prepend=0)  # crude highpass
    return (s * np.exp(-_t(n) * (18 if open_ else 70)) * 0.5).astype(np.float32)


def clap():
    n = int(0.22 * SR)
    rng = np.random.default_rng(11)
    s = rng.normal(0, 1, n).astype(np.float32)
    s *= np.sin(2 * np.pi * 1500 * _t(n)) * 0.4 + 0.6
    env = np.exp(-_t(n) * 26)
    for k in range(3):
        env[int(0.012 * k * SR):] += np.exp(-_t(n - int(0.012 * k * SR)) * 30) * 0.6
    return (s * env * 0.45).astype(np.float32)


def impact():
    n = int(1.1 * SR)
    t = _t(n)
    f = 90 * np.exp(-t * 8) + 38
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.2)
    rng = np.random.default_rng(5)
    s += np.diff(rng.normal(0, 1, n), prepend=0) * np.exp(-t * 28) * 0.7
    return np.tanh(s * 1.8).astype(np.float32)


def tick():
    n = int(0.03 * SR)
    rng = np.random.default_rng(9)
    s = np.diff(rng.normal(0, 1, n), prepend=0) * np.exp(-_t(n) * 120)
    return (s * 0.7).astype(np.float32)


def riser(dur=2.0):
    n = int(dur * SR)
    t = _t(n)
    rng = np.random.default_rng(13)
    nz = np.diff(rng.normal(0, 1, n), prepend=0)
    sw = np.sin(2 * np.pi * np.cumsum(120 + 900 * (t / dur) ** 2) / SR)
    env = (t / dur) ** 2.2
    return ((nz * 0.5 + sw * 0.4) * env * 0.8).astype(np.float32)


def bass_note(freq, dur):
    n = int(dur * SR)
    t = _t(n)
    # band-limited-ish saw: few harmonics
    s = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 7))
    env = np.minimum(1, t * 200) * np.exp(-t * 5)
    return (s * env * 0.30).astype(np.float32)


def pad_chord(freqs, dur, vol=0.16):
    n = int(dur * SR)
    t = _t(n)
    s = np.zeros(n, np.float32)
    for f0 in freqs:
        for det in (0.996, 1.0, 1.004):
            s += sum(np.sin(2 * np.pi * f0 * det * k * t + f0 * k) / (k * k) for k in range(1, 5))
    att = np.minimum(1, t / 1.2)
    rel = np.minimum(1, (dur - t) / 1.5)
    return (s / len(freqs) / 3 * att * rel * vol).astype(np.float32)


def heartbeat():
    n = int(0.5 * SR)
    t = _t(n)
    lub = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 26)
    dub = np.zeros(n, np.float32)
    off = int(0.16 * SR)
    td = _t(n - off)
    dub[off:] = np.sin(2 * np.pi * 48 * td) * np.exp(-td * 30) * 0.8
    return ((lub + dub) * 0.9).astype(np.float32)


def do_audio():
    n = int(DUR * SR)
    mix = np.zeros(n, np.float32)
    beat = 60.0 / 128.0
    ev_s = {k: v / FPS for k, v in EV.items()}

    # --- impacts on every text slam ---
    slams = ["w_still", "w_running", "w_boring", "w_paint", "logo_slam",
             "c_finishes", "c_patterns", "c_overlays", "c_combos",
             "punch_start", "alpha_open", "price_slam", "logo_out"]
    imp = impact()
    for s in slams:
        place(mix, imp, ev_s[s], 0.9 if s in ("logo_slam", "price_slam", "c_combos") else 0.55)
    place(mix, impact(), ev_s["punch_start"] + 24 / FPS, 0.45)
    place(mix, impact(), ev_s["punch_start"] + 48 / FPS, 0.6)

    # --- hook: strobe ticks ---
    tk = tick()
    f = 0
    while f < EV["hook_end"]:
        place(mix, tk, f / FPS, 0.5)
        f += 4
    place(mix, riser(1.6), ev_s["logo_slam"] - 1.6, 0.8)

    # --- groove: kick 4-on-floor from wall to control end ---
    kc, ht, ho, cp = kick(), hat(), hat(True), clap()
    t0, t1 = ev_s["wall_start"], ev_s["control_end"]
    b = 0
    t = t0
    while t < t1:
        place(mix, kc, t, 0.95)
        place(mix, ht, t + beat / 2, 0.5)
        if b % 2 == 1:
            place(mix, cp, t, 0.5)
        if b % 4 == 3:
            place(mix, ho, t + beat / 2, 0.4)
        # bass: root-fifth pattern in A minor (A1=55, E2=82.4, G1=49, F1=43.65)
        root = [55.0, 55.0, 43.65, 49.0][(b // 8) % 4]
        for sub in range(2):
            place(mix, bass_note(root, beat / 2 * 0.9), t + sub * beat / 2, 1.0 if sub == 0 else 0.7)
        b += 1
        t = t0 + b * beat

    # sidechain duck around kicks (cheap: scale whole mix dips)
    duck = np.ones(n, np.float32)
    b = 0
    t = t0
    dl = int(0.12 * SR)
    dip = 1 - 0.45 * np.exp(-_t(dl) * 18)
    while t < t1:
        i = int(t * SR)
        j = min(i + dl, n)
        duck[i:j] = np.minimum(duck[i:j], dip[: j - i])
        b += 1
        t = t0 + b * beat
    # apply duck only to pads/bass region — simpler: to whole mix minus re-add kicks
    mix *= duck
    b = 0
    t = t0
    while t < t1:
        place(mix, kc, t, 0.5)  # restore kick punch over duck
        b += 1
        t = t0 + b * beat

    # --- pads ---
    place(mix, pad_chord([110, 130.8, 164.8], ev_s["wall_start"] - ev_s["logo_slam"] + 2), ev_s["logo_slam"], 1.0)  # Am
    place(mix, pad_chord([110, 130.8, 164.8, 196], 14), ev_s["wall_start"], 0.8)
    place(mix, pad_chord([87.3, 110, 130.8], 12), ev_s["heroes_start"], 0.7)   # F
    place(mix, pad_chord([98, 123.5, 147], 12), ev_s["heroes_start"] + 12, 0.7)  # G
    place(mix, pad_chord([110, 130.8, 164.8], ev_s["control_end"] - ev_s["livery_start"]), ev_s["livery_start"], 0.8)
    place(mix, pad_chord([55, 110, 130.8, 164.8], DUR - ev_s["cta_start"] - 0.5), ev_s["cta_start"], 0.9)

    # --- CTA: heartbeat + final riser + end hit ---
    hb = heartbeat()
    t = ev_s["ekg_start"]
    while t < ev_s["logo_out"]:
        place(mix, hb, t, 0.9)
        t += 0.92
    place(mix, riser(2.2), ev_s["logo_out"] - 2.2, 0.7)
    place(mix, impact(), ev_s["get_it"], 0.5)

    # --- master ---
    mix = np.tanh(mix * 1.25)
    mix *= 0.94 / max(1e-6, np.abs(mix).max())
    # gentle fade-out last 0.8s
    fo = int(0.8 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    pcm = (mix * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(os.path.join(HERE, "audio.wav"), "wb") as wv:
        wv.setnchannels(2)
        wv.setsampwidth(2)
        wv.setframerate(SR)
        wv.writeframes(stereo.tobytes())
    print("audio.wav written")


def do_encode():
    out = os.path.join(HERE, "SPB_Alpha_Ad_60s_1080.mp4")
    cmd = [FFMPEG, "-y", "-framerate", str(FPS),
           "-i", os.path.join(FRAMES_DIR, "f_%05d.jpg"),
           "-i", os.path.join(HERE, "audio.wav"),
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("encoded:", out, os.path.getsize(out) / 1e6, "MB")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("curate", "all"):
        curate()
    if mode == "stills":
        do_stills()
    if mode in ("frames", "all"):
        do_frames()
    if mode in ("audio", "all"):
        do_audio()
    if mode in ("encode", "all"):
        do_encode()

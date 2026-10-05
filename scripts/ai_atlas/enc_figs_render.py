"""Encyclopedia v2 lane D - REAL engine renders r01..r14.

    python scripts/ai_atlas/enc_figs_render.py              # build every missing figure
    python scripts/ai_atlas/enc_figs_render.py r01 r04      # only these (always re-render)
    python scripts/ai_atlas/enc_figs_render.py --force      # rebuild all

ONE engine boot per run (CLAUDE.md). Zones go through shokker_engine_v2.preview_render, the same call the
app's live preview uses; the zone dict shape is copied from a real output/job_render_*/zones_payload.json
(name, color, intensity, base, pattern, base_color_mode, base_color, base_color_explicit, ...).
The engine's spec output (after iron rules) is what the illustrative studio shader (enc_figs_shade)
is fed - so a swatch always shows what the ENGINE produced, not what was asked for.
Never hits the live server (59876). Each figure is written to disk as soon as it is done.
Output only prints one verdict line per figure.
"""
import io
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import enc_figs_lib as L  # noqa: E402
import enc_figs_shade as S  # noqa: E402
from enc_figs_lib import ROOT, figure, reg, src  # noqa: E402

WORK = ROOT / "_enc_work"
WORK.mkdir(exist_ok=True)
FIGS = {}
E = None  # the engine module, imported lazily (one boot)
MAX_KB = 250
RED = (200, 40, 30)  # the paint colour of the sweep swatches (#c8281e)


def fig(fid):
    def deco(fn):
        FIGS[fid] = fn
        return fn
    return deco


# ------------------------------------------------------------------ engine plumbing
def boot():
    global E
    if E is None:
        logging.disable(logging.WARNING)
        t = time.time()
        import shokker_engine_v2 as eng
        logging.disable(logging.NOTSET)
        logging.getLogger().setLevel(logging.ERROR)
        for n in list(logging.root.manager.loggerDict):
            logging.getLogger(n).setLevel(logging.ERROR)
        E = eng
        print(f"engine boot {time.time() - t:.1f}s", flush=True)
    return E


def zone(base="gloss", color="remaining", name="zone", **kw):
    """One zone dict, same keys as a real zones_payload.json zone."""
    z = {"name": name, "color": color, "intensity": "100", "pattern_paint_mode": "overlay", "pattern_hue_shift": 0,
         "pattern_saturation": 0, "pattern_spec_opacity": 0, "base": base, "pattern": "none", "base_color_mode": "solid",
         "base_color": "#c8281e", "base_color_explicit": True, "base_color_strength": 1, "hard_edge": True}
    z.update(kw)
    return z


def pick(rgb, tol=30):
    return [{"color_rgb": list(rgb), "tolerance": tol}]


def render(paint_path, zones, scale=1.0, seed=51):
    eng = boot()
    if not hasattr(eng.build_multi_zone, "_zone_cache"):
        eng.build_multi_zone._zone_cache = {}
    eng.build_multi_zone._zone_cache.clear()  # the stale-cache trap (spb-render-replay skill)
    pr, sp, ms = eng.preview_render(str(paint_path), zones, seed=seed, preview_scale=scale)
    return np.asarray(pr), np.asarray(sp), ms


def flat_paint(name, size=64, rgb=(140, 140, 150)):
    p = WORK / f"{name}.png"
    if not p.exists():
        Image.fromarray(np.full((size, size, 3), rgb, np.uint8)).save(p)
    return p


def swatch_spec(m, r, cc, base="gloss"):
    """Engine spec (after iron rules) + paint colour for one flat material."""
    pr, sp, _ = render(flat_paint("flat64"), [zone(base, spec_material_override={"m": m, "r": r, "cc": cc, "a": 255})])
    c = sp[16:48, 16:48].reshape(-1, 4)
    spec = [int(np.median(c[:, i])) for i in range(4)]
    col = tuple(int(v) for v in np.median(pr[16:48, 16:48].reshape(-1, 3), axis=0))
    return spec, col


# ------------------------------------------------------------------ synthetic livery sheet
def car_boxes():
    d = json.loads((ROOT / "scripts/ai_atlas/car_atlas_clusters.json").read_text(encoding="utf8"))
    return [c for c in d["cars"] if c["id"] == "nextgen-camry-camaro-2024"][0]["parts"]


def make_sheet(name="sheet_livery", variant="plain"):
    """A neutral demo livery laid out like the NASCAR Next Gen sheet (no real driver art)."""
    p = WORK / f"{name}.png"
    if p.exists():
        return p
    S2 = 2048
    im = np.zeros((S2, S2, 3), np.uint8)
    im[:] = (22, 24, 32)
    BLUE, WHITE, REDC, TEAL = (31, 59, 143), (232, 232, 238), (214, 45, 32), (30, 140, 150)
    parts = car_boxes()
    rng = np.random.default_rng(5)
    for nm, pt in parts.items():
        x0, y0, x1, y1 = [int(v / 100 * S2) for v in pt["box"]]
        x0 += 6; y0 += 6; x1 -= 6; y1 -= 6
        body = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
        body[:] = BLUE
        if variant == "shaded":  # lightness drifts across the body so colour tolerance matters
            g = np.linspace(-1, 1, x1 - x0, dtype=np.float32)[None, :, None]
            body = np.clip(body + g * np.array([40, 60, 80], np.float32) + rng.normal(0, 2.5, body.shape), 0, 255)
        im[y0:y1, x0:x1] = body.astype(np.uint8)
        h = y1 - y0
        w = x1 - x0
        if nm in ("left side", "right side"):
            im[y0 + int(h * 0.55):y0 + int(h * 0.67), x0:x1] = WHITE
            im[y0 + int(h * 0.70):y0 + int(h * 0.80), x0:x1] = REDC
            if variant == "shaded":
                im[y0 + int(h * 0.14):y0 + int(h * 0.30), x0:x1] = TEAL
            cx, cy = x0 + int(w * 0.5), y0 + int(h * 0.28)
            yy, xx = np.ogrid[y0:y1, x0:x1]
            disc = (xx - cx) ** 2 + (yy - cy) ** 2 < (h * 0.2) ** 2
            im[y0:y1, x0:x1][disc[:, :]] = WHITE
        elif nm == "hood":
            c = x0 + w // 2
            im[y0:y1, c - 40:c + 40] = WHITE
            im[y0:y1, c + 52:c + 92] = REDC
        elif nm in ("front bumper", "rear bumper"):
            im[y0 + h // 2:y0 + h // 2 + 40, x0:x1] = WHITE
        elif nm == "spoiler":
            im[y0:y1, x0:x1] = REDC
        elif nm == "roof":
            im[y0:y0 + 60, x0:x1] = WHITE
    Image.fromarray(im).save(p)
    return p


# ------------------------------------------------------------------ saving
def save_img(fid, im, fmt="webp"):
    out = L.OUT
    out.mkdir(parents=True, exist_ok=True)
    if fmt == "png":
        p = out / f"{fid}.png"
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        if buf.tell() > MAX_KB * 1024:
            q = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            buf = io.BytesIO()
            q.save(buf, "PNG", optimize=True)
        data = buf.getvalue()
    else:
        p = out / f"{fid}.webp"
        data = b""
        for q in (92, 88, 84, 80, 74, 68, 60, 50):
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=q, method=6)
            data = buf.getvalue()
            if len(data) <= MAX_KB * 1024:
                break
    tmp = str(p) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, p)
    return p, len(data)


def done(fid, im, title, caption, sources, alt, fmt="webp", meta=None):
    p, n = save_img(fid, im, fmt)
    ent = figure(fid, title, caption, sources, alt, kind="render", file=f"figures/{p.name}", meta=meta)
    L.write_manifest("r")
    print(f"{fid}: {im.size[0]}x{im.size[1]} {n // 1024} KB -> {p.name}", flush=True)
    return ent


def header(d, w, title, sub=None):
    S.text(d, (16, 12), title, 22, S.HI, True)
    if sub:
        S.text(d, (16, 42), sub, 14, S.DIM)


# ------------------------------------------------------------------ r01
@fig("r01_spec_sweep_RxG")
def r01():
    ms = [0, 36, 73, 109, 146, 182, 219, 255]
    rs = [0, 36, 73, 109, 146, 182, 219, 255]
    cell, lx, ty = 104, 86, 116
    w, h = lx + 8 * cell + 12, ty + 8 * cell + 70
    im, d = S.canvas(w, h)
    header(d, w, "Metal across, roughness down", "Clearcoat 16 (max gloss), red paint. Each ball is lit by the same soft studio.")
    S.text(d, (lx + 4 * cell, ty - 44), "R metallic  (paint  ->  metal)", 14, (255, 93, 108), True, "ma")
    changed = 0
    for j, r in enumerate(rs):
        y = ty + j * cell
        S.text(d, (lx - 10, y + cell // 2), str(r), 13, S.DIM, True, "rm")
        for i, m in enumerate(ms):
            spec, col = swatch_spec(m, r, 16)
            if spec[1] != r:
                changed += 1
            im.paste(S.shade_sphere(col, spec[0], spec[1], spec[2], size=cell - 6), (lx + i * cell + 3, y + 3))
            if j == 0:
                S.text(d, (lx + i * cell + cell // 2, ty - 8), str(m), 13, S.DIM, True, "ms")
            if spec[1] != r:
                S.text(d, (lx + i * cell + cell - 8, y + cell - 12), f"{spec[1]}", 12, S.ORANGE, True, "rs")
    side = Image.new("RGB", (8 * cell, 24), S.BG)
    S.text(ImageDraw.Draw(side), (4 * cell, 12), "G roughness  (mirror  ->  matte)", 14, (67, 214, 138), True, "mm")
    im.paste(side.rotate(90, expand=True), (8, ty))
    S.text(d, (16, ty + 8 * cell + 14), "Every ball has clearcoat 16, the glossiest coat.", 13, S.DIM)
    S.text(d, (16, ty + 8 * cell + 38), "Orange number = the engine lifted roughness to 15, the iron-rule floor for anything below metal 240.", 13, S.DIM)
    return done("r01_spec_sweep_RxG", im, "Metal x roughness sweep (real engine values)",
                "Metal runs left to right and roughness top to bottom, all with the glossiest clearcoat. Top-right is a rough bare metal, "
                "bottom-left is wet paint, and the top row of the metal side is the mirror. These are lit balls drawn from the numbers the engine produced. "
                "Orange numbers show where the engine raised roughness to its floor of 15.",
                [src("shokker_engine_v2.py", r"def _apply_zone_spec_material_override"), src("shokker_engine_v2.py", r"def preview_render"),
                 src("shokker_engine_v2.py", r"ROUGHNESS_FLOOR_NONMIRROR = 15"), src("scripts/ai_atlas/enc_figs_shade.py", r"def shade_sphere")],
                "An 8 by 8 grid of lit balls. Metal increases left to right and roughness increases top to bottom. Top-right balls are mirror-like metal, bottom-left are glossy red paint, bottom-right are flat matte.",
                meta={"cells_lifted_to_floor": changed, "shading": "illustration, one studio light; not iRacing's lighting"})


# ------------------------------------------------------------------ r02
@fig("r02_clearcoat_sweep")
def r02():
    bs = [16, 32, 64, 128, 255]
    cell = 160
    w, h = 16 + len(bs) * cell, 290
    im, d = S.canvas(w, h)
    header(d, w, "Clearcoat: 16 is glossiest, 255 is dullest", "Same semi-rough metallic red (metal 150, roughness 110). Only the blue number changes.")
    for i, b in enumerate(bs):
        spec, col = swatch_spec(150, 110, b, base="gloss")
        x = 8 + i * cell
        im.paste(S.shade_sphere(col, spec[0], spec[1], spec[2], size=cell - 10), (x + 5, 76))
        S.text(d, (x + cell // 2, 76 + cell - 4), f"B = {spec[2]}", 15, S.HI, True, "ma")
        lab = {16: "max gloss", 255: "dull"}.get(spec[2], "")
        if b != spec[2]:
            lab = f"asked {b}"
        S.text(d, (x + cell // 2, 76 + cell + 18), lab, 13, S.DIM, False, "ma")
    return done("r02_clearcoat_sweep", im, "Clearcoat sweep",
                "One semi-rough metallic red paint with only the clearcoat changed. 16 is the glossiest coat; the number gets duller as it goes up to 255. "
                "The balls use the values the engine returned for each setting.",
                [src("shokker_engine_v2.py", r"B = Clearcoat"), src("shokker_engine_v2.py", r"def preview_render"), src("shokker_engine_v2.py", r"def _enforce_iron_rules")],
                "Five lit red metallic balls from clearcoat 16 to 255. The 16 ball has the sharpest glossy reflection on top; the 255 ball has none.",
                meta={"shading": "illustration"})


# ------------------------------------------------------------------ r03
@fig("r03_roughness_sweep")
def r03():
    gs = [2, 15, 40, 80, 120, 170, 220, 255]
    cell, lx, ty = 104, 110, 96
    w, h = lx + len(gs) * cell + 8, ty + 2 * cell + 64
    im, d = S.canvas(w, h)
    header(d, w, "Roughness: mirror to matte", "Same red paint, clearcoat 16. Top row is metal, bottom row is plain paint.")
    for j, (lab, m) in enumerate((("metal 255", 255), ("paint 0", 0))):
        y = ty + j * cell
        S.text(d, (lx - 12, y + cell // 2), lab, 14, S.HI, True, "rm")
        for i, g in enumerate(gs):
            spec, col = swatch_spec(m, g, 16)
            im.paste(S.shade_sphere(col, spec[0], spec[1], spec[2], size=cell - 6), (lx + i * cell + 3, y + 3))
            if j == 0:
                S.text(d, (lx + i * cell + cell // 2, ty - 8), f"G {spec[1]}", 14, (67, 214, 138), True, "ms")
    S.text(d, (16, ty + 2 * cell + 16), "Paint cannot go below G 15 (iron rule), so the bottom-left ball is lifted from 2 to 15.", 13, S.DIM)
    return done("r03_roughness_sweep", im, "Roughness sweep",
                "Roughness from a mirror (left) to flat matte (right), on bare metal (top) and on plain paint (bottom). "
                "Plain paint cannot go below roughness 15.",
                [src("engine/SPEC_MAP_REFERENCE.md", r"Green \(R\)"), src("shokker_engine_v2.py", r"ROUGHNESS_FLOOR_NONMIRROR = 15"), src("shokker_engine_v2.py", r"def preview_render")],
                "Two rows of eight lit balls. The top row is metal and the bottom row is paint; roughness grows left to right, so the reflections go from sharp to a soft glow.",
                meta={"shading": "illustration"})


# ------------------------------------------------------------------ shared tile layout
def ac_(i):
    return src("scripts/ai_atlas/app_controls.json", r'"id": "%s"' % i)


def ui_(i):
    return src("scripts/ai_atlas/ui_map.json", r'"id": "%s"' % i.replace(".", r"\."))


def field_paint():
    p = WORK / "field2048.png"
    if not p.exists():
        Image.fromarray(np.full((2048, 2048, 3), (60, 80, 120), np.uint8)).save(p)
    return p


def tiles_row(title, sub, tiles, labels, tile=300, rows=None, note=None):
    """tiles laid in a row (or `rows` rows); labels under each."""
    n = len(tiles)
    cols = n if rows is None else (n + rows - 1) // rows
    rws = 1 if rows is None else rows
    w = 16 + cols * (tile + 12)
    h = 80 + rws * (tile + 40) + (30 if note else 0)
    im, d = S.canvas(w, h)
    header(d, w, title, sub)
    for i, (t, lab) in enumerate(zip(tiles, labels)):
        x = 16 + (i % cols) * (tile + 12)
        y = 76 + (i // cols) * (tile + 40)
        im.paste(t.resize((tile, tile), Image.LANCZOS), (x, y))
        S.text(d, (x + tile // 2, y + tile + 8), lab, 15, S.HI, True, "ma")
    if note:
        S.text(d, (16, h - 26), note, 13, S.DIM)
    return im


CHEV = dict(pattern="chevron", pattern_opacity=1.0, pattern_spec_mult=1.0, base_color_mode="source")


# ------------------------------------------------------------------ r04
@fig("r04_foundation_before_after")
def r04():
    sheet = make_sheet()
    names = [("Chrome", "f_chrome"), ("Satin chrome", "f_satin_chrome"), ("Soft matte", "f_soft_matte")]
    outs = []
    for nm, fid in names:
        pr, sp, _ = render(sheet, [zone(fid, base_color_mode="source", base_color_explicit=True)], scale=0.25)
        outs.append((nm, fid, pr, sp))
    base = outs[0][2].astype(int)
    diff = max(int(np.abs(o[2].astype(int) - base).max()) for o in outs)
    tile = 260
    w, h = 16 + 3 * (tile + 14), 76 + tile + 30 + tile + 90
    im, d = S.canvas(w, h)
    header(d, w, "Foundation finishes: same paint, different shine", "Top: the paint the engine returned. Bottom: a ball wearing that same paint, lit with each finish's spec.")
    p_ = car_boxes()["left side"]["box"]
    for i, (nm, fid, pr, sp) in enumerate(outs):
        x = 16 + i * (tile + 14)
        im.paste(Image.fromarray(pr).resize((tile, tile), Image.LANCZOS), (x, 76))
        S.text(d, (x + tile // 2, 76 + tile + 6), nm, 16, S.HI, True, "ma")
        hh, ww = pr.shape[:2]
        x0, y0 = int(p_[0] / 100 * ww), int(p_[1] / 100 * hh)
        side = int((p_[3] - p_[1]) / 100 * hh)
        tex = pr[y0:y0 + side, x0 + int(0.08 * ww):x0 + int(0.08 * ww) + side]
        c = sp[y0 + 8:y0 + side - 8, x0 + 40:x0 + 120].reshape(-1, 4)
        spec = [int(np.median(c[:, k])) for k in range(4)]
        y = 76 + tile + 36
        im.paste(S.shade_sphere(None, spec[0], spec[1], spec[2], size=tile - 20, texture=tex), (x + 10, y))
        S.text(d, (x + tile // 2, y + tile - 12), f"M {spec[0]}   G {spec[1]}   B {spec[2]}", 14, S.DIM, True, "ma")
    return done("r04_foundation_before_after", im, "Foundation: paint identical, only the shine changes",
                "Three Foundation finishes (chrome, satin chrome, soft matte) with the colour set to source paint. The paint the engine returns is the same in all three; "
                "only the metal, roughness and clearcoat numbers change, shown on lit balls wearing that paint.",
                [src("mcp/server/index.js", r"FOUNDATION finish"), src("shokker_engine_v2.py", r"def preview_render"), reg("f_chrome")[3], reg("f_satin_chrome")[3], reg("f_soft_matte")[3]],
                "Three copies of the same blue striped car sheet above three balls wearing the same stripes, one chrome, one satin chrome and one matte.",
                meta={"max_pixel_difference_between_the_three_paints": diff, "shading": "illustration"})


# ------------------------------------------------------------------ r06 r07 r08 r09
def pat_tiles(vals, key, extra=None):
    out = []
    for v in vals:
        kw = dict(CHEV)
        kw.update(extra or {})
        kw[key] = v
        pr, sp, _ = render(field_paint(), [zone("gloss", **kw)], scale=0.25)
        out.append(Image.fromarray(pr))
    return out


@fig("r06_pattern_scale")
def r06():
    t = pat_tiles([0.25, 1.0, 4.0], "scale")
    im = tiles_row("Pattern scale: 0.25x, 1x, 4x", "The same pattern over a whole 2048 sheet. Smaller number = finer, more repeats.", t, ["Scale 0.25x", "Scale 1x", "Scale 4x"], 330)
    return done("r06_pattern_scale", im, "Pattern scale",
                "One pattern at three scales over the whole car sheet. Scale 0.25 repeats it four times as fine; scale 4 zooms right in. Smaller is finer.",
                [ac_("zone_pattern_scale"), src("shokker_engine_v2.py", r"def preview_render")],
                "Three square tiles of a zig-zag chevron pattern: very fine at 0.25x, medium at 1x and large at 4x.")


@fig("r07_pattern_rotation")
def r07():
    t = pat_tiles([0, 45, 90], "rotation", {"scale": 2.0})
    im = tiles_row("Pattern rotation: 0, 45, 90 degrees", "Same pattern and scale. Only the Rotate slider changes.", t, ["0 degrees", "45 degrees", "90 degrees"], 330)
    return done("r07_pattern_rotation", im, "Pattern rotation",
                "Rotate turns a directional pattern: 0, 45 and 90 degrees on the same chevron.",
                [ac_("zone_pattern_rotation"), src("shokker_engine_v2.py", r"def preview_render")],
                "Three square tiles of the chevron pattern turned 0, 45 and 90 degrees.")


@fig("r08_pattern_opacity_strength")
def r08():
    t1 = pat_tiles([1.0, 0.5, 0.2], "pattern_opacity", {"scale": 2.0})
    t2 = []
    for v in (0.0, 0.5, 1.0):
        kw = dict(CHEV)
        kw.update(scale=2.0, pattern_spec_opacity=v)
        pr, sp, _ = render(field_paint(), [zone("gloss", **kw)], scale=0.25)
        g = sp[..., 1]
        t2.append(Image.fromarray(np.stack([g, g, g], -1)))
    labels = ["Opacity 100%", "Opacity 50%", "Opacity 20%", "Spec amount 0%", "Spec amount 50%", "Spec amount 100%"]
    im = tiles_row("Pattern opacity fades the paint, spec amount adds the shine", "Top: the paint. Bottom: the roughness (G) channel for the same pattern.", t1 + t2, labels, 300, rows=2)
    return done("r08_pattern_opacity_strength", im, "Pattern opacity vs spec amount",
                "Opacity fades how much of the pattern you see. Spec amount decides how much of the pattern's own shine (shown here as the roughness channel) is added; it starts at 0.",
                [ac_("zone_pattern_opacity"), ui_("zone.pattern_spec_amount"), src("shokker_engine_v2.py", r"def preview_render")],
                "Top row: the chevron fading from full to faint. Bottom row: the roughness channel, flat at 0 spec amount and showing the pattern at 50 and 100 percent.")


@fig("r09_base_scale")
def r09():
    t, labels = [], []
    for base in ("carbon_base", "efx_chunky_flake"):
        for v in (0.25, 1.0, 4.0):
            pr, sp, _ = render(field_paint(), [zone(base, base_color_mode="finish", base_scale=v)], scale=0.5)
            g = sp[:256, :256, 0].astype(float)
            g = ((g - g.min()) / (np.ptp(g) + 1e-6) * 255).astype(np.uint8)
            t.append(Image.fromarray(np.stack([g, g, g], -1)))
            labels.append(f"{'Carbon' if base == 'carbon_base' else 'Chunky flake'}  {v}x")
    im = tiles_row("Base scale: 0.25x, 1x, 4x", "The texture of a base lives in its metal (R) channel. Top-left quarter of the sheet, contrast stretched.", t, labels, 300, rows=2)
    return done("r09_base_scale", im, "Base scale (what crushed means)",
                "Base Scale shrinks or grows the texture inside a base finish. Shown here as the metal channel of carbon and chunky flake at 0.25x, 1x and 4x. Lower numbers are finer and busier.",
                [ac_("zone_base_scale"), src("shokker_engine_v2.py", r"def _compose_finish_base_scale_for_zone")],
                "Two rows of three black and white tiles. Carbon weave and chunky flake at 0.25x are very fine; at 1x medium; at 4x the weave is large and the flake chunky.")


# ------------------------------------------------------------------ r10 r11 r12 r13
@fig("r10_colour_modes")
def r10():
    sheet = make_sheet()
    stops = [{"pos": 0, "color": [1, 0.2, 0.4]}, {"pos": 0.5, "color": [1, 0.67, 0]}, {"pos": 1, "color": [0.2, 1, 0.4]}]
    modes = [("Finish's own colour", dict(base_color_mode="finish")),
             ("Source paint", dict(base_color_mode="source")),
             ("Solid colour", dict(base_color_mode="solid", base_color="#c8281e")),
             ("From special", dict(base_color_mode="special", base_color_source="candy_gold")),
             ("Custom gradient", dict(base_color_mode="gradient", gradient_stops=stops, gradient_direction="horizontal"))]
    t = []
    for nm, kw in modes:
        pr, sp, _ = render(sheet, [zone("candy_emerald", **kw)], scale=0.25)
        t.append(Image.fromarray(pr))
    im = tiles_row("One finish, five colour modes", "Finish: candy emerald. Only the BASE COLOR dropdown changes.", t, [m[0] for m in modes], 230)
    return done("r10_colour_modes", im, "Zone colour modes",
                "The same finish on the same livery under the five BASE COLOR choices: its own colour, your source paint, one solid colour, colours borrowed from another finish, and a custom gradient.",
                [ac_("zone_base_colour_mode"), ui_("zone.base_color_mode"), src("shokker_engine_v2.py", r"def preview_render")],
                "Five car sheets in a row, each coloured a different way: green candy, the original blue livery, solid red, gold, and a red-orange-green gradient.")


@fig("r11_colour_tolerance")
def r11():
    sheet = make_sheet("sheet_shaded", "shaded")
    t = []
    for tol in (6, 30, 100):
        pr, sp, _ = render(sheet, [zone("gloss", color=pick((31, 59, 143), tol), base_color="#ff00c8")], scale=0.25)
        t.append(Image.fromarray(pr))
    im = tiles_row("Colour tolerance: 6, 30, 100", "Zone picks the mid blue; pink shows every pixel it grabbed.", t, ["Tolerance 6", "Tolerance 30", "Tolerance 100"], 330)
    return done("r11_colour_tolerance", im, "Colour tolerance",
                "A zone that picks one blue and paints what it selects pink. Tolerance 6 grabs only that exact shade, 30 is a normal reach and 100 pulls in much more.",
                [ui_("zone.tolerance"), ui_("zone.pick_color_from_car")],
                "Three car sheets where the pink area grows with tolerance: small patches at 6, most of the blue at 30, nearly everything blue at 100.")


@fig("r12_zone_priority_demo")
def r12():
    sheet = make_sheet()
    a = zone("gloss", color=pick((31, 59, 143), 30), name="A", base_color="#1fa84a")
    b = zone("gloss", color=pick((31, 59, 143), 30), name="B", base_color="#f5761a")
    rest = zone("gloss", color="remaining", name="Everything Else", base_color_mode="source")
    t = []
    for order in ([a, b, rest], [b, a, rest]):
        pr, sp, _ = render(sheet, order, scale=0.25)
        t.append(Image.fromarray(pr))
    im = tiles_row("Both zones want the blue. The top one wins.", "Zone A is green, zone B is orange. Both pick the same blue.", t, ["A above B: green", "B above A: orange"], 400)
    return done("r12_zone_priority_demo", im, "Zone priority demo",
                "Two zones both pick the body blue. Whichever sits higher in the list gets it; swap them and the car changes colour.",
                [ui_("zone.order"), src("mcp/server/index.js", r"LOWER index = higher priority")],
                "Two car sheets. With zone A above B the body is green; with B above A it is orange.")


@fig("r13_spec_channel_views")
def r13():
    sheet = make_sheet()
    zs = [zone("f_chrome", color=pick((232, 232, 238), 25), name="white = chrome", base_color_mode="source"),
          zone("f_soft_matte", color=pick((214, 45, 32), 25), name="red = soft matte", base_color_mode="source"),
          zone("f_metallic", color="remaining", name="Everything Else", base_color_mode="source")]
    pr, sp, _ = render(sheet, zs, scale=0.25)
    tiles = [Image.fromarray(pr)]
    for k in range(4):
        g = sp[..., k]
        tiles.append(Image.fromarray(np.stack([g, g, g], -1)))
    im = tiles_row("One livery: paint and its four spec channels", "White stripes = chrome, red = soft matte, blue body = metallic. Brighter = bigger number.", tiles,
                   ["Paint", "R metal", "G rough", "B coat", "A mask"], 240)
    return done("r13_spec_channel_views", im, "Paint and spec channel views",
                "A livery with chrome white stripes, matte red stripes and a metallic blue body, shown as the paint and then the four spec channels. Bright means a bigger number in that channel.",
                [ui_("pro.preview.r_metal"), ui_("pro.preview.g_rough"), ui_("pro.preview.b_coat"), ui_("pro.preview.a_mask"), src("shokker_engine_v2.py", r"def preview_render")],
                "Five tiles: the paint, then greyscale R metal, G rough, B coat and A mask views. Chrome stripes are bright in metal and dark in rough; matte stripes the reverse.")


@fig("r05_shelf_tiles")
def r05():
    items = json.load(open(ROOT / "_atlas_cards" / "items.json", encoding="utf8"))
    rate = {}
    for ln in open(ROOT / "_atlas_cards" / "ratings.jsonl", encoding="utf8"):
        ln = ln.strip()
        if ln:
            r = json.loads(ln)
            rate[r["k"]] = r
    shelves = {}
    for it in items:
        for s in it.get("shelves", []):
            shelves.setdefault(s, []).append(it)

    def thumb(it):
        kind, _, i = it["k"].partition("::")
        for p in (ROOT / "thumbnails" / kind / f"{i}.png", ROOT / "_atlas_cards" / "thumbs" / f"{kind}__{i}.png"):
            if p.exists():
                return p
        return None

    def clean(s):
        s = re.sub(r"[^\x20-\x7e]", "", s).strip()
        return s.title().replace(" Of ", " of ") if s.isupper() else s

    used, picks = set(), {}
    for sh in sorted(shelves, key=lambda s: len(shelves[s])):
        cand = []
        for it in shelves[sh]:
            if it["k"] in used or thumb(it) is None:
                continue
            r = rate.get(it["k"], {})
            cand.append((-r.get("hero", 0), r.get("risk", 9), -r.get("appeal", 0), it["k"], it))
        if cand:
            cand.sort(key=lambda c: c[:4])
            it = cand[0][4]
            used.add(it["k"])
            picks[sh] = it
    order = sorted(picks, key=lambda s: clean(s).lower())
    cols, tile, gap = 8, 112, 12
    cw, ch = tile + gap, tile + 40
    rows = (len(order) + cols - 1) // cols
    W, H = 16 + cols * cw, 70 + rows * ch + 6
    im, d = S.canvas(W, H)
    header(d, W, "One look from each of the %d shelves" % len(order), "Each tile is the shelf's best example. The name under it is the shelf.")
    meta = {"tiles": []}
    for n, sh in enumerate(order):
        x, y = 16 + (n % cols) * cw, 70 + (n // cols) * ch
        t = Image.open(thumb(picks[sh])).convert("RGB").resize((tile, tile), Image.LANCZOS)
        im.paste(t, (x, y))
        name = clean(sh)
        words, lines, cur = name.split(), [], ""
        for w in words:
            if S.font(13, True).getlength((cur + " " + w).strip()) <= tile:
                cur = (cur + " " + w).strip()
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        for j, ln in enumerate(lines[:2]):
            S.text(d, (x, y + tile + 4 + 16 * j), ln, 13, S.TEXT, True)
        meta["tiles"].append({"shelf": name, "finish": picks[sh]["k"], "name": picks[sh]["n"]})
    return done("r05_shelf_tiles", im, "One look from every shelf",
                "A contact sheet with one real finish picked from each shelf in the finish picker, so you can see how different the shelves look.",
                [src("_atlas_cards/items.json", r'"shelves"'), src("_atlas_cards/ratings.jsonl", r'"hero"')],
                "A grid of small finish swatches, eight per row, each labelled with the name of its shelf.", meta=meta)


@fig("r14_sculpt_before_after")
def r14():
    man = json.load(open(ROOT / "thumbnails" / "spec_sculpt_presets" / "_manifest.json", encoding="utf8"))
    byid = {t["id"]: t for t in man["thumbs"]}
    ids = ["mirror_chrome", "satin_weave", "candy_poison", "chaos_flake", "arctic_chameleon", "neon_outline"]
    tiles = [Image.new("RGB", (256, 256), (136, 136, 136))]
    labels = ["Before: flat grey paint"]
    for i in ids:
        t = byid[i]
        tiles.append(Image.open(ROOT / "thumbnails" / t["file"]).convert("RGB"))
        labels.append(t["label"])
    im = tiles_row("Spec Sculpt presets: one grey panel, six looks", "Left: flat neutral grey paint. The rest: the app's own preview of one preset on that grey.",
                   tiles, labels, 220, rows=2, note="Presets shown: chrome and metal, carbon and matte, candy, flake, holo and shift, glow. The tool has 175 in all.")
    meta = {"presets": [{"id": i, "label": byid[i]["label"], "category": byid[i]["category"], "finish_id": byid[i]["finish_id"]} for i in ids]}
    return done("r14_sculpt_before_after", im, "Spec Sculpt presets on neutral grey",
                "The first tile is flat neutral grey paint. The next six are the app's own previews of Spec Sculpt presets on that grey. Presets change the shine and metal, and some bring their own pattern and colour effects.",
                [src("thumbnails/spec_sculpt_presets/_manifest.json", r'"reference_paint"'), src("thumbnails/spec_sculpt_presets/_manifest.json", r'"count"')] +
                [src("engine/spec_sculpt/presets.py", r'_p\("%s"' % i) for i in ids],
                "Seven swatches: a flat grey one labelled Before, then six presets (Mirror Chrome, Satin Weave, Candy Poison, Chaos Flake, Arctic Chameleon, Neon Outline) on neutral grey paint.", meta=meta)


# ------------------------------------------------------------------ main (keep last; add figures ABOVE this marker)
def main(argv):
    force = "--force" in argv
    want = [a for a in argv if not a.startswith("--")]
    ids = [i for i in sorted(FIGS) if (not want or any(i.startswith(w) for w in want))]
    for fid in ids:
        exist = list(L.OUT.glob(fid + ".*"))
        if exist and not force and not want:
            print(f"{fid}: exists, skipped")
            continue
        t = time.time()
        try:
            FIGS[fid]()
        except Exception as exc:  # one failure must not lose the others
            import traceback
            print(f"{fid}: FAILED {type(exc).__name__}: {str(exc)[:200]}")
            traceback.print_exc(limit=3, file=sys.stdout)
        print(f"  ({time.time() - t:.1f}s)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])

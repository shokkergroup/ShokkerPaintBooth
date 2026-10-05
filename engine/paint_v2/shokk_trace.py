"""
Shokk Trace — zone auto-segmenter (production module).

SPB-AUTOPAINT-001 · 2026-05-29 · autonomous dev loop.
Owner mandate: turn photos/renders of a car into an editable iRacing template.
This module is step 1 of the pipeline — auto-segment a blank iRacing template
into named-able zone regions. Each paintable UV panel is an island on the flat
background; connected-components finds them so a human only NAMES them (the
template's baked-in "Zone N" text is the naming source of truth when present).

THREE-COPY FILE. Canonical = root engine/paint_v2/shokk_trace.py. Mirror to
electron-app/server/engine/paint_v2/ and .../pyserver/_internal/engine/paint_v2/.
Algorithm mirrors the dev reference _shokk_trace/zone_segmenter.py — keep in sync.

Pure numpy + scipy + PIL (no new deps; matches SPB's CV-only stack).
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, asdict
from typing import Optional, Union

import numpy as np
from PIL import Image
from scipy import ndimage

ImageLike = Union[str, bytes, Image.Image]


# --------------------------------------------------------------------------- #
# Background detection
# --------------------------------------------------------------------------- #
def _modal_border_color(rgb: np.ndarray, strip: int = 8) -> np.ndarray:
    h, w, _ = rgb.shape
    strip = max(1, min(strip, h // 4, w // 4))
    border = np.concatenate([
        rgb[:strip, :, :].reshape(-1, 3), rgb[-strip:, :, :].reshape(-1, 3),
        rgb[:, :strip, :].reshape(-1, 3), rgb[:, -strip:, :].reshape(-1, 3),
    ], axis=0)
    q = (border // 8 * 8).astype(np.int32)
    keys = q[:, 0] * 1_000_000 + q[:, 1] * 1000 + q[:, 2]
    vals, counts = np.unique(keys, return_counts=True)
    top = vals[int(np.argmax(counts))]
    return np.array([top // 1_000_000, (top // 1000) % 1000, top % 1000], dtype=np.float32)


def _foreground_mask(img, bg_tolerance, close_radius, min_area_frac):
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba)
    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3]
    bg = _modal_border_color(rgb)
    # Two background regimes (real iRacing templates vary):
    #  - transparent-bg (common in .tga paintable templates): alpha IS the signal,
    #    so the colour test would wrongly drop dark panels — use alpha alone.
    #  - opaque flat-field bg (the owner's labeled guide): use colour distance.
    if (alpha < 16).mean() > 0.02:           # meaningful transparency present
        fg = alpha >= 16
    else:
        dist = np.sqrt(((rgb - bg[None, None, :]) ** 2).sum(axis=2))
        fg = dist > bg_tolerance
    if close_radius > 0:
        st = ndimage.generate_binary_structure(2, 2)
        fg = ndimage.binary_closing(fg, structure=st, iterations=close_radius)
    fg = ndimage.binary_fill_holes(fg)
    min_area = int(min_area_frac * fg.size)
    if min_area > 0:
        fg = _remove_small(fg, min_area)
    return fg, bg


def _remove_small(mask, min_area):
    st = ndimage.generate_binary_structure(2, 2)
    lbl, n = ndimage.label(mask, structure=st)
    if n == 0:
        return mask
    sizes = ndimage.sum(np.ones_like(lbl), lbl, index=np.arange(1, n + 1))
    keep = np.where(sizes >= min_area)[0] + 1
    return np.isin(lbl, keep)


# --------------------------------------------------------------------------- #
@dataclass
class Region:
    id: int
    name: Optional[str]
    suggested_name: str
    bbox: list
    area_px: int
    centroid: list
    centroid_norm: list
    mirror_of: Optional[int]
    is_major: bool          # large enough to be a real paintable zone (vs fixture)
    mask_png_b64: str


def _mask_to_b64(mask_crop: np.ndarray) -> str:
    im = Image.fromarray((mask_crop * 255).astype(np.uint8), mode="L")
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _suggest_name(cx, cy, w, h, area_rank):
    ar = w / max(h, 1e-6)
    if area_rank < 4 and ar > 1.6:
        return "Left Side" if cy < 0.5 else "Right Side"
    if cy < 0.2 and cx < 0.45:
        return "Front Bumper"
    if cy < 0.2 and cx > 0.5:
        return "Rear Bumper"
    if cx > 0.6 and 0.25 < cy < 0.8:
        return "Hood"
    if 0.3 < cx < 0.6 and 0.4 < cy < 0.75 and ar < 1.5:
        return "Roof"
    if cx < 0.35 and 0.4 < cy < 0.8:
        return "Rear Decklid"
    if ar > 4 or h / max(w, 1e-6) > 4:
        return "Spoiler / Strip"
    return "Unassigned"


def _suggest_mirrors(regions, w, h):
    # check BOTH vertical-axis and horizontal-axis reflection (iRacing stacks L/R)
    for i, a in enumerate(regions):
        if a.mirror_of is not None:
            continue
        best, bs = None, 1e9
        for b in regions[i + 1:]:
            if b.mirror_of is not None:
                continue
            ar = abs(a.area_px - b.area_px) / max(a.area_px, b.area_px)
            if ar > 0.25:
                continue
            vx = abs((a.centroid[0] - w/2) + (b.centroid[0] - w/2)) / w
            vy = abs(a.centroid[1] - b.centroid[1]) / h
            hy = abs((a.centroid[1] - h/2) + (b.centroid[1] - h/2)) / h
            hx = abs(a.centroid[0] - b.centroid[0]) / w
            ok = (vx < 0.09 and vy < 0.09) or (hy < 0.09 and hx < 0.09)
            s = min(vx + vy, hx + hy)
            if ok and s < bs:
                bs, best = s, b
        if best is not None:
            a.mirror_of = best.id
            best.mirror_of = a.id


def _load(img: ImageLike) -> Image.Image:
    if isinstance(img, Image.Image):
        return img
    if isinstance(img, (bytes, bytearray)):
        return Image.open(io.BytesIO(img))
    return Image.open(img)


def segment_template(
    img: ImageLike,
    bg_tolerance: float = 34.0,
    close_radius: int = 2,
    min_area_frac: float = 0.0006,
    major_area_frac: float = 0.01,
    max_dim: int = 2048,
    source_name: str = "template",
) -> dict:
    """Segment a blank iRacing template into named-able zone regions."""
    im = _load(img)
    if max(im.size) > max_dim:
        scale = max_dim / max(im.size)
        im = im.resize((round(im.size[0] * scale), round(im.size[1] * scale)), Image.NEAREST)
    W, H = im.size

    fg, bg = _foreground_mask(im, bg_tolerance, close_radius, min_area_frac)
    st = ndimage.generate_binary_structure(2, 2)
    lbl, n = ndimage.label(fg, structure=st)

    raw = []
    for idx in range(1, n + 1):
        ys, xs = np.where(lbl == idx)
        if xs.size == 0:
            continue
        raw.append((idx, int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()),
                    int(xs.size), float(xs.mean()), float(ys.mean())))

    order = sorted(range(len(raw)), key=lambda k: -raw[k][5])
    rank_of = {raw[k][0]: r for r, k in enumerate(order)}
    major_min = major_area_frac * W * H

    regions: list[Region] = []
    for new_id, (idx, x0, y0, x1, y1, area, cx, cy) in enumerate(raw, start=1):
        bw, bh = (x1 - x0 + 1), (y1 - y0 + 1)
        crop = (lbl[y0:y1 + 1, x0:x1 + 1] == idx)
        regions.append(Region(
            id=new_id, name=None,
            suggested_name=_suggest_name(cx / W, cy / H, bw, bh, rank_of[idx]),
            bbox=[x0, y0, bw, bh], area_px=area,
            centroid=[round(cx, 1), round(cy, 1)],
            centroid_norm=[round(cx / W, 4), round(cy / H, 4)],
            mirror_of=None, is_major=area >= major_min,
            mask_png_b64=_mask_to_b64(crop),
        ))
    _suggest_mirrors(regions, W, H)

    return {
        "schema": "shokk-trace.zonemap/0",
        "source": source_name,
        "width": W, "height": H,
        "background_rgb": [int(c) for c in bg],
        "region_count": len(regions),
        "major_count": sum(1 for r in regions if r.is_major),
        "params": {"bg_tolerance": bg_tolerance, "close_radius": close_radius,
                   "min_area_frac": min_area_frac, "major_area_frac": major_area_frac},
        "regions": [asdict(r) for r in regions],
    }


# --------------------------------------------------------------------------- #
# Separator-based partition for REAL connected iRacing templates (iter 23-25).
# WHY: real iRacing paintable areas are ONE connected blue mass, NOT separate
# islands — plain connected-components merges every panel into a single blob
# (the Chevy Truck came out as one 82.7% region). The owner's correction:
# "with the wireframe you should SEE where the separators are." Right — the
# official "Zones and Gridlines" asset draws the zone boundaries as explicit
# GREEN LINES (the white mesh is just the UV triangle grid). So:
#   1. blue paintable mask (seal the white mesh, keep the brown panel gaps open)
#   2. detect the GREEN separator lines and CUT the blue along them
#   3. connected-components of the cut blue = TRUE panel cells (a cell can never
#      cross a drawn separator -> no bleed across panels)
#   4. name each cell by the seed (label position) falling inside it; hybrid:
#      1 seed -> whole cell; >1 seed (under-separated) -> geodesic sub-partition;
#      0 seeds -> region adjacency (longest shared border)
# Emits the SAME shokk-trace.zonemap/0 dict as segment_template, so RLE / fill /
# send-to-Paint-Booth all work unchanged. Seeds come from the caller (PSD label
# layers, OCR of the labeled guide, or a per-car reference map) as
# [(name, norm_x, norm_y), ...]. Owner verdict iter-24: bleed complaints resolved,
# 11 balanced zones each on its panel. composite movement n/a (separation stage).
# --------------------------------------------------------------------------- #
def _blue_paint_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[:, :, 0].astype(int), rgb[:, :, 1].astype(int), rgb[:, :, 2].astype(int)
    blue = (b - np.maximum(r, g) > 20) & (b > 90)
    white = (r > 175) & (g > 175) & (b > 175)        # UV mesh + label text live ON panels
    paint = blue | white
    paint = ndimage.binary_closing(paint, iterations=1)   # seal 1px AA only, don't bridge gaps
    filled = ndimage.binary_fill_holes(paint)
    holes = filled & ~paint
    hl, hn = ndimage.label(holes)
    if hn:
        hs = ndimage.sum(np.ones_like(hl), hl, np.arange(1, hn + 1))
        paint |= np.isin(hl, np.where(hs < 0.0008 * paint.size)[0] + 1)  # fill only small holes
    return paint


def _green_separator_mask(rgb: np.ndarray, dilate: int = 3) -> np.ndarray:
    r, g, b = rgb[:, :, 0].astype(int), rgb[:, :, 1].astype(int), rgb[:, :, 2].astype(int)
    green = (g > 140) & (g - r > 55) & (g - b > 45)
    return ndimage.binary_dilation(green, iterations=dilate)   # bridge dashes, widen to cut


def _geodesic_labels(mask: np.ndarray, seed_meta, W: int, H: int, small: int = 672) -> np.ndarray:
    """Assign each masked pixel to the seed nearest THROUGH the mask (geodesic),
    via multi-source BFS at reduced resolution then upscaled. Connectivity-aware:
    a seed can't claim a panel reachable only the long way around, so thin necks
    between panels become natural boundaries. seed_meta = [(i, name, x, y), ...]."""
    import collections
    sc = small / max(W, H)
    sw, sh = max(1, int(W * sc)), max(1, int(H * sc))
    sm = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize((sw, sh), Image.NEAREST)) > 127
    lab = np.zeros((sh, sw), np.int32)
    dq = collections.deque()
    sys_, sxs_ = np.where(sm)
    for i, name, x, y in seed_meta:
        sx = min(sw - 1, max(0, int(x * sw / W)))
        sy = min(sh - 1, max(0, int(y * sh / H)))
        if not sm[sy, sx] and sxs_.size:
            j = np.argmin((sxs_ - sx) ** 2 + (sys_ - sy) ** 2)
            sx, sy = int(sxs_[j]), int(sys_[j])
        if 0 <= sy < sh and 0 <= sx < sw and lab[sy, sx] == 0:
            lab[sy, sx] = i
            dq.append((sy, sx))
    NB = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    while dq:
        y, x = dq.popleft()
        c = lab[y, x]
        for dy, dx in NB:
            ny2, nx2 = y + dy, x + dx
            if 0 <= ny2 < sh and 0 <= nx2 < sw and sm[ny2, nx2] and lab[ny2, nx2] == 0:
                lab[ny2, nx2] = c
                dq.append((ny2, nx2))
    big = np.asarray(Image.fromarray(lab.astype(np.uint8)).resize((W, H), Image.NEAREST)).astype(np.int32)
    return np.where(mask, big, 0)


def segment_template_separators(
    grid_img: ImageLike,
    seeds,
    min_cell_frac: float = 0.0008,
    green_dilate: int = 3,
    max_dim: int = 2048,
    source_name: str = "template",
) -> dict:
    """Partition a REAL connected iRacing template by its drawn green separators.

    grid_img : the "Zones and Gridlines" asset (zone boundaries drawn as green).
    seeds    : [(name, norm_x, norm_y), ...] — one named seed per panel (PSD label
               layers / OCR / per-car reference map). Multiple seeds may share a
               name (e.g. the two spoiler strips) -> they merge into one zone.
    Returns the standard shokk-trace.zonemap/0 dict (one region per named zone)."""
    from collections import defaultdict
    im = _load(grid_img).convert("RGB")
    if max(im.size) > max_dim:
        scale = max_dim / max(im.size)
        im = im.resize((round(im.size[0] * scale), round(im.size[1] * scale)), Image.NEAREST)
    W, H = im.size
    rgb = np.asarray(im)
    blue = _blue_paint_mask(rgb)
    sep = _green_separator_mask(rgb, dilate=green_dilate)
    cells_mask = blue & ~sep                                  # cut blue along green lines

    st = ndimage.generate_binary_structure(2, 2)
    lbl, n = ndimage.label(cells_mask, structure=st)
    sizes = ndimage.sum(np.ones_like(lbl), lbl, np.arange(1, n + 1)) if n else np.array([])
    min_cell = min_cell_frac * W * H
    valid = {cid for cid in range(1, n + 1) if sizes[cid - 1] >= min_cell}

    # group seeds by the cell they fall in (look nearby if a label lands on a line)
    seeds_in_cell = defaultdict(list)
    for name, nx, ny in seeds:
        x, y = min(W - 1, int(nx * W)), min(H - 1, int(ny * H))
        cid = lbl[y, x]
        if cid == 0:
            patch = lbl[max(0, y - 12):y + 12, max(0, x - 12):x + 12]
            nz = patch[patch > 0]
            if nz.size:
                cid = int(np.bincount(nz).argmax())
        if cid in valid:
            seeds_in_cell[cid].append((name, x, y))

    # region-adjacency graph (shared-border length) for orphan cells
    _, inds = ndimage.distance_transform_edt(lbl == 0, return_indices=True)
    filled = lbl[inds[0], inds[1]]
    border: dict = {}
    for ax in (0, 1):
        a = filled
        s = np.roll(filled, 1, axis=ax)
        m = (a != s) & (a > 0) & (s > 0)
        aa, ss = a[m], s[m]
        key = np.minimum(aa, ss).astype(np.int64) * 100000 + np.maximum(aa, ss)
        u, c = np.unique(key, return_counts=True)
        for k, cnt in zip(u.tolist(), c.tolist()):
            border[k] = border.get(k, 0) + cnt
    adj = {cid: {} for cid in valid}
    for k, cnt in border.items():
        a, b = k // 100000, k % 100000
        if a in valid and b in valid:
            adj[a][b] = cnt
            adj[b][a] = cnt

    # per-pixel zone map: 1 seed -> whole cell; >1 -> geodesic sub-partition;
    # 0 seeds -> region adjacency (longest shared border), then nearest-seed fallback
    zone_px = np.zeros((H, W), np.int32)
    name_idx: dict = {}
    idx_name: dict = {}

    def zid(nm):
        if nm not in name_idx:
            i = len(name_idx) + 1
            name_idx[nm] = i
            idx_name[i] = nm
        return name_idx[nm]

    cell_zone: dict = {}
    multi_cells: set = set()
    for cid in valid:
        sset = seeds_in_cell.get(cid, [])
        names = list(dict.fromkeys(s[0] for s in sset))
        if len(names) == 1:
            cell_zone[cid] = names[0]
        elif len(names) > 1:
            cellmask = (lbl == cid)
            sm = [(i + 1, nm, x, y) for i, (nm, x, y) in enumerate(sset)]
            wl = _geodesic_labels(cellmask, sm, W, H)
            for i, (nm, x, y) in enumerate(sset, start=1):
                zone_px[wl == i] = zid(nm)
            multi_cells.add(cid)

    zone_of = dict(cell_zone)
    changed = True
    while changed:
        changed = False
        for cid in valid:
            if cid in zone_of or cid in multi_cells:
                continue
            cand = [(blen, zone_of[o]) for o, blen in adj[cid].items() if o in zone_of]
            if cand:
                zone_of[cid] = max(cand)[1]
                changed = True
    coms = ndimage.center_of_mass(np.ones_like(lbl), lbl, np.arange(1, n + 1)) if n else []
    seed_pts = [(nm, nx * W, ny * H) for nm, nx, ny in seeds]
    for cid in valid:
        if cid in multi_cells or cid in zone_of:
            continue
        cy, cx = coms[cid - 1]
        zone_of[cid] = min(seed_pts, key=lambda s: (s[1] - cx) ** 2 + (s[2] - cy) ** 2)[0]
    for cid in valid:
        if cid not in multi_cells:
            zone_px[lbl == cid] = zid(zone_of[cid])

    # one Region per named zone (whole-zone mask), compatible with all consumers
    regions: list[Region] = []
    new_id = 0
    for i, nm in idx_name.items():
        zmask = (zone_px == i)
        if not zmask.any():
            continue
        ys, xs = np.where(zmask)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        crop = zmask[y0:y1 + 1, x0:x1 + 1]
        cx, cy = float(xs.mean()), float(ys.mean())
        new_id += 1
        regions.append(Region(
            id=new_id, name=nm, suggested_name=nm,
            bbox=[x0, y0, bw, bh], area_px=int(zmask.sum()),
            centroid=[round(cx, 1), round(cy, 1)],
            centroid_norm=[round(cx / W, 4), round(cy / H, 4)],
            mirror_of=None, is_major=True,
            mask_png_b64=_mask_to_b64(crop),
        ))
    regions.sort(key=lambda r: -r.area_px)
    for new_id, r in enumerate(regions, start=1):
        r.id = new_id
    # Fit check: how many seeds actually land on the paintable area. A low score
    # means the seed reference doesn't match this template (e.g. the wrong car was
    # picked) — surfaced so the user gets a clear warning instead of garbage zones.
    ys_b, xs_b = np.where(blue)
    near2 = (0.012 * max(W, H)) ** 2
    in_paint = 0
    for nm, nx, ny in seeds:
        sx, sy = min(W - 1, int(nx * W)), min(H - 1, int(ny * H))
        ok = bool(blue[sy, sx])
        if not ok and xs_b.size:
            ok = bool(((xs_b - sx) ** 2 + (ys_b - sy) ** 2).min() <= near2)
        in_paint += 1 if ok else 0
    n_seeds = len(seeds)
    score = in_paint / max(n_seeds, 1)
    verdict = "good" if score >= 0.85 else ("weak" if score >= 0.5 else "mismatch")
    off = n_seeds - in_paint
    warnings = []
    if verdict == "mismatch":
        warnings.append(f"{off}/{n_seeds} seeds landed off the paintable area — is this the right car/template?")
    elif verdict == "weak":
        warnings.append(f"{off} of {n_seeds} seeds landed off the paint — minor template mismatch or a label in a gap.")
    # Separator-detection diagnostic: catches the failure the seed-fit MISSES — right
    # car, but the green lines weren't detected (e.g. a different green shade on a new
    # car), so the blue never got cut and zones silently merged. The seeds still land
    # on paint (fit "good") yet there's really one giant blob.
    paint_px = int(blue.sum())
    largest = max((r.area_px for r in regions), default=0)
    largest_frac = (largest / paint_px) if paint_px else 0.0
    cells_found = len(valid)
    if largest_frac > 0.5 or cells_found < 3:
        warnings.append(
            f"one zone covers {int(round(largest_frac * 100))}% of the paint and only "
            f"{cells_found} cell(s) were cut — the green separators may not be detected "
            f"(is this the 'Zones and Gridlines' image? try a different green threshold).")
        if verdict == "good":
            verdict = "weak"
    fit = {"seeds_total": n_seeds, "seeds_in_paint": in_paint, "score": round(score, 3),
           "verdict": verdict, "zones_emitted": len(regions),
           "green_frac": round(float(sep.mean()), 4), "cells_found": cells_found,
           "largest_zone_frac": round(largest_frac, 3), "warnings": warnings}

    bg = _modal_border_color(rgb.astype(np.float32))
    return {
        "schema": "shokk-trace.zonemap/0",
        "source": source_name,
        "method": "separators",
        "width": W, "height": H,
        "background_rgb": [int(c) for c in bg],
        "region_count": len(regions),
        "major_count": len(regions),
        "params": {"min_cell_frac": min_cell_frac, "green_dilate": green_dilate},
        "fit": fit,
        "regions": [asdict(r) for r in regions],
    }


# --------------------------------------------------------------------------- #
_PALETTE = np.array([
    [239, 192, 64], [98, 215, 255], [255, 110, 110], [140, 220, 140],
    [200, 140, 255], [255, 170, 80], [120, 200, 255], [255, 130, 200],
    [180, 255, 120], [255, 220, 120], [120, 255, 220], [220, 120, 255],
], dtype=np.uint8)


def render_overlay(img: ImageLike, zone_map: dict, major_only: bool = False) -> Image.Image:
    """Colourised debug overlay (PIL Image)."""
    from PIL import ImageDraw, ImageFont
    base = _load(img).convert("RGB")
    if base.size != (zone_map["width"], zone_map["height"]):
        base = base.resize((zone_map["width"], zone_map["height"]), Image.NEAREST)
    canvas = (np.asarray(base).astype(np.float32) * 0.35).astype(np.uint8).copy()
    for r in zone_map["regions"]:
        if major_only and not r.get("is_major", True):
            continue
        x, y, w, h = r["bbox"]
        mask = np.asarray(Image.open(io.BytesIO(base64.b64decode(r["mask_png_b64"])))) > 127
        color = _PALETTE[(r["id"] - 1) % len(_PALETTE)]
        px = canvas[y:y + h, x:x + w]
        px[mask] = (px[mask] * 0.45 + color * 0.55).astype(np.uint8)
        canvas[y:y + h, x:x + w] = px
    out = Image.fromarray(canvas)
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("arial.ttf", max(14, zone_map["width"] // 90))
    except Exception:
        font = ImageFont.load_default()
    for r in zone_map["regions"]:
        if major_only and not r.get("is_major", True):
            continue
        x, y, w, h = r["bbox"]
        label = f'#{r["id"]} {r.get("name") or r["suggested_name"]}'
        draw.rectangle([x, y, x + w, y + h], outline=(255, 255, 255), width=2)
        draw.text((x + 5, y + 5), label, fill=(0, 0, 0), font=font)
        draw.text((x + 4, y + 4), label, fill=(255, 255, 255), font=font)
    return out


def overlay_data_url(img: ImageLike, zone_map: dict, major_only: bool = False) -> str:
    out = render_overlay(img, zone_map, major_only=major_only)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# --------------------------------------------------------------------------- #
# Design-read (Problem A) + zone-fill compositor.
# Promoted from _shokk_trace/design_read.py + compositor.py (iter 3-4). Reads a
# design source already in UV space (flat design or existing painted template)
# through the zone map -> per-zone design spec, then fills a starting paint+spec.
# A vision model will later fill the SAME designspec schema for the photos path.
# --------------------------------------------------------------------------- #
DEFAULT_SPEC = (0, 200, 40)  # neutral satin for un-zoned canvas


def _hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _decode_mask(b64: str) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(b64)))) > 127


def _dominant_and_palette(pixels: np.ndarray, k: int = 3):
    q = (pixels // 16 * 16).astype(np.int32)
    keys = q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]
    vals, counts = np.unique(keys, return_counts=True)
    order = np.argsort(-counts)
    palette = []
    for idx in order[:k]:
        sel = keys == vals[idx]
        palette.append((_hex(pixels[sel].mean(axis=0)), float(counts[idx]) / len(pixels)))
    return (palette[0][0] if palette else "#000000"), palette


def _guess_finish(mean_luma, mean_sat, texture):
    L, S, T = mean_luma, mean_sat, texture
    if L > 0.82 and S < 0.18 and T < 0.10:
        return "chrome", [255, 4, 16]
    if L < 0.16 and S < 0.22:
        return ("matte_black", [10, 210, 40]) if T < 0.10 else ("satin_black", [40, 150, 60])
    if T > 0.16:
        return "metallic_flake", [200, 95, 24]
    if S > 0.45:
        return "gloss_color", [40, 70, 16]
    if L > 0.6 and S < 0.25:
        return "pearl_white", [120, 90, 18]
    return "gloss", [60, 100, 16]


def _zone_crop_image(arr: np.ndarray, region: dict, mask: np.ndarray) -> Image.Image:
    """The zone's design pixels as an alpha-masked RGBA crop — what a vision
    provider is handed so it sees only that one panel."""
    x, y, w, h = region["bbox"]
    sub = arr[y:y + h, x:x + w]
    a = np.zeros(sub.shape[:2], np.uint8)
    mh, mw = min(mask.shape[0], sub.shape[0]), min(mask.shape[1], sub.shape[1])
    a[:mh, :mw] = (mask[:mh, :mw] * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([sub, a]), "RGBA")


_VISION_OVERRIDE_KEYS = ("base_color", "finish_guess", "spec_MRCC", "palette", "label")


def read_design(zone_map: dict, design_img: ImageLike, design_name: str = "design",
                vision_provider=None) -> dict:
    """Zone map + design source (UV space) -> per-zone design spec dict.

    vision_provider: optional callable — the drop-in point for a real vision model.
      Signature: vision_provider(zone_crop_rgba_PIL, zone_name, deterministic_dict)
      -> dict | None. Return any of {base_color '#hex', finish_guess str, spec_MRCC
      [M,R,CC], palette [{hex,frac}], label str} to OVERRIDE the deterministic read
      for that zone (a zone's `source` then flips to "vision"). Best-effort — any
      exception is swallowed so the deterministic read always stands. A vision model
      wires here: send the crop, ask "what colour / finish / logo is this panel?",
      parse the answer into the override dict. The SAME shokk-trace.designspec/0
      schema is produced either way. None (default) = pure deterministic, unchanged.
    """
    img = _load(design_img).convert("RGB")
    W, H = zone_map["width"], zone_map["height"]
    if img.size != (W, H):
        img = img.resize((W, H), Image.BILINEAR)
    arr = np.asarray(img)
    zones = []
    for r in zone_map["regions"]:
        if not r.get("is_major", True):
            continue
        x, y, w, h = r["bbox"]
        mask = _decode_mask(r["mask_png_b64"])
        crop = arr[y:y + h, x:x + w]
        if mask.shape != crop.shape[:2]:
            mh, mw = min(mask.shape[0], crop.shape[0]), min(mask.shape[1], crop.shape[1])
            mask, crop = mask[:mh, :mw], crop[:mh, :mw]
        px = crop[mask]
        if px.size == 0:
            continue
        dom, palette = _dominant_and_palette(px)
        rgbf = px.astype(np.float32) / 255.0
        luma = 0.2126 * rgbf[:, 0] + 0.7152 * rgbf[:, 1] + 0.0722 * rgbf[:, 2]
        mx, mn = rgbf.max(axis=1), rgbf.min(axis=1)
        sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
        texture = float(luma.std())
        finish, spec = _guess_finish(float(luma.mean()), float(sat.mean()), texture)
        zdict = {
            "id": r["id"], "name": r.get("name") or r.get("suggested_name"),
            "base_color": dom,
            "palette": [{"hex": c, "frac": round(f, 3)} for c, f in palette],
            "finish_guess": finish, "spec_MRCC": spec,
            "mean_luma": round(float(luma.mean()), 3), "mean_sat": round(float(sat.mean()), 3),
            "texture_energy": round(texture, 3), "px_sampled": int(px.shape[0]),
            "source": "deterministic",
        }
        if vision_provider is not None:
            try:
                ov = vision_provider(_zone_crop_image(arr, r, mask), zdict["name"], dict(zdict))
                if isinstance(ov, dict):
                    applied = False
                    for k in _VISION_OVERRIDE_KEYS:
                        if ov.get(k) is not None:
                            zdict[k] = ov[k]
                            applied = True
                    if applied:
                        zdict["source"] = "vision"
            except Exception:
                pass   # vision is best-effort; never break the deterministic read
        zones.append(zdict)
    return {
        "schema": "shokk-trace.designspec/0", "design_source": design_name,
        "based_on_zonemap": zone_map.get("source", "zonemap"),
        "width": W, "height": H, "zone_count": len(zones), "zones": zones,
    }


def composite(zone_map: dict, design_spec: dict):
    """zonemap (masks) + designspec (colour/finish) -> (paint RGBA, spec RGBA)."""
    W, H = zone_map["width"], zone_map["height"]
    region_by_id = {r["id"]: r for r in zone_map["regions"]}
    paint = np.zeros((H, W, 4), dtype=np.uint8)
    spec = np.zeros((H, W, 4), dtype=np.uint8)
    spec[:, :, 0:3] = DEFAULT_SPEC
    spec[:, :, 3] = 255
    for z in design_spec["zones"]:
        reg = region_by_id.get(z["id"])
        if reg is None:
            continue
        x, y, w, h = reg["bbox"]
        mask = _decode_mask(reg["mask_png_b64"])
        rgb = _hex_to_rgb(z["base_color"])
        m, r, cc = (z.get("spec_MRCC") or list(DEFAULT_SPEC))[:3]
        pc = paint[y:y + h, x:x + w]
        pc[mask, 0], pc[mask, 1], pc[mask, 2], pc[mask, 3] = rgb[0], rgb[1], rgb[2], 255
        paint[y:y + h, x:x + w] = pc
        sc = spec[y:y + h, x:x + w]
        sc[mask, 0], sc[mask, 1], sc[mask, 2], sc[mask, 3] = m, r, cc, 255
        spec[y:y + h, x:x + w] = sc
    return Image.fromarray(paint, "RGBA"), Image.fromarray(spec, "RGBA")


def region_masks_rle(zone_map: dict, named_only: bool = False, major_only: bool = True) -> dict:
    """Export zones as SPB-native RLE region masks: {name: {width,height,runs}}.

    runs = [[value, count], ...] row-major over a full WxH canvas (value 0..255).
    Byte-for-byte the format Paint Booth's decode_region_mask() consumes
    (paint-booth-3-canvas.js), so a Shokk Trace result opens directly as editable
    zones. Islands sharing a zone name are merged into one mask."""
    W, H = zone_map["width"], zone_map["height"]
    merged: dict = {}
    for r in zone_map["regions"]:
        if major_only and not r.get("is_major", True):
            continue
        has_name = bool(r.get("name") or r.get("suggested_name"))
        if named_only and not has_name:
            continue
        name = r.get("name") or r.get("suggested_name") or f"Zone {r['id']}"
        full = merged.get(name)
        if full is None:
            full = np.zeros((H, W), dtype=np.uint8)
            merged[name] = full
        x, y, w, h = r["bbox"]
        m = _decode_mask(r["mask_png_b64"])
        full[y:y + h, x:x + w][m] = 255
    out = {}
    for name, full in merged.items():
        flat = full.ravel()
        idx = np.flatnonzero(np.diff(flat.astype(np.int16))) + 1
        starts = np.concatenate(([0], idx))
        ends = np.concatenate((idx, [flat.size]))
        runs = [[int(flat[s]), int(e - s)] for s, e in zip(starts, ends)]
        out[name] = {"width": int(W), "height": int(H), "runs": runs}
    return out


def extract_decals(zone_map: dict, design_img: ImageLike,
                   color_thresh: float = 60.0, min_decal_frac: float = 0.00015,
                   include_minor: bool = True) -> list[dict]:
    """Extract a decal library from a design (the infographic's 'extracted decals').

    Two sources:
      (a) WITHIN each major zone: pixels that deviate from the zone's dominant
          base colour (logos, numbers, text painted on the panel), grouped into
          connected blobs and cropped as alpha-masked PNGs.
      (b) MINOR islands (sit on the background — contingency sponsor blocks etc.).
    Returns a manifest: [{id, source_zone, kind, bbox, centroid_norm, area_px,
    png_data_url}]. Deterministic; a vision pass can later label each decal.
    """
    img = _load(design_img).convert("RGB")
    W, H = zone_map["width"], zone_map["height"]
    if img.size != (W, H):
        img = img.resize((W, H), Image.BILINEAR)
    arr = np.asarray(img)
    st8 = ndimage.generate_binary_structure(2, 2)
    min_area = max(48, int(min_decal_frac * W * H))
    decals = []
    did = 0

    def _emit(gx, gy, blob_mask, source, kind):
        nonlocal did
        ys, xs = np.where(blob_mask)
        if xs.size < min_area:
            return
        bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        cw, ch = bx1 - bx0 + 1, by1 - by0 + 1
        sub = arr[gy + by0:gy + by0 + ch, gx + bx0:gx + bx0 + cw]
        a = (blob_mask[by0:by1 + 1, bx0:bx1 + 1] * 255).astype(np.uint8)
        rgba = np.dstack([sub, a])
        buf = io.BytesIO()
        Image.fromarray(rgba, "RGBA").save(buf, format="PNG")
        did += 1
        decals.append({
            "id": did, "source_zone": source, "kind": kind,
            "bbox": [gx + bx0, gy + by0, cw, ch], "area_px": int(xs.size),
            "centroid_norm": [round((gx + bx0 + cw / 2) / W, 4),
                              round((gy + by0 + ch / 2) / H, 4)],
            "png_data_url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"),
        })

    for r in zone_map["regions"]:
        x, y, w, h = r["bbox"]
        zmask = _decode_mask(r["mask_png_b64"])
        crop = arr[y:y + h, x:x + w]
        if r.get("is_major", True):
            px = crop[zmask]
            if px.size == 0:
                continue
            dom = _hex_to_rgb(_dominant_and_palette(px)[0])
            dist = np.sqrt(((crop.astype(np.float32) - np.array(dom, np.float32)) ** 2).sum(axis=2))
            decal_px = (dist > color_thresh) & zmask
            lbl, n = ndimage.label(decal_px, structure=st8)
            for i in range(1, n + 1):
                _emit(x, y, lbl == i, r.get("name") or r.get("suggested_name"), "on_panel")
        elif include_minor:
            _emit(x, y, zmask, "background", "island")
    return decals


# --------------------------------------------------------------------------- #
# OCR naming (the PRECISION UNLOCK): read the official labeled template's baked-in
# "Zone N <Name>" text per region instead of guessing by position. Handles the
# upside-down panels (Left Side / Roof) by OCR-ing all four orientations.
# Optional — needs pytesseract + the tesseract binary; degrades to a no-op.
# --------------------------------------------------------------------------- #
# Most-specific keys first so "Spoiler (Inside)" wins over a bare "spoiler".
_CANON_LABELS = [
    ("Front Bumper", ("front bumper",)),
    ("Rear Bumper", ("rear bumper",)),
    ("Rear Decklid", ("rear decklid", "decklid", "deck lid")),
    ("Windshield Banner", ("windshield", "banner")),
    ("Left Side", ("left side",)),
    ("Right Side", ("right side",)),
    ("Spoiler (Inside)", ("facing inside",)),
    ("Spoiler (Outside)", ("facing outside", "spoiler")),
    ("Pitboard", ("pitboard", "pit board")),
    ("Number Panel", ("number panel",)),
    ("Hood", ("hood",)),
    ("Roof", ("roof",)),
]


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa
        import shutil
        import os as _os
        if shutil.which("tesseract"):
            return True
        for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                     r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
            if _os.path.isfile(cand):
                pytesseract.pytesseract.tesseract_cmd = cand
                return True
        return False
    except Exception:
        return False


def _ocr_prep_variants(crop):
    """Binarize (both polarities) + upscale — labels are white-on-colour text, so
    raw colour OCR fails on small panels. Returns PIL images ready for tesseract."""
    import cv2
    g = cv2.cvtColor(np.asarray(crop.convert("RGB")), cv2.COLOR_RGB2GRAY)
    h, w = g.shape
    s = max(1.0, 800.0 / max(h, w))
    if s > 1.0:
        g = cv2.resize(g, (int(w * s), int(h * s)), interpolation=cv2.INTER_CUBIC)
    _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return [Image.fromarray(otsu), Image.fromarray(255 - otsu)]


def _ocr_text_all_orientations(pil_img) -> str:
    import pytesseract
    out = []
    for variant in _ocr_prep_variants(pil_img):
        for angle in (0, 180, 90, 270):     # real templates have upside-down AND vertical labels
            im = variant.rotate(angle, expand=True) if angle else variant
            try:
                out.append(pytesseract.image_to_string(im, config="--psm 6"))
            except Exception:
                pass
    return " ".join(out).lower()


def name_zones_from_labels(zone_map: dict, template_img: ImageLike, major_only: bool = True) -> int:
    """Set zone names by OCR-ing the baked-in label text per region. Returns the
    number of zones confidently named. No-op (returns 0) if OCR is unavailable."""
    if not ocr_available():
        return 0
    base = _load(template_img).convert("RGB")
    W, H = zone_map["width"], zone_map["height"]
    if base.size != (W, H):
        base = base.resize((W, H), Image.NEAREST)
    arr = np.asarray(base)
    named = 0
    for r in zone_map["regions"]:
        if major_only and not r.get("is_major", True):
            continue
        x, y, w, h = r["bbox"]
        crop = Image.fromarray(arr[y:y + h, x:x + w])
        if max(crop.size) < 480:                      # upscale small crops for OCR
            s = 480 / max(crop.size)
            crop = crop.resize((max(1, int(crop.size[0] * s)), max(1, int(crop.size[1] * s))))
        import re
        txt = re.sub(r"\s+", " ", _ocr_text_all_orientations(crop))  # join words split across lines
        r["label_ocr"] = txt.strip()[:120]
        for canon, keys in _CANON_LABELS:
            if any(k in txt for k in keys):
                r["name"] = canon
                named += 1
                break
    return named


# --------------------------------------------------------------------------- #
# OCR seed authoring: turn a car's LABELED template guide into a per-car seed
# reference automatically (the "self-driving" path so Shokk Trace works on a car
# without hand-authoring from its PSD). Names each zone by its distinctive label
# word and drops a seed at the word's centre. Best-effort authoring aid — the
# precise paths remain PSD label layers / hand-tuning. iter 32.
# --------------------------------------------------------------------------- #
_DISTINCT_LABEL_WORD = {
    "front": "Front Bumper", "hood": "Hood", "roof": "Roof",
    "decklid": "Rear Decklid", "windshield": "Windshield Banner",
    "banner": "Windshield Banner", "pitboard": "Pitboard",
    "left": "Left Side", "right": "Right Side",
    "outside": "Spoiler (Outside)", "inside": "Spoiler (Inside)",
}
_ALL_ZONE_NAMES = ["Front Bumper", "Rear Bumper", "Hood", "Roof", "Rear Decklid",
                   "Windshield Banner", "Left Side", "Right Side",
                   "Spoiler (Outside)", "Spoiler (Inside)", "Pitboard"]


def _ocr_word_hits(img: Image.Image, min_conf: int):
    """OCR a labeled guide at 4 orientations -> [(alpha_word, nx, ny)] in ORIGINAL
    normalized coords. Vertical/upside-down labels are read by rotating; PIL rotates
    CCW so each detected box is mapped back to the original frame."""
    import pytesseract
    import re as _re
    W, H = img.size

    def invmap(angle, cx, cy):
        if angle == 180:
            return (W - 1 - cx), (H - 1 - cy)
        if angle == 90:
            return (W - 1 - cy), cx          # rotated dims (H, W)
        if angle == 270:
            return cy, (H - 1 - cx)
        return cx, cy

    hits = []
    for angle in (0, 90, 180, 270):
        im = img.rotate(angle, expand=True) if angle else img
        try:
            data = pytesseract.image_to_data(im, config="--psm 11",
                                             output_type=pytesseract.Output.DICT)
        except Exception:
            continue
        for i, txt in enumerate(data["text"]):
            w = _re.sub(r"[^a-z]", "", (txt or "").strip().lower())
            try:
                conf = int(float(data["conf"][i]))
            except (TypeError, ValueError):
                conf = -1
            if len(w) < 3 or conf < min_conf:
                continue
            cx = data["left"][i] + data["width"][i] / 2.0
            cy = data["top"][i] + data["height"][i] / 2.0
            ox, oy = invmap(angle, cx, cy)
            hits.append((w, ox / W, oy / H))
    return hits


def seeds_from_labels(labeled_img: ImageLike, min_conf: int = 40):
    """Author a per-car seed reference from a LABELED template guide via OCR.
    Returns (seeds, report): seeds = [(name, nx, ny), ...]; report =
    {available, found, missing, seed_count, note}. Degrades to ([], report) if OCR
    is unavailable. A new car can be seeded from just its labeled guide — top up
    any zone the OCR missed (e.g. a tiny Pitboard label) by hand."""
    if not ocr_available():
        return [], {"available": False, "found": [], "missing": list(_ALL_ZONE_NAMES),
                    "seed_count": 0, "note": "OCR (pytesseract + tesseract) not available"}
    img = _load(labeled_img).convert("RGB")
    hits = _ocr_word_hits(img, min_conf)
    raw, fronts, bumpers = [], [], []
    for w, nx, ny in hits:
        if w in _DISTINCT_LABEL_WORD:
            raw.append((_DISTINCT_LABEL_WORD[w], nx, ny))
            if w == "front":
                fronts.append((nx, ny))
        elif w == "bumper":
            bumpers.append((nx, ny))
    # Rear Bumper has no distinctive single word: a 'bumper' NOT near a 'front' is it.
    for bx, by in bumpers:
        if not any((bx - fx) ** 2 + (by - fy) ** 2 < 0.10 ** 2 for fx, fy in fronts):
            raw.append(("Rear Bumper", bx, by))
    # dedup per name: merge co-located hits (e.g. windshield+banner) but keep
    # genuinely separate instances apart (e.g. the two spoiler strips)
    seeds = []
    for name in dict.fromkeys(n for n, _, _ in raw):
        pts = [(nx, ny) for n, nx, ny in raw if n == name]
        clusters: list = []
        for (px, py) in pts:
            for c in clusters:
                if any((px - qx) ** 2 + (py - qy) ** 2 < 0.06 ** 2 for qx, qy in c):
                    c.append((px, py))
                    break
            else:
                clusters.append([(px, py)])
        for c in clusters:
            seeds.append((name, round(sum(p[0] for p in c) / len(c), 5),
                          round(sum(p[1] for p in c) / len(c), 5)))
    found = sorted(set(n for n, _, _ in seeds))
    missing = [n for n in _ALL_ZONE_NAMES if n not in found]
    note = f"OCR-authored {len(seeds)} seeds across {len(found)} zones"
    if missing:
        note += "; add manually: " + ", ".join(missing)
    return seeds, {"available": True, "found": found, "missing": missing,
                   "seed_count": len(seeds), "note": note}


def _png_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build_from_images(template_img: ImageLike, design_img: ImageLike,
                      names: dict | None = None, design_name: str = "design",
                      want_decals: bool = False, ocr_names: bool = False,
                      vision_provider=None, **seg_kwargs) -> dict:
    """Whole v1 chain: segment template -> (OCR/apply names) -> design-read ->
    composite. Returns design_spec + paint/spec/overlay data URLs + counts.
    When want_decals, also returns an extracted-decal library manifest. When
    ocr_names, names zones from the template's baked-in labels (overridden by an
    explicit names map if both are given)."""
    zm = segment_template(template_img, **seg_kwargs)
    if ocr_names:
        name_zones_from_labels(zm, template_img)
    if names:
        for r in zm["regions"]:
            nm = names.get(str(r["id"])) or names.get(r["id"])
            if nm:
                r["name"] = nm
    ds = read_design(zm, design_img, design_name=design_name, vision_provider=vision_provider)
    paint, spec = composite(zm, ds)
    out = {
        "design_spec": ds,
        "region_count": zm["region_count"], "major_count": zm.get("major_count"),
        "paint_data_url": _png_data_url(paint),
        "spec_data_url": _png_data_url(spec),
        "overlay_data_url": overlay_data_url(template_img, zm, major_only=True),
        "region_masks": region_masks_rle(zm),  # SPB-native RLE -> editable zones
    }
    if want_decals:
        out["decals"] = extract_decals(zm, design_img)
    return out


def build_from_separators(grid_img: ImageLike, design_img: ImageLike, seeds,
                          names: dict | None = None, design_name: str = "design",
                          want_decals: bool = False, vision_provider=None,
                          **sep_kwargs) -> dict:
    """Whole v1 chain for a REAL connected iRacing template: separator-partition
    the gridlines asset by `seeds` -> design-read -> composite. Returns the SAME
    bundle shape as build_from_images (design_spec + paint/spec/overlay data URLs
    + region_masks), so the tool/route handles the island path and the connected
    path identically. `seeds` = [(name, nx, ny), ...] — a per-car seed reference
    (authored once from PSD label layers / OCR / by hand; reused across siblings).
    `names` optionally overrides a zone's name (keyed by id or current name)."""
    zm = segment_template_separators(grid_img, seeds, **sep_kwargs)
    if names:
        for r in zm["regions"]:
            nm = (names.get(str(r["id"])) or names.get(r["id"])
                  or names.get(r.get("name")))
            if nm:
                r["name"] = nm
    ds = read_design(zm, design_img, design_name=design_name, vision_provider=vision_provider)
    paint, spec = composite(zm, ds)
    out = {
        "design_spec": ds, "method": "separators",
        "region_count": zm["region_count"], "major_count": zm.get("major_count"),
        "fit": zm.get("fit"),
        "paint_data_url": _png_data_url(paint),
        "spec_data_url": _png_data_url(spec),
        "overlay_data_url": overlay_data_url(grid_img, zm, major_only=True),
        "region_masks": region_masks_rle(zm),  # SPB-native RLE -> editable zones
    }
    if want_decals:
        out["decals"] = extract_decals(zm, design_img)
    return out


def _hue_hex(i: int, n: int) -> str:
    """Evenly-spaced distinct hue (hex) for zone i of n — so empty zones land in
    Paint Booth visually separated (the painter recolours each anyway)."""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb((i / max(n, 1)) % 1.0, 0.55, 0.92)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def zones_from_separators(grid_img: ImageLike, seeds, want_overlay: bool = True,
                          **sep_kwargs) -> dict:
    """Separator-partition a REAL template into editable zones WITHOUT a design —
    the "just give me my panels to paint in Paint Booth" path. Returns a Send-ready
    bundle (same handoff shape as build_from_separators, minus the paint/spec fill):
    each zone gets a distinct default colour + neutral satin spec so it lands
    visually separated, plus the SPB-native RLE region masks. Removes the hard
    design dependency for the common "auto-detect my zones" use case.
    seeds = [(name, nx, ny), ...] (a per-car seed reference)."""
    zm = segment_template_separators(grid_img, seeds, **sep_kwargs)
    rm = region_masks_rle(zm)
    n = len(zm["regions"])
    zones = [{"id": r["id"], "name": r["name"],
              "base_color": _hue_hex(i, n), "spec_MRCC": list(DEFAULT_SPEC)}
             for i, r in enumerate(zm["regions"])]
    out = {
        "method": "separators", "region_count": zm["region_count"],
        "fit": zm.get("fit"),
        "design_spec": {"schema": "shokk-trace.designspec/0",
                        "zone_count": len(zones), "zones": zones},
        "region_masks": rm,
    }
    if want_overlay:
        out["overlay_data_url"] = overlay_data_url(grid_img, zm, major_only=True)
    return out

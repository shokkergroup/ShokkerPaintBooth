# -*- coding: utf-8 -*-
"""IMAGE FORGE (2026-06-11) — owner-art-driven finishes.

Owner workflow: "I CREATE beautiful images and feed them to you... you make
dynamic and insane spec maps to match." Drop a square image into image_forge/
named `<finish_id>.jpg|png` and it becomes that finish:

  PAINT  = the image VERBATIM (small optimized 1024 JPG — no multi-GB packs,
           no procedural approximation losses; the owner's art IS the canvas)
  SPEC   = derived FROM the image itself, married by construction:
           * structure tensor -> the artwork's own stroke-flow orientation;
             gloss anisotropy follows the actual brushwork
           * luminance structure -> M traces the painting's lit motifs
           * fine-residual grain + signed flow polarity -> R (decorrelated)
           * HUE-BANDED IGNITION -> each color family in the art gets its OWN
             angle gate, so the painting's reds, golds and blues flash in
             SEQUENCE as the view sweeps — the art plays like an instrument
           * brightest-vein pins -> near-max Cc on the hottest strokes

Registered into MONOLITHIC_REGISTRY at boot (after the procedural packs, so a
forge image OVERRIDES the procedural finish of the same id). The picker/search
pick new ids up automatically via the 2026-06-11 registry sync; boot swatch
warm bakes their thumbnails. Verbatim-art doctrine: paint is never strength-
scaled or grained — the owner's pixels ship untouched.
"""
import os

import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _noise, _n01, _sstep, _gauss, _dirblur, _microtex, _seed_int,
    _m2, _pack,
)

FORGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "image_forge")

_IMG_CACHE = {}


def _load_forge_image(path):
    if path not in _IMG_CACHE:
        if len(_IMG_CACHE) > 8:
            _IMG_CACHE.pop(next(iter(_IMG_CACHE)))
        bgr = cv2.imread(path, cv2.IMREAD_COLOR)
        if bgr is None:
            raise RuntimeError("image_forge: unreadable image %s" % path)
        _IMG_CACHE[path] = np.ascontiguousarray(
            cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0)
    return _IMG_CACHE[path]


_FIELD_CACHE = {}


def _forge_fields(path, h, w):
    """Geometry fields mined from the artwork itself (cached per size)."""
    key = (path, h, w)
    if key in _FIELD_CACHE:
        return _FIELD_CACHE[key]
    if len(_FIELD_CACHE) > 6:
        _FIELD_CACHE.pop(next(iter(_FIELD_CACHE)))
    img = _load_forge_image(path)
    if img.shape[:2] != (h, w):
        interp = cv2.INTER_AREA if h < img.shape[0] else cv2.INTER_CUBIC
        img = cv2.resize(img, (w, h), interpolation=interp)
    g = img.mean(2)

    # PERF (owner 2026-06-11: "render times still need to be optimized"):
    # the structure tensor / hue analysis are smooth fields — derive them on a
    # <=1024 working copy and upsample (visually identical, ~4x faster at 2048).
    # grain + veins stay NATIVE res (cheap ops that need the fine detail).
    wk = min(1024, h)
    gs = g if wk == h else cv2.resize(g, (wk, wk), interpolation=cv2.INTER_AREA)
    sc = h / float(wk)
    gx = cv2.Sobel(gs, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gs, cv2.CV_32F, 0, 1, ksize=3)
    Jxx = _gauss(gx * gx, 5); Jyy = _gauss(gy * gy, 5); Jxy = _gauss(gx * gy, 5)
    orient = (0.5 * np.arctan2(2 * Jxy, (Jxx - Jyy) + 1e-9)).astype(np.float32)
    coher = _n01(np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / (Jxx + Jyy + 1e-6))
    edge = _n01(np.sqrt(gx * gx + gy * gy))
    if wk != h:
        orient = cv2.resize(orient, (w, h), interpolation=cv2.INTER_NEAREST)
        coher = cv2.resize(coher, (w, h), interpolation=cv2.INTER_LINEAR)
        edge = cv2.resize(edge, (w, h), interpolation=cv2.INTER_LINEAR)

    grain = _n01(np.abs(g - _gauss(g, 2.2)))
    p88 = float(np.percentile(gs, 88))
    veins = _sstep(p88, min(p88 + 0.10, 0.999), g)        # the hottest strokes

    # -- hue families (each color in the art = its own gate angle) ----------
    imgs = img if wk == h else cv2.resize(img, (wk, wk), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor((imgs * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    hue = hsv[..., 0].astype(np.float32) / 180.0
    sat = hsv[..., 1].astype(np.float32) / 255.0
    if wk != h:
        hue = cv2.resize(hue, (w, h), interpolation=cv2.INTER_NEAREST)
        sat = cv2.resize(sat, (w, h), interpolation=cv2.INTER_LINEAR)
    n_bands = 5
    hband = np.floor(hue * n_bands).astype(np.int32) % n_bands
    pol = np.sign(np.sin(orient * 2.0) + 1e-4)
    a_stable = (abs(hash(os.path.basename(path))) % 628) / 100.0
    brush = _dirblur(_noise(h, w, (abs(hash(path)) & 0x7FFFFFFF) ^ 0x6F, (1.6, 3.2)),
                     a_stable, max(3, int(0.012 * max(h, w))))
    out = dict(img=img, g=g.astype(np.float32), orient=orient, coher=coher,
               edge=edge, grain=grain, veins=veins, sat=sat,
               hband=hband, n_bands=n_bands, pol=pol.astype(np.float32),
               brush=brush.astype(np.float32),
               lit=_n01(_gauss(g, 1.2)))
    _FIELD_CACHE[key] = out
    return out


def forge_spec_channels(path, h, w, seed, gate_band=None):
    """The married spec: M/R/Cc (0..255 float) derived from the artwork."""
    F = _forge_fields(path, h, w)
    g, edge, grain = F["g"], F["edge"], F["grain"]
    coher, orient, veins, sat = F["coher"], F["orient"], F["veins"], F["sat"]
    rng = _rng(_seed_int(seed), 7)

    # which hue family is "lit" at this build (drifts with seed -> the art
    # flashes different color families on different cars/zones)
    if gate_band is None:
        gate_band = int(rng.integers(0, F["n_bands"]))
    gate = ((F["hband"] == gate_band) & (sat > 0.25)).astype(np.float32)
    gate = _gauss(gate, 1.5)

    # second flash angle: the NEXT hue family fires at half strength so the art
    # has a staggered two-beat reveal instead of one pop (owner: "more dynamic")
    gate2 = ((F["hband"] == (gate_band + 2) % F["n_bands"]) & (sat > 0.25)).astype(np.float32)
    gate2 = _gauss(gate2, 1.5)

    # M — gloss traces the painting's own lit structure + stroke anisotropy,
    # and the gated family goes near-MIRROR at its angle (Wovenlight: the motif
    # that is calm in paint detonates in spec)
    lit = F["lit"]
    M = 26 + 168 * lit + 50 * edge * coher + 42 * gate * veins
    # R — rough in the art's texture, brushed along the stroke flow, SIGNED by
    # flow polarity so raking light shimmers across the strokes
    pol, brush = F["pol"], F["brush"]
    # R primary = brushwork + grain + flow polarity (NOT luminance — M owns it;
    # sharing luma put |corr(M,R)| at 0.97, the classic decorrelation trap)
    R = (104 + 78 * (brush - 0.5) * pol * (0.5 + 0.5 * coher)
         + 70 * grain + 44 * (sat - 0.5) - 34 * coher - 26 * gate)
    # Cc — THE IGNITION: primary hue family DETONATES, second family echoes at
    # half strength, everything else stays calm so the flash reads violent
    Cc = (13 + 232 * veins * (0.28 + 0.72 * gate)
          + 142 * gate * _sstep(0.35, 0.7, g)
          + 88 * gate2 * (0.4 * _sstep(0.35, 0.7, g) + 0.6 * veins)
          + 10 * grain * (1 - gate) * (1 - gate2))
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 16, 255).astype(np.float32),
            np.clip(Cc, 0, 255).astype(np.float32))


def _mk_forge_finish(path):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        img = _load_forge_image(path)
        interp = cv2.INTER_AREA if fh < img.shape[0] else cv2.INTER_CUBIC
        eff = cv2.resize(img, (fw, fh), interpolation=interp)
        if fh > img.shape[0]:   # restore crispness lost to upscale, art untouched
            eff = np.clip(eff + (eff - cv2.GaussianBlur(eff, (0, 0), 1.2)) * 0.45, 0, 1)
        base = np.asarray(paint, np.float32)[:, :, :3]
        m = (_m2(mask, fh, fw) * float(pm))[..., None]
        return np.clip(base * (1.0 - m) + eff * m, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        # spec computes at the 1024 work grid and upsamples — the same contract
        # every wave2/spectrum procedural finish ships with (render-time rule)
        wh, ww = min(1024, fh), min(1024, fw)
        M, R, Cc = forge_spec_channels(path, wh, ww, seed)
        if (wh, ww) != (fh, fw):
            M = cv2.resize(M, (fw, fh), interpolation=cv2.INTER_LINEAR)
            R = cv2.resize(R, (fw, fh), interpolation=cv2.INTER_LINEAR)
            Cc = cv2.resize(Cc, (fw, fh), interpolation=cv2.INTER_LINEAR)
        return _pack(M, R, Cc, _m2(mask, fh, fw), float(sm))

    return spec_fn, paint_fn


_FORGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")

# new ids registered by the forge, grouped for the picker: {group_name: [ids]}
FORGE_GROUPS = {}


def _norm_group(name):
    """Normalize a group/folder name for matching: drop emoji/symbols/case."""
    import re as _re
    return _re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()


def _known_groups():
    """All picker group names from the live group maps (normalized -> real)."""
    out = {}
    try:
        import shokker_24k_expansion as _e24
        for key in ("bases", "patterns", "specials"):
            for gname in _e24.get_expansion_group_map().get(key, {}):
                out[_norm_group(gname)] = gname
    except Exception:
        pass
    try:
        import shokker_paradigm_expansion as _par
        for key in ("bases", "patterns", "specials"):
            for gname in _par.get_paradigm_group_map().get(key, {}):
                out[_norm_group(gname)] = gname
    except Exception:
        pass
    try:
        from engine.expansions import fusions as _fus
        for gname in _fus.get_fusion_group_map().get("fusions", {}):
            out[_norm_group(gname)] = gname
    except Exception:
        pass
    return out


def get_forge_group_map():
    """Picker group contributions for NEW forge ids ({group: [ids]}); merged
    into the /api/finish-data groups by finish_catalog_routes."""
    return dict(FORGE_GROUPS)


def _resolve_id(stem, mono_reg):
    """Forgiving filename -> finish id. "Stress Storm" matches
    spectrum_stress_storm: normalize, then exact match, then UNIQUE
    suffix match across the whole registry."""
    import re as _re
    key = _re.sub(r"[^a-z0-9]+", "_", str(stem).lower()).strip("_")
    if key in mono_reg:
        return key, "replace"
    cands = [fid for fid in mono_reg if str(fid).endswith("_" + key)]
    if len(cands) == 1:
        return cands[0], "replace"
    if len(cands) > 1:
        print("  [Image-Forge] WARNING: '%s' matches %d finishes (%s) - using "
              "NEW id '%s'; rename the file to the exact id to replace one."
              % (stem, len(cands), ", ".join(cands[:4]), key))
    return key, "new"


_INGEST_MAX_PX = 1024
_INGEST_MAX_KB = 900


def _ingest_file(dirpath, nm, mono_reg):
    """Normalize a dropped file in place: fuzzy-resolve the id, center-crop
    square, shrink to <=1024 JPG q90, rename to <id>.jpg; original moved to
    image_forge/_originals/. Already-clean files pass straight through."""
    stem, ext = os.path.splitext(nm)
    fid, _mode = _resolve_id(stem, mono_reg)
    src = os.path.join(dirpath, nm)
    dst = os.path.join(dirpath, fid + ".jpg")
    clean = (src == dst and ext.lower() == ".jpg"
             and os.path.getsize(src) <= _INGEST_MAX_KB * 1024)
    if clean:
        bgr = cv2.imread(src, cv2.IMREAD_COLOR)
        if bgr is not None and max(bgr.shape[:2]) <= _INGEST_MAX_PX + 90:
            return dst, fid
    bgr = cv2.imread(src, cv2.IMREAD_COLOR)
    if bgr is None:
        print("  [Image-Forge] WARNING: unreadable image skipped: %s" % nm)
        return None, None
    h, w = bgr.shape[:2]
    sz = min(h, w)
    bgr = bgr[(h - sz) // 2:(h - sz) // 2 + sz, (w - sz) // 2:(w - sz) // 2 + sz]
    if sz > _INGEST_MAX_PX:
        bgr = cv2.resize(bgr, (_INGEST_MAX_PX, _INGEST_MAX_PX), interpolation=cv2.INTER_AREA)
    arch = os.path.join(FORGE_DIR, "_originals")
    os.makedirs(arch, exist_ok=True)
    try:
        os.replace(src, os.path.join(arch, nm))
    except Exception:
        pass
    cv2.imwrite(dst, bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print("  [Image-Forge] ingested '%s' -> %s.jpg (%dx%d -> %dpx, original "
          "archived in _originals/)" % (nm, fid, w, h, min(sz, _INGEST_MAX_PX)))
    return dst, fid


def install_into_engine(mono_reg, base_reg=None):
    """Scan image_forge/ and register every image as a finish.

    Layout (owner workflow 2026-06-11):
      image_forge/<finish_id>.jpg            REPLACE the finish with that exact
                                             registry id (any category - the id
                                             decides, folder not needed).
      image_forge/<category>/<finish_id>.jpg same, AND a NEW id joins that
                                             picker category (folder matched to
                                             live group names, emoji/case
                                             insensitive: "spectrum shift" ->
                                             the real "Spectrum Shift" group).
      NEW id at root starting spectrum_      auto-joins Spectrum Shift.
      NEW id at root otherwise               registered but in NO picker lane
                                             (search-only); boot log warns -
                                             use a category subfolder.
    Runs AFTER the procedural packs -> owner art upgrades the same id."""
    if not os.path.isdir(FORGE_DIR):
        return "image-forge: no image_forge/ dir"
    FORGE_GROUPS.clear()
    groups_norm = _known_groups()
    n = 0
    new_ids = []
    orphans = []

    def _register(path, fid, folder_group):
        nonlocal n
        existed = fid in mono_reg
        mono_reg[fid] = _mk_forge_finish(path)
        n += 1
        if not existed:
            new_ids.append(fid)
            gname = None
            if folder_group is not None:
                gname = groups_norm.get(_norm_group(folder_group), folder_group)
            elif fid.startswith("spectrum_"):
                gname = groups_norm.get(_norm_group("spectrum shift"))
            if gname:
                FORGE_GROUPS.setdefault(gname, []).append(fid)
            else:
                orphans.append(fid)

    for nm in sorted(os.listdir(FORGE_DIR)):
        full = os.path.join(FORGE_DIR, nm)
        if os.path.isdir(full):
            if nm.startswith("_"):
                continue                      # _originals etc.
            for nm2 in sorted(os.listdir(full)):
                if os.path.splitext(nm2)[1].lower() not in _FORGE_EXTS:
                    continue
                try:
                    path2, fid2 = _ingest_file(full, nm2, mono_reg)
                    if path2:
                        _register(path2, fid2, nm)
                except Exception:
                    continue
            continue
        if os.path.splitext(nm)[1].lower() not in _FORGE_EXTS:
            continue
        try:
            path1, fid1 = _ingest_file(FORGE_DIR, nm, mono_reg)
            if path1:
                _register(path1, fid1, None)
        except Exception:
            continue
    if orphans:
        print("  [Image-Forge] WARNING: %d new id(s) have no category (unknown id "
              "at root) - put them in a category subfolder: %s"
              % (len(orphans), ", ".join(orphans[:6])))
    # keep the fusion-side registries in step for spectrum_ forge ids (the
    # Spectrum Shift picker group keys off FUSION_REGISTRY's spectrum_ prefix)
    forge_spectrum = [fid for fid in mono_reg
                      if fid.startswith("spectrum_") and fid in new_ids] +                      [fid for fid in mono_reg if fid.startswith("spectrum_")]
    forge_spectrum = sorted(set(forge_spectrum))
    try:
        import engine.expansions.fusions as _fus
        for fid in forge_spectrum:
            if fid in mono_reg:
                _fus.FUSION_REGISTRY.setdefault(fid, mono_reg[fid])
    except Exception:
        pass
    return ("image-forge: %d owner-art finishes registered (%d new, %d picker groups)"
            % (n, len(new_ids), len(FORGE_GROUPS)))

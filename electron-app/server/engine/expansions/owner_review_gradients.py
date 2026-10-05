"""Owner-review gradient monolithics for SPB-30.

The app exposes more gradient specials than the Python renderer previously
registered. This module wires the visible JS gradient catalog into real
monolithic renderers and gives the directional and vortex families distinct
fine-scale identities instead of flat two-color ramps.
"""

from __future__ import annotations

import colorsys
import hashlib
import re
from pathlib import Path
from collections import OrderedDict

import numpy as np

from engine.expansions.color_monolithics import COLOR_PALETTE


# --- Palette buckets for color/name -> mode steering -------------------------
# Named families let the mode picker read intent the digest can't (a "titanium"
# or "pewter" endpoint should brush, a "jade"/"emerald" endpoint should read as a
# gem, a "copper"/"bronze" endpoint should patina). Calc-based fallbacks below
# still classify any pair we didn't name explicitly.
_METAL_NAMES = {
    "silver", "gunmetal", "titanium", "pewter", "graphite", "slate", "steel",
    "chrome", "platinum", "nickel", "iron", "tungsten", "aluminum", "charcoal",
}
_JEWEL_NAMES = {
    "emerald", "jade", "amethyst", "ruby", "topaz", "sapphire", "opal",
    "garnet", "peridot", "citrine", "aquamarine", "turquoise",
}
_EARTH_NAMES = {
    "copper", "bronze", "sage", "tan", "chocolate", "champagne", "honey",
    "coffee", "olive", "khaki", "rust", "sienna", "umber", "caramel", "mocha",
    "wheat", "cocoa",
}

# Vortex sub-modes: the swirl now has 5 distinct geometries (was one 50-way tie).
_VORTEX_MODES = frozenset(
    {"vortex_spiral", "vortex_nebula", "vortex_shockwave", "vortex_lattice", "vortex_oil"}
)


def _palette_features(c1_name, c2_name, name):
    """Derive perceptual buckets from the two palette endpoints + finish name.

    Returns a dict of booleans/floats that the mode pickers branch on. Built on
    HSV of the raw palette tuples so it tracks the finish's actual colors, not a
    hash of its id.
    """
    c1 = COLOR_PALETTE[c1_name]
    c2 = COLOR_PALETTE[c2_name]
    h1, s1, v1 = colorsys.rgb_to_hsv(float(c1[0]), float(c1[1]), float(c1[2]))
    h2, s2, v2 = colorsys.rgb_to_hsv(float(c2[0]), float(c2[1]), float(c2[2]))
    sat = max(s1, s2)
    val = max(v1, v2)
    minv = min(v1, v2)
    contrast = abs(v1 - v2)
    # Hue of the more saturated endpoint drives warm/cool/green reads.
    deg = (h1 if s1 >= s2 else h2) * 360.0
    metal_name = c1_name in _METAL_NAMES or c2_name in _METAL_NAMES
    metal_calc = (s1 < 0.16 and 0.18 < v1 < 0.9) or (s2 < 0.16 and 0.18 < v2 < 0.9)
    lname = name.lower()
    jewel_name = (
        c1_name in _JEWEL_NAMES
        or c2_name in _JEWEL_NAMES
        or any(j in lname for j in ("emerald", "jade", "amethyst", "ruby", "topaz", "sapphire", "opal"))
    )
    return {
        "deg": deg,
        "sat": float(sat),
        "val": float(val),
        "minv": float(minv),
        "contrast": float(contrast),
        "metal": bool(metal_name or metal_calc),
        "jewel": bool(jewel_name),
        "earth": bool(c1_name in _EARTH_NAMES or c2_name in _EARTH_NAMES),
        "warm": bool(deg < 55 or deg >= 320),
        "cool": bool(150 <= deg <= 275),
        "green": bool(70 <= deg < 150),
        "light": bool(val > 0.85 and minv > 0.5),
    }


def _vortex_submode_from_palette(feat, digest):
    """Choose one of 5 vortex sub-modes from the finish's colors (not a 50-way tie).

    high contrast -> shockwave (radial CC shock bands + hard high-M ridges)
    metallic/desat -> lattice  (hex/voronoi cell arms)
    cool hues      -> nebula   (soft cloudy radial CC blooms)
    warm/jewel     -> oil      (thin-film oil iridescence)
    else           -> spiral   (classic tight log-spiral arms)
    """
    if feat["contrast"] >= 0.55:
        return "vortex_shockwave"
    if feat["metal"] or feat["sat"] < 0.22:
        return "vortex_lattice"
    if feat["cool"]:
        return "vortex_nebula"
    if feat["warm"] or feat["jewel"]:
        return "vortex_oil"
    return "vortex_spiral"


def _mode_from_palette(feat, digest):
    """Tie the non-vortex mode to color/name, with digest as same-bucket tiebreak.

    metallic   -> brushed / facets
    earthy     -> patina / ember
    jewel/green-> gem / plasma
    light/frost-> frost / silk
    warm bright-> ember / plasma / split
    cool       -> silk / ribbon
    else       -> plasma / ribbon / split
    """
    d = int(digest)
    if feat["metal"] and not feat["jewel"]:
        return ("brushed", "facets")[d % 2]
    if feat["earth"]:
        return ("patina", "ember")[d % 2]
    if feat["jewel"] or (feat["green"] and feat["sat"] > 0.4):
        return ("gem", "plasma")[d % 2]
    # Warm (fire/lava/solar/gold) reads first so bright warm ramps don't fall into
    # the cool 'frost' bucket — a fire gradient must look hot, not frosted.
    if feat["warm"] and feat["val"] > 0.55:
        return ("ember", "plasma", "split")[d % 3]
    if feat["light"] or (feat["cool"] and feat["val"] > 0.75 and feat["sat"] < 0.55):
        return ("frost", "silk")[d % 2]
    if feat["cool"]:
        return ("silk", "ribbon")[d % 2]
    return ("plasma", "ribbon", "split")[d % 3]


_ROW_RE = re.compile(
    r'\[\s*"(?P<id>grad_[^"]+)"\s*,\s*"(?P<name>[^"]+)"\s*,\s*"(?P<c1>[^"]+)"\s*,\s*"(?P<c2>[^"]+)"\s*\]'
)


def _catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "paint-booth-0-finish-data.js"


def _read_gradient_defs() -> list[tuple[str, str, str, str]]:
    text = _catalog_path().read_text(encoding="utf-8", errors="replace")
    start = text.index("const GRADIENT_DEFS")
    end = text.index("const GRADIENT_3C_DEFS", start)
    defs: list[tuple[str, str, str, str]] = []
    for match in _ROW_RE.finditer(text[start:end]):
        finish_id = match.group("id")
        c1 = match.group("c1")
        c2 = match.group("c2")
        if c1 in COLOR_PALETTE and c2 in COLOR_PALETTE:
            defs.append((finish_id, match.group("name"), c1, c2))
    return defs


def _hash_int(value: str) -> int:
    return int(hashlib.blake2s(value.encode("utf-8"), digest_size=4).hexdigest(), 16)


def _xy(shape):
    h, w = shape[:2] if len(shape) > 2 else shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _mask(mask, shape):
    if mask is None:
        h, w = shape[:2] if len(shape) > 2 else shape
        return np.ones((h, w), dtype=np.float32)
    return np.asarray(mask, dtype=np.float32)


def _norm(arr):
    arr = np.asarray(arr, dtype=np.float32)
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


_FIELD_CACHE: OrderedDict[tuple[str, int, int, int], tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = OrderedDict()
_FIELD_CACHE_MAX = 3


def _cached_field(shape, seed, cfg):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = (cfg["finish_id"], int(h), int(w), int(seed))
    cached = _FIELD_CACHE.get(key)
    if cached is not None:
        _FIELD_CACHE.move_to_end(key)
        return cached
    out = _field((h, w), seed, cfg)
    _FIELD_CACHE[key] = out
    _FIELD_CACHE.move_to_end(key)
    while len(_FIELD_CACHE) > _FIELD_CACHE_MAX:
        _FIELD_CACHE.popitem(last=False)
    return out


def _axis_ramp(x, y, direction):
    if direction == "horizontal":
        return np.broadcast_to(x, (y.shape[0], x.shape[1])).astype(np.float32)
    if direction == "diagonal":
        return np.clip((x + y) * 0.5, 0.0, 1.0).astype(np.float32)
    return np.broadcast_to(y, (y.shape[0], x.shape[1])).astype(np.float32)


def _config(finish_id, name, c1_name, c2_name):
    digest = _hash_int(finish_id)
    is_vortex = finish_id.endswith("_vortex") or "vortex" in name.lower()
    if is_vortex:
        direction = "vortex"
    elif finish_id.endswith("_h"):
        direction = "horizontal"
    elif finish_id.endswith("_diag"):
        direction = "diagonal"
    else:
        direction = "vertical"
    feat = _palette_features(c1_name, c2_name, name)
    if is_vortex:
        mode = _vortex_submode_from_palette(feat, digest)
    else:
        mode = _mode_from_palette(feat, digest)
    cfg = {
        "finish_id": finish_id,
        "name": name,
        "direction": direction,
        "is_vortex": is_vortex,
        "mode": mode,
        "feat": feat,
        "c1": np.array(COLOR_PALETTE[c1_name], dtype=np.float32),
        "c2": np.array(COLOR_PALETTE[c2_name], dtype=np.float32),
        "salt": digest % 9973,
        "phase": ((digest >> 5) % 4096) / 4096.0 * np.pi * 2.0,
        "freq": 12.0 + float((digest >> 9) % 17),
        "micro": 72.0 + float((digest >> 13) % 96),
        "arms": 3.0 + float((digest >> 17) % 6),
        "twist": 1.8 + float((digest >> 21) % 48) / 8.0,
        "ridge_width": 20.0 + float((digest >> 3) % 20),
        "metal": 92.0 + float((digest >> 11) % 82),
        "cc": 16.0 + float((digest >> 19) % 18),
        # Widen per-finish identity so same-mode finishes still differ: two extra
        # micro-octave phase offsets + an accent-rotation count derived from the id.
        "phase2": ((digest >> 7) % 4096) / 4096.0 * np.pi * 2.0,
        "phase3": ((digest >> 23) % 4096) / 4096.0 * np.pi * 2.0,
        "accent_rot": 1 + int((digest >> 14) % 7),
        "cell_freq": 5.0 + float((digest >> 6) % 7),
    }
    # Surgical: Grad Aqua Drift — report showed weak daylight sim flash, broad mid-glow,
    # oversized hot dots, weak pin flash (Finish Viewer DNA).
    if finish_id == "grad_aqua_drift":
        cfg["ridge_width"] = float(np.clip(cfg["ridge_width"] * 1.42 + 7.0, 26.0, 54.0))
        cfg["micro"] = float(np.clip(cfg["micro"] + 38.0, 100.0, 228.0))
        cfg["metal"] = float(np.clip(cfg["metal"] + 36.0, 118.0, 218.0))
        cfg["freq"] = float(np.clip(cfg["freq"] + 11.0, 16.0, 40.0))
        cfg["cc"] = float(np.clip(cfg["cc"] + 14.0, 22.0, 44.0))
    return cfg


def _field(shape, seed, cfg):
    x, y = _xy(shape)
    phase = cfg["phase"] + (int(seed) % 8192) * 0.00073 + cfg["salt"] * 0.00011
    freq = cfg["freq"]
    micro_freq = cfg["micro"]
    warp = (
        np.sin((x * (freq * 0.73) + y * (freq * 0.41)) * np.pi + phase) * 0.18
        + np.sin((x * (freq * 1.37) - y * (freq * 0.91)) * np.pi + phase * 1.7) * 0.11
        + np.sin((x * (freq * 2.11) + y * (freq * 1.53)) * np.pi + phase * 2.3) * 0.06
    )
    mode = cfg["mode"]
    if mode in _VORTEX_MODES:
        cx = x - (0.46 + np.sin(phase) * 0.08)
        cy = y - (0.52 + np.cos(phase * 0.7) * 0.08)
        dist = np.sqrt(cx * cx + cy * cy)
        angle = np.arctan2(cy, cx)
        arms = cfg["arms"]
        twist = cfg["twist"]
        if mode == "vortex_spiral":
            # Classic tight log-spiral arms.
            spiral = angle * arms + np.log1p(dist * 18.0) * twist + warp * 2.6
            field = _norm(np.sin(spiral) * 0.42 + dist * 1.25 + warp * 0.34)
            ridge_base = np.abs(np.sin((spiral * 2.6 + dist * micro_freq * 0.10) * np.pi))
        elif mode == "vortex_nebula":
            # Soft cloudy radial blooms: low-arm, heavy radial smear, gentle ridges.
            cloud = (
                np.sin((dist * (freq * 0.6) - phase) * np.pi) * 0.5
                + np.sin((angle * (arms * 0.5 + 1.0) + dist * 6.0 + phase * 1.4)) * 0.4
            )
            field = _norm(0.62 - dist * 0.9 + cloud * 0.45 + warp * 0.5)
            ridge_base = np.abs(np.sin((dist * micro_freq * 0.14 + cloud * 1.5 + phase) * np.pi))
        elif mode == "vortex_shockwave":
            # Concentric radial shock bands + hard high-M ridges between rings.
            rings = np.sin((dist * (freq * 1.8 + 10.0) - twist * 2.0 + phase) * np.pi)
            spoke = np.sin(angle * (arms + 4.0) + phase)
            field = _norm(0.5 + rings * 0.5 - dist * 0.55 + spoke * 0.12 + warp * 0.22)
            ridge_base = np.power(np.abs(rings), 0.5) * (0.6 + 0.4 * np.abs(spoke))
            ridge_base = np.clip(ridge_base, 0.0, 1.0)
        elif mode == "vortex_lattice":
            # Hex/voronoi-ish cells riding the swirl: metallic faceted vortex.
            sa = angle * arms + np.log1p(dist * 14.0) * twist
            u = np.cos(sa) * dist * cfg["cell_freq"] * 2.0
            v = np.sin(sa) * dist * cfg["cell_freq"] * 2.0
            cell = np.minimum(
                np.abs(np.sin((u + warp * 2.0) * np.pi)),
                np.abs(np.sin((v - warp * 1.5) * np.pi)),
            )
            field = _norm(0.5 + np.sin(sa) * 0.3 - dist * 0.5 + (0.5 - cell) * 0.6 + warp * 0.18)
            ridge_base = np.clip(cell, 0.0, 1.0)
        else:  # vortex_oil
            # Thin-film oil iridescence: multi-band interference around the swirl.
            sa = angle * arms + np.log1p(dist * 16.0) * twist + warp * 2.2
            band = (
                np.sin(sa * 1.0 + phase)
                + np.sin(sa * 1.93 + dist * 7.0 + cfg["phase2"]) * 0.7
                + np.sin(sa * 3.41 - dist * 4.0 + cfg["phase3"]) * 0.45
            )
            field = _norm(0.5 + band * 0.32 + np.sin(sa) * 0.18 - dist * 0.35)
            ridge_base = np.abs(np.sin((band * 2.2 + dist * micro_freq * 0.08) * np.pi))
    else:
        ramp = _axis_ramp(x, y, cfg["direction"])
        if mode == "ribbon":
            flow = np.sin((ramp * freq + warp * 1.7 + x * 3.0) * np.pi)
            field = _norm(ramp * 0.70 + flow * 0.18 + warp * 0.30)
        elif mode == "facets":
            cell = (
                np.floor((x * (7.0 + cfg["arms"]) + y * 3.3 + warp * 2.0 + phase) * 3.0)
                + np.floor((y * (8.0 + cfg["twist"]) - x * 4.1 + phase) * 2.0) * 0.7
            )
            field = _norm(ramp * 0.45 + np.mod(cell, 9.0) / 8.0 * 0.45 + warp * 0.18)
        elif mode == "plasma":
            plasma = np.sin((x * freq * 0.55 + warp * 2.2) * np.pi + phase)
            plasma += np.sin((y * freq * 0.77 - warp * 1.6) * np.pi + phase * 1.4)
            field = _norm(ramp * 0.46 + plasma * 0.22 + warp * 0.26)
        elif mode == "silk":
            waves = np.sin((ramp * freq * 1.2 + np.sin(x * 21.0 + phase) * 0.42 + warp) * np.pi)
            field = _norm(ramp * 0.62 + waves * 0.20 + warp * 0.22)
        elif mode == "split":
            seam = np.clip(1.0 - np.abs(ramp - (0.42 + np.sin(phase) * 0.08)) * 7.5, 0.0, 1.0)
            field = _norm(ramp * 0.72 + seam * 0.26 + warp * 0.22)
        elif mode == "frost":
            # Cool crystalline frost: fine fractured veins over a clean ramp.
            vein = (
                np.sin((x * freq * 1.9 + y * freq * 0.6 + warp * 2.4 + phase) * np.pi)
                + np.sin((x * freq * 0.5 - y * freq * 2.2 + cfg["phase2"]) * np.pi) * 0.6
            )
            crackle = np.abs(np.sin((x * micro_freq * 0.4 + y * micro_freq * 0.5 + vein) * np.pi))
            field = _norm(ramp * 0.66 + vein * 0.14 + (0.5 - crackle) * 0.22 + warp * 0.16)
        elif mode == "brushed":
            # Anisotropic brushed metal: streaks aligned to the gradient axis.
            grain = np.sin((x * micro_freq * 1.6 + warp * 0.6 + phase) * np.pi) * 0.5
            grain += np.sin((x * micro_freq * 3.1 - warp * 0.4 + cfg["phase3"]) * np.pi) * 0.25
            field = _norm(ramp * 0.74 + grain * 0.16 + warp * 0.12)
        elif mode == "gem":
            # Faceted gemstone: sharp angular cells with strong internal contrast.
            f = cfg["cell_freq"] + 2.0
            cell = (
                np.floor((x * f + y * (f * 0.45) + warp * 1.6 + phase) * 1.0)
                - np.floor((y * f - x * (f * 0.6) + cfg["phase2"]) * 1.0) * 0.6
            )
            face = np.mod(cell, 7.0) / 6.0
            field = _norm(ramp * 0.40 + face * 0.50 + warp * 0.16)
        elif mode == "patina":
            # Weathered earthy patina: blotchy organic mottle.
            mottle = (
                np.sin((x * freq * 0.7 + y * freq * 0.9 + warp * 3.0 + phase) * np.pi)
                + np.sin((x * freq * 1.6 - y * freq * 0.5 + cfg["phase2"]) * np.pi) * 0.55
                + np.sin((x * freq * 0.3 + y * freq * 1.9 + cfg["phase3"]) * np.pi) * 0.35
            )
            field = _norm(ramp * 0.52 + mottle * 0.30 + warp * 0.24)
        else:  # ember
            flame = np.sin((y * freq * 1.2 - x * freq * 0.28 + warp * 2.1) * np.pi + phase)
            field = _norm(ramp * 0.54 + flame * 0.26 + warp * 0.22)
        a = np.abs(np.sin((x * micro_freq * 0.47 + y * micro_freq * 0.29 + field * 4.0 + phase) * np.pi))
        b = np.abs(np.sin((x * -micro_freq * 0.31 + y * micro_freq * 0.61 + warp * 3.0 + phase * 1.3) * np.pi))
        ridge_base = np.minimum(a, b)
    ridges = np.clip(1.0 - ridge_base * cfg["ridge_width"], 0.0, 1.0)
    glint = np.clip(
        1.0
        - np.abs(
            np.sin((x * (micro_freq * 0.83) - y * (micro_freq * 0.37) + warp * 1.2 + phase) * np.pi)
        )
        * 48.0,
        0.0,
        1.0,
    )
    micro = _norm(
        np.sin((x * micro_freq * 2.9 + y * micro_freq * 1.7) * np.pi + phase)
        + np.sin((x * micro_freq * 4.3 - y * micro_freq * 3.1) * np.pi + phase * 1.9) * 0.5
    )
    return field, ridges.astype(np.float32), glint.astype(np.float32), micro.astype(np.float32)


def _make_spec(cfg):
    def spec_fn(shape, mask, seed, sm):
        h, w = shape[:2] if len(shape) > 2 else shape
        mask_arr = _mask(mask, (h, w))
        # SPB-105 perf heartbeat 2026-05-31; owner: "Speed is king."
        # Spec and paint are rendered as a pair, so reuse the expensive gradient field.
        # Metric target: gradient monolithics over 4s should fall under budget without visual recipe changes.
        field, ridges, glint, micro = _cached_field((h, w), seed, cfg)
        x, y = _xy((h, w))
        phase = cfg["phase"] + cfg["salt"] * 0.00017 + (int(seed) % 4096) * 0.00091
        fine_a = np.abs(
            np.sin((x * cfg["micro"] * 1.73 + y * cfg["micro"] * 0.91 + field * 5.4 + phase) * np.pi)
        )
        fine_b = np.abs(
            np.sin((x * -cfg["micro"] * 0.82 + y * cfg["micro"] * 1.37 + field * 3.1 + phase * 1.63) * np.pi)
        )
        crystal = np.clip(1.0 - np.minimum(fine_a, fine_b) * 34.0, 0.0, 1.0).astype(np.float32)
        satin_grain = _norm(
            np.sin((x * cfg["micro"] * 3.7 + y * cfg["micro"] * 2.1 + phase) * np.pi)
            + np.sin((x * cfg["micro"] * 5.3 - y * cfg["micro"] * 4.1 + phase * 1.9) * np.pi) * 0.45
        )
        channel_split = np.clip(np.abs(field - 0.5) * 2.0, 0.0, 1.0)
        hot_lane = np.clip(ridges * 0.62 + glint * 0.90 + crystal * 0.52, 0.0, 1.0)
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        m = (
            72.0
            + cfg["metal"] * 0.62
            + field * 104.0
            + channel_split * 34.0
            + ridges * 70.0
            + glint * 118.0
            + crystal * 82.0
            + (micro - 0.5) * 28.0
        )
        r = (
            72.0
            - field * 30.0
            - hot_lane * 46.0
            + (1.0 - ridges) * 24.0
            + satin_grain * 42.0
            + channel_split * 18.0
        )
        cc = (
            74.0
            + field * 78.0
            + ridges * 112.0
            + glint * 158.0
            + crystal * 96.0
            + np.roll(ridges, 2 + int(cfg["arms"]) % 5, axis=1) * 54.0
        )
        if cfg["direction"] == "horizontal":
            axis = x
            cross = y
        elif cfg["direction"] == "diagonal":
            axis = np.clip((x + y) * 0.5, 0.0, 1.0)
            cross = np.abs(x - y)
        else:
            axis = y
            cross = x
        pin = np.clip(
            1.0
            - np.abs(
                np.sin((axis * (cfg["freq"] * 1.7) + cross * (cfg["arms"] + 5.0) + phase) * np.pi)
            )
            * 18.0,
            0.0,
            1.0,
        )
        scatter = np.clip(
            1.0
            - np.abs(
                np.sin((x * cfg["micro"] * 2.31 - y * cfg["micro"] * 1.77 + phase * 1.41) * np.pi)
            )
            * 28.0,
            0.0,
            1.0,
        )
        mode = cfg["mode"]
        rot = int(cfg["accent_rot"])
        if mode == "vortex_spiral":
            arm = np.clip(ridges * 0.80 + glint * 1.15 + crystal * 0.28, 0.0, 1.0)
            m += arm * 62.0 + np.roll(glint, 4 + rot, axis=0) * 48.0
            r += satin_grain * 14.0 - arm * 42.0
            cc += arm * 94.0 + channel_split * 38.0 + scatter * 38.0
        elif mode == "vortex_nebula":
            # Soft cloudy radial CC blooms: low metal, broad glossy halo, gentle roughness lift.
            bloom = np.clip(field * 0.55 + glint * 0.70 + scatter * 0.30, 0.0, 1.0)
            halo = _norm(np.roll(field, 3 + rot, axis=1) + glint * 0.6)
            m += bloom * 34.0 + halo * 26.0
            r += (1.0 - field) * 30.0 + satin_grain * 16.0 - glint * 22.0
            cc += bloom * 96.0 + halo * 60.0 + channel_split * 24.0
        elif mode == "vortex_shockwave":
            # Hard high-M ridges between concentric rings + sharp CC shock fronts.
            shock = np.clip(ridges * 1.10 + crystal * 0.40, 0.0, 1.0)
            front = np.clip(np.power(np.clip(glint, 0.0, 1.0), 1.4) + pin * 0.4, 0.0, 1.0)
            m += np.power(shock, 0.8) * 104.0 + front * 40.0
            r += satin_grain * 10.0 - shock * 58.0 - front * 24.0
            cc += front * 150.0 + shock * 70.0 + channel_split * 34.0
        elif mode == "vortex_lattice":
            # Hex/voronoi cell vortex: faceted metal arms, cell edges glint.
            cell_edge = np.clip(ridges * 0.95 + pin * 0.45, 0.0, 1.0)
            facet = np.clip(crystal * 0.70 + scatter * 0.55, 0.0, 1.0)
            m += cell_edge * 96.0 + facet * 40.0 + channel_split * 30.0
            r += satin_grain * 24.0 - cell_edge * 50.0
            cc += cell_edge * 110.0 + glint * 64.0
        elif mode == "vortex_oil":
            # Thin-film oil iridescence: smooth high CC, low roughness, color-banded gloss.
            film = _norm(
                np.sin((field * 9.0 + cfg["phase2"]) * np.pi)
                + np.sin((field * 15.0 - cfg["phase3"]) * np.pi) * 0.6
            )
            sheen = np.clip(film * 0.55 + glint * 0.80 + scatter * 0.22, 0.0, 1.0)
            m += sheen * 50.0 + np.roll(glint, 3 + rot, axis=0) * 30.0
            r += (1.0 - film) * 14.0 - sheen * 40.0 - glint * 14.0
            cc += sheen * 140.0 + film * 54.0
        elif mode == "facets":
            facet = np.clip(crystal * 0.85 + scatter * 0.70 + pin * 0.35, 0.0, 1.0)
            m += facet * 92.0 + channel_split * 46.0
            r += satin_grain * 20.0 - facet * 46.0
            cc += facet * 118.0 + glint * 72.0
        elif mode == "plasma":
            plasma = _norm(
                np.sin((x * cfg["freq"] * 2.3 + field * 6.4 + phase) * np.pi)
                + np.sin((y * cfg["freq"] * 1.9 - field * 4.8 + phase * 1.7) * np.pi) * 0.7
            )
            spark = np.clip(plasma * 0.35 + glint * 1.05 + crystal * 0.50 + scatter * 0.25, 0.0, 1.0)
            m += spark * 64.0
            r += (1.0 - plasma) * 18.0 - spark * 34.0
            cc += spark * 132.0 + plasma * 46.0
        elif mode == "silk":
            weave = _norm(
                np.sin((axis * cfg["micro"] * 4.8 + phase) * np.pi)
                + np.sin((cross * cfg["micro"] * 5.7 + phase * 1.33) * np.pi) * 0.65
            )
            pearl = np.clip(weave * 0.52 + field * 0.34 + ridges * 0.28 + scatter * 0.22, 0.0, 1.0)
            m += pearl * 48.0
            r += weave * 36.0 - ridges * 36.0 - scatter * 18.0
            cc += pearl * 98.0 + glint * 72.0
        elif mode == "split":
            split_edge = np.clip(channel_split * 0.70 + pin * 0.55 + scatter * 0.30, 0.0, 1.0)
            m += split_edge * 76.0 + ridges * 34.0
            r += (1.0 - channel_split) * 24.0 - split_edge * 38.0
            cc += split_edge * 118.0 + ridges * 76.0
        elif mode == "frost":
            # Cool crystalline frost: bright glossy crackle, high roughness in the matte body.
            shard = np.clip(crystal * 0.85 + glint * 0.55 + (1.0 - field) * 0.20, 0.0, 1.0)
            body = np.clip((1.0 - ridges) * 0.6 + (1.0 - glint) * 0.4, 0.0, 1.0)
            m += shard * 44.0 + glint * 30.0
            r += body * 56.0 + satin_grain * 24.0 - shard * 30.0
            cc += shard * 116.0 + glint * 70.0
        elif mode == "brushed":
            # Anisotropic brushed metal: high directional metal, low CC, fine streak roughness.
            streak = _norm(
                np.sin((axis * cfg["micro"] * 5.6 + phase) * np.pi)
                + np.sin((axis * cfg["micro"] * 8.9 + cfg["phase2"]) * np.pi) * 0.5
            )
            grain_metal = np.clip(streak * 0.6 + ridges * 0.5 + field * 0.30, 0.0, 1.0)
            m += grain_metal * 96.0 + channel_split * 24.0
            r += (1.0 - streak) * 40.0 + satin_grain * 30.0 - grain_metal * 20.0
            cc += grain_metal * 60.0 + glint * 40.0
        elif mode == "gem":
            # Faceted gemstone: hard facet glints, deep glossy facets, crisp roughness drop.
            facet = np.clip(crystal * 0.80 + pin * 0.55 + channel_split * 0.40, 0.0, 1.0)
            depth = np.clip(field * 0.6 + (1.0 - ridges) * 0.3, 0.0, 1.0)
            m += facet * 86.0 + glint * 36.0
            r += (1.0 - facet) * 22.0 - facet * 40.0 + satin_grain * 16.0
            cc += facet * 128.0 + depth * 60.0 + glint * 54.0
        elif mode == "patina":
            # Weathered earthy patina: mottled metal, raised roughness, muted CC veined by mottle.
            mottle = np.clip(channel_split * 0.5 + (1.0 - glint) * 0.4 + satin_grain * 0.3, 0.0, 1.0)
            verdigris = np.clip(field * 0.55 + scatter * 0.35, 0.0, 1.0)
            m += verdigris * 50.0 + ridges * 30.0
            r += mottle * 64.0 + satin_grain * 28.0 - glint * 18.0
            cc += verdigris * 78.0 + glint * 44.0 + ridges * 36.0
        else:
            ember = np.clip(ridges * 0.66 + glint * 1.08 + crystal * 0.44 + scatter * 0.25, 0.0, 1.0)
            m += ember * 88.0 + pin * 34.0
            r += satin_grain * 24.0 - ember * 46.0
            cc += ember * 126.0 + crystal * 72.0
        # --- VIVA chroma-steer (mirror cultural_viva_mexico ~304-338) ----------
        # Reconstruct the SAME local color t the paint uses, blend c1->c2 per
        # pixel, derive warm/cool/green/yellow weights from that color, and push
        # R/M/CC by them. The hot end of a fire ramp gets warm gloss (lower R,
        # higher M), the cool end gets cool gloss (higher CC). Field-driven, no
        # image plate — so the spec's gloss temperature tracks the finish's
        # actual color sweep instead of being uniform.
        t_local = np.clip(field + (ridges - 0.5) * 0.08 + (micro - 0.5) * 0.06, 0.0, 1.0)
        if cfg["finish_id"] == "grad_aqua_drift":
            t_local = np.clip((t_local - 0.5) * 1.14 + 0.5, 0.0, 1.0)
        c1v = cfg["c1"]
        c2v = cfg["c2"]
        lr = c1v[0] * (1.0 - t_local) + c2v[0] * t_local
        lg = c1v[1] * (1.0 - t_local) + c2v[1] * t_local
        lb = c1v[2] * (1.0 - t_local) + c2v[2] * t_local
        lmax = np.maximum(np.maximum(lr, lg), lb) + 1e-6
        warm_w = np.clip((lr - np.maximum(lg, lb) * 0.92) / lmax, 0.0, 1.0)
        cool_w = np.clip((lb - np.maximum(lr, lg) * 0.92) / lmax, 0.0, 1.0)
        green_dom = np.clip((lg - np.maximum(lr, lb)) / lmax, 0.0, 1.0)
        yellow_hint = (
            np.clip((lr + lg) * 0.5 - lb, 0.0, 1.0)
            * np.clip(lr - 0.18, 0.0, 1.0)
            * np.clip(lg - 0.18, 0.0, 1.0)
        )
        DS = 1.0  # gradients already push hard; keep the chroma steer subtle.
        r = r - warm_w * (24.0 * DS) + cool_w * (15.0 * DS) - yellow_hint * (10.0 * DS)
        m = m + warm_w * (16.0 * DS) - cool_w * (7.0 * DS) + yellow_hint * (8.0 * DS)
        cc = cc - warm_w * (11.0 * DS) + cool_w * (14.0 * DS) + green_dom * (9.0 * DS)
        # Green split: phase-modulated R/Cc so green endpoints don't read flat.
        phase_g = np.sin(x * (310.0 + cfg["salt"] % 90) + y * (220.0 + (cfg["salt"] >> 3) % 70))
        r = r + phase_g * (16.0 * DS) * green_dom
        cc = cc - phase_g * (10.0 * DS) * green_dom
        m = m + np.abs(phase_g) * (8.0 * DS) * green_dom
        if cfg["finish_id"] == "grad_aqua_drift":
            glint_peaks = np.power(np.clip((glint - 0.36) / 0.64, 0.0, 1.0), 1.75)
            spike = np.clip(
                crystal * 0.90 + glint_peaks * 0.98 + scatter * 0.74 + channel_split * 0.22,
                0.0,
                1.0,
            )
            sun_fill = np.clip(field * 0.52 + scatter * 0.48 + pin * 0.28, 0.0, 1.0)
            m += spike * 52.0 + sun_fill * 26.0
            r -= spike * 62.0 + sun_fill * 30.0
            cc += spike * 76.0 + sun_fill * 42.0
            r += (micro - 0.5) * 34.0
        spec[:, :, 0] = np.clip(m * float(sm) * mask_arr + 5.0 * (1.0 - mask_arr), 0, 255).astype(np.uint8)
        spec[:, :, 1] = np.clip(r * mask_arr + 118.0 * (1.0 - mask_arr), 18, 235).astype(np.uint8)
        spec[:, :, 2] = np.where(mask_arr > 0.0, np.clip(cc, 16, 255), 0).astype(np.uint8)
        spec[:, :, 3] = np.clip(mask_arr * 255.0, 0, 255).astype(np.uint8)
        return spec

    return spec_fn


def _make_paint(cfg):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = shape[:2] if len(shape) > 2 else shape
        mask_arr = _mask(mask, (h, w))
        base = paint[:, :, :3].astype(np.float32, copy=True)
        field, ridges, glint, micro = _cached_field((h, w), seed, cfg)
        c1 = cfg["c1"].reshape(1, 1, 3)
        c2 = cfg["c2"].reshape(1, 1, 3)
        t = np.clip(field + (ridges - 0.5) * 0.08 + (micro - 0.5) * 0.06, 0.0, 1.0)
        if cfg["finish_id"] == "grad_aqua_drift":
            t = np.clip((t - 0.5) * 1.14 + 0.5, 0.0, 1.0)
        target = c1 * (1.0 - t[:, :, None]) + c2 * t[:, :, None]
        warm = np.maximum(c1, c2)
        cool = np.roll(np.minimum(c1, c2), 1, axis=2)
        accent = warm * ridges[:, :, None] * 0.20 + cool * glint[:, :, None] * 0.16
        if cfg["finish_id"] == "grad_aqua_drift":
            accent *= 1.38
        fine = np.clip(ridges * 0.12 + glint * 0.18 + (micro - 0.5) * 0.075, -0.06, 0.24)
        if cfg["finish_id"] == "grad_aqua_drift":
            fine = np.clip(fine * 1.32, -0.06, 0.30)
        target = np.clip(target + accent + fine[:, :, None], 0.0, 1.0)
        if cfg["is_vortex"]:
            target = np.clip(target * (0.72 + field[:, :, None] * 0.42) + glint[:, :, None] * 0.11, 0.0, 1.0)
        elif cfg["mode"] in {"facets", "split", "gem", "brushed"}:
            target = np.clip(target + ridges[:, :, None] * 0.09, 0.0, 1.0)
        blend = np.clip(0.88 * float(pm), 0.0, 1.0) * mask_arr[:, :, None]
        out = base * (1.0 - blend) + target * blend
        if bb is not None:
            bb_arr = bb[:, :, None] if getattr(bb, "ndim", 0) == 2 else bb
            out = np.clip(out + bb_arr * 0.18 * mask_arr[:, :, None], 0.0, 1.0)
        return np.ascontiguousarray(out.astype(np.float32))

    return paint_fn


def _build_entries():
    entries = {}
    for finish_id, name, c1, c2 in _read_gradient_defs():
        cfg = _config(finish_id, name, c1, c2)
        entries[finish_id] = (_make_spec(cfg), _make_paint(cfg))
    return entries


OWNER_REVIEW_GRADIENT_MONOLITHICS = _build_entries()


# ═══════════ 2026-06-21 COLOR SCIENCE REDIRECT — GRADIENTS (Directional/Vortex/Extended) ═══════════
# grad_ specs were the FLATTEST in COLOR SCIENCE (M.std 6-23). Replace EVERY grad_ spec with a
# UNIQUE elaborate color_science_2026 spec via a deterministic hash-recipe generator (vortex ids
# lean rotational spiral/ripple; the rest span all 7 looks). Keep paint. This is the last grad_ write.
_GR_LOOKS = ["spectral_spiral", "ripple_caustics", "oilslick_thinfilm", "holographic_mosaic",
             "crystal_facets", "guilloche", "iridescent_flow"]
_GR_CANDY = {
    "std": {}, "warm": dict(m_hi=242, cc_edge=186, r_edge=118),
    "dark": dict(m_lo=64, m_hi=214, cc_edge=180),
    "deep": dict(m_hi=240, cc_edge=192, r_core=20, gamma=1.5),
    "icy": dict(m_hi=232, r_edge=96, cc_edge=150, gamma=1.5),
}
_GR_CANDY_KEYS = list(_GR_CANDY.keys())


def _gr_cs_recipe(fid, idx):
    hh = (sum(ord(c) for c in fid) * 2654435761) & 0x7FFFFFFF
    pool = ["spectral_spiral", "ripple_caustics"] if "vortex" in fid else _GR_LOOKS
    look = pool[hh % len(pool)]
    if look == "spectral_spiral":
        kw = dict(arms=float(3 + hh % 9), twist=float(3 + (hh // 9) % 9))
    elif look == "ripple_caustics":
        kw = dict(rings=float(6 + hh % 9))
    elif look == "oilslick_thinfilm":
        kw = dict(bands=float(4 + hh % 7))
    elif look == "holographic_mosaic":
        kw = dict(cells=float(20 + (hh % 12) * 2))
    elif look == "crystal_facets":
        kw = dict(cells=float(30 + (hh % 7) * 7))
    elif look == "guilloche":
        kw = dict(a=float(9 + hh % 7), b=float(11 + (hh // 7) % 7))
    else:
        kw = dict(scale=float(3 + hh % 4))
    rec = {"look": look, "look_kwargs": kw, "depth_from": ("structure", "invert")[hh % 2],
           "candy": dict(_GR_CANDY[_GR_CANDY_KEYS[hh % len(_GR_CANDY_KEYS)]]),
           "motion": 0.32 + (hh % 5) * 0.05, "phase": (hh % 7) * 0.42, "relief": 28.0}
    return rec, 7000 + idx * 47


def _gr_cs_spec_fn(recipe, seed_off):
    _rc = dict(recipe); _so = int(seed_off)

    def spec_fn(shape, mask, seed, sm):
        import numpy as _np
        from engine.paint_v2 import color_science_2026 as _csx
        h, w = int(shape[0]), int(shape[1])
        spec = _csx.compose_cs_spec((h, w), int(seed) + _so, 1.0, _rc).astype(_np.float32)
        m = _mask(mask, (h, w))
        out = _np.zeros((h, w, 4), _np.uint8)
        out[:, :, 0] = _np.clip(spec[:, :, 0] * float(sm) * m + 5.0 * (1.0 - m), 0, 255).astype(_np.uint8)
        out[:, :, 1] = _np.clip(spec[:, :, 1] * m + 118.0 * (1.0 - m), 18, 235).astype(_np.uint8)
        out[:, :, 2] = _np.where(m > 0.0, _np.clip(spec[:, :, 2], 16, 255), 0).astype(_np.uint8)
        out[:, :, 3] = _np.clip(m * 255.0, 0, 255).astype(_np.uint8)
        return out
    return spec_fn


for _gr_idx, _gr_id in enumerate(list(OWNER_REVIEW_GRADIENT_MONOLITHICS.keys())):
    if _gr_id.startswith("grad_"):
        _gr_rec, _gr_so = _gr_cs_recipe(_gr_id, _gr_idx)
        OWNER_REVIEW_GRADIENT_MONOLITHICS[_gr_id] = (
            _gr_cs_spec_fn(_gr_rec, _gr_so), OWNER_REVIEW_GRADIENT_MONOLITHICS[_gr_id][1])

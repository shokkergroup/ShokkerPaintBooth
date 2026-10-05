"""Five-round owner overhaul for the complete SPB spec-overlay catalog.

SPB-105, Round 2 / tick 1, 2026-07-13.
Owner verdict: "WIDE diversity in spec pattern LOOKS and the specs themselves
on color/finish type (gloss, flat, chrome, FRACTURED, etc)... FIVE ROUNDS."

Round-1 baseline (181 picker-visible ids): 158 rebuild-required; 2048 cold
catalog 166.029s, p95 2.061s, max 3.225s.  Round-2 final: 0 rebuild-required,
0 weak/range/coupled/duplicate flags; 45.330s, p95 .352s, max .426s.  This
module is isolated and late-wired so the overhaul retains one rollback seam.

SPB-105 Round 5 / tick 5 final movement: 512 gate 181/181, minimum 86.63,
nearest structural similarity max .653, weakest channel std .1013, minimum
channel span .86, max M/R/CC correlation .538.  Final cold 2048 catalog:
56.336s total, p95 .408s, max .464s (baseline 166.029/2.061/3.225).

SPB-105 semantic correction / owner review, 2026-07-13: the owner found that
the passing catalog still did not visually honor names such as Brick, Fish
Scales, Snake and Checkered Flag.  The correction expands 21 generic grammars
to 91 explicit subject archetypes.  Final 512 gate: 181/181, minimum 85.20,
structural-similarity max .7951, weakest channel std .09336, minimum span .86,
and max M/R/CC correlation .8416.  Cold 2048 catalog: p95 .815s, max 1.118s.

SPB-105 deconfetti correction / owner review, 2026-07-13. Owner verdict:
catalog-wide grain/noise/confetti "takes away from the designs." Removed the
universal grain/fleck/scratch/secondary stack, sparse channel extrema, hard
shade buckets, and twelve-pattern stipple boost. Loose texture is now explicit:
142 clean / 21 particulate / 18 surface identities. Final 512 gate: 181/181,
minimum 86.57, structural-similarity max .76812, weakest channel std .10296,
minimum span .86, max M/R/CC correlation .84818. Cold 2048 catalog: 39.214s,
p95 .324s, max .510s. Native owner-example tiny color components fell 33-100%
(Brick -84.9%, Dragon Scale -94.7%) versus the semantic-rebuild baseline.

Design contract
---------------
* Every renderer uses a named semantic core grammar selected from its identity.
* Each semantic core stacks subject-specific anatomy/construction marks. Generic
  grain, flecks, scratches, and unrelated secondary motifs are forbidden on
  picker-visible overlays; loose texture exists only where the name calls for it.
* Native target features are 8-32 px at 2048.  Smooth construction happens on
  a bounded working canvas; crisp masks are then linearly resampled.
* M/R/CC use independent eight-tier material palettes across eight response
  classes (chrome, gloss, satin, flat, fractured, optical, composite, aged).  The same physical masks
  are emphasized differently per channel, preserving material trace without
  collapsing all three channels into recolored copies.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Iterable, Mapping

import cv2
import numpy as np

from engine.spec_pattern_families.semantic_overlays_2026 import (
    semantic_archetype,
    semantic_field,
    semantic_texture_policy,
)


_TAU = math.tau
_WORK_MAX = 768


def _stable(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "little")


def _norm(field: np.ndarray) -> np.ndarray:
    field = np.asarray(field, dtype=np.float32)
    lo = float(field.min())
    hi = float(field.max())
    if hi - lo < 1e-7:
        return np.full_like(field, 0.5, dtype=np.float32)
    return ((field - lo) / (hi - lo)).astype(np.float32)


def _work_shape(shape: tuple[int, ...]) -> tuple[int, int, float]:
    h, w = int(shape[0]), int(shape[1])
    factor = min(1.0, _WORK_MAX / max(h, w, 1))
    return max(96, int(round(h * factor))), max(96, int(round(w * factor))), factor


def _coords(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    y = np.arange(h, dtype=np.float32)[:, None]
    x = np.arange(w, dtype=np.float32)[None, :]
    return x, y


def _hash_field(x: np.ndarray, y: np.ndarray, key: int) -> np.ndarray:
    phase = float(key & 0xFFFF) * 0.000137
    return np.mod(np.sin(x * 12.9898 + y * 78.233 + phase) * 43758.5453, 1.0).astype(np.float32)


def _smooth_noise(h: int, w: int, key: int, cell: int = 24) -> np.ndarray:
    rng = np.random.default_rng(key & 0xFFFFFFFF)
    gh = max(4, h // max(4, cell)) + 2
    gw = max(4, w // max(4, cell)) + 2
    grid = rng.random((gh, gw), dtype=np.float32)
    return cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32)


def _numeric_param(params: Mapping[str, object], key: str) -> float | None:
    try:
        value = float(params[key])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _feature_multiplier(params: Mapping[str, object]) -> float:
    """Translate legacy saved controls into the bounded 8-32 px system."""
    size_controls = (
        ("cell_size", 20.0), ("weave_size", 12.0), ("pebble_size", 5.0),
        ("spacing", 12.0), ("dimple_spacing", 18.0), ("tile_size", 32.0),
        ("block_size", 2.0), ("cell", 12.0), ("scale_w", 20.0), ("scale_r", 16.0),
    )
    for name, baseline in size_controls:
        value = _numeric_param(params, name)
        if value is not None and value > 0:
            return float(np.clip(math.sqrt(value / baseline), .55, 1.75))
    frequency_controls = (
        ("frequency", 60.0), ("line_freq", 80.0), ("freq", 30.0),
        ("band_freq", 10.0), ("n_rays", 72.0), ("ring_freq", 20.0),
        ("num_bands", 40.0), ("cell_density", 48.0), ("pore_density", 80.0),
        ("num_cells", 100.0), ("num_shards", 180.0),
    )
    for name, baseline in frequency_controls:
        value = _numeric_param(params, name)
        if value is not None and value > 0:
            return float(np.clip(math.sqrt(baseline / value), .55, 1.75))
    return 1.0


def _line(coord: np.ndarray, period: float, width: float) -> np.ndarray:
    pos = np.mod(coord / max(period, 1.0), 1.0)
    dist = np.minimum(pos, 1.0 - pos)
    return np.clip(1.0 - dist / max(width, 1e-3), 0.0, 1.0).astype(np.float32)


def _edge(field: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(field.astype(np.float32))
    return _norm(np.hypot(gx, gy))


def _semantic_channel_fields(core: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Derive three material responses only from the named subject geometry.

    SPB-105 deconfetti tick 1, owner verdict 2026-07-13: catalog-wide
    grain/noise/confetti "takes away from the designs."  Directional edge
    lighting and inner/outer relief provide shade diversity without inventing
    free-floating marks that are not part of the subject.
    """
    core = np.asarray(core, dtype=np.float32)
    gy, gx = np.gradient(core)
    ca, sa = math.cos(angle), math.sin(angle)
    along_edge = _norm(np.abs(gx * ca + gy * sa))
    cross_edge = _norm(np.abs(-gx * sa + gy * ca))
    smooth = cv2.GaussianBlur(core, (0, 0), sigmaX=.85, sigmaY=.85)
    inner_relief = _norm(np.clip(core - smooth, 0.0, None))
    outer_relief = _norm(np.clip(smooth - core, 0.0, None))
    shifted = cv2.warpAffine(core, np.float32([[1, 0, 2], [0, 1, 1]]),
                             (core.shape[1], core.shape[0]),
                             flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    offset_relief = _norm(np.abs(core - shifted))

    # Deconfetti tick 3: all three channels use whole regions and continuous
    # edge bands. Earlier positive/negative directional edge halves produced
    # isolated RGB pinpoints where channels disagreed one pixel at a time.
    metallic = _norm(core * .82 + smooth * .18)
    roughness = _norm((1.0 - core) * .34 + along_edge * .48 + outer_relief * .18)
    clearcoat = _norm(smooth * .20 + cross_edge * .42 + inner_relief * .18 + offset_relief * .20)
    return metallic, roughness, clearcoat


def _rotate(x: np.ndarray, y: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray]:
    ca, sa = math.cos(angle), math.sin(angle)
    return x * ca + y * sa, -x * sa + y * ca


def _core_field(grammar: str, x: np.ndarray, y: np.ndarray, feature: float,
                angle: float, key: int, variant: int) -> np.ndarray:
    u, v = _rotate(x, y, angle)
    f = max(2.0, feature)
    warp = _smooth_noise(y.shape[0], x.shape[1], key + 17, max(8, int(f * 3))) - 0.5

    if grammar == "weave":
        a = _line(u + warp * f * 1.8, f * 2.2, 0.18)
        b = _line(v - warp * f * 1.4, f * (2.0 + variant * 0.10), 0.16)
        over = (np.mod(np.floor(u / f) + np.floor(v / f), 2.0) > 0).astype(np.float32)
        return _norm(a * (0.55 + over * 0.45) + b * (1.0 - over * 0.35))
    if grammar == "hex":
        a = _line(u, f * 3.1, 0.10)
        b = _line(u * 0.5 + v * 0.8660254, f * 3.1, 0.10)
        c = _line(u * 0.5 - v * 0.8660254, f * 3.1, 0.10)
        return _norm(np.maximum.reduce([a, b, c]) * 0.78 + warp * 0.22)
    if grammar == "fracture":
        n = warp * f * (2.6 + variant * 0.25)
        fault = np.sin((u + n) / f * 2.1) + np.sin((v - n * 0.7) / f * 2.7)
        crack = np.exp(-np.abs(fault) * (3.2 + variant * 0.35))
        branch = _line(u * 0.74 - v * 0.29 + warp * f * 6.0, f * 7.0, 0.055)
        return _norm(np.maximum(crack, branch * 0.85))
    if grammar == "brush":
        hair = _line(u + warp * f * 2.0, f * (0.82 + variant * 0.08), 0.11)
        sweep = _line(u * 0.31 + v * 0.08 + warp * f * 8.0, f * 7.5, 0.16)
        cross = _line(v - warp * f * 1.2, f * (2.8 + variant * 0.3), 0.065)
        return _norm(hair * 0.52 + sweep * 0.30 + cross * 0.18)
    if grammar == "radial":
        cx = x - x.shape[1] * (0.34 + ((key >> 9) & 31) / 100.0)
        cy = y - y.shape[0] * (0.34 + ((key >> 14) & 31) / 100.0)
        radius = np.hypot(cx, cy)
        theta = np.arctan2(cy, cx)
        rays = _line(theta * f * (4.0 + variant), f, 0.09)
        rings = _line(radius + warp * f * 3.0, f * 2.7, 0.12)
        return _norm(rays * 0.62 + rings * 0.38)
    if grammar == "wave":
        wave = np.sin((v + np.sin(u / (f * 2.2)) * f * (2.0 + variant * 0.2) + warp * f * 3.0) / f * _TAU)
        cross = np.sin((u * 0.37 - v * 0.19) / (f * 1.8) * _TAU)
        return _norm(wave * 0.65 + cross * 0.25 + warp * 0.35)
    if grammar == "scale":
        row = np.floor(y / (f * 1.25))
        px = np.mod(x + np.mod(row, 2.0) * f, f * 2.0) - f
        py = np.mod(y, f * 1.25) - f * 0.62
        dist = np.sqrt((px / f) ** 2 + (py / (f * 0.72)) ** 2)
        rim = np.exp(-np.abs(dist - 0.78) * 15.0)
        keel = np.exp(-np.abs(px) / max(f * 0.14, 0.8)) * (dist < 0.82)
        return _norm(rim * 0.70 + keel * 0.30 + warp * 0.16)
    if grammar == "circuit":
        gx = _line(u, f * 3.4, 0.085)
        gy = _line(v, f * 4.1, 0.085)
        gate = (_hash_field(np.floor(u / (f * 3.4)), np.floor(v / (f * 4.1)), key + 23) > 0.48).astype(np.float32)
        pads = _dots(u, v, f * 6.8, f * 8.2, f * 0.48)
        return _norm((gx * gate + gy * (1.0 - gate)) * 0.76 + pads * 0.62)
    if grammar == "fleck":
        rnd = _hash_field(np.floor(x / max(1.0, f * 0.28)), np.floor(y / max(1.0, f * 0.28)), key + 29)
        shard = np.clip((rnd - (0.74 - variant * 0.025)) * 4.8, 0.0, 1.0)
        streak = _line(u + warp * f * 3.0, f * 3.7, 0.055) * (rnd > 0.58)
        return _norm(shard * 0.72 + streak * 0.50 + warp * 0.12)
    if grammar == "wisps":
        lane = np.sin((u * 0.30 + v + warp * f * 10.0) / (f * 2.3) * _TAU) * 0.5 + 0.5
        veil = _smooth_noise(y.shape[0], x.shape[1], key + 31, max(12, int(f * 5)))
        return _norm(lane * veil + warp * 0.42)
    if grammar == "weld":
        band = np.mod(v + np.sin(u / (f * 5.0)) * f, f * 5.0) - f * 2.5
        bead_x = np.mod(u, f * 1.25) - f * 0.625
        bead = np.exp(-((bead_x / (f * 0.54)) ** 2 + (band / (f * 0.82)) ** 2) * 2.0)
        toe = np.exp(-np.abs(np.abs(band) - f * 0.88) / max(f * 0.12, 0.7))
        return _norm(bead * 0.78 + toe * 0.48 + warp * 0.12)
    if grammar == "rivet":
        dots = _dots(u, v, f * 3.8, f * 3.8, f * 0.58)
        inner = _dots(u, v, f * 3.8, f * 3.8, f * 0.28)
        return _norm(np.clip(dots - inner * 0.56, 0.0, 1.0) + inner * 0.38 + warp * 0.14)
    if grammar == "guilloche":
        cx, cy = x - x.shape[1] * 0.5, y - y.shape[0] * 0.5
        radius = np.hypot(cx, cy)
        theta = np.arctan2(cy, cx)
        rose = np.sin(radius / f * _TAU + np.sin(theta * (5 + variant)) * 3.0)
        lace = np.cos((u - v * 0.31) / (f * 1.2) * _TAU)
        return _norm(rose * 0.68 + lace * 0.32)
    if grammar == "droplet":
        px, py = f * (3.5 + variant * 0.3), f * 4.7
        outer = _dots(u, v, px, py, f * .78)
        inner = _dots(u, v, px, py, f * .46)
        ring = np.clip(outer - inner * .94, 0.0, 1.0)
        satellite = _dots(u + f * 1.2, v + f * 1.5, px, py, f * .23)
        trail = _line(u * 0.16 + v + warp * f * 4.0, f * 6.0, 0.055) * outer
        return _norm(ring * .70 + inner * .22 + satellite * .45 + trail * .42 + warp * .08)
    if grammar == "lattice":
        a = _line(u + v, f * 2.7, 0.10)
        b = _line(u - v, f * (2.5 + variant * 0.12), 0.10)
        nodes = np.minimum(1.0, a * b * 2.4)
        return _norm(a * 0.42 + b * 0.42 + nodes * 0.46 + warp * 0.12)
    if grammar == "bokeh":
        large = _dots(u, v, f * 6.2, f * 7.1, f * 1.55)
        small = _dots(u + f * 2.1, v + f * 1.6, f * 4.1, f * 4.7, f * 0.58)
        return _norm(large * 0.58 + small * 0.62 + warp * 0.16)
    if grammar == "rosette":
        outer = _dots(u, v, f * 2.4, f * 2.1, f * .62)
        inner = _dots(u, v, f * 2.4, f * 2.1, f * .34)
        satellite = _dots(u + f * .72, v + f * .58, f * 2.4, f * 2.1, f * .18)
        rings = np.clip(outer - inner * .92, 0.0, 1.0)
        return _norm(rings * .76 + inner * .22 + satellite * .48 + warp * .10)
    if grammar == "houndstooth":
        cell = max(f * 1.55, 2.0)
        ix = np.floor(u / cell)
        iy = np.floor(v / cell)
        lx = np.mod(u, cell) / cell
        ly = np.mod(v, cell) / cell
        parity = np.mod(ix + iy, 2.0)
        tooth = ((lx + ly * .62) > (.72 + parity * .10)).astype(np.float32)
        spur = ((lx < .26) & (ly > .48) & (parity < .5)).astype(np.float32)
        return _norm(np.maximum(tooth, spur) * .84 + warp * .16)
    if grammar == "claw":
        bend = np.sin(v / max(f * 2.8, 1.0)) * f * .55 + warp * f * 1.4
        strokes = np.maximum.reduce([
            _line(u + bend + offset * f * .62, f * 5.2, .075)
            for offset in (-1.0, 0.0, 1.0)
        ])
        segment = (np.mod(v + np.floor(u / max(f * 5.2, 1.0)) * f * 2.1,
                          f * 7.4) < f * 3.1).astype(np.float32)
        puncture = _dots(u + f * 1.1, v + f * .7, f * 5.2, f * 7.4, f * .28)
        return _norm(strokes * segment * .82 + puncture * .48 + warp * .12)
    if grammar == "chevron":
        period = f * 5.0
        fold = np.abs(np.mod(u, period) - period * .5)
        phase = v + fold * (.72 + variant * .035) + warp * f * 1.5
        band = _line(phase, f * 2.45, .18)
        seam = _line(phase + f * .62, f * 2.45, .055)
        rivet = _dots(u + f * .8, v + f * .4, f * 5.0, f * 4.9, f * .22)
        return _norm(band * .68 + seam * .44 + rivet * .38 + warp * .10)

    # Organic/fallback: cellular currents with fine contour ridges.
    flow = np.sin((u + warp * f * 9.0) / (f * 2.7) * _TAU)
    flow += np.cos((v - warp * f * 6.0) / (f * (3.2 + variant * 0.2)) * _TAU)
    contours = np.exp(-np.abs(flow) * 2.8)
    return _norm(contours * 0.72 + warp * 0.38)


def _dots(x: np.ndarray, y: np.ndarray, px: float, py: float, radius: float) -> np.ndarray:
    dx = np.mod(x + px * 0.5, max(px, 1.0)) - px * 0.5
    dy = np.mod(y + py * 0.5, max(py, 1.0)) - py * 0.5
    dist = np.hypot(dx, dy)
    return np.clip(1.0 - dist / max(radius, 1.0), 0.0, 1.0).astype(np.float32)


_GRAMMAR_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("weld",), "weld"),
    (("panel_fade",), "brush"),
    (("chevron_bands",), "chevron"),
    (("claw",), "claw"),
    (("scratch",), "brush"),
    (("hornet", "swarm"), "fleck"),
    (("jaguar", "leopard", "rosette"), "rosette"),
    (("houndstooth",), "houndstooth"),
    (("mandala", "sunray", "sunburst", "firework", "starfield", "sigil"), "radial"),
    (("damascus", "marble", "seigaiha"), "wave"),
    (("diffraction", "grating", "louver", "slot", "corridor"), "brush"),
    (("rain", "drip", "droplet", "clay", "roost", "spray", "bead_aero"), "droplet"),
    (("guilloche", "moire", "engine_turn", "jeweling", "ouija", "veve", "ritual", "rune"), "guilloche"),
    (("carbon", "kevlar", "nomex", "fiberglass", "weave", "braid", "textile", "tow"), "weave"),
    (("fracture", "fractured", "crack", "shatter", "kintsugi", "crackle", "rift"), "fracture"),
    (("hex", "honeycomb", "cell", "mesh", "chainmail", "lattice"), "hex"),
    (("brushed", "grain", "polish", "scratch", "linear", "waterjet", "sandblast"), "brush"),
    (("radial",), "radial"),
    (("ripple", "wave", "caustic", "liquid", "oil", "fuel", "wet", "pool"), "wave"),
    (("scale", "scute", "armor", "pangolin", "alligator", "croc", "snake", "fish", "shark"), "scale"),
    (("circuit", "microbar", "laser", "grid", "architectural", "binary", "pixel"), "circuit"),
    (("sparkle", "flake", "dust", "stardust", "glass", "pearl", "shimmer", "confetti"), "fleck"),
    (("cloud", "smoke", "soot", "fog", "haze", "mist"), "wisps"),
    (("rivet", "bolt", "dimple", "bead", "sinter", "pebble"), "rivet"),
    (("diamond", "knurl", "checker", "chevron", "brick", "panel"), "lattice"),
    (("bokeh", "orb", "bubble", "dew"), "bokeh"),
)

_GRAMMARS = ("weave", "hex", "fracture", "brush", "radial", "wave", "scale", "circuit",
             "fleck", "wisps", "weld", "rivet", "guilloche", "droplet", "lattice", "bokeh",
             "rosette", "houndstooth", "claw", "chevron", "organic")


def _grammar_for(pid: str, key: int) -> str:
    semantic = semantic_archetype(pid)
    if semantic is not None:
        return semantic
    low = pid.lower()
    for tokens, grammar in _GRAMMAR_RULES:
        if any(token in low for token in tokens):
            return grammar
    return _GRAMMARS[key % len(_GRAMMARS)]


def _material_for(pid: str, key: int) -> str:
    low = pid.lower()
    words = tuple(word for word in re.split(r"[^a-z0-9]+", low) if word)

    def has(*tokens: str) -> bool:
        return any(any(word == token or word.startswith(token) for word in words) for token in tokens)

    if has("fracture", "crack", "shatter", "rift", "broken", "battle", "kintsugi"):
        return "fractured"
    if has("holo", "prism", "iridescent", "diffraction", "anodized", "optical",
           "chameleon", "rainbow", "pearl", "abalone", "pvd", "colorflip"):
        return "optical"
    if low.startswith("cc_") or has("clear", "gloss", "wet", "oil", "fuel", "rain", "dew", "resin",
                                      "liquid", "pool", "wax", "halo", "overspray"):
        return "gloss"
    if has("carbon", "kevlar", "nomex", "fiberglass", "rubber", "textile", "weave",
           "burlap", "hose", "tire", "cord", "braid"):
        return "composite"
    if has("mud", "soot", "dust", "rust", "tar", "grime", "aged", "salt", "corrosion",
           "burnt", "exhaust", "patina", "erosion", "clay"):
        return "weathered"
    if has("matte", "flat", "powder", "ceramic", "sinter", "noir", "shadow", "graphite"):
        return "flat"
    if has("chrome", "metal", "steel", "titanium", "billet", "weld", "rivet", "bolt",
           "knurl", "aluminum", "galvanic", "guilloche", "edm", "solder"):
        return "chrome"
    if has("satin", "velvet", "emboss", "vinyl", "haze", "fog"):
        return "satin"
    return ("chrome", "gloss", "satin", "flat", "fractured", "optical", "composite", "weathered")[key % 8]


_PALETTES: dict[str, tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]] = {
    "chrome": (
        (.72, .94, .82, .99, .66, .90, .04, .78),
        (.18, .04, .12, .01, .26, .08, .98, .16),
        (.44, .86, .62, .98, .34, .76, .02, .92),
    ),
    "gloss": (
        (.04, .16, .08, .30, .12, .48, .92, .24),
        (.22, .04, .14, .01, .32, .08, .98, .18),
        (.58, .88, .72, .99, .46, .82, .02, .94),
    ),
    "satin": (
        (.02, .14, .06, .24, .10, .42, .94, .30),
        (.76, .48, .66, .34, .58, .26, .02, .88),
        (.04, .22, .10, .38, .16, .54, .96, .30),
    ),
    "flat": (
        (.01, .08, .03, .16, .06, .28, .94, .12),
        (.99, .88, .96, .80, .92, .70, .04, .84),
        (.01, .05, .02, .10, .04, .18, .96, .08),
    ),
    "fractured": (
        (.03, .38, .12, .66, .22, .88, .99, .48),
        (.98, .44, .76, .12, .60, .28, .02, .84),
        (.02, .42, .14, .74, .26, .92, .99, .56),
    ),
    "optical": (
        (.02, .68, .18, .94, .34, .80, .50, .99),
        (.96, .20, .72, .02, .52, .34, .10, .84),
        (.10, .88, .38, .99, .22, .72, .54, .01),
    ),
    "composite": (
        (.02, .18, .06, .34, .10, .52, .98, .26),
        (.94, .42, .76, .16, .62, .28, .02, .54),
        (.04, .56, .18, .82, .30, .70, .99, .44),
    ),
    "weathered": (
        (.01, .10, .04, .18, .30, .46, .98, .22),
        (.99, .84, .94, .72, .88, .60, .02, .78),
        (.01, .06, .03, .12, .20, .34, .96, .16),
    ),
}


def _render(pid: str, shape: tuple[int, ...], seed: int, sm: float, params: Mapping[str, object]) -> np.ndarray:
    h, w = int(shape[0]), int(shape[1])
    if sm < 0.001:
        return np.full((h, w, 3), 0.5, dtype=np.float32)
    wh, ww, _factor = _work_shape(shape)
    x, y = _coords(wh, ww)
    key = _stable(pid) ^ ((int(seed) * 0x9E3779B185EBCA87) & 0xFFFFFFFFFFFFFFFF)
    grammar = _grammar_for(pid, key)
    material = _material_for(pid, key)
    variant = int((key >> 11) % 5)
    target_feature = float(np.clip((8.0 + float((key >> 19) % 25)) * _feature_multiplier(params), 8.0, 32.0))
    # The owner's 8-32 px doctrine is expressed at the 2048 car canvas, not
    # at whatever thumbnail/audit resolution called the renderer.  Scale by
    # the bounded construction canvas so 96/192 previews retain the same
    # physical frequency instead of inflating motifs into false macro blobs.
    feature = max(1.25, target_feature * max(wh, ww) / 2048.0)
    angle = float((key >> 27) % 24) * math.pi / 24.0
    angle_override = _numeric_param(params, "angle_deg")
    if angle_override is not None:
        angle = math.radians(angle_override % 360.0)

    semantic_core = semantic_field(pid, x, y, feature, angle, key, variant)
    core = semantic_core if semantic_core is not None else _core_field(grammar, x, y, feature, angle, key, variant)
    if semantic_core is not None:
        # The semantic field itself owns all visible marks. Intentional loose
        # texture survives only inside archetypes explicitly declared as
        # particulate/surface; clean subjects receive no generic decoration.
        assert semantic_texture_policy(pid) is not None
        fm, fr, fc = _semantic_channel_fields(core, angle)
        # Deconfetti tick 4: a few strongly one-directional subjects can make
        # two channels mathematical inverses/copies. A displaced relief of the
        # same named mask supplies a continuous embossed rim—never new noise.
        relief_shift = cv2.warpAffine(core, np.float32([[1, 0, 3], [0, 1, -2]]),
                                      (core.shape[1], core.shape[0]),
                                      flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        relief = _norm(np.abs(core - relief_shift))
        if pid in {
            "spec_lfr_capitol_veins", "spec_brick_mortar", "banded_rows",
            "wave_ripple", "galaxy_swirl", "spec_terracotta_ceramic_grid",
            "spec_tar_snake_sealant", "mojo_bag_grain", "spec_burn_hole_mesh",
            "dragon_scale_macro", "shogun_scale_brocade", "chevron_bands",
            "spec_shadow_diamond_mesh", "wave_bands", "spec_carbon_tow_spread",
            "spec_carbon_2x2_twill", "spec_kevlar_weave", "spec_armadillo_band_armor",
            "scorpion_ember_hex",
        }:
            fr = _norm(fr * .56 + relief * .44)
        if pid in {"spec_retroreflective", "halftone_print", "spec_lfr_corridor_sheen"}:
            fc = _norm(fc * .56 + relief * .44)
        if pid == "coffin_nail_rust":
            ru, rv = _rotate(x, y, angle)
            pw, ph = feature * 1.25, feature * 1.80
            dx = np.mod(ru + pw * .5, max(pw, 1.0)) - pw * .5
            dy = np.mod(rv + ph * .5, max(ph, 1.0)) - ph * .5
            nail_heads = np.clip(1.0 - np.hypot(dx, dy) / max(feature * .23, .7), 0.0, 1.0)
            fc = _norm(fc * .22 + nail_heads * .78)
    else:
        edge = _edge(core)
        grain = _hash_field(np.floor(x / max(1.0, feature * .20)), np.floor(y / max(1.0, feature * .20)), key + 101)
        fleck_cut = 0.76 - variant * 0.025
        density_override = _numeric_param(params, "density")
        if density_override is not None and density_override >= 0:
            density_unit = density_override if density_override <= 1.0 else density_override / 100.0
            fleck_cut = float(np.clip(.82 - density_unit * 1.4, .54, .82))
        flecks = np.clip((grain - fleck_cut) * 5.5, 0.0, 1.0)
        u, v = _rotate(x, y, angle + math.pi * 0.37)
        scratches = _line(u + (_smooth_noise(wh, ww, key + 103, max(8, int(feature * 4))) - .5) * feature * 3.0,
                          feature * (2.6 + variant * .35), .055)
        secondary_grammar = _GRAMMARS[(key >> 33) % len(_GRAMMARS)]
        if secondary_grammar == grammar:
            secondary_grammar = _GRAMMARS[(_GRAMMARS.index(grammar) + 7) % len(_GRAMMARS)]
        secondary = _core_field(secondary_grammar, x, y, feature * 0.72,
                                angle + math.pi * 0.23, key + 211, (variant + 2) % 5)
        fm = _norm(core * .68 + edge * .17 + secondary * .10 + flecks * .04 + scratches * .01)
        fr = _norm((1.0 - core) * .30 + scratches * .30 + edge * .20 + secondary * .10 + flecks * .06 + grain * .04)
        fc = _norm(edge * .48 + core * .34 + secondary * .08 + flecks * .05 + scratches * .05)
    im = np.minimum((fm * 8.0).astype(np.int16), 7)
    ir = np.minimum((fr * 8.0).astype(np.int16), 7)
    ic = np.minimum((fc * 8.0).astype(np.int16), 7)
    pm, pr, pc = (np.asarray(values, dtype=np.float32) for values in _PALETTES[material])
    # SPB-105 semantic correction / owner review 2026-07-13: semantic masks
    # need an ordered intensity ramp so their silhouette survives the eight
    # physical tiers.  The former shuffled lookup retained range but turned a
    # brick/checker/scale boundary into visual confetti.  Sorting keeps every
    # authored shade while making increasing field strength read coherently.
    lm, lr, lc = ((np.sort(pm), np.sort(pr), np.sort(pc))
                  if semantic_core is not None else (pm, pr, pc))
    out = np.empty((wh, ww, 3), dtype=np.float32)
    if semantic_core is not None:
        # Deconfetti tick 5: the eight authored tones are control points, not
        # hard posterization buckets. Continuous interpolation prevents three
        # channels from creating unrelated one-pixel color steps while keeping
        # the full material palette and substantially more than eight shades.
        stops = np.linspace(0.0, 1.0, 8, dtype=np.float32)
        out[:, :, 0] = np.interp(fm, stops, lm).astype(np.float32)
        out[:, :, 1] = np.interp(fr, stops, lr).astype(np.float32)
        out[:, :, 2] = np.interp(fc, stops, lc).astype(np.float32)
    else:
        out[:, :, 0] = lm[im]
        out[:, :, 1] = lr[ir]
        out[:, :, 2] = lc[ic]

    if semantic_core is not None:
        # Deconfetti tick 2: widen quiet channels by monotonic contrast around
        # their existing mean. This changes no pixels' structural ordering and
        # creates no new marks; it replaces the former sparse random extrema
        # with stronger visibility for the named geometry already present.
        for channel in range(3):
            plane = out[:, :, channel]
            for _ in range(3):
                std = float(plane.std())
                if not (1e-6 < std < .105):
                    break
                mean = float(plane.mean())
                plane = np.clip(mean + (plane - mean) * min(12.0, .11 / std), 0.0, 1.0)
            out[:, :, channel] = plane

    if semantic_core is None:
        # Hidden legacy renderers retain their historical exposure accents.
        # Picker-visible semantic overlays may show particulate marks only
        # when those marks are authored into the named subject field.
        accents = (
            _smooth_noise(wh, ww, key + 307, 4),
            _smooth_noise(wh, ww, key + 401, 4),
            _smooth_noise(wh, ww, key + 503, 4),
        )
        for channel, (palette, accent) in enumerate(zip((pm, pr, pc), accents)):
            out[:, :, channel] = np.where(accent < .003, float(palette.min()), out[:, :, channel])
            out[:, :, channel] = np.where(accent > .997, float(palette.max()), out[:, :, channel])

    if (wh, ww) != (h, w):
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    if abs(float(sm) - 1.0) > 1e-6:
        out = 0.5 + (out - 0.5) * float(np.clip(sm, 0.0, 1.0))
    return np.clip(out, 0.0, 1.0).astype(np.float32, copy=False)


def _make_renderer(pid: str) -> Callable[..., np.ndarray]:
    def renderer(shape, seed, sm, **kwargs):
        return _render(pid, tuple(shape), int(seed), float(sm), kwargs)

    renderer.__name__ = f"overhaul_{pid}"
    renderer.__qualname__ = renderer.__name__
    renderer.__doc__ = (
        f"SPB-105 five-round overhaul renderer for {pid}. "
        "Targets R=Metallic G=Roughness B=Clearcoat."
    )
    renderer._spb_concept_complete = True
    renderer._spb_overhaul_round = 5
    return renderer


def build_overhaul_catalog(existing_ids: Iterable[str]) -> dict[str, Callable[..., np.ndarray]]:
    """Return renderers for every id while preserving saved-paint aliases.

    Legacy ids intentionally share the canonical renderer object.  This keeps
    old paint recipes pixel-compatible with renamed picker entries instead of
    letting the legacy spelling perturb the deterministic material seed.
    """
    from engine.spec_pattern_aliases import SPEC_PATTERN_ALIASES

    ids = tuple(str(pid) for pid in existing_ids)
    canonical_renderers: dict[str, Callable[..., np.ndarray]] = {}
    result: dict[str, Callable[..., np.ndarray]] = {}
    for pid in ids:
        canonical = str(SPEC_PATTERN_ALIASES.get(pid, pid))
        renderer = canonical_renderers.setdefault(canonical, _make_renderer(canonical))
        result[pid] = renderer
    return result

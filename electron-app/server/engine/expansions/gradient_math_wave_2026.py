"""SPB-GRADIENT-MATH-2026-08-23 — bounded math fields for Gradient wave GM-1.

Owner verdict (2026-08-23): use the recently-created math functions to make the
new gradients more unique, with the prior direction to push gradients to
"extremes" still controlling the visual bar.  These are structural fields, not
palette swaps: every topology composes two orthogonal generators through a
warp, gate, phase fold, or ridge interaction.

Audit movement: the twelve proposed Gradient IDs moved from unregistered to
official M7 90.6-93.6 (12/12 >=85).  This module supplies their scalar topology
fields; registration, 10-15-stop ramps, paint/spec assembly, and fail-closed
bake evidence belong to the calling Gradient expansion.

Performance contract: no source is evaluated above 768 square working pixels
(the public hard ceiling is 1024), and expensive iterative engines are called
with reduced, authored budgets.  Final resize happens once after composition.

Morpho provenance: ``g_scales`` and ``g_nacre`` are private structural helpers
from ``fractured_morpho_2026``.  Their use is intentional and narrowly bounded:
they are deterministic scalar thickness generators, called at <=704 square,
cropped before resize to preserve the requested output aspect, and retuned to
~96 rows so their primary cells land around 8-32 px at native 2048.  No Morpho
registry or art/spec assembly is invoked.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable

import cv2
import numpy as np

from engine.expansions import fractured_morpho_2026 as _morpho
from engine.paint_v2 import fractured_math as _fractured
from engine.paint_v2.exotic_packs import pack_complex_dynamics as _complex
from engine.paint_v2.exotic_packs import pack_curves_harmonic as _curves
from engine.paint_v2.exotic_packs import pack_optical_material as _optical
from engine.paint_v2.exotic_packs import pack_physical_fields as _physical


MATH_TOPOLOGIES = (
    "domain_singularity",
    "nebulabrot_ionstorm",
    "superformula_starforge",
    "bismuth_chladni",
    "stable_ink_caustics",
    "electrostatic_ridges",
    "ferrofluid_gyroid",
    "viscous_schlieren",
    "scarab_cascade",
    "nacre_filament",
    "singularity_loom",
    "harmonic_cathedral",
)

MATH_DEPENDENCY_MODULES = (
    "engine.paint_v2.fractured_math",
    "engine.paint_v2.exotic_packs.pack_complex_dynamics",
    "engine.paint_v2.exotic_packs.pack_curves_harmonic",
    "engine.paint_v2.exotic_packs.pack_optical_material",
    "engine.paint_v2.exotic_packs.pack_physical_fields",
    "engine.expansions.fractured_morpho_2026",
)

# Machine-readable provenance for dependency hashing and fail-closed tests.
MATH_TOPOLOGY_SOURCES = {
    "domain_singularity": (
        "engine.paint_v2.exotic_packs.pack_complex_dynamics.domain_coloring",
        "engine.paint_v2.fractured_math.curl_flow",
    ),
    "nebulabrot_ionstorm": (
        "engine.paint_v2.exotic_packs.pack_complex_dynamics.nebulabrot_density",
        "engine.paint_v2.fractured_math.spectral_silk",
    ),
    "superformula_starforge": (
        "engine.paint_v2.exotic_packs.pack_curves_harmonic.superformula_field",
        "engine.paint_v2.fractured_math.interference",
    ),
    "bismuth_chladni": (
        "engine.paint_v2.exotic_packs.pack_optical_material.bismuth_terraces",
        "engine.paint_v2.fractured_math.chladni",
    ),
    "stable_ink_caustics": (
        "engine.paint_v2.exotic_packs.pack_physical_fields.stable_fluids_ink",
        "engine.paint_v2.fractured_math.caustics",
    ),
    "electrostatic_ridges": (
        "engine.paint_v2.exotic_packs.pack_physical_fields.electrostatic_equipotential",
        "engine.paint_v2.fractured_math.ridged_terrain",
    ),
    "ferrofluid_gyroid": (
        "engine.paint_v2.exotic_packs.pack_physical_fields.ferrofluid_spikes",
        "engine.paint_v2.fractured_math.gyroid",
    ),
    "viscous_schlieren": (
        "engine.paint_v2.exotic_packs.pack_physical_fields.viscous_fingering",
        "engine.paint_v2.exotic_packs.pack_physical_fields.schlieren_refraction",
    ),
    "scarab_cascade": (
        "engine.expansions.fractured_morpho_2026.g_scales",
        "engine.paint_v2.fractured_math.caustics",
    ),
    "nacre_filament": (
        "engine.expansions.fractured_morpho_2026.g_nacre",
        "engine.paint_v2.fractured_math.gabor_weave",
    ),
    "singularity_loom": (
        "engine.paint_v2.fractured_math.conformal_lattice",
        "engine.paint_v2.fractured_math.gabor_weave",
    ),
    "harmonic_cathedral": (
        "engine.paint_v2.fractured_math.harmonograph",
        "engine.paint_v2.fractured_math.chladni",
    ),
}

_WORK_CAP = 768

# GM-4 owner-eye correction after the first 178-card production bake.  The
# imported fields were mathematically distinct, but several exposed one-pixel
# orbit/noise residue that the 10-15-stop ramp amplified into the same RGB
# confetti surface.  These small work-grid sigmas land around 8-24 px after a
# native-2048 upscale: fine enough for the finish doctrine, broad enough for
# the buyer card to reveal the actual terraces/wells/fingers/scales/looms.
_TOPOLOGY_SMOOTH_SIGMA = {
    "domain_singularity": 0.7,
    "nebulabrot_ionstorm": 1.4,
    "superformula_starforge": 0.8,
    "bismuth_chladni": 1.1,
    "stable_ink_caustics": 1.0,
    "electrostatic_ridges": 0.8,
    "ferrofluid_gyroid": 0.8,
    "viscous_schlieren": 0.8,
    "scarab_cascade": 0.6,
    "nacre_filament": 0.7,
    "singularity_loom": 0.7,
    "harmonic_cathedral": 0.8,
}


def _seed(seed: int, label: str) -> int:
    """Stable 32-bit child seed; Python's process-randomized hash() is forbidden."""
    payload = f"{int(seed)}:{label}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8, person=b"SPB-GM-1").digest()
    return int.from_bytes(digest, "little") & 0xFFFFFFFF


def _norm(field: np.ndarray) -> np.ndarray:
    """Finite percentile stretch to float32 [0,1], robust to isolated singularities."""
    a = np.nan_to_num(np.asarray(field, dtype=np.float32), nan=0.0, posinf=1.0, neginf=0.0)
    lo, hi = np.percentile(a, (0.5, 99.5))
    span = float(hi - lo)
    if span < 1e-8:
        return np.zeros_like(a, dtype=np.float32)
    return np.clip((a - np.float32(lo)) / np.float32(span), 0.0, 1.0).astype(np.float32)


def _work_shape(h: int, w: int) -> tuple[int, int]:
    longest = max(h, w)
    if longest <= _WORK_CAP:
        return h, w
    scale = _WORK_CAP / float(longest)
    return max(1, int(round(h * scale))), max(1, int(round(w * scale)))


def _source_res(h: int, w: int, lo: int, hi: int) -> int:
    return max(int(lo), min(int(hi), max(h, w)))


def _edge(field: np.ndarray) -> np.ndarray:
    f = np.asarray(field, np.float32)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    return _norm(np.hypot(gx, gy))


def _warp_by(field: np.ndarray, driver: np.ndarray, strength: float) -> np.ndarray:
    """Curl-like remap: the driver changes the first field's geometry, not its color."""
    h, w = field.shape
    gy, gx = np.gradient(np.asarray(driver, np.float32))
    scale = float(np.percentile(np.hypot(gx, gy), 95.0)) + 1e-6
    gx = np.clip(gx / scale, -1.0, 1.0)
    gy = np.clip(gy / scale, -1.0, 1.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Perpendicular gradient behaves like a small incompressible displacement.
    map_x = np.clip(xx + gy * float(strength), 0.0, w - 1.0).astype(np.float32)
    map_y = np.clip(yy - gx * float(strength), 0.0, h - 1.0).astype(np.float32)
    return cv2.remap(np.asarray(field, np.float32), map_x, map_y, cv2.INTER_CUBIC)


def _mirror_repeat(field: np.ndarray, repeats_y: int, repeats_x: int) -> np.ndarray:
    """Densify a field through seamless mirrored repetition.

    This is used only where the source engine has an intentionally large hero
    (one injection, a 3-5-cell supershape grid, or a 7x7 pole lattice). Mirrored
    coordinates avoid tile seams while shrinking every primitive into the
    owner's 8-32 px native range; the orthogonal second field breaks symmetry.
    """
    source = np.asarray(field, np.float32)
    h, w = source.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    span_x = max(1.0, float(w - 1))
    span_y = max(1.0, float(h - 1))
    phase_x = np.mod(xx * float(repeats_x) * 2.0, span_x * 2.0)
    phase_y = np.mod(yy * float(repeats_y) * 2.0, span_y * 2.0)
    map_x = np.abs(phase_x - span_x).astype(np.float32)
    map_y = np.abs(phase_y - span_y).astype(np.float32)
    return cv2.remap(source, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def _phase_fold(a: np.ndarray, b: np.ndarray, cycles: float, coupling: float) -> np.ndarray:
    phase = np.mod(np.asarray(a, np.float32) * float(cycles)
                   + (np.asarray(b, np.float32) - 0.5) * float(coupling), 1.0)
    return (0.5 - 0.5 * np.cos(phase * np.float32(2.0 * np.pi))).astype(np.float32)


def _morpho_aspect(
    generator: Callable[..., np.ndarray],
    h: int,
    w: int,
    seed: int,
    **kwargs: float,
) -> np.ndarray:
    """Render a square Morpho thickness field, then crop (never stretch) to aspect."""
    sq = _source_res(h, w, 256, 704)
    square = np.asarray(generator(sq, int(seed), **kwargs), np.float32)
    aspect = w / float(h)
    if aspect > 1.0:
        crop_h = max(1, min(sq, int(round(sq / aspect))))
        y0 = (sq - crop_h) // 2
        crop = square[y0:y0 + crop_h, :]
    elif aspect < 1.0:
        crop_w = max(1, min(sq, int(round(sq * aspect))))
        x0 = (sq - crop_w) // 2
        crop = square[:, x0:x0 + crop_w]
    else:
        crop = square
    return _norm(cv2.resize(crop, (w, h), interpolation=cv2.INTER_CUBIC))


def _domain_singularity(h: int, w: int, seed: int) -> np.ndarray:
    res = _source_res(h, w, 256, 512)
    a = _complex.domain_coloring(h, w, _seed(seed, "domain"), res=res)
    b = _fractured.curl_flow(h, w, _seed(seed, "curl"), res=min(res, 448),
                             particles=28000, steps=30, step_len=1.35)
    # GM-4 owner-eye correction: the public scalar intentionally blends phase,
    # modulus and isolines for general use, but that blend looked like ordinary
    # heat-map geology through a 15-stop ramp.  Preserve it as fine relief while
    # routing color through explicit complex phase wheels.  A periodic rational
    # field creates dense zeros/poles; log-modulus supplies thin nested rings.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = xx / np.float32(max(w - 1, 1)) * np.float32(2.0 * np.pi)
    y = yy / np.float32(max(h - 1, 1)) * np.float32(2.0 * np.pi)
    kx = np.float32(11 + seed % 5)
    ky = np.float32(13 + (seed // 5) % 5)
    kp = np.float32(9 + (seed // 11) % 5)
    kq = np.float32(12 + (seed // 17) % 5)
    p1 = np.float32((_seed(seed, "domain-p1") % 6283) / 1000.0)
    p2 = np.float32((_seed(seed, "domain-p2") % 6283) / 1000.0)
    p3 = np.float32((_seed(seed, "domain-p3") % 6283) / 1000.0)
    p4 = np.float32((_seed(seed, "domain-p4") % 6283) / 1000.0)
    numerator = (np.sin(kx * x + p1)
                 + np.complex64(1j) * np.sin(ky * y + p2))
    denominator = (np.sin(kp * (x + y) * np.float32(0.5) + p3)
                   + np.complex64(1j)
                   * np.sin(kq * (x - y) * np.float32(0.5) + p4))
    value = numerator / (denominator + np.complex64(1e-3 + 1e-3j))
    phase = np.mod(np.angle(value) / np.float32(2.0 * np.pi) + 1.0, 1.0)
    log_modulus = np.log(np.abs(value) + np.float32(1e-4))
    modulus_rings = np.float32(0.5) + np.float32(0.5) * np.cos(
        log_modulus * np.float32(5.5)
    )
    source_relief = cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), 0.55)
    route = np.mod(
        phase + np.float32(0.060) * (modulus_rings - np.float32(0.5))
        + np.float32(0.022) * (source_relief - np.float32(0.5)),
        1.0,
    ).astype(np.float32)
    return _norm(_warp_by(route, b, 0.75))


def _nebulabrot_ionstorm(h: int, w: int, seed: int) -> np.ndarray:
    # Nebulabrot keeps its public orbit implementation, but a 288 grid contains
    # the same trajectory density at substantially lower raster cost.
    a = _complex.nebulabrot_density(h, w, _seed(seed, "nebulabrot"), res=288)
    b = _fractured.spectral_silk(h, w, _seed(seed, "silk"),
                                 res=_source_res(h, w, 192, 448), beta=2.35)
    density = np.log1p(np.clip(a, 0.0, 1.0) * 18.0) / np.log(19.0)
    # Orbit ridges, not the filled density body, are the visual primitive.
    broad_density = cv2.GaussianBlur(density, (0, 0), 4.2)
    orbit_ridges = _norm(
        np.float32(0.68) * np.maximum(density - broad_density, 0.0)
        + np.float32(0.32) * _edge(density)
    )
    ridge_floor, ridge_peak = np.percentile(orbit_ridges, (72.0, 99.5))
    orbit_ridges = np.power(
        np.clip(
            (orbit_ridges - np.float32(ridge_floor))
            / np.float32(max(float(ridge_peak - ridge_floor), 1e-6)),
            0.0, 1.0,
        ),
        np.float32(0.72),
    ).astype(np.float32)
    # GM-4 owner-eye correction: additive silk filled the fractal black, while
    # an attempted three-cell affine montage exposed its source rectangles.
    # Keep one mathematically truthful continuous orbit storm.  Thresholded
    # ridges carry its density and silk bends only those filaments; there is no
    # affine source rectangle, synthetic panel edge, or repeated hero.
    storm = orbit_ridges
    storm = _warp_by(storm, b, 1.1)
    return _norm(0.94 * storm + 0.06 * _edge(storm))


def _superformula_starforge(h: int, w: int, seed: int) -> np.ndarray:
    res = _source_res(h, w, 256, 512)
    a = _curves.superformula_field(h, w, _seed(seed, "superformula"), res=res)
    b = _fractured.interference(h, w, _seed(seed, "interference"),
                                sources=9, res=min(res, 480))
    # GM-4 / owner-eye repair (2026-08-24): the rejected production contact
    # repeated every oscillatory ring in ``a`` 16x, so the authored stars read
    # as RGB grit.  Build a literal Gielis signed-distance cell here instead;
    # the public superformula remains its fine forged relief and the recent
    # interference engine bends the complete silhouettes, never the palette.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Twelve work-grid pixels become 32 px at native 2048 after the bounded
    # 768-grid upscale: the maximum allowed primitive, never a macro star.
    pitch = np.float32(12.0)
    row = np.floor(yy / pitch)
    stagger_x = xx + np.mod(row, 2.0) * pitch * np.float32(0.5)
    col = np.floor(stagger_x / pitch)
    dx = np.mod(stagger_x, pitch) / pitch * np.float32(2.0) - np.float32(1.0)
    dy = np.mod(yy, pitch) / pitch * np.float32(2.0) - np.float32(1.0)

    # Five-, six-, and seven-point cells alternate deterministically.  A small
    # per-cell rotation breaks wallpaper repetition without breaking the star.
    cell_code = np.mod(col * 17.0 + row * 11.0 + float(seed & 255), 3.0)
    arms = np.float32(5.0) + cell_code
    rotation = (np.float32((seed % 360) * np.pi / 180.0)
                + np.sin(col * 1.71 + row * 2.17) * np.float32(0.28))
    radius = np.hypot(dx, dy)
    theta = np.arctan2(dy, dx) + rotation
    t1 = np.abs(np.cos(arms * theta / np.float32(4.0))) ** np.float32(1.70)
    t2 = np.abs(np.sin(arms * theta / np.float32(4.0))) ** np.float32(1.70)
    shape_radius = np.power(t1 + t2 + np.float32(1e-5), np.float32(-1.0 / 0.30))
    ratio = radius / (shape_radius * np.float32(0.88) + np.float32(1e-4))
    support = np.clip((np.float32(1.08) - ratio) / np.float32(0.16), 0.0, 1.0)
    interior = np.clip(np.float32(1.0) - ratio, 0.0, 1.0)
    outer_rim = np.exp(-((ratio - np.float32(0.84)) / np.float32(0.105)) ** 2)
    inner_rim = np.exp(-((ratio - np.float32(0.43)) / np.float32(0.14)) ** 2)

    # Source relief is deliberately low-amplitude and confined to the cells;
    # it supplies fine 8-32 px facets without turning the black forge gaps on.
    relief = cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), 2.2)
    # A stable per-cell bank gives each star a coherent 2-4-color identity.
    # The rejected version sent the complete 13-stop ramp through every star.
    cell_hash = np.mod(col * 37.0 + row * 53.0 + float(seed % 29), 9.0) / 8.0
    cell_bank = np.float32(0.12) + np.float32(0.70) * cell_hash
    stars = support * np.clip(
        cell_bank + np.float32(0.055) * np.power(interior, 0.72)
        + np.float32(0.13) * outer_rim + np.float32(0.055) * inner_rim
        + np.float32(0.035) * (relief - np.float32(0.5)),
        0.0,
        1.0,
    )
    driver = cv2.GaussianBlur(np.asarray(b, np.float32), (0, 0),
                              max(2.0, float(pitch) * 0.22))
    forged = _warp_by(stars, driver, min(2.4, float(pitch) * 0.10))
    return _norm(forged)


def _bismuth_chladni(h: int, w: int, seed: int) -> np.ndarray:
    res = _source_res(h, w, 256, 512)
    a = _optical.bismuth_terraces(h, w, _seed(seed, "bismuth"), res=res)
    b = _fractured.chladni(h, w, _seed(seed, "chladni"), res=min(res, 512), modes=7)
    # GM-4 owner-eye correction: nine native seeds produced a few enormous
    # white plates, while mirrored copies became a symmetric kaleidoscope.
    # Re-express the source's Chebyshev hopper math as dense, independently
    # rotated 32px-native cells.  Each crystal owns a local palette bank and
    # six fine ledge lips; public Bismuth remains the face relief and Chladni
    # only supplies a restrained quake warp.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    pitch = np.float32(12.0)
    row = np.floor(yy / pitch)
    col = np.floor(xx / pitch)
    dx = np.mod(xx, pitch) / pitch * np.float32(2.0) - np.float32(1.0)
    dy = np.mod(yy, pitch) / pitch * np.float32(2.0) - np.float32(1.0)
    cell_hash = np.mod(np.sin(col * 31.731 + row * 17.137 + float(seed % 113))
                       * 41917.371, 1.0).astype(np.float32)
    angle = (np.floor(cell_hash * np.float32(4.0)) * np.float32(np.pi / 4.0)
             + (cell_hash - np.float32(0.5)) * np.float32(0.18))
    ca, sa = np.cos(angle), np.sin(angle)
    rx = dx * ca - dy * sa
    ry = dx * sa + dy * ca
    cheb = np.maximum(np.abs(rx), np.abs(ry))
    support = np.clip((np.float32(0.96) - cheb) / np.float32(0.12), 0.0, 1.0)
    depth = np.clip(np.float32(1.0) - cheb, 0.0, 1.0)
    ledge_index = np.floor(depth * np.float32(6.0)) / np.float32(5.0)
    ledge_phase = np.mod(depth * np.float32(6.0), 1.0)
    ledge_lip = np.exp(-((ledge_phase - np.float32(0.08)) / np.float32(0.13)) ** 2)
    face_relief = cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), 3.2)
    bank = np.float32(0.10) + np.float32(0.68) * cell_hash
    crystal = support * np.clip(
        bank + np.float32(0.055) * ledge_index + np.float32(0.14) * ledge_lip
        + np.float32(0.035) * (face_relief - np.float32(0.5)),
        0.0, 1.0,
    )
    driver = cv2.GaussianBlur(np.asarray(b, np.float32), (0, 0), 4.0)
    return _norm(_warp_by(crystal, driver, 0.45))


def _stable_ink_caustics(h: int, w: int, seed: int) -> np.ndarray:
    a = _physical.stable_fluids_ink(h, w, _seed(seed, "ink"),
                                     res=_source_res(h, w, 144, 208), steps=32)
    b = _fractured.caustics(h, w, _seed(seed, "caustics"),
                            res=_source_res(h, w, 256, 480))
    ink = _warp_by(a, b, 8.0)
    return _norm(0.58 * ink + 0.27 * _phase_fold(ink, b, 3.5, 2.8) + 0.15 * _edge(b))


def _electrostatic_ridges(h: int, w: int, seed: int) -> np.ndarray:
    a = _physical.electrostatic_equipotential(h, w, _seed(seed, "electrostatic"),
                                               res=_source_res(h, w, 224, 416), charges=72)
    b = _fractured.ridged_terrain(h, w, _seed(seed, "ridges"),
                                  res=_source_res(h, w, 256, 480), octaves=6)
    bent = _warp_by(a, b, 2.2)
    ridge_gate = np.power(np.clip(b, 0.0, 1.0), 0.75)
    return _norm(0.70 * bent * (0.72 + 0.28 * ridge_gate)
                 + 0.18 * _edge(a) + 0.12 * b)


def _ferrofluid_gyroid(h: int, w: int, seed: int) -> np.ndarray:
    a = _physical.ferrofluid_spikes(h, w, _seed(seed, "ferrofluid"),
                                    res=_source_res(h, w, 224, 416))
    # GM-4 / owner-eye repair (2026-08-24): repeated full-source illumination
    # and a 72-cycle gyroid made every pixel compete for a ramp color.  A literal
    # fine hex Rosensweig lattice now owns the silhouette; the recent source
    # engine varies crown height and gyroid is only restrained liquid relief.
    b = _fractured.gyroid(h, w, _seed(seed, "gyroid"),
                          res=_source_res(h, w, 320, 560), scale=24.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Seeded sub-pitch offsets vary the physical crown placement, not merely
    # its fine relief, so adjacent generated versions cannot alias.
    xx = xx + np.float32((_seed(seed, "ferro-x") % 1000) / 1000.0 * 11.0)
    yy = yy + np.float32((_seed(seed, "ferro-y") % 1000) / 1000.0 * 9.526279)
    pitch = np.float32(11.0)  # 29 px at native 2048 (inside the 8-32 doctrine)
    row_pitch = pitch * np.float32(0.8660254)
    row = np.floor(yy / row_pitch)
    local_y = np.mod(yy, row_pitch) - row_pitch * np.float32(0.5)
    shifted_x = xx + np.mod(row, 2.0) * pitch * np.float32(0.5)
    col = np.floor(shifted_x / pitch)
    local_x = np.mod(shifted_x, pitch) - pitch * np.float32(0.5)
    hash_a = np.mod(np.sin(col * 12.9898 + row * 78.233 + float(seed % 97))
                    * 43758.5453, 1.0).astype(np.float32)
    hash_b = np.mod(np.sin(col * 39.3467 - row * 11.135 + float(seed % 71))
                    * 24634.6345, 1.0).astype(np.float32)
    local_x += (hash_a - np.float32(0.5)) * pitch * np.float32(0.24)
    local_y += (hash_b - np.float32(0.5)) * row_pitch * np.float32(0.20)
    width = pitch * (np.float32(0.40) + np.float32(0.10) * hash_b)
    radius = np.hypot(local_x, local_y) / width
    source_relief = cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), 4.5)
    height = np.exp(-(radius / np.float32(0.56)) ** 2)
    height *= (np.float32(0.68) + np.float32(0.32) * hash_a)
    height *= np.float32(0.82) + np.float32(0.18) * source_relief
    support = np.clip((np.float32(1.04) - radius) / np.float32(0.18), 0.0, 1.0)
    shoulder = np.exp(-((height - np.float32(0.34)) / np.float32(0.115)) ** 2)
    crown = np.exp(-((height - np.float32(0.64)) / np.float32(0.13)) ** 2)
    tip = np.power(height, np.float32(2.2))
    liquid_relief = cv2.GaussianBlur(np.asarray(b, np.float32), (0, 0), 1.8)
    crown_bank = np.float32(0.16) + np.float32(0.64) * hash_a
    shaped = support * np.clip(
        crown_bank + np.float32(0.055) * np.power(height, 0.82)
        + np.float32(0.10) * shoulder + np.float32(0.13) * crown
        + np.float32(0.07) * tip
        + np.float32(0.04) * (liquid_relief - np.float32(0.5)),
        0.0,
        1.0,
    )
    return _norm(shaped)


def _viscous_schlieren(h: int, w: int, seed: int) -> np.ndarray:
    a = _physical.viscous_fingering(h, w, _seed(seed, "viscous"), res=176, grow=2200)
    b = _physical.schlieren_refraction(h, w, _seed(seed, "schlieren"),
                                       res=_source_res(h, w, 224, 416))
    # GM-4 owner-eye correction: mirrored or stamped central injections both
    # became ringed islands.  Draw a deterministic multi-injection Saffman-
    # Taylor network instead: wandering trunks, secondary splits, tip droplets
    # and age-coded color banks, all 8-32px wide at native 2048.  The public
    # Laplacian solve supplies local growth-age relief and Schlieren bends the
    # fingers; neither becomes an additive background.
    rng = np.random.default_rng(_seed(seed, "viscous-sites"))
    growth = np.zeros((h, w), np.float32)
    growth_mask = np.zeros((h, w), np.float32)
    px_scale = max(0.5, min(h, w) / 768.0)
    # Density, never larger branches: even a buyer card receives 30 irregular
    # injections; native area scales to 42 while the 8-32px stroke widths stay.
    site_count = max(30, int(round(42.0 * h * w / float(768 * 768))))
    for site_index in range(site_count):
        cx = float(rng.uniform(0.03, 0.97) * w)
        cy = float(rng.uniform(0.03, 0.97) * h)
        arms = int(rng.integers(5, 10))
        base_bank = float(0.10 + 0.74 * ((site_index * 7 + seed) % 13) / 12.0)
        core_radius = max(2, int(round(rng.uniform(2.5, 4.0) * px_scale)))
        cv2.circle(growth_mask, (int(cx), int(cy)), core_radius, 1.0, -1, cv2.LINE_AA)
        cv2.circle(growth, (int(cx), int(cy)), core_radius, base_bank, -1, cv2.LINE_AA)
        for arm in range(arms):
            angle = (arm / float(arms) * 2.0 * np.pi
                     + rng.uniform(-0.22, 0.22))
            point = np.float32([cx, cy])
            steps = int(rng.integers(7, 13))
            width = max(2, int(round(rng.uniform(2.8, 4.6) * px_scale)))
            for step_index in range(steps):
                angle += float(rng.normal(0.0, 0.12))
                step_len = float(rng.uniform(2.4, 4.3) * px_scale)
                next_point = point + np.float32([
                    np.cos(angle) * step_len,
                    np.sin(angle) * step_len,
                ])
                p0 = tuple(np.rint(point).astype(np.int32))
                p1 = tuple(np.rint(next_point).astype(np.int32))
                value = float(np.clip(
                    base_bank + 0.11 * step_index / max(steps - 1, 1)
                    + 0.035 * np.sin(arm * 1.7 + step_index),
                    0.04, 0.96,
                ))
                cv2.line(growth_mask, p0, p1, 1.0, width, cv2.LINE_AA)
                cv2.line(growth, p0, p1, value, width, cv2.LINE_AA)
                if step_index in (3, 6) and rng.random() < 0.58:
                    side_angle = angle + float(rng.choice((-1.0, 1.0)) * rng.uniform(0.55, 0.92))
                    side_len = float(rng.uniform(5.0, 10.0) * px_scale)
                    side = next_point + np.float32([
                        np.cos(side_angle) * side_len,
                        np.sin(side_angle) * side_len,
                    ])
                    ps = tuple(np.rint(side).astype(np.int32))
                    cv2.line(growth_mask, p1, ps, 1.0, max(2, width - 1), cv2.LINE_AA)
                    cv2.line(growth, p1, ps, float(np.clip(value - 0.08, 0.04, 0.96)),
                             max(2, width - 1), cv2.LINE_AA)
                point = next_point
            tip_radius = max(2, int(round(rng.uniform(2.0, 3.4) * px_scale)))
            tip = tuple(np.rint(point).astype(np.int32))
            cv2.circle(growth_mask, tip, tip_radius, 1.0, -1, cv2.LINE_AA)
            cv2.circle(growth, tip, tip_radius, float(np.clip(base_bank + 0.14, 0.0, 1.0)),
                       -1, cv2.LINE_AA)
    source_age = cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), 2.0)
    growth = np.clip(
        growth + growth_mask * np.float32(0.045)
        * (source_age - np.float32(0.5)),
        0.0, 1.0,
    )
    growth = _warp_by(growth, b, 0.65)
    return _norm(growth)


def _scarab_cascade(h: int, w: int, seed: int) -> np.ndarray:
    source_sq = _source_res(h, w, 256, 704)
    rows = max(32, int(round(96.0 * source_sq / 704.0)))
    a = _morpho_aspect(_morpho.g_scales, h, w, _seed(seed, "scarab"),
                        rows=rows, aniso=1.22, rib=3.0, rib_amp=0.05, jit=0.34,
                        warp=1.4, prof=0.15, drift=0.22, rim=0.08)
    b = _fractured.caustics(h, w, _seed(seed, "scarab-caustics"),
                            res=_source_res(h, w, 256, 448))
    cascade = _warp_by(a, b, 0.6)
    return _norm(cascade)


def _nacre_filament(h: int, w: int, seed: int) -> np.ndarray:
    source_sq = _source_res(h, w, 256, 704)
    rows = max(32, int(round(96.0 * source_sq / 704.0)))
    a = _morpho_aspect(_morpho.g_nacre, h, w, _seed(seed, "nacre"),
                        rows=rows, aniso=1.75, mortar=0.16, jit=0.28,
                        wave=0.06, warp=1.8, fine=0.05)
    b = _fractured.gabor_weave(h, w, _seed(seed, "gabor"),
                               res=_source_res(h, w, 256, 512), threads=104)
    filament = _warp_by(a, b, 0.45)
    return _norm(0.94 * filament + 0.06 * _edge(a))


def _singularity_loom(h: int, w: int, seed: int) -> np.ndarray:
    a = _fractured.conformal_lattice(h, w, _seed(seed, "lattice"),
                                     res=_source_res(h, w, 320, 640))
    b = _fractured.gabor_weave(h, w, _seed(seed, "loom-weave"),
                               res=_source_res(h, w, 320, 560), threads=32)
    # GM-4 / owner-eye repair (2026-08-24): the old 72-thread source was mixed
    # with a 4x repeated pole lattice, collapsing both into colored moire.  The
    # loom now has explicit ribbon cross-sections and alternating over/under
    # occlusion.  Conformal singularities act only as a broad geometric warp;
    # Gabor weave contributes restrained fibre relief inside those ribbons.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    pitch = np.float32(12.0)  # 32 px maximum after the native-2048 upscale
    ux = np.abs(np.mod(xx / pitch, 1.0) - np.float32(0.5)) * np.float32(2.0)
    vy = np.abs(np.mod(yy / pitch, 1.0) - np.float32(0.5)) * np.float32(2.0)
    warp_mask = np.clip((np.float32(0.58) - ux) / np.float32(0.16), 0.0, 1.0)
    weft_mask = np.clip((np.float32(0.58) - vy) / np.float32(0.16), 0.0, 1.0)
    warp_profile = warp_mask * np.clip(
        np.float32(1.0) - (ux / np.float32(0.58)) ** 2, 0.0, 1.0
    )
    weft_profile = weft_mask * np.clip(
        np.float32(1.0) - (vy / np.float32(0.58)) ** 2, 0.0, 1.0
    )
    cell_x = np.floor(xx / pitch)
    cell_y = np.floor(yy / pitch)
    warp_over = np.mod(cell_x + cell_y + float(seed & 1), 2.0) < 1.0
    crossing = warp_mask * weft_mask
    warp_visible = warp_profile * (
        np.float32(1.0) - crossing * np.where(warp_over, 0.0, 0.78)
    )
    weft_visible = weft_profile * (
        np.float32(1.0) - crossing * np.where(warp_over, 0.78, 0.0)
    )
    ribbons = np.maximum(
        warp_visible * np.float32(0.82),
        weft_visible * np.float32(0.74),
    )
    top_glint = crossing * np.where(warp_over, warp_profile, weft_profile)
    ribbons = np.clip(np.float32(0.10) * np.maximum(warp_mask, weft_mask)
                      + ribbons + np.float32(0.14) * top_glint, 0.0, 1.0)

    lattice_driver = cv2.GaussianBlur(
        np.asarray(a, np.float32), (0, 0), max(3.0, min(h, w) / 44.0)
    )
    bend = min(5.0, float(pitch) * 0.22)
    loom = _warp_by(ribbons, lattice_driver, bend)
    fibre = _warp_by(cv2.GaussianBlur(np.asarray(b, np.float32), (0, 0), 1.4),
                     lattice_driver, bend)
    loom = loom * (np.float32(0.92) + np.float32(0.08) * fibre)
    return _norm(loom)


def _harmonic_cathedral(h: int, w: int, seed: int) -> np.ndarray:
    a = _fractured.harmonograph(h, w, _seed(seed, "harmonograph"),
                                res=_source_res(h, w, 320, 544), t_n=48000, curves=5)
    b = _fractured.chladni(h, w, _seed(seed, "cathedral-chladni"),
                           res=_source_res(h, w, 288, 512), modes=7)
    # Four non-identical rose windows provide hierarchy; Chladni only bends
    # their leadwork.  The prior 8x/3x multiplication looked like wallpaper and
    # erased the actual damped harmonograph curves.
    tracery = _mirror_repeat(a, 2, 2)
    tracery = _warp_by(tracery, b, 0.55)
    return _norm(0.86 * tracery + 0.10 * _edge(tracery) + 0.04 * _edge(b))


_BUILDERS: dict[str, Callable[[int, int, int], np.ndarray]] = {
    "domain_singularity": _domain_singularity,
    "nebulabrot_ionstorm": _nebulabrot_ionstorm,
    "superformula_starforge": _superformula_starforge,
    "bismuth_chladni": _bismuth_chladni,
    "stable_ink_caustics": _stable_ink_caustics,
    "electrostatic_ridges": _electrostatic_ridges,
    "ferrofluid_gyroid": _ferrofluid_gyroid,
    "viscous_schlieren": _viscous_schlieren,
    "scarab_cascade": _scarab_cascade,
    "nacre_filament": _nacre_filament,
    "singularity_loom": _singularity_loom,
    "harmonic_cathedral": _harmonic_cathedral,
}


def build_math_field(topology: str, h: int, w: int, seed: int) -> np.ndarray:
    """Build one deterministic structural field as float32 ``(h,w)`` in ``[0,1]``.

    Unknown topology names fail closed with ``KeyError``; non-positive dimensions
    fail with ``ValueError``.  Large requests are composed at bounded resolution
    and upsampled once, keeping a native-2048 Gradient inside the render budget.
    """
    if topology not in _BUILDERS:
        raise KeyError(f"unknown Gradient math topology: {topology!r}")
    h = int(h)
    w = int(w)
    if h <= 0 or w <= 0:
        raise ValueError(f"Gradient math field dimensions must be positive, got {(h, w)!r}")

    work_h, work_w = _work_shape(h, w)
    field = _norm(_BUILDERS[topology](work_h, work_w, int(seed)))
    sigma = _TOPOLOGY_SMOOTH_SIGMA[topology]
    field = _norm(cv2.GaussianBlur(field, (0, 0), sigma))
    if (work_h, work_w) != (h, w):
        field = cv2.resize(field, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(np.asarray(field, dtype=np.float32), 0.0, 1.0)


__all__ = (
    "MATH_TOPOLOGIES",
    "MATH_DEPENDENCY_MODULES",
    "MATH_TOPOLOGY_SOURCES",
    "build_math_field",
)

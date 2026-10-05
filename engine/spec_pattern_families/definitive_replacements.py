"""Definitive replacement spec overlays for the post-purge rebuild.

SPB definitive pass 2026-05-29.
Owner verdict snippet: "50 GREAT SPEC OVERLAYS... real world things
that would be good to spec out on cars... clean, detailed... UNIQUE."
Metric movement: new post-purge collection, audited in
SPEC_OVERLAY_DEFINITIVE_AUDIT.html before lock-in.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree

from ..spec_patterns import (
    _CV2_OK,
    _cv2,
    _flat,
    _normalize,
    _sm_scale,
    _spb_fast_smooth_noise,
    _validate_spec_output,
    multi_scale_noise,
)


DEFINITIVE_SPEC_OVERLAY_METADATA = [
    ("spec_weld_stack_rainbow", "Weld Stack Rainbow", "TIG bead stacks with blue-straw heat tint and crisp bead rims.", "Machined & Race Hardware", "weld"),
    ("spec_titanium_heat_fishscale", "Titanium Heat Fishscale", "Overlapping titanium heat scales with blue, violet, and gold oxide shifts.", "Fire, Heat & Exhaust", "fishscale"),
    ("spec_ceramic_brake_sinter", "Ceramic Brake Sinter", "Carbon-ceramic rotor pores, swept brake arcs, and hot dust glazing.", "Machined & Race Hardware", "sinter"),
    ("spec_billet_chamfer_facets", "Billet Chamfer Facets", "Small CNC chamfer plates with alternating polished faces.", "Machined & Race Hardware", "facets"),
    ("spec_safety_wire_twist", "Safety Wire Twist", "Twisted lockwire runs, clipped tails, and tiny race-shop loop knots.", "Machined & Race Hardware", "wire"),
    ("spec_diamond_plate_micro", "Micro Diamond Plate", "Fine raised diamond tread with crisp worn high edges.", "Machined & Race Hardware", "diamond"),
    ("spec_beadlock_bolt_circle", "Beadlock Bolt Circle", "Dense beadlock bolt heads, washer rings, and indexed circular rows.", "Machined & Race Hardware", "bolts"),
    ("spec_knurled_socket_grip", "Knurled Socket Grip", "Socket-tool diamond knurl and polished peak flecks.", "Machined & Race Hardware", "knurl"),
    ("spec_louvered_aluminum_slot", "Louvered Aluminum Slot", "Stamped aluminum louvers with dark slots and bright leading lips.", "Machined & Race Hardware", "louver"),
    ("spec_rivnut_grid", "Rivnut Grid", "Inset rivnuts, circular rims, and tiny mandrel scars.", "Machined & Race Hardware", "rivnuts"),
    ("spec_carbon_tow_spread", "Carbon Tow Spread", "Spread-tow carbon ribbons with rectangular fiber lanes.", "Carbon & Composite", "spread_tow"),
    ("spec_kevlar_blue_hybrid", "Kevlar Blue Hybrid", "Aramid-carbon hybrid weave with satin yellow and blue-black tow crossings.", "Carbon & Composite", "hybrid_weave"),
    ("spec_nomex_honeycomb_core", "Nomex Honeycomb Core", "Open honeycomb composite core with resin-wet cell edges.", "Carbon & Composite", "honeycomb"),
    ("spec_fiberglass_crossply", "Fiberglass Crossply", "Fine glass cross-ply cloth strands and clear resin flashes.", "Carbon & Composite", "crossply"),
    ("spec_prepreg_resin_bleed", "Prepreg Resin Bleed", "Prepreg pinholes, resin bleed lines, and glossy trapped clear.", "Carbon & Composite", "resin_bleed"),
    ("spec_braided_hose_sleeve", "Braided Hose Sleeve", "Braided stainless and aramid sleeve strands in diagonal over-under rows.", "Race Track Materials", "braid"),
    ("spec_rubber_tire_cord", "Rubber Tire Cord", "Exposed tire cord ribs, rubber scuffs, and satin black worn streaks.", "Race Track Materials", "tire_cord"),
    ("spec_tar_snake_sealant", "Tar Snake Sealant", "Track tar-seal strips with glossy raised asphalt snakes.", "Race Track Materials", "tar"),
    ("spec_rain_bead_aero", "Rain Bead Aero", "Wind-sheared rain beads and short aero trails under clearcoat.", "Race Track Materials", "rain"),
    ("spec_asphalt_aggregate_sharp", "Asphalt Aggregate Sharp", "Sharp asphalt aggregate stones, tar pockets, and polished high points.", "Race Track Materials", "aggregate"),
    ("spec_sharkskin_riblet", "Sharkskin Riblet", "Directional shark denticle riblets with tiny keel highlights.", "Predator & Animal Armor", "riblet"),
    ("spec_alligator_scute_plate", "Alligator Scute Plate", "Alligator scute armor plates, dark seams, and worn glossy crowns.", "Predator & Animal Armor", "scute"),
    ("spec_stingray_pearl_skin", "Stingray Pearl Skin", "Pebbled stingray leather pearls with glossy bead centers.", "Predator & Animal Armor", "pearl_skin"),
    ("spec_mantis_shrimp_shell", "Mantis Shrimp Shell", "Segmented iridescent shell armor with micro ridges.", "Predator & Animal Armor", "segmented_shell"),
    ("spec_armadillo_band_armor", "Armadillo Band Armor", "Layered armadillo armor bands with hard ridges and dusty valleys.", "Predator & Animal Armor", "armor_bands"),
    ("spec_abalone_crack_inlay", "Abalone Crack Inlay", "Abalone shard inlay with pearly islands and dark grout.", "Cultural & Inlay", "inlay"),
    ("spec_kintsugi_clear_crack", "Kintsugi Clear Crack", "Gold repair crack lines over ceramic clear with high metallic seams.", "Cultural & Inlay", "kintsugi"),
    ("spec_cloisonne_enamel_cell", "Cloisonne Enamel Cell", "Raised metal cloisonne wires around enamel color cells.", "Cultural & Inlay", "cloisonne"),
    ("spec_guilloche_watch_dial", "Guilloche Watch Dial", "Fine watch-dial guilloche waves and jeweled engraved cuts.", "Engine Turn & Optical", "guilloche"),
    ("spec_engine_turn_coin_scale", "Engine Turn Coin Scale", "Overlapping coin-scale engine turning with crisp circular grain.", "Engine Turn & Optical", "engine_turn"),
    ("spec_laser_etched_microbar", "Laser Etched Microbar", "Laser-etched micro bars, registration ticks, and satin burn marks.", "Engine Turn & Optical", "microbar"),
    ("spec_circuit_solder_mask", "Circuit Solder Mask", "PCB traces, solder pads, via rings, and gloss mask islands.", "Engine Turn & Optical", "circuit"),
    ("spec_heat_shield_dimple_foil", "Heat Shield Dimple Foil", "Dimpled foil heat shield with alternating bright cups and dull lows.", "Fire, Heat & Exhaust", "dimple_foil"),
    ("spec_exhaust_soot_gradient", "Exhaust Soot Gradient", "Layered exhaust soot, oxide specks, and brushed heat flow.", "Fire, Heat & Exhaust", "soot"),
    ("spec_flame_lapped_clearcoat", "Flame Lapped Clearcoat", "Kustom flame-lap clearcoat edges with glossy hotrod overlap ridges.", "Fire, Heat & Exhaust", "flame_lap"),
    ("spec_burnt_clutch_dust", "Burnt Clutch Dust", "Copper clutch dust, hot spots, and scorched friction streaks.", "Fire, Heat & Exhaust", "clutch_dust"),
    ("spec_ice_frost_feather", "Ice Frost Feather", "Frost fern crystals with sharp clearcoat feather branches.", "Weathered Physical", "frost"),
    ("spec_salt_crystal_track", "Salt Crystal Track", "Salt-flat crystal crust, tiny cubics, and chalky dry roughness.", "Weathered Physical", "salt"),
    ("spec_mud_crackle_dried", "Dried Mud Crackle", "Dried mud plates with clean cracks and dusty high shelves.", "Weathered Physical", "mud"),
    ("spec_red_clay_roost", "Red Clay Roost", "Red-clay roost flecks and angled dirt sling streaks.", "Weathered Physical", "clay_roost"),
    ("spec_oil_film_gasket", "Oil Film Gasket", "Thin rainbow oil film, gasket edge marks, and wet ring stains.", "Liquid & Clearcoat", "oilfilm"),
    ("spec_fuel_stain_evap_ring", "Fuel Stain Evap Ring", "Fuel evaporated rings, ghost halos, and clean solvent edge marks.", "Liquid & Clearcoat", "fuel_ring"),
    ("spec_clearcoat_orange_peel_pro", "Pro Orange Peel", "Professional clearcoat orange peel with uniform tiny domes.", "Liquid & Clearcoat", "orange_peel"),
    ("spec_polished_swirl_compound", "Polished Swirl Compound", "Buffing-compound swirl marks and hologram trails.", "Liquid & Clearcoat", "swirl"),
    ("spec_sandblasted_mask_edge", "Sandblasted Mask Edge", "Masked blast transitions, satin eroded grain, and sharp tape borders.", "Weathered Physical", "blast_edge"),
    ("spec_anodized_hex_fade", "Anodized Hex Fade", "Anodized hex panels with electric fade and polished cell lips.", "Engine Turn & Optical", "anodized_hex"),
    ("spec_powdercoat_microflake", "Powdercoat Microflake", "Fine powdercoat microflake embedded in satin enamel.", "Liquid & Clearcoat", "powder_flake"),
    ("spec_cracked_powdercoat_edge", "Cracked Powdercoat Edge", "Cracked powdercoat islands with chipped shiny exposed edges.", "Weathered Physical", "cracked_powder"),
    ("spec_wrinkle_black_engine_paint", "Wrinkle Black Engine Paint", "Wrinkle-black valve-cover paint with raised ridges and dry valleys.", "Race Track Materials", "wrinkle"),
    ("spec_waterjet_cut_edge", "Waterjet Cut Edge", "Waterjet kerf striations, garnet scoring, and cut-edge shimmer.", "Machined & Race Hardware", "waterjet"),
]


def _shape2(shape) -> tuple[int, int]:
    return tuple(shape[:2]) if len(shape) > 2 else tuple(shape)


def _base(shape, seed, lo=0.18, hi=0.46):
    h, w = _shape2(shape)
    if _CV2_OK and max(h, w) > 1024:
        # 2026-05-30 perf pass: this is only the smooth substrate under the
        # full-res geometry. Render it smaller and upscale so crisp detail stays
        # sharp while avoiding nine 2048 Gaussian blurs per definitive overlay.
        ds = 2
        small_shape = (max(256, h // ds), max(256, w // ds))
        small_scales = [max(0.75, 7.0 / ds), max(1.25, 19.0 / ds), max(2.0, 43.0 / ds)]
        n_small = _normalize(multi_scale_noise(small_shape, small_scales, [0.45, 0.34, 0.21], seed))
        n = _cv2.resize(n_small.astype(np.float32), (w, h), interpolation=_cv2.INTER_LINEAR)
    else:
        n = _normalize(multi_scale_noise((h, w), [7.0, 19.0, 43.0], [0.45, 0.34, 0.21], seed))
    return (lo + (hi - lo) * n).astype(np.float32)


def _finish(M, R, CC, sm, name):
    # 2026-06-13 perf: write channels directly into a preallocated float32
    # buffer instead of np.stack (which builds an intermediate) followed by a
    # redundant .astype copy (M/R/CC are already float32). Bit-identical.
    h, w = M.shape[:2]
    out = np.empty((h, w, 3), dtype=np.float32)
    out[:, :, 0] = M
    out[:, :, 1] = R
    out[:, :, 2] = CC
    np.clip(out, 0.0, 1.0, out=out)
    return _validate_spec_output(_sm_scale(out, sm), name)


def _safe_line(arr, p0, p1, val, width=1):
    if _CV2_OK:
        _cv2.line(arr, p0, p1, float(val), int(width), lineType=_cv2.LINE_AA)


def _disc(arr, center, radius, val, filled=True):
    if _CV2_OK:
        _cv2.circle(arr, center, max(1, int(radius)), float(val), -1 if filled else 1, lineType=_cv2.LINE_AA)


def _poly(arr, pts, val, fill=True):
    if _CV2_OK:
        p = np.asarray(pts, dtype=np.int32)
        if fill:
            _cv2.fillPoly(arr, [p], float(val), lineType=_cv2.LINE_AA)
        else:
            _cv2.polylines(arr, [p], True, float(val), 1, lineType=_cv2.LINE_AA)


def _grid_coords(w, h, step, jitter, rng):
    for y in np.arange(-step, h + step, step):
        for x in np.arange(-step, w + step, step):
            yield int(x + rng.uniform(-jitter, jitter)), int(y + rng.uniform(-jitter, jitter))


def _draw_lines(M, R, CC, rng, count, w, h, scale, angle=None, length=(8, 28), bright=True):
    for _ in range(count):
        cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
        a = float(angle if angle is not None else rng.uniform(0, math.tau)) + float(rng.normal(0, 0.08))
        ln = float(rng.uniform(*length) * scale)
        p0 = (int(cx - math.cos(a) * ln * 0.5), int(cy - math.sin(a) * ln * 0.5))
        p1 = (int(cx + math.cos(a) * ln * 0.5), int(cy + math.sin(a) * ln * 0.5))
        if bright:
            _safe_line(M, p0, p1, rng.uniform(0.55, 0.96))
            _safe_line(R, p0, p1, rng.uniform(0.06, 0.32))
            _safe_line(CC, p0, p1, rng.uniform(0.44, 0.94))
        else:
            _safe_line(M, p0, p1, rng.uniform(0.04, 0.24))
            _safe_line(R, p0, p1, rng.uniform(0.62, 0.96))
            _safe_line(CC, p0, p1, rng.uniform(0.10, 0.38))


def _overlay_dots(M, R, CC, rng, w, h, n, mode="metal"):
    ys = rng.integers(0, h, n)
    xs = rng.integers(0, w, n)
    if mode == "dark":
        M[ys, xs] = rng.uniform(0.02, 0.20, n)
        R[ys, xs] = rng.uniform(0.60, 0.96, n)
        CC[ys, xs] = rng.uniform(0.08, 0.32, n)
    elif mode == "clear":
        M[ys, xs] = rng.uniform(0.15, 0.45, n)
        R[ys, xs] = rng.uniform(0.04, 0.22, n)
        CC[ys, xs] = rng.uniform(0.76, 0.99, n)
    else:
        M[ys, xs] = rng.uniform(0.62, 0.98, n)
        R[ys, xs] = rng.uniform(0.05, 0.28, n)
        CC[ys, xs] = rng.uniform(0.24, 0.82, n)


# ---------------------------------------------------------------------------
# 2026-06-04 OWNER MAKE-UNIQUE / REDESIGN pass.
# These five styles previously SHARED generic branches (inlay<->kintsugi/
# cloisonne, braid<->tire_cord<->carbon tow, fuel_ring<->oilfilm, guilloche<->
# engine_turn) which is exactly why the owner flagged them as "too similar".
# Each now has its OWN dedicated builder so the motif/scale/structure is
# genuinely distinct. All keep [0,1], (h,w,3) [M,R,CC] and _finish()/_sm_scale.
# ---------------------------------------------------------------------------

def _dedicated_setup(public_id, shape, seed):
    h, w = _shape2(shape)
    rng = np.random.default_rng((int(seed) * 1009 + sum(ord(c) for c in public_id)) & 0xFFFFFFFF)
    mn = min(h, w)
    scale = max(mn / 2048.0, 0.25)
    s256 = max(mn / 256.0, 0.55)  # crisp car-scale unit (fine detail reads here)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    return h, w, rng, mn, scale, s256, yy, xx


def _build_abalone_crack_inlay(public_id, shape, seed, sm):
    """Paua / abalone shell: rainbow nacre PATCHES split by a sharp dark
    cracked-inlay seam network. Distinct from kintsugi (single gold seams) and
    cloisonne (regular cells) by its irregular shard mosaic + iridescent banding
    INSIDE each shard."""
    h, w, rng, mn, scale, s256, yy, xx = _dedicated_setup(public_id, shape, seed)
    # Voronoi-style shard id field from scattered seed points (the nacre patches).
    n_seed = max(8, int(34 * (mn / 256.0) ** 2))
    sx = rng.uniform(0, w, n_seed).astype(np.float32)
    sy = rng.uniform(0, h, n_seed).astype(np.float32)
    sphase = rng.uniform(0, math.tau, n_seed).astype(np.float32)
    sfreq = rng.uniform(0.05, 0.13, n_seed).astype(np.float32) / max(s256, 0.6)
    sangle = rng.uniform(0, math.pi, n_seed).astype(np.float32)
    # 2026-06-04 perf: replace the per-seed Voronoi python loop (n_seed full-canvas
    # passes, ~2k at 2048px) with one vectorized cKDTree k=2 query over the pixel
    # meshgrid. Same Euclidean nearest assignment -> identical owner/d1/d2 fields.
    sites = np.column_stack((sx, sy))  # (n_seed, 2) in (x, y)
    px = np.broadcast_to(xx, (h, w)).ravel()
    py = np.broadcast_to(yy, (h, w)).ravel()
    pts = np.column_stack((px, py)).astype(np.float32)
    tree = cKDTree(sites)
    dist, idx = tree.query(pts, k=2, workers=-1)  # dist sorted ascending per point
    owner = idx[:, 0].reshape(h, w).astype(np.int32)
    # downstream uses squared distances (d1,d2) -> square the returned distances.
    d1 = (dist[:, 0] ** 2).reshape(h, w).astype(np.float32)
    d2 = (dist[:, 1] ** 2).reshape(h, w).astype(np.float32)
    # Per-shard iridescent nacre: directional rainbow banding (M carries it).
    ca = np.cos(sangle[owner]); sa = np.sin(sangle[owner])
    proj = (xx * ca + yy * sa)
    band = 0.5 + 0.5 * np.sin(proj * sfreq[owner] * math.tau + sphase[owner])
    # nacre micro-shimmer: a soft sub-detail modulation (weighted only +-0.14/0.10),
    # so render it via the bounded-res fast path -> no big full-canvas Gaussians.
    nacre = _normalize(_spb_fast_smooth_noise((h, w), [2.0 * s256, 5.0 * s256], [0.6, 0.4], seed + 41))
    M = np.clip(0.30 + band * 0.55 + (nacre - 0.5) * 0.14, 0.0, 1.0).astype(np.float32)
    # Nacre is wet/glossy: high CC, low-ish R, with a rainbow-shimmer modulation.
    CC = np.clip(0.55 + band * 0.34 - (nacre - 0.5) * 0.10, 0.0, 1.0).astype(np.float32)
    R = np.clip(0.30 - band * 0.18 + (1.0 - band) * 0.10, 0.05, 0.85).astype(np.float32)
    # SHARP dark crack seams = the Voronoi ridge (where d1~d2) → thin grout.
    edge = (np.sqrt(d2) - np.sqrt(d1))
    seam_w = max(1.1 * s256, 0.9)
    seam = np.clip(1.0 - edge / seam_w, 0.0, 1.0)  # 1 on the seam, 0 inside shard
    seam = seam ** 2
    M = M * (1.0 - seam * 0.92)            # crack goes dark/matte
    R = np.clip(R + seam * 0.78, 0.0, 1.0)  # crack is rough grout
    CC = CC * (1.0 - seam * 0.88)
    # Tiny secondary hairline cracks branching off (fine inlay detail).
    if _CV2_OK:
        for _ in range(int(260 * (mn / 256.0) ** 2)):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            a = float(rng.uniform(0, math.tau)); ln = float(rng.uniform(4, 13) * s256)
            pts = [(cx, cy)]
            for k in range(3):
                a += float(rng.normal(0, 0.5))
                pts.append((pts[-1][0] + math.cos(a) * ln * 0.34, pts[-1][1] + math.sin(a) * ln * 0.34))
            for p0, p1 in zip(pts, pts[1:]):
                q0 = (int(p0[0]), int(p0[1])); q1 = (int(p1[0]), int(p1[1]))
                _safe_line(M, q0, q1, rng.uniform(0.02, 0.12))
                _safe_line(R, q0, q1, rng.uniform(0.72, 0.95))
                _safe_line(CC, q0, q1, rng.uniform(0.04, 0.16))
    return _finish(M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32), sm, public_id)


def _build_braided_hose_sleeve(public_id, shape, seed, sm):
    """Over-under braided metallic sleeve: two opposing diagonal cord families
    that visibly INTERLACE (checkerboard of which family is on top), each cord a
    rounded metallic strand with a center sheen highlight. Distinct from carbon
    tow (square lanes) and tire cord (parallel straight) by the woven cross."""
    h, w, rng, mn, scale, s256, yy, xx = _dedicated_setup(public_id, shape, seed)
    pitch = max(11.0 * s256, 5.0)          # cord pitch (fine but reads at car scale)
    a = math.radians(34.0)
    u = (xx * math.cos(a) + yy * math.sin(a))     # +diagonal cords
    v = (-xx * math.sin(a) + yy * math.cos(a))    # -diagonal cords
    pu = (u / pitch) % 1.0
    pv = (v / pitch) % 1.0
    # rounded cord cross-section profile (bright crown at center of each cord)
    crown_u = np.cos((pu - 0.5) * math.pi) ** 2
    crown_v = np.cos((pv - 0.5) * math.pi) ** 2
    # over-under: which family is on top alternates per cell of the lattice.
    cell = ((np.floor(u / pitch).astype(np.int32) + np.floor(v / pitch).astype(np.int32)) % 2)
    over_u = (cell == 0)
    top_crown = np.where(over_u, crown_u, crown_v)
    bot_crown = np.where(over_u, crown_v, crown_u)
    metal = np.clip(top_crown * 0.92 + bot_crown * 0.30, 0.0, 1.0).astype(np.float32)
    # gap shadow between cords (where neither crown is high) goes dark/rough.
    gap = (1.0 - np.maximum(crown_u, crown_v))
    M = np.clip(0.22 + metal * 0.66 - gap * 0.12, 0.0, 1.0)
    R = np.clip(0.62 - metal * 0.46 + gap * 0.22, 0.04, 0.95)
    CC = np.clip(0.30 + metal * 0.58 - gap * 0.10, 0.0, 1.0)
    # specular pinstripe down each top cord crest (the satin metallic sheen).
    sheen = (np.where(over_u, crown_u, crown_v) > 0.86)
    M[sheen] = np.clip(M[sheen] + 0.18, 0, 1)
    CC[sheen] = np.clip(CC[sheen] + 0.16, 0, 1)
    # subtle aramid fuzz so it is not perfectly synthetic.
    fuzz = _normalize(multi_scale_noise((h, w), [1.3 * s256, 3.0 * s256], [0.6, 0.4], seed + 53))
    M = (M + (fuzz - 0.5) * 0.06).astype(np.float32)
    R = (R + (fuzz - 0.5) * 0.06).astype(np.float32)
    return _finish(np.clip(M, 0, 1).astype(np.float32), np.clip(R, 0, 1).astype(np.float32),
                   np.clip(CC, 0, 1).astype(np.float32), sm, public_id)


def _build_rubber_tire_cord(public_id, shape, seed, sm):
    """Actual tire cord: dense PARALLEL rubberized ply cords — fine straight-ish
    fiber bundles running one direction, embedded in dark rubber, each bundle a
    twisted multi-filament strand. NOT a weave (that was the confusion)."""
    h, w, rng, mn, scale, s256, yy, xx = _dedicated_setup(public_id, shape, seed)
    a = math.radians(8.0)                  # nearly vertical ply, slight bias
    u = (xx * math.cos(a) + yy * math.sin(a))      # across the cords
    v = (-xx * math.sin(a) + yy * math.cos(a))     # along the cords
    cord_pitch = max(7.0 * s256, 3.5)      # tight parallel cords (fine)
    pu = (u / cord_pitch) % 1.0
    # rounded rubberized cord crown (bright sheen on each cord ridge)
    crown = np.cos((pu - 0.5) * math.pi) ** 2
    # twist: filaments inside a cord create a periodic bright/dark chevron along v
    twist = 0.5 + 0.5 * np.sin(v / max(2.6 * s256, 1.2) + np.floor(u / cord_pitch) * 1.7)
    # sharpen the cord crown so the parallel ply ridges read crisply.
    crown = np.clip((crown - 0.35) / 0.65, 0.0, 1.0)
    fiber = crown * (0.55 + 0.45 * twist)
    rubber = _normalize(multi_scale_noise((h, w), [2.0 * s256, 5.0 * s256, 12.0 * s256],
                                          [0.5, 0.32, 0.18], seed + 67))
    # Rubber matrix is dark & satin (low M, high R); cords are brighter rubber sheen.
    M = np.clip(0.14 + fiber * 0.62 + (rubber - 0.5) * 0.06, 0.0, 1.0).astype(np.float32)
    R = np.clip(0.70 - fiber * 0.50 + (rubber - 0.5) * 0.08, 0.08, 0.96).astype(np.float32)
    CC = np.clip(0.18 + fiber * 0.48, 0.0, 1.0).astype(np.float32)
    # worn rubber scuff streaks along the cord direction (satin black wear).
    if _CV2_OK:
        ca, sa = math.cos(a), math.sin(a)
        for _ in range(int(160 * (mn / 256.0) ** 2)):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            ln = float(rng.uniform(14, 46) * s256)
            p0 = (int(cx - sa * ln * 0.5), int(cy + ca * ln * 0.5))
            p1 = (int(cx + sa * ln * 0.5), int(cy - ca * ln * 0.5))
            _safe_line(M, p0, p1, rng.uniform(0.06, 0.20), width=1)
            _safe_line(R, p0, p1, rng.uniform(0.70, 0.94), width=1)
            _safe_line(CC, p0, p1, rng.uniform(0.08, 0.24), width=1)
    return _finish(M, R, CC, sm, public_id)


def _build_fuel_stain_evap_ring(public_id, shape, seed, sm):
    """Fuel evaporation TIDE-MARK rings: a handful of large concentric nested
    oily rings (where the puddle edge paused as it dried) with iridescent sheen
    between rings and a clean solvent-clean center. Intentional, not squiggles."""
    h, w, rng, mn, scale, s256, yy, xx = _dedicated_setup(public_id, shape, seed)
    n_stain = max(3, int(7 * (mn / 256.0) ** 2))
    # 2026-06-04 perf: at 2048 n_stain explodes to ~448 large smooth radial rings.
    # The rings are a soft low-frequency radial field, so we render the whole
    # overlay onto a capped buffer and cv2.resize up to the canvas (the slight
    # softening is invisible on these tide-mark gradients). CRITICALLY, n_stain
    # and every stain's geometry are still driven by the FINAL shape (count,
    # position, relative size), so the LOOK is unchanged -- only the rasterization
    # resolution drops. Small canvases (<=cap, incl. the 256 audit size) keep the
    # exact full-res path so their std/look is bit-for-bit identical.
    _CAP = 640
    if _CV2_OK and mn > _CAP:
        f = float(_CAP) / float(mn)              # geometry scale onto the buffer
        rh = max(1, int(round(h * f))); rw = max(1, int(round(w * f)))
    else:
        f = 1.0; rh, rw = h, w
    M = _base((rh, rw), int(seed) + 11, 0.30, 0.46)
    R = _base((rh, rw), int(seed) + 17, 0.34, 0.52)
    CC = _base((rh, rw), int(seed) + 23, 0.40, 0.60)
    ryy = np.arange(rh, dtype=np.float32)[:, None]
    rxx = np.arange(rw, dtype=np.float32)[None, :]
    tide_w = 1.4 * s256 * f                       # tide-line width in buffer pixels
    tide_pad = tide_w + 1.0
    for _ in range(n_stain):
        # RNG draws use the FULL-res w,h,s256 (same order/values as before) so the
        # stain set is identical; we then scale geometry by f onto the buffer.
        cx = float(rng.uniform(0.1 * w, 0.9 * w)) * f
        cy = float(rng.uniform(0.1 * h, 0.9 * h)) * f
        rmax = float(rng.uniform(38, 86) * s256) * f
        ax = float(rng.uniform(0.8, 1.25)); ay = float(rng.uniform(0.8, 1.25))
        rot = float(rng.uniform(0, math.pi))
        cr, sr = math.cos(rot), math.sin(rot)
        # bounding half-extents of the rotated ellipse (semi-axes rmax*ax, rmax*ay)
        # plus the tide-line/clip padding so `rad < rmax` and `|rad-rmax|<pad` fit.
        rmax_eff = rmax + tide_pad
        hx = math.sqrt((rmax_eff * ax * cr) ** 2 + (rmax_eff * ay * sr) ** 2)
        hy = math.sqrt((rmax_eff * ax * sr) ** 2 + (rmax_eff * ay * cr) ** 2)
        x0 = max(0, int(math.floor(cx - hx))); x1 = min(rw, int(math.ceil(cx + hx)) + 1)
        y0 = max(0, int(math.floor(cy - hy))); y1 = min(rh, int(math.ceil(cy + hy)) + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        Mb = M[y0:y1, x0:x1]; Rb = R[y0:y1, x0:x1]; CCb = CC[y0:y1, x0:x1]
        dx = (rxx[:, x0:x1] - cx); dy = (ryy[y0:y1, :] - cy)
        rx = (dx * cr + dy * sr) / ax
        ry = (-dx * sr + dy * cr) / ay
        rad = np.sqrt(rx * rx + ry * ry)
        within = rad < rmax
        # nested tide-mark rings: ring count grows with size, rings darker/oilier.
        n_rings = max(4.0, rmax / (5.5 * s256 * f))
        ring_phase = rad / rmax * n_rings
        ring = 0.5 + 0.5 * np.cos(ring_phase * math.tau)
        edge_emph = np.clip(rad / rmax, 0, 1) ** 1.5  # rings stronger toward outer tide line
        oily = ring * edge_emph
        # iridescent fuel sheen between rings (rainbow modulation in M).
        irid = 0.5 + 0.5 * np.sin(ring_phase * math.tau * 2.1 + rad * (0.05 / f))
        m_add = (oily * 0.50 + irid * edge_emph * 0.20)
        Mb[:] = np.where(within, np.clip(Mb + m_add, 0, 1), Mb)
        CCb[:] = np.where(within, np.clip(CCb + oily * 0.40 + 0.10, 0, 1), CCb)
        Rb[:] = np.where(within, np.clip(Rb - oily * 0.18 + (1.0 - edge_emph) * 0.05, 0.04, 1), Rb)
        # crisp bright solvent-clean outer tide line (the final evaporation ring).
        tide = np.abs(rad - rmax) < tide_w
        tw = tide & within
        Mb[tw] = np.clip(Mb[tw] + 0.30, 0, 1)
        CCb[tw] = np.clip(CCb[tw] + 0.26, 0, 1)
    if (rh, rw) != (h, w):
        M = _cv2.resize(M, (w, h), interpolation=_cv2.INTER_LINEAR)
        R = _cv2.resize(R, (w, h), interpolation=_cv2.INTER_LINEAR)
        CC = _cv2.resize(CC, (w, h), interpolation=_cv2.INTER_LINEAR)
    return _finish(M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32), sm, public_id)


def _build_guilloche_watch_dial(public_id, shape, seed, sm):
    """Luxury watch-dial guilloche: FINE crisp engine-turning. A single dial
    center with very tight concentric circular waves PLUS a radial rose-engine
    petal modulation, like clous-de-Paris / barleycorn engraving. Fine, crisp,
    high frequency — reads as a watch dial, not soft cosine blobs."""
    h, w, rng, mn, scale, s256, yy, xx = _dedicated_setup(public_id, shape, seed)
    cx = w * 0.5 + float(rng.uniform(-0.05, 0.05)) * w
    cy = h * 0.5 + float(rng.uniform(-0.05, 0.05)) * h
    dx = (xx - cx); dy = (yy - cy)
    rad = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)
    # FINE but clean concentric engraving — the dominant dial hallmark. Pitch is
    # tight enough to read as engine-turning but not so tight it aliases to mush.
    ring_pitch = max(3.6 * s256, 1.6)
    # rose-engine barleycorn wobble: a LOW petal count gives the classic gentle
    # guilloche flower, not high-frequency static. Amplitude is modest so the
    # concentric rings stay clearly readable as a watch dial.
    petals = float(rng.choice([12, 16, 20, 24]))
    rose = (0.30 * ring_pitch) * np.sin(ang * petals)
    track = np.sin((rad + rose) / ring_pitch * math.tau)
    engrave = 0.5 + 0.5 * track
    # sharpen the engraving so grooves are crisp V-cuts (not soft cosine).
    engrave = np.clip((engrave - 0.5) * 1.7 + 0.5, 0.0, 1.0)
    # a second, much finer co-axial micro-track for jeweled depth (very fine).
    micro = 0.5 + 0.5 * np.sin(rad / max(1.4 * s256, 0.8) * math.tau)
    engrave = np.clip(engrave * 0.82 + micro * 0.18, 0.0, 1.0)
    # subtle global radial darkening toward rim (dial vignette).
    vig = 1.0 - np.clip(rad / (0.62 * min(h, w)), 0, 1) * 0.18
    M = np.clip(0.28 + engrave * 0.56 * vig, 0.0, 1.0).astype(np.float32)
    R = np.clip(0.58 - engrave * 0.40, 0.06, 0.95).astype(np.float32)
    CC = np.clip(0.34 + engrave * 0.54 * vig, 0.0, 1.0).astype(np.float32)
    # fine jeweled chapter-ring ticks around the dial (crisp index marks).
    if _CV2_OK:
        n_tick = 60
        rr = 0.46 * min(h, w)
        for k in range(n_tick):
            t = math.tau * k / n_tick
            big = (k % 5 == 0)
            r0 = rr * (0.90 if big else 0.94)
            r1 = rr
            p0 = (int(cx + math.cos(t) * r0), int(cy + math.sin(t) * r0))
            p1 = (int(cx + math.cos(t) * r1), int(cy + math.sin(t) * r1))
            _safe_line(M, p0, p1, 0.96, width=2 if big else 1)
            _safe_line(CC, p0, p1, 0.92, width=2 if big else 1)
            _safe_line(R, p0, p1, 0.06, width=2 if big else 1)
    return _finish(M, R, CC, sm, public_id)


_DEDICATED_BUILDERS = {
    "inlay": _build_abalone_crack_inlay,
    "braid": _build_braided_hose_sleeve,
    "tire_cord": _build_rubber_tire_cord,
    "fuel_ring": _build_fuel_stain_evap_ring,
    "guilloche": _build_guilloche_watch_dial,
}


def _render(style, public_id, shape, seed, sm):
    h, w = _shape2(shape)
    if sm < 0.001:
        return _flat((h, w))
    # 2026-06-04 owner make-unique/redesign: these styles now have dedicated,
    # genuinely distinct builders instead of sharing generic family branches.
    builder = _DEDICATED_BUILDERS.get(style)
    if builder is not None:
        return builder(public_id, shape, seed, sm)
    rng = np.random.default_rng((int(seed) * 1009 + sum(ord(c) for c in public_id)) & 0xFFFFFFFF)
    mn = min(h, w)
    scale = max(mn / 2048.0, 0.25)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]

    M = _base((h, w), int(seed) + 11, 0.18, 0.40)
    R = _base((h, w), int(seed) + 17, 0.42, 0.70)
    CC = _base((h, w), int(seed) + 23, 0.22, 0.54)

    if style in {"weld", "fishscale", "engine_turn", "guilloche"}:
        period = max(18.0 * scale, 5.0)
        if style == "weld":
            for y in np.arange(-period, h + period, period * 1.8):
                for x in np.arange(-period, w + period, period * 1.2):
                    r = max(2, int(rng.uniform(4.0, 8.5) * scale))
                    _disc(M, (int(x), int(y + math.sin(x * 0.02) * period)), r, rng.uniform(0.62, 0.98))
                    _disc(R, (int(x), int(y + math.sin(x * 0.02) * period)), r, rng.uniform(0.06, 0.26))
                    _disc(CC, (int(x), int(y + math.sin(x * 0.02) * period)), r, rng.uniform(0.42, 0.92))
            _draw_lines(M, R, CC, rng, int(650 * (mn / 512) ** 2), w, h, scale, angle=0.15, length=(10, 26))
        elif style == "fishscale":
            for y in np.arange(0, h + period, period * 0.72):
                off = period * 0.5 if int(y / period) % 2 else 0
                for x in np.arange(-period, w + period, period):
                    cx, cy = int(x + off), int(y)
                    _cv2.ellipse(M, (cx, cy), (int(period * .42), int(period * .22)), 0, 190, 350, float(rng.uniform(.56, .94)), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (cx, cy), (int(period * .42), int(period * .22)), 0, 190, 350, float(rng.uniform(.08, .34)), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (int(period * .42), int(period * .22)), 0, 190, 350, float(rng.uniform(.42, .96)), 1, lineType=_cv2.LINE_AA)
        else:
            centers = [(w * .18, h * .2), (w * .5, h * .52), (w * .82, h * .78)]
            field = np.zeros((h, w), np.float32)
            for cx, cy in centers:
                r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
                field = np.maximum(field, (np.cos(r / max(1.2 * scale, .6)) * .5 + .5) * (1 - np.clip(r / (260 * scale), 0, 1)))
            M = np.maximum(M, field * .86)
            R = np.minimum(R, .72 - field * .52)
            CC = np.maximum(CC, field * .72)
            _draw_lines(M, R, CC, rng, int(520 * (mn / 512) ** 2), w, h, scale, length=(7, 18))

    elif style in {"diamond", "knurl", "honeycomb", "riblet", "louver", "rivnuts", "bolts", "dimple_foil", "anodized_hex"}:
        pitch = max(14.0 * scale, 4.0)
        if style in {"diamond", "knurl"}:
            d1 = np.abs(((xx + yy) / pitch) % 1 - .5)
            d2 = np.abs(((xx - yy) / pitch) % 1 - .5)
            ridge = ((d1 < .055) | (d2 < .055)).astype(np.float32)
            M = np.maximum(M, .32 + ridge * .58)
            R = np.minimum(R, .66 - ridge * .50)
            CC = np.maximum(CC, .30 + ridge * .52)
        elif style in {"honeycomb", "anodized_hex"}:
            qx = np.mod(xx + ((yy // (pitch * .86)) % 2) * pitch * .5, pitch)
            qy = np.mod(yy, pitch * .86)
            edge = ((qx < 1.6 * scale) | (qy < 1.4 * scale) | (np.abs(qx - qy * .58) < 1.4 * scale)).astype(np.float32)
            M = np.maximum(M, .24 + edge * .64)
            R = np.minimum(R, .68 - edge * .52)
            CC = np.maximum(CC, .28 + edge * .55)
        elif style == "riblet":
            rid = (np.cos((xx + yy * .12) / max(2.8 * scale, 1.0)) * .5 + .5) ** 8
            M = np.maximum(M, .18 + rid * .48)
            R = np.minimum(R, .74 - rid * .42)
            CC = np.maximum(CC, .20 + rid * .50)
        elif style == "louver":
            stripe = (np.mod(yy + xx * .12, pitch * 1.6) < pitch * .34).astype(np.float32)
            lip = (np.mod(yy + xx * .12, pitch * 1.6) < pitch * .06).astype(np.float32)
            M = np.maximum(M, .22 + stripe * .36 + lip * .38)
            R = np.minimum(R, .72 - lip * .50)
            CC = np.maximum(CC, .28 + lip * .58)
        else:
            for x, y in _grid_coords(w, h, pitch * (1.4 if style == "bolts" else 1.0), pitch * .1, rng):
                r = rng.uniform(2.2, 5.0) * scale
                _disc(M, (x, y), r + 1, rng.uniform(.62, .94), False)
                _disc(R, (x, y), r, rng.uniform(.05, .24))
                _disc(CC, (x, y), r, rng.uniform(.54, .95))
        _overlay_dots(M, R, CC, rng, w, h, int(h * w / 330), "metal")

    elif style in {"spread_tow", "hybrid_weave", "crossply", "braid", "tire_cord"}:
        a = math.radians(35 if style != "crossply" else 12)
        u = xx * math.cos(a) + yy * math.sin(a)
        v = -xx * math.sin(a) + yy * math.cos(a)
        p1 = max(10 * scale, 3.0)
        tow = ((np.mod(u, p1 * 2.4) < p1) ^ (np.mod(v, p1 * 2.1) < p1)).astype(np.float32)
        fine = (np.cos(u / max(1.1 * scale, .6)) * .5 + .5) * (np.cos(v / max(1.4 * scale, .6)) * .5 + .5)
        M = np.maximum(M, .24 + tow * .34 + fine * .18)
        R = np.minimum(R, .72 - tow * .26 - fine * .18)
        CC = np.maximum(CC, .24 + tow * .28 + fine * .22)
        _draw_lines(M, R, CC, rng, int(900 * (mn / 512) ** 2), w, h, scale, angle=a, length=(8, 24))

    elif style in {"facets", "inlay", "kintsugi", "cloisonne", "cracked_powder", "mud", "salt", "aggregate"}:
        cells = int(800 * (mn / 512) ** 2)
        for _ in range(cells):
            cx = rng.uniform(0, w); cy = rng.uniform(0, h)
            rad = rng.uniform(5, 18) * scale
            sides = int(rng.integers(4, 8))
            pts = []
            for k in range(sides):
                t = math.tau * k / sides + rng.uniform(-.18, .18)
                rr = rad * rng.uniform(.55, 1.18)
                pts.append((int(cx + math.cos(t) * rr), int(cy + math.sin(t) * rr)))
            fill_m = rng.uniform(.18, .82)
            _poly(M, pts, fill_m)
            _poly(R, pts, rng.uniform(.10, .78))
            _poly(CC, pts, rng.uniform(.18, .92))
            edge_m = rng.uniform(.60, .98) if style in {"kintsugi", "cloisonne", "inlay"} else rng.uniform(.04, .28)
            _poly(M, pts, edge_m, False)
            _poly(R, pts, rng.uniform(.05, .28) if style in {"kintsugi", "cloisonne", "inlay"} else rng.uniform(.62, .92), False)
        _draw_lines(M, R, CC, rng, int(720 * (mn / 512) ** 2), w, h, scale, length=(7, 22), bright=style in {"kintsugi", "cloisonne", "inlay"})

    elif style in {"sinter", "tar", "rain", "pearl_skin", "orange_peel", "powder_flake", "frost", "fuel_ring", "oilfilm"}:
        if style in {"rain", "orange_peel", "pearl_skin"}:
            n = int(2200 * (mn / 512) ** 2)
            for _ in range(n):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h)); r = rng.uniform(1.0, 3.6) * scale
                _disc(M, (cx, cy), r, rng.uniform(.18, .46))
                _disc(R, (cx, cy), r, rng.uniform(.04, .22))
                _disc(CC, (cx, cy), r, rng.uniform(.74, .99))
                if style == "rain":
                    _safe_line(CC, (cx, cy), (int(cx + rng.uniform(5, 18) * scale), int(cy + rng.uniform(-2, 2) * scale)), rng.uniform(.52, .86))
        elif style in {"fuel_ring", "oilfilm"}:
            for _ in range(int(420 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                rx = int(rng.uniform(6, 22) * scale); ry = int(rng.uniform(3, 12) * scale)
                ang = float(rng.uniform(0, 180))
                _cv2.ellipse(M, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(.36, .90)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(.05, .30)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(.62, .98)), 1, lineType=_cv2.LINE_AA)
        elif style == "tar":
            _draw_lines(M, R, CC, rng, int(760 * (mn / 512) ** 2), w, h, scale, angle=math.radians(18), length=(18, 58), bright=False)
            _overlay_dots(M, R, CC, rng, w, h, int(h * w / 240), "dark")
        elif style == "frost":
            for _ in range(int(950 * (mn / 512) ** 2)):
                cx = rng.uniform(0, w); cy = rng.uniform(0, h); a = rng.uniform(0, math.tau)
                for b in (-.45, 0, .45):
                    ln = rng.uniform(6, 18) * scale
                    p1 = (int(cx + math.cos(a + b) * ln), int(cy + math.sin(a + b) * ln))
                    _safe_line(M, (int(cx), int(cy)), p1, rng.uniform(.58, .96))
                    _safe_line(R, (int(cx), int(cy)), p1, rng.uniform(.12, .36))
                    _safe_line(CC, (int(cx), int(cy)), p1, rng.uniform(.64, .99))
        else:
            _overlay_dots(M, R, CC, rng, w, h, int(h * w / 120), "metal")
            _overlay_dots(M, R, CC, rng, w, h, int(h * w / 200), "dark")

    elif style in {"microbar", "circuit", "wire", "resin_bleed", "soot", "flame_lap", "clutch_dust", "clay_roost", "blast_edge", "waterjet", "wrinkle", "armor_bands", "segmented_shell", "scute"}:
        ang = {
            "wire": math.radians(-28), "resin_bleed": math.radians(6),
            "soot": math.radians(82), "flame_lap": math.radians(-18),
            "clay_roost": math.radians(-23), "waterjet": math.radians(90),
            "armor_bands": math.radians(12), "segmented_shell": math.radians(28),
            "scute": math.radians(-10)
        }.get(style, math.radians(0))
        _draw_lines(M, R, CC, rng, int(1200 * (mn / 512) ** 2), w, h, scale, angle=ang, length=(6, 24), bright=style not in {"soot", "wrinkle"})
        _draw_lines(M, R, CC, rng, int(420 * (mn / 512) ** 2), w, h, scale, angle=ang + math.pi / 2, length=(4, 12), bright=style in {"wire", "circuit", "microbar"})
        if style in {"circuit", "wire", "microbar"}:
            for _ in range(int(650 * (mn / 512) ** 2)):
                _disc(M, (int(rng.uniform(0, w)), int(rng.uniform(0, h))), rng.uniform(1.2, 3.2) * scale, rng.uniform(.62, .98))
                _disc(R, (int(rng.uniform(0, w)), int(rng.uniform(0, h))), rng.uniform(1.0, 2.5) * scale, rng.uniform(.06, .24))
        if style in {"soot", "clutch_dust", "wrinkle"}:
            _overlay_dots(M, R, CC, rng, w, h, int(h * w / 110), "dark")
        else:
            _overlay_dots(M, R, CC, rng, w, h, int(h * w / 190), "metal")

    # Pass 1 visual rescue: these were the soft/noisy thumbnails in the
    # definitive audit sheet. Add explicit material marks instead of relying on
    # substrate texture so they read at car-canvas scale.
    if _CV2_OK and style == "swirl":
        for _ in range(int(560 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            rx = max(4, int(rng.uniform(8, 28) * scale))
            ry = max(2, int(rng.uniform(3, 11) * scale))
            start = float(rng.uniform(0, 300))
            end = start + float(rng.uniform(35, 105))
            ang = float(rng.uniform(0, 180))
            _cv2.ellipse(M, (cx, cy), (rx, ry), ang, start, end, float(rng.uniform(.62, .98)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), ang, start, end, float(rng.uniform(.04, .20)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), ang, start, end, float(rng.uniform(.58, .96)), 1, lineType=_cv2.LINE_AA)
        _draw_lines(M, R, CC, rng, int(700 * (mn / 512) ** 2), w, h, scale, angle=math.radians(12), length=(8, 26))

    if _CV2_OK and style in {"rain", "orange_peel", "pearl_skin"}:
        count = int((1400 if style == "orange_peel" else 900) * (mn / 512) ** 2)
        for _ in range(count):
            cx = int(rng.uniform(2, w - 2)); cy = int(rng.uniform(2, h - 2))
            r = max(1, int(rng.uniform(1.8, 5.5) * scale))
            _disc(M, (cx, cy), r, rng.uniform(.18, .42))
            _disc(R, (cx, cy), r, rng.uniform(.03, .16))
            _disc(CC, (cx, cy), r, rng.uniform(.80, .99))
            _disc(M, (max(0, cx - r // 2), max(0, cy - r // 2)), max(1, r // 3), rng.uniform(.78, .99))
            if style == "rain":
                _safe_line(CC, (cx, cy), (int(cx + rng.uniform(7, 24) * scale), int(cy + rng.uniform(-2, 5) * scale)), rng.uniform(.70, .98))
            if style == "pearl_skin":
                _disc(M, (cx, cy), r + 1, rng.uniform(.62, .92), False)
        if style == "orange_peel":
            ripple = (np.cos(xx / max(4.0 * scale, 1.0) + np.sin(yy / max(19.0 * scale, 1.0))) * .5 + .5).astype(np.float32)
            M[:] = np.maximum(M, .20 + ripple * .42)
            R[:] = np.minimum(R, .70 - ripple * .44)
            CC[:] = np.maximum(CC, .38 + ripple * .52)

    if _CV2_OK and style in {"tar", "soot", "wrinkle"}:
        for _ in range(int(900 * (mn / 512) ** 2)):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            length = float(rng.uniform(18, 70) * scale)
            a = {"tar": .22, "soot": 1.42, "wrinkle": .68}[style] + float(rng.normal(0, .22))
            p0 = (int(cx - math.cos(a) * length * .5), int(cy - math.sin(a) * length * .5))
            p1 = (int(cx + math.cos(a) * length * .5), int(cy + math.sin(a) * length * .5))
            if style == "tar":
                _safe_line(M, p0, p1, rng.uniform(.06, .22), width=2)
                _safe_line(R, p0, p1, rng.uniform(.80, .98), width=2)
                _safe_line(CC, p0, p1, rng.uniform(.72, .99), width=2)
            elif style == "soot":
                _safe_line(M, p0, p1, rng.uniform(.04, .18))
                _safe_line(R, p0, p1, rng.uniform(.70, .96))
                _safe_line(CC, p0, p1, rng.uniform(.08, .26))
            else:
                _safe_line(M, p0, p1, rng.uniform(.46, .88))
                _safe_line(R, p0, p1, rng.uniform(.18, .48))
                _safe_line(CC, p0, p1, rng.uniform(.16, .46))

    if _CV2_OK and style in {"sinter", "powder_flake"}:
        for _ in range(int(1200 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            if style == "sinter":
                r = rng.uniform(1.2, 4.0) * scale
                _disc(M, (cx, cy), r, rng.uniform(.04, .20))
                _disc(R, (cx, cy), r, rng.uniform(.68, .96))
                _disc(CC, (cx, cy), r, rng.uniform(.06, .30))
                _disc(M, (cx, cy), r + 1, rng.uniform(.40, .72), False)
            else:
                sides = int(rng.integers(3, 7))
                rad = rng.uniform(2.0, 6.5) * scale
                pts = []
                for k in range(sides):
                    a = math.tau * k / sides + rng.uniform(-.24, .24)
                    pts.append((int(cx + math.cos(a) * rad * rng.uniform(.65, 1.15)),
                                int(cy + math.sin(a) * rad * rng.uniform(.65, 1.15))))
                _poly(M, pts, rng.uniform(.56, .96))
                _poly(R, pts, rng.uniform(.08, .30))
                _poly(CC, pts, rng.uniform(.46, .90))

    if _CV2_OK and style in {"engine_turn", "guilloche"}:
        for _ in range(int(460 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r = max(3, int(rng.uniform(7, 18) * scale))
            _cv2.ellipse(M, (cx, cy), (r, max(2, r // 3)), float(rng.uniform(0, 180)), 0, 340,
                         float(rng.uniform(.70, .99)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (r, max(2, r // 3)), float(rng.uniform(0, 180)), 0, 340,
                         float(rng.uniform(.04, .18)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (r, max(2, r // 3)), float(rng.uniform(0, 180)), 0, 340,
                         float(rng.uniform(.56, .96)), 1, lineType=_cv2.LINE_AA)

    if _CV2_OK and style in {"fuel_ring", "oilfilm"}:
        for _ in range(int(340 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            rx = max(4, int(rng.uniform(10, 34) * scale))
            ry = max(2, int(rng.uniform(4, 15) * scale))
            ang = float(rng.uniform(0, 180))
            for grow, mul in ((0, 1.0), (2, .72)):
                _cv2.ellipse(M, (cx, cy), (rx + grow, ry + grow), ang, 0, 360, float(rng.uniform(.56, .98) * mul), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx + grow, ry + grow), ang, 0, 360, float(rng.uniform(.04, .24)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx + grow, ry + grow), ang, 0, 360, float(rng.uniform(.66, .99) * mul), 1, lineType=_cv2.LINE_AA)

    if _CV2_OK and style in {"scute", "armor_bands", "segmented_shell"}:
        pitch = max(18.0 * scale, 5.0)
        if style == "scute":
            for y in np.arange(-pitch, h + pitch, pitch * .9):
                off = pitch * .5 if int(y / pitch) % 2 else 0
                for x in np.arange(-pitch, w + pitch, pitch * 1.35):
                    cx = int(x + off); cy = int(y)
                    pts = [
                        (cx, int(cy - pitch * .45)),
                        (int(cx + pitch * .52), int(cy - pitch * .10)),
                        (int(cx + pitch * .42), int(cy + pitch * .40)),
                        (int(cx - pitch * .42), int(cy + pitch * .40)),
                        (int(cx - pitch * .52), int(cy - pitch * .10)),
                    ]
                    _poly(M, pts, rng.uniform(.28, .72))
                    _poly(R, pts, rng.uniform(.18, .56))
                    _poly(CC, pts, rng.uniform(.22, .74))
                    _poly(M, pts, rng.uniform(.66, .98), False)
                    _poly(R, pts, rng.uniform(.05, .24), False)
                    _safe_line(M, (cx, int(cy - pitch * .32)), (cx, int(cy + pitch * .25)), rng.uniform(.68, .98))
        elif style == "armor_bands":
            for y in np.arange(-pitch * 2, h + pitch * 2, pitch * 1.15):
                for x in np.arange(-pitch * 2, w + pitch * 2, pitch * 2.0):
                    cx = int(x + (y * .45) % (pitch * 2)); cy = int(y)
                    pts = [
                        (int(cx - pitch * .85), int(cy - pitch * .30)),
                        (int(cx + pitch * .85), int(cy - pitch * .10)),
                        (int(cx + pitch * .65), int(cy + pitch * .38)),
                        (int(cx - pitch * .95), int(cy + pitch * .20)),
                    ]
                    _poly(M, pts, rng.uniform(.34, .78))
                    _poly(R, pts, rng.uniform(.12, .46))
                    _poly(CC, pts, rng.uniform(.18, .66))
                    _poly(M, pts, rng.uniform(.70, .99), False)
        else:
            for _ in range(int(850 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                rx = max(4, int(rng.uniform(8, 22) * scale))
                ry = max(2, int(rng.uniform(3, 8) * scale))
                ang = float(rng.uniform(0, 180))
                _cv2.ellipse(M, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(.42, .90)), -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(.08, .36)), -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(.32, .88)), -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(.70, .99)), 1, lineType=_cv2.LINE_AA)

    if _CV2_OK and style in {"flame_lap", "clay_roost", "blast_edge", "waterjet", "resin_bleed", "wire"}:
        if style == "flame_lap":
            for _ in range(int(700 * (mn / 512) ** 2)):
                base_x = float(rng.uniform(0, w)); base_y = float(rng.uniform(0, h))
                length = float(rng.uniform(14, 40) * scale)
                a = float(rng.uniform(-.8, .4))
                pts = [(base_x, base_y)]
                for k in range(1, 4):
                    pts.append((base_x + math.cos(a + k * .18) * length * k * .32,
                                base_y + math.sin(a + k * .18) * length * k * .32))
                for a0, a1 in zip(pts, pts[1:]):
                    p0 = (int(a0[0]), int(a0[1])); p1 = (int(a1[0]), int(a1[1]))
                    _safe_line(M, p0, p1, rng.uniform(.66, .99), 1)
                    _safe_line(R, p0, p1, rng.uniform(.05, .24), 1)
                    _safe_line(CC, p0, p1, rng.uniform(.60, .98), 1)
        elif style == "clay_roost":
            for _ in range(int(1400 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                r = max(1, int(rng.uniform(1.0, 4.2) * scale))
                _disc(M, (cx, cy), r, rng.uniform(.52, .92))
                _disc(R, (cx, cy), r, rng.uniform(.22, .56))
                _disc(CC, (cx, cy), r, rng.uniform(.10, .42))
                _safe_line(M, (cx, cy), (int(cx + rng.uniform(4, 18) * scale), int(cy + rng.uniform(-3, 7) * scale)), rng.uniform(.48, .86))
        elif style == "blast_edge":
            # OWNER-REBUILD 2026-06-03: "flat/boring, weak, not enough fine
            # detail, low effort". CRISP masked-blast: a few hard tape diagonals
            # split the panel into MASKED glossy bands (smooth, high-M, low-R)
            # vs BLASTED satin bands (frosty FINE micro-texture, low-M, high-R),
            # with sharp bright tape-edge highlights along every boundary.
            s256 = max(mn / 256.0, 0.6)
            ang = math.radians(float(rng.uniform(58, 74)))
            ca, sa = math.cos(ang), math.sin(ang)
            coord = (xx * ca + yy * sa).astype(np.float32)
            band = float(rng.uniform(60.0, 95.0) * s256)
            phase = (coord / band + float(rng.uniform(0, 1.0))) % 1.0
            masked = (phase < 0.5)        # glossy masked stripes
            blasted = ~masked             # satin blasted stripes
            # MASKED: smooth high-gloss metal
            M[masked] = np.clip(0.62 + (M[masked] - M[masked].mean()) * 0.4 + 0.18, 0, 1)
            R[masked] = np.clip(0.10 + R[masked] * 0.10, 0, 1)
            CC[masked] = np.clip(0.55 + (CC[masked] - 0.3) * 0.3, 0, 1)
            # BLASTED: dark satin + FINE frost micro-texture
            frost = _normalize(multi_scale_noise((h, w), [1.4, 3.0, 6.5], [0.5, 0.3, 0.2], seed + 771))
            M[blasted] = np.clip(0.22 + frost[blasted] * 0.30, 0, 1)
            R[blasted] = np.clip(0.58 - frost[blasted] * 0.22, 0, 1)
            CC[blasted] = np.clip(0.20 + frost[blasted] * 0.22, 0, 1)
            # CRISP tape-edge highlight where phase crosses the 0.5 boundary.
            edge = np.minimum(np.abs(phase - 0.5), np.minimum(phase, 1.0 - phase))
            tape = edge < (1.2 * s256 / band)
            M[tape] = 0.96
            R[tape] = 0.06
            CC[tape] = np.clip(CC[tape] + 0.3, 0, 1)
            # FINE blast pin-pitting inside blasted zones (dense tiny dark specks)
            n_pit = int(h * w / 70)
            py = rng.integers(0, h, n_pit); px = rng.integers(0, w, n_pit)
            keep = blasted[py, px]
            py, px = py[keep], px[keep]
            M[py, px] = np.clip(M[py, px] - rng.uniform(0.05, 0.20, py.size).astype(np.float32), 0, 1)
            R[py, px] = np.clip(R[py, px] + rng.uniform(0.08, 0.24, py.size).astype(np.float32), 0, 1)
            # sparse bright satin sparkle in masked zones
            n_sp = int(h * w / 260)
            sy = rng.integers(0, h, n_sp); sx = rng.integers(0, w, n_sp)
            keepm = masked[sy, sx]
            sy, sx = sy[keepm], sx[keepm]
            M[sy, sx] = rng.uniform(0.88, 0.99, sy.size).astype(np.float32)
        elif style == "waterjet":
            for x in np.arange(0, w, max(7 * scale, 2)):
                drift = math.sin(x * .03) * 7 * scale
                _safe_line(M, (int(x), 0), (int(x + drift), h), rng.uniform(.40, .88))
                _safe_line(R, (int(x), 0), (int(x + drift), h), rng.uniform(.10, .42))
                _safe_line(CC, (int(x), 0), (int(x + drift), h), rng.uniform(.30, .78))
        elif style == "resin_bleed":
            for _ in range(int(720 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                rx = max(3, int(rng.uniform(5, 18) * scale)); ry = max(1, int(rng.uniform(2, 7) * scale))
                _cv2.ellipse(CC, (cx, cy), (rx, ry), float(rng.uniform(0, 180)), 0, 360, float(rng.uniform(.76, .99)), -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), float(rng.uniform(0, 180)), 0, 360, float(rng.uniform(.04, .18)), -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), float(rng.uniform(0, 180)), 0, 360, float(rng.uniform(.20, .52)), -1, lineType=_cv2.LINE_AA)
        else:
            for _ in range(int(680 * (mn / 512) ** 2)):
                cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
                ln = float(rng.uniform(12, 34) * scale)
                a = math.radians(-28)
                off = math.sin(cx * .045) * 2.0 * scale
                p0 = (int(cx - math.cos(a) * ln * .5), int(cy - math.sin(a) * ln * .5 + off))
                p1 = (int(cx + math.cos(a) * ln * .5), int(cy + math.sin(a) * ln * .5 - off))
                _safe_line(M, p0, p1, rng.uniform(.72, .99))
                _safe_line(R, p0, p1, rng.uniform(.04, .20))
                _safe_line(CC, p0, p1, rng.uniform(.44, .88))

    # SPB definitive heartbeat rescue 2026-05-29. Owner verdict snippet:
    # "no lazy cousin variants... real world things that would be good to spec
    # out on cars." These identity passes make the weakest thumbnail readers
    # materially specific without increasing primitive size beyond car-scale.
    if _CV2_OK and style == "wrinkle":
        ridges = (
            (np.cos((xx + np.sin(yy / max(19.0 * scale, 1.0)) * 8.0 * scale) / max(6.0 * scale, 1.2)) * .5 + .5) *
            (np.cos((yy + np.sin(xx / max(23.0 * scale, 1.0)) * 7.0 * scale) / max(8.5 * scale, 1.2)) * .5 + .5)
        ).astype(np.float32)
        ridge_mask = ridges > .72
        valley_mask = ridges < .22
        M[ridge_mask] = np.maximum(M[ridge_mask], .48 + ridges[ridge_mask] * .34)
        R[ridge_mask] = np.minimum(R[ridge_mask], .42 - ridges[ridge_mask] * .16)
        CC[ridge_mask] = np.maximum(CC[ridge_mask], .24 + ridges[ridge_mask] * .26)
        M[valley_mask] = np.minimum(M[valley_mask], .16)
        R[valley_mask] = np.maximum(R[valley_mask], .66)
        CC[valley_mask] = np.minimum(CC[valley_mask], .22)
        for _ in range(int(260 * (mn / 512) ** 2)):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            ln = float(rng.uniform(10, 30) * scale)
            a = float(rng.uniform(0, math.tau))
            p0 = (int(cx - math.cos(a) * ln), int(cy - math.sin(a) * ln))
            p1 = (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln))
            _safe_line(M, p0, p1, rng.uniform(.58, .93))
            _safe_line(R, p0, p1, rng.uniform(.14, .36))
            _safe_line(CC, p0, p1, rng.uniform(.16, .44))

    if _CV2_OK and style == "soot":
        flow = (np.sin((yy * .92 + np.sin(xx / max(37.0 * scale, 1.0)) * 21.0 * scale) / max(13.0 * scale, 1.0)) * .5 + .5).astype(np.float32)
        lanes = flow > .62
        M[lanes] = np.minimum(M[lanes], .06 + flow[lanes] * .10)
        R[lanes] = np.maximum(R[lanes], .72 + flow[lanes] * .18)
        CC[lanes] = np.minimum(CC[lanes], .12 + flow[lanes] * .10)
        for _ in range(int(360 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            ln = float(rng.uniform(16, 54) * scale)
            a = math.radians(82) + float(rng.normal(0, .12))
            p1 = (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln))
            _safe_line(M, (cx, cy), p1, rng.uniform(.03, .16))
            _safe_line(R, (cx, cy), p1, rng.uniform(.76, .98))
            _safe_line(CC, (cx, cy), p1, rng.uniform(.06, .24))
        for _ in range(int(180 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r = max(1, int(rng.uniform(1.0, 3.0) * scale))
            _disc(M, (cx, cy), r, rng.uniform(.55, .95))
            _disc(R, (cx, cy), r, rng.uniform(.05, .22))
            _disc(CC, (cx, cy), r, rng.uniform(.16, .52))

    if _CV2_OK and style == "sinter":
        for _ in range(int(260 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r = max(1, int(rng.uniform(2.0, 6.5) * scale))
            _disc(M, (cx, cy), r, rng.uniform(.03, .14))
            _disc(R, (cx, cy), r, rng.uniform(.78, .98))
            _disc(CC, (cx, cy), r, rng.uniform(.05, .20))
            _disc(M, (cx, cy), r + 1, rng.uniform(.52, .86), False)
            _disc(CC, (cx, cy), r + 1, rng.uniform(.26, .58), False)
        for _ in range(int(100 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            rx = max(5, int(rng.uniform(12, 30) * scale))
            ry = max(2, int(rng.uniform(3, 9) * scale))
            ang = float(rng.uniform(-18, 18))
            _cv2.ellipse(M, (cx, cy), (rx, ry), ang, 195, 345, float(rng.uniform(.62, .96)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), ang, 195, 345, float(rng.uniform(.05, .22)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), ang, 195, 345, float(rng.uniform(.36, .76)), 1, lineType=_cv2.LINE_AA)

    if _CV2_OK and style in {"facets", "mud", "salt"}:
        if style == "facets":
            step = max(18.0 * scale, 5.0)
            for y in np.arange(-step, h + step, step * .9):
                for x in np.arange(-step, w + step, step * 1.35):
                    cx = int(x + rng.uniform(-step * .25, step * .25)); cy = int(y + rng.uniform(-step * .25, step * .25))
                    rad = float(rng.uniform(5.5, 12.5) * scale)
                    pts = [
                        (int(cx - rad * 1.1), int(cy - rad * .25)),
                        (int(cx - rad * .12), int(cy - rad * .86)),
                        (int(cx + rad * 1.05), int(cy - rad * .18)),
                        (int(cx + rad * .22), int(cy + rad * .82)),
                    ]
                    _poly(M, pts, rng.uniform(.36, .88))
                    _poly(R, pts, rng.uniform(.06, .32))
                    _poly(CC, pts, rng.uniform(.30, .86))
                    _poly(M, pts, rng.uniform(.72, .99), False)
                    _safe_line(M, pts[0], pts[2], rng.uniform(.78, .99))
        elif style == "mud":
            crack_count = int(360 * (mn / 512) ** 2)
            for _ in range(crack_count):
                cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
                ln = float(rng.uniform(10, 34) * scale)
                a = float(rng.uniform(0, math.tau))
                pts = [(cx, cy)]
                for k in range(1, 4):
                    a += float(rng.normal(0, .45))
                    pts.append((pts[-1][0] + math.cos(a) * ln * .36, pts[-1][1] + math.sin(a) * ln * .36))
                for a0, a1 in zip(pts, pts[1:]):
                    p0 = (int(a0[0]), int(a0[1])); p1 = (int(a1[0]), int(a1[1]))
                    _safe_line(M, p0, p1, rng.uniform(.04, .16))
                    _safe_line(R, p0, p1, rng.uniform(.72, .94))
                    _safe_line(CC, p0, p1, rng.uniform(.06, .20))
            _overlay_dots(M, R, CC, rng, w, h, int(h * w / 210), "dark")
        else:
            for _ in range(int(300 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                r = float(rng.uniform(2.0, 6.0) * scale)
                pts = [(int(cx - r), int(cy)), (int(cx), int(cy - r)), (int(cx + r), int(cy)), (int(cx), int(cy + r))]
                _poly(M, pts, rng.uniform(.64, .98))
                _poly(R, pts, rng.uniform(.04, .18))
                _poly(CC, pts, rng.uniform(.48, .92))
                _poly(M, pts, rng.uniform(.80, .99), False)
            for _ in range(int(150 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                ln = float(rng.uniform(8, 26) * scale)
                for a in (0, math.pi / 2, math.pi / 4):
                    p1 = (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln))
                    _safe_line(M, (cx, cy), p1, rng.uniform(.68, .98))
                    _safe_line(R, (cx, cy), p1, rng.uniform(.05, .20))
                    _safe_line(CC, (cx, cy), p1, rng.uniform(.42, .82))

    if _CV2_OK and style in {"microbar", "circuit"}:
        if style == "microbar":
            step = max(13.0 * scale, 4.0)
            for y in np.arange(0, h + step, step * 1.6):
                offset = float(rng.uniform(-step, step))
                for x in np.arange(offset, w + step, step * 2.2):
                    cx = int(x); cy = int(y + rng.uniform(-step * .35, step * .35))
                    ln = int(rng.uniform(7, 22) * scale)
                    _safe_line(M, (cx, cy), (cx + ln, cy), rng.uniform(.62, .98))
                    _safe_line(R, (cx, cy), (cx + ln, cy), rng.uniform(.04, .18))
                    _safe_line(CC, (cx, cy), (cx + ln, cy), rng.uniform(.36, .78))
                    if rng.random() < .45:
                        _safe_line(M, (cx, cy - 2), (cx, cy + 2), rng.uniform(.72, .99))
            for _ in range(int(150 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                rx = max(2, int(rng.uniform(3, 9) * scale))
                _cv2.rectangle(M, (cx - rx, cy - 1), (cx + rx, cy + 1), float(rng.uniform(.70, .99)), -1, lineType=_cv2.LINE_AA)
                _cv2.rectangle(R, (cx - rx, cy - 1), (cx + rx, cy + 1), float(rng.uniform(.04, .16)), -1, lineType=_cv2.LINE_AA)
        else:
            step = max(20.0 * scale, 5.0)
            for y in np.arange(step * .5, h, step):
                for x in np.arange(step * .5, w, step):
                    if rng.random() < .42:
                        p0 = (int(x), int(y))
                        p1 = (int(x + rng.choice([-1, 1]) * rng.uniform(8, 28) * scale), int(y))
                        p2 = (p1[0], int(y + rng.choice([-1, 1]) * rng.uniform(8, 28) * scale))
                        for a0, a1 in ((p0, p1), (p1, p2)):
                            _safe_line(M, a0, a1, rng.uniform(.55, .96))
                            _safe_line(R, a0, a1, rng.uniform(.05, .22))
                            _safe_line(CC, a0, a1, rng.uniform(.34, .82))
                        _disc(M, p0, rng.uniform(1.5, 3.5) * scale, rng.uniform(.70, .99))
                        _disc(R, p0, rng.uniform(1.2, 2.8) * scale, rng.uniform(.04, .16))
                        _disc(CC, p0, rng.uniform(1.5, 3.5) * scale, rng.uniform(.48, .92), False)

    if _CV2_OK and style == "clutch_dust":
        for _ in range(int(360 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            ln = float(rng.uniform(8, 32) * scale)
            a = math.radians(-18) + float(rng.normal(0, .22))
            p1 = (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln))
            _safe_line(M, (cx, cy), p1, rng.uniform(.52, .94))
            _safe_line(R, (cx, cy), p1, rng.uniform(.18, .52))
            _safe_line(CC, (cx, cy), p1, rng.uniform(.08, .36))
        for _ in range(int(380 * (mn / 512) ** 2)):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r = max(1, int(rng.uniform(1.0, 3.8) * scale))
            _disc(M, (cx, cy), r, rng.uniform(.58, .96))
            _disc(R, (cx, cy), r, rng.uniform(.10, .40))
            _disc(CC, (cx, cy), r, rng.uniform(.06, .30))

    # Channel-color balancing for the same weak readers. This is still true
    # spec data, but avoids the audit thumbnail collapsing into generic green
    # roughness static.
    if style in {"wrinkle", "soot", "sinter", "facets", "microbar", "circuit", "salt", "mud", "clutch_dust"}:
        texture = _normalize(M * .42 + (1.0 - R) * .28 + CC * .30)
        fine = _normalize(multi_scale_noise((h, w), [3.0, 9.0, 21.0], [.45, .33, .22], seed + 901))
        t = np.clip(texture * .78 + fine * .22, 0.0, 1.0)
        if style == "wrinkle":
            M[:] = np.maximum(M * .35, .08 + t * .60)
            R[:] = np.minimum(R * .45, .10 + (1.0 - t) * .25)
            CC[:] = np.maximum(CC * .45, .10 + t * .62)
        elif style == "soot":
            lane = (np.sin((yy * .9 + np.sin(xx / max(35.0 * scale, 1.0)) * 18.0 * scale) / max(13.0 * scale, 1.0)) * .5 + .5).astype(np.float32)
            M[:] = np.minimum(M * .55, .04 + t * .20)
            R[:] = .10 + t * .28
            CC[:] = np.maximum(CC * .35, .12 + lane * .58)
        elif style == "sinter":
            M[:] = .16 + t * .58
            R[:] = .10 + (1.0 - t) * .22
            CC[:] = .12 + t * .42
        elif style == "facets":
            M[:] = .18 + t * .70
            R[:] = .06 + (1.0 - t) * .26
            CC[:] = .18 + t * .68
        elif style in {"microbar", "circuit"}:
            M[:] = .10 + t * .72
            R[:] = .05 + (1.0 - t) * .22
            CC[:] = .18 + t * .66
        elif style == "salt":
            M[:] = .34 + t * .62
            R[:] = .04 + (1.0 - t) * .18
            CC[:] = .42 + t * .52
        else:
            M[:] = .34 + t * .54
            R[:] = .16 + t * .38
            CC[:] = .05 + (1.0 - t) * .22

    # Final foreground marks after channel grading so the audit thumbnails keep
    # the actual material story instead of only a colored noise field.
    if _CV2_OK and style in {"sinter", "facets", "microbar", "circuit", "salt", "mud", "clutch_dust"}:
        if style == "sinter":
            for _ in range(int(180 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                r = max(1, int(rng.uniform(1.6, 4.8) * scale))
                _disc(M, (cx, cy), r, rng.uniform(.02, .12))
                _disc(R, (cx, cy), r, rng.uniform(.02, .16))
                _disc(CC, (cx, cy), r, rng.uniform(.02, .14))
                _disc(M, (cx, cy), r + 1, rng.uniform(.68, .96), False)
                _disc(CC, (cx, cy), r + 1, rng.uniform(.42, .82), False)
        elif style == "facets":
            for _ in range(int(110 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                rad = float(rng.uniform(6.0, 14.0) * scale)
                pts = []
                for k in range(4):
                    a = math.tau * k / 4 + math.radians(45) + rng.uniform(-.10, .10)
                    pts.append((int(cx + math.cos(a) * rad * rng.uniform(.75, 1.2)),
                                int(cy + math.sin(a) * rad * rng.uniform(.75, 1.2))))
                _poly(M, pts, rng.uniform(.76, .99), False)
                _poly(R, pts, rng.uniform(.03, .16), False)
                _poly(CC, pts, rng.uniform(.58, .96), False)
        elif style == "microbar":
            for _ in range(int(250 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                ln = int(rng.uniform(7, 24) * scale)
                horizontal = bool(rng.integers(0, 2))
                p1 = (cx + ln, cy) if horizontal else (cx, cy + ln)
                _safe_line(M, (cx, cy), p1, rng.uniform(.75, .99))
                _safe_line(R, (cx, cy), p1, rng.uniform(.03, .14))
                _safe_line(CC, (cx, cy), p1, rng.uniform(.46, .90))
        elif style == "circuit":
            for _ in range(int(110 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                x2 = int(cx + rng.choice([-1, 1]) * rng.uniform(8, 24) * scale)
                y2 = int(cy + rng.choice([-1, 1]) * rng.uniform(8, 24) * scale)
                elbow = (x2, cy)
                for p0, p1 in (((cx, cy), elbow), (elbow, (x2, y2))):
                    _safe_line(M, p0, p1, rng.uniform(.62, .98))
                    _safe_line(R, p0, p1, rng.uniform(.03, .16))
                    _safe_line(CC, p0, p1, rng.uniform(.42, .88))
                _disc(M, (cx, cy), rng.uniform(1.5, 3.5) * scale, rng.uniform(.72, .99))
                _disc(CC, (cx, cy), rng.uniform(1.5, 3.5) * scale, rng.uniform(.56, .96), False)
        elif style == "salt":
            for _ in range(int(180 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                sz = int(rng.uniform(2.0, 6.0) * scale)
                _cv2.rectangle(M, (cx - sz, cy - sz), (cx + sz, cy + sz), float(rng.uniform(.78, .99)), 1, lineType=_cv2.LINE_AA)
                _cv2.rectangle(R, (cx - sz, cy - sz), (cx + sz, cy + sz), float(rng.uniform(.04, .18)), 1, lineType=_cv2.LINE_AA)
                _cv2.rectangle(CC, (cx - sz, cy - sz), (cx + sz, cy + sz), float(rng.uniform(.70, .99)), 1, lineType=_cv2.LINE_AA)
        elif style == "mud":
            for _ in range(int(240 * (mn / 512) ** 2)):
                cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
                ln = float(rng.uniform(9, 28) * scale)
                a = float(rng.uniform(0, math.tau))
                p1 = (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln))
                _safe_line(M, (int(cx), int(cy)), p1, rng.uniform(.02, .12))
                _safe_line(R, (int(cx), int(cy)), p1, rng.uniform(.03, .15))
                _safe_line(CC, (int(cx), int(cy)), p1, rng.uniform(.02, .12))
        else:
            for _ in range(int(260 * (mn / 512) ** 2)):
                cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
                r = max(1, int(rng.uniform(1.0, 3.2) * scale))
                _disc(M, (cx, cy), r, rng.uniform(.70, .99))
                _disc(R, (cx, cy), r, rng.uniform(.30, .62))
                _disc(CC, (cx, cy), r, rng.uniform(.04, .18))

    return _finish(M, R, CC, sm, public_id)


def _make_renderer(public_id, style):
    def _renderer(shape, seed, sm, **kwargs):
        del kwargs
        return _render(style, public_id, shape, seed, sm)
    _renderer.__name__ = public_id
    return _renderer


DEFINITIVE_SPEC_OVERLAY_CATALOG = {
    public_id: _make_renderer(public_id, style)
    for public_id, _name, _desc, _category, style in DEFINITIVE_SPEC_OVERLAY_METADATA
}

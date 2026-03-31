"""
Atelier — Ultra-Detail Monolithic Finishes
==========================================
15–20 render-intensive finishes designed to approximate work that would take
a pro painter with 25+ years of experience 20+ hours to replicate by hand.
Multi-layer micro-detail: fine noise scales, veining, directional grain,
and intricate spatial variation. Not heavy for the sake of it — each design
is structurally complex so the result reads as hand-crafted.

Categories: Japanese lacquer, engine-turned (guilloché), damascus layering,
cathedral glass, vintage enamel crackle, carbon weave micro, pearl depth,
hand-brushed metal, forged texture, and similar.

Integration: Called from shokker_engine_v2 after color monolithics.
Engine module must provide: multi_scale_noise(shape, scales, weights, seed),
get_mgrid(shape).
"""

import numpy as np

_engine = None


def _ensure_bb_2d(bb, shape):
    """Expand scalar bb to (H,W) float32 if needed."""
    if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
        h, w = shape[0], shape[1]
        return np.full((h, w), float(bb), dtype=np.float32)
    return bb


def _atelier_spec(M=120, R=35, CC=45):
    """Shared high-quality spec for Atelier: visible metallic, moderate roughness, clearcoat depth.
    Used only by finishes 10+ that have not yet received individual spec functions."""
    def spec_fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
        spec[:, :, 2] = CC
        spec[:, :, 3] = 255
        return spec
    return spec_fn


# ============== Individual spec functions for first 9 finishes ==============

def _spec_japanese_lacquer(shape, mask, seed, sm):
    """Multi-layer lacquer with crackle network. Crackle lines rough/exposed, smooth areas glossy."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Crackle network from multi-scale noise edges
    n1 = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 50)
    n2 = e.multi_scale_noise(shape, [2, 6, 12, 24], [0.2, 0.3, 0.3, 0.2], seed + 51)
    crackle = np.clip(np.abs(n1) + np.abs(n2) * 0.6, 0, 1)
    crackle = np.clip(crackle * 2.0 - 0.6, 0, 1)  # sharpen into lines
    # Depth noise for CC variation
    depth = e.multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 52)
    depth01 = np.clip((depth + 1) * 0.5, 0, 1)
    # M: 20 at smooth lacquer, up to 160 in crackle zones
    m_ch = (20.0 + 140.0 * crackle + depth01 * 20.0) * mask + 5.0 * (1 - mask)
    # R: 15 smooth, 120 crackle lines
    r_ch = (15.0 + 105.0 * crackle) * mask + 100.0 * (1 - mask)
    # CC: 16 deep pools, 80 thin areas, driven by depth
    cc_ch = (16.0 + 64.0 * depth01) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_engine_turned(shape, mask, seed, sm):
    """Guilloché pattern — overlapping circular arcs creating interference."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = e.get_mgrid(shape)
    # Create guilloché: overlapping circles on a grid
    cell_size = max(h, w) / 12.0
    # Two offset grids of circular arcs
    cx1 = (x % cell_size) - cell_size * 0.5
    cy1 = (y % cell_size) - cell_size * 0.5
    r1 = np.sqrt(cx1**2 + cy1**2) / cell_size
    cx2 = ((x + cell_size * 0.5) % cell_size) - cell_size * 0.5
    cy2 = ((y + cell_size * 0.5) % cell_size) - cell_size * 0.5
    r2 = np.sqrt(cx2**2 + cy2**2) / cell_size
    groove1 = np.sin(r1 * 18.0) * 0.5 + 0.5
    groove2 = np.sin(r2 * 18.0) * 0.5 + 0.5
    groove = np.clip(groove1 * 0.5 + groove2 * 0.5, 0, 1)
    # Independent texture noise for R
    texture = e.multi_scale_noise(shape, [1, 2, 4, 8], [0.2, 0.3, 0.3, 0.2], seed + 60)
    texture01 = np.clip((texture + 1) * 0.5, 0, 1)
    # Independent CC variation noise
    cc_var = e.multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 61)
    cc_var01 = np.clip((cc_var + 1) * 0.5, 0, 1)
    # M: 120-250 (span 130)
    m_ch = (120.0 + 130.0 * groove) * mask + 5.0 * (1 - mask)
    # R: 10-160 driven by inverse groove + independent texture (span ~140)
    r_ch = (10.0 + 120.0 * (1 - groove) + texture01 * 30.0) * mask + 100.0 * (1 - mask)
    # CC: 16-96 driven by independent noise (span 80)
    cc_ch = (16.0 + 80.0 * cc_var01) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_damascus_layers(shape, mask, seed, sm):
    """Folded metal layers — sine-wave domain-warped bands with fine grain."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Domain warp noise
    warp = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 70)
    grain = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.25, 0.3, 0.25, 0.2], seed + 71)
    # Independent noise for CC channel
    cc_ind = e.multi_scale_noise(shape, [6, 12, 24, 48], [0.2, 0.3, 0.3, 0.2], seed + 72)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    grain01 = np.clip((grain + 1) * 0.5, 0, 1)
    y, _ = e.get_mgrid(shape)
    # Warped sine bands
    band = np.sin(y / max(1, h) * 14.0 + warp * 4.5) * 0.5 + 0.5
    band = np.clip(band + grain * 0.15, 0, 1)
    # M: 60-220 (span 160)
    m_ch = (60.0 + 160.0 * band) * mask + 5.0 * (1 - mask)
    # R: 20-150 driven by grain + inverse band (span ~130)
    r_ch = (20.0 + grain01 * 80.0 + (1 - band) * 50.0) * mask + 100.0 * (1 - mask)
    # CC: 16-116 driven by independent noise (span 100)
    cc_ch = (16.0 + 100.0 * cc_ind01) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_cathedral_glass(shape, mask, seed, sm):
    """Voronoi panes with lead-line borders. Glass interiors vs matte metal borders."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Approximate Voronoi with multi-scale noise gradients
    panes_lo = e.multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 80)
    panes_hi = e.multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 81)
    # Gradient magnitude ~ lead lines (edges between cells)
    gy_lo = np.abs(np.diff(panes_lo, axis=0, prepend=panes_lo[:1, :]))
    gx_lo = np.abs(np.diff(panes_lo, axis=1, prepend=panes_lo[:, :1]))
    edge = np.clip((gy_lo + gx_lo) * 8.0, 0, 1)
    # Per-pane CC variation
    pane_cc_var = e.multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 82)
    pane_cc01 = np.clip((pane_cc_var + 1) * 0.5, 0, 1)
    # Per-pane noise for M interior variation
    pane_noise = e.multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 83)
    pane_n01 = np.clip((pane_noise + 1) * 0.5, 0, 1)
    # Pane interiors: M=10/R=5/CC=20, Lead: M=140/R=125/CC=100 (span M~150, R~120)
    m_ch = (10.0 + 130.0 * edge + pane_n01 * 20.0) * mask + 5.0 * (1 - mask)
    r_ch = (5.0 + 120.0 * edge) * mask + 100.0 * (1 - mask)
    cc_ch = (20.0 + 80.0 * edge + (1 - edge) * pane_cc01 * 40.0) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_vintage_enamel_crackle(shape, mask, seed, sm):
    """Worley F2-F1 style crack network. Enamel surface vs exposed substrate cracks."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Crack network from high-freq noise edges (Worley approximation)
    n1 = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 90)
    n2 = e.multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 91)
    # Stress noise varies crack width
    stress = e.multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 92)
    stress01 = np.clip((stress + 1) * 0.5, 0, 1)
    crack = np.clip(np.abs(n1) + np.abs(n2) * 0.5, 0, 1)
    crack = np.clip(crack * (1.5 + stress01) - 0.4, 0, 1)
    # Micro-texture for M channel (single-material exception, need ≥40 span)
    micro_tex = e.multi_scale_noise(shape, [1, 2, 4, 8], [0.2, 0.3, 0.3, 0.2], seed + 93)
    micro_tex01 = np.clip((micro_tex + 1) * 0.5, 0, 1)
    # Independent noise for CC
    cc_ind = e.multi_scale_noise(shape, [6, 12, 24], [0.3, 0.4, 0.3], seed + 94)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    # Enamel: M=0-60 via micro texture (span 60, >40 single-material gate)
    m_ch = (60.0 * micro_tex01) * mask + 5.0 * (1 - mask)
    r_ch = (25.0 + 155.0 * crack) * mask + 100.0 * (1 - mask)
    cc_ch = (30.0 + 130.0 * crack * 0.5 + cc_ind01 * 65.0) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_carbon_weave_micro(shape, mask, seed, sm):
    """True 2x2 twill weave using sin products. Warp vs weft thread spec differences."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = e.get_mgrid(shape)
    # Tight twill weave frequency
    freq = 80.0
    # Twill: warp dominates where sin(y)*sin(x+y) > 0.5
    twill = np.sin(y / max(1, h) * freq) * np.sin((x + y) / max(1, w) * freq * 0.7)
    twill01 = np.clip(twill * 0.5 + 0.5, 0, 1)
    # Independent micro-texture noise
    micro = e.multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed + 100)
    micro01 = np.clip((micro + 1) * 0.5, 0, 1)
    # Independent thread noise for R
    thread_noise = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 101)
    thread01 = np.clip((thread_noise + 1) * 0.5, 0, 1)
    # Independent CC noise
    cc_ind = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 102)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    # M: 80-240 (span 160) driven by twill + micro
    m_ch = (80.0 + 140.0 * twill01 + micro01 * 20.0) * mask + 5.0 * (1 - mask)
    # R: 10-170 (span ~160) driven by inverse twill + thread noise
    r_ch = (10.0 + 130.0 * (1 - twill01) + thread01 * 30.0) * mask + 100.0 * (1 - mask)
    # CC: 16-106 (span 90) driven by independent noise
    cc_ch = (16.0 + 90.0 * cc_ind01) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_pearl_depth_layers(shape, mask, seed, sm):
    """Multi-layer pearl — 3 overlapping domain-warped noise fields at different scales."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Three pearl layers at different scales
    layer1 = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.25, 0.3, 0.25], seed + 110)
    layer2 = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 111)
    layer3 = e.multi_scale_noise(shape, [16, 32, 64, 128], [0.25, 0.3, 0.25, 0.2], seed + 112)
    l1 = np.clip((layer1 + 1) * 0.5, 0, 1)
    l2 = np.clip((layer2 + 1) * 0.5, 0, 1)
    l3 = np.clip((layer3 + 1) * 0.5, 0, 1)
    # M: 30-160 (span 130) driven by 3 independent layers
    m_ch = (30.0 + 60.0 * l1 + 40.0 * l2 + 30.0 * l3) * mask + 5.0 * (1 - mask)
    # R: 10-130 (span 120) each layer contributes independently
    r_ch = (10.0 + 50.0 * l1 + 40.0 * (1 - l2) + 30.0 * l3) * mask + 100.0 * (1 - mask)
    # CC: visible depth 16-120
    cc_ch = (16.0 + 40.0 * l2 + 35.0 * l3 + 29.0 * l1) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_hand_brushed_metal(shape, mask, seed, sm):
    """Anisotropic brush grain — elongated noise along horizontal direction."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = e.get_mgrid(shape)
    # Brush grain: multiple horizontal frequencies
    grain = e.multi_scale_noise(shape, [2, 4, 8, 16, 32], [0.15, 0.2, 0.25, 0.25, 0.15], seed + 120)
    # Horizontal flow gives directional anisotropy
    flow_h = np.sin(x / max(1, w) * 60.0 + grain * 3.0) * 0.5 + 0.5
    # Cross-grain variation
    cross = np.sin(y / max(1, h) * 200.0 + grain * 1.5) * 0.5 + 0.5
    # Independent CC noise
    cc_ind = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 121)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    # M: 100-240 (span 140) brush stroke variation
    m_ch = (100.0 + 140.0 * flow_h) * mask + 5.0 * (1 - mask)
    # R: 10 with grain, 120 across grain
    r_ch = (10.0 + 110.0 * cross * (1 - flow_h)) * mask + 100.0 * (1 - mask)
    # CC: 16-106 (span 90) driven by independent noise
    cc_ch = (16.0 + 90.0 * cc_ind01) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_forged_iron_texture(shape, mask, seed, sm):
    """Hammer scale marks — random overlapping circular depressions with micro-pitting."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Scale marks from layered noise
    n1 = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 130)
    # Circular depressions: threshold noise to create "hammered" spots
    marks_raw = np.clip((n1 + 1) * 0.5, 0, 1)
    marks = np.clip(marks_raw * 2.0 - 0.5, 0, 1)  # sharpen into distinct marks
    # Micro-pitting overlay
    pitting = e.multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed + 132)
    pit01 = np.clip((pitting + 1) * 0.5, 0, 1)
    # M: 60-230 (span ~170) driven by marks + pitting
    m_ch = (60.0 + 140.0 * marks + pit01 * 30.0) * mask + 5.0 * (1 - mask)
    r_ch = (160.0 - 120.0 * marks + pit01 * 20.0) * mask + 100.0 * (1 - mask)
    # CC: 16-116 (span 100) driven by inverse marks
    cc_ch = (16.0 + 100.0 * (1 - marks)) * mask + 30.0 * (1 - mask)
    spec[:, :, 0] = np.clip(m_ch, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r_ch, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc_ch, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


# ============== Individual spec functions for finishes 10-17 ==============

def _spec_micro_flake_burst(shape, mask, seed, sm):
    """Multi-scale metallic flake simulation with Voronoi-like large flakes and fine sparkle."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 1000)
    y, x = e.get_mgrid(shape)

    # --- Large flake pattern via pseudo-Voronoi (30 points) ---
    n_pts = 30
    pts_y = rng.rand(n_pts) * h
    pts_x = rng.rand(n_pts) * w
    d_min = np.full((h, w), 1e9, dtype=np.float32)
    d_second = np.full((h, w), 1e9, dtype=np.float32)
    for i in range(n_pts):
        d = np.sqrt((y - pts_y[i]) ** 2 + (x - pts_x[i]) ** 2)
        update_second = d < d_second
        d_second = np.where(update_second, np.minimum(d, d_second), d_second)
        swap = d_min > d_second
        d_min, d_second = np.where(swap, d_second, d_min), np.where(swap, d_min, d_second)
    max_d = np.percentile(d_min, 99) + 1e-6
    d_min_n = np.clip(d_min / max_d, 0, 1)
    flake_mask = np.clip(1.0 - d_min_n * 3.0, 0, 1)

    # --- Fine sparkle noise (micro-flake texture) ---
    sparkle = e.multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + 1002)
    sparkle_01 = np.clip((sparkle + 1) * 0.5, 0, 1)

    # --- Large-scale density envelope ---
    envelope = e.multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 1003)
    envelope_01 = np.clip((envelope + 1) * 0.5, 0, 1)
    flake_density = flake_mask * (0.4 + 0.6 * envelope_01)

    # Independent CC noise
    cc_ind = e.multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1004)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    # Flake: M=255/R=5/CC=16. Base coat: M=120/R=115/CC varies.
    M = flake_density * 255 + (1 - flake_density) * 120
    M = M + sparkle_01 * 20 * (1 - flake_density)
    R = flake_density * 5 + (1 - flake_density) * 110
    R = R + sparkle_01 * 20 * (1 - flake_density)
    CC = 16.0 + (1 - flake_density) * 80 + cc_ind01 * 30

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_marble_vein_fine(shape, mask, seed, sm):
    """Marble veining using domain-warped sine with ridge noise for sharp vein lines."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = e.get_mgrid(shape)

    # Domain warp fields
    warp1 = e.multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1100)
    warp2 = e.multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1101)

    # Multiple vein layers at different scales using ridge noise (1 - |noise|)
    vein_accum = np.zeros((h, w), dtype=np.float32)
    for i, (freq, weight) in enumerate([(6, 0.45), (12, 0.30), (24, 0.15), (48, 0.10)]):
        warped_y = y / max(1, h) * freq + warp1 * 2.5
        warped_x = x / max(1, w) * freq * 0.6 + warp2 * 1.8
        raw = np.sin(warped_y + warped_x * 0.7 + i * 1.3)
        ridge = 1.0 - np.abs(raw)
        ridge = ridge ** 3
        vein_accum += ridge * weight
    vein_accum = np.clip(vein_accum, 0, 1)

    # Independent CC noise
    cc_ind = e.multi_scale_noise(shape, [6, 12, 24, 48], [0.2, 0.3, 0.3, 0.2], seed + 1103)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)

    # Vein: M driven by vein + micro. Stone: R driven by inverse vein. CC independent.
    micro = e.multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1102)
    micro01 = np.clip((micro + 1) * 0.5, 0, 1)
    M = vein_accum * 140 + micro01 * 20
    R = vein_accum * 15 + (1 - vein_accum) * 100 + micro * 10
    # CC: 16-106 (span 90) driven by independent noise
    CC = 16.0 + 90.0 * cc_ind01

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_obsidian_glass(shape, mask, seed, sm):
    """Volcanic glass with conchoidal fracture pattern using overlapping noise intersections."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)

    n1 = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1200)
    n2 = e.multi_scale_noise(shape, [6, 12, 24, 48], [0.25, 0.3, 0.25, 0.2], seed + 1201)
    n3 = e.multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1202)

    # Thin fracture lines where noise fields cross zero
    edge1 = 1.0 - np.clip(np.abs(n1) * 4, 0, 1)
    edge2 = 1.0 - np.clip(np.abs(n2) * 4, 0, 1)
    fracture = np.clip((edge1 + edge2 + np.abs(n3) * 0.3) * 1.5, 0, 1)

    # Conchoidal fracture shells
    shell = e.multi_scale_noise(shape, [16, 32, 64, 128], [0.2, 0.3, 0.3, 0.2], seed + 1203)
    shell_01 = np.clip((shell + 1) * 0.5, 0, 1)

    # Independent CC noise
    cc_ind = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1204)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    # Smooth obsidian: M=40-200/R=2-132/CC=16-116 (independent)
    M = (1 - fracture) * (40 + shell_01 * 30) + fracture * (120 + shell_01 * 80)
    R = (1 - fracture) * 2 + fracture * 130
    CC = 16.0 + 100.0 * cc_ind01

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_silk_weave(shape, mask, seed, sm):
    """Fine silk weave — anisotropic roughness alternating warp and weft threads."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = e.get_mgrid(shape)

    thread_freq = 160
    micro = e.multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed + 1300)

    warp_thread = np.sin(x / max(1, w) * thread_freq + micro * 1.5) * 0.5 + 0.5
    weft_thread = np.sin(y / max(1, h) * thread_freq + micro * 1.2) * 0.5 + 0.5

    # Over-under checker pattern
    checker = ((np.floor(x / max(1, w) * thread_freq / np.pi) +
                np.floor(y / max(1, h) * thread_freq / np.pi)) % 2).astype(np.float32)
    warp_on_top = checker
    # Thread intersection dips
    intersection = warp_thread * weft_thread
    dip = np.clip(1.0 - intersection * 1.5, 0, 1) * 0.3

    # Independent thread noise for channel separation
    thread_noise = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1301)
    thread01 = np.clip((thread_noise + 1) * 0.5, 0, 1)
    # Independent CC noise
    cc_ind = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1302)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    # Combined weave signal for M
    weave = warp_on_top * warp_thread + (1 - warp_on_top) * weft_thread
    # M: 20-170 (span ~150) driven by weave + thread noise
    M = 20.0 + weave * 130 + thread01 * 20 - dip * 15
    # R: 10-160 (span ~150) driven by inverse weave + dip
    R = 10.0 + (1 - weave) * 120 + dip * 30
    # CC: 16-106 (span 90) driven by independent noise
    CC = 16.0 + 90.0 * cc_ind01

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_ceramic_glaze(shape, mask, seed, sm):
    """Pooled glaze with crazing — thick pools, thin zones, and crack network."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 1400)
    y, x = e.get_mgrid(shape)

    # Domain-warped noise for pool shapes
    warp = e.multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 1400)
    pool_raw = e.multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1401)
    pool = np.clip((pool_raw + warp * 0.8 + 1) * 0.5, 0, 1)
    pool_depth = np.clip(pool * 1.5 - 0.25, 0, 1)

    # Worley-like crazing via pseudo-Voronoi
    n_pts = 60
    pts_y = rng.rand(n_pts) * h
    pts_x = rng.rand(n_pts) * w
    d_min = np.full((h, w), 1e9, dtype=np.float32)
    d_second = np.full((h, w), 1e9, dtype=np.float32)
    for i in range(n_pts):
        d = np.sqrt((y - pts_y[i]) ** 2 + (x - pts_x[i]) ** 2)
        update = d < d_second
        d_second = np.where(update, np.minimum(d, d_second), d_second)
        swap = d_min > d_second
        d_min, d_second = np.where(swap, d_second, d_min), np.where(swap, d_min, d_second)
    f2_f1 = d_second - d_min
    max_f = np.percentile(f2_f1, 95) + 1e-6
    crack_raw = 1.0 - np.clip(f2_f1 / max_f * 3, 0, 1)
    crazing = crack_raw * (0.3 + 0.7 * (1 - pool_depth))

    # Thick pooled: M=10/R=10/CC=16. Thin: M=150/R=60/CC=80. Cracks: M=20/R=140/CC=120.
    M = pool_depth * 10 + (1 - pool_depth) * 150
    M = M * (1 - crazing) + crazing * 20
    R = pool_depth * 10 + (1 - pool_depth) * 60
    R = R * (1 - crazing) + crazing * 140
    CC = pool_depth * 16 + (1 - pool_depth) * 80
    CC = CC * (1 - crazing) + crazing * 120

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_brushed_titanium(shape, mask, seed, sm):
    """Anisotropic brush grain — elongated noise 10:1 x-stretch for directional grain."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = e.get_mgrid(shape)

    grain_noise = e.multi_scale_noise(shape, [2, 4, 8, 16, 32], [0.15, 0.2, 0.25, 0.25, 0.15], seed + 1500)
    # Elongated grain: high freq in x (along grain), low freq in y (across)
    grain_primary = np.sin(x / max(1, w) * 400 + grain_noise * 3) * 0.5 + 0.5
    micro_grain = np.sin(x / max(1, w) * 800 + grain_noise * 1.5) * 0.5 + 0.5
    cross = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1501)
    cross_01 = np.clip((cross + 1) * 0.5, 0, 1)
    combined_grain = grain_primary * 0.6 + micro_grain * 0.25 + cross_01 * 0.15

    # Independent CC noise (micro-grain driven)
    cc_ind = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1502)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    # M: 100-240 (span 140) with grain variation
    M = 100 + combined_grain * 140
    # R: 8 along grain (smooth), 130 across grain
    R = 8 + (1 - grain_primary) * 122
    R = R + cross_01 * 15
    # CC: 16-106 (span 90) driven by independent noise
    CC = 16 + cc_ind01 * 90

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_gold_leaf_micro(shape, mask, seed, sm):
    """Gold leaf patches with micro-cracks — Voronoi cells for leaves, F2-F1 for crack borders."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 1600)
    y, x = e.get_mgrid(shape)

    n_pts = 40
    pts_y = rng.rand(n_pts) * h
    pts_x = rng.rand(n_pts) * w
    patch_m_offset = rng.uniform(-15, 5, n_pts).astype(np.float32)

    d_min = np.full((h, w), 1e9, dtype=np.float32)
    d_second = np.full((h, w), 1e9, dtype=np.float32)
    nearest_id = np.zeros((h, w), dtype=np.int32)
    for i in range(n_pts):
        d = np.sqrt((y - pts_y[i]) ** 2 + (x - pts_x[i]) ** 2)
        closer = d < d_min
        d_second = np.where(closer, d_min, np.where(d < d_second, d, d_second))
        nearest_id = np.where(closer, i, nearest_id)
        d_min = np.where(closer, d, d_min)
    f2_f1 = d_second - d_min
    max_f = np.percentile(f2_f1, 95) + 1e-6
    crack_border = np.clip((1.0 - np.clip(f2_f1 / max_f * 4, 0, 1)) * 2, 0, 1)

    patch_offset_map = patch_m_offset[nearest_id]

    # Leaf: M=250/R=10/CC varies. Cracks: M=100/R=140/CC varies.
    leaf_area = 1.0 - crack_border
    M = leaf_area * (250 + patch_offset_map) + crack_border * 100
    R = leaf_area * 10 + crack_border * 140

    micro = e.multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1602)
    M = M + micro * 8 * leaf_area
    R = R + np.abs(micro) * 6 * leaf_area
    # Independent CC noise (separate driver from leaf_area)
    cc_ind = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1603)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    CC = 16.0 + leaf_area * 20 + cc_ind01 * 80

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def _spec_fluid_metal(shape, mask, seed, sm):
    """Liquid mercury flow — domain-warped sine for flow streams with turbulence."""
    e = _engine
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = e.get_mgrid(shape)

    warp1 = e.multi_scale_noise(shape, [16, 32, 64, 128], [0.2, 0.3, 0.3, 0.2], seed + 1700)
    warp2 = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1701)
    turb = e.multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1702)

    # Flow streams with gravity bias (dominant y-direction)
    flow1 = np.sin(y / max(1, h) * 10 + warp1 * 4 + x / max(1, w) * 3) * 0.5 + 0.5
    flow2 = np.sin(y / max(1, h) * 18 + warp2 * 3 + turb * 2) * 0.5 + 0.5
    flow3 = np.sin(y / max(1, h) * 30 + warp1 * 2 + warp2 * 1.5) * 0.5 + 0.5
    flow = np.clip(flow1 * 0.5 + flow2 * 0.3 + flow3 * 0.2 + turb * 0.15, 0, 1)

    # Independent CC noise
    cc_ind = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1703)
    cc_ind01 = np.clip((cc_ind + 1) * 0.5, 0, 1)
    turb01 = np.clip((turb + 1) * 0.5, 0, 1)
    # M: 80-240 (span 160) driven by flow
    M = 80.0 + 160.0 * flow
    # R: 5-165 (span ~160) driven by inverse flow + turbulence
    R = 5.0 + 130.0 * (1 - flow) + turb01 * 30.0
    # CC: 16-116 (span 100) driven by independent noise
    CC = 16.0 + 100.0 * cc_ind01

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


# ============== Ultra-detail paint factories ==============

def _paint_japanese_lacquer(paint, shape, mask, seed, pm, bb):
    """Deep red-black tint in crackle zones, smooth gloss in lacquer areas. Blend 0.40."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    # Crackle network
    n1 = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 50)
    n2 = e.multi_scale_noise(shape, [2, 6, 12, 24], [0.2, 0.3, 0.3, 0.2], seed + 51)
    crackle = np.clip(np.abs(n1) + np.abs(n2) * 0.6, 0, 1)
    crackle = np.clip(crackle * 2.0 - 0.6, 0, 1)
    # Dark red-black tint in crackle zones, slight warmth in smooth areas
    tint_r = -0.35 * crackle + 0.10 * (1 - crackle)
    tint_g = -0.20 * crackle - 0.04 * (1 - crackle)
    tint_b = -0.18 * crackle - 0.06 * (1 - crackle)
    blend = 0.75 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_engine_turned(paint, shape, mask, seed, pm, bb):
    """Silver/chrome with groove-driven brightness variation. Blend 0.45."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    y, x = e.get_mgrid(shape)
    # Guilloché grooves
    cell_size = max(h, w) / 12.0
    cx1 = (x % cell_size) - cell_size * 0.5
    cy1 = (y % cell_size) - cell_size * 0.5
    r1 = np.sqrt(cx1**2 + cy1**2) / cell_size
    cx2 = ((x + cell_size * 0.5) % cell_size) - cell_size * 0.5
    cy2 = ((y + cell_size * 0.5) % cell_size) - cell_size * 0.5
    r2 = np.sqrt(cx2**2 + cy2**2) / cell_size
    groove = np.clip(np.sin(r1 * 18.0) * 0.5 + np.sin(r2 * 18.0) * 0.5, -0.5, 1.0)
    groove01 = np.clip(groove * 0.5 + 0.5, 0, 1)
    # Brightness variation driven by groove pattern
    brightness_mod = groove01 * 0.60 - 0.30  # -0.30 to +0.30
    blend = 0.75 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    for c in range(3):
        target_c = np.clip(paint[:, :, c] + brightness_mod, 0, 1)
        # Replacement blend: fade between base and finish
        result[:, :, c] = paint[:, :, c] * (1 - blend[:, :, 0]) + target_c * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_damascus_layers(paint, shape, mask, seed, pm, bb):
    """Alternating light/dark silver bands with warm undertone. Blend 0.45."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    warp = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 70)
    grain = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.25, 0.3, 0.25, 0.2], seed + 71)
    y, _ = e.get_mgrid(shape)
    band = np.sin(y / max(1, h) * 14.0 + warp * 4.5) * 0.5 + 0.5
    band = np.clip(band + grain * 0.15, 0, 1)
    # Light bands brighten, dark bands darken, warm undertone shift
    brightness_mod = band * 0.45 - 0.22  # -0.22 to +0.23
    tint_r = brightness_mod + 0.08  # warm
    tint_g = brightness_mod
    tint_b = brightness_mod - 0.04  # cool suppress
    blend = 0.75 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_cathedral_glass(paint, shape, mask, seed, pm, bb):
    """Per-pane random hue tinting (stained glass effect). Blend 0.35."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    # Pane regions from low-freq noise
    panes = e.multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 80)
    # Lead line edges
    gy = np.abs(np.diff(panes, axis=0, prepend=panes[:1, :]))
    gx = np.abs(np.diff(panes, axis=1, prepend=panes[:, :1]))
    edge = np.clip((gy + gx) * 8.0, 0, 1)
    # Per-pane hue tint using 3 independent noise fields
    tint_r = e.multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 82)
    tint_g = e.multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 83)
    tint_b = e.multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 84)
    # Pane interiors get hue shift, lead lines darken
    hue_r = tint_r * 0.25 * (1 - edge) - edge * 0.40
    hue_g = tint_g * 0.25 * (1 - edge) - edge * 0.40
    hue_b = tint_b * 0.25 * (1 - edge) - edge * 0.40
    blend = 0.70 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + hue_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + hue_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + hue_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_vintage_enamel_crackle(paint, shape, mask, seed, pm, bb):
    """Cream/ivory enamel with dark brown crack lines. Blend 0.40."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    # Crack network matching spec
    n1 = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 90)
    n2 = e.multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 91)
    stress = e.multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 92)
    stress01 = np.clip((stress + 1) * 0.5, 0, 1)
    crack = np.clip(np.abs(n1) + np.abs(n2) * 0.5, 0, 1)
    crack = np.clip(crack * (1.5 + stress01) - 0.4, 0, 1)
    # Cream tint in enamel areas, dark brown in cracks
    tint_r = 0.12 * (1 - crack) - 0.40 * crack
    tint_g = 0.08 * (1 - crack) - 0.35 * crack
    tint_b = -0.03 * (1 - crack) - 0.28 * crack
    blend = 0.75 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_carbon_weave_micro(paint, shape, mask, seed, pm, bb):
    """Near-black carbon fiber with slight fiber direction sheen. Blend 0.40."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    y, x = e.get_mgrid(shape)
    # Twill weave pattern matching spec
    freq = 80.0
    twill = np.sin(y / max(1, h) * freq) * np.sin((x + y) / max(1, w) * freq * 0.7)
    twill01 = np.clip(twill * 0.5 + 0.5, 0, 1)
    micro = e.multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed + 100)
    micro01 = np.clip((micro + 1) * 0.5, 0, 1)
    # Darken toward carbon black, with fiber sheen variation
    darken = -0.25 - 0.15 * (1 - twill01)
    sheen = twill01 * 0.10 + micro01 * 0.03
    tint = darken + sheen
    blend = 0.75 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    for c in range(3):
        target_c = np.clip(paint[:, :, c] + tint, 0, 1)
        # Replacement blend: fade between base and finish
        result[:, :, c] = paint[:, :, c] * (1 - blend[:, :, 0]) + target_c * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_pearl_depth_layers(paint, shape, mask, seed, pm, bb):
    """Iridescent pearl with multi-harmonic hue shift. Blend 0.35."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    # Three pearl layers for multi-harmonic shift
    layer1 = e.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.25, 0.3, 0.25], seed + 110)
    layer2 = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 111)
    layer3 = e.multi_scale_noise(shape, [16, 32, 64, 128], [0.25, 0.3, 0.25, 0.2], seed + 112)
    # Iridescent hue shift: each layer shifts a different channel
    hue_r = layer1 * 0.25 + layer3 * 0.12
    hue_g = layer2 * 0.20 - layer1 * 0.08
    hue_b = layer3 * 0.25 + layer2 * 0.12
    blend = 0.70 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + hue_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + hue_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + hue_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_hand_brushed_metal(paint, shape, mask, seed, pm, bb):
    """Bronze/copper tone with grain-driven brightness variation. Blend 0.40."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    y, x = e.get_mgrid(shape)
    grain = e.multi_scale_noise(shape, [2, 4, 8, 16, 32], [0.15, 0.2, 0.25, 0.25, 0.15], seed + 120)
    flow_h = np.sin(x / max(1, w) * 60.0 + grain * 3.0) * 0.5 + 0.5
    # Grain-driven brightness with warm bronze/copper tint
    brightness = flow_h * 0.40 - 0.15
    tint_r = brightness + 0.12  # warm red
    tint_g = brightness + 0.03  # slight warm
    tint_b = brightness - 0.06  # cool suppress
    blend = 0.75 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_forged_iron_texture(paint, shape, mask, seed, pm, bb):
    """Dark iron with scale mark brightness variation. Blend 0.45."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    # Scale marks matching spec
    n1 = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 130)
    marks_raw = np.clip((n1 + 1) * 0.5, 0, 1)
    marks = np.clip(marks_raw * 2.0 - 0.5, 0, 1)
    pitting = e.multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed + 132)
    pit01 = np.clip((pitting + 1) * 0.5, 0, 1)
    # Scale marks brighten (polished impact), between darkens (rough oxide)
    brightness = marks * 0.25 - (1 - marks) * 0.20 + pit01 * 0.06
    blend = 0.75 * pm * m3
    result = paint.copy()
    # Target color = paint modified by finish's signature tint
    for c in range(3):
        target_c = np.clip(paint[:, :, c] + brightness, 0, 1)
        # Replacement blend: fade between base and finish
        result[:, :, c] = paint[:, :, c] * (1 - blend[:, :, 0]) + target_c * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_micro_flake_burst(paint, shape, mask, seed, pm, bb):
    """Dense micro flake: sparkle-driven brightness variation over base color. Blend 0.40."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    fine = e.multi_scale_noise(shape, [1, 2, 3, 4, 6, 8, 12, 16], [0.1, 0.12, 0.14, 0.14, 0.15, 0.15, 0.1, 0.1], seed + 1000)
    mid = e.multi_scale_noise(shape, [4, 8, 16], [0.33, 0.34, 0.33], seed + 1001)
    sparkle = np.clip((fine + 1) * 0.5, 0, 1)
    # Sparkle peaks brighten, valleys darken slightly, mid-scale adds variation
    brightness = sparkle ** 2 * 0.40 - (1 - sparkle) * 0.12 + mid * 0.08
    blend = 0.75 * pm * m3
    # Target color = paint modified by finish's signature tint
    for c in range(3):
        target_c = np.clip(paint[:, :, c] + brightness, 0, 1)
        # Replacement blend: fade between base and finish
        result[:, :, c] = paint[:, :, c] * (1 - blend[:, :, 0]) + target_c * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_marble_vein_fine(paint, shape, mask, seed, pm, bb):
    """Fine marble veining: vein-driven tinting with warm stone undertone. Blend 0.38."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    y, x = e.get_mgrid(shape)
    n1 = e.multi_scale_noise(shape, [4, 8, 16, 32, 64], [0.15, 0.2, 0.25, 0.25, 0.15], seed + 1100)
    n2 = e.multi_scale_noise(shape, [2, 6, 12, 24], [0.2, 0.3, 0.3, 0.2], seed + 1101)
    vein = np.sin(y / max(1, h) * 8 + n1 * 5) * np.exp(-np.abs(n2))
    vein = np.clip(vein * 0.5 + 0.5, 0, 1)
    # Veins darken, stone body gets slight warm tint
    tint_r = -0.35 * vein + 0.10 * (1 - vein)
    tint_g = -0.28 * vein + 0.04 * (1 - vein)
    tint_b = -0.22 * vein - 0.03 * (1 - vein)
    blend = 0.75 * pm * m3
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_obsidian_glass(paint, shape, mask, seed, pm, bb):
    """Obsidian glass: fracture-driven darkening with subtle reflection highlights. Blend 0.42."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    n1 = e.multi_scale_noise(shape, [2, 4, 8, 16, 32], [0.2, 0.2, 0.25, 0.2, 0.15], seed + 1200)
    n2 = e.multi_scale_noise(shape, [4, 12, 24], [0.3, 0.4, 0.3], seed + 1201)
    fracture = np.clip(np.abs(n2) * 1.5 - 0.3, 0, 1)
    # Glass body darkens, fracture faces get slight highlight
    brightness = -0.25 * (1 - fracture) + 0.22 * fracture + n1 * 0.10
    blend = 0.70 * pm * m3
    # Target color = paint modified by finish's signature tint
    for c in range(3):
        target_c = np.clip(paint[:, :, c] + brightness, 0, 1)
        # Replacement blend: fade between base and finish
        result[:, :, c] = paint[:, :, c] * (1 - blend[:, :, 0]) + target_c * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_silk_weave(paint, shape, mask, seed, pm, bb):
    """Fine silk weave: thread-driven sheen variation with warm silk tint. Blend 0.38."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    y, x = e.get_mgrid(shape)
    n1 = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.25, 0.25, 0.25, 0.25], seed + 1300)
    weft = np.sin(y / max(1, h) * 100 + n1 * 2) * 0.5 + 0.5
    warp = np.sin(x / max(1, w) * 100 + e.multi_scale_noise(shape, [2, 4, 8], [0.33, 0.33, 0.34], seed + 1301) * 2) * 0.5 + 0.5
    weave = np.clip(weft * warp + 0.2, 0, 1)
    # Silk sheen on thread crests, slight warmth
    tint_r = weave * 0.25 - (1 - weave) * 0.12 + 0.08
    tint_g = weave * 0.18 - (1 - weave) * 0.08
    tint_b = weave * 0.12 - (1 - weave) * 0.08 - 0.04
    blend = 0.75 * pm * m3
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_ceramic_glaze(paint, shape, mask, seed, pm, bb):
    """Ceramic glaze: depth-driven tint with craze darkening. Blend 0.40."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    n1 = e.multi_scale_noise(shape, [16, 32, 64, 128], [0.2, 0.3, 0.3, 0.2], seed + 1400)
    n2 = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.25, 0.25, 0.25, 0.25], seed + 1401)
    depth = np.clip((n1 + 1) * 0.5, 0, 1)
    crazing = np.clip(np.abs(n2) * 1.2 - 0.2, 0, 1)
    # Deep pools get slight cool tint, crazing darkens
    tint_r = -0.12 * depth - 0.32 * crazing + 0.10
    tint_g = 0.15 * depth - 0.25 * crazing
    tint_b = 0.18 * depth - 0.18 * crazing
    blend = 0.70 * pm * m3
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_brushed_titanium(paint, shape, mask, seed, pm, bb):
    """Brushed titanium: grain-driven brightness with cool blue-gray tint. Blend 0.42."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    y, x = e.get_mgrid(shape)
    grain = e.multi_scale_noise(shape, [1, 2, 4, 8, 16, 32], [0.12, 0.15, 0.18, 0.2, 0.2, 0.15], seed + 1500)
    flow = np.sin(x / max(1, w) * 120 + grain * 4) * 0.5 + 0.5
    # Grain peaks brighten, valleys darken, cool blue tint
    brightness = flow * 0.35 - 0.15 + grain * 0.06
    tint_r = brightness - 0.06
    tint_g = brightness
    tint_b = brightness + 0.10
    blend = 0.75 * pm * m3
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_gold_leaf_micro(paint, shape, mask, seed, pm, bb):
    """Gold leaf: patch-driven warm gold tint with crack darkening. Blend 0.40."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    n1 = e.multi_scale_noise(shape, [4, 8, 16, 32, 64], [0.15, 0.2, 0.25, 0.25, 0.15], seed + 1600)
    n2 = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.25, 0.25, 0.25, 0.25], seed + 1601)
    patch = np.clip((n1 + 1) * 0.5, 0, 1)
    crack = np.clip(np.abs(n2) * 1.3 - 0.4, 0, 1)
    # Gold leaf patches get warm golden tint, cracks darken
    tint_r = patch * 0.30 - crack * 0.25 + 0.08
    tint_g = patch * 0.18 - crack * 0.20
    tint_b = patch * -0.15 - crack * 0.12 - 0.06
    blend = 0.75 * pm * m3
    # Target color = paint modified by finish's signature tint
    target_r = np.clip(paint[:, :, 0] + tint_r, 0, 1)
    target_g = np.clip(paint[:, :, 1] + tint_g, 0, 1)
    target_b = np.clip(paint[:, :, 2] + tint_b, 0, 1)
    # Replacement blend: fade between base and finish
    result[:, :, 0] = paint[:, :, 0] * (1 - blend[:, :, 0]) + target_r * blend[:, :, 0]
    result[:, :, 1] = paint[:, :, 1] * (1 - blend[:, :, 0]) + target_g * blend[:, :, 0]
    result[:, :, 2] = paint[:, :, 2] * (1 - blend[:, :, 0]) + target_b * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


def _paint_fluid_metal(paint, shape, mask, seed, pm, bb):
    """Liquid metal: flow-driven brightness variation with cool metallic tint. Blend 0.45."""
    bb = _ensure_bb_2d(bb, shape)
    h, w = shape
    m3 = mask[:, :, np.newaxis]
    e = _engine
    result = paint.copy()
    y, x = e.get_mgrid(shape)
    n1 = e.multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1700)
    n2 = e.multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.25, 0.3, 0.25], seed + 1701)
    flow = np.sin(y / max(1, h) * 6 + n1 * 3) * np.cos(x / max(1, w) * 5 + n2 * 2)
    flow = np.clip(flow * 0.5 + 0.5, 0, 1)
    # Flow crests brighten, troughs darken, slight cool metallic shift
    brightness = flow * 0.40 - 0.18 + n2 * 0.10
    blend = 0.75 * pm * m3
    # Target color = paint modified by finish's signature tint
    for c in range(3):
        target_c = np.clip(paint[:, :, c] + brightness, 0, 1)
        # Replacement blend: fade between base and finish
        result[:, :, c] = paint[:, :, c] * (1 - blend[:, :, 0]) + target_c * blend[:, :, 0]
    result = np.clip(result + bb[:, :, np.newaxis] * 0.4 * m3, 0, 1)
    return result


# ============== Catalog and integration ==============

ATELIER_ENTRIES = [
    ("atelier_japanese_lacquer", "Japanese Lacquer", _spec_japanese_lacquer, _paint_japanese_lacquer),
    ("atelier_engine_turned", "Engine Turned", _spec_engine_turned, _paint_engine_turned),
    ("atelier_damascus_layers", "Damascus Layers", _spec_damascus_layers, _paint_damascus_layers),
    ("atelier_cathedral_glass", "Cathedral Glass", _spec_cathedral_glass, _paint_cathedral_glass),
    ("atelier_vintage_enamel_crackle", "Vintage Enamel Crackle", _spec_vintage_enamel_crackle, _paint_vintage_enamel_crackle),
    ("atelier_carbon_weave_micro", "Carbon Weave Micro", _spec_carbon_weave_micro, _paint_carbon_weave_micro),
    ("atelier_pearl_depth_layers", "Pearl Depth Layers", _spec_pearl_depth_layers, _paint_pearl_depth_layers),
    ("atelier_hand_brushed_metal", "Hand Brushed Metal", _spec_hand_brushed_metal, _paint_hand_brushed_metal),
    ("atelier_forged_iron_texture", "Forged Iron Texture", _spec_forged_iron_texture, _paint_forged_iron_texture),
    ("atelier_micro_flake_burst", "Micro Flake Burst", _spec_micro_flake_burst, _paint_micro_flake_burst),
    ("atelier_marble_vein_fine", "Marble Vein Fine", _spec_marble_vein_fine, _paint_marble_vein_fine),
    ("atelier_obsidian_glass", "Obsidian Glass", _spec_obsidian_glass, _paint_obsidian_glass),
    ("atelier_silk_weave", "Silk Weave", _spec_silk_weave, _paint_silk_weave),
    ("atelier_ceramic_glaze", "Ceramic Glaze", _spec_ceramic_glaze, _paint_ceramic_glaze),
    ("atelier_brushed_titanium", "Brushed Titanium", _spec_brushed_titanium, _paint_brushed_titanium),
    ("atelier_gold_leaf_micro", "Gold Leaf Micro", _spec_gold_leaf_micro, _paint_gold_leaf_micro),
    ("atelier_fluid_metal", "Fluid Metal", _spec_fluid_metal, _paint_fluid_metal),
]


def integrate_atelier(engine_module):
    """Register all Atelier ultra-detail finishes into the engine's MONOLITHIC_REGISTRY."""
    global _engine
    _engine = engine_module
    reg = getattr(engine_module, "MONOLITHIC_REGISTRY", None)
    if reg is None:
        print("[Atelier] MONOLITHIC_REGISTRY not found - skip")
        return 0
    count = 0
    for fid, name, spec_fn, paint_fn in ATELIER_ENTRIES:
        reg[fid] = (spec_fn, paint_fn)
        count += 1
    print(f"[Atelier] Loaded {count} ultra-detail finishes (Pro Grade)")
    return count

"""
engine/paint_v2/mortal_shokkbat.py — ★ MORTAL SHOKK Finishes
Fighting-game-inspired special finishes. Every finish uses a DIFFERENT algorithm.

ALL spatial features scaled for 2048×2048 full-car textures.
ALL rendering fully vectorized — ZERO per-pixel Python loops.
Uses scipy cKDTree + sobel + vectorized numpy throughout.

Seed offsets: 9100-9199.
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import sobel
from engine.core import multi_scale_noise


# ════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════════════

def _ms_micro(shape, seed):
    """Ultra-fine shimmer at 1-3px."""
    m = multi_scale_noise(shape, [1, 2, 3], [0.5, 0.3, 0.2], seed + 300)
    return np.clip(m * 0.5 + 0.5, 0, 1).astype(np.float32)


def _fast_voronoi(shape, n_pts, seed, jittered_grid=False):
    """Fast Voronoi via cKDTree. Returns (cell_id, d1, edge_dist, n_pts, rng)."""
    h, w = shape
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    if jittered_grid:
        grid_n = int(np.sqrt(n_pts)) + 1
        pts_y, pts_x = [], []
        for gy in range(grid_n):
            for gx in range(grid_n):
                by = (gy + 0.5) / grid_n * h
                bx = (gx + 0.5 + (gy % 2) * 0.5) / grid_n * w
                pts_y.append(by + rng.randn() * h / (grid_n * 2.5))
                pts_x.append(bx + rng.randn() * w / (grid_n * 2.5))
        pts = np.column_stack([pts_y, pts_x]).astype(np.float32)
    else:
        pts = np.column_stack([
            rng.uniform(0, h, n_pts), rng.uniform(0, w, n_pts)
        ]).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    grid_pts = np.column_stack([yy.ravel().astype(np.float32),
                                xx.ravel().astype(np.float32)])
    tree = cKDTree(pts)
    d, idx = tree.query(grid_pts, k=2, workers=-1)
    d1 = d[:, 0].reshape(h, w).astype(np.float32)
    d2 = d[:, 1].reshape(h, w).astype(np.float32)
    cell_id = idx[:, 0].reshape(h, w)
    return cell_id, d1, d2 - d1, len(pts), rng


def _fracture_field(shape, seed, n_layers=3):
    """Multi-directional fracture lines. Fully vectorized, no loops."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    cracks = np.zeros((h, w), dtype=np.float32)
    # Pre-generate all layer params
    angles = rng.uniform(0, np.pi, n_layers)
    freqs = rng.uniform(0.08, 0.20, n_layers)
    phases = rng.uniform(0, 2 * np.pi, n_layers)
    strengths = rng.uniform(0.5, 1.0, n_layers)
    for i in range(n_layers):
        rot = xf * np.cos(angles[i]) + yf * np.sin(angles[i])
        warp = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + i * 7)
        line = np.abs(np.sin((rot + warp * 25.0) * freqs[i] + phases[i]))
        cracks = np.maximum(cracks, np.clip((0.06 - line) * 25.0, 0, 1) * strengths[i])
    return cracks.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 01: FROZEN FURY — ANGULAR FRACTURE LINES (3 layers, fast)
# ════════════════════════════════════════════════════════════════════

def paint_ms_frozen_fury(paint, shape, mask, seed, pm, bb):
    """Frozen Fury: multi-directional ice fracture lines. 3 fast noise layers."""
    h, w = shape[:2] if len(shape) > 2 else shape
    cracks = _fracture_field((h, w), seed + 9100, n_layers=3)
    frost = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 9101)
    frost_n = np.clip(frost * 0.4 + 0.5, 0, 1).astype(np.float32)
    ice_blue = np.array([0.10, 0.35, 0.68], dtype=np.float32)
    deep_blue = np.array([0.03, 0.10, 0.40], dtype=np.float32)
    frost_white = np.array([0.88, 0.93, 0.98], dtype=np.float32)
    color = (deep_blue[None, None, :] * (1 - cracks[:, :, None]) * (1 - frost_n[:, :, None]) +
             ice_blue[None, None, :] * (1 - cracks[:, :, None]) * frost_n[:, :, None] +
             frost_white[None, None, :] * cracks[:, :, None] * 0.9 +
             frost_white[None, None, :] * frost_n[:, :, None] * 0.1)
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * 0.90, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1 - m3 * bl) + np.clip(color, 0, 1) * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


def spec_ms_frozen_fury(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    cracks = _fracture_field((h, w), seed + 9100, n_layers=3)
    M = 40.0 + cracks * 205.0 * sm
    R = 100.0 - cracks * 85.0 * sm
    CC = 60.0 - cracks * 44.0
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 02: VENOM STRIKE — CHAIN pattern (vectorized, no loops)
# ════════════════════════════════════════════════════════════════════

def paint_ms_venom_strike(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    yy, xx = np.mgrid[0:h, 0:w]
    yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    cs = max(10, min(h, w) // 80)
    cy = (yf % (cs * 2)) / (cs * 2)
    cx = (xf % (cs * 2)) / (cs * 2)
    ri = (yf // (cs * 2)).astype(np.int32)
    cx_s = np.where(ri % 2 == 0, cx, (cx + 0.5) % 1.0)
    rd = np.sqrt((cy - 0.5)**2 + (cx_s - 0.5)**2)
    chain = np.clip(1.0 - np.abs(rd - 0.3) / 0.06, 0, 1).astype(np.float32)
    rng = np.random.RandomState(seed + 9101)
    embers = np.where(rng.random((h, w)).astype(np.float32) > 0.985,
                      (rng.random((h, w)).astype(np.float32) * 0.5 + 0.5), 0.0).astype(np.float32)
    gold = np.array([0.88, 0.72, 0.15], dtype=np.float32)
    hellfire = np.array([0.06, 0.02, 0.01], dtype=np.float32)
    ember_orange = np.array([0.95, 0.45, 0.05], dtype=np.float32)
    color = np.clip(gold[None, None, :] * chain[:, :, None] +
                    hellfire[None, None, :] * (1 - chain[:, :, None]) +
                    ember_orange[None, None, :] * embers[:, :, None] * 0.5, 0, 1)
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * 0.92, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1 - m3 * bl) + color * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


def spec_ms_venom_strike(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    yy, xx = np.mgrid[0:h, 0:w]
    yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    cs = max(10, min(h, w) // 80)
    cy = (yf % (cs * 2)) / (cs * 2)
    cx = (xf % (cs * 2)) / (cs * 2)
    ri = (yf // (cs * 2)).astype(np.int32)
    cx_s = np.where(ri % 2 == 0, cx, (cx + 0.5) % 1.0)
    chain = np.clip(1.0 - np.abs(np.sqrt((cy-0.5)**2+(cx_s-0.5)**2) - 0.3) / 0.06, 0, 1).astype(np.float32)
    rng = np.random.RandomState(seed + 9101)
    embers = (rng.random((h, w)).astype(np.float32) > 0.985).astype(np.float32)
    M = 5.0 + chain * 237.0 * sm + embers * 200.0 * sm
    R = 210.0 - chain * 195.0 * sm - embers * 180.0 * sm
    CC = 180.0 - chain * 164.0
    return (np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 03: THUNDER LORD — NOISE GRADIENT EDGE lightning (fully vectorized)
# Sobel edge detection on noise creates natural branching bolt networks
# ════════════════════════════════════════════════════════════════════

def _lightning_field(shape, seed):
    """Branching lightning via Sobel edges of domain-warped noise. Zero loops."""
    h, w = shape
    # Large-scale noise with domain warp for branching
    base = multi_scale_noise((h, w), [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed)
    # Sobel edges = natural branching vein network
    ex = sobel(base, axis=1).astype(np.float32)
    ey = sobel(base, axis=0).astype(np.float32)
    edge = np.sqrt(ex**2 + ey**2)
    # Second layer at different scale for finer branches
    fine = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 50)
    fx = sobel(fine, axis=1).astype(np.float32)
    fy = sobel(fine, axis=0).astype(np.float32)
    fine_edge = np.sqrt(fx**2 + fy**2)
    # Combine: main bolts + fine branches
    combined = edge * 0.7 + fine_edge * 0.3
    # Normalize and sharpen
    p95 = np.percentile(combined, 95)
    bolts = np.clip((combined - p95 * 0.6) / (p95 * 0.4 + 1e-8), 0, 1).astype(np.float32)
    # Glow halo via softer threshold
    glow = np.clip((combined - p95 * 0.3) / (p95 * 0.7 + 1e-8), 0, 0.5).astype(np.float32)
    return bolts, glow


def paint_ms_thunder_lord(paint, shape, mask, seed, pm, bb):
    """Thunder Lord: branching lightning networks on dark storm."""
    h, w = shape[:2] if len(shape) > 2 else shape
    bolts, glow = _lightning_field((h, w), seed + 9102)
    storm = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9104)
    storm_n = np.clip(storm * 0.3 + 0.35, 0.1, 0.6).astype(np.float32)
    white_bolt = np.array([0.92, 0.94, 1.00], dtype=np.float32)
    blue_glow = np.array([0.20, 0.40, 0.95], dtype=np.float32)
    storm_dark = np.array([0.03, 0.02, 0.10], dtype=np.float32)
    storm_mid = np.array([0.06, 0.06, 0.18], dtype=np.float32)
    color = np.clip(storm_dark[None, None, :] * (1 - storm_n[:, :, None]) +
                    storm_mid[None, None, :] * storm_n[:, :, None] +
                    blue_glow[None, None, :] * glow[:, :, None] +
                    white_bolt[None, None, :] * bolts[:, :, None], 0, 1)
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * 0.92, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1 - m3 * bl) + color * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


def spec_ms_thunder_lord(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    bolts, glow = _lightning_field((h, w), seed + 9102)
    M = 15.0 + bolts * 240.0 * sm + glow * 120.0 * sm
    R = 160.0 - bolts * 145.0 * sm - glow * 80.0 * sm
    CC = 120.0 - bolts * 104.0 - glow * 50.0
    return (np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 04: CHROME CAGE — metallic GRID (vectorized, no loops)
# ════════════════════════════════════════════════════════════════════

def paint_ms_chrome_cage(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    bs = max(8, min(h, w) // 100)
    yy, xx = np.mgrid[0:h, 0:w]
    yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    warp = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 9106)
    bh = np.clip(1.0 - np.minimum((yf+warp*4)%bs, bs-(yf+warp*4)%bs)/2.0, 0, 1)
    bv = np.clip(1.0 - np.minimum((xf+warp*4)%bs, bs-(xf+warp*4)%bs)/2.0, 0, 1)
    bars = np.clip(np.maximum(bh, bv), 0, 1).astype(np.float32)
    energy = np.clip(multi_scale_noise((h,w),[2,4,8],[0.3,0.4,0.3],seed+9107)*0.5+0.5, 0, 1).astype(np.float32)
    gold = np.array([0.92,0.82,0.35]); green = np.array([0.08,0.65,0.20]); dark = np.array([0.02,0.08,0.03])
    color = np.clip(gold[None,None,:]*bars[:,:,None] + green[None,None,:]*(1-bars[:,:,None])*energy[:,:,None]*0.7 + dark[None,None,:]*(1-bars[:,:,None])*(1-energy[:,:,None]*0.7), 0, 1)
    m3 = mask[:,:,np.newaxis]; bl = np.clip(pm*0.90, 0, 1)
    paint[:,:,:3] = paint[:,:,:3]*(1-m3*bl) + color*m3*bl
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_ms_chrome_cage(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    bs = max(8, min(h, w) // 100)
    yy, xx = np.mgrid[0:h, 0:w]; yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    warp = multi_scale_noise((h,w),[8,16],[0.5,0.5],seed+9106)
    bh = np.clip(1.0-np.minimum((yf+warp*4)%bs,bs-(yf+warp*4)%bs)/2.0,0,1)
    bv = np.clip(1.0-np.minimum((xf+warp*4)%bs,bs-(xf+warp*4)%bs)/2.0,0,1)
    bars = np.clip(np.maximum(bh, bv), 0, 1).astype(np.float32)
    M = 30.0+bars*218.0*sm; R = 100.0-bars*85.0*sm; CC = 60.0-bars*44.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 05: DRAGON FLAME — FIRE gradient (vectorized, no loops)
# ════════════════════════════════════════════════════════════════════

def paint_ms_dragon_flame(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    y_g = np.linspace(0,1,h,dtype=np.float32).reshape(h,1)
    hw = multi_scale_noise((h,w),[4,8,16,32],[0.2,0.3,0.3,0.2],seed+9108)
    f = np.clip(y_g+hw*0.12,0,1).astype(np.float32)
    dr=np.array([0.35,0.02,0.01]); og=np.array([0.90,0.40,0.03]); yl=np.array([0.98,0.85,0.15]); wh=np.array([1.0,0.98,0.80])
    t = f
    c1 = np.where(t[:,:,None]<0.33, dr[None,None,:]*(1-t[:,:,None]*3)+og[None,None,:]*t[:,:,None]*3,
         np.where(t[:,:,None]<0.66, og[None,None,:]*(1-(t[:,:,None]-0.33)*3)+yl[None,None,:]*(t[:,:,None]-0.33)*3,
                  yl[None,None,:]*(1-(t[:,:,None]-0.66)*3)+wh[None,None,:]*(t[:,:,None]-0.66)*3))
    rng = np.random.RandomState(seed+9109)
    sp = np.where(rng.random((h,w)).astype(np.float32)>0.98, rng.uniform(0.5,1.0,(h,w)).astype(np.float32), 0.0)
    c1 = np.clip(c1+sp[:,:,None]*wh[None,None,:]*0.4, 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+c1*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_dragon_flame(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    f = np.clip(np.linspace(0,1,h,dtype=np.float32).reshape(h,1)+multi_scale_noise((h,w),[4,8,16,32],[0.2,0.3,0.3,0.2],seed+9108)*0.12,0,1).astype(np.float32)
    M=30.0+f*220.0*sm; R=180.0-f*165.0*sm; CC=140.0-f*124.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 06: ROYAL EDGE — DAMASCUS STEEL wave-fold (3 layers, vectorized)
# ════════════════════════════════════════════════════════════════════

def _damascus_field(shape, seed, n_layers=3):
    """Damascus steel wave pattern. Minimal loops (just 3 noise layers)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    damascus = np.zeros((h, w), dtype=np.float32)
    for i in range(n_layers):
        angle = i * np.pi / 3 + rng.uniform(-0.2, 0.2)
        freq = 0.15 + i * 0.10
        rot = xf * np.cos(angle) + yf * np.sin(angle)
        warp = multi_scale_noise((h, w), [4, 8, 16], [0.35, 0.4, 0.25], seed + i * 11)
        damascus += (np.sin((rot + warp * 20.0) * freq) * 0.5 + 0.5) * (0.40 - i * 0.08)
    return np.clip(damascus, 0, 1).astype(np.float32)


def paint_ms_royal_edge(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    damascus = _damascus_field((h, w), seed + 9110, n_layers=3)
    grain = np.clip(multi_scale_noise((h,w),[1,2,4],[0.4,0.35,0.25],seed+9111)*0.15+0.5, 0.3, 0.7).astype(np.float32)
    rb=np.array([0.06,0.10,0.48]); bs=np.array([0.72,0.76,0.85]); ds=np.array([0.12,0.14,0.28]); se=np.array([0.85,0.88,0.95])
    color = np.clip(ds[None,None,:]*(1-damascus[:,:,None])*0.5 + rb[None,None,:]*(1-damascus[:,:,None])*0.5 +
                    bs[None,None,:]*damascus[:,:,None]*grain[:,:,None] + se[None,None,:]*damascus[:,:,None]*(1-grain[:,:,None]), 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.90,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_royal_edge(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    d = _damascus_field((h, w), seed + 9110, n_layers=3)
    M=100.0+d*140.0*sm; R=55.0-d*40.0*sm; CC=40.0-d*24.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 07: FERAL GRIN — DIAGONAL SLASH MARKS (noise-based, zero loops)
# Domain-warped diagonal noise thresholds create grouped claw marks
# ════════════════════════════════════════════════════════════════════

def _slash_field(shape, seed):
    """Claw slash marks via diagonal noise thresholds. Fully vectorized."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    # Diagonal coordinate (45° rotation)
    diag = (xf - yf) * 0.7071
    # Domain warp for organic slash shapes
    warp = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed)
    warped_diag = diag + warp * 30.0
    # Fine slash lines (high frequency along diagonal)
    slash_raw = np.abs(np.sin(warped_diag * 0.25))
    slash_lines = np.clip((0.05 - slash_raw) * 25.0, 0, 1).astype(np.float32)
    # Group mask — slashes appear in clusters, not everywhere
    group_noise = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 20)
    group_mask = np.clip(group_noise * 2.0 + 0.3, 0, 1).astype(np.float32)
    slashes = slash_lines * group_mask
    # Drip: vertical streaks from slash areas
    drip_seed = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 40)
    drip_trigger = (slashes > 0.3).astype(np.float32)
    # Cumulative sum downward for drip effect
    drip_raw = np.cumsum(drip_trigger, axis=0).astype(np.float32)
    drip_raw = np.clip(drip_raw / (h * 0.03), 0, 1) * drip_trigger.max(axis=0, keepdims=True)
    drip = np.clip(drip_raw * 0.5 * np.clip(drip_seed * 0.5 + 0.5, 0, 1), 0, 0.6).astype(np.float32)
    return slashes, drip


def paint_ms_feral_grin(paint, shape, mask, seed, pm, bb):
    """Feral Grin: diagonal claw slashes on venomous purple. Toxic green drips."""
    h, w = shape[:2] if len(shape) > 2 else shape
    slashes, drip = _slash_field((h, w), seed + 9112)
    bg = np.clip(multi_scale_noise((h,w),[4,8,16],[0.3,0.4,0.3],seed+9113)*0.15+0.5, 0.3, 0.7).astype(np.float32)
    vp=np.array([0.22,0.03,0.32]); dp=np.array([0.10,0.01,0.15])
    hp=np.array([0.92,0.08,0.45]); wr=np.array([0.70,0.02,0.10]); tg=np.array([0.25,0.85,0.10])
    color = np.clip(vp[None,None,:]*bg[:,:,None]*(1-slashes[:,:,None]) +
                    dp[None,None,:]*(1-bg[:,:,None])*(1-slashes[:,:,None]) +
                    hp[None,None,:]*slashes[:,:,None]*0.7 + wr[None,None,:]*slashes[:,:,None]*0.3 +
                    tg[None,None,:]*drip[:,:,None], 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_feral_grin(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    slashes, drip = _slash_field((h, w), seed + 9112)
    M=35.0+slashes*165.0*sm+drip*80.0*sm; R=130.0-slashes*112.0*sm-drip*60.0*sm; CC=90.0-slashes*74.0-drip*30.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 08: ACID SCALE — Dense Voronoi reptile scales (cKDTree, fast)
# ════════════════════════════════════════════════════════════════════

def paint_ms_acid_scale(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    cell_id, d1, edge_dist, n_pts, rng = _fast_voronoi((h,w), 1200, seed+9113, jittered_grid=True)
    eg = np.clip(1.0-edge_dist/(np.percentile(edge_dist,90)+1e-8)*5.0, 0, 1).astype(np.float32)
    cv = rng.uniform(0,1,n_pts).astype(np.float32)[cell_id]
    dg=np.array([0.05,0.20,0.03]); ol=np.array([0.18,0.30,0.05]); ac=np.array([0.45,0.95,0.15])
    interior = 1.0 - eg
    color = np.clip(dg[None,None,:]*interior[:,:,None]*(1-cv[:,:,None]) + ol[None,None,:]*interior[:,:,None]*cv[:,:,None] + ac[None,None,:]*eg[:,:,None], 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_acid_scale(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    _,_,ed,_,_ = _fast_voronoi((h,w),1200,seed+9113,jittered_grid=True)
    eg = np.clip(1.0-ed/(np.percentile(ed,90)+1e-8)*5.0, 0, 1).astype(np.float32)
    M=30.0+eg*205.0*sm; R=110.0-eg*95.0*sm; CC=70.0-eg*54.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 09: SOUL DRAIN — SPIRAL VORTEX (vectorized modular angle, zero loops)
# ════════════════════════════════════════════════════════════════════

def _spiral_field(shape, seed, n_arms=12, tightness=14.0):
    """Spiral arm field. FULLY VECTORIZED — no arm loop."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    yf = (yy.astype(np.float32) - cy) / max(h, w)
    xf = (xx.astype(np.float32) - cx) / max(h, w)
    radius = np.sqrt(yf**2 + xf**2)
    theta = np.arctan2(yf, xf)
    # Spiral angle
    spiral_angle = theta - tightness * np.log(radius + 0.0005)
    # Modular distance to nearest arm (vectorized, replaces N-arm loop)
    period = 2 * np.pi / n_arms
    nearest = spiral_angle % period
    arm_dist = np.minimum(nearest, period - nearest)
    # cos mapping: 0 at arm center → 1, period/2 at midpoint → 0
    spiral = np.clip(np.cos(arm_dist / (period / 2) * np.pi), 0, 1).astype(np.float32)
    spiral = spiral ** 2.0  # sharpen
    core_dark = np.clip(1.0 - np.exp(-radius * 20.0), 0, 1).astype(np.float32)
    return spiral, core_dark, radius


def paint_ms_soul_drain(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    spiral, core_dark, radius = _spiral_field((h, w), seed + 9114)
    rng = np.random.RandomState(seed + 9114)
    particles = (rng.random((h,w)).astype(np.float32) > (0.997 - spiral * 0.015)).astype(np.float32)
    turb = np.clip(multi_scale_noise((h,w),[2,4,8],[0.3,0.4,0.3],seed+9115)*0.3+0.5, 0, 1).astype(np.float32)
    arm_e = spiral * core_dark * turb
    cr=np.array([0.85,0.06,0.04]); vb=np.array([0.02,0.01,0.02]); pm_c=np.array([0.20,0.04,0.25]); hr=np.array([1.0,0.25,0.10])
    color = np.clip(vb[None,None,:]*(1-arm_e[:,:,None])*(1-particles[:,:,None]) +
                    cr[None,None,:]*arm_e[:,:,None]*0.85 + pm_c[None,None,:]*(1-spiral[:,:,None])*turb[:,:,None]*0.25 +
                    hr[None,None,:]*particles[:,:,None], 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_soul_drain(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    spiral, core_dark, _ = _spiral_field((h, w), seed + 9114)
    arm_e = spiral * core_dark
    rng = np.random.RandomState(seed + 9114)
    particles = (rng.random((h,w)).astype(np.float32) > (0.997-spiral*0.015)).astype(np.float32)
    M=arm_e*230.0*sm+particles*250.0*sm; R=240.0-arm_e*225.0*sm-particles*225.0*sm; CC=220.0-arm_e*204.0-particles*204.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 10: EMERALD SHADOW — VECTORIZED RAYS (modular angle, zero loops)
# ════════════════════════════════════════════════════════════════════

def _ray_field(shape, seed, n_rays=80):
    """Crepuscular rays. FULLY VECTORIZED — no ray loop."""
    h, w = shape
    origin_y, origin_x = -h * 0.1, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    yf, xf = yy.astype(np.float32), xx.astype(np.float32)
    angle = np.arctan2(yf - origin_y, xf - origin_x)
    dist = np.sqrt((yf - origin_y)**2 + (xf - origin_x)**2)
    dist_norm = dist / (np.sqrt(h**2 + w**2) + 1e-8)
    # Rays are roughly evenly spaced in angle space from -0.85 to 0.85 rad
    ang_range = 1.7
    ang_offset = angle - np.pi / 2  # center around pi/2
    ray_spacing = ang_range / n_rays
    # Modular distance to nearest ray (replaces 80-iteration loop!)
    normalized = (ang_offset + 0.85) / ray_spacing
    nearest_dist = np.abs(normalized - np.round(normalized)) * ray_spacing
    # Brightness variation via noise (replaces per-ray random brightness)
    bright_var = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 10)
    bright = np.clip(bright_var * 0.3 + 0.7, 0.4, 1.0).astype(np.float32)
    # Width variation via finer noise
    width_var = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 20)
    avg_width = 0.008
    width = avg_width * np.clip(width_var * 0.3 + 1.0, 0.6, 1.5)
    ray_pattern = np.clip(1.0 - nearest_dist / width, 0, 1) * bright
    rays = ray_pattern * np.clip(1.0 - dist_norm * 0.4, 0.2, 1.0)
    return rays.astype(np.float32)


def paint_ms_emerald_shadow(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    rays = _ray_field((h, w), seed + 9115)
    dapple = np.clip(multi_scale_noise((h,w),[4,8,16],[0.3,0.4,0.3],seed+9116)*0.5+0.3, 0, 0.7).astype(np.float32)
    lit = rays * (1.0 - dapple * 0.4)
    em=np.array([0.05,0.60,0.20]); sd=np.array([0.02,0.06,0.02]); lg=np.array([0.10,0.35,0.08])
    color = np.clip(em[None,None,:]*lit[:,:,None] + lg[None,None,:]*dapple[:,:,None]*(1-lit[:,:,None])*0.4 +
                    sd[None,None,:]*(1-lit[:,:,None])*0.6, 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_emerald_shadow(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    rays = _ray_field((h, w), seed + 9115)
    M=10.0+rays*210.0*sm; R=180.0-rays*162.0*sm; CC=160.0-rays*144.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 11: VOID WALKER — Rift rings + scattered blue energy dots (no loops)
# ════════════════════════════════════════════════════════════════════

def paint_ms_void_walker(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    cy, cx = h*0.45, w*0.55
    yy,xx = np.mgrid[0:h,0:w]; yf,xf = yy.astype(np.float32)-cy, xx.astype(np.float32)-cx
    radius = np.sqrt(yf**2+xf**2)
    rf = 0.12+0.02*np.sin(radius*0.03)
    rs = np.clip(np.abs(np.sin(radius*rf*2*np.pi))**10, 0, 1).astype(np.float32)
    cg = np.clip(np.exp(-radius/(min(h,w)*0.05)), 0, 1).astype(np.float32)
    rng = np.random.RandomState(seed+9117)
    dots = (rng.random((h,w)).astype(np.float32) > (0.9985-rs*0.008-cg*0.01)).astype(np.float32)
    dn = np.clip(multi_scale_noise((h,w),[2,4,8],[0.4,0.35,0.25],seed+9118)*0.3+0.5, 0, 1).astype(np.float32)
    vb=np.array([0.01,0.01,0.02]); rp=np.array([0.28,0.08,0.60]); pb=np.array([0.12,0.30,0.88]); eb=np.array([0.30,0.65,1.00])
    re = rs*dn*0.6
    color = np.clip(vb[None,None,:]*(1-re[:,:,None]-cg[:,:,None]-dots[:,:,None]) +
                    rp[None,None,:]*re[:,:,None] + pb[None,None,:]*cg[:,:,None]*0.7 + eb[None,None,:]*dots[:,:,None], 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.90,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_void_walker(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    cy,cx = h*0.45,w*0.55
    yy,xx = np.mgrid[0:h,0:w]; r = np.sqrt((yy.astype(np.float32)-cy)**2+(xx.astype(np.float32)-cx)**2)
    rs = np.clip(np.abs(np.sin(r*(0.12+0.02*np.sin(r*0.03))*2*np.pi))**10, 0, 1).astype(np.float32)
    cg = np.clip(np.exp(-r/(min(h,w)*0.05)), 0, 1).astype(np.float32)
    rng = np.random.RandomState(seed+9117)
    dots = (rng.random((h,w)).astype(np.float32)>(0.9985-rs*0.008-cg*0.01)).astype(np.float32)
    M=rs*60.0*sm+cg*100.0*sm+dots*252.0*sm; R=252.0-rs*237.0*sm-cg*227.0*sm-dots*237.0*sm; CC=250.0-rs*234.0-cg*220.0-dots*234.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 12: GHOST VAPOR — Smoke wisps (noise only, no loops)
# ════════════════════════════════════════════════════════════════════

def paint_ms_ghost_vapor(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    s1 = np.clip(multi_scale_noise((h,w),[8,16,32],[0.3,0.4,0.3],seed+9118)*0.5+0.5, 0, 1).astype(np.float32)
    s2 = np.clip(multi_scale_noise((h,w),[4,8,16],[0.4,0.35,0.25],seed+9119)*0.5+0.5, 0, 1).astype(np.float32)
    s3 = np.clip(multi_scale_noise((h,w),[2,4,8],[0.5,0.3,0.2],seed+9120)*0.5+0.5, 0, 1).astype(np.float32)
    den = np.clip(s1*0.45+s2*0.35+s3*0.20, 0, 1)
    gaps = np.clip(1.0-(den-0.3)*5.0, 0, 1).astype(np.float32)
    sg=np.array([0.45,0.48,0.52]); cs=np.array([0.80,0.83,0.88]); ds=np.array([0.15,0.16,0.18])
    color = np.clip(sg[None,None,:]*den[:,:,None]*(1-gaps[:,:,None]) + ds[None,None,:]*(1-den[:,:,None])*(1-gaps[:,:,None]) + cs[None,None,:]*gaps[:,:,None], 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.90,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_ghost_vapor(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    s1 = np.clip(multi_scale_noise((h,w),[8,16,32],[0.3,0.4,0.3],seed+9118)*0.5+0.5, 0, 1).astype(np.float32)
    s2 = np.clip(multi_scale_noise((h,w),[4,8,16],[0.4,0.35,0.25],seed+9119)*0.5+0.5, 0, 1).astype(np.float32)
    den = np.clip(s1*0.5+s2*0.5, 0, 1); gaps = np.clip(1.0-(den-0.3)*5.0, 0, 1).astype(np.float32)
    M=30.0+den*70.0*sm+gaps*215.0*sm; R=150.0-den*80.0*sm-gaps*135.0*sm; CC=130.0-gaps*114.0
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 13: SHAPE SHIFT — Dense morphing Voronoi (cKDTree, fast)
# ════════════════════════════════════════════════════════════════════

def paint_ms_shape_shift(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    cell_id,d1,ed,n_pts,rng = _fast_voronoi((h,w), 1600, seed+9121)
    eg = np.clip(1.0-ed/(np.percentile(ed,85)+1e-8)*5.5, 0, 1).astype(np.float32)
    sm_map = rng.randint(0,3,n_pts).astype(np.int32)[cell_id]
    rm=np.array([0.85,0.18,0.10]); gm=np.array([0.10,0.72,0.28]); bm=np.array([0.12,0.18,0.82]); es=np.array([0.78,0.80,0.85])
    ir=(sm_map==0).astype(np.float32); ig=(sm_map==1).astype(np.float32); ib=(sm_map==2).astype(np.float32)
    inn = 1.0-eg
    color = np.clip(rm[None,None,:]*ir[:,:,None]*inn[:,:,None] + gm[None,None,:]*ig[:,:,None]*inn[:,:,None] +
                    bm[None,None,:]*ib[:,:,None]*inn[:,:,None] + es[None,None,:]*eg[:,:,None], 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_shape_shift(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    cell_id,_,ed,n_pts,rng = _fast_voronoi((h,w),1600,seed+9121)
    eg = np.clip(1.0-ed/(np.percentile(ed,85)+1e-8)*5.5, 0, 1).astype(np.float32)
    sm_map = rng.randint(0,3,n_pts).astype(np.int32)[cell_id]
    ir=(sm_map==0).astype(np.float32); ig=(sm_map==1).astype(np.float32); ib=(sm_map==2).astype(np.float32)
    Mc=230.0*ir+160.0*ig+80.0*ib; Rc=15.0*ir+35.0*ig+80.0*ib; Cc=16.0*ir+25.0*ig+50.0*ib
    M=Mc*(1-eg)*sm+245.0*eg*sm; R=Rc*(1-eg)+15.0*eg; CC=Cc*(1-eg)+16.0*eg
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 14: TITAN BRONZE — Craters via cKDTree (zero loops!)
# ════════════════════════════════════════════════════════════════════

def _crater_field(shape, seed, n_craters=350):
    """Hammer crater field using cKDTree nearest-crater lookup. Zero loops."""
    h, w = shape
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    min_dim = min(h, w)
    c_y = rng.uniform(0, h, n_craters).astype(np.float32)
    c_x = rng.uniform(0, w, n_craters).astype(np.float32)
    c_r = rng.uniform(min_dim * 0.004, min_dim * 0.016, n_craters).astype(np.float32)
    # cKDTree: find nearest crater for each pixel in one shot
    pts = np.column_stack([c_y, c_x])
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    grid = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    d, idx = tree.query(grid, k=1, workers=-1)
    d = d.reshape(h, w).astype(np.float32)
    idx = idx.reshape(h, w)
    r = c_r[idx]
    # Interior: parabolic dip within crater radius
    crater = np.clip(1.0 - d / r, 0, 1).astype(np.float32)
    # Rim: ring at crater edge
    rim = np.clip(1.0 - np.abs(d - r) / (r * 0.3), 0, 1).astype(np.float32)
    return crater, rim


def paint_ms_titan_bronze(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    crater, rim = _crater_field((h, w), seed + 9122, n_craters=350)
    patina = np.clip(multi_scale_noise((h,w),[2,4,8,16],[0.2,0.3,0.3,0.2],seed+9123)*0.3+0.5, 0, 1).astype(np.float32)
    bb_c=np.array([0.82,0.62,0.22]); do=np.array([0.25,0.16,0.06]); wb=np.array([0.55,0.40,0.15]); rg=np.array([0.90,0.75,0.30])
    color = np.clip(do[None,None,:]*crater[:,:,None]*0.7 + rg[None,None,:]*rim[:,:,None]*0.8 +
                    wb[None,None,:]*(1-crater[:,:,None])*patina[:,:,None] + bb_c[None,None,:]*(1-crater[:,:,None])*(1-patina[:,:,None])*0.6, 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_titan_bronze(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    crater, rim = _crater_field((h, w), seed + 9122, n_craters=350)
    flat = np.clip(1.0-crater-rim, 0, 1)
    M=180.0*flat*sm+120.0*crater*sm+230.0*rim*sm; R=50.0*flat+100.0*crater+20.0*rim; CC=80.0*flat+60.0*crater+16.0*rim
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))


# ════════════════════════════════════════════════════════════════════
# 15: WAR HAMMER — GEOMETRIC CRACK NETWORK (noise thresholds, no Voronoi)
# ════════════════════════════════════════════════════════════════════

def paint_ms_war_hammer(paint, shape, mask, seed, pm, bb):
    """War Hammer: geometric crack network with blood lava. NOT Voronoi."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # Main cracks via fracture_field (3 layers)
    cracks = _fracture_field((h, w), seed + 9124, n_layers=3)
    # Widen cracks and add micro-cracks for War Hammer look
    micro = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.4, 0.3], seed + 9125)
    micro_c = np.clip((np.abs(micro) - 0.3) * -8.0, 0, 0.3).astype(np.float32)
    cracks = np.clip(cracks + micro_c, 0, 1)
    vein_hot = np.clip(cracks - 0.4, 0, 0.6) / 0.6
    damage = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.4, 0.3], seed + 9126)
    scratches = np.clip(damage * 0.15, -0.08, 0.08).astype(np.float32)
    plate_var = np.clip(damage * 0.3 + 0.5, 0, 1).astype(np.float32)
    ad=np.array([0.07,0.05,0.05]); am=np.array([0.14,0.11,0.11]); br=np.array([0.72,0.05,0.03]); hc=np.array([0.95,0.28,0.05])
    interior = 1.0-cracks
    color = np.clip(ad[None,None,:]*interior[:,:,None]*(1-plate_var[:,:,None]) + am[None,None,:]*interior[:,:,None]*plate_var[:,:,None] +
                    br[None,None,:]*cracks[:,:,None]*(1-vein_hot[:,:,None]) + hc[None,None,:]*vein_hot[:,:,None] + scratches[:,:,None]*0.2, 0, 1)
    m3=mask[:,:,np.newaxis]; bl=np.clip(pm*0.92,0,1)
    paint[:,:,:3]=paint[:,:,:3]*(1-m3*bl)+color*m3*bl
    return np.clip(paint,0,1).astype(np.float32)

def spec_ms_war_hammer(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    cracks = _fracture_field((h, w), seed + 9124, n_layers=3)
    micro = multi_scale_noise((h,w),[1,2,4],[0.3,0.4,0.3],seed+9125)
    cracks = np.clip(cracks+np.clip((np.abs(micro)-0.3)*-8.0, 0, 0.3), 0, 1)
    vh = np.clip(cracks-0.4, 0, 0.6)/0.6
    M=15.0*(1-cracks)*sm+200.0*cracks*sm+40.0*vh*sm; R=200.0*(1-cracks)+15.0*cracks; CC=180.0*(1-cracks)+16.0*cracks
    return (np.clip(M,0,255).astype(np.float32), np.clip(R,15,255).astype(np.float32), np.clip(CC,16,255).astype(np.float32))

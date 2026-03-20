"""
engine/expansions/shokk_patterns.py - SHOKK Pattern Expansion
===============================================================
10 data-stream / glitch / digital-corruption style patterns.
All highly detailed with small-scale features (4-16px) at 2048x2048.
Pure numpy, reproducible via np.random.RandomState(seed).

Each pattern has:
  texture_shokk_xxx(shape, mask, seed, sm) -> dict with pattern_val (float32 0-1)
  paint_shokk_xxx(paint, shape, mask, seed, pm, bb) -> float32 paint array

Author: Shokker Engine - SHOKK Series
"""

import numpy as np
from PIL import Image


# ================================================================
# HELPERS
# ================================================================

def _mgrid(shape):
    return np.mgrid[0:shape[0], 0:shape[1]]


def _noise(shape, scales, weights, seed):
    """Multi-octave noise via PIL resize."""
    h, w = shape
    result = np.zeros((h, w), dtype=np.float32)
    rng = np.random.RandomState(seed)
    for scale, weight in zip(scales, weights):
        sh, sw = max(1, h // scale), max(1, w // scale)
        small = rng.randn(sh, sw).astype(np.float32)
        mn, mx = small.min(), small.max()
        norm = ((small - mn) / (mx - mn + 1e-8) * 255).clip(0, 255).astype(np.uint8)
        img = Image.fromarray(norm).resize((w, h), Image.BILINEAR)
        arr = np.array(img).astype(np.float32) / 255.0
        arr = arr * (mx - mn) + mn
        result += arr * weight
    return result


def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint


def _apply_paint_blend(paint, shape, mask, seed, pm, field, hue_shift=0.0, sat_boost=0.0):
    """Common paint blend: shift hue/brightness based on field intensity and pm."""
    h, w = shape[:2] if len(shape) > 2 else shape
    out = paint[:, :, :3].copy().astype(np.float32)
    if pm == 0.0:
        return out
    f = field[:h, :w]
    # Darken troughs, brighten peaks
    mod = 1.0 + (f - 0.5) * 0.6 * pm
    out *= mod[:, :, np.newaxis]
    # Optional hue shift on bright regions
    if hue_shift != 0.0:
        bright_mask = (f > 0.6).astype(np.float32) * pm
        # Rotate channels slightly for hue effect
        shift_amount = hue_shift * bright_mask
        r, g, b = out[:, :, 0], out[:, :, 1], out[:, :, 2]
        out[:, :, 0] = r * (1 - shift_amount * 0.3) + g * shift_amount * 0.3
        out[:, :, 1] = g * (1 - shift_amount * 0.3) + b * shift_amount * 0.3
        out[:, :, 2] = b * (1 - shift_amount * 0.3) + r * shift_amount * 0.3
    return np.clip(out, 0, 255).astype(np.float32)


# ================================================================
# 1. SHOKK_BITROT — Corrupted binary data blocks with glitch artifacts
# ================================================================

def _compute_bitrot(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)

    # Layer 1: Binary data grid (4px blocks)
    block_size = 4
    rows, cols = h // block_size, w // block_size
    bits = rng.randint(0, 2, (rows, cols)).astype(np.float32)
    binary_grid = np.repeat(np.repeat(bits, block_size, axis=0), block_size, axis=1)[:h, :w]
    result = binary_grid * 0.35

    # Layer 2: Corruption zones — random rectangular regions with scrambled data
    num_corrupt = max(60, h // 20)
    for _ in range(num_corrupt):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        ch = rng.randint(4, max(5, h // 50))
        cw = rng.randint(20, max(21, w // 10))
        y1, y2 = max(0, cy), min(h, cy + ch)
        x1, x2 = max(0, cx), min(w, cx + cw)
        if y1 < y2 and x1 < x2:
            corrupt_data = rng.rand(y2 - y1, x2 - x1).astype(np.float32)
            result[y1:y2, x1:x2] = corrupt_data * rng.uniform(0.5, 1.0)

    # Layer 3: Vertical byte-column degradation bands
    num_bands = rng.randint(8, 20)
    for _ in range(num_bands):
        bx = rng.randint(0, w)
        bw = rng.randint(2, 8)
        x1, x2 = max(0, bx), min(w, bx + bw)
        degradation = rng.uniform(0.3, 0.9)
        result[:, x1:x2] = result[:, x1:x2] * degradation + rng.rand(h, x2 - x1).astype(np.float32) * 0.2

    # Layer 4: Horizontal glitch displacement lines
    num_glitch_lines = max(40, h // 30)
    for _ in range(num_glitch_lines):
        gy = rng.randint(0, h)
        gh = rng.randint(1, 3)
        shift = rng.randint(-40, 40)
        y1, y2 = max(0, gy), min(h, gy + gh)
        result[y1:y2, :] = np.roll(result[y1:y2, :], shift, axis=1) * rng.uniform(0.7, 1.0)

    # Layer 5: Bit-flip noise scatter (single pixel corruption)
    num_flips = max(500, (h * w) // 4000)
    flip_y = rng.randint(0, h, num_flips)
    flip_x = rng.randint(0, w, num_flips)
    result[flip_y, flip_x] = rng.rand(num_flips).astype(np.float32)

    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_bitrot(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_bitrot((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_bitrot(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_bitrot((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.4)


# ================================================================
# 2. SHOKK_PACKET_STORM — Dense data packet headers/payloads as structured blocks
# ================================================================

def _compute_packet_storm(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)

    # Packet rows — each row is a data packet with header + payload
    packet_h = 6  # pixels tall per packet row
    header_w = max(16, w // 40)  # fixed header width
    num_rows = h // packet_h

    for r in range(num_rows):
        y1 = r * packet_h
        y2 = min(h, y1 + packet_h - 1)  # 1px gap between packets
        if y1 >= h:
            break

        # Header block — brighter, fixed width
        hdr_brightness = rng.uniform(0.6, 0.95)
        result[y1:y2, 0:header_w] = hdr_brightness

        # Address field — 8px wide block after header
        addr_w = 8
        addr_val = rng.uniform(0.3, 0.7)
        ax1, ax2 = header_w, min(w, header_w + addr_w)
        result[y1:y2, ax1:ax2] = addr_val

        # Payload — variable length blocks with varying intensities
        pos = header_w + addr_w
        while pos < w:
            block_w = rng.randint(4, 16)
            bx2 = min(w, pos + block_w)
            payload_val = rng.uniform(0.1, 0.8)
            result[y1:y2, pos:bx2] = payload_val
            pos = bx2 + rng.randint(1, 4)  # gap between payload blocks

    # Overlay: Protocol markers — vertical lines at regular intervals
    marker_spacing = max(32, w // 20)
    y_arr, x_arr = _mgrid((h, w))
    markers = ((x_arr % marker_spacing) < 1).astype(np.float32) * 0.5
    result = np.maximum(result, markers)

    # Overlay: Burst regions — dense areas where packets overlap
    num_bursts = rng.randint(8, 20)
    for _ in range(num_bursts):
        by = rng.randint(0, h)
        bx = rng.randint(0, w)
        bh = rng.randint(10, max(11, h // 40))
        bw_val = rng.randint(40, max(41, w // 8))
        by1, by2 = max(0, by), min(h, by + bh)
        bx1, bx2 = max(0, bx), min(w, bx + bw_val)
        burst = rng.rand(by2 - by1, bx2 - bx1).astype(np.float32) * 0.6 + 0.3
        result[by1:by2, bx1:bx2] = np.maximum(result[by1:by2, bx1:bx2], burst)

    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_packet_storm(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_packet_storm((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_packet_storm(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_packet_storm((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.2)


# ================================================================
# 3. SHOKK_HEX_DUMP — Hexadecimal memory dump columns
# ================================================================

def _compute_hex_dump(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)

    # Hex dump layout: address column | hex bytes | ASCII sidebar
    cell_w = 6   # width per hex character cell
    cell_h = 8   # height per row
    addr_cols = 4  # address columns on left
    hex_cols = 32  # hex byte columns
    ascii_cols = 16  # ASCII columns on right
    total_cols = addr_cols + hex_cols + ascii_cols

    # Compute number of visible rows and columns
    vis_rows = h // cell_h
    vis_cols = min(total_cols, w // cell_w)

    for r in range(vis_rows):
        y1 = r * cell_h
        y2 = min(h, y1 + cell_h - 1)
        if y1 >= h:
            break

        for c in range(vis_cols):
            x1 = c * cell_w
            x2 = min(w, x1 + cell_w - 1)
            if x1 >= w:
                break

            if c < addr_cols:
                # Address column — consistent medium brightness
                val = 0.4 + (r % 16) * 0.02
            elif c < addr_cols + hex_cols:
                # Hex bytes — random values simulating memory content
                val = rng.uniform(0.1, 0.9)
            else:
                # ASCII representation — dimmer, more uniform
                val = rng.uniform(0.2, 0.5) if rng.rand() > 0.3 else 0.05

            result[y1:y2, x1:x2] = val

    # Separator lines between sections
    sep1_x = min(w - 1, addr_cols * cell_w)
    sep2_x = min(w - 1, (addr_cols + hex_cols) * cell_w)
    result[:, max(0, sep1_x):min(w, sep1_x + 1)] = 0.6
    result[:, max(0, sep2_x):min(w, sep2_x + 1)] = 0.6

    # Highlight rows — occasional bright rows (changed memory)
    num_highlights = max(10, vis_rows // 8)
    for _ in range(num_highlights):
        hr = rng.randint(0, vis_rows)
        hy1 = hr * cell_h
        hy2 = min(h, hy1 + cell_h)
        result[hy1:hy2, :] = np.clip(result[hy1:hy2, :] * 1.4 + 0.15, 0, 1)

    # Row separator lines (every 16 rows thicker)
    for r in range(0, vis_rows, 16):
        ry = r * cell_h
        if ry < h:
            result[ry:min(h, ry + 1), :] = 0.7

    # Tile if canvas is wider than hex dump width
    dump_w = total_cols * cell_w
    if dump_w < w:
        full = result.copy()
        tiles = w // dump_w + 1
        for t in range(1, tiles):
            offset = t * dump_w
            end = min(w, offset + dump_w)
            src_w = end - offset
            full[:, offset:end] = result[:, :src_w]
        result = full

    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_hex_dump(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_hex_dump((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_hex_dump(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_hex_dump((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.15)


# ================================================================
# 4. SHOKK_SIGNAL_NOISE — Clean signal bands interrupted by noise bursts
# ================================================================

def _compute_signal_noise(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)

    y_arr, x_arr = _mgrid((h, w))
    yf = y_arr.astype(np.float32)
    xf = x_arr.astype(np.float32)

    # Base: Multiple sine wave signals at different frequencies
    signal = np.zeros((h, w), dtype=np.float32)
    num_signals = 12
    for i in range(num_signals):
        freq = rng.uniform(0.01, 0.08)
        phase = rng.uniform(0, 2 * np.pi)
        amplitude = rng.uniform(0.1, 0.3)
        band_y = rng.uniform(0, h)
        band_h = rng.uniform(h * 0.03, h * 0.08)
        wave = np.sin(xf * freq + phase) * amplitude + 0.5
        # Gaussian band mask
        band_mask = np.exp(-0.5 * ((yf - band_y) / band_h) ** 2)
        signal += wave * band_mask

    # Noise bursts — rectangular regions of pure noise
    num_bursts = max(25, h // 40)
    noise_layer = np.zeros((h, w), dtype=np.float32)
    for _ in range(num_bursts):
        ny = rng.randint(0, h)
        nx = rng.randint(0, w)
        nh = rng.randint(8, max(9, h // 60))
        nw = rng.randint(30, max(31, w // 6))
        ny1, ny2 = max(0, ny), min(h, ny + nh)
        nx1, nx2 = max(0, nx), min(w, nx + nw)
        noise_layer[ny1:ny2, nx1:nx2] = rng.rand(ny2 - ny1, nx2 - nx1).astype(np.float32)

    # SNR indicator bars on left edge (8px wide)
    bar_w = 8
    for r in range(0, h, 16):
        ry1, ry2 = r, min(h, r + 14)
        snr_val = rng.uniform(0.2, 0.9)
        result_w = min(w, bar_w)
        signal[ry1:ry2, 0:result_w] = snr_val

    # Horizontal scan reference lines
    scan_period = max(4, h // 200)
    scan_lines = ((y_arr % scan_period) == 0).astype(np.float32) * 0.15

    result = signal * 0.6 + noise_layer * 0.5 + scan_lines
    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_signal_noise(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_signal_noise((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_signal_noise(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_signal_noise((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.5)


# ================================================================
# 5. SHOKK_SCAN_LINE — CRT/VHS scan line effect with line dropout and tracking
# ================================================================

def _compute_scan_line(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)

    y_arr, x_arr = _mgrid((h, w))
    yf = y_arr.astype(np.float32)
    xf = x_arr.astype(np.float32)

    # CRT scanlines — alternating bright/dark with slight intensity variation
    scan_period = 4  # 4px per scanline pair
    scanlines = ((y_arr % scan_period) < 2).astype(np.float32)
    # Add per-line brightness variation
    line_brightness = rng.uniform(0.5, 1.0, h).astype(np.float32).reshape(-1, 1)
    scanlines = scanlines * np.broadcast_to(line_brightness, (h, w))

    # VHS tracking errors — horizontal displacement bands
    num_tracking = max(15, h // 80)
    for _ in range(num_tracking):
        ty = rng.randint(0, h)
        th = rng.randint(2, max(3, h // 100))
        shift = rng.randint(-60, 60)
        ty1, ty2 = max(0, ty), min(h, ty + th)
        scanlines[ty1:ty2, :] = np.roll(scanlines[ty1:ty2, :], shift, axis=1)
        # Brightness distortion at tracking boundary
        scanlines[ty1:ty2, :] *= rng.uniform(0.5, 1.5)

    # Line dropout — random lines go dark
    num_dropout = max(20, h // 60)
    for _ in range(num_dropout):
        dy = rng.randint(0, h)
        dh = rng.randint(1, 3)
        dy1, dy2 = max(0, dy), min(h, dy + dh)
        scanlines[dy1:dy2, :] *= rng.uniform(0.0, 0.2)

    # Color fringing — slight horizontal offset creates RGB separation effect
    fringe = np.zeros((h, w), dtype=np.float32)
    fringe[:, 2:] += scanlines[:, :-2] * 0.15  # shifted copy
    fringe[:, :-2] += scanlines[:, 2:] * 0.1

    # Vertical hold wobble — sine wave horizontal displacement
    wobble_amp = rng.uniform(1, 5)
    wobble_freq = rng.uniform(0.005, 0.02)
    wobble = (np.sin(yf * wobble_freq) * wobble_amp).astype(int)
    for row in range(h):
        scanlines[row, :] = np.roll(scanlines[row, :], int(wobble[row, 0]))

    # Static noise overlay
    static = rng.rand(h, w).astype(np.float32) * 0.08

    result = scanlines * 0.7 + fringe + static
    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_scan_line(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_scan_line((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_scan_line(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_scan_line((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.1)


# ================================================================
# 6. SHOKK_CIPHER — Encrypted data stream with periodic key boundaries
# ================================================================

def _compute_cipher(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)

    # Cipher blocks — 8x8 pixel blocks of pseudorandom intensities
    block_size = 8
    rows = h // block_size + 1
    cols = w // block_size + 1

    # Generate cipher stream
    cipher_data = rng.rand(rows, cols).astype(np.float32)
    cipher_grid = np.repeat(np.repeat(cipher_data, block_size, axis=0), block_size, axis=1)[:h, :w]

    # Key boundaries — every N rows, insert a structured header
    key_interval = max(64, h // 16)
    for ky in range(0, h, key_interval):
        ky1, ky2 = ky, min(h, ky + 4)
        # Key header: alternating high/low blocks (structured, not random)
        for c in range(0, w, 16):
            cx2 = min(w, c + 8)
            cipher_grid[ky1:ky2, c:cx2] = 0.9 if (c // 16) % 2 == 0 else 0.1
        # Key separator line
        if ky2 < h:
            cipher_grid[ky2:min(h, ky2 + 1), :] = 0.95

    # Block cipher mode visual — subtle grid showing block boundaries
    y_arr, x_arr = _mgrid((h, w))
    block_border = ((y_arr % block_size) == 0) | ((x_arr % block_size) == 0)
    border_val = block_border.astype(np.float32) * 0.08

    # Initialization vector — first 16px column is structured
    iv_w = 16
    iv_pattern = np.tile(
        rng.choice([0.2, 0.5, 0.8], size=(h // 4 + 1, 1)),
        (1, iv_w)
    )
    iv_expanded = np.repeat(iv_pattern, 4, axis=0)[:h, :iv_w]
    cipher_grid[:, :min(w, iv_w)] = iv_expanded[:, :min(w, iv_w)]

    # Round markers — small bright dots at regular intervals (cipher round indicators)
    round_spacing = 32
    for ry in range(0, h, round_spacing):
        for rx in range(0, w, round_spacing):
            ry1, ry2 = ry, min(h, ry + 2)
            rx1, rx2 = rx, min(w, rx + 2)
            cipher_grid[ry1:ry2, rx1:rx2] = 0.85

    result = cipher_grid * 0.85 + border_val
    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_cipher(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_cipher((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_cipher(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_cipher((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.3)


# ================================================================
# 7. SHOKK_OVERFLOW — Buffer overflow: orderly data becoming chaotic
# ================================================================

def _compute_overflow(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)

    # Orderly data section — top portion is structured
    cell_h = 6
    cell_w = 10
    rows = h // cell_h
    cols = w // cell_w

    # Generate structured data (orderly ascending values)
    for r in range(rows):
        y1 = r * cell_h
        y2 = min(h, y1 + cell_h - 1)
        # Corruption probability increases with row (overflow point)
        overflow_prob = (r / max(1, rows)) ** 2  # quadratic increase
        for c in range(cols):
            x1 = c * cell_w
            x2 = min(w, x1 + cell_w - 1)
            if rng.rand() < overflow_prob:
                # Corrupted: random noise
                val = rng.rand() * rng.uniform(0.5, 1.0)
            else:
                # Orderly: predictable pattern
                val = ((r * cols + c) % 256) / 256.0
            result[y1:y2, x1:x2] = val

    # Overflow cascade points — sudden transition bands
    num_cascades = rng.randint(3, 8)
    for _ in range(num_cascades):
        cascade_y = rng.randint(h // 4, h)
        cascade_h = rng.randint(4, max(5, h // 80))
        cy1, cy2 = max(0, cascade_y), min(h, cascade_y + cascade_h)
        # Bright overflow marker
        result[cy1:cy2, :] = 0.95
        # Below cascade: more corruption
        corrupt_depth = rng.randint(10, max(11, h // 30))
        cy3 = min(h, cy2 + corrupt_depth)
        if cy2 < cy3:
            result[cy2:cy3, :] = rng.rand(cy3 - cy2, w).astype(np.float32) * 0.8 + 0.1

    # Stack pointer markers — vertical lines that bend at overflow
    num_pointers = rng.randint(4, 10)
    for _ in range(num_pointers):
        px = rng.randint(0, w)
        pw = rng.randint(1, 3)
        bend_y = rng.randint(h // 3, 2 * h // 3)
        px1, px2 = max(0, px), min(w, px + pw)
        # Straight above bend
        result[:bend_y, px1:px2] = np.maximum(result[:bend_y, px1:px2], 0.6)
        # Offset below bend
        offset = rng.randint(-20, 20)
        opx1 = max(0, px + offset)
        opx2 = min(w, opx1 + pw)
        if opx1 < opx2:
            result[bend_y:, opx1:opx2] = np.maximum(result[bend_y:, opx1:opx2], 0.6)

    # Memory fill pattern (0xDEADBEEF) — repeating 8-block pattern in corrupted regions
    pattern = np.array([0.87, 0.93, 0.67, 0.73, 0.75, 0.93, 0.93, 0.60], dtype=np.float32)
    fill_y_start = int(h * 0.7)
    fill_row = np.tile(pattern, w // 8 + 1)[:w]
    for fy in range(fill_y_start, h, cell_h * 2):
        fy2 = min(h, fy + cell_h)
        if rng.rand() > 0.5:
            result[fy:fy2, :] = fill_row[:w] * rng.uniform(0.6, 0.9)

    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_overflow(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_overflow((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_overflow(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_overflow((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.6)


# ================================================================
# 8. SHOKK_KERNEL_PANIC — System crash dump: structured header + cascading corruption
# ================================================================

def _compute_kernel_panic(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)

    # Section 1: System header (top 5%) — bright structured blocks
    header_h = max(20, h // 20)
    # Register dump columns
    reg_w = max(12, w // 30)
    for c in range(0, w, reg_w):
        cx2 = min(w, c + reg_w - 1)
        val = rng.uniform(0.5, 0.95)
        result[0:header_h, c:cx2] = val
    # Header separator
    result[header_h:min(h, header_h + 2), :] = 0.95

    # Section 2: Call stack (5-25%) — structured lines with decreasing brightness
    stack_start = header_h + 2
    stack_end = min(h, int(h * 0.25))
    line_h = 8
    for ly in range(stack_start, stack_end, line_h):
        ly2 = min(h, ly + line_h - 1)
        depth = (ly - stack_start) / max(1, stack_end - stack_start)
        # Address column
        result[ly:ly2, 0:min(w, 40)] = 0.6 - depth * 0.3
        # Function name area
        name_w = rng.randint(40, max(41, w // 4))
        result[ly:ly2, min(w, 44):min(w, 44 + name_w)] = rng.uniform(0.3, 0.7) * (1 - depth * 0.5)
        # Arguments
        arg_start = min(w, 48 + name_w)
        arg_end = min(w, arg_start + rng.randint(20, 80))
        if arg_start < arg_end:
            result[ly:ly2, arg_start:arg_end] = rng.uniform(0.2, 0.5) * (1 - depth * 0.3)

    # Section 3: Memory dump (25-60%) — hex dump with increasing corruption
    dump_start = stack_end
    dump_end = min(h, int(h * 0.6))
    dump_cell = 6
    for dy in range(dump_start, dump_end, dump_cell):
        dy2 = min(h, dy + dump_cell - 1)
        corruption = ((dy - dump_start) / max(1, dump_end - dump_start)) ** 1.5
        for dx in range(0, w, dump_cell):
            dx2 = min(w, dx + dump_cell - 1)
            if rng.rand() < corruption:
                val = rng.rand()  # corrupted
            else:
                val = rng.uniform(0.15, 0.6)  # valid data
            result[dy:dy2, dx:dx2] = val

    # Section 4: Cascading crash (60-100%) — increasingly chaotic
    crash_start = dump_end
    for cy in range(crash_start, h, 2):
        cy2 = min(h, cy + 2)
        chaos = ((cy - crash_start) / max(1, h - crash_start))
        if rng.rand() < chaos * 0.3:
            # Full line glitch
            shift = rng.randint(-100, 100)
            line_data = rng.rand(cy2 - cy, w).astype(np.float32) * (0.3 + chaos * 0.7)
            result[cy:cy2, :] = np.roll(line_data, shift, axis=1)
        else:
            # Partially corrupted line
            result[cy:cy2, :] = rng.rand(cy2 - cy, w).astype(np.float32) * (0.1 + chaos * 0.5)

    # Panic message flash — bright horizontal band repeating
    panic_h = 12
    panic_spacing = max(60, h // 10)
    for py in range(crash_start, h, panic_spacing):
        py2 = min(h, py + panic_h)
        result[py:py2, :] = 0.9

    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_kernel_panic(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_kernel_panic((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_kernel_panic(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_kernel_panic((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.7)


# ================================================================
# 9. SHOKK_ZERO_DAY — Exploit injection: clean data with anomalous insertions
# ================================================================

def _compute_zero_day(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)

    # Base: Clean, orderly data stream — regular 10px columns of uniform blocks
    cell_h = 10
    cell_w = 10
    rows = h // cell_h + 1
    cols = w // cell_w + 1

    # Orderly base: smooth gradient blocks (simulating clean memory)
    base_vals = np.zeros((rows, cols), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            base_vals[r, c] = ((r + c) % 8) / 8.0 * 0.4 + 0.1
    result = np.repeat(np.repeat(base_vals, cell_h, axis=0), cell_w, axis=1)[:h, :w]

    # Grid lines — thin borders between data cells
    y_arr, x_arr = _mgrid((h, w))
    grid = ((y_arr % cell_h) == 0) | ((x_arr % cell_w) == 0)
    result = np.where(grid, 0.25, result)

    # Injection points — precisely placed anomalous data
    num_injections = rng.randint(15, 30)
    for _ in range(num_injections):
        # Each injection is a small, bright, structured anomaly
        iy = rng.randint(0, h)
        ix = rng.randint(0, w)

        # Injection type: NOP sled, shellcode, or return address
        inj_type = rng.randint(0, 3)

        if inj_type == 0:
            # NOP sled — uniform brightness strip
            sled_len = rng.randint(20, max(21, w // 10))
            sled_h = rng.randint(2, 6)
            iy1, iy2 = max(0, iy), min(h, iy + sled_h)
            ix1, ix2 = max(0, ix), min(w, ix + sled_len)
            result[iy1:iy2, ix1:ix2] = 0.75  # uniform NOP value

        elif inj_type == 1:
            # Shellcode — dense random data block
            sc_w = rng.randint(16, max(17, w // 20))
            sc_h = rng.randint(4, 12)
            iy1, iy2 = max(0, iy), min(h, iy + sc_h)
            ix1, ix2 = max(0, ix), min(w, ix + sc_w)
            shellcode = rng.rand(iy2 - iy1, ix2 - ix1).astype(np.float32) * 0.5 + 0.5
            result[iy1:iy2, ix1:ix2] = shellcode

        else:
            # Return address — 4-byte bright marker
            ra_w = 4
            ra_h = cell_h
            iy1, iy2 = max(0, iy), min(h, iy + ra_h)
            ix1, ix2 = max(0, ix), min(w, ix + ra_w)
            result[iy1:iy2, ix1:ix2] = 0.95  # bright return address

    # Payload activation traces — thin bright lines connecting injection points
    num_traces = rng.randint(5, 12)
    for _ in range(num_traces):
        ty = rng.randint(0, h)
        tx1 = rng.randint(0, w // 2)
        tx2 = rng.randint(w // 2, w)
        result[ty:min(h, ty + 1), tx1:tx2] = 0.85

    # Canary values — periodic bright markers in the clean regions
    canary_spacing_y = max(40, h // 20)
    canary_spacing_x = max(60, w // 15)
    for cy in range(0, h, canary_spacing_y):
        for cx in range(0, w, canary_spacing_x):
            cy1, cy2 = cy, min(h, cy + 3)
            cx1, cx2 = cx, min(w, cx + 3)
            result[cy1:cy2, cx1:cx2] = 0.65

    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_zero_day(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_zero_day((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_zero_day(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_zero_day((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.35)


# ================================================================
# 10. SHOKK_FIREWALL — Network defense grid with probe/breach scatter
# ================================================================

def _compute_firewall(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)

    y_arr, x_arr = _mgrid((h, w))

    # Defense grid — primary horizontal barrier lines
    barrier_spacing = max(16, h // 64)
    barrier_lines = ((y_arr % barrier_spacing) < 2).astype(np.float32) * 0.6

    # Secondary vertical barrier lines (cross-hatched defense)
    vert_spacing = max(16, w // 64)
    vert_lines = ((x_arr % vert_spacing) < 2).astype(np.float32) * 0.45

    # Grid nodes — bright intersection points
    nodes = (((y_arr % barrier_spacing) < 3) & ((x_arr % vert_spacing) < 3)).astype(np.float32) * 0.8

    result = barrier_lines + vert_lines + nodes

    # Probe attempts — small scattered dots around the grid (attack attempts)
    num_probes = max(200, (h * w) // 8000)
    probe_y = rng.randint(0, h, num_probes)
    probe_x = rng.randint(0, w, num_probes)
    for i in range(num_probes):
        py, px = probe_y[i], probe_x[i]
        radius = rng.randint(1, 4)
        py1, py2 = max(0, py - radius), min(h, py + radius)
        px1, px2 = max(0, px - radius), min(w, px + radius)
        probe_intensity = rng.uniform(0.3, 0.8)
        result[py1:py2, px1:px2] = np.maximum(result[py1:py2, px1:px2], probe_intensity)

    # Breach zones — regions where the grid is broken/brightened
    num_breaches = rng.randint(5, 15)
    for _ in range(num_breaches):
        bx = rng.randint(0, w)
        by = rng.randint(0, h)
        br = rng.randint(8, max(9, min(h, w) // 40))
        # Circular breach with radial falloff
        by1, by2 = max(0, by - br), min(h, by + br)
        bx1, bx2 = max(0, bx - br), min(w, bx + br)
        local_y = np.arange(by1, by2).reshape(-1, 1).astype(np.float32)
        local_x = np.arange(bx1, bx2).reshape(1, -1).astype(np.float32)
        dist = np.sqrt((local_y - by) ** 2 + (local_x - bx) ** 2)
        breach_val = np.clip(1.0 - dist / br, 0, 1) * 0.9
        result[by1:by2, bx1:bx2] = np.maximum(result[by1:by2, bx1:bx2], breach_val)

    # Firewall rules — periodic brighter horizontal bands (active rules)
    rule_spacing = max(40, h // 20)
    for ry in range(0, h, rule_spacing):
        ry2 = min(h, ry + 3)
        rule_brightness = rng.uniform(0.5, 0.85)
        result[ry:ry2, :] = np.maximum(result[ry:ry2, :], rule_brightness)

    # Port scan traces — thin vertical streaks
    num_scans = rng.randint(10, 25)
    for _ in range(num_scans):
        sx = rng.randint(0, w)
        sw = rng.randint(1, 3)
        scan_start = rng.randint(0, h // 2)
        scan_end = rng.randint(h // 2, h)
        sx1, sx2 = max(0, sx), min(w, sx + sw)
        result[scan_start:scan_end, sx1:sx2] = np.maximum(
            result[scan_start:scan_end, sx1:sx2],
            rng.uniform(0.3, 0.5)
        )

    return np.clip(result, 0, 1).astype(np.float32)


def texture_shokk_firewall(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _compute_firewall((h, w), seed)
    return {"pattern_val": field, "R_range": 1.0, "M_range": 1.0, "CC": None}


def paint_shokk_firewall(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    field = _compute_firewall((h, w), seed)
    return _apply_paint_blend(paint, (h, w), mask, seed, pm, field, hue_shift=0.25)


# ================================================================
# PATTERN REGISTRY DICT — for integration into engine registry
# ================================================================

SHOKK_PATTERNS = {
    "shokk_bitrot": {
        "texture_fn": texture_shokk_bitrot,
        "paint_fn": paint_shokk_bitrot,
        "variable_cc": False,
        "desc": "Corrupted binary data blocks with random degradation and glitch artifacts",
    },
    "shokk_packet_storm": {
        "texture_fn": texture_shokk_packet_storm,
        "paint_fn": paint_shokk_packet_storm,
        "variable_cc": False,
        "desc": "Dense data packet headers and payloads as structured blocks with address fields",
    },
    "shokk_hex_dump": {
        "texture_fn": texture_shokk_hex_dump,
        "paint_fn": paint_shokk_hex_dump,
        "variable_cc": False,
        "desc": "Hexadecimal memory dump visualization with address and ASCII columns",
    },
    "shokk_signal_noise": {
        "texture_fn": texture_shokk_signal_noise,
        "paint_fn": paint_shokk_signal_noise,
        "variable_cc": False,
        "desc": "Digital signal-to-noise ratio with clean bands interrupted by noise bursts",
    },
    "shokk_scan_line": {
        "texture_fn": texture_shokk_scan_line,
        "paint_fn": paint_shokk_scan_line,
        "variable_cc": False,
        "desc": "CRT/VHS scan line effect with line dropout and tracking errors",
    },
    "shokk_cipher": {
        "texture_fn": texture_shokk_cipher,
        "paint_fn": paint_shokk_cipher,
        "variable_cc": False,
        "desc": "Encrypted data stream with pseudorandom blocks and key boundary markers",
    },
    "shokk_overflow": {
        "texture_fn": texture_shokk_overflow,
        "paint_fn": paint_shokk_overflow,
        "variable_cc": False,
        "desc": "Buffer overflow — orderly data cascading into chaos at overflow points",
    },
    "shokk_kernel_panic": {
        "texture_fn": texture_shokk_kernel_panic,
        "paint_fn": paint_shokk_kernel_panic,
        "variable_cc": False,
        "desc": "System crash dump with structured header and cascading memory corruption",
    },
    "shokk_zero_day": {
        "texture_fn": texture_shokk_zero_day,
        "paint_fn": paint_shokk_zero_day,
        "variable_cc": False,
        "desc": "Exploit injection — clean data with precisely placed anomalous insertion points",
    },
    "shokk_firewall": {
        "texture_fn": texture_shokk_firewall,
        "paint_fn": paint_shokk_firewall,
        "variable_cc": False,
        "desc": "Network defense grid with probe attempts and breach scatter marks",
    },
}


def integrate_shokk(pattern_registry):
    """Merge SHOKK patterns into the engine pattern registry."""
    pattern_registry.update(SHOKK_PATTERNS)
    print(f"[SHOKK] Loaded {len(SHOKK_PATTERNS)} data-stream/glitch patterns")
    return len(SHOKK_PATTERNS)

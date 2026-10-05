"""Sock Hop Formica Boomerang I2 — fine 1950s countertop laminate.

SPB-105 / owner scale audit, 2026-08-29. Replaces a six-across macro motif
with a small printed laminate made of 7–15px engineered inlays.
"""
import numpy as np

from engine.core import get_mgrid


def _field(shape):
    h, w = shape[:2]
    g = get_mgrid((h, w)); y, x = g[0].astype(np.float32), g[1].astype(np.float32)
    per = max(h, w) / 21.8
    fx, fy = (x / per) % 1.0 - .5, (y / per) % 1.0 - .5
    ix, iy = np.floor(x / per).astype(np.int32), np.floor(y / per).astype(np.int32)
    parity = ((ix + iy) & 1).astype(np.float32)
    a = (parity - .5) * np.pi / 2; ca, sa = np.cos(a), np.sin(a)
    u, v = fx * ca + fy * sa, -fx * sa + fy * ca
    def arc(offset, shift, width):
        return np.clip((width - np.abs(v - (.42 * (u - shift) ** 2 + offset))) / (.65 * width), 0, 1) * np.clip((.38 - np.abs(u - shift)) / .10, 0, 1)
    black, teal, coral = arc(-.20, -.06, .052), arc(.01, .06, .046), arc(.21, -.02, .043)
    terminal = np.maximum(np.clip(1-np.sqrt(((u-.30)/.052)**2+((v+.14)/.052)**2),0,1),
                          np.clip(1-np.sqrt(((u+.28)/.050)**2+((v-.17)/.050)**2),0,1))
    seam = np.clip((.032 - np.abs(v + .33 + (parity-.5)*.13)) / .022, 0, 1)
    return black, teal, coral, terminal, seam, parity


def _mix(base, color, alpha):
    alpha = np.clip(alpha, 0, 1)[:, :, None]
    return base * (1-alpha) + np.asarray(color, np.float32)[None, None, :] * alpha


def _apply(paint, mask, color):
    if mask is not None and mask.size and float(mask.min()) >= .999:
        return np.ascontiguousarray(color, dtype=np.float32)
    if paint.ndim == 3 and paint.shape[2] > 3: paint=paint[:,:,:3].copy()
    return (color * mask[:,:,None] + paint * (1-mask[:,:,None])).astype(np.float32)


def paint_formica_boomerang(paint, shape, mask, seed, pm, bb):
    del seed, pm, bb
    black, teal, coral, terminal, seam, parity = _field(shape)
    h, w = shape[:2]; base=np.empty((h,w,3),np.float32); base[:]=(.90,.86,.74)
    # Alternating cream print lots are quiet in base paint but intentionally
    # distinguish adjacent stations under light—material, never grain.
    base=_mix(base,(.82,.78,.68),parity*.16)
    for field, color in ((seam,(.76,.69,.55)), (black,(.08,.09,.10)), (teal,(.06,.48,.52)),
                         (coral,(.88,.24,.16)), (terminal,(.92,.67,.20))):
        base=_mix(base,color,field)
    return _apply(paint,mask,base)


def spec_formica_boomerang(shape, seed, sm, base_m, base_r):
    del seed, base_m, base_r
    black, teal, coral, terminal, seam, parity = _field(shape)
    # Per-station print-run lacquer state plus independent inlay responses:
    # black satin, teal enamel, coral pigment, gold terminal and beige seam.
    M=24+62*parity+225*np.clip(.25*black+.24*teal+.22*coral+.17*terminal+.12*seam,0,1)*sm
    R=232-76*(1-parity)-188*np.clip(.29*black+.24*teal+.19*coral+.16*seam,0,1)
    CC=16+54*parity+232*np.clip(.27*black+.25*teal+.19*coral+.17*terminal+.12*seam,0,1)
    return tuple(np.clip(a,0,255).astype(np.float32) for a in (M,R,CC))

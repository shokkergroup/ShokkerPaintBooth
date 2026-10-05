"""Sock Hop Googie Orbit I3 — isolated owner-scale replacement.

SPB-105 / owner feedback 2026-08-29: the prior six-across orbit panels were
too large for a 2048² whole-car carrier.  This module deliberately keeps the
Googie/Sputnik language but makes it a complete Atomic-age silkscreen surface.
"""
import numpy as np

from engine.core import get_mgrid


def _field(shape):
    h, w = shape[:2]
    grid = get_mgrid((h, w))
    y, x = grid[0].astype(np.float32), grid[1].astype(np.float32)
    # 16x16 composed stations. The visible strokes and marks themselves are
    # 7–21px at 2048²: rail, pin, dial and pinwheel—not a macro-icon recipe.
    per = max(h, w) / 16.25
    fx, fy = (x / per) % 1.0 - .5, (y / per) % 1.0 - .5
    ix, iy = np.floor(x / per).astype(np.int32), np.floor(y / per).astype(np.int32)
    parity = ((ix + iy) & 1).astype(np.float32)
    a = (parity - .5) * .52; ca, sa = np.cos(a), np.sin(a)
    ex, ey = fx * ca + fy * sa, -fx * sa + fy * ca
    r1 = np.sqrt((ex / .39) ** 2 + (ey / .19) ** 2)
    r2 = np.sqrt(((ex + .08) / .265) ** 2 + ((ey - .02) / .115) ** 2)
    rail_a = np.clip((.061 - np.abs(r1 - 1.0)) / .043, 0, 1)
    rail_b = np.clip((.053 - np.abs(r2 - 1.0)) / .038, 0, 1)
    rr, th = np.sqrt(fx * fx + fy * fy), np.arctan2(fy, fx)
    pinwheel = np.clip((.034 - np.abs(np.sin(th * 4.0))) / .026, 0, 1) * np.clip((.205 - rr) / .105, 0, 1)
    hub = np.clip(1 - rr / .073, 0, 1)
    red_pin = np.clip(1 - np.sqrt(((fx - .305) / .061) ** 2 + ((fy + .11) / .061) ** 2), 0, 1)
    gold_pin = np.clip(1 - np.sqrt(((fx + .23) / .052) ** 2 + ((fy - .135) / .052) ** 2), 0, 1)
    dial = np.clip((.040 - np.abs(np.sin(th * 8.0 + .35))) / .026, 0, 1) * np.clip((.335 - rr) / .08, 0, 1) * np.clip((rr - .27) / .06, 0, 1)
    plate = np.clip((.052 - np.abs(fy + .31 - (parity - .5) * .14)) / .036, 0, 1)
    return rail_a, rail_b, pinwheel, hub, red_pin, gold_pin, dial, plate, parity


def _mix(base, color, alpha):
    alpha = np.clip(alpha, 0, 1)[:, :, None]
    return base * (1 - alpha) + np.asarray(color, np.float32)[None, None, :] * alpha


def _apply(paint, mask, color):
    if mask is not None and mask.size and float(mask.min()) >= .999:
        return np.ascontiguousarray(color, dtype=np.float32)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return (color * mask[:, :, None] + paint * (1 - mask[:, :, None])).astype(np.float32)


def paint_googie_orbit(paint, shape, mask, seed, pm, bb):
    rail_a, rail_b, pinwheel, hub, red_pin, gold_pin, dial, plate, parity = _field(shape)
    h, w = shape[:2]
    # I3.1 owner-eye refinement: I3's true midnight stock swallowed the
    # precisely built orbit work in the catalog tile. Lift the printed navy,
    # not the geometry, so its small-scale Googie language survives.
    base = np.empty((h, w, 3), np.float32); base[:] = (.060, .095, .135)
    # Alternating print-run ground is deliberately subtle in paint, but it
    # gives each little station its own lacquer response under moving light.
    base = _mix(base, (.095, .150, .205), parity * .34)
    for field, color in ((plate, (.11,.18,.25)), (rail_a, (.14,.86,.88)), (rail_b, (.82,.36,.74)),
                         (pinwheel, (.98,.76,.23)), (hub, (1.,.92,.53)), (red_pin, (.98,.21,.12)),
                         (gold_pin, (.98,.68,.16)), (dial, (.48,.96,.97))):
        base = _mix(base, color, field)
    return _apply(paint, mask, base)


def spec_googie_orbit(shape, seed, sm, base_m, base_r):
    rail_a, rail_b, pinwheel, hub, red_pin, gold_pin, dial, plate, parity = _field(shape)
    # M/R/Cc are deliberately distinct physical responses, never a shared scalar.
    # Two neighbouring ink-lacquer lots alternate beneath the tiny station
    # geometry. Their offsets are physical screenprint states, so the field
    # gains the owner-requested per-grid Fractured contrast without confetti.
    M = 18 + 70*parity + 237 * np.clip(.31*rail_a + .25*rail_b + .15*pinwheel + .10*red_pin + .09*gold_pin + .06*dial + .04*plate, 0, 1) * sm
    R = 236 - 76*(1-parity) - 202 * np.clip(.25*rail_a + .30*rail_b + .13*plate + .12*red_pin + .10*gold_pin + .10*hub, 0, 1)
    CC = 14 + 58*parity + 240 * np.clip(.28*rail_a + .22*rail_b + .20*pinwheel + .12*dial + .10*red_pin + .08*plate, 0, 1)
    return tuple(np.clip(a, 0, 255).astype(np.float32) for a in (M, R, CC))

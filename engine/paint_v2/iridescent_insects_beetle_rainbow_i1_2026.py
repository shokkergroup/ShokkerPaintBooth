"""Chrysochroa Ribbon I1 — polarized multilayer elytral ribbons.

SPB-105 / owner 2026-09-01.  Research basis: Chrysochroa fulgidissima has
an approximately flat, strongly specular multilayer epicuticle; green and
purple regions use roughly 16 and 12 optical layers, with red/orange border
transitions and a blue-shift under oblique illumination.  This renderer turns
that anatomy into 8-20px flowing ribbons, lamellar crosscuts, border lips,
melanin grooves and aligned wax pores.  It shares no carrier with Beetle Jewel.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, h2, n01

GEN = 1024


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape)
    if a.shape[:2] == (h, w):
        return np.asarray(a, np.float32)
    return cv2.resize(np.asarray(a, np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask * pm * .94, 0, 1)[:, :, None]
    paint[:, :, :3] = paint[:, :, :3] * (1-a) + np.clip(colour, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    # Long, locally bent elytral growth direction.  The phase warp is slow;
    # individual 7.6px generator ribbons become ~15px on the native canvas.
    bend = (12.0*np.sin(y/91.0+seed*.011+.55*np.sin(x/167.0))
            + 5.5*np.sin((x+y)/137.0-seed*.017)
            + 3.8*np.cos((x-2*y)/211.0))
    u = x*.76 + y*.22 + bend
    v = y*.82 - x*.18
    lane = np.floor(u/7.6)
    frac = np.mod(u/7.6, 1.0)
    centre = np.clip(1.0-np.abs(frac-.5)*5.2, 0, 1)
    shoulder = np.clip(1.0-np.abs(np.abs(frac-.5)-.285)*10.0, 0, 1)
    groove = np.clip((np.abs(frac-.5)-.405)*11.0, 0, 1)

    # Ten-layer optical cadence drifts slowly along each ribbon.  This is a
    # continuous multilayer-thickness system, not ten repeated paint stripes.
    layer_phase = np.mod((lane + 1.18*np.sin(v/91.0+lane*.031)
                          + .62*np.sin(v/37.0+lane*.19))/12.0, 1.0)
    long_phase = n01(np.sin(v/63.0+lane*.31)+.48*np.cos(v/127.0-lane*.17))
    # Irregular longitudinal purple domains. Incommensurate wavelengths make
    # bands widen, fork and merge without random placement or a repeat tile.
    stripe_field=n01(np.sin(u/47.0+.35*np.sin(v/173.0))
                     +.63*np.sin(u/73.0-v/311.0+seed*.021)
                     +.37*np.cos(u/29.0+v/257.0))
    polar_m = n01(np.sin(v/47.0+lane*.53)+.55*np.cos(v/109.0+lane*.13))
    polar_r = n01(np.cos(v/71.0-lane*.37)+.62*np.sin(v/139.0+lane*.29))
    polar_c = n01(np.sin(v/101.0+lane*.23)+.58*np.cos(v/41.0-lane*.43))

    # Fine transverse lamellae and aligned wax pores belong to each ribbon.
    lamella = np.clip((np.sin(v*np.pi/4.7 + lane*.71)*.5+.5-.46)*7.0, 0, 1) * centre
    pore_row = np.floor(v/10.5)
    pore_phase = np.mod(v, 10.5)-5.25
    lateral = (frac-.5)*7.6
    pore_gate = np.clip((h2(lane, pore_row, int(seed)+503)-.73)*4.2, 0, 1)
    pore = np.clip(1.0-(pore_phase/1.45)**2-(lateral/1.25)**2, 0, 1)**2 * pore_gate
    return tuple(np.asarray(a, np.float32) for a in (
        layer_phase, long_phase, stripe_field, centre, shoulder, groove, lamella, pore,
        polar_m, polar_r, polar_c,
    ))


def paint_beetle_rainbow_i1(paint, shape, mask, seed, pm, bb):
    phase, long_phase, stripe_field, centre, shoulder, groove, lamella, pore, pmf, prf, pcf = _surface(seed+9401)
    # P2 research correction: the real shell is primarily metallic green,
    # interrupted by longitudinal purple regions with red/orange borders.  The
    # optical phase remains continuous, but the paint no longer cycles through
    # an equal rainbow on every ribbon.
    green_t=np.clip(.18+.58*long_phase+.24*np.sin(phase*np.pi)**2,0,1)
    green_dark=np.array([.006,.055,.035],np.float32)
    green_bright=np.array([.22,.72,.16],np.float32)
    col=green_dark[None,None,:]*(1-green_t[...,None])+green_bright[None,None,:]*green_t[...,None]
    gold=np.clip((green_t-.64)*2.9,0,1)*(1-np.clip((phase-.52)*3.0,0,1))
    col+=gold[...,None]*np.array([.48,.29,.025],np.float32)
    # Aperiodic purple regions and copper transition lips; the field remains
    # longitudinal but never repeats at a fixed twelve-ribbon interval.
    purple=np.clip((stripe_field-.665)*5.1,0,1)
    border=np.clip(1.0-np.abs(stripe_field-.635)*25.0,0,1)
    purple_col=(np.array([.12,.008,.42],np.float32)[None,None,:]*(1-long_phase[...,None])
                +np.array([.46,.018,.30],np.float32)[None,None,:]*long_phase[...,None])
    col=col*(1-purple[...,None]) + purple_col*purple[...,None]
    col+=border[...,None]*np.array([.72,.17,.018],np.float32)
    # Specular ridge, copper border lip, melanin groove, layer crosscut, pore.
    col *= .48 + centre[...,None]*.52
    col += centre[...,None]*np.array([.10,.14,.055],np.float32)
    col += shoulder[...,None]*np.array([.17,.055,.018],np.float32)
    col *= 1.0-groove[...,None]*.68
    col += lamella[...,None]*np.array([.19,.15,.055],np.float32)
    col *= 1.0-pore[...,None]*.55

    # Recover crisp native lamellae and grooves after enlargement.
    col_hi = _resize(np.clip(col,0,1), shape)
    lam_hi = _resize(lamella,shape); groove_hi=_resize(groove,shape)
    shoulder_hi=_resize(shoulder,shape); pore_hi=_resize(pore,shape)
    col_hi += np.clip((lam_hi-.42)*5.0,0,1)[...,None]*np.array([.13,.11,.035],np.float32)
    col_hi += shoulder_hi[...,None]*np.array([.075,.018,.006],np.float32)
    col_hi *= 1.0-np.clip((groove_hi-.30)*4.4,0,1)[...,None]*.34-pore_hi[...,None]*.27
    return _blend(paint, mask, pm, np.clip(col_hi,0,1))


def spec_beetle_rainbow_i1(shape, seed, sm, base_m, base_r):
    phase, long_phase, stripe_field, centre, shoulder, groove, lamella, pore, pmf, prf, pcf = _surface(seed+9401)
    # Independently phased, pattern-bound channels: smooth 16-layer green
    # ridges, slightly rougher 12-layer purple ribbons, high-Cc transition lips.
    m = 55 + 155*(.58*pmf+.24*centre+.18*np.sin((phase+long_phase)*np.pi)**2)
    r = 38 + 130*(.58*prf+.24*groove+.18*(1-lamella))
    cc = 8 + 235*(.52*pcf+.25*shoulder+.15*lamella+.08*centre)
    m += shoulder*21-groove*33-pore*28
    r += groove*31+pore*38-centre*22
    cc += shoulder*42+lamella*24-groove*31-pore*24
    m += stripe_field*18; r += stripe_field*12; cc += stripe_field*21
    m=np.clip(m*sm,0,235); r=np.clip(r,20,210); cc=np.clip(cc,0,255)
    return _resize(m,shape), _resize(r,shape), _resize(cc,shape)

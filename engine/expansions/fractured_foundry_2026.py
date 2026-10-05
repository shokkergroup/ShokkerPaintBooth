# -*- coding: utf-8 -*-
"""FRACTURED FOUNDRY (2026-08-30) — worked metal: the mark the process left.

Owner mandate 2026-08-30: *"THEN also build out FRACTURED FOUNDRY with 50 of its
own finishes because I like the idea so much. Masculine, industrial."*

Every finish is a SURFACE, not a pattern: a height field a real process leaves
behind — a tool, a hammer, an arc, a pour, a chemical bath — shaded through the
anisotropic metal model in the kit and tinted by what the heat did to it.

CATEGORY LAW (binding on all 50):
  1. one PROCESS per finish, and the finish is named for it;
  2. the tooling has a DIRECTION, and the highlight stretches along it — that
     anisotropy is what makes metal read as metal instead of as plastic;
  3. THE TOOTH LAW: two scales minimum, the process mark and the mill tooth
     under it;
  4. no jewel colour. FOUNDRY is greys, blacks, oxide blues, straw, copper and
     heat colour. Chroma comes from temper, tarnish and coating — never paint;
  5. 8-32px process marks on the 2048 canvas (owner's universal fine-detail law).

Five chapters: 🔥 THE MELT · 🔨 THE HAMMER · ⚙ THE MACHINE · ⚡ THE ARC ·
🧪 THE BATH.

Lane state: FOUNDRY_PROGRESS.jsonl, _foundry_work/
"""
from __future__ import annotations

import zlib
from functools import lru_cache

import cv2
import numpy as np

from engine.expansions import fractured_foundry_kit_2026 as kit
from engine.expansions.fractured_foundry_kit_2026 import (
    GEN, WORK, cells, coords, fbm, frac, gauss, h2, metal_art, metal_spec, n01, rng,
)

_TAU = 6.283185307179586
_GROUP = "⚒ FRACTURED FOUNDRY"


def _seed(fid):
    return int(zlib.crc32(fid.encode())) & 0x7FFFFFFF


# ════════════════════════════════════════════════════════════════════════════
# SURFACES — each returns (height 0..1, heat field or None, patch field or None)
# ════════════════════════════════════════════════════════════════════════════

def s_pour(res, seed, flow=9.0):
    """A molten pour that froze while it was still moving: laminar tongues with
    a chilled skin wrinkling across the flow."""
    yy, xx = coords(res)
    r = rng(seed, 3)
    w = fbm(res, r, 4, 5)
    u = (xx * 0.30 + yy * 0.95) / (res / flow) + w * 2.2
    lam = 0.5 + 0.5 * np.sin(u * _TAU)
    skin = np.sin(u * _TAU * 5.0 + w * 6.0) * 0.16
    h = n01(lam + skin * 0.8)
    heat = np.clip(n01(lam * 0.7 + w * 0.5) * 1.15, 0, 1)
    return h, heat, None


def s_slag(res, seed, vesicle=11.0):
    """Furnace slag: gas vesicles frozen mid-rise in a glassy crust."""
    s = res / GEN
    _, _, d, idv, _ = cells(res, vesicle * s, seed % 7919 + 17, 0.62, taps=9, need2=False)
    rad = vesicle * s * (0.20 + 0.26 * h2(np.floor(idv * 37.0), 0.0, 5))
    bub = np.clip(1.0 - (d / rad) ** 2, 0.0, 1.0) ** 0.6
    crust = fbm(res, rng(seed, 7), 4, 7)
    h = n01(crust * 0.55 - bub * 0.9)
    return h, np.clip(n01(crust) * 0.5, 0, 1), None


def s_castskin(res, seed, grain=6.0):
    """Sand-cast skin — the pebbled face the mould leaves, with the parting
    line still showing."""
    s = res / GEN
    _, _, d, idg, _ = cells(res, grain * s, seed % 7919 + 23, 0.75, taps=5, need2=False)
    peb = np.clip(1.0 - (d / (grain * s * 0.55)) ** 2, 0.0, 1.0)
    coarse = fbm(res, rng(seed, 11), 3, 6)
    yy, xx = coords(res)
    part = np.exp(-(((xx - res * 0.42) / (res * 0.012)) ** 2)) * 0.4
    h = n01(peb * 0.6 + coarse * 0.4 + part)
    return h, None, np.clip(coarse * 1.2 - 0.3, 0, 1) * 0.5


def s_ingot(res, seed, bands=7.0):
    """An ingot pulled from the mould: chill bands across the face and the
    shrink pipe drawn down its middle."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 13), 3, 4)
    band = 0.5 + 0.5 * np.sin((yy / (res / bands) + w * 1.4) * _TAU)
    pipe = np.exp(-(((xx - res * 0.5) / (res * 0.10)) ** 2))
    h = n01(band * 0.7 - pipe * 0.45 + w * 0.3)
    return h, np.clip(band * 0.55 + pipe * 0.4, 0, 1), None


def s_forgescale(res, seed, flake=8.0):
    """Forge scale lifting off hot iron — black flakes curling at their edges."""
    s = res / GEN
    dx, dy, d, idf, d2 = cells(res, flake * s, seed % 7919 + 29, 0.55, taps=9, need2=True)
    edge = (d2 - d) / (flake * s)
    plate = np.clip(edge * 3.4, 0, 1)
    lift = np.exp(-((edge / 0.10) ** 2)) * 0.55          # the curled rim
    h = n01(plate * 0.6 + lift + fbm(res, rng(seed, 31), 3, 9) * 0.25)
    patch = np.clip(1.0 - plate * 1.5, 0, 1)             # bare metal in the losses
    return h, np.clip(plate * 0.35, 0, 1), patch


def s_planish(res, seed, facet=10.0):
    """Planished by hand: overlapping hammer facets, each one a shallow dish."""
    s = res / GEN
    _, _, d, idp, _ = cells(res, facet * s, seed % 7919 + 37, 0.42, taps=9, need2=False)
    dish = np.clip(1.0 - (d / (facet * s * 0.62)) ** 2, 0.0, 1.0)
    depth = 0.55 + 0.45 * h2(np.floor(idp * 41.0), 0.0, 9)
    h = n01(1.0 - dish * depth * 0.7)
    return h, None, None


def s_damascus(res, seed, layers=26.0):
    """Pattern-welded steel: hundreds of folded layers, ground back so the
    ladder shows where the billet was cut."""
    yy, xx = coords(res)
    w1 = fbm(res, rng(seed, 41), 4, 5)
    w2 = fbm(res, rng(seed, 43), 3, 3)
    u = (yy / (res / layers)) + w1 * 3.4 + np.sin(xx / (res / 5.0)) * 0.6
    lam = 0.5 + 0.5 * np.sin(u * _TAU)
    ladder = 0.5 + 0.5 * np.sin(xx / (res / 9.0) * _TAU + w2 * 2.0)
    h = n01(lam * 0.8 + ladder * 0.18)
    patch = np.clip(lam * 1.3 - 0.25, 0, 1)              # the two alloys etch differently
    return h, None, patch


def s_mill(res, seed, arc=13.0):
    """Face-milled: overlapping cutter arcs, each pass stepping across the last."""
    yy, xx = coords(res)
    step = res / arc
    pass_i = np.floor(xx / step)
    cx = pass_i * step + step * 0.5
    cy = np.mod(pass_i, 2) * step * 0.5
    d = np.hypot(xx - cx, yy - cy)
    cut = 0.5 + 0.5 * np.sin(d / (step * 0.10) * _TAU)
    feed = 0.5 + 0.5 * np.sin(yy / (res / 120.0) * _TAU)
    h = n01(cut * 0.7 + feed * 0.3)
    return h, None, None


def s_turn(res, seed, pitch=150.0):
    """Turned on a lathe: concentric feed grooves running out from the centre of
    the chuck, which sits off the panel."""
    yy, xx = coords(res)
    cx, cy = -0.25 * res, 1.15 * res
    d = np.hypot(xx - cx, yy - cy)
    groove = 0.5 + 0.5 * np.sin(d / (res / pitch) * _TAU)
    chatter = 0.5 + 0.5 * np.sin(d / (res / 11.0) * _TAU + np.arctan2(yy - cy, xx - cx) * 7.0)
    h = n01(groove * 0.72 + chatter * 0.28)
    return h, None, None


def s_knurl(res, seed, cell=15.0):
    """Diamond knurling — the wheel pressed a cross-hatch of pyramids into the bar."""
    yy, xx = coords(res)
    s = res / cell
    u = (xx + yy) / s
    v = (xx - yy) / s
    py = (1.0 - np.abs(frac(u) - 0.5) * 2.0) * (1.0 - np.abs(frac(v) - 0.5) * 2.0)
    h = n01(py)
    return h, None, None


def s_grind(res, seed, belt=3.2):
    """Belt-ground: long parallel scratches with the odd deep one where a torn
    grit dug in."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 47), 3, 4)
    u = (xx * 0.985 + yy * 0.17) / (res / (GEN / belt)) + w * 0.9
    fine = 0.5 + 0.5 * np.sin(u * _TAU)
    deep = (h2(np.floor(u), np.zeros_like(u), 13) > 0.90).astype(np.float32)
    h = n01(fine * 0.7 - deep * 0.4)
    return h, None, None


def s_weldbead(res, seed, bead=17.0):
    """Stacked weld beads — each pass a row of frozen ripples, the heat-affected
    zone tempering out either side."""
    yy, xx = coords(res)
    s = res / bead
    row = np.floor(yy / s)
    ph = h2(row, np.zeros_like(row), 17) * _TAU
    ly = (yy - row * s) / s
    crown = np.clip(1.0 - ((ly - 0.5) / 0.42) ** 2, 0.0, 1.0)
    ripple = 0.5 + 0.5 * np.sin(xx / (s * 0.22) * _TAU + ph + ly * 2.6)
    h = n01(crown * (0.40 + 0.60 * ripple))
    haz = np.clip(1.0 - np.abs(ly - 0.5) * 2.2, 0, 1)
    return h, np.clip(haz * 0.95, 0, 1), None


def s_plasmacut(res, seed, drag=11.0):
    """A plasma-cut edge: drag lines raked down the kerf with dross hanging
    off the bottom."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 53), 3, 5)
    u = (xx + yy * 0.22 + w * res * 0.02) / (res / drag)
    line = 0.5 + 0.5 * np.sin(u * _TAU)
    dross = np.clip((yy / res - 0.55) * 2.4, 0, 1) * (0.5 + 0.5 * np.sin(u * _TAU * 2.6))
    h = n01(line * 0.65 + dross * 0.5)
    return h, np.clip(line * 0.5 + dross * 0.6, 0, 1), None


def s_spangle(res, seed, crystal=22.0):
    """Hot-dip galvanising: the zinc froze into big spangle crystals, each one
    a facet catching the light differently."""
    s = res / GEN
    dx, dy, d, idc, d2 = cells(res, crystal * s, seed % 7919 + 59, 0.70, taps=9, need2=True)
    a = idc * _TAU
    facet = 0.5 + 0.5 * np.cos(np.arctan2(dy, dx) * 3.0 + a)
    grow = 0.5 + 0.5 * np.cos(d / (crystal * s * 0.16) * _TAU + a)
    h = n01(facet * 0.6 + grow * 0.25 + ((d2 - d) / (crystal * s) < 0.06) * 0.3)
    return h, None, None



# ── 🔥 THE MELT ──────────────────────────────────────────────────────────────

def s_dross(res, seed, skin=8.0):
    """Crucible dross — the oxide skin that has to be pulled off the top of a
    melt, wrinkled and torn where the rod dragged through it."""
    r = rng(seed, 61)
    w1, w2 = fbm(res, r, 4, 4), fbm(res, rng(seed, 63), 5, 9)
    wrinkle = np.abs(frac(w1 * skin) - 0.5) * 2.0
    tear = (w2 > 0.72).astype(np.float32)
    h = n01(wrinkle * 0.7 + w2 * 0.35 - tear * 0.4)
    return h, np.clip(w1 * 0.7, 0, 1), np.clip(tear, 0, 1) * 0.6


def s_spatter(res, seed, drops=7.0):
    """Cast spatter — droplets that flew, landed and froze where they hit, each
    one flattened into its own little splat."""
    s = res / GEN
    dx, dy, d, idd, _ = cells(res, drops * s, seed % 7919 + 67, 0.80, taps=9, need2=False)
    rad = drops * s * (0.16 + 0.34 * h2(np.floor(idd * 43.0), 0.0, 7))
    splat = np.clip(1.0 - (d / rad) ** 2, 0.0, 1.0) ** 0.45
    plate = fbm(res, rng(seed, 71), 3, 7) * 0.4
    h = n01(plate + splat * 0.8)
    return h, np.clip(splat * 0.8, 0, 1), None


def s_teeming(res, seed, stream=5.0):
    """The teeming stream — metal falling from the ladle, drawn out into
    ropes that thin as they stretch."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 73), 4, 4)
    u = (xx + w * res * 0.06) / (res / stream)
    rope = 0.5 + 0.5 * np.sin(u * _TAU)
    thin = np.clip(yy / res, 0, 1)
    h = n01(rope * (1.0 - thin * 0.45) + w * 0.25)
    return h, np.clip((1.0 - thin) * rope * 1.1, 0, 1), None


def s_chillshot(res, seed, shot=5.5):
    """Chill shot — atomised metal quenched into beads and packed into a bed."""
    s = res / GEN
    _, _, d, ids_, d2 = cells(res, shot * s, seed % 7919 + 79, 0.72, taps=9, need2=True)
    bead = np.clip(1.0 - (d / (shot * s * 0.52)) ** 2, 0.0, 1.0) ** 0.5
    h = n01(bead * 0.85 + ((d2 - d) / (shot * s) < 0.05) * 0.15)
    return h, None, None


def s_bloomiron(res, seed, sponge=9.0):
    """Bloomery iron — a sponge of metal and slag hammered together while it
    was never quite molten."""
    r = rng(seed, 83)
    f = fbm(res, r, 5, 5)
    pore = (f < 0.42).astype(np.float32)
    weld = np.abs(frac(f * sponge) - 0.5) * 2.0
    h = n01(weld * 0.55 + f * 0.45 - pore * 0.35)
    return h, None, np.clip(pore, 0, 1) * 0.7


def s_tuyere(res, seed, blast=13.0):
    """Tuyere burn — where the blast hit, the metal ran and the refractory
    glazed into streaks pointing downwind."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 89), 4, 5)
    u = (xx * 0.94 + yy * 0.34) / (res / blast) + w * 1.8
    streak = 0.5 + 0.5 * np.sin(u * _TAU)
    burn = np.clip(1.0 - np.abs(yy / res - 0.42) * 2.4, 0, 1)
    h = n01(streak * 0.6 + w * 0.4)
    return h, np.clip(burn * (0.5 + 0.5 * streak), 0, 1), None


# ── 🔨 THE HAMMER ────────────────────────────────────────────────────────────

def s_peened(res, seed, pit=4.6):
    """Peened — a thousand overlapping hammer pits, the surface work-hardened
    and dimpled all over."""
    s = res / GEN
    acc = np.zeros((res, res), np.float32)
    for k, salt in enumerate((97, 101, 103)):
        _, _, d, idp, _ = cells(res, pit * s * (1.0 + 0.32 * k), seed % 7919 + salt,
                                0.85, taps=5, need2=False)
        acc = np.maximum(acc, np.clip(1.0 - (d / (pit * s * 0.5)) ** 2, 0, 1) * (0.9 - 0.2 * k))
    h = n01(1.0 - acc * 0.75)
    return h, None, None


def s_anvilface(res, seed, mark=15.0):
    """The anvil face — worn hollow in the middle, scarred by everything that
    has ever been beaten on it."""
    yy, xx = coords(res)
    hollow = np.exp(-(((xx - res * 0.5) ** 2 + (yy - res * 0.55) ** 2) / (res * 0.42) ** 2))
    r = rng(seed, 107)
    scar = fbm(res, r, 5, 11)
    nick = (scar > 0.74).astype(np.float32) * 0.5
    h = n01(0.75 - hollow * 0.25 + scar * 0.3 - nick)
    return h, None, None


def s_drawntaper(res, seed, taper=11.0):
    """Drawn down under the hammer: the bar stretched, so its flats step
    narrower and narrower along its length."""
    yy, xx = coords(res)
    t = np.clip(xx / res, 0, 1)
    u = yy / (res / taper) * (1.0 + t * 1.1)
    flat = np.abs(frac(u) - 0.5) * 2.0
    chatter = 0.5 + 0.5 * np.sin(xx / (res / 90.0) * _TAU + frac(u) * 5.0)
    h = n01(1.0 - flat ** 1.6 * 0.8 + chatter * 0.18)
    return h, None, None


def s_upset(res, seed, bulge=6.0):
    """Upset — the end driven back on itself until it swelled, the metal folding
    over in rings around the swell."""
    yy, xx = coords(res)
    cx, cy = res * 0.34, res * 1.06
    d = np.hypot(xx - cx, yy - cy)
    ring = 0.5 + 0.5 * np.sin(d / (res / (bulge * 3.0)) * _TAU)
    fold = np.clip(1.2 - d / (res * 0.8), 0, 1)
    h = n01(ring * (0.4 + 0.6 * fold) + fold * 0.3)
    return h, None, None


def s_swage(res, seed, groove=13.0):
    """Swage block — the bar hammered down into a shaped die, so it carries the
    die's flutes along its whole length."""
    yy, xx = coords(res)
    u = yy / (res / groove)
    flute = np.cos(np.clip(np.abs(frac(u) - 0.5) * 2.0, 0, 1) * 1.5708)
    edge = (np.abs(frac(u) - 0.5) > 0.44).astype(np.float32) * 0.3
    h = n01(flute * 0.8 + edge)
    return h, None, None


def s_fuller(res, seed, groove=9.0):
    """Fullered — the smith's fuller drove a row of grooves across the stock to
    move metal sideways before drawing it out."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 109), 3, 4)
    u = (xx + w * res * 0.02) / (res / groove)
    g = np.clip(1.0 - (np.abs(frac(u) - 0.5) * 2.0 / 0.6) ** 2, 0, 1)
    ridge = np.clip((np.abs(frac(u) - 0.5) * 2.0 - 0.62) * 3.0, 0, 1) * 0.5
    h = n01(1.0 - g * 0.7 + ridge)
    return h, None, None


def s_quenchcrack(res, seed, net=17.0):
    """Quench-cracked: cooled too fast, so the skin let go in a net of fine
    checks with the hardened metal bright between them."""
    r = rng(seed, 113)
    f = fbm(res, r, 4, 6)
    crack = (np.abs(frac(f * net) - 0.5) > 0.455).astype(np.float32)
    crack = cv2.GaussianBlur(crack, (0, 0), 0.8)
    h = n01(0.8 - crack * 0.75 + fbm(res, rng(seed, 127), 3, 12) * 0.2)
    return h, np.clip(1.0 - crack * 2.0, 0, 1) * 0.35, np.clip(crack * 1.6, 0, 1)


# ── ⚙ THE MACHINE ───────────────────────────────────────────────────────────

def s_edm(res, seed, crater=3.4):
    """Wire EDM — the surface is a field of microscopic craters, each one a
    single spark's worth of metal removed."""
    s = res / GEN
    acc = np.zeros((res, res), np.float32)
    for k, salt in enumerate((131, 137)):
        _, _, d, ide, _ = cells(res, crater * s * (1 + 0.5 * k), seed % 7919 + salt,
                                0.9, taps=5, need2=False)
        acc = acc + np.clip(1.0 - (d / (crater * s * 0.45)) ** 2, 0, 1) * (0.7 - 0.25 * k)
    h = n01(1.0 - acc * 0.6)
    return h, None, None


def s_honed(res, seed, hatch=9.0):
    """Honed bore — the cross-hatch a hone leaves so the oil has somewhere to sit."""
    yy, xx = coords(res)
    u = (xx + yy * 1.9) / (res / hatch)
    v = (xx - yy * 1.9) / (res / hatch)
    a = np.abs(frac(u) - 0.5) * 2.0
    b = np.abs(frac(v) - 0.5) * 2.0
    h = n01(1.0 - np.minimum(a, b) ** 1.4 * 0.55)
    return h, None, None


def s_broach(res, seed, tooth_p=7.0):
    """Broached — each tooth of the broach cut a shade deeper than the last, so
    the wall steps down in fine parallel terraces."""
    yy, xx = coords(res)
    u = xx / (res / tooth_p)
    step = np.floor(u) / tooth_p
    within = frac(u)
    h = n01(step * 0.6 + within * 0.35 + fbm(res, rng(seed, 139), 2, 40) * 0.1)
    return h, None, None


def s_shotpeen(res, seed, ball=6.5):
    """Shot-peened — blasted with steel shot until the whole face is a mat of
    overlapping impact dimples."""
    s = res / GEN
    acc = np.zeros((res, res), np.float32)
    for k, salt in enumerate((149, 151, 157)):
        _, _, d, idb, _ = cells(res, ball * s * (1 + 0.28 * k), seed % 7919 + salt,
                                0.95, taps=5, need2=False)
        acc = np.maximum(acc, np.clip(1.0 - (d / (ball * s * 0.46)) ** 2, 0, 1))
    h = n01(1.0 - acc * 0.8)
    return h, None, None


def s_thread(res, seed, pitch=15.0):
    """Cut thread — a single helix running the length of the bar with the tool's
    flank marks still in the flanks."""
    yy, xx = coords(res)
    u = (yy + xx * 0.10) / (res / pitch)
    crest = np.abs(frac(u) - 0.5) * 2.0
    flank = 0.5 + 0.5 * np.sin(u * _TAU * 9.0)
    h = n01((1.0 - crest ** 1.5) * 0.85 + flank * 0.12)
    return h, None, None


def s_flycut(res, seed, sweep=5.0):
    """Fly-cut — one tool tip swinging a wide arc, leaving the big overlapping
    scallops a surfacing cut is prized for."""
    yy, xx = coords(res)
    step = res / sweep
    row = np.floor(yy / step)
    cx = np.mod(row, 2) * step * 0.5
    col = np.floor((xx - cx) / step)
    d = np.hypot((xx - cx) - (col + 0.5) * step, (yy - row * step) - step * 0.5)
    feed = 0.5 + 0.5 * np.cos(xx / (res / 150.0) * _TAU)
    h = n01((0.5 + 0.5 * np.cos(d / (step * 0.32) * _TAU)) * 0.78 + feed * 0.22)
    return h, None, None


# ── ⚡ THE ARC ───────────────────────────────────────────────────────────────

def s_tigstack(res, seed, coin=13.0):
    """TIG, stacked dimes — every dip of the rod froze as its own overlapping
    disc down the joint."""
    yy, xx = coords(res)
    s = res / coin
    row = np.floor(yy / (s * 1.7))
    ph = h2(row, np.zeros_like(row), 19) * s
    ci = np.floor((xx + ph) / (s * 0.42))
    cx = ci * s * 0.42 - ph + s * 0.21
    cy = row * s * 1.7 + s * 0.85
    d = np.hypot(xx - cx, (yy - cy) * 1.5)
    disc = np.clip(1.0 - (d / (s * 0.46)) ** 2, 0, 1) ** 0.6
    bead = np.clip(1.0 - np.abs(yy - cy) / (s * 0.85), 0, 1)
    h = n01(disc * 0.7 * bead + bead * 0.25)
    return h, np.clip(bead * 0.9, 0, 1), None


def s_migspatter(res, seed, bead=15.0):
    """MIG — a fast hot bead with the spatter it threw stuck fast either side."""
    yy, xx = coords(res)
    s = res / bead
    row = np.floor(yy / s)
    ly = (yy - row * s) / s
    crown = np.clip(1.0 - ((ly - 0.45) / 0.36) ** 2, 0, 1)
    rip = 0.5 + 0.5 * np.sin(xx / (s * 0.26) * _TAU + h2(row, np.zeros_like(row), 23) * 6.0)
    _, _, d, idsp, _ = cells(res, s * 0.30, seed % 7919 + 163, 0.9, taps=5, need2=False)
    sp = np.clip(1.0 - (d / (s * 0.06)) ** 2, 0, 1) * (h2(np.floor(idsp * 31), 0.0, 5) > 0.80)
    h = n01(crown * (0.55 + 0.45 * rip) + sp * 0.5)
    return h, np.clip(crown * 0.85 + sp * 0.6, 0, 1), None


def s_oxycut(res, seed, drag=9.0):
    """Oxy-fuel cut — coarse drag lines with the slag that ran down them still
    welded to the bottom edge."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 167), 3, 4)
    u = (xx + w * res * 0.04) / (res / drag)
    line = np.abs(frac(u) - 0.5) * 2.0
    h = n01(1.0 - line ** 1.3 * 0.7 + w * 0.25)
    return h, np.clip((1.0 - line) * 0.6, 0, 1), None


def s_stitchweld(res, seed, run=11.0):
    """Stitch weld — short runs with cold gaps between them, the way a thin
    panel gets joined without warping it."""
    yy, xx = coords(res)
    s = res / run
    row = np.floor(yy / (s * 1.6))
    seg = np.floor(xx / (s * 1.5) + h2(row, np.zeros_like(row), 29))
    on = (h2(seg, row, 31) > 0.42).astype(np.float32)
    ly = (yy - row * s * 1.6) / (s * 1.6)
    crown = np.clip(1.0 - ((ly - 0.35) / 0.28) ** 2, 0, 1) * on
    rip = 0.5 + 0.5 * np.sin(xx / (s * 0.22) * _TAU)
    h = n01(crown * (0.6 + 0.4 * rip) + 0.15)
    return h, np.clip(crown * 0.9, 0, 1), None


def s_tackrow(res, seed, tack=17.0):
    """Tacked — a row of spot welds holding the job while the real welding waits."""
    s = res / tack
    _, _, d, idt, _ = cells(res, s, seed % 7919 + 173, 0.30, taps=9, need2=False)
    dome = np.clip(1.0 - (d / (s * 0.30)) ** 2, 0, 1) ** 0.7
    ring = np.exp(-((d - s * 0.36) / (s * 0.06)) ** 2) * 0.4
    h = n01(0.35 + dome * 0.6 + ring)
    return h, np.clip(dome * 0.95 + ring, 0, 1), None


def s_undercut(res, seed, groove=13.0):
    """Undercut — the arc ate into the parent plate beside the bead and left a
    groove that no inspector will pass."""
    yy, xx = coords(res)
    s = res / groove
    row = np.floor(yy / s)
    ly = (yy - row * s) / s
    bead = np.clip(1.0 - ((ly - 0.5) / 0.24) ** 2, 0, 1)
    cut = np.exp(-((np.abs(ly - 0.5) - 0.30) / 0.05) ** 2) * 0.7
    h = n01(0.6 + bead * 0.4 - cut)
    return h, np.clip(bead * 0.7, 0, 1), None


def s_arcstrike(res, seed, strikes=9.0):
    """Arc strikes — where the rod touched off the joint and burned a bright
    scar into the plate."""
    s = res / GEN
    _, _, d, ida, _ = cells(res, strikes * s * 2.2, seed % 7919 + 179, 0.85, taps=5, need2=False)
    hit = (h2(np.floor(ida * 37), 0.0, 11) > 0.55).astype(np.float32)
    scar = np.clip(1.0 - (d / (strikes * s * 0.55)) ** 2, 0, 1) * hit
    plate = fbm(res, rng(seed, 181), 3, 8) * 0.3
    h = n01(plate + scar * 0.7)
    return h, np.clip(scar * 1.1, 0, 1), None


def s_hazbloom(res, seed, zone=6.0):
    """The heat-affected zone — no mark at all, just the temper colour blooming
    out from where the heat went in."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 191), 4, 4)
    band = np.clip(1.0 - np.abs((yy / res) - 0.5 + (w - 0.5) * 0.3) * zone * 0.5, 0, 1)
    h = n01(0.6 + w * 0.35)
    return h, np.clip(band, 0, 1), None


# ── 🧪 THE BATH ─────────────────────────────────────────────────────────────

def s_anodise(res, seed, grain=3.0):
    """Anodised — the etch left a fine directional grain and the dye sank into
    the pore structure."""
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 193), 3, 5)
    u = (xx * 0.99 + yy * 0.12) / (res / (GEN / grain)) + w * 0.6
    h = n01((0.5 + 0.5 * np.sin(u * _TAU)) * 0.6 + w * 0.4)
    return h, None, None


def s_bluing(res, seed, swirl=9.0):
    """Rust bluing — cards of black oxide grown, boiled and carded back, over
    and over, until the steel went blue-black."""
    r = rng(seed, 197)
    f = fbm(res, r, 5, 5)
    card = np.abs(frac(f * swirl) - 0.5) * 2.0
    h = n01(0.7 + card * 0.3)
    return h, None, np.clip(f * 1.3 - 0.2, 0, 1) * 0.5


def s_parkerize(res, seed, crystal=4.2):
    """Parkerised — a phosphate crystal coat, matt and grey and thirsty for oil."""
    s = res / GEN
    _, _, d, idc, d2 = cells(res, crystal * s, seed % 7919 + 199, 0.9, taps=9, need2=True)
    grain = np.clip(1.0 - (d / (crystal * s * 0.6)) ** 2, 0, 1)
    seam = ((d2 - d) / (crystal * s) < 0.08).astype(np.float32) * 0.35
    h = n01(grain * 0.6 + seam)
    return h, None, None


def s_patina(res, seed, bloom=11.0):
    """Copper patina — the green climbing out of the low ground and eating its
    way across the metal."""
    r = rng(seed, 211)
    f = fbm(res, r, 5, 4)
    g = fbm(res, rng(seed, 223), 4, 9)
    green = np.clip((f - 0.42) * 3.2, 0, 1)
    h = n01(0.6 + g * 0.4 - green * 0.2)
    return h, None, np.clip(green, 0, 1)


def s_powdercoat(res, seed, orange=7.0):
    """Powder coat — the film flowed out but not quite flat, so it kept the
    orange-peel every sprayed panel has."""
    r = rng(seed, 227)
    f = gauss(fbm(res, r, 3, int(orange * 4)), 1.4)
    h = n01(f)
    return h, None, None


def s_chromeflash(res, seed, ripple=13.0):
    """Flash chrome over a substrate that was never quite polished out, so the
    plating mirrors every wave still under it."""
    r = rng(seed, 229)
    f = gauss(fbm(res, r, 3, 6), 2.2)
    wave = 0.5 + 0.5 * np.sin(f * ripple * 2.0)
    h = n01(wave * 0.7 + f * 0.3)
    return h, None, None


def s_passivate(res, seed, mott=8.0):
    """Passivated stainless — no coating to see, just the faint mottle the acid
    left where it stripped the free iron out."""
    r = rng(seed, 233)
    f = fbm(res, r, 4, int(mott))
    h = n01(0.72 + f * 0.28)
    return h, None, np.clip(f * 1.2 - 0.35, 0, 1) * 0.4


def s_millscale(res, seed, plate=10.0):
    """Hot-rolled mill scale — blue-black and tight in places, flaked away to
    bare steel in others."""
    r = rng(seed, 239)
    f = fbm(res, r, 5, 5)
    tight = (f > 0.48).astype(np.float32)
    tight = cv2.GaussianBlur(tight, (0, 0), 1.2)
    h = n01(0.55 + tight * 0.3 + fbm(res, rng(seed, 241), 3, 14) * 0.2)
    return h, None, np.clip(1.0 - tight * 1.4, 0, 1)


def s_phosphate(res, seed, etch=5.0):
    """Manganese phosphate — a heavy dark etch that bites deepest wherever the
    grain of the steel runs."""
    yy, xx = coords(res)
    r = rng(seed, 251)
    f = fbm(res, r, 4, 7)
    grain = 0.5 + 0.5 * np.sin((xx * 0.6 + yy * 0.8) / (res / (GEN / etch)) * _TAU + f * 4.0)
    h = n01(grain * 0.45 + f * 0.55)
    return h, None, np.clip(f * 1.1 - 0.15, 0, 1) * 0.55


SURFACES = {
    "dross": s_dross, "spatter": s_spatter, "teeming": s_teeming,
    "chillshot": s_chillshot, "bloomiron": s_bloomiron, "tuyere": s_tuyere,
    "peened": s_peened, "anvilface": s_anvilface, "drawntaper": s_drawntaper,
    "upset": s_upset, "swage": s_swage, "fuller": s_fuller,
    "quenchcrack": s_quenchcrack, "edm": s_edm, "honed": s_honed,
    "broach": s_broach, "shotpeen": s_shotpeen, "thread": s_thread,
    "flycut": s_flycut, "tigstack": s_tigstack, "migspatter": s_migspatter,
    "oxycut": s_oxycut, "stitchweld": s_stitchweld, "tackrow": s_tackrow,
    "undercut": s_undercut, "arcstrike": s_arcstrike, "hazbloom": s_hazbloom,
    "anodise": s_anodise, "bluing": s_bluing, "parkerize": s_parkerize,
    "patina": s_patina, "powdercoat": s_powdercoat, "chromeflash": s_chromeflash,
    "passivate": s_passivate, "millscale": s_millscale, "phosphate": s_phosphate,
    "pour": s_pour, "slag": s_slag, "castskin": s_castskin, "ingot": s_ingot,
    "forgescale": s_forgescale, "planish": s_planish, "damascus": s_damascus,
    "mill": s_mill, "turn": s_turn, "knurl": s_knurl, "grind": s_grind,
    "weldbead": s_weldbead, "plasmacut": s_plasmacut, "spangle": s_spangle,
}


# ════════════════════════════════════════════════════════════════════════════
# RECIPES
# ════════════════════════════════════════════════════════════════════════════

def _F(fid, name, surface, metal, desc, *, sargs=None, axis=0.0, aniso=0.75,
       relief=14.0, gloss=0.85, tooth=0.16, grime=0.0, rough=42.0, clear=40.0,
       metallic=None, mvar=1.0, rvar=1.0, cvar=1.0, heat=1.0, wear=0.55,
       heat_amt=0.55, temper_band=0.62, coating=False, patch_spec=None):
    return dict(name=name, surface=surface, sargs=dict(sargs or {}), metal=metal,
                axis=axis, aniso=aniso, relief=relief, gloss=gloss, tooth=tooth,
                grime=grime, rough=rough, clear=clear, mvar=mvar, rvar=rvar,
                cvar=cvar, heat_gain=heat, wear=wear, heat_amt=heat_amt,
                temper_band=temper_band, coating=bool(coating), seed=_seed(fid), desc=desc,
                **({"metallic": metallic} if metallic else {}),
                **({"patch_spec": patch_spec} if patch_spec else {}))


FOUNDRY = {
 # ── 🔥 THE MELT ────────────────────────────────────────────────────────────
 "ffo_ladle_pour": _F("ffo_ladle_pour", "Ladle Pour", "pour", "steel",
    "A pour that froze while it was still moving: laminar tongues under a wrinkled chill skin.",
    sargs=dict(flow=9.0), axis=1.26, aniso=0.82, relief=16.0, grime=0.18,
    heat_amt=0.72, temper_band=0.42),
 "ffo_furnace_slag": _F("ffo_furnace_slag", "Furnace Slag", "slag", "castiron",
    "Gas vesicles frozen mid-rise in a glassy crust, the way slag comes off the top of a heat.",
    sargs=dict(vesicle=11.0), axis=0.4, aniso=0.35, relief=18.0, rough=120.0, grime=0.30),
 "ffo_sand_cast": _F("ffo_sand_cast", "Sand Cast", "castskin", "iron",
    "The pebbled face a sand mould leaves, parting line still showing across it.",
    sargs=dict(grain=6.0), aniso=0.20, relief=12.0, rough=150.0, gloss=0.42, grime=0.26,
    patch_spec=(120.0, 190.0, 200.0)),
 "ffo_chill_ingot": _F("ffo_chill_ingot", "Chill Ingot", "ingot", "steel",
    "Chill bands across the face of an ingot with the shrink pipe drawn down its middle.",
    sargs=dict(bands=7.0), axis=0.0, aniso=0.68, relief=15.0, grime=0.20,
    heat_amt=0.60, temper_band=0.34),
 # ── 🔨 THE HAMMER ──────────────────────────────────────────────────────────
 "ffo_forge_scale": _F("ffo_forge_scale", "Forge Scale", "forgescale", "graphite",
    "Black scale lifting off hot iron, every flake curling at its edge.",
    sargs=dict(flake=8.0), aniso=0.30, relief=20.0, rough=138.0, gloss=0.55, grime=0.34,
    patch_spec=(238.0, 40.0, 30.0)),
 "ffo_planished": _F("ffo_planished", "Planished", "planish", "aluminium",
    "Planished by hand: overlapping hammer facets, each one a shallow dish.",
    sargs=dict(facet=10.0), aniso=0.45, relief=13.0, rough=54.0, gloss=1.0),
 "ffo_damascus_fold": _F("ffo_damascus_fold", "Damascus Fold", "damascus", "steel",
    "Hundreds of folded layers ground back, the ladder showing where the billet was cut.",
    sargs=dict(layers=26.0), axis=1.5708, aniso=0.88, relief=11.0, rough=48.0,
    patch_spec=(96.0, 150.0, 120.0)),
 # ── ⚙ THE MACHINE ─────────────────────────────────────────────────────────
 "ffo_face_mill": _F("ffo_face_mill", "Face Mill", "mill", "steel",
    "Overlapping cutter arcs, each pass stepping across the last.",
    sargs=dict(arc=13.0), axis=0.0, aniso=0.80, relief=10.0, rough=38.0, gloss=0.95),
 "ffo_lathe_turn": _F("ffo_lathe_turn", "Lathe Turn", "turn", "nickel",
    "Concentric feed grooves running out from a chuck set off the panel.",
    sargs=dict(pitch=150.0), axis=0.0, aniso=0.86, relief=9.0, rough=34.0, gloss=1.0),
 "ffo_diamond_knurl": _F("ffo_diamond_knurl", "Diamond Knurl", "knurl", "steel",
    "The knurling wheel pressed a cross-hatch of pyramids into the bar.",
    sargs=dict(cell=15.0), aniso=0.30, relief=16.0, rough=64.0, grime=0.16),
 "ffo_belt_grind": _F("ffo_belt_grind", "Belt Grind", "grind", "titanium",
    "Long parallel scratches with the odd deep one where a torn grit dug in.",
    sargs=dict(belt=3.2), axis=0.17, aniso=0.94, relief=8.0, rough=44.0, gloss=1.0),
 # ── ⚡ THE ARC ─────────────────────────────────────────────────────────────
 "ffo_weld_bead": _F("ffo_weld_bead", "Weld Bead", "weldbead", "steel",
    "Stacked passes of frozen ripple with the heat-affected zone tempering out either side.",
    sargs=dict(bead=17.0), axis=0.0, aniso=0.70, relief=17.0, rough=58.0, grime=0.14,
    heat_amt=0.50, temper_band=0.78),
 "ffo_plasma_cut": _F("ffo_plasma_cut", "Plasma Cut", "plasmacut", "steel",
    "Drag lines raked down the kerf with dross still hanging off the bottom.",
    sargs=dict(drag=11.0), axis=1.35, aniso=0.88, relief=14.0, rough=76.0, grime=0.22,
    heat_amt=0.44, temper_band=0.55),
 # ── 🧪 THE BATH ───────────────────────────────────────────────────────────
 "ffo_zinc_spangle": _F("ffo_zinc_spangle", "Zinc Spangle", "spangle", "zinc",
    "Hot-dip galvanising froze into big spangle crystals, every facet catching light its own way.",
    sargs=dict(crystal=22.0), aniso=0.55, relief=12.0, rough=60.0, gloss=0.92),
}


_FOUNDRY_W2 = {
 # 🔥 THE MELT
 "ffo_crucible_dross": _F("ffo_crucible_dross", "Crucible Dross", "dross", "iron",
    "The oxide skin pulled off the top of a melt, wrinkled and torn where the rod dragged.",
    sargs=dict(skin=8.0), aniso=0.35, relief=17.0, rough=120.0, grime=0.30,
    heat_amt=0.40, temper_band=0.30, patch_spec=(80.0, 200.0, 190.0)),
 "ffo_cast_spatter": _F("ffo_cast_spatter", "Cast Spatter", "spatter", "steel",
    "Droplets that flew, landed and froze where they hit, each flattened into its own splat.",
    sargs=dict(drops=7.0), aniso=0.40, relief=16.0, rough=86.0, grime=0.22,
    heat_amt=0.46, temper_band=0.40),
 "ffo_teeming_stream": _F("ffo_teeming_stream", "Teeming Stream", "teeming", "steel",
    "Metal falling from the ladle, drawn into ropes that thin as they stretch.",
    sargs=dict(stream=5.0), axis=1.5708, aniso=0.86, relief=15.0,
    heat_amt=0.68, temper_band=0.36),
 "ffo_chill_shot": _F("ffo_chill_shot", "Chill Shot", "chillshot", "steel",
    "Atomised metal quenched into beads and packed into a bed.",
    sargs=dict(shot=5.5), aniso=0.30, relief=15.0, rough=70.0),
 "ffo_bloom_iron": _F("ffo_bloom_iron", "Bloom Iron", "bloomiron", "iron",
    "A sponge of metal and slag hammered together while it was never quite molten.",
    sargs=dict(sponge=9.0), aniso=0.28, relief=16.0, rough=132.0, grime=0.28,
    patch_spec=(70.0, 210.0, 200.0)),
 "ffo_tuyere_burn": _F("ffo_tuyere_burn", "Tuyere Burn", "tuyere", "castiron",
    "Where the blast hit, the metal ran and the refractory glazed into downwind streaks.",
    sargs=dict(blast=13.0), axis=0.34, aniso=0.80, relief=15.0, grime=0.26,
    heat_amt=0.62, temper_band=0.48),
 # 🔨 THE HAMMER
 "ffo_peened": _F("ffo_peened", "Peened", "peened", "steel",
    "A thousand overlapping hammer pits, the face work-hardened and dimpled all over.",
    sargs=dict(pit=4.6), aniso=0.35, relief=15.0, rough=74.0),
 "ffo_anvil_face": _F("ffo_anvil_face", "Anvil Face", "anvilface", "steel",
    "Worn hollow in the middle and scarred by everything ever beaten on it.",
    sargs=dict(mark=15.0), aniso=0.50, relief=13.0, rough=62.0, grime=0.24),
 "ffo_drawn_taper": _F("ffo_drawn_taper", "Drawn Taper", "drawntaper", "iron",
    "Stretched under the hammer, so the flats step narrower along the bar.",
    sargs=dict(taper=11.0), axis=0.0, aniso=0.84, relief=13.0, rough=66.0),
 "ffo_upset_bulge": _F("ffo_upset_bulge", "Upset Bulge", "upset", "iron",
    "Driven back on itself until it swelled, the metal folding in rings around the swell.",
    sargs=dict(bulge=6.0), aniso=0.55, relief=14.0, rough=70.0, grime=0.18),
 "ffo_swage_block": _F("ffo_swage_block", "Swage Block", "swage", "steel",
    "Hammered down into a shaped die, carrying the die's flutes end to end.",
    sargs=dict(groove=13.0), axis=0.0, aniso=0.82, relief=14.0, rough=56.0),
 "ffo_fullered": _F("ffo_fullered", "Fullered", "fuller", "iron",
    "The fuller drove a row of grooves across the stock to move metal sideways.",
    sargs=dict(groove=9.0), axis=1.5708, aniso=0.80, relief=15.0, rough=68.0),
 "ffo_quench_check": _F("ffo_quench_check", "Quench Check", "quenchcrack", "blued",
    "Cooled too fast: the skin let go in a net of fine checks with hard metal between.",
    sargs=dict(net=17.0), aniso=0.42, relief=18.0, rough=52.0,
    heat_amt=0.40, temper_band=0.80, patch_spec=(40.0, 190.0, 60.0)),
 # ⚙ THE MACHINE
 "ffo_wire_edm": _F("ffo_wire_edm", "Wire EDM", "edm", "titanium",
    "A field of microscopic craters, each one a single spark's worth of metal gone.",
    sargs=dict(crater=3.4), aniso=0.25, relief=13.0, rough=104.0, gloss=0.60),
 "ffo_honed_bore": _F("ffo_honed_bore", "Honed Bore", "honed", "steel",
    "The cross-hatch a hone leaves so the oil has somewhere to sit.",
    sargs=dict(hatch=9.0), axis=0.52, aniso=0.72, relief=11.0, rough=48.0),
 "ffo_broached": _F("ffo_broached", "Broached", "broach", "nickel",
    "Every tooth cut a shade deeper than the last, so the wall steps in fine terraces.",
    sargs=dict(tooth_p=7.0), axis=1.5708, aniso=0.86, relief=10.0, rough=40.0),
 "ffo_shot_peened": _F("ffo_shot_peened", "Shot Peened", "shotpeen", "aluminium",
    "Blasted with steel shot until the face is a mat of overlapping dimples.",
    sargs=dict(ball=6.5), aniso=0.28, relief=15.0, rough=118.0, gloss=0.58),
 "ffo_cut_thread": _F("ffo_cut_thread", "Cut Thread", "thread", "brass",
    "A single helix down the bar with the tool's flank marks still in the flanks.",
    sargs=dict(pitch=15.0), axis=0.10, aniso=0.88, relief=15.0, rough=46.0),
 "ffo_fly_cut": _F("ffo_fly_cut", "Fly Cut", "flycut", "aluminium",
    "One tool tip swinging a wide arc, leaving the big scallops a surfacing cut is prized for.",
    sargs=dict(sweep=5.0), aniso=0.66, relief=10.0, rough=36.0, gloss=1.0),
 # ⚡ THE ARC
 "ffo_tig_stack": _F("ffo_tig_stack", "TIG Stack", "tigstack", "steel",
    "Stacked dimes: every dip of the rod froze as its own overlapping disc.",
    sargs=dict(coin=13.0), axis=0.0, aniso=0.62, relief=16.0, rough=44.0,
    heat_amt=0.42, temper_band=0.60),
 "ffo_mig_spatter": _F("ffo_mig_spatter", "MIG Spatter", "migspatter", "steel",
    "A fast hot bead with the spatter it threw stuck fast either side.",
    sargs=dict(bead=15.0), axis=0.0, aniso=0.64, relief=17.0, rough=72.0, grime=0.16,
    heat_amt=0.40, temper_band=0.56),
 "ffo_oxy_cut": _F("ffo_oxy_cut", "Oxy Cut", "oxycut", "steel",
    "Coarse drag lines with the slag that ran down them still welded on.",
    sargs=dict(drag=9.0), axis=1.5708, aniso=0.84, relief=16.0, rough=92.0, grime=0.24,
    heat_amt=0.46, temper_band=0.44),
 "ffo_stitch_weld": _F("ffo_stitch_weld", "Stitch Weld", "stitchweld", "steel",
    "Short runs with cold gaps between them, the way thin panel gets joined.",
    sargs=dict(run=11.0), axis=0.0, aniso=0.66, relief=16.0, rough=58.0,
    heat_amt=0.40, temper_band=0.58),
 "ffo_tack_row": _F("ffo_tack_row", "Tack Row", "tackrow", "steel",
    "A row of spot welds holding the job while the real welding waits.",
    sargs=dict(tack=17.0), aniso=0.45, relief=17.0, rough=60.0,
    heat_amt=0.42, temper_band=0.60),
 "ffo_undercut": _F("ffo_undercut", "Undercut", "undercut", "steel",
    "The arc ate into the parent plate beside the bead and left a groove no inspector passes.",
    sargs=dict(groove=13.0), axis=0.0, aniso=0.70, relief=16.0, rough=64.0,
    heat_amt=0.38, temper_band=0.54),
 "ffo_arc_strike": _F("ffo_arc_strike", "Arc Strike", "arcstrike", "steel",
    "Where the rod touched off the joint and burned a bright scar into the plate.",
    sargs=dict(strikes=9.0), aniso=0.42, relief=22.0, rough=80.0, grime=0.20, mvar=1.5,
    rvar=1.6,
    heat_amt=0.44, temper_band=0.64),
 "ffo_haz_bloom": _F("ffo_haz_bloom", "HAZ Bloom", "hazbloom", "steel",
    "No mark at all, just the temper colour blooming out from where the heat went in.",
    sargs=dict(zone=6.0), aniso=0.72, relief=11.0, rough=44.0, gloss=0.80,
    heat_amt=0.48, temper_band=0.62),
 # 🧪 THE BATH
 "ffo_anodised": _F("ffo_anodised", "Anodised", "anodise", "aluminium",
    "The etch left a fine directional grain and the dye sank into the pore structure.",
    sargs=dict(grain=3.0), axis=0.12, aniso=0.92, relief=8.0, rough=54.0, clear=90.0),
 "ffo_rust_blued": _F("ffo_rust_blued", "Rust Blued", "bluing", "blued",
    "Cards of black oxide grown, boiled and carded back until the steel went blue-black.",
    sargs=dict(swirl=9.0), aniso=0.48, relief=10.0, rough=44.0, gloss=0.92,
    patch_spec=(150.0, 90.0, 60.0)),
 "ffo_parkerised": _F("ffo_parkerised", "Parkerised", "parkerize", "graphite",
    "A phosphate crystal coat, matt and grey and thirsty for oil.",
    sargs=dict(crystal=4.2), aniso=0.20, relief=14.0, rough=170.0, gloss=0.34, clear=150.0),
 "ffo_copper_patina": _F("ffo_copper_patina", "Copper Patina", "patina", "copper",
    "The green climbing out of the low ground and eating its way across the metal.",
    sargs=dict(bloom=11.0), aniso=0.35, relief=12.0, rough=120.0, grime=0.20,
    patch_spec=(30.0, 205.0, 190.0)),
 "ffo_powder_coat": _F("ffo_powder_coat", "Powder Coat", "powdercoat", "graphite",
    "The film flowed out but not quite flat, so it kept its orange-peel.",
    sargs=dict(orange=7.0), aniso=0.30, relief=7.0, rough=60.0, gloss=0.80, clear=30.0,
    metallic=70.0, coating=True),
 "ffo_chrome_flash": _F("ffo_chrome_flash", "Chrome Flash", "chromeflash", "nickel",
    "Flash chrome over a substrate never quite polished out, mirroring every wave under it.",
    sargs=dict(ripple=13.0), aniso=0.60, relief=6.0, rough=18.0, gloss=1.0, clear=18.0),
 "ffo_passivated": _F("ffo_passivated", "Passivated", "passivate", "steel",
    "No coating to see — just the faint mottle the acid left behind.",
    sargs=dict(mott=8.0), aniso=0.55, relief=7.0, rough=42.0, gloss=0.95,
    patch_spec=(200.0, 70.0, 50.0)),
 "ffo_mill_scale": _F("ffo_mill_scale", "Mill Scale", "millscale", "graphite",
    "Hot-rolled scale, blue-black and tight in places, flaked to bare steel in others.",
    sargs=dict(plate=10.0), aniso=0.36, relief=13.0, rough=126.0, grime=0.26,
    patch_spec=(240.0, 40.0, 26.0)),
 "ffo_phosphated": _F("ffo_phosphated", "Phosphated", "phosphate", "iron",
    "A heavy dark etch that bites deepest wherever the grain of the steel runs.",
    sargs=dict(etch=5.0), axis=0.93, aniso=0.74, relief=12.0, rough=140.0, gloss=0.50,
    patch_spec=(60.0, 200.0, 170.0)),
}
FOUNDRY.update(_FOUNDRY_W2)


# ════════════════════════════════════════════════════════════════════════════
# ART + REGISTRY CONTRACT
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=8)
def _surface(fid, res):
    d = FOUNDRY[fid]
    h, heat, patch = SURFACES[d["surface"]](res, d["seed"], **d.get("sargs", {}))
    return (np.asarray(h, np.float32),
            None if heat is None else np.asarray(heat, np.float32),
            None if patch is None else np.asarray(patch, np.float32))


def _recipe_at(fid, res):
    d = dict(FOUNDRY[fid])
    h, heat, patch = _surface(fid, res)
    if heat is not None:
        d["heat"] = np.clip(heat * float(d.get("heat_gain", 1.0)), 0, 1)
    if patch is not None:
        d["patch"] = patch
    return d, h


@lru_cache(maxsize=6)
def _art_cached(fid):
    d, h = _recipe_at(fid, WORK)
    return metal_art(h, d, WORK)


@lru_cache(maxsize=6)
def _spec_cached(fid):
    d, h = _recipe_at(fid, WORK)
    return metal_spec(h, d, WORK)


def _mk(fid):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        sp = cv2.resize(_spec_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        mk_ = np.clip(m2, 0, 1)
        out = sp.copy()
        out[..., 0] = (sp[..., 0] * mk_ + 4 * (1 - mk_)).astype(np.uint8)
        out[..., 1] = (sp[..., 1] * mk_ + 120 * (1 - mk_)).astype(np.uint8)
        out[..., 2] = (sp[..., 2] * mk_ + 16 * (1 - mk_)).astype(np.uint8)
        out[..., 3] = 255
        return out

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    for fid in FOUNDRY:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
    return f"fractured-foundry: {len(FOUNDRY)} worked-metal processes live ({_GROUP})"

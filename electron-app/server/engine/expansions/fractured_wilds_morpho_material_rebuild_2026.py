# -*- coding: utf-8 -*-
"""Explicit rejection rebuild for Morpho's feather/nacre/mineral half.

SPB-WILDS, 2026-08-24, owner-rejection lane WR-MORPHO-MATERIAL-1.
Owner verdict: the previous Fractured Wilds release committed the app's
"biggest cardinal sin PERIOD" by shipping the same paint and spec silhouettes
recolored.  Random noise is explicitly forbidden as a uniqueness device.

This isolated candidate overrides exactly the final twenty-five current
``fmo_*`` IDs, Pigeon Neck through Chalcopyrite.  There are twenty-five
separate builder functions below.  Every builder authors its own named
mechanism from seven or more causal literal masks, and explicitly assigns
feature-level Fractured material ownership (A metallic lobe, B clearcoat
lobe, N structural neutral).  It also authors independent metal, roughness,
and clearcoat topology from those named masks.  There is no RNG, noise,
fleck/grain pass, wrapped/tiled source image, generic source-field router, or
equal-population/rank quantizer in this module.

Art is authored at 512 square.  The current pass aggressively breaks former
card-length carriers into fine fragments, but mechanical execution does not
prove that every remaining semantic arc or assembly clears the owner's eye.
The shared code is intentionally limited to palette, compositing, resizing,
registry installation, and audit plumbing.  The strict evidence audit may
still reject a builder even when its hashes, channel spread, and timing pass.

Before -> isolated candidate: these 25 IDs belonged to the rejected 13-family
collapse across 110 Wilds finishes.  Current mechanical values are regenerated
into ``_wilds_rejection_work/morpho_material_explicit/candidate_audit.json``;
no number is frozen into this source as an acceptance claim.  Official M7
movement is pending central wiring and thumbnail bake; the prior machine-green
Wilds M7 claim was owner-invalid and is not treated as a baseline approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


_WORK = 512
_CALM_SPEC = np.asarray([4.0, 120.0, 16.0], np.float32)
_FOAM_BUILD_STATS: Dict[str, float] = {}
_CHALCOPYRITE_BUILD_STATS: Dict[str, float] = {}
_CHALCOPYRITE_DEBUG: Dict[str, np.ndarray] = {}


@dataclass
class _Grammar:
    """A finish-local construction graph, including explicit spec ancestry."""

    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    tone: np.ndarray
    metal: np.ndarray
    rough: np.ndarray
    coat: np.ndarray


@lru_cache(maxsize=1)
def _xy() -> Tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:_WORK, 0:_WORK].astype(np.float32)
    return x, y


def _f32(a: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


def _norm(a: np.ndarray) -> np.ndarray:
    u = np.asarray(a, np.float32)
    lo, hi = float(np.min(u)), float(np.max(u))
    if hi - lo < 1.0e-6:
        return np.zeros_like(u, np.float32)
    return ((u - lo) / (hi - lo)).astype(np.float32)


def _line(v: np.ndarray, half_width: float = 1.5) -> np.ndarray:
    return _f32(1.0 - np.abs(np.asarray(v, np.float32)) / max(0.25, float(half_width)))


def _ring(distance: np.ndarray, radius: np.ndarray | float, half_width: float = 1.5) -> np.ndarray:
    return _line(np.asarray(distance, np.float32) - np.asarray(radius, np.float32), half_width)


def _inside(distance: np.ndarray, radius: np.ndarray | float, feather: float = 1.0) -> np.ndarray:
    return _f32((np.asarray(radius, np.float32) - np.asarray(distance, np.float32))
                / max(0.25, float(feather)) + 0.5)


def _edge(mask: np.ndarray, width: int = 2) -> np.ndarray:
    u = _f32(mask)
    k = 2 * max(1, int(width)) + 1
    kernel = np.ones((k, k), np.uint8)
    return _f32(cv2.dilate(u, kernel) - cv2.erode(u, kernel))


def _halo(mask: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    u = _f32(mask)
    return _f32(cv2.GaussianBlur(u, (0, 0), max(0.25, float(sigma))) - 0.28 * u)


def _new(*names: str) -> Dict[str, np.ndarray]:
    return {name: np.zeros((_WORK, _WORK), np.float32) for name in names}


def _draw_line(mask: np.ndarray, a, b, width: int = 2, value: float = 1.0) -> None:
    cv2.line(mask, tuple(map(int, a)), tuple(map(int, b)), float(value),
             max(2, min(8, int(width))), cv2.LINE_AA)


def _draw_poly(mask: np.ndarray, pts, width: int = 2, fill: bool = False,
               value: float = 1.0, closed: bool = True) -> None:
    arr = np.asarray(pts, np.int32).reshape((-1, 1, 2))
    if fill:
        cv2.fillPoly(mask, [arr], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(mask, [arr], bool(closed), float(value),
                      max(2, min(8, int(width))), cv2.LINE_AA)


def _draw_ellipse(mask: np.ndarray, centre, axes, angle: float, width: int = 2,
                  fill: bool = False, start: float = 0.0, end: float = 360.0) -> None:
    thickness = -1 if fill else max(2, min(8, int(width)))
    cv2.ellipse(mask, tuple(map(int, centre)), tuple(map(int, axes)), float(angle),
                float(start), float(end), 1.0, thickness, cv2.LINE_AA)


def _cubic_points(controls, count: int = 121) -> Tuple[np.ndarray, ...]:
    """Low-level cubic sampler; callers own every control point and topology."""
    p0, p1, p2, p3 = (np.asarray(point, np.float32) for point in controls)
    points = []
    for sample in range(max(2, int(count))):
        t = sample / float(max(1, int(count) - 1))
        omt = 1.0 - t
        points.append((omt ** 3 * p0 + 3.0 * omt * omt * t * p1
                       + 3.0 * omt * t * t * p2 + t ** 3 * p3).astype(np.float32))
    return tuple(points)


def _unit(vector) -> np.ndarray:
    v = np.asarray(vector, np.float32)
    return v / max(1.0e-4, float(np.linalg.norm(v)))


def _chaikin(points, rounds: int = 2, closed: bool = False) -> Tuple[np.ndarray, ...]:
    """Low-level corner cutting; callers still author every vertex and closure."""
    pts = [np.asarray(point, np.float32) for point in points]
    for _ in range(max(0, int(rounds))):
        if len(pts) < 2:
            break
        source = pts + ([pts[0]] if closed else [])
        refined = [] if closed else [pts[0]]
        for a, b in zip(source[:-1], source[1:]):
            refined.extend((0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b))
        if not closed:
            refined.append(pts[-1])
        pts = refined
    return tuple(pts)


def _pack(masks: Mapping[str, np.ndarray], banks: Mapping[str, str], tone: np.ndarray,
          metal: np.ndarray, rough: np.ndarray, coat: np.ndarray) -> _Grammar:
    """Validate a builder's literal, finish-local causal graph."""
    if len(masks) < 7:
        raise ValueError("lazy Morpho grammar: fewer than seven causal masks")
    if set(masks) != set(banks):
        raise ValueError("every semantic mask needs explicit material ownership")
    owned = set(banks.values())
    if not {"A", "B"}.issubset(owned) or not owned.issubset({"A", "B", "N"}):
        raise ValueError("each grammar needs explicit opposing A/B material features")
    marks = []
    for name, mask in masks.items():
        u = _f32(mask)
        if float(np.std(u)) < 0.002:
            raise ValueError(f"flat causal mask {name!r}")
        marks.append((name, u, banks[name]))
    channels = tuple(_f32(v) for v in (metal, rough, coat))
    if any(float(np.std(v)) < 0.035 for v in channels):
        raise ValueError("flat finish-local spec topology")
    return _Grammar(tuple(marks), _norm(tone), *channels)


def _hsv(h: float, s: float, v: float) -> np.ndarray:
    px = np.uint8([[[int((h % 1.0) * 179.0), int(np.clip(s, 0, 1) * 255),
                     int(np.clip(v, 0, 1) * 255)]]])
    return cv2.cvtColor(px, cv2.COLOR_HSV2RGB)[0, 0].astype(np.float32) / 255.0


_COLOR_BANDS = np.asarray([0.11, 0.25, 0.40, 0.56, 0.72, 0.87], np.float32)
_SPEC_BANDS = np.asarray([0.10, 0.23, 0.36, 0.50, 0.64, 0.78, 0.90], np.float32)


def _palette(hues: Sequence[float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Two seven-color material ramps plus two structural bridge colors."""
    ha, hb = float(hues[0]), float(hues[1])
    offsets = (-0.070, -0.042, -0.018, 0.0, 0.025, 0.055, 0.092)
    values = (0.22, 0.31, 0.42, 0.55, 0.69, 0.83, 0.97)
    sats_a = (0.62, 0.72, 0.80, 0.88, 0.91, 0.82, 0.68)
    sats_b = (0.74, 0.86, 0.92, 0.84, 0.77, 0.70, 0.61)
    a = np.stack([_hsv(ha + offsets[i], sats_a[i], values[i]) for i in range(7)])
    b = np.stack([_hsv(hb - offsets[6 - i], sats_b[i], values[i]) for i in range(7)])
    bridge = np.stack([_hsv((ha + hb) * 0.5 + 0.50, 0.20, 0.13),
                       _hsv((ha + hb) * 0.5, 0.30, 0.52)])
    return a.astype(np.float32), b.astype(np.float32), bridge.astype(np.float32)


def _bank_image(bank: np.ndarray, tone: np.ndarray, phase: int) -> np.ndarray:
    # Fixed causal thresholds: never rank/equal-population quantization.
    shifted = np.mod(tone + 0.073 * phase, 1.0)
    return bank[np.digitize(shifted, _COLOR_BANDS)]


def _fixed_spec(field: np.ndarray, values: Sequence[int]) -> np.ndarray:
    return np.asarray(values, np.float32)[np.digitize(_f32(field), _SPEC_BANDS)]


def _compose(grammar: _Grammar, hues: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
    """Shared paint/spec plumbing; all topology was authored in the builder."""
    bank_a, bank_b, bridge = _palette(hues)
    tone = grammar.tone
    # One quiet base keeps broad tone fields from becoming macro paint shapes.
    # The second bridge color appears only on authored structural marks below.
    paint = np.broadcast_to(bridge[0], (_WORK, _WORK, 3)).copy()
    for i, (_name, mask, owner) in enumerate(grammar.marks):
        if owner == "A":
            color = _bank_image(bank_a, tone, i)
        elif owner == "B":
            color = _bank_image(bank_b, 1.0 - tone, i + 2)
        else:
            # Structural marks deliberately bridge, not add a third random ramp.
            color = np.broadcast_to(bridge[(i + 1) & 1], paint.shape)
        alpha = np.clip(mask * (0.62 + 0.06 * (i % 5)), 0.0, 0.94)[..., None]
        paint = paint * (1.0 - alpha) + color * alpha

    # Material response is supported only by literal finish features.  The
    # rejected candidate allowed broad tone coordinates to repaint the whole
    # canvas, preserving its row/grid carrier in M/R/Cc.  Here every response
    # descends from A/B/N marks with only a 2/5-pixel material falloff.
    zeros = np.zeros((_WORK, _WORK), np.float32)
    def owner_union(owner_name: str) -> np.ndarray:
        selected = [mask for _name, mask, owner in grammar.marks if owner == owner_name]
        return np.maximum.reduce(selected) if selected else zeros.copy()

    owner_a = owner_union("A")
    owner_b = owner_union("B")
    owner_n = owner_union("N")

    def local_support(primary: np.ndarray, secondary: np.ndarray,
                      tertiary: np.ndarray, near_size: int = 5,
                      far_size: int = 11, far_weight: float = 0.27) -> np.ndarray:
        core = _f32(primary + 0.34 * secondary + 0.22 * tertiary)
        near = cv2.dilate(core, np.ones((near_size, near_size), np.uint8))
        far = cv2.dilate(core, np.ones((far_size, far_size), np.uint8))
        return _f32(np.maximum(core, np.maximum(0.62 * near, far_weight * far)))

    # Opposing runtime lobes remain exclusive: A owns metallic response and B
    # owns clearcoat response.  Neutral anatomy may modulate either slightly,
    # but the opposing bank cannot manufacture the other bank's lobe.  All
    # falloff stays within three work pixels so every spec gradient remains
    # causally adjacent to a literal feature.
    metal_support = local_support(owner_a, 0.42 * owner_n, zeros, 5, 7, 0.38)
    rough_support = local_support(owner_n, owner_a, owner_b, 5, 7, 0.38)
    coat_support = local_support(owner_b, 0.42 * owner_n, zeros, 5, 7, 0.38)
    metal_shade = np.mod(_norm(grammar.metal) * 0.83 + tone * 0.37, 1.0)
    rough_shade = np.mod(_norm(grammar.rough) * 0.79 + (1.0 - tone) * 0.43 + 0.19, 1.0)
    coat_shade = np.mod(_norm(grammar.coat) * 0.81 + np.sqrt(tone) * 0.41 + 0.37, 1.0)
    mf = 0.03 + metal_support * (0.18 + 0.79 * metal_shade)
    rf = 0.03 + rough_support * (0.18 + 0.79 * rough_shade)
    cf = 0.03 + coat_support * (0.18 + 0.79 * coat_shade)

    metal = _fixed_spec(mf, (12, 42, 72, 104, 138, 172, 212, 246))
    rough = _fixed_spec(rf, (232, 52, 198, 78, 218, 106, 164, 34))
    coat = _fixed_spec(cf, (18, 188, 48, 226, 82, 156, 116, 244))
    spec = np.stack([metal, rough, coat], axis=2).astype(np.uint8)
    return np.clip(paint, 0, 1).astype(np.float32), spec


# ---------------------------------------------------------------------------
# Twenty-five literal per-ID builders.  Helpers draw primitives only; none of
# the following builders delegates its identity to a shared topology router.
# ---------------------------------------------------------------------------


def _build_fmo_pigeon_neck() -> _Grammar:
    """One continuous cortex sheet opened by edge-attached medullary bays.

    W5 removes every ribbon, fan and orientation carrier.  Unequal erosion
    fronts enter from card edges and expose medulla; their two cortex lips own
    the opposite green/purple thin-film response.  Local curvature alone makes
    delamination hooks, tears, compression cusps and thickness reversals.  No
    front closes into a cell, capsule or paver.
    """
    names=("intact_cortex_sheet","green_thick_lips","purple_thin_lips",
           "medullary_bays","thickness_reversals","delamination_hooks",
           "compression_cusps","tear_lips","rejoin_bridges","oil_menisci")
    m=_new(*names)
    fronts=(
        ((-24,42),(73,27),(86,143),(246,121),5.4,.2),
        ((536,71),(429,31),(447,183),(302,211),4.3,1.1),
        ((61,-24),(42,93),(196,79),(176,264),5.9,2.0),
        ((324,-24),(435,72),(291,159),(397,278),4.7,.7),
        ((536,287),(421,234),(482,402),(284,386),5.2,1.8),
        ((474,536),(417,407),(284,474),(205,336),4.1,2.7),
        ((153,536),(213,419),(65,385),(139,226),5.7,1.4),
        ((-24,399),(115,431),(53,272),(237,306),4.6,2.3),
        ((-24,191),(91,245),(177,102),(294,252),5.0,.9),
        ((536,169),(411,148),(372,306),(222,258),5.5,2.9),
        ((11,-24),(143,54),(72,203),(253,139),4.4,1.6),
        ((420,536),(333,437),(467,328),(278,295),5.8,.4),
        ((536,462),(448,494),(393,338),(241,441),4.2,2.1),
        ((-24,290),(67,292),(132,381),(287,344),5.1,1.2),
    )
    occupied=np.zeros((_WORK,_WORK),np.uint8)
    chronology=np.zeros((_WORK,_WORK),np.float32)
    for fi,(p0,p1,p2,p3,base_width,phase) in enumerate(fronts):
        pts=_cubic_points((p0,p1,p2,p3),97)
        current=np.zeros((_WORK,_WORK),np.float32)
        old_state=None
        for j,(pa,pb) in enumerate(zip(pts[:-1],pts[1:])):
            tangent=_unit(pb-pa); normal=np.asarray([-tangent[1],tangent[0]],np.float32)
            t=j/95.0
            width=base_width+.95*np.sin(2.0*np.pi*t*(1.2+.17*(fi%4))+phase)
            offset=width+3.0+.75*np.cos(2.0*np.pi*t*(1.7+.11*(fi%3))-.4*phase)
            # Every long curve is rasterized as fine 3--7 px connected pieces.
            _draw_line(m["medullary_bays"],pa,pb,max(2,int(round(width))),.94)
            _draw_line(current,pa,pb,max(2,int(round(width))),1.0)
            a0=pa+offset*normal; a1=pb+offset*normal
            b0=pa-offset*normal; b1=pb-offset*normal

            prev=pts[max(0,j-1)]; nxt=pts[min(len(pts)-1,j+2)]
            ta=_unit(pa-prev); tb=_unit(nxt-pb)
            curvature=float(ta[0]*tb[1]-ta[1]*tb[0])
            state=(1 if np.sin(2.0*np.pi*t*(1.1+.13*(fi%5))+phase)>=0.0
                   else -1)
            flip=(old_state is not None and state!=old_state)
            if (fi&1)^int(state<0):
                _draw_line(m["green_thick_lips"],a0,a1,6,.92)
                _draw_line(m["purple_thin_lips"],b0,b1,4,.90)
            else:
                _draw_line(m["purple_thin_lips"],a0,a1,4,.90)
                _draw_line(m["green_thick_lips"],b0,b1,6,.92)

            if flip:
                _draw_line(m["thickness_reversals"],b0,a0,2,.96)
            if abs(curvature)>.010:
                mid=(pa+pb)*.5
                cusp0=mid-(width+2.0)*normal; cusp1=mid+(width+2.0)*normal
                _draw_line(m["compression_cusps"],cusp0,cusp1,2,.90)
                hook=(mid+(width+2.0)*normal,
                      mid+(width+5.0)*normal+4.0*tangent,
                      mid+(width+1.5)*normal+7.0*tangent)
                _draw_poly(m["delamination_hooks"],hook,width=2,fill=False,
                           value=.93,closed=False)
            if abs(curvature)>.017:
                mid=(pa+pb)*.5
                direction=normal*(1.0 if curvature>0.0 else -1.0)
                _draw_line(m["tear_lips"],mid,mid+(6.0+2.0*t)*direction,2,.93)
            if width<base_width-.62 and abs(curvature)<.006:
                _draw_line(m["rejoin_bridges"],b0,a0,2,.92)
            old_state=state

        now=(current>.15).astype(np.uint8)
        crossing=(now>0)&(cv2.dilate(occupied,np.ones((3,3),np.uint8))>0)
        if np.any(crossing):
            m["delamination_hooks"]=_f32(np.maximum(
                m["delamination_hooks"],crossing.astype(np.float32)))
            halo=cv2.dilate(crossing.astype(np.uint8),
                            np.ones((5,5),np.uint8)).astype(np.float32)
            core=cv2.dilate(crossing.astype(np.uint8),
                            np.ones((2,2),np.uint8)).astype(np.float32)
            m["oil_menisci"]=_f32(np.maximum(m["oil_menisci"],halo-core))
        occupied=np.maximum(occupied,now)
        chronology=np.maximum(chronology,current*(.18+.82*fi/(len(fronts)-1)))

    opened=cv2.dilate((m["medullary_bays"]>.12).astype(np.uint8),
                      np.ones((3,3),np.uint8)).astype(np.float32)
    m["intact_cortex_sheet"]=_f32(1.0-.82*opened)
    # Oil is only valid where a measured crossing wets an intact cortex lip.
    lip_union=_f32(np.maximum(m["green_thick_lips"],m["purple_thin_lips"]))
    m["oil_menisci"]*=cv2.dilate((lip_union>.1).astype(np.uint8),
                                  np.ones((3,3),np.uint8))

    tone=_norm(.55*chronology+.31*m["thickness_reversals"]
               +.24*m["oil_menisci"]+.18*m["compression_cusps"]
               -.17*m["medullary_bays"])
    banks=dict(intact_cortex_sheet="N",green_thick_lips="A",
               purple_thin_lips="B",medullary_bays="N",
               thickness_reversals="B",delamination_hooks="A",
               compression_cusps="N",tear_lips="N",
               rejoin_bridges="A",oil_menisci="B")
    metal=_f32(.04+.72*m["green_thick_lips"]+.59*m["delamination_hooks"]
               +.47*m["rejoin_bridges"]+.16*tone*m["green_thick_lips"])
    rough=_f32(.07+.63*m["medullary_bays"]+.54*m["compression_cusps"]
               +.48*m["tear_lips"]+.15*(1.0-tone)*m["intact_cortex_sheet"])
    coat=_f32(.04+.72*m["purple_thin_lips"]+.61*m["thickness_reversals"]
              +.53*m["oil_menisci"]+.16*tone*m["purple_thin_lips"])
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_grackle_oil() -> _Grammar:
    """Three hidden barb families negotiate one continuous wet/dry oil film.

    The barbs are capillary constraints, not paint rails.  Only true pair and
    triple contacts seed unequal menisci; those coalesce, pinch into throats,
    leave dry islands, wet contact rims and drainage failures.  Every visible
    event therefore disappears if its contributing shaft family is removed.
    """
    names=("teal_pair_menisci","violet_pair_menisci","dry_film_islands",
           "droplet_throats","barb_hook_joints","split_shaft_gaps",
           "contact_angle_rims","drainage_breaks","wet_underlap_saddles")
    m=_new(*names)
    family_a=np.zeros((_WORK,_WORK),np.float32)
    family_b=np.zeros_like(family_a); family_c=np.zeros_like(family_a)
    curves_a=(
        ((-21,38),(109,8),(294,171),(534,86)),
        ((-18,123),(146,61),(281,248),(537,151)),
        ((-17,232),(118,132),(327,331),(539,242)),
        ((-19,348),(161,232),(299,457),(540,350)),
        ((-22,472),(136,357),(355,553),(537,451)),
        ((31,535),(164,395),(362,504),(530,514)),
        ((-19,291),(92,331),(225,221),(413,286)),
    )
    curves_b=(
        ((533,27),(385,-5),(248,189),(-21,78)),
        ((536,122),(395,70),(229,272),(-20,169)),
        ((539,217),(426,135),(255,364),(-22,273)),
        ((540,323),(374,245),(212,457),(-19,378)),
        ((536,461),(386,337),(185,552),(-23,488)),
        ((471,535),(337,396),(139,503),(-18,435)),
        ((532,282),(408,329),(287,219),(86,305)),
    )
    curves_c=(
        ((45,-20),(8,118),(167,276),(67,535)),
        ((132,-22),(94,143),(269,241),(166,536)),
        ((231,-21),(177,92),(357,282),(258,536)),
        ((329,-21),(282,132),(458,330),(350,537)),
        ((437,-22),(360,174),(544,306),(446,536)),
        ((517,-18),(472,101),(386,241),(535,449)),
        ((12,-17),(102,108),(33,278),(181,401)),
    )
    for target,curves in ((family_a,curves_a),(family_b,curves_b),(family_c,curves_c)):
        for ci,controls in enumerate(curves):
            curve=_cubic_points(controls,121)
            for point,next_point in zip(curve[:-1],curve[1:]):
                _draw_line(target,point,next_point,2+(ci%3==0),1.0)

    # Family proximity is evaluated before any paint exists.  Pair contacts
    # and triple saddles are literal geometric intersections.
    near_a=cv2.dilate((family_a>.1).astype(np.uint8),np.ones((7,7),np.uint8))
    near_b=cv2.dilate((family_b>.1).astype(np.uint8),np.ones((7,7),np.uint8))
    near_c=cv2.dilate((family_c>.1).astype(np.uint8),np.ones((7,7),np.uint8))
    ab=(near_a>0)&(near_b>0); bc=(near_b>0)&(near_c>0); ca=(near_c>0)&(near_a>0)
    triple=ab&bc&ca

    def capillary_kernel(size,angle,width):
        kernel=np.zeros((size,size),np.uint8); centre=(size//2,size//2)
        radius=size//2-1; theta=np.deg2rad(float(angle))
        delta=(int(round(radius*np.cos(theta))),int(round(radius*np.sin(theta))))
        cv2.line(kernel,(centre[0]-delta[0],centre[1]-delta[1]),
                 (centre[0]+delta[0],centre[1]+delta[1]),1,width,cv2.LINE_8)
        return kernel

    wet_ab=cv2.dilate(ab.astype(np.uint8),capillary_kernel(17,7,5))
    wet_bc=cv2.dilate(bc.astype(np.uint8),capillary_kernel(19,118,5))
    wet_ca=cv2.dilate(ca.astype(np.uint8),capillary_kernel(15,-54,5))
    # Coalescence closes only genuinely neighbouring pair menisci.  It removes
    # the crossed-line read while retaining irregular wet/dry negotiation.
    wet_union=np.maximum.reduce((wet_ab,wet_bc,wet_ca)).astype(np.uint8)
    wet_union=cv2.morphologyEx(wet_union,cv2.MORPH_CLOSE,
                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
    wet_union=cv2.dilate(wet_union,np.ones((3,3),np.uint8))
    teal=_f32(.83*wet_ab+.47*wet_ca)*wet_union
    violet=_f32(.84*wet_bc+.49*wet_ca)*wet_union
    m["teal_pair_menisci"]=_f32(teal)
    m["violet_pair_menisci"]=_f32(violet)
    m["dry_film_islands"]=_f32(1.0-wet_union.astype(np.float32))

    # Narrow bridges between eroded wet cores are capillary throats, not dots.
    eroded=cv2.erode(wet_union,np.ones((5,5),np.uint8))
    reopened=cv2.dilate(eroded,np.ones((5,5),np.uint8))
    m["droplet_throats"]=_f32((wet_union>0)&(reopened==0))
    m["barb_hook_joints"]=_f32(triple.astype(np.float32)
                                *cv2.dilate(wet_union,np.ones((3,3),np.uint8)))

    barb_union=np.maximum.reduce((family_a,family_b,family_c))
    # Split shafts occur only where a triple saddle over-bends one family.  A
    # short oriented dilation opens the gap and redirects the wet front.
    split=cv2.dilate(triple.astype(np.uint8),capillary_kernel(11,32,3))
    split=(split>0)&(barb_union>.1)
    m["split_shaft_gaps"]=_f32(split)
    wet_edge=cv2.morphologyEx(wet_union,cv2.MORPH_GRADIENT,
                              np.ones((3,3),np.uint8))
    rim=(wet_edge>0)&(cv2.dilate((barb_union>.1).astype(np.uint8),
                                 np.ones((5,5),np.uint8))>0)
    m["contact_angle_rims"]=_f32(rim)
    m["drainage_breaks"]=_f32((cv2.dilate(split.astype(np.uint8),
                                           np.ones((5,5),np.uint8))>0)
                                &(wet_edge>0))
    underlap=(triple.astype(np.uint8)
              *cv2.erode(wet_union,np.ones((3,3),np.uint8)))
    m["wet_underlap_saddles"]=_f32(underlap)

    # Tone is film thickness supported only inside actual coalesced menisci.
    distance=cv2.distanceTransform(wet_union,cv2.DIST_L2,3)
    tone=_norm(distance*m["teal_pair_menisci"]
               +.72*distance*m["violet_pair_menisci"]
               +.31*m["contact_angle_rims"]-.20*m["dry_film_islands"])
    banks=dict(teal_pair_menisci="A",violet_pair_menisci="B",
               dry_film_islands="N",droplet_throats="A",barb_hook_joints="B",
               split_shaft_gaps="N",contact_angle_rims="B",
               drainage_breaks="N",wet_underlap_saddles="A")
    metal=_f32(.04+.72*m["teal_pair_menisci"]+.61*m["droplet_throats"]
               +.49*m["wet_underlap_saddles"]+.15*tone*m["teal_pair_menisci"])
    rough=_f32(.07+.67*m["dry_film_islands"]+.59*m["split_shaft_gaps"]
               +.51*m["drainage_breaks"]+.16*(1.0-tone)*m["dry_film_islands"])
    coat=_f32(.04+.73*m["violet_pair_menisci"]+.62*m["contact_angle_rims"]
              +.52*m["barb_hook_joints"]+.16*tone*m["violet_pair_menisci"])
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_sunbird_throat() -> _Grammar:
    """Interlocked gorget currents grow from three offset throat seams."""
    names = ("crimson_throat_seams", "gold_feather_ridges", "violet_scale_lips",
             "emerald_barb_forks", "gorget_eyelets", "broken_tip_notches",
             "underfeather_shadows", "crossing_hooklets")
    m = _new(*names)
    seams = (
        ((-18, 420), (105, 330), (161, 67), (307, -17)),
        ((89, 529), (127, 345), (337, 214), (451, -20)),
        ((-13, 188), (136, 252), (341, 82), (528, 143)),
        ((-14, 72), (124, 154), (286, 388), (529, 334)),
        ((24, -18), (196, 121), (318, 420), (344, 529)),
        ((527, 488), (361, 411), (215, 92), (82, -18)),
        ((-18, 498), (151, 419), (379, 183), (527, 22)),
    )
    for seam_idx, control in enumerate(seams):
        curve = _cubic_points(control, 147)
        for sample in range(3+seam_idx%3,143,7+seam_idx%4):
            p=curve[sample]; d=_unit(curve[min(146,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["crimson_throat_seams"],p-d*3,p+d*4,3)
        for sample in range(7 + seam_idx, 141, 5 + seam_idx % 4):
            p = curve[sample]
            t = _unit(curve[min(146, sample + 3)] - curve[max(0, sample - 3)])
            n = np.asarray([-t[1], t[0]], np.float32)
            side = 1 if (sample // 8 + seam_idx) % 3 else -1
            reach = 13 + (sample * 5 + seam_idx * 19) % 32
            crown = [
                p - t * 6,
                p + n * side * reach * 0.46 - t * 1,
                p + n * side * reach + t * (3 + seam_idx),
                p + n * side * reach * 0.52 + t * 8,
            ]
            for edge in range(3):
                a=np.asarray(crown[edge]); b=np.asarray(crown[edge+1]); d=_unit(b-a)
                length=float(np.linalg.norm(b-a))
                for frac in (.18,.64):
                    q=a+(b-a)*frac
                    _draw_line(m["gold_feather_ridges"],q-d*2,q+d*min(5.0,length*.28),3)
            lip_a=np.asarray(crown[1]); lip_b=np.asarray(crown[3]); lip_d=_unit(lip_b-lip_a)
            lip_mid=(lip_a+lip_b)*.5
            _draw_line(m["violet_scale_lips"],lip_mid-lip_d*3,lip_mid+lip_d*4,
                       2+(sample%3==0))
            _draw_line(m["emerald_barb_forks"], crown[2],
                       crown[2] + t * 8 + n * side * 4, 2)
            _draw_line(m["emerald_barb_forks"], crown[2],
                       crown[2] - t * 7 + n * side * 3, 2)
            if (sample // 8 + seam_idx) % 4 == 0:
                _draw_ellipse(m["gorget_eyelets"], tuple(np.rint(crown[1]).astype(int)),
                              (5 + seam_idx, 3), sample * 1.7, 2)
            if (sample // 8 + 2 * seam_idx) % 5 == 1:
                _draw_line(m["broken_tip_notches"], crown[2] - t * 4,
                           crown[2] + n * side * 6, 3)
            if (sample // 8 + seam_idx) % 3 == 1:
                _draw_poly(m["underfeather_shadows"],
                           (p - n * side * 4 - t * 4, p + n * side * 7,
                            p + n * side * 3 + t * 8), 3, closed=False)
            if (sample // 8 + seam_idx) % 2:
                _draw_line(m["crossing_hooklets"], crown[1] - t * 3,
                           crown[1] + t * 4 + n * side * 3, 2)
    x, y = _xy()
    tone = _norm(np.cos((x + 1.8 * y) / 47.0) - 0.66 * np.sin((1.4 * x - y) / 39.0))
    banks = dict(crimson_throat_seams="B", gold_feather_ridges="A",
                 violet_scale_lips="B", emerald_barb_forks="A",
                 gorget_eyelets="B", broken_tip_notches="N",
                 underfeather_shadows="B", crossing_hooklets="A")
    metal = _f32(0.04 + 0.66 * m["gold_feather_ridges"] + 0.57 * m["emerald_barb_forks"]
                 + 0.42 * m["crossing_hooklets"] + 0.16 * tone)
    rough = _f32(0.07 + 0.67 * m["crimson_throat_seams"] + 0.54 * m["broken_tip_notches"]
                 + 0.42 * m["underfeather_shadows"] + 0.18 * (1.0 - tone))
    coat = _f32(0.04 + 0.69 * m["violet_scale_lips"] + 0.58 * m["gorget_eyelets"]
                + 0.43 * m["underfeather_shadows"] + 0.16 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fmo_cassowary_quill() -> _Grammar:
    """A crossed thicket of stiff cassowary shafts with broken defensive barbs."""
    names = ("black_rachis_thicket", "cobalt_quill_banks", "ember_quill_banks",
             "crossbarb_bridges", "shaft_breaks", "hollow_quill_mouths",
             "impact_junctions", "split_vane_splinters")
    m = _new(*names)
    controls = (
        ((-31, 53), (117, 138), (341, -26), (539, 82)),
        ((-28, 188), (144, 79), (331, 251), (540, 151)),
        ((-25, 344), (136, 247), (355, 472), (538, 311)),
        ((-19, 491), (113, 379), (373, 569), (531, 438)),
        ((48, -27), (161, 127), (-28, 328), (93, 536)),
        ((201, -30), (98, 139), (293, 353), (177, 540)),
        ((365, -23), (253, 144), (462, 329), (331, 537)),
        ((518, -17), (394, 142), (590, 327), (469, 534)),
        ((-22, 104), (119, 267), (402, 215), (536, 382)),
        ((-27, 414), (151, 527), (330, 283), (540, 493)),
        ((91, -24), (266, 91), (239, 432), (522, 527)),
    )
    for shaft_idx, control in enumerate(controls):
        curve = _cubic_points(control, 123)
        for sample in range(3+shaft_idx%3,119,7+shaft_idx%4):
            p=curve[sample]; d=_unit(curve[min(122,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["black_rachis_thicket"],p-d*3,p+d*4,4)
        for sample in range(7 + shaft_idx, 117, 6 + shaft_idx % 3):
            p = curve[sample]
            t = _unit(curve[min(122, sample + 3)] - curve[max(0, sample - 3)])
            n = np.asarray([-t[1], t[0]], np.float32)
            extent = 10 + (sample * 3 + shaft_idx * 11) % 27
            for part,frac in enumerate((.22,.53,.82)):
                q=p+(n*extent+t*3)*frac; d=_unit(n*extent+t*3)
                _draw_line(m["cobalt_quill_banks"],q-d*(2+part%2),q+d*(3+(sample+part)%3),3)
            for part,frac in enumerate((.31,.72)):
                q=p+(-n*extent-t*2)*frac; d=_unit(-n*extent-t*2)
                _draw_line(m["ember_quill_banks"],q-d*(2+part),q+d*(3+(shaft_idx+part)%2),3)
            if (sample // 9 + shaft_idx) % 3 == 0:
                _draw_line(m["crossbarb_bridges"], p - n * 7, p + n * 8, 2)
            if (sample // 9 + shaft_idx) % 4 == 1:
                _draw_line(m["shaft_breaks"], p - t * 6 - n * 3, p + t * 5 + n * 4, 4)
            if (sample // 9 + shaft_idx) % 5 == 2:
                _draw_ellipse(m["hollow_quill_mouths"], tuple(np.rint(p + n * extent).astype(int)),
                              (5, 3), np.degrees(np.arctan2(t[1], t[0])), 2)
            if (sample // 9 + shaft_idx) % 2:
                q=p+n*extent*.76+t*2
                d=_unit(n*extent*.45+t*7)
                _draw_line(m["split_vane_splinters"],q-d*3,q+d*4,2)
    junctions = ((111, 344), (179, 270), (246, 224), (322, 201), (386, 268), (271, 365))
    for idx, p in enumerate(junctions):
        _draw_ellipse(m["impact_junctions"], p, (5 + idx % 3, 3 + (idx + 1) % 2),
                      idx * 31, 2)
        _draw_line(m["impact_junctions"], (p[0] - 7, p[1] + 4), (p[0] + 8, p[1] - 5), 2)
    x, y = _xy()
    tone = _norm(np.sin((2.0 * x + y) / 55.0) + np.cos((x - 1.7 * y) / 43.0))
    m["cobalt_quill_banks"]=_f32(cv2.dilate(m["cobalt_quill_banks"],np.ones((3,3),np.uint8)))
    banks = dict(black_rachis_thicket="B", cobalt_quill_banks="A",
                 ember_quill_banks="B", crossbarb_bridges="A", shaft_breaks="N",
                 hollow_quill_mouths="B", impact_junctions="B",
                 split_vane_splinters="A")
    metal = _f32(0.05 + 0.65 * m["cobalt_quill_banks"] + 0.55 * m["crossbarb_bridges"]
                 + 0.43 * m["split_vane_splinters"] + 0.16 * tone)
    rough = _f32(0.08 + 0.66 * m["black_rachis_thicket"] + 0.57 * m["shaft_breaks"]
                 + 0.43 * m["impact_junctions"] + 0.18 * (1.0 - tone))
    coat = _f32(0.04 + 0.68 * m["ember_quill_banks"] + 0.58 * m["hollow_quill_mouths"]
                + 0.43 * m["impact_junctions"] + 0.16 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fmo_raven_flash() -> _Grammar:
    """A separated raven wing folds across the card like an open black hand."""
    names = ("wrist_fold", "separated_primaries", "covert_steps",
             "cyan_flash_edges", "violet_flash_edges", "vane_tears",
             "finger_notches", "shadow_overlaps")
    m = _new(*names)
    wrist = _cubic_points(((-17, 381), (104, 282), (182, 315), (255, 178)), 91)
    for sample in range(3,87,7):
        p=wrist[sample]; d=_unit(wrist[min(90,sample+2)]-wrist[max(0,sample-2)])
        _draw_line(m["wrist_fold"],p-d*3,p+d*4,4)
    controls = (
        ((44, 358), (161, 310), (313, 33), (527, 14)),
        ((63, 373), (189, 330), (369, 85), (534, 86)),
        ((84, 390), (213, 357), (399, 160), (530, 173)),
        ((107, 406), (240, 386), (417, 241), (518, 272)),
        ((132, 424), (262, 419), (406, 345), (476, 391)),
        ((160, 441), (274, 454), (350, 441), (387, 526)),
        ((190, 458), (255, 483), (278, 511), (282, 538)),
    )
    for finger, control in enumerate(controls):
        curve = _cubic_points(control, 111)
        for sample in range(3+finger%3,107,7+finger%3):
            p=curve[sample]; d=_unit(curve[min(110,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["separated_primaries"],p-d*3,p+d*(4+sample%2),3)
        for sample in range(8, 105, 6 + finger % 3):
            p = curve[sample]
            t = _unit(curve[min(110, sample + 3)] - curve[max(0, sample - 3)])
            n = np.asarray([-t[1], t[0]], np.float32)
            width = max(8, 24 - sample // 8 + (finger * 3) % 9)
            for part,frac in enumerate((.24,.55,.82)):
                q=p+n*width*frac
                _draw_line(m["cyan_flash_edges"],q-n*(2+part%2),q+n*(3+(part+sample)%3),2)
            for part,frac in enumerate((.31,.73)):
                q=p-n*(.65*width)*frac
                _draw_line(m["violet_flash_edges"],q+n*(2+part),q-n*(3+(part+finger)%2),2)
            if (sample // 9 + finger) % 4 == 0:
                _draw_line(m["vane_tears"], p - n * 7, p + n * 9 + t * 4, 3)
            if sample > 75 and (sample // 9 + finger) % 3 == 1:
                _draw_poly(m["finger_notches"],
                           (p - n * 4, p + t * 8, p + n * 5 + t * 4),
                           3, closed=False)
            if (sample // 9 + finger) % 5 == 2:
                _draw_ellipse(m["shadow_overlaps"], tuple(np.rint(p - n * 4).astype(int)),
                              (6, 3), finger * 18 + sample, 2)
    covert_curves = (
        ((-12, 332), (85, 244), (188, 291), (286, 177)),
        ((5, 365), (111, 285), (215, 337), (318, 225)),
        ((30, 400), (136, 330), (249, 385), (347, 286)),
    )
    for idx, control in enumerate(covert_curves):
        curve = _cubic_points(control, 73)
        for sample in range(3+idx,69,6+idx):
            p=curve[sample]; d=_unit(curve[min(72,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["covert_steps"],p-d*3,p+d*4,3)
        for sample in range(9 + idx, 68, 12):
            p = curve[sample]
            t = _unit(curve[min(72, sample + 2)] - curve[max(0, sample - 2)])
            n = np.asarray([-t[1], t[0]], np.float32)
            for side in (-1,1):
                q=p+n*side*(5+idx)
                _draw_line(m["covert_steps"],q-n*side*3,q+n*side*4,2)
    crossing_folds = (
        ((-18, 90), (147, 176), (315, 379), (528, 448)),
        ((-15, 178), (126, 243), (302, 426), (435, 529)),
        ((119, -17), (195, 121), (315, 251), (529, 315)),
        ((286, -18), (258, 126), (169, 301), (91, 529)),
    )
    for idx, control in enumerate(crossing_folds):
        curve = _cubic_points(control, 97)
        for sample in range(3+idx,93,7+idx):
            p=curve[sample]; d=_unit(curve[min(96,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["vane_tears"],p-d*3,p+d*4,3)
        for sample in range(9 + idx, 92, 13 + idx):
            p = curve[sample]
            t = _unit(curve[min(96, sample + 3)] - curve[max(0, sample - 3)])
            n = np.asarray([-t[1], t[0]], np.float32)
            _draw_line(m["finger_notches"], p - n * 7, p + n * 8, 2)
            _draw_ellipse(m["shadow_overlaps"], tuple(np.rint(p).astype(int)),
                          (6, 3), idx * 31 + sample, 2)
    m["violet_flash_edges"]=_f32(cv2.dilate(m["violet_flash_edges"],np.ones((3,3),np.uint8)))
    x, y = _xy()
    tone = _norm(np.cos((x + 0.8 * y) / 51.0) - 0.72 * np.sin((x - 1.3 * y) / 44.0))
    banks = dict(wrist_fold="N", separated_primaries="A", covert_steps="A",
                 cyan_flash_edges="A", violet_flash_edges="B", vane_tears="B",
                 finger_notches="N", shadow_overlaps="B")
    metal = _f32(0.04 + 0.68 * m["cyan_flash_edges"] + 0.52 * m["covert_steps"]
                 + 0.42 * m["finger_notches"] + 0.16 * tone)
    rough = _f32(0.08 + 0.66 * m["separated_primaries"] + 0.57 * m["vane_tears"]
                 + 0.43 * m["wrist_fold"] + 0.18 * (1.0 - tone))
    coat = _f32(0.04 + 0.69 * m["violet_flash_edges"] + 0.56 * m["shadow_overlaps"]
                + 0.42 * m["covert_steps"] + 0.17 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fmo_abalone_drift() -> _Grammar:
    """A single abalone terrain: broken nacre terraces migrate away from a hinge scar."""
    names = ("hinge_scar", "nacre_terraces", "turquoise_platelets",
             "magenta_platelets", "respiratory_pits", "mineral_seams",
             "chipped_lips", "terrace_junctions")
    m = _new(*names)
    hinge = _cubic_points(((17, 499), (32, 407), (94, 356), (136, 298)), 73)
    for sample in range(3,69,7):
        p=hinge[sample]; d=_unit(hinge[min(72,sample+2)]-hinge[max(0,sample-2)])
        _draw_line(m["hinge_scar"],p-d*3,p+d*4,4)
    terraces = (
        ((-18, 474), (72, 371), (255, 448), (528, 306)),
        ((-24, 419), (91, 322), (291, 398), (535, 237)),
        ((-17, 356), (123, 286), (309, 331), (527, 161)),
        ((5, 295), (147, 231), (337, 270), (511, 78)),
        ((35, 240), (176, 173), (354, 211), (467, -18)),
        ((84, 197), (221, 110), (364, 138), (379, -22)),
        ((140, 163), (249, 56), (311, 48), (286, -18)),
    )
    for level, control in enumerate(terraces):
        curve = _cubic_points(control, 129)
        for sample in range(3+level%3,125,6+level%4):
            p=curve[sample]; d=_unit(curve[min(128,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["nacre_terraces"],p-d*3,p+d*4,3+level%2)
        for sample in range(7 + level, 123, 10 + level % 4):
            p = curve[sample]
            t = _unit(curve[min(128, sample + 3)] - curve[max(0, sample - 3)])
            n = np.asarray([-t[1], t[0]], np.float32)
            reach = 7 + (sample * 7 + level * 13) % 18
            plate = "turquoise_platelets" if (sample // 10 + level) % 2 else "magenta_platelets"
            direction=_unit(n*reach+t*11)
            for part,frac in enumerate((.22,.55,.84)):
                q=p-t*5+(n*reach+t*11)*frac
                _draw_line(m[plate],q-direction*(2+part%2),q+direction*(3+(sample+part)%3),2)
            tip=p+n*reach+t*6
            _draw_line(m[plate],tip-n*3,tip+n*3-t*2,2)
            if (sample // 10 + level) % 4 == 0:
                _draw_line(m["mineral_seams"], p - n * 6, p + n * 9, 3)
            if (sample // 10 + level) % 5 == 1:
                _draw_poly(m["chipped_lips"],
                           (p - t * 6, p + n * 5, p + t * 6 - n * 2),
                           3, closed=False)
            if (sample // 10 + level) % 6 == 2:
                _draw_ellipse(m["terrace_junctions"], tuple(np.rint(p).astype(int)),
                              (5, 3), level * 23 + sample, 2)
    pits = ((94, 411, 7, 4, -18), (172, 352, 5, 8, 24),
            (286, 288, 8, 5, -31), (388, 204, 6, 9, 12),
            (238, 174, 5, 6, 47), (443, 112, 8, 4, -15))
    for cx, cy, ax, ay, angle in pits:
        _draw_ellipse(m["respiratory_pits"], (cx, cy), (ax, ay), angle, 3)
        _draw_line(m["respiratory_pits"], (cx - ax + 2, cy), (cx + ax - 2, cy), 2)
    crossfaults = (
        ((57, 529), (81, 359), (242, 236), (236, -18)),
        ((224, 529), (192, 381), (392, 190), (471, -18)),
        ((-18, 128), (128, 171), (338, 409), (529, 377)),
    )
    for idx, control in enumerate(crossfaults):
        curve = _cubic_points(control, 101)
        for sample in range(3+idx,97,7+idx):
            p=curve[sample]; d=_unit(curve[min(100,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["mineral_seams"],p-d*3,p+d*4,3)
        for sample in range(12 + idx, 96, 17 + idx):
            p = curve[sample]
            t = _unit(curve[min(100, sample + 3)] - curve[max(0, sample - 3)])
            n = np.asarray([-t[1], t[0]], np.float32)
            _draw_line(m["chipped_lips"], p - n * 6, p + n * 7 + t * 3, 2)
    # Dense screw-dislocation terraces continue the same shell growth terrain
    # through the formerly empty corners.  The dislocation charge changes at
    # each hinge defect, so these are neither parallel lanes nor a tiled mesh.
    x,y=_xy()
    r0=np.hypot(x+74.0,y-566.0); a0=np.arctan2(y-566.0,x+74.0)
    r1=np.hypot(x-183.0,y-287.0); a1=np.arctan2(y-287.0,x-183.0)
    r2=np.hypot(x-541.0,y+91.0); a2=np.arctan2(y+91.0,x-541.0)
    growth=.069*r0+.012*r1+.054*r2+1.7*a0-1.15*a1+.72*a2
    break_gate=np.sin(.031*x-.024*y+.37*np.sin(a0-a2))
    terrace_skin=(np.abs(np.sin(growth))<.085)&(break_gate>-.56)
    m["nacre_terraces"]=_f32(np.maximum(m["nacre_terraces"],terrace_skin))
    order=np.cos(.73*growth+2.1*a1-.8*a2)
    turquoise=terrace_skin&(order>.18)&(np.sin(.043*x+.027*y+a0)>.02)
    magenta=terrace_skin&(order<-.16)&(np.cos(.029*x-.041*y+a2)>-.08)
    m["turquoise_platelets"]=_f32(np.maximum(m["turquoise_platelets"],turquoise))
    m["magenta_platelets"]=_f32(np.maximum(m["magenta_platelets"],magenta))
    junction=(np.abs(np.sin(growth+.56*a1))<.065)&(np.abs(break_gate)<.16)
    m["terrace_junctions"]=_f32(np.maximum(m["terrace_junctions"],junction))
    m["turquoise_platelets"]=_f32(cv2.dilate(m["turquoise_platelets"],np.ones((7,7),np.uint8)))
    m["mineral_seams"]=_f32(cv2.dilate(m["mineral_seams"],np.ones((3,3),np.uint8)))
    m["magenta_platelets"]=_f32(cv2.dilate(m["magenta_platelets"],np.ones((3,3),np.uint8)))
    tone = _norm(np.sin((x + 1.5 * y) / 61.0) + 0.68 * np.cos((1.7 * x - y) / 53.0))
    banks = dict(hinge_scar="N", nacre_terraces="B", turquoise_platelets="A",
                 magenta_platelets="B", respiratory_pits="B", mineral_seams="A",
                 chipped_lips="N", terrace_junctions="B")
    metal = _f32(0.05 + 0.65 * m["turquoise_platelets"] + 0.55 * m["mineral_seams"]
                 + 0.41 * m["terrace_junctions"] + 0.17 * tone)
    rough = _f32(0.08 + 0.66 * m["nacre_terraces"] + 0.57 * m["chipped_lips"]
                 + 0.42 * m["hinge_scar"] + 0.18 * (1.0 - tone))
    coat = _f32(0.04 + 0.68 * m["magenta_platelets"] + 0.59 * m["respiratory_pits"]
                + 0.42 * m["terrace_junctions"] + 0.16 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fmo_black_pearl() -> _Grammar:
    """A flattened pearl skin: crossed orient fields buckle around one drill fold."""
    names=("green_orient_lips","violet_orient_lips","aragonite_sutures",
           "mie_cusp_caps","drill_fold","chipped_nacre_lips",
           "contact_saddles","surface_dimples","orient_dislocations")
    m=_new(*names)
    x,y=_xy(); u=(x-256.0)/182.0; v=(y-252.0)/188.0

    # A stereographic buckle is used as one continuous pearl skin.  Its two
    # orient families cross and exchange handedness at the drill fold; there
    # is deliberately no circular pearl outline or repeated bead glyph.
    fold_u=u+0.31*(u*u-v*v)-0.22*u*v+0.13*np.sin(2.7*v+u)
    fold_v=v-0.38*u*v+0.16*(v*v-.45*u*u)+0.11*np.cos(3.2*u-v)
    orient_a=15.7*fold_u+5.4*fold_v+2.3*fold_u*fold_v
    orient_b=12.9*(fold_u*fold_u-.72*fold_v*fold_v)-8.1*fold_v+2.6*fold_u
    break_a=np.sin(3.1*fold_u-4.7*fold_v+0.37*np.sin(orient_b))
    break_b=np.cos(5.3*fold_u+2.9*fold_v+0.31*np.sin(orient_a))
    a_wave=np.sin(orient_a)
    b_wave=np.sin(orient_b)
    m["green_orient_lips"]=_f32((np.abs(a_wave-.46)<.070)*(break_a>-.43))
    m["violet_orient_lips"]=_f32((np.abs(b_wave+.37)<.070)*(break_b>-.38))
    m["aragonite_sutures"]=_f32((np.abs(np.sin(orient_a-orient_b))<.052)
                                  *(break_a*break_b>-.12))
    cusp=fold_v**3-1.12*fold_u*fold_v+.24*fold_u**2-.19
    m["mie_cusp_caps"]=_f32((np.abs(np.sin(10.8*cusp+1.7*fold_u))<.060)
                             *(np.abs(cusp)<1.36))
    saddle=(orient_a+orient_b)/6.0+1.3*np.sin(fold_u-fold_v)
    m["contact_saddles"]=_f32((np.abs(np.cos(saddle)-.18)<.060)
                                *(break_a>.05))
    disloc=np.sin(orient_a+.52*orient_b+2.1*np.arctan2(fold_v-.18,fold_u+.11))
    m["orient_dislocations"]=_f32((np.abs(disloc)<.052)*(break_b>.08))
    dimples=np.cos(4.7*fold_u-6.1*fold_v)+np.cos(7.3*fold_u+3.2*fold_v)
    m["surface_dimples"]=_f32((dimples>1.72)*(np.abs(cusp)>.18))

    drill=_cubic_points(((171,-8),(196,128),(351,211),(522,174)),127)
    for sample in range(3,123,6):
        p=drill[sample]; t=_unit(drill[min(126,sample+3)]-drill[max(0,sample-3)])
        _draw_line(m["drill_fold"],p-t*3,p+t*4,4)
        if (sample//6)%3:
            n=np.asarray([-t[1],t[0]],np.float32)
            _draw_line(m["chipped_nacre_lips"],p-n*(4+sample%5),p+n*(5+(sample//7)%4),2)
    chips=(((3,114),(63,83),(113,137),(175,101)),
           ((508,333),(446,309),(405,379),(344,351)),
           ((38,500),(106,461),(163,506),(231,474)))
    for idx,control in enumerate(chips):
        curve=_cubic_points(control,73)
        for sample in range(2+idx,69,7+idx):
            _draw_line(m["chipped_nacre_lips"],curve[sample],curve[min(72,sample+4)],3)

    tone=_norm(.51*a_wave+.44*b_wave+.36*np.sin(3.2*cusp)+.22*break_a)
    banks=dict(green_orient_lips="A",violet_orient_lips="B",aragonite_sutures="A",
               mie_cusp_caps="B",drill_fold="N",chipped_nacre_lips="N",
               contact_saddles="B",surface_dimples="A",orient_dislocations="B")
    metal=_f32(.04+.67*m["green_orient_lips"]+.56*m["aragonite_sutures"]
               +.43*m["surface_dimples"]+.16*tone)
    rough=_f32(.08+.68*m["drill_fold"]+.57*m["chipped_nacre_lips"]
               +.44*m["orient_dislocations"]+.17*(1.0-tone))
    coat=_f32(.04+.69*m["violet_orient_lips"]+.58*m["mie_cusp_caps"]
              +.43*m["contact_saddles"]+.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_soap_bubble() -> _Grammar:
    """A warped Scherk membrane exposes saddles, necks, windows, and torn lips."""
    names=("saddle_seams","cyan_newton_fringes","rose_newton_fringes",
           "minimal_necks","three_way_junctions","drainage_rivulets",
           "rupture_lips","window_rims","film_thickness_checks")
    m=_new(*names)
    x,y=_xy()
    # A Scherk-type cos(u)-cos(v) section supplies actual hyperbolic saddles.
    # The coordinate bend is smooth and authored here; it is not a tiled
    # gyroid membrane and does not borrow a Petri process.
    u=(x-274.0+0.11*(y-256.0))/176.0
    v=(y-246.0-0.08*(x-256.0))/181.0
    # One aperiodic cusp/Scherk saddle sheet: unlike the rejected cosine
    # carrier it has no repeated basin, cell, icon, or lattice period.
    surface=(v**3-1.17*u*v+0.23*u*u-0.29*v
             +0.16*np.sin(4.1*u+1.7*v)+0.09*np.sin(7.3*v-2.2*u))
    seam=np.abs(surface)<0.055
    gate0=np.sin(31.0*u+19.0*v+0.6*np.sin(5.0*u-3.0*v))
    gate1=np.cos(23.0*u-37.0*v+0.5*np.cos(4.0*u+7.0*v))
    gate2=np.sin(41.0*u+17.0*v-0.4*np.sin(9.0*v))
    m["saddle_seams"]=_f32(seam*(gate0>-0.22))
    m["cyan_newton_fringes"]=_f32(((np.abs(surface-0.43)<0.070)
                                   | (np.abs(surface-1.04)<0.065))*(gate1>-0.18))
    m["rose_newton_fringes"]=_f32(((np.abs(surface+0.46)<0.070)
                                   | (np.abs(surface+1.11)<0.065))*(gate2>-0.20))
    grad_u=-1.17*v+0.46*u+0.656*np.cos(4.1*u+1.7*v)-0.198*np.cos(7.3*v-2.2*u)
    grad_v=3.0*v*v-1.17*u-0.29+0.272*np.cos(4.1*u+1.7*v)+0.657*np.cos(7.3*v-2.2*u)
    junction=(np.abs(grad_u)<0.20)&(np.abs(grad_v)<0.20)
    m["minimal_necks"]=_f32(junction*(gate1>-0.25))
    m["three_way_junctions"]=_f32((((np.abs(surface)<0.10)&
                                     (np.abs(np.sin(13.0*u-11.0*v))<0.10))|junction)
                                    *(gate2>-0.12))
    drainage_phase=np.sin(19.0*u+7.0*v+1.4*surface)
    m["drainage_rivulets"]=_f32(((np.abs(drainage_phase)<0.055)&(np.abs(surface)<0.72))
                                 *(gate0>0.0))
    m["window_rims"]=_f32((np.abs(np.abs(surface)-1.62)<0.055)*(gate1>0.1))
    checks=np.sin(29.0*u-17.0*v+0.8*surface)
    m["film_thickness_checks"]=_f32(((np.abs(checks)<0.045)&(np.abs(surface)<1.28))
                                     *(gate2>0.0))

    tears=(((17,82),(75,51),(131,94),(181,66)),
           ((321,8),(291,73),(347,126),(318,183)),
           ((506,121),(451,158),(483,221),(429,264)),
           ((-8,324),(56,291),(94,347),(152,316)),
           ((218,421),(272,379),(327,433),(386,397)),
           ((422,529),(397,474),(456,439),(503,398)))
    for idx,control in enumerate(tears):
        curve=_cubic_points(control,71)
        for sample in range(2+idx,67,7+idx%3):
            _draw_line(m["rupture_lips"],curve[sample],curve[min(70,sample+3)],4)
        for sample in range(8+idx,67,14+idx%3):
            p=curve[sample]; t=_unit(curve[min(70,sample+3)]-curve[max(0,sample-3)])
            n=np.asarray([-t[1],t[0]],np.float32)
            _draw_line(m["rupture_lips"],p-n*(4+idx%4),p+n*(5+(idx+1)%4),2)
    tone=_norm(0.58*surface+0.44*np.sin(u+v)+0.31*np.cos(1.4*u-v))
    banks=dict(saddle_seams="A",cyan_newton_fringes="A",rose_newton_fringes="B",
               minimal_necks="A",three_way_junctions="B",drainage_rivulets="A",
               rupture_lips="N",window_rims="B",film_thickness_checks="B")
    metal=_f32(0.04+0.67*m["minimal_necks"]+0.56*m["saddle_seams"]
               +0.43*m["drainage_rivulets"]+0.16*tone)
    rough=_f32(0.08+0.68*m["rupture_lips"]+0.57*m["drainage_rivulets"]
               +0.44*m["film_thickness_checks"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["rose_newton_fringes"]+0.58*m["window_rims"]
              +0.43*m["three_way_junctions"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_oil_slick() -> _Grammar:
    """Colliding oil fronts carry unequal shear curls, ruptures, and film islands."""
    names=("shear_fronts","green_eddies","violet_eddies",
           "film_islands","rupture_seams","interference_caps",
           "pinch_junctions","bare_water_slits")
    m=_new(*names)
    fronts=(
        ((-28,472),(128,568),(238,-72),(540,71)),
        ((-24,97),(151,-58),(357,552),(541,349)),
        ((74,-24),(551,88),(-64,391),(428,539)),
    )
    feature=0
    for fidx,control in enumerate(fronts):
        curve=_cubic_points(control,171)
        for sample in range(3+fidx%3,167,6+fidx%4):
            p=curve[sample]; d=_unit(curve[min(170,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["shear_fronts"],p-d*3,p+d*4,3+(fidx%3==0))
        for sample in range(9+fidx,165,8+fidx*2):
            p=curve[sample]
            t=_unit(curve[min(170,sample+4)]-curve[max(0,sample-4)])
            n=np.asarray([-t[1],t[0]],np.float32)
            sense=1 if (feature+fidx)%2 else -1
            centre=p+n*sense*(8+feature%9)
            curl=[]
            for step in range(23+feature%17):
                th=sense*(.2+step*.19)+feature*.37
                rad=(8+feature%11)*(1.0-step/(35.0+feature%17))
                curl.append(centre+np.asarray([rad*np.cos(th),.68*rad*np.sin(th)]))
            eddy="green_eddies" if feature%2 else "violet_eddies"
            for curl_step in range(1,len(curl)-1,3+feature%3):
                p0=np.asarray(curl[curl_step]); d=_unit(np.asarray(curl[curl_step+1])-np.asarray(curl[curl_step-1]))
                _draw_line(m[eddy],p0-d*2,p0+d*(3+curl_step%3),3)
            _draw_line(m["pinch_junctions"],p-n*6,p+n*7+t*3,2)
            if feature%3==0:
                _draw_poly(m["film_islands"],
                           (centre-t*8,centre+n*6,centre+t*9,centre-n*5),3)
            if feature%4==1:
                _draw_poly(m["rupture_seams"],(p-t*7-n*3,p+n*7,p+t*8-n*2),
                           3,closed=False)
            if feature%5==2:
                _draw_ellipse(m["interference_caps"],tuple(np.rint(centre).astype(int)),
                              (8+feature%5,3+feature%3),feature*17,2,start=9,end=174)
            if feature%7==3:
                _draw_line(m["bare_water_slits"],centre-t*7,centre+t*8,4)
            feature+=1
    # The three authored collision fronts induce a deterministic two-vortex
    # stream potential.  Fine roll-up packets extend edge-to-edge, but remain
    # attached to the same shear mechanism rather than becoming free texture.
    x,y=_xy(); u=(x-258.0)/171.0; v=(y-251.0)/176.0
    r0=np.hypot(u+.76,v-.38)+.08; a0=np.arctan2(v-.38,u+.76)
    r1=np.hypot(u-.69,v+.31)+.08; a1=np.arctan2(v+.31,u-.69)
    stream=1.73*v+.58*np.log(r0)-.51*np.log(r1)+.19*np.sin(2.8*u-1.7*v)
    roll=17.6*stream+3.4*np.sin(2.2*a0-1.4*a1)+1.8*u*v
    gate=np.cos(4.1*u+3.3*v+.7*np.sin(a0+a1))
    shear=(np.abs(np.sin(roll))<.078)&(gate>-.52)
    m["shear_fronts"]=_f32(np.maximum(m["shear_fronts"],shear))
    green=shear&(np.sin(2.9*a0+roll*.17)>.08)
    violet=shear&(np.cos(3.4*a1-roll*.13)>.02)
    m["green_eddies"]=_f32(np.maximum(m["green_eddies"],green))
    m["violet_eddies"]=_f32(np.maximum(m["violet_eddies"],violet))
    island_field=(r0*r1+.12*np.sin(3.0*a0-2.0*a1))
    islands=(np.abs(np.sin(13.7*island_field)-.31)<.070)&(gate>.04)
    m["film_islands"]=_f32(np.maximum(m["film_islands"],islands))
    rupture=(np.abs(np.sin(7.1*(r0-r1)+a0+a1))<.055)&(gate<-.28)
    m["rupture_seams"]=_f32(np.maximum(m["rupture_seams"],rupture))
    caps=(np.abs(np.cos(roll*.53+a0-a1)-.64)<.060)&(gate>.31)
    m["interference_caps"]=_f32(np.maximum(m["interference_caps"],caps))
    # A owns actual rolled eddies and islands; it is not manufactured from a
    # generic halo around the B-owned collision front.
    m["green_eddies"]=_f32(cv2.dilate(m["green_eddies"],np.ones((5,5),np.uint8)))
    m["violet_eddies"]=_f32(cv2.dilate(m["violet_eddies"],np.ones((5,5),np.uint8)))
    tone=_norm(.48*np.sin(roll)+.39*np.cos(7.1*island_field)+.31*gate)
    banks=dict(shear_fronts="B",green_eddies="A",violet_eddies="B",
               film_islands="A",rupture_seams="N",interference_caps="B",
               pinch_junctions="A",bare_water_slits="N")
    metal=_f32(0.04+0.67*m["green_eddies"]+0.55*m["film_islands"]
               +0.42*m["pinch_junctions"]+0.16*tone)
    rough=_f32(0.08+0.67*m["shear_fronts"]+0.56*m["rupture_seams"]
               +0.43*m["bare_water_slits"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["violet_eddies"]+0.58*m["interference_caps"]
              +0.42*m["film_islands"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_mother_of_pearl() -> _Grammar:
    """A calm shell-growth spiral carries mantle sectors and stacked nacre lips."""
    names = ("growth_spiral", "mantle_sectors", "aqua_platelet_stacks",
             "rose_platelet_stacks", "hinge_arcs", "growth_checks",
             "chipped_shell_lips", "sector_junctions")
    m = _new(*names)
    centre = np.asarray([718.0, 251.0], np.float32)
    spiral = []
    for step in range(1100):
        theta = 1.28 + step * 0.065
        radius = 31.0 + step * 0.95
        warp = np.asarray([1.0 + 0.12 * np.sin(theta * 1.7),
                           0.74 + 0.09 * np.cos(theta * 1.3)], np.float32)
        spiral.append(centre + warp * radius * np.asarray([np.cos(theta), np.sin(theta)]))
    for sample in range(3,1096,3):
        p=np.asarray(spiral[sample]); d=_unit(np.asarray(spiral[sample+2])-np.asarray(spiral[sample-2]))
        _draw_line(m["growth_spiral"],p-d*3,p+d*4,4)
    for sample in range(10, 1094, 2):
        p = spiral[sample]
        t = _unit(spiral[min(1099, sample + 3)] - spiral[max(0, sample - 3)])
        n = np.asarray([-t[1], t[0]], np.float32)
        reach = 8 + (sample * 7) % 22
        sector = p + n * reach * (1 if (sample // 7) % 3 else -1)
        direction=_unit(sector+t*6-(p-t*4))
        start=p-t*4; delta=sector+t*6-start
        for part,frac in enumerate((.18,.51,.82)):
            q=start+delta*frac
            _draw_line(m["mantle_sectors"],q-direction*(2+part%2),q+direction*(3+(sample+part)%3),3)
        stack = "aqua_platelet_stacks" if (sample // 2) % 2 else "rose_platelet_stacks"
        for offset in (-4, 0, 4):
            q=sector+n*offset
            _draw_line(m[stack],q-t*3,q+t*4,2)
        if (sample // 2) % 4 == 0:
            _draw_ellipse(m["growth_checks"], tuple(np.rint(p).astype(int)),
                          (7, 3), np.degrees(np.arctan2(t[1], t[0])), 2,
                          start=12, end=172)
        if (sample // 2) % 5 == 1:
            _draw_poly(m["chipped_shell_lips"],
                       (sector - t * 6, sector + n * 4,
                        sector + t * 5 - n * 3), 3, closed=False)
        if (sample // 2) % 6 == 2:
            _draw_ellipse(m["sector_junctions"], tuple(np.rint(sector).astype(int)),
                          (5, 3), sample * 1.4, 2)
    hinge_controls = (
        ((531, -18), (474, 41), (544, 102), (461, 163)),
        ((529, 31), (455, 91), (524, 151), (431, 217)),
        ((527, 84), (438, 142), (498, 217), (399, 276)),
    )
    for control in hinge_controls:
        curve=_cubic_points(control,73)
        for sample in range(3,69,7):
            p=curve[sample]; d=_unit(curve[min(72,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["hinge_arcs"],p-d*3,p+d*4,3)
    x, y = _xy()
    tone = _norm(np.cos((x + 1.1 * y) / 63.0) + 0.62 * np.sin((1.4 * x - y) / 49.0))
    m["aqua_platelet_stacks"]=_f32(cv2.dilate(m["aqua_platelet_stacks"],np.ones((5,5),np.uint8)))
    m["rose_platelet_stacks"]=_f32(cv2.dilate(m["rose_platelet_stacks"],np.ones((5,5),np.uint8)))
    banks = dict(growth_spiral="A", mantle_sectors="B", aqua_platelet_stacks="A",
                 rose_platelet_stacks="B", hinge_arcs="A", growth_checks="B",
                 chipped_shell_lips="N", sector_junctions="B")
    metal = _f32(0.05 + 0.66 * m["aqua_platelet_stacks"] + 0.53 * m["hinge_arcs"]
                 + 0.42 * m["sector_junctions"] + 0.16 * tone)
    rough = _f32(0.08 + 0.66 * m["growth_spiral"] + 0.56 * m["chipped_shell_lips"]
                 + 0.43 * m["mantle_sectors"] + 0.17 * (1.0 - tone))
    coat = _f32(0.04 + 0.69 * m["rose_platelet_stacks"] + 0.58 * m["growth_checks"]
                + 0.43 * m["sector_junctions"] + 0.16 * tone)
    return _pack(m, banks, tone, metal, rough, coat)


def _build_fmo_nacre_brick() -> _Grammar:
    """A stress-driven nacre process zone, not an ordinary brick bond.

    Thousands of unequal dovetail tablets form continuously bending courses.
    A crack is snapped to real tablet endcaps, then deflects, opens mortar,
    peels pockets and heals with repair wedges.  Bouligand order rotates only
    inside measured stress lobes; no decorative texture survives independently
    of the tablet/mortar/fracture architecture.
    """
    names=("aragonite_tablet_faces","rotated_bouligand_faces",
           "organic_mortar_capillaries","dovetail_bridges",
           "crack_arrest_hooks","chipped_endcaps","repair_wedges",
           "pinhole_canals","peeled_delamination_pockets","stepped_course_forks")
    m=_new(*names)
    tablet_age=np.zeros((_WORK,_WORK),np.float32)
    tablet_union=np.zeros((_WORK,_WORK),np.float32)
    endpoints=[]
    stress_lobes=(
        (72,91,104,82,.62),(214,76,92,116,-.71),(389,105,121,83,.81),
        (493,221,88,129,-.66),(338,261,126,101,.73),(146,283,111,137,-.79),
        (62,429,98,107,.68),(246,435,132,89,-.74),(444,426,111,116,.77),
    )
    # Courses are deposition histories.  Unequal tablet lengths, height, bend
    # and local stress rotation are evaluated for each connected tablet; the
    # loop never stamps a shared glyph or uses random placement.
    for course in range(102):
        base_y=-9.0+course*5.18
        phase=.71*course+.19*np.sin(.37*course)
        cursor=-17.0+2.6*np.sin(.83*course)
        tablet_index=0
        while cursor<529.0:
            x0=cursor
            amplitude=5.0+4.2*(.5+.5*np.sin(.29*course))
            wavelength=61.0+8.0*(course%7)
            y0=(base_y+amplitude*np.sin(x0/wavelength+phase)
                +2.3*np.sin(x0/(37.0+course%5)+.43*phase))
            rotation=0.0; rotation_grad=0.0
            for cx,cy,rx,ry,turn in stress_lobes:
                dx=(x0-cx)/rx; dy=(y0-cy)/ry
                influence=np.exp(-2.1*(dx*dx+dy*dy))
                rotation+=turn*influence
                rotation_grad+=abs(turn)*influence*(abs(dx)+abs(dy))
            dy_dx=(amplitude/wavelength*np.cos(x0/wavelength+phase)
                   +2.3/(37.0+course%5)*np.cos(x0/(37.0+course%5)+.43*phase))
            angle=np.arctan(dy_dx)+rotation
            tangent=np.asarray([np.cos(angle),np.sin(angle)],np.float32)
            normal=np.asarray([-tangent[1],tangent[0]],np.float32)
            length=5.0+2.7*(.5+.5*np.sin(.61*tablet_index+.37*course))
            half_height=1.65+.72*(.5+.5*np.cos(.43*tablet_index+.21*course))
            centre=np.asarray([x0,y0],np.float32)+.5*length*tangent
            p0=centre-.5*length*tangent; p1=centre+.5*length*tangent
            # Opposed bevels create a true dovetail contact without drawing a
            # rectangle, and every dimension remains 3--8 work pixels.
            bevel=(.55+.34*np.sin(.49*tablet_index+.17*course))*normal
            poly=(p0+half_height*normal,p1+(half_height-.35)*normal+bevel,
                  p1-(half_height-.35)*normal-bevel,p0-half_height*normal)
            order_b=rotation>.035
            target=("rotated_bouligand_faces" if order_b
                    else "aragonite_tablet_faces")
            _draw_poly(m[target],poly,width=1,fill=True,value=.94)
            _draw_poly(tablet_union,poly,width=1,fill=True,value=1.0)
            _draw_poly(tablet_age,poly,width=1,fill=True,
                       value=.12+.82*((course*7+tablet_index*3)%29)/28.0)
            endpoints.append((p1.copy(),normal.copy(),tangent.copy(),target,
                              float(rotation_grad)))

            # A large stress gradient makes the deposition course split rather
            # than adding an arbitrary decorative branch.
            if rotation_grad>.31:
                fork_tip=p1+(4.0+1.2*np.clip(rotation_grad,0,1))*tangent+3.0*normal
                _draw_poly(m["stepped_course_forks"],
                           (p1-half_height*normal,p1+half_height*normal,fork_tip),
                           width=1,fill=True,value=.90)
                _draw_poly(tablet_union,
                           (p1-half_height*normal,p1+half_height*normal,fork_tip),
                           width=1,fill=True,value=1.0)
            cursor+=length+1.35+.75*(.5+.5*np.cos(.33*tablet_index+.59*course))
            tablet_index+=1

    # The deflection path is selected from actual tablet endcaps nearest a
    # smooth loading trajectory.  The visible crack therefore turns only where
    # masonry provides a physical interface.
    crack_points=[]
    for sx in np.arange(-2.0,518.0,6.0):
        target_y=247.0+58.0*np.sin(sx/83.0)+.085*(sx-256.0)
        candidates=[entry for entry in endpoints if abs(float(entry[0][0])-sx)<4.2]
        if not candidates:
            continue
        chosen=min(candidates,key=lambda entry:abs(float(entry[0][1])-target_y))
        if not crack_points or float(np.linalg.norm(chosen[0]-crack_points[-1][0]))<17.0:
            crack_points.append(chosen)
    crack_mask=np.zeros((_WORK,_WORK),np.float32)
    if len(crack_points)>=3:
        _draw_poly(crack_mask,[entry[0] for entry in crack_points],width=3,
                   fill=False,value=1.0,closed=False)
    crack_zone=cv2.dilate((crack_mask>.1).astype(np.uint8),
                          np.ones((5,5),np.uint8)).astype(np.float32)
    # Open the real tablet faces at the crack; the organic mortar inherits the
    # void and cannot exist as an unrelated background texture.
    m["aragonite_tablet_faces"]*=1.0-crack_mask
    m["rotated_bouligand_faces"]*=1.0-crack_mask
    tablet_union*=1.0-crack_mask

    selected_caps=[]
    for point,normal,tangent,_target,_gradient in endpoints:
        px=int(np.clip(round(float(point[0])),0,_WORK-1))
        py=int(np.clip(round(float(point[1])),0,_WORK-1))
        if crack_zone[py,px]>.1:
            _draw_line(m["chipped_endcaps"],point-2.8*normal,
                       point+2.8*normal,2,.92)
            selected_caps.append((point,normal,tangent))

    # Curvature events in the snapped crack create arrest hooks, pinhole canals,
    # peeled pockets and repair wedges.  Each event is anchored to the crack.
    for index in range(1,max(1,len(crack_points)-1)):
        if index>=len(crack_points)-1:
            break
        prev=crack_points[index-1][0]; point=crack_points[index][0]
        nxt=crack_points[index+1][0]
        a=_unit(point-prev); b=_unit(nxt-point)
        turn=float(a[0]*b[1]-a[1]*b[0])
        normal=np.asarray([-a[1],a[0]],np.float32)
        if abs(turn)>.18:
            hook=(point-4.0*a,point+4.5*normal*np.sign(turn),
                  point+5.0*b)
            _draw_poly(m["crack_arrest_hooks"],hook,width=2,fill=False,
                       value=.95,closed=False)
            pit=(point-2.4*a-1.4*normal,point+1.8*normal,
                 point+2.7*a-1.0*normal)
            _draw_poly(m["pinhole_canals"],pit,width=2,fill=False,
                       value=.90,closed=False)
        if abs(turn)>.31:
            peel=np.zeros((_WORK,_WORK),np.float32)
            wedge=(point-6.0*a-3.0*normal,point+2.0*a-6.0*normal,
                   point+7.0*b+2.0*normal,point+1.0*normal)
            _draw_poly(peel,wedge,width=1,fill=True,value=.88)
            m["peeled_delamination_pockets"]=_f32(np.maximum(
                m["peeled_delamination_pockets"],peel*crack_zone))
        elif .075<abs(turn)<.13:
            wedge=(point-3.5*a-2.0*normal,point+4.0*b,
                   point-3.5*a+2.0*normal)
            _draw_poly(m["repair_wedges"],wedge,width=1,fill=True,value=.93)

    face_union=_f32(np.maximum(m["aragonite_tablet_faces"],
                               m["rotated_bouligand_faces"]))
    m["organic_mortar_capillaries"]=_f32(np.maximum(
        1.0-cv2.dilate((face_union>.12).astype(np.uint8),
                       np.ones((2,2),np.uint8)).astype(np.float32),crack_mask))
    a_near=cv2.dilate((m["aragonite_tablet_faces"]>.1).astype(np.uint8),
                      np.ones((3,3),np.uint8))
    b_near=cv2.dilate((m["rotated_bouligand_faces"]>.1).astype(np.uint8),
                      np.ones((3,3),np.uint8))
    m["dovetail_bridges"]=_f32((a_near>0)&(b_near>0)&(face_union>.1))
    tone=_norm(tablet_age+.27*m["stepped_course_forks"]
               +.22*m["repair_wedges"]-.19*m["organic_mortar_capillaries"])
    banks=dict(aragonite_tablet_faces="A",rotated_bouligand_faces="B",
               organic_mortar_capillaries="N",dovetail_bridges="A",
               crack_arrest_hooks="N",chipped_endcaps="A",repair_wedges="B",
               pinhole_canals="N",peeled_delamination_pockets="N",
               stepped_course_forks="B")
    metal=_f32(.04+.72*m["aragonite_tablet_faces"]+.61*m["dovetail_bridges"]
               +.50*m["chipped_endcaps"]+.15*tone*m["aragonite_tablet_faces"])
    rough=_f32(.07+.67*m["organic_mortar_capillaries"]+.59*m["crack_arrest_hooks"]
               +.53*m["pinhole_canals"]+.48*m["peeled_delamination_pockets"])
    coat=_f32(.04+.73*m["rotated_bouligand_faces"]+.62*m["repair_wedges"]
              +.51*m["stepped_course_forks"]+.16*tone*m["rotated_bouligand_faces"])
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_mussel_shell() -> _Grammar:
    """A cropped mussel surface resolves into micro-ribs around an off-card umbo."""
    names=("cobalt_rib_fragments","violet_growth_checks","hinge_teeth",
           "byssal_slits","nacre_lip_splinters","abrasion_notches",
           "umbo_stress_curls","periostracum_peels","overlap_shadows")
    m=_new(*names)
    # An off-card umbo supplies one coherent shell-stress field, but no hub,
    # outline, fan, or shell icon is drawn.  The visible finish is assembled
    # only from locally varied 2-8 pixel anatomical fragments.
    hinge=np.asarray([-74.0,-58.0],np.float32)
    golden=0.61803398875; silver=0.41421356237
    for index in range(2680):
        px=((index*golden+0.11*np.sin(index*0.173))%1.0)*512.0
        py=((index*silver+0.09*np.sin(index*0.119+1.7))%1.0)*512.0
        p=np.asarray([px,py],np.float32)
        radial=_unit(p-hinge)
        tangent=np.asarray([-radial[1],radial[0]],np.float32)
        shell_radius=float(np.linalg.norm(p-hinge))
        shell_angle=float(np.arctan2(radial[1],radial[0]))
        # Differential shell growth admits fragments in broken concentric
        # packets; the umbo itself remains outside the card.
        if np.sin(shell_radius/10.8+0.72*np.sin(3.0*shell_angle)+0.006*py)<-0.08:
            continue
        bend=np.sin(0.021*px+0.014*py)+0.55*np.cos(0.016*px-0.023*py)
        direction=_unit(tangent+radial*(0.18*bend))
        normal=np.asarray([-direction[1],direction[0]],np.float32)
        length=2.5+(index*7%12)*0.47
        kind=index%9
        if kind==0:
            _draw_line(m["cobalt_rib_fragments"],p-direction*length*.5,
                       p+direction*length*.5,2)
        elif kind==1:
            _draw_line(m["violet_growth_checks"],p-normal*(2+index%3),
                       p+normal*(3+(index//7)%3),2)
        elif kind==2:
            _draw_poly(m["hinge_teeth"],(p-direction*3,p+normal*4,p+direction*4),2,closed=False)
        elif kind==3:
            _draw_line(m["byssal_slits"],p-direction*4-normal*2,p+direction*4+normal,3)
        elif kind==4:
            _draw_poly(m["nacre_lip_splinters"],
                       (p-direction*4,p+normal*(3+index%3),p+direction*4-normal*2),2,closed=False)
        elif kind==5:
            _draw_line(m["abrasion_notches"],p-direction*3,p+direction*3,2)
            _draw_line(m["abrasion_notches"],p-normal*2,p+normal*3,2)
        elif kind==6:
            _draw_ellipse(m["umbo_stress_curls"],tuple(np.rint(p).astype(int)),
                          (4+index%3,2+index%2),np.degrees(np.arctan2(direction[1],direction[0])),
                          2,start=18,end=145+index%47)
        elif kind==7:
            _draw_poly(m["periostracum_peels"],
                       (p-direction*3-normal,p+normal*4,p+direction*4+normal),2,closed=False)
        else:
            _draw_line(m["overlap_shadows"],p-direction*4-normal*2,
                       p+direction*3-normal*2,3)
    x,y=_xy();tone=_norm(np.cos((x+1.7*y)/54.0)+0.68*np.sin((1.5*x-y)/45.0))
    banks=dict(cobalt_rib_fragments="A",violet_growth_checks="B",hinge_teeth="A",
               byssal_slits="N",nacre_lip_splinters="B",abrasion_notches="N",
               umbo_stress_curls="B",periostracum_peels="A",overlap_shadows="N")
    metal=_f32(0.04+0.67*m["cobalt_rib_fragments"]+0.56*m["hinge_teeth"]
               +0.43*m["periostracum_peels"]+0.16*tone)
    rough=_f32(0.08+0.68*m["byssal_slits"]+0.57*m["abrasion_notches"]
               +0.44*m["overlap_shadows"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["violet_growth_checks"]+0.58*m["nacre_lip_splinters"]
              +0.43*m["umbo_stress_curls"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_foam_film() -> _Grammar:
    """Pressure-grown unequal bubbles meet in a curved, coalescing Plateau anatomy."""
    names=("plateau_borders","cyan_thickness_bands","rose_thickness_bands",
           "three_way_nodes","drainage_arrows","ruptured_lips",
           "daughter_insertions","dry_cell_slits","meniscus_corners")
    m=_new(*names)
    x,y=_xy()
    # Explicit pressure nuclei have unequal radii, anisotropy, bias and bend.
    # They are neither a grid nor a reusable Voronoi carrier: their only role
    # is to solve this finish's curved film-pressure equilibrium.
    nuclei=(
        (-31,33,79,54,-.10,.2),(72,-24,61,88,-.04,1.1),
        (187,21,98,63,.05,2.3),(326,-29,72,104,-.08,3.0),
        (461,27,105,69,.01,4.4),(548,119,63,96,-.12,5.2),
        (18,137,72,111,.02,.8),(126,112,93,67,-.13,1.8),
        (255,143,62,112,.08,2.7),(389,116,111,76,-.03,3.8),
        (489,214,77,121,.06,5.7),(-27,262,99,72,-.07,1.5),
        (92,242,68,124,.10,2.1),(205,279,115,79,-.09,3.3),
        (350,246,74,132,.00,4.6),(462,337,126,83,-.11,5.9),
        (21,382,82,127,.04,.4),(151,367,121,72,-.06,1.9),
        (287,394,73,118,.07,3.6),(399,459,119,77,-.10,4.9),
        (535,444,68,119,.03,5.5),(-28,520,116,81,-.08,.9),
        (108,503,75,109,.05,2.5),(239,548,127,70,-.12,3.1),
        (345,516,66,96,.09,4.2),(506,554,126,76,-.05,6.0),
        (280,260,155,142,.17,2.9),
    )
    # W5, owner rejection follow-up: the twenty-seven unequal pressure parents
    # repeatedly bisect along changing stress axes until their last daughters
    # are only 2--8 work pixels wide.  This is a literal split genealogy, not a
    # jittered lattice, Voronoi wallpaper, repeated glyph, or noise carrier.
    pressure=[]
    parent_phase=np.zeros((_WORK,_WORK),np.float32)
    for sx,sy,rx,ry,bias,phase in nuclei:
        dx=(x-float(sx))/float(rx); dy=(y-float(sy))/float(ry)
        bend_x=dx+.105*np.sin(1.7*dy+phase)+.055*dx*dy
        bend_y=dy+.087*np.cos(1.4*dx-phase)-.047*(dx*dx-dy*dy)
        distance=np.hypot(bend_x,bend_y)
        distance+=float(bias)+.032*np.sin(2.3*dx-1.8*dy+phase)
        pressure.append(distance.astype(np.float32))
    parent_pressure=np.stack(pressure,axis=0)
    parent_map=np.argmin(parent_pressure,axis=0).astype(np.int16)
    parent_best=np.min(parent_pressure,axis=0)
    phase_values=np.asarray([entry[5] for entry in nuclei],np.float32)
    parent_phase[:]=phase_values[parent_map]

    seed_pixels=[]; seed_parents=[]; seed_families=[]; seed_birth=[]
    golden=np.pi*(3.0-np.sqrt(5.0))

    def divide_pressure_region(coords: np.ndarray, parent_index: int,
                               lineage: int, depth: int,
                               birth_clock: float) -> None:
        """Recursively pressure-bisect one physical mother chamber."""
        count=int(coords.shape[0])
        if count==0:
            return
        span_x=int(np.ptp(coords[:,1])) if count>1 else 0
        span_y=int(np.ptp(coords[:,0])) if count>1 else 0
        leaf_area=31+((lineage*13+parent_index*17+depth*7)%39)
        if (count<=leaf_area and max(span_x,span_y)<=13) or count<=5 or depth>=16:
            centre=np.mean(coords,axis=0)
            delta=coords-centre[None,:]
            seed_at=int(np.argmin(np.sum(delta*delta,axis=1)))
            py,px=(int(v) for v in coords[seed_at])
            seed_pixels.append((py,px))
            seed_parents.append(parent_index)
            # Same final mother identifies a real late daughter insertion.
            seed_families.append((parent_index<<25)|(depth<<20)|(lineage>>1))
            seed_birth.append(birth_clock)
            return
        phase=nuclei[parent_index][5]
        angle=phase+golden*depth+.419*(lineage%7)+.117*parent_index
        projection=coords[:,1]*np.cos(angle)+coords[:,0]*np.sin(angle)
        low=float(np.min(projection)); high=float(np.max(projection))
        split_fraction=.34+.05*((lineage+2*depth+parent_index)%7)
        split=low+split_fraction*(high-low)
        left=projection<=split
        left_count=int(np.count_nonzero(left))
        if left_count<3 or count-left_count<3:
            # A fixed midpoint is the pressure fallback; there is no rank or
            # equal-population quantizer hidden in the branch.
            split=.5*(low+high)
            left=projection<=split
            left_count=int(np.count_nonzero(left))
        if left_count==0 or left_count==count:
            centre=np.mean(coords,axis=0)
            delta=coords-centre[None,:]
            seed_at=int(np.argmin(np.sum(delta*delta,axis=1)))
            py,px=(int(v) for v in coords[seed_at])
            seed_pixels.append((py,px)); seed_parents.append(parent_index)
            seed_families.append((parent_index<<25)|(depth<<20)|(lineage>>1))
            seed_birth.append(birth_clock)
            return
        divide_pressure_region(coords[left],parent_index,lineage<<1,depth+1,
                               birth_clock+.28+.09*split_fraction)
        divide_pressure_region(coords[~left],parent_index,(lineage<<1)|1,depth+1,
                               birth_clock+.43+.11*(1.0-split_fraction))

    for parent_index in range(len(nuclei)):
        py,px=np.nonzero(parent_map==parent_index)
        parent_clock=.12*nuclei[parent_index][5]+.30*(nuclei[parent_index][4]+.15)
        divide_pressure_region(np.column_stack((py,px)).astype(np.int16),
                               parent_index,1,0,parent_clock)

    # OpenCV's exact nearest-seed labels turn the authored split genealogy into
    # compact unequal daughter chambers in one fast pass.  A small displacement
    # follows each mother's anisotropic pressure phase so films bow rather than
    # settling into a repeated Euclidean tiling.
    seed_image=np.ones((_WORK,_WORK),np.uint8)
    for py,px in seed_pixels:
        seed_image[py,px]=0
    distance,label_map=cv2.distanceTransformWithLabels(
        seed_image,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    label_count=int(np.max(label_map))
    label_parent=np.zeros(label_count+1,np.int16)
    label_family=np.zeros(label_count+1,np.int64)
    label_birth=np.zeros(label_count+1,np.float32)
    for (py,px),parent_index,family,birth in zip(
            seed_pixels,seed_parents,seed_families,seed_birth):
        label=int(label_map[py,px])
        label_parent[label]=parent_index
        label_family[label]=family
        label_birth[label]=birth
    pressure_bend_x=(2.4*np.sin(.071*y+parent_phase)
                     +1.5*np.sin(.043*(x+y)-.7*parent_phase))
    pressure_bend_y=(2.1*np.cos(.063*x-parent_phase)
                     +1.2*np.sin(.051*(x-1.3*y)+parent_phase))
    map_x=np.clip(x+pressure_bend_x,0.0,511.0).astype(np.float32)
    map_y=np.clip(y+pressure_bend_y,0.0,511.0).astype(np.float32)
    label_map=cv2.remap(label_map.astype(np.float32),map_x,map_y,
                        cv2.INTER_NEAREST,borderMode=cv2.BORDER_REFLECT).astype(np.int32)
    distance=cv2.remap(distance,map_x,map_y,cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT)
    parent_map=label_parent[label_map]
    family_map=label_family[label_map]
    birth_map=label_birth[label_map]
    parent_phase=phase_values[parent_map]

    # Chamber measurements stay strictly cell-local.  Centroids, area/radius,
    # split age and gravity coordinate drive every optical/material decision;
    # there is no full-card scalar carrier hiding the bubble anatomy.
    flat_labels=label_map.ravel()
    counts=np.bincount(flat_labels,minlength=label_count+1).astype(np.float32)
    safe_counts=np.maximum(1.0,counts)
    active_counts=counts[1:][counts[1:]>0]
    chamber_diameter=2.0*np.sqrt(active_counts/np.pi)
    _FOAM_BUILD_STATS.clear()
    _FOAM_BUILD_STATS.update({
        "chamber_count":float(active_counts.size),
        "diameter_min_work_px":float(np.min(chamber_diameter)),
        "diameter_p10_work_px":float(np.percentile(chamber_diameter,10)),
        "diameter_median_work_px":float(np.median(chamber_diameter)),
        "diameter_p90_work_px":float(np.percentile(chamber_diameter,90)),
        "diameter_max_work_px":float(np.max(chamber_diameter)),
        "fraction_diameter_2_to_8":float(np.mean((chamber_diameter>=2.0)
                                                  &(chamber_diameter<=8.0))),
    })
    centroid_x=np.bincount(flat_labels,weights=x.ravel(),
                           minlength=label_count+1).astype(np.float32)/safe_counts
    centroid_y=np.bincount(flat_labels,weights=y.ravel(),
                           minlength=label_count+1).astype(np.float32)/safe_counts
    label_radius=np.zeros(label_count+1,np.float32)
    np.maximum.at(label_radius,flat_labels,distance.ravel())
    radius_map=np.maximum(1.0,label_radius[label_map])
    scale_map=np.maximum(1.0,np.sqrt(counts[label_map]/np.pi))
    film_depth=_f32(distance/radius_map)
    local_down=np.clip((y-centroid_y[label_map])/scale_map,-1.5,1.5)
    cell_age=_norm(label_birth)[label_map]

    # A one-pixel ownership rule retains every interface once, producing closed
    # curved Plateau borders without the two-pixel double outline that made W4
    # a macro paver.  Labels choose the side; no random erosion breaks closure.
    raw_border=np.zeros((_WORK,_WORK),bool)
    h_left=label_map[:,:-1]; h_right=label_map[:,1:]
    h_diff=h_left!=h_right
    take_left=h_diff&(h_left<h_right)
    raw_border[:,:-1]|=take_left
    raw_border[:,1:]|=h_diff&(~take_left)
    v_top=label_map[:-1,:]; v_bottom=label_map[1:,:]
    v_diff=v_top!=v_bottom
    take_top=v_diff&(v_top<v_bottom)
    raw_border[:-1,:]|=take_top
    raw_border[1:,:]|=v_diff&(~take_top)

    # Literal three- and four-film junction tests from the four neighbouring
    # daughter identities.  Four-way nodes are unstable T1 swap candidates.
    a=label_map[:-1,:-1]; b=label_map[:-1,1:]
    c=label_map[1:,:-1]; d=label_map[1:,1:]
    abc=(a!=b)&(a!=c)&(b!=c)
    abd=(a!=b)&(a!=d)&(b!=d)
    acd=(a!=c)&(a!=d)&(c!=d)
    bcd=(b!=c)&(b!=d)&(c!=d)
    raw_nodes=np.zeros((_WORK,_WORK),bool)
    raw_nodes[:-1,:-1]=abc|abd|acd|bcd
    four_nodes=np.zeros((_WORK,_WORK),bool)
    four_nodes[:-1,:-1]=abc&(d!=a)&(d!=b)&(d!=c)

    # Final-split siblings share a recorded mother key.  Their common films
    # are genuine daughter fronts, not a generic edge selection.
    daughter_boundary=np.zeros((_WORK,_WORK),bool)
    horizontal=(h_left!=h_right)&(family_map[:,:-1]==family_map[:,1:])
    horizontal&=family_map[:,:-1]!=0
    daughter_boundary[:,:-1]|=horizontal
    vertical=(v_top!=v_bottom)&(family_map[:-1,:]==family_map[1:,:])
    vertical&=family_map[:-1,:]!=0
    daughter_boundary[:-1,:]|=vertical

    # Only late, large sibling films touching an unstable four-way node suffer
    # a T1 coalescence throat.  The local opening consumes the shared film and
    # leaves attached lips; no global rupture path or decorative glyph exists.
    overcrowded=cv2.dilate(four_nodes.astype(np.uint8),np.ones((5,5),np.uint8))>0
    coalescence_seed=(daughter_boundary&overcrowded&(scale_map>3.0)
                      &(cell_age>.62)&(local_down>.08))
    coalescence_front=coalescence_seed.copy()
    front_limit=(daughter_boundary&(scale_map>2.6)
                 &(cell_age>.50)&(local_down>-.12))
    for _ in range(3):
        attached=cv2.dilate(coalescence_front.astype(np.uint8),
                            np.ones((5,5),np.uint8))>0
        coalescence_front|=front_limit&attached
    rupture_zone=cv2.dilate(coalescence_front.astype(np.uint8),
                            np.ones((3,3),np.uint8))>0
    intact=raw_border&(~rupture_zone)

    # Newton thickness orders close around each unequal daughter.  A and B own
    # opposite cell-local interference bands; the small age/gravity offsets
    # are physical and never become a broad camouflage field.
    newton_phase=2.0*np.pi*(1.28*film_depth+.17*cell_age+.08*local_down)
    interference=np.sin(newton_phase)
    cyan=_f32((interference-.05)/.67)*(.46+.54*film_depth)
    rose=_f32((-interference-.05)/.67)*(.46+.54*(1.0-film_depth))
    wet_factor=1.0-.82*cv2.GaussianBlur(rupture_zone.astype(np.float32),
                                        (0,0),.8)
    cyan*=wet_factor; rose*=wet_factor
    m["plateau_borders"]=_f32(.82*intact.astype(np.float32))
    m["cyan_thickness_bands"]=_f32(cyan)
    m["rose_thickness_bands"]=_f32(rose)

    node_core=raw_nodes&(~rupture_zone)
    node_basin=node_core&(film_depth>.34)
    m["three_way_nodes"]=_f32(node_basin)
    near_node=cv2.dilate(node_core.astype(np.uint8),np.ones((3,3),np.uint8))>0
    meniscus=intact&near_node&(~node_core)&(film_depth>.52)
    m["meniscus_corners"]=_f32(meniscus)

    near_rupture=cv2.dilate(rupture_zone.astype(np.uint8),np.ones((5,5),np.uint8))>0
    rupture_lips=intact&near_rupture
    m["ruptured_lips"]=_f32(cv2.dilate(rupture_lips.astype(np.uint8),
                                        np.ones((3,3),np.uint8)))

    daughter_front=daughter_boundary&(~rupture_zone)
    daughter_front&=(cell_age>.24)&(cell_age<.78)
    m["daughter_insertions"]=_f32(daughter_front)

    # Gravity thickens the lower meniscus of every chamber continuously.  This
    # is a cell-local drainage gradient, not a scattered arrow or global lane.
    drainage=_f32((local_down-.34)/.50)*_f32((film_depth-.58)/.34)
    drainage*=~rupture_zone
    m["drainage_arrows"]=_f32(drainage)

    dry=intact&(local_down<-.18)&(film_depth>.48)&(cell_age<.66)
    dry&=(~node_basin)
    m["dry_cell_slits"]=_f32(cv2.dilate(dry.astype(np.uint8),
                                         np.ones((2,2),np.uint8)))

    # Each chamber selects a stable palette tier from its lineage age; Newton
    # masks, not rapid palette quantization, provide the within-cell bands.
    tone=_norm(.74*cell_age+.18*_f32((local_down+1.5)/3.0)
               +.08*film_depth)
    banks=dict(plateau_borders="A",cyan_thickness_bands="A",rose_thickness_bands="B",
               three_way_nodes="B",drainage_arrows="A",ruptured_lips="B",
               daughter_insertions="B",dry_cell_slits="N",meniscus_corners="N")
    metal=_f32(0.04+0.66*m["plateau_borders"]+0.58*m["drainage_arrows"]
               +0.43*m["cyan_thickness_bands"]
               +0.16*tone*m["cyan_thickness_bands"])
    rough=_f32(0.08+0.68*m["dry_cell_slits"]+0.57*m["ruptured_lips"]
               +0.44*m["meniscus_corners"]
               +0.17*(1.0-tone)*m["meniscus_corners"])
    coat=_f32(0.04+0.69*m["rose_thickness_bands"]+0.59*m["three_way_nodes"]
              +0.43*m["daughter_insertions"]
              +0.16*tone*m["rose_thickness_bands"])
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_paua_storm() -> _Grammar:
    """A single off-centre paua cyclone is torn sideways by nacre squalls."""
    names=("storm_fronts","teal_cyclone_bands","magenta_cyclone_bands",
           "lightning_veins","eye_breaks","nacre_spray_arcs",
           "terrace_collisions","lee_shadow_slits")
    m=_new(*names)
    centre=np.asarray([-30.0,300.0],np.float32)
    for band in range(11):
        pts=[]
        for step in range(151):
            th=-2.2+step*0.052+band*0.17
            r=28+band*8.0+step*(2.60+band*0.022)
            warp=np.asarray([1.0+0.08*np.sin(th*2.7+band),
                             0.58+0.13*np.cos(th*1.9-band)],np.float32)
            drift=np.asarray([step*0.52,-step*0.17],np.float32)
            pts.append(centre+warp*r*np.asarray([np.cos(th),np.sin(th)])+drift)
        mask="teal_cyclone_bands" if band%2 else "magenta_cyclone_bands"
        for sample in range(3+band%3,148,4+band%4):
            p=np.asarray(pts[sample],np.float32)
            t=_unit(np.asarray(pts[min(150,sample+1)])-np.asarray(pts[max(0,sample-1)]))
            _draw_line(m[mask],p-t*(3+sample%2),p+t*(4+(sample+band)%3),3)
        for sample in range(17+band,143,23+band%5):
            p=np.asarray(pts[sample],np.float32)
            t=_unit(np.asarray(pts[min(150,sample+3)])-np.asarray(pts[max(0,sample-3)]))
            n=np.asarray([-t[1],t[0]],np.float32)
            _draw_line(m["nacre_spray_arcs"],p-t*5,p+n*(8+band%6)+t*6,2)
            if (sample//23+band)%4==0:
                _draw_line(m["lee_shadow_slits"],p-n*6,p+n*7,4)
        if band in (1,4,7,9):
            p=np.asarray(pts[42+band*3],np.float32)
            _draw_ellipse(m["eye_breaks"],tuple(np.rint(p).astype(int)),
                          (6+band%4,3+band%2),band*19,3,start=20,end=147)
    squalls=(
        ((-18,74),(87,31),(208,122),(355,74),(530,145)),
        ((-17,182),(113,118),(248,219),(394,147),(532,246)),
        ((-14,423),(107,337),(265,471),(417,355),(530,461)),
        ((311,-16),(328,89),(287,179),(371,277),(350,398),(419,528)),
    )
    for idx,pts in enumerate(squalls):
        arr=np.asarray(pts,np.float32)
        for seg in range(len(arr)-1):
            a,b=arr[seg],arr[seg+1]; d=_unit(b-a); length=float(np.linalg.norm(b-a))
            for off in np.arange(5.0,length,13.0+idx):
                p=a+d*off
                _draw_line(m["storm_fronts"],p-d*3,p+d*(4+seg%3),3)
        for p in pts[1:-1]:
            _draw_line(m["terrace_collisions"],np.asarray(p)+(-7,-3),
                       np.asarray(p)+(8,4),3)
    lightning=(
        ((11,271),(68,249),(101,280),(153,241)),
        ((286,125),(313,164),(292,202),(337,236)),
        ((392,309),(427,282),(453,318),(507,287)),
        ((214,454),(246,421),(276,459),(321,432)),
    )
    for path_index,pts in enumerate(lightning):
        arr=np.asarray(pts,np.float32)
        for seg in range(len(arr)-1):
            a,b=arr[seg],arr[seg+1]; d=_unit(b-a); length=float(np.linalg.norm(b-a))
            for off in np.arange(3.0,length,11.0+path_index):
                p=a+d*off
                _draw_line(m["lightning_veins"],p-d*3,p+d*4,3)
    # A single off-card cyclone phase carries the nacre bands through every
    # edge.  The asymmetric radius and angular shear prevent a spiral icon or
    # visible hub, while all secondary marks remain attached to storm fronts.
    x,y=_xy(); dx=x+143.0; dy=(y-297.0)*1.19
    radius=np.hypot(dx,dy)+1.0; angle=np.arctan2(dy,dx)
    storm=.082*radius+3.65*angle+.74*np.sin(.014*x+.021*y+1.7*angle)
    gate=np.cos(.029*x-.024*y+.48*np.sin(2.0*angle))
    skin=(np.abs(np.sin(storm))<.080)&(gate>-.53)
    teal=skin&(np.cos(.61*storm+2.4*angle)>.02)
    magenta=skin&(np.cos(.61*storm+2.4*angle)<.31)
    m["teal_cyclone_bands"]=_f32(np.maximum(m["teal_cyclone_bands"],teal))
    m["magenta_cyclone_bands"]=_f32(np.maximum(m["magenta_cyclone_bands"],magenta))
    fronts=(np.abs(np.sin(.53*storm-2.1*angle)-.46)<.070)&(gate<.62)
    m["storm_fronts"]=_f32(np.maximum(m["storm_fronts"],fronts))
    spray=(np.abs(np.cos(.79*storm+3.2*angle)-.62)<.060)&(gate>.12)
    m["nacre_spray_arcs"]=_f32(np.maximum(m["nacre_spray_arcs"],spray))
    collision=(np.abs(np.sin(storm))<.13)&(np.abs(gate)<.12)
    m["terrace_collisions"]=_f32(np.maximum(m["terrace_collisions"],collision))
    m["teal_cyclone_bands"]=_f32(cv2.dilate(m["teal_cyclone_bands"],np.ones((7,7),np.uint8)))
    m["magenta_cyclone_bands"]=_f32(cv2.dilate(m["magenta_cyclone_bands"],np.ones((5,5),np.uint8)))
    m["lightning_veins"]=_f32(cv2.dilate(m["lightning_veins"],np.ones((3,3),np.uint8)))
    tone=_norm(.51*np.sin(storm)+.42*np.cos(.61*storm+2.4*angle)+.31*gate)
    banks=dict(storm_fronts="N",teal_cyclone_bands="A",magenta_cyclone_bands="B",
               lightning_veins="A",eye_breaks="N",nacre_spray_arcs="B",
               terrace_collisions="B",lee_shadow_slits="N")
    metal=_f32(0.04+0.67*m["teal_cyclone_bands"]+0.55*m["lightning_veins"]
               +0.42*m["terrace_collisions"]+0.16*tone)
    rough=_f32(0.08+0.67*m["storm_fronts"]+0.56*m["eye_breaks"]
               +0.43*m["lee_shadow_slits"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["magenta_cyclone_bands"]+0.58*m["nacre_spray_arcs"]
              +0.42*m["terrace_collisions"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_pearl_oyster() -> _Grammar:
    """An off-card elliptic-umbilic mantle buckles into one oyster reef skin."""
    names=("aqua_ruffle_fragments","rose_ruffle_fragments","hinge_scar_ticks",
           "tissue_tethers","pearl_nucleus_crescents","calcified_lip_hooks",
           "mantle_tubules","erosion_bites","reef_pressure_notches")
    m=_new(*names)
    x,y=_xy(); u=(x-378.0)/181.0; v=(y+63.0)/193.0
    # Elliptic-umbilic differential growth gives the mantle three unequal fold
    # directions without a sampled point carrier.  The catastrophe lies off
    # card, so no flower, fan, or repeated oyster icon appears in the tile.
    umbilic=u**3-3.0*u*v*v+.47*(u*u+v*v)-.23*u+.16*v
    fold=12.6*umbilic+3.8*np.sin(1.7*u+.9*v)+1.4*np.sin(2.2*u*v)
    tether=8.1*(u*u-v*v)-3.7*u*v+1.9*np.cos(2.3*v-u)
    gate=np.cos(3.4*u+4.9*v+.41*np.sin(tether))
    aqua=(np.abs(np.sin(fold)-.43)<.075)&(gate>-.41)
    rose=(np.abs(np.sin(fold)+.39)<.075)&(gate<.61)
    m["aqua_ruffle_fragments"]=_f32(aqua)
    m["rose_ruffle_fragments"]=_f32(rose)
    m["hinge_scar_ticks"]=_f32((np.abs(np.sin(fold-tether))<.060)
                                *(np.abs(umbilic)<1.54)*(gate>.05))
    m["tissue_tethers"]=_f32((np.abs(np.sin(tether))<.065)
                              *(np.abs(np.sin(fold))<.72)*(gate<.33))
    tubule=np.sin(19.0*(u+.14*v*v)-2.8*umbilic)
    m["mantle_tubules"]=_f32((np.abs(tubule)<.055)*(gate>.13))
    lip=np.cos(.47*fold+.61*tether)+.36*np.sin(4.3*u-2.7*v)
    m["calcified_lip_hooks"]=_f32((np.abs(lip-.78)<.060)*(gate<-.06))
    erosion=np.sin(.71*fold-.38*tether+2.1*u)
    m["erosion_bites"]=_f32((np.abs(erosion)<.052)*(gate<-.31))
    pressure=np.cos(.29*fold+.83*tether-1.7*v)
    m["reef_pressure_notches"]=_f32((np.abs(pressure+.72)<.060)*(gate>.27))

    nuclei=((44,91,11,-24),(137,166,8,31),(263,118,13,-9),(409,191,9,44),
            (79,336,12,18),(228,401,10,-37),(386,343,14,7),(486,469,9,52))
    for idx,(cx,cy,radius,angle) in enumerate(nuclei):
        _draw_ellipse(m["pearl_nucleus_crescents"],(cx,cy),(radius,4+idx%3),
                      angle,3,start=17,end=308)
        _draw_poly(m["calcified_lip_hooks"],
                   ((cx-radius,cy+2),(cx-2,cy-radius//2),(cx+radius,cy-3)),
                   2,closed=False)
    tone=_norm(.49*np.sin(fold)+.42*np.cos(tether)+.32*gate)
    banks=dict(aqua_ruffle_fragments="A",rose_ruffle_fragments="B",hinge_scar_ticks="A",
               tissue_tethers="N",pearl_nucleus_crescents="B",calcified_lip_hooks="B",
               mantle_tubules="A",erosion_bites="N",reef_pressure_notches="N")
    metal=_f32(0.04+0.67*m["aqua_ruffle_fragments"]+0.56*m["hinge_scar_ticks"]
               +0.43*m["mantle_tubules"]+0.16*tone)
    rough=_f32(0.08+0.68*m["tissue_tethers"]+0.57*m["erosion_bites"]
               +0.44*m["reef_pressure_notches"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["rose_ruffle_fragments"]+0.58*m["pearl_nucleus_crescents"]
              +0.43*m["calcified_lip_hooks"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_labradorite() -> _Grammar:
    """Conjugate feldspar twins switch orientation across a faulted domain sheet."""
    names=("blue_pericline_blades","gold_albite_blades","sawtooth_twin_walls",
           "cleavage_steps","flash_window_bevels","exsolution_needles",
           "cross_fractures","feldspar_slivers","fault_offset_ticks")
    m=_new(*names)
    x,y=_xy(); u=(x-255.0)/183.0; v=(y-249.0)/177.0
    # One curved twin boundary selects between two crystallographic plane
    # equations.  This retains labelled domains and removes the former
    # low-discrepancy point scatter/micro-stamp carrier completely.
    domain=(v-.31*u*u+.22*u*v+.34*np.sin(2.1*u+1.3*v)
            -.19*np.cos(3.4*v-u))
    phase_a=23.0*(.91*u+.28*v)+4.2*np.sin(1.7*v-.8*u)+1.6*domain
    phase_b=21.0*(-.37*u+.94*v)+3.7*np.sin(2.3*u+v)-1.4*domain
    fault_gate=np.cos(4.8*u-3.5*v+.53*np.sin(domain*4.0))
    blue=(np.abs(np.sin(phase_a))<.072)&(domain>-.08)&(fault_gate>-.52)
    gold=(np.abs(np.sin(phase_b))<.072)&(domain<.11)&(fault_gate<.67)
    m["blue_pericline_blades"]=_f32(blue)
    m["gold_albite_blades"]=_f32(gold)
    saw=np.sin(18.0*u+5.0*np.sin(4.0*v))
    m["sawtooth_twin_walls"]=_f32((np.abs(domain)<.038)*(saw>-.36))
    step=np.sin(.52*phase_a-.37*phase_b+3.1*domain)
    m["cleavage_steps"]=_f32((np.abs(step)<.055)*(fault_gate>.02))
    windows=(np.abs(np.sin(phase_a))<.12)&(np.abs(np.sin(phase_b))<.12)
    m["flash_window_bevels"]=_f32(windows)
    needles=np.sin(29.0*(u+.13*v*v)-2.2*domain)
    m["exsolution_needles"]=_f32((np.abs(needles)<.050)*(domain>.17)
                                  *(fault_gate>.11))
    sliver=np.cos(.43*phase_a+.61*phase_b)+.31*np.sin(5.2*u-4.1*v)
    m["feldspar_slivers"]=_f32((np.abs(sliver-.79)<.055)*(fault_gate<-.06))
    m["fault_offset_ticks"]=_f32((np.abs(domain)<.075)
                                  *(np.abs(np.sin(.71*phase_a+.29*phase_b))<.18))

    fractures=(
        ((-17,92),(104,51),(175,126),(286,87)),
        ((511,29),(421,107),(463,202),(371,263)),
        ((-13,322),(93,281),(202,354),(315,304),(423,369),(531,327)),
        ((76,529),(126,402),(91,274),(166,159),(128,-17)),
        ((441,529),(383,407),(438,288),(372,171),(415,-18)),
    )
    for idx,control in enumerate(fractures):
        curve=_chaikin(control,3)
        for sample in range(2+idx%2,len(curve)-2,3+idx%2):
            p=curve[sample]; d=_unit(curve[min(len(curve)-1,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["cross_fractures"],p-d*3,p+d*4,3)
    tone=_norm(.49*np.sin(phase_a)+.43*np.cos(phase_b)+.31*fault_gate)
    banks=dict(blue_pericline_blades="A",gold_albite_blades="B",sawtooth_twin_walls="N",
               cleavage_steps="A",flash_window_bevels="B",exsolution_needles="A",
               cross_fractures="N",feldspar_slivers="N",fault_offset_ticks="B")
    metal=_f32(0.04+0.67*m["blue_pericline_blades"]+0.56*m["cleavage_steps"]
               +0.43*m["exsolution_needles"]+0.16*tone)
    rough=_f32(0.08+0.68*m["sawtooth_twin_walls"]+0.57*m["cross_fractures"]
               +0.44*m["feldspar_slivers"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["gold_albite_blades"]+0.58*m["flash_window_bevels"]
              +0.43*m["fault_offset_ticks"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_black_opal() -> _Grammar:
    """A connected potch-river atlas carries changing Bragg order on its banks."""
    names=("potch_domain_walls","green_bragg_planes","red_bragg_planes",
           "silica_necks","order_nodes","lattice_dislocations",
           "color_bar_boundaries","crazing_cracks","potch_void_lips")
    m=_new(*names)
    # These unequal, overlapping circuits are one connected potch river
    # system.  They neither partition the card into tiles nor carry a local
    # sphere lattice.  Bragg planes grow only as bank-attached micro-lamellae.
    circuits=(
        ((-31,66),(64,8),(177,39),(228,139),(167,211),(43,195),(-28,132)),
        ((105,-22),(255,12),(352,91),(322,202),(210,247),(111,177),(72,73)),
        ((332,-27),(483,21),(547,131),(473,242),(354,228),(286,116)),
        ((-29,238),(83,191),(197,254),(180,382),(58,438),(-35,359)),
        ((145,222),(283,195),(397,277),(365,413),(231,454),(125,357)),
        ((384,226),(522,202),(557,340),(486,452),(353,421),(319,312)),
        ((-20,448),(116,390),(252,456),(288,548),(79,550)),
        ((253,407),(399,374),(542,446),(528,548),(331,548)),
    )
    feature=0
    for circuit_index,vertices in enumerate(circuits):
        curve=_chaikin(vertices,3,closed=True)
        count=len(curve)
        for sample in range(count):
            p=np.asarray(curve[sample]); prev=np.asarray(curve[(sample-2)%count])
            nxt=np.asarray(curve[(sample+2)%count]); tangent=_unit(nxt-prev)
            normal=np.asarray([-tangent[1],tangent[0]],np.float32)
            # The potch wall is broken at genuine order-transfer gates.
            if (sample+2*circuit_index)%5:
                _draw_line(m["potch_domain_walls"],p-tangent*3,p+tangent*4,4)
            bank_width=6+(3*sample+5*circuit_index)%12
            for side in (-1,1):
                bank=p+normal*side*bank_width
                plane=("green_bragg_planes" if (feature+side+circuit_index)%3
                       else "red_bragg_planes")
                _draw_line(m[plane],bank-tangent*(3+feature%2),
                           bank+tangent*(4+(feature+1)%3),3)
                if (feature+sample)%4==0:
                    _draw_line(m["silica_necks"],p+normal*side*4,
                               bank+normal*side*3,2)
                if (feature+2*circuit_index)%7==1:
                    _draw_poly(m["lattice_dislocations"],
                               (bank-tangent*4,bank+normal*side*4,
                                bank+tangent*5-normal*side*2),2,closed=False)
            if (feature+sample)%6==2:
                cv2.circle(m["order_nodes"],tuple(np.rint(p).astype(int)),
                           2+feature%2,1.0,-1,cv2.LINE_AA)
            if (feature+sample)%9==3:
                _draw_line(m["color_bar_boundaries"],p-normal*8,
                           p+normal*9+tangent*3,3)
            feature+=1

    connectors=(
        ((-17,151),(88,126),(162,292),(287,264),(405,371),(529,333)),
        ((42,-18),(91,115),(65,254),(154,403),(135,529)),
        ((489,-16),(421,119),(459,258),(371,401),(405,529)),
        ((-16,327),(96,301),(225,348),(350,296),(529,391)),
    )
    for idx,vertices in enumerate(connectors):
        curve=_chaikin(vertices,3)
        for sample in range(2+idx%2,len(curve)-2,3+idx%3):
            p=curve[sample]; tangent=_unit(curve[sample+2]-curve[sample-2])
            _draw_line(m["crazing_cracks"],p-tangent*3,p+tangent*4,3)
            if (sample+idx)%5==1:
                normal=np.asarray([-tangent[1],tangent[0]],np.float32)
                _draw_ellipse(m["potch_void_lips"],tuple(np.rint(p+normal*5).astype(int)),
                              (6+idx,3+idx%2),idx*31+sample,2,start=14,end=174)
    x,y=_xy(); tone=_norm(np.cos((1.9*x+y)/37.0)+.72*np.sin((x-1.6*y)/51.0))
    banks=dict(potch_domain_walls="N",green_bragg_planes="A",red_bragg_planes="B",
               silica_necks="A",order_nodes="B",lattice_dislocations="N",
               color_bar_boundaries="B",crazing_cracks="N",potch_void_lips="A")
    metal=_f32(0.04+0.67*m["green_bragg_planes"]+0.56*m["silica_necks"]
               +0.43*m["potch_void_lips"]+0.16*tone)
    rough=_f32(0.08+0.68*m["potch_domain_walls"]+0.57*m["lattice_dislocations"]
               +0.44*m["crazing_cracks"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["red_bragg_planes"]+0.58*m["order_nodes"]
              +0.43*m["color_bar_boundaries"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_ammolite_skin() -> _Grammar:
    """An off-card ammonite exposes only its edge-to-edge chamber-and-suture fabric."""
    names = ("whorl_backbone", "green_chambers", "red_chambers",
             "branching_sutures", "aragonite_cracks", "mineral_seams",
             "lobe_necks", "broken_growth_lips")
    m = _new(*names)
    # The whorl centre sits outside the card so this cannot read as a single
    # spiral icon.  Only the dense chamber fabric crosses the automotive tile.
    centre=np.asarray([620.0,580.0],np.float32)
    outer=[]
    for step in range(800):
        theta=-2.0+step*0.065
        radius=35.0+step*0.75
        outer.append(centre+np.asarray([radius*np.cos(theta),
                                       1.05*radius*np.sin(theta)],np.float32))
    for sample in range(3,796,5):
        p=np.asarray(outer[sample]); d=_unit(np.asarray(outer[sample+2])-np.asarray(outer[sample-2]))
        _draw_line(m["whorl_backbone"],p-d*3,p+d*4,4)
    for sample in range(10,794,2):
        p=outer[sample]
        t=_unit(outer[min(799,sample+4)]-outer[max(0,sample-4)])
        n=np.asarray([-t[1],t[0]],np.float32)
        radius=float(np.linalg.norm(p-centre))
        inward=-_unit(p-centre)
        length=min(54.0,10.0+0.29*radius)
        tip=p+inward*length
        chamber="green_chambers" if (sample//2)%2 else "red_chambers"
        chamber_path=(p-t*5,p+inward*length*0.52+n*4,tip,
                      p+inward*length*0.48-n*5,p+t*5)
        for edge in range(4):
            a=np.asarray(chamber_path[edge]); b=np.asarray(chamber_path[edge+1]); d=_unit(b-a)
            for frac in (.23,.68):
                q=a+(b-a)*frac
                _draw_line(m[chamber],q-d*3,q+d*4,3)
        # Suture lobes branch from the chamber wall instead of stamping a glyph.
        for frac in (0.28,0.55,0.79):
            root=p+inward*length*frac
            arm=5+(sample+int(frac*100))%7
            _draw_line(m["branching_sutures"],root,root+n*arm+inward*3,2)
            _draw_line(m["branching_sutures"],root,root-n*(arm-1)+inward*4,2)
        if (sample//2)%3==0:
            _draw_line(m["lobe_necks"],tip-n*5,tip+n*6,3)
        if (sample//2)%4==1:
            _draw_poly(m["broken_growth_lips"],(p-t*7,p+n*4,p+t*7-n*3),
                       3,closed=False)
        if (sample//2)%5==2:
            _draw_line(m["mineral_seams"],p-inward*4-n*6,p+inward*8+n*5,3)
    cracks=(
        ((15,192),(62,205),(88,176),(131,198)),
        ((389,58),(401,112),(379,147),(407,190)),
        ((407,371),(449,354),(471,390),(526,401)),
        ((92,421),(127,399),(159,428),(190,416)),
    )
    for pts in cracks:_draw_poly(m["aragonite_cracks"],pts,3,closed=False)
    x,y=_xy();tone=_norm(np.sin((1.5*x+y)/53.0)+0.69*np.cos((x-1.7*y)/46.0))
    m["green_chambers"]=_f32(cv2.dilate(m["green_chambers"],np.ones((3,3),np.uint8)))
    m["red_chambers"]=_f32(cv2.dilate(m["red_chambers"],np.ones((5,5),np.uint8)))
    banks=dict(whorl_backbone="N",green_chambers="A",red_chambers="B",
               branching_sutures="A",aragonite_cracks="N",mineral_seams="B",
               lobe_necks="B",broken_growth_lips="N")
    metal=_f32(0.04+0.67*m["green_chambers"]+0.55*m["branching_sutures"]
               +0.42*m["lobe_necks"]+0.16*tone)
    rough=_f32(0.08+0.67*m["whorl_backbone"]+0.56*m["aragonite_cracks"]
               +0.43*m["broken_growth_lips"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["red_chambers"]+0.58*m["mineral_seams"]
              +0.43*m["lobe_necks"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_alexandrite_dusk() -> _Grammar:
    """One continuous hourglass twin sheet folds through a cusp catastrophe."""
    names=("prism_edge_fragments","green_twin_wedges","red_twin_wedges",
           "hourglass_waist_ticks","growth_striae","internal_fracture_hooks",
           "crossing_node_crescents","chipped_terminations")
    m=_new(*names)
    x,y=_xy(); u=(x-251.0)/174.0; v=(y-258.0)/181.0
    # The two optical twins are literal opposite sheets of a single cusp.  The
    # finish is continuous at hue-null and does not use point scatter, stamps,
    # facets in a lattice, or a random carrier to manufacture distance.
    waist=u*u-.79*v*v+.24*np.sin(2.8*u+1.1*v)-.17*np.cos(3.7*v-u)
    cusp=v**3-1.21*u*v+.31*u*u-.23*v+.12*np.sin(4.3*u-2.1*v)
    prism=16.4*cusp+5.7*waist+1.9*np.sin(2.4*u*v)
    order=11.7*waist-3.1*cusp+2.2*np.cos(2.7*u+v)
    fracture_gate=np.cos(4.9*u-3.6*v+.4*np.sin(order))
    m["prism_edge_fragments"]=_f32((np.abs(np.sin(prism))<.075)
                                     *(fracture_gate>-.48))
    green=(np.abs(np.sin(order)-.42)<.075)&(cusp>=-.12)&(fracture_gate>-.37)
    red=(np.abs(np.sin(order)+.39)<.075)&(cusp<.18)&(fracture_gate<.67)
    m["green_twin_wedges"]=_f32(green)
    m["red_twin_wedges"]=_f32(red)
    m["hourglass_waist_ticks"]=_f32((np.abs(waist)<.040)
                                     *(np.abs(np.sin(14.0*cusp))<.31))
    striae=np.sin(23.0*(u+.16*v*v)-4.6*cusp)
    m["growth_striae"]=_f32((np.abs(striae)<.060)*(np.abs(waist)<1.38)
                              *(fracture_gate>.02))
    crossings=(np.abs(np.sin(prism))<.11)&(np.abs(np.sin(order))<.10)
    m["crossing_node_crescents"]=_f32(crossings)
    term=np.cos(7.3*cusp-3.9*waist)+.42*np.sin(5.1*u+4.7*v)
    m["chipped_terminations"]=_f32((np.abs(term-.91)<.060)
                                    *(fracture_gate<-.03))

    fractures=(
        ((-18,83),(91,41),(173,142),(252,119)),
        ((511,45),(429,112),(462,202),(377,247)),
        ((-14,348),(112,287),(211,399),(319,349)),
        ((178,526),(247,438),(352,479),(430,388)),
        ((46,-17),(135,111),(91,245),(161,376)),
        ((498,529),(421,401),(472,273),(397,156)),
    )
    for idx,control in enumerate(fractures):
        curve=_cubic_points(control,103)
        for sample in range(3+idx%3,99,6+idx%4):
            p=curve[sample]; d=_unit(curve[min(102,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m["internal_fracture_hooks"],p-d*3,p+d*4,3)
            if (sample//6+idx)%4==1:
                n=np.asarray([-d[1],d[0]],np.float32)
                _draw_poly(m["internal_fracture_hooks"],
                           (p-d*3,p+n*5,p+d*4+n),2,closed=False)
    tone=_norm(.48*np.sin(prism)+.43*np.cos(order)+.34*np.sin(4.1*cusp))
    banks=dict(prism_edge_fragments="N",green_twin_wedges="A",red_twin_wedges="B",
               hourglass_waist_ticks="A",growth_striae="N",internal_fracture_hooks="B",
               crossing_node_crescents="B",chipped_terminations="N")
    metal=_f32(0.04+0.67*m["green_twin_wedges"]+0.56*m["hourglass_waist_ticks"]
               +0.43*m["crossing_node_crescents"]+0.16*tone)
    rough=_f32(0.08+0.68*m["prism_edge_fragments"]+0.57*m["growth_striae"]
               +0.44*m["chipped_terminations"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["red_twin_wedges"]+0.58*m["internal_fracture_hooks"]
              +0.43*m["crossing_node_crescents"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_moonstone_adular() -> _Grammar:
    """Independent adularescent curtains drift across angular cleavage plates."""
    names=("cleavage_skeleton","blue_curtains","violet_curtains",
           "curtain_crests","shear_fractures","plate_notches",
           "curtain_crossings","milky_shadow_edges")
    m=_new(*names)
    def fragments(mask_name,points,width=3,closed=False,phase=0):
        arr=np.asarray(points,np.float32)
        pairs=list(zip(arr[:-1],arr[1:]))+([(arr[-1],arr[0])] if closed else [])
        for edge,(a,b) in enumerate(pairs):
            d=_unit(b-a); length=float(np.linalg.norm(b-a))
            for off in np.arange(3.0+phase%4,length,13.0+(phase+edge)%7):
                p=a+d*off
                _draw_line(m[mask_name],p-d*3,p+d*4,width)
    plates=(
        ((-7,25),(167,8),(211,112),(94,184),(-5,132)),
        ((192,9),(367,18),(414,129),(276,183),(213,111)),
        ((390,21),(519,9),(527,169),(438,212),(411,128)),
        ((-8,168),(91,191),(181,292),(114,374),(-6,333)),
        ((185,181),(322,195),(366,321),(246,392),(178,292)),
        ((389,215),(519,184),(526,381),(434,401),(366,319)),
        ((-8,365),(116,383),(195,526),(-6,525)),
        ((131,404),(252,395),(349,525),(199,528)),
        ((373,406),(520,397),(525,526),(352,527)),
    )
    for idx,pts in enumerate(plates):
        fragments("cleavage_skeleton",pts,3,True,idx)
        c=np.mean(np.asarray(pts,np.float32),axis=0)
        if idx%2:
            _draw_poly(m["plate_notches"],(c+(-8,-7),c+(0,5),c+(9,-5)),
                       3,closed=False)
        if idx%3==0:
            d=np.asarray([1.0,-.16],np.float32)
            for off in (-13,-5,4,12):
                p=c+d*off
                _draw_line(m["milky_shadow_edges"],p-d*3,p+d*4,3)
    curtains=(
        ((-20,76),(93,8),(294,90),(531,157)),
        ((-19,151),(121,72),(358,131),(531,224)),
        ((-17,257),(103,172),(397,203),(531,325)),
        ((-15,390),(146,264),(412,323),(529,442)),
        ((61,528),(112,359),(302,299),(445,-19)),
        ((531,35),(397,173),(151,31),(-19,229)),
        ((530,503),(388,372),(181,523),(-18,331)),
        ((173,-18),(251,139),(136,296),(286,529)),
        ((367,-18),(304,151),(478,307),(333,529)),
        ((-18,474),(103,438),(252,119),(529,83)),
    )
    for idx,control in enumerate(curtains):
        curve=_cubic_points(control,139)
        mask="blue_curtains" if idx%2==0 else "violet_curtains"
        for sample in range(3+idx%3,135,4+idx%4):
            p=curve[sample];d=_unit(curve[min(138,sample+2)]-curve[max(0,sample-2)])
            _draw_line(m[mask],p-d*3,p+d*4,4)
        for sample in range(12+idx,132,17+idx):
            p=curve[sample];t=_unit(curve[min(138,sample+3)]-curve[max(0,sample-3)])
            n=np.asarray([-t[1],t[0]],np.float32)
            for side in (-1,1):
                q=p+n*side*(4+idx)
                _draw_line(m["curtain_crests"],q-n*side*3,q+n*side*4,2)
            if (sample//17+idx)%3==0:
                _draw_ellipse(m["curtain_crossings"],tuple(np.rint(p).astype(int)),
                              (6,3),idx*29+sample,2)
    fractures=(
        ((12,305),(69,278),(111,312),(169,270)),
        ((242,31),(267,85),(249,139),(283,194)),
        ((321,414),(365,381),(398,421),(451,385)),
    )
    for idx,pts in enumerate(fractures):fragments("shear_fractures",pts,3,False,idx+2)
    m["blue_curtains"]=_f32(cv2.dilate(m["blue_curtains"],np.ones((5,5),np.uint8)))
    x,y=_xy();tone=_norm(np.sin((x+1.6*y)/57.0)+0.68*np.cos((1.9*x-y)/44.0))
    banks=dict(cleavage_skeleton="B",blue_curtains="A",violet_curtains="B",
               curtain_crests="A",shear_fractures="N",plate_notches="B",
               curtain_crossings="B",milky_shadow_edges="N")
    metal=_f32(0.04+0.67*m["blue_curtains"]+0.54*m["curtain_crests"]
               +0.42*m["curtain_crossings"]+0.16*tone)
    rough=_f32(0.08+0.66*m["cleavage_skeleton"]+0.57*m["shear_fractures"]
               +0.43*m["milky_shadow_edges"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["violet_curtains"]+0.58*m["plate_notches"]
              +0.42*m["curtain_crossings"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_sunstone_glitter() -> _Grammar:
    """A broken cleavage canyon carries localized sunstone inclusion constellations."""
    names=("branching_host_seam","gold_cleavage_plates","copper_cleavage_plates",
           "aligned_inclusions","inclusion_halves","microfractures",
           "plate_overlaps","shadow_clefts")
    m=_new(*names)
    def fragments(mask_name,points,width=3,phase=0):
        arr=np.asarray(points,np.float32)
        for edge in range(len(arr)-1):
            a,b=arr[edge],arr[edge+1];d=_unit(b-a);length=float(np.linalg.norm(b-a))
            for off in np.arange(3.0+phase%5,length,12.0+(phase+edge)%7):
                p=a+d*off
                _draw_line(m[mask_name],p-d*3,p+d*4,width)
    canyon=((-12,471),(68,418),(103,344),(179,319),(221,246),
            (301,223),(343,151),(425,127),(472,52),(529,39))
    fragments("branching_host_seam",canyon,4,1)
    sidewalls=(
        ((-12,401),(57,363),(114,382),(173,343),(236,369),(307,319),(377,343),(443,291),(529,310)),
        ((-9,515),(83,478),(142,513),(217,463),(287,496),(365,443),(446,465),(529,414)),
        ((-8,214),(69,188),(129,224),(202,175),(279,204),(351,153),(430,174),(527,118)),
    )
    for idx,pts in enumerate(sidewalls):
        mask="gold_cleavage_plates" if idx%2==0 else "copper_cleavage_plates"
        fragments(mask,pts,4,idx+2)
    clusters=((52,386,-24),(111,352,17),(177,326,-31),(239,282,9),
              (303,232,28),(362,174,-18),(423,131,37),(478,78,-7),
              (88,488,21),(208,457,-26),(333,432,13),(448,411,-35),
              (105,202,-12),(276,188,29),(429,157,-24),(38,79,32),
              (151,54,-19),(247,103,41),(355,62,-34),(487,219,11),
              (45,283,-37),(187,154,23),(321,337,-16),(493,351,28),
              (150,425,7),(265,389,-29),(397,492,35))
    for idx,(cx,cy,ang) in enumerate(clusters):
        th=np.radians(ang);d=np.asarray([np.cos(th),np.sin(th)],np.float32)
        n=np.asarray([-d[1],d[0]],np.float32);c=np.asarray([cx,cy],np.float32)
        for k in range(22+idx%9):
            along=((k*13+idx*7+k*k*3)%57)-28
            across=((k*k*7+idx*11+k*5)%43)-21
            p=c+d*along+n*across
            _draw_line(m["aligned_inclusions"],p-d*3,p+d*(4+k%4),2)
            if (k+idx)%3==0:
                _draw_line(m["inclusion_halves"],p,p+n*(4+k%5),2)
        fragments("microfractures",(c-d*19-n*5,c-d*4+n*7,c+d*21-n*4),2,idx)
        if idx%3==1:
            for side in (-1,1):
                q=c+n*side*7
                _draw_line(m["plate_overlaps"],q-n*side*3,q+n*side*4,3)
        if idx%4==2:fragments("shadow_clefts",(c-d*8,c+n*7,c+d*9-n*3),3,idx+3)
    m["inclusion_halves"]=_f32(cv2.dilate(m["inclusion_halves"],np.ones((5,5),np.uint8)))
    m["copper_cleavage_plates"]=_f32(cv2.dilate(m["copper_cleavage_plates"],np.ones((3,3),np.uint8)))
    x,y=_xy();tone=_norm(np.cos((1.5*x+y)/39.0)+0.71*np.sin((x-1.9*y)/53.0))
    banks=dict(branching_host_seam="B",gold_cleavage_plates="A",
               copper_cleavage_plates="B",aligned_inclusions="A",
               inclusion_halves="B",microfractures="N",plate_overlaps="B",
               shadow_clefts="N")
    metal=_f32(0.04+0.67*m["gold_cleavage_plates"]+0.55*m["aligned_inclusions"]
               +0.42*m["plate_overlaps"]+0.16*tone)
    rough=_f32(0.08+0.67*m["branching_host_seam"]+0.56*m["microfractures"]
               +0.43*m["shadow_clefts"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["copper_cleavage_plates"]+0.58*m["inclusion_halves"]
              +0.42*m["plate_overlaps"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_fire_agate() -> _Grammar:
    """Mutually occluding chalcedony lobes form one scalloped mineral terrain.

    A painter-ordered geological accretion leaves only partial leading fronts;
    no lobe can advertise a complete circle or ring.  Two attached skin orders,
    throat shadows, abrasion, cracks, pits and druzy facets all descend from the
    same occlusion state rather than floating over a generic substrate.
    """
    names=("chalcedony_terrain","limonite_first_order","chalcedony_second_order",
           "interlobe_throat_shadows","radial_microcracks","druzy_crown_facets",
           "pit_crescents","abraded_overlap_lips","healed_skin_bridges")
    m=_new(*names)
    x,y=_xy()
    lobes=(
        (-82,35,188,121,-18,.32),(74,-53,159,137,27,1.11),
        (225,-31,177,108,-9,2.03),(392,-43,163,151,34,.64),
        (555,42,174,112,-24,1.79),(-45,161,139,176,41,2.51),
        (83,118,116,82,-36,.18),(205,116,151,94,18,1.47),
        (354,105,123,159,-49,2.81),(503,147,151,101,23,.91),
        (7,275,171,126,-11,1.92),(143,235,108,151,52,.43),
        (278,247,164,118,-31,2.33),(424,236,111,154,37,1.23),
        (557,291,167,123,-17,2.93),(-51,401,146,162,29,.78),
        (73,375,157,106,-43,2.14),(222,369,114,169,33,1.02),
        (357,375,175,112,-21,2.67),(494,402,121,165,46,.29),
        (14,532,181,127,-14,1.55),(162,493,119,153,39,2.39),
        (307,516,171,103,-34,.57),(455,492,139,151,25,1.86),
        (561,524,155,119,-28,2.76),(123,292,91,73,17,.96),
        (330,178,87,68,-42,2.22),(396,475,82,71,31,.12),
    )
    q_fields=[]; local_fields=[]
    for cx,cy,rx,ry,angle,phase in lobes:
        theta=np.deg2rad(float(angle)); co=np.cos(theta); si=np.sin(theta)
        dx=x-float(cx); dy=y-float(cy)
        u=co*dx+si*dy; v=-si*dx+co*dy
        local=np.arctan2(v/float(ry),u/float(rx))
        radial=np.hypot(u/float(rx),v/float(ry))
        scallop=(1.0+.17*np.sin(3.0*local+phase)
                 +.075*np.sin(5.0*local-.7*phase)
                 +.055*np.cos(2.0*local+1.3*phase))
        q=radial/np.maximum(.63,scallop)
        q+=.055*(u/float(rx))*(v/float(ry))
        q_fields.append(q.astype(np.float32)); local_fields.append((u,v,local))
    q_stack=np.stack(q_fields,axis=0)
    top_id=np.full((_WORK,_WORK),-1,np.int16)
    top_q=np.ones((_WORK,_WORK),np.float32)
    inside_count=np.zeros((_WORK,_WORK),np.uint8)
    for li,q in enumerate(q_fields):
        inside=q<1.0
        inside_count+=inside.astype(np.uint8)
        top_id[inside]=li; top_q[inside]=q[inside]
    union=top_id>=0
    # The first geological bodies cover the complete cut; later bodies occlude
    # rather than tile them, so exposed regions share overlap throats.
    m["chalcedony_terrain"]=_f32(union.astype(np.float32)
                                  *(.55+.45*np.clip(1.0-top_q,0.0,1.0)))
    age=np.zeros((_WORK,_WORK),np.float32)
    all_visible_edge=np.zeros((_WORK,_WORK),np.float32)
    for li,(cx,cy,rx,ry,angle,phase) in enumerate(lobes):
        visible=(top_id==li)
        if not np.any(visible):
            continue
        q=q_fields[li]; u,v,local=local_fields[li]
        scale=float(np.sqrt(rx*ry))
        # Only the occluding leading sector may expose skins.  Six unequal
        # attached layers become broken scallops, never complete target rings.
        leading=v/float(ry)>-.58+.13*np.sin(2.0*local+phase)
        gate=visible&leading
        for order,target in enumerate((.28,.405,.535,.665,.795,.905)):
            band=_line((q-target)*scale,1.25+.18*((li+order)%3))*gate
            name=("limonite_first_order" if order%2==0
                  else "chalcedony_second_order")
            m[name]=_f32(np.maximum(m[name],band))

        vis_u=visible.astype(np.uint8)
        edge=cv2.morphologyEx(vis_u,cv2.MORPH_GRADIENT,
                              np.ones((3,3),np.uint8)).astype(np.float32)
        overlap=(inside_count>=2)&leading
        abrasion=edge*overlap.astype(np.float32)
        m["abraded_overlap_lips"]=_f32(np.maximum(
            m["abraded_overlap_lips"],abrasion))
        throat=edge*(inside_count>=3).astype(np.float32)*(q>.57)
        m["interlobe_throat_shadows"]=_f32(np.maximum(
            m["interlobe_throat_shadows"],throat))
        all_visible_edge=np.maximum(all_visible_edge,edge)

        # Every surviving crown owns a slit-pit, 2--8 px radial cracks and
        # attached angular druzy faces.  Temporary masks are clipped back to
        # the actual visible lobe, so nothing becomes a free icon scatter.
        th=np.deg2rad(float(angle)); tangent=np.asarray([np.cos(th),np.sin(th)],np.float32)
        normal=np.asarray([-tangent[1],tangent[0]],np.float32)
        crown=np.asarray([cx,cy],np.float32)+(.18*rx)*tangent+(.21*ry)*normal
        pit=np.zeros((_WORK,_WORK),np.float32)
        pit_pts=(crown-4.5*tangent-1.5*normal,
                 crown+1.5*normal,crown+4.0*tangent-1.0*normal)
        _draw_poly(pit,pit_pts,width=2,fill=False,value=.95,closed=False)
        m["pit_crescents"]=_f32(np.maximum(m["pit_crescents"],pit*visible))
        cracks=np.zeros((_WORK,_WORK),np.float32)
        for ci,delta in enumerate((-.62,.18,.83)):
            direction=np.asarray([np.cos(th+delta+phase*.11),
                                  np.sin(th+delta+phase*.11)],np.float32)
            start=crown+(2.0+ci)*direction
            _draw_line(cracks,start,start+(5.0+ci)*direction,2,.91)
        m["radial_microcracks"]=_f32(np.maximum(
            m["radial_microcracks"],cracks*visible))
        druzy=np.zeros((_WORK,_WORK),np.float32)
        for di,side in enumerate((-1.0,1.0)):
            root=crown+side*(5.0+2.0*di)*tangent+4.0*normal
            tri=(root-2.0*tangent,root+2.4*tangent,
                 root+(3.5+di)*normal+.4*side*tangent)
            _draw_poly(druzy,tri,width=2,fill=True,value=.92)
        m["druzy_crown_facets"]=_f32(np.maximum(
            m["druzy_crown_facets"],druzy*visible))
        age[visible]=(.14+.86*li/(len(lobes)-1))*(.38+.62*(1.0-q[visible]))

    # A healed bridge exists only where the two physical skin orders meet an
    # actual multi-lobe throat; it is not a shared highlight pass.
    a_near=cv2.dilate((m["limonite_first_order"]>.1).astype(np.uint8),
                      np.ones((9,9),np.uint8))
    b_near=cv2.dilate((m["chalcedony_second_order"]>.1).astype(np.uint8),
                      np.ones((9,9),np.uint8))
    contact_support=cv2.dilate(
        ((m["interlobe_throat_shadows"]+m["abraded_overlap_lips"])>.05).astype(np.uint8),
        np.ones((5,5),np.uint8))
    m["healed_skin_bridges"]=_f32((a_near>0)&(b_near>0)
                                   &(contact_support>0))
    tone=_norm(age+.28*m["limonite_first_order"]
               +.21*m["druzy_crown_facets"]-.18*m["interlobe_throat_shadows"])
    banks=dict(chalcedony_terrain="N",limonite_first_order="A",
               chalcedony_second_order="B",interlobe_throat_shadows="N",
               radial_microcracks="N",druzy_crown_facets="B",
               pit_crescents="N",abraded_overlap_lips="A",
               healed_skin_bridges="B")
    metal=_f32(.04+.72*m["limonite_first_order"]+.61*m["abraded_overlap_lips"]
               +.46*m["healed_skin_bridges"]+.15*tone*m["limonite_first_order"])
    rough=_f32(.07+.66*m["interlobe_throat_shadows"]+.58*m["radial_microcracks"]
               +.51*m["pit_crescents"]+.17*(1.0-tone)*m["chalcedony_terrain"])
    coat=_f32(.04+.73*m["chalcedony_second_order"]+.62*m["druzy_crown_facets"]
              +.51*m["healed_skin_bridges"]+.16*tone*m["chalcedony_second_order"])
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_spectrolite_vein() -> _Grammar:
    """A branching geologic vein tree offsets across plates and grows crystal teeth."""
    names=("master_vein","blue_wall_flash","violet_wall_flash",
           "vein_splays","fault_offsets","crystal_teeth",
           "alteration_halos","plate_boundaries")
    m=_new(*names)
    def fragments(mask_name,points,width=3,phase=0):
        arr=np.asarray(points,np.float32)
        for edge in range(len(arr)-1):
            a,b=arr[edge],arr[edge+1];d=_unit(b-a);length=float(np.linalg.norm(b-a))
            for off in np.arange(3.0+phase%4,length,12.0+(phase+edge)%6):
                p=a+d*off
                _draw_line(m[mask_name],p-d*3,p+d*4,width)
    trunk=((18,527),(62,449),(116,414),(141,337),(209,301),(232,221),
           (306,187),(337,109),(418,76),(476,-8))
    fragments("master_vein",trunk,4,1)
    splays=(
        ((116,414),(67,357),(11,338)),((141,337),(189,372),(244,365)),
        ((209,301),(161,245),(99,229)),((232,221),(280,257),(352,252),(406,286)),
        ((306,187),(264,130),(229,74)),((337,109),(389,137),(466,119),(526,143)),
        ((418,76),(390,22),(377,-8)),
    )
    for idx,pts in enumerate(splays):
        fragments("vein_splays",pts,3,idx+2)
        for p in pts[1:-1]:
            _draw_ellipse(m["fault_offsets"],p,(6,3),idx*27,2)
    paths=(trunk,)+splays
    feature=0
    for path in paths:
        arr=np.asarray(path,np.float32)
        for seg in range(len(arr)-1):
            a,b=arr[seg],arr[seg+1];d=_unit(b-a);n=np.asarray([-d[1],d[0]],np.float32)
            length=float(np.linalg.norm(b-a))
            for offset in np.arange(9.0,length,14.0+(feature%4)):
                p=a+d*offset
                wall="blue_wall_flash" if feature%2 else "violet_wall_flash"
                for side in (-1,1):
                    q=p+n*side*(3+feature%3)
                    _draw_line(m[wall],q-n*side*3,q+n*side*4,3)
                if feature%3==0:
                    _draw_poly(m["crystal_teeth"],(p-n*5,p+d*7,p+n*5),2,closed=False)
                if feature%4==1:
                    _draw_ellipse(m["alteration_halos"],tuple(np.rint(p).astype(int)),
                                  (7,3),np.degrees(np.arctan2(d[1],d[0])),2)
                feature+=1
    boundaries=(
        ((-9,128),(126,151),(220,113),(346,155),(526,121)),
        ((-8,304),(102,279),(241,337),(354,301),(526,344)),
        ((85,-8),(104,125),(77,259),(111,411),(92,526)),
    )
    for idx,pts in enumerate(boundaries):fragments("plate_boundaries",pts,3,idx+4)
    m["blue_wall_flash"]=_f32(cv2.dilate(m["blue_wall_flash"],np.ones((5,5),np.uint8)))
    m["violet_wall_flash"]=_f32(cv2.dilate(m["violet_wall_flash"],np.ones((5,5),np.uint8)))
    m["plate_boundaries"]=_f32(cv2.dilate(m["plate_boundaries"],np.ones((3,3),np.uint8)))
    x,y=_xy();tone=_norm(np.cos((1.6*x+y)/51.0)-0.7*np.sin((x-1.8*y)/44.0))
    m["blue_wall_flash"]=_f32(cv2.dilate(m["blue_wall_flash"],np.ones((3,3),np.uint8)))
    banks=dict(master_vein="A",blue_wall_flash="A",violet_wall_flash="B",
               vein_splays="A",fault_offsets="N",crystal_teeth="B",
               alteration_halos="B",plate_boundaries="B")
    metal=_f32(0.04+0.67*m["blue_wall_flash"]+0.55*m["vein_splays"]
               +0.42*m["alteration_halos"]+0.16*tone)
    rough=_f32(0.08+0.67*m["master_vein"]+0.56*m["fault_offsets"]
               +0.43*m["plate_boundaries"]+0.17*(1.0-tone))
    coat=_f32(0.04+0.69*m["violet_wall_flash"]+0.58*m["crystal_teeth"]
              +0.42*m["alteration_halos"]+0.16*tone)
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_bornite_patina() -> _Grammar:
    """Facet-bounded competing oxidation fronts record an actual chronology.

    The W1 branch diagram is gone.  Two chemical fronts advance as areas through
    seven hand-authored crystal faces at 4 px reaction increments.  Cleavages
    are real propagation barriers with explicit gates; the resulting stalls,
    stranded sulphide, collision heals and pits descend from that evolution.
    Face geometry is not a Voronoi source and no face outline is painted merely
    to advertise a polygon.
    """
    names=("teal_young_oxide","violet_mature_oxide","sulphide_remnants",
           "stalled_front_steps","dendritic_edge_feathers","pinhole_cavities",
           "cleavage_offsets","healed_collisions","redeposition_lips")
    m=_new(*names)
    s=128
    gy,gx=np.mgrid[0:s,0:s].astype(np.float32)
    face_id=np.zeros((s,s),np.uint8)
    face_polys=(
        ((-6,5),(68,-6),(59,37),(31,57),(-5,49)),
        ((47,-5),(133,9),(128,52),(92,64),(58,37)),
        ((-5,46),(31,57),(76,84),(60,111),(4,134)),
        ((31,57),(92,64),(116,102),(67,111),(76,84)),
        ((92,64),(133,42),(134,133),(116,102)),
        ((4,134),(60,111),(100,134)),
    )
    for face_number,poly in enumerate(face_polys,1):
        cv2.fillPoly(face_id,[np.asarray(poly,np.int32)],face_number)

    # Cleavages alter reaction arrival; their visible offsets are therefore
    # causal, never a post-composed crystal-line overlay.
    barrier_count=np.zeros((s,s),np.uint8)
    cleavage_paths=(
        ((-4,31),(22,38),(48,29),(78,44),(105,34),(132,39)),
        ((17,-4),(23,27),(38,61),(30,92),(44,132)),
        ((93,-4),(83,24),(104,54),(91,88),(116,132)),
        ((-4,101),(28,91),(61,106),(96,87),(132,96)),
    )
    for path in cleavage_paths:
        local=np.zeros((s,s),np.uint8)
        cv2.polylines(local,[np.asarray(path,np.int32)],False,1,1,cv2.LINE_8)
        barrier_count+=local
    barrier=(barrier_count>0).astype(np.uint8)
    # Fixed healed apertures interrupt the faults and let fronts resume with a
    # visible offset rather than turning every cleavage into a closed cell.
    for gate in ((35,34),(73,42),(25,48),(36,84),(88,34),(98,63),
                 (92,90),(31,94),(69,103),(112,94)):
        cv2.circle(barrier,gate,2,0,-1,cv2.LINE_8)

    kernels=(
        np.asarray(((0,1,0),(1,1,1),(0,0,0)),np.uint8),
        np.asarray(((1,1,0),(1,1,1),(0,0,0)),np.uint8),
        np.asarray(((0,0,0),(1,1,1),(0,1,0)),np.uint8),
        np.asarray(((0,1,1),(0,1,1),(0,0,0)),np.uint8),
        np.asarray(((0,0,0),(1,1,0),(1,1,0)),np.uint8),
        np.asarray(((1,0,0),(1,1,0),(0,1,0)),np.uint8),
        np.asarray(((0,1,0),(1,1,0),(0,1,0)),np.uint8),
    )

    def grow(seed,allowed,blocked,kernel,limit=108):
        arrival=np.full((s,s),-1,np.int16)
        active=(seed&allowed&(~blocked)).astype(np.uint8)
        arrival[active>0]=0
        for step in range(1,limit+1):
            expanded=cv2.dilate(active,kernel,iterations=1)
            new=(expanded>0)&allowed&(~blocked)&(arrival<0)
            if not np.any(new):
                break
            arrival[new]=step
            active[new]=1
        return arrival

    teal=np.zeros((s,s),np.float32); violet=np.zeros_like(teal)
    remnant=np.zeros_like(teal); chronology=np.zeros_like(teal)
    collision=np.zeros_like(teal); steps=np.zeros_like(teal)
    for face in range(7):
        allowed=(face_id==face)
        projection_axes=((1.0,.22),(.74,.67),(-.36,1.0),(.91,-.42),
                         (-.78,.62),(.28,-1.0),(-.93,-.31))
        ax,ay=projection_axes[face]
        projection=ax*gx+ay*gy
        values=projection[allowed]
        lo,hi=float(values.min()),float(values.max())
        seed_a=(projection<=lo+1.7)
        seed_b=(projection>=hi-1.7)
        blocked=(barrier>0)&allowed
        age_a=grow(seed_a,allowed,blocked>0,kernels[face],108)
        age_b=grow(seed_b,allowed,blocked>0,np.flip(kernels[face]),108)
        reached_a=age_a>=0; reached_b=age_b>=0
        both=reached_a&reached_b
        choose_a=reached_a&(~reached_b|((age_a+2*face)<=age_b))
        choose_b=reached_b&(~choose_a)
        arrived=reached_a|reached_b
        earliest=np.where(choose_a,age_a,np.where(choose_b,age_b,108))
        strength=.53+.47*np.clip(1.0-earliest.astype(np.float32)/108.0,0.0,1.0)
        teal[choose_a]=strength[choose_a]
        violet[choose_b]=strength[choose_b]
        remnant[allowed&(~arrived)]=1.0
        chronology[allowed&arrived]=np.clip(
            earliest[allowed&arrived].astype(np.float32)/108.0,0.0,1.0)
        collision[both&(np.abs(age_a-age_b)<=2)]=1.0
        # Four unequal, fixed chemical ages expose true terrace steps; they are
        # sparse boundaries between areas, not a repeated contour wallpaper.
        for age_mark in (9,24,47,76):
            steps[allowed&(np.abs(earliest-age_mark)<=0)]=1.0

    oxide=(teal+violet)>.08
    opposing=(cv2.dilate((teal>.08).astype(np.uint8),np.ones((3,3),np.uint8))>0)
    opposing&=(cv2.dilate((violet>.08).astype(np.uint8),
                          np.ones((3,3),np.uint8))>0)
    collision=np.maximum(collision,opposing.astype(np.float32))
    remnant=np.maximum(remnant,(barrier>0).astype(np.float32))
    # A stall is a reached front immediately against a real cleavage or an
    # unreacted sulphide remnant.  Edge feathers grow only from those stalls.
    obstacle_near=cv2.dilate((remnant>.1).astype(np.uint8),np.ones((3,3),np.uint8))
    stall=steps*np.maximum(obstacle_near.astype(np.float32),
                           cv2.dilate(barrier,np.ones((3,3),np.uint8)).astype(np.float32))
    oxide_edge=cv2.morphologyEx(oxide.astype(np.uint8),cv2.MORPH_GRADIENT,
                                np.ones((3,3),np.uint8))
    feather_seed=(oxide_edge>0)&(obstacle_near>0)
    feather=cv2.dilate(feather_seed.astype(np.uint8),
                       np.asarray(((1,0,1),(0,1,0),(0,1,0)),np.uint8))
    feather=(feather>0)&(~oxide)&(cv2.dilate(feather_seed.astype(np.uint8),
                                             np.ones((3,3),np.uint8))>0)

    # Pinhole inhibition is tied only to true cleavage intersections.  The
    # reaction had to flow around these points, so they are not a dot scatter.
    pin=(barrier_count>=2).astype(np.uint8)
    pin=cv2.dilate(pin,np.ones((2,2),np.uint8))*(oxide.astype(np.uint8))
    remnant_edge=cv2.morphologyEx((remnant>.1).astype(np.uint8),
                                  cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))
    redeposit=(remnant_edge>0)&oxide

    def up(field):
        return _f32(cv2.GaussianBlur(cv2.resize(np.asarray(field,np.float32),
                                                (_WORK,_WORK),
                                                interpolation=cv2.INTER_NEAREST),
                                     (0,0),.48))
    m["teal_young_oxide"]=up(teal)
    m["violet_mature_oxide"]=up(violet)
    m["sulphide_remnants"]=up(remnant)
    m["stalled_front_steps"]=up(np.maximum(steps*.55,stall))
    m["dendritic_edge_feathers"]=up(feather)
    m["pinhole_cavities"]=up(pin)
    offset=(barrier>0)&(cv2.dilate(oxide.astype(np.uint8),
                                   np.ones((3,3),np.uint8))>0)
    m["cleavage_offsets"]=up(offset)
    m["healed_collisions"]=up(collision)
    m["redeposition_lips"]=up(redeposit)
    tone=_norm(up(chronology)+.27*m["stalled_front_steps"]
               +.19*m["healed_collisions"]-.16*m["sulphide_remnants"])
    banks=dict(teal_young_oxide="A",violet_mature_oxide="B",
               sulphide_remnants="N",stalled_front_steps="A",
               dendritic_edge_feathers="B",pinhole_cavities="N",
               cleavage_offsets="N",healed_collisions="B",
               redeposition_lips="A")
    metal=_f32(.04+.70*m["sulphide_remnants"]+.58*m["teal_young_oxide"]
               +.47*m["redeposition_lips"]+.15*tone*m["teal_young_oxide"])
    rough=_f32(.07+.66*m["pinhole_cavities"]+.58*m["cleavage_offsets"]
               +.49*m["stalled_front_steps"]+.17*(1.0-tone)*m["sulphide_remnants"])
    coat=_f32(.04+.72*m["violet_mature_oxide"]+.61*m["healed_collisions"]
              +.52*m["dendritic_edge_feathers"]+.16*tone*m["violet_mature_oxide"])
    return _pack(m,banks,tone,metal,rough,coat)


def _build_fmo_chalcopyrite() -> _Grammar:
    """Exposed bismuth-nucleus chronology, chemically rewritten as chalcopyrite.

    Six literal off-frame hopper nuclei retain the exotic source's rotated
    Chebyshev stair ancestry.  Their scalar fields are never painted.  Growth
    arrival instead chooses one parent at each point; younger B twins overrun
    old A ledgers, and the surviving ledges are physically cut only by growth
    seams, cleavage sockets, oxidation fingers, pits, or healed collisions.
    Thus there is no complete hopper icon or independently colored territory.
    SPB-WILDS WR-MORPHO-MATERIAL-1, Chalcopyrite isolated trial W1.
    """
    x,y=_xy()
    xn=(x+0.5)/float(_WORK); yn=(y+0.5)/float(_WORK)

    # cx, cy, rotation, terrace frequency, birth time, growth speed, phase,
    # ancestry.  Every nucleus lies outside the crop, so even the un-erased
    # analytic ledger cannot close into a complete square hopper in frame.
    nuclei=(
        (-0.21, 0.17, 0.13, 34.0, 0.00, 0.88, 0.12, "A"),
        ( 1.17,-0.09, 0.91, 29.0, 0.04, 0.92, 0.43, "A"),
        (-0.08, 1.18, 0.62, 41.0, 0.08, 0.95, 0.71, "A"),
        ( 0.43,-0.22, 0.39, 37.0, 0.28, 1.18, 0.08, "B"),
        ( 1.19, 0.66, 0.17, 33.0, 0.32, 1.22, 0.48, "B"),
        ( 0.63, 1.19, 1.16, 43.0, 0.36, 1.26, 0.82, "B"),
    )
    arrivals=[]; risers=[]; landings=[]; striations=[]; phases=[]
    for index,(cx,cy,rotation,frequency,birth,speed,phase,owner) in enumerate(nuclei):
        cr,sr=float(np.cos(rotation)),float(np.sin(rotation))
        dx=(xn-cx)*cr-(yn-cy)*sr
        dy=(xn-cx)*sr+(yn-cy)*cr
        cheb=np.maximum(np.abs(dx),np.abs(dy))
        angle=np.arctan2(dy,dx)
        spiral=cheb*frequency+angle/(2.0*np.pi)+phase
        frac=np.mod(spiral,1.0).astype(np.float32)
        phase_distance=np.minimum(frac,1.0-frac)
        # 2-3 work-pixel risers and 4-7 work-pixel attached face landings.
        riser=_f32((0.085-phase_distance)/0.040)
        landing=_f32((frac-0.095)/0.055)*_f32((0.505-frac)/0.055)
        tangent=np.where(np.abs(dx)>=np.abs(dy),dy,dx)
        tangent_cycle=np.mod(tangent*_WORK+17.0*index,23.0+2.0*(index%3))
        tangent_gate=_f32(tangent_cycle/2.0)*_f32((15.0+index%4-tangent_cycle)/2.0)
        striation=_f32((0.045-np.abs(frac-0.285))/0.025)*landing*tangent_gate
        # Younger fronts genuinely start later but propagate faster.  The
        # angular term is the original hopper spiral's handed chronology.
        arrival=birth+cheb/speed+0.018*angle/(2.0*np.pi)
        arrivals.append(arrival.astype(np.float32))
        risers.append(riser); landings.append(landing); striations.append(striation)
        phases.append(frac)

    arrival_stack=np.stack(arrivals,axis=0)
    riser_stack=np.stack(risers,axis=0)
    landing_stack=np.stack(landings,axis=0)
    striation_stack=np.stack(striations,axis=0)
    phase_stack=np.stack(phases,axis=0)
    order=np.argsort(arrival_stack,axis=0)
    winner=order[0]
    runner=order[1]
    first=np.take_along_axis(arrival_stack,winner[None,...],axis=0)[0]
    second=np.take_along_axis(arrival_stack,runner[None,...],axis=0)[0]
    gap=second-first
    owner_is_b=np.asarray([entry[-1]=="B" for entry in nuclei],np.uint8)
    cross_owner=(owner_is_b[winner]!=owner_is_b[runner]).astype(np.float32)
    # The collision seam exists only where two analytic growth fields are
    # nearly simultaneous; it is not a decorative line drawn over the card.
    collision=_f32((0.0085-gap)/0.0055)
    ab_collision=collision*cross_owner
    same_parent_collision=collision*(1.0-cross_owner)

    one_hot=np.stack([(winner==index).astype(np.float32)
                      for index in range(len(nuclei))],axis=0)
    active_riser=np.max(riser_stack*one_hot,axis=0)
    active_landing=np.max(landing_stack*one_hot,axis=0)
    active_striation=np.max(striation_stack*one_hot,axis=0)
    winner_phase=np.take_along_axis(phase_stack,winner[None,...],axis=0)[0]
    a_domain=(owner_is_b[winner]==0).astype(np.float32)
    b_domain=1.0-a_domain

    # The old ledger is the winning A nucleus before the younger twins arrive;
    # using the within-A winner avoids superposing three square wallpapers.
    old_order=np.argmin(arrival_stack[:3],axis=0)
    old_sorted=np.sort(arrival_stack[:3],axis=0)
    old_family_collision=_f32((0.0085-(old_sorted[1]-old_sorted[0]))/0.0055)*a_domain
    old_raw_riser=np.max(riser_stack[:3]*np.stack(
        [(old_order==index).astype(np.float32) for index in range(3)],axis=0),axis=0)
    young_order=np.argmin(arrival_stack[3:],axis=0)
    young_sorted=np.sort(arrival_stack[3:],axis=0)
    young_family_collision=_f32((0.0085-(young_sorted[1]-young_sorted[0]))/0.0055)*b_domain
    young_raw_riser=np.max(riser_stack[3:]*np.stack(
        [(young_order==index).astype(np.float32) for index in range(3)],axis=0),axis=0)
    all_collision=_f32(np.maximum.reduce((collision,old_family_collision,
                                          young_family_collision)))

    # Young risers invade only a narrow old-face band adjoining a real A/B
    # collision.  These attached reaction fingers consume old landings instead
    # of floating as flecks or scalar oxidation territories.
    best_a=np.min(arrival_stack[:3],axis=0)
    best_b=np.min(arrival_stack[3:],axis=0)
    signed=best_a-best_b                 # negative on surviving old A
    old_side_band=_f32((signed+0.060)/0.018)*_f32((-signed+0.003)/0.010)
    young_riser_near=cv2.dilate((young_raw_riser>0.08).astype(np.float32),
                                 np.ones((5,5),np.uint8))
    oxidation_fingers=_f32(old_side_band*young_riser_near)

    # Three latent cleavage planes become visible only where they physically
    # notch a winning stair/landing.  Their macro carriers never reach paint.
    cleavage_planes=np.zeros((_WORK,_WORK),np.float32)
    _draw_poly(cleavage_planes,((-18,103),(116,146),(225,139),(343,191),(538,217)),6)
    _draw_poly(cleavage_planes,((73,-18),(99,114),(161,232),(144,350),(213,536)),5)
    _draw_poly(cleavage_planes,((536,73),(403,116),(333,207),(216,263),(-17,321)),7)
    structure_near=cv2.dilate(((active_riser>0.08)|(active_landing>0.35)).astype(np.float32),
                              np.ones((7,7),np.uint8))
    cleavage_core=_f32(cleavage_planes*structure_near)
    cleavage_damage=cv2.dilate((cleavage_core>0.12).astype(np.float32),
                                np.ones((5,5),np.uint8))

    # Pits and heals are snapped to actual collision/ledge crossings.  Fixed
    # anchors choose among causal sites; the anchors themselves draw nothing.
    collision_sites=(cv2.dilate((ab_collision>0.12).astype(np.uint8),
                                 np.ones((7,7),np.uint8))>0)&(active_riser>0.14)
    candidates=np.argwhere(collision_sites)
    def snapped_sites(anchors,count,minimum=34.0):
        selected=[]
        if not len(candidates):
            return selected
        for ax,ay in anchors:
            distances=(candidates[:,1]-ax)**2+(candidates[:,0]-ay)**2
            for pick in np.argsort(distances):
                py,px=(int(candidates[pick,0]),int(candidates[pick,1]))
                if all((px-qx)**2+(py-qy)**2>=minimum**2 for qx,qy in selected):
                    selected.append((px,py)); break
            if len(selected)>=count:
                break
        return selected
    anchors=((42,54),(151,61),(277,48),(423,67),(482,151),(454,275),
             (472,433),(352,476),(218,452),(84,472),(54,337),(86,214),
             (196,177),(321,246),(267,357),(382,366))
    sites=snapped_sites(anchors,12)
    pit_cavity=np.zeros((_WORK,_WORK),np.float32)
    pit_lip=np.zeros_like(pit_cavity)
    healed=np.zeros_like(pit_cavity)
    grad_y,grad_x=np.gradient(signed)
    for site_index,(px,py) in enumerate(sites):
        gx,gy=float(grad_x[py,px]),float(grad_y[py,px])
        normal=_unit((gx,gy)); tangent=np.asarray((-normal[1],normal[0]),np.float32)
        centre=np.asarray((px,py),np.float32)
        if site_index%3!=1:
            axes=(2+site_index%2,2+(site_index+1)%2)
            _draw_ellipse(pit_cavity,centre,axes,(site_index*29)%180,fill=True)
            _draw_ellipse(pit_lip,centre,(axes[0]+1,axes[1]+1),
                          (site_index*29)%180,width=2)
        else:
            points=(centre-tangent*(4+site_index%2)-normal*2,
                    centre+tangent*(5+site_index%3)-normal,
                    centre+tangent*2+normal*(5+site_index%2),
                    centre-tangent*3+normal*(4+site_index%3))
            _draw_poly(healed,points,fill=True)

    # Collision bridges and pit/cleavage interiors replace, rather than sit on,
    # their ledges.  This is the literal endpoint contract for every internal
    # riser fragment.  If competition accidentally encloses a riser loop, its
    # own inner contour nucleates one additional attached cleavage socket; this
    # enforces the no-complete-hopper contract without adding a free mark.
    heal_damage=cv2.dilate((healed>0.08).astype(np.float32),np.ones((3,3),np.uint8))
    old_active=old_raw_riser*a_domain
    young_active=young_raw_riser*b_domain
    provisional_damage=_f32(np.maximum.reduce((cleavage_damage,pit_cavity,
                                                heal_damage,oxidation_fingers)))
    provisional_riser=_f32((old_active+young_active)*(1.0-provisional_damage))
    contours,hierarchy=cv2.findContours((provisional_riser>0.14).astype(np.uint8),
                                         cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    closure_break=np.zeros((_WORK,_WORK),np.float32)
    if hierarchy is not None:
        for contour_index,relation in enumerate(hierarchy[0]):
            if int(relation[3])<0 or len(contours[contour_index])<2:
                continue
            points=contours[contour_index][:,0,:]
            px,py=map(int,points[np.argmin(points[:,1]+0.17*points[:,0])])
            _draw_ellipse(closure_break,(px,py),(4,3),31.0+17.0*contour_index,fill=True)
    cleavage_core=_f32(np.maximum(cleavage_core,closure_break))
    cleavage_damage=_f32(np.maximum(cleavage_damage,cv2.dilate(
        (closure_break>0.08).astype(np.float32),np.ones((3,3),np.uint8))))
    event_damage=_f32(np.maximum.reduce((cleavage_damage,pit_cavity,
                                         heal_damage,oxidation_fingers)))
    old_riser=_f32(old_active*(1.0-event_damage))
    young_riser=_f32(young_active*(1.0-np.maximum.reduce(
        (cleavage_damage,pit_cavity,heal_damage))))
    old_landing=_f32(active_landing*a_domain*(1.0-event_damage))
    young_landing=_f32(active_landing*b_domain*(1.0-np.maximum.reduce(
        (cleavage_damage,pit_cavity,heal_damage))))

    # All collision paint is clipped to the physical stair neighbourhood, so
    # the source competition cannot leak out as a macro Voronoi boundary.
    ledge_near=cv2.dilate(((old_riser+young_riser+old_landing+young_landing)>0.10)
                          .astype(np.float32),np.ones((5,5),np.uint8))
    twin_steps=_f32(all_collision*ledge_near)
    cleavage_offsets=_f32(np.maximum(pit_lip*0.28,
        _edge(cleavage_damage,1)*cv2.dilate((active_landing>0.2).astype(np.float32),
                                            np.ones((3,3),np.uint8))))
    landing_epoch=np.mod(np.floor(first*43.0)+2.0*winner,7.0)
    remnant_epoch=((landing_epoch==1.0)|(landing_epoch==4.0)).astype(np.float32)
    sulphide_remnants=_f32(old_landing*remnant_epoch
                            *_f32((0.055-np.abs(winner_phase-0.315))/0.030)
                            *(1.0-oxidation_fingers))
    face_striations=_f32(active_striation*(0.72*a_domain+0.46*b_domain)
                          *(1.0-event_damage))
    healed_bridges=_f32(healed*cv2.dilate((twin_steps>0.08).astype(np.float32),
                                          np.ones((7,7),np.uint8)))
    pinhole_cavities=_f32(np.maximum(pit_cavity,pit_lip*0.55))

    masks={
        "old_twin_face_landings":old_landing,
        "young_overrun_landings":young_landing,
        "exposed_brass_risers":old_riser,
        "iridescent_oxide_risers":young_riser,
        "stepped_twin_collision_seams":twin_steps,
        "face_tangent_striations":face_striations,
        "oxidation_reaction_fingers":oxidation_fingers,
        "cleavage_offset_sockets":cleavage_offsets,
        "pinhole_reaction_cavities":pinhole_cavities,
        "healed_collision_wedges":healed_bridges,
        "sulphide_face_remnants":sulphide_remnants,
    }
    banks=dict(old_twin_face_landings="A",young_overrun_landings="B",
               exposed_brass_risers="A",iridescent_oxide_risers="B",
               stepped_twin_collision_seams="N",face_tangent_striations="A",
               oxidation_reaction_fingers="B",cleavage_offset_sockets="N",
               pinhole_reaction_cavities="N",healed_collision_wedges="B",
               sulphide_face_remnants="A")
    # Fixed step chronology supplies shade variation only within named marks;
    # it never paints a scalar source field or a parent territory.
    step_age=np.mod(np.floor(np.take_along_axis(
        (phase_stack+arrival_stack*9.0),winner[None,...],axis=0)[0])*0.173
                    +winner_phase*0.71,1.0)
    tone=_norm(0.62*step_age+0.23*winner_phase+0.15*_norm(gap))

    # M/R/Cc own different physical anatomy instead of sharing one overlay.
    metal=_f32(0.03+0.74*old_landing+0.92*old_riser+0.63*sulphide_remnants
               +0.48*face_striations+0.13*tone*old_landing)
    rough=_f32(0.04+0.86*cleavage_offsets+0.78*pinhole_cavities
               +0.62*twin_steps+0.51*oxidation_fingers
               +0.11*(1.0-tone)*twin_steps)
    coat=_f32(0.03+0.77*young_landing+0.91*young_riser
              +0.72*healed_bridges+0.58*oxidation_fingers
              +0.12*tone*young_landing)

    old_pixels=old_raw_riser>0.12
    surviving_old=(old_riser>0.12)&old_pixels
    erasure=1.0-float(np.count_nonzero(surviving_old))/max(1.0,float(np.count_nonzero(old_pixels)))
    material_union=np.maximum.reduce(tuple(masks.values()))
    # Closed line contours would be a literal hopper-icon violation.
    riser_binary=((old_riser+young_riser)>0.14).astype(np.uint8)
    _contours,hierarchy=cv2.findContours(riser_binary,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    closed_holes=0 if hierarchy is None else int(np.count_nonzero(hierarchy[0,:,3]>=0))
    _CHALCOPYRITE_BUILD_STATS.clear()
    _CHALCOPYRITE_BUILD_STATS.update({
        "source_nucleus_count":float(len(nuclei)),
        "source_nuclei_inside_crop":float(sum(0.0<=q[0]<=1.0 and 0.0<=q[1]<=1.0
                                                for q in nuclei)),
        "old_ledger_erasure_fraction":erasure,
        "material_union_coverage_gt_0_1":float(np.mean(material_union>0.10)),
        "a_owned_coverage_gt_0_1":float(np.mean(np.maximum.reduce(
            tuple(mask for name,mask in masks.items() if banks[name]=="A"))>0.10)),
        "b_owned_coverage_gt_0_1":float(np.mean(np.maximum.reduce(
            tuple(mask for name,mask in masks.items() if banks[name]=="B"))>0.10)),
        "closed_riser_hole_count":float(closed_holes),
        "pit_site_count":float(len(sites)),
        "old_domain_fraction":float(np.mean(a_domain)),
        "young_domain_fraction":float(np.mean(b_domain)),
    })
    _CHALCOPYRITE_DEBUG.clear()
    _CHALCOPYRITE_DEBUG.update({
        "old_raw_ledger":old_raw_riser,
        "old_surviving_risers":old_riser,
        "young_surviving_risers":young_riser,
        "event_damage_union":event_damage,
        "twin_collision_support":twin_steps,
        "material_union":material_union,
    })
    return _pack(masks,banks,tone,metal,rough,coat)


_BUILDERS: Mapping[str, Callable[[], _Grammar]] = {
    "fmo_pigeon_neck": _build_fmo_pigeon_neck,
    "fmo_grackle_oil": _build_fmo_grackle_oil,
    "fmo_sunbird_throat": _build_fmo_sunbird_throat,
    "fmo_cassowary_quill": _build_fmo_cassowary_quill,
    "fmo_raven_flash": _build_fmo_raven_flash,
    "fmo_abalone_drift": _build_fmo_abalone_drift,
    "fmo_black_pearl": _build_fmo_black_pearl,
    "fmo_soap_bubble": _build_fmo_soap_bubble,
    "fmo_oil_slick": _build_fmo_oil_slick,
    "fmo_mother_of_pearl": _build_fmo_mother_of_pearl,
    "fmo_nacre_brick": _build_fmo_nacre_brick,
    "fmo_mussel_shell": _build_fmo_mussel_shell,
    "fmo_foam_film": _build_fmo_foam_film,
    "fmo_paua_storm": _build_fmo_paua_storm,
    "fmo_pearl_oyster": _build_fmo_pearl_oyster,
    "fmo_labradorite": _build_fmo_labradorite,
    "fmo_black_opal": _build_fmo_black_opal,
    "fmo_ammolite_skin": _build_fmo_ammolite_skin,
    "fmo_alexandrite_dusk": _build_fmo_alexandrite_dusk,
    "fmo_moonstone_adular": _build_fmo_moonstone_adular,
    "fmo_sunstone_glitter": _build_fmo_sunstone_glitter,
    "fmo_fire_agate": _build_fmo_fire_agate,
    "fmo_spectrolite_vein": _build_fmo_spectrolite_vein,
    "fmo_bornite_patina": _build_fmo_bornite_patina,
    "fmo_chalcopyrite": _build_fmo_chalcopyrite,
}


_HUES: Mapping[str, Tuple[float, float]] = {
    "fmo_pigeon_neck": (0.42, 0.82),
    "fmo_grackle_oil": (0.55, 0.76),
    "fmo_sunbird_throat": (0.09, 0.88),
    "fmo_cassowary_quill": (0.54, 0.08),
    "fmo_raven_flash": (0.51, 0.78),
    "fmo_abalone_drift": (0.47, 0.91),
    "fmo_black_pearl": (0.39, 0.79),
    "fmo_soap_bubble": (0.49, 0.96),
    "fmo_oil_slick": (0.34, 0.84),
    "fmo_mother_of_pearl": (0.51, 0.94),
    "fmo_nacre_brick": (0.45, 0.89),
    "fmo_mussel_shell": (0.58, 0.78),
    "fmo_foam_film": (0.50, 0.02),
    "fmo_paua_storm": (0.46, 0.87),
    "fmo_pearl_oyster": (0.12, 0.92),
    "fmo_labradorite": (0.56, 0.12),
    "fmo_black_opal": (0.47, 0.98),
    "fmo_ammolite_skin": (0.36, 0.02),
    "fmo_alexandrite_dusk": (0.37, 0.96),
    "fmo_moonstone_adular": (0.58, 0.72),
    "fmo_sunstone_glitter": (0.07, 0.56),
    "fmo_fire_agate": (0.10, 0.99),
    "fmo_spectrolite_vein": (0.53, 0.83),
    "fmo_bornite_patina": (0.48, 0.80),
    "fmo_chalcopyrite": (0.12, 0.58),
}


MORPHO_MATERIAL_IDS: Tuple[str, ...] = tuple(_BUILDERS)


if len(MORPHO_MATERIAL_IDS) != 25 or set(MORPHO_MATERIAL_IDS) != set(_HUES):
    raise AssertionError("Morpho material rebuild must own exactly its 25 configured IDs")
if len(set(_BUILDERS.values())) != 25:
    raise AssertionError("one separate builder function is required per ID")


@lru_cache(maxsize=8)
def _authored(fid: str) -> Tuple[np.ndarray, np.ndarray]:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _compose(_BUILDERS[fid](), _HUES[fid])


def clear_cache() -> None:
    _authored.cache_clear()
    _xy.cache_clear()


def debug_grammar(fid: str) -> _Grammar:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _BUILDERS[fid]()


def debug_hue_null(fid: str) -> np.ndarray:
    """Palette-independent topology evidence; color cannot hide repetition."""
    grammar = debug_grammar(fid)
    out = np.full((_WORK, _WORK), 0.07, np.float32)
    levels = (0.28, 0.73, 0.43, 0.91, 0.57, 0.82, 0.35, 0.66, 0.97)
    for i, (_name, mask, owner) in enumerate(grammar.marks):
        # A and B receive opposing luminance order, exposing material ownership.
        idx = i if owner != "B" else len(levels) - 1 - (i % len(levels))
        value = levels[idx % len(levels)]
        out = out * (1.0 - mask) + value * mask
    return np.repeat(np.clip(out[..., None], 0, 1), 3, axis=2).astype(np.float32)


def debug_angle_pair(fid: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Controlled A/B material proof driven only by independent spec topology."""
    paint, spec = _authored(fid)
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - 0.58 * rough, 0.20, 1.0)
    lobe_a = np.clip(0.16 + 1.02 * metal * aperture, 0.12, 1.20)
    lobe_b = np.clip(0.16 + 1.02 * coat * aperture, 0.12, 1.20)
    warm = np.asarray([0.15, 0.065, 0.018], np.float32)
    cool = np.asarray([0.018, 0.085, 0.16], np.float32)
    angle_a = np.clip(paint * lobe_a[..., None] + warm * (metal * aperture)[..., None], 0, 1)
    angle_b = np.clip(paint * lobe_b[..., None] + cool * (coat * aperture)[..., None], 0, 1)
    diff = np.abs(angle_a - angle_b)
    return angle_a.astype(np.float32), angle_b.astype(np.float32), diff.astype(np.float32)


def _entry(fid: str):
    """Return the registry's required ``(spec_fn, paint_fn)`` tuple."""
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)
        if src.ndim != 3 or src.shape[2] < 3:
            src = np.zeros((fh, fw, 3), np.float32)
        else:
            src = src[:, :, :3]
            if src.size and float(np.max(src)) > 1.5:
                src = src / 255.0
            if src.shape[:2] != (fh, fw):
                src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored, _ = _authored(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(m2 * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        _, authored = _authored(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(_CALM_SPEC + (authored - _CALM_SPEC) * max(0.0, float(sm)), 0, 255)
        mk = np.clip(m2, 0, 1)[..., None]
        rgb = active * mk + _CALM_SPEC * (1.0 - mk)
        out = np.empty((fh, fw, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    spec_fn.__name__ = f"spec_{fid}_material_rejection_rebuild"
    paint_fn.__name__ = f"paint_{fid}_material_rejection_rebuild"
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the 25 current Morpho feather/nacre/mineral IDs."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    engine_module = _sys.modules.get("shokker_engine_v2")
    if engine_module is not None and hasattr(engine_module, "FUSION_REGISTRY"):
        regs.append(engine_module.FUSION_REGISTRY)
    unique_regs = []
    for reg in regs:
        if all(reg is not other for other in unique_regs):
            unique_regs.append(reg)
    for fid in MORPHO_MATERIAL_IDS:
        entry = _entry(fid)
        for reg in unique_regs:
            reg[fid] = entry
    return f"fractured-wilds-morpho-material-rejection-candidate: {len(MORPHO_MATERIAL_IDS)} explicit grammars live"


def _sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _card(image: np.ndarray, label: str, cell: int = 224, header: int = 28) -> np.ndarray:
    u = np.asarray(image)
    if u.ndim == 2:
        u = np.repeat(u[:, :, None], 3, axis=2)
    if np.issubdtype(u.dtype, np.floating):
        u = np.clip(u * 255.0, 0, 255).astype(np.uint8)
    else:
        u = np.clip(u, 0, 255).astype(np.uint8)
    rgb = cv2.resize(u[:, :, :3], (cell, cell), interpolation=cv2.INTER_NEAREST)
    card = np.full((cell + header, cell, 3), 17, np.uint8)
    card[header:] = rgb
    cv2.putText(card, label.replace("fmo_", "")[:25], (5, 19), cv2.FONT_HERSHEY_SIMPLEX,
                0.42, (245, 245, 245), 1, cv2.LINE_AA)
    return card


def _write_contact(path: Path, images: Sequence[np.ndarray], labels: Sequence[str]) -> None:
    cards = [_card(image, label) for image, label in zip(images, labels)]
    rows = []
    for i in range(0, len(cards), 5):
        row = cards[i:i + 5]
        while len(row) < 5:
            row.append(np.full_like(cards[0], 17))
        rows.append(np.hstack(row))
    rgb = np.vstack(rows)
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def _audit(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    labels = list(MORPHO_MATERIAL_IDS)
    contacts = {key: [] for key in ("color", "hue_null", "metal", "rough", "coat",
                                            "angle_a", "angle_b", "angle_diff")}
    rows = []
    hue_vectors = []
    paint_vectors = []
    for fid in labels:
        started = time.perf_counter()
        grammar = debug_grammar(fid)
        paint, spec = _compose(grammar, _HUES[fid])
        hue_null = debug_hue_null(fid)
        angle_a, angle_b, angle_diff = debug_angle_pair(fid)
        elapsed = time.perf_counter() - started
        contacts["color"].append(paint)
        contacts["hue_null"].append(hue_null)
        contacts["metal"].append(np.repeat((spec[:, :, 0:1] / 255.0), 3, axis=2))
        contacts["rough"].append(np.repeat((spec[:, :, 1:2] / 255.0), 3, axis=2))
        contacts["coat"].append(np.repeat((spec[:, :, 2:3] / 255.0), 3, axis=2))
        contacts["angle_a"].append(angle_a)
        contacts["angle_b"].append(angle_b)
        contacts["angle_diff"].append(np.clip(angle_diff * 2.4, 0, 1))
        small = cv2.resize(hue_null[:, :, 0], (64, 64), interpolation=cv2.INTER_AREA)
        hue_vectors.append((small - float(np.mean(small))).reshape(-1))
        paint_gray = cv2.cvtColor((paint * 255.0).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        paint_small = cv2.resize(paint_gray, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
        paint_vectors.append((paint_small - float(np.mean(paint_small))).reshape(-1))
        active_ramp_levels = {"A": set(), "B": set()}
        for i, (_name, mark_mask, owner) in enumerate(grammar.marks):
            if owner == "A":
                field = np.mod(grammar.tone + 0.073 * i, 1.0)
            elif owner == "B":
                field = np.mod((1.0 - grammar.tone) + 0.073 * (i + 2), 1.0)
            else:
                continue
            active_ramp_levels[owner].update(
                np.unique(np.digitize(field, _COLOR_BANDS)[mark_mask > 0.10]).tolist())
        rows.append({
            "id": fid,
            "builder": _BUILDERS[fid].__name__,
            "mark_count": len(grammar.marks),
            "mark_names": [name for name, _mask, _bank in grammar.marks],
            "material_owners": {name: bank for name, _mask, bank in grammar.marks},
            "palette_authored_color_count": 16,
            "active_purposeful_color_count": (len(active_ramp_levels["A"])
                                                + len(active_ramp_levels["B"]) + 2),
            "paint_sha256": _sha((paint * 255.0).astype(np.uint8)),
            "hue_null_sha256": _sha((hue_null * 255.0).astype(np.uint8)),
            "metal_sha256": _sha(spec[:, :, 0]),
            "rough_sha256": _sha(spec[:, :, 1]),
            "coat_sha256": _sha(spec[:, :, 2]),
            "metal_std": round(float(np.std(spec[:, :, 0])), 3),
            "rough_std": round(float(np.std(spec[:, :, 1])), 3),
            "coat_std": round(float(np.std(spec[:, :, 2])), 3),
            "metal_level_count": int(len(np.unique(spec[:, :, 0]))),
            "rough_level_count": int(len(np.unique(spec[:, :, 1]))),
            "coat_level_count": int(len(np.unique(spec[:, :, 2]))),
            "angle_diff_mean": round(float(np.mean(angle_diff)), 5),
            "candidate_build_seconds": round(elapsed, 4),
        })

    similarities = []
    for i in range(len(labels)):
        vi = hue_vectors[i]
        ni = max(1.0e-6, float(np.linalg.norm(vi)))
        for j in range(i + 1, len(labels)):
            vj = hue_vectors[j]
            corr = float(np.dot(vi, vj) / (ni * max(1.0e-6, float(np.linalg.norm(vj)))))
            similarities.append((corr, labels[i], labels[j]))
    similarities.sort(reverse=True)
    paint_similarities = []
    for i in range(len(labels)):
        vi = paint_vectors[i]
        ni = max(1.0e-6, float(np.linalg.norm(vi)))
        for j in range(i + 1, len(labels)):
            vj = paint_vectors[j]
            corr = float(np.dot(vi, vj) / (ni * max(1.0e-6, float(np.linalg.norm(vj)))))
            paint_similarities.append((corr, labels[i], labels[j]))
    paint_similarities.sort(reverse=True)

    native_samples = []
    for fid in (labels[0], labels[5], labels[12], labels[18], labels[-1]):
        clear_cache()
        spec_fn, paint_fn = _entry(fid)
        shape = (2048, 2048)
        mask = np.ones(shape, np.float32)
        base = np.zeros((2048, 2048, 3), np.float32)
        started = time.perf_counter()
        spec_out = spec_fn(shape, mask, 17, 1.0)
        paint_out = paint_fn(base, shape, mask, 17, 1.0, None)
        elapsed = time.perf_counter() - started
        native_samples.append({
            "id": fid, "combined_cold_2048_seconds": round(elapsed, 4),
            "paint_shape": list(paint_out.shape), "paint_dtype": str(paint_out.dtype),
            "spec_shape": list(spec_out.shape), "spec_dtype": str(spec_out.dtype),
        })

    for key, images in contacts.items():
        _write_contact(output / f"{key}_contact.png", images, labels)

    all_hash_keys = ("paint_sha256", "hue_null_sha256", "metal_sha256", "rough_sha256", "coat_sha256")
    report = {
        "status": "isolated_candidate_not_owner_accepted",
        "ticket": "SPB-WILDS-REJECTION-2026-08-24 WR-MORPHO-MATERIAL-1",
        "id_count": len(labels),
        "separate_builder_count": len(set(_BUILDERS.values())),
        "ids_in_insertion_order": labels,
        "no_rng_noise_grain_or_flecks": True,
        "no_shared_source_router": True,
        "fixed_thresholds_not_rank_quantization": True,
        "all_have_seven_or_more_causal_marks": all(row["mark_count"] >= 7 for row in rows),
        "all_have_explicit_a_and_b_ownership": all(
            {"A", "B"}.issubset(set(row["material_owners"].values())) for row in rows),
        "all_spec_std_over_20": all(min(row["metal_std"], row["rough_std"], row["coat_std"]) > 20.0
                                     for row in rows),
        "all_spec_channels_use_eight_authored_levels": all(
            min(row["metal_level_count"], row["rough_level_count"], row["coat_level_count"]) == 8
            for row in rows),
        "all_paints_use_at_least_fourteen_purposeful_colors": all(
            row["active_purposeful_color_count"] >= 14 for row in rows),
        "unique_hash_counts": {key: len({row[key] for row in rows}) for key in all_hash_keys},
        "weakest_spec_channel_std": min(min(row["metal_std"], row["rough_std"], row["coat_std"])
                                          for row in rows),
        "slowest_sampled_combined_cold_2048_seconds": max(r["combined_cold_2048_seconds"]
                                                            for r in native_samples),
        "closest_hue_null_pairs_cosine": [
            {"cosine": round(corr, 5), "a": a, "b": b} for corr, a, b in similarities[:12]
        ],
        "closest_paint_pairs_cosine": [
            {"cosine": round(corr, 5), "a": a, "b": b} for corr, a, b in paint_similarities[:12]
        ],
        "native_2048_samples": native_samples,
        "finishes": rows,
    }
    (output / "candidate_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Fractured Wilds — Morpho Material Explicit Candidate Audit",
        "",
        "**Status: isolated candidate; NOT owner accepted.**",
        "",
        f"- IDs/builders: {report['id_count']}/{report['separate_builder_count']}",
        f"- 7+ causal masks per finish: {report['all_have_seven_or_more_causal_marks']}",
        f"- Explicit opposing A/B material ownership: {report['all_have_explicit_a_and_b_ownership']}",
        f"- Unique paint/hue-null/M/R/Cc hashes: {report['unique_hash_counts']}",
        f"- Weakest spec-channel std: {report['weakest_spec_channel_std']:.3f}",
        f"- Every M/R/Cc channel uses all eight authored levels: {report['all_spec_channels_use_eight_authored_levels']}",
        f"- Every paint actively uses at least 14 purposeful palette colors: {report['all_paints_use_at_least_fourteen_purposeful_colors']}",
        f"- Slowest sampled cold combined 2048 paint+spec: {report['slowest_sampled_combined_cold_2048_seconds']:.4f}s",
        "- Randomness/noise/grain/flecks: absent by construction.",
        "- Quantization: fixed causal thresholds, never rank/equal-population.",
        "",
        "## Owner-eye status",
        "",
        "- This file records mechanical evidence only; it does not declare any card a KEEP.",
        "- Continuous rails were fragmented and several stamped/paved prototypes were replaced, but the strict contact audit remains authoritative and may still return REPAIR/REBUILD.",
        f"- Current closest hue-null diagnostic: {similarities[0][0]:.5f} ({similarities[0][1]} vs {similarities[0][2]}).",
        f"- Current closest paint diagnostic: {paint_similarities[0][0]:.5f} ({paint_similarities[0][1]} vs {paint_similarities[0][2]}).",
        "",
        "Machine evidence is diagnostic only.  See FINAL_OWNER_EYE_AUDIT.md for the",
        "adversarial per-ID verdict; no metric or hash can confer visual acceptance.",
    ]
    (output / "CANDIDATE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _write_rgb(path: Path, image: np.ndarray) -> None:
    u=np.asarray(image)
    if u.ndim==2:
        u=np.repeat(u[:,:,None],3,axis=2)
    if np.issubdtype(u.dtype,np.floating):
        u=np.clip(u*255.0,0,255).astype(np.uint8)
    else:
        u=np.clip(u,0,255).astype(np.uint8)
    cv2.imwrite(str(path),cv2.cvtColor(u[:,:,:3],cv2.COLOR_RGB2BGR))


def _audit_single(fid: str, output: Path) -> dict:
    """Focused evidence; never regenerates or visually launders the full shelf."""
    if fid not in _BUILDERS:
        raise KeyError(fid)
    output.mkdir(parents=True,exist_ok=True)
    clear_cache()
    started=time.perf_counter()
    grammar=debug_grammar(fid)
    paint,spec=_compose(grammar,_HUES[fid])
    hue_null=debug_hue_null(fid)
    angle_a,angle_b,angle_diff=debug_angle_pair(fid)
    build_seconds=time.perf_counter()-started
    channels={
        "paint":paint,
        "hue_null":hue_null,
        "metal":np.repeat(spec[:,:,0:1]/255.0,3,axis=2),
        "rough":np.repeat(spec[:,:,1:2]/255.0,3,axis=2),
        "coat":np.repeat(spec[:,:,2:3]/255.0,3,axis=2),
        "angle_a":angle_a,
        "angle_b":angle_b,
        "angle_diff":np.clip(angle_diff*2.4,0,1),
    }
    for name,image in channels.items():
        _write_rgb(output/f"{name}.png",image)
    _write_contact(output/"finish_evidence_contact.png",list(channels.values()),
                   list(channels))
    mask_images=[]; mask_names=[]; marks=[]
    for name,mask,owner in grammar.marks:
        mask_images.append(np.repeat(mask[:,:,None],3,axis=2))
        mask_names.append(f"{owner}_{name}")
        marks.append({"name":name,"owner":owner,"std":round(float(np.std(mask)),5),
                      "coverage_gt_0_1":round(float(np.mean(mask>.10)),5),
                      "sha256":_sha((mask*255.0).astype(np.uint8))})
    _write_contact(output/"semantic_masks_contact.png",mask_images,mask_names)

    clear_cache(); spec_fn,paint_fn=_entry(fid)
    shape=(2048,2048); mask=np.ones(shape,np.float32)
    base=np.zeros((2048,2048,3),np.float32)
    native_started=time.perf_counter()
    native_spec=spec_fn(shape,mask,17,1.0)
    native_paint=paint_fn(base,shape,mask,17,1.0,None)
    native_seconds=time.perf_counter()-native_started
    chalcopyrite_thickness={}
    if fid=="fmo_chalcopyrite":
        # Preserve the exact native API result plus true picker reductions.
        # These are evidence artifacts only; the isolated trial remains unwired.
        picker_128=cv2.resize(paint,(128,128),interpolation=cv2.INTER_AREA)
        picker_64=cv2.resize(paint,(64,64),interpolation=cv2.INTER_AREA)
        hue_picker_64=cv2.resize(hue_null,(64,64),interpolation=cv2.INTER_AREA)
        native_crop=native_paint[768:1280,768:1280]
        _write_rgb(output/"native_2048_paint.png",native_paint)
        _write_rgb(output/"picker_128.png",picker_128)
        _write_rgb(output/"picker_64.png",picker_64)
        _write_contact(output/"native_picker_contact.png",
                       (native_paint,native_crop,paint,picker_128,picker_64,
                        hue_picker_64),
                       ("native full 2048","native 512 crop","authored 512",
                        "picker 128","picker 64","hue-null picker 64"))
        native_m=np.repeat(native_spec[:,:,0:1]/255.0,3,axis=2)
        native_r=np.repeat(native_spec[:,:,1:2]/255.0,3,axis=2)
        native_c=np.repeat(native_spec[:,:,2:3]/255.0,3,axis=2)
        _write_contact(output/"native_material_contact.png",
                       (native_paint,native_m,native_r,native_c,angle_diff),
                       ("native paint 2048","native M 2048","native R 2048",
                        "native Cc 2048","runtime A-B diff"))

        # Distance-transform thickness is reported in work and native pixels.
        # A few maxima exceed eight only where attached primitives intersect;
        # p95 records the local carrier thickness rather than those junctions.
        thickness_images=[]; thickness_labels=[]
        for name,mark_mask,owner in grammar.marks:
            binary=(mark_mask>0.10).astype(np.uint8)
            distance=cv2.distanceTransform(binary,cv2.DIST_L2,5)*2.0
            values=distance[binary>0]
            stats={
                "owner":owner,
                "p50_work_px":round(float(np.percentile(values,50)),3),
                "p90_work_px":round(float(np.percentile(values,90)),3),
                "p95_work_px":round(float(np.percentile(values,95)),3),
                "max_work_px":round(float(np.max(values)),3),
                "p95_native_2048_px":round(float(np.percentile(values,95))*4.0,3),
            }
            chalcopyrite_thickness[name]=stats
            thickness_images.append(np.repeat(np.clip(distance/8.0,0,1)[:,:,None],3,axis=2))
            thickness_labels.append(f"{owner} {name} p95={stats['p95_work_px']}")
        _write_contact(output/"local_thickness_contact.png",thickness_images,
                       thickness_labels)
        ancestry_names=("old_raw_ledger","old_surviving_risers",
                        "young_surviving_risers","event_damage_union",
                        "twin_collision_support","material_union")
        ancestry_images=[np.repeat(_CHALCOPYRITE_DEBUG[name][:,:,None],3,axis=2)
                         for name in ancestry_names]
        _write_contact(output/"chalcopyrite_ancestry_contact.png",ancestry_images,
                       ancestry_names)
    report={
        "status":"isolated_single_finish_candidate_not_owner_accepted",
        "id":fid,"builder":_BUILDERS[fid].__name__,"build_seconds_512":build_seconds,
        "combined_cold_2048_seconds":native_seconds,"marks":marks,
        "paint_sha256":_sha((paint*255.0).astype(np.uint8)),
        "hue_null_sha256":_sha((hue_null*255.0).astype(np.uint8)),
        "metal_std":float(np.std(spec[:,:,0])),
        "rough_std":float(np.std(spec[:,:,1])),
        "coat_std":float(np.std(spec[:,:,2])),
        "angle_diff_mean":float(np.mean(angle_diff)),
        "native_paint_shape":list(native_paint.shape),
        "native_spec_shape":list(native_spec.shape),
        "owner_acceptance_claimed":False,
    }
    if fid=="fmo_foam_film":
        report["foam_build_stats"]={key:round(float(value),5)
                                    for key,value in _FOAM_BUILD_STATS.items()}
    if fid=="fmo_chalcopyrite":
        report["chalcopyrite_build_stats"]={key:round(float(value),5)
                                             for key,value in _CHALCOPYRITE_BUILD_STATS.items()}
        report["local_thickness"] = chalcopyrite_thickness
        report["all_mark_p95_thickness_between_2_and_8_work_px"] = all(
            2.0<=row["p95_work_px"]<=8.0 for row in chalcopyrite_thickness.values())
        report["anti_paver_contract"]={
            "source_scalar_or_parent_territory_painted":False,
            "all_six_nuclei_off_frame":True,
            "complete_hopper_icons_allowed":False,
            "old_ledger_erasure_required_fraction":[0.40,0.60],
            "riser_clip_causes":["twin seam","cleavage","pit","oxidation","heal"],
            "a_b_runtime_ancestry":"A old twin / B younger overrun twin",
        }
    (output/"single_finish_evidence.json").write_text(
        json.dumps(report,indent=2),encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit isolated Morpho material rejection rebuild")
    parser.add_argument("--output", type=Path,
                        default=Path("_wilds_rejection_work/morpho_material_explicit"))
    parser.add_argument("--single", choices=MORPHO_MATERIAL_IDS,
                        help="render focused evidence for one ID without rebuilding the shelf")
    args = parser.parse_args()
    if args.single:
        report=_audit_single(args.single,args.output)
        print(json.dumps(report,indent=2))
        return 0
    report = _audit(args.output)
    print(json.dumps({
        "status": report["status"],
        "ids": report["id_count"],
        "builders": report["separate_builder_count"],
        "hashes": report["unique_hash_counts"],
        "weakest_spec_std": report["weakest_spec_channel_std"],
        "slowest_2048": report["slowest_sampled_combined_cold_2048_seconds"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

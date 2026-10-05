"""Firefly Lantern I2 — three-layer photogenic organ architecture.

IRIDESCENT INSECTS tick 31 / owner identity law 2026-09-01.
Identity contract: connected organ paths carry three physically ordered fine
families: 8–20px jagged cuticle extraction prisms, a translucent cross-linked
photogenic net, and an opaque reflector sheet containing attached 9–18px radial
urate spherulites.  Transverse tracheae, twigs, end bulbs, hollow reflector
vesicles and dark shell sutures provide six further named marks.  Spherulites
may never float as dots; no generic glow blobs, random particles, honeycomb,
Click Beetle bead-routes, broad light bands or palette variants are allowed.
M/R/Cc states derive from prism face, photogenic rail, reflector needle,
tracheal wall, bulb, vesicle and shell suture.

Research: Goh et al. 2013 found a translucent net-like photogenic layer above
an opaque reflector layer densely packed with ~700nm uric-acid spherulites,
including hollow vesicles and larger edge granules with radial concentric
needle structure.  Kim et al. 2012/2015 describe the overlying jagged cuticle
as a light-extraction structure.  Photinus histology adds transverse tracheae,
tracheal twigs, end cells and bulbs between photogenic cells.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

GEN = 660


def _hw(shape): return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape); a = np.asarray(a, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    a = np.clip(mask * pm * .97, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(colour, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0xF1FE31)
    h = w = GEN
    cuticle = np.zeros((h, w), np.float32)
    prism = np.zeros_like(cuticle)
    photo = np.zeros_like(cuticle)
    cross = np.zeros_like(cuticle)
    reflector = np.zeros_like(cuticle)
    crystal = np.zeros_like(cuticle)
    vesicle = np.zeros_like(cuticle)
    trachea = np.zeros_like(cuticle)
    twig = np.zeros_like(cuticle)
    bulb = np.zeros_like(cuticle)
    suture = np.zeros_like(cuticle)

    # Complete dark shell carrier: compact overlapping tergite chips remain
    # subordinate but ensure no region is empty on a 2048² whole-car canvas.
    for row, y0 in enumerate(np.arange(-3, h + 4, 7.0)):
        for x0 in np.arange(-3, w + 4, 7.6):
            cx, cy = x0 + rng.uniform(-1.7, 1.7), y0 + rng.uniform(-1.5, 1.5)
            a = (-.24 if row % 2 else .18) + rng.uniform(-.10, .10)
            ux, uy = np.cos(a), np.sin(a); nx, ny = -uy, ux
            ln, hh = rng.uniform(3.0, 5.4), rng.uniform(1.2, 2.2)
            pts = np.asarray([(round(cx - ln * ux), round(cy - ln * uy)),
                              (round(cx + hh * nx), round(cy + hh * ny)),
                              (round(cx + ln * ux), round(cy + ln * uy)),
                              (round(cx - hh * nx), round(cy - hh * ny))], np.int32)
            cv2.fillConvexPoly(cuticle, pts, float(rng.uniform(.25, .72)), cv2.LINE_AA)
            if rng.random() < .18:
                cv2.line(suture, tuple(pts[0]), tuple(pts[2]), float(rng.uniform(.28, .78)), 1, cv2.LINE_AA)

    # Connected organ paths.  Control polylines are invisible; all visible
    # geometry is assembled from compact prisms, crosslinks and attached crystals.
    # P2 shortens and densifies the organ paths so the three-layer material
    # reads as a continuous lantern tissue rather than sparse illuminated wire.
    for lane in range(46):
        x, y = float(rng.integers(-25, w + 25)), float(rng.integers(-25, h + 25))
        angle = rng.choice(np.array([-.75, -.30, .12, .42, .82, 1.30, -1.30]))
        points = [(x, y)]
        for _ in range(rng.integers(3, 7)):
            angle += rng.uniform(-.46, .46); ln = rng.uniform(18.0, 37.0)
            x += ln * np.cos(angle); y += ln * np.sin(angle); points.append((x, y))
        for p0, p1 in zip(points, points[1:]):
            x0, y0 = p0; x1, y1 = p1
            dx, dy = x1 - x0, y1 - y0; length = max(np.hypot(dx, dy), 1.0)
            ux, uy = dx / length, dy / length; nx, ny = -uy, ux
            # A faint 9–15px native photogenic sheet sits under the two rails;
            # crosslinks remain individually visible within that tissue.
            cv2.line(photo, (round(x0), round(y0)), (round(x1), round(y1)),
                     float(rng.uniform(.14, .34)), int(rng.integers(3, 5)), cv2.LINE_AA)
            # Photogenic rails and 8–24px crosslinks form a translucent net.
            for side in (-1, 1):
                off = side * 2.5
                cv2.line(photo, (round(x0 + off * nx), round(y0 + off * ny)),
                         (round(x1 + off * nx), round(y1 + off * ny)),
                         float(rng.uniform(.26, .70)), 1, cv2.LINE_AA)
            for dist in np.arange(rng.uniform(1, 6), length, rng.uniform(4.0, 7.0)):
                cx, cy = x0 + dist * ux, y0 + dist * uy
                cv2.line(cross, (round(cx - 2.8 * nx), round(cy - 2.8 * ny)),
                         (round(cx + 2.8 * nx), round(cy + 2.8 * ny)),
                         float(rng.uniform(.30, .88)), 1, cv2.LINE_AA)

                # Jagged extraction prism sits on the cuticle side.
                if rng.random() < .72:
                    base = cx + 5.3 * nx, cy + 5.3 * ny
                    plen = rng.uniform(2.8, 5.2); ph = rng.uniform(2.2, 4.5)
                    tri = np.asarray([(round(base[0] - plen * ux), round(base[1] - plen * uy)),
                                      (round(base[0] + plen * ux), round(base[1] + plen * uy)),
                                      (round(base[0] + ph * nx), round(base[1] + ph * ny))], np.int32)
                    cv2.fillConvexPoly(prism, tri, float(rng.uniform(.38, 1.0)), cv2.LINE_AA)

                # Reflector sheet and radial urate spherulite stay attached to
                # the opposite side of the same photogenic crosslink.
                rcx, rcy = cx - 5.3 * nx, cy - 5.3 * ny
                cv2.line(reflector, (round(rcx - 2.6 * ux), round(rcy - 2.6 * uy)),
                         (round(rcx + 2.6 * ux), round(rcy + 2.6 * uy)),
                         float(rng.uniform(.30, .82)), 2, cv2.LINE_AA)
                if rng.random() < .66:
                    radius = rng.uniform(2.4, 4.2)
                    for spoke in range(rng.integers(5, 9)):
                        aa = spoke * 2 * np.pi / 7 + rng.uniform(-.10, .10)
                        cv2.line(crystal, (round(rcx), round(rcy)),
                                 (round(rcx + radius * np.cos(aa)), round(rcy + radius * np.sin(aa))),
                                 float(rng.uniform(.30, .95)), 1, cv2.LINE_AA)
                    if rng.random() < .16:
                        cv2.ellipse(vesicle, (round(rcx), round(rcy)),
                                    (round(radius + 1), round(radius + 1)), 0, 0, 360,
                                    float(rng.uniform(.35, .90)), 1, cv2.LINE_AA)

            # Transverse trachea branches from the organ path, ending in bulbs.
            if rng.random() < .74:
                dist = rng.uniform(.25, .75) * length; cx, cy = x0 + dist * ux, y0 + dist * uy
                side = rng.choice([-1, 1]); tl = rng.uniform(8.0, 17.0)
                ex, ey = cx + side * tl * nx, cy + side * tl * ny
                cv2.line(trachea, (round(cx), round(cy)), (round(ex), round(ey)),
                         float(rng.uniform(.40, .96)), 1, cv2.LINE_AA)
                for branch in (-1, 1):
                    ba = np.arctan2(side * ny, side * nx) + branch * rng.uniform(.42, .72)
                    bl = rng.uniform(3.2, 6.5)
                    bx, by = ex + bl * np.cos(ba), ey + bl * np.sin(ba)
                    cv2.line(twig, (round(ex), round(ey)), (round(bx), round(by)),
                             float(rng.uniform(.32, .86)), 1, cv2.LINE_AA)
                    cv2.ellipse(bulb, (round(bx), round(by)), (2, 1), np.degrees(ba), 0, 360,
                                float(rng.uniform(.38, .94)), -1, cv2.LINE_AA)

    # P3 rejects P1/P2's sparse path/noodle silhouette and rebuilds the visible
    # organ as a complete nonperiodic mosaic of ordered three-layer modules.
    for a in (prism, photo, cross, reflector, crystal, vesicle, trachea, twig, bulb):
        a.fill(0)
    step_y = 12.2
    for row, y0 in enumerate(np.arange(-4, h + 5, step_y)):
        step_x = rng.uniform(12.0, 15.5)
        x0 = -5.0 + (step_x * .48 if row % 2 else 0)
        for cx0 in np.arange(x0, w + 6, step_x):
            cx = float(cx0 + rng.uniform(-2.0, 2.0)); cy = float(y0 + rng.uniform(-1.8, 1.8))
            field = .55 * np.sin(cx / 73.0 + cy / 109.0) + .45 * np.cos(cy / 61.0 - cx / 131.0)
            angle = .75 * field + rng.uniform(-.22, .22)
            active = float(np.clip(.18 + .66 * (.5 + .5 * np.sin(cx / 57.0 - cy / 83.0 + field)) +
                                   rng.normal(0, .14), .14, 1.0))
            ux, uy = np.cos(angle), np.sin(angle); nx, ny = -uy, ux
            span = rng.uniform(2.8, 5.0)

            # Ordered layer 1: asymmetric cuticle extraction prism.
            pcx, pcy = cx + 3.6 * nx, cy + 3.6 * ny
            tri = np.asarray([(round(pcx - span * ux), round(pcy - span * uy)),
                              (round(pcx + span * ux), round(pcy + span * uy)),
                              (round(pcx + rng.uniform(2.1, 4.0) * nx),
                               round(pcy + rng.uniform(2.1, 4.0) * ny))], np.int32)
            cv2.fillConvexPoly(prism, tri, float(rng.uniform(.38, 1.0) * active), cv2.LINE_AA)

            # Ordered layer 2: a tiny photogenic double rail and cross-net.
            for side in (-1, 1):
                off = side * 1.5
                cv2.line(photo, (round(cx - span * ux + off * nx), round(cy - span * uy + off * ny)),
                         (round(cx + span * ux + off * nx), round(cy + span * uy + off * ny)),
                         float(rng.uniform(.30, .82) * active), 1, cv2.LINE_AA)
            for frac in (-.45, .15, .65):
                qx, qy = cx + frac * span * ux, cy + frac * span * uy
                cv2.line(cross, (round(qx - 1.6 * nx), round(qy - 1.6 * ny)),
                         (round(qx + 1.6 * nx), round(qy + 1.6 * ny)),
                         float(rng.uniform(.30, .88) * active), 1, cv2.LINE_AA)

            # Ordered layer 3: reflector plate plus attached radial spherulite.
            rcx, rcy = cx - 3.8 * nx, cy - 3.8 * ny
            cv2.line(reflector, (round(rcx - span * ux), round(rcy - span * uy)),
                     (round(rcx + span * ux), round(rcy + span * uy)),
                     float(rng.uniform(.38, .92) * active), 2, cv2.LINE_AA)
            radius = rng.uniform(2.1, 3.7)
            spoke_count = int(rng.integers(5, 9))
            for spoke in range(spoke_count):
                aa = angle + spoke * 2 * np.pi / spoke_count
                cv2.line(crystal, (round(rcx), round(rcy)),
                         (round(rcx + radius * np.cos(aa)), round(rcy + radius * np.sin(aa))),
                         float(rng.uniform(.30, .92) * active), 1, cv2.LINE_AA)
            if rng.random() < .13:
                cv2.ellipse(vesicle, (round(rcx), round(rcy)),
                            (round(radius + 1), round(radius + 1)), 0, 0, 360,
                            float(rng.uniform(.35, .86) * active), 1, cv2.LINE_AA)

            # Every few modules share an attached transverse tracheal twig.
            if rng.random() < .22:
                tx, ty = cx + rng.uniform(4.5, 7.5) * ux, cy + rng.uniform(4.5, 7.5) * uy
                cv2.line(trachea, (round(cx), round(cy)), (round(tx), round(ty)),
                         float(rng.uniform(.34, .90) * active), 1, cv2.LINE_AA)
                ba = angle + rng.choice([-1, 1]) * rng.uniform(.55, .90)
                bx, by = tx + 3.6 * np.cos(ba), ty + 3.6 * np.sin(ba)
                cv2.line(twig, (round(tx), round(ty)), (round(bx), round(by)),
                         float(rng.uniform(.30, .82) * active), 1, cv2.LINE_AA)
                cv2.ellipse(bulb, (round(bx), round(by)), (2, 1), np.degrees(ba), 0, 360,
                            float(rng.uniform(.38, .90) * active), -1, cv2.LINE_AA)

    arrays = (cuticle, prism, photo, cross, reflector, crystal, vesicle, trachea, twig, bulb, suture)
    return tuple(cv2.GaussianBlur(a, (0, 0), .17).astype(np.float32) for a in arrays)


def paint_firefly_glow_i2(paint, shape, mask, seed, pm, bb):
    cuticle, prism, photo, cross, reflector, crystal, vesicle, trachea, twig, bulb, suture = _surface(seed + 31037)
    col = np.zeros((*cuticle.shape, 3), np.float32)
    col[:] = np.array([.012, .024, .018], np.float32)
    col += cuticle[..., None] * np.array([.055, .16, .11], np.float32) * .96
    col += prism[..., None] * np.array([.48, 1.00, .12], np.float32) * .86
    col += photo[..., None] * np.array([.18, .92, .32], np.float32) * .72
    col += cross[..., None] * np.array([.48, 1.00, .28], np.float32) * .78
    col += reflector[..., None] * np.array([.68, .74, .42], np.float32) * .42
    col += crystal[..., None] * np.array([.88, .86, .46], np.float32) * .48
    col += vesicle[..., None] * np.array([.32, .72, .55], np.float32) * .64
    col += trachea[..., None] * np.array([.84, .45, .08], np.float32) * .67
    col += twig[..., None] * np.array([.53, .31, .08], np.float32) * .58
    col += bulb[..., None] * np.array([1.00, .72, .15], np.float32) * .82
    col += suture[..., None] * np.array([.025, .045, .038], np.float32) * .88
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_firefly_glow_i2(shape, seed, sm, base_m, base_r):
    cuticle, prism, photo, cross, reflector, crystal, vesicle, trachea, twig, bulb, suture = _surface(seed + 31037)
    m = 7 + 238 * (.30 * reflector + .24 * crystal + .17 * prism +
                   .12 * bulb + .09 * trachea + .08 * suture)
    r = 14 + 224 * (.28 * cuticle + .22 * suture + .17 * twig +
                    .13 * photo + .11 * vesicle + .09 * cross)
    cc = 5 + 244 * (.29 * prism + .22 * photo + .17 * cross +
                    .13 * vesicle + .11 * bulb + .08 * crystal)
    m += crystal * 36 + reflector * 27 - photo * 17
    r += suture * 31 + twig * 22 - prism * 25 - bulb * 18
    cc += prism * 34 + photo * 26 + bulb * 20 - cuticle * 13

    def spread(a, lo, hi):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        return np.clip(lo + (a - p1) * ((hi - lo) / max(float(p99 - p1), 1e-5)), lo, hi)

    return (np.clip(_resize(spread(m, 4, 250) * sm, shape), 4, 250),
            np.clip(_resize(spread(r, 7, 247), shape), 7, 247),
            np.clip(_resize(spread(cc, 2, 252), shape), 2, 252))

"""[SPB-REV-SEAM 2026-10-10] Edge Bleed: extend paint AND spec a few pixels past every UV-island edge, at render time.

WHY. An iRacing paint is a 2048 sheet with the car cut into UV islands. The sim filters and mip-maps the sheet, so a texel at a panel rim
is a blend that reaches into the unused gutter, more and more at distance (mip n reaches 2^n - 1 px outside the rim). Whatever the
gutter holds (the catch-all zone's paint, a different spec) leaks into the rim as a thin line: a chrome edge dulled by gutter spec, a dark
art edge rimmed with base colour. Painters fix it by hand by "bleeding" paint past every edge. This does it for paint and spec in one pass.

WHAT. Given the island mask (client-built from the car's Wire template, js/rev/seam/seam.js) every gutter pixel within ``px`` pixels of an
island takes the value of its NEAREST island pixel (Euclidean nearest, all channels together: paint R,G,B and spec M,R,CC,A). The source is
the island's core (its rim band of ~2 px, the template outline, is skipped as a source: zones often leave those px in the catch-all colour).
Island pixels are never written (0 px changed inside islands) and a gutter pixel only ever copies from an island, so one island's art
never lands on another island; gutter further than ``px`` (+ the 2 px band) from every island is left as it was.

CONTRACT.
- Optional + additive: no ``edge_bleed`` request (or env ``SPB_REV_SEAM_OFF=1``) = every output byte-identical to before.
- The nearest-island map is cached per (mask, px, sheet size): the first render of a car pays the distance transform (4 strips in parallel),
  later renders only one cv2.remap per sheet.
- Never raises into the render: any problem logs a warning and the sheet is written as it was.
"""
from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import threading
import time
from collections import OrderedDict

import numpy as np

logger = logging.getLogger("engine.rev_seam_bleed")

VER = "seam1.1"
DEFAULT_PX = 16
MAX_PX = 64
_CACHE_MAX = 3
_PLAN_LOCK = threading.Lock()
_PLANS: "OrderedDict[tuple, dict]" = OrderedDict()
_INFLIGHT: dict = {}
_IDENT: dict = {}                                       # shape -> identity (x, y) int16 map; copied per plan (a copy is 5 ms, building it 25 ms)


def _off() -> bool:
    return str(os.environ.get("SPB_REV_SEAM_OFF", "")).strip() not in ("", "0", "false", "False")


def enabled() -> bool:
    return not _off()


# ---------------------------------------------------------------------------------------------------------------- request
def normalize_request(raw) -> dict | None:
    """Server-side validation of the optional ``edge_bleed`` render field (cheap: the PNG is only decoded on a plan-cache miss).
    ``{"on": true, "px": 16, "mask_png": "<base64 PNG, island = white>", "ver": "seam1.0"}`` -> {"px", "b64", "key"} or None."""
    if _off() or not isinstance(raw, dict) or not raw.get("on", True):
        return None
    try:
        px = int(raw.get("px", DEFAULT_PX))
    except Exception:
        px = DEFAULT_PX
    px = max(1, min(MAX_PX, px))
    b64 = raw.get("mask_png")
    if not isinstance(b64, str) or not b64:
        logger.warning("edge_bleed: no mask_png in the request; skipped")
        return None
    if "," in b64[:64]:                       # data: URL
        b64 = b64.split(",", 1)[1]
    if len(b64) > 12_000_000:
        logger.warning("edge_bleed: mask_png too large; skipped")
        return None
    return {"px": px, "b64": b64, "key": hashlib.blake2b(b64.encode("ascii", "ignore"), digest_size=12).hexdigest()}


def _decode_mask(b64: str, shape) -> np.ndarray:
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(b64)))
    if im.width > 8192 or im.height > 8192:
        raise ValueError("mask too large")
    im = im.convert("L")
    if (im.height, im.width) != tuple(shape):          # the page sizes the mask 2048; resample once (nearest) if the sheet differs
        im = im.resize((shape[1], shape[0]), Image.NEAREST)
    return np.asarray(im) > 127


# ---------------------------------------------------------------------------------------------------------------- plan
BAND = 2                                                # px of a panel's rim that are NOT used as bleed source (see _build_plan)


def _strip(src_u8, srcb, prot, m16, a, b, halo, lim):
    """Nearest-source pixel for every gutter pixel within lim of a source, rows [a, b); writes (x, y) of that source into the int16 map.
    srcb = source pixels (island core), prot = whole island (never written)."""
    import cv2
    h, w = src_u8.shape
    r0, r1 = max(0, a - halo), min(h, b + halo)
    dist, lab = cv2.distanceTransformWithLabels(src_u8[r0:r1], cv2.DIST_L2, cv2.DIST_MASK_PRECISE, labelType=cv2.DIST_LABEL_PIXEL)
    pts = np.flatnonzero(srcb[r0:r1].ravel())                # raster order of the source (zero) pixels = label order (1-based)
    c0, c1 = a - r0, b - r0
    d, lb = dist[c0:c1], lab[c0:c1]
    ys, xs = np.nonzero((d > 0) & (d <= lim + 1e-3) & (lb > 0) & ~prot[a:b])
    if ys.size == 0:
        return 0
    loc = pts[lb[ys, xs] - 1]
    sy = (loc // w) + r0
    sx = loc % w
    gy = ys + a
    keep = (sy - gy) ** 2 + (sx - xs) ** 2 <= lim * lim   # bled only when its source really is within lim (cv2's label can be <1 px off)
    ys_k, xs_k = gy[keep], xs[keep]
    m16[ys_k, xs_k, 0] = sx[keep]
    m16[ys_k, xs_k, 1] = sy[keep]
    return int(keep.sum())


def _build_plan(mask: np.ndarray, px: int) -> dict:
    t0 = time.perf_counter()
    h, w = mask.shape
    ident = _IDENT.get((h, w))                                # identity map (every pixel copies itself) ...
    if ident is None:
        ident = np.empty((h, w, 2), np.int16)
        ident[..., 0] = np.arange(w, dtype=np.int16)[None, :]
        ident[..., 1] = np.arange(h, dtype=np.int16)[:, None]
        _IDENT[(h, w)] = ident
    m16 = ident.copy()
    ring = 0
    if mask.any() and not mask.all():
        # SOURCE = the island CORE, not its outermost BAND px: those are the template's outline pixels, which the zone regions often do not
        # cover (a chrome hood whose last 1-2 px read as the catch-all body colour). Copying that rim outward would re-create the seam, so
        # gutter pixels copy the nearest CORE pixel instead. The band itself is still never written (island = 0 px changed). Slivers too
        # narrow to have a core (<= ~2*BAND px wide) stay sources themselves. Reach is measured from the core, hence px + BAND.
        import cv2
        k3 = np.ones((3, 3), np.uint8)
        m8 = np.ascontiguousarray(mask.astype(np.uint8))
        core = cv2.erode(m8, k3, iterations=BAND).astype(bool)
        lost = mask & ~cv2.dilate(core.astype(np.uint8), k3, iterations=BAND).astype(bool)
        srcb = np.ascontiguousarray(core | lost)
        src = np.ascontiguousarray((~srcb).astype(np.uint8))  # zero = source (distance source)
        lim = px + BAND
        halo = lim + 3
        nth = max(1, min(4, (os.cpu_count() or 2)))
        cuts = np.linspace(0, h, nth + 1).astype(int)
        jobs = [(int(cuts[i]), int(cuts[i + 1])) for i in range(nth) if cuts[i + 1] > cuts[i]]
        if len(jobs) == 1:
            ring = _strip(src, srcb, mask, m16, 0, h, halo, lim)
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
                ring = sum(ex.map(lambda ab: _strip(src, srcb, mask, m16, ab[0], ab[1], halo, lim), jobs))
    # ... and every gutter pixel within px of an island points at its nearest island pixel. cv2.remap(INTER_NEAREST) then applies it to any 3/4-channel sheet.
    return {"map": m16, "ring": int(ring), "shape": (h, w), "px": px, "build_ms": (time.perf_counter() - t0) * 1000.0}


def get_plan(req: dict, shape) -> tuple[dict, bool]:
    """(plan, built_here). One build per key even when prewarm() and the render ask at the same time."""
    key = (req["key"], req["px"], tuple(shape))
    with _PLAN_LOCK:
        p = _PLANS.get(key)
        if p is not None:
            _PLANS.move_to_end(key)
            return p, False
        ev = _INFLIGHT.get(key)
        mine = ev is None
        if mine:
            ev = _INFLIGHT[key] = threading.Event()
    if not mine:                                         # prewarm() is building it: wait for that instead of building twice
        ev.wait(120)
        with _PLAN_LOCK:
            p = _PLANS.get(key)
        if p is not None:
            return p, False
    try:
        p = _build_plan(_decode_mask(req["b64"], shape), req["px"])
        with _PLAN_LOCK:
            _PLANS[key] = p
            while len(_PLANS) > _CACHE_MAX:
                _PLANS.popitem(last=False)
    finally:
        if mine:
            with _PLAN_LOCK:
                _INFLIGHT.pop(key, None)
            ev.set()
    return p, True


def prewarm(req: dict, shape=(2048, 2048)) -> None:
    """Start building the nearest-island map in the background at the START of a render request, so the (seconds-long) zone render hides it."""
    def _run():
        try:
            get_plan(req, shape)
        except Exception as e:                           # noqa: BLE001
            logger.warning("Edge Bleed prewarm failed: %s", e)
    threading.Thread(target=_run, name="spb-seam-prewarm", daemon=True).start()


# ---------------------------------------------------------------------------------------------------------------- apply
def bleed(arr: np.ndarray, plan: dict) -> np.ndarray:
    """Return ``arr`` (H,W,C uint8, C = 3 or 4) with the planned gutter pixels copied from their nearest island pixel (a new array; the input is not touched)."""
    if arr is None or plan["ring"] == 0 or arr.shape[:2] != plan["shape"]:
        return arr
    import cv2
    return cv2.remap(np.ascontiguousarray(arr), plan["map"], None, cv2.INTER_NEAREST)


def apply_to_pipeline_results(results: dict, output_dir: str, iracing_id, car_prefix: str, req: dict, write24, write32) -> dict:
    """Post-step of full_render_pipeline (after wear + night variants, before the ZIP): bleed the car paint + spec (+ night spec) and rewrite their TGAs.
    Returns a small stats dict for the render response. Never raises."""
    st = {"applied": False, "ver": VER}
    try:
        if _off() or not req:
            return st
        t0 = time.perf_counter()
        paint = results.get("car_paint")
        spec = results.get("car_spec")
        if paint is None and spec is None:
            st["reason"] = "no car arrays"
            return st
        ref = paint if paint is not None else spec
        plan, cold = get_plan(req, ref.shape[:2])
        t1 = time.perf_counter()
        tb = tw = 0.0                                   # bleed compute vs TGA rewrite (disk) time, reported separately
        if paint is not None:
            ta = time.perf_counter(); results["car_paint"] = bleed(paint, plan); tb += time.perf_counter() - ta
            ta = time.perf_counter()
            write24(os.path.join(output_dir, f"{car_prefix}_{iracing_id}.tga"), results["car_paint"])
            # the wear step historically writes car_num_<id>.tga: keep that file in step when a different prefix is in use
            alt = os.path.join(output_dir, f"car_num_{iracing_id}.tga")
            if car_prefix != "car_num" and os.path.exists(alt):
                write24(alt, results["car_paint"])
            tw += time.perf_counter() - ta
        if spec is not None:
            ta = time.perf_counter(); results["car_spec"] = bleed(spec, plan); tb += time.perf_counter() - ta
            ta = time.perf_counter(); write32(os.path.join(output_dir, f"car_spec_{iracing_id}.tga"), results["car_spec"]); tw += time.perf_counter() - ta
        nspec = results.get("car_spec_night")
        if nspec is not None:
            ta = time.perf_counter(); results["car_spec_night"] = bleed(nspec, plan); tb += time.perf_counter() - ta
            ta = time.perf_counter(); write32(os.path.join(output_dir, f"car_spec_night_{iracing_id}.tga"), results["car_spec_night"]); tw += time.perf_counter() - ta
        t2 = time.perf_counter()
        st.update({"applied": True, "px": plan["px"], "ring_px": plan["ring"], "cold": bool(cold),
                   "plan_ms": round((t1 - t0) * 1000, 1), "apply_ms": round((t2 - t1) * 1000, 1), "bleed_ms": round(tb * 1000, 1), "write_ms": round(tw * 1000, 1),
                   "build_ms": round(plan["build_ms"], 1)})
        logger.info("  Edge Bleed %s: %d px ring (%d px) plan %.0f ms (%s) bleed %.0f ms + TGA rewrite %.0f ms", VER, plan["ring"], plan["px"], st["plan_ms"], "cold" if cold else "cached", st["bleed_ms"], st["write_ms"])
    except Exception as e:                    # noqa: BLE001
        logger.warning("Edge Bleed failed, sheet left as rendered: %s", e)
        st["reason"] = "error: %s" % str(e)[:120]
    return st


# ---------------------------------------------------------------------------------------------------------------- reference island finder (tests / tools)
def island_mask_from_wire(wire_rgba: np.ndarray, mask_alpha: np.ndarray | None = None, grow: int = 1) -> np.ndarray:
    """Python reference of js/rev/seam/seam.js: islands = regions enclosed by the Wire template's pure-green (1,255,0) outline, minus the Mask
    layer's unused holes (brown >= 50%) and the big exterior component. Used by the measurement scripts and the JS parity test."""
    from scipy import ndimage as ndi
    a = wire_rgba[..., 3] > 16
    green = a & (wire_rgba[..., 0] < 128) & (wire_rgba[..., 1] > 200)
    m = (mask_alpha > 128) if mask_alpha is not None else np.zeros(a.shape, bool)
    barrier = ndi.binary_dilation(green, structure=np.ones((3, 3), bool), iterations=grow) if grow else green
    lab, n = ndi.label(~barrier)
    area = np.bincount(lab.ravel(), minlength=n + 1)
    brown = np.bincount(lab.ravel(), weights=m.ravel().astype(np.float64), minlength=n + 1)
    touches = np.zeros(n + 1, bool)
    for e in (lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]):
        touches[np.unique(e)] = True
    big = int(np.argmax(area[1:]) + 1)
    isl = np.zeros(n + 1, bool)
    for k in range(1, n + 1):
        if k == big or touches[k] or area[k] < 30 or brown[k] / max(area[k], 1) >= 0.5:
            continue
        isl[k] = True
    inner = isl[lab]
    return inner | (barrier & ndi.binary_dilation(inner, structure=np.ones((3, 3), bool), iterations=grow + 1))

"""SMART livery separation (2026-06-26) — OCR-driven NUMBERS / SPONSORS / PAINT.

The classic contrast-based detector (separate_livery_layers) can't tell a bold paint
graphic from a decal, and can't tell a number from a sponsor wordmark. This module READS
the livery with EasyOCR: short digit groups -> NUMBERS, words/wordmarks -> SPONSORS, and
everything the text+logo detectors don't claim stays PAINT. Tight glyph masks (Otsu within
each OCR box) keep the masks on the actual letterforms, not bounding boxes.

ADDITIVE: separate_livery_layers stays untouched; this is a smarter alternative the route
selects (with graceful fallback if OCR is unavailable). Returns the same contract:
{"numbers","sponsors","paint"} uint8 (255 = member), full input resolution.
"""
from __future__ import annotations
import os
import re
import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

_OCR_READER = None
_OCR_FAILED = False


def _reader():
    """Lazy, cached EasyOCR reader (CPU). Init ~2s once, then reused for the session."""
    global _OCR_READER, _OCR_FAILED
    if _OCR_READER is not None:
        return _OCR_READER
    if _OCR_FAILED:
        return None
    try:
        import easyocr
        _OCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)
    except Exception:
        _OCR_FAILED = True
        _OCR_READER = None
    return _OCR_READER


def ocr_available():
    return _reader() is not None


def _to_u8(tex):
    a = np.asarray(tex)
    if a.dtype != np.uint8:
        a = np.clip(a[:, :, :3] if a.ndim == 3 else a, 0.0, 1.0)
        a = (a * 255.0).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return np.ascontiguousarray(a[:, :, :3])


def _restore_ocr_poly(poly, rot, rotated_shape, work_shape, mirrored=False):
    """Map a polygon from a rotated/reflected OCR view back to the work image.

    A backwards word stays backwards through every 90-degree rotation, so
    reflected UV islands need an explicit mirror pass before OCR.
    """
    restored = np.asarray(poly, np.float32).copy()
    rh, rw = [int(v) for v in rotated_shape[:2]]
    _work_h, work_w = [int(v) for v in work_shape[:2]]
    if rot == 2:
        restored = np.stack([rw - 1 - restored[:, 0], rh - 1 - restored[:, 1]], axis=1)
    elif rot == 1:
        restored = np.stack([rh - 1 - restored[:, 1], restored[:, 0]], axis=1)
    elif rot == 3:
        restored = np.stack([restored[:, 1], rw - 1 - restored[:, 0]], axis=1)
    if mirrored:
        restored[:, 0] = work_w - 1 - restored[:, 0]
    return restored


def _mirror_ocr_enabled(value=None):
    if value is not None:
        return bool(value)
    return os.environ.get("SPB_SMART_TGA_MIRROR_OCR", "1").strip().lower() not in {
        "0", "false", "no", "off",
    }


def _ocr_boxes(rgb_u8, min_conf=0.30, rotations=(0, 2), mirror_ocr=None):
    """OCR across rotations and optional reflected UV views.

    Mirror OCR defaults on and can be reverted with
    ``SPB_SMART_TGA_MIRROR_OCR=0``.
    """
    reader = _reader()
    if reader is None:
        return []
    H0, W0 = rgb_u8.shape[:2]
    out = []
    # MULTI-SCALE (2026-06-26 layer-review fix): EasyOCR's text detector has a SIZE sweet spot — a
    # BIG door/roof car number is MISSED at high res (too large for the detector) while SMALL
    # contingency text is missed at low res. So run a BIG pass (~1280 long side: small text + vertical
    # sponsors, all rotations) AND a SMALL pass (~700: the big car numbers, upright/180 only). This is
    # what makes the NUMBERS layer actually fire (the '17'/'55' door numbers).
    upr = tuple(r for r in rotations if r in (0, 2)) or (0,)
    passes = [(1280, tuple(rotations)), (700, upr)]
    for target, rots in passes:
        sc = target / max(H0, W0)
        if abs(sc - 1.0) > 0.01:
            interp = cv2.INTER_AREA if sc < 1.0 else cv2.INTER_LANCZOS4
            work = cv2.resize(rgb_u8, (max(1, int(W0 * sc)), max(1, int(H0 * sc))), interpolation=interp)
        else:
            work = rgb_u8
        mirror_views = (False, True) if _mirror_ocr_enabled(mirror_ocr) else (False,)
        for mirrored in mirror_views:
            base = np.ascontiguousarray(np.fliplr(work)) if mirrored else work
            for rot in rots:
                img = np.ascontiguousarray(np.rot90(base, rot)) if rot else base
                try:
                    res = reader.readtext(img, detail=1, paragraph=False)
                except Exception:
                    continue
                for box, txt, conf in res:
                    t = (txt or "").strip()
                    if conf < min_conf or not t:
                        continue
                    poly = _restore_ocr_poly(
                        box, rot, img.shape, work.shape, mirrored=mirrored
                    ) / sc
                    xs, ys = poly[:, 0], poly[:, 1]
                    out.append({
                        "poly": poly, "text": t, "conf": float(conf),
                        "h": float(ys.max() - ys.min()), "w": float(xs.max() - xs.min()),
                        "cx": float(xs.mean()), "cy": float(ys.mean()),
                        "rotation": int(rot), "mirrored": bool(mirrored),
                        "seen_mirrored": bool(mirrored),
                        "seen_unmirrored": not bool(mirrored),
                    })
    return out


def _dedup(boxes, iou_thr=0.55):
    """Drop near-duplicate boxes from the multi-rotation passes (keep higher conf)."""
    def bbox(b):
        p = b["poly"]; return (p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max())
    kept = []
    for b in sorted(boxes, key=lambda b: -b["conf"]):
        bx = bbox(b); drop = False
        for k in kept:
            kx = bbox(k)
            ix0, iy0 = max(bx[0], kx[0]), max(bx[1], kx[1])
            ix1, iy1 = min(bx[2], kx[2]), min(bx[3], kx[3])
            iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
            inter = iw * ih
            a1 = (bx[2] - bx[0]) * (bx[3] - bx[1]); a2 = (kx[2] - kx[0]) * (kx[3] - kx[1])
            if inter / max(1.0, min(a1, a2)) > iou_thr:
                k["seen_mirrored"] = bool(k.get("seen_mirrored")) or bool(b.get("seen_mirrored"))
                k["seen_unmirrored"] = bool(k.get("seen_unmirrored")) or bool(b.get("seen_unmirrored"))
                drop = True; break
        if not drop:
            kept.append(b)
    return kept


def _box_overlap_min(a, b):
    ap = a["poly"]; bp = b["poly"]
    ax0, ay0, ax1, ay1 = ap[:, 0].min(), ap[:, 1].min(), ap[:, 0].max(), ap[:, 1].max()
    bx0, by0, bx1, by1 = bp[:, 0].min(), bp[:, 1].min(), bp[:, 0].max(), bp[:, 1].max()
    iw = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    ih = max(0.0, min(ay1, by1) - max(ay0, by0))
    area_a = max(1.0, (ax1 - ax0) * (ay1 - ay0))
    area_b = max(1.0, (bx1 - bx0) * (by1 - by0))
    return float(iw * ih / min(area_a, area_b))


_NUMLIKE = re.compile(r'^[0-9OoIlSsB]{1,3}$')  # tolerate common OCR digit confusions


def _classify(boxes, H, W):
    """Digit-dominant + prominent -> NUMBER; words/wordmarks -> SPONSOR; tiny digits -> sponsor."""
    for b in boxes:
        clean = re.sub(r'[^0-9A-Za-z]', '', b["text"])  # strip OCR punctuation noise: "55)" -> "55"
        digits = sum(c.isdigit() for c in clean)
        alpha = sum(c.isalpha() for c in clean)
        # NUMBER = short, digit-DOMINANT (tolerate one stray OCR letter, e.g. "552" mis-read of 55,
        # "B12", "55"). The exact value need not be right — for the LAYER what matters is that a big
        # door/roof digit-glyph region routes to NUMBERS, not SPONSORS. (2026-06-26 lenient classify.)
        mirror_only = bool(b.get("seen_mirrored")) and not bool(b.get("seen_unmirrored"))
        b["mirror_only"] = mirror_only
        # A mirrored sponsor/logo can resemble a digit after reflection. Mirrored-only
        # evidence starts in Sponsors; later repeated-family logic may still promote a
        # genuine race number using whole-sheet siblings and palette/shape evidence.
        b["is_num"] = (
            not mirror_only
            and 1 <= digits <= 3
            and alpha <= 1
            and len(clean) <= 3
            and digits >= max(1, alpha)
        )
    num_boxes = [b for b in boxes if b["is_num"]]
    nums, spons = [], []
    if num_boxes:
        maxh = max(b["h"] for b in num_boxes)
        for b in num_boxes:
            # the car number is the PROMINENT digit group: a good fraction of the tallest, and big vs the car
            if b["h"] >= 0.45 * maxh and b["h"] >= 0.035 * H:
                nums.append(b)
            else:
                spons.append(b)  # small digits = part of a logo / phone / class -> sponsor bucket
    spons.extend(b for b in boxes if not b["is_num"])
    return nums, spons


def _proposals_for_big_numbers(rgb_u8, work=1024):
    """SHAPE stage of the big-number rescue: MSER finds large ISOLATED glyph-like blobs (both
    polarities) the global OCR passes miss when a door/roof number is too large for the detector.
    Returns bboxes in FULL-res coords. Gate tuned on real NASCAR liveries (2026-06-27 harness):
    admit a big single-digit silhouette; EXCLUDE wordmarks (too wide), solid logo discs (extent
    too high), specks (too short). CANDIDATES ONLY — every one is digit-OCR-confirmed before use,
    so a stray panel/stripe that slips the gate is rejected downstream. Cheap (runs on a ~1024 gray)."""
    if cv2 is None:
        return []
    H0, W0 = rgb_u8.shape[:2]
    sc = work / float(max(H0, W0))
    if sc < 1.0:
        g = cv2.resize(cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY),
                       (max(1, int(W0 * sc)), max(1, int(H0 * sc))), interpolation=cv2.INTER_AREA)
    else:
        sc = 1.0
        g = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY)
    H, W = g.shape[:2]
    min_a, max_a = int(0.0015 * H * W), int(0.05 * H * W)
    regs = []
    for img in (g, 255 - g):
        try:
            mser = cv2.MSER_create()
            mser.setDelta(6); mser.setMinArea(min_a); mser.setMaxArea(max_a)
            r, _ = mser.detectRegions(img)
            regs.extend(r)
        except Exception:
            pass
    cands = []
    for pts in regs:
        x, y, w, h = cv2.boundingRect(pts)
        if w < 4 or h < 4:
            continue
        n = float(len(pts)); aspect = w / float(h); extent = n / float(w * h); hfrac = h / float(H)
        if not (0.10 <= hfrac <= 0.55):      # tall like a door number, not a speck/whole-panel
            continue
        if not (0.22 <= aspect <= 1.35):     # single-digit silhouette (wordmarks are wide)
            continue
        if not (0.18 <= extent <= 0.78):     # strokes, not a filled blob (logo discs ~>0.85)
            continue
        pad = max(3, int(0.02 * max(H, W)))
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
        contrast = abs(float(g[y:y + h, x:x + w].mean()) - float(g[y0:y1, x0:x1].mean()))
        if contrast < 34:                    # must stand out from its surroundings
            continue
        cands.append((w * h, (int(x / sc), int(y / sc), int(w / sc), int(h / sc))))
    cands.sort(key=lambda c: -c[0])
    kept = []
    for _, bb in cands:
        x, y, w, h = bb; ok = True
        for kx, ky, kw, kh in kept:
            ix0, iy0 = max(x, kx), max(y, ky)
            ix1, iy1 = min(x + w, kx + kw), min(y + h, ky + kh)
            iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
            if iw * ih > 0.4 * min(w * h, kw * kh):
                ok = False; break
        if ok:
            kept.append(bb)
    return kept[:6]


def _confirm_digit_crop(reader, rgb_u8, bbox, min_conf=0.45):
    """CONFIRM stage: re-OCR a single proposal crop at the detector's glyph sweet spot with a FREE
    read (NO allowlist) and accept ONLY a SHORT, PURELY-NUMERIC token. A digit-only allowlist is a
    trap — it forces bold sponsor LETTERS (O->0, I->1) to read as fake digits, which grabbed the
    'NATIONWIDE' wordmark (2026-06-27 real-livery review). Requiring a free read that is itself
    digit-dominant + alpha-free rejects wordmarks while still confirming a genuine door number that
    the global pass missed only because it was too big (crop-scale normalization). Returns (digits, conf)."""
    H0, W0 = rgb_u8.shape[:2]
    x, y, w, h = bbox
    pad = int(0.25 * h)
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W0, x + w + pad), min(H0, y + h + pad)
    crop = rgb_u8[y0:y1, x0:x1]
    if crop.shape[0] < 8 or crop.shape[1] < 8:
        return None
    s = min(max(96.0 / crop.shape[0], 0.12), 6.0)  # NORMALIZE glyph to ~96px tall: DOWN for a huge
    #                                                 door number (the case the global pass can't read
    #                                                 because it's too big), UP for a small one
    up = cv2.resize(crop, (max(1, int(crop.shape[1] * s)), max(1, int(crop.shape[0] * s))),
                    interpolation=cv2.INTER_CUBIC)
    best = None
    for img in (up, np.ascontiguousarray(np.rot90(up, 2))):
        try:
            res = reader.readtext(img, detail=1, paragraph=False)   # FREE read — no allowlist
        except Exception:
            continue
        for box, txt, conf in res:
            clean = re.sub(r'[^0-9A-Za-z]', '', txt or '')
            digits = sum(c.isdigit() for c in clean)
            alpha = sum(c.isalpha() for c in clean)
            # SHORT + PURELY NUMERIC only: a door number reads as "25"/"3"; a wordmark fails alpha==0
            if conf >= min_conf and 1 <= len(clean) <= 3 and digits >= 1 and alpha == 0:
                if best is None or conf > best[1]:
                    best = (clean, float(conf))
    return best


def _big_number_rescue(rgb_u8, existing_boxes, H, W, min_conf=0.30):
    """Shape-propose large isolated glyph blobs the global OCR passes missed, skip any already
    claimed by an OCR box, then DIGIT-OCR-confirm each. Returns NUMBER box-dicts (<=2). Additive."""
    reader = _reader()
    if reader is None or cv2 is None:
        return []
    claimed = np.zeros((H, W), np.uint8)
    for b in existing_boxes:
        try:
            cv2.fillConvexPoly(claimed, np.round(b["poly"]).astype(np.int32), 255)
        except Exception:
            pass
    out = []
    for bb in _proposals_for_big_numbers(rgb_u8):
        x, y, w, h = bb
        sub = claimed[y:y + h, x:x + w]
        if sub.size and (sub > 0).mean() > 0.25:     # already found by the global OCR pass
            continue
        conf = _confirm_digit_crop(reader, rgb_u8, bb, min_conf=max(min_conf, 0.35))
        if conf is None:
            continue
        t, c = conf
        poly = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], np.float32)
        out.append({"poly": poly, "text": t, "conf": c, "h": float(h), "w": float(w),
                    "cx": float(x + w / 2.0), "cy": float(y + h / 2.0), "is_num": True})
    return out[:2]


def _crop_reads_as_word(reader, rgb_u8, bbox, min_conf=0.40):
    """True iff a NUMBER-candidate crop actually free-reads as a WORD (>=2 letters, alpha-dominant) —
    i.e. a sponsor wordmark the global pass mis-binned as a short number. Only a POSITIVE word read
    returns True, so a real (even stylized) number that reads as digits, or reads as nothing, STAYS a
    number. Reuses the crop-normalize path from _confirm_digit_crop."""
    H0, W0 = rgb_u8.shape[:2]
    x, y, w, h = bbox
    pad = int(0.2 * h)
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W0, x + w + pad), min(H0, y + h + pad)
    crop = rgb_u8[y0:y1, x0:x1]
    if crop.shape[0] < 8 or crop.shape[1] < 8:
        return False
    s = min(max(64.0 / crop.shape[0], 0.2), 5.0)
    up = cv2.resize(crop, (max(1, int(crop.shape[1] * s)), max(1, int(crop.shape[0] * s))),
                    interpolation=cv2.INTER_CUBIC)
    try:
        res = reader.readtext(up, detail=1, paragraph=False)
    except Exception:
        return False
    for box, txt, conf in res:
        clean = re.sub(r'[^0-9A-Za-z]', '', txt or '')
        a = sum(c.isalpha() for c in clean); d = sum(c.isdigit() for c in clean)
        if conf >= min_conf and a >= 2 and a > d:
            return True
    return False


def _tight_glyph_mask(rgb_u8, boxes, H, W, dilate=1):
    """Within each OCR polygon, Otsu-threshold the letterform strokes (minority extreme) -> tight mask."""
    mask = np.zeros((H, W), np.uint8)
    for b in boxes:
        poly = np.round(b["poly"]).astype(np.int32)
        x0, y0 = max(0, int(poly[:, 0].min())), max(0, int(poly[:, 1].min()))
        x1, y1 = min(W, int(poly[:, 0].max())), min(H, int(poly[:, 1].max()))
        if x1 - x0 < 3 or y1 - y0 < 3:
            continue
        crop = rgb_u8[y0:y1, x0:x1]
        g = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        try:
            _, t = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        except Exception:
            continue
        fg = t if (t > 0).mean() < 0.5 else (255 - t)  # strokes are the minority class
        pm = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillPoly(pm, [poly - [x0, y0]], 255)
        fg = cv2.bitwise_and(fg, pm)
        if dilate:
            fg = cv2.dilate(fg, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=dilate)
        sub = mask[y0:y1, x0:x1]
        mask[y0:y1, x0:x1] = np.maximum(sub, fg)
    return mask


def separate_livery_layers_smart(tex, *, min_conf=0.30, want_overlay_boxes=False,
                                 rotations=(0, 1, 2, 3), mirror_ocr=None, **_kw):
    """OCR-driven separation. Returns {"numbers","sponsors","paint"} uint8 (255=member) at input res,
    or None if OCR is unavailable (caller falls back to the classic detector).

    rotations: OCR is run at each 90deg rotation and boxes are mapped back — iRacing UV unwraps
    rotated panels, so (0,1,2,3) catches vertical/upside-down sponsor text the upright pass
    misses (e.g. a vertical MENARDS). Reflection is handled by a separate mirror pass;
    set SPB_SMART_TGA_MIRROR_OCR=0 for the legacy rotation-only path."""
    if cv2 is None or not ocr_available():
        return None
    try:
        rgb = _to_u8(tex)
        H, W = rgb.shape[:2]
        raw_boxes = _ocr_boxes(
            rgb, min_conf=min_conf, rotations=rotations, mirror_ocr=mirror_ocr
        )
        boxes = _dedup([b for b in raw_boxes if not b.get("mirrored")])
        nums, spons = _classify(boxes, H, W)
        mirror_supplements = []
        if _mirror_ocr_enabled(mirror_ocr):
            mirrored_boxes = _dedup([b for b in raw_boxes if b.get("mirrored")])
            for box in mirrored_boxes:
                if any(_box_overlap_min(box, normal) > 0.45 for normal in boxes):
                    continue
                box["is_num"] = False
                box["mirror_only"] = True
                mirror_supplements.append(box)
        # CROSS-ASSIGNMENT FIX (audit #2, 2026-06-27): a sponsor WORDMARK the global pass mis-binned as
        # a short NUMBER would be tinted as a door number (red). Re-read each number candidate's crop;
        # if it POSITIVELY reads as a WORD, move it to SPONSORS (blue) — never paint. Only positive
        # word-reads move, so real (incl. stylized) numbers are never demoted.
        try:
            _rdr = _reader()
            if _rdr is not None and nums:
                _kept = []
                for _b in nums:
                    _p = _b["poly"]
                    _bb = (int(_p[:, 0].min()), int(_p[:, 1].min()),
                           int(_p[:, 0].max() - _p[:, 0].min()), int(_p[:, 1].max() - _p[:, 1].min()))
                    if _bb[2] >= 6 and _bb[3] >= 6 and _crop_reads_as_word(_rdr, rgb, _bb):
                        spons.append(_b)
                    else:
                        _kept.append(_b)
                nums = _kept
        except Exception:
            pass
        # BIG-NUMBER RESCUE (2026-06-27): the global OCR passes miss a door/roof number that is
        # too LARGE for the detector. Shape-propose big isolated glyph blobs, then DIGIT-OCR each
        # crop at its own scale to CONFIRM — only blobs that read as a 1-3 digit number join
        # NUMBERS (logos/stripes/panels are rejected). Additive; never raises (best-effort).
        try:
            nums.extend(_big_number_rescue(rgb, nums + spons, H, W, min_conf=min_conf))
        except Exception:
            pass
        # Reflection is sponsor recall only at this stage. Add it after Number
        # classification/rescue so a backwards logo cannot alter global digit
        # prominence or suppress/trigger a big-number proposal.
        spons.extend(mirror_supplements)
        boxes.extend(mirror_supplements)
        numbers = _tight_glyph_mask(rgb, nums, H, W)
        sponsors = _tight_glyph_mask(rgb, spons, H, W)
        sponsors[numbers > 0] = 0                      # numbers win overlaps
        # NOTE: graphic-logo (CLIP) detection is NOT merged here — it feeds a dedicated BRAND-GRAPHICS
        # layer in car_layers.separate_into_layers so the user can keep it separate / merge to paint /
        # merge to sponsors (owner 2026-06-27). This OCR path stays text-only numbers/sponsors/paint.
        decals = cv2.bitwise_or(numbers, sponsors)
        paint = np.where(decals > 0, np.uint8(0), np.uint8(255))
        out = {"numbers": numbers, "sponsors": sponsors, "paint": paint}
        if want_overlay_boxes:
            out["_boxes"] = [{"poly": b["poly"].tolist(), "text": b["text"],
                              "is_num": b.get("is_num", False), "conf": b["conf"],
                              "rotation": b.get("rotation", 0),
                              "mirrored": b.get("mirrored", False),
                              "mirror_only": b.get("mirror_only", False),
                              "seen_unmirrored": b.get("seen_unmirrored", False)} for b in boxes]
        return out
    except Exception:
        return None

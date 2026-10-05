"""SPB-93: place linked copies of rendered material, including raw spec alpha.

Version 2 records refer to rectangles in document pixels. All sources are read
from the completed, unmodified render; copies cannot accidentally sample an
earlier copy. This module never interprets paint RGB as material channels.
"""
import math

import cv2
import numpy as np


def _rect(value, sx, sy):
    if not isinstance(value, dict):
        return None
    try:
        a = [float(value[k]) for k in ("x1", "y1", "x2", "y2")]
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in a) or a[2] <= a[0] or a[3] <= a[1]:
        return None
    return a[0] * sx, a[1] * sy, a[2] * sx, a[3] * sy


def apply_instances(paint, spec, zones, zone_masks=None, export_layers=None, source_paint=None):
    """Return paint/spec with valid v2 copies; leave all inputs unchanged.

    A copy contains the visible rendered material within its source Zone mask.
    Its rectangle controls independent size/position; rotation is clockwise in
    screen coordinates. Spec's fourth channel is sampled independently from
    coverage, so lighting alpha zero does not erase M/R/Cc.
    """
    h, w = paint.shape[:2]
    if paint.dtype != np.uint8 or spec.dtype != np.uint8 or paint.shape != (h, w, 3) or spec.shape != (h, w, 4):
        raise ValueError("Material instances require matching RGB/RGBA byte arrays")
    if source_paint is not None and (source_paint.dtype != np.uint8 or source_paint.shape != paint.shape):
        raise ValueError("Material paint ownership requires matching original RGB bytes")
    out_paint, out_spec = paint, spec
    for zi, zone in enumerate(zones or []):
        if not isinstance(zone, dict) or zone.get("muted"):
            continue
        records = zone.get("material_instances")
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict) or record.get("version") != 2 or record.get("muted"):
                continue
            try:
                dw, dh = (float(record[k]) for k in ("documentWidth", "documentHeight"))
                angle = float(record.get("rotation", 0))
            except (KeyError, TypeError, ValueError):
                continue
            if not all(math.isfinite(v) for v in (dw, dh, angle)) or dw <= 0 or dh <= 0:
                continue
            src = _rect(record.get("renderSourceBbox", record.get("sourceBbox")), w / dw, h / dh)
            dst = _rect(record.get("instanceBbox"), w / dw, h / dh)
            if src is None or dst is None:
                continue
            # Keep every covered source pixel at reduced resolution. Rounding
            # an odd document origin dropped a source column after promotion.
            x0, y0, x1, y1 = math.floor(src[0]), math.floor(src[1]), math.ceil(src[2]), math.ceil(src[3])
            if x0 < 0 or y0 < 0 or x1 > w or y1 > h or x1 <= x0 or y1 <= y0:
                continue
            sw, sh = x1 - x0, y1 - y0
            if record.get('isSource') and record.get('instanceBbox') == record.get('renderSourceBbox', record.get('sourceBbox')) and angle % 360 == 0:
                # The existing source patch already occupies these sampled pixels.
                # Keep its identity frame exact at fractional preview resolution.
                dst = (x0, y0, x1, y1)
            mask = np.ones((sh, sw), dtype=np.float32)
            if zone_masks is not None and zi < len(zone_masks) and zone_masks[zi] is not None:
                mask = np.clip(np.asarray(zone_masks[zi])[y0:y1, x0:x1], 0, 1).astype(np.float32)
            source_rgb, source_spec = paint[y0:y1, x0:x1], spec[y0:y1, x0:x1]
            authored = np.any(source_rgb != source_paint[y0:y1, x0:x1], axis=2) if source_paint is not None else np.zeros((sh, sw), dtype=bool)
            paint_mask = mask * authored
            snapshot = record.get('frozenMaterial')
            if snapshot is None and record.get('masterId'):
                master = next((r for r in records if isinstance(r, dict) and r.get('id') == record['masterId'] and not r.get('detached')), None)
                snapshot = master.get('frozenMaterial') if master else None
            if snapshot is not None:
                from engine.zone_material_snapshot import decode
                preview = snapshot.get('preview', {})
                if preview.get('documentWidth') == w and preview.get('documentHeight') == h:
                    snapshot = preview.get('material', snapshot)
                source_rgb, source_spec, mask, paint_mask = decode(snapshot)
                sh, sw = mask.shape
            # Explicit capture is consumed by the preview route, never persisted implicitly.
            if record.get('id') in zone.get('_material_capture_ids', []):
                from engine.zone_material_snapshot import encode
                zone.setdefault('_material_captures', {})[record['id']] = encode(source_rgb, source_spec, mask, paint_mask)
            tw, th = dst[2] - dst[0], dst[3] - dst[1]
            cx, cy = (dst[0] + dst[2]) / 2, (dst[1] + dst[3]) / 2
            radians = math.radians(angle % 360)
            cos, sin = math.cos(radians), math.sin(radians)
            # Physical pixel centers avoid one-pixel drift on exact quarter turns.
            a, b, c, d = cos * tw / sw, -sin * th / sh, sin * tw / sw, cos * th / sh
            rx, ry = (abs(cos) * tw + abs(sin) * th) / 2, (abs(sin) * tw + abs(cos) * th) / 2
            left, top = max(0, math.floor(cx - rx)), max(0, math.floor(cy - ry))
            right, bottom = min(w, math.ceil(cx + rx)), min(h, math.ceil(cy + ry))
            if right <= left or bottom <= top:
                continue
            matrix = np.array([[a, b, cx - .5 - a * (sw - 1) / 2 - b * (sh - 1) / 2 - left],
                               [c, d, cy - .5 - c * (sw - 1) / 2 - d * (sh - 1) / 2 - top]], dtype=np.float64)
            if not np.any(mask):
                continue
            size = (right - left, bottom - top)
            coverage = cv2.warpAffine(mask, matrix, size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            if not np.any(coverage):
                continue
            if out_paint is paint:
                out_paint, out_spec = paint.copy(), spec.copy()
            alpha = coverage[:, :, None]
            patches = []
            for original, output, source in ((paint, out_paint, source_rgb), (spec, out_spec, source_spec)):
                # Premultiply by geometric coverage, never by the spec alpha.
                channel_mask = mask
                channel_alpha = alpha
                if original is paint:
                    # A Zone material copy cannot clone untouched Layer artwork.
                    channel_mask = paint_mask
                    channel_alpha = cv2.warpAffine(channel_mask, matrix, size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[:, :, None]
                weighted = source.astype(np.float32) * channel_mask[:, :, None]
                patch = cv2.warpAffine(weighted, matrix, size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                region = output[top:bottom, left:right]
                region[:] = np.clip(np.rint(patch + region.astype(np.float32) * (1 - channel_alpha)), 0, 255).astype(np.uint8)
                if export_layers is not None:
                    patches.append(region.copy() if original is paint else np.clip(np.rint(np.divide(patch, alpha, out=np.zeros_like(patch), where=alpha > 0)), 0, 255).astype(np.uint8))
            if export_layers is not None:
                lp, ls, lm = np.zeros_like(paint), np.zeros_like(spec), np.zeros((h, w), dtype=np.float32)
                lp[top:bottom, left:right], ls[top:bottom, left:right], lm[top:bottom, left:right] = patches[0], patches[1], coverage
                export_layers.append({"zone_index": zi, "zone_name": str(zone.get("name", "Zone")) + " linked instance",
                                      "paint": lp, "spec": ls, "mask": lm})
    return out_paint, out_spec

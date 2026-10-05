"""SPB reference tracing routes (2026-10-02): measure the DESIGN of a reference picture (engine/ref_analyze.py).

POST /api/trace/analyze  { image: dataURL, views: [{kind:'side', nose:'left'|'right', box:[x0,y0,x1,y1]}] (fractions 0..1 of the picture, or pixels), part_px: [L, H], snap?: bool }
  -> { ok, base, accents, rings, strokes, bands, suggest:[{tool,args,why}], box, nose, size }

Local only (loopback host + the same origin guard as the other AI routes). Nothing is stored; the picture is decoded in memory.
"""
from __future__ import annotations

import time

MAX_BYTES = 14 * 1024 * 1024


def _loopback_host(host: str) -> bool:
    h = str(host or '').strip().lower()
    if h.startswith('['):
        h = h[1:h.find(']')] if ']' in h else h
    else:
        h = h.split(':')[0]
    return h in ('127.0.0.1', 'localhost', '::1')


def analyze_request(body: dict) -> dict:
    from engine import ref_analyze as RA
    img_src = body.get('image') or ''
    if not img_src or len(img_src) > MAX_BYTES * 1.4:
        return {'ok': False, 'error': 'image missing or too large'}
    img = RA._decode_image(img_src)
    h, w = img.shape[:2]
    views = []
    for v in body.get('views') or []:
        box = [float(x) for x in (v.get('box') or [])]
        if len(box) != 4:
            continue
        if max(box) <= 1.5:          # fractions of the picture
            box = [box[0] * w, box[1] * h, box[2] * w, box[3] * h]
        x0, y0, x1, y1 = [int(round(c)) for c in box]
        x0, x1 = sorted((max(0, x0), min(w, x1)))
        y0, y1 = sorted((max(0, y0), min(h, y1)))
        if x1 - x0 < 40 or y1 - y0 < 20:
            continue
        views.append({'kind': v.get('kind', 'side'), 'nose': v.get('nose', 'left'), 'box': (x0, y0, x1, y1)})
    if not views:
        # a lone picture with a side-view shape is taken as the side view itself
        if 2.2 <= w / max(1, h) <= 5.5:
            views.append({'kind': 'side', 'nose': body.get('nose', 'left'), 'box': (0, 0, w, h)})
        else:
            return {'ok': False, 'error': 'give the side view box (views:[{kind:"side", nose:"left", box:[x0,y0,x1,y1]}]) as fractions of the picture'}
    pp = body.get('part_px') or [1800, 512]
    t0 = time.time()
    res = RA.analyze(img, views, (int(pp[0]), int(pp[1])), snap=bool(body.get('snap')))
    if res.get('error'):
        return {'ok': False, 'error': res['error']}
    res['ok'] = True
    res['ms'] = int((time.time() - t0) * 1000)
    res['image_size'] = [w, h]
    return res


def register_trace_routes(app, logger=None):
    from flask import request, jsonify
    from server_routes.ai_copilot_routes import _origin_ok

    @app.route('/api/trace/analyze', methods=['POST'])
    def trace_analyze():
        if not _loopback_host(request.host) or not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        try:
            return jsonify(analyze_request(request.get_json(silent=True) or {}))
        except Exception as e:
            try:
                if logger:
                    logger.warning('[TRACE] analyze failed: %s' % e)
            except Exception:
                pass
            return jsonify({'ok': False, 'error': 'failed', 'message': str(e)[:160]}), 200

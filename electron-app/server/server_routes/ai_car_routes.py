"""SPB AI — template layout from the PSD itself  (SPB-AI 2026-09-30).

Some template PSDs (found in the owner's library: 3 of 21 tested) keep their Mask layer as a layer whose pixels only exist in the raw layer data: the app's importer composites each
layer, and for those files the Mask comes back EMPTY, so the page cannot see where the car's panels are (and the car library cannot recognise the layout).
This route reads the raw Mask / Wire layer pixels with psd-tools and returns them as two small 256x256 grids the page can use instead.

GET /api/ai/template-mask?path=<absolute .psd path>   ->   {ok, size:[W,H], mask:"<base64 PNG 256x256, 255 = opaque>", wall:"<base64 PNG 256x256, 255 = green wire outline>", found:{mask:bool, wire:bool}}
Only local origins (same guard as the other AI routes); only existing *.psd files; returns derived grids only, never layer pixels at full size.
"""
from __future__ import annotations

import base64
import io
import os
import re
import threading

_CACHE = {}
_LOCK = threading.Lock()
GRID = 256


def _find(psd, pat):
    hit = []

    def walk(layers):
        for l in layers:
            try:
                if re.search(pat, (l.name or '').strip(), re.I):
                    hit.append(l)
                if l.is_group():
                    walk(l)
            except Exception:
                continue
    walk(psd)
    return hit[0] if hit else None


def _full_rgba(psd, layer):
    import numpy as np
    from PIL import Image
    W, H = psd.width, psd.height
    full = np.zeros((H, W, 4), np.uint8)
    im = layer.topil()
    if im is None:
        return full
    a = np.asarray(im.convert('RGBA'))
    l, t = layer.left, layer.top
    x0, y0 = max(0, l), max(0, t)
    x1, y1 = min(W, l + a.shape[1]), min(H, t + a.shape[0])
    if x1 > x0 and y1 > y0:
        full[y0:y1, x0:x1] = a[y0 - t:y1 - t, x0 - l:x1 - l]
    return full


def _png_b64(arr) -> str:
    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(arr).save(b, 'PNG')
    return base64.b64encode(b.getvalue()).decode('ascii')


def compute(path: str) -> dict:
    import numpy as np
    from PIL import Image
    from psd_tools import PSDImage
    psd = PSDImage.open(path)
    out = {'ok': True, 'size': [psd.width, psd.height], 'found': {'mask': False, 'wire': False}}
    mk = _find(psd, r'^mask$')
    if mk is not None:
        a = _full_rgba(psd, mk)[:, :, 3]
        g = np.asarray(Image.fromarray(a).resize((GRID, GRID), Image.BILINEAR))
        out['mask'] = _png_b64(((g > 40) * 255).astype(np.uint8))
        out['found']['mask'] = True
    wr = _find(psd, r'^(wire|wireframe)$')
    if wr is not None:
        px = _full_rgba(psd, wr)
        green = (px[:, :, 3] > 120) & (px[:, :, 1] > 140) & (px[:, :, 0] < 130) & (px[:, :, 2] < 130) & ((px[:, :, 1].astype(int) - px[:, :, 0].astype(int)) > 60)
        g = np.asarray(Image.fromarray((green * 255).astype(np.uint8)).resize((GRID, GRID), Image.BOX))
        out['wall'] = _png_b64(((g > 0) * 255).astype(np.uint8))
        out['found']['wire'] = True
    return out


# ----------------------------------------------------------------------------- LEARNED CARS (SPB-AI 2026-10-02)
# The app learns every car it is shown: when a buyer (or the team) teaches / confirms where the parts of a car are on its UV sheet, the page POSTs the layout here and it is kept in
#   %APPDATA%/ShokkerPaintBooth/ai/learned_cars.json     (SPB_AI_DIR overrides the folder)
# The page merges GET /api/ai/learned-cars into window.SPB_CAR_ATLAS at start, so the next time that layout (or that iRacing car folder) is opened the parts are simply KNOWN.
# scripts/ai_atlas/merge_learned_cars.py folds a learned_cars.json into js/spb-car-atlas-data.js, which is how what the team teaches ships to every buyer.
_LEARN_LOCK = threading.Lock()


def _learned_file():
    from server_routes.ai_copilot_routes import _path
    return os.environ.get('SPB_LEARNED_CARS') or _path('learned_cars.json')      # SPB_LEARNED_CARS: a test server keeps its own file


def _load_learned():
    import json
    try:
        with open(_learned_file(), 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get('cars'), list):
            return d
    except Exception:
        pass
    return {'v': 1, 'cars': []}


def _sig_sim(a, b):
    """Jaccard similarity of two hex layout fingerprints (same measure as js/spb-pro-carmap.js sigSim)."""
    try:
        if not a or not b or len(a) != len(b):
            return 0.0
        inter = uni = 0
        for x, y in zip(a, b):
            xi, yi = int(x, 16), int(y, 16)
            inter += bin(xi & yi).count('1')
            uni += bin(xi | yi).count('1')
        return inter / uni if uni else 0.0
    except Exception:
        return 0.0


def _norm_folder(f):
    """The iRacing car folder key: the LAST segment of a path (a file segment is skipped), lowercase letters + digits only ('trucks ram2026' -> 'trucksram2026')."""
    f = str(f or '').strip().replace('\\', '/').rstrip('/')
    segs = [x for x in f.split('/') if x]
    seg = segs[-1] if segs else ''
    if re.search(r'\.(tga|png|psd|jpg)$', seg, re.I):
        seg = segs[-2] if len(segs) > 1 else ''
    return re.sub(r'[^a-z0-9]+', '', seg.lower())


def _clean_part(name, p):
    name = re.sub(r'\s+', ' ', str(name or '').strip().lower())[:40]
    box = p.get('box') if isinstance(p, dict) else None
    if not name or not isinstance(box, list) or len(box) != 4:
        return None, None
    try:
        v = [float(x) for x in box]
    except Exception:
        return None, None
    if max(v) > 1.5:          # the page exports percent of the sheet
        v = [x / 100.0 for x in v]
    v = [round(min(1.0, max(0.0, x)), 3) for x in v]
    if v[2] <= v[0] or v[3] <= v[1] or (v[2] - v[0]) * (v[3] - v[1]) < 0.002:
        return None, None
    out = {'box': v}
    for k in ('front', 'up'):
        if isinstance(p, dict) and p.get(k) in ('left', 'right', 'top', 'bottom'):
            out[k] = p[k]
    return name, out


def learn_car(body, now=None):
    """Merge one taught / confirmed / viewer-measured layout into the learned store. Returns (entry_id, n_parts) or (None, 0)."""
    import time
    parts_in = body.get('parts') if isinstance(body, dict) else None
    if not isinstance(parts_in, dict) or not parts_in:
        return None, 0
    folder = _norm_folder(body.get('folder'))
    sig = str(body.get('layoutSig') or '')
    if sig and not re.fullmatch(r'[0-9a-f]{64,512}', sig):
        sig = ''
    clean = {}
    for k, v in list(parts_in.items())[:24]:
        nm, pv = _clean_part(k, v)
        if nm:
            clean[nm] = pv
    if not clean:
        return None, 0
    with _LEARN_LOCK:
        d = _load_learned()
        hit = None
        for c in d['cars']:
            if folder and folder in [_norm_folder(x) for x in (c.get('folders') or [])]:
                hit = c
                break
            if sig and any(_sig_sim(sig, s2) >= 0.9 for s2 in (c.get('sigs') or [])):
                hit = c
                break
        if hit is None:
            ident = folder or (sig[:10] if sig else 'x%d' % (len(d['cars']) + 1))
            name = str(body.get('car') or body.get('psdName') or body.get('folder') or 'Learned car')[:80]
            hit = {'id': 'learned-' + ident, 'name': name, 'folders': [], 'sigs': [], 'parts': {}, 'learned': True, 'sources': [], 'n': 0}
            d['cars'].append(hit)
        if folder and folder not in [_norm_folder(x) for x in hit['folders']]:
            hit['folders'].append(str(body.get('folder') or folder)[:80])
        if sig and sig not in hit['sigs']:
            hit['sigs'] = (hit['sigs'] + [sig])[-4:]
        for nm, pv in clean.items():
            hit['parts'][nm] = pv
        src = str(body.get('source') or 'taught')[:40]
        if src not in hit['sources']:
            hit['sources'] = (hit['sources'] + [src])[-6:]
        hit['n'] = int(hit.get('n') or 0) + 1
        hit['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now or time.time()))
        if body.get('psdName') and not hit.get('psd'):
            hit['psd'] = str(body.get('psdName'))[:120]
        import json
        from server_routes.ai_copilot_routes import _atomic_write
        _atomic_write(_learned_file(), json.dumps(d, indent=1))
        return hit['id'], len(clean)


# ----------------------------------------------------------------------------- LEARNED NUMBER PLACES (SPB-AI 2026-10-03)
# On a flat paint the element finder (js/spb-pro-elements.js) asks the buyer to confirm / show where the car's NUMBERS are; the answer is kept per iRacing car folder (every paint of one car has them in
# the same place).  The browser keeps its own copy and also POSTs it here:   %APPDATA%/ShokkerPaintBooth/ai/learned_elements.json   (SPB_LEARNED_ELEMENTS overrides the file)
# {v:1, rows:[{key: car folder, kind: 'numbers', boxes: [[x0,y0,x1,y1] 0-1 ...], source, n: times told, at}]}.  GET returns the rows so another browser / machine starts out knowing them.
_ELEM_LOCK = threading.Lock()
_ELEM_KINDS = ('numbers',)


def _elements_file():
    from server_routes.ai_copilot_routes import _path
    return os.environ.get('SPB_LEARNED_ELEMENTS') or _path('learned_elements.json')


def _load_elements():
    import json
    try:
        with open(_elements_file(), 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get('rows'), list):
            return d
    except Exception:
        pass
    return {'v': 1, 'rows': []}


def learn_elements(body):
    # validate + store one row; returns (key, boxes_kept) or (None, 0)
    import json
    import time
    key = re.sub(r'[^a-z0-9]+', '', str(body.get('key') or '').lower())[:80]
    kind = str(body.get('kind') or '')
    if not key or kind not in _ELEM_KINDS:
        return None, 0
    forget = bool(body.get('forget'))
    boxes = []
    for b in (body.get('boxes') or [])[:12]:
        try:
            q = [min(1.0, max(0.0, float(v))) for v in b[:4]]
        except Exception:
            continue
        if len(q) == 4 and q[2] > q[0] and q[3] > q[1] and (q[2] - q[0]) * (q[3] - q[1]) <= 0.3:
            boxes.append([round(v, 3) for v in q])
    if not forget and not boxes:
        return None, 0
    with _ELEM_LOCK:
        d = _load_elements()
        rows = [r for r in d['rows'] if not (r.get('key') == key and r.get('kind') == kind)]
        old = [r for r in d['rows'] if r.get('key') == key and r.get('kind') == kind]
        if not forget:
            rows.append({'key': key, 'kind': kind, 'boxes': boxes, 'source': str(body.get('source') or 'confirm')[:20], 'n': (old[0].get('n', 0) + 1) if old else 1, 'at': int(time.time())})
        d['rows'] = rows[-400:]
        from server_routes.ai_copilot_routes import _atomic_write
        _atomic_write(_elements_file(), json.dumps(d, indent=1))
    return key, len(boxes)


# ----------------------------------------------------------------------------- "WHAT THE HELPER DID NOT UNDERSTAND" (SPB-AI 2026-10-02)
# The copilot writes every sentence it could not turn into a change (no built-in handler, an unknown look word, a colour that is not on the car ...) to
#   %APPDATA%/ShokkerPaintBooth/ai/ai_misses.jsonl     (SPB_AI_MISSES overrides the file)
# One JSON line per miss: {t: the buyer's words (200 chars max), w: why, at: unix seconds}. Local only; read it to grow the vocabulary (scripts/ai_atlas/read_misses.py).
_MISS_LOCK = threading.Lock()
_MISS_MAX_BYTES = 2 * 1024 * 1024


def _misses_file():
    from server_routes.ai_copilot_routes import _path
    return os.environ.get('SPB_AI_MISSES') or _path('ai_misses.jsonl')


def log_miss(text, why):
    import json
    import time
    text = re.sub(r'\s+', ' ', str(text or '')).strip()[:200]
    if not text:
        return False
    row = json.dumps({'t': text, 'w': str(why or '')[:60], 'at': int(time.time())}, ensure_ascii=False)
    with _MISS_LOCK:
        f = _misses_file()
        try:
            os.makedirs(os.path.dirname(f), exist_ok=True)
            if os.path.isfile(f) and os.path.getsize(f) > _MISS_MAX_BYTES:
                with open(f, 'r', encoding='utf-8') as h:
                    keep = h.read().splitlines()[-2000:]
                with open(f, 'w', encoding='utf-8') as h:
                    h.write('\n'.join(keep) + '\n')
            with open(f, 'a', encoding='utf-8') as h:
                h.write(row + '\n')
            return True
        except Exception:
            return False


def register_ai_car_routes(app, logger=None):
    from flask import request, jsonify
    from server_routes.ai_copilot_routes import _origin_ok

    @app.route('/api/ai/template-mask', methods=['GET'])
    def ai_template_mask():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        path = str(request.args.get('path') or '')
        if not path.lower().endswith('.psd') or not os.path.isfile(path):
            return jsonify({'ok': False, 'error': 'not_found', 'message': 'no such .psd file'}), 404
        try:
            key = (path, os.path.getmtime(path))
            with _LOCK:
                hit = _CACHE.get(key)
            if hit is None:
                hit = compute(path)
                with _LOCK:
                    _CACHE[key] = hit
                    while len(_CACHE) > 6:
                        _CACHE.pop(next(iter(_CACHE)))
            return jsonify(hit)
        except Exception as e:
            try:
                if logger:
                    logger.warning('[AI] template-mask failed: %s' % e)
            except Exception:
                pass
            return jsonify({'ok': False, 'error': 'failed', 'message': str(e)[:120]}), 200


    @app.route('/api/ai/misses', methods=['POST'])
    def ai_misses_post():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):      # [WP10 2026-10-03] a JSON array / scalar body used to 500 (body.get on a list)
            body = {}
        return jsonify({'ok': bool(log_miss(body.get('text'), body.get('why')))})

    @app.route('/api/ai/misses', methods=['GET'])
    def ai_misses_get():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        import json
        rows = []
        try:
            with open(_misses_file(), 'r', encoding='utf-8') as h:
                for line in h.read().splitlines()[-300:]:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass
        return jsonify({'ok': True, 'misses': rows})

    @app.route('/api/ai/learned-elements', methods=['GET'])
    def ai_learned_elements_get():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        return jsonify({'ok': True, 'v': 1, 'rows': _load_elements().get('rows', [])})

    @app.route('/api/ai/learned-elements', methods=['POST'])
    def ai_learned_elements_post():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        try:
            key, n = learn_elements(request.get_json(silent=True) or {})
            return jsonify({'ok': bool(key), 'key': key, 'boxes': n})
        except Exception as e:
            return jsonify({'ok': False, 'error': 'failed', 'message': str(e)[:120]}), 200

    @app.route('/api/ai/learned-cars', methods=['GET'])
    def ai_learned_cars_get():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        d = _load_learned()
        return jsonify({'ok': True, 'v': 1, 'cars': d.get('cars', [])})

    @app.route('/api/ai/learned-cars', methods=['POST'])
    def ai_learned_cars_post():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        try:
            body = request.get_json(silent=True) or {}
            cid, n = learn_car(body)
            if not cid:
                return jsonify({'ok': False, 'error': 'nothing_to_learn'}), 200
            try:
                if logger:
                    logger.info('[AI] learned car layout %s (%d parts, source %s)' % (cid, n, str(body.get('source'))[:30]))
            except Exception:
                pass
            return jsonify({'ok': True, 'id': cid, 'parts': n})
        except Exception as e:
            return jsonify({'ok': False, 'error': 'failed', 'message': str(e)[:120]}), 200

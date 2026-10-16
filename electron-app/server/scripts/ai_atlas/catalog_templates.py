#!/usr/bin/env python
"""Fingerprint the Mask layer of every template/livery PSD found by scan_psds.py, so cars can be grouped into LAYOUTS and added to the car library in bulk.
Python re-implementation of SpbProCar.layoutSigOf (256-grid alpha of the Mask layer -> paintable -> 32x32 bits); validated against sigs computed by the app
(`python scripts/ai_atlas/catalog_templates.py --verify`).  Writes _easy_claude_work/atlas/templates/<id>/{mask.png,wire.png} (1024px) for label sheets and
_easy_claude_work/atlas/catalog.jsonl (incremental).  SPB-AI 2026-09-30."""
import sys, os, json, re, time, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
from PIL import Image
from psd_tools import PSDImage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ATLAS = os.path.join(ROOT, '_easy_claude_work', 'atlas')
GRID = 256


def find_layer(psd, pat):
    out = []
    def walk(ls):
        for l in ls:
            if re.search(pat, l.name.strip(), re.I): out.append(l)
            if l.is_group(): walk(l)
    walk(psd)
    return out[0] if out else None


def layer_alpha(psd, layer):
    """full-canvas alpha plane (H,W) uint8 of one layer"""
    W, H = psd.width, psd.height
    im = layer.topil()
    full = np.zeros((H, W), np.uint8)
    if im is None: return full
    a = np.asarray(im.convert('RGBA'))[:, :, 3]
    l, t = layer.left, layer.top
    x0, y0 = max(0, l), max(0, t); x1, y1 = min(W, l + a.shape[1]), min(H, t + a.shape[0])
    if x1 > x0 and y1 > y0: full[y0:y1, x0:x1] = a[y0 - t:y1 - t, x0 - l:x1 - l]
    return full


def py_sig(alpha, W=2048):
    g = np.asarray(Image.fromarray(alpha).resize((GRID, GRID), Image.BILINEAR)) > 40
    frac = g.mean(); inv = frac < 0.12
    paint = g if inv else ~g
    pf = paint.mean()
    if not (0.08 < pf < 0.92): return None, pf
    bits = (paint.reshape(32, 8, 32, 8).sum(axis=(1, 3)) >= 32).astype(np.uint8).flatten()
    hexs = ''.join('%x' % int(''.join(map(str, bits[i:i + 4])), 2) for i in range(0, 1024, 4))
    return hexs, float(pf)


POP = [bin(i).count('1') for i in range(16)]
def sim(a, b):
    i = u = 0
    for x, y in zip(a, b):
        x, y = int(x, 16), int(y, 16); i += POP[x & y]; u += POP[x | y]
    return i / u if u else 0


def slug(p):
    base = os.path.splitext(os.path.basename(p))[0]
    return re.sub(r'[^a-z0-9]+', '_', base.lower()).strip('_')[:40] + '_' + hashlib.md5(p.encode('utf-8')).hexdigest()[:6]


def process(path, save_png=True):
    psd = PSDImage.open(path)
    mk = find_layer(psd, r'^mask$'); wr = find_layer(psd, r'^(wire|wireframe)$')
    if mk is None: return None
    ma = layer_alpha(psd, mk)
    sig, pf = py_sig(ma)
    rec = {'path': path, 'id': slug(path), 'sig': sig, 'paintable': round(pf, 3)}
    if save_png:
        d = os.path.join(ATLAS, 'templates', rec['id']); os.makedirs(d, exist_ok=True)
        Image.fromarray(ma).resize((1024, 1024), Image.BILINEAR).save(os.path.join(d, 'mask.png'))
        if wr is not None:
            wa = layer_alpha(psd, wr)
            try:
                wi = wr.topil().convert('RGBA'); full = Image.new('RGBA', (psd.width, psd.height), (0, 0, 0, 0)); full.paste(wi, (wr.left, wr.top)); full.resize((1024, 1024), Image.BILINEAR).save(os.path.join(d, 'wire.png'))
            except Exception:
                Image.fromarray(wa).resize((1024, 1024)).save(os.path.join(d, 'wire.png'))
    return rec


if __name__ == '__main__':
    if '--verify' in sys.argv:
        known = json.load(open(os.path.join(ROOT, 'scripts', 'ai_atlas', 'sigs.json'), encoding='utf-8'))
        tests = {'g6': 'C:/1Shokker Paint Car Examples/Older Junk/Smith G6 Chevy PSD.psd', 'arca': 'C:/1Shokker Paint Car Examples/SPB ARCA V7.psd',
                 'ngcity': 'C:/1Shokker Paint Car Examples/NEXT GEN/Next Gen City PSD.psd', 'truck': 'C:/1Shokker Paint Car Examples/Shokker Paint Booth Chevy Truck PSD.psd'}
        for k, p in tests.items():
            r = process(p, save_png=False); print(k, 'python-vs-app similarity %.3f' % (sim(r['sig'], known[k]) if r and r['sig'] else -1))
        sys.exit(0)
    scan, out = sys.argv[1], sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else ''
    done = set()
    if os.path.exists(out):
        for ln in open(out, encoding='utf-8'):
            try: done.add(json.loads(ln)['path'])
            except Exception: pass
    rows = [json.loads(l) for l in open(scan, encoding='utf-8')]
    rows = [r for r in rows if r.get('has_mask') and r['path'] not in done and (not only or only in r['path'].replace(chr(92), '/'))]
    n = 0; t0 = time.time()
    for r in rows:
        try:
            rec = process(r['path'])
        except Exception as e:
            rec = {'path': r['path'], 'error': str(e)[:100]}
        if rec is None: continue
        rec['size_mb'] = r['size_mb']
        open(out, 'a', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
        n += 1
        if n % 20 == 0: print(n, 'of', len(rows), round(time.time() - t0), 's', flush=True)
    print('done', n)

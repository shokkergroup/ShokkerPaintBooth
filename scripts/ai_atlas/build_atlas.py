#!/usr/bin/env python
"""SPB FINISH ATLAS builder — the AI copilot's deep knowledge of every finish (SPB-AI 2026-09-30).

The copilot used to find finishes by keyword search over names. It could not know that "Liquid Gallium" is a near-mirror, that "Dealer Pearl"
takes the zone colour while "Orchid Shift Pearl" brings its own, that a spec pattern is fine sparkle or broad bands, or which shelf a look lives on.
This script RENDERS every catalog item offline (paint + spec, the same engine the app uses) and MEASURES it:

  paint   palette (3 hex), colour name, brings-own-colour vs takes-the-zone-colour (rendered on two different input paints), lightness, saturation,
          contrast, hue spread (multi-colour / rainbow), texture fineness, flat-vs-textured, directionality
  spec    metal / roughness / clearcoat mean + std  (R/G/B of the spec map), sparkle score (high-frequency metal specks), shine class
  meta    name, description, shelf memberships (the buyer's 59 catalogue sections), curated tags, M7 quality score, protected/gold flag

Inputs : _easy_claude_work/atlas/catalog_dump.json  (made by scripts/ai_atlas/dump_catalog.py from the RUNNING app — the page catalogue is larger than
         the static finish-data file: other files add ~600 specials / 120 spec patterns at runtime)
Outputs: js/spb-ai-atlas-data.js   (window.SPB_ATLAS_DATA = {...}; injected lazily by js/spb-ai-atlas.js)   + _easy_claude_work/atlas/atlas_raw.jsonl (resumable work file)
Usage  : python scripts/ai_atlas/build_atlas.py [--limit N] [--force]
"""
import argparse, colorsys, contextlib, io, json, math, os, re, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / 'scripts'))
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass
import numpy as np
import cv2

DUMP = REPO / '_easy_claude_work' / 'atlas' / 'catalog_dump.json'
RAW = REPO / '_easy_claude_work' / 'atlas' / 'atlas_raw.jsonl'
OUT = REPO / 'js' / 'spb-ai-atlas-data.js'      # .js because the app's static route only serves js/css/png/svg/ico
SIZE = 128
SEED = 7777
SOLID_STD = 0.012

# ------------------------------------------------------------------ colour naming
def colour_name(rgb):
    r, g, b = [float(x) for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if l < 0.10: return 'black'
    if l > 0.93: return 'white'
    if s < 0.10:
        return 'charcoal' if l < 0.25 else ('dark grey' if l < 0.40 else ('grey' if l < 0.62 else ('silver' if l < 0.82 else 'pale grey')))
    hd = h * 360
    if hd < 14 or hd >= 346: base = 'red'
    elif hd < 40: base = 'orange' if l > 0.30 else 'brown'
    elif hd < 62: base = 'gold' if s > 0.45 and 0.30 < l < 0.70 else 'yellow'
    elif hd < 90: base = 'lime'
    elif hd < 160: base = 'green'
    elif hd < 185: base = 'teal'
    elif hd < 205: base = 'cyan'
    elif hd < 250: base = 'blue'
    elif hd < 275: base = 'indigo'
    elif hd < 300: base = 'purple'
    elif hd < 330: base = 'magenta'
    else: base = 'pink' if l > 0.55 else 'crimson'
    if base == 'orange' and l < 0.42: base = 'burnt orange'
    if base == 'red' and l < 0.30: base = 'maroon'
    if base == 'pink' and s > 0.6 and l > 0.5: base = 'hot pink'
    pre = ''
    if base not in ('gold', 'silver', 'brown', 'maroon', 'burnt orange', 'hot pink'):
        pre = 'deep ' if l < 0.30 else ('dark ' if l < 0.40 else ('pale ' if l > 0.78 else ('bright ' if s > 0.75 and 0.45 < l < 0.7 else '')))
    return pre + base

def hexof(rgb):
    return '#%02x%02x%02x' % tuple(int(round(max(0.0, min(1.0, float(c))) * 255)) for c in rgb)

# ------------------------------------------------------------------ rendering (mirrors scripts/spb_visual_workbench._render_item, with a chosen input paint)
def _spec_array(spec, shape):
    from spb_visual_workbench import _spec_array as sa
    return sa(spec, shape)

def render_base_or_mono(eng, item_id, kind, in_rgb):
    from spb_visual_workbench import _call_mono_spec
    shape = (SIZE, SIZE)
    mask = np.ones(shape, np.float32); bb = np.zeros(shape, np.float32)
    paint = np.empty((SIZE, SIZE, 3), np.float32); paint[:] = np.asarray(in_rgb, np.float32)
    if kind == 'base' and item_id in eng.BASE_REGISTRY:
        e = eng.BASE_REGISTRY[item_id]; rgb = paint.copy()
        if e.get('paint_fn'): rgb = e['paint_fn'](rgb, shape, mask, SEED, 1.0, bb)
        spec = None
        if e.get('base_spec_fn'): spec = e['base_spec_fn'](shape, SEED, 1.0, float(e.get('M', 120)), float(e.get('R', 80)))
        else:   # registry-only numbers (plain materials)
            spec = (np.full(shape, float(e.get('M', 0)), np.float32), np.full(shape, float(e.get('R', 80)), np.float32), np.full(shape, float(e.get('CC', 16)), np.float32))
        return np.clip(rgb[:, :, :3], 0, 1), _spec_array(spec, shape)
    if item_id in eng.MONOLITHIC_REGISTRY:
        sp_fn, pt_fn = eng.MONOLITHIC_REGISTRY[item_id][:2]
        rgb = pt_fn(paint.copy(), shape, mask, SEED, 1.0, bb)
        return np.clip(rgb[:, :, :3], 0, 1), _spec_array(_call_mono_spec(sp_fn, shape, mask, SEED), shape)
    raise KeyError(item_id)

def luma_of(rgb): return rgb[:, :, :3].mean(axis=2)

def fine_energy(l):
    return float(np.abs(np.diff(l, axis=1)).mean() + np.abs(np.diff(l, axis=0)).mean())

def anisotropy(l):
    gx = float(np.abs(np.diff(l, axis=1)).mean()); gy = float(np.abs(np.diff(l, axis=0)).mean())
    return (gx - gy) / (gx + gy + 1e-9)        # +1 = vertical lines/streaks, -1 = horizontal

def dom_freq(l):
    """centroid of the radial power spectrum in cycles/image (low = broad forms, high = fine grain)"""
    g = l - l.mean()
    if float(g.std()) < 1e-4: return 0.0
    F = np.abs(np.fft.fftshift(np.fft.fft2(g))) ** 2
    h, w = F.shape; yy, xx = np.indices(F.shape); rr = np.hypot(yy - h / 2, xx - w / 2)
    F[int(h / 2), int(w / 2)] = 0
    return float((rr * F).sum() / (F.sum() + 1e-9))

def palette(rgb, k=3):
    px = (rgb.reshape(-1, 3) * 255).astype(np.float32)
    if len(px) > 4096: px = px[:: len(px) // 4096]
    if float(px.std(axis=0).max()) < 2.0:
        m = px.mean(axis=0) / 255.0; return [(m, 1.0)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
    _, lab, cen = cv2.kmeans(px, k, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    cnt = np.bincount(lab.ravel(), minlength=k).astype(np.float32); cnt /= cnt.sum()
    order = np.argsort(-cnt)
    out = []
    for i in order:
        c = cen[i] / 255.0
        if out and any(np.linalg.norm((c - o[0]) * 255) < 28 for o in out): out[0] = (out[0][0], out[0][1] + float(cnt[i])); continue
        out.append((c, float(cnt[i])))
    return out

def hue_spread(rgb):
    hsv = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV_FULL).reshape(-1, 3).astype(np.float32)
    m = hsv[:, 1] > 60
    if m.sum() < 30: return 0.0, 0
    ang = hsv[m, 0] / 255.0 * 2 * math.pi
    R = math.hypot(float(np.cos(ang).mean()), float(np.sin(ang).mean()))
    sectors = len(set(int(a / (2 * math.pi) * 8) % 8 for a in ang.tolist() if True)) if len(ang) else 0
    return float(1.0 - R), sectors

def analyse_paint_spec(rgb0, rgb1, spec):
    out = {}
    l0 = luma_of(rgb0)
    out['flat_paint'] = bool(float(l0.std()) < SOLID_STD)
    # brings own colour? compare the two renders (different input paint)
    d_out = float(np.abs(rgb1.reshape(-1, 3).mean(0) - rgb0.reshape(-1, 3).mean(0)).max())
    d_in = 0.44                                      # how different the two inputs were (max channel)
    follow = d_out / d_in
    out['follow'] = round(follow, 3)
    out['own'] = 0 if follow > 0.45 else 1           # 1 = ignores the input paint (brings its own colours)
    use = rgb0 if out['own'] else rgb1
    pal = palette(use, 3)
    out['pal'] = [hexof(c) for c, w in pal][:3]
    out['palw'] = [round(w, 2) for c, w in pal][:3]
    mean = use.reshape(-1, 3).mean(0)
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in mean])
    out['cname'] = colour_name(pal[0][0]) if pal else colour_name(mean)
    out['L'] = int(round(l * 100)); out['S'] = int(round(s * 100))
    lu = luma_of(use)
    out['V'] = int(round(float(lu.std()) * 200))        # contrast 0..100ish
    hs, sec = hue_spread(use)
    out['hs'] = int(round(hs * 100)); out['hsec'] = sec
    out['fe'] = round(fine_energy(lu), 4); out['df'] = round(dom_freq(lu), 2); out['an'] = round(anisotropy(lu), 2)
    if spec is not None:
        sp = spec.astype(np.float32)
        for nm, ch in (('M', 0), ('R', 1), ('C', 2)):
            out[nm] = [int(round(float(sp[:, :, ch].mean()))), int(round(float(sp[:, :, ch].std())))]
        m = sp[:, :, 0]; blur = cv2.GaussianBlur(m, (0, 0), 2.0)
        resid = m - blur
        out['spark'] = int(round(min(100.0, float(resid.std()) / 35.0 * 100)))
        r_ = sp[:, :, 1]; out['spark_r'] = int(round(min(100.0, float((r_ - cv2.GaussianBlur(r_, (0, 0), 2.0)).std()) / 35.0 * 100)))
        sl = sp[:, :, :3].mean(axis=2) / 255.0
        out['spec_energy'] = round(float(sl.std()), 4)
        out['spec_fe'] = round(fine_energy(sl), 4)
    out['energy'] = round(max(float(lu.std()), out.get('spec_energy', 0.0)), 4)
    return out

def analyse_field(pv):
    """paint-pattern / spec-pattern scalar field stats"""
    pv = np.asarray(pv, np.float32)
    if pv.ndim == 3: pv = pv.mean(axis=2)
    lo, hi = float(pv.min()), float(pv.max())
    n = (pv - lo) / (hi - lo + 1e-9)
    thr = 0.5
    return {
        'cov': int(round(float((n > thr).mean()) * 100)),      # fraction of the field that is "on"
        'con': int(round(float(n.std()) * 200)),
        'fe': round(fine_energy(n), 4), 'df': round(dom_freq(n), 2), 'an': round(anisotropy(n), 2),
        'flat': bool(float(n.std()) < 0.02),
    }

# ------------------------------------------------------------------ text tag vocabulary (name + desc -> concept tags)
TAG_WORDS = {
 'chrome': ['chrome', 'mirror', 'liquid metal', 'mercury', 'gallium', 'polished'], 'candy': ['candy', 'jelly', 'tinted clear'], 'pearl': ['pearl', 'nacre', 'opal'],
 'matte': ['matte', 'flat black', 'dead flat', 'satin'], 'metallic': ['metallic', 'metal flake', 'flake'], 'holographic': ['holographic', 'hologram', 'rainbow', 'prism', 'iridescent', 'dichroic', 'spectral', 'chameleon', 'color shift', 'colour shift', 'flip'],
 'carbon': ['carbon'], 'weave': ['weave', 'twill', 'mesh', 'knit', 'fabric', 'cloth'], 'brushed': ['brushed', 'anodized', 'machined', 'engine turn', 'spun'], 'glitter': ['glitter', 'sparkle', 'sequin', 'stardust', 'flake', 'confetti'],
 'camo': ['camo', 'camouflage', 'digital'], 'scales': ['scale', 'snake', 'dragon', 'reptile', 'lizard', 'fish'], 'wood': ['wood', 'grain', 'timber', 'bamboo'], 'leather': ['leather', 'hide', 'suede'],
 'stone': ['marble', 'granite', 'stone', 'concrete', 'slate', 'terrazzo', 'quartz'], 'rust': ['rust', 'corrod', 'patina', 'oxid', 'verdigris'], 'weathered': ['weather', 'worn', 'faded', 'dirty', 'grunge', 'scratch', 'chip', 'distress', 'crack', 'mud', 'dust'],
 'neon': ['neon', 'glow', 'fluoresc', 'laser', 'plasma'], 'gradient': ['gradient', 'fade', 'ombre', 'blend'], 'stripes': ['stripe', 'pinstripe', 'band', 'chevron', 'racing stripe'], 'flames': ['flame', 'fire', 'inferno', 'ember', 'blaze'],
 'geometric': ['geometric', 'hex', 'triangle', 'diamond', 'grid', 'lattice', 'voronoi', 'truchet', 'polygon', 'facet', 'tessell'], 'floral': ['floral', 'flower', 'petal', 'botanical', 'leaf', 'vine'], 'cosmic': ['galaxy', 'nebula', 'cosmic', 'star', 'aurora', 'space', 'supernova', 'planet'],
 'water': ['water', 'ocean', 'wave', 'ripple', 'rain', 'droplet', 'ice', 'frost', 'liquid'], 'organic': ['organic', 'cell', 'vein', 'skin', 'bone', 'coral', 'moss', 'lichen'], 'glass': ['glass', 'crystal', 'prismatic', 'stained'], 'retro': ['retro', 'vintage', '70s', '60s', '80s', '90s', 'groovy', 'diner'],
 'tactical': ['tactical', 'military', 'stealth', 'cerakote', 'gunmetal', 'flat dark'], 'luxury': ['gold', 'platinum', 'luxury', 'royal', 'jewel', 'gem', 'diamond', 'velvet', 'silk', 'premium'], 'cyber': ['cyber', 'circuit', 'digital', 'glitch', 'tron', 'pixel', 'hologram', 'synth'],
 'dark': ['black', 'dark', 'night', 'shadow', 'void', 'obsidian', 'onyx', 'noir', 'ink'], 'light': ['white', 'ivory', 'cream', 'pale', 'snow', 'pastel'], 'japanese': ['sakura', 'japan', 'anime', 'koi', 'seigaiha', 'kintsugi'], 'mexican': ['mexic', 'calavera', 'sugar skull', 'talavera'],
 'spooky': ['skull', 'bone', 'gothic', 'horror', 'blood', 'witch', 'voodoo', 'predator', 'venom', 'toxic'], 'sparkle_fine': ['fine flake', 'micro', 'dust', 'sand'],
}
def text_tags(text):
    t = ' ' + re.sub(r'[^a-z0-9 ]+', ' ', text.lower()) + ' '
    out = []
    for tag, words in TAG_WORDS.items():
        if any((' ' + w + ' ') in t or (w in t and len(w) > 4) for w in words): out.append(tag)
    return out

def shine_class(Rm, Mm, Cm):
    if Rm is None: return None
    if Rm < 28 and Mm >= 150: return 'mirror'
    if Rm < 60: return 'high gloss' if Cm <= 60 else 'gloss'
    if Rm < 120: return 'satin'
    if Rm < 180: return 'semi-matte'
    return 'matte'
def metal_class(Mm):
    if Mm is None: return None
    return 'none' if Mm < 30 else ('low' if Mm < 90 else ('medium' if Mm < 160 else ('high' if Mm < 215 else 'full')))
def fine_bucket(fe, df, flat):
    if flat: return 'flat'
    if df < 6: return 'broad'
    if df < 14: return 'medium'
    if df < 28: return 'fine'
    return 'micro'

_ENG = None
def _init_worker():
    global _ENG
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as eng
        if hasattr(eng, '_ensure_expansions_loaded'): eng._ensure_expansions_loaded()
    _ENG = eng

def _render_one(job):
    key, kind, iid, meta = job
    IN0 = (0.18, 0.18, 0.18); IN1 = (0.62, 0.20, 0.20)
    rec = {'k': key}
    try:
        from spb_visual_workbench import _render_item
        if kind in ('base', 'monolithic'):
            rgb0, spec = render_base_or_mono(_ENG, iid, kind, IN0)
            rgb1, _ = render_base_or_mono(_ENG, iid, kind, IN1)
            rec.update(analyse_paint_spec(rgb0, rgb1, spec))
        elif kind == 'pattern':
            rgb, spec, _ = _render_item(_ENG, iid, 'pattern', SIZE, SEED, meta)
            rec.update(analyse_field(rgb.mean(axis=2)))
        else:
            from engine.spec_patterns import PATTERN_CATALOG
            if iid not in PATTERN_CATALOG: raise KeyError(iid)
            rec.update(analyse_field(PATTERN_CATALOG[iid]((SIZE, SIZE), SEED, 1.0)))
    except Exception as e:
        rec['err'] = str(e)[:100]
    return rec

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=0); ap.add_argument('--force', action='store_true'); ap.add_argument('--workers', type=int, default=6); args = ap.parse_args()
    cat = json.load(open(DUMP, encoding='utf-8'))
    t0 = time.time()
    done = {}
    if RAW.exists() and not args.force:
        for l in open(RAW, encoding='utf-8'):
            try: r = json.loads(l); done[r['k']] = r
            except Exception: pass
    # work list: (key, kind, id, meta)
    work = []
    for b in cat['bases']: work.append(('base::' + b['id'], 'base', b['id'], b))
    for m in cat['monolithics']: work.append(('monolithic::' + m['id'], 'monolithic', m['id'], m))
    for p in cat['patterns']: work.append(('pattern::' + p['id'], 'pattern', p['id'], p))
    for s in cat['spec_patterns']: work.append(('spec::' + s['id'], 'spec', s['id'], s))
    if args.limit: work = work[: args.limit]
    RAW.parent.mkdir(parents=True, exist_ok=True)
    todo = [w for w in work if w[0] not in done]
    n_skip = len(work) - len(todo); n_ok = n_fail = 0
    fh = open(RAW, 'a', encoding='utf-8')
    import multiprocessing as mp
    workers = max(1, min(int(args.workers), (os.cpu_count() or 4) - 1))
    print('rendering %d items with %d workers' % (len(todo), workers), flush=True)
    t1 = time.time()
    if workers == 1:
        _init_worker(); it = map(_render_one, todo)
        pool = None
    else:
        pool = mp.Pool(workers, initializer=_init_worker); it = pool.imap_unordered(_render_one, todo, chunksize=4)
    for n, rec in enumerate(it):
        if 'err' in rec: n_fail += 1
        else: n_ok += 1
        fh.write(json.dumps(rec) + chr(10))
        if n % 100 == 0: fh.flush()
        if (n + 1) % 300 == 0: print('  %d/%d  ok=%d fail=%d  %.0fs' % (n + 1, len(todo), n_ok, n_fail, time.time() - t1), flush=True)
    if pool: pool.close(); pool.join()
    fh.close()
    print('render pass done: ok=%d fail=%d skipped(cached)=%d in %.0fs' % (n_ok, n_fail, n_skip, time.time() - t0))
    assemble(cat)

def assemble(cat):
    raw = {}
    for l in open(RAW, encoding='utf-8'):
        try: r = json.loads(l); raw[r['k']] = r
        except Exception: pass
    # shelves
    sections = [s['title'] for s in cat['sections']]
    sec_of = {}
    for si, s in enumerate(cat['sections']):
        for key in s['ids']:
            sec_of.setdefault(key, []).append(si)
    top = set(t if isinstance(t, str) else (t.get('id') or t.get('key') or '') for t in (cat.get('top') or []))
    pat_group = {}
    for gname, ids in (cat.get('PATTERN_GROUPS') or {}).items():
        for i in ids: pat_group.setdefault(i, gname)
    tags_cur = cat.get('FINISH_TAGS') or {}
    m7 = {}
    try: m7 = json.load(open(REPO / '_workbook_metrics' / 'm7_composite.json', encoding='utf-8'))['byFinish']
    except Exception: pass
    prot = {}
    try: prot = json.load(open(REPO / 'scripts' / 'protected_finishes.json', encoding='utf-8')).get('locked', {})
    except Exception: pass
    # fineness quantile buckets for paint finishes (computed on the catalogue itself)
    dfs = sorted(float(r['df']) for r in raw.values() if 'pal' in r and not (r.get('flat_paint') and r.get('spec_energy', 0) < SOLID_STD))
    def q(p): return dfs[min(len(dfs) - 1, int(len(dfs) * p))] if dfs else 0
    Q1, Q2, Q3 = q(0.22), q(0.55), q(0.85)
    def bucket(r):
        if r.get('flat_paint') and r.get('spec_energy', 0) < SOLID_STD: return 'flat'
        df = float(r.get('df', 0))
        return 'broad' if df <= Q1 else ('medium' if df <= Q2 else ('fine' if df <= Q3 else 'micro'))
    items = []
    def base_row(kind_key, m, typ):
        iid = m['id']; r = raw.get(kind_key, {})
        desc = re.sub(r'\s+', ' ', str(m.get('desc') or '')).strip()
        row = {'k': kind_key, 'n': m.get('name') or iid, 'd': desc[:170]}
        if typ in ('base', 'monolithic'):
            row['s'] = sec_of.get(kind_key, [])
            if m.get('astraLane'): row['lane'] = m['astraLane']
            if r and 'pal' in r:
                row['c'] = r['pal']; row['cn'] = r['cname']; row['o'] = r['own']
                row['L'] = r['L']; row['S'] = r['S']; row['V'] = r['V']; row['hs'] = r['hs']; row['hc'] = r['hsec']
                row['fb'] = bucket(r); row['an'] = r['an']
                if 'M' in r:
                    row['M'] = r['M']; row['R'] = r['R']; row['C'] = r['C']; row['sp'] = r['spark']
                    row['shine'] = shine_class(r['R'][0], r['M'][0], r['C'][0]); row['metal'] = metal_class(r['M'][0])
                    row['se'] = int(round(r.get('spec_energy', 0) * 200))
            elif m.get('swatch'):
                row['c'] = [m['swatch']]
        tg = []
        for t in (m.get('tags') or []): tg.append(str(t))
        for t in (tags_cur.get(iid) or []): tg.append(str(t))
        tg += text_tags((m.get('name') or '') + ' ' + desc)
        if typ in ('base', 'monolithic') and r and 'pal' in r:
            if r.get('own') == 0 and not r.get('flat_paint'): pass
            if r.get('hs', 0) > 45 and r.get('hsec', 0) >= 4: tg.append('rainbow')
            if r.get('an', 0) > 0.35: tg.append('streaks-v')
            if r.get('an', 0) < -0.35: tg.append('streaks-h')
        seen = []; [seen.append(t) for t in tg if t not in seen]
        row['t'] = seen[:14]
        q = (m7.get('%s:%s' % ({'spec': 'spec_pattern'}.get(typ, typ), iid)) or {}).get('composite')
        if q is not None: row['q'] = int(round(q))
        if iid in prot: row['gold'] = 1
        if iid in top or kind_key in top: row['top'] = 1
        return row
    for m in cat['bases']: items.append(base_row('base::' + m['id'], m, 'base'))
    for m in cat['monolithics']: items.append(base_row('monolithic::' + m['id'], m, 'monolithic'))
    for m in cat['patterns']:
        row = base_row('pattern::' + m['id'], m, 'pattern'); r = raw.get('pattern::' + m['id'], {}); row['g'] = pat_group.get(m['id'])
        if 'cov' in r: row['cov'] = r['cov']; row['con'] = r['con']; row['fb'] = fine_bucket(r['fe'], r['df'], r['flat']); row['an'] = r['an']
        items.append(row)
    for m in cat['spec_patterns']:
        row = base_row('spec::' + m['id'], m, 'spec'); r = raw.get('spec::' + m['id'], {})
        row['g'] = m.get('category'); row['ch'] = m.get('defaultChannels'); row['df'] = m.get('defaults')
        if 'cov' in r: row['cov'] = r['cov']; row['con'] = r['con']; row['fb'] = fine_bucket(r['fe'], r['df'], r['flat']); row['an'] = r['an']
        items.append(row)
    sp_vals = sorted(it['sp'] for it in items if it.get('sp') is not None)
    SP_T = sp_vals[int(len(sp_vals) * 0.78)] if sp_vals else 40
    for it in items:
        if it.get('sp') is not None:
            tg = [t for t in (it.get('t') or []) if t != 'sparkle']
            if it['sp'] >= SP_T: tg.append('sparkle')
            it['t'] = tg[:14]; it['sk'] = 1 if it['sp'] >= SP_T else 0
    print('sparkle threshold (78th pct):', SP_T)
    blurbs = []
    from collections import Counter
    for si, sname in enumerate(sections):
        its = [it for it in items if si in (it.get('s') or [])]
        if not its: blurbs.append(''); continue
        n = len(its)
        fin = [it for it in its if 'M' in it]
        parts = []
        if fin:
            own = sum(1 for it in fin if it.get('o') == 1) / len(fin)
            parts.append('brings its own colours' if own > 0.8 else ('takes the zone colour' if own < 0.3 else 'mix of own-colour and tintable'))
            sh = Counter(it.get('shine') for it in fin if it.get('shine')).most_common(2); mt = Counter(it.get('metal') for it in fin if it.get('metal')).most_common(1)
            if sh: parts.append('mostly ' + '/'.join(x for x, _ in sh))
            if mt and mt[0][0] not in ('none',): parts.append(mt[0][0] + ' metal')
            sp = sum(1 for it in fin if it.get('sk')) / len(fin)
            if sp > 0.4: parts.append('sparkly')
        tg = Counter(t for it in its for t in (it.get('t') or []) if t not in ('dark', 'light', 'sparkle', 'streaks-v', 'streaks-h')).most_common(4)
        if tg: parts.append('themes: ' + ', '.join(t for t, _ in tg[:3]))
        ex = sorted(its, key=lambda it: (-(it.get('q') or 0), it['n']))[:3]
        parts.append('e.g. ' + ', '.join(it['n'] for it in ex))
        blurbs.append('; '.join(parts)[:230])
    OVERRIDES = json.load(open(REPO / 'scripts' / 'ai_atlas' / 'shelf_notes.json', encoding='utf-8')) if (REPO / 'scripts' / 'ai_atlas' / 'shelf_notes.json').exists() else {}
    for si, sname in enumerate(sections):
        if sname in OVERRIDES: blurbs[si] = OVERRIDES[sname] + (' | ' + blurbs[si] if blurbs[si] else '')
    payload = {'v': 1, 'blurbs': blurbs, 'generated': int(time.time()), 'sections': sections, 'count': len(items), 'items': items,
               'groups': {'base': list((cat.get('BASE_GROUPS') or {}).keys()), 'special': list((cat.get('SPECIAL_GROUPS') or {}).keys()), 'pattern': list((cat.get('PATTERN_GROUPS') or {}).keys()), 'spec': list((cat.get('SPEC_PATTERN_GROUPS') or {}).keys())},
               'sectionSize': [len(s['ids']) for s in cat['sections']]}
    tmp = str(OUT) + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline=chr(10)) as f:
        f.write('/* GENERATED by scripts/ai_atlas/build_atlas.py - do not edit. The AI copilot measured knowledge of every finish. */' + chr(10) + 'window.SPB_ATLAS_DATA=')
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';' + chr(10))
    os.replace(tmp, OUT)
    measured = sum(1 for it in items if 'M' in it)
    print('atlas: %d items (%d with measured spec) -> %s (%.2f MB)' % (len(items), measured, OUT.name, OUT.stat().st_size / 1e6))

if __name__ == '__main__':
    sys.exit(main())

"""enc_gen_B.py - Encyclopedia v2 lane B generator (2026-10-04).
Writes one page per finish / pattern / spec pattern from the shipped catalogue data (atlas + finish cards):
  data/encyclopedia/finish_pages.json, pattern_pages.json, spec_pattern_pages.json   (manifests: {domain, version, articles:[], parts:[...]})
  data/encyclopedia/pages/<stem>.json                                                 (parts <= 95 KB, each a normal domain file {domain:<stem>, articles:[...]})
Why parts live in pages/: the shared gate caps every top-level domain file at 100 KB and ~4,800 pages are ~5 MB.
Run:  python scripts/ai_atlas/enc_gen_B.py [--flat]   (--flat writes the parts next to the manifests, used to run the shared gate over them)
Source of truth: js/spb-ai-atlas-data.js + js/spb-ai-cards-data.js (+ paint-booth-0-finish-data.js for lists), read through enc_gen_B_dump.js.
Deterministic: partition = primary shelf / group order, then sorted key. Parts are rewritten only if their text changed (resume-safe)."""
import json, os, re, subprocess, sys, unicodedata, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc_hidden as _H   # shared hidden-feature list (Easy mode is hidden, owner rule 2026-10-04)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc_gen_B_v3 as V3
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'data', 'encyclopedia')
DUMP = os.path.join(OUT, '_drafts', '_dumpB.json')
FLAT = '--flat' in sys.argv
PAGES = OUT if FLAT else os.path.join(OUT, 'pages')
MAXB = 95 * 1024
TODAY = '2026-10-04'
# FACTCHECK 2026-10-04: finishes that the live Pro picker does NOT list (snapshot: enc_picker_hidden.json). The old pages told every
# reader to "open the Base Material picker and search for" these, which is false for about a third of the catalogue.
# FACTCHECK round 2: pinned flat Foundation spec straight from the engine (enc_dump_pinned.py); the atlas measured base::semi_gloss at 60/16, the registry pins 55/40.
try: PINNED = json.load(open(os.path.join(HERE, 'enc_foundation_pinned.json'), encoding='utf-8'))['pinned']
except Exception: PINNED = {}
try: NOT_IN_PICKER = set(json.load(open(os.path.join(HERE, 'enc_picker_hidden.json'), encoding='utf-8'))['hidden'])
except Exception: NOT_IN_PICKER = set()
ATLAS_SRC, CARDS_SRC = 'js/spb-ai-atlas-data.js:2', 'js/spb-ai-cards-data.js:2'
try: UI_SPEC = json.load(open(os.path.join(HERE, 'ui_spec_groups.json'), encoding='utf-8'))   # spec id -> [collection tab, real picker group] (UI audit 2026-10-05)
except Exception: UI_SPEC = {}

# ---- text hygiene (same rules as the gate) ----
JARGON = [re.compile(x, re.I) for x in (r'\b[\w-]+\.(?:js|py|jsx|ts|css|html|json|md|bat|ps1)\b', r'\\[A-Za-z]', r'(?:^|\s)/api/', r'\b\w+\(\)',
          r'\b(?:payload|endpoint|localStorage|sessionStorage|DOM|regex|JSON|inventory|handler|callback|refactor|SPB-\d+|TODO|FIXME|monkey-?patch|state machine|API call|stack trace)\b')]
STATS = {'cleaned': 0}


def clean(t):
    if not isinstance(t, str): return t
    t = t.replace('’', "'").strip()
    for _ in range(3):
        hit = False
        for r in JARGON:
            if r.search(t):
                t = r.sub('', t); hit = True; STATS['cleaned'] += 1
        if not hit: break
    return re.sub(r'\s{2,}', ' ', t).strip()


def n_sent(s): return len(re.findall(r'[.!?](\s|$)', s))


def fit_summary(t):
    """greedy: whole sentences while <= 330 chars and <= 2 sentences; if the first sentence alone is too long, cut at a clause."""
    t = clean(t) or ''
    parts, last = [], 0
    for m in re.finditer(r'[.!?](\s|$)', t):
        parts.append(t[last:m.end()].strip()); last = m.end()
    if last < len(t): parts.append(t[last:].strip())
    out = ''
    for sent in parts[:2]:
        cand = (out + ' ' + sent).strip()
        if len(cand) <= 330: out = cand
        else: break
    if not out and parts:
        first = parts[0]
        cut = max(first.rfind(';', 0, 300), first.rfind(',', 0, 300), first.rfind(' ', 0, 300))
        out = first[:cut].rstrip(',;:.- ') + '.'
    if out and not re.search(r'[.!?]$', out): out += '.'
    return out


def cap(t, n):
    t = clean(t) or ''
    if len(t) <= n: return t
    return t[:n - 1].rsplit(' ', 1)[0].rstrip(',;:.-') + '.'


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_').lower()
    return s or 'misc'


def safe_id(s): return re.sub(r'[^A-Za-z0-9_\-]', '_', s)


# ---- data ----
if not os.path.exists(DUMP):
    subprocess.check_call(['node', os.path.join(HERE, 'enc_gen_B_dump.js'), DUMP], cwd=ROOT)
D = json.load(open(DUMP, encoding='utf-8'))
AT = D['atlas']; ITEMS = [i for i in AT['items'] if '::ui_' not in i['k']]  # FACTCHECK R2: maintainer's own Shokk Drop imports never ship
CARDS = {k: v for k, v in D['cards']['cards'].items() if '::ui_' not in k}
MOODS, ERAS, USES, FITS = (D['cards'][k] for k in ('moods', 'eras', 'uses', 'fits'))
SCALE = ['', 'fine', 'medium', 'broad']
SECT = AT['sections']


def pick(v, ix): return [v[i] for i in (ix or []) if 0 <= i < len(v)]


def thumb(kind_dir, ident):
    p = os.path.join(ROOT, 'thumbnails', kind_dir, ident + '.png')
    return 'thumbnails/%s/%s.png' % (kind_dir, ident) if os.path.exists(p) else None


def card_fields(key):
    r = CARDS.get(key)
    if not r: return {}
    deep = r[18] if len(r) > 18 and isinstance(r[18], dict) else {}
    return dict(look=r[0], analog=r[1], syn=r[2], mood=pick(MOODS, r[3]), era=pick(ERAS, r[4]), fit=pick(FITS, r[5]), use=pick(USES, r[6]),
                loud=r[7], busy=r[8], pair=r[9], avoid=r[10], scale=SCALE[r[11]] if isinstance(r[11], int) and r[11] < 4 else '',
                ratings=dict(visible=r[12], appeal=r[13], body=r[14], accent=r[15], hero=r[16], risk=r[17]), deep=deep)


def lst(label, xs, n=6):
    xs = [clean(x) for x in (xs or []) if x]
    return '%s: %s.' % (label, ', '.join(xs[:n])) if xs else None


def flat(v):
    if isinstance(v, str): return v
    if isinstance(v, list): return '; '.join(flat(x) for x in v[:3] if x)
    if isinstance(v, dict): return '; '.join(flat(x) for x in list(v.values())[:2] if x)
    return ''


def items(v, n=2, m=170):
    if isinstance(v, str): v = [v]
    if isinstance(v, dict): v = list(v.values())
    out = []
    for x in (v or [])[:n]:
        x = flat(x) if not isinstance(x, str) else x
        x = cap(x[:1].upper() + x[1:], m) if x else ''
        if x: out.append(x)
    return out


def deep_bits(c):
    d = c.get('deep') or {}
    tips = items(d.get('p'), 2) + items(d.get('w'), 1)
    sv = d.get('s')
    if isinstance(sv, dict):
        for k, v in list(sv.items())[:1]: tips += items(v, 1, 150)
    pr = lst('Pairs well with', c.get('pair'))
    if pr: tips.append(pr)
    pits = items(d.get('n'), 2)
    av = lst('Avoid', c.get('avoid'), 4)
    if av: pits.append(av)
    return tips[:5], pits[:3]


def look_close_far(c):
    d = c.get('deep') or {}
    out = []
    if flat(d.get('c')): out.append('Up close: ' + cap(flat(d['c']), 300))
    if flat(d.get('f')): out.append('From a distance: ' + cap(flat(d['f']), 300))
    return out


def base_page(it, kind):
    c = card_fields(it['k'])
    ident = it['k'].split('::', 1)[1]
    look = c.get('look') or it.get('d') or ''
    return it, c, ident, look


def fnum(x, i=0):
    try: return x[i]
    except Exception: return None


# ---------------- finish pages ----------------
def finish_page(it):
    it, c, ident, look = base_page(it, 'finish')
    kind, _ = it['k'].split('::', 1)
    own = it.get('o')
    M, R, Cc = fnum(it.get('M')), fnum(it.get('R')), fnum(it.get('C'))
    _pin = PINNED.get(ident) if kind == 'base' else None
    _fixspec = None
    if _pin and M is not None and max(abs(M - _pin[0]), abs(R - _pin[1]), abs(Cc - _pin[2])) > 3:
        _fixspec = (M, R, Cc); M, R, Cc = _pin
    what = [clean(it.get('d') or '')]
    what += look_close_far(c)
    spec = 'Measured spec (average): metal %s, roughness %s, coat %s.' % (M, R, Cc) if M is not None else ''
    if it.get('shine') or it.get('metal'): spec += ' Shine: %s. Metal: %s.' % (it.get('shine', 'n/a'), it.get('metal', 'n/a'))
    what.append(spec.strip())
    what.append('It brings its own colours.' if own else 'It takes the colour you give the zone.')
    when = [x for x in (lst('Best on', c.get('use')), lst('Mood', c.get('mood')), lst('Era', c.get('era')), lst('Fits', c.get('fit'))) if x]
    nm = clean(it.get('n', ident))
    hidden = it['k'] in NOT_IN_PICKER
    if hidden:
        how = ['This finish is not listed in the Base Material picker, so you cannot pick it there.',
               'Open the AI copilot (the ✦ AI button, bottom right) and ask for it by name, for example "put %s on the hood".' % nm]
    else:
        how = ['Click the zone you want to change.', 'Click the BASE MATERIAL box (it says "Click to choose a base") and type "%s" in the SEARCH FINISHES box.' % nm,
               'Click it to open the big preview, then click Apply.']  # UI audit 2026-10-05: Classic picker has Apply; USE IT only exists in the Live picker, which has no switch
    how.append('Leave BASE COLOR on Use finish\'s own color to keep its colours.' if own else 'Pick your colour with BASE COLOR.')
    how.append('Render and judge it on the car, not on the swatch.')
    tips, pits = deep_bits(c)
    if c.get('scale'): tips.append('Texture size on the car: %s.' % c['scale'])
    shelves = [SECT[i] for i in it.get('s', []) if i < len(SECT)]
    pg = dict(title=nm, summary=fit_summary(look), what=cap(' '.join(w for w in what if w), 1100), when=when, how=how, controls=[], tips=tips, pitfalls=pits,
              related=[], actions=[{'do': 'finish', 'id': it['k']}], figures=[], covers=[], sources=[ATLAS_SRC, CARDS_SRC], quick=False, lane='B', updated=TODAY, generated=True)
    pg.update(key=it['k'], type=kind, shelves=[clean(s) for s in shelves], metal=M, rough=R, coat=Cc, palette=it.get('c', [])[:4], own_colours=bool(own),
              quality=it.get('q'), loud=c.get('loud'), busy=c.get('busy'), ratings=c.get('ratings'), mood=c.get('mood'), era=c.get('era'), use=c.get('use'), tags=it.get('t', [])[:8])
    if _fixspec:
        pg['what'] = pg['what'].replace('roughness about %s, clearcoat at max gloss about %s' % (_fixspec[1], _fixspec[2]), 'roughness %s, clearcoat %s' % (R, Cc))
    ex = V3.finish_extras(it, c, ident, shelves[0] if shelves else '', nm, bool(own), kind)
    if hidden:
        ex['examples'] = [{'title': 'Ask for it by name', 'goal': 'See %s on the car.' % nm, 'settings': {'AI copilot (✦ AI button)': 'put %s on the hood' % nm},
                           'result': 'The copilot puts the finish on a zone. It is not in the picker, so this is the way in.'}]
        pg['in_picker'] = False
        tips.append('Not listed in the picker: ask the AI copilot for it by name.')
        pg['tips'] = tips
    pg['sources'] = pg['sources'] + ex.pop('_src'); pg.update(ex)
    th = thumb('base' if kind == 'base' else 'monolithic', ident)
    if th: pg['thumb'] = th
    pg['swatch'] = '/api/swatch/%s/%s' % (kind, ident)
    return pg


def pattern_page(it):
    it, c, ident, look = base_page(it, 'pattern')
    nm = clean(it.get('n', ident)); g = clean(re.sub(r'^[^A-Za-z0-9]+', '', it.get('g') or 'Patterns'))
    what = [clean(it.get('d') or '')]
    what += look_close_far(c)
    what.append('Group: %s. Texture detail: %s.' % (g, it.get('fb', 'n/a')))
    when = [x for x in (lst('Best on', c.get('use')), lst('Mood', c.get('mood')), lst('Era', c.get('era'))) if x]
    how = ['Click a zone card and open the PATTERN section.', 'Click Pattern 1 on this Layer to open the picker.', 'Open the group "%s" or search for "%s", then click it.' % (g, nm),
           'Drag Scale below 1.00 until the repeats look fine on the car.', 'Switch Paint mode to Blend if you want to keep your paint colour.']
    tips, pits = deep_bits(c)
    pg = dict(title=nm, summary=fit_summary(look), what=cap(' '.join(w for w in what if w), 1100), when=when, how=how, controls=[], tips=tips, pitfalls=pits,
              related=[], actions=[{'do': 'pattern', 'id': ident}], figures=[], covers=[], sources=[ATLAS_SRC, CARDS_SRC], quick=False, lane='B', updated=TODAY, generated=True)
    pg.update(key=it['k'], group=g, quality=it.get('q'), coverage=it.get('cov'), contrast=it.get('con'), detail=it.get('fb'), loud=c.get('loud'), busy=c.get('busy'),
              ratings=c.get('ratings'), mood=c.get('mood'), era=c.get('era'), use=c.get('use'), tags=it.get('t', [])[:8])
    ex = V3.pattern_extras(it, c, ident, g, nm)
    pg['sources'] = pg['sources'] + ex.pop('_src'); pg.update(ex)
    th = thumb('pattern', ident)
    if th: pg['thumb'] = th
    pg['swatch'] = '/api/swatch/pattern/' + ident
    return pg


def spec_page(it):
    it, c, ident, look = base_page(it, 'spec')
    nm = clean(it.get('n', ident)); g = clean(re.sub(r'^[^A-Za-z0-9]+', '', it.get('g') or 'More spec patterns'))
    # UI audit 2026-10-05: the picker has two collections (Surface library / Legacy collection) with their own group headers; the atlas group is not what the reader sees.
    _ui = UI_SPEC.get(ident)
    if _ui: coll, g = _ui[0], clean(_ui[1])
    else: coll = None
    ch = it.get('ch')
    chs = ', '.join({'M': 'metal', 'R': 'roughness', 'C': 'clearcoat'}[x] for x in ch if x in 'MRC') if ch else 'the channels set by its defaults'
    what = [clean(it.get('d') or '')]
    what += look_close_far(c)
    what.append('It changes the shine only, never the colour. Channels it touches: %s. Group: %s%s. Texture detail: %s.' % (chs, g, (' (%s tab of the spec overlay picker)' % coll) if coll else '', it.get('fb', 'n/a')))
    when = [x for x in (lst('Best on', c.get('use')), lst('Mood', c.get('mood'))) if x]
    how = ['Click a zone card and expand SPEC OVERLAYS.', 'Click + ADD SPEC OVERLAY, ' + ('open the %s tab and the group "%s"' % (coll, g) if coll else 'open the group "%s"' % g) + ', or search for "%s".' % nm,
           'Click it, then click Add this overlay in the Inspect surface window.', 'Set Strength (default 50%) and tick the Metallic, Roughness and Clearcoat boxes you want.', 'Use Size and Rotation to make the texture finer, then render.']
    tips, pits = deep_bits(c)
    pg = dict(title=nm, summary=fit_summary(look), what=cap(' '.join(w for w in what if w), 1100), when=when, how=how, controls=[], tips=tips, pitfalls=pits,
              related=[], actions=[{'do': 'spec', 'id': ident}], figures=[], covers=[], sources=[ATLAS_SRC, CARDS_SRC], quick=False, lane='B', updated=TODAY, generated=True)
    pg.update(key=it['k'], group=g, channels=ch, quality=it.get('q'), coverage=it.get('cov'), contrast=it.get('con'), detail=it.get('fb'), loud=c.get('loud'), busy=c.get('busy'),
              ratings=c.get('ratings'), mood=c.get('mood'), use=c.get('use'), tags=it.get('t', [])[:8])
    ex = V3.spec_extras(it, c, ident, g, nm, ', '.join(x for x in (ch or '') if x in 'MRC') or 'as set by its defaults')
    pg['sources'] = pg['sources'] + ex.pop('_src'); pg.update(ex)
    th = thumb('spec_patterns', ident)
    if th: pg['thumb'] = th
    pg['swatch'] = '/api/swatch/spec/' + ident
    return pg


# ---------------- partition + write ----------------
def jdump(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def neighbours(members, pool, vec, k):
    """nearest k pool items (by feature distance) for each member; returns {key: [keys]}"""
    import numpy as np
    pk = [i['k'] for i in pool]
    X = np.array([vec(i) for i in pool], dtype=float)
    pos = {key: n for n, key in enumerate(pk)}
    out = {}
    for m in members:
        a = pos[m['k']]
        d = ((X - X[a]) ** 2).sum(1); d[a] = 1e18
        idx = np.argsort(d, kind='stable')[:min(k, len(pk) - 1)]
        out[m['k']] = [pk[j] for j in idx]
    return out


def write_atomic(path, text):
    if _H.mentions(text): raise SystemExit('enc_gen_B: output names a hidden feature (enc_hidden_features.json): ' + path)   # owner rule 2026-10-04
    if os.path.exists(path) and open(path, encoding='utf-8').read() == text: return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: f.write(text)
    os.replace(tmp, path)
    return True


def build(domain, stem_prefix, items, builder, grouper, group_order, vec, k_rel, note):
    groups = {}
    for it in items: groups.setdefault(grouper(it), []).append(it)
    order = sorted(groups, key=lambda g: (group_order(g), str(g)))
    # pass 1: pages + packing
    parts, pages_by_key = [], {}
    for g in order:
        its = sorted(groups[g], key=lambda i: i['k'])
        rel = neighbours(its, its if len(its) > k_rel else items, vec, k_rel)
        gs = slug(g if isinstance(g, str) else str(g))
        built = []
        for it in its:
            pg = builder(it); pg['_rel'] = rel[it['k']]
            built.append((pg, len(jdump(pg)) + 48 * k_rel + 170))
        total = sum(e for _, e in built)
        nparts = max(1, -(-total // (MAXB - 3500)))           # fewest parts that fit
        target = total / nparts                                  # balanced fill (no 35 + 1 splits)
        HARD = MAXB - 3500
        cur, size, n = [], 0, 1
        for pg, est in built:
            if cur and (size + est > HARD or (size + est > target and n < nparts)):
                parts.append(dict(stem='%s_%s_%d' % (stem_prefix, gs, n), group=g, items=cur)); n += 1; cur, size = [], 0
            cur.append(pg); size += est
        if cur: parts.append(dict(stem='%s_%s_%d' % (stem_prefix, gs, n), group=g, items=cur))
    # pass 2: ids + related
    key2id = {}
    for p in parts:
        for pg in p['items']:
            ident = pg['key'].split('::', 1)
            tag = ('mono' if pg.get('type') == 'monolithic' else ident[0]) if domain == 'finish_pages' else ident[0]
            pg['id'] = '%s.%s.%s' % (p['stem'], tag, safe_id(ident[1])); pg['domain'] = p['stem']; key2id[pg['key']] = pg['id']
    mparts, total_bytes, written = [], 0, 0
    for p in parts:
        arts = []
        for pg in p['items']:
            pg['related'] = [key2id[x] for x in pg.pop('_rel') if x in key2id]
            ordered = {k: pg[k] for k in ('id', 'title', 'domain', 'summary', 'what', 'when', 'how', 'controls', 'tips', 'pitfalls', 'related', 'actions', 'figures', 'covers', 'sources', 'quick', 'lane', 'updated', 'generated')}
            ordered.update({k: v for k, v in pg.items() if k not in ordered and (v not in (None, [], '') or k == 'screens')})
            arts.append(ordered)
        text = jdump({'domain': p['stem'], 'version': 1, 'articles': arts})
        b = len(text.encode('utf-8'))
        assert b <= 100 * 1024, (p['stem'], b)
        if write_atomic(os.path.join(PAGES, p['stem'] + '.json'), text): written += 1
        total_bytes += b
        mparts.append(dict(file=('' if FLAT else 'pages/') + p['stem'] + '.json', domain=p['stem'], group=clean(re.sub(r'^[^A-Za-z0-9]+', '', str(p['group']))), count=len(arts), bytes=b,
                           firstKey=arts[0]['key'], lastKey=arts[-1]['key']))
    keep = {p['stem'] + '.json' for p in parts}
    for fn in os.listdir(PAGES):   # drop stale parts of this set (a re-partition can change the count)
        if fn.startswith(stem_prefix + '_') and fn.endswith('.json') and fn not in keep and os.path.isfile(os.path.join(PAGES, fn)):
            os.remove(os.path.join(PAGES, fn))
    man = {'domain': domain, 'version': 1, 'articles': [], 'generated': True, 'note': note, 'pageCount': sum(m['count'] for m in mparts), 'bytes': total_bytes, 'parts': mparts}
    write_atomic(os.path.join(OUT, domain + '.json'), json.dumps(man, ensure_ascii=False, indent=1))
    return man, written


def main():
    fin = [i for i in ITEMS if i['k'].startswith(('base::', 'monolithic::'))]
    # FACTCHECK 2026-10-04: 'ui_*' patterns are the machine owner's own Shokk Drop imports that leaked into the atlas; nobody else has them.
    pat = [i for i in ITEMS if i['k'].startswith('pattern::') and not i['k'].startswith('pattern::ui_')]
    spc = [i for i in ITEMS if i['k'].startswith('spec::')]

    def fvec(i):
        return [fnum(i.get('M')) or 0, fnum(i.get('R')) or 0, (fnum(i.get('C')) or 0) * 0.5, (i.get('L') or 0) * 2.5, (i.get('S') or 0) * 2.5, (i.get('V') or 0) * 1.0, 40 * (i.get('o') or 0), (i.get('q') or 0) * 0.5]

    def pvec(i): return [(i.get('cov') or 0) * 2, (i.get('con') or 0) * 2, {'micro': 0, 'fine': 40, 'medium': 80, 'broad': 120}.get(i.get('fb'), 60), (i.get('q') or 0) * 0.5]

    res = {}
    res['finish'] = build('finish_pages', 'finish', fin, finish_page, lambda i: SECT[i['s'][0]] if i.get('s') else 'Other', lambda g: SECT.index(g) if g in SECT else 999, fvec, 4,
                          'One page per base and special (primary shelf = atlas item s[0]; parts of a shelf are sorted by key). Part files live in pages/.')
    res['pattern'] = build('pattern_pages', 'pattern', pat, pattern_page, lambda i: re.sub(r'^[^A-Za-z0-9]+', '', i.get('g') or 'Misc'), lambda g: g, pvec, 3,
                           'One page per pattern; grouped by pattern group (sorted by key inside a group). Part files live in pages/.')
    res['spec'] = build('spec_pattern_pages', 'specpat', spc, spec_page, lambda i: re.sub(r'^[^A-Za-z0-9]+', '', i.get('g') or 'More spec patterns'), lambda g: g, pvec, 3,
                        'One page per spec pattern (incl. the spov2 overlay set); grouped by spec group. Part files live in pages/.')
    for k, (m, w) in res.items():
        print('%-8s pages=%d parts=%d bytes=%d KB written=%d' % (k, m['pageCount'], len(m['parts']), m['bytes'] // 1024, w))
    print('cleaned fragments:', STATS['cleaned'])


if __name__ == '__main__':
    main()

"""Catalogue QA defect list, compiled mechanically from the 2026-10-03 deep cards.
Writes _atlas_deep/qa/*.json and docs/CATALOGUE_QA_2026-10-03.md. Read-only on everything else.
Usage: python scripts/ai_atlas/catalogue_qa.py
"""
import os, sys, json, glob, hashlib, re, collections
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
QA = os.path.join(ROOT, '_atlas_deep', 'qa'); os.makedirs(QA, exist_ok=True)
DOC = os.path.join(ROOT, 'docs', 'CATALOGUE_QA_2026-10-03.md')
STRIP = 24            # top label strip, cropped before hashing (checked by eye: 24 px on base, monolithic, spec, pattern)
FLAT_STD = 3.0        # left-panel grey std below this = flat paint, perceptual compare is meaningless
CORR_T_BM = 0.99      # base/monolithic near-duplicate: Pearson corr of z-scored 64x64 grey of the left panel
CORR_T_SP = 0.70      # spec/pattern near-duplicate: corr of high-passed, contrast-normalised 256x256 left half
TOPN = 300
TYPE_ORD = {'base': 0, 'monolithic': 1, 'pattern': 2, 'spec': 3}


def rj(p):
    return json.load(open(p, encoding='utf8'))


def load():
    us = []
    for f in sorted(glob.glob(os.path.join(ROOT, '_atlas_deep/shards/shard_*.json'))):
        us += rj(f)['units']
    cards = {}
    for f in sorted(glob.glob(os.path.join(ROOT, '_atlas_deep/out/shard_*.jsonl'))):
        for l in open(f, encoding='utf8'):
            l = l.strip()
            if l:
                d = json.loads(l); cards[d['u']] = d
    appeal = {}
    for l in open(os.path.join(ROOT, '_atlas_cards/ratings.jsonl'), encoding='utf8'):
        try:
            r = json.loads(l); appeal[r['k']] = int(r.get('appeal', 3))
        except Exception:
            pass
    items = rj(os.path.join(ROOT, '_atlas_cards/items.json'))
    return us, cards, appeal, items


def detail_feats(us):
    """Hash of the render minus label strip + a perceptual feature vector (zero-padded to 65536).
    base/monolithic: 64x64 grey of the LEFT ('default') panel.
    spec/pattern: left half (satin base) high-passed and local-contrast normalised at 256x256, so the
    shared diagonal highlight sweep does not make every spec look alike."""
    from scipy.ndimage import gaussian_filter as gf
    old = {}  # no on-disk cache: the padded feature matrix is >1 GB; recompute takes ~2 min
    ks, hs, fs = [], [], []
    for u in us:
        k = u['u']
        if k in old:
            h, f = old[k]
        else:
            try:
                im = Image.open(os.path.join(ROOT, u['img'])).convert('RGB')
                im = im.crop((0, STRIP, im.width, im.height))
                h = hashlib.md5(im.tobytes()).hexdigest()
                g = im.convert('L'); w, hh = g.size
                if u['type'] in ('base', 'monolithic'):
                    f = np.asarray(g.crop((0, 0, w // 2, hh)).resize((64, 64), Image.BILINEAR), dtype=np.float32)
                    f = np.pad(f.ravel(), (0, 65536 - 4096))
                else:
                    a = np.asarray(g.crop((0, 0, w // 2, hh)).resize((256, 256), Image.BILINEAR), dtype=np.float32)
                    d = a - gf(a, 3); s = np.sqrt(gf(d * d, 10)) + 1.0
                    f = (d / s).ravel()
            except Exception:
                h = 'MISSING'; f = np.zeros(65536, np.float32)
        ks.append(k); hs.append(h); fs.append(np.asarray(f, np.float32))
    return dict(zip(ks, hs)), dict(zip(ks, fs))


def uf_groups(keys, pairs):
    par = {k: k for k in keys}
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for a, b in pairs:
        par[find(a)] = find(b)
    g = collections.defaultdict(list)
    for k in keys:
        g[find(k)].append(k)
    return [v for v in g.values() if len(v) > 1]


def esc(s, n=230):
    s = re.sub(r'\s+', ' ', str(s if s is not None else '')).replace('|', '/').strip()
    return s if len(s) <= n else s[:n - 1] + '...'


PARTS = collections.OrderedDict()
SECTION_ROWS = {}
TYPE_COUNT = collections.defaultdict(collections.Counter)


def write_doc(header=''):
    with open(DOC, 'w', encoding='utf8') as f:
        f.write(header)
        for name, txt in PARTS.items():
            f.write(txt)


def table(rows, cols, cap=TOPN):
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for r in rows[:cap]:
        out.append('| ' + ' | '.join(esc(r.get(c, '')) for c in cols) + ' |')
    if len(rows) > cap:
        out.append('\n*...%d more rows in the JSON.*' % (len(rows) - cap))
    return '\n'.join(out) + '\n'


COL = r'(red|orange|yellow|gold|amber|green|teal|cyan|blue|navy|cobalt|purple|violet|lilac|magenta|pink|crimson|scarlet|brown|tan|bronze|copper|silver|grey|gray|black|white|cream|ivory|champagne|olive|khaki|lime|aqua|turquoise|rose|burgundy|maroon|emerald)'
SHIFT = r'(colou?r[- ]?(flip|shift)|flip|chameleon|hologra|iridesc|dichroic|duochrome|shifts? (colou?r|hue)|goniochrom|opalescen|prism)'
SCALEW = r'(faint|micro|tiny|subtle|bold|huge|giant|too small|much (bigger|smaller|larger)|chunky)'
BRANDS = ['billabong', 'freepik', 'vecteezy', 'shutterstock', 'getty', 'istock', 'nike', 'adidas', 'puma', 'red bull', 'redbull',
          'monster energy', 'rockstar', 'pepsi', 'coca', 'budweiser', 'bud light', 'miller lite', 'mobil 1', 'castrol', 'valvoline',
          'pennzoil', 'sunoco', 'martini', 'jagermeister', 'marlboro', 'camel', 'rolex', 'nascar', 'iracing', 'jack daniel', 'rayban',
          'oakley', 'fox racing', 'quiksilver', 'hurley', "o'neill", 'gucci', 'louis vuitton', 'chanel', 'burberry', 'nutella',
          'disney', 'marvel', 'pokemon', 'nintendo', 'blind']
DEFECTS = [('seam', r'\bseams?\b|tile seam|tiling seam|repeat seam'), ('mirror cross', r'mirror(ed)? (cross|axis|line)|symmetry (line|seam)'),
           ('parting line', r'parting line'), ('glitch strip', r'glitch (strip|band|stripe|line)'), ('tear line', r'tear line'),
           ('edge artefact', r'edge artefact|edge artifact|border artefact|artefact|artifact'),
           ('hard horizontal edge', r'hard (horizontal )?(edge|line|cut)|horizontal (edge|cut)'),
           ('credit/watermark', r'designed by|\bcredit\b|watermark|freepik|signature'), ('letterbox', r'letterbox|black bars?|border bars?'),
           ('stray box', r'stray (box|rectangle|square)')]


def main():
    us, cards, appeal, items = load()
    U = {u['u']: u for u in us}

    def ap(k):
        return appeal.get(k, appeal.get(U[k]['rep'], 3))

    def shelf(u):
        sh = u.get('shelves') or []
        return ', '.join(map(str, sh)) if sh else (u.get('lane') or '')

    def sortkey(r):
        return (TYPE_ORD.get(r['type'], 9), -r.get('appeal', 3), r['id'])

    def mk(k, finding, evidence, **x):
        u = U[k]
        r = dict(id=k.split('::', 1)[1], key=k, name=u['name'], type=u['type'], shelf=shelf(u), appeal=ap(k),
                 finding=finding, evidence=evidence)
        r.update(x); return r

    def finish_section(num, title, intro, rows, cols, tag, order=None):
        rows.sort(key=order or sortkey)
        json.dump(rows, open(os.path.join(QA, 's%d_%s.json' % (num, tag)), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
        SECTION_ROWS[num] = (title, rows)
        for r in rows:
            TYPE_COUNT[num][r['type']] += 1
        PARTS[num] = '\n## %d. %s  (%d rows)\n\n%s\n\n%s\n' % (num, title, len(rows), intro, table(rows, cols))
        write_doc('# Catalogue QA 2026-10-03 (in progress, sections written so far)\n')
        print('section', num, len(rows), flush=True)

    H, F = detail_feats(us)
    COLS = ['id', 'name', 'type', 'shelf', 'finding', 'evidence']

    # ---------------- 1. identical renders ----------------
    rows = []
    byh = collections.defaultdict(list)
    for u in us:
        byh[H[u['u']]].append(u['u'])
    gi = 0
    for h, ks in byh.items():
        if len(ks) < 2 or h == 'MISSING':
            continue
        gi += 1
        flat = bool(U[ks[0]]['type'] == 'base' and float(np.std(F[ks[0]][:4096])) < FLAT_STD)
        lst = ', '.join(x.split('::', 1)[1] for x in ks[:12]) + (' ...(+%d)' % (len(ks) - 12) if len(ks) > 12 else '')
        for k in ks:
            rows.append(mk(k, 'EXACT identical render (group E%d, %d members)%s' % (gi, len(ks), ', flat blank paint = spec-only unit' if flat else ''),
                           'md5 %s; with: %s' % (h[:10], lst), group='E%d' % gi, group_size=len(ks), flat=flat))
    near = []
    for kind, types, thr in (('A', ('base', 'monolithic'), CORR_T_BM), ('B', ('spec', 'pattern'), CORR_T_SP)):
        ks = [u['u'] for u in us if u['type'] in types and H[u['u']] != 'MISSING']
        n = 4096 if kind == 'A' else 65536
        X = np.stack([F[k][:n] for k in ks]); sd = X.std(1)
        ok = np.where(sd >= (FLAT_STD if kind == 'A' else 0.0))[0]
        Z = (X[ok] - X[ok].mean(1, keepdims=True)) / sd[ok, None]
        C = Z @ Z.T / n; np.fill_diagonal(C, 0)
        ii = np.argwhere(np.triu(C) >= thr)
        pairs = [(ks[ok[a]], ks[ok[b]]) for a, b in ii]
        pc = {(ks[ok[a]], ks[ok[b]]): float(C[a, b]) for a, b in ii}
        for grp in uf_groups(sorted({x for p in pairs for x in p}), pairs):
            if all(H[x] == H[grp[0]] for x in grp):
                continue
            near.append((grp, pc, thr))
    json.dump([g[0] for g in near], open(os.path.join(QA, 's1_near_groups.json'), 'w'), indent=1)
    for grp, pc, thr in near:
        gi += 1
        gs = set(grp)
        edges = [v for (a, b), v in pc.items() if a in gs and b in gs]
        lst = ', '.join(x.split('::', 1)[1] for x in grp[:12]) + (' ...(+%d)' % (len(grp) - 12) if len(grp) > 12 else '')
        for k in grp:
            rows.append(mk(k, 'NEAR-identical render (group N%d, %d members, min pair corr %.3f)' % (gi, len(grp), min(edges)),
                           'perceptual corr >= %.2f; with: %s' % (thr, lst), group='N%d' % gi, group_size=len(grp)))
    # real groups first, flat spec-only exact groups last
    def k1(r):
        return (r.get('flat', False), -r['group_size'], r['group']) + sortkey(r)
    finish_section(1, 'Identical renders',
        'Exact = md5 of the render with the top %d px label strip cropped. Near = perceptual, colour-independent (grey only, so recolours group): base/monolithic = z-scored 64x64 grey of the left "default" panel, Pearson corr >= %.2f (panels with std < %g skipped as flat); spec/pattern = left half high-passed + local-contrast-normalised at 256x256, corr >= %.2f. Groups are union-find chains, so a big near group may contain members that are only chain-similar (min pair corr is printed per row is the weakest linked edge). Exact groups flagged "flat" are blank-paint units whose only difference is spec numbers: not real defects. Sorted by group size (real groups first), then type and appeal.' % (STRIP, CORR_T_BM, FLAT_STD, CORR_T_SP),
        rows, ['group'] + COLS, 'identical', k1)

    # ---------------- 2. name/description contradicts render ----------------
    rows = []
    for u in us:
        k = u['u']; c = cards[k]; q = c['qa_fix'] or ''
        nm = (u['name'] or '').lower(); nmcols = set(re.findall(r'\b' + COL + r'\b', nm))
        hit = None
        if q.lower().startswith('unflagged, but'):
            hit = q
        else:
            for l in c['not']:
                ll = l.lower()
                if (len(nm) > 3 and nm in ll) or (nmcols and re.search(r'\b(' + '|'.join(nmcols) + r')\b', ll)):
                    hit = 'NOT line names own name/colour: ' + l; break
        if not hit:
            continue
        ql = hit.lower()
        subj = 'name/description/id' if re.search(r'\b(name|description|desc|id|called|title|tags?|filename|file id)\b', ql) else 'old card text'
        if re.search(SHIFT, ql) and re.search(r'(not visible|no (colou?r|shift|flip)|does not|doesn.t|never|only|single|flat|static|confirmed)', ql):
            cls = 'shift-claim'
        elif subj != 'old card text' and nmcols and re.search(r'\b' + COL + r'\b', ql):
            cls = 'colour'
        elif re.search(SCALEW, ql):
            cls = 'scale'
        elif re.search(r'\b' + COL + r'\b', ql) and re.search(r'(render (is|shows)|palette)', ql):
            cls = 'colour'
        else:
            cls = 'motif'
        rows.append(mk(k, '%s | %s' % (cls, subj), hit, cls=cls, subject=subj))
    finish_section(2, 'Name or description contradicts the render',
        'Source: cards whose qa_fix starts "unflagged, but", or whose "not" lines name the unit\'s own name / a colour in its name. Class by keyword regex on the card text: colour / motif / scale / shift-claim (heuristic, read the evidence). Subject "name/description/id" = the card says the NAME, description, id or tags is wrong; "old card text" = the card only corrects the previous AI card (lower owner priority). Sorted: name/description rows first, then type and appeal.',
        rows, COLS, 'name_vs_render', lambda r: (r['subject'] == 'old card text',) + sortkey(r))

    # ---------------- 3. palette / colour fields ----------------
    rows = []
    for u in us:
        k = u['u']; c = cards[k]
        blob = ' '.join([c['qa_fix'] or ''] + list(c['not']) + [c['look_close'] or ''])
        rx = r'(takes? (the |your )?colou?r|colou?r_on_takes|placeholder colou?r|preview colou?r|palette (says|shows|is))'
        m = re.search(r'.{0,110}' + rx + r'.{0,150}', blob, re.I | re.S)
        if not m:
            continue
        kind = 'palette contradicted' if re.search(r'palette (says|shows|is)', m.group(0), re.I) else 'takes your colour'
        rows.append(mk(k, kind, m.group(0), palette=u.get('palette'), colour_name=u.get('colour_name')))
    finish_section(3, 'Placeholder or misleading palette fields',
        'Cards that say the unit "takes your colour" (so the stored `palette` / `colour_name` is a placeholder swatch) or whose text says the palette contradicts the render. The unit palette and colour_name values are in the JSON.',
        rows, COLS, 'palette')

    # ---------------- 4. render defects ----------------
    rows = []
    for u in us:
        k = u['u']; c = cards[k]
        blob = ' '.join([c['qa_fix'] or '', c['variants_note'] or ''] + list(c['not']) + [c['look_close'] or '', c['look_far'] or ''])
        found = []
        for lab, rx in DEFECTS:
            m = re.search(r'.{0,90}(' + rx + r').{0,110}', blob, re.I | re.S)
            if not m:
                continue
            s = m.group(0)
            if re.search(r'\b(no|not|without|free of|never|nothing like)\b[^.]{0,25}(' + rx + ')', s, re.I):
                continue
            found.append((lab, s))
        if found:
            rows.append(mk(k, ', '.join(sorted({f[0] for f in found})), found[0][1], defects=[f[0] for f in found]))
    finish_section(4, 'Render defects',
        'Cards (qa_fix, not, look_close, look_far, variants_note) mentioning seam, mirror cross, parting line, glitch strip, tear line, edge artefact, hard horizontal edge, credit / "designed by", letterbox or stray box. Simple negation ("no seam") is skipped; false positives remain (e.g. "seam" as a design motif such as stitched seams), read the evidence.',
        rows, COLS, 'defects')

    # ---------------- 5. licence / naming ----------------
    rows = []; seen = set()

    def add5(k, finding, ev, cat):
        if (k, cat) in seen:
            return
        seen.add((k, cat)); rows.append(mk(k, finding, ev, cat=cat))
    brx = re.compile(r'\b(' + '|'.join(re.escape(b) for b in BRANDS) + r')\b', re.I)
    for u in us:
        k = u['u']; i = k.split('::', 1)[1]
        m = brx.search(i.replace('_', ' ')) or brx.search(u['name'] or '') or brx.search(u['desc'] or '')
        if m:
            add5(k, 'brand/licence word "%s"' % m.group(0), 'id=%s name=%s desc=%s' % (i, u['name'], u['desc']), 'brand')
        if re.fullmatch(r'\d{5,}(_\d+)?', i):
            add5(k, 'stock-asset numeric id (source/licence unknown)', 'id=%s name=%s' % (i, u['name']), 'stock-id')
        t = ' '.join([u['name'] or '', u['desc'] or '', str(u.get('lane') or ''), ' '.join(map(str, u.get('shelves') or [])), ' '.join(u.get('tags') or [])])
        if re.search(r'R1 REJECTED|R3 DEV|\bREJECTED\b|\bR[0-9] ?(DEV|REJECT)', t):
            add5(k, 'marked REJECTED / DEV but still in data', t[:200], 'rejected')
        cq = cards[k]['qa_fix'] or ''
        if re.search(r'(freepik|designed by|credit|watermark|trademark|licen[cs]e|brand name|real brand)', cq, re.I):
            add5(k, 'card mentions credit/brand/licence', cq, 'card-credit')
    low = collections.defaultdict(set)
    for it in items:
        low[it['k'].lower()].add(it['k'])
    for u in us:
        low[u['u'].lower()].add(u['u'])
    cases = [v for v in low.values() if len(v) > 1]
    for v in cases:
        for key in v:
            if key in U:
                add5(key, 'ids differ only by letter case (%s)' % ' vs '.join(sorted(v)), 'collides on a case-insensitive filesystem', 'case')
    json.dump(sorted(map(sorted, cases)), open(os.path.join(QA, 's5_case_collisions.json'), 'w'), indent=1)
    STOP = set('the a of and to in on for with by v1 v2 v3 base pattern spec monolithic'.split())

    def toks(s):
        return {w[:4] for w in re.split(r'[^a-z0-9]+', s.lower()) if len(w) > 2 and w not in STOP}
    for u in us:
        k = u['u']; i = k.split('::', 1)[1]
        if re.fullmatch(r'\d+(_\d+)?', i) or not u['name']:
            continue
        a, b = toks(i), toks(u['name'])
        parts = i.split('_')
        a2 = toks('_'.join(parts[1:])) if len(parts) > 2 else a
        if a and b and not (a & b) and not (a2 & b):
            cq = cards[k]['qa_fix'] or ''
            conf = bool(re.search(r'(\bid\b|file ?name)[^.]{0,40}(says|is)', cq, re.I))
            add5(k, 'id and display name share no word%s' % (' (card confirms)' if conf else ''), 'id=%s -> name="%s"' % (i, u['name']), 'id-name')
    for k in ('base::brushed_sparkle', 'monolithic::brushed_sparkle', 'spec::spec_polished_swirl_compound', 'monolithic::ferrari_rosso',
              'base::ferrari_rosso', 'monolithic::neon_pink_blaze', 'base::neon_pink_blaze'):
        if k in U:
            add5(k, 'owner-listed id/name mismatch', 'id=%s -> name="%s"' % (k.split('::')[1], U[k]['name']), 'id-name')

    def k5(r):
        pri = {'rejected': 0, 'brand': 1, 'case': 2, 'stock-id': 3, 'card-credit': 4}
        conf = 'card confirms' in r['finding'] or 'owner-listed' in r['finding']
        return (pri.get(r['cat'], 5 if conf else 6),) + sortkey(r)
    finish_section(5, 'Licence and naming',
        'Categories (field `cat`): rejected = still marked R1 REJECTED / R3 DEV; brand = brand/sponsor word in id/name/description (word list in script, BRANDS; note "blind" and "camel" can be plain words); case = ids colliding on a case-insensitive filesystem (checked over all %d items.json ids and the %d deep units; full list in s5_case_collisions.json); stock-id = numeric asset ids (freepik-style, licence unknown); card-credit = the card mentions credit/brand/licence; id-name = id and display name share no word (4-letter prefix match), card-confirmed and owner-listed ones first. id-name is a loose heuristic with false positives (collection prefix codes, abbreviations).' % (len(items), len(us)),
        rows, COLS, 'licence_naming', k5)

    # ---------------- 6. low confidence ----------------
    rows = []
    for u in us:
        k = u['u']; c = cards[k]
        if c['confidence'] is not None and int(c['confidence']) <= 2:
            rows.append(mk(k, 'confidence %s' % c['confidence'], c['qa_fix'] or '(no reason recorded in the card; qa_fix empty)', conf=c['confidence']))
    finish_section(6, 'Low-confidence cards',
        'Deep cards with confidence <= 2. The reason is the card\'s qa_fix text; some have none.', rows, COLS, 'low_conf')

    # ---------------- header ----------------
    s1 = SECTION_ROWS[1][1]
    eg = collections.Counter(r['group'] for r in s1 if r['group'].startswith('E') and not r.get('flat'))
    egflat = collections.Counter(r['group'] for r in s1 if r['group'].startswith('E') and r.get('flat'))
    ng = collections.Counter(r['group'] for r in s1 if r['group'].startswith('N'))
    top_exact = ', '.join('E%s=%d' % (g[1:], n) for g, n in eg.most_common(5))
    cc = collections.Counter(r['cls'] for r in SECTION_ROWS[2][1])
    c5 = collections.Counter(r['cat'] for r in SECTION_ROWS[5][1])
    hdr = ['# Catalogue QA 2026-10-03', '',
           'Generated mechanically by `scripts/ai_atlas/catalogue_qa.py` from the 4,722 deep cards (`_atlas_deep/out`), unit records (`_atlas_deep/shards`), renders (`_atlas_deep/img`) and `_atlas_cards/ratings.jsonl` (appeal). Full row sets: `_atlas_deep/qa/s*.json`. Tables show the top %d rows, ordered base, monolithic, pattern, spec, then by appeal (highest first). Read-only analysis; nothing in the catalogue was changed. Every finding is a mechanical flag from card text or render pixels, not an owner verdict.' % TOPN, '',
           '## Counts', '', '| Section | rows | base | monolithic | pattern | spec |', '|---|---|---|---|---|---|']
    for n in sorted(SECTION_ROWS):
        t, rr = SECTION_ROWS[n]
        hdr.append('| %d. %s | %d | %d | %d | %d | %d |' % (n, t, len(rr), TYPE_COUNT[n]['base'], TYPE_COUNT[n]['monolithic'], TYPE_COUNT[n]['pattern'], TYPE_COUNT[n]['spec']))
    hdr += ['', 'Section 1: %d exact groups (%d renders) plus %d flat spec-only exact groups (%d renders), %d near groups (%d renders). Section 2 classes: %s. Section 5 categories: %s.' % (
        len(eg), sum(eg.values()), len(egflat), sum(egflat.values()), len(ng), sum(ng.values()), dict(cc), dict(c5)), '',
        '## What to do first (by owner value)', '',
        '1. Section 1 groups containing base or monolithic ids with high appeal: keep one survivor per group, redo or retire the rest (uniqueness law). Biggest real exact groups: %s. Near groups: check with the similarity tab. Flat exact groups are spec-only units, not defects.' % top_exact,
        '2. Section 5 `rejected` rows: anything still marked R1 REJECTED / R3 DEV should leave the picker data.',
        '3. Section 2 rows with subject "name/description/id", classes colour and motif, base/monolithic first: rename or rebuild, this is "the name lies" for a buyer.',
        '4. Section 5 `case` rows: ids differing only by letter case break on case-insensitive filesystems; rename one of each pair.',
        '5. Section 5 `brand` and `stock-id` rows: licence review before the next release.',
        '6. Section 2 shift-claim rows: finishes selling a colour flip / hologram the render does not show.',
        '7. Section 4 render defects (seams, mirror crosses, glitch strips), base/monolithic first: visible on every car.',
        '8. Section 3: units whose stored palette is a placeholder; decide whether the picker swatch should be neutral.',
        '9. Section 6: low-confidence cards need a human look at the render (reason in each row).',
        '10. Section 5 `id-name` rows the card confirms or the owner listed: fix the display name or the id.', '']
    write_doc('\n'.join(hdr) + '\n')
    sz = os.path.getsize(DOC)
    json.dump({'sections': {n: len(SECTION_ROWS[n][1]) for n in SECTION_ROWS}, 'top_exact': eg.most_common(10),
               'near_groups': len(ng), 'doc_bytes': sz}, open(os.path.join(QA, 'summary.json'), 'w'), indent=1)
    print('doc bytes', sz)


if __name__ == '__main__':
    main()

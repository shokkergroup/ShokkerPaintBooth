"""DEEP CARDS plan: units (families) + shards for the card-writer fleet.   python scripts/ai_atlas/deep_plan.py [--stage 1]
  stage 1 = spec patterns + patterns only (no family grouping needed)  -> shards 001..
  default = everything (bases + monolithics grouped into colour-variant families, appended after)
Writes _atlas_deep/plan.json, _atlas_deep/shards/shard_NNN.json.  Pictures: thumbnails/<type>/<id>.png, _atlas_cards/thumbs/<type>__<id>.png (spec), else fetched
from the TEST server 59879 only into _atlas_deep/img/.  Read-only on _atlas_cards/*.
"""
import os, sys, json, re, time, math, collections, urllib.request, urllib.parse
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
AC = os.path.join(ROOT, '_atlas_cards')
OUT = os.path.join(ROOT, '_atlas_deep')
SHARDS = os.path.join(OUT, 'shards')
IMG = os.path.join(OUT, 'img')
BASE = os.environ.get('SPB_CARDS_SERVER', 'http://127.0.0.1:59879')
SHARD_MAX = 60
NUM = ['L', 'S', 'V', 'hs', 'hc', 'fb', 'an', 'M', 'R', 'C', 'sp', 'shine', 'metal', 'se', 'q']
CARD_KEEP = ['look', 'analog', 'syn', 'mood', 'use', 'pair', 'avoid', 'loud', 'busy', 'scale']
COL = set('red blue green yellow orange purple violet pink black white grey gray silver gold copper bronze teal cyan magenta crimson scarlet cobalt azure emerald lime amber indigo brown chrome navy aqua turquoise lavender rose ruby sapphire mint coral ivory charcoal maroon burgundy lilac olive tan beige cream platinum titanium steel graphite jade'.split())


def jl(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def rel(p):
    return os.path.relpath(p, ROOT).replace('\\', '/')


def pic(it):
    t, i = it['k'].split('::', 1)
    for p in (os.path.join(ROOT, 'thumbnails', t, i + '.png'), os.path.join(AC, 'thumbs', t + '__' + i + '.png'), os.path.join(IMG, t + '__' + i + '.png')):
        if os.path.exists(p):
            return p
    os.makedirs(IMG, exist_ok=True)
    p = os.path.join(IMG, t + '__' + i + '.png')
    try:
        if t == 'spec':
            url = '%s/api/spec-pattern-preview/%s' % (BASE, urllib.parse.quote(i))
        else:
            url = '%s/api/swatch/%s/%s?size=256&color=8a8f98' % (BASE, t, urllib.parse.quote(i))
        with urllib.request.urlopen(url, timeout=60) as r:
            open(p, 'wb').write(r.read())
        return p
    except Exception:
        return None


def px(p):
    try:
        return list(Image.open(p).size)
    except Exception:
        return None


def stem(it):
    n = it['n'].replace('�', '-')
    n = re.sub(r'\([^)]*\)', '', n)
    n = re.sub(r'\s+', ' ', n).strip(' -')
    w = n.lower().split()
    while len(w) > 1 and w[-1] in COL:
        w.pop()
    return ' '.join(w)


def build_units(items, cards, qa, types, group):
    units = []
    for t in types:
        L = [x for x in items if x['k'].split('::')[0] == t]
        if group and t in ('base', 'monolithic'):
            g = collections.defaultdict(list)
            for x in L:
                g[(stem(x), x.get('fb'), x.get('shine'))].append(x)   # same name stem AND same fineness + shine class = one construction
            fams = list(g.values())
        else:
            fams = [[x] for x in L]
        for m in fams:
            units.append((t, m))
    return units


def main():
    stage1 = '--stage' in sys.argv and sys.argv[sys.argv.index('--stage') + 1] == '1'
    items = json.load(open(os.path.join(AC, 'items.json'), encoding='utf-8'))
    cards = {c['k']: c for c in jl(os.path.join(AC, 'cards.jsonl'))}
    rt = {r['k']: r for r in jl(os.path.join(AC, 'ratings.jsonl'))}
    qa = {q['k']: q for q in json.load(open(os.path.join(AC, 'qa_flags.json'), encoding='utf-8'))}
    types = ['spec', 'pattern'] if stage1 else ['spec', 'pattern', 'base', 'monolithic']
    units = build_units(items, cards, qa, types, not stage1)
    recs = []
    for t, m in units:
        med = sorted(m, key=lambda x: x.get('L', 50))[len(m) // 2]
        # representative: median lightness member that has a picture
        rep = med
        p = pic(rep)
        if not p:
            for x in m:
                p = pic(x)
                if p:
                    rep = x
                    break
        c = cards.get(rep['k']) or {}
        flagged = [qa[x['k']] for x in m if x['k'] in qa]
        r = rt.get(rep['k'], {})
        short = rep['k'].split('::', 1)[1]
        if len(m) > 1:
            rep = dict(rep); rep['n'] = stem(rep).title() + ' (family of %d)' % len(m)
        rec = {'u': t + '::' + (short if len(m) == 1 else 'fam_' + re.sub(r'[^a-z0-9]+', '_', stem(rep)).strip('_') + '_' + short),
               'type': t, 'rep': rep['k'], 'members': [x['k'] for x in m], 'name': rep['n'], 'lane': rep.get('lane'), 'shelves': rep.get('shelves'),
               'desc': rep.get('d'), 'img': rel(p) if p else None, 'img_px': px(p) if p else None,
               'numbers': {k: rep.get(k) for k in NUM}, 'tags': rep.get('t'), 'palette': rep.get('c'), 'colour_name': rep.get('cn'),
               'card': {k: c.get(k) for k in CARD_KEEP if k in c},
               'qa': ({'rule': flagged[0]['rule'], 'detail': flagged[0]['detail'], 'keys': [f['k'] for f in flagged]} if flagged else None),
               'variants_note': ', '.join(x.get('cn') or x['n'] for x in m) if len(m) > 1 else '',
               'variants': [{'k': x['k'], 'n': x['n'], 'cn': x.get('cn'), 'c': x.get('c')} for x in m] if len(m) > 1 else [],
               '_ap': (r.get('appeal', 3) + r.get('hero', 3))}
        if not p:
            rec['no_picture'] = True
        recs.append(rec)
    shards, order = [], []
    for t in types:
        U = [r for r in recs if r['type'] == t]
        if t in ('base', 'monolithic'):
            U.sort(key=lambda r: (r['qa'] is None, -r['_ap'], r['name']))
        else:
            U.sort(key=lambda r: (r['qa'] is None, r['name']))
        order.append((t, U))
    # one family-pure type per shard run; balanced chunk sizes <= 60
    sid = 0
    os.makedirs(SHARDS, exist_ok=True)
    for t, U in order:
        n = len(U)
        k = max(1, math.ceil(n / SHARD_MAX))
        size = math.ceil(n / k)
        for i in range(k):
            ch = U[i * size:(i + 1) * size]
            if not ch:
                continue
            sid += 1
            name = 'shard_%03d' % sid
            for r in ch:
                r.pop('_ap', None)
            path = os.path.join(SHARDS, name + '.json')
            tmp = path + '.tmp'
            json.dump({'id': name, 'type': t, 'units': ch}, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
            os.replace(tmp, path)
            shards.append({'id': name, 'path': rel(path), 'n': len(ch), 'types': [t]})
    fam = collections.Counter(len(r['members']) for r in recs)
    plan = {'units': len(recs), 'shards': shards, 'families': sum(1 for r in recs if len(r['members']) > 1), 'no_picture': sum(1 for r in recs if r.get('no_picture')),
            'by_type': dict(collections.Counter(r['type'] for r in recs)), 'family_size_hist': dict(sorted(fam.items())),
            'stage': 1 if stage1 else 'full', 'made': time.strftime('%Y-%m-%d %H:%M')}
    tmp = os.path.join(OUT, 'plan.json.tmp')
    json.dump(plan, open(tmp, 'w', encoding='utf-8'), indent=1)
    os.replace(tmp, os.path.join(OUT, 'plan.json'))
    print('plan: %d units, %d shards, %d families, %d no_picture, %s' % (plan['units'], len(shards), plan['families'], plan['no_picture'], plan['by_type']))
    print('family hist', plan['family_size_hist'])
    sz = collections.Counter(tuple(r['img_px']) for r in recs if r['img_px'])
    print('img px', sz.most_common(6))


if __name__ == '__main__':
    main()

"""Fold validated deep cards (_atlas_deep/out/*.jsonl) into _atlas_cards/cards.jsonl for EVERY member of the unit's family.
  python scripts/ai_atlas/merge_deep_cards.py           # dry run: counts + 2 sample records
  python scripts/ai_atlas/merge_deep_cards.py --write   # backup cards.before_deep_<date>.jsonl, write via temp + os.replace
Per merged card: deep (the object minus u/rep/confidence), deep_conf, and the SEARCHABLE fields (the only ones build_cards_js.py ships and the BM25/LSA index reads:
look, syn, analog) are extended from the ORIGINAL values kept in look0 / syn0 (so re-running never grows them):
  look = look0 + ' ' + look_far          (look weight 2.0 in js/spb-ai-cards.js)
  syn  = syn0 + the asks phrases         (syn weight 3.0)
The 'not' phrases and avoid_asks are NOT added to the searchable text on purpose: 'not chrome: ...' would make a search for chrome hit this item (they stay in `deep`).
NOTE build_cards_js.py ships only look/analog/syn/mood/.../ratings, so `deep` itself stays data on disk until a JS change reads it."""
import os, sys, json, time, shutil, glob, importlib.util
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CARDS = os.path.join(ROOT, '_atlas_cards', 'cards.jsonl')
_spec = importlib.util.spec_from_file_location('deep_validate', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deep_validate.py'))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _opt(name):
    if name not in sys.argv:
        return None
    return [x.strip() for x in sys.argv[sys.argv.index(name) + 1].split(',') if x.strip()]


def _sid(x):
    x = str(x).replace('shard_', '').replace('.jsonl', '')
    return x.zfill(3) if x.isdigit() else x


def load_good():
    U = V.plan_units(); good = {}; bad = 0; low = 0
    only = _opt('--only'); excl = _opt('--exclude')
    only = set(_sid(x) for x in only) if only else None; excl = set(_sid(x) for x in excl) if excl else set()
    minc = int(_opt('--min-conf')[0]) if _opt('--min-conf') else 1
    for f in sorted(glob.glob(os.path.join(V.D, 'out', '*.jsonl'))):
        sid = _sid(os.path.basename(f))
        if (only is not None and sid not in only) or sid in excl:
            continue
        for l in open(f, encoding='utf-8'):
            if not l.strip():
                continue
            try:
                o = json.loads(l)
            except Exception:
                bad += 1; continue
            if isinstance(o, dict) and not V.check(o, U):
                if int(o.get('confidence') or 0) < minc:
                    low += 1; continue
                good[o['u']] = o
            else:
                bad += 1
    load_good.low = low
    return U, good, bad


def merged(card, o):
    c = dict(card)
    c.setdefault('look0', card.get('look', ''))
    c.setdefault('syn0', list(card.get('syn') or []))
    c['deep'] = {k: v for k, v in o.items() if k not in ('u', 'rep', 'confidence')}
    c['deep_conf'] = o['confidence']
    c['look'] = (c['look0'] + ' ' + o['look_far']).strip()
    seen = set(); syn = []
    for s in list(c['syn0']) + list(o['asks']):
        k = s.strip().lower()
        if k and k not in seen:
            seen.add(k); syn.append(s.strip())
    c['syn'] = syn
    return c


def main():
    U, good, bad = load_good()
    by_key = {}
    for u, o in good.items():
        for k in U[u]['members']:
            by_key[k] = o
    lines = [l for l in open(CARDS, encoding='utf-8') if l.strip()]
    out, n_new, n_same, samples = [], 0, 0, []
    for l in lines:
        c = json.loads(l)
        o = by_key.get(c.get('k'))
        if o:
            m = merged(c, o)
            if m == c:
                n_same += 1
            else:
                n_new += 1
            if len(samples) < 2:
                samples.append(m)
            c = m
        out.append(json.dumps(c, ensure_ascii=False))
    print('options: only=%s exclude=%s min-conf=%s; skipped below min-conf: %d' % (_opt('--only'), _opt('--exclude'), _opt('--min-conf'), load_good.low))
    from collections import Counter
    ty = Counter(); cf = Counter()
    for u, o in good.items():
        ty[U[u].get('type', '?')] += len(U[u]['members']); cf[o['confidence']] += 1
    print('cards by type', dict(ty), 'units by confidence', dict(sorted(cf.items())))
    print('valid deep units %d (invalid lines skipped %d) -> %d cards touched: %d changed, %d already current; total cards %d' % (len(good), bad, n_new + n_same, n_new, n_same, len(out)))
    for s in samples:
        print('SAMPLE', json.dumps({k: (v if k != 'deep' else {kk: str(vv)[:90] for kk, vv in list(v.items())[:5]}) for k, v in s.items()}, ensure_ascii=False)[:900])
    if '--write' not in sys.argv:
        print('dry run (use --write)'); return
    if not n_new:
        print('nothing to write'); return
    bk = os.path.join(os.path.dirname(CARDS), 'cards.before_deep_%s.jsonl' % time.strftime('%Y%m%d'))
    if not os.path.exists(bk):
        shutil.copyfile(CARDS, bk)
    tmp = CARDS + '.tmp'
    open(tmp, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    for _ in range(8):
        try:
            os.replace(tmp, CARDS); break
        except OSError:
            time.sleep(0.5)
    print('written', CARDS, 'backup', bk)


if __name__ == '__main__':
    main()

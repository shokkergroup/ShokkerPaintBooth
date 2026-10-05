"""Deterministic scorer for the INTRICATE-ASKS benchmark (no LLM).
   python scripts/ai_atlas/intricate_score.py [tag=baseline] [--compare other_tag]
   reads  _easy_claude_work/eval/intricate_<tag>.jsonl (from intricate_run.js) + scripts/ai_atlas/intricate_asks.json + js/spb-ai-atlas-data.js
   writes _easy_claude_work/eval/intricate_<tag>_score.json  (per-ask, per-class, overall; paths: offline = advisor reply, tool = suggest_finishes, any = best of the two per metric)
Metrics (each 0/1 or fraction; None = not applicable to that ask, excluded from means):
  base_hit      a returned base/monolithic item matches a base_class word            pattern_hit  a returned pattern:: item matches a pattern_class word
  spec_hit      a returned spec:: item matches a spec_class word                      stack_shape  returned layer kinds (base/pattern/spec) are a superset of the expected kinds (only asks expecting >=2 kinds)
  scale_hit     >=50% of returned items with a scale facet match the asked scale (fine=fine|micro, medium=medium, coarse=broad)
  parts_hit     fraction of expected part words found in the reply's target/part names or text
  must_not_ok   no returned item matches a must_not word (tags / name / colour name / shine)      askback_ok  expect.ask_back -> the reply asks a question (None when not expected)
  composite     mean of the applicable metrics of that ask
An item matches a class word when the word equals one of its tags / shine / colour name / shelf, or is a token of its name or one-line description."""
import json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
EV = os.path.join(ROOT, '_easy_claude_work', 'eval')
def _opt(n): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
ASKS = _opt('--asks'); SINCE = int(_opt('--since')) if _opt('--since') else None   # MSR-RUN: JSONL/JSON ask file + batch filter
_skip = {_opt('--compare'), ASKS, _opt('--since')} - {None}
args = [x for x in sys.argv[1:] if not x.startswith('--') and x not in _skip]
TAG = args[0] if args else 'baseline'
CMP = sys.argv[sys.argv.index('--compare') + 1] if '--compare' in sys.argv else None

txt = open(os.path.join(ROOT, 'js', 'spb-ai-atlas-data.js'), encoding='utf-8').read()
D = json.loads(txt[txt.index('{'):txt.rindex('}') + 1])
SECT = D.get('sections') or []
ITEM = {}
for i in D['items']:
    toks = set(re.findall(r'[a-z0-9]+', (i['n'] + ' ' + i.get('d', '')).lower()))
    feats = set(x.lower() for x in (i.get('t') or []))
    feats |= set(re.findall(r'[a-z]+', (i.get('cn') or '').lower()))
    if i.get('shine'): feats |= set(i['shine'].lower().replace('-', ' ').split()) | {i['shine'].lower()}
    for s in i.get('s') or []:
        if s < len(SECT): feats |= set(re.findall(r'[a-z]+', SECT[s].lower()))
    ITEM[i['k']] = (feats | toks, i.get('fb'))
SCALE = {'fine': {'fine', 'micro'}, 'medium': {'medium'}, 'coarse': {'broad'}}

def kind(k):
    p = k.split('::')[0]
    return 'base' if p in ('base', 'monolithic') else p
def has(key, words):
    f = ITEM.get(key, (set(), None))[0]
    return any(w.lower() in f for w in words)
def frac(xs): return None if not xs else sum(xs) / len(xs)

def score_path(ask, p):
    ex = ask['expect']; items = p.get('items', []); keys = [i['key'] for i in items]
    bk = [k for k in keys if kind(k) == 'base']; pk = [k for k in keys if kind(k) == 'pattern']; sk = [k for k in keys if kind(k) == 'spec']
    m = {}
    m['base_hit'] = (None if not ex['base_class'] else float(any(has(k, ex['base_class']) for k in bk)))
    m['pattern_hit'] = (None if ex['pattern_class'] == 'none' else float(any(has(k, ex['pattern_class']) for k in pk)))
    m['spec_hit'] = (None if ex['spec_class'] == 'none' else float(any(has(k, ex['spec_class']) for k in sk)))
    need = set()
    if ex['base_class']: need.add('base')
    if ex['pattern_class'] != 'none': need.add('pattern')
    if ex['spec_class'] != 'none': need.add('spec')
    got = set(kind(k) for k in keys)
    m['stack_shape'] = float(need <= got) if len(need) >= 2 else None
    if ex['scale']:
        fb = [ITEM[k][1] for k in keys if k in ITEM and ITEM[k][1]]
        m['scale_hit'] = float(bool(fb) and sum(1 for x in fb if x in SCALE[ex['scale']]) / len(fb) >= 0.5)
    else: m['scale_hit'] = None
    if ex['parts']:
        hay = (' '.join(p.get('parts') or []) + ' ' + str(p.get('part') or '') + ' ' + (p.get('text', '') if 'claimed' in p else '')).lower()   # tool path: only its inferred part counts (its text is generic lane help)
        m['parts_hit'] = sum(1 for x in ex['parts'] if x in hay) / len(ex['parts'])
    else: m['parts_hit'] = None
    if ex['must_not']:
        bad = [k for k in keys if has(k, ex['must_not'])]
        m['must_not_ok'] = float(not bad)
    else: m['must_not_ok'] = None
    m['askback_ok'] = float('?' in p.get('text', '')) if ex['ask_back'] else None
    ap = [v for v in m.values() if v is not None]
    # an empty reply (ask not claimed / no rows) can never score; metrics above already give 0 for hits, must_not/ask-back need the reply to exist
    if not keys: m['must_not_ok'] = 0.0 if ex['must_not'] else None; ap = [v for v in m.values() if v is not None]
    m['composite'] = frac(ap)
    m['n_items'] = len(keys); m['is_stack'] = float(len(got) > 1)
    return m

METRICS = ['base_hit', 'pattern_hit', 'spec_hit', 'stack_shape', 'scale_hit', 'parts_hit', 'must_not_ok', 'askback_ok', 'composite']
def mean(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return None if not v else sum(v) / len(v)

def build(tag):
    if ASKS:
        raw = open(ASKS, encoding='utf-8').read().strip()
        lst = json.loads(raw) if raw.startswith('[') else [json.loads(l) for l in raw.splitlines() if l.strip()]
        if SINCE is not None: lst = [a for a in lst if int(a.get('batch', 0) or 0) >= SINCE]
        asks = {a['id']: a for a in lst}
    else:
        asks = {a['id']: a for a in json.load(open(os.path.join(ROOT, 'scripts', 'ai_atlas', 'intricate_asks.json'), encoding='utf-8'))}
    rows = [json.loads(l) for l in open(os.path.join(EV, 'intricate_%s.jsonl' % tag), encoding='utf-8') if l.strip()]
    per = []
    for r in rows:
        if r['id'] not in asks: continue
        a = asks[r['id']]; off = score_path(a, r['offline']); tl = score_path(a, r['tool'])
        anyp = {k: (None if off[k] is None else max(off[k] or 0, tl[k] or 0)) for k in METRICS}
        anyp['composite'] = frac([v for k, v in anyp.items() if k != 'composite' and v is not None])
        per.append(dict(id=a['id'], cls=a['class'], ask=a['ask'], claimed=r['offline'].get('claimed', False), offline=off, tool=tl, any=anyp))
    out = dict(tag=tag, n=len(per), by_class={}, overall={})
    for path in ('offline', 'tool', 'any'):
        for cls in sorted(set(p['cls'] for p in per)) + ['ALL']:
            sub = [p[path] for p in per if cls == 'ALL' or p['cls'] == cls]
            out['by_class'].setdefault(cls, {})[path] = {k: mean(sub, k) for k in METRICS}
    n = len(per)
    out['overall'] = dict(offline_claimed_rate=sum(p['claimed'] for p in per) / n,
        offline_multi_layer_rate=mean([p['offline'] for p in per], 'is_stack'), tool_multi_layer_rate=mean([p['tool'] for p in per], 'is_stack'),
        stack_shape_offline=mean([p['offline'] for p in per], 'stack_shape'), stack_shape_tool=mean([p['tool'] for p in per], 'stack_shape'),
        composite_offline=mean([p['offline'] for p in per], 'composite'), composite_tool=mean([p['tool'] for p in per], 'composite'), composite_any=mean([p['any'] for p in per], 'composite'))
    out['per_ask'] = per
    return out

def f(x): return '  -  ' if x is None else '%.2f' % x
def table(out, title):
    print(title)
    for path in ('offline', 'tool', 'any'):
        print('  [%s]' % path)
        print('  %-15s' % 'class' + ''.join('%11s' % m[:10] for m in METRICS))
        for cls, v in out['by_class'].items():
            print('  %-15s' % cls + ''.join('%11s' % f(v[path][m]) for m in METRICS))
    print('  overall', {k: round(v, 3) for k, v in out['overall'].items()})

if __name__ == '__main__':
    out = build(TAG)
    json.dump(out, open(os.path.join(EV, 'intricate_%s_score.json' % TAG), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    table(out, 'TAG %s  (%d asks)' % (TAG, out['n']))
    if CMP:
        o2 = build(CMP)
        print('\nDELTA %s - %s (composite, any path / offline / tool)' % (TAG, CMP))
        for cls in out['by_class']:
            print('  %-15s' % cls + ' '.join('%+.3f' % ((out['by_class'][cls][p]['composite'] or 0) - (o2['by_class'][cls][p]['composite'] or 0)) for p in ('any', 'offline', 'tool')))

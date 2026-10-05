"""Automatic QA of the finish cards against the MEASURED numbers (no LLM, no cost).  2026-10-03 overnight run.
  python scripts/ai_atlas/qa_cards.py            # writes _atlas_cards/qa_flags.json + prints a summary with samples
Rules (each flag = {k, rule, detail}); a flag is a SUSPECT to look at, not a verdict:
  shine_vs_look   look claims gloss/mirror on a matte-ish item, or flat/matte on a mirror/gloss one
  metal_vs_look   look claims metal on metal=none (non-pattern), or "no metal/flake" on metal full/high
  colour_on_takes takes-colour item whose card names a colour that is not in the item's own name
  loud_outlier / busy_outlier   rating far from what the measured numbers predict (linear fit, residual >= 2)
  generic_syn     3+ search words that are generic ('pattern', 'design', ...)
  dup_look        identical look text on two cards
  thin            fewer than 8 search words / no mood / no use / no pair
  near_twin       two cards of one shelf whose look + search words overlap >= 0.75 (siblings the search cannot tell apart)
"""
import os, sys, json, re, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, '_atlas_cards')
items = {x['k']: x for x in json.load(open(os.path.join(OUT, 'items.json'), encoding='utf-8'))}
cards = {}
for l in open(os.path.join(OUT, 'cards.jsonl'), encoding='utf-8'):
    if l.strip():
        c = json.loads(l); cards[c['k']] = c
flags = []
def flag(k, rule, detail):
    flags.append({'k': k, 'rule': rule, 'detail': detail})

COLOUR = re.compile(r'\b(red|reddish|maroon|crimson|scarlet|burgundy|pink|rose|salmon|coral|brick|blue|green|yellow|orange|purple|violet|teal|cyan|magenta|gold|golden|copper|bronze|silver|tan|brown|beige|cream|ivory|lime|olive|navy)\b', re.I)
GLOSSY = re.compile(r'\b(mirror|high[- ]gloss|glossy|wet[- ]look|mirror-like|wet shine|wet highlight|glass-smooth|lacquer)\b', re.I)
FLATLY = re.compile(r'\b(dead[- ]flat|completely dull|no sheen|no shine|zero shine|chalk|absorbs light|dull matte|flat matte|flat black)\b', re.I)
MOVING = re.compile(r'\b(gradient|fad(?:e|es|ing)|to (?:dead-flat|matte|satin|gloss)|zones?|blend(?:s|ing)?|shift(?:s|ing)?|transitions?|from )\b', re.I)
METALCL = re.compile(r'\b(chrome|mirror metal|metal flake|metallic|brushed metal|steel|aluminium|aluminum|titanium|gunmetal|foil)\b', re.I)
NOMETAL = re.compile(r'\b(no (?:metal|metallic|flake|metal flake)|non-metallic|plain solid)\b', re.I)
GENERIC = {'pattern', 'design', 'finish', 'paint', 'look', 'color', 'colour', 'texture', 'surface', 'nice', 'cool', 'effect', 'style', 'special', 'unique', 'custom', 'modern', 'base', 'layer', 'detail', 'details'}

def is_base(k):
    return k.split('::')[0] in ('base', 'monolithic')

for k, c in cards.items():
    it = items.get(k) or {}
    look = c.get('look', '') or ''
    nm = (it.get('n') or '').lower()
    shine = it.get('shine'); metal = it.get('metal')
    if is_base(k):
        if GLOSSY.search(look) and shine in ('matte', 'semi-matte') and not MOVING.search(look):
            flag(k, 'shine_vs_look', 'look claims gloss, measured shine=%s: %s' % (shine, look[:90]))
        if FLATLY.search(look) and shine in ('mirror', 'high gloss') and not MOVING.search(look):
            flag(k, 'shine_vs_look', 'look claims flat, measured shine=%s: %s' % (shine, look[:90]))
        if METALCL.search(look) and metal == 'none' and shine != 'mirror' and not NOMETAL.search(look):
            flag(k, 'metal_vs_look', 'look claims metal, measured metal=none: %s' % look[:90])
        if NOMETAL.search(look) and metal in ('full', 'high'):
            flag(k, 'metal_vs_look', 'look says no metal, measured metal=%s: %s' % (metal, look[:90]))
    if is_base(k) and it.get('o') == 0:
        txt = look + ' ' + ' '.join(c.get('syn', [])) + ' ' + ' '.join(c.get('analog', []))
        bad = sorted({m.group(1).lower() for m in COLOUR.finditer(txt)} - set(re.findall(r'[a-z]+', nm)))
        if bad:
            flag(k, 'colour_on_takes', 'colour words %s on a takes-colour item: %s' % (bad[:4], look[:80]))
    g = [s for s in c.get('syn', []) if s.lower().strip() in GENERIC]
    if len(g) >= 3:
        flag(k, 'generic_syn', 'generic search words: %s' % g)
    if len(c.get('syn', [])) < 8 or not c.get('mood') or not c.get('use') or not c.get('pair'):
        flag(k, 'thin', 'syn=%d mood=%d use=%d pair=%d' % (len(c.get('syn', [])), len(c.get('mood', [])), len(c.get('use', [])), len(c.get('pair', []))))

# identical looks
by_look = collections.defaultdict(list)
for k, c in cards.items():
    by_look[re.sub(r'[^a-z0-9 ]+', '', (c.get('look', '') or '').lower()).strip()].append(k)
for lk, ks in by_look.items():
    if lk and len(ks) > 1:
        for k in ks:
            flag(k, 'dup_look', 'same look text as %s' % [x for x in ks if x != k][:2])

# loud / busy vs the measured numbers (linear fit on the numeric features; flags only when the fit is informative)
def feats(it):
    f = [1.0, (it.get('S') or 0) / 100, (it.get('V') or 0) / 100, (it.get('hs') or 0) / 100, (it.get('hc') or 0) / 8, (it.get('sp') or 0) / 100, abs((it.get('L') or 50) - 50) / 50, 1.0 if it.get('o') == 1 else 0.0]
    f += [1.0 if it.get('fb') == t else 0.0 for t in ('micro', 'fine', 'medium', 'broad')]
    f += [1.0 if it.get('metal') == t else 0.0 for t in ('low', 'medium', 'high', 'full')]
    f += [1.0 if it.get('shine') == t else 0.0 for t in ('satin', 'gloss', 'high gloss', 'mirror')]
    return f
keys = [k for k in cards if k in items and items[k].get('S') is not None]
X = np.array([feats(items[k]) for k in keys])
for tgt in ('loud', 'busy'):
    y = np.array([cards[k][tgt] for k in keys], dtype=float)
    w, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ w; res = y - pred; r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
    print('%s: linear fit R^2 = %.2f over %d items (residual sd %.2f)' % (tgt, r2, len(keys), res.std()))
    if r2 >= 0.25:
        for k, r, p in zip(keys, res, pred):
            if abs(r) >= 2.0:
                flag(k, tgt + '_outlier', '%s=%d but the numbers predict %.1f' % (tgt, cards[k][tgt], p))

# near twins inside a shelf
tok = lambda c: set(re.findall(r'[a-z]{3,}', ((c.get('look', '') or '') + ' ' + ' '.join(c.get('syn', []))).lower()))
shelf = collections.defaultdict(list)
for k in cards:
    it = items.get(k) or {}
    shelf[(k.split('::')[0], (it.get('shelves') or [''])[0])].append(k)
nt = 0
for sk, ks in shelf.items():
    if len(ks) > 400:
        continue
    T = {k: tok(cards[k]) for k in ks}
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = T[ks[i]], T[ks[j]]
            if a and b and len(a & b) / len(a | b) >= 0.75:
                nt += 1; flag(ks[i], 'near_twin', 'overlaps %s (%.2f)' % (ks[j], len(a & b) / len(a | b)))
json.dump(flags, open(os.path.join(OUT, 'qa_flags.json'), 'w', encoding='utf-8'))
cnt = collections.Counter(f['rule'] for f in flags)
print('cards', len(cards), 'flags', len(flags), 'cards flagged', len({f['k'] for f in flags}))
for r, n in cnt.most_common():
    print('  %-16s %5d' % (r, n))
if '--samples' in sys.argv:
    for r in cnt:
        print('\n##', r)
        for f in [x for x in flags if x['rule'] == r][:8]:
            print('  ', f['k'], '|', f['detail'][:150])

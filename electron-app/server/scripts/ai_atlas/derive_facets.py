"""Derive controlled-vocabulary facet tags (animal / fire / era / weather-light / material) from the deep cards.
   python scripts/ai_atlas/derive_facets.py            # dry run: counts + 5 examples per tag
   python scripts/ai_atlas/derive_facets.py --write    # backup cards.before_facets_20261003.jsonl, add `facets` + append to `syn` (idempotent)
Text read: deep.look_close, deep.look_far, item name (not the long atlas desc: too noisy). NEVER read: deep.not, deep.avoid_asks, avoid.
Any clause (split on . ; , ( ) ) containing a negator (no / not / never / without / isn't / instead of / unlike / rather than) is dropped first.
Then run build_cards_js.py (facets ride in `syn`, which the retrieval + LSA already use)."""
import json, os, re, sys, shutil, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CARDS = os.path.join(ROOT, '_atlas_cards', 'cards.jsonl')
BAK = os.path.join(ROOT, '_atlas_cards', 'cards.before_facets_20261003.jsonl')
ITEMS = os.path.join(ROOT, '_atlas_cards', 'items.json')
V = {
 # animal
 'snake': r'\bsnake(?!s?\s+(through|across|around|along))(skin|s)?\b|\bserpent|\bpython skin|\bcobra', 'scales': r'\bscaly\b|\bscales\b(?!\s+(with|to|up|down|the|by|as|from|across|so|when|if))',
 'leopard': r'\bleopard|\bcheetah|\bjaguar print', 'tiger': r'\btiger', 'zebra': r'\bzebra',
 'croc': r'\bcroc(odile)?\b|\bcrocodile|\balligator|\bgator\b', 'fish-scale': r'\bfish[- ]?scales?\b|\bkoi\b|\bmermaid|\bscalloped scales?',
 'dragon': r'\bdragon', 'feather': r'\bfeather',
 # fire
 'flames': r'\bflames?\b|\bflaming\b|\bflaming\b|\bblaze\b|\bblazing', 'fire': r'\bfire\b|\bfiery\b|\bburning\b|\bburnt\b|\binferno',
 'ember': r'\bembers?\b|\bsmolder', 'lava': r'\blava\b|\bmagma\b|\bmolten',
 # era
 '90s': r'\b(90s|1990s|nineties)\b', '80s': r'\b(80s|1980s|eighties)\b', 'synthwave': r'\bsynthwave|\bvaporwave|\boutrun\b|\bretrowave',
 'retro': r'\bretro\b', 'vintage': r'\bvintage\b', 'hot-rod': r'\bhot[- ]?rod|\brat rod|\bkustom|\bkandy\b',
 # weather / light
 'wet': r'\bwet\b|\bdripping\b|\bdroplets?\b', 'frosted': r'\bfrost(ed|y)?\b|\brime\b', 'frozen': r'\bfrozen\b|\bice\b|\bicy\b|\bglacier|\bglacial',
 'glow': r'\bglow(ing|s|ed)?\b|\bluminous\b|\bluminescen', 'neon': r'\bneon\b', 'rain': r'\brain(y|drops?|fall)?\b', 'dust': r'\bdust(y)?\b|\bdesert sand\b',
 # material
 'marble': r'\bmarble|\bmarbled', 'wood': r'\bwood(en|grain)?\b|\bwoodgrain', 'stone': r'\bstone\b|\bgranite\b|\bslate\b|\bconcrete\b',
 'glass': r'\bglass(y)?\b|\bstained[- ]glass', 'leather': r'\bleather\b|\bsuede\b', 'denim': r'\bdenim\b|\bjean\b',
 'carbon': r'\bcarbon[- ]?(fib(er|re)|weave|twill)?\b', 'weave': r'\bweave\b|\bwoven\b|\btwill\b|\bbasket ?weave|\bplaid\b',
}
RX = {k: re.compile(p, re.I) for k, p in V.items()}
NEG = re.compile(r"\b(no|not|never|without|isn't|isnt|nor|instead of|rather than|unlike|n't|none|neither|lacks?|zero)\b", re.I)
SPLIT = re.compile(r'[.;,()\n:\u2014]| - | but ')
def clean(text):
    return ' . '.join(c for c in SPLIT.split(text or '') if c.strip() and not NEG.search(c))
SIM = re.compile(r'\b(like|resembl\w*|reminds?|recalls?|as if|a bit of|echoes?|hint of)\b', re.I)
LIT = ('snake','scales','leopard','tiger','zebra','croc','fish-scale','dragon','feather','flames','fire','ember','lava')   # animals / fire: similes ("looks like a leopard") are analogies, not the item -> dropped
def tags_for(c, it):
    d = c.get('deep') or {}
    parts = [d.get('look_close'), d.get('look_far'), it.get('n')]
    txt = clean(' . '.join(p for p in parts if p))
    lit = ' . '.join(x for x in txt.split(' . ') if not SIM.search(x))
    return [k for k, rx in RX.items() if rx.search(lit if k in LIT else txt)], txt
PROVENANCE = '_facet_generator'

def update_card(card, tags):
    """Replace our prior additions while leaving unrelated card data alone.

    Older cards have no provenance. Their facet list was generated here, so it
    is refreshed; their syn entries are ambiguous, so they are preserved.
    """
    c = dict(card)
    prior = c.get(PROVENANCE) or {}
    old_syn = set(prior.get('syn') or [])
    syn = list(c.get('syn') or [])
    syn = [s for s in syn if s not in old_syn]
    have = {s.lower() for s in syn}
    added = [tag for tag in tags if tag.lower() not in have]
    c['facets'] = list(tags)
    c['syn'] = syn + added
    c[PROVENANCE] = {'syn': added}
    return c

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    W = '--write' in argv
    items = json.load(open(ITEMS, encoding='utf-8'))
    IM = {i['k']: i for i in items} if isinstance(items, list) else items
    # Always derive from the current cards. The dated backup is retained as a
    # recovery snapshot only; reading it here would discard later card edits.
    L = [json.loads(l) for l in open(CARDS, encoding='utf-8') if l.strip()]
    cnt = collections.Counter(); ex = collections.defaultdict(list); out = []
    for c in L:
        tg, txt = tags_for(c, IM.get(c['k'], {}))
        for t in tg:
            cnt[t] += 1
            if len(ex[t]) < 5: ex[t].append(c['k'])
        out.append(update_card(c, tg))
    for t in V: print('%-10s %4d  %s' % (t, cnt[t], ', '.join(ex[t])))
    print('cards with >=1 facet:', sum(1 for c in out if c.get('facets')), '/', len(out))
    if not W:
        print('dry run: current cards unchanged')
    if W:
        # Preserve the pre-write current catalog once for recovery. Never use
        # this snapshot as derivation input; it may predate later card edits.
        if not os.path.exists(BAK): shutil.copyfile(CARDS, BAK)
        tmp = CARDS + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            for c in out: f.write(json.dumps(c, ensure_ascii=False) + '\n')
        os.replace(tmp, CARDS); print('WROTE', CARDS)
if __name__ == '__main__':
    main()

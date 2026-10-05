#!/usr/bin/env python
"""Article builder for the Encyclopedia DESIGN IDEAS & STYLES part (domain "ideas", 2026-10-05).

Batch scripts (enc_ideas_b01.py ...) do:   from enc_ideas_build import *     then call  art(slug, title, ...)  once per article.
art() validates every finish / pattern / spec id against the picker-visible catalogue (enc_ideas.py), fills actions[] and sources[] from the
registry / catalogue lines, checks jargon + summary length + depth bar + alias collisions (dropped aliases are logged to
data/encyclopedia/_drafts/ideas_alias_dropped.txt), then writes ideas.json atomically (temp + os.replace) after EVERY article.
Resume = a batch script skips slugs already present (use  todo(slug)).
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc_ideas as E
from enc_ideas import FIN, VIS, PAT, SPEC, ROOT, load, add, have, finish_src, pat_src, spec_src, spec_of

TODAY = E.TODAY
UI_SRC = 'paint-booth-2-state-zones.js:1656'
DOC_DESIGN = 'docs/ai_knowledge/05_design_and_taste.md'
DOC_LIVERY = 'docs/ai_knowledge/08_livery_design.md'
DOC_RECIPES = 'docs/ai_knowledge/03_recipes.md'
JARGON = [re.compile(x, re.I) for x in (r'\b[\w-]+\.(?:js|py|jsx|ts|css|html|json|md|bat|ps1)\b', r'\\[A-Za-z]', r'(?:^|\s)/api/', r'\b\w+\(\)')]
JARGON2 = re.compile(r'\b(?:payload|endpoint|localStorage|sessionStorage|DOM|regex|JSON|inventory|handler|callback|refactor|SPB-\d+|TODO|FIXME|monkey-?patch|state machine|API call|stack trace)\b')
LOG = os.path.join(ROOT, 'data', 'encyclopedia', '_drafts', 'ideas_alias_dropped.txt')
from enc_ideas_plan import PLAN   # planned ids: related[] may point at any of them before it is written


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9#]+', ' ', re.sub(r"['’`]", '', str(s or '').lower()))).strip()


def _walk():
    base = os.path.join(ROOT, 'data', 'encyclopedia')
    for d, ds, fs in os.walk(base):
        ds[:] = [x for x in ds if x not in ('_drafts', 'figures', 'reader', 'screens')]
        for fn in fs:
            if not fn.endswith('.json') or fn.startswith('_') or fn == 'ideas.json':
                continue
            try:
                j = json.load(open(os.path.join(d, fn), encoding='utf-8'))
            except Exception:
                continue
            if isinstance(j, dict):
                for a in j.get('articles') or []:
                    yield a


_OTHER = None
_IDS = None
_SCREENS = None
_DOC_LINES = {}


def screens_ok(i):
    global _SCREENS
    if _SCREENS is None:
        j = json.load(open(os.path.join(ROOT, 'data', 'encyclopedia', 'screens.json'), encoding='utf-8'))
        _SCREENS = {x['id'] for x in j['screens']}
    return i in _SCREENS


def doc(file, phrase):
    """'file:line' of the first line containing phrase (for citing the knowledge cards)."""
    n = E.find_line(file, phrase)
    if not n:
        raise SystemExit('doc phrase not found: %s :: %s' % (file, phrase))
    return '%s:%d' % (file, n)


def sp(key):
    """buyer text for a finish spec: exact registry value when pinned, else the catalogue's measured average."""
    (m, r, c), how = spec_of(key)
    if how == 'pinned':
        return 'metal %d, roughness %d, coat %d' % (m, r, c)
    return 'about metal %d, roughness %d, coat %d (catalogue average)' % (m, r, c)


def nm(key):
    return FIN[key]['n']


def todo(slug):
    return not have('ideas.' + slug)


def _check_text(a):
    t = [a['title'], a['summary'], a['what']] + a['when'] + a['how'] + a['tips'] + a['pitfalls'] + a['aliases'] + a['protips']
    for d in a['deep']:
        t += [d['heading'], d['body']]
    for x in a['examples']:
        t += [x['title'], x['goal'], x['result']]
        for k, v in x['settings'].items():
            t += [k, str(v)]
    for c in a['combos']:
        t.append(c['why'])
    for q in a['faq']:
        t += [q['q'], q['a']]
    for m in a['mistakes']:
        t += [m['symptom'], m['cause'], m['fix']]
    bad = []
    for s in t:
        for r in JARGON:
            m = r.search(s)
            if m:
                bad.append(m.group(0))
        m = JARGON2.search(s)
        if m:
            bad.append(m.group(0))
        if re.search(r'easy.{0,12}mode|mode.{0,12}easy', s, re.I):
            bad.append('EASY MODE')
    return bad


def art(slug, title, summary, what, level, how, examples, deep, faq, mistakes, protips, aliases, fin=(), pat=(), spc=(), related=(), combos=(),
        screens=(), quick=False, when=(), tips=(), pitfalls=(), extra_src=()):
    global _OTHER, _IDS
    if _OTHER is None:
        _OTHER, _IDS = {}, set()
        for a in _walk():
            _IDS.add(a.get('id'))
            for al in a.get('aliases', []) or []:
                _OTHER.setdefault(al, a.get('id'))
    aid = 'ideas.' + slug
    actions, srcs = [], []
    for k in fin:
        if k not in VIS:
            raise SystemExit('%s: finish not picker-visible %s' % (aid, k))
        actions.append({'do': 'finish', 'id': k})
        srcs.append(finish_src(k) or 'js/spb-ai-atlas-data.js:2')
    for k in pat:
        if k not in PAT:
            raise SystemExit('%s: pattern not visible %s' % (aid, k))
        actions.append({'do': 'pattern', 'id': k})
        srcs.append(pat_src(k) or 'js/spb-ai-atlas-data.js:2')
    for k in spc:
        if k not in SPEC:
            raise SystemExit('%s: spec pattern not visible %s' % (aid, k))
        actions.append({'do': 'spec', 'id': k})
        srcs.append(spec_src(k) or 'js/spb-ai-atlas-data.js:2')
    srcs += list(extra_src) + [UI_SRC]
    seen = set()
    sources = [s for s in srcs if not (s in seen or seen.add(s))]
    al, dropped = [], []
    mine = {a2 for a in load()['articles'] if a['id'] != aid for a2 in a.get('aliases', [])}
    for a in aliases:
        n = norm(a)
        if not n or len(n) < 2 or n in al:
            continue
        if n in _OTHER or n in mine:
            dropped.append('%s :: %s (owned by %s)' % (aid, n, _OTHER.get(n) or 'another ideas article'))
            continue
        al.append(n)
    if dropped:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write('\n'.join(dropped) + '\n')
    for r in related:
        if r not in _IDS and r not in PLAN and not have(r):
            raise SystemExit('%s: related id not found %s' % (aid, r))
    for sc in screens:
        if not screens_ok(sc):
            raise SystemExit('%s: unknown screen %s' % (aid, sc))
    for x in examples:
        if x.get('screen') and not screens_ok(x['screen']):
            raise SystemExit('%s: unknown example screen' % aid)
    a = dict(id=aid, title=title, domain='ideas', summary=summary, what=what, when=list(when), how=how, controls=[], tips=list(tips), pitfalls=list(pitfalls),
             related=list(related), actions=actions, figures=[], covers=[], sources=sources, quick=bool(quick), lane='C', updated=TODAY, aliases=al, level=level,
             deep=deep, examples=examples, combos=[{'with': w, 'why': y} for w, y in combos], faq=faq, mistakes=mistakes, protips=protips, screens=list(screens))
    if len(summary) > 330 or len(re.findall(r'[.!?](\s|$)', summary)) > 2:
        raise SystemExit('%s: summary too long / too many sentences (%d chars)' % (aid, len(summary)))
    if len(how) < 3:
        raise SystemExit('%s: how needs 3 steps' % aid)
    for k, mn in (('deep', 2), ('examples', 2), ('faq', 3), ('mistakes', 2), ('protips', 1)):
        if len(a[k]) < mn:
            raise SystemExit('%s: %s needs >= %d' % (aid, k, mn))
    # ENC_READER_FIX 2026-10-05: a hand-picked screen must show the idea (the stealth guide showed the bright blue 'Abyss Blue' car)
    import enc_reader_fix as RF
    _sc = {x['id']: x for x in json.load(open(os.path.join(ROOT, 'data', 'encyclopedia', 'screens.json'), encoding='utf-8'))['screens']}
    RF.load_shelves()
    a['screens'] = [x for x in a.get('screens', []) if x not in _sc or RF.screen_ok(a, _sc[x])[0]]
    if not a['screens']:
        print('%s: no screen shows this idea (pictures are optional)' % aid)
    b = _check_text(a)
    if b:
        raise SystemExit('%s: jargon / hidden words %s' % (aid, b))
    add(a)
    print('wrote', aid, len(json.dumps(a, ensure_ascii=False, separators=(',', ':'))), 'bytes', ('| aliases dropped: %d' % len(dropped)) if dropped else '')


# ---- shared how-step wording (real button names, copied from the shipped recipes) ----
S_ZONE = 'Press + Add Zone, set COLOR to Remaining (or PICK COLOR FROM CAR on the colour to restyle), and tick Car Paint under RESTRICT TO LAYERS.'
S_BOX = 'Under APPLY AREA press Draw box and drag over the part on the flat sheet.'
S_BASE = 'Under BASE press Base Material, open FOUNDATIONS > Foundation Bases and choose %s.'
S_SEARCH = 'Under BASE press Base Material and search for %s.'
S_SOLID = 'Set BASE COLOR to Use solid color and enter the hex colour.'
S_SOURCE = 'Set BASE COLOR to Use source paint (spec only) so your colours stay exactly as they are and only the shine changes.'
S_OWN = "Leave BASE COLOR on Use finish's own color; the finish brings its own palette."
S_PATTERN = 'Open PATTERN, choose %s, set Paint mode to Blend so it keeps your base colour, and set Scale (pattern) to %s.'
S_OVERLAY = 'Open BASE > SPEC OVERLAYS, press + ADD SPEC OVERLAY, choose %s and set its Strength to %s.'
S_CHECK = 'Check the preview strip: R METAL, G ROUGH (dark is mirror), B COAT (16 is glossiest).'
S_RENDER = 'Press RENDER, then Ctrl+R in iRacing.'

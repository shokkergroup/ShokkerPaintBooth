"""enc_B_lib.py - Encyclopedia v2, lane B writer helpers (2026-10-04).
Append-safe authoring: add() validates one article and appends it to data/encyclopedia/_drafts/<domain>.jsonl
(skip if the id is already there); assemble() rewrites data/encyclopedia/<domain>.json atomically from the drafts.
Usage from an authoring script:  from enc_B_lib import *;  add('spec', id='spec.what_is', title=..., ...);  assemble('spec')
"""
import json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'data', 'encyclopedia')
DRAFTS = os.path.join(OUT, '_drafts')
os.makedirs(DRAFTS, exist_ok=True)
TODAY = '2026-10-04'
_inv = None
_lines = {}
_atlas = None


def inv():
    global _inv
    if _inv is None:
        d = json.load(open(os.path.join(ROOT, 'scripts', 'ai_atlas', 'enc_inventory.json'), encoding='utf-8'))
        _inv = d['records']
    return _inv


def inv_ids(domains=None, kinds=None, prefix=None):
    """inventory ids filtered by domain / kind / id prefix (used for covers[] so ids are never typed by hand)."""
    out = []
    for r in inv():
        if domains and r['domain'] not in domains: continue
        if kinds and r['kind'] not in kinds: continue
        if prefix and not r['id'].startswith(prefix): continue
        out.append(r['id'])
    return out


def inv_has(i):
    return any(r['id'] == i for r in inv())


def nlines(path):
    if path not in _lines:
        try:
            t = open(os.path.join(ROOT, path), encoding='utf-8', errors='replace').read()
            _lines[path] = len(t.split('\n')) - (1 if t.endswith('\n') else 0)
        except Exception:
            _lines[path] = -1
    return _lines[path]


def norm(s):
    s = s.lower().replace("'", '').replace('’', '')
    s = re.sub(r'[^a-z0-9#]+', ' ', s)
    return s.strip()


def atlas_keys():
    global _atlas
    if _atlas is None:
        p = os.path.join(DRAFTS, '_dumpB.json')
        if not os.path.exists(p):
            import subprocess
            subprocess.check_call(['node', os.path.join(ROOT, 'scripts', 'ai_atlas', 'enc_gen_B_dump.js'), p], cwd=ROOT)
        d = json.load(open(p, encoding='utf-8'))
        _atlas = {i['k'] for i in d['atlas']['items']}
    return _atlas


JARGON = [re.compile(x) for x in (r'\b[\w-]+\.(?:js|py|jsx|ts|css|html|json|md|bat|ps1)\b', r'\\[A-Za-z]', r'(?:^|\s)/api/', r'\b\w+\(\)',
                                  r'\b(?:payload|endpoint|localStorage|sessionStorage|DOM|regex|JSON|inventory|handler|callback|refactor|SPB-\d+|TODO|FIXME|state machine|API call|stack trace)\b')]


def check(a):
    errs = []
    for k in ('id', 'title', 'summary', 'what'):
        if not a.get(k, '').strip(): errs.append('empty ' + k)
    if len(re.findall(r'[.!?](\s|$)', a['summary'])) > 2 or len(a['summary']) > 330: errs.append('summary too long')
    if a.get('quick') and len(a['how']) < 3: errs.append('quick needs 3 how steps')
    for s in a['sources']:
        m = re.match(r'^([A-Za-z0-9_.\-/]+):(\d+)(?:-(\d+))?$', s)
        if m:
            n = nlines(m.group(1))
            if n < 0 or int(m.group(2)) > n or (m.group(3) and int(m.group(3)) > n): errs.append('bad source ' + s)
        elif not re.match(r'^SPB_WIKI\.html#[A-Za-z0-9_]+$', s): errs.append('bad source form ' + s)
    for c in a['covers']:
        if not inv_has(c): errs.append('unknown cover ' + c)
    for c in a['controls']:
        if c.get('inv') and not inv_has(c['inv']): errs.append('unknown control inv ' + c['inv'])
    for x in a['actions']:
        if x['do'] == 'finish' and x['id'] not in atlas_keys(): errs.append('unknown finish ' + x['id'])
        if x['do'] == 'pattern' and 'pattern::' + x['id'] not in atlas_keys(): errs.append('unknown pattern ' + x['id'])
        if x['do'] == 'spec' and 'spec::' + x['id'] not in atlas_keys(): errs.append('unknown spec ' + x['id'])
    txt = [a['title'], a['summary'], a['what']] + a['when'] + a['how'] + a['tips'] + a['pitfalls']
    for c in a['controls']: txt += [c.get('label', ''), c.get('range', ''), c.get('default', ''), c.get('effect', '')]
    for t in txt:
        for r in JARGON:
            m = r.search(t or '')
            if m: errs.append('jargon "%s"' % m.group(0))
    for al in a.get('aliases', []):
        if al != norm(al): errs.append('alias not normalised: ' + al)
    return errs


def add(domain, **kw):
    a = dict(id='', title='', domain=domain, summary='', what='', when=[], how=[], controls=[], tips=[], pitfalls=[], related=[], actions=[],
             figures=[], covers=[], sources=[], quick=False, lane='B', updated=TODAY)
    a.update(kw)
    a['domain'] = domain
    if not a['id'].startswith(domain + '.'): raise SystemExit('id prefix: ' + a['id'])
    errs = check(a)
    if errs:
        print('REJECT', a['id'], errs)
        return False
    p = os.path.join(DRAFTS, domain + '.jsonl')
    have = set()
    if os.path.exists(p):
        for l in open(p, encoding='utf-8'):
            if l.strip(): have.add(json.loads(l)['id'])
    if a['id'] in have:
        print('skip (exists)', a['id'])
        return True
    with open(p, 'a', encoding='utf-8') as f:
        f.write(json.dumps(a, ensure_ascii=False) + '\n')
    print('ok', a['id'])
    return True


V3_KEYS = ('level', 'deep', 'examples', 'combos', 'faq', 'mistakes', 'protips', 'screens')
import enc_hidden as _H


def check_v3(domain, aid, f):
    errs = []
    ne = lambda x: isinstance(x, str) and x.strip()
    if f.get('level') not in ('beginner', 'intermediate', 'pro'): errs.append('level')
    if len(f.get('deep', [])) < 2 or not all(ne(x.get('heading')) and ne(x.get('body')) for x in f.get('deep', [])): errs.append('deep>=2')
    ex = f.get('examples', [])
    if len(ex) < 2 or not all(ne(x.get('title')) and ne(x.get('goal')) and ne(x.get('result')) and x.get('settings') for x in ex): errs.append('examples>=2')
    if len(f.get('faq', [])) < 3 or not all(ne(x.get('q')) and ne(x.get('a')) for x in f.get('faq', [])): errs.append('faq>=3')
    if len(f.get('mistakes', [])) < 2 or not all(ne(x.get('symptom')) and ne(x.get('cause')) and ne(x.get('fix')) for x in f.get('mistakes', [])): errs.append('mistakes>=2')
    if len(f.get('protips', [])) < 1: errs.append('protips>=1')
    for c in f.get('combos', []):
        if not (ne(c.get('with')) and ne(c.get('why'))) or c['with'] == aid: errs.append('combo ' + str(c.get('with')))
    txt = []
    for d in f.get('deep', []): txt += [d.get('heading', ''), d.get('body', '')]
    for x in ex:
        txt += [x.get('title', ''), x.get('goal', ''), x.get('result', '')]
        for k, v in (x.get('settings') or {}).items(): txt += [k, str(v)]
    for c in f.get('combos', []): txt.append(c.get('why', ''))
    for q in f.get('faq', []): txt += [q.get('q', ''), q.get('a', '')]
    for m in f.get('mistakes', []): txt += [m.get('symptom', ''), m.get('cause', ''), m.get('fix', '')]
    txt += f.get('protips', [])
    for t in txt:
        for r in JARGON:
            m = r.search(t or '')
            if m: errs.append('jargon "%s"' % m.group(0))
        if _H.mentions(t or ''): errs.append('hidden feature wording: ' + (t or '')[:50])
    return errs


def _v3path(domain): return os.path.join(DRAFTS, domain + '_v3.json')


def _v3load(domain):
    p = _v3path(domain)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def enrich(domain, aid, sources=None, **f):
    """Attach v3 depth fields (level, deep, examples, combos, faq, mistakes, protips, screens) to an existing article.
    Stored in _drafts/<domain>_v3.json (id -> fields, replace semantics) and merged by assemble(). sources = extra sources to union in."""
    errs = check_v3(domain, aid, f)
    for s in (sources or []):
        m = re.match(r'^([A-Za-z0-9_.\-/]+):(\d+)(?:-(\d+))?$', s)
        if m:
            n = nlines(m.group(1))
            if n < 0 or int(m.group(2)) > n or (m.group(3) and int(m.group(3)) > n): errs.append('bad source ' + s)
        elif not re.match(r'^SPB_WIKI\.html#[A-Za-z0-9_]+$', s): errs.append('bad source form ' + s)
    if errs:
        print('REJECT-V3', aid, errs); return False
    d = _v3load(domain)
    d[aid] = dict(f, _sources=sources or [])
    tmp = _v3path(domain) + '.tmp'
    json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(tmp, _v3path(domain))
    print('ok-v3', aid)
    return True


def assemble(domain):
    p = os.path.join(DRAFTS, domain + '.jsonl')
    arts = []
    seen = set()
    for l in open(p, encoding='utf-8'):
        if l.strip():
            a = json.loads(l)
            if a['id'] not in seen:
                seen.add(a['id']); arts.append(a)
    scp = os.path.join(OUT, 'screens.json')
    attach = {}
    if os.path.exists(scp):   # lane S publishes real app screenshots; attach those that name one of my articles
        for r in json.load(open(scp, encoding='utf-8')).get('screens', []):
            for aid in r.get('article_ids', []) or []: attach.setdefault(aid, []).append(r['id'])
    v3 = _v3load(domain)
    for a in arts:
        f = v3.get(a['id'])
        if f:
            for k, v in f.items():
                if k == '_sources':
                    a['sources'] = list(dict.fromkeys(a['sources'] + v))
                else: a[k] = v
            a['updated'] = TODAY
        if a['id'] in attach: a['screens'] = list(dict.fromkeys(a.get('screens', []) + attach[a['id']]))
    import enc_ui_fix; enc_ui_fix.fix_articles(arts)   # UI audit 2026-10-05: wording must equal the labels the live app shows
    out = os.path.join(OUT, domain + '.json')
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'domain': domain, 'version': 1, 'articles': arts}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    print('assembled %s: %d articles, %d KB' % (domain, len(arts), os.path.getsize(out) // 1024))

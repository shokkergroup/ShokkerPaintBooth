#!/usr/bin/env python
"""Encyclopedia v2, lane C writer helper (2026-10-04).
Append-safe article writer: every call loads data/encyclopedia/<domain>.json, upserts ONE article (by id) and writes it back atomically
(temp file + os.replace), so a crash never loses finished articles. Content files (data/encyclopedia/_drafts/C_*.py) call A(...) once per article.
Aliases are normalised exactly like scripts/ai_atlas/enc_extract.js norm(): lowercase, delete ' and the curly apostrophe, every other run outside a-z 0-9 # -> one space.
"""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / 'data' / 'encyclopedia'
TODAY = '2026-10-04'


def norm(s):
    s = str(s or '').lower().replace("'", '').replace('’', '').replace('`', '')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9#]+', ' ', s)).strip()


def _other_aliases(my_id):
    """alias -> owner id for every article in every domain file except my own id (the gate demands unique aliases across lanes)."""
    out = {}
    for p in list(DIR.glob('*.json')) + list((DIR / 'pages').glob('*.json')):
        if p.name.startswith('_') or p.stem in ('manifest', 'graphics'):
            continue
        try:
            doc = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        for a in doc.get('articles', []):
            if not isinstance(a, dict) or a.get('id') == my_id:
                continue
            for al in a.get('aliases', []) or []:
                out.setdefault(al, a.get('id'))
    return out


def _load(domain):
    p = DIR / (domain + '.json')
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return {'domain': domain, 'version': 1, 'articles': []}


def _save(domain, doc):
    DIR.mkdir(parents=True, exist_ok=True)
    p = DIR / (domain + '.json')
    tmp = p.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    os.replace(tmp, p)


def A(domain, slug, title, summary, what, when=None, how=None, controls=None, tips=None, pitfalls=None, related=None,
      actions=None, figures=None, covers=None, sources=None, quick=False, aliases=None, generated=False):
    """Upsert one article. id = '<domain>.<slug>'. sources are 'file:line' (or 'SPB_WIKI.html#section')."""
    art = {
        'id': domain + '.' + slug, 'title': title, 'domain': domain, 'summary': summary, 'what': what,
        'when': when or [], 'how': how or [], 'controls': controls or [], 'tips': tips or [], 'pitfalls': pitfalls or [],
        'related': related or [], 'actions': actions or [], 'figures': figures or [], 'covers': covers or [],
        'sources': sources or [], 'quick': bool(quick), 'lane': 'C', 'updated': TODAY,
    }
    if aliases:
        taken = _other_aliases(art['id'])
        seen, dropped = [], []
        for a in aliases:
            n = norm(a)
            if not n or n in seen:
                continue
            if n in taken:
                dropped.append(n + ' (on ' + taken[n] + ')')
                continue
            seen.append(n)
        art['aliases'] = seen
        if dropped:
            with open(DIR / '_drafts' / 'C_alias_dropped.txt', 'a', encoding='utf-8') as fh:
                fh.write(art['id'] + ': ' + '; '.join(dropped) + chr(10))
    if generated:
        art['generated'] = True
    doc = _load(domain)
    arts = [a for a in doc['articles'] if a.get('id') != art['id']]
    arts.append(art)
    doc['articles'] = arts
    _save(domain, doc)
    return art['id']


def C(label, rng='', default='', effect='', inv=None):
    c = {'label': label, 'range': rng, 'default': default, 'effect': effect}
    if inv:
        c['inv'] = inv
    return c


def F(kind, id_):
    return {'do': kind, 'id': id_}

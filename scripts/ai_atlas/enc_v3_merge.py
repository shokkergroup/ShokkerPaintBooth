#!/usr/bin/env python
"""Encyclopedia v3 (lane C, 2026-10-04): merge the depth drafts into the hand-written articles.
Drafts: scripts/ai_atlas/enc_C_drafts/V3_<domain>.py, each defines  V3 = { '<article id>': { level, deep[], examples[], combos[], faq[], mistakes[], protips[], screens[]?,
        tips_add[], pitfalls_add[], how_replace[], related_add[], sources_add[], aliases_add[] } }.
Idempotent: new fields are SET (not appended), *_add lists are appended only when missing. Atomic write per domain file (via enc_write_C._load/_save).
Checks every new string for dev jargon + hidden-feature names and prints the depth-bar shortfall per article.   python enc_v3_merge.py [domain ...] [--check]
"""
import importlib.util, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enc_write_C as W
import enc_hidden as H

JARGON = [re.compile(r, re.I if i else 0) for r, i in [(r'\b[\w-]+\.(?:js|py|jsx|ts|css|html|json|md|bat|ps1)\b', 1), (r'\[A-Za-z]', 0), (r'(?:^|\s)/api/', 1), (r'\b\w+\(\)', 0),
          (r'\b(?:payload|endpoint|localStorage|sessionStorage|DOM|regex|JSON|inventory|handler|callback|refactor|SPB-\d+|TODO|FIXME|monkey-?patch|state machine|API call|stack trace)\b', 0), (r'\bC:\|\bE:\|/Users/', 0)]]
SET = ['level', 'deep', 'examples', 'combos', 'faq', 'mistakes', 'protips', 'screens']
BAR = {'deep': 2, 'examples': 2, 'faq': 3, 'mistakes': 2, 'protips': 1}


def strings(o):
    if isinstance(o, str): yield o
    elif isinstance(o, dict):
        for v in o.values(): yield from strings(v)
    elif isinstance(o, list):
        for v in o: yield from strings(v)


def check_text(aid, new):
    bad = []
    for s in strings(new):
        if H.mentions(s): bad.append('hidden: ' + s[:60])
        for r in JARGON:
            m = r.search(s)
            if m: bad.append('jargon "%s" in: %s' % (m.group(0), s[:70]))
    return bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    files = sorted(HERE.glob('enc_C_drafts/V3_*.py'))
    tot = fixed = 0
    for f in files:
        dom = f.stem[3:]
        if args and dom not in args: continue
        spec = importlib.util.spec_from_file_location(f.stem, f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        doc = W._load(dom); byid = {a['id']: a for a in doc['articles']}; short = []
        for aid, d in m.V3.items():
            a = byid.get(aid)
            if a is None: print('MISSING article', aid); continue
            bad = check_text(aid, {k: v for k, v in d.items() if k not in ('sources_add', 'related_add')})
            if bad: print('TEXT', aid, ' | '.join(bad[:3])); continue
            for k in SET:
                if k in d: a[k] = d[k]
            for k, tgt in (('tips_add', 'tips'), ('pitfalls_add', 'pitfalls'), ('related_add', 'related'), ('sources_add', 'sources'), ('aliases_add', 'aliases')):
                for x in d.get(k, []):
                    a.setdefault(tgt, [])
                    if x not in a[tgt]: a[tgt].append(x)
            if 'how_replace' in d: a['how'] = d['how_replace']
            miss = [k + ':%d/%d' % (len(a.get(k) or []), n) for k, n in BAR.items() if len(a.get(k) or []) < n]
            if len(a.get('how') or []) < 3: miss.append('how<3')
            if miss: short.append(aid + ' ' + ','.join(miss))
            tot += 1
        for a in doc['articles']:
            if a['id'] not in m.V3: short.append(a['id'] + ' (no v3 draft)')
        if '--check' not in sys.argv: W._save(dom, doc)
        print('%s: %d merged, %d short of the bar%s' % (dom, len(m.V3), len(short), (' :: ' + ' | '.join(short[:6])) if short else ''))
    print('merged', tot)


if __name__ == '__main__':
    main()

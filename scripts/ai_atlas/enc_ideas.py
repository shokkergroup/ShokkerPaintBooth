#!/usr/bin/env python
"""Encyclopedia DESIGN IDEAS & STYLES part (domain "ideas", 2026-10-05).

Catalogue helper + incremental article writer for data/encyclopedia/ideas.json.
  python scripts/ai_atlas/enc_ideas.py find <regex>      picker-visible finishes (key, name, shine, M/R/CC measured, group)
  python scripts/ai_atlas/enc_ideas.py pat <regex>       picker-visible paint patterns (id, name, group)
  python scripts/ai_atlas/enc_ideas.py spec <regex>      picker-visible spec patterns (id, name, group)
  python scripts/ai_atlas/enc_ideas.py src <key>         the registry / data line that defines a finish
  python scripts/ai_atlas/enc_ideas.py check             verify every id named in ideas.json is real + picker-visible
Used as a library: add(article) validates ids against the catalogue, fills sources, and writes ideas.json atomically (resume = skip ids present).
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'data', 'encyclopedia', 'ideas.json')
DUMP = os.path.join(ROOT, 'data', 'encyclopedia', '_drafts', '_dumpB.json')
HID = os.path.join(HERE, 'enc_picker_hidden.json')
PINNED = os.path.join(HERE, 'enc_foundation_pinned.json')
TODAY = '2026-10-05'


def _load():
    if not os.path.exists(DUMP):
        import subprocess
        subprocess.check_call(['node', os.path.join(HERE, 'enc_gen_B_dump.js'), DUMP], cwd=ROOT)
    D = json.load(open(DUMP, encoding='utf-8'))
    hidden = set(json.load(open(HID, encoding='utf-8'))['hidden'])
    pinned = json.load(open(PINNED, encoding='utf-8'))['pinned']
    fin = {}
    for it in D['atlas']['items']:
        k = it['k']
        if '::ui_' in k or not re.match(r'^(base|monolithic)::', k):
            continue
        fin[k] = it
    grouped_p = set()
    for g, ids in (D['pattern_groups'] or {}).items():
        grouped_p.update(ids if isinstance(ids, list) else [])
    grouped_s = set()
    for g, ids in (D['spec_pattern_groups'] or {}).items():
        grouped_s.update(ids if isinstance(ids, list) else [])
    pat = {p['id']: p for p in D['patterns'] if p['id'] in grouped_p}
    spec = {p['id']: p for p in D['spec_patterns'] if p['id'] in grouped_s}
    atlas_keys = {i['k'] for i in D['atlas']['items']}
    return D, fin, hidden, pinned, pat, spec, atlas_keys


D, FIN, HIDDEN, PINNED_SPEC, PAT, SPEC, ATLAS_KEYS = _load()
VIS = {k: v for k, v in FIN.items() if k not in HIDDEN}
_lines = {}


def flines(f):
    if f not in _lines:
        p = os.path.join(ROOT, f)
        _lines[f] = open(p, encoding='utf-8', errors='replace').read().split('\n') if os.path.isfile(p) else []
    return _lines[f]


def find_line(f, needle, lo=0, hi=None):
    L = flines(f)
    for i in range(lo, hi if hi is not None else len(L)):
        if needle in L[i]:
            return i + 1
    return None


_JS = 'paint-booth-0-finish-data.js'


def _sect(name):
    """(lo, hi) 0-based line range of `const NAME = [` ... next top-level const in the finish data file."""
    L = flines(_JS)
    lo = next(i for i, l in enumerate(L) if l.startswith('const %s = [' % name))
    hi = next(i for i in range(lo + 1, len(L)) if L[i].startswith('const '))
    return lo, hi


def _jsdef(section, ident):
    lo, hi = _sect(section)
    return find_line(_JS, 'id: "%s"' % ident, lo, hi) or find_line(_JS, "id: '%s'" % ident, lo, hi)


def finish_src(key):
    """-> 'file:line' where the finish is defined: registry for flat foundations / registry-defined bases, else the shipped catalogue."""
    kind, ident = key.split('::', 1)
    if kind == 'base':
        n = find_line('engine/base_registry_data.py', '"%s":' % ident)
        if n:
            return 'engine/base_registry_data.py:%d' % n
    n = _jsdef('BASES' if kind == 'base' else 'MONOLITHICS', ident)
    return '%s:%d' % (_JS, n) if n else None


def spec_of(key):
    """flat registry value if pinned, else the atlas measured mean (M, R, CC)."""
    ident = key.split('::', 1)[1]
    if ident in PINNED_SPEC:
        return tuple(PINNED_SPEC[ident]), 'pinned'
    it = FIN[key]
    if 'M' not in it:
        return (0, 0, 0), 'none'
    return (it['M'][0], it['R'][0], it['C'][0]), 'measured'


def pat_src(pid):
    n = _jsdef('PATTERNS', pid)
    return '%s:%d' % (_JS, n) if n else None


def spec_src(pid):
    n = _jsdef('SPEC_PATTERNS', pid)
    return '%s:%d' % (_JS, n) if n else None


def _pgroup(groups, pid):
    for g, ids in (groups or {}).items():
        if isinstance(ids, list) and pid in ids:
            return g
    return ''


def validate_ids(art):
    bad = []
    for a in art.get('actions', []):
        d, i = a['do'], a['id']
        if d == 'finish' and i not in VIS:
            bad.append('finish ' + i + (' (HIDDEN from picker)' if i in FIN else ' (unknown)'))
        elif d == 'pattern' and (i not in PAT or 'pattern::' + i not in ATLAS_KEYS):
            bad.append('pattern ' + i)
        elif d == 'spec' and (i not in SPEC or 'spec::' + i not in ATLAS_KEYS):
            bad.append('spec ' + i)
    # every finish / pattern id typed inside examples settings must be a real one too
    blob = json.dumps(art, ensure_ascii=False)
    for m in set(re.findall(r'\b((?:base|monolithic)::[A-Za-z0-9_\-]+)', blob)):
        if m not in VIS:
            bad.append('text finish ' + m)
    return bad


def load():
    if os.path.exists(OUT):
        return json.load(open(OUT, encoding='utf-8'))
    return {'domain': 'ideas', 'version': 1, 'articles': []}


def add(art):
    """validate + append/replace one article, atomic write. Returns True if written."""
    bad = validate_ids(art)
    if bad:
        raise SystemExit('BAD IDS in %s: %s' % (art['id'], bad))
    art.setdefault('domain', 'ideas'); art.setdefault('lane', 'C'); art.setdefault('updated', TODAY)
    art.setdefault('covers', []); art.setdefault('figures', []); art.setdefault('controls', [])
    art.setdefault('quick', False)
    doc = load()
    arts = [a for a in doc['articles'] if a['id'] != art['id']]
    arts.append(art)
    doc['articles'] = arts
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write('{"domain": "ideas", "version": 1, "articles": [\n')
        f.write(',\n'.join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in doc['articles']))
        f.write('\n]}\n')
    os.replace(tmp, OUT)
    return True


def have(i):
    return any(a['id'] == i for a in load()['articles'])


def check():
    doc = load(); n = 0; bad = 0
    for a in doc['articles']:
        b = validate_ids(a); n += 1
        if b:
            bad += 1; print('BAD', a['id'], b)
    print('CHECK %d articles, %d with bad ids' % (n, bad))
    return bad


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ''
    rx = re.compile(argv[2], re.I) if len(argv) > 2 else None
    if cmd == 'find':
        for k, it in sorted(VIS.items()):
            if rx.search(k + ' ' + it['n'] + ' ' + ' '.join(it.get('t', [])) + ' ' + it.get('d', '')[:80]):
                (m, r, c), how = spec_of(k)
                print('%s | %s | %s %s | M%d R%d CC%d (%s) | %s' % (k, it['n'], it.get('shine', ''), it.get('metal', ''), m, r, c, how[0], it.get('lane', '')))
    elif cmd == 'pat':
        for k, p in sorted(PAT.items()):
            if rx.search(k + ' ' + p['name']):
                print('%s | %s | %s' % (k, p['name'], _pgroup(D['pattern_groups'], k)))
    elif cmd == 'spec':
        for k, p in sorted(SPEC.items()):
            if rx.search(k + ' ' + p['name']):
                print('%s | %s | %s' % (k, p['name'], _pgroup(D['spec_pattern_groups'], k)))
    elif cmd == 'info':
        for k in argv[2:]:
            it = FIN.get(k)
            if not it:
                print(k, 'UNKNOWN'); continue
            (m, r, c), how = spec_of(k)
            print('%s | %s | M%d R%d CC%d %s | vis=%s | %s | %s' % (k, it['n'], m, r, c, how[0], k in VIS, it.get('d', '')[:170].replace('\n', ' '), it.get('lane', '')))
    elif cmd == 'src':
        print(finish_src(argv[2]))
    elif cmd == 'check':
        sys.exit(1 if check() else 0)
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv)

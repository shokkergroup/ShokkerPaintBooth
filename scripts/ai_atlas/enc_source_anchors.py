#!/usr/bin/env python
"""Encyclopedia source-line anchors (ENC_FACTCHECK round 2, 2026-10-04).

Problem: article `sources[]` cite "file:line"; the files keep moving, so ~1/3 of the control pages pointed at the wrong line.
Fix: every cited "file:line[-line]" gets an ANCHOR -- a distinctive text that must sit on that line -- stored in the sidecar
scripts/ai_atlas/enc_source_anchors.json  {"file:line": ["anchor", ...]}.  The article text stays a plain "file:line" string.

  python scripts/ai_atlas/enc_source_anchors.py --build    # add anchors for cited sources that have none (control pages: from the
                                                           #  inventory id / label; everything else: the text on the cited line NOW)
  python scripts/ai_atlas/enc_source_anchors.py --repair   # line moved? search the anchor in the file, rewrite the line number in every
                                                           #  article + the sidecar.  Exit 1 ONLY when an anchor is GONE from the file.
  python scripts/ai_atlas/enc_source_anchors.py --check    # report only (no writes)
build_encyclopedia.py runs --build then --repair; the gate (_easy_claude_work/enc_v2_test.js) runs --repair first and fails on gone / missing.
"""
import json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ENC = os.path.join(ROOT, 'data', 'encyclopedia')
SIDE = os.path.join(os.path.dirname(__file__), 'enc_source_anchors.json')
INV = os.path.join(os.path.dirname(__file__), 'enc_inventory.json')
SKIP_DIRS = {'_drafts', 'figures', 'reader', 'screens'}
SRC_RE = re.compile(r'^([A-Za-z0-9_.\-/]+):(\d+)(?:-(\d+))?(\s.*)?$')
ARR_RE = re.compile(r'("sources"\s*:\s*\[)(.*?)(\])', re.S)
STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
_lines = {}


def lines(f):
    if f not in _lines:
        p = os.path.join(ROOT, f)
        _lines[f] = open(p, encoding='utf-8', errors='replace').read().split('\n') if os.path.isfile(p) else None
    return _lines[f]


def files():
    for d, ds, fs in os.walk(ENC):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        for fn in fs:
            if fn.endswith('.json') and True:
                yield os.path.join(d, fn)


def keyof(mm):
    return '%s:%s%s' % (mm.group(1), mm.group(2), ('-' + mm.group(3)) if mm.group(3) else '')


def cited():
    """-> {key: 1} over every article; key = 'file:line[-end]' (text after the line spec is ignored)."""
    out = {}
    for p in files():
        t = open(p, encoding='utf-8').read()
        if '"sources"' not in t:
            continue
        for m in ARR_RE.finditer(t):
            for s in STR_RE.findall(m.group(2)):
                mm = SRC_RE.match(s)
                if mm and not s.startswith('SPB_WIKI'):
                    out[keyof(mm)] = 1
    return out


def load_side():
    return json.load(open(SIDE, encoding='utf-8')) if os.path.isfile(SIDE) else {}


def save_side(d):
    with open(SIDE, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(sorted(d.items())), f, ensure_ascii=False, indent=0)


def norm(s):
    return re.sub(r'\s*=\s*', '=', re.sub(r'\s+', ' ', s.replace('&amp;', '&'))).strip().lower()


_nl = {}


def nlines(L):
    k = id(L)
    if k not in _nl:
        _nl[k] = [norm(l) for l in L]
    return _nl[k]


def hits(L, anchor):
    a = norm(anchor)
    if not a:
        return []
    return [i + 1 for i, l in enumerate(nlines(L)) if a in l]


def parse_key(k):
    m = re.match(r'^(.+):(\d+)(?:-(\d+))?$', k)
    return m.group(1), int(m.group(2)), (int(m.group(3)) if m.group(3) else None)


def trivial(s):
    return len(s.strip()) < 12 or re.fullmatch(r'[\W_]*', s.strip()) is not None


def build(side):
    inv = {}
    try:
        for r in json.load(open(INV, encoding='utf-8'))['records']:
            inv.setdefault(r.get('source', ''), []).append(r)
    except Exception:
        pass
    added = weak = 0
    for k in cited():
        if side.get(k):
            continue
        f, n, e = parse_key(k)
        L = lines(f)
        if not L or n > len(L):
            continue
        anchors = []
        recs = inv.get('%s:%d' % (f, n), [])
        if len(recs) > 1 and not trivial(L[n - 1]):
            recs = []   # several controls share this one line (a function head, a data blob): the line's own text is the only honest anchor
        for r in recs:
            idv = r['id'].split('.')[-1]
            lab = (r.get('label') or '').strip()
            cands = ['id="%s"' % idv, "id='%s'" % idv, '"%s"' % idv, idv if len(idv) >= 6 else '', lab if len(lab) >= 4 else '']
            found = [(len(hits(L, c)), i, c) for i, c in enumerate(cands) if c and hits(L, c)]
            if found:
                # prefer one that already sits on the cited line; else the rarest in the file
                onl = [x for x in found if n in hits(L, x[2])]
                best = min(onl or found, key=lambda x: (x[0], x[1]))
                if best[2] not in anchors:
                    anchors.append(best[2])
        if not anchors and f.endswith('-data.js') and L[n - 1].startswith('window.'):
            anchors.append(L[n - 1].split('=')[0].strip() + ' =')   # generated data blobs: the stable 'window.X =' head, never the payload
        if not anchors:
            # the text on the cited line (or the first non-trivial line of the range)
            for i in range(n, (e or n) + 1):
                if i <= len(L) and not trivial(L[i - 1]):
                    anchors.append(L[i - 1].strip()[:110])
                    break
            if not anchors:
                # cited a blank / brace-only line: use the nearest real line within 5 (the citation then snaps to it)
                for d in range(1, 6):
                    for i in (n - d, n + d):
                        if 1 <= i <= len(L) and not trivial(L[i - 1]) and not anchors:
                            anchors.append(L[i - 1].strip()[:110])
            weak += 1
        if anchors:
            side[k] = anchors
            added += 1
    return added, weak


def repair(side, write=True):
    """-> (moved, gone[list], ok)"""
    mapping = {}
    gone = []
    ok = 0
    for k, anchors in side.items():
        f, n, e = parse_key(k)
        L = lines(f)
        if not L:
            gone.append((k, 'file missing'))
            continue
        if n <= len(L) and any(norm(a) in nlines(L)[n - 1] for a in anchors):
            ok += 1
            continue
        best = None
        for a in anchors:
            h = hits(L, a)
            if h:
                near = min(h, key=lambda x: abs(x - n))
                cand = (len(h), abs(near - n), near)
                if best is None or cand < best:
                    best = cand
        if not best:
            gone.append((k, anchors[0][:60]))
            continue
        nn = best[2]
        ne = (e + (nn - n)) if e else None
        mapping[k] = '%s:%d%s' % (f, nn, ('-%d' % ne) if ne else '')
    if mapping and write:
        # rewrite every article + the sidecar in ONE pass (simultaneous, so shifted keys never collide)
        def fix_block(m):
            def fs(sm):
                s = sm.group(1)
                mm = SRC_RE.match(s)
                if not mm or s.startswith('SPB_WIKI'):
                    return sm.group(0)
                new = mapping.get(keyof(mm))
                return '"%s%s"' % (new, mm.group(4) or '') if new else sm.group(0)
            return m.group(1) + STR_RE.sub(fs, m.group(2)) + m.group(3)
        for p in files():
            t = open(p, encoding='utf-8').read()
            if '"sources"' not in t:
                continue
            t2 = ARR_RE.sub(fix_block, t)
            if t2 != t:
                with open(p, 'w', encoding='utf-8', newline='') as fh:
                    fh.write(t2)
        new_side = {}
        for k, a in side.items():
            nk = mapping.get(k, k)
            merged = new_side.get(nk, []) + [x for x in a if x not in new_side.get(nk, [])]
            new_side[nk] = merged
        side.clear()
        side.update(new_side)
    return len(mapping), gone, ok


def main():
    mode = [a for a in sys.argv[1:] if a.startswith('--')]
    quiet = '--quiet' in mode
    side = load_side()
    if '--build' in mode:
        a, w = build(side)
        save_side(side)
        print('anchors added %d (%d weak: line text, no id/label match)' % (a, w))
    if '--repair' in mode or '--check' in mode:
        w = '--repair' in mode
        moved, gone, ok = repair(side, write=w)
        if w and moved:
            save_side(side)
        missing = [k for k in cited() if k not in side]
        print('anchors ok %d, %s %d, gone %d, cited-without-anchor %d' % (ok, 'repaired' if w else 'drifting', moved, len(gone), len(missing)))
        if not quiet:
            for k, a in gone[:30]:
                print('  GONE', k, '|', a)
            for k in missing[:10]:
                print('  NO ANCHOR', k)
        sys.exit(1 if gone or missing else 0)


if __name__ == '__main__':
    main()

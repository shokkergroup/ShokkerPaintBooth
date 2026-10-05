# -*- coding: utf-8 -*-
"""enc_stale_refs_check.py - gate: no buyer-facing help text may send a buyer to something they cannot reach (2026-10-05).

WHAT IT CATCHES (derived from CODE, not from a hand-kept list)
  (a) RETIRED controls.  A function in paint-booth-5-api-render.js that calls _showRetiredBatchModeToast(...) is retired (today: toggleFleetMode,
      doFleetRender, toggleSeasonMode, doSeasonRender).  The panel it hides (getElementById('fleetPanel') / 'seasonPanel') is found in
      paint-booth-v2.html; every button, id and onclick inside that panel is a retired control, and so is the mode label the toast names
      ("Fleet mode", "Season mode").  scripts/ai_atlas/ui_map.json rows for those DOM ids add the generated control ids (pro.zones.add_car ...).
  (b) HIDDEN finishes.  scripts/ai_atlas/enc_picker_hidden.json (snapshot of the live picker) lists Base Material finishes the picker does not
      show.  Their display names come from the dump of the shipped catalogue (data/encyclopedia/_drafts/_dumpB.json, built by enc_gen_B_dump.js).
      A name that is ALSO the name of a visible finish / pattern / spec pattern is ignored (the buyer can find that one).

WHAT COUNTS AS A HIT
  Scanned: every article in data/encyclopedia/**/*.json (not _drafts, figures, screens, reader), js/spb-self-help.js, js/spb-ai-knowledge.js.
  Skipped fields: aliases, sources, covers, id, title, controls[].label, related (names only, not instructions).  Finish / pattern / spec-pattern /
  control PAGES are about the thing itself; they are scanned for retired controls but a hidden finish is only a hit on them if a Do-it chip targets
  a control that does not exist.
  (a) a retired label / mode label / generated control id in a sentence that does NOT say it is retired (retired, cannot be reached, disabled,
      no longer, hidden, not available, exists in the code), or a Do-it action on a retired control id.
  (b) a hidden finish name in a sentence that tells the buyer to pick / choose / search / use it (or a settings row under Base Material / BASE)
      and does NOT say it is not in the picker / ask the AI helper by name.

Output: one verdict line per hit; final RESULT line; exit 1 if any hit remains.   python scripts/ai_atlas/enc_stale_refs_check.py [--list-retired] [-q]
"""
import glob
import html as H
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ENC = os.path.join(ROOT, 'data', 'encyclopedia')
API_JS = os.path.join(ROOT, 'paint-booth-5-api-render.js')
HTML = os.path.join(ROOT, 'paint-booth-v2.html')
UI_MAP = os.path.join(HERE, 'ui_map.json')
HIDDEN_JSON = os.path.join(HERE, 'enc_picker_hidden.json')
DUMP = os.path.join(ENC, '_drafts', '_dumpB.json')

RETIRED_MARK = re.compile(r"not there|finds no|not found|retired|cannot be reached|can.?not be (used|clicked|opened)|disabled|no longer|not available|is hidden|stays hidden|exists in the code|nothing (in the Pro window )?opens|what happened|\bwent\b|cannot find|can.t find", re.I)
NOT_PICKABLE = re.compile(r"not there|finds no|not found|cannot find|can.t find|" r'not (listed|shown|in the (Base Material )?picker|in the picker)|picker-hidden|hidden from the picker|ask (the|for)|by name|AI (helper|copilot)|Shokker AI', re.I)
PICK_VERB = re.compile(r'\b(pick|picks|choose|chooses|select|search|searches|try|use|using|apply|add|set)\b|Base Material|\bBASE\b|picker|shelf', re.I)
SKIP_KEYS = {'aliases', 'sources', 'covers', 'id', 'title', 'label', 'related', 'screens', 'figures', 'level', 'lane', 'updated', 'tags', 'kw', 'links'}


# ------------------------------------------------------------------ (a) retired controls, from code
def _func_bodies(src):
    """name -> body text for top-level `function name(` / `async function name(` in a JS file (brace balanced)."""
    out = {}
    for m in re.finditer(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', src):
        i = src.find('{', m.end())
        if i < 0:
            continue
        d, j = 0, i
        while j < len(src):
            c = src[j]
            if c == '{':
                d += 1
            elif c == '}':
                d -= 1
                if d == 0:
                    break
            j += 1
        out[m.group(1)] = src[i:j + 1]
    return out


class _Panel(HTMLParser):
    """collects every element inside the element with id == target: (tag, id, onclick fn, visible label, title)."""
    VOID = {'input', 'br', 'img', 'meta', 'link', 'hr', 'source', 'col', 'area', 'base', 'wbr', 'embed', 'param', 'track'}

    def __init__(self, target):
        super().__init__(convert_charrefs=True)
        self.target, self.depth, self.stack, self.inside = target, 0, [], False
        self.rows, self.style, self.h4 = [], '', ''
        self._cur = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.inside and a.get('id') == self.target:
            self.inside, self.depth, self.style = True, 0, a.get('style', '')
        if self.inside:
            if tag not in self.VOID:
                self.depth += 1
            if tag == 'button' or a.get('onclick') or a.get('id'):
                self._cur = {'tag': tag, 'id': a.get('id', ''), 'onclick': a.get('onclick', ''), 'title': a.get('title', ''), 'text': ''}
                self.rows.append(self._cur)
            if tag == 'h4':
                self._cur = {'tag': 'h4', 'id': '', 'onclick': '', 'title': '', 'text': ''}
                self.rows.append(self._cur)

    def handle_endtag(self, tag):
        if self.inside and tag not in self.VOID:
            self.depth -= 1
            if self.depth <= 0:
                self.inside = False
            if tag in ('button', 'h4'):
                self._cur = None

    def handle_data(self, data):
        if self.inside and self._cur is not None and self._cur['tag'] in ('button', 'h4'):
            self._cur['text'] += data


def _norm_label(s):
    s = re.sub(r'\s+', ' ', H.unescape(s or '')).strip()
    return re.sub(r'^[+➕\s]+', '', s).strip()


def retired_code_evidence():
    """Pure code evidence (no ui_map): dict(funcs, modes, labels, dom_ids, by_label, by_dom, evidence[]). Nothing is hand-listed.
    by_label / by_dom map a retired control's label / DOM id to its mode word ('fleet', 'season'); build_ui_map.py uses them to mark the controls."""
    ev, funcs, modes, labels, dom_ids = [], [], set(), set(), set()
    by_label, by_dom = {}, {}
    js = open(API_JS, encoding='utf-8', errors='replace').read()
    html = open(HTML, encoding='utf-8', errors='replace').read()
    bodies = _func_bodies(js)
    jl = js.split('\n')

    def line_of(needle):
        for n, l in enumerate(jl, 1):
            if needle in l:
                return n
        return 0
    tox = re.compile(r'_showRetiredBatchModeToast\(\s*[\'"`]([^\'"`]+)[\'"`]')
    panels = set()
    for name, body in bodies.items():
        if name == '_showRetiredBatchModeToast':
            continue
        m = tox.search(body)
        if not m:
            continue
        funcs.append(name)
        modes.add(m.group(1))
        ev.append('paint-booth-5-api-render.js:%d %s() shows the retired toast for "%s"' % (line_of('function ' + name), name, m.group(1)))
        for pid in re.findall(r"getElementById\(\s*['\"](\w+Panel)['\"]\s*\)", body):
            panels.add(pid)
        for b in re.findall(r"getElementById\(\s*['\"](btn\w+Toggle)['\"]\s*\)", body):
            dom_ids.add(b)
        for t in re.findall(r"textContent\s*=\s*['\"]([^'\"]+)['\"]", body):
            if re.match(r'(Fleet|Season)\s+Mode$', t):        # the toggle button's own label; other strings here are dead code
                labels.add(t)
    hl = html.split('\n')
    for pid in sorted(panels):
        p = _Panel(pid)
        p.feed(html)
        hidden = 'display: none' in p.style.replace('  ', ' ') or 'display:none' in p.style.replace(' ', '')
        ln = next((n for n, l in enumerate(hl, 1) if 'id="%s"' % pid in l), 0)
        ev.append('paint-booth-v2.html:%d #%s style="%s" (hidden=%s)' % (ln, pid, p.style.strip(), hidden))
        if not hidden:
            continue
        dom_ids.add(pid)
        word = re.sub(r'Panel$', '', pid).lower()
        by_dom[pid] = word
        for r in p.rows:
            if r['id']:
                dom_ids.add(r['id'])
                by_dom[r['id']] = word
            t = _norm_label(r['text'])
            if t and r['tag'] == 'button':
                by_label[t] = word
            if r['tag'] == 'h4' and t:
                labels.add(re.split(r'\s+[—-]\s+', t)[0])      # "Fleet Mode - Multi-Car Batch Render" -> "Fleet Mode"
            elif r['tag'] == 'button' and t:
                labels.add(t)
                fn = re.match(r'\s*([A-Za-z_$][\w$]*)\s*\(', r['onclick'] or '')
                ev.append('paint-booth-v2.html:%d button "%s" onclick=%s inside hidden #%s' % (ln, t, fn.group(1) if fn else '-', pid))
    # the buyer says "Fleet mode" / "Season mode" / "Season set-up"; also lower-case toast labels
    for m in list(modes):
        labels.add(m)
    for m in list(labels):
        if re.match(r'\w+:\s+\w', m):
            labels.add(m.split(':', 1)[1].strip())            # "Quick: Wear Ramp" is also said as "Wear Ramp"
        mm = re.match(r'(\w+)\s+[Mm]ode$', m)
        if mm:
            for suffix in ('set-up', 'setup', 'batch', 'panel', 'ramp'):
                labels.add(mm.group(1) + ' ' + suffix)
    return dict(funcs=funcs, modes=sorted(modes), labels=sorted(l for l in labels if len(l) > 3), dom_ids=sorted(dom_ids), by_label=by_label, by_dom=by_dom, evidence=ev)


def retired_from_code():
    """retired_code_evidence() plus the generated control ids (scripts/ai_atlas/ui_map.json rows built from those DOM ids / labels)."""
    R = retired_code_evidence()
    ev, dom_ids, labels = R['evidence'], set(R['dom_ids']), set(R['labels'])
    control_ids = set()
    try:
        um = json.load(open(UI_MAP, encoding='utf-8'))
        for it in um['items']:
            if it.get('dom_id') in dom_ids or it['id'] in dom_ids or it.get('label') in labels or _norm_label(it.get('label', '')) in labels:
                control_ids.add(it['id'])
                if it.get('dom_id'):
                    control_ids.add(it['dom_id'])
    except Exception as e:
        ev.append('ui_map.json not readable: %s' % e)
    R['control_ids'] = sorted(control_ids)
    return R


# ------------------------------------------------------------------ (b) hidden finishes
def hidden_finishes():
    """-> (names: {display name: [ids]}, hidden id set, visible labels longest first).  A hidden finish whose name is also a visible
    finish / pattern / spec-pattern name is not tracked.  Visible labels ("Camo: M81 Woodland", "Scuffed Enamel") are masked out of a sentence before
    hidden names are matched, so a longer visible name that merely CONTAINS a hidden name is not a hit."""
    hid = set(json.load(open(HIDDEN_JSON, encoding='utf-8'))['hidden'])
    if not os.path.exists(DUMP):
        subprocess.check_call(['node', os.path.join(HERE, 'enc_gen_B_dump.js'), DUMP], cwd=ROOT, stdout=subprocess.DEVNULL)
    D = json.load(open(DUMP, encoding='utf-8'))
    pick_name = {}
    for kind, arr in (('base', D['bases']), ('monolithic', D['monolithics'])):
        for x in arr:
            pick_name['%s::%s' % (kind, x['id'])] = x.get('name') or ''
    for it in D['atlas']['items']:
        pick_name.setdefault(it['k'], it['n'])
    visible, names, vis_labels, last = set(), {}, set(), set()
    for k, n in pick_name.items():
        if re.match(r'^(base|monolithic)::', k) and '::ui_' not in k:
            if k not in hid:
                visible.add(n.lower())
                vis_labels.add(n)
                if ': ' in n:
                    visible.add(n.split(': ', 1)[1].lower())      # the picker search for "M81 Woodland" finds "Camo: M81 Woodland"
                if ' ' in n.strip():
                    last.add(n.strip().rsplit(' ', 1)[1].lower())  # "search Chameleon, then choose Amethyst": the last word of "Chameleon Amethyst"

        else:
            visible.add(n.lower())
            vis_labels.add(n)
    for p in D['patterns'] + D['spec_patterns']:
        visible.add((p.get('name') or '').lower())
    try:                                              # catalogue family / shelf names ("Candy & Tinted Clear") are not finishes
        meta = open(os.path.join(ROOT, 'paint-booth-0-finish-metadata.js'), encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'"(?:family|browserSection)":\s*"([^"]+)"', meta):
            for part in re.split(r'\s+(?:&|and)\s+', m.group(1)):
                visible.add(part.strip().lower())
    except Exception:
        pass
        vis_labels.add(p.get('name') or '')
    for k in hid:
        n = pick_name.get(k, '')
        if not n or n.lower() in visible or len(n) < 4 or (' ' not in n and n.lower() in last):
            continue
        names.setdefault(n, []).append(k)
    nrx = re.compile('|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)))
    mask = [x for x in vis_labels if len(x) >= 5 and x not in names and nrx.search(x)]       # visible labels that CONTAIN a hidden name
    return names, hid, sorted(mask, key=len, reverse=True)


# ------------------------------------------------------------------ scanning
def _sentences(s):
    return [x for x in re.split(r'(?<=[.!?;])\s+|\n+', s) if x.strip()]


def _walk(o, path, out, skip_hidden_names=False):
    if isinstance(o, dict):
        if 'settings' in o and isinstance(o['settings'], dict):
            for k, v in o['settings'].items():
                if isinstance(v, str):
                    out.append((path + '.settings.' + k, '%s: %s' % (k, v), True))
        for k, v in o.items():
            if k in SKIP_KEYS or k == 'settings':
                continue
            _walk(v, path + '.' + k, out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _walk(v, '%s[%d]' % (path, i), out)
    elif isinstance(o, str):
        out.append((path, o, False))


def _article_strings(a):
    out = []
    _walk(a, '', out)
    return out


def load_articles():
    for f in sorted(glob.glob(os.path.join(ENC, '**', '*.json'), recursive=True)):
        fs = f.replace('\\', '/')
        if '/_drafts/' in fs or '/figures/' in fs or '/screens/' in fs or '/reader/' in fs or fs.endswith('/figures.json') or fs.endswith('/screens.json'):
            continue
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get('articles'), list):
            for a in d['articles']:
                yield os.path.relpath(f, ENC).replace('\\', '/'), a


def js_records():
    """(file, id, [(path, text, is_setting)]) for the two buyer-facing JS help files."""
    p = os.path.join(ROOT, 'js', 'spb-ai-knowledge.js')
    s = open(p, encoding='utf-8').read()
    m = re.search(r'var CHUNKS = (\[.*?\]);\s*\n', s, re.S)
    if m:
        for c in json.loads(m.group(1)):
            yield 'js/spb-ai-knowledge.js', c.get('t', '?'), [('.b', c.get('b', ''), False)]
    p = os.path.join(ROOT, 'js', 'spb-self-help.js')
    s = open(p, encoding='utf-8').read()
    for var in ('UI_DATA', 'HOWTO'):
        m = re.search(r'var %s = (\[.*?\]);\s*\n' % var, s, re.S)
        if m:
            for r in json.loads(m.group(1)):
                rid = r.get('id') or r.get('q') or '?'
                strs = []
                _walk(r, '', strs)
                yield 'js/spb-self-help.js', '%s:%s' % (var, rid), strs
    # hand-written part (TOPICS, label table): scan the raw lines outside the generated block
    rest = re.sub(r'/\*@@UI_DATA_START\*/.*?/\*@@UI_DATA_END\*/', '', s, flags=re.S)
    strs = [('.line%d' % n, l, False) for n, l in enumerate(rest.split('\n'), 1) if l.strip() and not l.lstrip().startswith(('//', '/*', '*'))]
    yield 'js/spb-self-help.js', 'TOPICS', strs


_VERB = r'(?:pick|picks|choose|chooses|select|search|searches|try|use|using|apply|add|set|swap|switch to|go for|grab|load|with)'
_BASE_ROW = re.compile(r'^(?:Base Material|BASE|Base|Finish|Camo|Material)\b[^:]*:\s*', re.I)


def _is_pick(sent, m, is_set):
    """True when this hidden-finish name is being offered to the buyer as something to pick.  A match that is only part of a longer proper name
    ("Scuffed Enamel", "Sea Glass Confessional") is not the hidden finish.  Single-word names (Enamel, Ember, Void ...) are common English
    words, so they count only right after a pick verb or in a Base Material settings row; multi-word names count in any pick sentence."""
    name, a, b = m.group(1), m.start(), m.end()
    after = sent[b:b + 30]
    if re.match(r'\s+[A-Z][a-z]', after) and not re.match(r'\s+(?:And|Or)\b', after):
        if not re.match(r'\s+(?:Base|Pattern|Blend|Paint|Opacity|Scale|Strength|Zone|Layer|Hex|Alt)\b', after):
            return False
    before = sent[:a]
    pw = re.search(r"([A-Z][\w']+)[\s:]*$", before)
    if pw and not re.match(r'(?:Pick|Choose|Select|Search|Try|Use|Add|Apply|Set|Base|BASE|Camo|Material|Finish|The|A|An|Or|And|With|Under|Open)$', pw.group(1)):
        return False                                   # sits at the end of a longer capitalised name
    row = bool(is_set and _BASE_ROW.match(sent))
    if ' ' in name:
        return True                                    # a distinctive multi-word finish name offered in any sentence is an offer to use it
    near = re.search(r'\b' + _VERB + r'\b(?:\s+(?:a|an|the|one|either|such as|e\.g\.|like))?(?:[^.;:]{0,40}?,)?\s*$', before, re.I)
    return bool(near) or row


def _asks_by_name(a):
    """An article whose whole point is "these finishes are not in the picker, ask the Shokker AI helper for them by name": its summary says they are
    not listed AND its steps tell the buyer to ask by name.  Only such an article may describe hidden finishes freely (recipes.named_looks)."""
    summ = a.get('summary') or ''
    steps = ' '.join(x for x in (a.get('how') or []) if isinstance(x, str))
    return bool(re.search(r'not (listed|in the)|picker does not list|none of [^.]{0,60}listed', summ, re.I) and re.search(r'ask [^.]{0,40}by name|asked for by name|ask for', steps, re.I))


def scan(quiet=False):
    R = retired_from_code()
    hnames, hid, vis_labels = hidden_finishes()
    vis_rx = re.compile('|'.join(re.escape(x) for x in vis_labels))
    lab_rx = re.compile(r'(?<![\w-])(' + '|'.join(re.escape(l) for l in sorted(R['labels'], key=len, reverse=True)) + r')(?![\w-])', re.I)
    id_set = set(R['control_ids']) | set(R['dom_ids'])
    hn_rx = re.compile(r'(?<![\w-])(' + '|'.join(re.escape(n) for n in sorted(hnames, key=len, reverse=True)) + r')(?![\w-])')
    hits = []

    def check(src, aid, strs, is_page, actions, by_name=False):
        for path, text, is_set in strs:
            if not isinstance(text, str):
                continue
            for sent in ([text] if is_set else _sentences(text)):
                for m in lab_rx.finditer(sent):
                    if not RETIRED_MARK.search(sent):
                        hits.append(('RETIRED-CONTROL', src, aid, path, m.group(1), sent))
                if not is_page and not by_name and not NOT_PICKABLE.search(sent):
                    masked = vis_rx.sub(lambda mm: '\u2022' * len(mm.group(0)), sent)       # same length, so offsets stay valid
                    for m in hn_rx.finditer(masked):
                        if _is_pick(sent, m, is_set):
                            hits.append(('HIDDEN-FINISH', src, aid, path, m.group(1), sent))
        for ac in actions or []:
            if isinstance(ac, dict):
                i = ac.get('id', '')
                if ac.get('do') == 'control' and i in id_set:
                    hits.append(('RETIRED-DOIT', src, aid, '.actions', i, 'Do-it action on a retired control'))
                if ac.get('do') == 'finish' and i in hid and not is_page:
                    hits.append(('HIDDEN-DOIT', src, aid, '.actions', i, 'Do-it action applies a finish the picker does not list'))

    nart = 0
    for rel, a in load_articles():
        nart += 1
        is_page = bool(re.match(r'(finish|pattern|specpat|controls)_', a['id']))
        check(rel, a['id'], _article_strings(a), is_page, a.get('actions'), _asks_by_name(a))
    for src, rid, strs in js_records():
        check(src, rid, strs, False, None)
    return R, hnames, hits, nart


def main():
    quiet = '-q' in sys.argv
    R, hnames, hits, nart = scan(quiet)
    if '--list-retired' in sys.argv:
        print('RETIRED funcs :', ', '.join(R['funcs']))
        print('RETIRED modes :', ', '.join(R['modes']))
        print('RETIRED labels:', ' | '.join(R['labels']))
        print('RETIRED dom   :', ', '.join(R['dom_ids']))
        print('RETIRED ctl ids:', ', '.join(R['control_ids']))
        for e in R['evidence']:
            print('  evidence:', e)
        print('HIDDEN finish names tracked:', len(hnames))
    if not R['funcs']:
        print('FAIL no retired functions found in paint-booth-5-api-render.js: the check cannot trust itself')
        return 2
    for kind, src, aid, path, what, sent in hits:
        s = re.sub(r'\s+', ' ', sent)[:150]
        print('%s %s %s%s [%s] %s' % (kind, src, aid, path, what, s))
    nr = sum(1 for h in hits if h[0].startswith('RETIRED'))
    nh = sum(1 for h in hits if h[0].startswith('HIDDEN'))
    print('RESULT %s: %d article(s)+js scanned, retired labels %d, hidden names %d; hits retired=%d hidden=%d' % (
        'FAIL' if hits else 'PASS', nart, len(R['labels']), len(hnames), nr, nh))
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())

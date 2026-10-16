#!/usr/bin/env python3
"""ENC_READER_FIX (2026-10-05): data rules the Encyclopedia READER needs, shared by the generators and applied as an idempotent post-pass.

Input: docs/handoff_reports/ENC_UX_TEST.md (blind buyer test). Three rules, each a function the generators import and a pass over the
article files on disk (so pages that are not regenerated get the same fix):

  1. PICTURES must show the article's topic (screen_ok / figure_ok):
     - a car render shows ONE finish: it belongs on that finish's page, on a page that names the finish, or (lane S's own pick) on the
       concept page about its shelf. Never as a stand-in on another finish's page (the Chrome page showed the tie-dye 'Moonstone' shelf car)
       or on a guide that merely shares a colour word (the stealth guide showed the bright blue 'Abyss Blue' car).
     - a UI screenshot or diagram attached by word overlap must share a real subject word with the article's title / aliases / summary
       (not 'paint', 'car', 'colour' ...). Lane S's own article_ids are trusted.
  2. CONTROL PAGE TITLES are names a buyer can read (clean_control_title): leading symbols ('+ Add Zone', '‹ ON-CAR STAGE', '? Guide') are
     dropped, '#carbon' filter chips become 'Carbon tag (finish picker)', HTML fragments ('(the color art)', '), which is why it's required',
     '...or paste / browse...') are replaced by the control's on-screen label.
  3. DO-IT LABELS never show internal ids: a {do: 'control', id} action without a label gets the control's visible label from
     scripts/ai_atlas/ui_map.json ('btnRender' -> 'RENDER button', 'carPickBtn' -> 'Pick detected iRacing car').

  python scripts/ai_atlas/enc_reader_fix.py            # audit only: one verdict line, details -> _easy_claude_work/enc_fix/reader_fix_audit.json
  python scripts/ai_atlas/enc_reader_fix.py --write    # apply (atomic, byte-format preserving, idempotent)
build_encyclopedia.py runs it with --write before compiling, so a regenerated page file gets the rules back automatically.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ENC = os.path.join(ROOT, 'data', 'encyclopedia')
AUDIT = os.path.join(ROOT, '_easy_claude_work', 'enc_fix', 'reader_fix_audit.json')


def norm(s):
    s = re.sub(r"['’`]", '', str(s or '').lower())
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9#]+', ' ', s)).strip()


STOP = set('the a an and or of to in on for with is are it its be your you how what why do does my this that from as at by not no can will when into than then '
           'one two all any each more most only also just use used using make makes get set see shows show here there which who'.split())
# words every page shares: they say nothing about what a picture shows
GENERIC = set('paint paints painted painting car cars colour color colours colors shokker app booth livery liveries look looks finish finishes '
              'button buttons box panel tab click press open opens choose pick step steps new first your way part parts side whole area'.split())

UI_FRAME = set('window windows header labelled labeled whole top row rows menu bar strip view'.split())


def words(s, generic=True):
    out = set()
    for w in norm(s).split():
        if len(w) < 3 or w in STOP or (generic and w in GENERIC):
            continue
        if len(w) > 4 and w.endswith('ves'):
            w = w[:-3] + 'f'
        elif len(w) > 4 and w.endswith('s') and not w.endswith('ss'):
            w = w[:-1]
        out.add(w)
    return out


def art_text(a, deep=True):
    parts = [a.get('title'), a.get('summary'), ' '.join(a.get('aliases') or [])]
    if deep:
        parts += [a.get('what')] + [x if isinstance(x, str) else (x or {}).get('text', '') for x in (a.get('how') or [])]
        parts += [(d or {}).get('heading', '') + ' ' + (d or {}).get('body', '') for d in (a.get('deep') or []) if isinstance(d, dict)]
        parts += [(q or {}).get('q', '') for q in (a.get('faq') or []) if isinstance(q, dict)]
    return ' '.join(str(p or '') for p in parts)


def look_ids(a):
    out = set()
    for x in a.get('actions') or []:
        if not isinstance(x, dict):
            continue
        for k in ('id', 'finish_id', 'pattern_id', 'spec_id'):
            if x.get(k):
                v = str(x[k])
                out.add(v)
                out.add(v.split('::')[-1])
    for c in a.get('combos') or []:          # 'works with' a real finish / pattern key (not another article)
        w = str((c or {}).get('with') or '') if isinstance(c, dict) else ''
        if '::' in w:
            out.add(w)
            out.add(w.split('::')[-1])
    return out


def shelf_name(s):
    return norm(re.sub(r'^[^A-Za-z0-9]+', '', str(s or '')))


# ------------------------------------------------------------------ rule 1: pictures
SHELF_FILLER = set('fractured shokk more special specials base bases lab fun field works city underground vibes that all bad rad far out sock hop extended '
                   'world money surface physics light optics minds forge foundry relics tessera elements wilds cosmos nightshift opalfire'.split())
SHELF_OF = {}          # finish key ('base::x' and bare 'x') -> shelf slug of its generated page (finish_<slug>_<n>); filled by load_shelves()


def load_shelves():
    if SHELF_OF:
        return SHELF_OF
    pd = os.path.join(ENC, 'pages')
    for f in os.listdir(pd):
        m = re.match(r'^finish_(.+)_\d+\.json$', f)
        if not m:
            continue
        try:
            d = json.load(open(os.path.join(pd, f), encoding='utf-8'))
        except Exception:
            continue
        for a in d.get('articles') or []:
            for k in look_ids(a):
                SHELF_OF.setdefault(k, m.group(1))
    return SHELF_OF


# mood / tone words in a shelf name say nothing about what its hero car looks like ('dark' city is a bright blue car)
SHELF_MOOD = set('dark light bright deep soft warm cold cool hot neon black white night day city street royal pure classic modern retro wild super ultra prime elite'.split())


SHELF_PLAIN = set('pattern patterns plate plates source shokk works work let ring sea signal more base bases foundation efx fun era'.split())


OUR_EXEMPT = 'No app screenshot shows this topic yet; an unrelated picture was removed (ENC_READER_FIX 2026-10-05).'
SPEC_FILLER = set('spec map maps finish foundation soft worn zone a an of the'.split())
LOOK_DOMAINS = set('ideas recipes finishes patterns playbook styles colour colours'.split())
# eye verdicts: {article id: {screen id: true|false}} + reasons. Kept with the generators so a rebuild never undoes a look.
EYE, EYE_WHY = {}, {}
try:
    for _r in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'enc_pic_verdicts.json'), encoding='utf-8')).get('verdicts') or []:
        EYE.setdefault(_r['article'], {})[_r['screen']] = bool(_r['ok'])
        EYE_WHY[(_r['article'], _r['screen'])] = _r.get('why') or ''
except Exception:
    pass


def screen_ok(a, scr, curated=False):
    """(ok, reason). a = article dict, scr = screens.json row; curated = lane S listed this article in the screen's article_ids."""
    kind = scr.get('kind') or ''
    meta = scr.get('meta') or {}
    aid = str(a.get('id') or '')
    if EYE.get(aid, {}).get(str(scr.get('id'))) is False:          # a person LOOKED and said no (enc_pic_verdicts.json)
        return False, 'rejected by eye: ' + EYE_WHY.get((aid, str(scr.get('id'))), '')
    if EYE.get(aid, {}).get(str(scr.get('id'))) is True:
        return True, ''
    # LOOK pages (ideas / recipes / finishes / styles ...): a picture made FROM a finish or pattern is kept only when that exact
    # finish / pattern is one the page itself uses (its Do-it actions or combos). Sharing a shelf or a word is not enough: the
    # Flames idea got a yellow blotchy 'Smoke & Fire' shelf car, Wet look got a teal camo-like glass car (coordinator, by eye).
    if meta.get('look') and aid not in (scr.get('article_ids') or []):
        # a LOOK render (run_looks.py) was judged by eye for the pages it names; plain Gloss in racing green is not 'Flames' just
        # because the Flames page also lists Gloss as a base
        return False, 'look picture made for another page'
    fk = str(meta.get('finish_key') or '')
    if fk and aid.split('.')[0] in LOOK_DOMAINS:
        ids = look_ids(a)
        own = fk in ids or fk.split('::')[-1] in ids
        if not own and kind == 'car_render' and curated and aid.startswith('finishes.') and str(scr.get('id')).startswith('cat_'):
            own = True          # a shelf overview page (finishes.<shelf family>) shows that shelf's own hero car (lane S CONCEPT map)
        if not own and kind == 'spec_view':          # a spec map lane S made FOR this page (a shared title word put Chrome's map on the 50s diner)
            own = curated
        if not own:
            return False, '%s made from %s, which this look page does not use' % (kind or 'picture', fk)
    if not fk and kind != 'car_render' and aid.split('.')[0] in LOOK_DOMAINS and not curated:
        # pics40 audit (2026-10-05, by eye): uncurated UI / before-after shots matched look pages on one shared word - the PRO / CHAT
        # pill on 'Match a photo', the Candy zone card on 'matte black', Base Scale plaid on 'Make it look fast'. A look page keeps a
        # picture with no finish behind it only when lane S made it for that page.
        return False, '%s picture "%s" was not made for this look page' % (kind or 'ui', scr.get('title'))
    if kind == 'car_render':
        key = str(meta.get('finish_key') or '')
        bare = key.split('::')[-1]
        name = norm(re.sub(r'\s+on the car\s*$', '', str(scr.get('title') or ''), flags=re.I))
        ids = look_ids(a)
        page_key = aid.split('.', 2)[-1] if re.match(r'^(finish|pattern|specpat)_', aid) else ''
        if re.match(r'^(finish|pattern|specpat)_', aid):          # a generated finish page: only the render of THIS finish
            return (bare == page_key or key in ids or bare in ids and len(ids) <= 2), 'car render of another finish (%s) on a finish page' % (name or bare)
        if key in ids or bare in ids:
            return True, ''
        txt = ' ' + norm(art_text(a)) + ' '
        if name and len(name) >= 4 and (' ' + name + ' ') in txt:
            return True, ''
        if not str(scr.get('id')).startswith('cat_'):          # one finish's own render: only that finish (named or used) earns it
            return False, 'car render of %s, which the article never names or uses' % (name or bare)
        sh = shelf_name(meta.get('shelf'))
        # (a hero car of ANOTHER finish from the same shelf is not allowed: the stealth recipe got the bright Abyss Blue DARK CITY car)
        if sh and len(sh) >= 4 and (' ' + sh + ' ') in (' ' + norm(art_text(a, deep=False)) + ' '):          # the page is ABOUT that shelf (title / aliases / summary; 'Foundation Bases shelf > Flat Black' in a step is not)
            return True, ''
        # the page's TITLE names the shelf's theme ('Flames and graphics' -> the FLAMES hero). One shared word anywhere was too loose:
        # 'pattern' put SOURCE PATTERN PLATES' marble car on every pattern page, 'shokk' put SHOKK WORKS on Shokk Drop
        if (words(sh) - SHELF_FILLER - SHELF_MOOD - SHELF_PLAIN) & words(str(a.get('title') or '')):
            return True, ''
        return False, 'car render of %s (%s shelf), which the article never names' % (name or bare, sh or '?')
    if curated:
        return True, ''
    # an uncurated screenshot must share a subject word with the page's title / aliases / summary, and the app's
    # frame words do not count: 'window' / 'header' / 'folder' put the same two tour shots on every file and settings page
    tw = words(scr.get('title')) - UI_FRAME
    core = words(art_text(a, deep=False))
    hit = tw & core
    if hit:
        return True, ''
    return False, '%s picture "%s" shares no subject word with the article title / aliases / summary' % (kind or 'ui', scr.get('title'))


def best_screen(a, S, cur):
    """the screenshot that shares the most subject words with the page (title / aliases / summary count double), among those
    screen_ok accepts; car renders only for the page's own looks. None when nothing fits."""
    core, deep = words(art_text(a, deep=False)), words(art_text(a, deep=True))
    head = words(' '.join([str(a.get('title') or '')] + [str(x) for x in (a.get('aliases') or [])]))
    best, bs = None, 0.0
    for sid, s in S.items():
        ok, _ = screen_ok(a, s, curated=sid in cur.get(a.get('id'), ()))
        if not ok:
            continue
        if str(a.get('id') or '').split('.')[0] in LOOK_DOMAINS and not (s.get('meta') or {}).get('finish_key'):
            continue          # a look page's picture must SHOW one of its looks (a render or spec map), never a generic UI shot
        tw = words(str(s.get('title') or '')) - UI_FRAME
        cw = words(str(s.get('caption') or '')) - UI_FRAME
        sc = 2.0 * len(tw & core) + 0.5 * len(cw & core) + 0.25 * len((tw | cw) & deep)
        if s.get('kind') == 'car_render':
            sc += 3.0          # the page's own look on the car (screen_ok already demands the page names or uses it)
        elif not (sid in cur.get(a.get('id'), ()) or ((tw & head) and len(tw & core) >= 2)):
            continue          # a screenshot must share a word with the page's TITLE or aliases: one summary word put 'The PRO / CHAT pill' on Trading Paints
        if sc > bs:
            best, bs = sid, sc
    return best if bs >= 2.0 else None


def figure_ok(a, fig):
    if EYE.get(str(a.get('id') or ''), {}).get(str(fig.get('id'))) is False:
        return False, 'rejected by eye: ' + EYE_WHY.get((str(a.get('id') or ''), str(fig.get('id'))), '')
    tw = words(fig.get('title'))
    core = words(art_text(a, deep=True))          # diagrams were attached by hand: the whole page may name the subject
    return (bool(tw & core), 'diagram "%s" shares no subject word with the article' % fig.get('title'))


# ------------------------------------------------------------------ rule 2: control page titles
LEAD = re.compile(r'^[\s+＋‹›?⧉⤢�✕×▶◀•·*….]+')
FRAGMENT = re.compile(r'^\s*[(),;:]|^\s*(\.\.\.|…)|[a-z-]+:\s*\d+px|;\s*[a-z-]+\s*:', re.I)
TITLE_FIX = {          # on-screen labels read from the HTML (the scanner picked up a hint / sentence fragment instead)
    'drop.userImportSetPaint': 'Paint image (import set)',
    'drop.the_color_art.181': 'Paint image label (import set)',
    'sculpt.useCustomNum': 'Custom-number car',
    'sculpt.outputDir': 'Output car folder (Spec Sculpt)',
    'dualShiftHexA': 'Hex colour box (Legacy Dual Color Shift)',
    'dualShiftHexB': 'Hex colour box (custom dual colour shift)',
    'fgHexInput': 'Hex colour box (tool colour)',
}


def clean_control_title(title, cid=''):
    t = str(title or '')
    if cid in TITLE_FIX:
        return TITLE_FIX[cid]
    m = re.match(r'^\s*#([a-z]+)\s*$', t, re.I)
    if m:
        return '%s tag (finish picker)' % m.group(1).capitalize()
    if FRAGMENT.search(t):
        return ''          # caller falls back to the on-screen label / a readable id
    t2 = re.sub(r'^\s*[+＋](?=\d)', '+', t)          # '+1 (expand selection)' keeps its sign
    t2 = t2 if t2.startswith('+') and t2[1:2].isdigit() else LEAD.sub('', t).strip()          # on-screen capitals stay ('RENDER' is what the button says)
    return t2 or t


def _toks(s):
    return [w for w in (re.sub(r"[^\w\-°]+", ' ', str(s or '').lower()).split()) if w not in STOP and not w.isdigit()]


def dtitle(t):
    return re.sub(r',\s[^,]*$', '', re.sub(r'\s+\d+$', '', str(t or ''))).strip().lower()


def sibling_hint(cid, summ):
    """the words that tell control `cid` apart from its same-label siblings (cid~2, cid~3 ...): from their summaries"""
    base = cid.split('~')[0]
    if cid not in summ:
        return ''
    sibs = [k for k in summ if k.split('~')[0] == base and k != cid and summ[k][1] == summ[cid][1]]          # only true same-name twins
    if not sibs:
        return ''
    other = set()
    for k in sibs:
        other |= set(_toks(summ[k][0]))
    seen, out = set(), []
    for w in _toks(summ[cid][0]):
        if w not in other and w not in seen and w not in ('it', 'button', 'is', 'a', 'ctrl', 'shift', 'alt') and w not in summ[cid][1]:
            seen.add(w)
            out.append(w)
    return ' '.join(out[:2])


def readable_title(t0, cid):
    """the title a buyer reads for control page `cid` (enc_gen_A.py uses it too)"""
    t1 = clean_control_title(t0, cid)
    if not t1:
        base, n = cid.split('~')[0], (cid.split('~')[1] if '~' in cid else '')
        t1 = re.sub(r'\s+(button|switch|slider|menu|tab)$', '', control_label(base))
        seg = base.split('.')
        if len(seg) >= 3 and seg[-2].lower() not in t1.lower():
            t1 += ' (%s)' % seg[-2].replace('_', ' ')
        if n:
            t1 += ' %s' % n
    return t1


def humanize(i):
    i = re.sub(r'^(?:sculpt|drop|pro|html|ctl|zone|layer|key)[.:]', '', str(i))
    i = re.sub(r'\.\d+$', '', i)
    i = re.sub(r'^(?:btn|s|n|chk|sel|inp|cb)(?=[A-Z])', '', i)
    i = re.sub(r'([a-z])([A-Z])', r'\1 \2', i).replace('_', ' ').replace('.', ' ')
    i = re.sub(r'\s+', ' ', i).strip()
    return i[:1].upper() + i[1:].lower() if i else i


# ------------------------------------------------------------------ rule 3: Do-it labels
_UI = None


def ui_labels():
    global _UI
    if _UI is None:
        _UI = {}
        try:
            for it in json.load(open(os.path.join(HERE, 'ui_map.json'), encoding='utf-8')).get('items') or []:
                if it.get('id') and it.get('label'):
                    _UI[it['id']] = it
        except Exception:
            pass
    return _UI


KIND_WORD = {'button': 'button', 'toggle': 'switch', 'checkbox': 'switch', 'slider': 'slider', 'dropdown': 'menu', 'tab': 'tab'}


def control_label(cid):
    it = ui_labels().get(cid)
    lab = str((it or {}).get('label') or '')
    lab = LEAD.sub('', lab).strip()
    if not lab or FRAGMENT.search(lab) or len(lab) > 48:
        lab = humanize(cid)
    if it and it.get('kind') in KIND_WORD and not re.search(r'\b(button|box|switch|slider|menu|dropdown|tab|checkbox)\b', lab, re.I):
        lab += ' ' + KIND_WORD[it['kind']]
    return lab


# ------------------------------------------------------------------ files (format-preserving, like search_lab/apply_aliases.py)
def files():
    out = [os.path.join(ENC, f) for f in sorted(os.listdir(ENC)) if f.endswith('.json') and not f.startswith('_') and f not in ('screens.json', 'figures.json')]
    pd = os.path.join(ENC, 'pages')
    out += [os.path.join(pd, f) for f in sorted(os.listdir(pd)) if f.endswith('.json') and not f.startswith('_')]
    return out


def dumps(d, src):
    c = [json.dumps(d, ensure_ascii=False, indent=1), json.dumps(d, ensure_ascii=True, indent=1),
         json.dumps(d, ensure_ascii=False, separators=(',', ':')), json.dumps(d, ensure_ascii=True, separators=(',', ':'))]
    m = re.match(r'^(\{.*?"articles": ?\[\n)', src, re.S)
    if m:
        for ea in (False, True):
            c.append(m.group(1) + ',\n'.join(json.dumps(a, ensure_ascii=ea, separators=(',', ':')) for a in d['articles']) + '\n]}')
    return c


def fmt_of(src, d):
    for i, c in enumerate(dumps(d, src)):
        for tail in ('', '\n'):
            if c + tail == src:
                return i, tail
    return None


def load(p):
    raw = open(p, 'rb').read().decode('utf-8')
    crlf = '\r\n' in raw
    src = raw.replace('\r\n', '\n')
    return json.loads(src), src, crlf


def save(p, d, src, crlf, fmt):
    out = dumps(d, src)[fmt[0]] + fmt[1]
    if crlf:
        out = out.replace('\n', '\r\n')
    tmp = p + '.tmp'
    with open(tmp, 'wb') as fh:
        fh.write(out.encode('utf-8'))
    os.replace(tmp, p)


# ------------------------------------------------------------------ the pass
def main():
    write = '--write' in sys.argv
    load_shelves()
    scr = json.load(open(os.path.join(ENC, 'screens.json'), encoding='utf-8'))
    S = {s['id']: s for s in scr.get('screens') or []}
    cur = {}
    for s in S.values():
        for x in s.get('article_ids') or []:
            cur.setdefault(x, set()).add(s['id'])
    fj = json.load(open(os.path.join(ENC, 'figures.json'), encoding='utf-8'))
    F = {f['id']: f for f in (fj if isinstance(fj, list) else (fj.get('figures') or fj.get('items') or [])) if isinstance(f, dict) and f.get('id')}
    rep = {'pictures': [], 'titles': [], 'labels': [], 'unwritable': [], 'added': [], 'exempt': []}
    nfiles = 0
    arts_by_id = {}
    SUMM = {}
    for p in files():
        if os.path.basename(p).startswith('controls_'):
            try:
                for a in (load(p)[0].get('articles') or []):
                    if isinstance(a, dict) and a.get('id'):
                        SUMM[(a.get('covers') or [a['id'].split('.', 1)[-1]])[0]] = (str(a.get('summary') or ''), dtitle(a.get('title')))
            except Exception:
                pass
    for p in files():
        try:
            d, src, crlf = load(p)
        except Exception:
            continue
        if not isinstance(d, dict) or not isinstance(d.get('articles'), list):
            continue
        fmt = fmt_of(src, d)
        dirty = False
        for a in d['articles']:
            if not isinstance(a, dict) or not a.get('id'):
                continue
            aid = a['id']
            arts_by_id[aid] = a
            # 1. pictures on the article itself
            keep = []
            for sid in a.get('screens') or []:
                s = S.get(sid)
                if not s:
                    keep.append(sid)
                    continue
                ok, why = screen_ok(a, s, curated=sid in cur.get(aid, ()))
                if ok:
                    keep.append(sid)
                else:
                    rep['pictures'].append({'id': aid, 'title': a.get('title'), 'pic': sid, 'pic_title': s.get('title'), 'why': why, 'src': 'article.screens'})
            if keep != list(a.get('screens') or []):
                a['screens'] = keep
                dirty = True
            fk = []
            for fid in a.get('figures') or []:
                f = F.get(fid)
                ok, why = figure_ok(a, f) if f else (True, '')
                if ok:
                    fk.append(fid)
                else:
                    rep['pictures'].append({'id': aid, 'title': a.get('title'), 'pic': fid, 'pic_title': f.get('title'), 'why': why, 'src': 'article.figures'})
            if fk != list(a.get('figures') or []):
                a['figures'] = fk
                dirty = True
            # 1a. a hand-written page left with no picture gets the best RIGHT one (the depth bar wants >= 1), never a wrong one
            if not a.get('screens') and not a.get('generated') and not os.path.basename(p).startswith(('controls_', 'finish_', 'pattern_', 'specpat_', 'help_')) \
                    and not (isinstance(a.get('screens_exempt'), str) and len(a['screens_exempt'].strip()) >= 20 and not a['screens_exempt'].startswith(OUR_EXEMPT[:30])):
                pick = best_screen(a, S, cur)
                if pick:
                    a['screens'] = [pick]
                    a.pop('screens_exempt', None)
                    rep['added'].append({'id': aid, 'title': a.get('title'), 'pic': pick, 'pic_title': S[pick].get('title')})
                    dirty = True
                elif a.get('screens_exempt') != OUR_EXEMPT:
                    a['screens_exempt'] = OUR_EXEMPT
                    rep['exempt'].append({'id': aid, 'title': a.get('title')})
                    dirty = True
            # 1b. a worked example's own picture: judged against THAT example (title, goal, settings, result)
            for ex in a.get('examples') or []:
                sid = ex.get('screen') if isinstance(ex, dict) else None
                s = S.get(sid) if sid else None
                if not s:
                    continue
                st = ex.get('settings') or {}
                pseudo = {'id': aid + '#example', 'title': ex.get('title') or '', 'aliases': [], 'actions': [],
                          'summary': ' '.join([str(ex.get('goal') or ''), str(ex.get('result') or '')] + ['%s %s' % (k, v) for k, v in st.items()])}
                ok, why = screen_ok(pseudo, s, curated=False)
                if not ok:
                    rep['pictures'].append({'id': aid, 'title': a.get('title'), 'pic': sid, 'pic_title': s.get('title'), 'why': why, 'src': 'example: ' + str(ex.get('title'))})
                    del ex['screen']
                    dirty = True
            # 2. control page titles
            if re.match(r'^controls_', aid):
                cid = (a.get('covers') or [aid.split('.', 1)[-1]])[0]
                t0 = str(a.get('title') or '')
                t1 = readable_title(t0, cid)
                hint = sibling_hint(cid, SUMM)          # two controls with one label ('90° (placement)' x2): say how they differ
                if hint and hint.lower() not in t1.lower():
                    t1 = re.sub(r'\s+\d+$', '', t1) + ', ' + hint
                elif hint:
                    t1 = t0 if hint.lower() in t0.lower() else t1
                if t1 and t1 != t0:
                    rep['titles'].append({'id': aid, 'from': t0, 'to': t1})
                    a['title'] = t1
                    for c in a.get('controls') or []:
                        if isinstance(c, dict) and c.get('label') == t0 or (isinstance(c, dict) and FRAGMENT.search(str(c.get('label') or ''))):
                            c['label'] = t1
                    for k in ('summary', 'what'):
                        if isinstance(a.get(k), str) and t0 and t0 in a[k]:
                            a[k] = a[k].replace(t0, t1)
                    dirty = True
            # 3. Do-it labels
            for x in a.get('actions') or []:
                if isinstance(x, dict) and x.get('do') == 'control' and x.get('id') and not x.get('label'):
                    c = [c for c in (a.get('controls') or []) if isinstance(c, dict) and c.get('inv') == x['id'] and c.get('label') and not FRAGMENT.search(str(c['label']))]
                    if c:
                        continue          # the reader already shows the page's own control name
                    x['label'] = control_label(x['id'])
                    rep['labels'].append({'id': aid, 'control': x['id'], 'label': x['label']})
                    dirty = True
        if dirty:
            nfiles += 1
            if write:
                if fmt is None:
                    rep['unwritable'].append(os.path.relpath(p, ROOT))
                else:
                    save(p, d, src, crlf, fmt)
    # lane S's own article_ids in screens.json: car renders credited to pages that never name the finish
    sdirty = False
    for s in S.values():
        if s.get('kind') != 'car_render':
            continue
        ids = []
        for x in s.get('article_ids') or []:
            a = arts_by_id.get(x)
            ok, why = screen_ok(a, s, curated=True) if a else (True, '')
            if ok:
                ids.append(x)
            else:
                rep['pictures'].append({'id': x, 'title': a.get('title'), 'pic': s['id'], 'pic_title': s.get('title'), 'why': why, 'src': 'screens.article_ids'})
        if ids != list(s.get('article_ids') or []):
            s['article_ids'] = ids
            sdirty = True
    if sdirty and write:
        sp = os.path.join(ENC, 'screens.json')
        d0, src0, crlf0 = load(sp)
        f0 = fmt_of(src0, d0)
        if f0 is None:
            rep['unwritable'].append('data/encyclopedia/screens.json')
        else:
            save(sp, scr, src0, crlf0, f0)
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    with open(AUDIT, 'w', encoding='utf-8') as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print('ENC_READER_FIX %s: pictures dropped %d, right pictures added %d, no-picture exempt %d, control titles %d, Do-it labels %d, files %d%s' % (
        'WRITTEN' if write else 'AUDIT', len(rep['pictures']), len(rep['added']), len(rep['exempt']), len(rep['titles']), len(rep['labels']), nfiles,
        (' UNWRITABLE %s' % rep['unwritable']) if rep['unwritable'] else ''))


if __name__ == '__main__':
    main()

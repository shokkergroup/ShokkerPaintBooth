#!/usr/bin/env python
"""Encyclopedia v2, lane C close-out generator (2026-10-04): help pages generated from the shipped help sources.

  data/encyclopedia/help_pages.json                (manifest {domain, version, articles:[], parts:[...]}, like lane A/B)
  data/encyclopedia/pages/help_<kind>_<n>.json     (parts <= 95 KB; part domain help_<kind>_<n>; page id help_<kind>_<n>.<slug>)

Sources (nothing is invented; every page carries sources[] and covers[] = the inventory record it explains):
  howto  : hdi.* records  <- scripts/ai_atlas/enc_inventory.json facts.steps (curated how-do-I answers, from scripts/ai_atlas/ui_map.json)
  topics : topic.*        <- js/spb-self-help.js TOPICS (steps are the exact lines the offline helper shows; read via enc_gen_C2_dump.js)
  support: support.*      <- js/spb-support-answers.js FAQ + pasted-error answers (read via enc_gen_C2_dump.js)
  guide  : gs.*           <- GETTING_STARTED.html sections (heading line numbers from the inventory)
Only inventory records NOT already named by some article's covers[] get a page, so re-running never duplicates hand-written work.
Run:  python scripts/ai_atlas/enc_gen_C2.py          (deterministic, atomic writes, one summary line)
"""
import glob, html, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enc_write_C import norm, _other_aliases, TODAY  # same alias normaliser as the gate

DIR = ROOT / 'data' / 'encyclopedia'
PAGES = DIR / 'pages'
import enc_help_v3 as V3   # v3 enrichment (2026-10-04)
import enc_hidden as H   # owner rule 2026-10-04: hidden features (Easy mode) get no pages and are scrubbed out of every page
_ALL_INV = json.loads((ROOT / 'scripts' / 'ai_atlas' / 'enc_inventory.json').read_text(encoding='utf-8'))['records']
INV = [r for r in _ALL_INV if not r.get('hidden')]
BYID = {r['id']: r for r in INV}
PART_MAX = 92 * 1024

MODE_TXT = {'pro': 'Pro mode', 'chat': 'Chat mode', 'any': 'any mode'}
NEEDS_TXT = {'paint': 'a paint loaded', 'psd': 'a layered PSD template loaded', 'car_folder': 'the iRacing Car Folder set', 'zone': 'a zone', 'selected': 'a zone selected', 'none': ''}

# keyword -> related article (all ids exist; the gate checks them)
REL = [
    (r'\b(user id|customer id)\b', 'workflows.user_id_and_folder'),
    (r'\b(trading paints)\b', 'support.trading_paints'),
    (r'\b(licen[sc]e|activat)', 'settings.activation_license'),
    (r'\b(ai key|openrouter|deepseek|api key|claude|chatgpt|codex|mcp)\b', 'ai_copilot.gear_key_model'),
    (r'\b(chat|copilot|helper)\b', 'ai_copilot.chat_mode'),
    (r'\b(car folder|where.{0,12}files|deploy|iracing folder)\b', 'preview_render.where_files_go'),
    (r'\b(number|custom number|sim.stamped)\b', 'preview_render.number_modes'),
    (r'\b(render)\b', 'preview_render.render_button'),
    (r'\b(reload|ctrl\+r)\b', 'preview_render.reload_in_iracing'),
    (r'\b(psd|template|layer)', 'layers.open_psd'),
    (r'\b(zone)', 'zones.what_is_a_zone'),
    (r'\b(spec|shine|chrome|metal|clearcoat|roughness)', 'spec.what_is_spec_map'),
    (r'\b(undo)\b', 'tools.undo_redo'),
    (r'\b(save|project)', 'preview_render.saving_projects'),
    (r'\b(part|hood|roof|car map)', 'cars.teach_parts'),
    (r'\b(preview)\b', 'preview_render.preview_vs_render'),
    (r'\b(problem|error|wrong|stuck|fail)', 'support.reporting_problem'),
]


def related_for(text, selfid, extra=()):
    out = list(extra)
    t = text.lower()
    for rx, rid in REL:
        if rid not in out and rid != selfid and re.search(rx, t):
            out.append(rid)
        if len(out) >= 4:
            break
    return out[:4] or ['workflows.what_is_shokker']


# ------------------------------------------------------------------------------------------------ text helpers
def demoji(s):
    return re.sub(r'[\U0001F000-\U0001FFFF☀-➿⬀-⯿️]', '', s)


def clean(t):
    t = html.unescape(str(t or ''))
    t = t.replace('**', '').replace('`', '').replace('→', '>').replace('\\', ' > ')
    t = t.replace('⚙️', 'the Settings gear').replace('⚙', 'the Settings gear').replace('\U0001F4C2', '')
    t = re.sub(r'<[^>]+>', ' ', t)
    t = demoji(t)
    return re.sub(r'[ \t]+', ' ', t).strip()


def sentences(s):
    return len(re.findall(r'[.!?](\s|$)', s))


def first_sentences(text, maxlen=300, n=1):
    text = re.sub(r'\s+', ' ', text).strip()
    parts = re.findall(r'.+?[.!?](?:\s|$)', text) or [text]
    out = ''
    for p in parts[:n]:
        if len(out) + len(p) > maxlen:
            break
        out += p
    if not out:
        # FACTCHECK 2026-10-04: the old hard cut left summaries ending "... troubleshooter and the." - cut at the last comma/semicolon instead,
        # and never end on a connector word.
        cut = text[:maxlen]
        k = max(cut.rfind(', '), cut.rfind('; '))
        cut = cut[:k] if k > maxlen * 0.5 else cut.rsplit(' ', 1)[0]
        cut = re.sub(r'(?:\s+(?:and|or|the|a|an|of|to|with|plus|in|for|but|that|which))+$', '', cut.rstrip(',;: '), flags=re.I)
        out = cut.rstrip(',;:') + '.'
    return out.strip()


def cap(t, n):
    t = t.strip()
    if len(t) <= n:
        return t
    cut = t[:n]
    m = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
    return (cut[:m + 1] if m > n * 0.5 else cut.rsplit(' ', 1)[0].rstrip(',;:') + '.')


def slug(i, strip_prefix):
    s = i[len(strip_prefix):] if i.startswith(strip_prefix) else i
    return re.sub(r'[^A-Za-z0-9_.\-]', '_', s)


def _scrub_list(xs):
    return [y for y in (H.scrub(x, True) for x in xs) if y]


def mk(domain, sl, title, summary, what, when, how, tips, pitfalls, related, actions, covers, sources, aliases):
    # hidden-feature filter: rewrite / drop every sentence about it; a page whose title or whole body is about it is not made (None)
    if H.mentions(title) or H.scrub(title, True) != title:
        return None
    summary, what = H.scrub(summary, True), H.scrub(what, True)
    when, how, tips, pitfalls = _scrub_list(when), _scrub_list(how), _scrub_list(tips), _scrub_list(pitfalls)
    aliases = [a for a in aliases if not H.mentions(a) and not re.search(r'\beasy\b', a, re.I)]
    related = [r for r in related if not H.is_hidden_article_id(r)]
    actions = [x for x in actions if not H.is_hidden_id(x.get('id', ''))]
    if not what and not summary and not how:
        return None
    if not summary:
        summary = first_sentences(what, 300, 1) if what else (how[0] if how else title)
    if not what:
        what = summary
    return {
        'id': domain + '.' + sl, 'title': title[:110], 'domain': domain, 'summary': summary, 'what': what,
        'when': when, 'how': how, 'controls': [], 'tips': tips, 'pitfalls': pitfalls, 'related': related, 'actions': actions,
        'figures': [], 'covers': covers, 'sources': sources, 'quick': False, 'lane': 'C', 'updated': TODAY,
        'aliases': aliases, 'generated': True,
    }


# ------------------------------------------------------------------------------------------------ control ids (actions)
def control_ids():
    ids = set()
    for r in INV:
        f = r.get('facts') or {}
        if f.get('ui_kind') or f.get('handler') or r['kind'] == 'zone_param':
            ids.add(r['id'])
    try:
        for c in json.loads((ROOT / 'scripts' / 'ai_atlas' / 'app_controls.json').read_text(encoding='utf-8'))['controls']:
            ids.add(c['id'])
    except Exception:
        pass
    sh = (ROOT / 'js' / 'spb-self-help.js').read_text(encoding='utf-8')
    m = re.search(r'var UI_DATA = (\[.*?\]);\s*\n', sh, re.S)
    if m:
        for c in json.loads(m.group(1)):
            ids.add(c['id'])
    return ids


# ------------------------------------------------------------------------------------------------ builders
def build_howto(rec, ctl):
    f = rec['facts']
    label = clean(rec['label']).rstrip('?').strip()
    steps = [cap(clean(s), 400) for s in f.get('steps', []) if clean(s)]
    mode = f.get('mode', 'pro')
    needs = [NEEDS_TXT.get(n, n) for n in f.get('needs', []) if NEEDS_TXT.get(n, n)]
    ui_labels = []
    for u in f.get('ui', []):
        r = BYID.get(u)
        if r and r.get('label'):
            ui_labels.append(clean(r['label'])[:50])
    first = first_sentences(steps[0], 260) if steps else label + '.'
    what = 'Short answer to "%s" (%s).' % (label, MODE_TXT.get(mode, mode))
    if needs:
        what += ' You need ' + ' and '.join(needs) + ' first.'
    if ui_labels:
        what += ' Controls involved: ' + ', '.join(ui_labels[:6]) + '.'
    pit = []
    if not steps:
        return None
    actions = [{'do': 'control', 'id': u} for u in f.get('ui', []) if u in ctl][:3]
    txt = label + ' ' + ' '.join(steps)
    sl = slug(rec['id'], 'hdi.')
    al = []
    n = norm(label)
    if n.count(' ') >= 2:
        al.append(n)
    return ('howto', mk('', sl, label[0].upper() + label[1:] + '?', first_sentences(steps[0], 260), what, ['You asked: ' + label + '?'], steps, [], pit,
                        related_for(txt, ''), actions, [rec['id']], [rec['source']], al))


def build_topic(rec, T):
    t = T.get(rec['id'][6:])
    if not t or not t.get('steps'):
        return None
    title = clean(t['title'])
    steps = [cap(clean(s), 400) for s in t['steps'] if clean(s)]
    needs = [NEEDS_TXT.get(n, n) for n in (t.get('needs') or []) if NEEDS_TXT.get(n, n)]
    what = 'The built-in helper answers "%s" with these steps.' % title
    if needs:
        what += ' You need ' + ' and '.join(needs) + ' first.'
    tips = []
    if t.get('say'):
        tips.append(cap(clean(t['say']), 200)[0].upper() + cap(clean(t['say']), 200)[1:])
    pit = []
    txt = title + ' ' + t.get('kw', '') + ' ' + ' '.join(steps)
    al = []
    n = norm(title)
    if n.count(' ') >= 1:
        al.append(n)
    return ('topics', mk('', slug(rec['id'], 'topic.'), title, first_sentences(steps[0], 260), what, ['You want to: ' + title.lower() + '.'], steps, tips, pit,
                         related_for(txt, ''), [], [rec['id']], [rec['source']], al))


def md_to_parts(text):
    """-> (segments in order [paragraph text, bullets as sentences], numbered steps)"""
    segs, how = [], []
    for raw in str(text or '').split(chr(10)):
        l = raw.strip()
        if not l:
            continue
        m = re.match(r'^(\d+)[.)]\s+(.*)$', l)
        if m:
            how.append(cap(clean(m.group(2)), 400)); continue
        m = re.match(r'^[-*]\s+(.*)$', l)
        if m:
            b = cap(clean(m.group(1)), 400)
            segs.append(b if b.endswith(('.', '!', '?')) else b + '.'); continue
        segs.append(clean(l))
    return segs, how


def build_support(rec, S):
    sid = rec['facts']['support_id']
    s = S.get(sid)
    if not s or not s.get('text'):
        return None
    what, how = md_to_parts(s['text'])
    bullets = []
    title = clean(s.get('title') or rec['label'])
    TITLE_FIX = {'support.thanks': 'Saying thanks to the helper', 'support.insult': 'When something is frustrating', 'support.getting_started': 'Getting started with the helper'}
    if rec['id'] in TITLE_FIX:
        title = TITLE_FIX[rec['id']]
    if rec['kind'] == 'faq' and rec['id'] not in TITLE_FIX:
        raw_title = re.match(r'^\*\*(.+?)\*\*', s['text'])
        if raw_title:
            title = clean(raw_title.group(1))
            if what and what[0] == title:
                what = what[1:]
    if rec['kind'] == 'error_answer':
        title = title[0].upper() + title[1:] if title else rec['label']
    body = ' '.join(what)
    if bullets:
        body += ' ' + ' '.join(('Option: ' + b if len(bullets) > 1 else b) for b in bullets)
    body = body.strip()
    if not body:
        return None
    summary = first_sentences(body, 300, 1)
    wh = ('If you see the message "%s", here is what it means. ' % clean(rec['label']) if rec['kind'] == 'error_answer' and not re.search(r'message', title, re.I) and False else '') + body
    txt = title + ' ' + body
    al = []
    n = norm(title)
    if n.count(' ') >= 1 and rec['kind'] == 'faq':
        al.append(n)
    elif rec['kind'] == 'error_answer' and n.count(' ') >= 2:
        al.append(n)
    when = ['You asked the built-in helper: ' + title + '.'] if rec['kind'] == 'faq' else ['The app showed a message about: ' + clean(rec['label']) + '.']
    return ('support', mk('', slug(rec['id'], 'support.'), title, summary, cap(wh, 1900), when, how, [], [],
                          related_for(txt, '', ['support.reporting_problem'] if rec['kind'] == 'error_answer' else []), [], [rec['id']], [rec['source']], al))


GS_LINES = (ROOT / 'GETTING_STARTED.html').read_text(encoding='utf-8').split('\n')


def build_guide(rec, end):
    start = int(rec['source'].split(':')[1])
    paras, how = [], []
    for i in range(start, min(end, len(GS_LINES))):
        t = clean(re.sub(r'<(script|style).*?</\1>', ' ', GS_LINES[i], flags=re.S))
        if not t:
            continue
        m = re.match(r'^(?:STEP\s+)?(\d{1,2})\s+(.*)$', t)
        if m and len(t) < 600:
            how.append(cap(m.group(2), 400)); continue
        paras.append(t)
    title = clean(rec['label'])
    if not paras and not how:
        return None
    body = ' '.join(paras) or ' '.join(how)
    pit = ['This page comes from the older Getting Started guide, written during the beta. Where it differs from what you see (for example the number of quests), trust the screen.']
    al = []
    n = norm(title)
    if n.count(' ') >= 2:
        al.append(n)
    lead = next((p for p in paras if len(p) >= 50), None) or (how[0] if how else body)
    summary = first_sentences(lead, 300, 1)
    return ('guide', mk('', slug(rec['id'], 'gs.'), title, summary, cap(body, 1800), ['You are reading the Getting Started guide section: ' + title + '.'], how, [], pit,
                        related_for(title + ' ' + body, ''), [], [rec['id']], [rec['source']], al))


# ------------------------------------------------------------------------------------------------ main
def covered_ids():
    cov = set()
    for f in glob.glob(str(DIR / '*.json')) + glob.glob(str(PAGES / '*.json')):
        if os.path.basename(f).startswith('help_'):
            continue
        try:
            d = json.loads(open(f, encoding='utf-8').read())
        except Exception:
            continue
        if isinstance(d, dict):
            for a in d.get('articles', []):
                cov.update(a.get('covers', []))
    return cov


def write_atomic(path, text):
    tmp = str(path) + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, path)


def main():
    dump = subprocess.run(['node', str(ROOT / 'scripts' / 'ai_atlas' / 'enc_gen_C2_dump.js')], capture_output=True, cwd=str(ROOT))
    if dump.returncode != 0:
        sys.exit('dump failed: ' + dump.stderr.decode('utf-8', 'replace')[:300])
    D = json.loads(dump.stdout.decode('utf-8'))
    S = {f['id']: f for f in D['faqs'] + D['errs']}
    T = {t['id']: t for t in D['topics']}
    ctl = control_ids()
    cov = covered_ids()
    gs_sorted = sorted([r for r in INV if r['id'].startswith('gs.')], key=lambda r: int(r['source'].split(':')[1]))
    gs_end = {r['id']: (int(gs_sorted[i + 1]['source'].split(':')[1]) - 1 if i + 1 < len(gs_sorted) else len(GS_LINES)) for i, r in enumerate(gs_sorted)}
    made = {'howto': [], 'topics': [], 'support': [], 'guide': []}
    skipped = []
    for r in INV:
        if r['id'] in cov:
            continue
        b = None
        if r['id'].startswith('hdi.'):
            b = build_howto(r, ctl)
        elif r['id'].startswith('topic.'):
            b = build_topic(r, T)
        elif r['id'].startswith('support.') and r['kind'] in ('faq', 'error_answer'):
            b = build_support(r, S)
        elif r['id'].startswith('gs.'):
            b = build_guide(r, gs_end[r['id']])
        else:
            continue
        if b is None or b[1] is None:
            skipped.append(r['id'])
            continue
        made[b[0]].append((r, b[1]))

    # ---- v3 enrichment (2026-10-04): short Q&A pages -> real articles (deep / faq / mistakes / combos); see enc_help_v3.py
    ART = {}
    for f in glob.glob(str(DIR / '*.json')) + glob.glob(str(PAGES / '*.json')):
        if os.path.basename(f).startswith('help_'):
            continue
        try:
            dd = json.loads(open(f, encoding='utf-8').read())
        except Exception:
            continue
        if isinstance(dd, dict):
            for ar in dd.get('articles', []):
                for cid in ar.get('covers', []):
                    ART.setdefault(cid, ar['id'])

    def sc(s):
        s = str(s or '')
        return H.scrub(s, True) if H.mentions(s) else s
    PBT = {}
    for kind_, items_ in made.items():
        for r_, a_ in items_:
            PBT.setdefault(norm(V3.TITLE_OVR.get(a_['id'].lstrip('.'), a_['title'])), (kind_, a_))
    NEXT = {f['id']: f.get('next') or [] for f in D['faqs'] + D['errs']}

    class _PB(dict):
        def get(self, k, d=None):
            v = dict.get(self, k)
            return None if v is None else {'id': '@' + v[0] + v[1]['id'], 'summary': v[1]['summary']}
    ctx = {'BYID': BYID, 'ART': ART, 'sc': sc, 'PAGE_BY_TITLE': _PB(PBT), 'NEXT': NEXT, 'TOPIC': T, 'norm': norm}
    for kind_, items_ in made.items():
        for r_, a_ in items_:
            V3.enrich(kind_, r_, a_, ctx)
    FINAL = {}   # '@kind.slug' placeholder -> final page id

    taken = {k: v for k, v in _other_aliases('help_').items() if not str(v).startswith('help_')}
    seen = set()
    manifest_parts, total, nbytes = [], 0, 0
    PAGES.mkdir(parents=True, exist_ok=True)
    for old in glob.glob(str(PAGES / 'help_*.json')):
        os.remove(old)
    PLAN = {}
    for kind in ('howto', 'topics', 'support', 'guide'):
        items = sorted(made[kind], key=lambda x: x[0]['id'])
        __import__('enc_ui_fix').fix_articles([a for _r, a in items])   # UI audit 2026-10-05
        parts, cur, size = [], [], 0
        for r, a in items:
            for key in ('title', 'summary', 'what'):
                a[key] = a[key].strip()
            sz = len(json.dumps(a, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) + 2
            if cur and size + sz > PART_MAX:
                parts.append(cur); cur, size = [], 0
            cur.append((r, a)); size += sz
        if cur:
            parts.append(cur)
        PLAN[kind] = parts
        for n, part in enumerate(parts, 1):
            for r, a in part:
                FINAL['@' + kind + a['id']] = 'help_%s_%d' % (kind, n) + a['id']
    for kind in ('howto', 'topics', 'support', 'guide'):
        parts = PLAN[kind]
        for n, part in enumerate(parts, 1):
            dom = 'help_%s_%d' % (kind, n)
            arts = []
            for r, a in part:
                a = dict(a)
                a['related'] = [FINAL.get(x, x) for x in a['related'] if not x.startswith('@') or x in FINAL]
                a['id'] = dom + a['id']       # '' domain was empty: id = '.' + slug  -> dom + '.' + slug
                a['domain'] = dom
                al = []
                for x in a['aliases']:
                    nn = norm(x)
                    if nn and nn not in seen and nn not in taken:
                        seen.add(nn); al.append(nn)
                a['aliases'] = al
                if not al:
                    del a['aliases']
                arts.append(a)
            head = {'domain': dom, 'version': 1, 'generated': True}
            body = ',\n'.join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in arts)
            text = json.dumps(head, ensure_ascii=False)[:-1] + ',"articles":[\n' + body + '\n]}\n'
            fp = PAGES / (dom + '.json')
            write_atomic(fp, text)
            b = len(text.encode('utf-8'))
            manifest_parts.append({'file': 'pages/%s.json' % dom, 'domain': dom, 'group': kind, 'count': len(arts), 'bytes': b,
                                   'firstKey': part[0][0]['id'], 'lastKey': part[-1][0]['id']})
            total += len(arts); nbytes += b
    man = {'domain': 'help_pages', 'version': 1, 'articles': [], 'generated': True,
           'note': 'One page per help-source record that no hand-written article covers (how-do-I answers, self-help topics, support answers, Getting Started sections). Generated by scripts/ai_atlas/enc_gen_C2.py; part files live in pages/.',
           'pageCount': total, 'bytes': nbytes, 'parts': manifest_parts}
    write_atomic(DIR / 'help_pages.json', json.dumps(man, ensure_ascii=False, indent=1) + '\n')
    print('help_pages: %d pages in %d parts (%d KB): %s; skipped %d %s' % (total, len(manifest_parts), nbytes // 1024,
          ', '.join('%s %d' % (k, len(v)) for k, v in made.items()), len(skipped), skipped[:6]))


if __name__ == '__main__':
    main()

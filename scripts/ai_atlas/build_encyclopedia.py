# -*- coding: utf-8 -*-
"""build_encyclopedia.py - compiles js/spb-encyclopedia-data.js (window.SPB_ENCYCLOPEDIA), the offline helper's keyword encyclopedia.
Deterministic and re-runnable:   python scripts/ai_atlas/build_encyclopedia.py            (writes the data file + prints one summary line)
AI-as-compiler: hand recipes live in encyclopedia_recipes.py; everything else (finish choices, colours, parts, shelves, tags, slang, schemes,
every word the offline parser understands) is DERIVED from the shipped sources, so a new finish / colour / parser word needs a re-run, not typing.
Pipeline: node enc_extract.js -> _easy_claude_work/enc/extract.json -> terms -> alias index -> js/spb-encyclopedia-data.js (+ _easy_claude_work/enc/build_stats.json).
Never invents ids: every choice is an atlas key, every link target is checked against the support answers / self-help / UI controls / GETTING_STARTED headings."""
import json, os, re, sys, subprocess, hashlib, html, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import encyclopedia_recipes as R

WORK = os.path.join(ROOT, '_easy_claude_work', 'enc')
OUT_JS = os.path.join(ROOT, 'js', 'spb-encyclopedia-data.js')
VERSION_DATE = '2026-10-04'

# ------------------------------------------------------------------------------------------------ helpers
def norm(s):
    s = str(s or '').lower().replace('’', '').replace("'", '').replace('`', '')
    s = re.sub(r'[^a-z0-9#]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def read(p):
    with open(os.path.join(ROOT, p), encoding='utf8', errors='replace') as f:
        return f.read()

def cap(s):
    return s[:1].upper() + s[1:]

def strip_emoji(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^\x20-\x7e]', ' ', s)).strip()

def title_of(s):
    s = strip_emoji(s)
    if s.isupper() and len(s) > 3: return s.title()
    return s

STOP = set(('about above after again against also always another around because been before being below between both bring brings build builds came come comes could does doing done down during each either else even ever every from gets give gives going gone have having here into just keep kind know less like made make makes many more most much must never next none only onto other others over same should since some soon still such take than that their them then there these they thing things think this those through today under until upon very want wants were what when where which while will with within without would your yours '
            'dense fine large small thin thick wide very super extra lots busy loud calm soft hard high long short deep light dark bright plain clear simple mixed tiny huge great good best nice cool look looks looking style finish finishes texture textures pattern patterns field fields effect effects design designs paint painted colour colours color colors panel panels paneling over under across along along inside outside body hood roof sides door doors full half whole entire layer layers detail details detailed contrast shape shapes line lines edge edges color overall repeat repeated repeating random scale scaled tone tones toned shade shades shaded base based type types made using used uses feel feels feeling reads reading read heavy mostly mainly slightly subtle strong weak rich wild bold lots lot').split())

WEAK_SINGLE = set(('car cars truck body base look looks make made paint front rear back side sides part parts area areas the bed nose tail wing dash seat light lights plate plates handle handles vent vents start begin new image picture group groups line lines detail details accent accents trim graphic graphics select selection sim pro easy free help guide ai tp mat flat wet mirror tile tiles web bat rose sun rays check checks scale design speed slow lag fast raw bare clear film wrap wraps flow fluid cloud clouds mist fog steam haze ink pour spray drip drips arc arcs spark sparks static shock tesla storm king money cash bank dollar dollars treasure window windows glass door doors left right sea pool tree trees grass moss nature natural forest woods mat fire burn burning blaze glow glowing salt dirt mud sunny summer beach horizon dawn dusk wave waves rain water liquid ice snow winter frost frozen steel iron stone rock rocks concrete cement log bark wood grain army military combat armor armour bullet code digital arcade matrix comic dot dots spots spotted cow cobra viper python snake snakes dragon dragons tiger tigers zebra jaguar eagle bat bats spider spiders witch witches devil evil death grim bone bones skull skulls ghost ghosts monster monsters vampire zombie halloween wine cherry ruby jewel jewels gem gems diamond diamonds king queen classic vintage retro disco groovy diner pearl pearls mica silk silky satin velvet suede chalk chalky dull plain primer sheen polish polished factory showroom piano glaze lacquer enamel ceramic gloss glossy shiny shine shinier glossier flake flakes glitter sparkle sparkles bling glam fade fades blend blends band bands stripe stripes pop zing contrast boost flip deeper richer bolder brighter darker lighter muted faded paler subdued electric neon cyber tech techy grid grids mesh circuit circuits lattice poly shapes shape abstract geo lightning bolt bolts thunder plasma space stars star cosmic cosmos galaxy planet planets universe astro')) 
WEAK_SINGLE -= set(('galaxy', 'camo', 'chrome', 'candy', 'holographic', 'snakeskin', 'carbon', 'flames', 'marble', 'gradient', 'matte', 'pearl'))

# ------------------------------------------------------------------------------------------------ load sources
def run_extract():
    os.makedirs(WORK, exist_ok=True)
    out = os.path.join(WORK, 'extract.json')
    r = subprocess.run(['node', os.path.join(HERE, 'enc_extract.js'), out], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        sys.exit('enc_extract.js failed: ' + (r.stderr or r.stdout)[:400])
    with open(out, encoding='utf8') as f:
        return json.load(f), r.stdout.strip()

# FACTCHECK R2 2026-10-04: give every cited file:line an anchor, then snap drifted lines back onto their anchor (see enc_source_anchors.py).
for _m in ('--build', '--repair'):
    _r = subprocess.run([sys.executable, os.path.join(HERE, 'enc_source_anchors.py'), _m], capture_output=True, text=True, cwd=ROOT)
    print('anchors', _m, (_r.stdout.strip().splitlines() or ['?'])[0], '' if _r.returncode == 0 else '(exit %d: %s)' % (_r.returncode, ' | '.join(_r.stdout.strip().splitlines()[1:4])))
X, extract_line = run_extract()
ITEMS = X['atlas']['items']
SECT = X['atlas']['sections']
CARDS = X['cards']
D = X['design']
P = X['parser']
ITEM_BY_KEY = {i['k']: i for i in ITEMS}

# support answers (FAQ + ERR ids with a human title)
SUP = {}
txt = read('js/spb-support-answers.js')
for m in re.finditer(r"^\s*F\('([a-z_0-9]+)',.*?\n\s*'(.*?)',\n", txt, re.S | re.M):
    t = re.match(r"\*\*(.+?)\*\*", m.group(2))
    SUP[m.group(1)] = t.group(1) if t else m.group(1).replace('_', ' ')
for m in re.finditer(r"^\s*E\('([a-z_0-9]+)',\s*/.*?/[a-z]*,\s*'([^']*)'", txt, re.M):
    SUP[m.group(1)] = m.group(2)
for m in re.finditer(r"^\s*[FE]\('([a-z_0-9]+)'", txt, re.M):
    SUP.setdefault(m.group(1), m.group(1).replace('_', ' '))
# self-help topics + UI controls
sh = read('js/spb-self-help.js')
HELP = {m.group(1): m.group(2).replace('’', "'") for m in re.finditer(r"\{ id: '([a-z_0-9]+)', kw: '[^']*', title: '([^']*)'", sh)}
CTRL = {}
m = re.search(r'var UI_DATA = (\[.*?\]);\s*\n', sh, re.S)
if m:
    for c in json.loads(m.group(1)):
        CTRL[c['id']] = c.get('label') or c['id']
try:
    for c in json.load(open(os.path.join(HERE, 'app_controls.json'), encoding='utf8'))['controls']:
        CTRL.setdefault(c['id'], c.get('ui_label', c['id']).split(' (')[0])
except Exception:
    pass
# doc headings (GETTING_STARTED.html): anchor = the heading text (verbatim prefix)
DOCS = {}
gs = read('GETTING_STARTED.html')
DOCS['GETTING_STARTED.html'] = [html.unescape(re.sub(r'<[^>]+>', '', h)).strip() for h in re.findall(r'<h[23][^>]*>(.*?)</h[23]>', gs, re.S)]

def link(target):
    kind, _, rest = target.partition(':')
    if kind == 'support' and rest in SUP: return {'label': SUP[rest], 'target': target}
    if kind == 'help' and rest in HELP: return {'label': HELP[rest], 'target': target}
    if kind == 'control' and rest in CTRL: return {'label': CTRL[rest], 'target': target}
    if kind == 'doc':
        f, _, a = rest.partition('#')
        for h in DOCS.get(f, []):
            if a and h.startswith(a): return {'label': 'Guide: ' + a, 'target': target}
    return None

# ------------------------------------------------------------------------------------------------ colours
COLOURS = {}
for k, v in (D.get('COLOURS') or {}).items(): COLOURS[norm(k)] = v
for k, v in (X.get('colourExt') or {}).items(): COLOURS.setdefault(norm(k), v)
for k, v in (P.get('TINT') or {}).items(): COLOURS.setdefault(norm(k), v)

# ------------------------------------------------------------------------------------------------ ranking of catalogue choices
def card_of(k):
    c = CARDS.get(k)
    return c or [None, [], [], 3, 3, 3, 3, 3, 3, 3]

def build_rank_data():
    rd = []
    for it in ITEMS:
        c = card_of(it['k'])
        syn = ' | '.join((c[2] or []))
        ana = ' | '.join((c[1] or []))
        rd.append((it, (it['n'] + ' ' + it['k']).lower(), syn.lower(), ana.lower(), (c[0] or '').lower() + ' ' + (it.get('d') or '').lower(), c))
    return rd
RD = build_rank_data()

def rank(name='', words='', tags=(), shine=None, metal=None, own=None, n=5, exclude=(), shelf=None, types=('base', 'monolithic', 'pattern'), cn=None):
    rn = re.compile(name, re.I) if name else None
    rw = re.compile(words, re.I) if words else None
    tags = set(tags or ())
    res = []
    for it, nm, syn, ana, look, c in RD:
        typ = it['k'].split('::')[0]
        if typ not in types or it['k'] in exclude or 'user-import' in (it.get('t') or []) or 'development' in (it.get('t') or []): continue
        if shelf is not None and shelf not in (it.get('s') or []): continue
        if shine and it.get('shine') not in shine: continue
        if metal and it.get('metal') not in metal: continue
        if own is not None and (it.get('o') or 0) != own: continue
        if cn and not re.search(cn, it.get('cn') or ''): continue
        nh = 1 if (rn and rn.search(nm)) else 0
        sh_ = 1 if (rw and rw.search(syn)) else 0
        ah = 1 if (rw and rw.search(ana)) else 0
        lh = 1 if (rw and rw.search(look)) else 0
        th = len(tags & set(it.get('t') or []))
        if shelf is None and cn is None and not (nh or sh_ or ah or th or (lh and not rn and not tags)): continue
        sc = nh * 50 + sh_ * 25 + ah * 12 + lh * 6 + min(th, 2) * 10 + 0.35 * (it.get('q') or 55) + 5 * (c[3] or 3) + 6 * (c[6] or 3) - 3 * (c[7] or 3) + (8 if (it.get('gold') or it.get('g')) else 0)
        if cn: sc += 5 * (1 if (it.get('o') or 0) == 1 else 0)
        res.append((-sc, it['k'], it))
    res.sort(key=lambda r: (r[0], r[1]))
    out, seen, per = [], set(), collections.Counter()
    for _, k, it in res:
        nmk = norm(it['n'])
        if nmk in seen: continue
        sh0 = (it.get('s') or [-1])[0]
        if per[sh0] >= 2: continue
        seen.add(nmk); per[sh0] += 1; out.append(it)
        if len(out) >= n: break
    if len(out) < n:                      # relax diversity
        for _, k, it in res:
            nmk = norm(it['n'])
            if nmk in seen: continue
            seen.add(nmk); out.append(it)
            if len(out) >= n: break
    return out

def choice_of(it, forced=False):
    k = it['k']; typ, _, ident = k.partition('::')
    ch = {'label': it['n']}
    if typ == 'pattern': ch['pattern_id'] = ident
    elif typ == 'spec': ch['spec_id'] = ident
    else: ch['finish_id'] = k
    c = (it.get('c') or [None])[0]
    if c and not it.get('o'): ch['hex'] = c.lstrip('#')
    return ch

def choices_for(r):
    out, used = [], set()
    names = set()
    def add(it):
        if it and it['k'] not in used and norm(it['n']) not in names:
            used.add(it['k']); names.add(norm(it['n'])); out.append(choice_of(it))
    for k in r.get('fin') or []: add(ITEM_BY_KEY.get(k))
    for p in r.get('pats') or []: add(ITEM_BY_KEY.get('pattern::' + p))
    n = max(3, min(8, r.get('n', 5)))
    for it in rank(name=r.get('name', ''), words=r.get('words', ''), tags=r.get('tags') or (), shine=r.get('shine'), metal=r.get('metal'), own=r.get('own'), n=n + len(used), exclude=used):
        if len([c for c in out if 'spec_id' not in c]) >= n: break
        add(it)
    for s in r.get('specs') or []: add(ITEM_BY_KEY.get('spec::' + s))
    return out

# ------------------------------------------------------------------------------------------------ term registry
TERMS, INDEX, CONFLICTS, ORDER = [], {}, [], {}
SHARED_FLOWS = {
    'paint_part': [{'type': 'ask_look', 'text': 'What should this part get: a colour, a finish or a pattern?'}, {'type': 'ask_colour', 'text': 'Which colour (or keep the current one)?'}, {'type': 'confirm', 'text': 'Apply it to this part only?'}],
    'element': [{'type': 'ask_part', 'text': 'Where should it go: whole car or a part?'}, {'type': 'ask_colour', 'text': 'Which colour?'}, {'type': 'confirm', 'text': 'Add it?'}],
    'scheme': [{'type': 'ask_choice', 'text': 'Which layout: lower band, twin stripes, two-tone or colour block?'}, {'type': 'ask_colour', 'text': 'Which colours (or keep the set shown)?'}, {'type': 'confirm', 'text': 'Lay this scheme out on the car?'}],
}
BYID = {}

VOCAB = set()
for _it in ITEMS:
    VOCAB.update(norm(_it['n'] + ' ' + (_it.get('d') or '')).split(' '))
for _c in CARDS.values():
    VOCAB.update(norm(' '.join(_c[2] or []) + ' ' + ' '.join(_c[1] or [])).split(' '))

def variants(a, plural=True):
    a = norm(a)
    out = [a]
    if 'color' in a: out.append(a.replace('color', 'colour'))
    if 'colour' in a: out.append(a.replace('colour', 'color'))
    if 'grey' in a: out.append(a.replace('grey', 'gray'))
    if 'gray' in a: out.append(a.replace('gray', 'grey'))
    if plural:
        w = a.split(' ')
        if len(w) <= 3 and len(w[-1]) >= 4 and w[-1].isalpha() and not w[-1].endswith('s'):
            last = w[-1]
            if last.endswith('y') and last[-2] not in 'aeiou': pl = last[:-1] + 'ies'
            elif re.search(r'(ch|sh|x|z)$', last): pl = last + 'es'
            else: pl = last + 's'
            if pl in VOCAB: out.append(' '.join(w[:-1] + [pl]))
    return out

def register(term, aliases, plural=True):
    """first term to claim an alias wins; losers are logged. Returns the aliases the term actually owns."""
    mine = []
    for a in aliases:
        for v in variants(a, plural):
            if len(v) < 2 or not re.search(r'[a-z0-9]', v): continue
            if v in INDEX and INDEX[v] != term['id']:
                CONFLICTS.append((v, INDEX[v], term['id']))
                continue
            if v not in INDEX:
                INDEX[v] = term['id']; mine.append(v)
    seen = set(term.get('aliases', []))
    term.setdefault('aliases', [])
    for v in mine:
        if v not in seen: term['aliases'].append(v); seen.add(v)
    return mine

def add_term(t, aliases, plural=True):
    if t['id'] in BYID: raise SystemExit('duplicate term id ' + t['id'])
    t['aliases'] = []
    BYID[t['id']] = t
    register(t, aliases, plural)
    TERMS.append(t)
    return t

def finish_term(t, r):
    if r.get('det'): t['details'] = r['det'][:6]
    lk = [l for l in (link(x) for x in (r.get('links') or [])) if l]
    if lk: t['links'] = lk
    t['related'] = list(r.get('rel') or [])
    return t

def terms_split(s):
    return [x for x in (s or '').split('|') if x.strip()]

# ----- 1. parts (from the parser's PART_WORDS)
PART_EXTRA = {'spoiler': ['rear wing', 'rear spoiler', 'ducktail', 'wing spoiler'], 'hood': ['hood panel', 'engine hood'], 'trunk': ['boot', 'boot lid', 'trunk lid'], 'roof': ['roof panel', 'rooftop']}
for pw in P['PART_WORDS']:
    pid = pw['id']
    t = {'id': 'part:' + norm(pid).replace(' ', '_'), 'title': cap(pid), 'kind': 'flow', 'tier': 1, 'part': pid,
         'summary': 'The %s is a named part of your car. Tell me what to do with it: a colour, a finish or a stripe.' % pid,
         'flow': {'name': 'paint_part'},
         'details': ['I place changes on the named part, never on a grid box.', 'If I do not know your car\'s parts yet, use Teach me the car\'s parts.'],
         'links': [l for l in [link('help:teach_parts'), link('help:whats_on_car')] if l], 'related': ['colour', 'finish', 'part']}
    add_term(t, [pid] + pw['words'] + PART_EXTRA.get(pid, []))
# ----- 2. hand info
for r in R.INFO:
    t = {'id': r['id'], 'title': r['title'], 'kind': 'info', 'tier': 1, 'summary': r['sum']}
    finish_term(t, r); add_term(t, terms_split(r['al']))
# ----- 3. hand flows
def steps_of(lst):
    out = []
    for s in lst:
        ty, _, tx = s.partition('|'); out.append({'type': ty, 'text': tx})
    return out
for r in R.FLOW:
    t = {'id': r['id'], 'title': r['title'], 'kind': 'flow', 'tier': 1, 'summary': r['sum'], 'flow': {'name': r['id'], 'steps': steps_of(r['steps'])}}
    finish_term(t, r); add_term(t, terms_split(r['al']))
# ----- 4. hand looks (action; flow when it needs sub-choices)
for r in R.ACT:
    t = {'id': r['id'], 'title': r['title'], 'kind': r['kind'], 'tier': 1, 'summary': r['sum']}
    ch = choices_for(r)
    if ch: t['choices'] = ch
    if r['kind'] == 'flow': t['flow'] = {'name': r['id'], 'steps': steps_of(r['steps'] or [])}
    finish_term(t, r); add_term(t, terms_split(r['al']))
    # a metal / colour word that is also a named colour carries its hex
    for a in t['aliases']:
        if a in COLOURS: t['colour'] = {'hex': COLOURS[a]}; break

# ----- 5. the offline parser's own LOOKS table (fills the gaps the hand families left)
for lk in P['LOOKS']:
    lid = lk['id']
    t = {'id': 'look:' + lid.replace(' ', '_'), 'title': cap(lk['label']), 'kind': 'action', 'tier': 2,
         'summary': '%s: %s.' % (cap(lk['label']), lk['about'].rstrip('.'))}
    nm = '|'.join(re.escape(w).replace('\\ ', '.?') for w in sorted(set([lid] + lk['words']), key=len, reverse=True)[:6])
    ch = choices_for({'fin': [lk['found']] if lk.get('found') else [], 'name': nm, 'words': nm, 'n': 5})
    if ch: t['choices'] = ch
    t['related'] = ['finish', 'spec']
    t['details'] = ['Foundation finishes keep your paint colours and change only the shine.'] if (lk.get('found') or '').startswith('base::f_') else []
    if not t['details']: del t['details']
    add_term(t, lk['words'] + [lid])

# ----- 6. modifiers (darker / shinier / duller / pop ...) straight from the parser's regex tables
MOD = [('shade', 'Darker / lighter / bolder', 'SHADE', 'Shade words change how dark, bright or vivid a colour is. Tell me which part.', ['hue_sat_bright', 'colour']),
       ('shinier', 'Shinier / glossier', 'REL_UP', 'Make a part shinier: I move it toward gloss and wetter reflections.', ['spec', 'gloss_look']),
       ('duller', 'Duller / flatter', 'REL_DOWN', 'Make a part duller: I move it toward satin or matte.', ['spec', 'matte_look'])]
FIN_FOR = {'shinier': ['base::f_gel_coat', 'base::f_soft_gloss', 'base::f_chrome'], 'duller': ['base::f_soft_matte', 'base::f_clear_satin', 'base::f_powder_coat']}
for mid, title, key, summ, rel in MOD:
    words = P['words'].get(key, [])
    t = {'id': 'modifier:' + mid, 'title': title, 'kind': 'action', 'tier': 2, 'summary': summ, 'related': rel, 'adjust': {'op': mid}}
    ch = [choice_of(ITEM_BY_KEY[k]) for k in FIN_FOR.get(mid, []) if k in ITEM_BY_KEY]
    if ch: t['choices'] = ch
    add_term(t, words)

# ----- 7. colours (every colour name the offline parser / advisor knows). Core names get an entry each; the long tail (CSS / racing names) shares ONE entry with a name -> hex map
PLAIN_SET = set(norm(x) for x in P['PLAIN'])
CORE_COL = PLAIN_SET | set(norm(k) for k in (D.get('COLOURS') or {})) | set(norm(k) for k in (P.get('TINT') or {}))
LONG_TAIL = {}
for name in sorted(COLOURS):
    if name in INDEX: continue
    hexv = COLOURS[name]
    if name not in CORE_COL:
        LONG_TAIL[name] = hexv; continue
    core = name in PLAIN_SET
    t = {'id': 'colour:' + name.replace(' ', '_'), 'title': cap(name), 'kind': 'action', 'tier': 2,
         'summary': '%s is a colour I know. Say which part of the car to make %s, or start the colour flow.' % (cap(name), name) if core else '%s is a colour I know.' % cap(name),
         'colour': {'hex': hexv}, 'related': ['colour']}
    if core:
        ch = [choice_of(i) for i in rank(cn=r'(^|\s)%s$' % re.escape(name.split(' ')[-1]), own=1, n=4, types=('base', 'monolithic'))] if name in ('red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'black', 'white', 'grey', 'brown', 'teal', 'tan') else []
        if ch: t['choices'] = ch
    add_term(t, [name], plural=False)
if LONG_TAIL:
    t = {'id': 'colour:names', 'title': 'Colour names', 'kind': 'action', 'tier': 3, 'colours': LONG_TAIL,
         'summary': 'These are colour names I understand (CSS and racing colours). Say which part of the car to make that colour.', 'related': ['colour']}
    add_term(t, list(LONG_TAIL), plural=False)

# ----- 8. design elements + livery schemes
EL_TXT = {'lower_band': ('Lower band', 'lower band|bottom band|rocker band|rocker stripe|lower stripe', 'A colour band along the lower body of both sides, from the belt down to the rocker.'),
          'upper_band': ('Upper band', 'upper band|top band|roof band|roofline band', 'A colour band along the upper body of both sides, near the roof line.'),
          'belt_stripe': ('Belt stripe', 'belt stripe|beltline stripe|belt line|beltline|shoulder line|shoulder stripe', 'A stripe just under the roof line along both sides.'),
          'rear_quarter': ('Rear quarter', 'rear quarter|rear quarters|back quarter|sweep back|sweepback', 'The rear quarter of both sides in its own colour, like a sweep-back look.'),
          'front_fender': ('Front fender', 'front fender|front fenders|front wing|front guard', 'The front fender area of both sides in its own colour.'),
          'rings_graphic': ('Sonic rings', 'rings|sonic rings|arcs|concentric|concentric rings|target|bullseye|bullseye rings|circles|circle', 'Concentric arcs across the car, with optional dashes and a tail.'),
          'speed_lines_graphic': ('Speed lines', 'speed lines graphic|tapered lines|tapered strokes|manga speed lines|dash lines', 'Tapered lines streaming along the car, like motion.'),
          'waves_graphic': ('Wavy bands', 'wavy bands|wavy lines|wavy stripes|flow bands|flow lines|wave bands|waves graphic|squiggle|squiggles', 'Wavy flowing colour bands across the car.'),
          'chevrons_graphic': ('Chevrons', 'chevron graphic|v shapes|arrows|arrow|arrows pattern|arrowheads|v stripes', 'Repeating V or arrow shapes pointing along the car.'),
          'dots_graphic': ('Halftone dots', 'halftone dots|dot field|polka dots|polka dot|dotted|dot matrix|dotted pattern', 'A field of dots that grow and shrink, like a comic-book halftone.'),
          'rays_graphic': ('Sunburst rays', 'sunburst|sun burst|sunburst rays|rays burst|radial|radial rays|starburst|star burst', 'Rays fanning out from a point like a sunburst.'),
          'bumpers': ('Bumpers', 'bumper|bumpers|both bumpers|front and rear bumpers', 'The front and rear bumpers in their own colour.'),
          'lightning_graphic': ('Lightning bolt graphic', 'lightning graphic|bolt graphic|zap|zap graphic', 'A drawn lightning bolt across the car.')}
for key, (title, al, summ) in EL_TXT.items():
    if key not in (D.get('ELEMENTS') or {}): continue
    t = {'id': 'element:' + key, 'title': title, 'kind': 'flow', 'tier': 2, 'summary': summ,
         'flow': {'name': 'element'},
         'related': ['stripes', 'colour', 'part']}
    add_term(t, terms_split(al))
for key, pr in (D.get('PRESETS') or {}).items():
    ab = pr['about'].split(':')[-1].strip() if ':' in pr['about'][:20] else pr['about']
    s = re.split(r'(?<=[.!?])\s', pr['about'])[0]
    t = {'id': 'scheme:' + key, 'title': pr['name'], 'kind': 'flow', 'tier': 2, 'summary': s if len(s) < 200 else s[:197] + '...',
         'flow': {'name': 'scheme'}, 'related': ['schemes', 'stripes']}
    add_term(t, [pr['name'], key.replace('_', ' ')])
for pal in (D.get('PALETTES') or []):
    s = re.split(r'(?<=[.!?;])\s', pal['about'])[0].rstrip('.')
    t = {'id': 'palette:' + pal['id'], 'title': cap(pal['names'][0]) if pal['names'] else cap(pal['id']), 'kind': 'flow', 'tier': 2,
         'summary': cap(s) + '.', 'palette': {'base': pal.get('base'), 'a': pal.get('a'), 'b': pal.get('b')},
         'flow': {'name': 'scheme'}, 'related': ['schemes', 'colour']}
    add_term(t, list(pal['names']) + [pal['id'].replace('-', ' ')])

# ----- 9. catalogue shelves
for i, nm in enumerate(SECT):
    ttl = title_of(nm)
    if not ttl: continue
    blurb = (X['atlas']['blurbs'][i] or '').split('|')[0].strip()
    blurb = blurb.rstrip('.')
    summ = '%s is a shelf of the finish library: %s.' % (ttl, blurb[:150].rstrip(' ,;:('))
    t = {'id': 'shelf:' + norm(ttl).replace(' ', '_'), 'title': ttl, 'kind': 'action', 'tier': 2, 'summary': summ, 'related': ['finish']}
    ch = [choice_of(it) for it in rank(shelf=i, n=4, types=('base', 'monolithic', 'pattern'))]
    if ch: t['choices'] = ch
    nt = norm(ttl)
    add_term(t, [nt, nt + ' shelf', nt + ' finishes', nt + ' collection'])

# ----- 10. atlas tags the catalogue is organised by
TAG_SKIP = set('user-import development nonband fable story storybook hot-edge streaks-h streaks-v colorshoxx shokk-drop prism-forge paradigm fractured shokk era-50s era-60s era-70s era-80s era-90s dark light bright deep warm cold soft showcase texture modern clear'.split())
TAGC = collections.Counter(t for it in ITEMS for t in (it.get('t') or []))
for tag, cnt in sorted(TAGC.items()):
    if cnt < 10 or tag in TAG_SKIP: continue
    nt = norm(tag)
    if nt in INDEX: continue
    t = {'id': 'tag:' + nt.replace(' ', '_'), 'title': cap(nt), 'kind': 'action', 'tier': 2,
         'summary': '%s is one of the looks the catalogue is sorted by (%d finishes). Pick one to try it.' % (cap(nt), cnt), 'related': ['finish']}
    ch = [choice_of(it) for it in rank(tags=[tag], n=5)]
    if ch: t['choices'] = ch
    add_term(t, [nt])

# ----- 11. painter slang the advisor learned (spb-lexicon-ext.js)
LEX = X.get('lexExt') or {}
lex_items = [(k, v) for k, v in (LEX.get('words') or {}).items()] + [(k, v) for k, v in (LEX.get('phrases') or {}).items()]
for k, v in sorted(lex_items):
    nk = norm(k)
    if not nk or nk in INDEX: continue
    toks = [w for w in norm(v).split(' ') if w not in STOP and len(w) > 3]
    t = {'id': 'slang:' + nk.replace(' ', '_'), 'title': cap(nk), 'kind': 'action', 'tier': 3,
         'summary': '%s is painter talk. I look for finishes that read like: %s.' % (cap(nk), norm(v)), 'related': ['finish']}
    rx = '|'.join(re.escape(w) for w in toks[:5])
    ch = [choice_of(it) for it in rank(words=rx, name=rx, n=3)] if rx else []
    if ch: t['choices'] = ch
    add_term(t, [nk])

# ----- 12. buyer vocabulary of the finish cards (words painters type; tier 3)
DF = collections.Counter()
for k, c in CARDS.items():
    for w in set(norm(' '.join(c[2] or [])).split(' ')):
        if w.isalpha() and 4 <= len(w) <= 14: DF[w] += 1
cw = []
for w, n_ in DF.most_common():
    if n_ < 8 or n_ > 450: continue
    if w in STOP or w in INDEX or (w + 's') in INDEX or (w[:-1] in INDEX) or (w[:-2] in INDEX if w.endswith('es') else False): continue
    if w.endswith('ing') and w[:-3] in INDEX: continue
    cw.append((w, n_))
CARD_WORD_CAP = 45
for w, n_ in sorted(cw[:CARD_WORD_CAP], key=lambda x: x[0]):
    t = {'id': 'word:' + w, 'title': cap(w), 'kind': 'action', 'tier': 3, 'summary': '%s is a look word I know. These finishes read that way.' % cap(w), 'related': ['finish']}
    rx = r'\b%s' % re.escape(w)
    ch = [choice_of(it) for it in rank(words=rx, name=rx, n=3)]
    if ch: t['choices'] = ch
    add_term(t, [w], plural=False)

# ------------------------------------------------------------------------------------------------ absorb every parser word nobody owns yet (flagged == understood)
FALLBACK = {'NUMBERS_RE': 'number', 'SPONSORS_RE': 'sponsor', 'ACCENT_RE': 'stripes', 'BODY_RE': 'part', 'HOLO_RE': 'holographic', 'UNKNOWN_PART_RE': 'small_parts'}
TEXMAP = {'snake': 'snakeskin', 'croc': 'crocodile', 'dragon': 'dragon_scales', 'scales': 'fish_scales'}
absorbed = collections.Counter()
STEMS = []
def absorb(word, why):
    w = norm(word)
    if not w: return
    if w.endswith('#'):
        STEMS.append((w[:-1], why)); return
    if w in INDEX: return
    src, _, sub = why.partition(':')
    target = None
    if src == 'LOOKS': target = 'look:' + sub.replace(' ', '_')
    elif src == 'TEXTURES': target = TEXMAP.get(sub)
    elif src == 'PART_WORDS': target = 'part:' + norm(sub).replace(' ', '_')
    elif src == 'LAYERWORDS': target = {'rollbar': 'interior', 'cockpit': 'interior', 'pit box': 'interior', 'windows': 'windows', 'wheels': 'wheels'}.get(sub, 'interior')
    elif src in FALLBACK: target = FALLBACK[src]
    elif src == 'SHADE_RE': target = 'modifier:shade'
    elif src == 'REL_UP': target = 'modifier:shinier'
    elif src == 'REL_DOWN': target = 'modifier:duller'
    elif src == 'POP_RE': target = 'pop'
    elif src == 'WORD_TYPOS': target = None
    elif src in ('PLAIN', 'TINT', 'COLOURS', 'COLOUR_EXT'):
        target = 'colour:' + w.replace(' ', '_')
        if target not in BYID and w in COLOURS: BYID['colour:names'].setdefault('colours', {})[w] = COLOURS[w]; target = 'colour:names'
    t = BYID.get(target) if target else None
    if t is None and src == 'WORD_TYPOS':
        canon = norm(P['WORD_TYPOS'].get(w, ''))
        tid = INDEX.get(canon) or INDEX.get(canon + 's')
        t = BYID.get(tid) if tid else None
        if t is None and canon in COLOURS:
            t = BYID.get('colour:' + canon.replace(' ', '_'))
    if t is None:
        absorbed['UNMAPPED'] += 1; UNMAPPED.append((w, why)); return
    register(t, [w], plural=False); absorbed[src] += 1
UNMAPPED = []
for w, why in sorted((P.get('terms') or {}).items()):
    absorb(w, why)
# design words the offline designer curates (SpbProDesign.LOOK_CURATED keys) must resolve too
CUR = D.get('LOOK_CURATED') or {}
for w, z in sorted(CUR.items()):
    nw = norm(w)
    if nw in INDEX: continue
    z = z.get('zone') or {}
    fk = z.get('finish') if isinstance(z.get('finish'), str) else None
    pid = (z.get('pattern') or {}).get('id') if isinstance(z.get('pattern'), dict) else None
    tgt = None
    for t in TERMS:
        for c in t.get('choices') or []:
            if (fk and c.get('finish_id') == fk) or (pid and c.get('pattern_id') == pid): tgt = t; break
        if tgt: break
    if tgt: register(tgt, [nw], plural=False); absorbed['LOOK_CURATED'] += 1
    else: UNMAPPED.append((nw, 'LOOK_CURATED'))

# ------------------------------------------------------------------------------------------------ finalize: related, drop empty, validate
dropped = []
final = []
for t in TERMS:
    if not t['aliases']:
        dropped.append(t['id']); continue
    final.append(t)
ids = set(t['id'] for t in final)
bad_rel = []
for t in final:
    rel = []
    for r in t.get('related') or []:
        if r in ids and r != t['id']: rel.append(r)
        else: bad_rel.append((t['id'], r))
    t['related'] = [r for r in rel if not (r == 'finish' and t.get('tier') == 3)]
    if t.get('summary') and len(re.findall(r'[.!?](\s|$)', t['summary'])) > 2: t['_long'] = True
    # tidy key order for readability / stable output
    order = ['id', 'title', 'kind', 'tier', 'aliases', 'summary', 'details', 'choices', 'flow', 'colour', 'colours', 'palette', 'part', 'adjust', 'links', 'related']
    for k in list(t.keys()):
        if k not in order: order.append(k)
TERMS_OUT = []
for t in final:
    o = collections.OrderedDict()
    for k in ['id', 'title', 'kind', 'tier', 'aliases', 'summary', 'details', 'choices', 'flow', 'colour', 'colours', 'palette', 'part', 'adjust', 'links', 'related']:
        if k in t and t[k] not in (None, [], {}): o[k] = t[k]
    if t.get('tier') == 1 and 'tier' in o: pass
    TERMS_OUT.append(o)
# ---- hidden features (owner rule 2026-10-04, scripts/ai_atlas/enc_hidden_features.json): no term, alias, link or sentence may name Easy mode
import enc_hidden as H
def _hid_term(o):
    blob = ' '.join([str(o.get('title', '')), str(o.get('summary', '')), json.dumps(o.get('details', ''), ensure_ascii=False)])
    return o['id'].startswith('easy') or H.is_hidden_id(o['id']) or H.mentions(blob) or any(re.search(r'\beasy\b', a) for a in o.get('aliases', []) if a.startswith('easy'))
_gone = {o['id'] for o in TERMS_OUT if _hid_term(o)}
HIDDEN_TERMS = sorted(_gone)
TERMS_OUT = [o for o in TERMS_OUT if o['id'] not in _gone]
for _o in TERMS_OUT:
    _o['aliases'] = [a for a in _o['aliases'] if not H.mentions(a) and not re.search(r'\beasy\b', a)]
    for _k in ('summary', 'details', 'flow', 'choices', 'adjust', 'part'):
        if _k in _o:
            _o[_k] = H.scrub_obj(_o[_k], True, _k)
    for _k in ('related', 'links'):
        if _k in _o:
            _o[_k] = [x for x in _o[_k] if not (isinstance(x, str) and (x in _gone or re.search(r'easy', x, re.I))) and not (isinstance(x, dict) and re.search(r'easy', str(x.get('target', '')), re.I))]
# every alias of a dropped / kept term -> id (recomputed from the final terms so index == aliases exactly)
index = {}
for o in TERMS_OUT:
    for a in o['aliases']: index[a] = o['id']
phrases = sorted([a for a in index if ' ' in a], key=lambda a: (-len(a.split(' ')), -len(a), a))
max_words = max(len(a.split(' ')) for a in index)
weak = sorted(a for a in index if (' ' not in a and (a in WEAK_SINGLE or len(a) <= 2)) or a in ('make it', 'the car', 'my car', 'my truck', 'the paint', 'the base', 'the truck', 'all of it', 'everything', 'the whole thing', 'whole car', 'entire car', 'main color', 'main colour', 'base color', 'base colour', 'primary color', 'primary colour', 'how to', 'how do i', 'im stuck', 'no idea', 'what can you do', 'what can i ask', 'get started', 'check', 'detail', 'change', 'changing', 'changed', 'switch', 'swap', 'replace', 'turn the', 'tint the', 'subtle'))
for o in TERMS_OUT:
    if o.get('tier') == 1 and False: del o['tier']

meta = {
    'normalize': "lowercase; delete ' and the curly apostrophe; every other run of characters outside a-z 0-9 # becomes one space; trim. Apply to the buyer's text, then match.",
    'match': 'Walk the normalised words left to right. At each position try the multi-word aliases in `phrases` (already longest-first; at most `maxWords` words), then the single word in `index`. A match skips its words. Aliases in `weak` are common English words: underline them only with context.',
    'tiers': '1 = hand-written core entry, 2 = derived from catalogue / parser tables, 3 = vocabulary (card words, painter slang, long-tail colour names): show softly.',
    'kinds': 'info = explain + links; action = ask to apply a look with `choices` (real catalogue ids); flow = a guided flow (`flow.steps`, step types ask_target ask_colour ask_look ask_part ask_choice open_control tell confirm).',
    'choice': "finish_id = catalogue key (base:: / monolithic::), pattern_id = bare pattern id, spec_id = bare spec-pattern id; hex (only on items that TAKE the zone colour) = a sample colour for the thumbnail, no #. Thumbnail: '/api/swatch/{base|monolithic}/{id}?size=200&color={hex}', patterns '/api/swatch/pattern/{id}?size=200&color={hex}', specs '/api/spec-pattern-preview/{id}'.",
    'links': "target = support:<id> (SpbSupport FAQ/error id) | help:<id> (SpbSelfHelp topic id) | control:<id> (app control id, UI_DATA / app_controls.json) | doc:<file>#<heading start> (GETTING_STARTED.html).",
    'flows': 'a term whose flow has no steps uses top-level flows[flow.name].',
    'extra': 'colour = {hex}; colours = {name: hex} on the long-tail entry colour:names; palette = {base,a,b}; part = parser part id; adjust = {op}.',
    'atlas_v': X['atlas'].get('v'), 'cards_v': X['cardsMeta'].get('v'), 'generator': 'scripts/ai_atlas/build_encyclopedia.py',
}
# ------------------------------------------------------------------------------------------------ v2 article index (2026-10-04, lane C INDEX MERGE)
# Every Encyclopedia v2 article / generated page (data/encyclopedia/*.json + the part files under pages/), grouped by the file that holds it:
#   v2.groups[i] = {f: file path under data/encyclopedia/ (holds the FULL article), d: domain, k: 0 article (hand-written) | 1 page (script-made), r: rows}
#   row = [slug, title, summary?, aliases?]   -> article id = d + '.' + slug   (the id prefix IS the domain, a schema rule the gate enforces)
# v2.byAlias maps a normalised alias to [group, row]. v2 aliases are NOT merged into `index`/`phrases`: that would change which words the helper underlines.
# Size guard: V2_BUDGET bytes for the whole data file; if over, the summaries of script-made pages are dropped (the row keeps slug/title/aliases).
V2_DIR = os.path.join(ROOT, 'data', 'encyclopedia')
V2_BUDGET = 900 * 1024


def v2_build(with_page_summaries):
    groups, by_alias = [], {}

    def one_file(rel):
        try:
            doc = json.load(open(os.path.join(V2_DIR, rel), encoding='utf8'))
        except Exception:
            return
        if not isinstance(doc, dict):
            return
        slots = {}
        gi = {}
        for a in doc.get('articles') or []:
            if not isinstance(a, dict) or not a.get('id'):
                continue
            dom = a.get('domain') or ''
            gen = 1 if a.get('generated') else 0
            assert a['id'].startswith(dom + '.'), a['id']
            key = (dom, gen)
            if key not in slots:
                slots[key] = {'f': rel, 'd': dom, 'k': gen, 'r': []}
                groups.append(slots[key])
                gi[key] = len(groups) - 1
            g = slots[key]
            summ = a.get('summary') or ''
            if gen and not with_page_summaries:
                summ = ''
            row = [a['id'][len(dom) + 1:], a.get('title') or a['id']]
            als = [x for x in (a.get('aliases') or []) if x]
            keep_als = als if not (gen and not with_page_summaries) else []   # compact mode: a page's aliases live only in byAlias
            if summ or keep_als:
                row.append(summ)
            if keep_als:
                row.append(keep_als)
            g['r'].append(row)
            for x in als:
                by_alias.setdefault(x, [gi[key], len(g['r']) - 1])

    names = sorted(n for n in os.listdir(V2_DIR) if n.endswith('.json') and not n.startswith('_') and n not in ('manifest.json', 'graphics.json', 'figures.json'))
    for n in names:
        try:
            top = json.load(open(os.path.join(V2_DIR, n), encoding='utf8'))
        except Exception:
            continue
        if isinstance(top, dict) and top.get('parts'):
            for p in top['parts']:
                one_file(p['file'].replace(chr(92), '/'))
        else:
            one_file(n)
    return {'kinds': ['article', 'page'], 'cols': ['slug', 'title', 'summary', 'aliases'], 'groups': groups, 'count': sum(len(g['r']) for g in groups),
            'byAlias': collections.OrderedDict(sorted(by_alias.items()))}


# ENC_READER_FIX 2026-10-05: one idempotent post-pass over data/encyclopedia before indexing -- pictures must match the topic (no shelf car
# on another finish's page), control-page titles are the visible label (never a scanned fragment), every Do-it has a human label.
_fx = subprocess.run([sys.executable, os.path.join(HERE, 'enc_reader_fix.py'), '--write'], capture_output=True, text=True, cwd=ROOT)
print((_fx.stdout or _fx.stderr).strip().splitlines()[-1:] or ['enc_reader_fix: no output'])
# WEAR FIX 2026-10-05: Season mode is retired and there is no Wear slider; keep the Wear article + the 3 Season control pages honest on every build.
_wf = subprocess.run([sys.executable, os.path.join(HERE, 'enc_wear_fix.py'), '--write'], capture_output=True, text=True, cwd=ROOT)
print((_wf.stdout or _wf.stderr).strip().splitlines()[-1:] or ['enc_wear_fix: no output'])
# STALE-REFERENCES FIX 2026-10-05: Fleet batch pages (retired), hidden-picker finishes -> visible twins, Do-it ids -> visible twins (gate: enc_stale_refs_check.py).
_sf = subprocess.run([sys.executable, os.path.join(HERE, 'enc_stale_fix.py'), '--write'], capture_output=True, text=True, cwd=ROOT)
print((_sf.stdout or _sf.stderr).strip().splitlines()[-1:] or ['enc_stale_fix: no output'])
V2 = v2_build(True)
body = collections.OrderedDict([('version', ''), ('meta', meta), ('flows', SHARED_FLOWS), ('terms', TERMS_OUT), ('index', collections.OrderedDict(sorted(index.items()))), ('phrases', phrases), ('maxWords', max_words), ('weak', weak), ('v2', V2)])
meta['v2'] = 'v2 = every Encyclopedia v2 article / page. groups[i] = {f: file under data/encyclopedia/ holding the full article, d: domain, k: 0 hand-written article | 1 script-made page, r: rows}; row = [slug, title, summary?, aliases?]; article id = d + "." + slug. byAlias = alias -> [group, row]. Not part of `index`: v2 aliases never change what the helper underlines. Summaries of script-made pages are left out when the file would pass 900 KB (read them from the file in f).'
_probe = 'window.SPB_ENCYCLOPEDIA = ' + json.dumps(body, ensure_ascii=False, separators=(',', ':')) + ';\n'
if len(_probe.encode('utf8')) > V2_BUDGET:
    V2 = v2_build(False)
    body['v2'] = V2
h = hashlib.sha1(json.dumps([TERMS_OUT, index, V2['groups']], sort_keys=True).encode()).hexdigest()[:8]
body['version'] = '%s.%s' % (VERSION_DATE, h)
js = '/* GENERATED by scripts/ai_atlas/build_encyclopedia.py (do not edit). The offline helper\'s keyword encyclopedia: every word the helper understands, as info / action / flow entries. */\nwindow.SPB_ENCYCLOPEDIA = ' + json.dumps(body, ensure_ascii=False, separators=(',', ':')) + ';\n'
with open(OUT_JS, 'w', encoding='utf8', newline='\n') as f:
    f.write(js)

kinds = collections.Counter(o['kind'] for o in TERMS_OUT)
tiers = collections.Counter(o.get('tier') for o in TERMS_OUT)
stats = {'version': body['version'], 'bytes': len(js.encode('utf8')), 'terms': len(TERMS_OUT), 'kinds': kinds, 'tiers': tiers, 'aliases': len(index), 'phrases': len(phrases), 'weak': len(weak),
         'conflicts': len(CONFLICTS), 'dropped_terms': dropped, 'bad_related': bad_rel, 'absorbed': absorbed, 'unmapped': UNMAPPED[:80], 'extract': extract_line, 'long_summaries': [o['id'] for o in TERMS_OUT if len(re.findall(r'[.!?](\s|$)', o['summary'])) > 2],
         'stems_uncovered': [s for s, _ in STEMS if not any(a.startswith(s) for a in index)], 'choice_terms': sum(1 for o in TERMS_OUT if o.get('choices'))}
with open(os.path.join(WORK, 'build_stats.json'), 'w', encoding='utf8') as f:
    json.dump(stats, f, indent=1, default=lambda o: dict(o) if isinstance(o, collections.Counter) else str(o))
    f.write('\n')
with open(os.path.join(WORK, 'conflicts.txt'), 'w', encoding='utf8') as f:
    for a, w, l in CONFLICTS: f.write('%s\t%s\t(lost: %s)\n' % (a, w, l))
print('encyclopedia: %d terms %s tiers %s | %d aliases, %d phrases | %.0f KB | conflicts %d | dropped %d | unmapped %d | stems uncovered %s | v%s' % (
    len(TERMS_OUT), dict(kinds), dict(tiers), len(index), len(phrases), len(js.encode('utf8')) / 1024, len(CONFLICTS), len(dropped), len(UNMAPPED), stats['stems_uncovered'], body['version']))

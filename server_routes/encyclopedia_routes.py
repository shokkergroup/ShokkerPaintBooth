"""SPB Encyclopedia search for the ONLINE AI and the MCP bridge (ONLINE_GROUNDING 2026-10-04).

Owner rule: offline first, then MCP, then OpenRouter, and all three must AGREE. The offline helper
(js/spb-offline-answer.js) answers questions from the hand-written Encyclopedia articles with a BM25F
search; this module is a faithful Python port of that search (same documents, same words, same
field weights, same intent nudges) so the online model (js/spb-pro-ai.js grounding) and MCP
(spb_encyclopedia / spb_manual) get the SAME top article the offline helper would show.

GET /api/encyclopedia/search?q=<question>&k=<1-8, default 4>
  -> {ok, q, k, version, results: [{id, title, summary, faq: {q, a} | null, how: [...], controls: [...],
       sources: [...], link: "#enc:<id>", score, cov, confident}]}   (compact: about 1.5k tokens for k=4)

Hidden features (scripts/ai_atlas/enc_hidden_features.json, built-in defaults when the file is not shipped)
are never indexed and hidden sentences are scrubbed from every returned text.
Parity check: _easy_claude_work/eval/online_ground/enc_parity.js (node offline search vs this module).
"""
from __future__ import annotations

import json
import math
import os
import re
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENC_DIR = os.path.join(ROOT, 'data', 'encyclopedia')
DATA_JS = os.path.join(ROOT, 'js', 'spb-encyclopedia-data.js')
HIDDEN_JSON = os.path.join(ROOT, 'scripts', 'ai_atlas', 'enc_hidden_features.json')
FALLBACK_FILES = ['ai_copilot.json', 'cars.json', 'concepts.json', 'finishes.json', 'history.json', 'layers.json', 'patterns.json',
                  'playbook.json', 'preview_render.json', 'recipes.json', 'settings.json', 'shokk_drop.json', 'shortcuts.json', 'spec.json',
                  'spec_sculpt.json', 'support.json', 'tools.json', 'ui_shell.json', 'workflows.json', 'zones.json']

# ------------------------------------------------------------------ words (mirror of js/spb-offline-answer.js)
STOP = set(('a an the is are was were be been am do does did doing done i me my mine we our you your yours it its it s this that these those there here to of in on at for by from with and or but if so as '
            'what whats wat wht how hw why where wheres when which who whos whom can could would should will shall may might must im ive id dont doesnt didnt cant wont isnt arent wasnt '
            'about tell explain please pls plz just really very much many some any thing things one also too get got gets getting have has had having need want wanna gonna like know '
            'thanks thank hi hey hello ok okay yes no not nothing something anything difference differences between vs versus compared compare another').split())
STOP.discard('id')          # "user id" is a real word here
SYN = {'colour': 'color', 'colours': 'colors', 'coloured': 'colored', 'colouring': 'coloring', 'recolour': 'recolor', 'grey': 'gray', 'metalic': 'metallic', 'metalics': 'metallic',
       'aluminium': 'aluminum', 'licence': 'license', 'centre': 'center', 'favourite': 'favorite', 'fibre': 'fiber', 'liveries': 'livery', 'clearcoat': 'clearcoat', 'clear': 'clear',
       'photoshop': 'photoshop', 'psds': 'psd', 'tgas': 'tga', 'ui': 'interface', 'game': 'iracing', 'sim': 'iracing', 'ingame': 'iracing', 'iracings': 'iracing', 'id': 'id',
       'numbers': 'number', 'nums': 'number', 'num': 'number', 'sponsor': 'sponsor', 'decals': 'decal', 'logos': 'logo', 'chromed': 'chrome', 'shiny': 'shine', 'shinier': 'shine',
       'shininess': 'shine', 'glossy': 'gloss', 'glossier': 'gloss', 'flat': 'matte', 'mat': 'matte', 'mate': 'matte', 'speccing': 'spec', 'specs': 'spec'}
EXPAND = {'missing': ['vanished', 'disappear', 'gone', 'lost'], 'vanish': ['missing', 'disappear'], 'disappear': ['missing', 'vanished'], 'gone': ['missing', 'lost'],
          'big': ['size', 'large', '2048'], 'large': ['size', 'big'], 'size': ['big', '2048'], 'shine': ['gloss', 'shiny', 'spec'], 'gloss': ['shine', 'glossy'], 'matte': ['flat', 'gloss'],
          'save': ['saving', 'project'], 'open': ['load', 'opening'], 'load': ['open', 'loading'], 'broken': ['wrong', 'error'], 'slow': ['speed', 'performance'], 'crash': ['error', 'start'],
          'start': ['begin', 'first'], 'begin': ['start', 'first'], 'new': ['beginner', 'first', 'start'], 'picture': ['image', 'photo', 'logo'], 'photo': ['picture', 'image'],
          'stamped': ['sim', 'stamp'], 'stamp': ['stamped'], 'channel': ['channels'], 'sticker': ['decal', 'logo'], 'decal': ['logo', 'sponsor', 'sticker'], 'mirror': ['symmetry', 'flip'],
          'flip': ['mirror'], 'wrong': ['different', 'broken'], 'rgb': ['channel'], 'userid': ['user', 'id'], 'customer': ['user'], 'delete': ['remove'], 'remove': ['delete'],
          'erase': ['eraser', 'delete'], 'fade': ['gradient'], 'gradient': ['fade'], 'dark': ['flat', 'black']}
FW = {'t': 3.0, 'a': 2.4, 's': 1.2, 'q': 1.4, 'b': 0.35}          # title, aliases, summary, FAQ questions, body (what + how, first 90 words)
TITLE_PROB = re.compile(r"\b(slow|fails?|failed|won'?t|wont|not|missing|vanished|error|broken|problems?|trouble|wrong|stuck|crash\w*)\b", re.I)
Q_PROBLEM = re.compile(r"\b(doesn'?t|dont|don'?t|won'?t|wont|isn'?t|isnt|aren'?t|can'?t|cant|not (show|showing|work|working|load|loading|sav|open|opening|chang|changing|there|right|appear)\w*|missing|vanish\w*|disappear\w*|\blost\b|broken|stuck|slow|crash\w*|error|frozen|freez\w*|keeps|blank|black in|different in|look\w* different|wrong|blobby|smeared|tiny on|huge on|it says|got painted|nothing happen\w*|(?:does|do|did) nothing|not using|isnt using|isn'?t using|too (?:shiny|glossy|dull|matte|dark|bright|flat|big|small|blurry)|cant (?:find|see)|can'?t (?:find|see))\b", re.I)
FAQ_PROB = re.compile(r"\b(why|wont|won['’]t|doesnt|doesn['’]t|dont|don['’]t|cant|can['’]t|isnt|isn['’]t|not|fails?|failed|broken|stuck|greyed|grayed|wrong|missing|gone|error|too (much|many|little|dark|bright))\b", re.I)


def norm(s) -> str:
    s = str(s or '').lower()
    s = re.sub(r"['’]", '', s)
    s = re.sub(r'clear[\s-]+coat', 'clearcoat', s)
    s = re.sub(r'\bget rid of\b', 'remove', s)
    s = re.sub(r'\btrading paints?\b', 'tradingpaints', s)
    s = re.sub(r'\b(ctrl|control)\s*[-+ ]\s*r\b', 'reload', s)
    s = re.sub(r'\br (channel|value|slider)', r'metallic \1', s)
    s = re.sub(r'\bg (channel|value|slider)', r'roughness \1', s)
    s = re.sub(r'\bb (channel|value|slider)', r'clearcoat \1', s)
    return re.sub(r'[^a-z0-9#]+', ' ', s).strip()


def stem(w: str) -> str:
    if len(w) <= 3 or re.match(r'^[0-9#]', w):
        return w
    if w.endswith('ies') and len(w) > 4:
        return w[:-3] + 'y'
    if re.search(r'(ss|us|is)$', w):
        return w
    if re.search(r'(xes|ches|shes|sses)$', w):
        w = w[:-2]
    elif w.endswith('s'):
        w = w[:-1]
    if w.endswith('ing') and len(w) > 5:
        w = w[:-3]
        if re.search(r'([^aeioulsz])\1$', w):
            w = w[:-1]
    elif w.endswith('ed') and len(w) > 4:
        w = w[:-2]
        if re.search(r'([^aeioulsz])\1$', w):
            w = w[:-1]
    if re.search(r'[^aeiou]e$', w) and len(w) > 4:
        w = w[:-1]
    return w


def toks(s, keep_stop: bool = False) -> list:
    out = []
    for w in norm(s).split(' '):
        if not w:
            continue
        w = SYN.get(w) or w
        if not keep_stop and w in STOP:
            continue
        if len(w) < 2 and not re.search(r'[0-9]', w):
            continue
        out.append(stem(w))
    return out


# ------------------------------------------------------------------ hidden features (OWNER RULE: Easy mode is hidden)
_HID = {'domains': ['easy_mode'], 'prefixes': ['easy_mode.', 'controls_easy_mode_'],
        'ids': [re.compile(x) for x in (r'^easy\.', r'^mode\.easy$', r'^spbModeEasyBtn$', r'^hdi\.easy_', r'^hdi\.use_easy$', r'^topic\.easy_pro$', r'^sculpt\.btnEasyMode$')] + [re.compile(r'(^|[._:])easy([._:]|$)', re.I)],
        'text': [re.compile(r'\beasy[\s-]*mode\b', re.I), re.compile(r'\bEASY\b'), re.compile(r'\beasy\s+(vs|or|and)\s+pro\b', re.I),
                 re.compile(r'\bpro\s*[|/,]\s*(?:chat\s*[|/,]?\s*(?:and\s+)?)?easy\b', re.I), re.compile(r'\bpaint[\s-]*by[\s-]*numbers\b', re.I)]}


def _load_hidden() -> None:
    try:
        with open(HIDDEN_JSON, encoding='utf-8') as f:
            h = json.load(f)
    except Exception:
        return
    for d in (h.get('hidden_domains') or []) + (h.get('features') or []):
        if d not in _HID['domains']:
            _HID['domains'].append(d)
    for p in h.get('hidden_article_prefixes') or []:
        if p not in _HID['prefixes']:
            _HID['prefixes'].append(p)
    for x in h.get('hidden_record_ids') or []:
        try:
            _HID['ids'].append(re.compile(x))
        except re.error:
            pass
    for x in h.get('gate_text_patterns') or []:
        try:
            # JS lookbehind-free patterns; the curly apostrophe escape arrives decoded already
            _HID['text'].append(re.compile(x['re'], re.I if 'i' in (x.get('flags') or '') else 0))
        except Exception:
            pass


def hidden_id(i) -> bool:
    i = str(i or '')
    dom = i.split('.')[0]
    key = i[i.index('.') + 1:] if '.' in i[1:] else i
    if dom in _HID['domains']:
        return True
    for p in _HID['prefixes']:
        if i.startswith(p) or (dom + '.').startswith(p):
            return True
    return any(r.search(i) or r.search(key) for r in _HID['ids'])


def hidden_text(x) -> bool:
    x = str(x or '')
    return bool(x) and any(r.search(x) for r in _HID['text'])


def hidden(i, text='') -> bool:
    return hidden_id(i) or hidden_text(text)


def scrub(s) -> str:
    return ' '.join(x for x in re.split(r'(?<=[.!?])\s+', str(s or '')) if not hidden('', x))


# ------------------------------------------------------------------ index (built once, rebuilt when a source file changes)
_LOCK = threading.Lock()
_IX: dict = {'sig': None}


def _files() -> list:
    files = []
    try:
        with open(DATA_JS, encoding='utf-8') as f:
            s = f.read()
        d = json.loads(s[s.index('{'):s.rindex('}') + 1])
        for g in ((d.get('v2') or {}).get('groups') or []):
            if g.get('k') == 0 and g.get('f') not in files:
                files.append(g['f'])
    except Exception:
        files = []
    files = files or list(FALLBACK_FILES)
    try:
        with open(os.path.join(ENC_DIR, 'help_pages.json'), encoding='utf-8') as f:
            files += [p['file'] for p in (json.load(f).get('parts') or []) if p.get('file')]
    except Exception:
        pass
    return files


def _sig(files: list):
    out = []
    for p in [DATA_JS, SX_JS, os.path.join(ENC_DIR, 'help_pages.json'), os.path.join(ENC_DIR, OVERLAY)] + [os.path.join(ENC_DIR, f) for f in files]:   # SX_JS: a ranker edit rebuilds too
        try:
            st = os.stat(p)
            out.append((p, st.st_mtime_ns, st.st_size))
        except OSError:
            out.append((p, 0, 0))
    return tuple(out)


def _arts(x) -> list:
    if not x:
        return []
    return x if isinstance(x, list) else (x.get('articles') or [])


OVERLAY = '_alias_overlay.json'          # HELPER_V2 fix pass 4 2026-10-04: search aliases layered over the articles (same file the offline helper reads)


def _overlay() -> dict:
    try:
        with open(os.path.join(ENC_DIR, OVERLAY), encoding='utf-8') as f:
            return json.load(f).get('overlay') or {}
    except Exception:
        return {}


def _apply_overlay(a: dict, ov: dict) -> dict:
    x = ov.get(a.get('id')) if a else None
    if not x:
        return a
    drop = [str(w).lower() for w in (x.get('drop') or [])]
    al = [w for w in (a.get('aliases') or []) if str(w).lower() not in drop]
    for w in (x.get('add') or []):
        if str(w).lower() not in [str(y).lower() for y in al]:
            al.append(w)
    b = dict(a)
    b['aliases'] = al
    return b


def _build(files: list) -> dict:
    _load_hidden()
    docs, df, vocab = [], {}, {}
    ov = _overlay()
    for fn in files:
        try:
            with open(os.path.join(ENC_DIR, fn), encoding='utf-8') as f:
                arts = _arts(json.load(f))
        except Exception:
            continue
        for a in arts:
            a = _apply_overlay(a, ov) if isinstance(a, dict) else a
            if not a or not a.get('id') or hidden(a['id'], ' | '.join([str(a.get('title') or ''), ' | '.join(a.get('aliases') or [])])):
                continue
            how = [x for x in (a.get('how') or []) if isinstance(x, str)]
            fld = {'t': toks(a.get('title')), 'a': toks(' '.join(a.get('aliases') or [])), 's': toks(a.get('summary')),
                   'q': toks(' '.join(str(x.get('q') or '') for x in (a.get('faq') or []) if isinstance(x, dict))),
                   'b': toks(' '.join([str(a.get('what') or '')] + how))[:90]}
            tf, ln = {}, 0.0
            for k, wt in FW.items():
                for w in fld[k]:
                    tf[w] = tf.get(w, 0) + wt
                    ln += wt
            for w in tf:
                df[w] = df.get(w, 0) + 1
                vocab[w] = 1
            hlp = a['id'].startswith('help_')
            gen = bool(a.get('generated')) and not hlp
            docs.append({'id': a['id'], 'a': a, 'tf': tf, 'len': ln, 'prior': 1.0 if hlp else (0.8 if gen else 1.12), 'tn': ' '.join(toks(a.get('title'))),
                         'al': [y for y in (' '.join(toks(x)) for x in (a.get('aliases') or [])) if ' ' in y],
                         'faq': [{'q': x['q'], 'a': x.get('a') or '', 'k': toks(x['q'])} for x in (a.get('faq') or [])
                                 if isinstance(x, dict) and x.get('q') and not hidden('', str(x['q']) + ' ' + str(x.get('a') or ''))]})
    n = len(docs)
    avg = sum(d['len'] for d in docs) / max(1, n)
    idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
    dele = {}
    for w in vocab:          # typo tolerance: symmetric delete-1 neighbourhood ("yelow" / "chnage" / "clearcot")
        if len(w) < 4:
            continue
        for i in range(len(w)):
            k = w[:i] + w[i + 1:]
            if k not in dele or df[w] > df[dele[k]]:
                dele[k] = w
    exs = {}
    for k, v in EXPAND.items():
        sk = stem(SYN.get(k) or k)
        exs[sk] = exs.get(sk, []) + v
    try:          # ENC_SEARCH_LAB 2026-10-05: the shared ranker (js/spb-enc-search.js mirror) ranks; these docs keep feeding best_faq / compact
        sx = sx_build([d['a'] for d in docs])
    except Exception:
        sx = None
    return {'docs': docs, 'idf': idf, 'avg': avg, 'N': n, 'del': dele, 'exs': exs, 'maxIdf': math.log(1 + (n - 0.5) / 1.5), 'byId': {d['id']: d for d in docs}, 'sx': sx}


def _mt(p: str):
    try:
        return os.stat(p).st_mtime_ns
    except OSError:
        return 0


def index() -> dict:
    files = _files()
    sig = (_sig(files), _mt(SX_JS), _mt(SX_QB_JS))          # ROUND 3: the ranker's FIELDS and the paraphrase bank shape the index too
    with _LOCK:
        if _IX.get('sig') != sig:
            _IX.clear()
            _IX.update(_build(files))
            _IX['sig'] = sig
            _IX['files'] = len(files)
        return _IX


def _fix(ix: dict, w: str) -> str:
    if w in ix['idf'] or len(w) < 4 or re.search(r'[0-9]', w):
        return w
    if w in ix['del']:
        return ix['del'][w]
    for i in range(len(w)):
        k = w[:i] + w[i + 1:]
        if k in ix['idf']:
            return k
        if k in ix['del']:
            return ix['del'][k]
    return w


# ------------------------------------------------------------------ the SHARED ranker (ENC_SEARCH_LAB 2026-10-05)
# Line-for-line mirror of js/spb-enc-search.js (the ONE ranker the offline helper and the reader also use). The tunable constants
# (STOP, SYN, EXPAND, EXP_W, K1, FIELDS, KIND_PRIOR, P and the intent regexes) are READ FROM THAT JS FILE, so the two can never drift
# on numbers; the copies below are only the fallback when the JS file is not shipped. Parity (top-1 on the 1,226-question benchmark):
# _easy_claude_work/eval/online_ground/enc_parity.py.
SX_JS = os.path.join(ROOT, 'js', 'spb-enc-search.js')
SX = {'loaded': False}


def _js_obj(src: str, name: str, opener: str = '{', closer: str = '}'):
    """`var NAME = {...};` / `[...]` from the JS source -> Python value (JS literal -> JSON: comments, bare keys, single quotes)."""
    m = re.search(r'\bvar ' + name + r' = ' + re.escape(opener), src)
    if not m:
        raise ValueError(name)
    i, depth, j = m.end() - 1, 0, m.end() - 1
    while j < len(src):
        c = src[j]
        if c == "'":
            j = src.index("'", j + 1)
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                break
        j += 1
    lit = src[i:j + 1]
    lit = re.sub(r'//[^\n]*', '', lit)
    lit = re.sub(r"'([^']*)'", lambda mm: json.dumps(mm.group(1)), lit)
    lit = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', lit)
    lit = re.sub(r',(\s*[}\]])', r'\1', lit)
    return json.loads(lit)


def _js_re(src: str, name: str):
    m = re.search(r'\bvar [^;\n]*?\b' + name + r' = /(.+?)/([gimsuy]*)[,;]', src)
    if not m:
        raise ValueError(name)
    return re.compile(m.group(1), re.I if 'i' in m.group(2) else 0)


def _sx_load() -> None:
    try:
        mt = os.stat(SX_JS).st_mtime_ns
    except OSError:
        mt = 0
    if SX['loaded'] and SX.get('mt') == mt:          # re-read the constants when js/spb-enc-search.js changes (no server restart needed)
        return
    SX['mt'] = mt
    with open(SX_JS, encoding='utf-8') as f:
        src = f.read()
    m = re.search(r"var STOP = \{\};\s*\((.*?)\)\s*\.split", src, re.S)
    stop = set(''.join(re.findall(r"'([^']*)'", m.group(1))).split())
    stop.discard('id')
    SX.update({'STOP': stop, 'SYN': _js_obj(src, 'SYN'), 'EXPAND': _js_obj(src, 'EXPAND'), 'FIELDS': _js_obj(src, 'FIELDS', '[', ']'),
               'KIND_PRIOR': _js_obj(src, 'KIND_PRIOR'), 'DOM_PRIOR': _js_obj(src, 'DOM_PRIOR'), 'P': _js_obj(src, 'P'), 'LFW': _js_obj(src, 'LFW'), 'LPROB': _js_re(src, 'LPROB'),
               'EXP_W': float(re.search(r'var EXP_W = ([0-9.]+);', src).group(1)), 'K1': float(re.search(r'var K1 = ([0-9.]+);', src).group(1)),
               'RE_WHAT': _js_re(src, 'RE_WHAT'), 'RE_HOW': _js_re(src, 'RE_HOW'), 'RE_WHERE': _js_re(src, 'RE_WHERE'), 'RE_PROB': _js_re(src, 'RE_PROB'),
               'RE_TOOLW': _js_re(src, 'RE_TOOLW'), 'RE_LOOKW': _js_re(src, 'RE_LOOKW'), 'RE_TOOLCTX': _js_re(src, 'RE_TOOLCTX'), 'RE_BAREV': _js_re(src, 'RE_BAREV'),
               'RE_BAREF': _js_re(src, 'RE_BAREF'), 'RE_SIMCTX': _js_re(src, 'RE_SIMCTX'), 'RE_SIMSYM': _js_re(src, 'RE_SIMSYM'),
               'SIMSYM_ADD': re.search(r"var SIMSYM_ADD = '([^']*)';", src).group(1), 'REWRITE': _js_rewrite(src),
               'VERSION': re.search(r"var VERSION = '([^']+)'", src).group(1), 'loaded': True})


SX_HID_ID = re.compile(r'(^|[._:])easy([._:]|$)', re.I)
SX_HID_TX = re.compile(r'\beasy[\s-]*mode\b|\bpaint[\s-]*by[\s-]*numbers\b|\bEASY\b')


def sx_norm(s) -> str:
    s = str(s or '').lower()
    s = re.sub(r"['’]", '', s)
    s = re.sub(r'clear[\s-]+coat', 'clearcoat', s)
    s = re.sub(r'\bget rid of\b', 'remove', s)
    s = re.sub(r'\btrading ?paints?\b', 'tradingpaints', s)
    s = re.sub(r'\b(ctrl|control)\s*[-+ ]\s*r\b', 'reload', s)
    s = re.sub(r'\b(ctrl|control)\s*[-+ ]\s*z\b', 'undo', s)
    s = re.sub(r'\b(r|red) (channel|value|slider)', r'metallic \2', s)
    s = re.sub(r'\b(g|green) (channel|value|slider)', r'roughness \2', s)
    s = re.sub(r'\b(b|blue) (channel|value|slider)', r'clearcoat \2', s)
    s = re.sub(r'\b(a|alpha) (channel|value)', r'alpha \2', s)
    s = re.sub(r'(\d)\s*x\s*(\d)', r'\1 \2', s)
    s = re.sub(r'\buser ?id\b', 'user id', s)
    s = re.sub(r'\bspec ?map\b', 'spec map', s)
    return re.sub(r'[^a-z0-9#]+', ' ', s).strip()


def sx_stem(w: str) -> str:
    if len(w) <= 3 or re.match(r'^[0-9#]', w):
        return w
    if w.endswith('ies') and len(w) > 4:
        return w[:-3] + 'y'
    if re.search(r'(ss|us|is)$', w):
        return w
    if re.search(r'(xes|ches|shes|sses)$', w):
        w = w[:-2]
    elif w.endswith('s'):
        w = w[:-1]
    if w.endswith('ing') and len(w) > 5:
        w = w[:-3]
        if re.search(r'([^aeioulsz])\1$', w):
            w = w[:-1]
    elif w.endswith('ed') and len(w) > 4:
        w = w[:-2]
        if re.search(r'([^aeioulsz])\1$', w):
            w = w[:-1]
    if re.search(r'[^aeiou]e$', w) and len(w) > 4:
        w = w[:-1]
    return w


def sx_word(w: str) -> str:
    return sx_stem(SX['SYN'].get(w) or w)


def sx_toks(s) -> list:
    out = []
    for w in sx_norm(s).split(' '):
        if not w:
            continue
        w = SX['SYN'].get(w) or w
        if w in SX['STOP']:
            continue
        if len(w) < 2 and not re.search(r'[0-9]', w):
            continue
        out.append(sx_stem(w))
    return out


def _s(x) -> str:
    return '' if x is None else (x if isinstance(x, str) else (('true' if x else 'false') if isinstance(x, bool) else str(x)))


def _l(x) -> list:
    return x if isinstance(x, list) else []


def _text_of(L, f) -> str:
    o = []
    for x in _l(L):
        if isinstance(x, str):
            o.append(x)
        elif isinstance(x, dict):
            o.append(f(x))
    return ' '.join(o)


def _sx_hidden(d: dict) -> bool:
    return bool(SX_HID_ID.search(_s(d.get('id'))) or SX_HID_TX.search(_s(d.get('title'))) or SX_HID_TX.search(' | '.join(_s(x) for x in _l(d.get('aliases')))))


def _sx_kind(d: dict) -> dict:
    i, t = _s(d.get('id')), _s(d.get('title')).lower()
    k = d.get('kind') or ('help' if i.startswith('help_') else 'article')
    trouble = bool(i.startswith('support.') or (i.startswith('help_support_') and re.search(r'\b(not|no|failed|gone|wrong|problem|missing|busy|off|limit|too|differ|dark|black|drift|error)\b', t)) or
                   re.search(r'\b(not|wont|won t|doesnt|does not|do not|did not|will not|fails?|failed|slow|vanished|missing|wrong|broken|error|errors|trouble|problems?|stuck|blank|lost|gone|blobby|smeared|dark)\b', t) or re.match(r'why\b', t))
    howto = bool(re.match(r'help_howto_|help_topics_|recipes\.', i) or re.match(r'how (do|to|a)\b', t))
    what = bool(re.match(r'what\b', t) or i.startswith('concepts.') or re.search(r'\bexplained\b|\bwhat (it|each|is|a)\b', t))
    where = bool(re.search(r'\b(where|folder|files?|output|save|saving|projects?|panel|tab|box|menu|bar|button|buttons|settings|index)\b', t))
    return {'k': k, 'trouble': trouble, 'howto': howto, 'what': what, 'where': where}


def sx_intent(raw) -> dict:
    raw = str(raw or '').replace('’', "'")
    bv, bf = bool(SX['RE_BAREV'].search(raw)), bool(SX['RE_BAREF'].search(raw))          # ENC_READER_FIX: mirror of intentOf() (look / bare cues)
    return {'what': bool(SX['RE_WHAT'].search(raw)) and not bv, 'how': bool(SX['RE_HOW'].search(raw)) or bv, 'where': bool(SX['RE_WHERE'].search(raw)) or bf,
            'prob': bool(SX['RE_PROB'].search(raw)),
            'look': bool(SX['RE_TOOLW'].search(raw)) and bool(SX['RE_LOOKW'].search(raw)) and not SX['RE_TOOLCTX'].search(raw), 'bare': bv or bf}


def _js_rewrite(src: str) -> list:
    """ROUND 4 (ENC_SEARCH_LAB): the `var REWRITE = [...]` rows of js/spb-enc-search.js, one `[/regex/flags, 'replacement'],` per line ->
    [(compiled, python replacement)]. '$&' -> the whole match, '$n' -> group n (JS replace syntax -> re.sub syntax)."""
    m = re.search(r'var REWRITE = \[\n(.*?)\n\s*\];', src, re.S)
    if not m:
        return []
    rows = []
    for line in m.group(1).split('\n'):
        r = re.match(r"\s*\[/(.+)/([gimsuy]*), '([^']*)'\],?\s*$", line)
        if not r:
            continue
        rows.append((re.compile(r.group(1), re.I if 'i' in r.group(2) else 0),
                     re.sub(r'\$(\d)', r'\\g<\1>', r.group(3).replace('$&', '\\g<0>'))))
    return rows


def sx_rewrite(raw: str) -> str:
    """mirror of rewrite(): casual phrasing classes -> the words the articles use (rows read from the JS file)"""
    for rx, rp in SX.get('REWRITE') or []:
        raw = rx.sub(lambda mm: mm.expand(rp), raw)
    return re.sub(r'\s+', ' ', raw).strip()


def sx_cue(raw: str) -> str:
    """mirror of cue(): a colour symptom seen in the sim reads as 'colours look different in iRacing'"""
    if SX['RE_SIMSYM'].search(raw) and SX['RE_SIMCTX'].search(raw) and not re.search(r'colou?rs? look different in iracing', raw, re.I):
        return raw + SX['SIMSYM_ADD']
    return raw


def _sx_tool_doc(d: dict) -> bool:
    return d['dom'] in ('tools', 'controls_tools')


SX_QB_JS = os.path.join(ROOT, 'js', 'spb-enc-qbank.js')
SXQ = {'mt': None, 'data': None, 'map': None, 'QB': None}


def _sx_qbank():
    """ROUND 3: the paraphrase bank (js/spb-enc-qbank.js, {v, bank: [[id, [questions]]]}); re-read when the file changes. None when absent."""
    try:
        mt = os.stat(SX_QB_JS).st_mtime_ns
    except OSError:
        return None
    if SXQ['mt'] != mt:
        try:
            with open(SX_QB_JS, encoding='utf-8') as f:
                src = f.read()
            i, j = src.index('{"v"'), src.rindex('\n);')
            d = json.loads(src[i:j])
        except (OSError, ValueError):
            d = None
        SXQ.update({'mt': mt, 'data': d, 'map': ({r[0]: r[1] for r in d['bank']} if d and d.get('bank') else None), 'QB': None})
    return SXQ['data'] if SXQ['data'] and SXQ['data'].get('bank') else None


def _sx_qbmap():
    return SXQ['map'] if _sx_qbank() else None


def _sx_qtoks(s, ix) -> list:
    """Mirror of qtoks(): bank words keep the little (stop) words; synonyms + stems; the asked question's other words get typo repair."""
    out = []
    for w in sx_norm(s).split(' '):
        if not w:
            continue
        x = SX['SYN'].get(w) or w
        if x in SX['STOP']:
            out.append(x)
            continue
        c = '' if (len(x) < 2 and not re.search(r'[0-9]', x)) else sx_stem(x)
        if c:
            out.append(sx_fix(ix, c) if ix else c)
    return out


def _sx_qfeat(words: list):
    f, c, s = [], {}, ' ' + ' '.join([w for w in words if w not in SX['STOP']] if SX['P'].get('qcs') else words) + ' '
    def add(k):
        if k not in c:
            c[k] = 0
            f.append(k)
        c[k] += 1
    for w in words:
        add('w' + w)
    for j in range(len(words) - 1):
        add('b' + words[j] + ' ' + words[j + 1])
    for n in (3, 4):
        for k in range(len(s) - n + 1):
            add(str(n) + s[k:k + n])
    return f, c


def _sx_qvec(F, df, N, P):
    f, c = F
    v, ss = [], 0.0
    for k in f:
        d = df.get(k)
        if not d:
            continue
        g = k[0]
        gw = P['qww'] if g == 'w' else (P['qbw'] if g == 'b' else P['qcw'])
        w = gw * (1 + math.log(c[k])) * (math.log((N + 1) / (d + 1)) + 1)
        if w > 0:
            v.append([k, w])
            ss += w * w
    nr = math.sqrt(ss)
    if nr > 0:
        for e in v:
            e[1] = e[1] / nr
    return v


def _sx_qbbuild():
    D, P = _sx_qbank(), SX['P']
    if not D:
        return None
    key = '%r|%r|%r' % (P['qcw'], P['qww'], P['qbw'])
    if SXQ['QB'] and SXQ['QB']['key'] == key:
        return SXQ['QB']
    qa, fs, df, post = [], [], {}, {}
    for a, row in enumerate(D['bank']):
        for qq in (row[1] or []):
            t = _sx_qtoks(qq, None)
            if not t:
                continue
            F = _sx_qfeat(t)
            qa.append(a)
            fs.append(F)
            for k in F[0]:
                df[k] = df.get(k, 0) + 1
    N = len(fs)
    for qi in range(N):
        for k, w in _sx_qvec(fs[qi], df, N, P):
            post.setdefault(k, []).append((qi, w))
    SXQ['QB'] = {'key': key, 'ids': [r[0] for r in D['bank']], 'qa': qa, 'df': df, 'N': N, 'post': post}
    return SXQ['QB']


def _sx_qbhits(ix: dict, raw: str) -> list:
    Q, P = _sx_qbbuild(), SX['P']
    q = _sx_qtoks(raw, ix)
    if not Q or not q:
        return []
    qb = ix.get('qb')
    if not qb or qb['Q'] is not Q:
        by = {}
        for di, d in enumerate(ix['docs']):
            by[d['id']] = di
        qb = ix['qb'] = {'Q': Q, 'm': [by.get(i, -1) for i in Q['ids']]}
    v = _sx_qvec(_sx_qfeat(q), Q['df'], Q['N'], P)
    acc, ql = {}, []
    for k, w in v:
        for qi, w2 in Q['post'][k]:
            if qi not in acc:
                acc[qi] = 0.0
                ql.append(qi)
            acc[qi] += w * w2
    best, sec, al = {}, {}, []
    for qi in ql:
        di, s = qb['m'][Q['qa'][qi]], acc[qi]
        if di < 0 or s < P['qt']:
            continue
        if di not in best:
            best[di] = s
            sec[di] = 0
            al.append(di)
        elif s > best[di]:
            sec[di] = best[di]
            best[di] = s
        elif s > sec[di]:
            sec[di] = s
    out = [{'i': di, 's': best[di] + P['qk'] * sec[di]} for di in al]
    out.sort(key=lambda h: (-h['s'], h['i']))
    return out[:50]


def _sx_qbblend(ix: dict, out: list, raw: str, lock: int = -1) -> list:
    P = SX['P']
    hs = _sx_qbhits(ix, raw)
    if not hs:
        return out
    sim = {h['i']: h['s'] for h in hs}
    inm, sc, L = set(), [h['score'] for h in out], []
    for r, h in enumerate(out):
        sv = sim.get(h['i'])
        inm.add(h['i'])
        L.append({'h': h, 'r': r, 'k': 1 / (P['qf'] + r + 1) + (P['qw'] * math.pow(sv, P['qg']) if sv is not None else 0) + (1 if h['i'] == lock else 0)})
    for b, x in enumerate(hs):
        if x['i'] in inm:
            continue
        d = ix['docs'][x['i']]
        L.append({'h': {'id': d['id'], 'i': d['i'], 'score': 0, 'cov': 0, 'faq': -1, 'fs': 0}, 'r': len(out) + b, 'k': P['qw'] * math.pow(x['s'], P['qg'])})
    L.sort(key=lambda z: (-z['k'], z['r']))
    last = sc[-1] if sc else 0
    res = []
    for r1, z in enumerate(L):
        h, s1 = z['h'], sim.get(z['h']['i']) or 0
        h['score'] = P['qs'] * s1 if not sc else (sc[r1] if r1 < len(sc) else last)
        if r1 == 0 and s1 >= P['qc'] and h['cov'] < s1:
            h['cov'] = min(1, s1)
        res.append(h)
    return res


def sx_build(lst: list, prefix: bool = False) -> dict:
    _sx_load()
    FIELDS = SX['FIELDS']
    docs, vocab, avg, cnt = [], [], {}, 0
    QM = _sx_qbmap()          # ROUND 3: paraphrase bank questions -> field 'p' + 'p' units
    upost = {}
    sw = {}          # ENC_READER_FIX: surface words (titles, aliases, FAQ questions, summaries) -> doc count, for sx_spell
    for a in _l(lst):
        if not isinstance(a, dict) or not a.get('id') or _sx_hidden(a):
            continue
        faq = _l(a.get('faq'))
        fl = {'t': sx_toks(a.get('title')), 'a': sx_toks(' . '.join(_s(x) for x in _l(a.get('aliases')))),
              'q': sx_toks(' . '.join((_s(x.get('q')) if isinstance(x, dict) and x.get('q') else '') for x in faq)), 's': sx_toks(a.get('summary')),
              'c': sx_toks(' . '.join((_s(x.get('label')) if isinstance(x, dict) else '') for x in _l(a.get('controls')))),
              'm': sx_toks(' . '.join((_s(x.get('symptom')) if isinstance(x, dict) else '') for x in _l(a.get('mistakes')))),
              'b': sx_toks(' '.join([_s(a.get('what')), _text_of(a.get('how'), lambda x: _s(x.get('text') or x.get('step'))), _text_of(a.get('when'), lambda x: ''),
                                     _text_of(a.get('tips'), lambda x: ''), _text_of(a.get('pitfalls'), lambda x: ''),
                                     ' '.join((_s(x.get('a')) if isinstance(x, dict) and x.get('a') else '') for x in faq),
                                     ' '.join((_s(x.get('effect')) if isinstance(x, dict) else '') for x in _l(a.get('controls'))),
                                     ' '.join((_s(x.get('cause')) + ' ' + _s(x.get('fix')) if isinstance(x, dict) else '') for x in _l(a.get('mistakes'))),
                                     ' '.join((_s(x.get('heading')) + ' ' + _s(x.get('body')) if isinstance(x, dict) else '') for x in _l(a.get('deep')))])),
              'p': sx_toks(' . '.join(QM[a['id']]) if QM and a['id'] in QM else '')}
        units, tt = [], sx_toks(a.get('title'))
        if tt:
            units.append({'k': 't', 'w': tt})
            if _s(a['id']).startswith('help_') and re.search(r'\?\s*$', _s(a.get('title'))):
                units.append({'k': 'q', 'w': tt, 'j': -1})
        for x in _l(a.get('aliases')):
            w = sx_toks(x)
            if w:
                units.append({'k': 'a', 'w': w})
        for j, x in enumerate(faq):
            if isinstance(x, dict) and x.get('q') and not SX_HID_TX.search(_s(x.get('q')) + ' ' + _s(x.get('a'))):
                w = sx_toks(x['q'])
                if w:
                    units.append({'k': 'q', 'w': w, 'j': j})
        if QM and a['id'] in QM:
            for x in QM[a['id']]:
                w = sx_toks(x)
                if w:
                    units.append({'k': 'p', 'w': w})
        for U in units:
            uq, sn = [], set()
            for t in U['w']:
                if t not in sn:
                    sn.add(t)
                    uq.append(t)
            U['u'] = uq
            U['s'] = ' ' + ' '.join(U['w']) + ' '
        for ui, U in enumerate(units):          # word -> (doc, unit) pairs (mirror of the JS upost)
            for t in U['u']:
                upost.setdefault(t, []).append((len(docs), ui))
        aid = _s(a['id'])
        d = {'id': a['id'], 'i': len(docs), 'fl': fl, 'units': units, 'kind': _sx_kind(a), 'gen': bool(a.get('generated')) and not aid.startswith('help_'),
             'help': aid.startswith('help_'), 'dom': re.sub(r'_[0-9]+$', '', aid.split('.')[0]), 'ntitle': ' '.join(tt)}
        # plain channel (mirror of the JS: the old helper's one-bag BM25 + title / alias bonuses, fused by rank in sx_search)
        lf = {'t': tt, 'a': sx_toks(' '.join(_s(x) for x in _l(a.get('aliases')))), 's': fl['s'],
              'q': sx_toks(' '.join((_s(x.get('q')) if isinstance(x, dict) and x.get('q') else '') for x in faq)),
              'b': sx_toks(' '.join([_s(a.get('what')), _text_of(a.get('how'), lambda x: _s(x.get('text') or x.get('step')))]))[:90], 'p': fl['p']}
        lt, ll = {}, 0.0
        for lk, lw in SX['LFW'].items():
            for t in lf[lk]:
                lt[t] = lt.get(t, 0) + lw
                ll += lw
        d.update({'lt': lt, 'll': ll, 'lpr': 1.0 if d['help'] else (0.8 if d['gen'] else 1.12), 'tws': tt,
                  'lal': [x for x in (' '.join(sx_toks(y)) for y in _l(a.get('aliases'))) if x.find(' ') > 0],
                  'tq': bool(re.match(r'\s*(what|why)\b', _s(a.get('title')), re.I)), 'tp': bool(SX['LPROB'].search(_s(a.get('title'))))})
        _sx_surf(sw, ' '.join([_s(a.get('title')), ' '.join(_s(x) for x in _l(a.get('aliases'))),
                               ' '.join((_s(x.get('q')) if isinstance(x, dict) and x.get('q') else '') for x in faq), _s(a.get('summary'))]))
        docs.append(d)
        cnt += 1
        for f in FIELDS:
            avg[f[0]] = avg.get(f[0], 0) + len(fl[f[0]])
    for f in FIELDS:
        avg[f[0]] = max(1, (avg.get(f[0]) or 0) / max(1, cnt))
    post = {}
    for d in docs:
        tf, terms = {}, []
        for key, w, b in FIELDS:
            L = d['fl'][key]
            nrm = 1 - b + b * len(L) / avg[key]
            seen = {}
            for t in L:
                seen[t] = seen.get(t, 0) + 1
            for t in L:
                if seen[t] < 0:
                    continue
                if t not in tf:
                    tf[t] = 0
                    terms.append(t)
                tf[t] += w * seen[t] / nrm
                seen[t] = -1
        for t in terms:
            if t not in post:
                post[t] = []
                vocab.append(t)
            post[t].append([d['i'], tf[t]])
        d['fl'] = None
    n = len(docs)
    idf = {t: math.log(1 + (n - len(post[t]) + 0.5) / (len(post[t]) + 0.5)) for t in vocab}
    dele = {}

    def add_del(k, t):
        c = dele.get(k)
        if not c or len(post[t]) > len(post[c]) or (len(post[t]) == len(post[c]) and t < c):
            dele[k] = t
    for t in vocab:
        if len(t) < 4 or re.search(r'[0-9]', t):
            continue
        for i in range(len(t)):
            k = t[:i] + t[i + 1:]
            add_del(k, t)
            if len(t) >= 7:
                for j in range(i, len(k)):
                    add_del(k[:j] + k[j + 1:], t)
    for d in docs:
        for U in d['units']:
            m = 0
            for t in U['u']:
                v = idf.get(t)
                m += 0 if v is None else v
            U['m'] = m
    lpost, lsum = {}, 0.0
    for d in docs:
        lsum += d['ll']
        for t in d['lt']:
            lpost.setdefault(t, []).append(d['i'])
    lidf = {t: math.log(1 + (n - len(v) + 0.5) / (len(v) + 0.5)) for t, v in lpost.items()}
    return {'v': SX['VERSION'], 'docs': docs, 'post': post, 'idf': idf, 'del': dele, 'vocab': sorted(vocab), 'N': n,
            'maxIdf': math.log(1 + (n - 0.5) / 1.5), 'prefix': bool(prefix), 'lpost': lpost, 'lidf': lidf, 'lavg': lsum / max(1, n), 'upost': upost,
            'sw': sw, 'swl': sorted(sw), 'spc': {}}


def _sx_fuse(ix: dict, out: list, q: list, qs: list, alt: list, raw: str, it: dict) -> list:
    """Mirror of the JS fuse(): plain-channel score, then reciprocal-rank fusion; the main scores are handed out again in the new order."""
    P, KP, lidf = SX['P'], SX['KIND_PRIOR'], ix['lidf']
    lk1, lb, qn, mass = 1.2, 0.55, ' ' + ' '.join(q) + ' ', 0.0
    qset = set()
    for a, w in enumerate(qs):
        qset.add(w)
        qset.update(alt[a])
        iv = lidf.get(w)
        mass += ix['maxIdf'] if iv is None else iv
    q_how = bool(re.search(r'^\s*(how|hw|where)\b|^\s*(can|do) i\b', raw, re.I))
    cand, seen = [], set()
    for a, w in enumerate(qs):
        for t in [w] + alt[a]:
            for di in ix['lpost'].get(t, []):
                if di not in seen:
                    seen.add(di)
                    cand.append(di)
    ls = []
    for di in cand:
        d, s = ix['docs'][di], 0.0
        for w_i, w in enumerate(qs):
            f, idf, wt = d['lt'].get(w), lidf.get(w), 1.0
            if not f:
                for x in alt[w_i]:
                    if d['lt'].get(x):
                        f = d['lt'][x]
                        idf = max(idf or 0, lidf[x])
                        wt = 0.75
                        break
            if f:
                s += wt * idf * (f * (lk1 + 1)) / (f + lk1 * (1 - lb + lb * d['ll'] / ix['lavg']))
        if not s:
            continue
        if len(d['ntitle']) > 3 and (' ' + d['ntitle'] + ' ') in qn:
            s += 3
        for al in d['lal']:
            if (' ' + al + ' ') in qn:
                s += 2.5
                continue
            if all(x in qset for x in al.split(' ')):
                s += 1.5
        ov = sum(1 for w in qs if w in d['tws']) / len(qs)
        s += 2 * ov * ov
        if q_how and d['tq']:
            s *= 0.75
        if not it['prob'] and d['tp']:
            s *= 0.7
        if it['prob'] and (d['id'].startswith('support.') or d['id'].startswith('help_support')):
            s *= 1.15
        if it.get('look') and _sx_tool_doc(d):
            s *= P['il']
        ls.append((d['i'], s * d['lpr'] * (KP.get(d['kind']['k']) or 1)))
    ls.sort(key=lambda z: (-z[1], z[0]))
    rk = {di: r + 1 for r, (di, _) in enumerate(ls[:50])}
    F, FW = P.get('fk', 1), P.get('fw', 0)
    sc = [h['score'] for h in out]
    fused = [(1 / (F + r0 + 1) + (FW / (F + rk[h['i']]) if h['i'] in rk else 0), r0, h) for r0, h in enumerate(out)]
    fused.sort(key=lambda z: (-z[0], z[1]))
    res = []
    for r1, (_, _, h) in enumerate(fused):
        h['score'] = sc[r1]
        res.append(h)
    return res


def sx_fix(ix: dict, w: str) -> str:
    idf = ix['idf']
    if w in idf or len(w) < 4 or re.search(r'[0-9]', w):
        return w
    c = ix['del'].get(w)
    if c:
        return c
    for i in range(len(w)):
        k = w[:i] + w[i + 1:]
        if k in idf:
            return k
        c = ix['del'].get(k)
        if c:
            return c
    if len(w) >= 6:
        for i in range(len(w)):
            k1 = w[:i] + w[i + 1:]
            for j in range(i, len(k1)):
                k2 = k1[:j] + k1[j + 1:]
                if k2 in idf and len(k2) >= 4:
                    return k2
    return w


# ---- did you mean (ENC_READER_FIX 2026-10-05; mirror of spell() in js/spb-enc-search.js): raw-word typo repair against the surface words
def _sx_surf(sw: dict, text) -> None:
    seen = set()
    for w in re.split(r'[^a-z0-9]+', re.sub(r"['’]", '', str(text or '').lower())):
        if len(w) >= 3 and re.fullmatch(r'[a-z]+', w) and w not in SX['STOP'] and w not in seen:
            seen.add(w)
            sw[w] = sw.get(w, 0) + 1


def _sx_osa(a: str, b: str, mx: int) -> int:
    la, lb = len(a), len(b)
    if abs(la - lb) > mx:
        return mx + 1
    p2, p1 = [], list(range(lb + 1))
    for i in range(1, la + 1):
        c, lo = [i], i
        for j in range(1, lb + 1):
            v = min(p1[j] + 1, c[j - 1] + 1, p1[j - 1] + (0 if a[i - 1] == b[j - 1] else 1))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, p2[j - 2] + 1)
            c.append(v)
            if v < lo:
                lo = v
        if lo > mx:
            return mx + 1
        p2, p1 = p1, c
    return p1[lb]


def _sx_known(ix: dict, w: str) -> bool:
    if w in ix['sw'] or w in SX['STOP'] or w in SX['SYN']:
        return True
    t = sx_toks(w)
    return not t or (len(t) == 1 and t[0] in ix['idf'])


def _sx_nearest(ix: dict, w: str) -> str:
    if w in ix['spc']:
        return ix['spc'][w]
    mx = 2 if len(w) >= 7 else 1
    best, bd, bf = '', mx + 1, 0
    for c in ix['swl']:
        if abs(len(c) - len(w)) > mx or len(c) < 4:
            continue
        d = _sx_osa(w, c, min(mx, bd))
        if d > mx:
            continue
        f = ix['sw'][c]
        if d < bd or (d == bd and f > bf):
            best, bd, bf = c, d, f
    ix['spc'][w] = best
    return best


def _sx_starts_any(ix: dict, w: str) -> bool:
    import bisect
    L = ix['swl']
    i = bisect.bisect_left(L, w)
    return i < len(L) and L[i].startswith(w)


def sx_spell(ix: dict, text, prefix=None) -> dict:
    """{'text': repaired text, 'fixes': [[typed, meant], ...]} (mirror of SpbEncSearch.spell)."""
    raw, fixes = str(text or ''), []
    if not ix or 'sw' not in ix:
        return {'text': raw, 'fixes': fixes}
    parts = re.split(r"([^A-Za-z0-9'’]+)", raw)
    last = -1
    for k in range(len(parts) - 1, -1, -2):
        if parts[k]:
            last = k
            break
    for i in range(0, len(parts), 2):
        w = re.sub(r"['’]", '', parts[i].lower())
        if len(w) < 4 or not re.fullmatch(r'[a-z]+', w) or _sx_known(ix, w):
            continue
        if i == last and i == len(parts) - 1 and ix.get('prefix') and prefix is not False and _sx_starts_any(ix, w):
            continue
        c = _sx_nearest(ix, w)
        if c and c != w:
            fixes.append([parts[i], c])
            parts[i] = c
    return {'text': ''.join(parts) if fixes else raw, 'fixes': fixes}


def _sx_prefix_words(ix: dict, w: str) -> list:
    import bisect
    L, out = ix['vocab'], []
    i = bisect.bisect_left(L, w)
    while i < len(L) and len(out) < 6 and L[i].startswith(w):
        if L[i] != w:
            out.append(L[i])
        i += 1
    return out


def sx_search(ix: dict, text, limit: int = 6, prefix=None) -> list:
    """[{id, i, score, cov, faq}] best first (mirror of SpbEncSearch.search)."""
    if not ix or not ix['N']:
        return []
    P, KP, EXP_W, K1 = SX['P'], SX['KIND_PRIOR'], SX['EXP_W'], SX['K1']
    DP = SX.get('DOM_PRIOR') or {}
    idf = ix['idf']
    raw = sx_cue(sx_rewrite(sx_spell(ix, text, prefix)['text']))
    q = [sx_fix(ix, w) for w in sx_toks(raw)]
    cj = 0
    while cj + 1 < len(q):          # mirror of the JS: rejoin a typo'd 'trading panits' after typo repair
        if q[cj] == 'trad' and q[cj + 1] == 'paint':
            q[cj:cj + 2] = ['tradingpaint']
        cj += 1
    qs = []
    for w in q:
        if w not in qs:
            qs.append(w)
    if not qs:
        return []
    qn = ' ' + ' '.join(q) + ' '
    it = sx_intent(raw)
    alt, mass, qw = [], 0.0, []
    for a, w0 in enumerate(qs):
        ex = []
        for e in (SX['EXPAND'].get(w0) or []):
            x = sx_word(e)
            if x != w0 and x in idf and x not in ex:
                ex.append(x)
        if ix['prefix'] and prefix is not False and a == len(qs) - 1 and w0 not in idf and len(w0) >= 2:
            for p in _sx_prefix_words(ix, w0):
                if p not in ex:
                    ex.append(p)
        alt.append(ex)
        wi = idf.get(w0)
        qw.append(ix['maxIdf'] if wi is None else wi)
        mass += qw[a]
    acc, got, cand = {}, {}, []
    for b, w in enumerate(qs):
        hit = set()
        idw = idf.get(w)
        for di, tf in ix['post'].get(w, []):
            if di not in acc:
                acc[di] = 0.0
                got[di] = 0.0
                cand.append(di)
            acc[di] += idw * tf * (K1 + 1) / (tf + K1)
            got[di] += qw[b]
            hit.add(di)
        for x2 in alt[b]:
            idx2 = idf[x2]
            for d2, tf2 in ix['post'].get(x2, []):
                if d2 in hit:
                    continue
                hit.add(d2)
                if d2 not in acc:
                    acc[d2] = 0.0
                    got[d2] = 0.0
                    cand.append(d2)
                acc[d2] += EXP_W * min(idx2, qw[b]) * tf2 * (K1 + 1) / (tf2 + K1)
                got[d2] += EXP_W * qw[b]
    qmap = {}
    for c, w in enumerate(qs):
        qmap[w] = max(qmap.get(w, 0), qw[c])
        for y in alt[c]:
            qmap[y] = max(qmap.get(y, 0), EXP_W * qw[c])
    UH = {}          # doc -> {unit: shared question-word weight}, summed in question-word order (mirror of the JS)
    for tq, qv0 in qmap.items():
        LU = ix['upost'].get(tq)
        if not LU or not qv0:
            continue
        vq = min(qv0, idf[tq])
        for dd, uix in LU:
            H = UH.setdefault(dd, {})
            H[uix] = H.get(uix, 0) + vq
    bigr = [q[g] + ' ' + q[g + 1] for g in range(len(q) - 1) if q[g] != q[g + 1]]
    out, B2, qj = [], P['beta'] * P['beta'], ' '.join(q)
    for di in cand:
        d = ix['docs'][di]
        s = P['bm'] * acc[di]
        bt = ba = bq = bp = 0.0
        bj, ph, xu = -1, 0, 0
        Hd = UH.get(di) or {}
        for ui in sorted(Hd):
            U = d['units'][ui]
            hitw, um = Hd[ui], U['m']
            if not um or not hitw:
                continue
            r1, r2 = hitw / mass, hitw / um
            f1 = (1 + B2) * r1 * r2 / (B2 * r2 + r1)
            if r1 >= 0.999 and r2 >= 0.999:
                xu = max(xu, P.get('xq', 1) if U['k'] == 'q' else (P.get('xp', 1) if U['k'] == 'p' else 1))
            if U['k'] == 't':
                if f1 > bt:
                    bt = f1
            elif U['k'] == 'a':
                if f1 > ba:
                    ba = f1
            elif U['k'] == 'p':
                if f1 > bp:
                    bp = f1
                continue
            elif f1 > bq:
                bq, bj = f1, U['j']
            if bigr:
                for bg in bigr:
                    if (' ' + bg + ' ') in U['s']:
                        ph += 1
                        break
        s += P['ut'] * bt + P['ua'] * ba + P['uq'] * bq + P.get('up', 0) * bp + P['ph'] * min(2, ph) + P.get('xu', 0) * xu
        if ' ' in d['ntitle'] and d['ntitle'].index(' ') > 0 and (' ' + d['ntitle'] + ' ') in qn:
            s += P['whole']
        K = d['kind']
        m = KP.get(K['k']) or 1
        if d['help']:
            m *= P['gen']
        if d['dom'] in DP:
            m *= DP[d['dom']]
        if it['prob']:
            if K['trouble']:
                m *= P['iy']
        elif K['trouble']:
            m *= P['ip']
        if it['what'] and not it['how'] and not it['prob']:
            if K['what']:
                m *= P['iw']
            if K['howto']:
                m *= P['iq']
        elif it['how'] and not it['what']:
            if K['howto']:
                m *= P['ih']
            if K['what'] and not K['howto']:
                m *= P['iq']
        if it['where'] and K['where']:
            m *= P['iwh']
        if it.get('look') and _sx_tool_doc(d):
            m *= P['il']
        if d['ntitle'] and d['ntitle'] == qj:
            m = P['exact']
        cv = min(1, got[di] / mass) if mass else 0
        cg = P.get('cg', 0)
        out.append({'id': d['id'], 'i': d['i'], 'score': s * m * P.get('scale', 1) * (math.pow(cv, cg) if cg else 1), 'cov': cv, 'faq': bj, 'fs': bq})
    out.sort(key=lambda h: (-h['score'], h['i']))
    lock = out[0]['i'] if P.get('qlock', 0) > 0 and len(out) > 1 and out[0]['score'] >= P['qlock'] * out[1]['score'] else -1          # R4b
    if P.get('fw', 0) > 0 and len(out) > 1:
        out = _sx_fuse(ix, out, q, qs, alt, raw, it)
    if lock != -1 and out[0]['i'] != lock:
        lock = -1
    if P.get('qw', 0) > 0:          # ROUND 3: nearest question in the paraphrase bank
        out = _sx_qbblend(ix, out, raw, lock)
    return out[:limit or 6]


def search(text: str, limit: int = 6) -> list:
    """[{id, score, cov, doc}] best first; cov = share of the question's word weight the doc covers.
    ENC_SEARCH_LAB 2026-10-05: ranked by the shared ranker (sx_search, mirror of js/spb-enc-search.js); the old BM25F stays only as
    the fallback when the JS file with the ranker's constants is not shipped."""
    ix = index()
    sx = ix.get('sx')
    if sx is not None:
        return [{'id': h['id'], 'score': h['score'], 'cov': h['cov'], 'doc': ix['byId'][h['id']]} for h in sx_search(sx, text, limit or 6) if h['id'] in ix['byId']]
    return _legacy_search(text, limit)


def _legacy_search(text: str, limit: int = 6) -> list:
    """The pre-2026-10-05 BM25F (kept as a fallback only)."""
    ix = index()
    text = str(text or '')
    q = [_fix(ix, w) for w in toks(text)]
    qs = []
    for w in q:
        if w not in qs:
            qs.append(w)
    if not qs:
        return []
    idf = ix['idf']
    alt = {w: [y for y in (stem(x) for x in (ix['exs'].get(w) or EXPAND.get(w) or [])) if y in idf] for w in qs}
    qset = set(qs)
    for w in qs:
        qset.update(alt[w])
    qn = ' ' + ' '.join(q) + ' '
    mass = sum(idf.get(w, ix['maxIdf']) for w in qs)
    k1, b = 1.2, 0.55
    q_how = bool(re.match(r'^\s*(how|hw|where)\b|^\s*(can|do) i\b', text, re.I))
    q_prob = bool(Q_PROBLEM.search(text)) or bool(re.match(r'^\s*why\b', text, re.I))
    out = []
    for d in ix['docs']:
        s = got = 0.0
        for w in qs:
            f = d['tf'].get(w)
            wi = idf.get(w)
            wt = 1.0
            if not f:
                for x in alt[w]:
                    if d['tf'].get(x):
                        f = d['tf'][x]
                        wi = max(wi or 0, idf[x])
                        wt = 0.75
                        break
            if not f:
                continue
            s += wt * wi * (f * (k1 + 1)) / (f + k1 * (1 - b + b * d['len'] / ix['avg']))
            got += wt * (idf[w] if w in idf else wi)
        if not s:
            continue
        if d['tn'] and len(d['tn']) > 3 and (' ' + d['tn'] + ' ') in qn:
            s += 3
        for al in d['al']:
            if (' ' + al + ' ') in qn:
                s += 2.5
                continue
            if all(x in qset for x in al.split(' ')):
                s += 1.5
        tw = d['tn'].split(' ') if d['tn'] else []
        ov = len([w for w in qs if w in tw]) / len(qs)
        s += 2 * ov * ov
        at = str(d['a'].get('title') or '')
        if q_how and re.match(r'^\s*(what|why)\b', at, re.I):
            s *= 0.75
        if not q_prob and TITLE_PROB.search(at):
            s *= 0.7
        if q_prob and (d['id'].startswith('support.') or d['id'].startswith('help_support')):
            s *= 1.15
        out.append({'id': d['id'], 'score': s * d['prior'], 'cov': got / mass if mass else 0, 'doc': d})
    out.sort(key=lambda h: -h['score'])
    return out[:limit or 6]


def best_faq(ix: dict, d: dict, text: str):
    q = [_fix(ix, w) for w in toks(text)]
    yn = bool(re.match(r'^\s*(is|isnt|are|arent|does|doesnt|do|dont|can|cant|could|should|will|would|did|has|have|am|must)\b', re.sub(r"['’]", '', str(text or '')), re.I))
    best, bs = None, 0.0
    idf = ix['idf']
    for f in d['faq']:
        m = sum(idf.get(w, 0) for w in q)
        s = sum(idf.get(w, 0) for w in q if w in f['k'])
        r = s / m if m else 0
        m2 = sum(idf.get(w, 0) for w in f['k'])
        s2 = sum(idf.get(w, 0) for w in f['k'] if w in q)
        r2 = s2 / m2 if m2 else 0
        if re.match(r'^\s*(yes|no)\b', f['a'], re.I) and not yn:
            continue
        if FAQ_PROB.search(f['q']) and not FAQ_PROB.search(text):
            continue
        if re.match(r"^\s*(what|whats|what's)\b", str(text), re.I) and not re.match(r'^\s*(what|which)\b', f['q'], re.I):
            continue
        if r2 < 0.5:
            continue
        if r > bs:
            bs, best = r, f
    return best if bs >= 0.6 else None


def more_faq(ix: dict, d: dict, text: str, best, n: int = 2) -> list:
    """FAQ entries whose question is mostly inside what was asked (the helper's r2 >= 0.5 test) but that missed best_faq's 0.6 bar:
    extra facts for the MODEL only (the helper's card shows best_faq). Fixed 2026-10-04 eval: "the sliders in my zone panel are missing"
    never reached "Where did my sliders go?", "no shine at all in iRacing" never reached "What if there is no shine at all?"."""
    q = [_fix(ix, w) for w in toks(text)]
    idf = ix['idf']
    m = sum(idf.get(w, 0) for w in q) or 1
    out = []
    for f in d['faq']:
        if best is not None and f is best:
            continue
        m2 = sum(idf.get(w, 0) for w in f['k'])
        r2 = (sum(idf.get(w, 0) for w in f['k'] if w in q) / m2) if m2 else 0
        if r2 < 0.5 or (FAQ_PROB.search(f['q']) and not FAQ_PROB.search(text)):
            continue
        out.append((sum(idf.get(w, 0) for w in q if w in f['k']) / m, f))
    out.sort(key=lambda x: -x[0])
    return [f for r, f in out[:n] if r >= 0.25]


def _cut(s, n: int) -> str:
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'


def confident(h: dict) -> bool:
    """The offline helper's own 'question' bar (js/spb-offline-answer.js route: cov >= 0.34 and score >= 2.4)."""
    return bool(h) and h['cov'] >= 0.34 and h['score'] >= 2.4


def compact(h: dict, text: str) -> dict:
    ix = index()
    d, a = h['doc'], h['doc']['a']
    fq = best_faq(ix, d, text)
    hlp = a['id'].startswith('help_')
    how = [_cut(re.sub(r'^\d+\.\s*', '', x), 220) for x in (a.get('how') or []) if isinstance(x, str) and not hidden('', x)][:4 if hlp else 3]
    ctr = []
    for c in (a.get('controls') or [])[:4]:
        if not isinstance(c, dict) or hidden('', json.dumps(c)):
            continue
        ctr.append({k: _cut(c.get(k), 120) for k in ('label', 'range', 'default', 'effect') if c.get(k) not in (None, '')})
    more = [{'q': _cut(f['q'], 160), 'a': _cut(scrub(f['a']), 260)} for f in more_faq(ix, d, text, fq)] if confident(h) else []
    return {'id': a['id'], 'title': a.get('title') or a['id'], 'summary': _cut(scrub(a.get('summary')), 340),
            'faq': {'q': _cut(fq['q'], 160), 'a': _cut(scrub(fq['a']), 420)} if fq else None, 'more_faq': [x for x in more if x['a']],
            'how': how, 'controls': ctr, 'sources': [str(x) for x in (a.get('sources') or [])[:2]],
            'link': '#enc:' + a['id'], 'score': round(h['score'], 2), 'cov': round(h['cov'], 2), 'confident': confident(h)}


def lookup(text: str, k: int = 4) -> dict:
    k = max(1, min(8, int(k or 4)))
    ix = index()
    hits = search(text, k)
    return {'ok': True, 'q': str(text or '')[:300], 'k': k, 'articles': ix['N'], 'ranker': (SX.get('VERSION') if ix.get('sx') is not None else 'legacy'), 'results': [compact(h, text) for h in hits]}


def register_encyclopedia_routes(app, logger=None):
    from flask import jsonify, request

    @app.route('/api/encyclopedia/search', methods=['GET'])
    def encyclopedia_search():
        q = str(request.args.get('q') or '').strip()[:500]
        try:
            k = int(request.args.get('k') or 4)
        except ValueError:
            k = 4
        if not q:
            return jsonify({'ok': False, 'error': 'empty', 'message': 'pass ?q=<question>'}), 400
        try:
            return jsonify(lookup(q, k))
        except Exception as e:          # never take the chat down with the search
            if logger:
                try:
                    logger.warning('[encyclopedia] search failed: %s', e)
                except Exception:
                    pass
            return jsonify({'ok': False, 'error': 'search_failed', 'message': str(e)[:200]}), 500


if __name__ == '__main__':          # python server_routes/encyclopedia_routes.py "how do i export to trading paints" [k]
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    r = lookup(sys.argv[1] if len(sys.argv) > 1 else 'what does the roughness channel do', int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print('chars', len(json.dumps(r, ensure_ascii=False)))

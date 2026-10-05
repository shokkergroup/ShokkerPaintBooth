# -*- coding: utf-8 -*-
"""enc_inventory.py - KNOWLEDGE INVENTORY for the offline Encyclopedia v2 (2026-10-04).

One record per KNOWABLE THING in Shokker Paint Booth: {id, domain, kind, label, source:"file:line", topic, facts:{}}.
Everything is DERIVED (html scan, ui_map.json, app_controls.json, shipped JS data in a vm, engine docstrings, wiki markdown);
nothing is typed in from memory except the SEEDS table (concepts), and every seed must resolve a real file:line anchor.

Run:  python scripts/ai_atlas/enc_inventory.py            -> enc_inventory.json + enc_coverage.json + one verdict line
Reads only. Never edits existing files. No server, no port.
"""
import json, os, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / 'scripts' / 'ai_atlas'
WORK = ROOT / '_easy_claude_work' / 'enc'
WORK.mkdir(parents=True, exist_ok=True)

RECS, IDS = [], set()


def rd(p):
    return (ROOT / p).read_text(encoding='utf8', errors='replace')


def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', str(s).lower()).strip('_')[:60] or 'x'


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9#]+', ' ', re.sub(r"['’`]", '', str(s).lower()))).strip()


def add(id_, domain, kind, label, source, facts=None, topic=''):
    base, n = id_, 2
    while id_ in IDS:
        id_ = '%s~%d' % (base, n); n += 1
    IDS.add(id_)
    RECS.append({'id': id_, 'domain': domain, 'kind': kind, 'label': str(label).strip()[:140], 'source': source,
                 'topic': topic, 'facts': {k: v for k, v in (facts or {}).items() if v not in (None, '', [], {})}})
    return id_


# ---------------------------------------------------------------- line finders (cached file text)
_LINES = {}


def lines(p):
    if p not in _LINES:
        try:
            _LINES[p] = rd(p).split('\n')
        except Exception:
            _LINES[p] = []
    return _LINES[p]


def find_line(files, rx, flags=re.I):
    """first 'file:line' where regex rx matches, searching files in order; None if absent."""
    if isinstance(files, str):
        files = [files]
    r = re.compile(rx, flags)
    for f in files:
        for i, l in enumerate(lines(f), 1):
            if r.search(l):
                return '%s:%d' % (f, i)
    return None


# ---------------------------------------------------------------- function index (handler -> where defined)
FN_FILES = sorted([p.name for p in ROOT.glob('paint-booth-*.js')]) + ['js/spb-pro-zone-kit.js', 'js/spb-slider-fill.js']
_FN = None


def fn_index():
    global _FN
    if _FN is None:
        _FN = {}
        rx = re.compile(r'^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(|^\s*(?:window\.)?([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)')
        for f in FN_FILES:
            for i, l in enumerate(lines(f), 1):
                m = rx.match(l)
                if m:
                    n = m.group(1) or m.group(2)
                    _FN.setdefault(n, (f, i))
    return _FN


SKIP_FN = {'event', 'document', 'this', 'parseInt', 'parseFloat', 'Number', 'String', 'if', 'return', 'var', 'let', 'const', 'void',
           'stopPropagation', 'preventDefault', 'getElementById', 'querySelector', 'toggle', 'function', 'window', 'setTimeout', 'Math'}
SKIP_PROP = {'style', 'textContent', 'innerHTML', 'value', 'title', 'checked', 'disabled', 'className', 'display', 'innerText', 'src',
             'href', 'id', 'hidden', 'onclick', 'width', 'height', 'opacity', 'color', 'background', 'cursor', 'border'}


def handler_fn(code):
    for m in re.finditer(r'([A-Za-z_$][\w$.]*)\s*\(', code or ''):
        n = m.group(1).split('.')[-1]
        if n not in SKIP_FN and m.group(1).split('.')[0] not in ('document', 'event', 'this', 'window') or (m.group(1).startswith('window.') and n not in SKIP_FN):
            return n
    return None


def drives(code):
    n = handler_fn(code)
    if not n:
        return None
    d = fn_index().get(n)
    out = {'fn': n}
    if d:
        out['defined'] = '%s:%d' % d
        body = lines(d[0])[d[1] - 1:d[1] + 30]
        sets = []
        for l in body:
            for m in re.finditer(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*(?:=(?!=)|\+=|-=)', l):
                if m.group(2) not in SKIP_PROP and m.group(1) not in ('style', 'el', 'e', 'btn', 'node', 'window', 'document') and '%s.%s' % m.groups() not in sets:
                    sets.append('%s.%s' % m.groups())
        out['sets'] = sets[:6]
    return out


# ---------------------------------------------------------------- HTML scan
class Scan(HTMLParser):
    VOID = {'input', 'br', 'hr', 'img', 'meta', 'link', 'source', 'wbr', 'col'}

    def __init__(self, fname):
        super().__init__(convert_charrefs=True)
        self.f = fname; self.els = []; self.stack = []; self.labels = {}; self.last = ''
        self.skip = 0; self.open_btn = None; self.open_sel = None; self.open_lbl = None; self.open_head = None; self.open_dlg = []

    def _attr(self, a):
        return {k: (v if v is not None else '') for k, v in a}

    def handle_starttag(self, tag, attrs):
        a = self._attr(attrs); line = self.getpos()[0]
        if tag in ('script', 'style'):
            self.skip += 1
        anc = [x for x in (e.get('id') for e in self.stack) if x]
        e = {'tag': tag, 'a': a, 'line': line, 'anc': anc, 'text': ''}
        if tag in self.VOID:
            self._single(e)
            return
        self.stack.append(e)
        if tag == 'button':
            self.open_btn = e
        elif tag == 'select':
            e['opts'] = []; self.open_sel = e
        elif tag == 'option' and self.open_sel is not None:
            self.open_sel['opts'].append({'v': a.get('value', ''), 't': ''}); self._opt = self.open_sel['opts'][-1]
        elif tag == 'label':
            self.open_lbl = e
        elif tag in ('h1', 'h2', 'h3', 'h4', 'summary', 'legend'):
            self.open_head = e
        elif tag == 'textarea':
            self._single(e)
        if (a.get('role') == 'dialog' or re.search(r'(Modal|Dialog|Overlay)$', a.get('id', ''))) and a.get('id'):
            e['dlg'] = True; self.open_dlg.append(e)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def _single(self, e):
        e['text'] = self.last
        self.els.append(e)

    def handle_data(self, data):
        if self.skip:
            return
        t = data.strip()
        if t:
            self.last = t[:70]
        for k in ('open_btn', 'open_lbl', 'open_head'):
            o = getattr(self, k)
            if o is not None:
                o['text'] += ' ' + data
        if self.open_sel is not None and getattr(self, '_opt', None) is not None and self.stack and self.stack[-1]['tag'] == 'option':
            self._opt['t'] += data
        for d in self.open_dlg:
            if d is not None and 'ht' not in d and self.open_head is not None and self.open_head['text'].strip():
                d['ht'] = self.open_head['text']

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                e = self.stack[i]; del self.stack[i:]
                break
        else:
            return
        e['text'] = re.sub(r'\s+', ' ', e['text']).strip()
        if tag == 'button':
            self.open_btn = None; self.els.append(e)
        elif tag == 'select':
            self.open_sel = None; self._opt = None; e['text'] = self.last; self.els.append(e)
        elif tag == 'label':
            self.open_lbl = None
            if e['a'].get('for'):
                self.labels[e['a']['for']] = e['text']
        elif tag in ('h1', 'h2', 'h3', 'h4', 'summary', 'legend'):
            self.open_head = None
            if e['text'] and len(e['text']) < 90:
                self.els.append(e)
        if e.get('dlg'):
            self.open_dlg = [d for d in self.open_dlg if d is not e]; self.els.append(e)


def scan_html(fname):
    s = Scan(fname); s.feed(rd(fname)); return s


# ---------------------------------------------------------------- domain maps
PANEL_DOMAIN = {'pro.header': 'ui_shell', 'pro.modes': 'ui_shell', 'pro.settings': 'settings', 'pro.toolbar': 'tools', 'pro.zones': 'zones',
                'pro.zones_more': 'zones', 'pro.zone_editor': 'zones', 'pro.center': 'ui_shell', 'pro.tool_options': 'tools',
                'pro.selection_bar': 'tools', 'pro.placement': 'tools', 'pro.transform': 'tools', 'pro.eyedropper': 'tools',
                'pro.preview': 'preview_render', 'pro.render': 'preview_render', 'pro.right': 'layers', 'pro.layers': 'layers',
                'pro.finish_library': 'finishes', 'pro.finish_picker': 'finishes', 'pro.spec_tools': 'spec_sculpt', 'pro.dialogs': 'ui_shell',
                'pro.history': 'history', 'pro.shokk_library': 'shokk_drop', 'pro.ai': 'ai_copilot', 'easy': 'easy_mode',
                'easy.part_panel': 'easy_mode', 'chat': 'ai_copilot'}
GROUP_DOMAIN = {'colour': 'bases', 'base_material': 'bases', 'pattern': 'patterns', 'spec_pattern': 'spec', 'spec_direct': 'spec',
                'region': 'zones', 'order': 'zones', 'second_base': 'bases', 'paint_global': 'bases'}
ANC_DOMAIN = [('layerEffectsDialog', 'layers'), ('layerPanelContent', 'layers'), ('rightPanel', 'layers'), ('zoneDetailPanel', 'zones'),
              ('leftPanel', 'zones'), ('renderResultsPanel', 'preview_render'), ('shokkLibraryModal', 'shokk_drop'), ('saveShokkModal', 'shokk_drop'),
              ('specMapInspectorModal', 'spec_sculpt'), ('specLightingMaskOverlay', 'spec_sculpt'), ('specMaterialRemapOverlay', 'spec_sculpt'),
              ('finishBrowserOverlay', 'finishes'), ('finishCompareOverlay', 'finishes'), ('presetGalleryOverlay', 'finishes'),
              ('exportToPhotoshopModal', 'preview_render'), ('undoHistoryPanel', 'history'), ('shortcutOverlay', 'shortcuts'),
              ('centerPanel', 'ui_shell'), ('fineTuningPanel', 'spec')]
KIND_MAP = {'range': 'slider', 'number': 'number input', 'checkbox': 'toggle', 'radio': 'radio', 'text': 'text input', 'search': 'search box',
            'color': 'picker', 'file': 'file input', 'password': 'text input', 'email': 'text input', 'url': 'text input'}


def anc_domain(anc):
    for k, d in ANC_DOMAIN:
        if k in anc:
            return d
    return 'ui_shell'


def pick_label(e, labels):
    a = e['a']
    for c in (labels.get(a.get('id', '')), a.get('aria-label'), e['text'] if e['tag'] in ('button', 'select', 'summary', 'h1', 'h2', 'h3', 'h4', 'legend') else '', a.get('title'), a.get('placeholder'), e['text'], a.get('id')):
        if c and str(c).strip():
            return re.sub(r'\s+', ' ', str(c)).strip()[:110]
    return ''


def html_facts(e, labels):
    a = e['a']; t = e['tag']; f = {}
    if t == 'input':
        ty = a.get('type', 'text').lower(); f['input_type'] = ty
        for k in ('min', 'max', 'step', 'value', 'placeholder'):
            if k in a:
                f[k if k != 'value' else 'default'] = a[k]
        if 'checked' in a:
            f['default'] = 'on'
    if t == 'select':
        f['options'] = [(o['v'] or o['t'].strip()) + ('' if not o['v'] or o['v'] == o['t'].strip() else ' = ' + o['t'].strip()) for o in e.get('opts', [])][:40]
        f['default'] = next((o['v'] for o in e.get('opts', []) if False), None)
    if a.get('title'):
        f['tooltip'] = a['title'][:300]
    h = a.get('onclick') or a.get('oninput') or a.get('onchange')
    if h:
        f['handler'] = h[:140]
        dv = drives(h)
        if dv:
            f['drives'] = dv
    if a.get('data-tool'):
        f['data_tool'] = a['data-tool']
    return f


# ---------------------------------------------------------------- collectors
def collect_ui():
    u = json.load(open(AI / 'ui_map.json', encoding='utf8'))
    ac = json.load(open(AI / 'app_controls.json', encoding='utf8'))
    ctl = {c['id']: c for c in ac['controls']}
    s = scan_html('paint-booth-v2.html')
    by_id = {}
    for e in s.els:
        if e['a'].get('id') and e['tag'] in ('input', 'select', 'button', 'textarea', 'summary'):
            by_id.setdefault(e['a']['id'], e)
    by_lbl = {}
    for e in s.els:
        if e['tag'] == 'button' and e['text']:
            by_lbl.setdefault(norm(e['text']), e)
        if e['a'].get('title'):
            by_lbl.setdefault(norm(e['a']['title'])[:60], e)
    claimed = set()
    miss_js = 0
    for it in u['items']:
        dom = PANEL_DOMAIN.get(it.get('panel'), 'ui_shell')
        cid = it.get('control_id')
        c = ctl.get(cid) if cid else None
        f = {'mode': it.get('mode'), 'ui_kind': it.get('kind'), 'where': it.get('where'), 'does': it.get('does'), 'when': it.get('when'),
             'mistakes': it.get('mistakes'), 'needs': it.get('needs'), 'related': it.get('related'), 'curated': it.get('curated')}
        src = None; e = None
        if it.get('dom_id') and it['dom_id'] in by_id:
            e = by_id[it['dom_id']]
        elif it['source'] == 'html':
            e = by_lbl.get(norm(it['label'])) or by_lbl.get(norm(it['label'])[:60])
        if e is not None:
            claimed.add(id(e)); f.update(html_facts(e, s.labels)); src = 'paint-booth-v2.html:%d' % e['line']
        elif it['source'] == 'html':
            src = find_line('paint-booth-v2.html', re.escape(it['label'][:30]) if len(it['label']) > 3 else re.escape(it['id'])) or 'paint-booth-v2.html:1'
        else:  # js built
            fnm = it['source'].split(':', 1)[-1].strip()
            m = re.search(r'([A-Za-z_]\w+)', fnm)
            d = fn_index().get(m.group(1)) if m else None
            src = ('%s:%d' % d) if d else (find_line(JS_UI_FILES, re.escape(it['label'][:26])) or find_line(JS_UI_FILES, re.escape(it['id'].split('.')[-1].replace('_', ' ')[:20])) or find_line(JS_UI_FILES, re.escape("'" + it['id'].split('.')[-1] + "'")) or None)
            if not src:
                miss_js += 1; src = 'js:' + fnm
        if c:
            dom = GROUP_DOMAIN.get(c['group'], dom)
            f['control'] = {k: c.get(k) for k in ('zone_field', 'spec_key', 'payload_field', 'range', 'default', 'unit', 'applies_to', 'effect', 'interactions', 'planner_hint')}
            f['engine_evidence'] = c.get('evidence')
        elif it['id'].startswith('zone.'):
            lab = it['label'].lower()
            dom = 'spec' if 'spec' in lab else ('patterns' if 'pattern' in lab else dom)
        if e is not None and e['a'].get('id') and not c:
            ru = find_read(e['a']['id'])
            if ru:
                f['read_at'] = ru
        add(it['id'], dom, it.get('kind') or 'control', it['label'], src, f, it.get('panel', ''))
    # html elements nobody curated
    extra = 0
    for e in s.els:
        if id(e) in claimed:
            continue
        a = e['a']; t = e['tag']
        if t in ('h1', 'h2', 'h3', 'h4', 'legend'):
            continue
        if t == 'summary':
            kind = 'section'
        elif e.get('dlg'):
            kind = 'dialog'
        elif t == 'button':
            kind = 'button'
        elif t == 'input':
            kind = KIND_MAP.get(a.get('type', 'text').lower())
            if not kind:
                continue
        elif t == 'select':
            kind = 'dropdown'
        elif t == 'textarea':
            kind = 'text input'
        else:
            continue
        lab = e.get('ht') if e.get('dlg') else pick_label(e, s.labels)
        if not lab or (not a.get('id') and not e['text'] and not a.get('title')):
            continue
        if not a.get('id') and kind == 'button' and len(lab) < 2:
            continue
        if kind in ('dialog',) and not a.get('id'):
            continue
        dom = anc_domain(e['anc'])
        f = html_facts(e, s.labels); f['curated'] = False; f['area'] = ' > '.join(e['anc'][-2:])
        if a.get('id'):
            ru = find_read(a['id'])
            if ru:
                f['read_at'] = ru
        rid = a.get('id') or ('html.%s.%d' % (slug(lab), e['line']))
        add(rid, dom, kind, lab, 'paint-booth-v2.html:%d' % e['line'], f, 'html:' + (e['anc'][-1] if e['anc'] else 'root'))
        extra += 1
    # modes + how-do-i
    for m in u['modes']:
        add(m['id'], 'ui_shell' if m['id'] != 'mode.easy' else 'easy_mode', 'mode', m['label'], find_line('paint-booth-v2.html', r'id="mode' + slug(m['label']) ) or 'paint-booth-v2.html:1',
            {'where': m.get('where'), 'does': m.get('does'), 'when': m.get('when'), 'mistakes': m.get('mistakes')}, 'modes')
    for h in u['how_do_i']:
        add(h['id'], 'workflows', 'howto', h['title'], 'scripts/ai_atlas/ui_map.json:' + str(find_line('scripts/ai_atlas/ui_map.json', re.escape('"' + h['id'] + '"')) or '').split(':')[-1],
            {'mode': h.get('mode'), 'steps': h.get('steps'), 'ui': h.get('ui'), 'needs': h.get('needs')}, 'how_do_i')
    return {'ui_map_items': len(u['items']), 'extra_html': extra, 'unresolved_js': miss_js}


JS_UI_FILES = ['js/spb-easy-mode.js', 'js/spb-easy-tell.js', 'js/spb-easy-ai.js', 'js/spb-easy-auto.js', 'js/spb-easy-autoparts.js', 'js/spb-pro-ai.js', 'js/spb-chat-studio.js', 'js/spb-ai-core.js', 'js/spb-mcp-bridge.js', 'js/spb-focus-mode.js', 'js/spb-guided-mode.js', 'js/spb-pro-advisor.js', 'paint-booth-6-ui-boot.js', 'paint-booth-2-state-zones.js', 'paint-booth-3-canvas.js']
_READ = None


def find_read(dom_id):
    global _READ
    if _READ is None:
        _READ = {}
        rx = re.compile(r"getElementById\(\s*['\"]([\w-]+)['\"]\s*\)")
        for f in ('paint-booth-5-api-render.js', 'paint-booth-2-state-zones.js', 'paint-booth-3-canvas.js', 'paint-booth-6-ui-boot.js'):
            for i, l in enumerate(lines(f), 1):
                for m in rx.finditer(l):
                    if m.group(1) not in _READ:
                        key = None
                        km = re.search(r'([A-Za-z_]\w*)\s*[:=]\s*[^;,]*getElementById', l)
                        if km:
                            key = km.group(1)
                        _READ[m.group(1)] = '%s:%d' % (f, i) + (' (%s)' % key if key else '')
    return _READ.get(dom_id)


def collect_app_controls():
    ac = json.load(open(AI / 'app_controls.json', encoding='utf8'))
    have = {r['facts'].get('control', {}).get('zone_field') for r in RECS if r['facts'].get('control')}
    n = 0
    for c in ac['controls']:
        if c.get('zone_field') in have:
            continue
        add('ctl.' + c['id'], GROUP_DOMAIN.get(c['group'], 'zones'), 'zone_param', c['ui_label'][:100],
            'scripts/ai_atlas/app_controls.json:%s' % (find_line('scripts/ai_atlas/app_controls.json', re.escape('"id": "' + c['id'] + '"')) or ':1').split(':')[-1],
            {k: c.get(k) for k in ('zone_field', 'spec_key', 'payload_field', 'range', 'default', 'unit', 'applies_to', 'effect', 'interactions', 'where')} | {'evidence': c.get('evidence')}, 'ctl:' + c['group'])
        n += 1
    return n


def collect_other_html():
    n = 0
    for fn, dom, tag in (('spec-sculpt.html', 'spec_sculpt', 'sculpt'), ('shokk-drop.html', 'shokk_drop', 'drop')):
        if not (ROOT / fn).exists():
            continue
        s = scan_html(fn)
        for e in s.els:
            a = e['a']; t = e['tag']
            if t == 'button' or (t == 'input' and a.get('type', 'text') in KIND_MAP) or t == 'select':
                lab = pick_label(e, s.labels)
                if not lab or not (a.get('id') or e['text'] or a.get('title')):
                    continue
                kind = 'button' if t == 'button' else ('dropdown' if t == 'select' else KIND_MAP[a.get('type', 'text')])
                f = html_facts(e, s.labels); f['page'] = fn
                add('%s.%s' % (tag, a.get('id') or slug(lab) + '.%d' % e['line']), dom, kind, lab, '%s:%d' % (fn, e['line']), f, 'page:' + fn)
                n += 1
    return n


def collect_layer_buttons():
    rx = re.compile(r'<button[^>]*?(?:onclick="([^"]*)")?[^>]*?class="layer-act-btn"[^>]*?(?:title="([^"]*)")?[^>]*>([^<]{1,30})</button>')
    seen = set(); n = 0
    for i, l in enumerate(lines('paint-booth-3-canvas.js'), 1):
        if 'layer-act-btn' not in l:
            continue
        m = rx.search(l)
        if not m:
            continue
        lab = re.sub(r'\$\{[^}]*\}', '', m.group(3)).strip()
        if not lab or lab.lower() in seen:
            continue
        seen.add(lab.lower())
        t = re.search(r'title="\$\{[^}]*\|\|\s*\'([^\']+)\'', l) or re.search(r'title="([^"$]+)"', l)
        add('layer.btn.' + slug(lab), 'layers', 'button', lab, 'paint-booth-3-canvas.js:%d' % i,
            {'handler': (m.group(1) or '')[:100], 'tooltip': t.group(1) if t else None, 'where': 'LAYERS tab > layer card (one row of buttons per layer)',
             'drives': drives(m.group(1))}, 'layer_card')
        n += 1
    return n


def collect_shortcuts():
    s = rd('paint-booth-v2.html').split('\n')
    start = next((i for i, l in enumerate(s) if 'id="shortcutOverlay"' in l), None)
    if start is None:
        return 0
    n = 0; sec = ''
    for i in range(start, min(start + 140, len(s))):
        l = s[i]
        h = re.search(r'<h3[^>]*>([^<]+)</h3>', l)
        if h:
            sec = h.group(1).strip()
        m = re.findall(r'<kbd[^>]*>([^<]+)</kbd>', l)
        if m:
            txt = re.sub(r'<[^>]+>', '', l).strip()
            lab = re.sub(r'^(?:[^\s]+\s*/?\s*)+?', '', txt, count=0) if False else txt
            add('key.' + slug(' '.join(m)), 'shortcuts', 'shortcut', txt[:100], 'paint-booth-v2.html:%d' % (i + 1), {'keys': m, 'section': sec, 'text': txt}, 'shortcuts:' + slug(sec))
            n += 1
    return n


def collect_catalog():
    r = json.load(open(WORK / 'inv_js.json', encoding='utf8'))
    FD = 'paint-booth-0-finish-data.js'
    ci = {}
    src = rd('engine/paint_v2/surface_intent.py').split('\n')
    for i, l in enumerate(src[97:170], 98):
        m = re.match(r'\s+"([^"]+)":\s+(\w+),', l)
        if m:
            ci[m.group(1)] = (m.group(2), i)
    cats = r['finish_categories']
    n = lambda s: re.sub(r'[^a-z0-9]+', '', s.lower())
    cn = {n(k): k for k in cats}; cin = {n(k): k for k in ci}
    a = r['atlas']; grp_of = {}
    for g, names in a['groups'].items():
        for nm in names:
            grp_of[nm] = g
    used_c, used_i = set(), set()
    for i, nm in enumerate(a['sections']):
        key = n(re.sub(r'^[^\w]+', '', nm))
        f = {'count': a['sizes'][i], 'blurb': a['blurbs'][i], 'atlas_group': grp_of.get(nm)}
        ck = cn.get(key); ik = cin.get(key)
        if ck: f['category_desc'] = cats[ck]['desc']; f['tier'] = cats[ck]['tier']; used_c.add(ck)
        if ik: f['intent'] = ci[ik][0]; used_i.add(ik)
        add('shelf.' + slug(nm), 'finishes' if grp_of.get(nm) in ('base', 'special') else ('patterns' if grp_of.get(nm) == 'pattern' else 'spec'), 'finish_shelf', re.sub(r'^[^\w]+', '', nm),
            'js/spb-ai-atlas-data.js:2', f, 'shelf:' + str(grp_of.get(nm)))
    for k in cats:
        if k not in used_c:
            add('cat.' + slug(k), 'finishes', 'finish_category', k, (find_line('paint-booth-0-finish-metadata.js', r'^\s*"%s"\s*:' % re.escape(k)) or 'paint-booth-0-finish-metadata.js:19326'),
                {'count': cats[k]['count'], 'category_desc': cats[k]['desc'], 'tier': cats[k]['tier'], 'intent': ci.get(cin.get(n(k)), (None,))[0]}, 'category')
    for k, (v, ln) in ci.items():
        if k not in used_i and n(k) not in cn:
            add('intent.' + slug(k), 'finishes', 'intent_category', k, 'engine/paint_v2/surface_intent.py:%d' % ln, {'intent': v}, 'intent')
    for nm, key, dom in (('BASES', 'bases', 'bases'), ('MONOLITHICS', 'monolithics', 'finishes'), ('PATTERNS', 'patterns', 'patterns'), ('SPEC_PATTERNS', 'spec patterns', 'spec')):
        add('catalog.' + slug(nm), dom, 'catalog_count', '%s (%d entries)' % (key, r['counts'][nm]),
            find_line(FD, r'^const %s = \[' % nm) or FD + ':1', {'count': r['counts'][nm]}, 'catalog')
    add('catalog.finish_cards', 'finishes', 'catalog_count', 'finish cards (%d)' % r['cards']['n'], 'js/spb-ai-cards-data.js:2',
        {'count': r['cards']['n'], 'cards': 'js/spb-ai-cards-data.js (words, ratings, mood/era/use/fit); atlas js/spb-ai-atlas-data.js (4,799 finish rows)', 'moods': r['cards']['moods'], 'eras': r['cards']['eras'], 'uses': r['cards']['uses']}, 'catalog')
    for key, const, dom, kind in (('pattern_groups', 'PATTERN_GROUPS', 'patterns', 'pattern_group'), ('spec_pattern_groups', 'SPEC_PATTERN_GROUPS', 'spec', 'spec_pattern_group'), ('base_groups', 'BASE_GROUPS', 'bases', 'base_group')):
        start = int((find_line(FD, r'^const %s = \{' % const) or FD + ':1').split(':')[1])
        for g, cnt in (r[key] or {}).items():
            nm = re.sub(r'^[^\w]+', '', g)
            ln = None
            for i in range(start, start + 400):
                if i - 1 < len(lines(FD)) and ('"%s"' % g in lines(FD)[i - 1] or re.escape(nm[:12]) and nm[:14] in lines(FD)[i - 1]):
                    ln = i; break
            add('%s.%s' % (kind, slug(nm)), dom, kind, nm, '%s:%d' % (FD, ln or start), {'count': cnt, 'examples': (r[key.replace('_groups', '_sample')] if key.replace('_groups', '_sample') in r else {}).get(g)}, 'groups')
    for c in r['cars']:
        add('car.' + c['id'], 'cars', 'car', c['name'], 'js/spb-car-atlas-data.js:2', {'folders': c['folders']}, 'cars')
    return len(r['cars'])


def collect_support():
    n = 0
    L = lines('js/spb-support-answers.js')
    for i, l in enumerate(L, 1):
        m = re.match(r"\s*(F|E)\('(\w+)'", l)
        if not m:
            continue
        title = None
        for j in range(i - 1, min(i + 4, len(L))):
            t = re.search(r"'\*\*(.+?)\*\*", L[j]) or re.search(r"title.{0,3}'([^']+)'", L[j])
            if t:
                title = t.group(1); break
        add('support.' + m.group(2), 'support', 'faq' if m.group(1) == 'F' else 'error_answer', title or m.group(2).replace('_', ' '), 'js/spb-support-answers.js:%d' % i, {'support_id': m.group(2)}, 'support')
        n += 1
    L = lines('js/spb-self-help.js'); st = next((i for i, l in enumerate(L) if 'var TOPICS = [' in l), 0)
    for i in range(st, min(st + 160, len(L))):
        m = re.match(r"\s*\{ id: '(\w+)', kw: '([^']*)', title: '([^']+)'", L[i])
        if m:
            add('topic.' + m.group(1), 'workflows', 'topic', m.group(3), 'js/spb-self-help.js:%d' % (i + 1), {'keywords': m.group(2)[:120]}, 'self_help_topics')
            n += 1
    return n


def collect_mcp():
    n = 0; seen = set()
    for f in ('mcp/server/index.js', 'js/spb-pro-ai.js'):
        for i, l in enumerate(lines(f), 1):
            for m in re.finditer(r"name:\s*'(spb_[a-z_]+)'(?:,\s*description:\s*'([^']{0,160}))?", l):
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                add('mcp.' + m.group(1), 'ai_copilot', 'mcp_tool', m.group(1), '%s:%d' % (f, i), {'description': m.group(2)}, 'mcp')
                n += 1
    return n


def collect_docs():
    n = 0
    dm = {'01': 'zones', '02': 'spec', '03': 'workflows', '04': 'ui_shell', '05': 'finishes', '06': 'layers', '08': 'workflows', '09': 'workflows', '10': 'support', '11': 'finishes'}
    for p in sorted((ROOT / 'docs' / 'ai_knowledge').glob('*.md')):
        k = p.name[:2]
        if k not in dm:
            continue
        rel = 'docs/ai_knowledge/' + p.name
        for i, l in enumerate(lines(rel), 1):
            if re.match(r'^## ', l):
                add('doc.%s.%s' % (k, slug(l[3:])), dm[k], 'concept', l[3:].strip(), '%s:%d' % (rel, i), {'doc': p.name}, 'ai_knowledge:' + p.name[:2])
                n += 1
    # GETTING_STARTED headings
    gs = rd('GETTING_STARTED.html').split('\n')
    for i, l in enumerate(gs, 1):
        m = re.search(r'<h[23][^>]*>(.*?)</h[23]>', l)
        if m:
            t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if t:
                add('gs.' + slug(t), 'workflows', 'concept', t, 'GETTING_STARTED.html:%d' % i, {'doc': 'GETTING_STARTED.html'}, 'getting_started')
                n += 1
    return n


WIKI = {  # section -> (domain, [heading regexes to KEEP])
    'overview': ('ui_shell', [r'What it does for the user']),
    'start_here': ('spec', [r'What SPB actually is', r'Spec map channels']),
    'finish_doctrine': ('finishes', [r'GHOST SHIFT', r'North Star', r'Sacred Finish', r'2048 Car-Canvas', r'Paint / Spec Marriage', r'iRacing Spec-Map Truth', r'Color-Shift', r'Pattern / Base / Finish Quality']),
    'spec_guide': ('spec', [r'^RGB Spec Finish', r'coordinate system', r'literal combined-map', r'four channels', r'Fast navigator', r'Exact production paint cards', r'Advanced cards', r'Construction grammar', r'Mixing and gradients', r'Worked master recipe', r'Car integration guide', r'SPB controls that mutate', r'Export and preview truth', r'shorthand']),
    'spec_sculpt': ('spec_sculpt', [r'Why it matters', r'three modes', r'scratch presets', r'Paint response', r'Generation DNA', r'Iron rules', r'Diagnostics in the preview', r'Power features', r'flagship UX']),
    'smart_separate': ('zones', [r'shipped heuristic engine', r'The front-end']),
    'lessons': ('concepts', [r'Traps of', r'Design lessons']),
}


def collect_wiki():
    n = 0
    L = lines('SPB_WIKI.html'); cur = None
    for i, l in enumerate(L, 1):
        m = re.search(r'data-section="([^"]+)"', l)
        if m:
            cur = m.group(1)
        if cur in WIKI and re.match(r'^#{2,3} ', l):
            dom, keeps = WIKI[cur]
            t = re.sub(r'^#+\s*', '', l).strip()
            t = re.sub(r'<[^>]+>|&amp;', '', t)
            if any(re.search(k, t, re.I) for k in keeps):
                body = ' '.join(x.strip() for x in L[i:i + 6] if x.strip() and not x.startswith('#'))[:260]
                add('wiki.%s.%s' % (cur, slug(t)[:40]), dom if dom != 'concepts' else 'concepts', 'wiki_topic', t[:120], 'SPB_WIKI.html#%s:%d' % (cur, i), {'excerpt': body}, 'wiki:' + cur)
                n += 1
    return n


# ---------------------------------------------------------------- SEEDS: concepts that live only in code comments / answers
SEEDS = [
    # (id, domain, kind, label, [files], anchor regex, facts)
    ('spec.ch_r', 'spec', 'spec_channel', 'Spec channel R = Metallic', ['shokker_engine_v2.py'], r'R = Metallic', {'channel': 'R', 'range': '0 dielectric .. 255 mirror metal'}),
    ('spec.ch_g', 'spec', 'spec_channel', 'Spec channel G = Roughness', ['shokker_engine_v2.py'], r'G = Roughness', {'channel': 'G', 'range': '0 mirror smooth .. 255 matte'}),
    ('spec.ch_b', 'spec', 'spec_channel', 'Spec channel B = Clearcoat', ['shokker_engine_v2.py'], r'B = Clearcoat', {'channel': 'B', 'range': '0-15 none; 16 max gloss; 16-255 duller (inverted)'}),
    ('spec.ch_a', 'spec', 'spec_channel', 'Spec channel A = Spec mask', ['shokker_engine_v2.py'], r'A = Spec mask', {'channel': 'A', 'range': '255 active, 0 transparent'}),
    ('spec.iron1', 'spec', 'iron_rule', 'Iron rule 1: clearcoat 0 or >= 16', ['shokker_engine_v2.py'], r'CC must be >= 16', {'why': 'values 1-15 whitewash in iRacing GGX shader'}),
    ('spec.iron2', 'spec', 'iron_rule', 'Iron rule 2: roughness floor 15 unless mirror (M>=240)', ['shokker_engine_v2.py'], r'Roughness floor is 15', {}),
    ('spec.iron3', 'spec', 'iron_rule', 'Iron rule 3: alpha follows zone masks', ['shokker_engine_v2.py'], r'alpha \(spec mask\) channel', {}),
    ('spec.colorspace', 'spec', 'concept', 'Colour space: paint sRGB TGA, spec linear', ['shokker_engine_v2.py'], r'^COLOR SPACE', {}),
    ('spec.reference', 'spec', 'concept', 'Spec Map Channel Reference (iRacing PBR)', ['engine/SPEC_MAP_REFERENCE.md'], r'^# Spec Map', {}),
    ('spec.cc_floor', 'spec', 'concept', 'CC_FLOOR = 16 (clearcoat floor constant)', ['shokker_engine_v2.py'], r'^CC_FLOOR', {}),
    ('spec.file', 'preview_render', 'export_file', 'car_spec_<ID>.tga - the spec file', ['js/spb-support-answers.js'], r'car_spec_<ID>', {}),
    ('render.car_num', 'preview_render', 'export_file', 'car_num_<ID>.tga vs car_<ID>.tga (Custom Number vs Sim-Stamped)', ['server.py', 'js/spb-support-answers.js'], r'car_num_', {}),
    ('render.hide_numbers', 'preview_render', 'concept', 'Hide Car Numbers', ['js/spb-support-answers.js'], r'hide car numbers', {}),
    ('render.user_id', 'preview_render', 'concept', 'iRacing User ID (Customer ID)', ['js/spb-support-answers.js'], r"F\('customer_id'", {}),
    ('render.ctrl_r', 'preview_render', 'concept', 'Ctrl+R in iRacing reloads the paint', ['js/spb-support-answers.js'], r"F\('reload'", {}),
    ('render.livelink', 'preview_render', 'concept', 'Auto-deploy / live link', ['paint-booth-v2.html'], r'id="liveLinkHint"', {}),
    ('render.mip', 'preview_render', 'concept', 'iRacing compiles TGA into .mip (Trading Paints spec = .mip only)', ['server.py'], r'iRacing compiles paint', {}),
    ('render.tp', 'preview_render', 'concept', 'Trading Paints', ['js/spb-support-answers.js'], r'trading paints', {}),
    ('render.ps_export', 'preview_render', 'dialog', 'Export to Photoshop (layer ZIP)', ['paint-booth-v2.html'], r'id="exportToPhotoshopModal"', {}),
    ('render.stats', 'preview_render', 'dialog', 'Render stats overlay', ['paint-booth-v2.html'], r'id="renderStatsOverlay"', {}),
    ('render.size', 'preview_render', 'concept', 'Render canvas 2048x2048 over the whole car', ['engine/SPEC_MAP_REFERENCE.md', 'shokker_engine_v2.py', 'CLAUDE.md'], r'2048', {}),
    ('layers.turnoff', 'layers', 'concept', 'Turn Off Before Exporting TGA group', ['paint-booth-3-canvas.js', 'js/spb-support-answers.js', 'paint-booth-layer-flow.js'], r'Turn Off Before Exporting', {}),
    ('layers.paintable', 'layers', 'concept', 'Paintable Area group', ['js/spb-support-answers.js', 'paint-booth-layer-flow.js', 'paint-booth-3-canvas.js', 'docs/ai_knowledge/06_layers_panels_and_export.md', 'docs/ai_knowledge/10_support_troubleshooting.md', 'GETTING_STARTED.html'], r'Paintable', {}),
    ('layers.wire', 'layers', 'concept', 'Wire / Mask / Car Mandatory template layers', ['js/spb-support-answers.js', 'paint-booth-layer-flow.js', 'paint-booth-3-canvas.js'], r'(Car Mandatory|Wire\b)', {}),
    ('layers.roles', 'layers', 'concept', 'Layer roles (body paint / numbers / decals / tape)', ['js/spb-pro-edit.js', 'js/spb-support-answers.js'], r'(NUMBERS|layer role)', {}),
    ('zones.priority', 'zones', 'concept', 'Zone priority: lower index wins overlaps', ['js/spb-pro-zone-kit.js', 'paint-booth-2-state-zones.js', 'mcp/server/index.js'], r'(LOWER index|lower index)', {}),
    ('zones.everything', 'zones', 'concept', 'Everything Else (catch-all zone)', ['paint-booth-2-state-zones.js'], r'Everything Else', {}),
    ('zones.lock', 'zones', 'concept', 'Zone lock', ['paint-booth-2-state-zones.js'], r'lock-toggle', {}),
    ('zones.selectors', 'zones', 'concept', 'Zone selectors: colour / region / layer / part', ['paint-booth-2-state-zones.js'], r"c\.value === 'everything'", {}),
    ('zones.parts', 'zones', 'concept', 'Named car parts (left side, hood, roof ...)', ['js/spb-pro-carmap.js', 'js/spb-pro-edit.js'], r'(left side|PART_WORDS)', {}),
    ('spec.intent', 'spec', 'concept', 'Surface intent: spec_driven / pattern_design / pattern_image / full', ['engine/paint_v2/surface_intent.py'], r'^SPEC_DRIVEN', {}),
    ('spec.foundation_pure', 'bases', 'concept', 'Foundation bases: pure spec, keep source paint', ['engine/paint_v2/surface_intent.py'], r'"Foundation"', {}),
    ('spec.sculpt', 'spec_sculpt', 'concept', 'Spec Sculpt Lab', ['spec-sculpt.html'], r'<title>', {}),
]


def collect_seeds():
    ok = bad = 0
    for sid, dom, kind, lab, files, rx, facts in SEEDS:
        src = find_line(files, rx)
        if not src:
            bad += 1; src = 'UNRESOLVED:' + files[0]
        else:
            ok += 1
        add(sid, dom, kind, lab, src, facts, 'seed')
    return ok, bad


# ---------------------------------------------------------------- coverage vs encyclopedia
def load_enc():
    code = ("const vm=require('vm'),fs=require('fs');const c={console:{log(){}}};c.window=c;vm.createContext(c);"
            "vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);const E=c.SPB_ENCYCLOPEDIA;"
            "const t=E.terms;const arr=Array.isArray(t)?t:Object.keys(t).map(k=>Object.assign({id:k},t[k]));"
            "process.stdout.write(JSON.stringify({terms:arr.map(x=>({id:x.id,title:x.title,aliases:x.aliases||[],links:x.links||[],kind:x.kind,tier:x.tier,"
            "sum:(x.summary||'').length,det:(x.details||'').length,flow:!!(x.flow&&x.flow.steps)})),weak:E.weak||[]}))")
    out = subprocess.run(['node', '-e', code, str(ROOT / 'js' / 'spb-encyclopedia-data.js')], capture_output=True, text=True, encoding='utf8')
    return json.loads(out.stdout)


STOP = set('the a an of to for and or in on your my zone'.split())


def coverage():
    enc = load_enc(); weak = {norm(w) for w in enc['weak']}
    alias = {}
    for t in enc['terms']:
        for a in t['aliases'] + [t['title']]:
            alias.setdefault(norm(a), t['id'])
    links = set()
    for t in enc['terms']:
        for l in t['links']:
            links.add(l.get('target', '') if isinstance(l, dict) else str(l))
    tit = {t['id']: {w.rstrip('s') for w in norm(t['title'] + ' ' + t['id'].replace(':', ' ').replace('_', ' ')).split()} for t in enc['terms']}
    deep_ids = {t['id'] for t in enc['terms'] if t['det'] > 600}  # an "article" would need far more than a glossary sentence
    out = []; per = {}
    for r in RECS:
        if r.get('hidden'):
            continue   # hidden features (enc_hidden_features.json) are not part of the coverage count
        cands = [norm(r['label']), norm(re.sub(r'\([^)]*\)', '', r['label'])), norm(re.sub(r'^(mode|tool|zone)\.', '', r['id']).replace('_', ' ').replace('.', ' '))]
        if r['kind'] in ('shortcut',):
            cands += [norm(x) for x in r['facts'].get('keys', [])]
        hit = None; how = None; loose = None
        dom_id = r['id'].split('~')[0]
        tg = None
        if r['id'].startswith('support.'):
            tg = 'support:' + r['id'][8:]
        elif r['id'].startswith('topic.'):
            tg = 'help:' + r['id'][6:]
        elif r['kind'] not in ('concept', 'wiki_topic', 'howto', 'catalog_count', 'car'):
            tg = 'control:' + dom_id
        if tg and tg in links:
            hit, how = 'link:' + tg, 'link'
        ltok = {w.rstrip('s') for w in cands[0].split()}
        generous = r['domain'] in ('finishes', 'patterns', 'spec', 'bases', 'support', 'cars') and r['kind'] in ('finish_shelf', 'finish_category', 'pattern_group', 'spec_pattern_group', 'base_group', 'faq', 'error_answer', 'car')
        if not hit:
            for c in cands:
                if c and c in alias and c not in weak:
                    tid = alias[c]
                    if generous or ' ' in c and len(c) > 8 or (tit.get(tid, set()) & ltok):
                        hit, how = tid, 'alias'
                    else:
                        loose = tid
                    break
        if not hit and not loose:
            for a_, tid in alias.items():
                if a_ in weak or len(a_) < 4 or ' ' not in a_:
                    continue
                if (' ' + a_ + ' ') in (' ' + cands[0] + ' '):
                    loose = tid; break
        status = 'uncovered'
        if hit:
            status = 'covered_deep' if hit in deep_ids else 'covered_glossary'
        out.append({'id': r['id'], 'domain': r['domain'], 'kind': r['kind'], 'status': status, 'via': how, 'term': hit, 'loose_term': loose})
        p = per.setdefault(r['domain'], {'records': 0, 'covered_deep': 0, 'covered_glossary': 0, 'uncovered': 0, 'loose_only': 0})
        p['records'] += 1; p[status] += 1
        if status == 'uncovered' and loose:
            p['loose_only'] += 1
    tot = sum(1 for r in RECS if not r.get('hidden')); g = sum(p['covered_glossary'] for p in per.values()); d = sum(p['covered_deep'] for p in per.values())
    loose = sum(p['loose_only'] for p in per.values())
    res = {'terms': len(enc['terms']), 'records': tot, 'covered_deep': d, 'covered_glossary': g, 'uncovered': tot - g - d, 'loose_only': loose,
           'coverage_any_pct': round(100.0 * (g + d) / tot, 1), 'coverage_any_incl_loose_pct': round(100.0 * (g + d + loose) / tot, 1),
           'coverage_article_pct': round(100.0 * d / tot, 1), 'per_domain': per, 'records_detail': out}
    return res


def apply_hidden(recs):
    """Owner rule 2026-10-04 (scripts/ai_atlas/enc_hidden_features.json): records that ARE a hidden feature get hidden:true (kept in the file, excluded
    from coverage); every other record has the hidden feature's names / sentences scrubbed out of its label and facts. Idempotent."""
    sys.path.insert(0, str(AI))
    import enc_hidden as H
    n = 0
    for r in recs:
        if H.is_hidden_record(r):
            r['hidden'] = True; n += 1
            continue
        r.pop('hidden', None)
        lab = H.scrub(r.get('label', ''), True)
        if lab:
            r['label'] = lab
        for k in ('facts', 'topic'):
            if k in r:
                r[k] = H.scrub_obj(r[k], True, k)
    return n


def main():
    if '--apply-hidden' in sys.argv:    # no re-collect: load the existing file, apply the hidden-feature filter, rewrite it and the coverage
        inv = json.loads((AI / 'enc_inventory.json').read_text(encoding='utf8'))
        RECS[:] = inv['records']
        nh = apply_hidden(RECS)
        vis = [r for r in RECS if not r.get('hidden')]
        dom = {}
        for r in vis:
            dom[r['domain']] = dom.get(r['domain'], 0) + 1
        inv['meta']['records'] = len(vis); inv['meta']['hidden'] = nh; inv['meta']['by_domain'] = dict(sorted(dom.items(), key=lambda x: -x[1]))
        inv['meta']['by_kind'] = {k: sum(1 for r in vis if r['kind'] == k) for k in sorted({r['kind'] for r in vis})}
        inv['records'] = RECS
        (AI / 'enc_inventory.json').write_text(json.dumps(inv, ensure_ascii=False, indent=0), encoding='utf8')
        cov = coverage()
        (AI / 'enc_coverage.json').write_text(json.dumps(cov, ensure_ascii=False, indent=0), encoding='utf8')
        print('INVENTORY apply-hidden: %d records hidden, %d visible | coverage (a) any entry %.1f%%' % (nh, len(vis), cov['coverage_any_pct']))
        return
    subprocess.run(['node', str(AI / 'enc_inventory_js.js'), str(WORK / 'inv_js.json')], check=True, capture_output=True)
    stats = {}
    stats['ui'] = collect_ui(); stats['app_controls_extra'] = collect_app_controls(); stats['other_html'] = collect_other_html()
    stats['layer_buttons'] = collect_layer_buttons(); stats['shortcuts'] = collect_shortcuts(); stats['cars'] = collect_catalog()
    stats['support'] = collect_support(); stats['mcp'] = collect_mcp(); stats['docs'] = collect_docs(); stats['wiki'] = collect_wiki()
    stats['seeds_ok_bad'] = collect_seeds()
    nh = apply_hidden(RECS)
    dom = {}
    for r in RECS:
        if not r.get('hidden'):
            dom[r['domain']] = dom.get(r['domain'], 0) + 1
    unresolved = [r['id'] for r in RECS if not re.match(r'^[\w./#-]+:\d+$', r['source'])]
    inv = {'meta': {'built': '2026-10-04', 'records': len(RECS) - nh, 'hidden': nh, 'by_domain': dict(sorted(dom.items(), key=lambda x: -x[1])),
                    'by_kind': {k: sum(1 for r in RECS if r['kind'] == k and not r.get('hidden')) for k in sorted({r['kind'] for r in RECS})}, 'collector_stats': stats,
                    'sources_unresolved': unresolved[:40], 'n_sources_unresolved': len(unresolved)}, 'records': RECS}
    (AI / 'enc_inventory.json').write_text(json.dumps(inv, ensure_ascii=False, indent=0), encoding='utf8')
    cov = coverage()
    (AI / 'enc_coverage.json').write_text(json.dumps(cov, ensure_ascii=False, indent=0), encoding='utf8')
    parts = ['%s %d/%d/%d' % (d, p['records'], p['covered_glossary'] + p['covered_deep'], p['uncovered']) for d, p in sorted(cov['per_domain'].items(), key=lambda x: -x[1]['records'])]
    print('INVENTORY %d records | domains (records/glossary/uncovered): %s | coverage (a) any entry %.1f%% (incl loose mentions %.1f%%), (b) real article %.1f%% | unresolved sources %d'
          % (len(RECS), '; '.join(parts), cov['coverage_any_pct'], cov['coverage_any_incl_loose_pct'], cov['coverage_article_pct'], len(unresolved)))


if __name__ == '__main__':
    main()

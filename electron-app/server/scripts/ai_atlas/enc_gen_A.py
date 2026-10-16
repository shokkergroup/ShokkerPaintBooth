#!/usr/bin/env python3
"""Encyclopedia v2, lane A generator.

Writes two domain files from facts that already exist on disk (nothing is typed from memory):
  data/encyclopedia/controls.json   one page per control a buyer can touch (every slider, button, switch, box)
  data/encyclopedia/shortcuts.json  the 6 reference articles (key table, control index, glossary, colours, shelves, spec cheat sheet)

Sources of fact: scripts/ai_atlas/enc_inventory.json (label, range, default, tooltip, curated does/when/mistakes),
the three HTML pages (section heading, hint line, option list around each control), js/spb-encyclopedia-data.js
(glossary), the finish atlas and colour tables (read through scripts/ai_atlas/enc_extract.js), engine/SPEC_MAP_REFERENCE.md.

Re-run any time (idempotent, atomic write, small output). Run it AFTER the other lanes have written their files so the
related links can point at their articles (a link is only written when the target article exists).

  python scripts/ai_atlas/enc_gen_A.py            # both files
  python scripts/ai_atlas/enc_gen_A.py --only controls|shortcuts
"""
import argparse, collections, datetime, html, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ENC = os.path.join(ROOT, 'data', 'encyclopedia')
TODAY = datetime.date.today().isoformat()


def P(*a): return os.path.join(ROOT, *a)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc_reader_fix as RF          # ENC_READER_FIX 2026-10-05: readable control titles (shared with the post-pass)


def jload(p):
    with open(p, encoding='utf8') as fh: return json.load(fh)


def atomic_json(path, obj):
    t = path + '.tmp'
    with open(t, 'w', encoding='utf8') as fh: json.dump(obj, fh, ensure_ascii=False, separators=(',', ':'))
    os.replace(t, path)


def norm(s):
    s = re.sub(r"['’`]", '', str(s).lower())
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9#]+', ' ', s)).strip()


# ---------------------------------------------------------------- text hygiene
JARGON = [re.compile(p, re.I) for p in [
    r'\b[\w-]+\.(?:js|py|jsx|ts|css|html|json|md|bat|ps1)\b', r'\\[A-Za-z]', r'(?:^|\s)/api/', r'\b\w+\(\)',
    r'\b(?:payload|endpoint|localStorage|sessionStorage|DOM|regex|JSON|inventory|handler|callback|refactor|SPB-\d+|TODO|FIXME|monkey-?patch|state machine|API call|stack trace)\b',
    r'\bC:\\|\bE:\\|/Users/']]
NOISE = re.compile('[\U0001F000-\U0001FFFF☀-➿⬀-⯿①-⓿←-⇿■-◿️‍•✓✔✕✖ ]')
FIXES = [(re.compile(r'\(press E\)'), '(press Shift+E)'), (re.compile(r'\bE shows / hides the panel'), 'Shift+E shows / hides the panel'), (re.compile(r'\bpainted into the car\b'), 'painted into the car')]
TAG = re.compile(r'</?(?:b|i|u|br|code|span|div|p|a|strong|em|small|sup|sub|li|ul|ol|h[1-6]|img|button|label|svg|path|select|option|input|summary|details|kbd|font|center)(?:\s[^>]*)?/?>', re.I)


def is_jargon(t): return any(r.search(t) for r in JARGON)


TECH_PAREN = re.compile(r'\s*\([^()]*\b(?:kit|engine|setter|server|null|undefined|UI)\b[^()]*\)|\s*\([^()]*\b[A-Z]+_[A-Z_]+\b[^()]*\)')
TECH_WORD = re.compile(r'\b(?:kit|engine|setter|server|undefined|null|payload)\b')


def scrub_tech(s):
    s = TECH_PAREN.sub('', s)
    cl = [c for c in s.split(';') if not TECH_WORD.search(c)]
    s = ';'.join(cl)
    return re.sub(r'\bUI\s+', '', s)


def clean(s):
    """one user-facing string: entities and tags out, symbols out, jargon sentences dropped"""
    if s is None: return ''
    s = str(s)
    s = re.sub(r'<code[^>]*>.*?</code>', '', s, flags=re.S)
    s = html.unescape(TAG.sub(' ', s))
    s = NOISE.sub(' ', s).replace('—', ' - ').replace('–', '-').replace('−', '-').replace('’', "'").replace('…', '...')
    for rx, rep in FIXES: s = rx.sub(rep, s)
    s = scrub_tech(s).replace('....', '...')
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'^[\s|:;,]+|[\s|:;,]+$', '', s)
    s = re.sub(r'^-\s+|\s+-$', '', s).strip()
    if not s: return ''
    parts = re.split(r'(?<=[.!?])\s+', s)
    keep = [p for p in parts if not is_jargon(p)]
    return ' '.join(keep).strip()


def sent_count(s): return len(re.findall(r'[.!?](\s|$)', s))


def first_sentence(s, cap=170):
    if not s: return ''
    p = re.split(r'(?<=[.!?])\s+', s)[0]
    if len(p) > cap: p = p[:cap].rsplit(' ', 1)[0].rstrip(' ,;:-') + '...'
    return p


def endp(s):
    s = s.strip()
    return s if not s or s[-1] in '.!?' else s + '.'


def cap1(s): return s[:1].upper() + s[1:] if s else s


def humanize(i):
    i = re.sub(r'^(?:sculpt|drop|pro|html|ctl|zone|layer|key)[.:]', '', i)
    i = re.sub(r'\.\d+$', '', i)
    i = re.sub(r'^(?:btn|s|n|chk|sel|inp|cb)(?=[A-Z])', '', i)
    i = re.sub(r'([a-z])([A-Z])', r'\1 \2', i).replace('_', ' ').replace('.', ' ')
    return cap1(re.sub(r'\s+', ' ', i).strip())


# ---------------------------------------------------------------- HTML context around a control
_LINES = {}


def lines_of(rel):
    if rel not in _LINES:
        p = P(rel)
        _LINES[rel] = open(p, encoding='utf8', errors='replace').read().split('\n') if os.path.exists(p) else []
    return _LINES[rel]


STOP = re.compile(r'<input|<button|<select|<textarea|slider-head')
HEAD = re.compile(r'class="(?:lbl-sub|section-title|panel-title|card-title|sec-title|sec-head|group-title)[^"]*"|<h[1-4][ >]|<summary')


def ctx(rec):
    m = re.match(r'^([\w./-]+\.html):(\d+)$', rec.get('source', ''))
    if not m: return {}
    L = lines_of(m.group(1)); i = int(m.group(2)) - 1
    if i < 0 or i >= len(L): return {}
    cur = L[i]; out = {}
    t = re.search(r'title="([^"]*)"', cur)
    if t: out['title'] = clean(t.group(1))
    ph = re.search(r'placeholder="([^"]*)"', cur)
    if ph: out['ph'] = clean(ph.group(1))
    b = re.search(r'<button[^>]*>(.*?)</button>', cur)
    own = clean(b.group(1)) if b else clean(cur)
    if own: out['own'] = own
    if not own or rec['kind'] in ('slider', 'number input', 'dropdown', 'text input', 'file input'):
        for j in range(i - 1, max(i - 4, -1), -1):
            if re.search(r'slider-head|<label|lbl', L[j]):
                h = clean(L[j])
                if h and not re.fullmatch(r'[-\d.\s]*', h): out['head'] = h; break
            if STOP.search(L[j]) and 'slider-head' not in L[j]: break
    for j in range(i + 1, min(i + 4, len(L))):
        if re.search(r'class="(?:hint|sub|note|help)', L[j]):
            blob = L[j]; k = j
            while not re.search(r'</(?:div|p|span)>', blob) and k < min(j + 3, len(L) - 1): k += 1; blob += ' ' + L[k]
            h = clean(blob)
            if h: out['hint'] = h
            break
        if STOP.search(L[j]): break
    for j in range(i, max(i - 14, -1), -1):
        if HEAD.search(L[j]):
            h = clean(L[j])
            if 3 <= len(h) <= 60:
                out['section'] = h.capitalize() if h.isupper() else h; break
    if rec['kind'] == 'dropdown':
        opts = []
        for j in range(i, min(i + 70, len(L))):
            for o in re.findall(r'<option[^>]*>(.*?)</option>', L[j]):
                o = clean(o)
                if o and o not in opts: opts.append(o)
            if '</select>' in L[j]: break
        if opts: out['opts'] = opts
    return out


# ---------------------------------------------------------------- library of what already exists
def existing_articles():
    ids, ali, title = set(), {}, {}
    for fn in sorted(os.listdir(ENC)):
        if not fn.endswith('.json') or fn.startswith('_') or fn in ('manifest.json', 'graphics.json', 'figures.json', 'controls.json', 'shortcuts.json'): continue
        try: j = jload(os.path.join(ENC, fn))
        except Exception: continue
        if not isinstance(j, dict): continue
        for a in j.get('articles', []):
            ids.add(a['id']); title[a['id']] = a.get('title', a['id'])
            for al in a.get('aliases') or []: ali[al] = a['id']
    return ids, ali, title


# ---------------------------------------------------------------- controls
CTL_KINDS = {'button', 'slider', 'toggle', 'dropdown', 'text input', 'picker', 'number input', 'file input', 'radio', 'menu', 'search box', 'tab', 'zone_param'}
KIND_WORD = {'button': 'button', 'slider': 'slider', 'toggle': 'on/off switch', 'dropdown': 'drop-down menu', 'text input': 'text box', 'number input': 'number box',
             'file input': 'file chooser', 'radio': 'choice button', 'picker': 'colour picker', 'menu': 'menu', 'search box': 'search box', 'tab': 'tab', 'zone_param': 'zone setting'}
ART = lambda w: ('an ' if w[0] in 'aeiou' else 'a ') + w
HOW = {'button': 'Click the button.', 'slider': 'Drag the slider, or click it and use the arrow keys.', 'toggle': 'Click to switch it on or off.',
       'dropdown': 'Open the menu and pick a choice.', 'text input': 'Click the box and type.', 'number input': 'Click the box and type a number, or use the arrows.',
       'file input': 'Click it and choose a file.', 'radio': 'Click the circle to pick this choice.', 'picker': 'Click the colour swatch and pick a colour.',
       'menu': 'Click to open the menu and pick an item.', 'search box': 'Click the box and type part of a name.', 'tab': 'Click the tab to open it.', 'zone_param': 'Set it in the zone panel.'}
PAGE_NAME = {'spec-sculpt.html': 'Spec Sculpt Lab', 'shokk-drop.html': 'Shokk Drop'}
TOPIC_NAME = {
    'pro.ai': 'Pro > Shokker AI panel', 'pro.finish_library': 'Pro > Finish library', 'pro.finish_picker': 'Pro > left column > finish picker', 'pro.history': 'Pro > Undo History panel',
    'layer_card': 'Pro > LAYERS tab > layer card', 'pro.layers': 'Pro > right column > LAYERS tab', 'pro.right': 'Pro > right column', 'pro.preview': 'Pro > preview and canvas bar',
    'pro.render': 'Pro > render panel', 'pro.settings': 'Pro > Settings', 'pro.shokk_library': 'Pro > Shokk library', 'pro.spec_tools': 'Pro > Spec tools',
    'pro.eyedropper': 'Pro > Eyedropper options', 'pro.placement': 'Pro > placement bar', 'pro.selection_bar': 'Pro > selection bar', 'pro.tool_options': 'Pro > tool options bar',
    'pro.toolbar': 'Pro > left toolbar', 'pro.transform': 'Pro > transform bar', 'pro.center': 'Pro > centre of the window', 'pro.dialogs': 'Pro > dialog box',
    'pro.finish_browser': 'Pro > Finish catalog browser', 'pro.header': 'Pro > top bar', 'pro.modes': 'Pro > mode pill', 'pro.zone_editor': 'Pro > zone popout panel',
    'pro.zones': 'Pro > left column > ZONES', 'pro.zones_more': 'Pro > ZONES > More menu', 
    'ctl:colour': 'zone colour setting', 'ctl:paint_global': 'paint setting', 'ctl:spec_direct': 'spec setting', 'html:root': 'the main window'}
NEEDS = {'paint': 'Needs a paint loaded first.', 'psd': 'Needs a layered template (PSD) loaded.', 'zone': 'Needs a zone selected first.'}

# (regex on label+does+id, article id). First matching candidate wins, then the domain default.
REL = {
    'tools': [(r'eraser|brush size|hardness|brush', 'tools.brush_eraser'), (r'fill|bucket', 'tools.fill_bucket'), (r'eyedropper|pick colo', 'tools.eyedropper_pick'),
              (r'heal|smudge|burn|dodge|recolor|retouch|color brush', 'tools.retouch'), (r'wand|lasso|rect|marquee|ellip', 'tools.select_shapes'),
              (r'add|subtract|intersect|replace', 'tools.selection_modes'), (r'grow|shrink|feather|invert|expand|contract|smooth border|refine', 'tools.refine_selection'),
              (r'mirror|symmetr', 'tools.mirror_symmetry'), (r'move|transform|rotate|scale|flip|nudge|placement', 'tools.move_transform'),
              (r'zoom|pan|fit|view', 'tools.zoom_pan'), (r'undo|redo', 'tools.undo_redo'), (r'mask', 'tools.mask_vs_layer')],
    'layers': [(r'\bfx|effect|shadow|glow|stroke|bevel|overlay', 'layers.effects'), (r'opacity|blend|\bhue\b|saturation|bright', 'layers.opacity_blend'),
               (r'merge|flatten|blank', 'layers.merge'), (r'photoshop|psexport|exchange|car file', 'layers.export_photoshop'), (r'open layered|psd|xcf|ora\b', 'layers.open_psd'),
               (r'lock zone|make zone', 'layers.lock_zone_to_layer'), (r'layer\.btn|dupe|mirror|rename|solo|flip|rot 90|xform|\bpan\b|\bfit\b|export|delete', 'layers.card_buttons')],
    'zones': [(r'tolerance', 'zones.tolerance'), (r'priority|order|move up|move down', 'zones.priority'), (r'region|box|lasso|apply area|draw', 'zones.regions'),
              (r'exclude|use region', 'zones.exclude_set_use_region'), (r'layer', 'zones.restrict_layers'), (r'pick|add|colou?r', 'zones.add_pick_colour'),
              (r'preset|template', 'zones.presets_templates'), (r'part', 'zones.named_parts')],
    'spec': [(r'remap|lighting|material', 'spec.material_override_remap_lighting'), (r'blend', 'spec.blend_modes'), (r'scale|rotation', 'spec.scale_rotation'),
             (r'strength|independent', 'spec.strength_and_independent'), (r'inspector|angle', 'spec.inspector'), (r'channel|metal|rough|clear', 'spec.channel_sliders')],
    'patterns': [(r'scale|rotation|opacity|strength', 'patterns.scale_rotation_opacity'), (r'place|position|offset', 'patterns.placement'), (r'layer|stack', 'patterns.layers_and_stacking')],
    'bases': [(r'scale|rotation', 'finishes.base_scale_rotation'), (r'hue|sat|bright|strength|colou?r', 'finishes.base_colour_tuning'), (r'second|overlay', 'finishes.second_base_overlays'),
              (r'flip|depth|underglow|gradient', 'finishes.gradients_flip_depth_underglow')],
    'finishes': [(r'library|browser|filter|search', 'finishes.picker_library_browser'), (r'foundation|source', 'finishes.foundation_shine_only')],
    'preview_render': [(r'render|ctrl\+r', 'preview_render.render_button'), (r'view|channel|preview', 'ui_shell.preview_channel_views'), (r'history|stats', 'preview_render.render_history_stats')],
    'ui_shell': [(r'selection', 'ui_shell.selection_bar'), (r'tool option', 'ui_shell.tool_options_bar'), (r'placement', 'ui_shell.placement_overlay'), (r'dialog|apply|cancel', 'ui_shell.dialogs_reference'),
                 (r'project|save|open', 'ui_shell.save_open_projects'), (r'update', 'ui_shell.update_banner'), (r'source paint|template|psd', 'ui_shell.source_paint'),
                 (r'car folder|iracing', 'ui_shell.car_folder'), (r'mode|pro', 'ui_shell.mode_pill')],
    'spec_sculpt': [(r'preset|scratch', 'spec_sculpt.scratch_presets'), (r'separate|protect|mask', 'spec_sculpt.smart_separate'), (r'export|save', 'spec_sculpt.iron_safe_export'),
                    (r'mode|simple|advanced', 'spec_sculpt.three_modes'), (r'diagnos|loupe|inspect', 'spec_sculpt.diagnostics'), (r'recipe|look', 'spec_sculpt.recipes')],
    'shokk_drop': [(r'import|plate|bundle|export', 'shokk_drop.import_export'), (r'gallery|favou?rite|delete|select', 'shokk_drop.gallery')],
}
DEFAULT_REL = {'tools': 'tools.shortcuts_quick', 'layers': 'layers.panel', 'zones': 'zones.card_controls', 'spec': 'spec.channel_sliders', 'patterns': 'patterns.what_is_a_pattern',
               'bases': 'finishes.base_colour_tuning', 'finishes': 'finishes.picker_library_browser', 'preview_render': 'preview_render.render_button', 'history': 'history.panel',
               'ui_shell': 'ui_shell.window_tour', 'spec_sculpt': 'spec_sculpt.controls_reference', 'settings': 'settings.overview', 'shokk_drop': 'shokk_drop.overview',
               'ai_copilot': 'ai_copilot.overview'}
TOPIC_REL = {'pro.header': 'ui_shell.top_bar_buttons', 'pro.dialogs': 'ui_shell.dialogs_reference', 'pro.finish_browser': 'finishes.picker_library_browser',
             'pro.modes': 'ui_shell.mode_pill', 'pro.center': 'ui_shell.canvas_overlays', 'pro.selection_bar': 'ui_shell.selection_bar', 'pro.tool_options': 'ui_shell.tool_options_bar',
             'pro.placement': 'ui_shell.placement_overlay', 'pro.zones_more': 'ui_shell.zones_more_menu', 'pro.spec_tools': 'spec_sculpt.spec_tools_menu',
             'pro.zone_editor': 'zones.popout_panel', 'pro.settings': 'ui_shell.panels_and_ui_size', 'pro.toolbar': 'tools.shortcuts_quick'}


# The four zone_param records are settings the app or the Shokker AI writes; there is no slider for them.
BEHIND = 'Behind the scenes: the app and the Shokker AI set this. There is no control for it'
ZP = {
    'ctl.zone_base_colour_strength': ('Colour strength (zone setting)', 'How strongly a chosen colour replaces the own colours of the finish. It is an older crossfade setting.',
                                      'Ignored in finish and source colour modes. The Colour Depth control takes over when the Color Lab is active.'),
    'ctl.zone_spec_material_override_remap_lightingmask': ('Spec sample override, remap and lighting mask (zone setting)',
                                                           'Exact metal, roughness and clearcoat values for a zone, a low and high range remap, and the spec alpha used as a lighting mask.',
                                                           'No Pro slider writes these. The spec sample tools set them.'),
    'ctl.zone_cc_quality': ('Clearcoat quality (older setting)', 'Lower values give a worse, hazier clearcoat.',
                            'It overlaps with the blue clearcoat channel shift. It is an older setting and is not in the main panel.'),
    'ctl.paint_global_base_color_depth_rule': ('Exact colour rule (zone setting)', 'Your colour mode choice is final: source mode keeps your paint and a solid colour stays exact.',
                                               'Colour depth is only added when you have touched the Color Lab, because depth darkens an exact colour.'),
}
# Inventory slip: these two records point at the Settings spec-map Clear button (line 2242). The real Undo History Clear is at line 4763.
FIX_REC = {'pro.history.clear': {'source': 'paint-booth-v2.html:4763', 'drop': ('tooltip', 'handler', 'drives', 'read_at')},
           'pro.tool_options.clear': {'drop': ('tooltip', 'handler', 'drives', 'read_at')}}
GENERIC = {'none', 'close', 'clear', 'apply', 'ok', 'cancel', 'all', 'reset', 'done', 'yes', 'no', 'select', 'edit', 'add', 'remove', 'delete', 'save', 'load', 'open', 'back', 'next', 'more', 'off', 'on', 'undo', 'redo', 'go', 'set', 'use', 'new', 'copy', 'paste'}


def related_for(rec, blob, have):
    out = []
    dom = rec['domain']
    for rx, art in REL.get(dom, []):
        if re.search(rx, blob) and art in have and art not in out: out.append(art); break
    d = TOPIC_REL.get(rec.get('topic')) if dom in ('ui_shell', 'tools', 'zones', 'bases', 'patterns', 'spec', 'settings', 'ai_copilot') else None
    for a in (d, DEFAULT_REL.get(dom)):
        if a and a in have and a not in out: out.append(a)
    if not out: out.append('shortcuts.control_index')
    return out[:2]


def make_range(f, c):
    if f.get('range'): return clean(f['range'])
    if c.get('range'): return clean(c['range'])
    if 'min' in f and 'max' in f:
        return '%s to %s' % (f['min'], f['max']) + (', step %s' % f['step'] if f.get('step') not in (None, '') else '')
    return ''


def good_label(s):
    if not s or len(re.sub(r'[^A-Za-z]', '', s)) < 2: return False
    if RF.FRAGMENT.search(s): return False          # ENC_READER_FIX: hint / sentence fragments ('(the color art)', '...or paste', CSS)
    if re.match(r'^(e\.g\.|path to|your name)', s, re.I): return False
    if re.search(r"'\s*\+|_msel|\\u[0-9a-f]{4}", s): return False
    return True


def short_label(s):
    """labels copied from tooltips are sentences; keep the name part"""
    s = re.split(r'\s+[-|]\s+|:\s|\s\(|\.\s', s)[0].strip(' :-')
    return s


def trim(s, n):
    if len(s) <= n: return s
    return s[:n].rsplit(' ', 1)[0].rstrip(' ,;:-(') + '...'



LEVEL = {'spec_sculpt': 'pro', 'shokk_drop': 'pro', 'zones': 'intermediate', 'bases': 'intermediate', 'spec': 'intermediate', 'patterns': 'intermediate', 'layers': 'intermediate'}


def fields_h(zf):
    """zone field names -> plain words ('baseHueOffset' -> 'base hue offset'); empty when the text is not a simple list"""
    if not zf or re.search(r'[{}()\[\]:]', zf): return ''
    out = []
    for p_ in re.split(r'\s*,\s*', zf.strip()):
        w_ = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', p_).lower().strip()
        if w_ and re.fullmatch(r'[a-z ]+', w_): out.append(w_)
    return ' and '.join(out) if len(out) <= 2 else ''


def enrich(a, r, f, c, label, kw, lead, rng, dflt, src_ok):
    """schema v3 depth for a generated control page, only from facts that exist (nothing invented)"""
    ctl = f.get('control') or {}
    deep = []
    eff = clean(ctl.get('effect')); app = clean(ctl.get('applies_to'))
    if eff or app:
        deep.append({'heading': 'What it changes', 'body': trim(' '.join(x for x in (endp(eff) if eff else '', ('Applies to: ' + endp(app)) if app else '') if x), 520)})
    hood = []
    zf = fields_h(ctl.get('zone_field'))
    if zf: hood.append('Behind the scenes it sets the zone %s.' % zf)
    if rng: hood.append('It runs over %s%s.' % (rng, (' and starts at %s' % dflt) if dflt else ''))
    elif dflt and ctl: hood.append('It starts at %s.' % dflt)
    unit = clean(ctl.get('unit'))
    if unit and unit.lower() not in ('rule',): hood.append('Measured in %s.' % unit)
    if hood: deep.append({'heading': 'Under the hood', 'body': trim(' '.join(hood), 520)})
    inter = clean(ctl.get('interactions'))
    if inter: deep.append({'heading': 'How it combines with other controls', 'body': trim(inter, 520)})
    if deep: a['deep'] = deep
    hint = clean(ctl.get('planner_hint'))
    if hint: a['protips'] = [trim('Typical values: ' + endp(hint), 300)]
    faq = []
    if lead: faq.append({'q': 'What does %s do?' % label, 'a': trim(lead, 300)})
    if f.get('when') and clean(f['when']): faq.append({'q': 'When should I use %s?' % label, 'a': trim(endp(clean(f['when'])), 300)})
    if rng or dflt: faq.append({'q': 'What is the range and starting value of %s?' % label, 'a': trim(('Range %s. ' % rng if rng else '') + ('It starts at %s.' % dflt if dflt else ''), 200).strip()})
    if f.get('mistakes') and clean(f['mistakes']): faq.append({'q': 'Why does %s not seem to do what I expect?' % label, 'a': trim(endp(clean(f['mistakes'])), 300)})
    if len(faq) >= 2 and (deep or hint): a['faq'] = faq
    dom = r['domain']
    if (deep or hint or len(faq) >= 2) and dom in LEVEL: a['level'] = LEVEL[dom]
    elif (deep or hint or len(faq) >= 2): a['level'] = 'beginner'
    rel = [i for i in (f.get('related') or []) if i != r['id']]
    if rel: a['_rel'] = rel
    extra = []
    for sx in ((f.get('drives') or {}).get('defined'), (f.get('read_at') or '').split(' ')[0]):
        s2 = src_ok(sx)
        if s2 and s2 not in a['sources'] and s2 not in extra: extra.append(s2)
    if (deep or hint) and extra: a['sources'] = (a['sources'] + extra)[:3]


def build_controls():
    inv = jload(P('scripts', 'ai_atlas', 'enc_inventory.json'))['records']
    recs = [r for r in inv if r['kind'] in CTL_KINDS and not r.get('hidden')]   # hidden features (enc_hidden_features.json) get no pages
    have, owned, _ = existing_articles()
    have |= {'shortcuts.table', 'shortcuts.control_index', 'shortcuts.glossary', 'shortcuts.colour_names', 'shortcuts.finish_shelves', 'shortcuts.spec_cheat_sheet'}
    nlines = {}

    def src_ok(s):
        m = re.match(r'^([\w./-]+):(\d+)', s or '')
        if not m: return None
        f, n = m.group(1), int(m.group(2))
        if f not in nlines:
            p = P(f); nlines[f] = len(open(p, encoding='utf8', errors='replace').read().split('\n')) if os.path.exists(p) else 0
        return '%s:%d' % (f, n) if 1 <= n <= nlines[f] else None

    rows = []
    for r in recs:
        fx = FIX_REC.get(r['id'])
        if fx:
            r = dict(r); r['facts'] = {k: v for k, v in r['facts'].items() if k not in fx['drop']}
            if fx.get('source'): r['source'] = fx['source']
        f = r['facts']; c = f.get('control') or {}
        x = ctx(r)
        kind = r['kind']
        raw = clean(r['label'])
        label = raw if good_label(raw) else ''
        if kind in ('text input', 'file input', 'number input', 'dropdown') and x.get('head') and (not label or raw.lower().startswith('e.g')): label = x['head']
        for cand in (x.get('head') if kind == 'slider' and not label else '', x.get('own'), x.get('title'), clean(f.get('tooltip')), clean(f.get('does'))):
            if not label and cand and good_label(cand): label = first_sentence(cand, 60)
        if not label: label = humanize(r['id'])
        label = label.strip(' :')
        if len(label) > 44: label = trim(short_label(label), 44) or trim(label, 44)
        does = clean(f.get('does') or c.get('effect') or f.get('effect') or f.get('tooltip') or x.get('title') or x.get('hint') or '')
        where = clean(f.get('where'))
        if not where:
            pg = f.get('page')
            sec = x.get('section')
            where = ('%s > %s' % (PAGE_NAME.get(pg, pg), sec) if pg and sec else PAGE_NAME.get(pg, '') if pg else (TOPIC_NAME.get(r.get('topic'), 'the main window') + (' > ' + sec if sec and r.get('topic') == 'html:root' else '')))
        where = trim(where, 110)
        if r['id'] in ZP:
            label, does, extra = ZP[r['id']]; where = BEHIND; c = dict(c); c['_extra'] = extra
        rows.append({'r': r, 'f': f, 'c': c, 'x': x, 'kind': kind, 'label': label, 'does': does, 'where': where})

    # make titles unique inside the file: repeat of a title gets its place in brackets, then a number
    used = set()
    # FACTCHECK 2026-10-04: 7 labels came out of the HTML scan as attribute fragments (autocomplete=..., <button class=..., 'title=...'). Real on-screen labels:
    LABEL_FIX = {'psExportExchangeFolder': 'Export folder', 'shokkPsExportFolder': 'Channel PNG Export folder',
                 'drop.userImportSetSpecCombined': 'Combined spec image', 'sculpt.sepSens': 'Sensitivity (decal detection)',
                 'pro.selection_bar.1': '+1 (expand selection)', 'pro.transform.180': '180 degrees (rotate transform)', 'scriptFilename': 'SCRIPT NAME'}
    for w in rows:
        w['label'] = LABEL_FIX.get(w['r']['id'], w['label'])
        w['label'] = RF.readable_title(w['label'], w['r']['id'])          # ENC_READER_FIX 2026-10-05: no '(the color art)', '+ Add Zone', '#carbon' titles
    for w in rows:
        t = w['label']; sec = w['x'].get('section') or w['where'].split(' > ')[-1]
        if norm(t) in GENERIC or len(norm(t)) <= 3: t = '%s (%s)' % (t, trim(sec, 28))
        cand = t
        if norm(cand) in used and '(' not in t: cand = '%s (%s)' % (t, trim(sec, 24))
        n = 2
        while norm(cand) in used: cand = '%s %d' % (t if '(' in t else '%s (%s)' % (t, trim(sec, 24)), n); n += 1
        used.add(norm(cand)); w['title'] = cand
    labcount = collections.Counter(norm(w['label']) for w in rows)

    arts = []
    for w in rows:
        r, f, c, x, kind = w['r'], w['f'], w['c'], w['x'], w['kind']
        kw = KIND_WORD[kind]; label = w['label']
        does = w['does']; hint = x.get('hint', '')
        if hint and norm(hint) == norm(does): hint = ''
        lead = endp(first_sentence(does)) if does else ''
        if not lead and hint: lead = endp(first_sentence(hint)); hint = ''
        if lead and norm(lead.rstrip('.')) == norm(label): lead = ''
        summ = (lead + ' ' if lead else '') + 'It is %s.' % ART(kw) if lead else 'The %s %s.' % (label, kw)
        if sent_count(summ) > 2 or len(summ) > 320: summ = 'The %s %s.' % (label, kw)
        rng = make_range(f, c); dflt = f.get('default', c.get('default', ''))
        dflt = clean(dflt) if isinstance(dflt, str) else ('' if dflt in (None, '') else str(dflt))
        det = []
        rest = clean(f.get('does') or '')
        more = re.split(r'(?<=[.!?])\s+', rest)[1:] if rest else []
        det += [endp(m) for m in more[:2]]
        tt = norm(clean(f.get('tooltip')))
        if tt and not any(tt in norm(z) or norm(z) in tt for z in (does, rest, label) if z): det.append(endp(first_sentence(clean(f['tooltip']))))
        if hint: det.append(endp(first_sentence(hint, 220)))
        if rng: det.append('Range %s%s.' % (rng, (', starts at %s' % dflt) if dflt else ''))
        elif dflt and kind in ('toggle', 'dropdown', 'radio', 'text input', 'number input'): det.append('Starts as %s.' % dflt)
        opts = f.get('options') or x.get('opts') or []
        if opts:
            o = [clean(v) for v in opts if clean(v)]
            if o: det.append('Choices: %s.' % trim('; '.join(o[:10]), 200))
        ph = clean(f.get('placeholder') or x.get('ph') or '')
        if ph and kind in ('text input', 'search box', 'number input'): det.append('Hint inside the box: %s.' % trim(ph, 80).rstrip('.'))
        if c.get('_extra'): det.append(c['_extra'])
        what = ' '.join([('Find it in %s.' % w['where']) if kind != 'zone_param' else endp(w['where'])] + det)
        when = [trim(endp(clean(f['when'])), 170)] if f.get('when') and clean(f['when']) else []
        pit = [trim(endp(clean(f['mistakes'])), 200)] if f.get('mistakes') and clean(f['mistakes']) else []
        tips = []
        for n in (f.get('needs') or []):
            if n in NEEDS and NEEDS[n] not in tips: tips.append(NEEDS[n])
        blob = ' '.join([label, does, r['id'], str(r.get('topic') or '')]).lower()
        eff = trim(lead.rstrip('.') if lead else (hint or ''), 80)
        srcs = []
        for s in (r.get('source'), (f.get('drives') or {}).get('defined')):
            s2 = src_ok(s)
            if s2 and s2 not in srcs: srcs.append(s2)
        m = re.match(r'^([\w./-]+):\d+', f.get('read_at') or '')
        if m and len(srcs) < 2:
            s2 = src_ok(f['read_at'].split(' ')[0])
            if s2 and s2 not in srcs: srcs.append(s2)
        a = {'id': 'controls.' + r['id'], 'title': w['title'], 'domain': 'controls', 'summary': summ, 'what': what, 'when': when,
             'how': [HOW[kind]], 'controls': [{'label': label, 'range': rng, 'default': dflt, 'effect': eff, 'inv': r['id']}],
             'tips': tips, 'pitfalls': pit, 'related': related_for(r, blob, have), 'actions': [], 'figures': [], 'covers': [r['id']], 'sources': srcs[:1],
             'aliases': [], 'quick': False, 'lane': 'A', 'updated': TODAY, 'generated': True}
        if f.get('ui_kind') or f.get('handler') or kind == 'zone_param': a['actions'] = [{'do': 'control', 'id': r['id']}]
        k = norm(label)
        if (len(k) >= 8 or len(k.split()) >= 2) and labcount[k] == 1 and k not in owned and not norm(w['title']).startswith(('1 ', '2 ')) and not re.fullmatch(r'[\d. %]+', k):
            a['aliases'] = [k]
        if not srcs: a['sources'] = [{'spec-sculpt.html': 'spec-sculpt.html:1', 'shokk-drop.html': 'shokk-drop.html:1'}.get(f.get('page'), 'paint-booth-v2.html:1')]
        for key in ('title', 'summary', 'what'):
            if is_jargon(a[key]): a[key] = a[key] if key == 'title' else 'The %s %s is in %s.' % (label, kw, trim(w['where'], 70))
        enrich(a, r, f, c, label, kw, lead, rng, dflt, src_ok)
        arts.append(a)
    return arts


# ---------------------------------------------------------------- shortcuts (6 reference articles)
def node_dump():
    code = ("const e=require('./scripts/ai_atlas/enc_extract.js');const r=e.dump('.');const c={};"
            "r.atlas.items.forEach(i=>{c[i.s]=(c[i.s]||0)+1});"
            "console.log(JSON.stringify({sections:r.atlas.sections,blurbs:r.atlas.blurbs,count:r.atlas.count,counts:c,colours:r.design.COLOURS,colourExt:Object.keys(r.colourExt||{})}));")
    out = subprocess.run(['node', '-e', code], cwd=ROOT, capture_output=True, text=True, encoding='utf8')
    for ln in reversed(out.stdout.strip().split('\n')):
        if ln.startswith('{'): return json.loads(ln)
    raise SystemExit('node dump failed: ' + out.stderr[:300])


def art(aid, title, summary, what, when=(), how=(), controls=(), tips=(), pitfalls=(), related=(), actions=(), figures=(), covers=(), sources=(), quick=False, aliases=()):
    return {'id': 'shortcuts.' + aid, 'title': title, 'domain': 'shortcuts', 'summary': summary, 'what': what, 'when': list(when), 'how': list(how), 'controls': list(controls),
            'tips': list(tips), 'pitfalls': list(pitfalls), 'related': list(related), 'actions': list(actions), 'figures': list(figures), 'covers': list(covers),
            'sources': list(sources), 'aliases': sorted({norm(a) for a in aliases}), 'quick': quick, 'lane': 'A', 'updated': TODAY, 'generated': True}


KEY_FIX = {'key.m': 'Select with the elliptical marquee (the rectangle select is on O).', 'key.e': 'Eraser.', 'key.x': 'Make the brush smaller or larger (5 at a time); { and } change hardness.',
           'key.1_9': 'Set the brush or layer opacity to 10 to 90 percent (0 sets 100 percent).', 'key.shift_e': 'Show or hide the zone popout panel.',
           'key.x~2': 'Swap the foreground and background colours.', 'key.x~3': 'Reset the foreground and background colours.', 'key.x~4': 'Open this shortcut panel.',
           'key.esc': 'Close the shortcut panel.'}


def build_shortcuts(have_titles, owned=None):
    inv = jload(P('scripts', 'ai_atlas', 'enc_inventory.json'))['records']
    keys = [r for r in inv if r['domain'] == 'shortcuts' and not r.get('hidden')]
    nd = node_dump()
    enc = open(P('js', 'spb-encyclopedia-data.js'), encoding='utf8').read()
    terms = json.loads(enc[enc.index('=') + 1:].strip().rstrip(';'))['terms']
    info = [t for t in terms if t.get('kind') == 'info']
    R = lambda ids: [i for i in ids if i in have_titles or i.startswith('shortcuts.')]
    out = []

    # 1. the key table
    ctls = []; sections = collections.OrderedDict()
    for k in keys:
        f = k['facts']; kk = ' / '.join(f.get('keys') or [k['label']]) if isinstance(f.get('keys'), list) else clean(k['label'])
        txt = clean(f.get('text') or k['label'])
        rest = txt
        changed = True
        while changed:   # strip each leading key once, only at a word boundary ("B Brush" -> "Brush", never "rush")
            changed = False
            for ky in sorted(f.get('keys') or [], key=len, reverse=True):
                if re.match(re.escape(ky) + r'(?=\s|/|$)', rest): rest = rest[len(ky):].lstrip(' /'); changed = True; break
        eff = KEY_FIX.get(k['id']) or cap1(endp(rest or txt))
        eff = re.sub(r'^/\s*', '', eff)
        ctls.append({'label': kk, 'range': '', 'default': '', 'effect': eff, 'inv': k['id']})
        sections.setdefault(f.get('section', 'OTHER'), []).append(kk)
    what = ('Keys listed in the in-app shortcut panel (press ?): ' + ' | '.join('%s: %s' % (cap1(s.lower()), ', '.join(v)) for s, v in sections.items()) +
            '. More keys that work in the canvas: O rectangle select, Y pick item, A select all of one colour, Ctrl+T transform, Ctrl+S save a snapshot, Ctrl+G generate script, F5 refresh the preview. '
            'Zones: Alt+1 to Alt+9 pick a zone, Up and Down move through zones, Ctrl+Up and Ctrl+Down change priority, with the Move Selection Border tool armed, Arrow nudges the zone\'s drawn border 1 pixel and Shift+Arrow 10 pixels. '
            'Brush: { and } change hardness by 10. With no paint tool active, 0, 1 and 2 give fit, 100 percent and 200 percent zoom. The mouse wheel always zooms.')
    out.append(art('table', 'Keyboard shortcuts', 'Every key the app listens to, grouped by job. The same list opens inside the app.', what,
                   when=['You want to work faster.', 'You forgot which key a tool uses.'], how=['Press ? to open the shortcut panel in the app.', 'Read the group you need.', 'Press ? or Esc to close it.'],
                   controls=ctls, tips=['Letter keys do nothing while you are typing in a text box.', 'Shift+E shows or hides the zone panel. E alone is the Eraser.'],
                   pitfalls=['The panel says Marquee for M. M is the elliptical marquee; use O for a rectangle.', 'Ctrl+S saves an autosave snapshot, not a project file. Use Save project for that.'],
                   related=R(['tools.shortcuts_quick', 'tools.undo_redo', 'tools.zoom_pan', 'zones.card_controls', 'ui_shell.save_open_projects']),
                   covers=[k['id'] for k in keys], sources=['paint-booth-v2.html:5221', 'paint-booth-3-canvas.js:12717', 'paint-booth-6-ui-boot.js:3825', 'paint-booth-v2.html:2231'],
                   aliases=['keyboard shortcuts', 'shortcuts', 'hotkeys', 'key list', 'what key does what', 'shortcut keys', 'keybindings'], quick=True))

    # 2. the control index
    cnt = collections.Counter()
    inv_all = [r for r in inv if r['kind'] in CTL_KINDS and not r.get('hidden')]
    for r in inv_all: cnt[r['domain']] += 1
    AREA = [('ui_shell', 'Window, top bar, dialogs', 'ui_shell.window_tour'), ('tools', 'Tools, tool options, selection', 'tools.shortcuts_quick'), ('zones', 'Zones', 'zones.card_controls'),
            ('layers', 'Layers tab', 'layers.panel'), ('finishes', 'Finish picker and library', 'finishes.picker_library_browser'), ('bases', 'Base colour and base settings', 'finishes.base_colour_tuning'),
            ('patterns', 'Patterns', 'patterns.what_is_a_pattern'), ('spec', 'Spec controls', 'spec.channel_sliders'), ('preview_render', 'Preview and render', 'preview_render.render_button'),
            ('history', 'Undo History', 'history.panel'), ('spec_sculpt', 'Spec Sculpt Lab', 'spec_sculpt.controls_reference'), ('shokk_drop', 'Shokk Drop', 'shokk_drop.overview'),
            ('settings', 'Settings', 'settings.overview'), ('ai_copilot', 'Shokker AI panel', 'ai_copilot.overview')]
    lines = ['%s: %d controls, start with "%s".' % (nm, cnt.get(d, 0), have_titles.get(a, a)) for d, nm, a in AREA if cnt.get(d)]
    out.append(art('control_index', 'Control index: where is every control', 'Every slider, button, switch and box has its own page. This index shows which area of the app each one lives in.',
                   'Each control page tells you what it does, its range and starting value, and where to find it. Search for the control by its label, or start from the area. ' + ' '.join(lines),
                   when=['You see a control and want to know what it does.', 'You know the job but not where the control is.'],
                   how=['Search for the label you see on screen.', 'Open the control page for the range, starting value and place.', 'Or open the area article first and follow its list.'],
                   tips=['A page says where the control is, for example Pro > right column > LAYERS tab.', 'Controls that the app builds on the fly (such as layer rows) are covered by their area article.'],
                   related=R([a for _, _, a in AREA]) + ['shortcuts.table'], sources=['paint-booth-v2.html:2231'],
                   aliases=['control index', 'where is the slider', 'what does this button do', 'list of controls', 'find a control', 'every control'], quick=False))

    # 3. glossary
    gl = ['%s: %s' % (clean(t['title']), endp(first_sentence(clean(t['summary']), 230))) for t in info if clean(t.get('summary'))]
    gl = [g for g in gl if not is_jargon(g)]
    gl = [g.replace('The template layers (Wire, Mask, Car_Mandatory) are guides, not paint.', 'Wire and Mask are guides, not paint. Car_Mandatory is real template art for the headlight and grill mesh.')
          .replace('Lock pins a zone so it survives if you randomise other things.', 'The lock on the BASE row stops Randomize from changing the base. LOCK ZONE on a layer card is a different lock: it ties a zone to one layer.') for g in gl]
    out.append(art('glossary', 'Glossary', 'Plain-words meaning of the terms the app uses, from spec map and tolerance to PSD and zone order.',
                   ' | '.join(gl), when=['A word in the app or in a help answer is new to you.'], how=['Find the term in the list.', 'Read the short meaning next to it.', 'Open the linked article for the full story.'],
                   tips=['Ask the Shokker AI "what is <term>" for the same answer in chat.'],
                   related=R(['spec.what_is_spec_map', 'zones.tolerance', 'zones.priority', 'layers.roles', 'preview_render.number_modes', 'finishes.foundation_shine_only']),
                   sources=['js/spb-encyclopedia-data.js:2'], aliases=['glossary', 'what does this word mean', 'terms', 'dictionary of terms', 'definitions']))

    # 4. colour names
    cols = nd['colours']; ext = [e for e in nd['colourExt'] if e not in cols]
    out.append(art('colour_names', 'Colour names the app understands', 'You can name a colour in words and the app maps it to a real colour. Only the core names set a zone colour; the extra names are for finding looks.',
                   'Core names with their exact colour: ' + ', '.join('%s %s' % (k, v) for k, v in cols.items()) + '. Only these ' + str(len(cols)) + ' core names set a zone colour. The extra words below are understood when you search for a look, but they do not set a zone colour: ' + ', '.join(sorted(ext)) + '.',
                   when=['You type a colour into the Shokker AI box and want to know which words work.', 'You want an exact shade by name.'],
                   how=['Type the colour name in your request, for example "make the hood burgundy".', 'If the shade is not right, add a word such as light, dark or deep.', 'Or pick the exact colour with the colour picker.'],
                   tips=['Two-word names such as antique gold work.', 'For an exact match, use the colour picker or a hex code.'],
                   pitfalls=['Some words name a finish, not a colour. Chrome, candy and pearl are finishes.', 'An extra name outside the core list will not set a zone colour. Use a core name, the colour picker or a hex code.'],
                   related=R(['finishes.colour_source_modes', 'finishes.base_colour_tuning', 'zones.add_pick_colour']), sources=['js/spb-pro-design.js:23', 'js/spb-colours-ext.js:2'],
                   aliases=['colour names', 'color names', 'which colours can i type', 'colour list', 'named colours', 'colour words']))

    # 5. finish shelves
    sec = nd['sections']; bl = nd['blurbs']; cn = {int(k): v for k, v in nd['counts'].items() if k.isdigit()}
    sl = []
    for i, nm in enumerate(sec):
        b = clean((bl[i] if i < len(bl) else '').split('|')[0])
        n = clean(nm)
        sl.append('%s (%d): %s' % (n, cn.get(i, 0), trim(b, 140)))
    out.append(art('finish_shelves', 'Finish shelf index', 'The catalogue is arranged in %d shelves. This index lists each shelf with how many finishes it holds and what it is for.' % len(sec),
                   'About %s finishes sit on these shelves in total. ' % format(sum(cn.values()), ',') + ' | '.join(sl) + ' | Note: Foundation mostly keeps your paint colours, but 5 of its 25 finishes (Orchid Shift Pearl, Moonstone, Dragon\'s Pearl Scale, Sentient Polycarbonate and Black Diamond Candy) bring their own colours.', when=['You want to browse by theme rather than search.', 'You want to know which shelf holds a look.'],
                   how=['Find the shelf that matches your idea.', 'Open the finish picker and pick that shelf.', 'Click a finish and look at the preview.'],
                   tips=['Most Foundation finishes change only the shine and keep your paint colours; 5 of the 25 bring their own colours.'], related=R(['finishes.catalogue_overview', 'finishes.picker_library_browser', 'finishes.foundation_and_efx', 'finishes.astra']),
                   sources=['js/spb-ai-atlas-data.js:2'], aliases=['finish shelves', 'shelf list', 'finish categories', 'list of finish groups', 'which shelf has', 'catalogue shelves']))

    # 6. spec cheat sheet
    out.append(art('spec_cheat_sheet', 'Spec value cheat sheet', 'The three spec numbers on one page: red is metal, green is roughness, blue is clearcoat.',
                   'Red (metal): 0 is paint or plastic, 255 is full metal. Green (roughness): 0 is a mirror, 255 is rough and dull. Blue (clearcoat): 16 is the shiniest coat, 255 is dull, 0 to 15 means no clearcoat. '
                   'Chrome: red 255, green near 0, blue 16, with near-white paint under it. Matte paint: red 0, green high, blue 255. '
                   'Where metal is below 240, keep roughness at 15 or more. Do not use blue values 1 to 15: the app raises them to 16. In the full-car render every clearcoat is lifted to at least 16, except on Shokk Drop finishes you uploaded yourself. '
                   'Decal kit values (metal, roughness, clearcoat): Flat Vinyl 0, 100, 110. Satin Decal 0, 100, 75. Gloss Decal 0, 42, 22.',
                   when=['You are setting metal, roughness or clearcoat and want the numbers at a glance.', 'A part looks too dull or too shiny.'],
                   how=['Decide the look: mirror, satin, matte or metal.', 'Set red for metal, green for roughness and blue for clearcoat using the table above.', 'Check the preview, then render.'],
                   controls=[{'label': 'Red (metal)', 'range': '0 to 255', 'default': '', 'effect': '255 is full metal, 0 is paint or plastic.', 'inv': ''},
                             {'label': 'Green (roughness)', 'range': '0 to 255', 'default': '', 'effect': '0 is a perfect mirror, 255 is rough and dull.', 'inv': ''},
                             {'label': 'Blue (clearcoat)', 'range': '16 to 255', 'default': '', 'effect': '16 is the shiniest, 255 is dull, 0 means no clearcoat.', 'inv': ''}],
                   tips=['Low roughness plus high metal is chrome. High roughness is matte or brushed.', 'A chrome part needs near-white paint under it, because iRacing multiplies the paint colour by the metal.'],
                   pitfalls=['A clearcoat of 255 makes even a chrome part look dull.', 'Without a spec file iRacing keeps the normal material: colours show but shine and chrome do not.'],
                   related=R(['spec.what_is_spec_map', 'spec.channel_r_metallic', 'spec.channel_g_roughness', 'spec.channel_b_clearcoat', 'spec.iron_rules', 'layers.decal_rescue']),
                   figures=['g01_spec_channels'], sources=['engine/SPEC_MAP_REFERENCE.md:9', 'engine/SPEC_MAP_REFERENCE.md:13', 'paint-booth-v2.html:4105'],
                   aliases=['spec cheat sheet', 'spec values', 'chrome values', 'metal rough clearcoat numbers', 'rgb spec table', 'what numbers for chrome', 'matte values'], quick=True))
    for a in out:
        a['aliases'] = [x for x in a['aliases'] if x not in (owned or {})]
        a['controls'] = [dict(c) for c in a['controls']]
        for c in a['controls']:
            if c.get('inv') == '': c.pop('inv')
        a['quick'] = a['quick'] and len(a['how']) >= 3
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--only', choices=['controls', 'shortcuts']); a = ap.parse_args()
    ids, owned_al, titles = existing_articles()
    if a.only in (None, 'shortcuts'):
        arts = build_shortcuts(titles, owned_al)
        atomic_json(os.path.join(ENC, 'shortcuts.json'), {'domain': 'shortcuts', 'version': 1, 'articles': arts})
        print('shortcuts.json: %d articles' % len(arts))
    if a.only in (None, 'controls'):
        arts = build_controls()
        inv = {r['id']: r for r in jload(P('scripts', 'ai_atlas', 'enc_inventory.json'))['records']}
        write_control_parts(arts, inv)


PART_TARGET = 70000   # bytes per part file (gate cap is 128 KB)


def write_control_parts(arts, inv):
    """split the control pages into pages/controls_<area>_<n>.json (same layout as the finish pages) + controls_pages.json"""
    import enc_ui_fix; enc_ui_fix.fix_articles(arts)   # UI audit 2026-10-05
    pdir = os.path.join(ENC, 'pages'); os.makedirs(pdir, exist_ok=True)
    for fn in os.listdir(pdir):
        if fn.startswith('controls_') and fn.endswith('.json'): os.remove(os.path.join(pdir, fn))
    old = os.path.join(ENC, 'controls.json')
    if os.path.exists(old): os.remove(old)
    groups = collections.OrderedDict()
    for x in arts: groups.setdefault(inv[x['covers'][0]]['domain'], []).append(x)
    parts = []; total = 0; plan = []
    for area, items in groups.items():
        chunks = [[]]; size = 0
        for x in items:
            n = len(json.dumps(x, ensure_ascii=False, separators=(',', ':')).encode('utf8')) + 1 + (1200 if x.get('_rel') else 0)
            if size + n > PART_TARGET and chunks[-1]: chunks.append([]); size = 0
            chunks[-1].append(x); size += n
        for i, ch in enumerate(chunks, 1):
            dom = 'controls_%s_%d' % (area, i)
            for x in ch: x['id'] = '%s.%s' % (dom, x['covers'][0]); x['domain'] = dom
            plan.append((area, dom, ch))
    pid = {x['covers'][0]: x for _, _, ch in plan for x in ch}
    for x in pid.values():
        rel = x.pop('_rel', None)
        if not rel: continue
        cb = [{'with': pid[i]['id'], 'why': 'Works together with the %s control.' % pid[i]['title']} for i in rel if i in pid and pid[i]['id'] != x['id']][:4]
        if cb: x['combos'] = cb
    for area, dom, ch in plan:
        fp = os.path.join(pdir, dom + '.json')
        atomic_json(fp, {'domain': dom, 'version': 1, 'articles': ch})
        nb = os.path.getsize(fp); total += nb
        parts.append({'file': 'pages/%s.json' % dom, 'domain': dom, 'group': area, 'count': len(ch), 'bytes': nb, 'firstKey': ch[0]['covers'][0], 'lastKey': ch[-1]['covers'][0]})
    atomic_json(os.path.join(ENC, 'controls_pages.json'), {'domain': 'controls_pages', 'version': 1, 'articles': [], 'generated': True,
                'note': 'One page per control (slider, button, switch, box). Page id is <part domain>.<control id>; part files live in pages/.',
                'pageCount': len(arts), 'bytes': total, 'parts': parts})
    print('controls: %d pages in %d part files, %.0f KB total, %d with aliases' % (len(arts), len(parts), total / 1024, sum(1 for x in arts if x['aliases'])))


if __name__ == '__main__':
    main()

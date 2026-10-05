"""enc_ui_fix.py - one place that keeps Encyclopedia wording equal to the labels the live app really shows (UI audit 2026-10-05).

The audit (_easy_claude_work/ui_audit/, report docs/handoff_reports/ENC_UI_AUDIT.md) opened every panel of the running app and compared each
label an article uses with the DOM. The wording below was wrong in thousands of articles. Fixing it per article by hand would be undone the next
time a generator runs, so every generator calls fix_tree() on its articles before writing, and this CLI repairs files on disk:

    python scripts/ai_atlas/enc_ui_fix.py            # rewrite data/encyclopedia/**/*.json in place (atomic, idempotent), print counts
    python scripts/ai_atlas/enc_ui_fix.py --report   # count only

Never touches `aliases`, ids, sources, related, or figures/screens/reader files.  Only edit RULES; every rule cites what the app shows.
"""
import json, os, re, sys
from pathlib import Path

ENC = Path(__file__).resolve().parents[2] / 'data' / 'encyclopedia'
SKIP_KEYS = {'aliases', 'id', 'sources', 'related', 'actions', 'covers', 'figures', 'screens', 'thumb', 'swatch', 'domain', 'key'}
MASKADV = 'MASK > Advanced spec utilities'

# (pattern, replacement) applied in order to every string value.  Plain strings are literal, re.compile objects are regexes.
RULES = [
    # --- finish picker: the default (Classic) picker opens a big preview with Apply; USE IT exists only in the Live picker which has no switch ---
    ('Click it to stage it on the car, then click USE IT.', 'Click it to open the big preview, then click Apply.'),
    ('Click a result, then USE IT', 'Click a result, then click Apply in the preview'),
    ('a finish, check the On-Car Stage, then USE IT', 'a finish, check the big preview, then click Apply'),
    ('review on the On-Car Stage, then press "USE IT".', 'review in the big preview, then click Apply.'),
    ('put it on the On-Car Stage, then USE IT.', 'open its big preview, then click Apply.'),
    ('click through finishes with USE IT and look at the On-Car Stage.', 'click through finishes, look at the big preview and click Apply.'),
    ('a Color Lock button, Surprise me, an On-Car Stage and USE IT.', 'Surprise me, a Favorites filter and a big preview with an Apply button.'),
    (', Color Lock, Surprise me, See on paint, the On-Car Stage and USE IT.', ', Surprise me, See on paint and the big preview with its Apply button.'),
    ('rolls a high-ranked finish onto the On-Car Stage; confirm with Enter / click', 'rolls a high-ranked finish into the picker preview; click Apply to keep it'),
    ('Puts a highly ranked finish on the stage.', 'Opens a highly ranked finish in the big preview.'),
    ('Applies the staged finish.', 'Applies the finish shown in the big preview (the Apply button).'),
    ('Shows the search box, chips and On-Car Stage you use to browse a shelf.', 'Shows the search box and chips you use to browse a shelf.'),
    ('Find it in Pro > Base Material picker > On-Car Stage.', 'Find it in the Live picker (its On-Car Stage). The current build has no switch for the Live picker, so you will not see this; the default picker uses its Apply button instead.'),
    ('Works together with the USE IT control.', "Works together with the Live picker's USE IT control (the default picker uses its Apply button)."),
    ('The right column has the FINISHES and LAYERS tabs.', 'The right column holds the layer list.'),
    # --- AI: the button is "AI" (bottom right) and the panel is titled "AI copilot" ---
    ('Open the Shokker AI helper and ask for it by name', 'Open the AI copilot (the ✦ AI button, bottom right) and ask for it by name'),
    ('Shokker AI helper', 'AI copilot'),
    ('Shokker AI panel', 'AI copilot panel'),
    (re.compile(r'\bthe AI helper\b'), 'the AI copilot'),
    (re.compile(r'\bThe AI helper\b'), 'The AI copilot'),
    (re.compile(r'\bAI helper\b'), 'AI copilot'),
    (re.compile(r'\bthe Shokker AI\b'), 'the AI copilot'),
    (re.compile(r'\bThe Shokker AI\b'), 'The AI copilot'),
    (re.compile(r'Shokker AI'), 'AI copilot'),
    # --- layers: there is no LAYERS tab in the visible window; the right column is a layer list (buttons Open Layered, + Layer, Actions, filter box) ---
    ('Pro > right column > LAYERS tab', 'Pro > right column > layer list'),
    ('Right column > LAYERS tab', 'Right column > layer list'),
    ('right column > LAYERS tab', 'right column > layer list'),
    ('Right column > tabs. LAYERS tab:', 'Right column. Layer list:'),
    ('Pro > LAYERS >', 'Pro > right column > layer list >'),
    ('Pro > LAYERS tab', 'Pro > right column > layer list'),
    ('Open the LAYERS tab', 'Open the layer list (right column)'),
    ('Open the Layers tab', 'Look at the layer list (right column)'),
    (re.compile(r'\bthe (?:LAYERS|Layers) tab\b'), 'the layer list'),
    (re.compile(r'\bThe (?:LAYERS|Layers) tab\b'), 'The layer list'),
    (re.compile(r'(?<=: )(?:LAYERS|Layers) tab\b'), 'layer list'),
    (re.compile(r'^(?:LAYERS|Layers) tab\b'), 'Layer list'),
    (re.compile(r'\b(?:LAYERS|Layers) tab\b'), 'layer list'),
    # --- FINISHES tab: present in the HTML but hidden in the window layout; the library opens from the BASE MATERIAL box ---
    ('Click the FINISHES tab on the right (full-screen library).', 'Click the BASE MATERIAL box ("Click to choose a base") to open the finish library.'),
    ('give each zone a finish from the FINISHES tab.', 'give each zone a finish from the BASE MATERIAL box.'),
    ('Right column > tabs. FINISHES tab: opens the full-screen finish library.', 'Right column. A FINISHES tab exists in the page but is not shown in the current window layout; the same library opens from the BASE MATERIAL box.'),
    ('FINISHES tab: opens the full-screen finish library', 'FINISHES tab (not shown in the current window layout; use the BASE MATERIAL box instead): opens the full-screen finish library'),
    # --- Material Sampler window: the menu is labelled "Sample area" (not "Sample mode") and the slider "Material tolerance" ---
    ('Sample modes are Point, 3 by 3 Median and 5 by 5 Median', 'The Sample area menu offers Point, 3 by 3 Median and 5 by 5 Median'),
    ('Sample mode', 'Sample area'),
    # --- spec tools: the four helpers live under MASK > Advanced spec utilities (button labels end with an ellipsis); there is no SPEC TOOLS menu ---
    ('HISTORY, SELECT, RETOUCH, MASK, SPEC TOOLS, TRANSFORM and ADJUST', 'HISTORY, SELECT, RETOUCH, MASK, TRANSFORM and ADJUST'),
    ('Pro > top toolbar > Spec Tools >', 'Pro > top toolbar > ' + MASKADV + ' >'),
    ('Pro > Spec Tools >', 'Pro > top toolbar > ' + MASKADV + ' >'),
    ('Top toolbar > SPEC TOOLS >', 'Top toolbar > ' + MASKADV + ' >'),
    ('Open the Spec Tools menu and choose', 'Open ' + MASKADV + ' and choose'),
    ('Open Spec Tools and choose', 'Open ' + MASKADV + ' and choose'),
    ('Open SPEC TOOLS and choose', 'Open ' + MASKADV + ' and choose'),
    ('Open SPEC TOOLS then Material Sampler', 'Open ' + MASKADV + ', then Material Sampler'),
    ('Open SPEC TOOLS in the top bar.', 'Open the MASK menu in the top bar, then Advanced spec utilities.'),
    ('Click SPEC TOOLS in the top bar.', 'Click MASK in the top bar, then Advanced spec utilities.'),
    ('in the same Spec Tools menu', 'in the same Advanced spec utilities list'),
    ('SPEC TOOLS has three power tools', MASKADV + ' has power tools'),
    ('The SPEC TOOLS menu opens four helpers', MASKADV + ' opens four helpers'),
    ('Where is the Spec Tools menu?', 'Where are the spec tools (Decal Rescue Kit, Lighting Mask, Material Sampler, Range Remapper)?'),
    ('SPEC TOOLS in the main app', 'Spec tools in the main app (' + MASKADV + ')'),
    ('SPEC TOOLS menu: ', 'Advanced spec utilities (MASK menu): '),
    ('Transform (Spec Tools)', 'Transform'),
    (re.compile(r'\bSPEC TOOLS\b|\bSpec Tools\b(?: menu)?'), MASKADV),
]

_SELF_FIX = re.compile(r'(MASK > Advanced spec utilities)( > Advanced spec utilities)+')


def fix_text(s):
    if not isinstance(s, str) or not s:
        return s
    o = s
    for a, b in RULES:
        if isinstance(a, str):
            if a in s: s = s.replace(a, b)
        else:
            s = a.sub(b, s)
    s = _SELF_FIX.sub(r'\1', s)
    return s


def fix_tree(o, key=None):
    """Return o with every user-facing string fixed (dict keys of example `settings` too). In-place for dicts/lists."""
    if isinstance(o, str):
        return fix_text(o)
    if isinstance(o, list):
        for i, x in enumerate(o): o[i] = fix_tree(x)
        return o
    if isinstance(o, dict):
        if o.get('label') == 'USE IT' and o.get('inv') == 'swatchStageUseBtn' and 'Apply button' in str(fix_text(o.get('effect', ''))):
            o['label'] = 'Apply'
        for k in list(o):
            if k in SKIP_KEYS: continue
            o[k] = fix_tree(o[k], k)
            if key == 'settings':
                nk = fix_text(k)
                if nk != k: o[nk] = o.pop(k)
        # `settings` dicts keep their order stable enough for display; keys renamed above
        if key is None and 'settings' in o and isinstance(o['settings'], dict):
            s = o['settings']
            for k in list(s):
                nk = fix_text(k)
                if nk != k: s[nk] = s.pop(k)
            if 'Sample area' in s and 'Tolerance' in s: s['Material tolerance'] = s.pop('Tolerance')
        return o
    return o


def fix_articles(arts):
    for a in arts: fix_tree(a)
    return arts


def _dump(d, fmt):
    NL = '\n'
    if fmt == 'i1': return json.dumps(d, ensure_ascii=False, indent=1) + NL
    if fmt == 'i1nn': return json.dumps(d, ensure_ascii=False, indent=1)
    if fmt == 'i2': return json.dumps(d, ensure_ascii=False, indent=2) + NL
    if fmt == 'c': return json.dumps(d, ensure_ascii=False, separators=(',', ':')) + NL
    if fmt == 'cnn': return json.dumps(d, ensure_ascii=False, separators=(',', ':'))
    head = {k: v for k, v in d.items() if k != 'articles'}
    body = (',' + NL).join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in d['articles'])
    if fmt == 'ln':   # generators' layout: head, then one compact article per line
        return json.dumps(head, ensure_ascii=False)[:-1] + ',"articles":[' + NL + body + NL + ']}' + NL
    if fmt == 'ln2':
        return json.dumps(head, ensure_ascii=False, separators=(',', ':'))[:-1] + ',"articles":[' + NL + body + NL + ']}' + NL
    return None
FMTS = ['i1', 'i1nn', 'i2', 'c', 'cnn', 'ln', 'ln2']


def main():
    report = '--report' in sys.argv
    files = changed = odd = 0
    for p in sorted(ENC.rglob('*.json')):
        rel = p.relative_to(ENC).parts
        if rel[0] in ('reader', 'figures', 'screens') or p.name.startswith('_') or p.name in ('figures.json', 'screens.json', 'cars.json', 'preview_render.json'):
            continue
        raw = p.read_text(encoding='utf-8')
        try: d = json.loads(raw)
        except Exception: continue
        if not isinstance(d, dict) or not isinstance(d.get('articles'), list): continue
        fmt = next((f for f in FMTS if _dump(d, f) == raw.replace('\r\n', '\n')), None)
        before = json.dumps(d['articles'], ensure_ascii=False, sort_keys=True)
        fix_articles(d['articles'])
        files += 1
        if before != json.dumps(d['articles'], ensure_ascii=False, sort_keys=True):
            changed += 1
            if fmt is None:
                odd += 1; print('  layout not round-trippable, written as indent=1:', p.name); fmt = 'i1'
            if not report:
                tmp = p.with_suffix('.json.tmp')
                tmp.write_text(_dump(d, fmt), encoding='utf-8', newline='\n')
                os.replace(tmp, p)
    print('enc_ui_fix: %d files read, %d %s (%d odd layouts)' % (files, changed, 'would change' if report else 'rewritten', odd))


if __name__ == '__main__':
    main()

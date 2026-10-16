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
    # --- ENC-GEN 2026-10-10: spec-channel teaching must carry the floors the renderer applies (iron rules, engine/core.py + compose.py):
    #     blue 0-15 = NO clearcoat (16 = strongest, 255 = dull); roughness under 15 is lifted to 15 unless the metal is chrome-tier (240+).
    #     "low / dark blue = strong coat" was wrong below 16; "black = gloss" was wrong too (true black = coat off, normal gloss = dark green-black 0,30,16). ---
    ('green is roughness (0 is a mirror), blue is clearcoat (16 is the glossiest, higher is duller) and alpha is the specular mask',
     'green is roughness (0 is a mirror, but only chrome-tier metal, about 240 and up, can go under 15), blue is clearcoat (16 is the strongest, 0 to 15 means none, higher is duller) and alpha is the specular mask'),
    # support.flat_or_shiny summary must stay within the gate's 330 chars / 2 sentences: keep the 0-15 caveat, move the rest to the FAQ answer
    ('green is roughness (0 is a mirror) and blue is clearcoat (16 is the glossiest, higher is duller). No shine at all in iRacing usually means car_spec_<ID>.tga is missing or old in the car folder (render, then Ctrl+R to reload); else check the spec views and change the finish or sliders.',
     'green is roughness (0 is a mirror on chrome-tier metal, 15 at least otherwise), blue is clearcoat (16 is the glossiest, 0 to 15 is none, higher is duller). No shine at all in iRacing usually means car_spec_<ID>.tga is missing or old in the car folder (render, then Ctrl+R to reload).'),
    ('green is roughness (0 is a mirror, but only chrome-tier metal, about 240 and up, can go under 15) and blue is clearcoat (16 is the glossiest, 0 to 15 means none, higher is duller). No shine at all in iRacing usually means car_spec_<ID>.tga is missing or old in the car folder (render, then Ctrl+R to reload); else check the spec views and change the finish or sliders.',
     'green is roughness (0 is a mirror on chrome-tier metal, 15 at least otherwise), blue is clearcoat (16 is the glossiest, 0 to 15 is none, higher is duller). No shine at all in iRacing usually means car_spec_<ID>.tga is missing or old in the car folder (render, then Ctrl+R to reload).'),
    ('green is roughness (0 is a mirror) and blue is clearcoat (16 is the glossiest, 0 to 15 is none, higher is duller). No shine at all in iRacing usually means car_spec_<ID>.tga is missing or old in the car folder (render, then Ctrl+R to reload).',
     'green is roughness (0 is a mirror on chrome-tier metal, 15 at least otherwise), blue is clearcoat (16 is the glossiest, 0 to 15 is none, higher is duller). No shine at all in iRacing usually means car_spec_<ID>.tga is missing or old in the car folder (render, then Ctrl+R to reload).'),
    ('green is roughness (0 is a mirror) and blue is clearcoat (16 is the glossiest, higher is duller)',
     'green is roughness (0 is a mirror, but only chrome-tier metal, about 240 and up, can go under 15) and blue is clearcoat (16 is the glossiest, 0 to 15 means none, higher is duller)'),
    ('blue is clearcoat (16 is the glossiest, higher is duller)', 'blue is clearcoat (16 is the glossiest, 0 to 15 means none, higher is duller)'),
    ('green is roughness (0 is a mirror), blue is clearcoat (0 to 15 is none, 16 is maximum gloss, 255 is dull) and alpha is the mask',
     'green is roughness (0 is a mirror, but only chrome-tier metal, about 240 and up, can go under 15), blue is clearcoat (0 to 15 is none, 16 is maximum gloss, 255 is dull) and alpha is the mask'),
    ('green is roughness (0 is a mirror), blue is clearcoat (16 is the glossiest) and alpha is a lighting mask',
     'green is roughness (0 is a mirror, but only chrome-tier metal, about 240 and up, can go under 15), blue is clearcoat (16 is the glossiest, 0 to 15 means none) and alpha is a lighting mask'),
    ('low blue values are a strong clearcoat (16 is maximum gloss in the game) and high blue is dull',
     'a blue value of 16 is the strongest clearcoat in the game, 0 to 15 means no clearcoat at all, and higher blue is duller'),
    ('Low blue means strong clearcoat; 16 is maximum gloss and high values are dull.',
     'Blue 16 is the strongest clearcoat, 0 to 15 means no clearcoat, and higher values are duller.'),
    ('Dull clearcoat. Low blue is glossier.', 'Dull clearcoat. Blue near 16 is the glossiest, 0 to 15 means no clearcoat, and higher is duller.'),
    ('darker blue means a glassier clearcoat', 'blue closest to 16 (very dark, but not black) means the glassiest clearcoat, and black means none'),
    ('Black in G ROUGH is a mirror; dark in B COAT is a glossy coat.',
     'Black in G ROUGH is a mirror (only chrome-tier metal can really go that low); a very dark but not black B COAT (about 16) is the glossiest coat, and pure black there means no coat.'),
    ('Black does not mean empty. It means smooth, non-metal, glossy coat.',
     'Black does not mean empty or glossy: true black (0, 0, 0) has the coat off. Normal gloss is a dark green-black such as 0, 30, 16.'),
    ('The strongest coat is a dark blue channel. Check B COAT.',
     'The strongest coat is a blue of 16, a very dark blue but not black. Blue 0 to 15 means no coat. Check B COAT.'),
    ('red means metal, teal means matte and black means gloss', 'red means metal, teal means matte and dark green-black means gloss'),
    ('On the blue channel 16 is the glossiest and bigger numbers get duller.',
     'On the blue channel 16 is the glossiest, 0 to 15 means no clearcoat, and bigger numbers get duller.'),
    ('Blue channel: Clearcoat (16 = max gloss, 255 = dull).', 'Blue channel: Clearcoat (16 = max gloss, 0-15 = none, 255 = dull).'),
    # --- ENC-GEN: the buttons on a layer card are labelled "More > ..." (no "Now" prefix); "Click to choose a base" shows only on an EMPTY zone ---
    ('Now More > ', 'More > '),
    ('Click the BASE MATERIAL box ("Click to choose a base") to open the finish library.',
     'Click the Base Material box under BASE (it shows "Click to choose a base" on an empty zone) to open the finish library.'),
]

# --- ENC-FIX 2026-10-10: the 9 corrections the APP-IQ exam found (rules + code anchors live in enc_fix_rules.py) ---
def _load_encfix_rules():
    import importlib.util
    spec = importlib.util.spec_from_file_location('enc_fix_rules', Path(__file__).with_name('enc_fix_rules.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return list(mod.ENCFIX_RULES)


RULES += _load_encfix_rules()

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

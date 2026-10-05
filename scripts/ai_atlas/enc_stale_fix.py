# -*- coding: utf-8 -*-
"""enc_stale_fix.py - removes STALE REFERENCES from the encyclopedia (2026-10-05).  Companion to enc_stale_refs_check.py (the gate) and to
enc_wear_fix.py (which did the Season pages + the Wear article).

WHAT IT FIXES (the check script finds them, this script rewrites them):
  1. FLEET batch control pages (Add Car, Render All Cars).  Fleet mode is RETIRED exactly like Season mode:
       paint-booth-5-api-render.js:2356 toggleFleetMode() and :2411 doFleetRender() only call _showRetiredBatchModeToast('Fleet mode') and return;
       paint-booth-v2.html:2517 #fleetPanel style="display: none;" holds the two buttons.  The pages now say so, point at the single-car RENDER,
       and lose their Do-it action.
  2. HIDDEN FINISHES: finishes in scripts/ai_atlas/enc_picker_hidden.json are not in the Base Material picker, so "pick Candy Gold" sends a
     buyer to something they cannot find.  Each is swapped for a VISIBLE equivalent whose look was checked against paint-booth-0-finish-data.js
     (line numbers in SWAPS below), or the text says "ask the Shokker AI helper for it by name".
  3. Do-it ACTION ids that apply a hidden finish are remapped to the visible twin (ACTION_MAP), de-duplicated in order.
  4. "season ramp" wording in the Weathered article (Season mode is retired).

HOW: text is replaced by exact long substrings (PAIRS) and by article-scoped leaf edits (LEAF); both are idempotent.  The same substrings are
patched in the generator sources (scripts/ai_atlas/enc_*.py, enc_C_drafts/*.py) and in data/encyclopedia/_drafts/*, so a regenerate does not bring
the stale text back.  build_encyclopedia.py runs this as a post-pass right after enc_wear_fix.py.

Run (idempotent):  python scripts/ai_atlas/enc_stale_fix.py [--write]      (no --write = dry run, prints counts)"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ENC = os.path.join(ROOT, 'data', 'encyclopedia')

API = 'paint-booth-5-api-render.js'
FD = 'paint-booth-0-finish-data.js'

# ---- 1. Fleet pages -------------------------------------------------------------------------------------------------------------------------
FLEET_SOURCES = [API + ':2352', API + ':2356', API + ':2411', 'paint-booth-v2.html:2517']
FLEET_PAGES = {
    'controls_zones_1.pro.zones.add_car': dict(
        summary='Add Car belonged to the Fleet batch panel, which is retired in this build. It cannot be reached.',
        what='The Fleet batch panel stays hidden and nothing in the Pro window opens it, so Add Car cannot be clicked. Paint one car at a time: load the car, build the zones and press RENDER.',
        when=[],
        how=['Skip it: it cannot be used in this build.', 'Render each car on its own with the normal RENDER button.'],
        controls=[{'label': 'Add Car', 'range': '', 'default': '', 'effect': 'Retired: it added a car to the Fleet batch.', 'inv': 'pro.zones.add_car'}],
        tips=['Save a zone setup (zone presets) to reuse the same look on the next car.'],
        related=['zones.card_controls'], actions=[]),
    'controls_zones_1.btnFleetRender': dict(
        summary='Render All Cars belonged to the Fleet batch panel, which is retired in this build. It only shows a disabled message.',
        what='The Fleet batch panel stays hidden, and its Render All Cars action only shows a message that Fleet mode is disabled in this booth build. Render each car with a normal RENDER instead.',
        when=[],
        how=['Skip it: it cannot be used in this build.', 'Load one car, press RENDER, then load the next car.'],
        controls=[{'label': 'Render All Cars', 'range': '', 'default': '', 'effect': 'Retired: it rendered every car in the Fleet batch.', 'inv': 'btnFleetRender'}],
        tips=['Save a zone setup (zone presets) to reuse the same look on the next car.'],
        related=['zones.card_controls'], actions=[]),
}

# ---- 2. Hidden finish -> visible twin (evidence = finish-data line + the exact spec numbers) -------------------------------------------------
SWAPS = {
    'base::f_soft_matte -> base::matte':   FD + ':791 Matte 0/200/158, identical to the hidden Soft Matte 0/200/158',
    'base::f_clear_satin -> base::satin':  FD + ':1001 Satin 0/95/69, identical to the hidden Clear Satin 0/95/69',
    'base::f_soft_gloss -> base::gloss':   FD + ':724 Gloss 0/30/16, identical to the hidden Soft Gloss 0/30/16',
    'base::candy -> base::f_candy':        FD + ':714 Candy (Foundation) 200/15/16, polished metal under a colour you pick',
    'Carbon Base/Carbon Fiber -> Hardware: Carbon Handguard': FD + ':442 twill weave under resin, high gloss (glossy carbon)',
    'Carbon Satin -> Carbon Twill Weave':  FD + ':5356 materials2_carbon, true 2/2 twill, semi-matte (the quieter carbon)',
    'Metal Flake -> Chunky Metalflake':    FD + ':1101 Foundation EFX, big metalflake chips (mirror, high metal)',
    'Supernova Flake / Starlight Mica Resin -> Holo Flake / Micro Glitter': FD + ':1097 Holo Flake, efx_micro_glitter in the Foundation EFX shelf',
    'Pearl (hidden) -> Pearl (Foundation)': 'base::f_pearl is the visible Pearl 100/40/16',
    'Sapphire/Ruby/Emerald/Amber Glass -> Wet Look + a colour':  FD + ':1077 Wet Look 0/15/16, same spec as the gem glasses 0/17/16 (colour is the only difference)',
    'Cathedral Glass -> Cathedral Veil':   FD + ':1084 Foundation EFX, leaded glass panes in your colour',
    'Smoked Glass -> Shag: Smoked Glass':  FD + ':268 bronze-tinted glass, high gloss',
    'Desert Worn -> Sun Faded':            FD + ':1107 Foundation EFX, broad bleached zones and a dust-pitted skin (Desert Worn is sun-bleached too)',
    'Rally Mud -> Extreme: BMX Dirt':      FD + ':380 compacted clay and embedded grains, semi-matte (dirt spray)',
    'Race Worn -> Hardware: Battle Worn':  FD + ':441',
    'Firefly Glow -> Firefly Lantern':     FD + ':663 Iridescent Insects, light-organ modules (the hidden one is lantern zones on a dark shell)',
    'Bioluminescent -> Bioluminescent Wave': FD + ':3948 ocean bioluminescence with electric-blue wave glow',
}

# long exact substrings, applied to every string of every article (final JSON, drafts) and to the generator sources
PAIRS = [
    # carbon_hood
    ('choose Carbon Base (raw carbon, the weave is the finish), or the plain Carbon Fiber base and add the weave as a pattern.',
     'choose Hardware: Carbon Handguard (a glossy twill weave under resin) or Carbon Twill Weave (a semi-matte 2 by 2 twill), or a plain dark base such as Gloss and add the weave as a pattern.'),
    ('Carbon Satin gives the OEM stealth look; Carbon Base is raw and glossy.',
     'Carbon Twill Weave gives a quieter, semi-matte look; Hardware: Carbon Handguard is glossy under resin.'),
    ('Carbon Base is raw and glossy; the weave is the finish. Carbon Satin gives the OEM stealth look. Or use',
     'Hardware: Carbon Handguard is a glossy twill weave under resin and Carbon Twill Weave is semi-matte; the weave is the finish. Or use'),
    ('Either: a Carbon Base carries its own weave; a dark base plus the pattern gives control.',
     'Either: a carbon base such as Carbon Twill Weave carries its own weave; a dark base plus the pattern gives control.'),
    # candy
    ('Candy (or Candy on the Foundation Bases shelf for the plain version; named candies such as Candy Gold, Candy Lime and Candy Aqua also exist).',
     'Candy on the Foundation Bases shelf (a polished metallic under the colour you pick, so gold, lime or aqua candy is just a colour choice; Van: Candy Apple is a ready-made candy over silver).'),
    ('Named candies such as Candy Gold, Candy Lime and Candy Aqua also exist.',
     'For a named candy colour such as gold, lime or aqua, pick Candy and choose that colour yourself.'),
    # flake_pearl
    ('Metal Flake (heavy visible flake), Supernova Flake, Starlight Mica Resin, or Pearl / Pearl (Foundation) for a softer sheen.',
     'Chunky Metalflake (heavy visible flake), Holo Flake (rainbow flake) or Micro Glitter (fine sparkle) from the Foundation EFX shelf, or Pearl (Foundation) for a softer sheen.'),
    # wet_glass
    ('For glass looks choose a gem or art glass finish such as Sapphire Glass, Emerald Glass, Cathedral Glass or Smoked Glass, and keep roughness low and the coat at 16.',
     'For glass looks choose Cathedral Veil, Shag: Smoked Glass or Glass Flake, or put Wet Look over a deep blue, red, green or amber colour, and keep the coat at 16.'),
    # (the summary is capped at 2 sentences / 300 chars by enc_v2_test; the ask-by-name hint lives in TIPS_ADD)
    ('For glass looks choose Cathedral Veil (leaded glass panes in your colour), Shag: Smoked Glass or Glass Flake, or put Wet Look over a deep blue, red, green or amber colour for a gem-glass look, and keep roughness low and the coat at 16. The old named gem-glass finishes are not in the picker: ask the Shokker AI helper for one by name.',
     'For glass looks choose Cathedral Veil, Shag: Smoked Glass or Glass Flake, or put Wet Look over a deep blue, red, green or amber colour, and keep the coat at 16.'),
    ('for glass pick Sapphire Glass, Ruby Glass, Emerald Glass, Amber Glass, Cathedral Glass, Smoked Glass or Milk Glass.',
     'for glass pick Cathedral Veil (leaded glass panes), Shag: Smoked Glass (bronze-tinted) or Glass Flake (glass shards), or choose Wet Look and set a deep blue, red, green or amber colour for a gem look.'),
    ('Glass finishes add transparent colour on top: Sapphire Glass, Ruby Glass, Emerald Glass, Amber Glass, Cathedral Glass, Smoked Glass or Milk Glass. They bring their own colour (recolour with Hue Shift). They are',
     'Glass looks put clear colour over the paint: Cathedral Veil lays leaded glass panes in your colour, Shag: Smoked Glass is a bronze tint and Glass Flake suspends glass shards in clear; for a plain gem glass use Wet Look and pick the colour yourself. They are'),
    # weathered
    ('such as Desert Worn, Hardware: Battle Worn or Die-Back Patina,', 'such as Sun Faded, Hardware: Battle Worn or Die-Back Patina,'),
    ('Under BASE pick Desert Worn (sun-bleached), Hardware', 'Under BASE pick Sun Faded (sun-bleached), Hardware'),
    ('Wear from a season ramp roughens the surface', 'Engine wear roughens the surface'),
    # glow_look
    ('Bioluminescent (a soft deep-sea glow) and Firefly Glow (yellow-green lantern zones on a dark shell)',
     'Bioluminescent Wave (ocean bioluminescence with electric-blue wave glow) and Firefly Lantern (light-organ modules that glow like a firefly)'),
    ('Bioluminescent or Firefly Glow', 'Bioluminescent Wave or Firefly Lantern'),
    ('Bioluminescent and Firefly Glow.', 'Bioluminescent Wave and Firefly Lantern.'),
    # crash_damage
    ('Hardware: Battle Worn, Desert Worn, Die-Back Patina or Rally Mud', 'Hardware: Battle Worn, Sun Faded, Die-Back Patina or Extreme: BMX Dirt'),
    ('Hardware: Battle Worn, Desert Worn, Die-Back Patina and Rally Mud', 'Hardware: Battle Worn, Sun Faded, Die-Back Patina and Extreme: BMX Dirt'),
    ('search worn, patina or mud;', 'search worn, patina or dirt;'),
    # nature_tactical_cyberpunk / spec
    ('Weathered Paint and Race Worn.', 'Weathered Paint and Hardware: Battle Worn.'),
    ('Chrome is roughness 2, Mercury is 3, Candy Chrome is 4.', 'Foundation Chrome is roughness 2.'),
]

# article-scoped leaf edits: (article id, path, old, new)
LEAF = [
    ('recipes.carbon_hood', 'examples.1.settings.BASE', 'Carbon Satin', 'Carbon Twill Weave'),
    ('recipes.carbon_hood', 'examples.1.result', 'A subtle satin weave.', 'A subtle semi-matte weave.'),
    ('recipes.wet_glass', 'examples.1.title', 'Sapphire glass', 'Gem-blue glass'),
    ('recipes.wet_glass', 'examples.1.settings.Base Material', 'Sapphire Glass', 'Wet Look'),
    ('recipes.wet_glass', 'examples.1.settings.BASE COLOR', "Use finish's own color", 'A deep sapphire blue'),
    ('recipes.wet_glass', 'examples.1.result', 'A transparent blue gem look.', 'A deep, wet blue gem gloss.'),
    ('recipes.weathered', 'examples.1.settings.Base Material', 'Desert Worn', 'Sun Faded'),
    ('workflows.crash_damage', 'examples.1.settings.Base Material', 'Rally Mud', 'Extreme: BMX Dirt'),
    ('workflows.crash_damage', 'examples.1.goal', 'Muddy lower body', 'Dirty lower body'),
    ('workflows.crash_damage', 'examples.1.result', 'Mud spray on the lower body, clean above.', 'Dirt on the lower body, clean above.'),
    ('workflows.crash_damage', 'mistakes.1.symptom', 'The whole car looks muddy.', 'The whole car looks dirty.'),
    ('workflows.crash_damage', 'mistakes.1.cause', 'Rally Mud is on the body zone.', 'Extreme: BMX Dirt is on the body zone.'),
]

# tips appended (once) to an article: the named gem-glass finishes are hidden, so say how to get them
TIPS_ADD = {'recipes.wet_glass': ['The named gem-glass finishes (the sapphire, ruby, emerald and amber glasses) are not in the Base Material picker: ask the Shokker AI helper for one by name.']}

# Do-it action ids: hidden finish -> visible twin (None = drop; duplicates removed in order)
ACTION_MAP = {
    'base::f_soft_matte': 'base::matte', 'base::f_clear_satin': 'base::satin', 'base::f_soft_gloss': 'base::gloss',
    'base::candy': 'base::f_candy', 'base::candy_gold': 'base::f_candy', 'base::candy_aqua': 'base::f_candy', 'base::candy_lime': 'base::f_candy',
    'base::carbon_base': 'base::tac_carbon_handguard', 'base::f_carbon_fiber': 'base::tac_carbon_handguard', 'base::carbon_satin': 'monolithic::materials2_carbon',
    'base::metal_flake_base': 'base::efx_chunky_flake', 'base::pearl': 'base::f_pearl',
    'base::sapphire_glass': 'base::wet_look', 'base::cathedral_glass': 'base::efx_cathedral_veil', 'base::smoked_glass': 'base::fo_smoked_glass',
    'base::desert_worn': 'base::efx_sun_faded',
}


def _load(p):
    with open(p, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


def _dump_atomic(p, obj, **kw):
    tmp = p + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(json.dumps(obj, ensure_ascii=False, **kw).encode('utf-8'))
    os.replace(tmp, p)


def _walk(o, st):
    """Replace PAIRS inside every string; returns the new object and counts the replacements in st['n']."""
    if isinstance(o, str):
        s = o
        for old, new in PAIRS:
            if old in s:
                s = s.replace(old, new)
        if s != o:
            st['n'] += 1
        return s
    if isinstance(o, list):
        return [_walk(x, st) for x in o]
    if isinstance(o, dict):
        return {k: _walk(v, st) for k, v in o.items()}
    return o


def _get_parent(a, path):
    keys = path.split('.')
    o = a
    for k in keys[:-1]:
        o = o[int(k)] if k.isdigit() else o[k]
    return o, keys[-1]


def _leaf(a, st):
    for aid, path, old, new in LEAF:
        if a.get('id') != aid:
            continue
        try:
            par, k = _get_parent(a, path)
            key = int(k) if k.isdigit() else k
            cur = par[key]
        except (KeyError, IndexError, TypeError):
            continue
        if cur == old:
            par[key] = new
            st['n'] += 1


def _actions(a, st):
    acts = a.get('actions')
    if not isinstance(acts, list) or not any(isinstance(x, dict) and x.get('id') in ACTION_MAP for x in acts):
        return
    out, seen = [], set()
    for x in acts:
        if isinstance(x, dict) and x.get('id') in ACTION_MAP:
            x = dict(x)
            x['id'] = ACTION_MAP[x['id']]
        key = json.dumps(x, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    a['actions'] = out
    st['n'] += 1


def patch_article(a, st):
    """In place; a is one article / page dict."""
    if a.get('id') in FLEET_PAGES:
        for k, v in FLEET_PAGES[a['id']].items():
            nv = json.loads(json.dumps(v))
            if a.get(k) != nv:
                a[k] = nv
                st['n'] += 1
        a['sources'] = list(FLEET_SOURCES)
    new = _walk(a, st)
    a.clear()
    a.update(new)
    _leaf(a, st)
    for t in TIPS_ADD.get(a.get('id'), []):
        if isinstance(a.get('tips'), list) and t not in a['tips']:
            a['tips'].append(t)
            st['n'] += 1
    if not re.match(r'(finish|pattern|specpat)_', a.get('id', '')):     # a hidden finish's OWN page may keep its Do-it: it says "ask the AI copilot by name"
        _actions(a, st)


def _final_files():
    fs = sorted(glob.glob(os.path.join(ENC, '*.json')) + glob.glob(os.path.join(ENC, 'pages', '*.json')))
    return [f for f in fs if os.path.basename(f) not in ('_index.json',)]


def apply(write=True):
    changed, total = [], 0
    for p in _final_files():
        try:
            d = _load(p)
        except Exception:
            continue
        arts = d.get('articles') if isinstance(d, dict) else d
        if not isinstance(arts, list):
            continue
        st = {'n': 0}
        for a in arts:
            if isinstance(a, dict):
                patch_article(a, st)
        if st['n']:
            total += st['n']
            changed.append('%s (%d)' % (os.path.relpath(p, ENC), st['n']))
            if write:
                _dump_atomic(p, d, indent=1) if _indent(p) else _dump_atomic(p, d)
    # drafts: jsonl (one article per line) and json (id -> fields); only the PAIRS text matters there
    for p in sorted(glob.glob(os.path.join(ENC, '_drafts', '*'))):
        if not p.endswith(('.json', '.jsonl')):
            continue
        raw = open(p, 'rb').read().decode('utf-8')
        new = raw
        for old, nw in PAIRS:
            new = new.replace(old, nw)
            # json-escaped variants (— etc. never occur in the PAIRS, but quotes might)
            new = new.replace(old.replace('"', '\\"'), nw.replace('"', '\\"'))
        if new != raw:
            changed.append('_drafts/' + os.path.basename(p))
            if write:
                tmp = p + '.tmp'
                open(tmp, 'wb').write(new.encode('utf-8'))
                os.replace(tmp, p)
    # generator sources
    srcs = sorted(glob.glob(os.path.join(HERE, 'enc_*.py')) + glob.glob(os.path.join(HERE, 'enc_C_drafts', '*.py')) + glob.glob(os.path.join(HERE, 'encyclopedia_*.py')))
    for p in srcs:
        if os.path.basename(p) in ('enc_stale_fix.py', 'enc_stale_refs_check.py'):
            continue
        raw = open(p, 'rb').read().decode('utf-8')
        new = raw
        for old, nw in PAIRS:
            if old in new:
                new = new.replace(old, nw)
        if new != raw:
            changed.append('src:' + os.path.relpath(p, HERE))
            if write:
                crlf = '\r\n' in raw
                tmp = p + '.tmp'
                open(tmp, 'wb').write(new.encode('utf-8'))
                os.replace(tmp, p)
    return changed, total


_INDENT = {}


def _indent(p):
    """Keep each file's existing layout (indented or compact) so a diff stays small."""
    if p not in _INDENT:
        head = open(p, 'rb').read(400).decode('utf-8', 'ignore')
        _INDENT[p] = '\n ' in head
    return _INDENT[p]


if __name__ == '__main__':
    write = '--write' in sys.argv
    ch, n = apply(write)
    print('enc_stale_fix: %s %d edits in %d files%s' % ('wrote' if write else 'dry-run', n, len(ch), (' -> ' + ', '.join(ch[:14])) if ch else ''))

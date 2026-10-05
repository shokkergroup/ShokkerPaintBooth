# -*- coding: utf-8 -*-
"""enc_wear_fix.py - the CORRECT text for the Wear article (finishes.wear) and for the three retired Season-batch control pages (2026-10-05).

WHY: Season mode is RETIRED (toggleSeasonMode hides the panel; doSeasonRender only shows a 'disabled in this booth build' toast) and the Pro
window has no per-zone Wear slider, yet the article told buyers to open "Season set-up", click "+ Add Race", "Quick: Wear Ramp" and
"Render All Races". Single source of truth for the fixed text: enc_B_part6.py and enc_B_v3_finishes_b.py import WEAR_ADD / WEAR_V3 from here,
so a generator rebuild produces the same words.

Run (idempotent):  python scripts/ai_atlas/enc_wear_fix.py [--write]
  --write patches data/encyclopedia/finishes.json (finishes.wear), data/encyclopedia/pages/controls_zones_1.json (3 Season control pages) and the
  stale drafts (_drafts/finishes.jsonl, _drafts/finishes_v3.json). build_encyclopedia.py runs it as a post-pass, so the pages cannot regress.
Evidence (file:line) for every claim is in WEAR_ADD['sources'] / WEAR_V3['_sources'] and docs/handoff_reports/ENC_FACTCHECK.md."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ENC = os.path.join(ROOT, 'data', 'encyclopedia')

ENG = 'shokker_engine_v2.py'
ZONES = 'paint-booth-2-state-zones.js'
API = 'paint-booth-5-api-render.js'
FD = 'paint-booth-0-finish-data.js'

SOURCES = [
    API + ':2648',                 # toggleSeasonMode: hides the panel, shows the retired toast
    API + ':2352',                 # _showRetiredBatchModeToast text
    API + ':2706',                 # doSeasonRender: toast then return
    'paint-booth-v2.html:2534',    # seasonPanel style="display: none;" (no toggle button exists in the page)
    ZONES + ':12221',              # setZoneWear (0-100 clamp); no slider or button calls it
    API + ':738',                  # zone wear > 0 is sent to the engine as wear_level
    ENG + ':20467',                # engine per-zone wear step
    ENG + ':22944',                # apply_wear
    ENG + ':23013',
    ENG + ':23354-23380',
    ZONES + ':2098',               # Base Strength slider on the zone card
    'js/zones/zone-config-preset-controls.js:113',   # wear is saved with a zone setup
    FD + ':1107',                  # Sun Faded
    FD + ':152',                   # Die-Back Patina
    FD + ':441',                   # Hardware: Battle Worn
    FD + ':1104',                  # Surface Rust
    'js/spec-overlays/catalog-data.js:1244',   # Micro Chipping
    'js/spec-overlays/catalog-data.js:1169',   # Scuffed Enamel
    'mcp/server/tools.json:721',   # spb_edit_zone has base_strength, no wear
    'docs/handoff_reports/BUGFIX_2026-10-04.md:15',
]

WEAR_ADD = dict(
    title='Wear: scuffed and aged looks',
    summary='Wear is a stored per-zone value from 0 to 100 that the engine turns into chips, scratches and a duller clearcoat. This build has no Wear slider and Season mode is retired, so you get a worn look from a worn Base Material and Base Strength.',
    what='Wear is a number from 0 to 100 kept on each zone. When a zone has wear above 0, the render engine adds chips, scratches and a duller clearcoat to that zone. In this build nothing in the Pro window sets it: the zone card has no Wear slider, and the old Season set-up (add races, Quick: Wear Ramp, Render All Races) is retired. Its panel stays hidden and nothing opens it. To get a worn look today, pick a worn finish as the zone\'s Base Material, lower Base Strength so your own paint shows through, and add chip or scuff spec overlays.',
    when=['A race-worn, barn-find or sun-faded look', 'You wonder where the Wear slider and Season mode went'],
    how=['Make or pick the zone to age: Remaining on Car Paint, or APPLY AREA > Draw box on the lower body, front or roof.',
         'Under BASE press Base Material and search a worn finish: Sun Faded, Die-Back Patina, Hardware: Battle Worn or Surface Rust.',
         'Lower Base Strength to 50 to 70 so your own colours show through (0 is your paint, 100 is the full finish).',
         'For chips and scuffs open BASE > SPEC OVERLAYS and add Micro Chipping or Scuffed Enamel at Strength 30 to 40.',
         'Press RENDER and check at 100 percent zoom: wear should read as fine detail, not blotches.'],
    controls=[{'label': 'Base Strength', 'range': '0-100%', 'default': '100', 'effect': 'How much of the worn finish replaces your own paint.', 'inv': 'zone.base_strength'}],
    tips=['Sun Faded and Surface Rust are on the Foundation EFX shelf, Die-Back Patina on SHOKK WORKS and Hardware: Battle Worn on TACTICAL & FIELD, so searching by name is quickest.',
          'Desert Worn, Barn Find and Rally Mud exist in the catalogue but are not listed in the Base Material picker. Ask the Shokker AI helper for them by name.'],
    pitfalls=['High Base Strength with a heavy worn finish hides your own colours and fine detail.'],
    related=['finishes.nature_tactical_cyberpunk', 'finishes.base_colour_tuning', 'spec.overlays_stack', 'ideas.worn_patina'],
    actions=[{'do': 'finish', 'id': 'base::efx_sun_faded'}, {'do': 'finish', 'id': 'base::bth_die_back'}, {'do': 'finish', 'id': 'base::tac_battle_worn'},
             {'do': 'finish', 'id': 'base::efx_surface_rust'}, {'do': 'control', 'id': 'zone.base_strength'}],
    figures=[],
    covers=['zone.wear', 'cat.weathered_aged'],
    sources=SOURCES,
    aliases=['wear', 'weathering', 'worn paint', 'race worn', 'aging'])

WEAR_V3 = dict(
    level='intermediate',
    _sources=SOURCES,
    deep=[
        {'heading': 'What wear does, by level', 'body': 'These are the engine\'s values, whoever sets them. Wear runs 0 to 100. 0 is showroom fresh. About 25 is light track wear with micro-scratches. 50 is mid-season with visible scratches, rougher surfaces and chips. 75 is heavy use. 100 is a track-beaten veteran. Scratches are horizontal-biased: roughness goes up by as much as 60 times the wear fraction and metal goes down by as much as 30 times it. Wear also DULLS the clearcoat (the coat byte goes up toward 255, never toward the glossy end): on average a matte base goes from 153 at wear 0 to 176 at 50 and 198 at 100, a satin from 67 to 90 to 114, and a gloss from 16 to 39 to 63. Edges wear a little more. Above 20 percent, chips desaturate and slightly brighten damaged areas. Above 30 percent, edges where colours meet wear more, with extra roughness and metal loss.'},
        {'heading': 'How it is applied', 'body': 'The wear step runs once at the highest wear level among your zones and is blended per zone by that zone\'s level over the maximum, only where the zone owns the pixel. After wear the iron rules are applied again, so the result is always legal. The render engine also has an all-in-one export that takes one global wear level (helmet 20 lower, suit 40 lower), but the booth window has no control for it.'},
        {'heading': 'Where the controls went', 'body': 'A zone still stores a wear value, and the render path sends it to the engine whenever it is above 0. Zone setups save it. But the Pro window no longer has anything that sets it: the zone card shows Base Strength and no Wear slider. The Season panel (Add Race, Quick: Wear Ramp, Render All Races) is hidden and nothing opens it, and Render All Races only shows a message that Season mode is disabled in this booth build. The MCP zone-edit tool has Base Strength and Spec Strength but no wear option, and the Shokker AI helper has no wear setting in its edit code either.'},
        {'heading': 'The look you can get today', 'body': 'Pick the worn finish by the story you want. Sun Faded is broad bleached zones over a fine dust-pitted skin, an unevenly sun-bleached panel. Die-Back Patina is a dusty aged earth-tone surface of collapsed matte patches with faint glossy lips. Hardware: Battle Worn is a dark olive-brown surface with heavy speckled wear and pale chips. Surface Rust is rust blooming through the paint in spots. Lower Base Strength to keep your own colours, then add Micro Chipping or Scuffed Enamel from BASE > SPEC OVERLAYS for chips and scuffs.'},
        {'heading': 'Wear needs detail to hide', 'body': 'Fine finishes lose their detail under heavy wear, because chips and scratches cover it. Worn finishes already carry the damage, so a strong worn base needs few overlays.'},
    ],
    examples=[
        {'title': 'A car that gets dirtier across a season', 'goal': 'The same car at three stages of wear.',
         'settings': {'Stage 1': 'Sun Faded at Base Strength 30', 'Stage 2': 'Base Strength 50, Micro Chipping at Strength 30', 'Stage 3': 'Base Strength 70, Micro Chipping at Strength 40', 'Action': 'Press RENDER once per stage, one after another'},
         'result': 'Three separate renders from lightly dusty to heavily worn, each made by hand. There is no one-click batch of all stages.'},
        {'title': 'Worn lower body without a slider', 'goal': 'Track rash only on the sills.',
         'settings': {'Sill zone': 'Base Material: Hardware: Battle Worn, Base Strength 60', 'Spec overlay': 'Micro Chipping', 'Body zone': 'A clean Gloss base'},
         'result': 'Chips and wear on the sills with a clean body.'},
    ],
    combos=[{'with': 'spec.iron_rules', 'why': 'The engine re-applies the safe limits after its wear step.'},
            {'with': 'finishes.nature_tactical_cyberpunk', 'why': 'Worn finishes give the look without any slider.'},
            {'with': 'ideas.worn_patina', 'why': 'A full worn and patina recipe with rust and spec overlays.'}],
    faq=[
        {'q': 'Does wear affect numbers?', 'a': 'The decal protection step restores number and sponsor colours before wear runs.'},
        {'q': 'Why is there no Wear slider?', 'a': 'This build does not show one. Wear is still a stored zone value that the engine understands, but nothing in the window sets it. Use a worn Base Material and Base Strength.'},
        {'q': 'What happened to Season mode, Add Race and Quick: Wear Ramp?', 'a': 'They are retired. The Season panel is hidden and Render All Races only shows a disabled message. Render the car once per stage instead.'},
        {'q': 'Can the Shokker AI helper or MCP set wear?', 'a': 'No. The MCP zone-edit tool takes Base Strength and Spec Strength but no wear. Ask for a worn finish by name instead.'},
        {'q': 'Is wear random?', 'a': 'The engine uses a fixed seed, so the same wear looks the same each render.'},
    ],
    mistakes=[
        {'symptom': 'I cannot find a Wear slider or a Season set-up.', 'cause': 'This build has neither.', 'fix': 'Pick a worn Base Material, lower Base Strength and add a chip overlay.'},
        {'symptom': 'The worn finish replaced my colours.', 'cause': 'Base Strength is at 100, the full finish.', 'fix': 'Lower Base Strength to 50 to 70.'},
        {'symptom': 'Heavy wear killed my fine finish.', 'cause': 'Chips and scratches cover the detail.', 'fix': 'Use a lighter worn finish or lower Base Strength.'},
    ],
    protips=['The engine\'s fixed seed means you can re-render a worn car and get identical damage.',
             'A worn base plus a chip or scuff overlay is the quickest route to a used-car look.'])

# ---- the three retired Season control pages (generated from the UI scan, which cannot know a panel is hidden) ----
SEASON_PAGES = {
    'controls_zones_1.pro.zones.add_race': dict(
        summary='Add Race belonged to the Season batch panel, which is retired in this build. It cannot be reached.',
        what='The Season batch panel stays hidden and nothing in the Pro window opens it, so Add Race cannot be clicked. For a worn look, use a worn Base Material and Base Strength instead.',
        effect='Retired: it added a race event to the Season batch.'),
    'controls_zones_1.pro.zones.quick_wear_ramp': dict(
        summary='Quick: Wear Ramp belonged to the Season batch panel, which is retired in this build. It cannot be reached.',
        what='The Season batch panel stays hidden and nothing in the Pro window opens it, so Quick: Wear Ramp cannot be clicked. For a worn look, use a worn Base Material and Base Strength instead.',
        effect='Retired: it spread wear from 0 to 100 across the Season batch races.'),
    'controls_zones_1.btnSeasonRender': dict(
        summary='Render All Races belonged to the Season batch panel, which is retired in this build. It only shows a disabled message.',
        what='The Season batch panel stays hidden, and its Render All Races action only shows a message that Season mode is disabled in this booth build. Render the car once per stage with a normal RENDER instead.',
        effect='Retired: it rendered every race in the Season batch.'),
}
SEASON_SRC = [API + ':2648', API + ':2706', 'paint-booth-v2.html:2534']


def _load(p):
    with open(p, encoding='utf8') as f:
        return json.load(f)


def _dump_atomic(p, obj, **kw):
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf8', newline='\n') as f:
        f.write(json.dumps(obj, ensure_ascii=False, **kw))
    os.replace(tmp, p)


def patch_article(a, merge_v3=True):
    """Overwrite the wear fields of one article dict in place. Keeps ids, aliases, screens, lane, updated."""
    for k in ('title', 'summary', 'what', 'when', 'how', 'controls', 'tips', 'pitfalls', 'related', 'actions', 'figures', 'covers'):
        a[k] = json.loads(json.dumps(WEAR_ADD[k]))
    a['sources'] = list(WEAR_ADD['sources'])
    if merge_v3:
        for k in ('level', 'deep', 'examples', 'combos', 'faq', 'mistakes', 'protips'):
            a[k] = json.loads(json.dumps(WEAR_V3[k]))
    seen = set(a.get('aliases', []))
    for al in WEAR_ADD['aliases']:
        if al not in seen:
            a.setdefault('aliases', []).append(al)
    return a


def apply(write=True):
    changed = []
    # 1. the article itself
    p = os.path.join(ENC, 'finishes.json')
    d = _load(p)
    for a in d['articles']:
        if a['id'] == 'finishes.wear':
            before = json.dumps(a, sort_keys=True)
            patch_article(a)
            if json.dumps(a, sort_keys=True) != before:
                changed.append('finishes.json')
    if write and 'finishes.json' in changed:
        _dump_atomic(p, d, indent=1)
    # 2. the Season control pages
    p = os.path.join(ENC, 'pages', 'controls_zones_1.json')
    d = _load(p)
    n = 0
    for a in d['articles']:
        fx = SEASON_PAGES.get(a['id'])
        if not fx:
            continue
        before = json.dumps(a, sort_keys=True)
        a['summary'] = fx['summary']
        a['what'] = fx['what']
        a['how'] = ['Skip it: it cannot be used in this build.', 'For a worn look, pick a worn Base Material under BASE and lower Base Strength.']
        a['tips'] = ['The Wear article explains what to use instead.']
        a['related'] = ['finishes.wear', 'zones.card_controls']
        a['actions'] = []
        for c in a.get('controls', []):
            c['effect'] = fx['effect']
        a['sources'] = list(SEASON_SRC)
        if json.dumps(a, sort_keys=True) != before:
            n += 1
    if n:
        changed.append('controls_zones_1.json')
        if write:
            _dump_atomic(p, d, separators=(',', ':'))
    # 3. stale drafts, so assemble() from drafts cannot bring the old text back
    p = os.path.join(ENC, '_drafts', 'finishes.jsonl')
    if os.path.exists(p):
        lines = open(p, encoding='utf8').read().split('\n')
        out, dirty = [], False
        for l in lines:
            if l.strip():
                a = json.loads(l)
                if a.get('id') == 'finishes.wear':
                    before = json.dumps(a, sort_keys=True)
                    patch_article(a, merge_v3=False)
                    if json.dumps(a, sort_keys=True) != before:
                        dirty = True
                    l = json.dumps(a, ensure_ascii=False)
            out.append(l)
        if dirty:
            changed.append('_drafts/finishes.jsonl')
            if write:
                tmp = p + '.tmp'
                open(tmp, 'w', encoding='utf8', newline='\n').write('\n'.join(out))
                os.replace(tmp, p)
    p = os.path.join(ENC, '_drafts', 'finishes_v3.json')
    if os.path.exists(p):
        d = _load(p)
        new = {k: json.loads(json.dumps(WEAR_V3[k])) for k in ('level', 'deep', 'examples', 'combos', 'faq', 'mistakes', 'protips')}
        new['_sources'] = list(WEAR_V3['_sources'])
        old = d.get('finishes.wear', {})
        if 'screens' in old:
            new['screens'] = old['screens']
        if old != new:
            d['finishes.wear'] = new
            changed.append('_drafts/finishes_v3.json')
            if write:
                _dump_atomic(p, d)
    return changed


if __name__ == '__main__':
    ch = apply(write='--write' in sys.argv)
    print('enc_wear_fix:', ('changed ' + ', '.join(ch)) if ch else 'no change (already fixed)', '' if '--write' in sys.argv else '(dry run)')

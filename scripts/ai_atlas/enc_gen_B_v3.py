"""Encyclopedia V3 enrichment for the generated per-finish / per-pattern / per-spec-pattern pages (lane B).
Imported by enc_gen_B.py. Every sentence here restates a fact from the wiki spec guide (band tables, albedo coupling),
engine/paint_v2/surface_intent.py (category intent) or the page's own measured atlas numbers. No hidden-feature wording."""
import ast, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SCREENS_PATH = os.path.join(ROOT, 'data', 'encyclopedia', 'screens.json')

WIKI_SPEC = 'SPB_WIKI.html#spec_guide'
INTENT_SRC = 'engine/paint_v2/surface_intent.py:98-160'


# ---------------------------------------------------------------- surface intent (parsed, never imported: no engine boot)
def _load_intent():
    src = open(os.path.join(ROOT, 'engine', 'paint_v2', 'surface_intent.py'), encoding='utf-8').read()
    tree = ast.parse(src)
    consts, table = {}, {}
    for n in tree.body:
        t = n.targets[0] if isinstance(n, ast.Assign) else (n.target if isinstance(n, ast.AnnAssign) else None)
        if t is None or not isinstance(t, ast.Name): continue
        if t.id.isupper() and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str): consts[t.id] = n.value.value
        if t.id == 'CATEGORY_INTENT' and isinstance(n.value, ast.Dict):
            for k, v in zip(n.value.keys, n.value.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Name): table[k.value] = consts.get(v.id, v.id)
    return table


def _nk(s): return re.sub(r'[^a-z0-9&]+', ' ', re.sub(r'^[^A-Za-z0-9]+', '', s or '').lower()).strip()


_T = _load_intent()
INTENT = {_nk(k): v for k, v in _T.items()}

INTENT_TEXT = {
    'spec_driven': 'Spec-driven shelf: the shine does all the visual work and your own paint colour stays as it is.',
    'fine_structural_color': 'Fine structural colour shelf: 8 to 32 pixel colour detail whose shine shifts with the viewing angle.',
    'pattern_design': 'Pattern-design shelf: the structure of the pattern matters, not the colour it is printed in.',
    'pattern_image': 'Pattern-image shelf: the pattern carries its own colours.',
    'full': 'Full-finish shelf: the finish carries both its own paint look and its own shine.',
}


def intent_of(shelf):
    return INTENT.get(_nk(shelf), 'full')


# ---------------------------------------------------------------- band words (wiki spec guide section 3)
def _band(v, edges, words):
    for e, w in zip(edges, words):
        if v <= e: return w
    return words[-1]


M_W = [(15, 'non-metal paint'), (63, 'low metal, like carbon or subtle flake'), (127, 'pearl-level metal'), (175, 'strong pearl or anodized metal'),
       (239, 'true metallic'), (255, 'chrome or mirror tier')]
R_W = [(14, 'razor or mirror smooth'), (29, 'wet mirror gloss'), (59, 'high gloss'), (99, 'satin gloss'), (129, 'satin or eggshell'),
       (159, 'semi-matte'), (199, 'matte or blasted'), (229, 'flat'), (255, 'dead flat or porous')]
C_W = [(15, 'no clearcoat'), (16, 'maximum clearcoat'), (31, 'very strong clearcoat'), (63, 'strong-to-medium clearcoat'), (127, 'satin or weak clearcoat'),
       (191, 'dull or trace clearcoat'), (254, 'almost no clearcoat'), (255, 'no clearcoat shine')]


def w(v, table):
    for e, t in table:
        if v <= e: return t
    return table[-1][1]


def spec_character(it):
    M, R, C = (it.get(k) or [None, None] for k in ('M', 'R', 'C'))
    if M[0] is None: return ''
    m, r, c = int(round(M[0])), int(round(R[0])), int(round(C[0]))
    s = 'Average spec: metal %d (%s), roughness %d (%s), clearcoat %d (%s).' % (m, w(m, M_W), r, w(r, R_W), c, w(c, C_W))
    wide = [n for n, v in (('metal', M), ('roughness', R), ('clearcoat', C)) if len(v) > 1 and v[1] is not None and v[1] >= 20]
    if wide: s += ' The spec is textured, not flat: %s vary by 20 or more across the surface.' % ' and '.join(wide)
    elif len(M) > 1 and all(len(v) > 1 and (v[1] or 0) < 5 for v in (M, R, C)): s += ' The spec is almost perfectly flat, one smooth material.'
    return s


def paint_advice(it, c, own):
    M, R = (it.get('M') or [None])[0], (it.get('R') or [None])[0]
    if M is None: return ''
    if own:
        s = 'It brings its own colours, so leave BASE COLOR on the finish\'s own colour. Put it next to a plain zone of the opposite sheen (matte beside gloss, warm beside cool) so the colours have a calm neighbour.'
    elif M >= 240:
        s = 'Reflection inherits the paint colour: near-white paint gives silver, a coloured paint gives tinted chrome, and a dark paint stays dark.'
    elif M >= 176:
        s = 'Metal takes on the paint colour: light and mid colours keep the sparkle, very dark colours swallow it.'
    elif M >= 64:
        s = 'Pearl depth shows best on a clear mid-tone or deep saturated colour; a dull grey paint hides the shift.'
    elif R >= 160:
        s = 'Matte reads as flat colour, so a clean saturated colour looks richer than a muddy mid-grey; pair it with a gloss or metal neighbour for contrast.'
    else:
        s = 'Gloss shows the paint colour as it is, so any colour works; pick the colour for contrast with the neighbouring zones, not for the finish.'
    av = [x for x in (c.get('avoid') or []) if x][:3]
    if av: s += ' Avoid: %s.' % ', '.join(av)
    return s


def level_of(it, c, kind):
    r = c.get('ratings') or {}
    risk, busy, loud = r.get('risk') or 0, c.get('busy') or 0, c.get('loud') or 0
    if kind == 'finish':
        sh = [s for s in (it.get('s') or [])]
        if it.get('fb') == 'flat' or risk <= 2 and busy <= 2: return 'beginner'
        if risk >= 4 or (busy >= 4 and loud >= 4): return 'pro'
        return 'intermediate'
    if kind == 'pattern':
        if busy >= 4 or risk >= 4: return 'intermediate'
        return 'beginner'
    return 'intermediate' if (it.get('ch') or '') else 'pro'   # spec patterns: exact channels need the spec map


def _cap(t, n):
    t = (t or '').strip()
    return t if len(t) <= n else t[:n - 1].rsplit(' ', 1)[0].rstrip(',;:') + '.'


def _txt(v, n=2):
    if isinstance(v, str): v = [v]
    return '; '.join(str(x) for x in (v or [])[:n] if x)


def combos_for(c, kind):
    d = (c.get('deep') or {}).get('s') or {}
    out = []
    if isinstance(d, dict):
        for key, tgt, lead in (('patterns_over', 'patterns.layers_and_stacking', 'Patterns that suit it: '), ('patterns_avoid', 'patterns.choosing_at_car_scale', 'Patterns to avoid: '),
                               ('spec_over', 'spec.overlays_stack', 'Spec overlays that work: ')):
            t = _txt(d.get(key), 2)
            if t: out.append({'with': tgt, 'why': _cap(lead + t[:1].lower() + t[1:], 230)})
    out.append({'with': 'spec.paint_spec_marriage', 'why': 'Judge the paint and the shine together: the same spec looks different under different colours.'})
    return out[:4]


# ---------------------------------------------------------------- screens (lane S): car renders keyed by finish id
_SC = None


def screens_set():
    global _SC
    if _SC is None:
        _SC = set()
        if os.path.exists(SCREENS_PATH):
            try:
                j = json.load(open(SCREENS_PATH, encoding='utf-8'))
                rows = j.get('screens', j) if isinstance(j, dict) else j
                _SC = {(r.get('id') if isinstance(r, dict) else r) for r in (rows if isinstance(rows, list) else list(rows))} if not isinstance(rows, dict) else set(rows.keys())
            except Exception:
                _SC = set()
    return _SC


def screens_for(ident, shelf=None):
    # ENC_READER_FIX 2026-10-05: only the render of THIS finish. The shelf's hero car (cat_<shelf>) used to stand in for every finish on the
    # shelf, so the Chrome page showed a tie-dye 'Moonstone' car (blind buyer test). The page's own swatch is the picture when there is no render.
    sc = screens_set()
    return ['car_' + ident] if ('car_' + ident) in sc else []


# ---------------------------------------------------------------- per-kind extras
def finish_extras(it, c, ident, shelf, nm, own, kind):
    ex = {}
    ex['level'] = level_of(it, c, 'finish')
    sc = spec_character(it)
    if sc: ex['spec_character'] = sc
    it_ = intent_of(shelf)
    ex['intent'] = it_
    ex['intent_note'] = INTENT_TEXT[it_]
    pa = paint_advice(it, c, own)
    if pa: ex['paint_advice'] = pa
    ex['combos'] = combos_for(c, 'finish')
    settings = {'Zone section': 'BASE MATERIAL', 'Base': nm}
    if shelf and re.sub(r'^[^A-Za-z0-9]+', '', shelf).lower().startswith('foundation') and not str(shelf).lower().endswith('efx'):
        settings['BASE COLOR'] = 'Source paint (keeps your colours)'
        res = 'Only the shine changes; your livery colours stay exactly as painted.'
    elif own:
        settings['BASE COLOR'] = "Use finish's own color"
        res = 'The finish shows its own colours and spec together.'
    else:
        settings['BASE COLOR'] = 'Pick the colour you want'
        res = 'The finish takes your colour and adds its own shine.'
    ex['examples'] = [{'title': 'Put it on a zone', 'goal': 'See %s on the car.' % nm, 'settings': settings, 'result': res}]
    scr = screens_for(ident, shelf)
    ex['screens'] = scr
    ex['_src'] = [WIKI_SPEC, INTENT_SRC]
    return ex


def pattern_extras(it, c, ident, g, nm):
    ex = {'level': level_of(it, c, 'pattern'), 'intent': 'pattern_design', 'intent_note': INTENT_TEXT['pattern_design']}
    con, cov, fb = it.get('con'), it.get('cov'), it.get('fb')
    bits = []
    if con is not None:
        bits.append('Pattern contrast %s out of 100: %s' % (con, 'strong, it shows over almost any plain colour.' if con >= 70 else
                                                        'medium, pick a base colour that is clearly lighter or darker than the pattern.' if con >= 40 else
                                                        'subtle, give it a high-contrast base or raise its opacity.'))
    if cov is not None: bits.append('It covers about %s percent of the tile%s.' % (cov, ', so a lot of base colour stays visible' if cov < 35 else ''))
    bits.append('Use Paint mode Blend to keep your colour; Overlay prints the pattern\'s own colours over it.')
    ex['paint_advice'] = ' '.join(bits)
    ex['combos'] = [x for x in combos_for(c, 'pattern') if x['with'] != 'patterns.layers_and_stacking'][:3] + [{'with': 'patterns.paint_mode', 'why': 'Blend keeps your paint colour; Overlay hides it under the pattern colours.'}]
    ex['examples'] = [{'title': 'Fine pattern on a zone', 'goal': 'Get %s to read at car scale.' % nm,
                       'settings': {'Zone section': 'PATTERN', 'Pattern 1': nm, 'Paint mode': 'Blend', 'Scale': 'Below 1.00'},
                       'result': 'The pattern repeats finely across the zone and keeps your paint colour.'}]
    ex['screens'] = screens_for(ident)
    ex['_src'] = [WIKI_SPEC]
    return ex


def spec_extras(it, c, ident, g, nm, chs):
    ex = {'level': level_of(it, c, 'spec'), 'intent': 'spec_driven',
          'intent_note': 'A spec pattern changes the shine only: metal, roughness and clearcoat, never the paint colour.'}
    ex['paint_advice'] = 'It cannot recolour anything. Metal added to a light paint looks bright; metal added to a dark paint stays dark, because metal reflection inherits the paint colour. Pair it with a paint that gives the gloss difference something to show on.'
    ex['combos'] = [{'with': 'spec.overlays_stack', 'why': 'Up to five overlays stack in order; a strong overlay can wash out the ones below it.'},
                    {'with': 'spec.blend_modes', 'why': 'The blend mode decides how this overlay meets the base shine. Normal is the safe start.'},
                    {'with': 'spec.iron_rules', 'why': 'Coat values 1 to 15 and roughness under 15 on non-chrome pixels are raised to safe values on export.'}]
    ex['examples'] = [{'title': 'Add it as an overlay', 'goal': 'Layer %s over a base finish.' % nm,
                       'settings': {'Zone section': 'SPEC OVERLAYS', 'Overlay': nm, 'Strength': '50% (default)', 'Boxes ticked': chs},
                       'result': 'The shine of the zone gets this texture while the colours stay put.'}]
    ex['screens'] = screens_for(ident)
    ex['_src'] = [WIKI_SPEC]
    return ex

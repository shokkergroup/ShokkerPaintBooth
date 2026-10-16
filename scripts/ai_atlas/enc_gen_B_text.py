"""enc_gen_B_text.py - text hygiene + spec-wording rules shared by the finish / pattern / spec page generator (ENC-GEN lane, 2026-10-10).

Why a module: the sprint (burn_1010 E0-E12, T-a/T-b, C-encfin) found the same wrong words in thousands of generated pages. They all come from a few
generator rules, so the fix lives here once and `enc_gen_B.py` runs every page through `fix_page()` before it is written.

Spec map facts used everywhere (iRacing + wiki spec_guide section 3):  R = metallic, G = roughness (0 = mirror, but only chrome-tier metal may go under 15),
B = clearcoat (0-15 = none, 16 = max gloss, rising toward 255 = duller), A = specular mask.  Roughness is NEVER called "R" in buyer copy.
"""
import re

# ---------------------------------------------------------------- wording bands
# Roughness (G) bands = wiki spec_guide table. The Shine label below uses the SAME edges, so the two lines on a page can never disagree.
R_W = [(14, 'razor or mirror smooth'), (29, 'wet mirror gloss'), (59, 'high gloss'), (99, 'satin gloss'), (129, 'satin or eggshell'),
       (159, 'semi-matte'), (199, 'matte or blasted'), (229, 'flat'), (255, 'dead flat or porous')]
# Clearcoat (B) bands. 0-15 = NO clearcoat, 16 = strongest, then weaker; "dull" only near 255 (ENC-GEN 2026-10-10: 128-191 used to read "dull or trace",
# which is wrong -- reflectivity at B 130-190 is still roughly 55-25 percent of the maximum).
C_W = [(15, 'no clearcoat'), (16, 'maximum clearcoat'), (31, 'very strong clearcoat'), (63, 'strong-to-medium clearcoat'), (127, 'moderate clearcoat, satin range'),
       (191, 'weak clearcoat'), (239, 'very weak clearcoat'), (254, 'dull, almost no clearcoat'), (255, 'dull, no clearcoat shine')]


def band(v, table):
    for e, t in table:
        if v <= e: return t
    return table[-1][1]


def coat_adj(c):
    """one adjective for the clearcoat byte, used inside sentences"""
    if c <= 15: return 'switched off'
    if c <= 63: return 'strong'
    if c <= 100: return 'moderate'
    if c <= 191: return 'weak'
    if c <= 239: return 'very weak'
    return 'dull'


def shine_label(M, R, C):
    """-> (word, note).  Word comes from roughness (same edges as R_W) AND clearcoat.
    A smooth surface only reads as gloss while the clearcoat is really on: B 16-100 (16 = maximum). With B > 100, or B 0-15 (= none), the glossy words
    are not used (owner rule: never 'gloss' when B > 100) and the label drops to 'satin' with a note that explains why."""
    if R is None: return None, ''
    if R <= 14: word = 'mirror'
    elif R <= 29: word = 'high gloss'
    elif R <= 59: word = 'gloss'
    elif R <= 129: word = 'satin'
    elif R <= 159: word = 'semi-matte'
    elif R <= 199: word = 'matte'
    else: word = 'flat'
    note = ''
    if word in ('mirror', 'high gloss', 'gloss') and C is not None:
        if C > 100 or C <= 15:
            metal = M is not None and M >= 176
            note = ('The surface is smooth (roughness %d), but the clearcoat (B %d) is %s, so it does not read as wet gloss%s.'
                    % (R, C, coat_adj(C), '; the bare metal still gives it a bright, hard-edged shine' if metal else ''))
            word = 'satin'
        elif C > 63 and word in ('mirror', 'high gloss'):
            word = 'gloss'
    return word, note


# ---------------------------------------------------------------- text rules (idempotent, applied to every buyer-facing string)
_DEV = [
    (re.compile(r'\s*The preview title shows a lost dash as \?\?\?\.?'), ''),                      # dev note that leaked from the finish card (flm_ember_storm_*)
    (re.compile(r'\s*\(?\s*\?{3}\s*\)?'), ''),
]
_PLACEHOLDER = [
    (re.compile(r'\bplaceholder-like\b', re.I), 'stand-in'),
    (re.compile(r'\bplaceholders\b', re.I), 'stand-ins'),
    (re.compile(r'\bplaceholder\b', re.I), 'stand-in'),
]
_SPEC_LETTERS = [
    (re.compile(r'\bM/R/Cc\b'), 'metal/roughness/clearcoat'),
    (re.compile(r'\bM/R\b'), 'metal/roughness'),
    (re.compile(r'\bM(\d{2,3}) R(\d{1,3})\b'), r'metal \1, roughness \2'),                          # "M255 R2 pure chrome"
    (re.compile(r'(?i)\b(roughness|rough) \(R (\d{1,3})\)'), r'\1 (\2)'),                           # "roughness (R 15)" -> "roughness (15)"
    (re.compile(r'(?i)\bclearcoat \((?:C|Cc) (\d{1,3})\)'), r'clearcoat (\1)'),
    (re.compile(r'(?<![A-Za-z0-9_/])R (\d{1,3})(?![\d%A-Za-z])'), r'roughness \1'),
    (re.compile(r'(?<![A-Za-z0-9_/])M (\d{1,3})(?![\d%A-Za-z])'), r'metal \1'),
    (re.compile(r'(?<![A-Za-z0-9_/])C (\d{1,3})(?![\d%A-Za-z])'), r'clearcoat \1'),
    # "M about 30", "R ~116", "C about 200", "M is 25": engine shorthand for metal / roughness / clearcoat (R is metallic in the iRacing map, so never print it for roughness)
    (re.compile(r'(?<![A-Za-z0-9_/\-])M (about|is) (\d{1,3})(?![\d%A-Za-z])'), r'metal \1 \2'),
    (re.compile(r'(?<![A-Za-z0-9_/\-])R (about|is) (\d{1,3})(?![\d%A-Za-z])'), r'roughness \1 \2'),
    (re.compile(r'(?<![A-Za-z0-9_/\-])C (about|is) (\d{1,3})(?![\d%A-Za-z])'), r'clearcoat \1 \2'),
    (re.compile(r'(?<![A-Za-z0-9_/\-])M ?~ ?(\d{1,3})(?![\d%A-Za-z])'), r'metal ~\1'),
    (re.compile(r'(?<![A-Za-z0-9_/\-])R ?~ ?(\d{1,3})(?![\d%A-Za-z])'), r'roughness ~\1'),
    (re.compile(r'(?<![A-Za-z0-9_/\-])C ?~ ?(\d{1,3})(?![\d%A-Za-z])'), r'clearcoat ~\1'),
]


def fix_str(t):
    if not isinstance(t, str): return t
    for rx, rep in _DEV + _PLACEHOLDER + _SPEC_LETTERS:
        t = rx.sub(rep, t)
    return re.sub(r'  +', ' ', t)


FIELDS_TEXT = ('summary', 'what', 'paint_advice', 'spec_character', 'intent_note')
FIELDS_LIST = ('when', 'how', 'tips', 'pitfalls')


def _fix_any(o):
    if isinstance(o, str): return fix_str(o)
    if isinstance(o, list): return [_fix_any(x) for x in o]
    if isinstance(o, dict): return {k: _fix_any(v) for k, v in o.items()}
    return o


def fix_page(pg):
    """in place: run the text rules over the buyer-facing fields of one generated page"""
    for k in FIELDS_TEXT:
        if k in pg: pg[k] = fix_str(pg[k])
    for k in FIELDS_LIST:
        if k in pg: pg[k] = [fix_str(x) for x in pg[k]]
    for k in ('examples', 'combos'):
        if k in pg: pg[k] = _fix_any(pg[k])
    return pg


# ---------------------------------------------------------------- per-finish wording that contradicts the finish's own spec (ENC-GEN fix 4)
# key -> list of (old, new). `old` must occur in summary / what / tips / pitfalls (checked; a miss prints a warning so a data change is noticed).
# Every row cites the measured numbers on the page (M/R/C = metal / roughness / clearcoat average) and, for bases, the registry (engine.BASE_REGISTRY).
# Finishes whose own description claims gloss while the measured clearcoat B is over 100 (dull side of the scale). Source: sprint burn_1010 E9 (text_vs_spec),
# E10 (gloss_vs_clearcoat) and E11 (gloss_text_with_clearcoat_gt100); the E8 tone list is a word heuristic with many intended two-population finishes and is NOT used.
GLOSS_SOFTEN_IDENTS = frozenset(('bth_die_back', 'bth_edge_map', 'cs_black_gold', 'cs_black_red', 'cs_darkflame', 'cs_gunmetal_lime', 'cs_gunmetal_orange', 'halftone', 'liquid_metal', 'living_neon_equalizer', 'living_oil_pulse', 'living_wave_tide', 'magnesium_burn', 'mo_chrono_rings', 'ms_venom_veil', 'mul_decoy_blackout', 'neon2_emberwake_delam', 'neon2_plasma_tubes', 'neon_rainbow_tube', 'neon_toxic_green', 'ns2_hyper_rings', 'ns2_monsoon_glass', 'p_aurora', 'pdg_lichen_mercury', 'pdg_silk_carrier', 'pp_chrome_oval_chain', 'pp_ice_facet_shatter', 'pp_pink_checker_carbon', 'prizm_mystichrome', 'prizm_venom', 'reactive_candy_reveal', 'reactive_chrome_fade', 'reactive_ghost_metal', 'reactive_mirror_shadow', 'reactive_pearl_flash', 'reactive_pulse_metal', 'reactive_stealth_pop', 'refraction', 'rs_jorogumo_silk', 'rs_oni_nocturne', 'rs_wangan_midnight_pulse', 'spectrum_oilfilm_rain', 'tidal_wave', 'vm_rosa_corazon', 'wave_candy_flow', 'wave_metallic_pulse', 'wave_standing_chrome', 'xlab_bloomglass', 'xlab_chromatophore', 'xlab_cinder_mirror', 'xlab_comet_terrace', 'xlab_hex_reliquary', 'xlab_labyrinth_pulse', 'xlab_murmuration', 'xlab_quantum_tide', 'xlab_sonic_chrome'))
_SOFT = [
    (re.compile(r'\bglossy sparkle\b'), 'bright sparkle'), (re.compile(r'\bglossy highlights?\b'), lambda m: 'soft ' + m.group(0).split()[1]),
    (re.compile(r'\bglossy\b'), 'smooth'), (re.compile(r'\bGlossy\b'), 'Smooth'),
    (re.compile(r'\bhigh clearcoat gloss\b'), 'clearcoat sheen'), (re.compile(r'\bmirror gloss\b'), 'bright sheen'),
    (re.compile(r'\bBlack gloss\b'), 'Smooth black'), (re.compile(r'\bhigh-speed gloss\b'), 'high-speed sheen'),
    (re.compile(r'\bwet-looking\b'), 'smooth-looking'),
    # ENC-FIX 2026-10-10: the other gloss claims the census found next to a dull coat (every spelling of "high gloss" / "wet look" / "mirror-gloss")
    (re.compile(r'\bunder high gloss\b'), 'under a smooth sheen'),
    (re.compile(r'\bHigh[- ]gloss\b'), 'Smooth sheen'), (re.compile(r'\bhigh[- ]gloss\b'), 'smooth sheen'),
    (re.compile(r'\bMirror-gloss\b'), 'Bright sheen'), (re.compile(r'\bmirror-gloss\b'), 'bright sheen'),
    (re.compile(r'\bWet[- ]look\b'), 'Smooth'), (re.compile(r'\bwet[- ]look\b'), 'smooth'),
    (re.compile(r'\bdeep gloss\b'), 'smooth sheen'), (re.compile(r'\bgloss clearcoat\b'), 'smooth clearcoat'),
]
# a gloss word inside a negation ("satin not glossy", "rather than glossy", "nothing glossy") already says the right thing: never touched
_NEG = re.compile(r"\b(?:not|no|nothing|never|less|than|without|isn't|aren't)\b", re.I)


def _negated(t, pos):
    clause = re.split(r'[.;:!?]', t[:pos])[-1]
    return bool(_NEG.search(clause[-40:]))


# ENC-FIX 2026-10-10 (glossy-on-dull-clearcoat, 376 finish cards): which finishes may keep gloss words.
# The card prose was written from the picture; the page's own measured spec (metal / roughness / clearcoat averages) is the check.  Rule, from R/G/B together
# and with the SAME numbers shine_label() already uses (M >= 176 = "bare metal still gives a bright hard-edged shine", R <= 59 = the high-gloss roughness band):
#   clearcoat B <= 100  -> the coat is really on: gloss words are fine (nothing to do);
#   clearcoat B  > 100  -> gloss words are KEPT only for polished metal (M >= 176 AND R <= 59), where the bare metal reads shiny with a weak or absent coat;
#                          every other finish gets 'glossy' -> 'smooth' etc. in its description (summary / what); the numbers say satin sheen at most.
# Tips / pitfalls / combos are NOT touched: there "glossy" is advice about a spec overlay or a neighbour ("glossy bars over the frosted shell", "Not glossy: matte").
POLISHED_METAL_M = 176
POLISHED_METAL_R = 59


def reads_shiny_without_coat(M, R, C):
    """True when a finish with a dull / absent clearcoat (B > 100) still reads shiny because it is polished bare metal"""
    return M is not None and R is not None and M >= POLISHED_METAL_M and R <= POLISHED_METAL_R


def needs_gloss_soften(pg):
    ident = (pg.get('key') or '').split('::', 1)[-1]
    coat = pg.get('coat')
    if coat is None or coat <= 100: return False
    if ident in GLOSS_SOFTEN_IDENTS: return True
    return not reads_shiny_without_coat(pg.get('metal'), pg.get('rough'), coat)


def soften_gloss(pg):
    """finishes with clearcoat B > 100 that do not read as polished metal: 'glossy' style claims in summary / what become 'smooth' / 'sheen' (the numbers say the coat is weak or dull).
    Rule-based (needs_gloss_soften), so a regeneration of the cards can never bring the claim back; GLOSS_SOFTEN_IDENTS stays as an always-soften override.  -> number of words changed"""
    if not needs_gloss_soften(pg): return 0
    n = 0

    def fix(t):
        nonlocal n
        for rx, rep in _SOFT:
            def sub(m, rep=rep):
                nonlocal n
                if _negated(m.string, m.start()): return m.group(0)
                n += 1
                return rep(m) if callable(rep) else rep
            t = rx.sub(sub, t)
        return t
    for f in ('summary', 'what'):
        if f in pg: pg[f] = fix(pg[f])
    return n


TEXT_FIXES = {
    # multiscale_matte_silk: card says "dead-flat matte, zero gloss" but the measured spec is metal 13, roughness 42, coat 76 (smooth, moderate coat = a soft highlight).
    'monolithic::multiscale_matte_silk': [
        ('Dead-flat matte with a faint silk fabric ripple, ultra smooth and zero gloss,', 'Smooth silk-like finish with a faint fabric ripple and a soft highlight,'),
        ('Dead-flat matte with silk micro-texture — ultra-smooth fabric feel on zero-gloss base', 'Silk micro-texture — ultra-smooth fabric feel on a soft-sheen base'),
        ('Not dead-flat matte: the old card says zero gloss, but roughness is low (42), so it shows a real highlight', 'Not dead-flat matte: roughness is low (42), so it shows a real highlight'),
    ],
    # x_lab (sprint E11): the card tagline says "mirror" for finishes whose measured spec is only a moderate sheen (coat 119-125, roughness 45-59).
    'monolithic::xlab_quantum_tide': [
        ('Blue quantum tide folding through a black tidal mirror', 'Blue quantum tide folding through a dark, deep tide'),
    ],
    'monolithic::xlab_sonic_chrome': [
        ('Golden sonic pressure waves embossed in mirror chrome', 'Golden sonic pressure waves embossed in polished metal'),
        ('smooth chrome-like shine', 'smooth metallic sheen'),
    ],
    # liquid_obsidian: registry base setting is metal 255 / roughness 2 / clearcoat 16 (engine.BASE_REGISTRY['liquid_obsidian']) but the measured panel average on the page is
    # metal 87 / roughness 131 / coat 99, so "roughness stays near-zero" contradicted the numbers printed right after it.
    'base::liquid_obsidian': [
        ('while roughness stays near-zero', 'while its base setting is roughness 2 and clearcoat 16 (the measured panel average is higher: roughness 131, coat 99)'),
    ],
}

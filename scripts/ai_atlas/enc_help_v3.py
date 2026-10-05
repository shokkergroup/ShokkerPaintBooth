#!/usr/bin/env python
"""Encyclopedia v3 (lane C, 2026-10-04): turns the short generated help_* Q&A pages into real articles.

Called from enc_gen_C2.py after the page is built. Adds, from STRUCTURED sources only:
  deep[]     what you need first, the controls involved (their curated `does`/`where`/`when` from the inventory), more detail
  faq[]      data-driven (where is the control, when to use it, what you need) + a small curated library
  pitfalls[] the controls' own curated `mistakes` facts
  mistakes[] / protips[]  from the curated library below (each entry cites the doc line it comes from)
  related[] / combos[]    article that covers each involved control, article that covers the controls it is used with
  level      beginner | intermediate
The library entries only restate facts that the hand-written support / preview_render / zones articles already source
(docs/ai_knowledge/10_support_troubleshooting.md etc.); line numbers below are those same anchors.
"""
import re

TS = 'docs/ai_knowledge/10_support_troubleshooting.md'

# keyword rx (lowercase text of the page) -> curated facts. Order = priority.
LIB = [
 dict(rx=r'user id|customer id',
      faq=('Is the User ID my car number?', 'No. It is your iRacing Customer ID, 4 to 7 digits (helmet icon top right in iRacing, then Profile).'),
      mis=('Your paint renders but never appears in iRacing', 'The User ID box holds a car number or another ID, and every file name carries it', 'Type your Customer ID (4 to 7 digits) and render again, then press Ctrl+R in iRacing.'),
      src=TS + ':11'),
 dict(rx=r'custom number|sim-stamped|hide car numbers|number mode',
      faq=('Which number mode should I pick?', 'Match iRacing: with Hide Car Numbers ON use Custom Number (car_num_<ID>.tga); with it OFF (the default) use Sim-Stamped Number (car_<ID>.tga). Restart iRacing after changing that setting.'),
      mis=('iRacing loads nothing after a good render', 'The number switch does not match iRacing Hide Car Numbers', 'Switch the mode, render again, restart iRacing if you changed its setting, then press Ctrl+R.'),
      src=TS + ':14'),
 dict(rx=r'ctrl\+r|reload',
      faq=('Which window do I press Ctrl+R in?', 'In iRacing, with your car in a session. In Shokker the same keys start a render.'),
      mis=('Nothing changes after RENDER', 'iRacing still holds the old textures', 'Switch to iRacing and press Ctrl+R (Reload Car Textures).'),
      src=TS + ':23'),
 dict(rx=r'car folder|output folder|deploy|where.{0,15}files|iracing folder',
      faq=('Which folder should I pick as the car folder?', 'The folder of the car you are driving: not a file, not the main paint folder, not a helmet or suit folder. Pick it from the car menu next to iRacing Car Folder.'),
      mis=('RENDER succeeds but iRacing finds no files', 'The car folder is not the folder of the car you drive', 'Open the car menu, pick your car and read the folder name.'),
      src=TS + ':20'),
 dict(rx=r'template layer|wire|car_mandatory|turn off before',
      faq=('Which template layers must be off when I render?', 'Wire, Mask, Car_Mandatory and everything in the group named Turn Off Before Exporting TGA.'),
      mis=('Guide lines or masks appear on the car', 'Template guide layers were visible when you rendered', 'Switch them off with their eye icons and render again.'),
      src=TS + ':31'),
 dict(rx=r'sponsor|decal|\blogo|(the|your|my) numbers|numbers? (look|vanish|got|under|on top)',
      faq=('How do I keep numbers and sponsors untouched?', 'Limit the zone to the body layer with Restrict to layer, or use a Foundation finish with Source colours, which changes only the shine.'),
      mis=('Numbers or sponsors changed colour or finish', 'The zone covered every layer, not just the body', 'Set Restrict to layer to the body layer only, or add a layer restriction to the zone.'),
      tip='Select logos and numbers by layer name, not by colour: exact edges, no colour bleed.',
      src='docs/ai_knowledge/03_recipes.md:33'),
 dict(rx=r'scale|finer|crush|tiny|huge|blobby|smear',
      faq=('What scale looks fine on a whole car?', 'Start around 0.5x. Scale (pattern) runs 0.10x to 4.0x and Base Scale 0.05x to 5.0x; 1.0x is normal and smaller is finer.'),
      mis=('A texture looks like boulders or a fishing net', 'The scale is too large for a whole-car sheet', 'Lower Scale (pattern) or Base Scale toward 0.5x and judge at 100 percent zoom.'),
      tip='Lower the scale first, then judge at 100 percent; it is the cheapest fix.',
      src='docs/ai_knowledge/09_field_playbook.md:12'),
 dict(rx=r'spec map|spec channel|r metal|g rough|b coat|metallic|roughness|clearcoat|\bspec\b',
      faq=('What do the spec channels mean?', 'Red is metal, green is roughness (0 is a mirror), blue is clearcoat (16 is the glossiest, higher is duller) and alpha is the specular mask.'),
      mis=('The shine looks wrong', 'The shine was judged in the colour view, which cannot show it', 'Open the R METAL, G ROUGH and B COAT views in the preview.'),
      tip='Look at the three spec views, not only the colour view; most surprises hide in the spec.',
      src='engine/SPEC_MAP_REFERENCE.md:6'),
 dict(rx=r'zone.{0,30}(order|priority|above|overlap|not showing|no show)|lower zone|zone order',
      faq=('Which zone wins when two overlap?', 'The one higher in the list (the lower number). Everything Else must stay at the bottom.'),
      mis=('A zone shows nothing', 'Another zone higher in the list claims the same pixels', 'Drag your zone higher, or mute the others to test.'),
      tip='Mute every other zone to test one zone quickly.',
      src=TS + ':36'),
 dict(rx=r'trading paints|other drivers',
      faq=('Can Shokker upload to Trading Paints?', 'No. Shokker writes files on your PC only. Trading Paints shares the car_spec .mip that iRacing builds for the shine, not the .tga.'),
      mis=('Other drivers see a white car', 'They do not have your files in their paint folder', 'Trading Paints puts files there; Shokker does not upload.'),
      src=TS + ':45'),
 dict(rx=r'\bpsd\b|xcf|\bora\b|layered',
      faq=('Which files open with layers?', 'PSD, XCF and ORA with the PSD/XCF/ORA button. Flat TGA, PNG and JPEG open without layers.'),
      mis=('Layers are missing after opening a PSD', 'Text, shape and adjustment layers are not plain pixels and cannot import', 'Rasterize them in your editor, save and open the file again.'),
      tip='Open the car template at its normal 2048 size; never resize the canvas first.',
      src='paint-booth-3-canvas.js:21616'),
 dict(rx=r'chrome',
      mis=('Chrome looks dark or grey in the sim', 'iRacing multiplies the paint by the metal, so a dark paint under metal turns dark; flat mirror metal also reflects a cloudy sky', 'Use a near-white paint under chrome or a Foundation chrome finish with Source colours kept, and try a track with a brighter sky.'),
      src=TS + ':29'),
 dict(rx=r'preview',
      faq=('Does the preview change my iRacing files?', 'No. The preview never writes into your iRacing folder; only RENDER does.'),
      mis=('The preview looks stale or wrong', 'It was not refreshed after a change', 'Press F5 over the preview, then diagnose.'),
      src=TS + ':42'),
 dict(rx=r'\bai\b|deepseek|openrouter|claude|chatgpt|\bmcp\b|copilot',
      faq=('Will the AI change my numbers or sponsors?', 'Not unless you name them, and every AI change has an Undo button.'),
      tip='Describe the look in plain words, then refine one change at a time so each step is easy to undo.',
      src='docs/ai_knowledge/01_how_pro_works.md:33'),
 dict(rx=r'save|project|recipe',
      faq=('Is a saved project an iRacing file?', 'No. A saved project (.spb) is for Shokker only; RENDER writes the files iRacing reads.'),
      src=TS + ':17'),
 dict(rx=r'render',
      tip='Judge the car in the sim at driving distance after Ctrl+R, not only in the zoomed-in preview.',
      src=TS + ':29'),
]

NEEDS_SENT = {
 'paint': 'a paint loaded', 'psd': 'a layered PSD template loaded', 'car_folder': 'the iRacing Car Folder set',
 'zone': 'a zone', 'selected': 'a zone selected', 'render': 'a finished render',
}
MODE_SENT = {'pro': 'Pro mode', 'chat': 'Chat mode', 'any': 'either mode'}

# hand-written titles / lead text for pages whose generated title or voice was poor (key = page slug)
TITLE_OVR = {
 'and_here_s_the_part_we_re_proud_of_we_re_not_gatekeeping_it': 'The FRACTURED finishes are not locked behind a tier',
 'bases_the_finish_on_the_surface': 'Bases: picking the finish on the surface',
 'first_what_this_thing_is': 'What Shokker Paint Booth makes (Getting Started)',
 'gotchas_in_one_place': 'Getting Started gotchas in one place',
 'how_to_fire_one_off': 'How to use one FRACTURED finish',
 'in_depth': 'Getting Started: the in-depth chapters',
 'new_here_training_wheels_teach_the_app_while_you_use_it': 'Training Wheels: the coach inside the app',
 'patterns_texture_and_shape': 'Patterns: texture and shape',
 'psd_vs_tga_how_much_control_you_get': 'PSD or TGA: how much control you get',
 'quick_start_a_real_finish_in_five_minutes': 'Quick Start: a real finish in five minutes',
 'render_amp_see_it_in_iracing': 'Render and see it in iRacing',
 'settings_license_amp_updates': 'Settings, licence and updates',
 'share_everything': 'Sharing finishes with the community',
 'spec_patterns_the_secret_sauce': 'Spec Patterns: the secret sauce',
 'the_family': 'The FRACTURED family',
 'the_one_idea_that_makes_everything_click_the_spec_map': 'The spec map: the one idea that makes everything click',
 'the_workspace': 'The workspace tour',
 'zones_telling_spb_where': 'Zones: telling Shokker where',
 'about_me': 'What the built-in helper is',
 'thanks': 'Thanking the helper',
 'cross_origin': 'Wrong address: opening Shokker in a browser tab',
 'render_busy': 'A render is already running',
 'need_id': 'Shokker asks for your iRacing User ID',
 'getting_started': 'Getting started with the built-in helper',
 'render_time': 'How long a render takes',
 'memory': 'Too much for one render (too many zones)',
 'zone_limit': 'How many zones you can use',
 'what_can_you_do_support': 'What the built-in helper can check for you',
}
WHAT_OVR = {
 'in_depth': 'The in-depth chapters of the Getting Started guide: the spec map, the workspace, setting up iRacing, PSD versus TGA, zones, bases, patterns, spec patterns, rendering, more tools, settings and gotchas.',
 'quick_start_a_real_finish_in_five_minutes': 'The short version: make a zone, make a second zone, give each its own finish and render. Everything after this is how to make it good.',
 'about_me': 'The built-in helper is software, not a person. It runs on your PC, works offline and reads your real settings to find out why a paint will not render or show up in iRacing.',
}

# first-person helper voice -> neutral (the helper speaks as "I" in chat; articles describe it)
_VERB = {'will': 'will', 'can': 'can', 'cannot': 'cannot', 'keep': 'keeps', 'find': 'finds', 'list': 'lists', 'show': 'shows',
         'read': 'reads', 'run': 'runs', 'check': 'checks', 'do': 'does', 'make': 'makes', 'give': 'gives', 'look': 'looks', 'bring': 'brings'}


def deperson(t):
    if not t:
        return t
    def verb(m):
        v = m.group(2).lower()
        start = m.group(1) is not None
        out = 'it ' + _VERB.get(v, v)
        return (m.group(1) or '') + (out[0].upper() + out[1:] if start else out)
    t = re.sub(r'(^|[.!?:]\s+)I (will|can|cannot|keep|find|list|show|read|run|check|do|make|give|look|bring)\b', lambda m: (m.group(1) or '') + 'It ' + _VERB[m.group(2)], t)
    t = re.sub(r'\b(?<![.!?]\s)I (will|can|cannot|keep|find|list|show|read|run|check|do|make|give|look|bring)\b', lambda m: 'it ' + _VERB[m.group(1)], t)
    for a, b in [(r'\bSay it to me\b', 'Tell the helper'), (r'\bsay it to me\b', 'tell the helper'), (r'\bto me\b', 'to the helper'),
                 (r'\bTell me\b', 'Tell the helper'), (r'\btell me\b', 'tell the helper'), (r'\bask me\b', 'ask the helper'), (r'\bAsk me\b', 'Ask the helper'),
                 (r'\bfrom me\b', 'from the helper'), (r'\bmy Versions strip\b', 'the Versions strip'), (r'\bmy earlier one\b', 'the earlier one'),
                 (r'\bunder my message\b', "under the helper's message"), (r'\bFor my changes\b', "For the helper's changes"),
                 (r'\bmy changes\b', "the helper's changes"), (r'\bjust tell it\b', 'just tell the helper')]:
        t = re.sub(a, b, t)
    return t


def level_for(kind, rec, steps):
    if kind == 'howto':
        needs = set(rec['facts'].get('needs') or [])
        return 'beginner' if len(steps) <= 3 and needs <= {'none', 'paint'} else 'intermediate'
    return 'beginner'


def _uniq(xs):
    out = []
    for x in xs:
        if x and x not in out:
            out.append(x)
    return out


def _cap(s, n):
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    m = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
    return cut[:m + 1] if m > n * 0.5 else cut.rsplit(' ', 1)[0].rstrip(',;:') + '.'


def _sent_split(text):
    return [s.strip() for s in re.findall(r'.+?(?:[.!?](?=\s|$)|$)', re.sub(r'\s+', ' ', text).strip()) if s.strip()]


def lib_hits(text):
    hits = [e for e in LIB if re.search(e['rx'], text)]
    return hits


def apply_lib(a, text, max_faq=4, max_mis=3, max_tip=2):
    faq, mis, tips, srcs = list(a.get('faq', [])), list(a.get('mistakes', [])), list(a.get('protips', [])), []
    for e in lib_hits(text):
        used = False
        if 'faq' in e and len(faq) < max_faq and e['faq'][0] not in [f['q'] for f in faq]:
            faq.append({'q': e['faq'][0], 'a': e['faq'][1]}); used = True
        if 'mis' in e and len(mis) < max_mis:
            mis.append({'symptom': e['mis'][0], 'cause': e['mis'][1], 'fix': e['mis'][2]}); used = True
        if 'tip' in e and len(tips) < max_tip and e['tip'] not in tips:
            tips.append(e['tip']); used = True
        if used:
            srcs.append(e['src'])
    a['faq'], a['mistakes'], a['protips'] = faq, mis, tips
    for s in srcs:
        if s not in a['sources']:
            a['sources'].append(s)


def enrich(kind, rec, a, ctx):
    """kind: howto|topics|support|guide; rec: inventory record; a: page dict (mutated); ctx: dict(BYID, ART, PAGE_BY_TITLE, NEXT, TOPIC, sc)"""
    sc = ctx['sc']
    slug = a['id'].split('.', 1)[-1] if '.' in a['id'] else a['id']
    slug = slug.lstrip('.')
    for k in ('summary', 'what'):
        a[k] = deperson(a[k])
    for k in ('how', 'tips', 'pitfalls'):
        a[k] = [deperson(x) for x in a[k]]
    if slug in TITLE_OVR:
        a['title'] = TITLE_OVR[slug]
    if slug in TITLE_OVR and kind == 'support':
        a['when'] = ['You asked the built-in helper: ' + a['title'] + '.']
    if slug in WHAT_OVR:
        a['what'] = WHAT_OVR[slug]
        a['summary'] = _cap(WHAT_OVR[slug], 300)
    deep, faq, mis, tips = [], [], [], []
    related, combos = list(a['related']), []

    if kind == 'howto':
        f = rec['facts']
        ctls = [ctx['BYID'][u] for u in f.get('ui', []) if u in ctx['BYID']]
        label = a['title'].rstrip('?')
        mode = f.get('mode', 'pro')
        needs = [NEEDS_SENT[n] for n in (f.get('needs') or []) if n in NEEDS_SENT]
        # lead paragraph: what the controls do (curated sentences)
        does = _uniq([deperson(sc(c['facts'].get('does', ''))) for c in ctls])
        howq = bool(re.match(r'(how|where|what|which|can)\b', label, re.I))
        if does and howq:
            a['what'] = _cap(' '.join(does[:2]), 600)
        elif ctls:
            a['what'] = 'Quick checks for "%s". The controls involved are %s.' % (label, ', '.join(sc(c['label'])[:40] for c in ctls[:5]))
        a['summary'] = _cap(a['summary'], 300)
        lines = []
        if needs:
            lines.append('You need ' + ' and '.join(needs) + ' first.')
        lines.append('This works in %s.' % MODE_SENT.get(mode, mode))
        deep.append({'heading': 'What you need first', 'body': ' '.join(lines)})
        if ctls:
            body = '; '.join('%s (%s): %s' % (sc(c['label'])[:60], sc(c['facts'].get('where', '')).replace('Pro > ', ''), deperson(sc(c['facts'].get('does', ''))).rstrip('.')) for c in ctls[:5])
            deep.append({'heading': 'The controls involved', 'body': _cap(body + '.', 1400)})
        whens = _uniq([re.sub(r'\bA buyer (says|wants|asks|does not)\b', lambda m: 'You ' + {'says': 'say', 'wants': 'want', 'asks': 'ask', 'does not': 'do not'}[m.group(1)], sc(c['facts'].get('when', ''))) for c in ctls])
        if whens:
            deep.append({'heading': 'When this comes up', 'body': _cap(' '.join(whens[:3]), 900)})
        for c in ctls[:2]:
            where = sc(c['facts'].get('where', '')).replace('Pro > ', '')
            if where:
                faq.append({'q': 'Where do I find %s?' % sc(c['label'])[:60], 'a': _cap('%s. %s' % (where[0].upper() + where[1:], deperson(sc(c['facts'].get('does', '')))), 360)})
        if whens:
            faq.append({'q': 'When should I use this?', 'a': _cap(whens[0], 300)})
        faq.append({'q': 'What do I need before I start?', 'a': ('You need ' + ' and '.join(needs) + ' first.') if needs else 'Nothing special: it works as soon as Shokker is open, in %s.' % MODE_SENT.get(mode, mode)})
        pit = _uniq([deperson(sc(c['facts'].get('mistakes', ''))) for c in ctls])
        a['pitfalls'] = _uniq(a['pitfalls'] + pit[:4])
        for c in ctls[:3]:
            art = ctx['ART'].get(c['id'])
            if art and art not in related:
                related.append(art)
        seen_c = set(ctls_id for ctls_id in [c['id'] for c in ctls])
        for c in ctls[:3]:
            for rid in (c['facts'].get('related') or [])[:2]:
                if rid in seen_c:
                    continue
                art, rr = ctx['ART'].get(rid), ctx['BYID'].get(rid)
                if art and rr and art not in [x['with'] for x in combos]:
                    combos.append({'with': art, 'why': _cap('%s: %s' % (sc(rr['label'])[:60], deperson(sc(rr['facts'].get('does', '')))), 260)})
        combos = combos[:3]
    else:
        # restructure long text: first sentences stay in what, the rest becomes deep sections
        if kind in ('support', 'guide') and slug not in WHAT_OVR:
            ss = _sent_split(a['what'])
            lead, rest = [], []
            n = 0
            for s in ss:
                if n < 360 or not lead:
                    lead.append(s); n += len(s) + 1
                else:
                    rest.append(s)
            if rest and len(' '.join(rest)) >= 60:
                a['what'] = ' '.join(lead)
                chunks, cur = [], []
                for s in rest:
                    cur.append(s)
                    if len(' '.join(cur)) > 420:
                        chunks.append(cur); cur = []
                if cur:
                    chunks.append(cur)
                heads = ['More detail', 'Also worth knowing', 'Going further', 'And then']
                for i, ch in enumerate(chunks[:4]):
                    deep.append({'heading': heads[i], 'body': ' '.join(ch)})
        if kind == 'topics':
            t = ctx['TOPIC'].get(rec['id'][6:]) or {}
            a['what'] = '%s: %d step%s, in the order you do them.' % (a['title'], len(a['how']), '' if len(a['how']) == 1 else 's')
            nd0 = [NEEDS_SENT[n] for n in (t.get('needs') or []) if n in NEEDS_SENT]
            if nd0:
                a['what'] += ' You need ' + ' and '.join(nd0) + ' first.'
            if t.get('needs'):
                nd = [NEEDS_SENT[n] for n in t['needs'] if n in NEEDS_SENT]
                if nd:
                    deep.append({'heading': 'Before you start', 'body': 'You need ' + ' and '.join(nd) + ' first.'})
                    faq.append({'q': 'What do I need before I start?', 'a': 'You need ' + ' and '.join(nd) + ' first.'})
            if t.get('say'):
                say = deperson(re.sub(r'\s+', ' ', t['say'])).strip()
                say = say[0].upper() + say[1:]
                deep.append({'heading': 'Or just ask in Chat', 'body': say.rstrip('.') + '.'})
                faq.append({'q': 'Can I do this by typing instead?', 'a': say.rstrip('.') + '.'})
        if kind == 'support':
            for q in ctx['NEXT'].get(rec['facts'].get('support_id'), [])[:3]:
                tgt = ctx['PAGE_BY_TITLE'].get(ctx['norm'](q))
                if tgt and tgt['id'] != '@' + kind + a['id']:
                    faq.append({'q': q.rstrip('?') + '?', 'a': _cap(tgt['summary'], 300)})
                    if tgt['id'] not in related:
                        related.append(tgt['id'])
    text = ' '.join([a['title'], a['summary']] + (a['how'] if kind in ('howto', 'topics') else [a['what'][:260]])).lower()
    a['faq'], a['mistakes'], a['protips'] = faq, mis, tips
    apply_lib(a, text)
    # scrub hidden-feature mentions from every new string
    a['deep'] = [d for d in ({'heading': d['heading'], 'body': sc(d['body'])} for d in deep) if d['body']]
    a['faq'] = [q for q in ({'q': sc(q['q']), 'a': sc(q['a'])} for q in a['faq']) if q['q'] and q['a']]
    a['mistakes'] = [m for m in ({'symptom': sc(m['symptom']), 'cause': sc(m['cause']), 'fix': sc(m['fix'])} for m in a['mistakes']) if m['symptom'] and m['cause'] and m['fix']]
    a['protips'] = [x for x in (sc(x) for x in a['protips']) if x]
    a['pitfalls'] = [x for x in (sc(x) for x in a['pitfalls']) if x]
    from enc_help_v3_links import HAND_REL
    hand = HAND_REL.get(kind + ':' + slug, [])
    related = [rid for rid, _ in hand] + related
    for rid, why in hand:
        if rid not in [x['with'] for x in combos]:
            combos.insert(0, {'with': rid, 'why': why})
    a['related'] = [x for x in _uniq(related) if x != a['id']][:7]
    if combos:
        a['combos'] = combos[:4]
    a['level'] = level_for(kind, rec, a['how'])
    for k in ('deep', 'faq', 'mistakes', 'protips'):
        if not a[k]:
            del a[k]
    return a

"""Phase 3 (owner rule 2026-10-04: Easy mode is hidden): rewrite the hand-written sentences that named it. Idempotent.
Each entry: (domain file, article id) -> {field: new value}. Lists are replaced whole. Run enc_hidden_apply.py afterwards to confirm nothing is left."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import enc_write_C as W

FIX = {
    ('ui_shell', 'ui_shell.mode_pill'): {
        'title': 'The PRO / CHAT pill: pick your door',
        'summary': 'Shokker has two ways in: PRO is the full shop and CHAT lets you type what you want. They both edit the same car, so you can switch any time.',
        'what': 'The pill sits in the top row. PRO gives you every control: zones, finishes, layers, masks, spec tools, sliders. CHAT is the Pro screen with the Shokker AI helper open so you can say "make the hood matte black" and watch it happen; it works with no key and gets smarter with one. Chat cannot do everything: it cannot import files, export or hand-paint, and every change it makes has an Undo button.',
        'when': ['You do not know which control to use and just know the look you want (try CHAT).',
                 'You want exact control, hand-drawn masks, layers or spec sliders (use PRO).'],
        'how': ['1. Find the PRO / CHAT pill in the top row.',
                '2. Click the mode you want. Your paint and zones stay as they are.',
                '3. To come back, click PRO. Nothing is lost by switching.'],
        'tips': ['New to Shokker? Start in CHAT, or turn on the Tutorial (Training Wheels) in PRO.'],
        'drop_controls': ['EASY'],
    },
    ('ui_shell', 'ui_shell.template_layer_views'): {
        'tips_replace': ('In Easy mode, the template guides card has a Turn off button for the same thing.',
                         'In the Layers tab, the eye on the group Turn Off Before Exporting TGA switches all the guides off at once.'),
    },
    ('workflows', 'workflows.pro_chat_easy'): {
        'id': 'workflows.pro_or_chat',
        'summary': 'PRO is the full paint shop and CHAT lets you type what you want; both edit the same car, so you can switch any time.',
        'what': 'The mode switch at the top has two entries: PRO and CHAT. Use PRO when you know what you want and want every control. Use CHAT when you would rather describe it. Both change the same zones and layer settings.',
        'pitfalls': ['Chat cannot render, save or export for you. Press RENDER yourself.'],
    },
    ('workflows', 'workflows.tutorial_quests'): {
        'pitfalls_replace': ('The old step-by-step Easy mode tutorial overlay was removed; the Tutorial button is the current guide.',
                             'The old step-by-step tutorial overlay was removed; the Tutorial button is the current guide.'),
    },
}

n = 0
for (dom, aid), edits in FIX.items():
    doc = W._load(dom)
    art = [a for a in doc['articles'] if a['id'] == aid or a['id'] == edits.get('id')]
    assert art, aid
    a = art[0]
    for k, v in edits.items():
        if k == 'drop_controls':
            a['controls'] = [c for c in a['controls'] if c['label'] not in v]
        elif k.endswith('_replace'):
            f = k[:-8]
            old, new = v
            a[f] = [new if x == old else x for x in a[f]]
        else:
            a[k] = v
    n += 1
    W._save(dom, doc)
print('fixed articles', n)

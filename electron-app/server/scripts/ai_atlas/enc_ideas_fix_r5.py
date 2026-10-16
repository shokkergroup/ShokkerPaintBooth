# -*- coding: utf-8 -*-
"""enc_ideas_fix_r5.py - ENC_READER_FIX round 2 (2026-10-05). Idempotent: re-apply after enc_ideas_build.py / enc_ideas_fix_r4.py.
Retro 90s promises "teal, purple and magenta splashes", but none of its finishes or patterns renders splashes (checked by eye on the
example car: Rave Zigzag = multicolour zigzag stripes, Geo Minimal = dark confetti, Y2K Chrome = liquid silver, Flannel = green plaid).
The catalogue's 'Radical: Splatter Tee' (teal, purple and pink thrown paint) IS that look, so the page now offers it (Do-it action + a step)
and its car picture (look_splatter_tee) belongs to the page. The batch generator enc_ideas_b03.py carries the same change.
Run: python scripts/ai_atlas/enc_ideas_fix_r5.py"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '..', '..', 'data', 'encyclopedia', 'ideas.json')
STEP = ("For the splash look in one go: Base Material Radical: Splatter Tee (fine teal, purple and pink thrown paint over a light base), "
        "BASE COLOR Use finish's own color.")
SRC = 'paint-booth-0-finish-data.js:359'

import sys
sys.path.insert(0, HERE)
import enc_reader_fix as RF          # same format-preserving loader / writer the post-pass uses
d, src, crlf = RF.load(P)
fmt = RF.fmt_of(src, d)
assert fmt is not None, 'ideas.json format not recognised - refusing to rewrite it'
n = 0
for a in d['articles']:
    if a.get('id') != 'ideas.retro_90s':
        continue
    if not any(x.get('id') == 'base::rad_splatter_tee' for x in a.get('actions') or []):
        acts = a['actions']
        i = 1 if acts and acts[0].get('id') == 'base::gloss' else 0      # keep Gloss as the first (default) Do-it
        acts.insert(i, {'do': 'finish', 'id': 'base::rad_splatter_tee'}); n += 1
    if STEP not in a['how']:
        a['how'].insert(len(a['how']) - 1, STEP); n += 1
    if SRC not in a.get('sources', []):
        a.setdefault('sources', []).insert(0, SRC); n += 1
if n:
    RF.save(P, d, src, crlf, fmt)
print('enc_ideas_fix_r5: %d change(s)' % n)

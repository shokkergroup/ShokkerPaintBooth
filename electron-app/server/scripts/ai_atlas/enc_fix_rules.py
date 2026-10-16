# -*- coding: utf-8 -*-
"""enc_fix_rules.py - literal (old, new) text rules for the 9 corrections the APP-IQ exam found in the Encyclopedia (lane ENC-FIX, 2026-10-10).

Source list: _easy_claude_work/eval/app_iq/ENC_FIXES.jsonl.  Every rule cites the code line it was checked against.
enc_ui_fix.py appends ENCFIX_RULES to its RULES, so every generator that calls fix_articles() (enc_gen_A, enc_gen_B, ...) and the
`enc_ui_fix.py` CLI keep the corrected wording; _easy_claude_work/enc_fix/apply_fixes.py applies the same rules to the files on disk.
Idempotent: no new text contains its own old text.  Only edit by adding pairs; keep each one literal.
"""

# --- 1. There is NO zone-wide "Colour tolerance" slider.  Each picked colour chip has its own Exact <-> Loose "Color Match" slider, 0-100 (0 = exact shade only),
#        new picks start at 40.  paint-booth-2-state-zones.js:1793-1797 (zone-level TOL slider removed, SPB-SIMPLIFY-2026-07-18) and :1490-1499 (per-chip slider).
_TOL_DOES = ('How many nearby shades of the picked colour the zone grabs. Slide toward Exact for only that shade, toward Loose for lighter, darker and similar shades too '
             '(about 30-50 is normal). Every picked colour chip has its own slider; there is no zone-wide one.')
_TOL_RANGE = '0-100 on each picked colour chip (0 = exact shade only); default 40'
TOLERANCE = [
    ('Colour tolerance (sliders next to the colour chips)', 'Color Match (the Exact to Loose slider on each picked colour chip)'),
    ('How close a pixel must be to the picked colour to belong to the zone (about 30-50 normal; 6 = exact shade, 100 = loose).', _TOL_DOES),
    ('How close a pixel must be to the picked colour to belong to the zone (about 30-50 normal; 6 = exact shade, 100 = loose)', _TOL_DOES.rstrip('.')),
    ('How close a pixel must be to the picked colour to belong to the zone (about...', 'How many nearby shades of the picked colour the zone grabs (Exact = only that shade, Loose = similar shades too)...'),
    ('tolerance 6-100 (kit) / 0-100 (UI per colour); default 40', _TOL_RANGE),
    ('tolerance 6-100 / 0-100; default 40', _TOL_RANGE),
    ('Works together with the Colour tolerance control.', 'Works together with the Color Match slider on each picked colour chip.'),
    ('raise the zone\'s colour tolerance', 'slide the chip\'s Color Match toward Loose'),
    ('raise the colour tolerance', 'slide Color Match toward Loose'),
    ('Raise the colour tolerance', 'Slide Color Match toward Loose'),
    ('Keep the tolerance low (about 10 to 16),', "Keep the chip's Color Match slider near Exact (about 10 to 16),"),
]

# --- 2/3. A pattern's Spec amount is independent of paint Opacity and Strength (engine/pattern_material.py:3-5; js/zones/pattern-transform-controls.js:12, default 0).
PATTERN_SPEC = [
    ('Pattern: Opacity fades the pattern colour. The shine it adds fades with it only when the pattern has a spec amount above 0.',
     'Pattern: Opacity fades the pattern colour only. The shine a pattern adds comes from its own Spec amount slider (it starts at 0), which does not change with paint Opacity or Strength.'),
    ('Pattern Opacity (the PATTERN section of a zone) fades the pattern in the paint, and it also scales the shine the pattern adds through its separate spec amount, which starts at 0; the base finish keeps its own shine.',
     'Pattern Opacity (the PATTERN section of a zone) fades the pattern in the paint only. The shine a pattern adds comes from its own Spec amount slider, which starts at 0 and is independent of paint Opacity and Strength; the base finish keeps its own shine.'),
    ('Pattern Opacity fades the pattern colour and, if the pattern spec amount is above 0, the shine the pattern adds.',
     'Pattern Opacity fades the pattern colour only; the shine a pattern adds is set by its own Spec amount slider, which is independent of paint Opacity and Strength.'),
    ('It fades the pattern colour, and the shine the pattern adds fades with it when the pattern has a spec amount above 0. The base finish keeps its own shine.',
     'It fades the pattern colour only. The shine a pattern adds comes from its Spec amount slider (it starts at 0), which is independent of Opacity and Strength. The base finish keeps its own shine.'),
    ('Pattern Opacity fades the pattern colour, and the shine the pattern adds fades with it when its spec amount is above 0. The base finish keeps its own shine.',
     'Pattern Opacity fades the pattern colour only. The shine a pattern adds comes from its Spec amount slider, which is independent of paint Opacity and Strength. The base finish keeps its own shine.'),
    ('Pattern effect in paint and spec: 0 removes the effect.',
     'Pattern paint strength: 0 removes the pattern\'s paint effect. The shine it adds is set separately by the Spec amount slider.'),
    ('opacity fades the pattern, strength scales its paint/spec effect.',
     'opacity fades the pattern, strength scales its paint strength; the shine it adds comes from the separate Spec amount slider.'),
]

# --- 4. The cap is 5 spec overlays PER BASE; the primary base and each of the 2nd to 5th base layers has its own stack of five.
#        js/spec-overlays/picker.js:5 (five stack keys) and :49,60,72 ("Maximum 5 spec overlays per base").
SPEC_OVERLAY_CAP = [
    ('and you can stack up to 5 of them per zone.', 'and each base in a zone (the primary and the 2nd to 5th base layers) can carry its own stack of up to 5 of them.'),
    ('a texture that only touches the shine, up to five stacked in a zone.', 'a texture that only touches the shine, up to five stacked on each base layer of a zone.'),
    ('up to four more base overlays and up to five spec overlays can share a zone.', 'up to four more base overlays and up to five spec overlays on each of those bases can share a zone.'),
    ('Then up to five spec overlays add surface detail only to the spec', 'Then up to five spec overlays per base add surface detail only to the spec'),
    ('There are at most five pattern layers and five spec overlays per zone,', 'There are at most five pattern layers per zone and five spec overlays per base (each of a zone\'s five bases has its own stack),'),
    ('Stack up to five per zone in SPEC OVERLAYS and tune each one.', 'Stack up to five per base in SPEC OVERLAYS and tune each one.'),
    ('You can stack up to five. Each layer has', 'You can stack up to five per base: the primary base and each of the 2nd to 5th base layers has its own stack of five. Each layer has'),
    ('Stack up to five spec overlays per zone and use the spec views to see them.', 'Stack up to five spec overlays per base and use the spec views to see them.'),
    ('Overlay stacks combine up to five per zone', 'Overlay stacks combine up to five per base'),
    ('layers detail directly onto the M, R, and CC channels — independently, up to five stacked.', 'layers detail directly onto the M, R, and CC channels — independently, up to five stacked on each base.'),
]

# --- 6/7. The ZIP is written into the render's own job folder and offered as a download link; it is never pushed into the iRacing car folder.
#          With the iRacing Car Folder set, EVERY render already saves its TGAs there; Auto-Deploy (Live Link) is only a second, optional push.
#          server.py:6051 (zip -> job_dir), :6161 / :6346 (zip_url), :6167-6168 (files_to_push = TGAs), :6260 (PRIMARY output-dir push), :6289-6311 (Live Link SECONDARY).
SETTINGS = [
    ('a zip with the paint TGA, the spec TGA and a preview in your output folder.',
     "a zip with the paint TGA, the spec TGA and a preview in that render's own job folder, with a download link under the render."),
    ('Bundles paint TGA, spec TGA and preview into one ZIP on every render, in your output folder.',
     'Builds one ZIP of paint TGA, spec TGA and preview on every render. The ZIP stays in that render\'s own job folder and is offered as a Download ZIP Package link under the render; it is never copied into the iRacing car folder, which only receives the TGA files.'),
    ('Every render is bundled in a ZIP in your output folder, and nothing is copied into iRacing until you switch Auto-Deploy on.',
     'Every render makes a ZIP in its own job folder, with a download link under the render. Nothing reaches iRacing while the iRacing Car Folder box in the header is empty; with a car folder set, every render copies its TGAs there whether Auto-Deploy is on or off.'),
    ('Keep Auto-deploy off while experimenting and turn it on when you are happy, to avoid overwriting a paint you like in iRacing.',
     'To avoid overwriting a paint you like in iRacing while you experiment, leave the iRacing Car Folder box in the header empty and Auto-deploy off. As soon as a car folder is set, every render is copied into it, whether Auto-deploy is on or not.'),
    ('Auto-Deploy was on while you were testing',
     'The iRacing Car Folder was set while you were testing (every render is copied into it), or Auto-Deploy was on'),
    ('Turn Auto-Deploy off while experimenting and on when you are happy.',
     'Clear the iRacing Car Folder box and keep Auto-Deploy off while experimenting; set the folder again when you are happy.'),
    ('Auto-Deploy to iRacing copies each render into your car folder.',
     'Auto-Deploy to iRacing is only a second, optional push of each render, to the visible iRacing Car Folder or a saved active car; a car folder set in the header is already filled by every render without it.'),
    ('Auto-Deploy copies each render into your iRacing car folder;',
     'Auto-Deploy is only a second, optional push (an iRacing Car Folder set in the header already receives every render);'),
    ('Export ZIP Package adds a ZIP with the paint TGA, spec TGA and preview on every render;',
     'Export ZIP Package adds a ZIP with the paint TGA, spec TGA and preview on every render (kept in the render\'s job folder, with a download link);'),
    ('Copies each render to your iRacing car folder automatically.',
     'A second, optional push of each render to the visible iRacing Car Folder or a saved active car; a car folder set in the header already receives every render without it.'),
    ('Auto-deploy: copies every render to your iRacing car folder automatically',
     'Auto-deploy: a second, optional push of each render to your iRacing car folder (a car folder set in the header already gets every render)'),
]

ENCFIX_RULES = TOLERANCE + PATTERN_SPEC + SPEC_OVERLAY_CAP + SETTINGS

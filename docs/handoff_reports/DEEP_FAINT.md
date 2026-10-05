# DEEP-FAINT (2026-10-03)
Script: _atlas_deep/render_faint.py (pics in _atlas_deep/img2/<type>/; spec units *_raw.png = contrast-stretched M|R|Cc of the engine spec map, 3x). Cards rewritten via append.py --replace.
- 48 low-conf units re-rendered, 47 rewritten (infinite_finish: spec fn signature error, not rewritten). Confidence 2/1 -> 3:27, 4:17, 2:4 (spiral_fern, triple_knot, voronoi_relaxed, infinite_finish).
- Plus 18 faint conf-3 spec units: 3 -> 4 (17), 5 (cc_panel_fade).
- Lit zoom of specs stayed unreadable even boosted; the raw stretched spec map is the readable view.
- Not re-done: other cards fields (asks/not) of changed-identity items (zebra, hex_circuit, cane_weave, barbed_wire, art_deco_chevron, skull_wings, fte_lichtenberg_crown) still carry old-name asks; only look_close/look_far/confidence/qa_fix were rewritten. build_cards_js not run.
- Trap: spiral_fern, triple_knot, art_deco_chevron render byte-identical (probable engine fallback).

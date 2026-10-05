# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.17; invariant nearest 0.47053 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Celtic Triskeles. Identity declared before rendering/scoring."""
from ..engraved_designs import celtic_triskeles
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_celtic_triskeles',
 'display_name': 'Celtic Triskeles - spec overlay',
 'promise': 'Celtic Triskeles assembles three spiral bands, spiral outer bevels, interlace underpass '
            'breaks, central binding knot and engraver endpoint beads.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Celtic Triskeles assembles three spiral bands, spiral outer bevels, interlace '
                    'underpass breaks, central binding knot and engraver endpoint beads. Geometry is '
                    'independently authored in engraved_designs.py:celtic_triskeles.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to three spiral bands, spiral '
                 'outer bevels, interlace underpass breaks, central binding knot, engraver endpoint '
                 'beads.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'three_spiral_bands',
                 'role': 'Three spiral bands use M/R/Cc intervals [(18, 246), (0, 255), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'spiral_outer_bevels',
                 'role': 'Spiral outer bevels use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'interlace_underpass_breaks',
                 'role': 'Interlace underpass breaks use M/R/Cc intervals [(0, 100), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'central_binding_knot',
                 'role': 'Central binding knot use M/R/Cc intervals [(56, 206), (102, 232), (68, 212)] '
                         'in their own geometry.'},
                {'name': 'engraver_endpoint_beads',
                 'role': 'Engraver endpoint beads use M/R/Cc intervals [(96, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['three_spiral_bands',
                            'spiral_outer_bevels',
                            'interlace_underpass_breaks',
                            'central_binding_knot',
                            'engraver_endpoint_beads'],
                      'R': ['three_spiral_bands',
                            'spiral_outer_bevels',
                            'interlace_underpass_breaks',
                            'central_binding_knot',
                            'engraver_endpoint_beads'],
                      'Cc': ['three_spiral_bands',
                             'spiral_outer_bevels',
                             'interlace_underpass_breaks',
                             'central_binding_knot',
                             'engraver_endpoint_beads']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Celtic Triskeles must visibly separate through three spiral '
                                      'bands, spiral outer bevels, interlace underpass breaks and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Celtic Triskeles must visibly separate through three spiral '
                                      'bands, spiral outer bevels, interlace underpass breaks and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three connected spiral traces have distinct interrupted '
                                     'underpasses.',
                                     'three spiral bands is present in the native named-feature '
                                     'coverage probe.',
                                     'spiral outer bevels is present in the native named-feature '
                                     'coverage probe.',
                                     'interlace underpass breaks is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/celtic_triskeles/independent-feature-carrier',
 'spec_key': 'spec-v2/celtic_triskeles/named-material-bindings'}

render = build_renderer(celtic_triskeles, IDENTITY_CONTRACT)

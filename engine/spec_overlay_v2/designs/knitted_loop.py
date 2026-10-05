# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.75; invariant nearest 0.53638 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Knitted Loop. Identity declared before rendering/scoring."""
from ..weave_designs import knitted_loop
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_knitted_loop',
 'display_name': 'Knitted Loop - spec overlay',
 'promise': 'Knitted Loop assembles loop shoulders, crossed loop legs, underpass knots, loop inner '
            'filaments and loose stitch tails.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Knitted Loop assembles loop shoulders, crossed loop legs, underpass knots, loop '
                    'inner filaments and loose stitch tails. Geometry is independently authored in '
                    'weave_designs.py:knitted_loop.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to loop shoulders, crossed loop '
                 'legs, underpass knots, loop inner filaments, loose stitch tails.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'loop_shoulders',
                 'role': 'Loop shoulders use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in their '
                         'own geometry.'},
                {'name': 'crossed_loop_legs',
                 'role': 'Crossed loop legs use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'underpass_knots',
                 'role': 'Underpass knots use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'loop_inner_filaments',
                 'role': 'Loop inner filaments use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'loose_stitch_tails',
                 'role': 'Loose stitch tails use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['loop_shoulders',
                            'crossed_loop_legs',
                            'underpass_knots',
                            'loop_inner_filaments',
                            'loose_stitch_tails'],
                      'R': ['loop_shoulders',
                            'crossed_loop_legs',
                            'underpass_knots',
                            'loop_inner_filaments',
                            'loose_stitch_tails'],
                      'Cc': ['loop_shoulders',
                             'crossed_loop_legs',
                             'underpass_knots',
                             'loop_inner_filaments',
                             'loose_stitch_tails']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Knitted Loop must visibly separate through loop shoulders, '
                                      'crossed loop legs, underpass knots and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Knitted Loop must visibly separate through loop shoulders, '
                                      'crossed loop legs, underpass knots and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Curved knit ribs flank alternating crossed knit legs and open '
                                     'purl loops, joined through reinforced shoulders.',
                                     'loop shoulders is present in the native named-feature coverage '
                                     'probe.',
                                     'crossed loop legs is present in the native named-feature coverage '
                                     'probe.',
                                     'underpass knots is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/knitted_loop/independent-feature-carrier',
 'spec_key': 'spec-v2/knitted_loop/named-material-bindings'}

render = build_renderer(knitted_loop, IDENTITY_CONTRACT)

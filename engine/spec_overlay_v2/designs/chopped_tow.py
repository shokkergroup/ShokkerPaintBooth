# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.48; invariant nearest 0.32405 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Chopped Tow. Identity declared before rendering/scoring."""
from ..weave_designs import chopped_tow
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_chopped_tow',
 'display_name': 'Chopped Tow - spec overlay',
 'promise': 'Chopped Tow assembles angular tow chips, split bundle edges, epoxy windows, crossing '
            'offcuts and torn fiber ends.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Chopped Tow assembles angular tow chips, split bundle edges, epoxy windows, '
                    'crossing offcuts and torn fiber ends. Geometry is independently authored in '
                    'weave_designs.py:chopped_tow.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to angular tow chips, split '
                 'bundle edges, epoxy windows, crossing offcuts, torn fiber ends.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'angular_tow_chips',
                 'role': 'Angular tow chips use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'split_bundle_edges',
                 'role': 'Split bundle edges use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'epoxy_windows',
                 'role': 'Epoxy windows use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in their '
                         'own geometry.'},
                {'name': 'crossing_offcuts',
                 'role': 'Crossing offcuts use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'torn_fiber_ends',
                 'role': 'Torn fiber ends use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['angular_tow_chips',
                            'split_bundle_edges',
                            'epoxy_windows',
                            'crossing_offcuts',
                            'torn_fiber_ends'],
                      'R': ['angular_tow_chips',
                            'split_bundle_edges',
                            'epoxy_windows',
                            'crossing_offcuts',
                            'torn_fiber_ends'],
                      'Cc': ['angular_tow_chips',
                             'split_bundle_edges',
                             'epoxy_windows',
                             'crossing_offcuts',
                             'torn_fiber_ends']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Chopped Tow must visibly separate through angular tow chips, '
                                      'split bundle edges, epoxy windows and the remaining named marks, '
                                      'not color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Chopped Tow must visibly separate through angular tow chips, '
                                      'split bundle edges, epoxy windows and the remaining named marks, '
                                      'not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Short comb-like tow packets cross at different directions.',
                                     'angular tow chips is present in the native named-feature coverage '
                                     'probe.',
                                     'split bundle edges is present in the native named-feature '
                                     'coverage probe.',
                                     'epoxy windows is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/chopped_tow/independent-feature-carrier',
 'spec_key': 'spec-v2/chopped_tow/named-material-bindings'}

render = build_renderer(chopped_tow, IDENTITY_CONTRACT)

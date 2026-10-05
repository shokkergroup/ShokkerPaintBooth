# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 95.75; invariant nearest 0.45078 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Fractal Seeds. Identity declared before rendering/scoring."""
from ..experimental_designs import fractal_seeds
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_fractal_seeds',
 'display_name': 'Fractal Seeds - spec overlay',
 'promise': 'Fractal Seeds assembles recursive triangle plates, three seed vertex nodes, central '
            'triangle voids, recursive edge notches and seed bridge witnesses.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Fractal Seeds assembles recursive triangle plates, three seed vertex nodes, '
                    'central triangle voids, recursive edge notches and seed bridge witnesses. Geometry '
                    'is independently authored in experimental_designs.py:fractal_seeds.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to recursive triangle plates, '
                 'three seed vertex nodes, central triangle voids, recursive edge notches, seed bridge '
                 'witnesses.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'recursive_triangle_plates',
                 'role': 'Recursive triangle plates use M/R/Cc intervals [(18, 246), (0, 246), (24, '
                         '248)] in their own geometry.'},
                {'name': 'three_seed_vertex_nodes',
                 'role': 'Three seed vertex nodes use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'central_triangle_voids',
                 'role': 'Central triangle voids use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'recursive_edge_notches',
                 'role': 'Recursive edge notches use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'seed_bridge_witnesses',
                 'role': 'Seed bridge witnesses use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['recursive_triangle_plates',
                            'three_seed_vertex_nodes',
                            'central_triangle_voids',
                            'recursive_edge_notches',
                            'seed_bridge_witnesses'],
                      'R': ['recursive_triangle_plates',
                            'three_seed_vertex_nodes',
                            'central_triangle_voids',
                            'recursive_edge_notches',
                            'seed_bridge_witnesses'],
                      'Cc': ['recursive_triangle_plates',
                             'three_seed_vertex_nodes',
                             'central_triangle_voids',
                             'recursive_edge_notches',
                             'seed_bridge_witnesses']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Fractal Seeds must visibly separate through recursive triangle '
                                      'plates, three seed vertex nodes, central triangle voids and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Fractal Seeds must visibly separate through recursive triangle '
                                      'plates, three seed vertex nodes, central triangle voids and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three nested triangular seed generations retain separate internal '
                                     'voids.',
                                     'recursive triangle plates is present in the native named-feature '
                                     'coverage probe.',
                                     'three seed vertex nodes is present in the native named-feature '
                                     'coverage probe.',
                                     'central triangle voids is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/fractal_seeds/independent-feature-carrier',
 'spec_key': 'spec-v2/fractal_seeds/named-material-bindings'}

render = build_renderer(fractal_seeds, IDENTITY_CONTRACT)

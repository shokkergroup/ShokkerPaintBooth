# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.08; invariant nearest 0.53772 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Tensegrity Cells. Identity declared before rendering/scoring."""
from ..experimental_designs import tensegrity_cells
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_tensegrity_cells',
 'display_name': 'Tensegrity Cells - spec overlay',
 'promise': 'Tensegrity Cells assembles compression strut pairs, tension cable triangles, floating '
            'joint recesses, anchored strut collars and cable clamp tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Tensegrity Cells assembles compression strut pairs, tension cable triangles, '
                    'floating joint recesses, anchored strut collars and cable clamp tabs. Geometry is '
                    'independently authored in experimental_designs.py:tensegrity_cells.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to compression strut pairs, '
                 'tension cable triangles, floating joint recesses, anchored strut collars, cable clamp '
                 'tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'compression_strut_pairs',
                 'role': 'Compression strut pairs use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'tension_cable_triangles',
                 'role': 'Tension cable triangles use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'floating_joint_recesses',
                 'role': 'Floating joint recesses use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'anchored_strut_collars',
                 'role': 'Anchored strut collars use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'cable_clamp_tabs',
                 'role': 'Cable clamp tabs use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['compression_strut_pairs',
                            'tension_cable_triangles',
                            'floating_joint_recesses',
                            'anchored_strut_collars',
                            'cable_clamp_tabs'],
                      'R': ['compression_strut_pairs',
                            'tension_cable_triangles',
                            'floating_joint_recesses',
                            'anchored_strut_collars',
                            'cable_clamp_tabs'],
                      'Cc': ['compression_strut_pairs',
                             'tension_cable_triangles',
                             'floating_joint_recesses',
                             'anchored_strut_collars',
                             'cable_clamp_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Tensegrity Cells must visibly separate through compression strut '
                                      'pairs, tension cable triangles, floating joint recesses and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Tensegrity Cells must visibly separate through compression strut '
                                      'pairs, tension cable triangles, floating joint recesses and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Disjoint compression bars are tied by fine cable loops.',
                                     'compression strut pairs is present in the native named-feature '
                                     'coverage probe.',
                                     'tension cable triangles is present in the native named-feature '
                                     'coverage probe.',
                                     'floating joint recesses is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/tensegrity_cells/independent-feature-carrier',
 'spec_key': 'spec-v2/tensegrity_cells/named-material-bindings'}

render = build_renderer(tensegrity_cells, IDENTITY_CONTRACT)

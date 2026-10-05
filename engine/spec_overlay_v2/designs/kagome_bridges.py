# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.87; invariant nearest 0.53922 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Kagome Bridges. Identity declared before rendering/scoring."""
from ..experimental_designs import kagome_bridges
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_kagome_bridges',
 'display_name': 'Kagome Bridges - spec overlay',
 'promise': 'Kagome Bridges assembles trihexagonal ligaments, three way bond knots, recessed hex '
            'windows, bridge stress gussets and bonded corner tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Kagome Bridges assembles trihexagonal ligaments, three way bond knots, recessed '
                    'hex windows, bridge stress gussets and bonded corner tabs. Geometry is '
                    'independently authored in experimental_designs.py:kagome_bridges.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to trihexagonal ligaments, '
                 'three way bond knots, recessed hex windows, bridge stress gussets, bonded corner '
                 'tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'trihexagonal_ligaments',
                 'role': 'Trihexagonal ligaments use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'three_way_bond_knots',
                 'role': 'Three way bond knots use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'recessed_hex_windows',
                 'role': 'Recessed hex windows use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'bridge_stress_gussets',
                 'role': 'Bridge stress gussets use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'bonded_corner_tabs',
                 'role': 'Bonded corner tabs use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['trihexagonal_ligaments',
                            'three_way_bond_knots',
                            'recessed_hex_windows',
                            'bridge_stress_gussets',
                            'bonded_corner_tabs'],
                      'R': ['trihexagonal_ligaments',
                            'three_way_bond_knots',
                            'recessed_hex_windows',
                            'bridge_stress_gussets',
                            'bonded_corner_tabs'],
                      'Cc': ['trihexagonal_ligaments',
                             'three_way_bond_knots',
                             'recessed_hex_windows',
                             'bridge_stress_gussets',
                             'bonded_corner_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Kagome Bridges must visibly separate through trihexagonal '
                                      'ligaments, three way bond knots, recessed hex windows and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Kagome Bridges must visibly separate through trihexagonal '
                                      'ligaments, three way bond knots, recessed hex windows and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Triangular kagome bridge units surround open junctions.',
                                     'trihexagonal ligaments is present in the native named-feature '
                                     'coverage probe.',
                                     'three way bond knots is present in the native named-feature '
                                     'coverage probe.',
                                     'recessed hex windows is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/kagome_bridges/independent-feature-carrier',
 'spec_key': 'spec-v2/kagome_bridges/named-material-bindings'}

render = build_renderer(kagome_bridges, IDENTITY_CONTRACT)

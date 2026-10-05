# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.34; invariant nearest 0.49466 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Barite Petals. Identity declared before rendering/scoring."""
from ..crystal_designs import barite_petals
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_barite_petals',
 'display_name': 'Barite Petals - spec overlay',
 'promise': 'Barite Petals assembles tabular petal faces, crossing crystal blades, petal growth rims, '
            'matrix pockets and cleaved petal tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Barite Petals assembles tabular petal faces, crossing crystal blades, petal growth '
                    'rims, matrix pockets and cleaved petal tips. Geometry is independently authored in '
                    'crystal_designs.py:barite_petals.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to tabular petal faces, '
                 'crossing crystal blades, petal growth rims, matrix pockets, cleaved petal tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'tabular_petal_faces',
                 'role': 'Tabular petal faces use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'crossing_crystal_blades',
                 'role': 'Crossing crystal blades use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'petal_growth_rims',
                 'role': 'Petal growth rims use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'matrix_pockets',
                 'role': 'Matrix pockets use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'cleaved_petal_tips',
                 'role': 'Cleaved petal tips use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['tabular_petal_faces',
                            'crossing_crystal_blades',
                            'petal_growth_rims',
                            'matrix_pockets',
                            'cleaved_petal_tips'],
                      'R': ['tabular_petal_faces',
                            'crossing_crystal_blades',
                            'petal_growth_rims',
                            'matrix_pockets',
                            'cleaved_petal_tips'],
                      'Cc': ['tabular_petal_faces',
                             'crossing_crystal_blades',
                             'petal_growth_rims',
                             'matrix_pockets',
                             'cleaved_petal_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Barite Petals must visibly separate through tabular petal faces, '
                                      'crossing crystal blades, petal growth rims and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Barite Petals must visibly separate through tabular petal faces, '
                                      'crossing crystal blades, petal growth rims and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Five overlapping tabular petals form an open mineral fan, with '
                                     'distinct stepped outer edges and a matrix root.',
                                     'tabular petal faces is present in the native named-feature '
                                     'coverage probe.',
                                     'crossing crystal blades is present in the native named-feature '
                                     'coverage probe.',
                                     'petal growth rims is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/barite_petals/independent-feature-carrier',
 'spec_key': 'spec-v2/barite_petals/named-material-bindings'}

render = build_renderer(barite_petals, IDENTITY_CONTRACT)

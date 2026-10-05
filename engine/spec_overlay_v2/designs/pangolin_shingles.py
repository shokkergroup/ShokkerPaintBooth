# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.09; invariant nearest 0.52271 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Pangolin Shingles. Identity declared before rendering/scoring."""
from ..skin_designs import pangolin_shingles
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_pangolin_shingles',
 'display_name': 'Pangolin Shingles - spec overlay',
 'promise': 'Pangolin Shingles assembles keratin shingles, scale overlap rims, growth furrows, '
            'protected scale roots and polished scale tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Pangolin Shingles assembles keratin shingles, scale overlap rims, growth furrows, '
                    'protected scale roots and polished scale tips. Geometry is independently authored '
                    'in skin_designs.py:pangolin_shingles.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to keratin shingles, scale '
                 'overlap rims, growth furrows, protected scale roots, polished scale tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'keratin_shingles',
                 'role': 'Keratin shingles use M/R/Cc intervals [(18, 246), (28, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'scale_overlap_rims',
                 'role': 'Scale overlap rims use M/R/Cc intervals [(138, 255), (16, 102), (0, 106)] in '
                         'their own geometry.'},
                {'name': 'growth_furrows',
                 'role': 'Growth furrows use M/R/Cc intervals [(46, 188), (124, 242), (112, 252)] in '
                         'their own geometry.'},
                {'name': 'protected_scale_roots',
                 'role': 'Protected scale roots use M/R/Cc intervals [(0, 104), (174, 255), (160, 254)] '
                         'in their own geometry.'},
                {'name': 'polished_scale_tips',
                 'role': 'Polished scale tips use M/R/Cc intervals [(176, 255), (12, 80), (60, 196)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['keratin_shingles',
                            'scale_overlap_rims',
                            'growth_furrows',
                            'protected_scale_roots',
                            'polished_scale_tips'],
                      'R': ['keratin_shingles',
                            'scale_overlap_rims',
                            'growth_furrows',
                            'protected_scale_roots',
                            'polished_scale_tips'],
                      'Cc': ['keratin_shingles',
                             'scale_overlap_rims',
                             'growth_furrows',
                             'protected_scale_roots',
                             'polished_scale_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Pangolin Shingles must visibly separate through keratin '
                                      'shingles, scale overlap rims, growth furrows and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Pangolin Shingles must visibly separate through keratin '
                                      'shingles, scale overlap rims, growth furrows and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Curved keratin shingles overlap protected roots and polished '
                                     'tips.',
                                     'keratin shingles is present in the native named-feature coverage '
                                     'probe.',
                                     'scale overlap rims is present in the native named-feature '
                                     'coverage probe.',
                                     'growth furrows is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/pangolin_shingles/independent-feature-carrier',
 'spec_key': 'spec-v2/pangolin_shingles/named-material-bindings'}

render = build_renderer(pangolin_shingles, IDENTITY_CONTRACT)

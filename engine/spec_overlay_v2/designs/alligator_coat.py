# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.87; invariant nearest 0.54228 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Alligator Coat. Identity declared before rendering/scoring."""
from ..crack_designs import alligator_coat
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_alligator_coat',
 'display_name': 'Alligator Coat - spec overlay',
 'promise': 'Alligator Coat assembles aged coating blocks, deep coat channels, curled block shoulders, '
            'secondary cross checks and exposed corner chips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Alligator Coat assembles aged coating blocks, deep coat channels, curled block '
                    'shoulders, secondary cross checks and exposed corner chips. Geometry is '
                    'independently authored in crack_designs.py:alligator_coat.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to aged coating blocks, deep '
                 'coat channels, curled block shoulders, secondary cross checks, exposed corner chips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'aged_coating_blocks',
                 'role': 'Aged coating blocks use M/R/Cc intervals [(18, 244), (26, 216), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'deep_coat_channels',
                 'role': 'Deep coat channels use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'curled_block_shoulders',
                 'role': 'Curled block shoulders use M/R/Cc intervals [(146, 255), (16, 108), (0, 112)] '
                         'in their own geometry.'},
                {'name': 'secondary_cross_checks',
                 'role': 'Secondary cross checks use M/R/Cc intervals [(56, 204), (100, 230), (68, '
                         '204)] in their own geometry.'},
                {'name': 'exposed_corner_chips',
                 'role': 'Exposed corner chips use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['aged_coating_blocks',
                            'deep_coat_channels',
                            'curled_block_shoulders',
                            'secondary_cross_checks',
                            'exposed_corner_chips'],
                      'R': ['aged_coating_blocks',
                            'deep_coat_channels',
                            'curled_block_shoulders',
                            'secondary_cross_checks',
                            'exposed_corner_chips'],
                      'Cc': ['aged_coating_blocks',
                             'deep_coat_channels',
                             'curled_block_shoulders',
                             'secondary_cross_checks',
                             'exposed_corner_chips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Alligator Coat must visibly separate through aged coating '
                                      'blocks, deep coat channels, curled block shoulders and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Alligator Coat must visibly separate through aged coating '
                                      'blocks, deep coat channels, curled block shoulders and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Aged coating blocks show curled shoulders and secondary checks.',
                                     'aged coating blocks is present in the native named-feature '
                                     'coverage probe.',
                                     'deep coat channels is present in the native named-feature '
                                     'coverage probe.',
                                     'curled block shoulders is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/alligator_coat/independent-feature-carrier',
 'spec_key': 'spec-v2/alligator_coat/named-material-bindings'}

render = build_renderer(alligator_coat, IDENTITY_CONTRACT)

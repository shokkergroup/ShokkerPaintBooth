# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.39; invariant nearest 0.51465 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Wrinkled Lacquer. Identity declared before rendering/scoring."""
from ..crack_designs import wrinkled_lacquer
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_wrinkled_lacquer',
 'display_name': 'Wrinkled Lacquer - spec overlay',
 'promise': 'Wrinkled Lacquer assembles compressed lacquer ridges, fold crest splits, polished wrinkle '
            'shoulders, cross fold creases and trapped coat bubbles.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Wrinkled Lacquer assembles compressed lacquer ridges, fold crest splits, polished '
                    'wrinkle shoulders, cross fold creases and trapped coat bubbles. Geometry is '
                    'independently authored in crack_designs.py:wrinkled_lacquer.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to compressed lacquer ridges, '
                 'fold crest splits, polished wrinkle shoulders, cross fold creases, trapped coat '
                 'bubbles.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'compressed_lacquer_ridges',
                 'role': 'Compressed lacquer ridges use M/R/Cc intervals [(18, 246), (22, 218), (24, '
                         '248)] in their own geometry.'},
                {'name': 'fold_crest_splits',
                 'role': 'Fold crest splits use M/R/Cc intervals [(0, 102), (174, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'polished_wrinkle_shoulders',
                 'role': 'Polished wrinkle shoulders use M/R/Cc intervals [(148, 255), (16, 110), (0, '
                         '114)] in their own geometry.'},
                {'name': 'cross_fold_creases',
                 'role': 'Cross fold creases use M/R/Cc intervals [(56, 206), (100, 230), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'trapped_coat_bubbles',
                 'role': 'Trapped coat bubbles use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['compressed_lacquer_ridges',
                            'fold_crest_splits',
                            'polished_wrinkle_shoulders',
                            'cross_fold_creases',
                            'trapped_coat_bubbles'],
                      'R': ['compressed_lacquer_ridges',
                            'fold_crest_splits',
                            'polished_wrinkle_shoulders',
                            'cross_fold_creases',
                            'trapped_coat_bubbles'],
                      'Cc': ['compressed_lacquer_ridges',
                             'fold_crest_splits',
                             'polished_wrinkle_shoulders',
                             'cross_fold_creases',
                             'trapped_coat_bubbles']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Wrinkled Lacquer must visibly separate through compressed '
                                      'lacquer ridges, fold crest splits, polished wrinkle shoulders '
                                      'and the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Wrinkled Lacquer must visibly separate through compressed '
                                      'lacquer ridges, fold crest splits, polished wrinkle shoulders '
                                      'and the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Dense folded coating ridges contain transverse wrinkle breaks.',
                                     'compressed lacquer ridges is present in the native named-feature '
                                     'coverage probe.',
                                     'fold crest splits is present in the native named-feature coverage '
                                     'probe.',
                                     'polished wrinkle shoulders is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/wrinkled_lacquer/independent-feature-carrier',
 'spec_key': 'spec-v2/wrinkled_lacquer/named-material-bindings'}

render = build_renderer(wrinkled_lacquer, IDENTITY_CONTRACT)

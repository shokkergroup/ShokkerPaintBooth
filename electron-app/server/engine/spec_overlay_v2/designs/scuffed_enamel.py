# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.9; invariant nearest 0.5393 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Scuffed Enamel. Identity declared before rendering/scoring."""
from ..crack_designs import scuffed_enamel
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_scuffed_enamel',
 'display_name': 'Scuffed Enamel - spec overlay',
 'promise': 'Scuffed Enamel assembles enamel witness pads, abrasion sweeps, embedded road grit, chipped '
            'scuff starts and burnished exit hooks.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Scuffed Enamel assembles enamel witness pads, abrasion sweeps, embedded road grit, '
                    'chipped scuff starts and burnished exit hooks. Geometry is independently authored '
                    'in crack_designs.py:scuffed_enamel.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to enamel witness pads, '
                 'abrasion sweeps, embedded road grit, chipped scuff starts, burnished exit hooks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'enamel_witness_pads',
                 'role': 'Enamel witness pads use M/R/Cc intervals [(16, 238), (28, 216), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'abrasion_sweeps',
                 'role': 'Abrasion sweeps use M/R/Cc intervals [(148, 255), (16, 106), (0, 110)] in '
                         'their own geometry.'},
                {'name': 'embedded_road_grit',
                 'role': 'Embedded road grit use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'chipped_scuff_starts',
                 'role': 'Chipped scuff starts use M/R/Cc intervals [(54, 204), (100, 232), (66, 204)] '
                         'in their own geometry.'},
                {'name': 'burnished_exit_hooks',
                 'role': 'Burnished exit hooks use M/R/Cc intervals [(98, 228), (54, 178), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['enamel_witness_pads',
                            'abrasion_sweeps',
                            'embedded_road_grit',
                            'chipped_scuff_starts',
                            'burnished_exit_hooks'],
                      'R': ['enamel_witness_pads',
                            'abrasion_sweeps',
                            'embedded_road_grit',
                            'chipped_scuff_starts',
                            'burnished_exit_hooks'],
                      'Cc': ['enamel_witness_pads',
                             'abrasion_sweeps',
                             'embedded_road_grit',
                             'chipped_scuff_starts',
                             'burnished_exit_hooks']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Scuffed Enamel must visibly separate through enamel witness '
                                      'pads, abrasion sweeps, embedded road grit and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Scuffed Enamel must visibly separate through enamel witness '
                                      'pads, abrasion sweeps, embedded road grit and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Abrasion sweeps expose separate scuff starts and polished exits.',
                                     'enamel witness pads is present in the native named-feature '
                                     'coverage probe.',
                                     'abrasion sweeps is present in the native named-feature coverage '
                                     'probe.',
                                     'embedded road grit is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/scuffed_enamel/independent-feature-carrier',
 'spec_key': 'spec-v2/scuffed_enamel/named-material-bindings'}

render = build_renderer(scuffed_enamel, IDENTITY_CONTRACT)

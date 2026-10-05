# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.07; invariant nearest 0.45921 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Micro Chipping. Identity declared before rendering/scoring."""
from ..crack_designs import micro_chipping
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_micro_chipping',
 'display_name': 'Micro Chipping - spec overlay',
 'promise': 'Micro Chipping assembles stone chip craters, bare chip centers, fractured enamel rims, '
            'impact comet scars and detached paint specks.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Micro Chipping assembles stone chip craters, bare chip centers, fractured enamel '
                    'rims, impact comet scars and detached paint specks. Geometry is independently '
                    'authored in crack_designs.py:micro_chipping.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to stone chip craters, bare '
                 'chip centers, fractured enamel rims, impact comet scars, detached paint specks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'stone_chip_craters',
                 'role': 'Stone chip craters use M/R/Cc intervals [(18, 244), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'bare_chip_centers',
                 'role': 'Bare chip centers use M/R/Cc intervals [(148, 255), (0, 94), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'fractured_enamel_rims',
                 'role': 'Fractured enamel rims use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'impact_comet_scars',
                 'role': 'Impact comet scars use M/R/Cc intervals [(56, 204), (102, 232), (70, 204)] in '
                         'their own geometry.'},
                {'name': 'detached_paint_specks',
                 'role': 'Detached paint specks use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['stone_chip_craters',
                            'bare_chip_centers',
                            'fractured_enamel_rims',
                            'impact_comet_scars',
                            'detached_paint_specks'],
                      'R': ['stone_chip_craters',
                            'bare_chip_centers',
                            'fractured_enamel_rims',
                            'impact_comet_scars',
                            'detached_paint_specks'],
                      'Cc': ['stone_chip_craters',
                             'bare_chip_centers',
                             'fractured_enamel_rims',
                             'impact_comet_scars',
                             'detached_paint_specks']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Micro Chipping must visibly separate through stone chip craters, '
                                      'bare chip centers, fractured enamel rims and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Micro Chipping must visibly separate through stone chip craters, '
                                      'bare chip centers, fractured enamel rims and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Undercut impact crescents sit beside detached sharp enamel '
                                     'flakes.',
                                     'stone chip craters is present in the native named-feature '
                                     'coverage probe.',
                                     'bare chip centers is present in the native named-feature coverage '
                                     'probe.',
                                     'fractured enamel rims is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/micro_chipping/independent-feature-carrier',
 'spec_key': 'spec-v2/micro_chipping/named-material-bindings'}

render = build_renderer(micro_chipping, IDENTITY_CONTRACT)

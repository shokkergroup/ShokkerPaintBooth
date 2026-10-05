# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.15; invariant nearest 0.38951 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Mud Crackle. Identity declared before rendering/scoring."""
from ..crack_designs import mud_crackle
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_mud_crackle',
 'display_name': 'Mud Crackle - spec overlay',
 'promise': 'Mud Crackle assembles dry mud platelets, shrinkage fissures, curled plate edges, secondary '
            'dry checks and crumbled grit pockets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Mud Crackle assembles dry mud platelets, shrinkage fissures, curled plate edges, '
                    'secondary dry checks and crumbled grit pockets. Geometry is independently authored '
                    'in crack_designs.py:mud_crackle.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to dry mud platelets, shrinkage '
                 'fissures, curled plate edges, secondary dry checks, crumbled grit pockets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'dry_mud_platelets',
                 'role': 'Dry mud platelets use M/R/Cc intervals [(12, 238), (38, 226), (24, 250)] in '
                         'their own geometry.'},
                {'name': 'shrinkage_fissures',
                 'role': 'Shrinkage fissures use M/R/Cc intervals [(0, 98), (176, 255), (138, 252)] in '
                         'their own geometry.'},
                {'name': 'curled_plate_edges',
                 'role': 'Curled plate edges use M/R/Cc intervals [(150, 255), (16, 112), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'secondary_dry_checks',
                 'role': 'Secondary dry checks use M/R/Cc intervals [(54, 202), (100, 234), (68, 208)] '
                         'in their own geometry.'},
                {'name': 'crumbled_grit_pockets',
                 'role': 'Crumbled grit pockets use M/R/Cc intervals [(96, 224), (60, 186), (168, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['dry_mud_platelets',
                            'shrinkage_fissures',
                            'curled_plate_edges',
                            'secondary_dry_checks',
                            'crumbled_grit_pockets'],
                      'R': ['dry_mud_platelets',
                            'shrinkage_fissures',
                            'curled_plate_edges',
                            'secondary_dry_checks',
                            'crumbled_grit_pockets'],
                      'Cc': ['dry_mud_platelets',
                             'shrinkage_fissures',
                             'curled_plate_edges',
                             'secondary_dry_checks',
                             'crumbled_grit_pockets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Mud Crackle must visibly separate through dry mud platelets, '
                                      'shrinkage fissures, curled plate edges and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_wrinkled_lacquer',
                        'difference': 'Mud Crackle must visibly separate through dry mud platelets, '
                                      'shrinkage fissures, curled plate edges and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Curled irregular mud platelets retain dark separation channels.',
                                     'dry mud platelets is present in the native named-feature coverage '
                                     'probe.',
                                     'shrinkage fissures is present in the native named-feature '
                                     'coverage probe.',
                                     'curled plate edges is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/mud_crackle/independent-feature-carrier',
 'spec_key': 'spec-v2/mud_crackle/named-material-bindings'}

render = build_renderer(mud_crackle, IDENTITY_CONTRACT)

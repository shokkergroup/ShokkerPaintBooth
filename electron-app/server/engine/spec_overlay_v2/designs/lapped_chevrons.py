# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.76; invariant nearest 0.50216 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Lapped Chevrons. Identity declared before rendering/scoring."""
from ..machine_designs import lapped_chevrons
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_lapped_chevrons',
 'display_name': 'Lapped Chevrons - spec overlay',
 'promise': 'Lapped Chevrons assembles lap faces, lapping edges, return scrapes, keystone pits and '
            'feathered tails.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Lapped Chevrons assembles lap faces, lapping edges, return scrapes, keystone pits '
                    'and feathered tails. Geometry is independently authored in '
                    'machine_designs.py:lapped_chevrons.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to lap faces, lapping edges, '
                 'return scrapes, keystone pits, feathered tails.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'lap_faces',
                 'role': 'Lap faces use M/R/Cc intervals [(14, 252), (0, 246), (34, 226)] in their own '
                         'geometry.'},
                {'name': 'lapping_edges',
                 'role': 'Lapping edges use M/R/Cc intervals [(112, 246), (0, 72), (0, 104)] in their '
                         'own geometry.'},
                {'name': 'return_scrapes',
                 'role': 'Return scrapes use M/R/Cc intervals [(8, 120), (130, 253), (124, 254)] in '
                         'their own geometry.'},
                {'name': 'keystone_pits',
                 'role': 'Keystone pits use M/R/Cc intervals [(4, 82), (182, 251), (66, 192)] in their '
                         'own geometry.'},
                {'name': 'feathered_tails',
                 'role': 'Feathered tails use M/R/Cc intervals [(156, 254), (30, 154), (66, 246)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['lap_faces',
                            'lapping_edges',
                            'return_scrapes',
                            'keystone_pits',
                            'feathered_tails'],
                      'R': ['lap_faces',
                            'lapping_edges',
                            'return_scrapes',
                            'keystone_pits',
                            'feathered_tails'],
                      'Cc': ['lap_faces',
                             'lapping_edges',
                             'return_scrapes',
                             'keystone_pits',
                             'feathered_tails']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Lapped Chevrons must visibly separate through lap faces, lapping '
                                      'edges, return scrapes and the remaining named marks, not color '
                                      'or parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Lapped Chevrons must visibly separate through lap faces, lapping '
                                      'edges, return scrapes and the remaining named marks, not color '
                                      'or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Interrupted V-shaped lapping cuts intersect a second fine pass.',
                                     'lap faces is present in the native named-feature coverage probe.',
                                     'lapping edges is present in the native named-feature coverage '
                                     'probe.',
                                     'return scrapes is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/lapped_chevrons/independent-feature-carrier',
 'spec_key': 'spec-v2/lapped_chevrons/named-material-bindings'}

render = build_renderer(lapped_chevrons, IDENTITY_CONTRACT)

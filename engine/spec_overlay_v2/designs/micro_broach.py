# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.92; invariant nearest 0.52715 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Micro Broach. Identity declared before rendering/scoring."""
from ..machine_designs import micro_broach
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_micro_broach',
 'display_name': 'Micro Broach - spec overlay',
 'promise': 'Micro Broach assembles stepped cut floors, tooth shoulders, chip curls, recessed stops and '
            'runout tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Micro Broach assembles stepped cut floors, tooth shoulders, chip curls, recessed '
                    'stops and runout tabs. Geometry is independently authored in '
                    'machine_designs.py:micro_broach.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to stepped cut floors, tooth '
                 'shoulders, chip curls, recessed stops, runout tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'stepped_cut_floors',
                 'role': 'Stepped cut floors use M/R/Cc intervals [(4, 246), (0, 246), (20, 246)] in '
                         'their own geometry.'},
                {'name': 'tooth_shoulders',
                 'role': 'Tooth shoulders use M/R/Cc intervals [(172, 255), (0, 76), (20, 164)] in '
                         'their own geometry.'},
                {'name': 'chip_curls',
                 'role': 'Chip curls use M/R/Cc intervals [(42, 204), (96, 208), (142, 255)] in their '
                         'own geometry.'},
                {'name': 'recessed_stops',
                 'role': 'Recessed stops use M/R/Cc intervals [(4, 74), (190, 255), (56, 166)] in their '
                         'own geometry.'},
                {'name': 'runout_tabs',
                 'role': 'Runout tabs use M/R/Cc intervals [(116, 246), (22, 138), (0, 86)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['stepped_cut_floors',
                            'tooth_shoulders',
                            'chip_curls',
                            'recessed_stops',
                            'runout_tabs'],
                      'R': ['stepped_cut_floors',
                            'tooth_shoulders',
                            'chip_curls',
                            'recessed_stops',
                            'runout_tabs'],
                      'Cc': ['stepped_cut_floors',
                             'tooth_shoulders',
                             'chip_curls',
                             'recessed_stops',
                             'runout_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Micro Broach must visibly separate through stepped cut floors, '
                                      'tooth shoulders, chip curls and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Micro Broach must visibly separate through stepped cut floors, '
                                      'tooth shoulders, chip curls and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three progressively cut comb teeth have separate shoulders and '
                                     'curled chips.',
                                     'stepped cut floors is present in the native named-feature '
                                     'coverage probe.',
                                     'tooth shoulders is present in the native named-feature coverage '
                                     'probe.',
                                     'chip curls is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/micro_broach/independent-feature-carrier',
 'spec_key': 'spec-v2/micro_broach/named-material-bindings'}

render = build_renderer(micro_broach, IDENTITY_CONTRACT)

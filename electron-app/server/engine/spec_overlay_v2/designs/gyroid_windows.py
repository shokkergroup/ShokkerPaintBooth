# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.68; invariant nearest 0.37816 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Gyroid Windows. Identity declared before rendering/scoring."""
from ..experimental_designs import gyroid_windows
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_gyroid_windows',
 'display_name': 'Gyroid Windows - spec overlay',
 'promise': 'Gyroid Windows assembles saddle surface lobes, gyroid neck crests, open saddle windows, '
            'junction shoulder ribs and etched saddle ticks.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Gyroid Windows assembles saddle surface lobes, gyroid neck crests, open saddle '
                    'windows, junction shoulder ribs and etched saddle ticks. Geometry is independently '
                    'authored in experimental_designs.py:gyroid_windows.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to saddle surface lobes, gyroid '
                 'neck crests, open saddle windows, junction shoulder ribs, etched saddle ticks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'saddle_surface_lobes',
                 'role': 'Saddle surface lobes use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'gyroid_neck_crests',
                 'role': 'Gyroid neck crests use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'open_saddle_windows',
                 'role': 'Open saddle windows use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'junction_shoulder_ribs',
                 'role': 'Junction shoulder ribs use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'etched_saddle_ticks',
                 'role': 'Etched saddle ticks use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['saddle_surface_lobes',
                            'gyroid_neck_crests',
                            'open_saddle_windows',
                            'junction_shoulder_ribs',
                            'etched_saddle_ticks'],
                      'R': ['saddle_surface_lobes',
                            'gyroid_neck_crests',
                            'open_saddle_windows',
                            'junction_shoulder_ribs',
                            'etched_saddle_ticks'],
                      'Cc': ['saddle_surface_lobes',
                             'gyroid_neck_crests',
                             'open_saddle_windows',
                             'junction_shoulder_ribs',
                             'etched_saddle_ticks']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Gyroid Windows must visibly separate through saddle surface '
                                      'lobes, gyroid neck crests, open saddle windows and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_kagome_bridges',
                        'difference': 'Gyroid Windows must visibly separate through saddle surface '
                                      'lobes, gyroid neck crests, open saddle windows and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['A continuous saddle-like network encloses gyroid-inspired '
                                     'windows.',
                                     'saddle surface lobes is present in the native named-feature '
                                     'coverage probe.',
                                     'gyroid neck crests is present in the native named-feature '
                                     'coverage probe.',
                                     'open saddle windows is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/gyroid_windows/independent-feature-carrier',
 'spec_key': 'spec-v2/gyroid_windows/named-material-bindings'}

render = build_renderer(gyroid_windows, IDENTITY_CONTRACT)

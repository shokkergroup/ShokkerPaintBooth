# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.77; invariant nearest 0.53587 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Rumble Strip Ticks. Identity declared before rendering/scoring."""
from ..track_designs import rumble_strip_ticks
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_rumble_strip_ticks',
 'display_name': 'Rumble Strip Ticks - spec overlay',
 'promise': 'Rumble Strip Ticks assembles kerb ramp packets, grooved strip separators, worn kerb '
            'shoulders, aggregate breakouts and tire witness ticks.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Rumble Strip Ticks assembles kerb ramp packets, grooved strip separators, worn '
                    'kerb shoulders, aggregate breakouts and tire witness ticks. Geometry is '
                    'independently authored in track_designs.py:rumble_strip_ticks.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to kerb ramp packets, grooved '
                 'strip separators, worn kerb shoulders, aggregate breakouts, tire witness ticks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'kerb_ramp_packets',
                 'role': 'Kerb ramp packets use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'grooved_strip_separators',
                 'role': 'Grooved strip separators use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'worn_kerb_shoulders',
                 'role': 'Worn kerb shoulders use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'aggregate_breakouts',
                 'role': 'Aggregate breakouts use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'tire_witness_ticks',
                 'role': 'Tire witness ticks use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['kerb_ramp_packets',
                            'grooved_strip_separators',
                            'worn_kerb_shoulders',
                            'aggregate_breakouts',
                            'tire_witness_ticks'],
                      'R': ['kerb_ramp_packets',
                            'grooved_strip_separators',
                            'worn_kerb_shoulders',
                            'aggregate_breakouts',
                            'tire_witness_ticks'],
                      'Cc': ['kerb_ramp_packets',
                             'grooved_strip_separators',
                             'worn_kerb_shoulders',
                             'aggregate_breakouts',
                             'tire_witness_ticks']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Rumble Strip Ticks must visibly separate through kerb ramp '
                                      'packets, grooved strip separators, worn kerb shoulders and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Rumble Strip Ticks must visibly separate through kerb ramp '
                                      'packets, grooved strip separators, worn kerb shoulders and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three short stepped kerb ramps have worn shoulders and witness '
                                     'ticks.',
                                     'kerb ramp packets is present in the native named-feature coverage '
                                     'probe.',
                                     'grooved strip separators is present in the native named-feature '
                                     'coverage probe.',
                                     'worn kerb shoulders is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/rumble_strip_ticks/independent-feature-carrier',
 'spec_key': 'spec-v2/rumble_strip_ticks/named-material-bindings'}

render = build_renderer(rumble_strip_ticks, IDENTITY_CONTRACT)

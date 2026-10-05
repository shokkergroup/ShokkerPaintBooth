# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.05; invariant nearest 0.43794 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Telemetry Dash. Identity declared before rendering/scoring."""
from ..track_designs import telemetry_dash
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_telemetry_dash',
 'display_name': 'Telemetry Dash - spec overlay',
 'promise': 'Telemetry Dash assembles telemetry bar packets, peak hold markers, display grid gutters, '
            'sampling clock tabs and signal trace kinks.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Telemetry Dash assembles telemetry bar packets, peak hold markers, display grid '
                    'gutters, sampling clock tabs and signal trace kinks. Geometry is independently '
                    'authored in track_designs.py:telemetry_dash.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to telemetry bar packets, peak '
                 'hold markers, display grid gutters, sampling clock tabs, signal trace kinks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'telemetry_bar_packets',
                 'role': 'Telemetry bar packets use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'peak_hold_markers',
                 'role': 'Peak hold markers use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'display_grid_gutters',
                 'role': 'Display grid gutters use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'sampling_clock_tabs',
                 'role': 'Sampling clock tabs use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'signal_trace_kinks',
                 'role': 'Signal trace kinks use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['telemetry_bar_packets',
                            'peak_hold_markers',
                            'display_grid_gutters',
                            'sampling_clock_tabs',
                            'signal_trace_kinks'],
                      'R': ['telemetry_bar_packets',
                            'peak_hold_markers',
                            'display_grid_gutters',
                            'sampling_clock_tabs',
                            'signal_trace_kinks'],
                      'Cc': ['telemetry_bar_packets',
                             'peak_hold_markers',
                             'display_grid_gutters',
                             'sampling_clock_tabs',
                             'signal_trace_kinks']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Telemetry Dash must visibly separate through telemetry bar '
                                      'packets, peak hold markers, display grid gutters and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Telemetry Dash must visibly separate through telemetry bar '
                                      'packets, peak hold markers, display grid gutters and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Small telemetry bar packets contain peak markers and trace kinks.',
                                     'telemetry bar packets is present in the native named-feature '
                                     'coverage probe.',
                                     'peak hold markers is present in the native named-feature coverage '
                                     'probe.',
                                     'display grid gutters is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/telemetry_dash/independent-feature-carrier',
 'spec_key': 'spec-v2/telemetry_dash/named-material-bindings'}

render = build_renderer(telemetry_dash, IDENTITY_CONTRACT)

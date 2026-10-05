# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.91; invariant nearest 0.51135 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Aero Vortex Tabs. Identity declared before rendering/scoring."""
from ..track_designs import aero_vortex_tabs
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_aero_vortex_tabs',
 'display_name': 'Aero Vortex Tabs - spec overlay',
 'promise': 'Aero Vortex Tabs assembles paired vortex vanes, vane leading crests, mounting recesses, '
            'shear layer witness arcs and riveted vane feet.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Aero Vortex Tabs assembles paired vortex vanes, vane leading crests, mounting '
                    'recesses, shear layer witness arcs and riveted vane feet. Geometry is '
                    'independently authored in track_designs.py:aero_vortex_tabs.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to paired vortex vanes, vane '
                 'leading crests, mounting recesses, shear layer witness arcs, riveted vane feet.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'paired_vortex_vanes',
                 'role': 'Paired vortex vanes use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'vane_leading_crests',
                 'role': 'Vane leading crests use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'mounting_recesses',
                 'role': 'Mounting recesses use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'shear_layer_witness_arcs',
                 'role': 'Shear layer witness arcs use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'riveted_vane_feet',
                 'role': 'Riveted vane feet use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['paired_vortex_vanes',
                            'vane_leading_crests',
                            'mounting_recesses',
                            'shear_layer_witness_arcs',
                            'riveted_vane_feet'],
                      'R': ['paired_vortex_vanes',
                            'vane_leading_crests',
                            'mounting_recesses',
                            'shear_layer_witness_arcs',
                            'riveted_vane_feet'],
                      'Cc': ['paired_vortex_vanes',
                             'vane_leading_crests',
                             'mounting_recesses',
                             'shear_layer_witness_arcs',
                             'riveted_vane_feet']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Aero Vortex Tabs must visibly separate through paired vortex '
                                      'vanes, vane leading crests, mounting recesses and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Aero Vortex Tabs must visibly separate through paired vortex '
                                      'vanes, vane leading crests, mounting recesses and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Short aerodynamic tabs carry leading-edge and attachment details.',
                                     'paired vortex vanes is present in the native named-feature '
                                     'coverage probe.',
                                     'vane leading crests is present in the native named-feature '
                                     'coverage probe.',
                                     'mounting recesses is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/aero_vortex_tabs/independent-feature-carrier',
 'spec_key': 'spec-v2/aero_vortex_tabs/named-material-bindings'}

render = build_renderer(aero_vortex_tabs, IDENTITY_CONTRACT)

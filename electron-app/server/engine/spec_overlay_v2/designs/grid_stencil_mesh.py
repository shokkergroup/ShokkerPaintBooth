# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.76; invariant nearest 0.52878 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Grid Stencil Mesh. Identity declared before rendering/scoring."""
from ..track_designs import grid_stencil_mesh
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_grid_stencil_mesh',
 'display_name': 'Grid Stencil Mesh - spec overlay',
 'promise': 'Grid Stencil Mesh assembles stencil cell frames, stencil bridge tabs, recessed grid '
            'corners, registration chevrons and overspray edge grains.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Grid Stencil Mesh assembles stencil cell frames, stencil bridge tabs, recessed '
                    'grid corners, registration chevrons and overspray edge grains. Geometry is '
                    'independently authored in track_designs.py:grid_stencil_mesh.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to stencil cell frames, stencil '
                 'bridge tabs, recessed grid corners, registration chevrons, overspray edge grains.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'stencil_cell_frames',
                 'role': 'Stencil cell frames use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'stencil_bridge_tabs',
                 'role': 'Stencil bridge tabs use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'recessed_grid_corners',
                 'role': 'Recessed grid corners use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'registration_chevrons',
                 'role': 'Registration chevrons use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'overspray_edge_grains',
                 'role': 'Overspray edge grains use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['stencil_cell_frames',
                            'stencil_bridge_tabs',
                            'recessed_grid_corners',
                            'registration_chevrons',
                            'overspray_edge_grains'],
                      'R': ['stencil_cell_frames',
                            'stencil_bridge_tabs',
                            'recessed_grid_corners',
                            'registration_chevrons',
                            'overspray_edge_grains'],
                      'Cc': ['stencil_cell_frames',
                             'stencil_bridge_tabs',
                             'recessed_grid_corners',
                             'registration_chevrons',
                             'overspray_edge_grains']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Grid Stencil Mesh must visibly separate through stencil cell '
                                      'frames, stencil bridge tabs, recessed grid corners and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Grid Stencil Mesh must visibly separate through stencil cell '
                                      'frames, stencil bridge tabs, recessed grid corners and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Open stencil frames retain tabs and registration chevrons.',
                                     'stencil cell frames is present in the native named-feature '
                                     'coverage probe.',
                                     'stencil bridge tabs is present in the native named-feature '
                                     'coverage probe.',
                                     'recessed grid corners is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/grid_stencil_mesh/independent-feature-carrier',
 'spec_key': 'spec-v2/grid_stencil_mesh/named-material-bindings'}

render = build_renderer(grid_stencil_mesh, IDENTITY_CONTRACT)

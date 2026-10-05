# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.51; invariant nearest 0.54085 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Catch Fence Clips. Identity declared before rendering/scoring."""
from ..track_designs import catch_fence_clips
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_catch_fence_clips',
 'display_name': 'Catch Fence Clips - spec overlay',
 'promise': 'Catch Fence Clips assembles crossed fence strands, wrapped wire clips, clip crimp pockets, '
            'wire twist tails and galvanized contact nibs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Catch Fence Clips assembles crossed fence strands, wrapped wire clips, clip crimp '
                    'pockets, wire twist tails and galvanized contact nibs. Geometry is independently '
                    'authored in track_designs.py:catch_fence_clips.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to crossed fence strands, '
                 'wrapped wire clips, clip crimp pockets, wire twist tails, galvanized contact nibs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'crossed_fence_strands',
                 'role': 'Crossed fence strands use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'wrapped_wire_clips',
                 'role': 'Wrapped wire clips use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'clip_crimp_pockets',
                 'role': 'Clip crimp pockets use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'wire_twist_tails',
                 'role': 'Wire twist tails use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'galvanized_contact_nibs',
                 'role': 'Galvanized contact nibs use M/R/Cc intervals [(98, 228), (54, 180), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['crossed_fence_strands',
                            'wrapped_wire_clips',
                            'clip_crimp_pockets',
                            'wire_twist_tails',
                            'galvanized_contact_nibs'],
                      'R': ['crossed_fence_strands',
                            'wrapped_wire_clips',
                            'clip_crimp_pockets',
                            'wire_twist_tails',
                            'galvanized_contact_nibs'],
                      'Cc': ['crossed_fence_strands',
                             'wrapped_wire_clips',
                             'clip_crimp_pockets',
                             'wire_twist_tails',
                             'galvanized_contact_nibs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Catch Fence Clips must visibly separate through crossed fence '
                                      'strands, wrapped wire clips, clip crimp pockets and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Catch Fence Clips must visibly separate through crossed fence '
                                      'strands, wrapped wire clips, clip crimp pockets and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Crossed fence wires are held by wrapped central clips.',
                                     'crossed fence strands is present in the native named-feature '
                                     'coverage probe.',
                                     'wrapped wire clips is present in the native named-feature '
                                     'coverage probe.',
                                     'clip crimp pockets is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/catch_fence_clips/independent-feature-carrier',
 'spec_key': 'spec-v2/catch_fence_clips/named-material-bindings'}

render = build_renderer(catch_fence_clips, IDENTITY_CONTRACT)

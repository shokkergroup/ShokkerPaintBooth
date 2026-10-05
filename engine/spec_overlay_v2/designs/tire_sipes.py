# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.31; invariant nearest 0.39302 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Tire Sipes. Identity declared before rendering/scoring."""
from ..track_designs import tire_sipes
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_tire_sipes',
 'display_name': 'Tire Sipes - spec overlay',
 'promise': 'Tire Sipes assembles tread block faces, zigzag sipe cuts, polished tread shoulders, '
            'transverse drainage notches and rubber pickup nibs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Tire Sipes assembles tread block faces, zigzag sipe cuts, polished tread '
                    'shoulders, transverse drainage notches and rubber pickup nibs. Geometry is '
                    'independently authored in track_designs.py:tire_sipes.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to tread block faces, zigzag '
                 'sipe cuts, polished tread shoulders, transverse drainage notches, rubber pickup nibs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'tread_block_faces',
                 'role': 'Tread block faces use M/R/Cc intervals [(12, 226), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'zigzag_sipe_cuts',
                 'role': 'Zigzag sipe cuts use M/R/Cc intervals [(0, 86), (188, 255), (150, 254)] in '
                         'their own geometry.'},
                {'name': 'polished_tread_shoulders',
                 'role': 'Polished tread shoulders use M/R/Cc intervals [(158, 255), (0, 92), (0, 112)] '
                         'in their own geometry.'},
                {'name': 'transverse_drainage_notches',
                 'role': 'Transverse drainage notches use M/R/Cc intervals [(62, 202), (100, 232), (70, '
                         '204)] in their own geometry.'},
                {'name': 'rubber_pickup_nibs',
                 'role': 'Rubber pickup nibs use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['tread_block_faces',
                            'zigzag_sipe_cuts',
                            'polished_tread_shoulders',
                            'transverse_drainage_notches',
                            'rubber_pickup_nibs'],
                      'R': ['tread_block_faces',
                            'zigzag_sipe_cuts',
                            'polished_tread_shoulders',
                            'transverse_drainage_notches',
                            'rubber_pickup_nibs'],
                      'Cc': ['tread_block_faces',
                             'zigzag_sipe_cuts',
                             'polished_tread_shoulders',
                             'transverse_drainage_notches',
                             'rubber_pickup_nibs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Tire Sipes must visibly separate through tread block faces, '
                                      'zigzag sipe cuts, polished tread shoulders and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_brake_rotor_slots',
                        'difference': 'Tire Sipes must visibly separate through tread block faces, '
                                      'zigzag sipe cuts, polished tread shoulders and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Rhomboidal tread lugs contain zigzag cuts and drainage notches.',
                                     'tread block faces is present in the native named-feature coverage '
                                     'probe.',
                                     'zigzag sipe cuts is present in the native named-feature coverage '
                                     'probe.',
                                     'polished tread shoulders is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/tire_sipes/independent-feature-carrier',
 'spec_key': 'spec-v2/tire_sipes/named-material-bindings'}

render = build_renderer(tire_sipes, IDENTITY_CONTRACT)

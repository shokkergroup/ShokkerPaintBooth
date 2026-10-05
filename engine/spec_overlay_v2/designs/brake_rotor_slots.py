# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.94; invariant nearest 0.3783 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Brake Rotor Slots. Identity declared before rendering/scoring."""
from ..track_designs import brake_rotor_slots
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_brake_rotor_slots',
 'display_name': 'Brake Rotor Slots - spec overlay',
 'promise': 'Brake Rotor Slots assembles rotor swept lands, curved degas slots, slot chamfers, wear '
            'track arclets and drilled cooling pores.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Brake Rotor Slots assembles rotor swept lands, curved degas slots, slot chamfers, '
                    'wear track arclets and drilled cooling pores. Geometry is independently authored '
                    'in track_designs.py:brake_rotor_slots.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to rotor swept lands, curved '
                 'degas slots, slot chamfers, wear track arclets, drilled cooling pores.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'rotor_swept_lands',
                 'role': 'Rotor swept lands use M/R/Cc intervals [(112, 255), (20, 198), (20, 232)] in '
                         'their own geometry.'},
                {'name': 'curved_degas_slots',
                 'role': 'Curved degas slots use M/R/Cc intervals [(0, 98), (180, 255), (148, 254)] in '
                         'their own geometry.'},
                {'name': 'slot_chamfers',
                 'role': 'Slot chamfers use M/R/Cc intervals [(156, 255), (16, 92), (0, 112)] in their '
                         'own geometry.'},
                {'name': 'wear_track_arclets',
                 'role': 'Wear track arclets use M/R/Cc intervals [(54, 204), (98, 230), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'drilled_cooling_pores',
                 'role': 'Drilled cooling pores use M/R/Cc intervals [(96, 228), (54, 178), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['rotor_swept_lands',
                            'curved_degas_slots',
                            'slot_chamfers',
                            'wear_track_arclets',
                            'drilled_cooling_pores'],
                      'R': ['rotor_swept_lands',
                            'curved_degas_slots',
                            'slot_chamfers',
                            'wear_track_arclets',
                            'drilled_cooling_pores'],
                      'Cc': ['rotor_swept_lands',
                             'curved_degas_slots',
                             'slot_chamfers',
                             'wear_track_arclets',
                             'drilled_cooling_pores']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Brake Rotor Slots must visibly separate through rotor swept '
                                      'lands, curved degas slots, slot chamfers and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Brake Rotor Slots must visibly separate through rotor swept '
                                      'lands, curved degas slots, slot chamfers and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Swept rotor lands are interrupted by curved slots and cooling '
                                     'pores.',
                                     'rotor swept lands is present in the native named-feature coverage '
                                     'probe.',
                                     'curved degas slots is present in the native named-feature '
                                     'coverage probe.',
                                     'slot chamfers is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/brake_rotor_slots/independent-feature-carrier',
 'spec_key': 'spec-v2/brake_rotor_slots/named-material-bindings'}

render = build_renderer(brake_rotor_slots, IDENTITY_CONTRACT)

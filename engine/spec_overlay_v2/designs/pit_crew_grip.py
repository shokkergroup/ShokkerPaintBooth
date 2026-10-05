# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.43; invariant nearest 0.53587 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Pit Crew Grip. Identity declared before rendering/scoring."""
from ..track_designs import pit_crew_grip
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_pit_crew_grip',
 'display_name': 'Pit Crew Grip - spec overlay',
 'promise': 'Pit Crew Grip assembles molded grip lugs, raised lug crowns, grip drain channels, lug flex '
            'notches and contact wear dimples.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Pit Crew Grip assembles molded grip lugs, raised lug crowns, grip drain channels, '
                    'lug flex notches and contact wear dimples. Geometry is independently authored in '
                    'track_designs.py:pit_crew_grip.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to molded grip lugs, raised lug '
                 'crowns, grip drain channels, lug flex notches, contact wear dimples.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'molded_grip_lugs',
                 'role': 'Molded grip lugs use M/R/Cc intervals [(18, 244), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'raised_lug_crowns',
                 'role': 'Raised lug crowns use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'grip_drain_channels',
                 'role': 'Grip drain channels use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'lug_flex_notches',
                 'role': 'Lug flex notches use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'contact_wear_dimples',
                 'role': 'Contact wear dimples use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['molded_grip_lugs',
                            'raised_lug_crowns',
                            'grip_drain_channels',
                            'lug_flex_notches',
                            'contact_wear_dimples'],
                      'R': ['molded_grip_lugs',
                            'raised_lug_crowns',
                            'grip_drain_channels',
                            'lug_flex_notches',
                            'contact_wear_dimples'],
                      'Cc': ['molded_grip_lugs',
                             'raised_lug_crowns',
                             'grip_drain_channels',
                             'lug_flex_notches',
                             'contact_wear_dimples']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Pit Crew Grip must visibly separate through molded grip lugs, '
                                      'raised lug crowns, grip drain channels and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Pit Crew Grip must visibly separate through molded grip lugs, '
                                      'raised lug crowns, grip drain channels and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three molded grip fingers have separate crowns and flex notches.',
                                     'molded grip lugs is present in the native named-feature coverage '
                                     'probe.',
                                     'raised lug crowns is present in the native named-feature coverage '
                                     'probe.',
                                     'grip drain channels is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/pit_crew_grip/independent-feature-carrier',
 'spec_key': 'spec-v2/pit_crew_grip/named-material-bindings'}

render = build_renderer(pit_crew_grip, IDENTITY_CONTRACT)

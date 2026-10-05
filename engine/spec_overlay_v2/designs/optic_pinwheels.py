# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 90.85; invariant nearest 0.54881 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Optic Pinwheels. Identity declared before rendering/scoring."""
from ..optical_designs import optic_pinwheels
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_optic_pinwheels',
 'display_name': 'Optic Pinwheels - spec overlay',
 'promise': 'Optic Pinwheels assembles folded angular sails, sail fold crests, central rotor hubs, '
            'blade clearance notches and registration pinholes.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Optic Pinwheels assembles folded angular sails, sail fold crests, central rotor '
                    'hubs, blade clearance notches and registration pinholes. Geometry is independently '
                    'authored in optical_designs.py:optic_pinwheels.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to folded angular sails, sail '
                 'fold crests, central rotor hubs, blade clearance notches, registration pinholes.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'folded_angular_sails',
                 'role': 'Folded angular sails use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'sail_fold_crests',
                 'role': 'Sail fold crests use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'central_rotor_hubs',
                 'role': 'Central rotor hubs use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'blade_clearance_notches',
                 'role': 'Blade clearance notches use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'registration_pinholes',
                 'role': 'Registration pinholes use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['folded_angular_sails',
                            'sail_fold_crests',
                            'central_rotor_hubs',
                            'blade_clearance_notches',
                            'registration_pinholes'],
                      'R': ['folded_angular_sails',
                            'sail_fold_crests',
                            'central_rotor_hubs',
                            'blade_clearance_notches',
                            'registration_pinholes'],
                      'Cc': ['folded_angular_sails',
                             'sail_fold_crests',
                             'central_rotor_hubs',
                             'blade_clearance_notches',
                             'registration_pinholes']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Optic Pinwheels must visibly separate through folded angular '
                                      'sails, sail fold crests, central rotor hubs and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Optic Pinwheels must visibly separate through folded angular '
                                      'sails, sail fold crests, central rotor hubs and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Four folded sails connect around a central pinwheel hub; '
                                     'individual creases and clipped tips remain visible.',
                                     'folded angular sails is present in the native named-feature '
                                     'coverage probe.',
                                     'sail fold crests is present in the native named-feature coverage '
                                     'probe.',
                                     'central rotor hubs is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/optic_pinwheels/independent-feature-carrier',
 'spec_key': 'spec-v2/optic_pinwheels/named-material-bindings'}

render = build_renderer(optic_pinwheels, IDENTITY_CONTRACT)

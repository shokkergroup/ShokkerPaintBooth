# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.2; invariant nearest 0.50597 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Pyrite Cuboids. Identity declared before rendering/scoring."""
from ..crystal_designs import pyrite_cuboids
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_pyrite_cuboids',
 'display_name': 'Pyrite Cuboids - spec overlay',
 'promise': 'Pyrite Cuboids assembles cubic twin roof faces, penetrant cube sidewalls, intergrowth '
            'contact grooves, growth face striations and crumbled sulfide corners.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Pyrite Cuboids assembles cubic twin roof faces, penetrant cube sidewalls, '
                    'intergrowth contact grooves, growth face striations and crumbled sulfide corners. '
                    'Geometry is independently authored in crystal_designs.py:pyrite_cuboids.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to cubic twin roof faces, '
                 'penetrant cube sidewalls, intergrowth contact grooves, growth face striations, '
                 'crumbled sulfide corners.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'cubic_twin_roof_faces',
                 'role': 'Cubic twin roof faces use M/R/Cc intervals [(18, 246), (0, 246), (24, 246)] '
                         'in their own geometry.'},
                {'name': 'penetrant_cube_sidewalls',
                 'role': 'Penetrant cube sidewalls use M/R/Cc intervals [(56, 235), (16, 128), (0, '
                         '132)] in their own geometry.'},
                {'name': 'intergrowth_contact_grooves',
                 'role': 'Intergrowth contact grooves use M/R/Cc intervals [(0, 100), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'growth_face_striations',
                 'role': 'Growth face striations use M/R/Cc intervals [(58, 208), (100, 230), (68, '
                         '212)] in their own geometry.'},
                {'name': 'crumbled_sulfide_corners',
                 'role': 'Crumbled sulfide corners use M/R/Cc intervals [(96, 226), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['cubic_twin_roof_faces',
                            'penetrant_cube_sidewalls',
                            'intergrowth_contact_grooves',
                            'growth_face_striations',
                            'crumbled_sulfide_corners'],
                      'R': ['cubic_twin_roof_faces',
                            'penetrant_cube_sidewalls',
                            'intergrowth_contact_grooves',
                            'growth_face_striations',
                            'crumbled_sulfide_corners'],
                      'Cc': ['cubic_twin_roof_faces',
                             'penetrant_cube_sidewalls',
                             'intergrowth_contact_grooves',
                             'growth_face_striations',
                             'crumbled_sulfide_corners']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Pyrite Cuboids must visibly separate through cubic twin roof '
                                      'faces, penetrant cube sidewalls, intergrowth contact grooves and '
                                      'the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Pyrite Cuboids must visibly separate through cubic twin roof '
                                      'faces, penetrant cube sidewalls, intergrowth contact grooves and '
                                      'the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Intergrown cubic staircases retain rhombus roofs, two side faces, '
                                     'Y seams and separate face striations.',
                                     'cubic twin roof faces is present in the native named-feature '
                                     'coverage probe.',
                                     'penetrant cube sidewalls is present in the native named-feature '
                                     'coverage probe.',
                                     'intergrowth contact grooves is present in the native '
                                     'named-feature coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/pyrite_cuboids/independent-feature-carrier',
 'spec_key': 'spec-v2/pyrite_cuboids/named-material-bindings'}

render = build_renderer(pyrite_cuboids, IDENTITY_CONTRACT)

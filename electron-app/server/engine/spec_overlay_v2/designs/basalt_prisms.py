# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.67; invariant nearest 0.50497 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Basalt Prisms. Identity declared before rendering/scoring."""
from ..crystal_designs import basalt_prisms
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_basalt_prisms',
 'display_name': 'Basalt Prisms - spec overlay',
 'promise': 'Basalt Prisms assembles broken column caps, prismatic column sides, bundle joint recesses, '
            'vesicle socket pairs and fractured root chips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Basalt Prisms assembles broken column caps, prismatic column sides, bundle joint '
                    'recesses, vesicle socket pairs and fractured root chips. Geometry is independently '
                    'authored in crystal_designs.py:basalt_prisms.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to broken column caps, '
                 'prismatic column sides, bundle joint recesses, vesicle socket pairs, fractured root '
                 'chips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'broken_column_caps',
                 'role': 'Broken column caps use M/R/Cc intervals [(24, 252), (24, 210), (24, 250)] in '
                         'their own geometry.'},
                {'name': 'prismatic_column_sides',
                 'role': 'Prismatic column sides use M/R/Cc intervals [(130, 255), (16, 108), (0, 122)] '
                         'in their own geometry.'},
                {'name': 'bundle_joint_recesses',
                 'role': 'Bundle joint recesses use M/R/Cc intervals [(0, 94), (180, 255), (142, 254)] '
                         'in their own geometry.'},
                {'name': 'vesicle_socket_pairs',
                 'role': 'Vesicle socket pairs use M/R/Cc intervals [(54, 204), (100, 226), (72, 216)] '
                         'in their own geometry.'},
                {'name': 'fractured_root_chips',
                 'role': 'Fractured root chips use M/R/Cc intervals [(98, 238), (42, 180), (168, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['broken_column_caps',
                            'prismatic_column_sides',
                            'bundle_joint_recesses',
                            'vesicle_socket_pairs',
                            'fractured_root_chips'],
                      'R': ['broken_column_caps',
                            'prismatic_column_sides',
                            'bundle_joint_recesses',
                            'vesicle_socket_pairs',
                            'fractured_root_chips'],
                      'Cc': ['broken_column_caps',
                             'prismatic_column_sides',
                             'bundle_joint_recesses',
                             'vesicle_socket_pairs',
                             'fractured_root_chips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Basalt Prisms must visibly separate through broken column caps, '
                                      'prismatic column sides, bundle joint recesses and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Basalt Prisms must visibly separate through broken column caps, '
                                      'prismatic column sides, bundle joint recesses and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Broken prismatic column ends have distinct raised polygonal rims.',
                                     'broken column caps is present in the native named-feature '
                                     'coverage probe.',
                                     'prismatic column sides is present in the native named-feature '
                                     'coverage probe.',
                                     'bundle joint recesses is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/basalt_prisms/independent-feature-carrier',
 'spec_key': 'spec-v2/basalt_prisms/named-material-bindings'}

render = build_renderer(basalt_prisms, IDENTITY_CONTRACT)

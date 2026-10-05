# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.17; invariant nearest 0.54085 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Salt Hoppers. Identity declared before rendering/scoring."""
from ..crystal_designs import salt_hoppers
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_salt_hoppers',
 'display_name': 'Salt Hoppers - spec overlay',
 'promise': 'Salt Hoppers assembles hopper terraces, raised square rims, hollow growth centers, corner '
            'bridges and salt satellites.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Salt Hoppers assembles hopper terraces, raised square rims, hollow growth centers, '
                    'corner bridges and salt satellites. Geometry is independently authored in '
                    'crystal_designs.py:salt_hoppers.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to hopper terraces, raised '
                 'square rims, hollow growth centers, corner bridges, salt satellites.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'hopper_terraces',
                 'role': 'Hopper terraces use M/R/Cc intervals [(8, 246), (26, 220), (24, 250)] in '
                         'their own geometry.'},
                {'name': 'raised_square_rims',
                 'role': 'Raised square rims use M/R/Cc intervals [(160, 255), (16, 100), (0, 118)] in '
                         'their own geometry.'},
                {'name': 'hollow_growth_centers',
                 'role': 'Hollow growth centers use M/R/Cc intervals [(0, 86), (186, 255), (158, 254)] '
                         'in their own geometry.'},
                {'name': 'corner_bridges',
                 'role': 'Corner bridges use M/R/Cc intervals [(74, 218), (78, 202), (70, 218)] in '
                         'their own geometry.'},
                {'name': 'salt_satellites',
                 'role': 'Salt satellites use M/R/Cc intervals [(22, 174), (132, 240), (106, 248)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['hopper_terraces',
                            'raised_square_rims',
                            'hollow_growth_centers',
                            'corner_bridges',
                            'salt_satellites'],
                      'R': ['hopper_terraces',
                            'raised_square_rims',
                            'hollow_growth_centers',
                            'corner_bridges',
                            'salt_satellites'],
                      'Cc': ['hopper_terraces',
                             'raised_square_rims',
                             'hollow_growth_centers',
                             'corner_bridges',
                             'salt_satellites']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Salt Hoppers must visibly separate through hopper terraces, '
                                      'raised square rims, hollow growth centers and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Salt Hoppers must visibly separate through hopper terraces, '
                                      'raised square rims, hollow growth centers and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Hollow stepped square hoppers retain protected centers and corner '
                                     'breaks.',
                                     'hopper terraces is present in the native named-feature coverage '
                                     'probe.',
                                     'raised square rims is present in the native named-feature '
                                     'coverage probe.',
                                     'hollow growth centers is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/salt_hoppers/independent-feature-carrier',
 'spec_key': 'spec-v2/salt_hoppers/named-material-bindings'}

render = build_renderer(salt_hoppers, IDENTITY_CONTRACT)

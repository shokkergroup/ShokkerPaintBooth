# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.17; invariant nearest 0.39267 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Stress Star Crazing. Identity declared before rendering/scoring."""
from ..crack_designs import stress_star_crazing
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_stress_star_crazing',
 'display_name': 'Stress Star Crazing - spec overlay',
 'promise': 'Stress Star Crazing assembles stress field platelets, radial star fissures, impact center '
            'chips, arrest branch segments and fissure tip tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Stress Star Crazing assembles stress field platelets, radial star fissures, impact '
                    'center chips, arrest branch segments and fissure tip tabs. Geometry is '
                    'independently authored in crack_designs.py:stress_star_crazing.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to stress field platelets, '
                 'radial star fissures, impact center chips, arrest branch segments, fissure tip tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'stress_field_platelets',
                 'role': 'Stress field platelets use M/R/Cc intervals [(18, 244), (0, 240), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'radial_star_fissures',
                 'role': 'Radial star fissures use M/R/Cc intervals [(0, 96), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'impact_center_chips',
                 'role': 'Impact center chips use M/R/Cc intervals [(150, 255), (0, 82), (0, 110)] in '
                         'their own geometry.'},
                {'name': 'arrest_branch_segments',
                 'role': 'Arrest branch segments use M/R/Cc intervals [(54, 204), (100, 230), (70, '
                         '202)] in their own geometry.'},
                {'name': 'fissure_tip_tabs',
                 'role': 'Fissure tip tabs use M/R/Cc intervals [(96, 226), (56, 184), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['stress_field_platelets',
                            'radial_star_fissures',
                            'impact_center_chips',
                            'arrest_branch_segments',
                            'fissure_tip_tabs'],
                      'R': ['stress_field_platelets',
                            'radial_star_fissures',
                            'impact_center_chips',
                            'arrest_branch_segments',
                            'fissure_tip_tabs'],
                      'Cc': ['stress_field_platelets',
                             'radial_star_fissures',
                             'impact_center_chips',
                             'arrest_branch_segments',
                             'fissure_tip_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Stress Star Crazing must visibly separate through stress field '
                                      'platelets, radial star fissures, impact center chips and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Stress Star Crazing must visibly separate through stress field '
                                      'platelets, radial star fissures, impact center chips and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Offset impact chips connect to multiple short branching fissures.',
                                     'stress field platelets is present in the native named-feature '
                                     'coverage probe.',
                                     'radial star fissures is present in the native named-feature '
                                     'coverage probe.',
                                     'impact center chips is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/stress_star_crazing/independent-feature-carrier',
 'spec_key': 'spec-v2/stress_star_crazing/named-material-bindings'}

render = build_renderer(stress_star_crazing, IDENTITY_CONTRACT)

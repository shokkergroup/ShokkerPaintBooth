# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.46; invariant nearest 0.34161 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Spherulite Frost. Identity declared before rendering/scoring."""
from ..crystal_designs import spherulite_frost
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_spherulite_frost',
 'display_name': 'Spherulite Frost - spec overlay',
 'promise': 'Spherulite Frost assembles radiating crystal fans, frozen growth fronts, nucleation pits, '
            'fan boundary clefts and satellite ice tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Spherulite Frost assembles radiating crystal fans, frozen growth fronts, '
                    'nucleation pits, fan boundary clefts and satellite ice tabs. Geometry is '
                    'independently authored in crystal_designs.py:spherulite_frost.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to radiating crystal fans, '
                 'frozen growth fronts, nucleation pits, fan boundary clefts, satellite ice tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'radiating_crystal_fans',
                 'role': 'Radiating crystal fans use M/R/Cc intervals [(12, 248), (0, 246), (20, 248)] '
                         'in their own geometry.'},
                {'name': 'frozen_growth_fronts',
                 'role': 'Frozen growth fronts use M/R/Cc intervals [(136, 254), (0, 86), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'nucleation_pits',
                 'role': 'Nucleation pits use M/R/Cc intervals [(0, 94), (178, 255), (146, 252)] in '
                         'their own geometry.'},
                {'name': 'fan_boundary_clefts',
                 'role': 'Fan boundary clefts use M/R/Cc intervals [(40, 190), (120, 236), (66, 190)] '
                         'in their own geometry.'},
                {'name': 'satellite_ice_tabs',
                 'role': 'Satellite ice tabs use M/R/Cc intervals [(86, 232), (50, 174), (144, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['radiating_crystal_fans',
                            'frozen_growth_fronts',
                            'nucleation_pits',
                            'fan_boundary_clefts',
                            'satellite_ice_tabs'],
                      'R': ['radiating_crystal_fans',
                            'frozen_growth_fronts',
                            'nucleation_pits',
                            'fan_boundary_clefts',
                            'satellite_ice_tabs'],
                      'Cc': ['radiating_crystal_fans',
                             'frozen_growth_fronts',
                             'nucleation_pits',
                             'fan_boundary_clefts',
                             'satellite_ice_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Spherulite Frost must visibly separate through radiating crystal '
                                      'fans, frozen growth fronts, nucleation pits and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Spherulite Frost must visibly separate through radiating crystal '
                                      'fans, frozen growth fronts, nucleation pits and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Unequal radiating fans end in scalloped growth fronts.',
                                     'radiating crystal fans is present in the native named-feature '
                                     'coverage probe.',
                                     'frozen growth fronts is present in the native named-feature '
                                     'coverage probe.',
                                     'nucleation pits is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/spherulite_frost/independent-feature-carrier',
 'spec_key': 'spec-v2/spherulite_frost/named-material-bindings'}

render = build_renderer(spherulite_frost, IDENTITY_CONTRACT)

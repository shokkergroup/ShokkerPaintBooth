# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.85; invariant nearest 0.53115 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Triaxial Basket. Identity declared before rendering/scoring."""
from ..weave_designs import triaxial_basket
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_triaxial_basket',
 'display_name': 'Triaxial Basket - spec overlay',
 'promise': 'Triaxial Basket assembles horizontal tows, ascending tows, descending tows, triangular '
            'resin pockets and bundle frays.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Triaxial Basket assembles horizontal tows, ascending tows, descending tows, '
                    'triangular resin pockets and bundle frays. Geometry is independently authored in '
                    'weave_designs.py:triaxial_basket.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to horizontal tows, ascending '
                 'tows, descending tows, triangular resin pockets, bundle frays.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'horizontal_tows',
                 'role': 'Horizontal tows use M/R/Cc intervals [(6, 118), (124, 246), (16, 252)] in '
                         'their own geometry.'},
                {'name': 'ascending_tows',
                 'role': 'Ascending tows use M/R/Cc intervals [(110, 248), (20, 116), (16, 252)] in '
                         'their own geometry.'},
                {'name': 'descending_tows',
                 'role': 'Descending tows use M/R/Cc intervals [(36, 210), (44, 218), (16, 252)] in '
                         'their own geometry.'},
                {'name': 'triangular_resin_pockets',
                 'role': 'Triangular resin pockets use M/R/Cc intervals [(0, 84), (16, 68), (0, 106)] '
                         'in their own geometry.'},
                {'name': 'bundle_frays',
                 'role': 'Bundle frays use M/R/Cc intervals [(160, 255), (148, 255), (146, 254)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['horizontal_tows',
                            'ascending_tows',
                            'descending_tows',
                            'triangular_resin_pockets',
                            'bundle_frays'],
                      'R': ['horizontal_tows',
                            'ascending_tows',
                            'descending_tows',
                            'triangular_resin_pockets',
                            'bundle_frays'],
                      'Cc': ['horizontal_tows',
                             'ascending_tows',
                             'descending_tows',
                             'triangular_resin_pockets',
                             'bundle_frays']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Triaxial Basket must visibly separate through horizontal tows, '
                                      'ascending tows, descending tows and the remaining named marks, '
                                      'not color or parameter changes.'},
                       {'finish_id': 'spov2_leno_lock',
                        'difference': 'Triaxial Basket must visibly separate through horizontal tows, '
                                      'ascending tows, descending tows and the remaining named marks, '
                                      'not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three strand directions interlock around small crossovers.',
                                     'horizontal tows is present in the native named-feature coverage '
                                     'probe.',
                                     'ascending tows is present in the native named-feature coverage '
                                     'probe.',
                                     'descending tows is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/triaxial_basket/independent-feature-carrier',
 'spec_key': 'spec-v2/triaxial_basket/named-material-bindings'}

render = build_renderer(triaxial_basket, IDENTITY_CONTRACT)

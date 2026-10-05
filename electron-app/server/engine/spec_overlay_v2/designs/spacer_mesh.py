# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.71; invariant nearest 0.45333 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Spacer Mesh. Identity declared before rendering/scoring."""
from ..weave_designs import spacer_mesh
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_spacer_mesh',
 'display_name': 'Spacer Mesh - spec overlay',
 'promise': 'Spacer Mesh assembles spacer crowns, vertical pillars, buried diagonals, open window rims '
            'and resin bridge drops.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Spacer Mesh assembles spacer crowns, vertical pillars, buried diagonals, open '
                    'window rims and resin bridge drops. Geometry is independently authored in '
                    'weave_designs.py:spacer_mesh.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to spacer crowns, vertical '
                 'pillars, buried diagonals, open window rims, resin bridge drops.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'spacer_crowns',
                 'role': 'Spacer crowns use M/R/Cc intervals [(26, 246), (22, 212), (20, 248)] in their '
                         'own geometry.'},
                {'name': 'vertical_pillars',
                 'role': 'Vertical pillars use M/R/Cc intervals [(140, 254), (16, 106), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'buried_diagonals',
                 'role': 'Buried diagonals use M/R/Cc intervals [(0, 114), (170, 255), (140, 252)] in '
                         'their own geometry.'},
                {'name': 'open_window_rims',
                 'role': 'Open window rims use M/R/Cc intervals [(84, 218), (62, 186), (70, 222)] in '
                         'their own geometry.'},
                {'name': 'resin_bridge_drops',
                 'role': 'Resin bridge drops use M/R/Cc intervals [(4, 90), (16, 74), (16, 80)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['spacer_crowns',
                            'vertical_pillars',
                            'buried_diagonals',
                            'open_window_rims',
                            'resin_bridge_drops'],
                      'R': ['spacer_crowns',
                            'vertical_pillars',
                            'buried_diagonals',
                            'open_window_rims',
                            'resin_bridge_drops'],
                      'Cc': ['spacer_crowns',
                             'vertical_pillars',
                             'buried_diagonals',
                             'open_window_rims',
                             'resin_bridge_drops']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Spacer Mesh must visibly separate through spacer crowns, '
                                      'vertical pillars, buried diagonals and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Spacer Mesh must visibly separate through spacer crowns, '
                                      'vertical pillars, buried diagonals and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Open diagonal mesh windows are supported by corner ties.',
                                     'spacer crowns is present in the native named-feature coverage '
                                     'probe.',
                                     'vertical pillars is present in the native named-feature coverage '
                                     'probe.',
                                     'buried diagonals is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/spacer_mesh/independent-feature-carrier',
 'spec_key': 'spec-v2/spacer_mesh/named-material-bindings'}

render = build_renderer(spacer_mesh, IDENTITY_CONTRACT)

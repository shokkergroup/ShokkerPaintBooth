# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.1; invariant nearest 0.52483 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Ply Delamination. Identity declared before rendering/scoring."""
from ..weave_designs import ply_delamination
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_ply_delamination',
 'display_name': 'Ply Delamination - spec overlay',
 'promise': 'Ply Delamination assembles lifted ply shingles, peeled lips, exposed underlayers, bridging '
            'filaments and epoxy blisters.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Ply Delamination assembles lifted ply shingles, peeled lips, exposed underlayers, '
                    'bridging filaments and epoxy blisters. Geometry is independently authored in '
                    'weave_designs.py:ply_delamination.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to lifted ply shingles, peeled '
                 'lips, exposed underlayers, bridging filaments, epoxy blisters.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'lifted_ply_shingles',
                 'role': 'Lifted ply shingles use M/R/Cc intervals [(14, 246), (26, 202), (36, 246)] in '
                         'their own geometry.'},
                {'name': 'peeled_lips',
                 'role': 'Peeled lips use M/R/Cc intervals [(168, 255), (16, 80), (0, 92)] in their own '
                         'geometry.'},
                {'name': 'exposed_underlayers',
                 'role': 'Exposed underlayers use M/R/Cc intervals [(0, 110), (150, 254), (136, 252)] '
                         'in their own geometry.'},
                {'name': 'bridging_filaments',
                 'role': 'Bridging filaments use M/R/Cc intervals [(66, 218), (50, 174), (86, 230)] in '
                         'their own geometry.'},
                {'name': 'epoxy_blisters',
                 'role': 'Epoxy blisters use M/R/Cc intervals [(28, 172), (22, 94), (16, 86)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['lifted_ply_shingles',
                            'peeled_lips',
                            'exposed_underlayers',
                            'bridging_filaments',
                            'epoxy_blisters'],
                      'R': ['lifted_ply_shingles',
                            'peeled_lips',
                            'exposed_underlayers',
                            'bridging_filaments',
                            'epoxy_blisters'],
                      'Cc': ['lifted_ply_shingles',
                             'peeled_lips',
                             'exposed_underlayers',
                             'bridging_filaments',
                             'epoxy_blisters']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Ply Delamination must visibly separate through lifted ply '
                                      'shingles, peeled lips, exposed underlayers and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Ply Delamination must visibly separate through lifted ply '
                                      'shingles, peeled lips, exposed underlayers and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Torn triangular ply packets expose separate lower layers.',
                                     'lifted ply shingles is present in the native named-feature '
                                     'coverage probe.',
                                     'peeled lips is present in the native named-feature coverage '
                                     'probe.',
                                     'exposed underlayers is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/ply_delamination/independent-feature-carrier',
 'spec_key': 'spec-v2/ply_delamination/named-material-bindings'}

render = build_renderer(ply_delamination, IDENTITY_CONTRACT)

# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.56; invariant nearest 0.19777 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Hyperbolic Scales. Identity declared before rendering/scoring."""
from ..experimental_designs import hyperbolic_scales
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_hyperbolic_scales',
 'display_name': 'Hyperbolic Scales - spec overlay',
 'promise': 'Hyperbolic Scales assembles saddle scale faces, conjugate hyperbola rims, scale waist '
            'recesses, overlap corner studs and split cusp tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Hyperbolic Scales assembles saddle scale faces, conjugate hyperbola rims, scale '
                    'waist recesses, overlap corner studs and split cusp tabs. Geometry is '
                    'independently authored in experimental_designs.py:hyperbolic_scales.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to saddle scale faces, '
                 'conjugate hyperbola rims, scale waist recesses, overlap corner studs, split cusp '
                 'tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'saddle_scale_faces',
                 'role': 'Saddle scale faces use M/R/Cc intervals [(18, 246), (24, 216), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'conjugate_hyperbola_rims',
                 'role': 'Conjugate hyperbola rims use M/R/Cc intervals [(146, 255), (16, 108), (0, '
                         '114)] in their own geometry.'},
                {'name': 'scale_waist_recesses',
                 'role': 'Scale waist recesses use M/R/Cc intervals [(0, 100), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'overlap_corner_studs',
                 'role': 'Overlap corner studs use M/R/Cc intervals [(58, 204), (102, 232), (68, 212)] '
                         'in their own geometry.'},
                {'name': 'split_cusp_tabs',
                 'role': 'Split cusp tabs use M/R/Cc intervals [(96, 228), (54, 184), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['saddle_scale_faces',
                            'conjugate_hyperbola_rims',
                            'scale_waist_recesses',
                            'overlap_corner_studs',
                            'split_cusp_tabs'],
                      'R': ['saddle_scale_faces',
                            'conjugate_hyperbola_rims',
                            'scale_waist_recesses',
                            'overlap_corner_studs',
                            'split_cusp_tabs'],
                      'Cc': ['saddle_scale_faces',
                             'conjugate_hyperbola_rims',
                             'scale_waist_recesses',
                             'overlap_corner_studs',
                             'split_cusp_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Hyperbolic Scales must visibly separate through saddle scale '
                                      'faces, conjugate hyperbola rims, scale waist recesses and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Hyperbolic Scales must visibly separate through saddle scale '
                                      'faces, conjugate hyperbola rims, scale waist recesses and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Saddle plates have conjugate hyperbolic cuts and split cusp ends.',
                                     'saddle scale faces is present in the native named-feature '
                                     'coverage probe.',
                                     'conjugate hyperbola rims is present in the native named-feature '
                                     'coverage probe.',
                                     'scale waist recesses is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/hyperbolic_scales/independent-feature-carrier',
 'spec_key': 'spec-v2/hyperbolic_scales/named-material-bindings'}

render = build_renderer(hyperbolic_scales, IDENTITY_CONTRACT)

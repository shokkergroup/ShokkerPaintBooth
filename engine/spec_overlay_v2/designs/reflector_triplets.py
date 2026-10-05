# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.92; invariant nearest 0.27513 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Reflector Triplets. Identity declared before rendering/scoring."""
from ..optical_designs import reflector_triplets
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_reflector_triplets',
 'display_name': 'Reflector Triplets - spec overlay',
 'promise': 'Reflector Triplets assembles three corner faces, corner cube seams, central return pits, '
            'reflector border tabs and chipped cube tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Reflector Triplets assembles three corner faces, corner cube seams, central return '
                    'pits, reflector border tabs and chipped cube tips. Geometry is independently '
                    'authored in optical_designs.py:reflector_triplets.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to three corner faces, corner '
                 'cube seams, central return pits, reflector border tabs, chipped cube tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'three_corner_faces',
                 'role': 'Three corner faces use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'corner_cube_seams',
                 'role': 'Corner cube seams use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'central_return_pits',
                 'role': 'Central return pits use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'reflector_border_tabs',
                 'role': 'Reflector border tabs use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'chipped_cube_tips',
                 'role': 'Chipped cube tips use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['three_corner_faces',
                            'corner_cube_seams',
                            'central_return_pits',
                            'reflector_border_tabs',
                            'chipped_cube_tips'],
                      'R': ['three_corner_faces',
                            'corner_cube_seams',
                            'central_return_pits',
                            'reflector_border_tabs',
                            'chipped_cube_tips'],
                      'Cc': ['three_corner_faces',
                             'corner_cube_seams',
                             'central_return_pits',
                             'reflector_border_tabs',
                             'chipped_cube_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Reflector Triplets must visibly separate through three corner '
                                      'faces, corner cube seams, central return pits and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Reflector Triplets must visibly separate through three corner '
                                      'faces, corner cube seams, central return pits and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three-faced corner cubes sit inside raised hexagonal apertures.',
                                     'three corner faces is present in the native named-feature '
                                     'coverage probe.',
                                     'corner cube seams is present in the native named-feature coverage '
                                     'probe.',
                                     'central return pits is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/reflector_triplets/independent-feature-carrier',
 'spec_key': 'spec-v2/reflector_triplets/named-material-bindings'}

render = build_renderer(reflector_triplets, IDENTITY_CONTRACT)

# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 95.97; invariant nearest 0.49834 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Prism Herringbone. Identity declared before rendering/scoring."""
from ..optical_designs import prism_herringbone
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_prism_herringbone',
 'display_name': 'Prism Herringbone - spec overlay',
 'promise': 'Prism Herringbone assembles prismatic ribbons, ridge breaks, end face sockets, cross prism '
            'notches and polished terminal facets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Prism Herringbone assembles prismatic ribbons, ridge breaks, end face sockets, '
                    'cross prism notches and polished terminal facets. Geometry is independently '
                    'authored in optical_designs.py:prism_herringbone.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to prismatic ribbons, ridge '
                 'breaks, end face sockets, cross prism notches, polished terminal facets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'prismatic_ribbons',
                 'role': 'Prismatic ribbons use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'ridge_breaks',
                 'role': 'Ridge breaks use M/R/Cc intervals [(144, 255), (0, 92), (0, 114)] in their '
                         'own geometry.'},
                {'name': 'end_face_sockets',
                 'role': 'End face sockets use M/R/Cc intervals [(0, 98), (178, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'cross_prism_notches',
                 'role': 'Cross prism notches use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'polished_terminal_facets',
                 'role': 'Polished terminal facets use M/R/Cc intervals [(96, 228), (54, 180), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['prismatic_ribbons',
                            'ridge_breaks',
                            'end_face_sockets',
                            'cross_prism_notches',
                            'polished_terminal_facets'],
                      'R': ['prismatic_ribbons',
                            'ridge_breaks',
                            'end_face_sockets',
                            'cross_prism_notches',
                            'polished_terminal_facets'],
                      'Cc': ['prismatic_ribbons',
                             'ridge_breaks',
                             'end_face_sockets',
                             'cross_prism_notches',
                             'polished_terminal_facets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Prism Herringbone must visibly separate through prismatic '
                                      'ribbons, ridge breaks, end face sockets and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Prism Herringbone must visibly separate through prismatic '
                                      'ribbons, ridge breaks, end face sockets and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Linked zigzag prism strips terminate at alternating end joints.',
                                     'prismatic ribbons is present in the native named-feature coverage '
                                     'probe.',
                                     'ridge breaks is present in the native named-feature coverage '
                                     'probe.',
                                     'end face sockets is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/prism_herringbone/independent-feature-carrier',
 'spec_key': 'spec-v2/prism_herringbone/named-material-bindings'}

render = build_renderer(prism_herringbone, IDENTITY_CONTRACT)

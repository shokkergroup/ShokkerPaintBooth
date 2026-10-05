# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 90.21; invariant nearest 0.47883 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Quartz Clusters. Identity declared before rendering/scoring."""
from ..crystal_designs import quartz_clusters
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_quartz_clusters',
 'display_name': 'Quartz Clusters - spec overlay',
 'promise': 'Quartz Clusters assembles splayed crystal prisms, central intergrowth faces, pyramidal '
            'termination edges, root inclusion matrix and healed prism fractures.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Quartz Clusters assembles splayed crystal prisms, central intergrowth faces, '
                    'pyramidal termination edges, root inclusion matrix and healed prism fractures. '
                    'Geometry is independently authored in crystal_designs.py:quartz_clusters.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to splayed crystal prisms, '
                 'central intergrowth faces, pyramidal termination edges, root inclusion matrix, healed '
                 'prism fractures.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'splayed_crystal_prisms',
                 'role': 'Splayed crystal prisms use M/R/Cc intervals [(14, 244), (28, 218), (24, 246)] '
                         'in their own geometry.'},
                {'name': 'central_intergrowth_faces',
                 'role': 'Central intergrowth faces use M/R/Cc intervals [(146, 255), (16, 106), (0, '
                         '118)] in their own geometry.'},
                {'name': 'pyramidal_termination_edges',
                 'role': 'Pyramidal termination edges use M/R/Cc intervals [(0, 100), (178, 255), (144, '
                         '254)] in their own geometry.'},
                {'name': 'root_inclusion_matrix',
                 'role': 'Root inclusion matrix use M/R/Cc intervals [(50, 206), (98, 232), (68, 212)] '
                         'in their own geometry.'},
                {'name': 'healed_prism_fractures',
                 'role': 'Healed prism fractures use M/R/Cc intervals [(94, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['splayed_crystal_prisms',
                            'central_intergrowth_faces',
                            'pyramidal_termination_edges',
                            'root_inclusion_matrix',
                            'healed_prism_fractures'],
                      'R': ['splayed_crystal_prisms',
                            'central_intergrowth_faces',
                            'pyramidal_termination_edges',
                            'root_inclusion_matrix',
                            'healed_prism_fractures'],
                      'Cc': ['splayed_crystal_prisms',
                             'central_intergrowth_faces',
                             'pyramidal_termination_edges',
                             'root_inclusion_matrix',
                             'healed_prism_fractures']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Quartz Clusters must visibly separate through splayed crystal '
                                      'prisms, central intergrowth faces, pyramidal termination edges '
                                      'and the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Quartz Clusters must visibly separate through splayed crystal '
                                      'prisms, central intergrowth faces, pyramidal termination edges '
                                      'and the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Splayed pointed prisms share irregular intergrowth roots.',
                                     'splayed crystal prisms is present in the native named-feature '
                                     'coverage probe.',
                                     'central intergrowth faces is present in the native named-feature '
                                     'coverage probe.',
                                     'pyramidal termination edges is present in the native '
                                     'named-feature coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/quartz_clusters/independent-feature-carrier',
 'spec_key': 'spec-v2/quartz_clusters/named-material-bindings'}

render = build_renderer(quartz_clusters, IDENTITY_CONTRACT)

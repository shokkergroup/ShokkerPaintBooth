# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.35; invariant nearest 0.51376 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Weld-Pool Archive. Identity declared before scoring."""
from ..proof_designs import weld_pool_archive
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_weld_pool_archive',
 'display_name': 'Weld-Pool Archive — spec overlay',
 'promise': 'Three-sided corner seams contain overlapping scalloped weld beads, heat-affected toes, '
            'spatter and interrupted polished breaks.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'A decorative welded surface distinguishes solidified pool crowns '
                                    'from overlap edges and attached spatter.',
                       'sources': ['https://www.nist.gov/publications/simulation-and-analysis-g-ni-cellular-growth-during-laser-powder-deposition-ni-based']},
 'carrier_grammar': 'Three-sided corner seams contain overlapping scalloped weld beads, heat-affected '
                    'toes, spatter and interrupted polished breaks.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at solidification_crescents, '
                 'overlap_saddles, edge_toes, spatter_clusters, polished_breaks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'solidification_crescents',
                 'role': 'Material response follows the named solidification crescents feature.'},
                {'name': 'overlap_saddles',
                 'role': 'Material response follows the named overlap saddles feature.'},
                {'name': 'edge_toes', 'role': 'Material response follows the named edge toes feature.'},
                {'name': 'spatter_clusters',
                 'role': 'Material response follows the named spatter clusters feature.'},
                {'name': 'polished_breaks',
                 'role': 'Material response follows the named polished breaks feature.'}],
 'material_binding': {'M': ['solidification_crescents',
                            'overlap_saddles',
                            'edge_toes',
                            'spatter_clusters',
                            'polished_breaks'],
                      'R': ['solidification_crescents',
                            'overlap_saddles',
                            'edge_toes',
                            'spatter_clusters',
                            'polished_breaks'],
                      'Cc': ['solidification_crescents',
                             'overlap_saddles',
                             'edge_toes',
                             'spatter_clusters',
                             'polished_breaks']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'spec_weld_stack_rainbow',
                        'difference': 'Must differ through overlapping solidification crescents meet '
                                      'saddles, rough toes, compact spatter clusters and polished '
                                      'breaks.'},
                       {'finish_id': 'spec_titanium_heat_fishscale',
                        'difference': 'Must differ through overlapping solidification crescents meet '
                                      'saddles, rough toes, compact spatter clusters and polished '
                                      'breaks.'}],
 'name_truth': {'visible_evidence': ['Three-sided corner seams contain overlapping scalloped weld '
                                     'beads, heat-affected toes, spatter and interrupted polished '
                                     'breaks.',
                                     'solidification crescents is present in the native named-feature '
                                     'coverage probe.',
                                     'overlap saddles is present in the native named-feature coverage '
                                     'probe.',
                                     'edge toes is present in the native named-feature coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/weld_pool_archive/solidification_crescents:overlap_saddles:edge_toes:spatter_clusters:polished_breaks '
                     '/ independently reconstructed r4 / reconstructed r6',
 'spec_key': 'v2/weld_pool_archive/authored-feature-targets-and-coverage / named r4 features / named r6 '
             'bindings'}

render = build_renderer(weld_pool_archive, IDENTITY_CONTRACT)

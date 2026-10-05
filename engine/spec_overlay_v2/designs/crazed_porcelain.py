# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.44; invariant nearest 0.25879 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Crazed Porcelain. Identity declared before scoring."""
from ..proof_designs import crazed_porcelain
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_crazed_porcelain',
 'display_name': 'Crazed Porcelain — spec overlay',
 'promise': 'A warped quadrilateral glaze fracture network contains secondary arrested checks, glaze '
            'lips, tiny pore clusters and exposed corner chips.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Decorative interpretation of brittle coating fragmentation: '
                                    'fissures expose a substrate distinct from surviving glazed '
                                    'surfaces.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'A warped quadrilateral glaze fracture network contains secondary arrested checks, '
                    'glaze lips, tiny pore clusters and exposed corner chips.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at glaze_lips, primary_fissures, '
                 'secondary_checks, pore_clusters, exposed_chips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'glaze_lips',
                 'role': 'Material response follows the named glaze lips feature.'},
                {'name': 'primary_fissures',
                 'role': 'Material response follows the named primary fissures feature.'},
                {'name': 'secondary_checks',
                 'role': 'Material response follows the named secondary checks feature.'},
                {'name': 'pore_clusters',
                 'role': 'Material response follows the named pore clusters feature.'},
                {'name': 'exposed_chips',
                 'role': 'Material response follows the named exposed chips feature.'}],
 'material_binding': {'M': ['glaze_lips',
                            'primary_fissures',
                            'secondary_checks',
                            'pore_clusters',
                            'exposed_chips'],
                      'R': ['glaze_lips',
                            'primary_fissures',
                            'secondary_checks',
                            'pore_clusters',
                            'exposed_chips'],
                      'Cc': ['glaze_lips',
                             'primary_fissures',
                             'secondary_checks',
                             'pore_clusters',
                             'exposed_chips']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'crackle_network',
                        'difference': 'Must differ through fine irregular fissures interrupt glaze '
                                      'lips, secondary checks, pore clusters and exposed chips.'},
                       {'finish_id': 'voronoi_fracture',
                        'difference': 'Must differ through fine irregular fissures interrupt glaze '
                                      'lips, secondary checks, pore clusters and exposed chips.'}],
 'name_truth': {'visible_evidence': ['Warped glaze fissures divide platelets and arrest smaller checks.',
                                     'glaze lips is present in the native named-feature coverage probe.',
                                     'primary fissures is present in the native named-feature coverage '
                                     'probe.',
                                     'secondary checks is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/crazed_porcelain/glaze_lips:primary_fissures:secondary_checks:pore_clusters:exposed_chips '
                     '/ reconstructed r6',
 'spec_key': 'v2/crazed_porcelain/authored-feature-targets-and-coverage / named r6 bindings'}

render = build_renderer(crazed_porcelain, IDENTITY_CONTRACT)

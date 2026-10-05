# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.83; invariant nearest 0.22317 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Aperiodic Alloy. Identity declared before scoring."""
from ..proof_designs import aperiodic_alloy
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_aperiodic_alloy',
 'display_name': 'Aperiodic Alloy — spec overlay',
 'promise': 'Unequal inset tiles meet interrupted bridges, multiway junctions and locally scarred '
            'corners.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Beatty-sequence displacements make a nonrepeating decorative '
                                    'tessellation inspired by aperiodic tiling; this is not a '
                                    'reproduction or proof of the hat monotile.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Unequal inset tiles meet interrupted bridges, multiway junctions and locally '
                    'scarred corners.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at unequal_small_tiles, '
                 'multiway_junctions, inset_windows, interrupted_bridges, corner_scars.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'unequal_small_tiles',
                 'role': 'Material response follows the named unequal small tiles feature.'},
                {'name': 'multiway_junctions',
                 'role': 'Material response follows the named multiway junctions feature.'},
                {'name': 'inset_windows',
                 'role': 'Material response follows the named inset windows feature.'},
                {'name': 'interrupted_bridges',
                 'role': 'Material response follows the named interrupted bridges feature.'},
                {'name': 'corner_scars',
                 'role': 'Material response follows the named corner scars feature.'}],
 'material_binding': {'M': ['unequal_small_tiles',
                            'multiway_junctions',
                            'inset_windows',
                            'interrupted_bridges',
                            'corner_scars'],
                      'R': ['unequal_small_tiles',
                            'multiway_junctions',
                            'inset_windows',
                            'interrupted_bridges',
                            'corner_scars'],
                      'Cc': ['unequal_small_tiles',
                             'multiway_junctions',
                             'inset_windows',
                             'interrupted_bridges',
                             'corner_scars']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'spec_gunmetal_geo_tessellation',
                        'difference': 'Must differ through unequal inset tiles meet interrupted '
                                      'bridges, multiway junctions and locally scarred corners.'},
                       {'finish_id': 'architectural_grid',
                        'difference': 'Must differ through unequal inset tiles meet interrupted '
                                      'bridges, multiway junctions and locally scarred corners.'}],
 'name_truth': {'visible_evidence': ['Unequal multi-axis alloy windows contain distinct intervening '
                                     'facet edges.',
                                     'unequal small tiles is present in the native named-feature '
                                     'coverage probe.',
                                     'multiway junctions is present in the native named-feature '
                                     'coverage probe.',
                                     'inset windows is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/aperiodic_alloy/unequal_small_tiles:multiway_junctions:inset_windows:interrupted_bridges:corner_scars',
 'spec_key': 'v2/aperiodic_alloy/authored-feature-targets-and-coverage'}

render = build_renderer(aperiodic_alloy, IDENTITY_CONTRACT)

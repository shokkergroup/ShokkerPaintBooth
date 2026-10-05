# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.25; invariant nearest 0.22251 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Pit Lane Ghost. Identity declared before scoring."""
from ..proof_designs import pit_lane_ghost
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_pit_lane_ghost',
 'display_name': 'Pit Lane Ghost — spec overlay',
 'promise': 'Fine pit-stall corners and service-box outlines combine with independently placed lane '
            'ticks, corner tabs, worn scuffs and witness dots.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'A coat-led material stencil uses local roughness and coating '
                                    'differences to reveal fine racing symbols over unchanged paint.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Fine pit-stall corners and service-box outlines combine with independently placed '
                    'lane ticks, corner tabs, worn scuffs and witness dots.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at service_box_corners, '
                 'staggered_tick_clusters, corner_tabs, wear_scuffs, polished_witness_dots.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'service_box_corners',
                 'role': 'Material response follows the named service box corners feature.'},
                {'name': 'staggered_tick_clusters',
                 'role': 'Material response follows the named staggered tick clusters feature.'},
                {'name': 'corner_tabs',
                 'role': 'Material response follows the named corner tabs feature.'},
                {'name': 'wear_scuffs',
                 'role': 'Material response follows the named wear scuffs feature.'},
                {'name': 'polished_witness_dots',
                 'role': 'Material response follows the named polished witness dots feature.'}],
 'material_binding': {'M': ['service_box_corners',
                            'staggered_tick_clusters',
                            'corner_tabs',
                            'wear_scuffs',
                            'polished_witness_dots'],
                      'R': ['service_box_corners',
                            'staggered_tick_clusters',
                            'corner_tabs',
                            'wear_scuffs',
                            'polished_witness_dots'],
                      'Cc': ['service_box_corners',
                             'staggered_tick_clusters',
                             'corner_tabs',
                             'wear_scuffs',
                             'polished_witness_dots']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'checker_flag_subtle',
                        'difference': 'Must differ through tiny racing check packets, staggered ticks, '
                                      'corner tabs, witness dots and scuffed local breaks.'},
                       {'finish_id': 'cc_panel_fade',
                        'difference': 'Must differ through tiny racing check packets, staggered ticks, '
                                      'corner tabs, witness dots and scuffed local breaks.'}],
 'name_truth': {'visible_evidence': ['Short service-box corners, lane ticks and scuffs form pit-stall '
                                     'markings.',
                                     'service box corners is present in the native named-feature '
                                     'coverage probe.',
                                     'staggered tick clusters is present in the native named-feature '
                                     'coverage probe.',
                                     'corner tabs is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/pit_lane_ghost/service_box_corners:staggered_tick_clusters:corner_tabs:wear_scuffs:polished_witness_dots '
                     '/ independently reconstructed r4',
 'spec_key': 'v2/pit_lane_ghost/authored-feature-targets-and-coverage / named r4 features'}

render = build_renderer(pit_lane_ghost, IDENTITY_CONTRACT)

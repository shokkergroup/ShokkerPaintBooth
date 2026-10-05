# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.6; invariant nearest 0.47231 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Braided Junction. Identity declared before scoring."""
from ..proof_designs import braided_junction
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_braided_junction',
 'display_name': 'Braided Junction — spec overlay',
 'promise': 'Crossing tow bundles, raised overpasses, recessed underpasses, resin pockets and stitch '
            'collars.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Woven composite bundles alternate over and under neighboring tows '
                                    'while resin fills their junctions.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Crossing tow bundles, raised overpasses, recessed underpasses, resin pockets and '
                    'stitch collars.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at underpassing_bundles, '
                 'resin_pockets, overpassing_bundles, stitch_collars, loose_fiber_ends.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'underpassing_bundles',
                 'role': 'Material response follows the named underpassing bundles feature.'},
                {'name': 'resin_pockets',
                 'role': 'Material response follows the named resin pockets feature.'},
                {'name': 'overpassing_bundles',
                 'role': 'Material response follows the named overpassing bundles feature.'},
                {'name': 'stitch_collars',
                 'role': 'Material response follows the named stitch collars feature.'},
                {'name': 'loose_fiber_ends',
                 'role': 'Material response follows the named loose fiber ends feature.'}],
 'material_binding': {'M': ['underpassing_bundles',
                            'resin_pockets',
                            'overpassing_bundles',
                            'stitch_collars',
                            'loose_fiber_ends'],
                      'R': ['underpassing_bundles',
                            'resin_pockets',
                            'overpassing_bundles',
                            'stitch_collars',
                            'loose_fiber_ends'],
                      'Cc': ['underpassing_bundles',
                             'resin_pockets',
                             'overpassing_bundles',
                             'stitch_collars',
                             'loose_fiber_ends']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'carbon_weave',
                        'difference': 'Must differ through crossing tow bundles, raised overpasses, '
                                      'recessed underpasses, resin pockets and stitch collars.'},
                       {'finish_id': 'spec_carbon_2x2_twill',
                        'difference': 'Must differ through crossing tow bundles, raised overpasses, '
                                      'recessed underpasses, resin pockets and stitch collars.'}],
 'name_truth': {'visible_evidence': ['Looping strands cross at compact reinforced junctions.',
                                     'underpassing bundles is present in the native named-feature '
                                     'coverage probe.',
                                     'resin pockets is present in the native named-feature coverage '
                                     'probe.',
                                     'overpassing bundles is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/braided_junction/underpassing_bundles:resin_pockets:overpassing_bundles:stitch_collars:loose_fiber_ends',
 'spec_key': 'v2/braided_junction/authored-feature-targets-and-coverage'}

render = build_renderer(braided_junction, IDENTITY_CONTRACT)

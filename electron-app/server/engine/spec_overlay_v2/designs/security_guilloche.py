# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 95.91; invariant nearest 0.335 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Security Guilloché. Identity declared before scoring."""
from ..proof_designs import security_guilloche
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_security_guilloche',
 'display_name': 'Security Guilloché — spec overlay',
 'promise': 'Two independently placed engraving passes interlace fine figure-eight arclets, partial '
            'secondary arcs, recessed knots, beads and burnished crests. No isolated medallion lattice.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Engine-turning engraves intersecting straight and curved cuts; '
                                    'this design translates cut floors and crests into material states.',
                       'sources': ['https://www.breguet.com/en/breguet-house/1775-1801/appearance-guilloche-watchmaking']},
 'carrier_grammar': 'Two independently placed engraving passes interlace fine figure-eight arclets, '
                    'partial secondary arcs, recessed knots, beads and burnished crests. No isolated '
                    'medallion lattice.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at interlaced_arclets, '
                 'crossover_saddles, recessed_knots, beaded_borders, burnished_crests.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'interlaced_arclets',
                 'role': 'Material response follows the named interlaced arclets feature.'},
                {'name': 'crossover_saddles',
                 'role': 'Material response follows the named crossover saddles feature.'},
                {'name': 'recessed_knots',
                 'role': 'Material response follows the named recessed knots feature.'},
                {'name': 'beaded_borders',
                 'role': 'Material response follows the named beaded borders feature.'},
                {'name': 'burnished_crests',
                 'role': 'Material response follows the named burnished crests feature.'}],
 'material_binding': {'M': ['interlaced_arclets',
                            'crossover_saddles',
                            'recessed_knots',
                            'beaded_borders',
                            'burnished_crests'],
                      'R': ['interlaced_arclets',
                            'crossover_saddles',
                            'recessed_knots',
                            'beaded_borders',
                            'burnished_crests'],
                      'Cc': ['interlaced_arclets',
                             'crossover_saddles',
                             'recessed_knots',
                             'beaded_borders',
                             'burnished_crests']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'guilloche_waves',
                        'difference': 'Must differ through figure-eight engravings interlace around '
                                      'recessed knots, saddles, beaded borders and burnished crests.'},
                       {'finish_id': 'guilloche_moire',
                        'difference': 'Must differ through figure-eight engravings interlace around '
                                      'recessed knots, saddles, beaded borders and burnished crests.'}],
 'name_truth': {'visible_evidence': ['Interlaced figure-eight arclets meet engraved knots and beads.',
                                     'interlaced arclets is present in the native named-feature '
                                     'coverage probe.',
                                     'crossover saddles is present in the native named-feature coverage '
                                     'probe.',
                                     'recessed knots is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/security_guilloche/interlaced_arclets:crossover_saddles:recessed_knots:beaded_borders:burnished_crests '
                     '/ independently reconstructed r4',
 'spec_key': 'v2/security_guilloche/authored-feature-targets-and-coverage / named r4 features'}

render = build_renderer(security_guilloche, IDENTITY_CONTRACT)

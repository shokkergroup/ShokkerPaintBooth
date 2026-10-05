# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.32; invariant nearest 0.54313 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Toolpath Reversal. Identity declared before scoring."""
from ..proof_designs import toolpath_reversal
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_toolpath_reversal',
 'display_name': 'Toolpath Reversal — spec overlay',
 'promise': 'Alternating interrupted cuts with entry crescents, exit scallops, protected lands and '
            'compact burrs.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Interrupted cutting tool engagement leaves separate entry, land '
                                    'and exit surfaces.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Alternating interrupted cuts with entry crescents, exit scallops, protected lands '
                    'and compact burrs.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at overlap_lands, cut_segments, '
                 'entry_crescents, exit_scallops, compact_burrs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'overlap_lands',
                 'role': 'Material response follows the named overlap lands feature.'},
                {'name': 'cut_segments',
                 'role': 'Material response follows the named cut segments feature.'},
                {'name': 'entry_crescents',
                 'role': 'Material response follows the named entry crescents feature.'},
                {'name': 'exit_scallops',
                 'role': 'Material response follows the named exit scallops feature.'},
                {'name': 'compact_burrs',
                 'role': 'Material response follows the named compact burrs feature.'}],
 'material_binding': {'M': ['overlap_lands',
                            'cut_segments',
                            'entry_crescents',
                            'exit_scallops',
                            'compact_burrs'],
                      'R': ['overlap_lands',
                            'cut_segments',
                            'entry_crescents',
                            'exit_scallops',
                            'compact_burrs'],
                      'Cc': ['overlap_lands',
                             'cut_segments',
                             'entry_crescents',
                             'exit_scallops',
                             'compact_burrs']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'jeweling_circles',
                        'difference': 'Must differ through alternating interrupted cuts with entry '
                                      'crescents, exit scallops, protected lands and compact burrs.'},
                       {'finish_id': 'brushed_diagonal',
                        'difference': 'Must differ through alternating interrupted cuts with entry '
                                      'crescents, exit scallops, protected lands and compact burrs.'}],
 'name_truth': {'visible_evidence': ['Nested turnaround arcs terminate in short return legs.',
                                     'overlap lands is present in the native named-feature coverage '
                                     'probe.',
                                     'cut segments is present in the native named-feature coverage '
                                     'probe.',
                                     'entry crescents is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/toolpath_reversal/overlap_lands:cut_segments:entry_crescents:exit_scallops:compact_burrs',
 'spec_key': 'v2/toolpath_reversal/authored-feature-targets-and-coverage'}

render = build_renderer(toolpath_reversal, IDENTITY_CONTRACT)

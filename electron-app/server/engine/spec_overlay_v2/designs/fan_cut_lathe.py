# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.06; invariant nearest 0.45811 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Fan Cut Lathe. Identity declared before rendering/scoring."""
from ..machine_designs import fan_cut_lathe
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_fan_cut_lathe',
 'display_name': 'Fan Cut Lathe - spec overlay',
 'promise': 'Fan Cut Lathe assembles radial cut faces, hub collars, blade edges, peripheral chips and '
            'tool witness arcs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Fan Cut Lathe assembles radial cut faces, hub collars, blade edges, peripheral '
                    'chips and tool witness arcs. Geometry is independently authored in '
                    'machine_designs.py:fan_cut_lathe.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to radial cut faces, hub '
                 'collars, blade edges, peripheral chips, tool witness arcs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'radial_cut_faces',
                 'role': 'Radial cut faces use M/R/Cc intervals [(16, 248), (20, 216), (24, 232)] in '
                         'their own geometry.'},
                {'name': 'hub_collars',
                 'role': 'Hub collars use M/R/Cc intervals [(8, 100), (160, 255), (110, 252)] in their '
                         'own geometry.'},
                {'name': 'blade_edges',
                 'role': 'Blade edges use M/R/Cc intervals [(174, 255), (16, 100), (0, 128)] in their '
                         'own geometry.'},
                {'name': 'peripheral_chips',
                 'role': 'Peripheral chips use M/R/Cc intervals [(32, 158), (124, 242), (104, 226)] in '
                         'their own geometry.'},
                {'name': 'tool_witness_arcs',
                 'role': 'Tool witness arcs use M/R/Cc intervals [(84, 208), (45, 186), (68, 250)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['radial_cut_faces',
                            'hub_collars',
                            'blade_edges',
                            'peripheral_chips',
                            'tool_witness_arcs'],
                      'R': ['radial_cut_faces',
                            'hub_collars',
                            'blade_edges',
                            'peripheral_chips',
                            'tool_witness_arcs'],
                      'Cc': ['radial_cut_faces',
                             'hub_collars',
                             'blade_edges',
                             'peripheral_chips',
                             'tool_witness_arcs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Fan Cut Lathe must visibly separate through radial cut faces, '
                                      'hub collars, blade edges and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Fan Cut Lathe must visibly separate through radial cut faces, '
                                      'hub collars, blade edges and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Radial tool-cut faces surround a small lathe hub.',
                                     'radial cut faces is present in the native named-feature coverage '
                                     'probe.',
                                     'hub collars is present in the native named-feature coverage '
                                     'probe.',
                                     'blade edges is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/fan_cut_lathe/independent-feature-carrier',
 'spec_key': 'spec-v2/fan_cut_lathe/named-material-bindings'}

render = build_renderer(fan_cut_lathe, IDENTITY_CONTRACT)

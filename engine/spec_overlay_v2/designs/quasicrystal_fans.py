# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.87; invariant nearest 0.22467 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Quasicrystal Fans. Identity declared before rendering/scoring."""
from ..experimental_designs import quasicrystal_fans
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_quasicrystal_fans',
 'display_name': 'Quasicrystal Fans - spec overlay',
 'promise': 'Quasicrystal Fans assembles five axis facet packets, quasiperiodic bond edges, deep '
            'interference nodes, fan crossing saddles and growth front islets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Quasicrystal Fans assembles five axis facet packets, quasiperiodic bond edges, '
                    'deep interference nodes, fan crossing saddles and growth front islets. Geometry is '
                    'independently authored in experimental_designs.py:quasicrystal_fans.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to five axis facet packets, '
                 'quasiperiodic bond edges, deep interference nodes, fan crossing saddles, growth front '
                 'islets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'five_axis_facet_packets',
                 'role': 'Five axis facet packets use M/R/Cc intervals [(18, 246), (24, 214), (24, '
                         '248)] in their own geometry.'},
                {'name': 'quasiperiodic_bond_edges',
                 'role': 'Quasiperiodic bond edges use M/R/Cc intervals [(146, 255), (16, 108), (0, '
                         '114)] in their own geometry.'},
                {'name': 'deep_interference_nodes',
                 'role': 'Deep interference nodes use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'fan_crossing_saddles',
                 'role': 'Fan crossing saddles use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'growth_front_islets',
                 'role': 'Growth front islets use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['five_axis_facet_packets',
                            'quasiperiodic_bond_edges',
                            'deep_interference_nodes',
                            'fan_crossing_saddles',
                            'growth_front_islets'],
                      'R': ['five_axis_facet_packets',
                            'quasiperiodic_bond_edges',
                            'deep_interference_nodes',
                            'fan_crossing_saddles',
                            'growth_front_islets'],
                      'Cc': ['five_axis_facet_packets',
                             'quasiperiodic_bond_edges',
                             'deep_interference_nodes',
                             'fan_crossing_saddles',
                             'growth_front_islets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Quasicrystal Fans must visibly separate through five axis facet '
                                      'packets, quasiperiodic bond edges, deep interference nodes and '
                                      'the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Quasicrystal Fans must visibly separate through five axis facet '
                                      'packets, quasiperiodic bond edges, deep interference nodes and '
                                      'the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Five-axis interference facets form unequal quasiperiodic '
                                     'rosettes.',
                                     'five axis facet packets is present in the native named-feature '
                                     'coverage probe.',
                                     'quasiperiodic bond edges is present in the native named-feature '
                                     'coverage probe.',
                                     'deep interference nodes is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/quasicrystal_fans/independent-feature-carrier',
 'spec_key': 'spec-v2/quasicrystal_fans/named-material-bindings'}

render = build_renderer(quasicrystal_fans, IDENTITY_CONTRACT)

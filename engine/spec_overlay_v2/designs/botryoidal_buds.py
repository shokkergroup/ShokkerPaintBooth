# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.16; invariant nearest 0.53922 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Botryoidal Buds. Identity declared before rendering/scoring."""
from ..crystal_designs import botryoidal_buds
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_botryoidal_buds',
 'display_name': 'Botryoidal Buds - spec overlay',
 'promise': 'Botryoidal Buds assembles merged mineral buds, growth layer rings, bud junction valleys, '
            'satellite nodules and fractured bud windows.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Botryoidal Buds assembles merged mineral buds, growth layer rings, bud junction '
                    'valleys, satellite nodules and fractured bud windows. Geometry is independently '
                    'authored in crystal_designs.py:botryoidal_buds.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to merged mineral buds, growth '
                 'layer rings, bud junction valleys, satellite nodules, fractured bud windows.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'merged_mineral_buds',
                 'role': 'Merged mineral buds use M/R/Cc intervals [(18, 246), (26, 216), (20, 246)] in '
                         'their own geometry.'},
                {'name': 'growth_layer_rings',
                 'role': 'Growth layer rings use M/R/Cc intervals [(134, 255), (16, 94), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'bud_junction_valleys',
                 'role': 'Bud junction valleys use M/R/Cc intervals [(0, 100), (172, 255), (142, 252)] '
                         'in their own geometry.'},
                {'name': 'satellite_nodules',
                 'role': 'Satellite nodules use M/R/Cc intervals [(62, 214), (78, 206), (76, 220)] in '
                         'their own geometry.'},
                {'name': 'fractured_bud_windows',
                 'role': 'Fractured bud windows use M/R/Cc intervals [(30, 168), (124, 236), (170, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['merged_mineral_buds',
                            'growth_layer_rings',
                            'bud_junction_valleys',
                            'satellite_nodules',
                            'fractured_bud_windows'],
                      'R': ['merged_mineral_buds',
                            'growth_layer_rings',
                            'bud_junction_valleys',
                            'satellite_nodules',
                            'fractured_bud_windows'],
                      'Cc': ['merged_mineral_buds',
                             'growth_layer_rings',
                             'bud_junction_valleys',
                             'satellite_nodules',
                             'fractured_bud_windows']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Botryoidal Buds must visibly separate through merged mineral '
                                      'buds, growth layer rings, bud junction valleys and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Botryoidal Buds must visibly separate through merged mineral '
                                      'buds, growth layer rings, bud junction valleys and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Paired rounded mineral buds retain their merged growth '
                                     'boundaries.',
                                     'merged mineral buds is present in the native named-feature '
                                     'coverage probe.',
                                     'growth layer rings is present in the native named-feature '
                                     'coverage probe.',
                                     'bud junction valleys is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/botryoidal_buds/independent-feature-carrier',
 'spec_key': 'spec-v2/botryoidal_buds/named-material-bindings'}

render = build_renderer(botryoidal_buds, IDENTITY_CONTRACT)

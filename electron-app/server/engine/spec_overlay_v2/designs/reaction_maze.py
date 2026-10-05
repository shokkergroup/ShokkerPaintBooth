# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.65; invariant nearest 0.21101 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Reaction Maze. Identity declared before rendering/scoring."""
from ..experimental_designs import reaction_maze
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_reaction_maze',
 'display_name': 'Reaction Maze - spec overlay',
 'promise': 'Reaction Maze assembles reaction front ribbons, branching front crests, depleted reaction '
            'pools, front collision nodes and nucleation seed pores.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Reaction Maze assembles reaction front ribbons, branching front crests, depleted '
                    'reaction pools, front collision nodes and nucleation seed pores. Geometry is '
                    'independently authored in experimental_designs.py:reaction_maze.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to reaction front ribbons, '
                 'branching front crests, depleted reaction pools, front collision nodes, nucleation '
                 'seed pores.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'reaction_front_ribbons',
                 'role': 'Reaction front ribbons use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'branching_front_crests',
                 'role': 'Branching front crests use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'depleted_reaction_pools',
                 'role': 'Depleted reaction pools use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'front_collision_nodes',
                 'role': 'Front collision nodes use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'nucleation_seed_pores',
                 'role': 'Nucleation seed pores use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['reaction_front_ribbons',
                            'branching_front_crests',
                            'depleted_reaction_pools',
                            'front_collision_nodes',
                            'nucleation_seed_pores'],
                      'R': ['reaction_front_ribbons',
                            'branching_front_crests',
                            'depleted_reaction_pools',
                            'front_collision_nodes',
                            'nucleation_seed_pores'],
                      'Cc': ['reaction_front_ribbons',
                             'branching_front_crests',
                             'depleted_reaction_pools',
                             'front_collision_nodes',
                             'nucleation_seed_pores']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Reaction Maze must visibly separate through reaction front '
                                      'ribbons, branching front crests, depleted reaction pools and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Reaction Maze must visibly separate through reaction front '
                                      'ribbons, branching front crests, depleted reaction pools and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['A connected fine maze contains separate reaction-like banks and '
                                     'nodes.',
                                     'reaction front ribbons is present in the native named-feature '
                                     'coverage probe.',
                                     'branching front crests is present in the native named-feature '
                                     'coverage probe.',
                                     'depleted reaction pools is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/reaction_maze/independent-feature-carrier',
 'spec_key': 'spec-v2/reaction_maze/named-material-bindings'}

render = build_renderer(reaction_maze, IDENTITY_CONTRACT)

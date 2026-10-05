# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 94.95; invariant nearest 0.29586 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Coral Polyps. Identity declared before rendering/scoring."""
from ..skin_designs import coral_polyps
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_coral_polyps',
 'display_name': 'Coral Polyps - spec overlay',
 'promise': 'Coral Polyps assembles polyp septa, calice walls, central mouths, connecting coenosteum '
            'and budding sockets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Coral Polyps assembles polyp septa, calice walls, central mouths, connecting '
                    'coenosteum and budding sockets. Geometry is independently authored in '
                    'skin_designs.py:coral_polyps.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to polyp septa, calice walls, '
                 'central mouths, connecting coenosteum, budding sockets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'polyp_septa',
                 'role': 'Polyp septa use M/R/Cc intervals [(18, 248), (24, 204), (24, 246)] in their '
                         'own geometry.'},
                {'name': 'calice_walls',
                 'role': 'Calice walls use M/R/Cc intervals [(140, 255), (16, 106), (0, 104)] in their '
                         'own geometry.'},
                {'name': 'central_mouths',
                 'role': 'Central mouths use M/R/Cc intervals [(0, 90), (178, 255), (148, 254)] in '
                         'their own geometry.'},
                {'name': 'connecting_coenosteum',
                 'role': 'Connecting coenosteum use M/R/Cc intervals [(46, 194), (102, 230), (64, 194)] '
                         'in their own geometry.'},
                {'name': 'budding_sockets',
                 'role': 'Budding sockets use M/R/Cc intervals [(92, 222), (58, 192), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['polyp_septa',
                            'calice_walls',
                            'central_mouths',
                            'connecting_coenosteum',
                            'budding_sockets'],
                      'R': ['polyp_septa',
                            'calice_walls',
                            'central_mouths',
                            'connecting_coenosteum',
                            'budding_sockets'],
                      'Cc': ['polyp_septa',
                             'calice_walls',
                             'central_mouths',
                             'connecting_coenosteum',
                             'budding_sockets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Coral Polyps must visibly separate through polyp septa, calice '
                                      'walls, central mouths and the remaining named marks, not color '
                                      'or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Coral Polyps must visibly separate through polyp septa, calice '
                                      'walls, central mouths and the remaining named marks, not color '
                                      'or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Unequal budding calices connect through short colony branches.',
                                     'polyp septa is present in the native named-feature coverage '
                                     'probe.',
                                     'calice walls is present in the native named-feature coverage '
                                     'probe.',
                                     'central mouths is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/coral_polyps/independent-feature-carrier',
 'spec_key': 'spec-v2/coral_polyps/named-material-bindings'}

render = build_renderer(coral_polyps, IDENTITY_CONTRACT)

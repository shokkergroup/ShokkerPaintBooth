# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.3; invariant nearest 0.36456 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Leaf Stomata. Identity declared before rendering/scoring."""
from ..skin_designs import leaf_stomata
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_leaf_stomata',
 'display_name': 'Leaf Stomata - spec overlay',
 'promise': 'Leaf Stomata assembles guard cell pairs, stomatal apertures, raised pore lips, cuticle '
            'folds and wax platelets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Leaf Stomata assembles guard cell pairs, stomatal apertures, raised pore lips, '
                    'cuticle folds and wax platelets. Geometry is independently authored in '
                    'skin_designs.py:leaf_stomata.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to guard cell pairs, stomatal '
                 'apertures, raised pore lips, cuticle folds, wax platelets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'guard_cell_pairs',
                 'role': 'Guard cell pairs use M/R/Cc intervals [(16, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'stomatal_apertures',
                 'role': 'Stomatal apertures use M/R/Cc intervals [(0, 94), (178, 255), (140, 254)] in '
                         'their own geometry.'},
                {'name': 'raised_pore_lips',
                 'role': 'Raised pore lips use M/R/Cc intervals [(150, 255), (0, 86), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'cuticle_folds',
                 'role': 'Cuticle folds use M/R/Cc intervals [(62, 200), (100, 230), (68, 200)] in '
                         'their own geometry.'},
                {'name': 'wax_platelets',
                 'role': 'Wax platelets use M/R/Cc intervals [(100, 232), (54, 182), (160, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['guard_cell_pairs',
                            'stomatal_apertures',
                            'raised_pore_lips',
                            'cuticle_folds',
                            'wax_platelets'],
                      'R': ['guard_cell_pairs',
                            'stomatal_apertures',
                            'raised_pore_lips',
                            'cuticle_folds',
                            'wax_platelets'],
                      'Cc': ['guard_cell_pairs',
                             'stomatal_apertures',
                             'raised_pore_lips',
                             'cuticle_folds',
                             'wax_platelets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Leaf Stomata must visibly separate through guard cell pairs, '
                                      'stomatal apertures, raised pore lips and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Leaf Stomata must visibly separate through guard cell pairs, '
                                      'stomatal apertures, raised pore lips and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Kidney-like guard cells surround a narrow pore amid cuticle '
                                     'folds.',
                                     'guard cell pairs is present in the native named-feature coverage '
                                     'probe.',
                                     'stomatal apertures is present in the native named-feature '
                                     'coverage probe.',
                                     'raised pore lips is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/leaf_stomata/independent-feature-carrier',
 'spec_key': 'spec-v2/leaf_stomata/named-material-bindings'}

render = build_renderer(leaf_stomata, IDENTITY_CONTRACT)

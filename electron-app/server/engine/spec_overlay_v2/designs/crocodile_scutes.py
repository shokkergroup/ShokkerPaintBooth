# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.39; invariant nearest 0.52715 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Crocodile Scutes. Identity declared before rendering/scoring."""
from ..skin_designs import crocodile_scutes
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_crocodile_scutes',
 'display_name': 'Crocodile Scutes - spec overlay',
 'promise': 'Crocodile Scutes assembles scute plates, raised dorsal keels, flexible sutures, sensory '
            'pits and growth corner rings.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Crocodile Scutes assembles scute plates, raised dorsal keels, flexible sutures, '
                    'sensory pits and growth corner rings. Geometry is independently authored in '
                    'skin_designs.py:crocodile_scutes.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to scute plates, raised dorsal '
                 'keels, flexible sutures, sensory pits, growth corner rings.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'scute_plates',
                 'role': 'Scute plates use M/R/Cc intervals [(16, 240), (0, 244), (24, 250)] in their '
                         'own geometry.'},
                {'name': 'raised_dorsal_keels',
                 'role': 'Raised dorsal keels use M/R/Cc intervals [(156, 255), (0, 94), (0, 106)] in '
                         'their own geometry.'},
                {'name': 'flexible_sutures',
                 'role': 'Flexible sutures use M/R/Cc intervals [(0, 108), (170, 255), (130, 252)] in '
                         'their own geometry.'},
                {'name': 'sensory_pits',
                 'role': 'Sensory pits use M/R/Cc intervals [(34, 180), (126, 242), (68, 192)] in their '
                         'own geometry.'},
                {'name': 'growth_corner_rings',
                 'role': 'Growth corner rings use M/R/Cc intervals [(88, 224), (54, 182), (156, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['scute_plates',
                            'raised_dorsal_keels',
                            'flexible_sutures',
                            'sensory_pits',
                            'growth_corner_rings'],
                      'R': ['scute_plates',
                            'raised_dorsal_keels',
                            'flexible_sutures',
                            'sensory_pits',
                            'growth_corner_rings'],
                      'Cc': ['scute_plates',
                             'raised_dorsal_keels',
                             'flexible_sutures',
                             'sensory_pits',
                             'growth_corner_rings']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Crocodile Scutes must visibly separate through scute plates, '
                                      'raised dorsal keels, flexible sutures and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Crocodile Scutes must visibly separate through scute plates, '
                                      'raised dorsal keels, flexible sutures and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Paired dorsal plates contain longitudinal keels and sensory pits.',
                                     'scute plates is present in the native named-feature coverage '
                                     'probe.',
                                     'raised dorsal keels is present in the native named-feature '
                                     'coverage probe.',
                                     'flexible sutures is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/crocodile_scutes/independent-feature-carrier',
 'spec_key': 'spec-v2/crocodile_scutes/named-material-bindings'}

render = build_renderer(crocodile_scutes, IDENTITY_CONTRACT)

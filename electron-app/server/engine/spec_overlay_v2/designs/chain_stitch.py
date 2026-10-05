# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.96; invariant nearest 0.53664 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Chain Stitch. Identity declared before rendering/scoring."""
from ..weave_designs import chain_stitch
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_chain_stitch',
 'display_name': 'Chain Stitch - spec overlay',
 'promise': 'Chain Stitch assembles forward chain links, return chain links, locking bars, needle '
            'eyelets and tension scars.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Chain Stitch assembles forward chain links, return chain links, locking bars, '
                    'needle eyelets and tension scars. Geometry is independently authored in '
                    'weave_designs.py:chain_stitch.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to forward chain links, return '
                 'chain links, locking bars, needle eyelets, tension scars.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'forward_chain_links',
                 'role': 'Forward chain links use M/R/Cc intervals [(44, 242), (18, 172), (24, 234)] in '
                         'their own geometry.'},
                {'name': 'return_chain_links',
                 'role': 'Return chain links use M/R/Cc intervals [(132, 255), (30, 128), (0, 116)] in '
                         'their own geometry.'},
                {'name': 'locking_bars',
                 'role': 'Locking bars use M/R/Cc intervals [(0, 100), (166, 255), (138, 254)] in their '
                         'own geometry.'},
                {'name': 'needle_eyelets',
                 'role': 'Needle eyelets use M/R/Cc intervals [(12, 160), (110, 244), (68, 210)] in '
                         'their own geometry.'},
                {'name': 'tension_scars',
                 'role': 'Tension scars use M/R/Cc intervals [(100, 232), (62, 202), (134, 252)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['forward_chain_links',
                            'return_chain_links',
                            'locking_bars',
                            'needle_eyelets',
                            'tension_scars'],
                      'R': ['forward_chain_links',
                            'return_chain_links',
                            'locking_bars',
                            'needle_eyelets',
                            'tension_scars'],
                      'Cc': ['forward_chain_links',
                             'return_chain_links',
                             'locking_bars',
                             'needle_eyelets',
                             'tension_scars']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Chain Stitch must visibly separate through forward chain links, '
                                      'return chain links, locking bars and the remaining named marks, '
                                      'not color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Chain Stitch must visibly separate through forward chain links, '
                                      'return chain links, locking bars and the remaining named marks, '
                                      'not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Successive loops chain through small protected underpasses.',
                                     'forward chain links is present in the native named-feature '
                                     'coverage probe.',
                                     'return chain links is present in the native named-feature '
                                     'coverage probe.',
                                     'locking bars is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/chain_stitch/independent-feature-carrier',
 'spec_key': 'spec-v2/chain_stitch/named-material-bindings'}

render = build_renderer(chain_stitch, IDENTITY_CONTRACT)

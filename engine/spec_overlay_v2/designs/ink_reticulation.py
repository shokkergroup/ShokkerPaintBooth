# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.27; invariant nearest 0.21383 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Ink Reticulation. Identity declared before rendering/scoring."""
from ..liquid_designs import ink_reticulation
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_ink_reticulation',
 'display_name': 'Ink Reticulation - spec overlay',
 'promise': 'Ink Reticulation assembles reticulated film banks, rupture network, retained ink pools, '
            'short drying feathers and pigment aggregate islets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Ink Reticulation assembles reticulated film banks, rupture network, retained ink '
                    'pools, short drying feathers and pigment aggregate islets. Geometry is '
                    'independently authored in liquid_designs.py:ink_reticulation.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to reticulated film banks, '
                 'rupture network, retained ink pools, short drying feathers, pigment aggregate islets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'reticulated_film_banks',
                 'role': 'Reticulated film banks use M/R/Cc intervals [(18, 242), (0, 242), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'rupture_network',
                 'role': 'Rupture network use M/R/Cc intervals [(142, 255), (0, 94), (0, 114)] in their '
                         'own geometry.'},
                {'name': 'retained_ink_pools',
                 'role': 'Retained ink pools use M/R/Cc intervals [(0, 102), (176, 255), (144, 254)] in '
                         'their own geometry.'},
                {'name': 'short_drying_feathers',
                 'role': 'Short drying feathers use M/R/Cc intervals [(58, 206), (100, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'pigment_aggregate_islets',
                 'role': 'Pigment aggregate islets use M/R/Cc intervals [(98, 230), (54, 178), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['reticulated_film_banks',
                            'rupture_network',
                            'retained_ink_pools',
                            'short_drying_feathers',
                            'pigment_aggregate_islets'],
                      'R': ['reticulated_film_banks',
                            'rupture_network',
                            'retained_ink_pools',
                            'short_drying_feathers',
                            'pigment_aggregate_islets'],
                      'Cc': ['reticulated_film_banks',
                             'rupture_network',
                             'retained_ink_pools',
                             'short_drying_feathers',
                             'pigment_aggregate_islets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Ink Reticulation must visibly separate through reticulated film '
                                      'banks, rupture network, retained ink pools and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Ink Reticulation must visibly separate through reticulated film '
                                      'banks, rupture network, retained ink pools and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Fine irregular film banks surround retained ink pools and pigment '
                                     'islands.',
                                     'reticulated film banks is present in the native named-feature '
                                     'coverage probe.',
                                     'rupture network is present in the native named-feature coverage '
                                     'probe.',
                                     'retained ink pools is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/ink_reticulation/independent-feature-carrier',
 'spec_key': 'spec-v2/ink_reticulation/named-material-bindings'}

render = build_renderer(ink_reticulation, IDENTITY_CONTRACT)

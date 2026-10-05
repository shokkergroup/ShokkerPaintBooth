# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.67; invariant nearest 0.42947 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Crossed Hone. Identity declared before rendering/scoring."""
from ..machine_designs import crossed_hone
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_crossed_hone',
 'display_name': 'Crossed Hone - spec overlay',
 'promise': 'Crossed Hone assembles abrasive lands, forward grooves, return grooves, crossing burrs and '
            'trapped grit.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Crossed Hone assembles abrasive lands, forward grooves, return grooves, crossing '
                    'burrs and trapped grit. Geometry is independently authored in '
                    'machine_designs.py:crossed_hone.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to abrasive lands, forward '
                 'grooves, return grooves, crossing burrs, trapped grit.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'abrasive_lands',
                 'role': 'Abrasive lands use M/R/Cc intervals [(24, 178), (55, 184), (36, 224)] in '
                         'their own geometry.'},
                {'name': 'forward_grooves',
                 'role': 'Forward grooves use M/R/Cc intervals [(170, 255), (10, 96), (18, 108)] in '
                         'their own geometry.'},
                {'name': 'return_grooves',
                 'role': 'Return grooves use M/R/Cc intervals [(4, 94), (160, 253), (106, 246)] in '
                         'their own geometry.'},
                {'name': 'crossing_burrs',
                 'role': 'Crossing burrs use M/R/Cc intervals [(92, 225), (68, 220), (0, 190)] in their '
                         'own geometry.'},
                {'name': 'trapped_grit',
                 'role': 'Trapped grit use M/R/Cc intervals [(8, 84), (186, 255), (170, 255)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['abrasive_lands',
                            'forward_grooves',
                            'return_grooves',
                            'crossing_burrs',
                            'trapped_grit'],
                      'R': ['abrasive_lands',
                            'forward_grooves',
                            'return_grooves',
                            'crossing_burrs',
                            'trapped_grit'],
                      'Cc': ['abrasive_lands',
                             'forward_grooves',
                             'return_grooves',
                             'crossing_burrs',
                             'trapped_grit']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Crossed Hone must visibly separate through abrasive lands, '
                                      'forward grooves, return grooves and the remaining named marks, '
                                      'not color or parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Crossed Hone must visibly separate through abrasive lands, '
                                      'forward grooves, return grooves and the remaining named marks, '
                                      'not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Crossed straight abrasive cuts meet small trapped grit pockets.',
                                     'abrasive lands is present in the native named-feature coverage '
                                     'probe.',
                                     'forward grooves is present in the native named-feature coverage '
                                     'probe.',
                                     'return grooves is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/crossed_hone/independent-feature-carrier',
 'spec_key': 'spec-v2/crossed_hone/named-material-bindings'}

render = build_renderer(crossed_hone, IDENTITY_CONTRACT)

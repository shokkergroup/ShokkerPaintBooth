# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.15; invariant nearest 0.50497 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Resin Fray. Identity declared before rendering/scoring."""
from ..weave_designs import resin_fray
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_resin_fray',
 'display_name': 'Resin Fray - spec overlay',
 'promise': 'Resin Fray assembles resin islands, frayed fiber fans, bundle collars, dry fiber knots and '
            'fractured resin tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Resin Fray assembles resin islands, frayed fiber fans, bundle collars, dry fiber '
                    'knots and fractured resin tips. Geometry is independently authored in '
                    'weave_designs.py:resin_fray.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to resin islands, frayed fiber '
                 'fans, bundle collars, dry fiber knots, fractured resin tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'resin_islands',
                 'role': 'Resin islands use M/R/Cc intervals [(6, 108), (16, 112), (16, 252)] in their '
                         'own geometry.'},
                {'name': 'frayed_fiber_fans',
                 'role': 'Frayed fiber fans use M/R/Cc intervals [(134, 255), (42, 214), (68, 250)] in '
                         'their own geometry.'},
                {'name': 'bundle_collars',
                 'role': 'Bundle collars use M/R/Cc intervals [(48, 224), (16, 96), (0, 90)] in their '
                         'own geometry.'},
                {'name': 'dry_fiber_knots',
                 'role': 'Dry fiber knots use M/R/Cc intervals [(0, 82), (196, 255), (0, 108)] in their '
                         'own geometry.'},
                {'name': 'fractured_resin_tips',
                 'role': 'Fractured resin tips use M/R/Cc intervals [(88, 238), (114, 240), (108, 244)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['resin_islands',
                            'frayed_fiber_fans',
                            'bundle_collars',
                            'dry_fiber_knots',
                            'fractured_resin_tips'],
                      'R': ['resin_islands',
                            'frayed_fiber_fans',
                            'bundle_collars',
                            'dry_fiber_knots',
                            'fractured_resin_tips'],
                      'Cc': ['resin_islands',
                             'frayed_fiber_fans',
                             'bundle_collars',
                             'dry_fiber_knots',
                             'fractured_resin_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Resin Fray must visibly separate through resin islands, frayed '
                                      'fiber fans, bundle collars and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Resin Fray must visibly separate through resin islands, frayed '
                                      'fiber fans, bundle collars and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Frayed fiber fragments remain connected to broken resin outlines.',
                                     'resin islands is present in the native named-feature coverage '
                                     'probe.',
                                     'frayed fiber fans is present in the native named-feature coverage '
                                     'probe.',
                                     'bundle collars is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/resin_fray/independent-feature-carrier',
 'spec_key': 'spec-v2/resin_fray/named-material-bindings'}

render = build_renderer(resin_fray, IDENTITY_CONTRACT)

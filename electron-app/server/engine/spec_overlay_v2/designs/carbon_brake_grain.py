# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.45; invariant nearest 0.5011 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Carbon Brake Grain. Identity declared before rendering/scoring."""
from ..track_designs import carbon_brake_grain
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_carbon_brake_grain',
 'display_name': 'Carbon Brake Grain - spec overlay',
 'promise': 'Carbon Brake Grain assembles compacted carbon grains, fractured fiber fragments, venting '
            'matrix pores, resin conversion rims and polished grain tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Carbon Brake Grain assembles compacted carbon grains, fractured fiber fragments, '
                    'venting matrix pores, resin conversion rims and polished grain tips. Geometry is '
                    'independently authored in track_designs.py:carbon_brake_grain.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to compacted carbon grains, '
                 'fractured fiber fragments, venting matrix pores, resin conversion rims, polished '
                 'grain tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'compacted_carbon_grains',
                 'role': 'Compacted carbon grains use M/R/Cc intervals [(14, 228), (34, 232), (24, '
                         '248)] in their own geometry.'},
                {'name': 'fractured_fiber_fragments',
                 'role': 'Fractured fiber fragments use M/R/Cc intervals [(146, 255), (16, 108), (0, '
                         '114)] in their own geometry.'},
                {'name': 'venting_matrix_pores',
                 'role': 'Venting matrix pores use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'resin_conversion_rims',
                 'role': 'Resin conversion rims use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'polished_grain_tips',
                 'role': 'Polished grain tips use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['compacted_carbon_grains',
                            'fractured_fiber_fragments',
                            'venting_matrix_pores',
                            'resin_conversion_rims',
                            'polished_grain_tips'],
                      'R': ['compacted_carbon_grains',
                            'fractured_fiber_fragments',
                            'venting_matrix_pores',
                            'resin_conversion_rims',
                            'polished_grain_tips'],
                      'Cc': ['compacted_carbon_grains',
                             'fractured_fiber_fragments',
                             'venting_matrix_pores',
                             'resin_conversion_rims',
                             'polished_grain_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Carbon Brake Grain must visibly separate through compacted '
                                      'carbon grains, fractured fiber fragments, venting matrix pores '
                                      'and the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Carbon Brake Grain must visibly separate through compacted '
                                      'carbon grains, fractured fiber fragments, venting matrix pores '
                                      'and the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Compacted grains contain fractured carbon fibers and matrix '
                                     'pores.',
                                     'compacted carbon grains is present in the native named-feature '
                                     'coverage probe.',
                                     'fractured fiber fragments is present in the native named-feature '
                                     'coverage probe.',
                                     'venting matrix pores is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/carbon_brake_grain/independent-feature-carrier',
 'spec_key': 'spec-v2/carbon_brake_grain/named-material-bindings'}

render = build_renderer(carbon_brake_grain, IDENTITY_CONTRACT)

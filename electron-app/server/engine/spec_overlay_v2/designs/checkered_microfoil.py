# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.18; invariant nearest 0.42555 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Checkered Microfoil. Identity declared before rendering/scoring."""
from ..track_designs import checkered_microfoil
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_checkered_microfoil',
 'display_name': 'Checkered Microfoil - spec overlay',
 'promise': 'Checkered Microfoil assembles checker foil squares, creased foil ridges, torn fragment '
            'borders, exposed adhesive tabs and folded checker corners.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Checkered Microfoil assembles checker foil squares, creased foil ridges, torn '
                    'fragment borders, exposed adhesive tabs and folded checker corners. Geometry is '
                    'independently authored in track_designs.py:checkered_microfoil.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to checker foil squares, '
                 'creased foil ridges, torn fragment borders, exposed adhesive tabs, folded checker '
                 'corners.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'checker_foil_squares',
                 'role': 'Checker foil squares use M/R/Cc intervals [(14, 250), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'creased_foil_ridges',
                 'role': 'Creased foil ridges use M/R/Cc intervals [(144, 255), (0, 92), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'torn_fragment_borders',
                 'role': 'Torn fragment borders use M/R/Cc intervals [(0, 100), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'exposed_adhesive_tabs',
                 'role': 'Exposed adhesive tabs use M/R/Cc intervals [(58, 204), (102, 230), (68, 210)] '
                         'in their own geometry.'},
                {'name': 'folded_checker_corners',
                 'role': 'Folded checker corners use M/R/Cc intervals [(96, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['checker_foil_squares',
                            'creased_foil_ridges',
                            'torn_fragment_borders',
                            'exposed_adhesive_tabs',
                            'folded_checker_corners'],
                      'R': ['checker_foil_squares',
                            'creased_foil_ridges',
                            'torn_fragment_borders',
                            'exposed_adhesive_tabs',
                            'folded_checker_corners'],
                      'Cc': ['checker_foil_squares',
                             'creased_foil_ridges',
                             'torn_fragment_borders',
                             'exposed_adhesive_tabs',
                             'folded_checker_corners']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Checkered Microfoil must visibly separate through checker foil '
                                      'squares, creased foil ridges, torn fragment borders and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Checkered Microfoil must visibly separate through checker foil '
                                      'squares, creased foil ridges, torn fragment borders and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Torn checker fragments show individual squares and folded '
                                     'corners.',
                                     'checker foil squares is present in the native named-feature '
                                     'coverage probe.',
                                     'creased foil ridges is present in the native named-feature '
                                     'coverage probe.',
                                     'torn fragment borders is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/checkered_microfoil/independent-feature-carrier',
 'spec_key': 'spec-v2/checkered_microfoil/named-material-bindings'}

render = build_renderer(checkered_microfoil, IDENTITY_CONTRACT)

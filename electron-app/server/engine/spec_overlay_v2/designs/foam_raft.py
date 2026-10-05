# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.64; invariant nearest 0.2789 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Foam Raft. Identity declared before rendering/scoring."""
from ..liquid_designs import foam_raft
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_foam_raft',
 'display_name': 'Foam Raft - spec overlay',
 'promise': 'Foam Raft assembles bubble film faces, plateau borders, thinning film windows, drainage '
            'necks and burst film tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Foam Raft assembles bubble film faces, plateau borders, thinning film windows, '
                    'drainage necks and burst film tabs. Geometry is independently authored in '
                    'liquid_designs.py:foam_raft.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to bubble film faces, plateau '
                 'borders, thinning film windows, drainage necks, burst film tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'bubble_film_faces',
                 'role': 'Bubble film faces use M/R/Cc intervals [(16, 242), (24, 214), (16, 250)] in '
                         'their own geometry.'},
                {'name': 'plateau_borders',
                 'role': 'Plateau borders use M/R/Cc intervals [(148, 255), (16, 112), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'thinning_film_windows',
                 'role': 'Thinning film windows use M/R/Cc intervals [(0, 106), (174, 255), (142, 254)] '
                         'in their own geometry.'},
                {'name': 'drainage_necks',
                 'role': 'Drainage necks use M/R/Cc intervals [(56, 204), (98, 232), (66, 198)] in '
                         'their own geometry.'},
                {'name': 'burst_film_tabs',
                 'role': 'Burst film tabs use M/R/Cc intervals [(94, 228), (52, 180), (166, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['bubble_film_faces',
                            'plateau_borders',
                            'thinning_film_windows',
                            'drainage_necks',
                            'burst_film_tabs'],
                      'R': ['bubble_film_faces',
                            'plateau_borders',
                            'thinning_film_windows',
                            'drainage_necks',
                            'burst_film_tabs'],
                      'Cc': ['bubble_film_faces',
                             'plateau_borders',
                             'thinning_film_windows',
                             'drainage_necks',
                             'burst_film_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Foam Raft must visibly separate through bubble film faces, '
                                      'plateau borders, thinning film windows and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Foam Raft must visibly separate through bubble film faces, '
                                      'plateau borders, thinning film windows and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Merged foam cells form irregular shared walls and junctions.',
                                     'bubble film faces is present in the native named-feature coverage '
                                     'probe.',
                                     'plateau borders is present in the native named-feature coverage '
                                     'probe.',
                                     'thinning film windows is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/foam_raft/independent-feature-carrier',
 'spec_key': 'spec-v2/foam_raft/named-material-bindings'}

render = build_renderer(foam_raft, IDENTITY_CONTRACT)

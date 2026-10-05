# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 94.61; invariant nearest 0.54454 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Rheology Combs. Identity declared before rendering/scoring."""
from ..liquid_designs import rheology_combs
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_rheology_combs',
 'display_name': 'Rheology Combs - spec overlay',
 'promise': 'Rheology Combs assembles viscous fingers, finger tip caps, trailing furrows, side comb '
            'teeth and recoil meniscus loops.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Rheology Combs assembles viscous fingers, finger tip caps, trailing furrows, side '
                    'comb teeth and recoil meniscus loops. Geometry is independently authored in '
                    'liquid_designs.py:rheology_combs.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to viscous fingers, finger tip '
                 'caps, trailing furrows, side comb teeth, recoil meniscus loops.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'viscous_fingers',
                 'role': 'Viscous fingers use M/R/Cc intervals [(18, 246), (24, 214), (22, 248)] in '
                         'their own geometry.'},
                {'name': 'finger_tip_caps',
                 'role': 'Finger tip caps use M/R/Cc intervals [(144, 255), (16, 108), (0, 110)] in '
                         'their own geometry.'},
                {'name': 'trailing_furrows',
                 'role': 'Trailing furrows use M/R/Cc intervals [(0, 98), (178, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'side_comb_teeth',
                 'role': 'Side comb teeth use M/R/Cc intervals [(58, 204), (104, 234), (68, 206)] in '
                         'their own geometry.'},
                {'name': 'recoil_meniscus_loops',
                 'role': 'Recoil meniscus loops use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['viscous_fingers',
                            'finger_tip_caps',
                            'trailing_furrows',
                            'side_comb_teeth',
                            'recoil_meniscus_loops'],
                      'R': ['viscous_fingers',
                            'finger_tip_caps',
                            'trailing_furrows',
                            'side_comb_teeth',
                            'recoil_meniscus_loops'],
                      'Cc': ['viscous_fingers',
                             'finger_tip_caps',
                             'trailing_furrows',
                             'side_comb_teeth',
                             'recoil_meniscus_loops']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Rheology Combs must visibly separate through viscous fingers, '
                                      'finger tip caps, trailing furrows and the remaining named marks, '
                                      'not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Rheology Combs must visibly separate through viscous fingers, '
                                      'finger tip caps, trailing furrows and the remaining named marks, '
                                      'not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Small combed flow tracks end in separate recoil menisci.',
                                     'viscous fingers is present in the native named-feature coverage '
                                     'probe.',
                                     'finger tip caps is present in the native named-feature coverage '
                                     'probe.',
                                     'trailing furrows is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/rheology_combs/independent-feature-carrier',
 'spec_key': 'spec-v2/rheology_combs/named-material-bindings'}

render = build_renderer(rheology_combs, IDENTITY_CONTRACT)

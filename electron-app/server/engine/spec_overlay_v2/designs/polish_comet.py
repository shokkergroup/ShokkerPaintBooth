# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 95.86; invariant nearest 0.27525 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Polish Comet. Identity declared before rendering/scoring."""
from ..machine_designs import polish_comet
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_polish_comet',
 'display_name': 'Polish Comet - spec overlay',
 'promise': 'Polish Comet assembles polish heads, trailing fans, second fan, compound residue and tail '
            'witnesses.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Polish Comet assembles polish heads, trailing fans, second fan, compound residue '
                    'and tail witnesses. Geometry is independently authored in '
                    'machine_designs.py:polish_comet.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to polish heads, trailing fans, '
                 'second fan, compound residue, tail witnesses.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'polish_heads',
                 'role': 'Polish heads use M/R/Cc intervals [(116, 255), (0, 100), (20, 144)] in their '
                         'own geometry.'},
                {'name': 'trailing_fans',
                 'role': 'Trailing fans use M/R/Cc intervals [(24, 246), (0, 246), (104, 252)] in their '
                         'own geometry.'},
                {'name': 'second_fan',
                 'role': 'Second fan use M/R/Cc intervals [(8, 112), (138, 248), (36, 180)] in their '
                         'own geometry.'},
                {'name': 'compound_residue',
                 'role': 'Compound residue use M/R/Cc intervals [(0, 90), (180, 255), (160, 254)] in '
                         'their own geometry.'},
                {'name': 'tail_witnesses',
                 'role': 'Tail witnesses use M/R/Cc intervals [(148, 250), (18, 98), (0, 60)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['polish_heads',
                            'trailing_fans',
                            'second_fan',
                            'compound_residue',
                            'tail_witnesses'],
                      'R': ['polish_heads',
                            'trailing_fans',
                            'second_fan',
                            'compound_residue',
                            'tail_witnesses'],
                      'Cc': ['polish_heads',
                             'trailing_fans',
                             'second_fan',
                             'compound_residue',
                             'tail_witnesses']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Polish Comet must visibly separate through polish heads, '
                                      'trailing fans, second fan and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Polish Comet must visibly separate through polish heads, '
                                      'trailing fans, second fan and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Two intersecting polish passes carry distinct rounded heads and '
                                     'short curved wakes.',
                                     'polish heads is present in the native named-feature coverage '
                                     'probe.',
                                     'trailing fans is present in the native named-feature coverage '
                                     'probe.',
                                     'second fan is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/polish_comet/independent-feature-carrier',
 'spec_key': 'spec-v2/polish_comet/named-material-bindings'}

render = build_renderer(polish_comet, IDENTITY_CONTRACT)

# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.46; invariant nearest 0.48859 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Foil Scarf. Identity declared before rendering/scoring."""
from ..machine_designs import foil_scarf
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_foil_scarf',
 'display_name': 'Foil Scarf - spec overlay',
 'promise': 'Foil Scarf assembles scarfed laps, fold crests, sheared tabs, recessed punches and peel '
            'curls.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Foil Scarf assembles scarfed laps, fold crests, sheared tabs, recessed punches and '
                    'peel curls. Geometry is independently authored in machine_designs.py:foil_scarf.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to scarfed laps, fold crests, '
                 'sheared tabs, recessed punches, peel curls.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'scarfed_laps',
                 'role': 'Scarfed laps use M/R/Cc intervals [(16, 244), (32, 212), (24, 236)] in their '
                         'own geometry.'},
                {'name': 'fold_crests',
                 'role': 'Fold crests use M/R/Cc intervals [(178, 255), (8, 64), (0, 112)] in their own '
                         'geometry.'},
                {'name': 'sheared_tabs',
                 'role': 'Sheared tabs use M/R/Cc intervals [(44, 164), (154, 246), (106, 252)] in '
                         'their own geometry.'},
                {'name': 'recessed_punches',
                 'role': 'Recessed punches use M/R/Cc intervals [(4, 88), (172, 255), (82, 184)] in '
                         'their own geometry.'},
                {'name': 'peel_curls',
                 'role': 'Peel curls use M/R/Cc intervals [(104, 230), (50, 146), (40, 216)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['scarfed_laps',
                            'fold_crests',
                            'sheared_tabs',
                            'recessed_punches',
                            'peel_curls'],
                      'R': ['scarfed_laps',
                            'fold_crests',
                            'sheared_tabs',
                            'recessed_punches',
                            'peel_curls'],
                      'Cc': ['scarfed_laps',
                             'fold_crests',
                             'sheared_tabs',
                             'recessed_punches',
                             'peel_curls']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Foil Scarf must visibly separate through scarfed laps, fold '
                                      'crests, sheared tabs and the remaining named marks, not color or '
                                      'parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Foil Scarf must visibly separate through scarfed laps, fold '
                                      'crests, sheared tabs and the remaining named marks, not color or '
                                      'parameter changes.'}],
 'name_truth': {'visible_evidence': ['Overlapping scarf ledges end in small separated foil fragments.',
                                     'scarfed laps is present in the native named-feature coverage '
                                     'probe.',
                                     'fold crests is present in the native named-feature coverage '
                                     'probe.',
                                     'sheared tabs is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/foil_scarf/independent-feature-carrier',
 'spec_key': 'spec-v2/foil_scarf/named-material-bindings'}

render = build_renderer(foil_scarf, IDENTITY_CONTRACT)

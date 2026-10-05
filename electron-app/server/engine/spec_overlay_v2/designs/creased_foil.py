# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.17; invariant nearest 0.44404 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Creased Foil. Identity declared before rendering/scoring."""
from ..crack_designs import creased_foil
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_creased_foil',
 'display_name': 'Creased Foil - spec overlay',
 'promise': 'Creased Foil assembles crumpled foil facets, fold intersections, fatigue crease splits, '
            'pinched corner tabs and crease scuff lozenges.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Creased Foil assembles crumpled foil facets, fold intersections, fatigue crease '
                    'splits, pinched corner tabs and crease scuff lozenges. Geometry is independently '
                    'authored in crack_designs.py:creased_foil.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to crumpled foil facets, fold '
                 'intersections, fatigue crease splits, pinched corner tabs, crease scuff lozenges.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'crumpled_foil_facets',
                 'role': 'Crumpled foil facets use M/R/Cc intervals [(16, 248), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'fold_intersections',
                 'role': 'Fold intersections use M/R/Cc intervals [(148, 255), (0, 92), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'fatigue_crease_splits',
                 'role': 'Fatigue crease splits use M/R/Cc intervals [(0, 102), (178, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'pinched_corner_tabs',
                 'role': 'Pinched corner tabs use M/R/Cc intervals [(56, 206), (102, 232), (70, 202)] '
                         'in their own geometry.'},
                {'name': 'crease_scuff_lozenges',
                 'role': 'Crease scuff lozenges use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['crumpled_foil_facets',
                            'fold_intersections',
                            'fatigue_crease_splits',
                            'pinched_corner_tabs',
                            'crease_scuff_lozenges'],
                      'R': ['crumpled_foil_facets',
                            'fold_intersections',
                            'fatigue_crease_splits',
                            'pinched_corner_tabs',
                            'crease_scuff_lozenges'],
                      'Cc': ['crumpled_foil_facets',
                             'fold_intersections',
                             'fatigue_crease_splits',
                             'pinched_corner_tabs',
                             'crease_scuff_lozenges']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Creased Foil must visibly separate through crumpled foil facets, '
                                      'fold intersections, fatigue crease splits and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Creased Foil must visibly separate through crumpled foil facets, '
                                      'fold intersections, fatigue crease splits and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Opposed foil tents meet converging crease lines and torn corners.',
                                     'crumpled foil facets is present in the native named-feature '
                                     'coverage probe.',
                                     'fold intersections is present in the native named-feature '
                                     'coverage probe.',
                                     'fatigue crease splits is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/creased_foil/independent-feature-carrier',
 'spec_key': 'spec-v2/creased_foil/named-material-bindings'}

render = build_renderer(creased_foil, IDENTITY_CONTRACT)

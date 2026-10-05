# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.2; invariant nearest 0.38951 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Orange Peel Film. Identity declared before rendering/scoring."""
from ..liquid_designs import orange_peel_film
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_orange_peel_film',
 'display_name': 'Orange Peel Film - spec overlay',
 'promise': 'Orange Peel Film assembles coating hillocks, valley polish arcs, solvent pop pores, flow '
            'leveling saddles and dust nib collars.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Orange Peel Film assembles coating hillocks, valley polish arcs, solvent pop '
                    'pores, flow leveling saddles and dust nib collars. Geometry is independently '
                    'authored in liquid_designs.py:orange_peel_film.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to coating hillocks, valley '
                 'polish arcs, solvent pop pores, flow leveling saddles, dust nib collars.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'coating_hillocks',
                 'role': 'Coating hillocks use M/R/Cc intervals [(16, 240), (26, 218), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'valley_polish_arcs',
                 'role': 'Valley polish arcs use M/R/Cc intervals [(134, 255), (16, 106), (0, 110)] in '
                         'their own geometry.'},
                {'name': 'solvent_pop_pores',
                 'role': 'Solvent pop pores use M/R/Cc intervals [(0, 102), (180, 255), (148, 254)] in '
                         'their own geometry.'},
                {'name': 'flow_leveling_saddles',
                 'role': 'Flow leveling saddles use M/R/Cc intervals [(54, 204), (102, 230), (68, 206)] '
                         'in their own geometry.'},
                {'name': 'dust_nib_collars',
                 'role': 'Dust nib collars use M/R/Cc intervals [(98, 228), (56, 180), (162, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['coating_hillocks',
                            'valley_polish_arcs',
                            'solvent_pop_pores',
                            'flow_leveling_saddles',
                            'dust_nib_collars'],
                      'R': ['coating_hillocks',
                            'valley_polish_arcs',
                            'solvent_pop_pores',
                            'flow_leveling_saddles',
                            'dust_nib_collars'],
                      'Cc': ['coating_hillocks',
                             'valley_polish_arcs',
                             'solvent_pop_pores',
                             'flow_leveling_saddles',
                             'dust_nib_collars']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Orange Peel Film must visibly separate through coating hillocks, '
                                      'valley polish arcs, solvent pop pores and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Orange Peel Film must visibly separate through coating hillocks, '
                                      'valley polish arcs, solvent pop pores and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Dense small coating bowls create orange-peel relief.',
                                     'coating hillocks is present in the native named-feature coverage '
                                     'probe.',
                                     'valley polish arcs is present in the native named-feature '
                                     'coverage probe.',
                                     'solvent pop pores is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/orange_peel_film/independent-feature-carrier',
 'spec_key': 'spec-v2/orange_peel_film/named-material-bindings'}

render = build_renderer(orange_peel_film, IDENTITY_CONTRACT)

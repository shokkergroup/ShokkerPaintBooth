# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.38; invariant nearest 0.26515 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Trabecular Pores. Identity declared before rendering/scoring."""
from ..skin_designs import trabecular_pores
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_trabecular_pores',
 'display_name': 'Trabecular Pores - spec overlay',
 'promise': 'Trabecular Pores assembles porous bone walls, load bearing struts, marrow recesses, pore '
            'neck rims and remodeling pits.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Trabecular Pores assembles porous bone walls, load bearing struts, marrow '
                    'recesses, pore neck rims and remodeling pits. Geometry is independently authored '
                    'in skin_designs.py:trabecular_pores.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to porous bone walls, load '
                 'bearing struts, marrow recesses, pore neck rims, remodeling pits.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'porous_bone_walls',
                 'role': 'Porous bone walls use M/R/Cc intervals [(18, 242), (28, 218), (24, 250)] in '
                         'their own geometry.'},
                {'name': 'load_bearing_struts',
                 'role': 'Load bearing struts use M/R/Cc intervals [(142, 255), (16, 102), (0, 106)] in '
                         'their own geometry.'},
                {'name': 'marrow_recesses',
                 'role': 'Marrow recesses use M/R/Cc intervals [(0, 92), (180, 255), (148, 254)] in '
                         'their own geometry.'},
                {'name': 'pore_neck_rims',
                 'role': 'Pore neck rims use M/R/Cc intervals [(54, 202), (94, 226), (66, 208)] in '
                         'their own geometry.'},
                {'name': 'remodeling_pits',
                 'role': 'Remodeling pits use M/R/Cc intervals [(92, 226), (60, 178), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['porous_bone_walls',
                            'load_bearing_struts',
                            'marrow_recesses',
                            'pore_neck_rims',
                            'remodeling_pits'],
                      'R': ['porous_bone_walls',
                            'load_bearing_struts',
                            'marrow_recesses',
                            'pore_neck_rims',
                            'remodeling_pits'],
                      'Cc': ['porous_bone_walls',
                             'load_bearing_struts',
                             'marrow_recesses',
                             'pore_neck_rims',
                             'remodeling_pits']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Trabecular Pores must visibly separate through porous bone '
                                      'walls, load bearing struts, marrow recesses and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Trabecular Pores must visibly separate through porous bone '
                                      'walls, load bearing struts, marrow recesses and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Closely packed cavities leave a trabecular network between the '
                                     'holes.',
                                     'porous bone walls is present in the native named-feature coverage '
                                     'probe.',
                                     'load bearing struts is present in the native named-feature '
                                     'coverage probe.',
                                     'marrow recesses is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/trabecular_pores/independent-feature-carrier',
 'spec_key': 'spec-v2/trabecular_pores/named-material-bindings'}

render = build_renderer(trabecular_pores, IDENTITY_CONTRACT)

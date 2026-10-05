# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.22; invariant nearest 0.46823 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Freeze Thaw. Identity declared before rendering/scoring."""
from ..crack_designs import freeze_thaw
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_freeze_thaw',
 'display_name': 'Freeze Thaw - spec overlay',
 'promise': 'Freeze Thaw assembles frost lifted wedges, ice jacking splits, fresh fracture faces, '
            'stepped frost lenses and friable grain clusters.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Freeze Thaw assembles frost lifted wedges, ice jacking splits, fresh fracture '
                    'faces, stepped frost lenses and friable grain clusters. Geometry is independently '
                    'authored in crack_designs.py:freeze_thaw.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to frost lifted wedges, ice '
                 'jacking splits, fresh fracture faces, stepped frost lenses, friable grain clusters.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'frost_lifted_wedges',
                 'role': 'Frost lifted wedges use M/R/Cc intervals [(18, 242), (26, 216), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'ice_jacking_splits',
                 'role': 'Ice jacking splits use M/R/Cc intervals [(0, 102), (176, 255), (142, 254)] in '
                         'their own geometry.'},
                {'name': 'fresh_fracture_faces',
                 'role': 'Fresh fracture faces use M/R/Cc intervals [(148, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'stepped_frost_lenses',
                 'role': 'Stepped frost lenses use M/R/Cc intervals [(56, 204), (102, 230), (70, 204)] '
                         'in their own geometry.'},
                {'name': 'friable_grain_clusters',
                 'role': 'Friable grain clusters use M/R/Cc intervals [(96, 228), (54, 182), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['frost_lifted_wedges',
                            'ice_jacking_splits',
                            'fresh_fracture_faces',
                            'stepped_frost_lenses',
                            'friable_grain_clusters'],
                      'R': ['frost_lifted_wedges',
                            'ice_jacking_splits',
                            'fresh_fracture_faces',
                            'stepped_frost_lenses',
                            'friable_grain_clusters'],
                      'Cc': ['frost_lifted_wedges',
                             'ice_jacking_splits',
                             'fresh_fracture_faces',
                             'stepped_frost_lenses',
                             'friable_grain_clusters']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Freeze Thaw must visibly separate through frost lifted wedges, '
                                      'ice jacking splits, fresh fracture faces and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Freeze Thaw must visibly separate through frost lifted wedges, '
                                      'ice jacking splits, fresh fracture faces and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Frost-lifted wedges are split by short irregular jacking cracks.',
                                     'frost lifted wedges is present in the native named-feature '
                                     'coverage probe.',
                                     'ice jacking splits is present in the native named-feature '
                                     'coverage probe.',
                                     'fresh fracture faces is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/freeze_thaw/independent-feature-carrier',
 'spec_key': 'spec-v2/freeze_thaw/named-material-bindings'}

render = build_renderer(freeze_thaw, IDENTITY_CONTRACT)

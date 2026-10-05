# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.52; invariant nearest 0.51809 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Drying Fronts. Identity declared before rendering/scoring."""
from ..liquid_designs import drying_fronts
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_drying_fronts',
 'display_name': 'Drying Fronts - spec overlay',
 'promise': 'Drying Fronts assembles wet remnant bands, receding front lips, dried residue islands, '
            'arrested drop tails and contact line beads.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Drying Fronts assembles wet remnant bands, receding front lips, dried residue '
                    'islands, arrested drop tails and contact line beads. Geometry is independently '
                    'authored in liquid_designs.py:drying_fronts.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to wet remnant bands, receding '
                 'front lips, dried residue islands, arrested drop tails, contact line beads.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'wet_remnant_bands',
                 'role': 'Wet remnant bands use M/R/Cc intervals [(14, 236), (20, 198), (20, 244)] in '
                         'their own geometry.'},
                {'name': 'receding_front_lips',
                 'role': 'Receding front lips use M/R/Cc intervals [(142, 255), (16, 114), (0, 108)] in '
                         'their own geometry.'},
                {'name': 'dried_residue_islands',
                 'role': 'Dried residue islands use M/R/Cc intervals [(0, 102), (180, 255), (156, 254)] '
                         'in their own geometry.'},
                {'name': 'arrested_drop_tails',
                 'role': 'Arrested drop tails use M/R/Cc intervals [(54, 208), (96, 230), (76, 212)] in '
                         'their own geometry.'},
                {'name': 'contact_line_beads',
                 'role': 'Contact line beads use M/R/Cc intervals [(98, 226), (36, 154), (152, 252)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['wet_remnant_bands',
                            'receding_front_lips',
                            'dried_residue_islands',
                            'arrested_drop_tails',
                            'contact_line_beads'],
                      'R': ['wet_remnant_bands',
                            'receding_front_lips',
                            'dried_residue_islands',
                            'arrested_drop_tails',
                            'contact_line_beads'],
                      'Cc': ['wet_remnant_bands',
                             'receding_front_lips',
                             'dried_residue_islands',
                             'arrested_drop_tails',
                             'contact_line_beads']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Drying Fronts must visibly separate through wet remnant bands, '
                                      'receding front lips, dried residue islands and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Drying Fronts must visibly separate through wet remnant bands, '
                                      'receding front lips, dried residue islands and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Stepped receding fronts leave separate scalloped residue lines.',
                                     'wet remnant bands is present in the native named-feature coverage '
                                     'probe.',
                                     'receding front lips is present in the native named-feature '
                                     'coverage probe.',
                                     'dried residue islands is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/drying_fronts/independent-feature-carrier',
 'spec_key': 'spec-v2/drying_fronts/named-material-bindings'}

render = build_renderer(drying_fronts, IDENTITY_CONTRACT)

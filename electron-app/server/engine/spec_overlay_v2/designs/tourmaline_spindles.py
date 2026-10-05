# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.74; invariant nearest 0.47612 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Tourmaline Spindles. Identity declared before rendering/scoring."""
from ..crystal_designs import tourmaline_spindles
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_tourmaline_spindles',
 'display_name': 'Tourmaline Spindles - spec overlay',
 'promise': 'Tourmaline Spindles assembles elongate prism faces, longitudinal flutes, termination '
            'facets, broken roots and crosswise inclusions.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Tourmaline Spindles assembles elongate prism faces, longitudinal flutes, '
                    'termination facets, broken roots and crosswise inclusions. Geometry is '
                    'independently authored in crystal_designs.py:tourmaline_spindles.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to elongate prism faces, '
                 'longitudinal flutes, termination facets, broken roots, crosswise inclusions.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'elongate_prism_faces',
                 'role': 'Elongate prism faces use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'longitudinal_flutes',
                 'role': 'Longitudinal flutes use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'termination_facets',
                 'role': 'Termination facets use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'broken_roots',
                 'role': 'Broken roots use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in their '
                         'own geometry.'},
                {'name': 'crosswise_inclusions',
                 'role': 'Crosswise inclusions use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['elongate_prism_faces',
                            'longitudinal_flutes',
                            'termination_facets',
                            'broken_roots',
                            'crosswise_inclusions'],
                      'R': ['elongate_prism_faces',
                            'longitudinal_flutes',
                            'termination_facets',
                            'broken_roots',
                            'crosswise_inclusions'],
                      'Cc': ['elongate_prism_faces',
                             'longitudinal_flutes',
                             'termination_facets',
                             'broken_roots',
                             'crosswise_inclusions']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Tourmaline Spindles must visibly separate through elongate prism '
                                      'faces, longitudinal flutes, termination facets and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Tourmaline Spindles must visibly separate through elongate prism '
                                      'faces, longitudinal flutes, termination facets and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Two crossing populations of double-ended needles show '
                                     'longitudinal flutes and compact prism terminations.',
                                     'elongate prism faces is present in the native named-feature '
                                     'coverage probe.',
                                     'longitudinal flutes is present in the native named-feature '
                                     'coverage probe.',
                                     'termination facets is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/tourmaline_spindles/independent-feature-carrier',
 'spec_key': 'spec-v2/tourmaline_spindles/named-material-bindings'}

render = build_renderer(tourmaline_spindles, IDENTITY_CONTRACT)

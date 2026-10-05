# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.66; invariant nearest 0.25951 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Coded Apertures. Identity declared before rendering/scoring."""
from ..optical_designs import coded_apertures
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_coded_apertures',
 'display_name': 'Coded Apertures - spec overlay',
 'promise': 'Coded Apertures assembles coded opaque platelets, milled aperture windows, polished window '
            'chamfers, registration diamonds and interrupted support tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Coded Apertures assembles coded opaque platelets, milled aperture windows, '
                    'polished window chamfers, registration diamonds and interrupted support tabs. '
                    'Geometry is independently authored in optical_designs.py:coded_apertures.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to coded opaque platelets, '
                 'milled aperture windows, polished window chamfers, registration diamonds, interrupted '
                 'support tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'coded_opaque_platelets',
                 'role': 'Coded opaque platelets use M/R/Cc intervals [(18, 244), (28, 224), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'milled_aperture_windows',
                 'role': 'Milled aperture windows use M/R/Cc intervals [(0, 102), (176, 255), (140, '
                         '254)] in their own geometry.'},
                {'name': 'polished_window_chamfers',
                 'role': 'Polished window chamfers use M/R/Cc intervals [(150, 255), (16, 100), (0, '
                         '112)] in their own geometry.'},
                {'name': 'registration_diamonds',
                 'role': 'Registration diamonds use M/R/Cc intervals [(56, 206), (102, 232), (68, 212)] '
                         'in their own geometry.'},
                {'name': 'interrupted_support_tabs',
                 'role': 'Interrupted support tabs use M/R/Cc intervals [(98, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['coded_opaque_platelets',
                            'milled_aperture_windows',
                            'polished_window_chamfers',
                            'registration_diamonds',
                            'interrupted_support_tabs'],
                      'R': ['coded_opaque_platelets',
                            'milled_aperture_windows',
                            'polished_window_chamfers',
                            'registration_diamonds',
                            'interrupted_support_tabs'],
                      'Cc': ['coded_opaque_platelets',
                             'milled_aperture_windows',
                             'polished_window_chamfers',
                             'registration_diamonds',
                             'interrupted_support_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Coded Apertures must visibly separate through coded opaque '
                                      'platelets, milled aperture windows, polished window chamfers and '
                                      'the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Coded Apertures must visibly separate through coded opaque '
                                      'platelets, milled aperture windows, polished window chamfers and '
                                      'the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['A coded matrix of individual square apertures contains '
                                     'registration details.',
                                     'coded opaque platelets is present in the native named-feature '
                                     'coverage probe.',
                                     'milled aperture windows is present in the native named-feature '
                                     'coverage probe.',
                                     'polished window chamfers is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/coded_apertures/independent-feature-carrier',
 'spec_key': 'spec-v2/coded_apertures/named-material-bindings'}

render = build_renderer(coded_apertures, IDENTITY_CONTRACT)

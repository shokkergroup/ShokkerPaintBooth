# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.4; invariant nearest 0.49102 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Diffractive Hatch. Identity declared before rendering/scoring."""
from ..optical_designs import diffractive_hatch
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_diffractive_hatch',
 'display_name': 'Diffractive Hatch - spec overlay',
 'promise': 'Diffractive Hatch assembles segmented grating lands, hatch crosscuts, polished grating '
            'crests, missing grating teeth and termination fan tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Diffractive Hatch assembles segmented grating lands, hatch crosscuts, polished '
                    'grating crests, missing grating teeth and termination fan tabs. Geometry is '
                    'independently authored in optical_designs.py:diffractive_hatch.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to segmented grating lands, '
                 'hatch crosscuts, polished grating crests, missing grating teeth, termination fan '
                 'tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'segmented_grating_lands',
                 'role': 'Segmented grating lands use M/R/Cc intervals [(18, 246), (24, 214), (24, '
                         '248)] in their own geometry.'},
                {'name': 'hatch_crosscuts',
                 'role': 'Hatch crosscuts use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'polished_grating_crests',
                 'role': 'Polished grating crests use M/R/Cc intervals [(144, 255), (16, 108), (0, '
                         '112)] in their own geometry.'},
                {'name': 'missing_grating_teeth',
                 'role': 'Missing grating teeth use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'termination_fan_tabs',
                 'role': 'Termination fan tabs use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['segmented_grating_lands',
                            'hatch_crosscuts',
                            'polished_grating_crests',
                            'missing_grating_teeth',
                            'termination_fan_tabs'],
                      'R': ['segmented_grating_lands',
                            'hatch_crosscuts',
                            'polished_grating_crests',
                            'missing_grating_teeth',
                            'termination_fan_tabs'],
                      'Cc': ['segmented_grating_lands',
                             'hatch_crosscuts',
                             'polished_grating_crests',
                             'missing_grating_teeth',
                             'termination_fan_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Diffractive Hatch must visibly separate through segmented '
                                      'grating lands, hatch crosscuts, polished grating crests and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Diffractive Hatch must visibly separate through segmented '
                                      'grating lands, hatch crosscuts, polished grating crests and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Crossing hatch lines interrupt fine etched aperture rows.',
                                     'segmented grating lands is present in the native named-feature '
                                     'coverage probe.',
                                     'hatch crosscuts is present in the native named-feature coverage '
                                     'probe.',
                                     'polished grating crests is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/diffractive_hatch/independent-feature-carrier',
 'spec_key': 'spec-v2/diffractive_hatch/named-material-bindings'}

render = build_renderer(diffractive_hatch, IDENTITY_CONTRACT)

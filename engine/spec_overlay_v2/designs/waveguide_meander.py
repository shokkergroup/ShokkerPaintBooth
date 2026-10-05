# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.33; invariant nearest 0.44387 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Waveguide Meander. Identity declared before rendering/scoring."""
from ..optical_designs import waveguide_meander
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_waveguide_meander',
 'display_name': 'Waveguide Meander - spec overlay',
 'promise': 'Waveguide Meander assembles meandering guide ribbons, guide turn crowns, absorbing '
            'terminations, coupling bridge ports and etched locator dots.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Waveguide Meander assembles meandering guide ribbons, guide turn crowns, absorbing '
                    'terminations, coupling bridge ports and etched locator dots. Geometry is '
                    'independently authored in optical_designs.py:waveguide_meander.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to meandering guide ribbons, '
                 'guide turn crowns, absorbing terminations, coupling bridge ports, etched locator '
                 'dots.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'meandering_guide_ribbons',
                 'role': 'Meandering guide ribbons use M/R/Cc intervals [(18, 246), (0, 246), (24, '
                         '248)] in their own geometry.'},
                {'name': 'guide_turn_crowns',
                 'role': 'Guide turn crowns use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'absorbing_terminations',
                 'role': 'Absorbing terminations use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'coupling_bridge_ports',
                 'role': 'Coupling bridge ports use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'etched_locator_dots',
                 'role': 'Etched locator dots use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['meandering_guide_ribbons',
                            'guide_turn_crowns',
                            'absorbing_terminations',
                            'coupling_bridge_ports',
                            'etched_locator_dots'],
                      'R': ['meandering_guide_ribbons',
                            'guide_turn_crowns',
                            'absorbing_terminations',
                            'coupling_bridge_ports',
                            'etched_locator_dots'],
                      'Cc': ['meandering_guide_ribbons',
                             'guide_turn_crowns',
                             'absorbing_terminations',
                             'coupling_bridge_ports',
                             'etched_locator_dots']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Waveguide Meander must visibly separate through meandering guide '
                                      'ribbons, guide turn crowns, absorbing terminations and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Waveguide Meander must visibly separate through meandering guide '
                                      'ribbons, guide turn crowns, absorbing terminations and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Interdigitated hairpin guides contain return bends and coupling '
                                     'ports.',
                                     'meandering guide ribbons is present in the native named-feature '
                                     'coverage probe.',
                                     'guide turn crowns is present in the native named-feature coverage '
                                     'probe.',
                                     'absorbing terminations is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/waveguide_meander/independent-feature-carrier',
 'spec_key': 'spec-v2/waveguide_meander/named-material-bindings'}

render = build_renderer(waveguide_meander, IDENTITY_CONTRACT)

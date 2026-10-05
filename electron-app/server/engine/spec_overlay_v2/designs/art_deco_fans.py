# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.93; invariant nearest 0.54454 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Art Deco Fans. Identity declared before rendering/scoring."""
from ..engraved_designs import art_deco_fans
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_art_deco_fans',
 'display_name': 'Art Deco Fans - spec overlay',
 'promise': 'Art Deco Fans assembles sunburst fan facets, radiating fan inlays, recessed fan bases, '
            'stepped fan borders and deco corner gems.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Art Deco Fans assembles sunburst fan facets, radiating fan inlays, recessed fan '
                    'bases, stepped fan borders and deco corner gems. Geometry is independently '
                    'authored in engraved_designs.py:art_deco_fans.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to sunburst fan facets, '
                 'radiating fan inlays, recessed fan bases, stepped fan borders, deco corner gems.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'sunburst_fan_facets',
                 'role': 'Sunburst fan facets use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'radiating_fan_inlays',
                 'role': 'Radiating fan inlays use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'recessed_fan_bases',
                 'role': 'Recessed fan bases use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'stepped_fan_borders',
                 'role': 'Stepped fan borders use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'deco_corner_gems',
                 'role': 'Deco corner gems use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['sunburst_fan_facets',
                            'radiating_fan_inlays',
                            'recessed_fan_bases',
                            'stepped_fan_borders',
                            'deco_corner_gems'],
                      'R': ['sunburst_fan_facets',
                            'radiating_fan_inlays',
                            'recessed_fan_bases',
                            'stepped_fan_borders',
                            'deco_corner_gems'],
                      'Cc': ['sunburst_fan_facets',
                             'radiating_fan_inlays',
                             'recessed_fan_bases',
                             'stepped_fan_borders',
                             'deco_corner_gems']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Art Deco Fans must visibly separate through sunburst fan facets, '
                                      'radiating fan inlays, recessed fan bases and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Art Deco Fans must visibly separate through sunburst fan facets, '
                                      'radiating fan inlays, recessed fan bases and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Radial stepped fan faces sit on small decorative bases.',
                                     'sunburst fan facets is present in the native named-feature '
                                     'coverage probe.',
                                     'radiating fan inlays is present in the native named-feature '
                                     'coverage probe.',
                                     'recessed fan bases is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/art_deco_fans/independent-feature-carrier',
 'spec_key': 'spec-v2/art_deco_fans/named-material-bindings'}

render = build_renderer(art_deco_fans, IDENTITY_CONTRACT)

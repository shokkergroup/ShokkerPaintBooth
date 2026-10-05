# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.95; invariant nearest 0.42149 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Barleycorn Cuts. Identity declared before rendering/scoring."""
from ..engraved_designs import barleycorn_cuts
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_barleycorn_cuts',
 'display_name': 'Barleycorn Cuts - spec overlay',
 'promise': 'Barleycorn Cuts assembles barley grain facets, central grain keels, separating burin '
            'hollows, cross grain veins and terminal stipple beads.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Barleycorn Cuts assembles barley grain facets, central grain keels, separating '
                    'burin hollows, cross grain veins and terminal stipple beads. Geometry is '
                    'independently authored in engraved_designs.py:barleycorn_cuts.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to barley grain facets, central '
                 'grain keels, separating burin hollows, cross grain veins, terminal stipple beads.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'barley_grain_facets',
                 'role': 'Barley grain facets use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'central_grain_keels',
                 'role': 'Central grain keels use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'separating_burin_hollows',
                 'role': 'Separating burin hollows use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'cross_grain_veins',
                 'role': 'Cross grain veins use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'terminal_stipple_beads',
                 'role': 'Terminal stipple beads use M/R/Cc intervals [(96, 228), (54, 180), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['barley_grain_facets',
                            'central_grain_keels',
                            'separating_burin_hollows',
                            'cross_grain_veins',
                            'terminal_stipple_beads'],
                      'R': ['barley_grain_facets',
                            'central_grain_keels',
                            'separating_burin_hollows',
                            'cross_grain_veins',
                            'terminal_stipple_beads'],
                      'Cc': ['barley_grain_facets',
                             'central_grain_keels',
                             'separating_burin_hollows',
                             'cross_grain_veins',
                             'terminal_stipple_beads']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Barleycorn Cuts must visibly separate through barley grain '
                                      'facets, central grain keels, separating burin hollows and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Barleycorn Cuts must visibly separate through barley grain '
                                      'facets, central grain keels, separating burin hollows and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Fine repeated barleycorn cuts contain split shoulders and tails.',
                                     'barley grain facets is present in the native named-feature '
                                     'coverage probe.',
                                     'central grain keels is present in the native named-feature '
                                     'coverage probe.',
                                     'separating burin hollows is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/barleycorn_cuts/independent-feature-carrier',
 'spec_key': 'spec-v2/barleycorn_cuts/named-material-bindings'}

render = build_renderer(barleycorn_cuts, IDENTITY_CONTRACT)

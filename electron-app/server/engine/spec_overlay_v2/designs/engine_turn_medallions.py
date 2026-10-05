# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.09; invariant nearest 0.54044 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Engine Turn Medallions. Identity declared before rendering/scoring."""
from ..engraved_designs import engine_turn_medallions
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_engine_turn_medallions',
 'display_name': 'Engine Turn Medallions - spec overlay',
 'promise': 'Engine Turn Medallions assembles eccentric turning faces, nested burin arclets, medallion '
            'separation cuts, turning spindle pits and burnished border tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Engine Turn Medallions assembles eccentric turning faces, nested burin arclets, '
                    'medallion separation cuts, turning spindle pits and burnished border tabs. '
                    'Geometry is independently authored in engraved_designs.py:engine_turn_medallions.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to eccentric turning faces, '
                 'nested burin arclets, medallion separation cuts, turning spindle pits, burnished '
                 'border tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'eccentric_turning_faces',
                 'role': 'Eccentric turning faces use M/R/Cc intervals [(18, 246), (24, 214), (24, '
                         '248)] in their own geometry.'},
                {'name': 'nested_burin_arclets',
                 'role': 'Nested burin arclets use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'medallion_separation_cuts',
                 'role': 'Medallion separation cuts use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'turning_spindle_pits',
                 'role': 'Turning spindle pits use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'burnished_border_tabs',
                 'role': 'Burnished border tabs use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['eccentric_turning_faces',
                            'nested_burin_arclets',
                            'medallion_separation_cuts',
                            'turning_spindle_pits',
                            'burnished_border_tabs'],
                      'R': ['eccentric_turning_faces',
                            'nested_burin_arclets',
                            'medallion_separation_cuts',
                            'turning_spindle_pits',
                            'burnished_border_tabs'],
                      'Cc': ['eccentric_turning_faces',
                             'nested_burin_arclets',
                             'medallion_separation_cuts',
                             'turning_spindle_pits',
                             'burnished_border_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Engine Turn Medallions must visibly separate through eccentric '
                                      'turning faces, nested burin arclets, medallion separation cuts '
                                      'and the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Engine Turn Medallions must visibly separate through eccentric '
                                      'turning faces, nested burin arclets, medallion separation cuts '
                                      'and the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Nested eccentric turning arcs surround small spindle pits.',
                                     'eccentric turning faces is present in the native named-feature '
                                     'coverage probe.',
                                     'nested burin arclets is present in the native named-feature '
                                     'coverage probe.',
                                     'medallion separation cuts is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/engine_turn_medallions/independent-feature-carrier',
 'spec_key': 'spec-v2/engine_turn_medallions/named-material-bindings'}

render = build_renderer(engine_turn_medallions, IDENTITY_CONTRACT)

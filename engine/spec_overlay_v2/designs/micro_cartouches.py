# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.56; invariant nearest 0.53664 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Micro Cartouches. Identity declared before rendering/scoring."""
from ..engraved_designs import micro_cartouches
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_micro_cartouches',
 'display_name': 'Micro Cartouches - spec overlay',
 'promise': 'Micro Cartouches assembles engraved cartouche frames, inner burnished shields, recessed '
            'scroll tabs, central engraver flourishes and border witness beads.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Micro Cartouches assembles engraved cartouche frames, inner burnished shields, '
                    'recessed scroll tabs, central engraver flourishes and border witness beads. '
                    'Geometry is independently authored in engraved_designs.py:micro_cartouches.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to engraved cartouche frames, '
                 'inner burnished shields, recessed scroll tabs, central engraver flourishes, border '
                 'witness beads.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'engraved_cartouche_frames',
                 'role': 'Engraved cartouche frames use M/R/Cc intervals [(18, 246), (24, 214), (24, '
                         '248)] in their own geometry.'},
                {'name': 'inner_burnished_shields',
                 'role': 'Inner burnished shields use M/R/Cc intervals [(146, 255), (16, 108), (0, '
                         '114)] in their own geometry.'},
                {'name': 'recessed_scroll_tabs',
                 'role': 'Recessed scroll tabs use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'central_engraver_flourishes',
                 'role': 'Central engraver flourishes use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'border_witness_beads',
                 'role': 'Border witness beads use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['engraved_cartouche_frames',
                            'inner_burnished_shields',
                            'recessed_scroll_tabs',
                            'central_engraver_flourishes',
                            'border_witness_beads'],
                      'R': ['engraved_cartouche_frames',
                            'inner_burnished_shields',
                            'recessed_scroll_tabs',
                            'central_engraver_flourishes',
                            'border_witness_beads'],
                      'Cc': ['engraved_cartouche_frames',
                             'inner_burnished_shields',
                             'recessed_scroll_tabs',
                             'central_engraver_flourishes',
                             'border_witness_beads']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Micro Cartouches must visibly separate through engraved '
                                      'cartouche frames, inner burnished shields, recessed scroll tabs '
                                      'and the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Micro Cartouches must visibly separate through engraved '
                                      'cartouche frames, inner burnished shields, recessed scroll tabs '
                                      'and the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Oval cartouche frames contain interior engraved strokes.',
                                     'engraved cartouche frames is present in the native named-feature '
                                     'coverage probe.',
                                     'inner burnished shields is present in the native named-feature '
                                     'coverage probe.',
                                     'recessed scroll tabs is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/micro_cartouches/independent-feature-carrier',
 'spec_key': 'spec-v2/micro_cartouches/named-material-bindings'}

render = build_renderer(micro_cartouches, IDENTITY_CONTRACT)

# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 95.25; invariant nearest 0.42271 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Rope Filigree. Identity declared before rendering/scoring."""
from ..engraved_designs import rope_filigree
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_rope_filigree',
 'display_name': 'Rope Filigree - spec overlay',
 'promise': 'Rope Filigree assembles twisted rope rings, rope crossing splices, filigree center '
            'openings, soldered link tabs and terminal wire curls.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Rope Filigree assembles twisted rope rings, rope crossing splices, filigree center '
                    'openings, soldered link tabs and terminal wire curls. Geometry is independently '
                    'authored in engraved_designs.py:rope_filigree.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to twisted rope rings, rope '
                 'crossing splices, filigree center openings, soldered link tabs, terminal wire curls.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'twisted_rope_rings',
                 'role': 'Twisted rope rings use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'rope_crossing_splices',
                 'role': 'Rope crossing splices use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'filigree_center_openings',
                 'role': 'Filigree center openings use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'soldered_link_tabs',
                 'role': 'Soldered link tabs use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'terminal_wire_curls',
                 'role': 'Terminal wire curls use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['twisted_rope_rings',
                            'rope_crossing_splices',
                            'filigree_center_openings',
                            'soldered_link_tabs',
                            'terminal_wire_curls'],
                      'R': ['twisted_rope_rings',
                            'rope_crossing_splices',
                            'filigree_center_openings',
                            'soldered_link_tabs',
                            'terminal_wire_curls'],
                      'Cc': ['twisted_rope_rings',
                             'rope_crossing_splices',
                             'filigree_center_openings',
                             'soldered_link_tabs',
                             'terminal_wire_curls']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Rope Filigree must visibly separate through twisted rope rings, '
                                      'rope crossing splices, filigree center openings and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Rope Filigree must visibly separate through twisted rope rings, '
                                      'rope crossing splices, filigree center openings and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Continuous twisted cable paths cross at soldered ornamental '
                                     'joints.',
                                     'twisted rope rings is present in the native named-feature '
                                     'coverage probe.',
                                     'rope crossing splices is present in the native named-feature '
                                     'coverage probe.',
                                     'filigree center openings is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/rope_filigree/independent-feature-carrier',
 'spec_key': 'spec-v2/rope_filigree/named-material-bindings'}

render = build_renderer(rope_filigree, IDENTITY_CONTRACT)

# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 99.17; invariant nearest 0.54313 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Seigaiha Etching. Identity declared before rendering/scoring."""
from ..engraved_designs import seigaiha_etching
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_seigaiha_etching',
 'display_name': 'Seigaiha Etching - spec overlay',
 'promise': 'Seigaiha Etching assembles nested wave arches, wave crest burin lines, engraved tide '
            'gutters, wave foot knots and crest stippling pairs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Seigaiha Etching assembles nested wave arches, wave crest burin lines, engraved '
                    'tide gutters, wave foot knots and crest stippling pairs. Geometry is independently '
                    'authored in engraved_designs.py:seigaiha_etching.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to nested wave arches, wave '
                 'crest burin lines, engraved tide gutters, wave foot knots, crest stippling pairs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'nested_wave_arches',
                 'role': 'Nested wave arches use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'wave_crest_burin_lines',
                 'role': 'Wave crest burin lines use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'engraved_tide_gutters',
                 'role': 'Engraved tide gutters use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'wave_foot_knots',
                 'role': 'Wave foot knots use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'crest_stippling_pairs',
                 'role': 'Crest stippling pairs use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['nested_wave_arches',
                            'wave_crest_burin_lines',
                            'engraved_tide_gutters',
                            'wave_foot_knots',
                            'crest_stippling_pairs'],
                      'R': ['nested_wave_arches',
                            'wave_crest_burin_lines',
                            'engraved_tide_gutters',
                            'wave_foot_knots',
                            'crest_stippling_pairs'],
                      'Cc': ['nested_wave_arches',
                             'wave_crest_burin_lines',
                             'engraved_tide_gutters',
                             'wave_foot_knots',
                             'crest_stippling_pairs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Seigaiha Etching must visibly separate through nested wave '
                                      'arches, wave crest burin lines, engraved tide gutters and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Seigaiha Etching must visibly separate through nested wave '
                                      'arches, wave crest burin lines, engraved tide gutters and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Nested wave arches contain separate crest cuts and foot knots.',
                                     'nested wave arches is present in the native named-feature '
                                     'coverage probe.',
                                     'wave crest burin lines is present in the native named-feature '
                                     'coverage probe.',
                                     'engraved tide gutters is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/seigaiha_etching/independent-feature-carrier',
 'spec_key': 'spec-v2/seigaiha_etching/named-material-bindings'}

render = build_renderer(seigaiha_etching, IDENTITY_CONTRACT)

# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.35; invariant nearest 0.23843 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Voronoi Kites. Identity declared before rendering/scoring."""
from ..experimental_designs import voronoi_kites
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_voronoi_kites',
 'display_name': 'Voronoi Kites - spec overlay',
 'promise': 'Voronoi Kites assembles asymmetric kite faces, kite diagonal spines, interkite recesses, '
            'offset kite hinges and beveled tail chips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Voronoi Kites assembles asymmetric kite faces, kite diagonal spines, interkite '
                    'recesses, offset kite hinges and beveled tail chips. Geometry is independently '
                    'authored in experimental_designs.py:voronoi_kites.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to asymmetric kite faces, kite '
                 'diagonal spines, interkite recesses, offset kite hinges, beveled tail chips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'asymmetric_kite_faces',
                 'role': 'Asymmetric kite faces use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'kite_diagonal_spines',
                 'role': 'Kite diagonal spines use M/R/Cc intervals [(146, 255), (0, 88), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'interkite_recesses',
                 'role': 'Interkite recesses use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'offset_kite_hinges',
                 'role': 'Offset kite hinges use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'beveled_tail_chips',
                 'role': 'Beveled tail chips use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['asymmetric_kite_faces',
                            'kite_diagonal_spines',
                            'interkite_recesses',
                            'offset_kite_hinges',
                            'beveled_tail_chips'],
                      'R': ['asymmetric_kite_faces',
                            'kite_diagonal_spines',
                            'interkite_recesses',
                            'offset_kite_hinges',
                            'beveled_tail_chips'],
                      'Cc': ['asymmetric_kite_faces',
                             'kite_diagonal_spines',
                             'interkite_recesses',
                             'offset_kite_hinges',
                             'beveled_tail_chips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Voronoi Kites must visibly separate through asymmetric kite '
                                      'faces, kite diagonal spines, interkite recesses and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Voronoi Kites must visibly separate through asymmetric kite '
                                      'faces, kite diagonal spines, interkite recesses and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Asymmetric dual-site kite faces meet recessed edges and short '
                                     'hinges.',
                                     'asymmetric kite faces is present in the native named-feature '
                                     'coverage probe.',
                                     'kite diagonal spines is present in the native named-feature '
                                     'coverage probe.',
                                     'interkite recesses is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/voronoi_kites/independent-feature-carrier',
 'spec_key': 'spec-v2/voronoi_kites/named-material-bindings'}

render = build_renderer(voronoi_kites, IDENTITY_CONTRACT)

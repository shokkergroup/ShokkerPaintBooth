# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.13; invariant nearest 0.54881 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Mica Books. Identity declared before rendering/scoring."""
from ..crystal_designs import mica_books
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_mica_books',
 'display_name': 'Mica Books - spec overlay',
 'promise': 'Mica Books assembles cleavage leaves, book edges, lifted leaf corners, dark interleaf '
            'pockets and fracture pinholes.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Mica Books assembles cleavage leaves, book edges, lifted leaf corners, dark '
                    'interleaf pockets and fracture pinholes. Geometry is independently authored in '
                    'crystal_designs.py:mica_books.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to cleavage leaves, book edges, '
                 'lifted leaf corners, dark interleaf pockets, fracture pinholes.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'cleavage_leaves',
                 'role': 'Cleavage leaves use M/R/Cc intervals [(18, 248), (0, 246), (16, 250)] in '
                         'their own geometry.'},
                {'name': 'book_edges',
                 'role': 'Book edges use M/R/Cc intervals [(160, 255), (0, 90), (0, 108)] in their own '
                         'geometry.'},
                {'name': 'lifted_leaf_corners',
                 'role': 'Lifted leaf corners use M/R/Cc intervals [(62, 212), (86, 220), (126, 250)] '
                         'in their own geometry.'},
                {'name': 'dark_interleaf_pockets',
                 'role': 'Dark interleaf pockets use M/R/Cc intervals [(0, 100), (162, 255), (160, '
                         '255)] in their own geometry.'},
                {'name': 'fracture_pinholes',
                 'role': 'Fracture pinholes use M/R/Cc intervals [(12, 152), (132, 240), (56, 184)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['cleavage_leaves',
                            'book_edges',
                            'lifted_leaf_corners',
                            'dark_interleaf_pockets',
                            'fracture_pinholes'],
                      'R': ['cleavage_leaves',
                            'book_edges',
                            'lifted_leaf_corners',
                            'dark_interleaf_pockets',
                            'fracture_pinholes'],
                      'Cc': ['cleavage_leaves',
                             'book_edges',
                             'lifted_leaf_corners',
                             'dark_interleaf_pockets',
                             'fracture_pinholes']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Mica Books must visibly separate through cleavage leaves, book '
                                      'edges, lifted leaf corners and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Mica Books must visibly separate through cleavage leaves, book '
                                      'edges, lifted leaf corners and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Overlapping lamellar books show stacked edges and raised leaf '
                                     'corners.',
                                     'cleavage leaves is present in the native named-feature coverage '
                                     'probe.',
                                     'book edges is present in the native named-feature coverage probe.',
                                     'lifted leaf corners is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/mica_books/independent-feature-carrier',
 'spec_key': 'spec-v2/mica_books/named-material-bindings'}

render = build_renderer(mica_books, IDENTITY_CONTRACT)
